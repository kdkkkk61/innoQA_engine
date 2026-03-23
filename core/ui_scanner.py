"""
core/ui_scanner.py — 통합 UI 스캐너

스캔 전략:
  scan_hints yaml 존재 → yaml 구동 검증 (confidence 1.0) + 자동 탐지 보완
  scan_hints yaml 없음 → 자동 탐지 폴백 (새 페이지 첫 투입 시)

탭 복원 원칙 (readonly):
  스캔 전 현재 활성 탭을 기억하고, 스캔 완료 후 반드시 복원한다.

설계 원칙:
  - ScanResult는 selector 문자열 보관 (Playwright Locator 미보관)
    → 직렬화 가능, 리포트에 그대로 기록 가능
  - 스캐너는 토글 ON/OFF 동작 검증 외에는 페이지 상태를 변경하지 않는다
  - known_bug 항목은 fail 카운트에서 제외 (PageScanReport.failed 미포함)
"""
from __future__ import annotations

import traceback
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.sync_api import Page
from utils.scan_logger import make_scan_logger


# ──────────────────────────────────────────────────────────────────────────────
# 결과 데이터 클래스
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ScanResult:
    """
    스캐너가 검사한 UI 요소 하나의 결과.

    Attributes:
        pattern  : "toggle_checkbox" | "plain_checkbox" | "radio_group" |
                   "text_input" | "tag_input" | "auto_detect" | "modal_open"
        selector : CSS selector 문자열
        label    : 사람이 읽을 수 있는 설명
        status   : "pass" | "fail" | "skip" | "known_bug" | "error"
        detail   : 결과 상세 메시지
        extra    : 패턴별 추가 정보 (dependent_fields, tag_id 등)
        order    : scan_hints yaml의 order 값 — 출력 정렬 기준 (None이면 패턴 타입 순)
    """
    pattern:  str
    selector: str
    label:    str
    status:   str
    detail:   str          = ""
    extra:    dict         = field(default_factory=dict)
    order:    Optional[int] = None

    def is_real_failure(self) -> bool:
        """known_bug 와 skip 은 실패 카운트에서 제외한다."""
        return self.status == "fail"


@dataclass
class PageScanReport:
    """페이지 하나의 전체 스캔 결과."""
    page_id:      str
    results:      list[ScanResult] = field(default_factory=list)
    tab_sections: list[dict]       = field(default_factory=list)
    # tab_sections: [{"label": str, "start_order": int}, ...] — start_order 오름차순
    # modal_tabs에 start_order가 정의된 탭만 포함.
    # 출력 시 r.order >= start_order 구간으로 탭 헤더 삽입에 사용.

    @property
    def passed(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "pass"]

    @property
    def failed(self) -> list[ScanResult]:
        return [r for r in self.results if r.is_real_failure()]

    @property
    def known_bugs(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "known_bug"]

    @property
    def errors(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "error"]

    def summary(self) -> str:
        return (
            f"[{self.page_id}] "
            f"pass={len(self.passed)} "
            f"fail={len(self.failed)} "
            f"known_bug={len(self.known_bugs)} "
            f"error={len(self.errors)}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 스캐너 본체
# ──────────────────────────────────────────────────────────────────────────────

class UIScanner:
    """
    scan_hints yaml + known_bugs yaml을 기반으로 페이지 UI를 검사한다.
    yaml이 없으면 HTML 속성 기반 자동 탐지로 폴백한다.

    사용법:
        scanner = UIScanner(page, config_dir="config")
        report  = scanner.scan("ransom_detect_policy", modal_open_fn=open_fn)
    """

    # 자동 탐지용 HTML 속성 기반 selector
    _ATTR_TOGGLE_SEL = 'input[type="checkbox"][toggle]'
    _ATTR_TEXT_INPUT = (
        'input[type="text"]:not([toggle]), '
        'input:not([type]):not([toggle]):not([hidden])'
    )
    _ATTR_NUMBER     = 'input[type="number"]'

    # 자동 탭 탐지 selector (Bootstrap 3 / AngularJS 패턴)
    _SEL_TAB_LINKS   = "ul#modalTabLayer li a"

    # 탭 전환 후 콘텐츠 안정 대기 (ms)
    _TAB_SETTLE_MS   = 300

    def __init__(self, page: Page, config_dir: str = "config") -> None:
        self.page = page
        self._config_dir = Path(config_dir)
        self._known_bugs: list[dict] = self._load_yaml(
            self._config_dir / "known_bugs.yaml"
        ) or []
        self._log = make_scan_logger()

    # ── 공개 API ──────────────────────────────────────────────────────────────

    def scan(
        self,
        page_id: str,
        modal_open_fn:  Optional[Callable] = None,
        modal_close_fn: Optional[Callable] = None,
    ) -> PageScanReport:
        """
        page_id에 해당하는 scan_hints를 로드하고 전체 패턴을 검사한다.

        scan_hints yaml 존재 → yaml 구동 검증 (모든 패턴 속성/동작 검증)
        scan_hints yaml 없음 → HTML 속성 기반 자동 탐지 폴백 (존재 여부 확인)

        Args:
            page_id:        config/scan_hints/{page_id}.yaml 식별자
            modal_open_fn:  모달을 열어주는 callable.
                            None이면 현재 DOM 상태 그대로 스캔한다.
            modal_close_fn: 모달을 닫아주는 callable.
                            None이면 hints의 modal_actions.close 버튼을 시도한다.
        """
        hints_path = self._config_dir / "scan_hints" / f"{page_id}.yaml"
        hints = self._load_yaml(hints_path)

        report = PageScanReport(page_id=page_id)

        # 모달 열기
        modal_opened = False
        if modal_open_fn:
            try:
                modal_open_fn()
                modal_opened = True
            except Exception:
                trigger_sel = (hints or {}).get("modal_trigger", {}).get("add", "")
                self._append_error(report, "modal_open", trigger_sel, "모달 열기")
                return report

        if hints:
            # YAML 구동 검증
            self._scan_from_hints(hints, report)
        else:
            # YAML 없음 → 자동 탐지 폴백
            print(f"[UIScanner] scan_hints 없음 — 자동 탐지 폴백: {hints_path}")
            self._scan_auto_fallback(report)

        # 모달 닫기
        if modal_opened:
            try:
                if modal_close_fn:
                    modal_close_fn()
                else:
                    close_btn = (hints or {}).get("modal_actions", {}).get("close")
                    if close_btn:
                        self.page.locator(close_btn).first.evaluate("el => el.click()")
            except Exception:
                pass

        return report

    # ── YAML 구동 스캔 ────────────────────────────────────────────────────────

    def _scan_from_hints(self, hints: dict, report: PageScanReport) -> None:
        """
        scan_hints yaml에 정의된 패턴을 순서대로 검증한다.

        탭 복원 원칙:
          스캔 시작 전 첫 번째 탭을 기억하고, 모든 패턴 스캔 완료 후 복원한다.
          각 패턴 스캔 메서드는 필요 시 자체적으로 탭을 전환한다.
        """
        tabs = hints.get("modal_tabs", [])
        original_tab = tabs[0] if tabs else None

        # tab_sections 구성 — start_order가 정의된 탭을 오름차순으로 report에 저장
        # 출력 단계에서 탭 구간 헤더 삽입에 사용됨
        report.tab_sections = sorted(
            [
                {"label": t.get("label", ""), "start_order": t["start_order"]}
                for t in tabs
                if "start_order" in t
            ],
            key=lambda t: t["start_order"],
        )

        # 탭이 있으면 첫 번째 탭에서 시작 (toggle/plain/radio는 탭 전환 없음)
        if original_tab:
            self._activate_tab(original_tab)

        # 패턴별 검증 (tag_input, text_input은 자체적으로 탭 전환)
        self._scan_toggle_checkboxes(hints, report)
        self._scan_plain_checkboxes(hints, report)
        self._scan_radio_groups(hints, report)
        self._scan_text_inputs(hints, report)
        self._scan_tag_inputs(hints, report)

        # 필수 필드 미입력 제출 검증 (마지막에 실행 — 모달 상태 변화 가능)
        self._scan_required_submit(hints, report)

        # 원래 탭으로 복원 (readonly 원칙)
        if original_tab:
            self._activate_tab(original_tab)

    # ── 자동 탐지 폴백 ────────────────────────────────────────────────────────

    def _scan_auto_fallback(self, report: PageScanReport) -> None:
        """
        scan_hints yaml이 없을 때 HTML 속성으로 자동 탐지한다.
        탭 구조가 있으면 탭별로 탐지하고 원래 탭 복원.
        결과는 존재 여부 확인 (pass / skip).
        """
        tabs = self._get_tabs_auto()

        if tabs:
            original_tab = tabs[0]
            for tab_label, tab_selector in tabs:
                self._switch_tab_by_selector(tab_selector)
                self._auto_detect_in_context("body", tab_label, report)
            # 원래 탭 복원
            self._switch_tab_by_selector(original_tab[1])
        else:
            self._auto_detect_in_context("body", None, report)

    def _auto_detect_in_context(
        self,
        context:   str,
        tab_label: Optional[str],
        report:    PageScanReport,
        exclude:   Optional[set[str]] = None,
    ) -> None:
        """
        HTML 속성 기반 자동 탐지 — 존재 여부만 확인.

        Args:
            exclude: 이미 hints에서 처리된 selector set.
                     중복 결과 방지 — 동일 selector는 hints 결과가 우선.
        """
        excluded = exclude or set()
        tab_info = f" (탭: {tab_label})" if tab_label else ""

        # ① toggle="" 속성 체크박스
        try:
            toggles = self.page.locator(
                f"{context} {self._ATTR_TOGGLE_SEL}"
            ).all()
            for cb in toggles:
                cb_id    = cb.get_attribute("id") or ""
                selector = f"input#{cb_id}" if cb_id else self._ATTR_TOGGLE_SEL
                if selector in excluded:
                    continue
                dependent = self._find_dependent_fields(cb)
                report.results.append(ScanResult(
                    pattern="auto_detect",
                    selector=selector,
                    label=f"[자동탐지] 토글 {cb_id}{tab_info}",
                    status="pass",
                    detail="toggle 속성 존재",
                    extra={"type": "toggle", "dependent_fields": dependent},
                ))
        except Exception:
            pass

        # ② text_input
        try:
            inputs = self.page.locator(
                f"{context} {self._ATTR_TEXT_INPUT}"
            ).all()
            for inp in inputs:
                inp_id   = inp.get_attribute("id") or ""
                selector = f"input#{inp_id}" if inp_id else 'input[type="text"]'
                if selector in excluded:
                    continue
                maxlen = inp.get_attribute("maxlength")
                report.results.append(ScanResult(
                    pattern="auto_detect",
                    selector=selector,
                    label=f"[자동탐지] text_input {inp_id}{tab_info}",
                    status="pass",
                    detail=f"text input 존재 (maxlength={maxlen})",
                    extra={"type": "text_input", "maxlength": maxlen},
                ))
        except Exception:
            pass

        # ③ number_input
        try:
            inputs = self.page.locator(
                f"{context} {self._ATTR_NUMBER}"
            ).all()
            for inp in inputs:
                inp_id   = inp.get_attribute("id") or ""
                selector = f"input#{inp_id}" if inp_id else 'input[type="number"]'
                if selector in excluded:
                    continue
                report.results.append(ScanResult(
                    pattern="auto_detect",
                    selector=selector,
                    label=f"[자동탐지] number_input {inp_id}{tab_info}",
                    status="pass",
                    detail="number input 존재",
                    extra={"type": "number_input"},
                ))
        except Exception:
            pass

    # ── 탭 처리 (YAML 기반) ───────────────────────────────────────────────────

    def _activate_tab(self, tab: dict) -> bool:
        """
        YAML에 정의된 탭을 활성화한다 (data_tab 속성 기준).

        반환:
            True  = 탭 정상 활성화
            False = 경고 다이얼로그 출현으로 탭 전환 차단됨
                    (다이얼로그는 자동으로 닫고 반환)
        """
        data_tab = tab.get("data_tab", "")
        self._log.debug(f"[tab] 활성화 시도: data_tab={data_tab!r}")
        try:
            tab_link = self.page.locator(f'a[data-tab="{data_tab}"]')
            if tab_link.count() > 0:
                tab_link.first.evaluate("el => el.click()")
                self.page.wait_for_timeout(self._TAB_SETTLE_MS)
                # 경고 다이얼로그 감지 (예: "정책 정보를 먼저 등록 하셔야 합니다.")
                if self._dismiss_warning_dialog():
                    self._log.debug(f"[tab] 경고 다이얼로그로 차단됨: {data_tab!r}")
                    return False  # 탭 전환 차단됨
            else:
                self._log.debug(f"[tab] 탭 링크 없음: a[data-tab={data_tab!r}]")
        except Exception:
            self._log.debug(f"[tab] 예외 발생:\n{traceback.format_exc()}")
        self._log.debug(f"[tab] 활성화 완료: {data_tab!r}")
        return True

    # 앱 공통 경고 다이얼로그 selector (login_page.py SEL_ERROR_MODAL과 동일)
    _SEL_WARN_MODAL        = "div#__globalMessageModal.in"
    _SEL_WARN_MODAL_CLOSED = "div#__globalMessageModal"   # .in 없으면 닫혀있음

    def _dismiss_warning_dialog(self) -> bool:
        """
        탭 전환 등으로 출현하는 경고/알림 다이얼로그를 감지하고 닫는다.

        감지: div#__globalMessageModal.in — 앱 공통 경고 다이얼로그
              (로그인 오류, 탭 접근 차단 등 모든 경고에 사용되는 공통 모달)

        주의: .modal.in 전체를 탐색하면 addItemModal의 "닫기" 버튼까지 포함되어
              메인 모달이 닫힌다 — 반드시 #__globalMessageModal 직접 지정 필요.

        반환:
            True  = 다이얼로그가 있었고 닫음 (탭 전환 차단 상태였음)
            False = 다이얼로그 없음 (탭 전환 정상)
        """
        try:
            warn_modal = self.page.locator(self._SEL_WARN_MODAL)
            if warn_modal.count() == 0:
                return False
            self._log.debug(f"[warn_dialog] 경고 모달 감지됨 ({self._SEL_WARN_MODAL})")
            # 확인 버튼 클릭 (내부 첫 번째 버튼 — data-dismiss 또는 텍스트 버튼)
            confirm = warn_modal.locator("button")
            if confirm.count() > 0:
                self._log.debug("[warn_dialog] 확인 버튼 클릭")
                confirm.first.evaluate("el => el.click()")
                self.page.wait_for_timeout(300)
                return True
            else:
                self._log.debug("[warn_dialog] 버튼 없음 — 닫기 불가")
        except Exception:
            self._log.debug(f"[warn_dialog] 예외 발생:\n{traceback.format_exc()}")
        return False

    # ── 탭 처리 (자동 탐지 폴백) ──────────────────────────────────────────────

    def _get_tabs_auto(self) -> list[tuple[str, str]]:
        """Bootstrap 3 탭 목록 자동 탐지 (YAML 없을 때 사용)."""
        tabs = []
        try:
            tab_links = self.page.locator(self._SEL_TAB_LINKS).all()
            for i, tab in enumerate(tab_links):
                label    = tab.inner_text().strip() or f"탭{i + 1}"
                href     = tab.get_attribute("href") or f"#tab{i}"
                base_sel = self._SEL_TAB_LINKS.rsplit(" a", 1)[0]
                selector = f'{base_sel} a[href="{href}"]'
                tabs.append((label, selector))
        except Exception:
            pass
        return tabs

    def _switch_tab_by_selector(self, tab_selector: str) -> None:
        """selector로 탭을 클릭한다 (자동 탐지 폴백용)."""
        try:
            self.page.locator(tab_selector).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(self._TAB_SETTLE_MS)
        except Exception:
            pass

    # ── 스캔 결과 헬퍼 ───────────────────────────────────────────────────────

    @staticmethod
    def _status_detail(failures: list[str], checks: list[str]) -> tuple[str, str]:
        """failures/checks 리스트에서 status·detail 문자열을 생성한다."""
        status = "fail" if failures else "pass"
        detail = "; ".join(failures) if failures else " + ".join(checks)
        return status, detail

    def _append_error(
        self,
        report: PageScanReport,
        pattern: str,
        selector: str,
        label: str,
        order=None,
    ) -> None:
        """예외 발생 시 로그 기록 후 ScanResult(error)를 report에 추가한다."""
        tb = traceback.format_exc()
        self._log.error(f"[{pattern}] {label!r} ({selector}) 예외 발생:\n{tb}")
        report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="error", detail=tb, order=order,
        ))

    # ── 토글 체크박스 스캔 ────────────────────────────────────────────────────

    def _scan_toggle_checkboxes(self, hints: dict, report: PageScanReport) -> None:
        """
        toggle_checkboxes 항목을 검증한다.

        known_bug 항목도 실제로 검사한다 — 어떤 필드가 비정상인지 개별 확인이 목적.
        is_known_bug=True 로 전달하면 _check_toggle_with_deps 내부에서
        실패한 종속 필드를 "fail" 대신 "known_bug" 로 마킹한다.

        dependent_fields 포맷 두 가지 모두 지원:
          구형(str 리스트): ["input#foo", "input#bar"]  ← 하위 호환
          신형(dict 리스트): [{selector, label, type, maxlength?, onpaste_blocked?}, ...]
        """
        for toggle in hints.get("toggle_checkboxes", []):
            selector        = toggle["selector"]
            label           = toggle.get("label", selector)
            raw_deps        = toggle.get("dependent_fields", [])
            is_kb           = self._is_known_bug(selector, "toggle_dependent_fields")
            default_checked = toggle.get("default")  # True/False/None

            # ── 포맷 정규화 ──────────────────────────────────────────────────
            # 구형(str) → dict 변환, 신형은 그대로 사용
            dep_fields: list[dict] = []
            for d in raw_deps:
                if isinstance(d, str):
                    dep_fields.append({"selector": d, "label": d, "type": "field"})
                else:
                    dep_fields.append(d)

            # 출력용 레이블·타입 리스트 (test_ui_scan.py 프린터 호환)
            dep_labels = [d.get("label", d["selector"]) for d in dep_fields]
            dep_types  = [d.get("type", "field")         for d in dep_fields]

            try:
                result = self._check_toggle_with_deps(
                    selector, label, dep_fields,
                    is_known_bug=is_kb,
                    default_checked=default_checked,
                )
                result.order = toggle.get("order")
                result.extra.update({
                    "dependent_labels": dep_labels,
                    "dependent_types":  dep_types,
                })
                report.results.append(result)
            except Exception:
                self._append_error(report, "toggle_checkbox", selector, label, toggle.get("order"))

    def _check_toggle_with_deps(
        self,
        selector:        str,
        label:           str,
        dep_fields:      list[dict],
        is_known_bug:    bool = False,
        default_checked: Optional[bool] = None,
    ) -> ScanResult:
        """
        토글 + 종속 필드 동작 검증 (C안: OFF→ON+입력→OFF재확인→복원).

        ① 기본값 확인 (default_checked 전달 시) — 모달 최초 열린 상태 기준
        ② OFF 상태 → 각 종속 필드 disabled 여부 확인
        ③ ON  상태 → enabled 확인 + 종속 필드 실제 입력 테스트 (_test_dep_input)
        ④ OFF 재확인 → ON→OFF 전환 후에도 disabled 유지 여부 재검증
        ⑤ 원래 상태로 복원

        is_known_bug=True 이면 실패 종속 필드를 "fail" 대신 "known_bug" 로 마킹.

        dep_fields 항목 구조:
            {selector, label, type, maxlength?(number/text), onpaste_blocked?(text)}

        반환하는 ScanResult.extra:
            "dependent_fields"  : dep_fields 원본 리스트
            "dependent_results" : 필드별 {"selector", "status", "detail"} 딕트 리스트
        """
        dep_selectors = [d["selector"] for d in dep_fields]
        toggle_loc    = self.page.locator(selector)

        if toggle_loc.count() == 0:
            return ScanResult(
                pattern="toggle_checkbox",
                selector=selector,
                label=label,
                status="skip",
                detail="요소를 찾을 수 없음",
                extra={"dependent_fields": dep_fields, "dependent_results": []},
            )

        # 종속 필드 없는 단순 토글 — 존재 확인만
        if not dep_fields:
            return ScanResult(
                pattern="toggle_checkbox",
                selector=selector,
                label=label,
                status="pass",
                detail="토글 존재 확인 (종속 필드 없음)",
                extra={"dependent_fields": [], "dependent_results": []},
            )

        was_checked = toggle_loc.is_checked()

        # ① 기본값 확인
        default_fail: Optional[str] = None
        if default_checked is not None and was_checked != default_checked:
            expected = "ON" if default_checked else "OFF"
            actual   = "ON" if was_checked    else "OFF"
            default_fail = f"기본값 불일치 (기대: {expected}, 실제: {actual})"

        # ② OFF 상태 → 종속 필드 disabled 확인
        # off1_ok[sel]: True=정상(disabled), False=비정상(enabled), None=요소없음
        off1_ok: dict[str, bool | None] = {}
        if was_checked:
            toggle_loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(400)

        for sel in dep_selectors:
            loc = self.page.locator(sel)
            off1_ok[sel] = None if loc.count() == 0 else not loc.is_enabled()

        # ③ ON 상태 → enabled 확인 + 실제 입력 테스트
        # on_ok[sel]: True=정상(enabled), False=비정상(disabled), None=요소없음
        on_ok:        dict[str, bool | None] = {}
        input_res:    dict[str, dict]        = {}   # sel → _test_dep_input 결과
        toggle_loc.evaluate("el => el.click()")
        self.page.wait_for_timeout(400)

        for dep in dep_fields:
            sel = dep["selector"]
            loc = self.page.locator(sel)
            if loc.count() == 0:
                on_ok[sel] = None
            else:
                on_ok[sel] = loc.is_enabled()
                if on_ok[sel]:
                    input_res[sel] = self._test_dep_input(dep)

        # ④ OFF 재확인 → ON→OFF 전환 후에도 disabled 유지 여부
        # off2_ok[sel]: True=정상(disabled), False=비정상(enabled), None=요소없음
        off2_ok: dict[str, bool | None] = {}
        toggle_loc.evaluate("el => el.click()")
        self.page.wait_for_timeout(400)

        for sel in dep_selectors:
            loc = self.page.locator(sel)
            off2_ok[sel] = None if loc.count() == 0 else not loc.is_enabled()

        # ⑤ 원래 상태로 복원
        current = toggle_loc.is_checked()
        if current != was_checked:
            toggle_loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(200)

        # ── 필드별 독립 결과 조립 ─────────────────────────────────────────────
        dep_results: list[dict] = []
        real_fail_count = 0
        known_bug_count = 0

        for dep in dep_fields:
            sel  = dep["selector"]
            o1   = off1_ok.get(sel)
            n    = on_ok.get(sel)
            o2   = off2_ok.get(sel)
            i_r  = input_res.get(sel, {})

            if o1 is None and n is None and o2 is None:
                dep_results.append({"selector": sel, "status": "skip", "detail": "요소 없음"})
                continue

            issues: list[str] = []
            checks: list[str] = []

            if o1 is False:
                issues.append("OFF 시 활성화됨 (비정상)")
            elif o1 is True:
                checks.append("OFF→disabled")

            if n is False:
                issues.append("ON 시 비활성화됨 (비정상)")
            elif n is True:
                checks.append("ON→enabled")

            if o2 is False:
                issues.append("ON→OFF 전환 후 활성화 유지됨 (비정상)")
            elif o2 is True:
                checks.append("OFF재확인→disabled")

            # 입력 테스트 결과 병합
            if i_r:
                if i_r.get("status") == "fail":
                    issues.append(f"입력 테스트 실패: {i_r.get('detail', '')}")
                elif i_r.get("status") == "pass":
                    checks.append(i_r.get("detail", "입력 테스트 pass"))

            if issues:
                if is_known_bug:
                    dep_status = "known_bug"
                    known_bug_count += 1
                else:
                    dep_status = "fail"
                    real_fail_count += 1
                dep_results.append({
                    "selector": sel,
                    "status":   dep_status,
                    "detail":   ", ".join(issues),
                })
            else:
                detail_str = " + ".join(checks) if checks else "ON/OFF 정상"
                dep_results.append({"selector": sel, "status": "pass", "detail": detail_str})

        # ── 부모 토글 요약 상태 결정 ──────────────────────────────────────────
        if real_fail_count > 0 or default_fail:
            parent_status = "fail"
            msgs: list[str] = []
            if default_fail:
                msgs.append(default_fail)
            if real_fail_count > 0:
                msgs.append(f"종속 필드 {real_fail_count}개 검증 실패")
            parent_detail = "; ".join(msgs)
        elif known_bug_count > 0:
            parent_status = "known_bug"
            parent_detail = (
                f"알려진 버그 — 종속 필드 {known_bug_count}개 비정상"
                f" ({len(dep_fields) - known_bug_count}개 정상)"
            )
        else:
            parent_status = "pass"
            parts: list[str] = []
            if default_checked is not None:
                parts.append(f"기본값 {'ON' if default_checked else 'OFF'} 확인")
            if dep_fields:
                parts.append(f"종속 필드 {len(dep_fields)}개 ON/OFF+입력 정상")
            parent_detail = " + ".join(parts) if parts else "토글 존재 확인"

        return ScanResult(
            pattern="toggle_checkbox",
            selector=selector,
            label=label,
            status=parent_status,
            detail=parent_detail,
            extra={"dependent_fields": dep_fields, "dependent_results": dep_results},
        )

    # ── 종속 필드 입력 테스트 헬퍼 ───────────────────────────────────────────

    def _test_dep_input(self, dep_field: dict) -> dict:
        """
        ON 상태에서 종속 필드 타입별 실제 입력 테스트를 수행한다.

        dep_field 키:
            selector         : CSS selector
            type             : "number_input" | "text_input" | "plain_checkbox" | "field"
            maxlength        : (number/text) 기대 maxlength 값 (없으면 자동 감지)
            onpaste_blocked  : (text) True이면 onpaste="return false" 속성 검증

        반환: {"status": "pass"|"fail"|"skip", "detail": str}
        """
        ftype    = dep_field.get("type", "field")
        sel      = dep_field["selector"]
        maxlen   = dep_field.get("maxlength")
        onpaste  = dep_field.get("onpaste_blocked", False)

        if ftype == "plain_checkbox":
            return self._test_plain_checkbox_dep(sel)
        elif ftype in ("number_input", "text_input"):
            return self._test_text_like_dep(sel, maxlen, onpaste, ftype)
        else:
            return {"status": "skip", "detail": f"입력 테스트 미지원 타입: {ftype}"}

    def _test_text_like_dep(
        self,
        selector:        str,
        maxlength:       Optional[int],
        onpaste_blocked: bool,
        ftype:           str = "text_input",
    ) -> dict:
        """
        number_input / text_input 종속 필드 입력 테스트.

        maxlength 지정 시:
          ① HTML maxlength 속성값 확인 (기대값 vs 실제)
          ② maxlength+5 글자 입력 → 실제 길이로 truncation 동작 확인
        maxlength 미지정 시:
          ③ "1234567890" (10자) 입력 → 실제 입력된 길이로 제한 자동 감지
        onpaste_blocked=True 시:
          ④ onpaste="return false" 속성 존재 확인
        공통:
          ⑤ 입력/삭제 시도
             - text_input : 삭제 불가 시 fail
             - number_input: 삭제 불가는 앱 유효성 검사로 간주 → 정보로만 기록 (pass 유지)
        """
        loc = self.page.locator(selector)
        if loc.count() == 0:
            return {"status": "skip", "detail": "요소 없음"}

        checks:   list[str] = []
        failures: list[str] = []

        # ① maxlength 속성 + ② truncation 동작
        if maxlength is not None:
            actual_attr = loc.get_attribute("maxlength")
            if actual_attr is None:
                failures.append(f"maxlength 속성 없음 (기대: {maxlength})")
            elif int(actual_attr) != maxlength:
                failures.append(
                    f"maxlength 불일치 (기대: {maxlength}, 실제: {actual_attr})"
                )
            else:
                loc.fill("1" * (maxlength + 5))
                actual_len = len(loc.input_value())
                if actual_len > maxlength:
                    failures.append(
                        f"maxlength {maxlength}자 미적용 ({actual_len}자 입력됨)"
                    )
                else:
                    checks.append(f"maxlength {maxlength}자 동작 확인")
        else:
            # ③ 자동 감지: 10자 입력
            loc.fill("1234567890")
            actual_len = len(loc.input_value())
            if actual_len < 10:
                checks.append(f"maxlength {actual_len}자 감지 (YAML 미명시)")
            else:
                checks.append("maxlength 없음 (10자 이상 가능)")

        # ④ onpaste 차단 속성 확인
        if onpaste_blocked:
            attr = loc.get_attribute("onpaste") or ""
            if "false" in attr:
                checks.append("붙여넣기 차단 확인 (onpaste)")
            else:
                failures.append("onpaste 차단 속성 없음")

        # ⑤ 입력/삭제 시도
        loc.fill("")
        if loc.input_value() != "":
            if ftype == "number_input":
                # 설정값 필드는 비움 불가가 앱 유효성 검사일 수 있음 → 정보로만 기록
                checks.append("비움 불가 (앱 유효성 검사 추정)")
            else:
                failures.append("입력 후 삭제 불가")
        else:
            checks.append("입력/삭제 자유도 확인")

        status, detail = self._status_detail(failures, checks)
        return {"status": status, "detail": detail}

    def _test_plain_checkbox_dep(self, selector: str) -> dict:
        """
        plain_checkbox 종속 필드 클릭 동작 테스트.
        ON 상태일 때 호출된다 — 클릭 후 상태 변경 확인 후 원래 상태로 복원.
        """
        loc = self.page.locator(selector)
        if loc.count() == 0:
            return {"status": "skip", "detail": "요소 없음"}

        was   = loc.is_checked()
        loc.evaluate("el => el.click()")
        self.page.wait_for_timeout(200)
        after = loc.is_checked()

        # 원래 상태 복원
        if after != was:
            loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(200)

        if after != was:
            return {"status": "pass", "detail": "클릭 동작 확인"}
        else:
            return {"status": "fail", "detail": "클릭 후 상태 미변경"}

    # ── 일반 체크박스 스캔 ────────────────────────────────────────────────────

    def _scan_plain_checkboxes(self, hints: dict, report: PageScanReport) -> None:
        """
        plain_checkboxes 항목을 검증한다.

        검증 항목:
          ① 요소 DOM 존재 확인
          ② label[for="id"] 클릭 시 체크 상태 변화 확인 (라벨 클릭 동작 테스트)
             - label[for] 없으면 조상 <label> 시도
             - label 자체가 없으면 "label[for] 없음" 으로 생략 처리
          검증 후 원래 체크 상태로 복원.
        """
        for cb in hints.get("plain_checkboxes", []):
            selector = cb["selector"]
            label    = cb.get("label", selector)
            order    = cb.get("order")
            self._log.debug(f"[plain_checkbox] 스캔 시작: {label!r} ({selector})")
            try:
                loc = self.page.locator(selector)
                if loc.count() == 0:
                    report.results.append(ScanResult(
                        pattern="plain_checkbox",
                        selector=selector,
                        label=label,
                        status="skip",
                        detail="요소를 찾을 수 없음",
                        order=order,
                    ))
                    continue

                failures: list[str] = []
                checks:   list[str] = ["존재 확인"]

                # ② 라벨 클릭 동작 테스트
                cb_id     = selector.replace("input#", "", 1)
                label_loc = self.page.locator(f'label[for="{cb_id}"]')

                # label[for] 없으면 조상 <label> 시도
                if label_loc.count() == 0:
                    has_ancestor = loc.evaluate("el => !!el.closest('label')")
                    if has_ancestor:
                        label_loc = self.page.locator(f"label:has({selector})")

                if label_loc.count() > 0:
                    self._log.debug(f"[plain_checkbox] {label!r} → is_checked() 호출")
                    before = loc.is_checked()
                    self._log.debug(f"[plain_checkbox] {label!r} → 라벨 클릭 (before={before})")
                    label_loc.first.evaluate("el => el.click()")
                    self.page.wait_for_timeout(300)
                    after = loc.is_checked()
                    self._log.debug(f"[plain_checkbox] {label!r} → 클릭 후 after={after}")

                    if after == before:
                        failures.append("라벨 클릭 무반응 (체크 상태 변화 없음)")
                    else:
                        checks.append("라벨 클릭 동작 확인")
                        # 원래 상태로 복원
                        self._log.debug(f"[plain_checkbox] {label!r} → 상태 복원")
                        loc.evaluate("el => el.click()")
                        self.page.wait_for_timeout(200)
                else:
                    checks.append("label[for] 없음 (라벨 클릭 테스트 생략)")

                status, detail = self._status_detail(failures, checks)
                self._log.debug(f"[plain_checkbox] {label!r} → {status}: {detail}")
                report.results.append(ScanResult(
                    pattern="plain_checkbox",
                    selector=selector,
                    label=label,
                    status=status,
                    detail=detail,
                    order=order,
                ))
            except Exception:
                self._append_error(report, "plain_checkbox", selector, label, order)

    # ── 라디오 그룹 스캔 ──────────────────────────────────────────────────────

    def _scan_radio_groups(self, hints: dict, report: PageScanReport) -> None:
        """
        radio_groups를 검증한다.

        검증 항목:
          ① 모든 옵션 DOM 존재 확인
          ② 기본값 확인 (YAML default 정의 시) — 모달 최초 열렸을 때 선택 상태 검증
          ③ 클릭 변경 동작 테스트 — 현재 선택 외 다른 옵션 클릭 → checked 변화 확인 → 복원
        """
        for group in hints.get("radio_groups", []):
            name          = group["name"]
            label         = group.get("label", name)
            options       = group.get("options", [])
            order         = group.get("order")
            default_value = group.get("default")  # YAML에 정의된 기본 선택값

            self._log.debug(f"[radio_group] 스캔 시작: {label!r} (name={name})")
            try:
                # ① 모든 옵션 존재 확인
                missing = [
                    opt["selector"]
                    for opt in options
                    if self.page.locator(opt["selector"]).count() == 0
                ]
                if missing:
                    report.results.append(ScanResult(
                        pattern="radio_group",
                        selector=f"[name={name}]",
                        label=label,
                        status="fail",
                        detail=f"라디오 옵션 누락: {missing}",
                        order=order,
                    ))
                    continue

                failures: list[str] = []
                checks:   list[str] = [f"옵션 {len(options)}개 모두 존재"]

                # ② 기본값 확인
                if default_value is not None:
                    default_opt = next(
                        (o for o in options if o.get("value") == default_value), None
                    )
                    if default_opt is None:
                        failures.append(f"YAML default '{default_value}' 에 해당하는 옵션 없음")
                    elif not self.page.locator(default_opt["selector"]).is_checked():
                        failures.append(f"기본값 불일치 (기대: '{default_value}')")
                    else:
                        checks.append(f"기본값 '{default_value}' 확인")

                # ③ 클릭 변경 동작 테스트
                # 현재 선택 옵션 파악
                self._log.debug(f"[radio_group] {label!r} → 현재 선택 옵션 파악")
                current_opt = next(
                    (o for o in options
                     if self.page.locator(o["selector"]).is_checked()),
                    None,
                )
                self._log.debug(f"[radio_group] {label!r} → current={current_opt and current_opt.get('value')!r}")
                # 현재 선택과 다른 옵션 선택
                alt_opt = next(
                    (o for o in options if o != current_opt), None
                )
                if alt_opt:
                    self._log.debug(f"[radio_group] {label!r} → alt 클릭: {alt_opt.get('value')!r}")
                    alt_loc = self.page.locator(alt_opt["selector"])
                    alt_loc.evaluate("el => el.click()")
                    self.page.wait_for_timeout(300)
                    if alt_loc.is_checked():
                        checks.append("클릭 변경 동작 확인")
                        # 원래 옵션으로 복원
                        if current_opt:
                            self._log.debug(f"[radio_group] {label!r} → 복원: {current_opt.get('value')!r}")
                            self.page.locator(current_opt["selector"]).evaluate(
                                "el => el.click()"
                            )
                            self.page.wait_for_timeout(200)
                    else:
                        failures.append("라디오 클릭 후 선택 상태 변화 없음")

                status, detail = self._status_detail(failures, checks)
                self._log.debug(f"[radio_group] {label!r} → {status}: {detail}")
                report.results.append(ScanResult(
                    pattern="radio_group",
                    selector=f"[name={name}]",
                    label=label,
                    status=status,
                    detail=detail,
                    order=order,
                ))

            except Exception:
                self._append_error(report, "radio_group", f"[name={name}]", label, order)

    # ── 텍스트 입력 스캔 ──────────────────────────────────────────────────────

    def _scan_text_inputs(self, hints: dict, report: PageScanReport) -> None:
        """
        text_inputs 항목을 검증한다.
        tab 필드가 있으면 검사 전 해당 탭을 활성화한다.

        검증 항목:
          ① maxlength 속성 값 일치 확인
          ② maxlength 실제 동작 — maxlength+5 글자 입력 후 잘리는지 확인
          ③ 입력/삭제 자유도 — 값 입력 후 clear 가능한지 확인
          ④ required 마커 — HTML required 속성 또는 label .star 마커 존재
          ① ④는 속성 검사, ② ③은 동작 테스트. 검증 후 필드 값 복원(fill "").
        """
        for inp in hints.get("text_inputs", []):
            selector  = inp["selector"]
            label     = inp.get("label", selector)
            maxlength = inp.get("maxlength")
            required  = inp.get("required", False)
            order     = inp.get("order")

            self._log.debug(f"[text_input] 스캔 시작: {label!r} ({selector})")
            # 탭 전환 필요 시
            tab = inp.get("tab")
            if tab:
                self._activate_tab({"data_tab": tab})

            try:
                loc = self.page.locator(selector)
                if loc.count() == 0:
                    report.results.append(ScanResult(
                        pattern="text_input",
                        selector=selector,
                        label=label,
                        status="skip",
                        detail="요소를 찾을 수 없음",
                        order=order,
                    ))
                    continue

                # 원래 값 저장 — 스캔 후 복원 (EDIT 모달 대응)
                original_value = loc.input_value()

                failures: list[str] = []
                checks:   list[str] = ["존재 확인"]

                # ① maxlength 속성 확인
                if maxlength is not None:
                    actual_ml = loc.get_attribute("maxlength")
                    if actual_ml is None:
                        failures.append(f"maxlength 속성 없음 (기대: {maxlength})")
                    elif int(actual_ml) != maxlength:
                        failures.append(
                            f"maxlength 불일치 (기대: {maxlength}, 실제: {actual_ml})"
                        )
                    else:
                        # ② maxlength 실제 동작 테스트
                        test_str = "x" * (maxlength + 5)
                        self._log.debug(f"[text_input] {label!r} → fill({len(test_str)}자)")
                        loc.fill(test_str)
                        actual_len = len(loc.input_value())
                        if actual_len > maxlength:
                            failures.append(
                                f"maxlength {maxlength}자 실제 미적용"
                                f" ({actual_len}자 입력됨)"
                            )
                        else:
                            checks.append(f"maxlength {maxlength}자 실제 동작 확인")
                        # ③ 삭제 자유도 (maxlength 테스트 후 clear)
                        loc.fill("")
                        if loc.input_value() != "":
                            failures.append("입력 후 삭제 불가")
                        else:
                            checks.append("입력/삭제 자유도 확인")
                else:
                    # maxlength 없을 때도 ③ 입력/삭제 자유도만 확인
                    loc.fill("scan_test")
                    loc.fill("")
                    if loc.input_value() != "":
                        failures.append("입력 후 삭제 불가")
                    else:
                        checks.append("입력/삭제 자유도 확인")

                # 원래 값 복원
                if loc.input_value() != original_value:
                    loc.fill(original_value)

                # ④ required 마커 확인
                if required:
                    has_req_attr = loc.get_attribute("required") is not None
                    inp_id       = selector.replace("input#", "", 1)
                    label_sel    = f'label[for="{inp_id}"] .star'
                    has_star     = self.page.locator(label_sel).count() > 0
                    if not has_req_attr and not has_star:
                        failures.append(
                            "필수 필드 표시 없음 (required 속성 & .star 마커 모두 미확인)"
                        )
                    else:
                        checks.append("required 마커 확인")

                status, detail = self._status_detail(failures, checks)
                self._log.debug(f"[text_input] {label!r} → {status}: {detail}")
                report.results.append(ScanResult(
                    pattern="text_input",
                    selector=selector,
                    label=label,
                    status=status,
                    detail=detail,
                    order=order,
                ))

            except Exception:
                self._append_error(report, "text_input", selector, label, order)

    # ── 태그 입력 스캔 ────────────────────────────────────────────────────────

    # 태그 삭제 버튼 자동 탐지 시 시도 패턴 (컨테이너 내부 상대 selector)
    _REMOVE_BTN_PATTERNS = [
        ".delBtn", ".del", ".removeBtn", ".remove-btn",
        ".close", ".btn-delete", ".tag-delete",
        "[ng-click*='remove']", "[ng-click*='delete']", "[ng-click*='del']",
    ]

    def _scan_tag_inputs(self, hints: dict, report: PageScanReport) -> None:
        """
        tag_input 항목을 검증한다.
        tab 필드가 있으면 검사 전 해당 탭을 활성화한다.

        검증 항목:
          ① input + add_btn + container 세 요소 DOM 존재 확인
          ② required 마커 (required: true 시) — dt의 * 또는 .star
          ③ 태그 추가 동작 — test_value 입력 후 add_btn 클릭 → container 항목 증가 확인
          ④ 태그 삭제 동작 — remove_btn 클릭 → container 항목 감소 확인
             remove_btn: YAML 명시 우선, 없으면 container 내 자동 탐지

        required_toggle: 탭 접근 전 활성화해야 하는 prerequisite 토글 selector.
          탭 활성화 실패(경고 다이얼로그) 시 해당 토글을 ON하고 재시도.
          스캔 완료 후 원래 상태로 복원.
        """
        # required_toggle 복원 추적: {selector: was_checked}
        _toggle_restore: dict[str, bool] = {}

        for tag in hints.get("tag_input", []):
            tag_id         = tag["id"]
            label          = tag.get("label", tag_id)
            inp_sel        = tag["input"]
            btn_sel        = tag["add_btn"]
            cont_sel       = tag["container"]
            required       = tag.get("required", False)
            order          = tag.get("order")
            test_value        = tag.get("test_value", "scan_test")
            unique_test_value = tag.get("unique_test_value")  # 중복 거부 후 실제 추가용 고유값
            remove_btn_sel    = tag.get("remove_btn")  # 명시적 selector (선택)
            required_toggle   = tag.get("required_toggle")   # 탭 접근 prerequisite 토글

            self._log.debug(f"[tag_input] 스캔 시작: {label!r} (id={tag_id})")
            # 탭 전환 필요 시
            # tab_activated=False → 경고 다이얼로그로 차단됨 → 동작 테스트(③④) 스킵
            tab_activated = True
            tab_id = tag.get("tab")
            if tab_id:
                tab_activated = self._activate_tab({"data_tab": tab_id})
                # 탭 접근 차단 + prerequisite 토글 지정 → 토글 ON 후 재시도
                if not tab_activated and required_toggle:
                    req_loc = self.page.locator(required_toggle)
                    if req_loc.count() > 0:
                        prev_checked = req_loc.is_checked()
                        if required_toggle not in _toggle_restore:
                            _toggle_restore[required_toggle] = prev_checked
                        if not prev_checked:
                            self._log.debug(
                                f"[tag_input] {label!r} → required_toggle ON: {required_toggle}"
                            )
                            req_loc.evaluate("el => el.click()")
                            self.page.wait_for_timeout(300)
                        tab_activated = self._activate_tab({"data_tab": tab_id})
            self._log.debug(f"[tag_input] {label!r} → tab_activated={tab_activated}")

            try:
                # ① 세 요소 존재 확인
                missing = [
                    sel
                    for sel in [inp_sel, btn_sel, cont_sel]
                    if self.page.locator(sel).count() == 0
                ]
                if missing:
                    report.results.append(ScanResult(
                        pattern="tag_input",
                        selector=inp_sel,
                        label=label,
                        status="fail",
                        detail=f"요소 누락: {missing}",
                        extra={"tag_id": tag_id},
                        order=order,
                    ))
                    continue

                failures: list[str] = []
                checks:   list[str] = ["input + 추가버튼 + 컨테이너 존재"]

                # ② required 마커 검증
                if required:
                    inp_id       = inp_sel.replace("input#", "", 1)
                    has_star_cls = self.page.locator(
                        f'label[for="{inp_id}"] .star, dt .star'
                    ).count() > 0
                    has_req_attr = self.page.locator(inp_sel).get_attribute("required") is not None
                    if not has_star_cls and not has_req_attr:
                        try:
                            dt_text = self.page.locator(inp_sel).evaluate(
                                "el => el.closest('dl')?.querySelector('dt')?.textContent || ''"
                            )
                            if "*" not in dt_text and "＊" not in dt_text:
                                failures.append("필수 필드 표시 없음 (dt에 * 마커 미확인)")
                            else:
                                checks.append("required 마커 확인")
                        except Exception:
                            failures.append("필수 필드 마커 확인 중 오류")
                    else:
                        checks.append("required 마커 확인")

                # ③④ 동작 테스트 — 탭이 경고 다이얼로그로 차단된 경우 스킵
                # (ADD 모달에서 예외처리 탭은 정책 저장 전 접근 불가)
                if not tab_activated:
                    checks.append("생성 시 작성 불가 (탭 클릭 시 앱이 경고로 차단 — 수정 모달에서 검증)")
                else:
                    # ③ 태그 추가 동작 테스트
                    cont_loc = self.page.locator(cont_sel)
                    inp_loc  = self.page.locator(inp_sel)
                    btn_loc  = self.page.locator(btn_sel)

                    self._log.debug(f"[tag_input] {label!r} → 초기 항목 수 카운트 ({cont_sel})")
                    initial_count = cont_loc.evaluate(
                        "el => el.querySelectorAll(':scope > *').length"
                    )
                    self._log.debug(f"[tag_input] {label!r} → initial_count={initial_count}")

                    # ③-1차: test_value 추가 시도
                    self._log.debug(f"[tag_input] {label!r} → fill({test_value!r}) → {inp_sel}")
                    inp_loc.fill(test_value)
                    self.page.wait_for_timeout(200)
                    self._log.debug(f"[tag_input] {label!r} → add_btn 클릭 ({btn_sel})")
                    btn_loc.first.evaluate("el => el.click()")
                    self.page.wait_for_timeout(400)

                    after_first = cont_loc.evaluate(
                        "el => el.querySelectorAll(':scope > *').length"
                    )
                    self._log.debug(f"[tag_input] {label!r} → after_first={after_first}")

                    tag_was_added = False

                    if after_first > initial_count:
                        # 추가 성공 (ADD 모달 정상 케이스, 또는 EDIT에서 중복 아닌 경우)
                        checks.append("태그 추가 동작 확인")
                        tag_was_added = True

                    elif unique_test_value:
                        # 추가 거부 → 중복 검사 확인 후 unique_test_value로 2차 시도
                        checks.append(f"중복 입력 거부 확인 ({test_value!r})")
                        self._log.debug(
                            f"[tag_input] {label!r} → 2차 시도: "
                            f"unique_test_value={unique_test_value!r}"
                        )
                        inp_loc.fill(unique_test_value)
                        self.page.wait_for_timeout(200)
                        btn_loc.first.evaluate("el => el.click()")
                        self.page.wait_for_timeout(400)

                        after_second = cont_loc.evaluate(
                            "el => el.querySelectorAll(':scope > *').length"
                        )
                        self._log.debug(
                            f"[tag_input] {label!r} → after_second={after_second}"
                        )
                        if after_second > after_first:
                            checks.append("태그 추가 동작 확인")
                            tag_was_added = True
                        else:
                            failures.append(
                                f"태그 추가 동작 실패 (추가 전: {after_first},"
                                f" 추가 후: {after_second})"
                            )

                    else:
                        # unique_test_value 없이 추가 거부 → 실패
                        failures.append(
                            f"태그 추가 동작 실패 (추가 전: {initial_count},"
                            f" 추가 후: {after_first})"
                        )

                    # ④ 태그 삭제 동작 테스트 (태그가 실제로 추가된 경우에만)
                    if tag_was_added:
                        # remove_btn 미명시 시 자동 탐지
                        if not remove_btn_sel:
                            for pat in self._REMOVE_BTN_PATTERNS:
                                if cont_loc.locator(pat).count() > 0:
                                    remove_btn_sel = pat  # 컨테이너 내 상대 selector
                                    self._log.debug(f"[tag_input] {label!r} → 삭제버튼 자동탐지: {pat}")
                                    break

                        if remove_btn_sel:
                            remove_loc = cont_loc.locator(remove_btn_sel)
                            if remove_loc.count() > 0:
                                before_remove = cont_loc.evaluate(
                                    "el => el.querySelectorAll(':scope > *').length"
                                )
                                self._log.debug(f"[tag_input] {label!r} → 삭제버튼 클릭 ({remove_btn_sel})")
                                remove_loc.first.evaluate("el => el.click()")
                                self.page.wait_for_timeout(400)
                                after_remove = cont_loc.evaluate(
                                    "el => el.querySelectorAll(':scope > *').length"
                                )
                                if after_remove >= before_remove:
                                    failures.append("태그 삭제 동작 실패")
                                else:
                                    checks.append("태그 삭제 동작 확인")
                            else:
                                checks.append("삭제 버튼 없음 (삭제 테스트 생략)")
                        else:
                            checks.append("삭제 버튼 미탐지 (삭제 테스트 생략)")

                status, detail = self._status_detail(failures, checks)
                self._log.debug(f"[tag_input] {label!r} → {status}: {detail}")
                report.results.append(ScanResult(
                    pattern="tag_input",
                    selector=inp_sel,
                    label=label,
                    status=status,
                    detail=detail,
                    extra={"tag_id": tag_id},
                    order=order,
                ))

            except Exception:
                self._append_error(report, "tag_input", inp_sel, label, order)

        # required_toggle 원래 상태로 복원
        for req_sel, was_checked in _toggle_restore.items():
            try:
                req_loc = self.page.locator(req_sel)
                if req_loc.count() > 0 and req_loc.is_checked() != was_checked:
                    self._log.debug(
                        f"[tag_input] required_toggle 복원: {req_sel} → {'ON' if was_checked else 'OFF'}"
                    )
                    req_loc.evaluate("el => el.click()")
                    self.page.wait_for_timeout(200)
            except Exception:
                self._log.debug(
                    f"[tag_input] required_toggle 복원 실패 ({req_sel}):\n{traceback.format_exc()}"
                )

    # ── 필수 입력 제출 검증 ───────────────────────────────────────────────────

    _ORDER_REQUIRED_SUBMIT = 9999  # required_submit 항목은 항상 출력 맨 마지막

    def _scan_required_submit(self, hints: dict, report: PageScanReport) -> None:
        """
        필수 입력 미입력 시 제출 검증.

        ADD 모달 + required_submit_sequence 정의 → 단계별 순서 검증
        ADD 모달 + 시퀀스 없음              → 빈 폼 단순 검증 (폴백)
        EDIT 모달 (submit_modify)           → 필수 필드 비움 → 수정 시도 → 경고 확인 → 복원

        주의: 호출 전 모달이 열려 있어야 하며, 호출 후 모달은 그대로 유지.
        """
        actions    = hints.get("modal_actions") or {}
        add_sel    = actions.get("submit_add", "")
        modify_sel = actions.get("submit_modify", "")

        # ng-show 방식: DOM에 두 버튼 모두 존재할 수 있음 → is_visible()로 ADD/EDIT 구분
        is_add  = bool(add_sel    and self.page.locator(add_sel).is_visible())
        is_edit = bool(modify_sel and self.page.locator(modify_sel).is_visible()) and not is_add

        if not is_add and not is_edit:
            report.results.append(ScanResult(
                pattern="required_submit",
                selector=add_sel or modify_sel or "(none)",
                label="필수 필드 미입력 제출 검증",
                status="skip",
                detail="submit 버튼 없음",
                order=self._ORDER_REQUIRED_SUBMIT,
            ))
            return

        # 첫 번째 탭으로 이동 (필수 입력 필드 있는 탭)
        tabs = hints.get("modal_tabs", [])
        if tabs:
            self._activate_tab(tabs[0])

        if is_add and hints.get("required_submit_sequence"):
            self._run_submit_sequence(hints, report, add_sel)
        elif is_add:
            self._run_submit_simple(hints, report, add_sel, mode="등록")
        else:
            self._run_submit_edit(hints, report, modify_sel)

    def _run_submit_sequence(
        self, hints: dict, report: PageScanReport, submit_sel: str
    ) -> None:
        """
        required_submit_sequence YAML 기반 단계별 필수 입력 검증 (ADD 모달 전용).

        각 step에서 fill 필드를 누적으로 채우고 submit 클릭 → 경고 메시지 일치 검증.
        expected: "success" 인 마지막 step은 실행 생략 (실제 저장은 close_fn 담당).
        """
        sequence = hints.get("required_submit_sequence", [])
        main_modal_sel = hints.get("modal_id", "addItemModal")

        # 필드 조회용 인덱스 {id_or_selector_key → hint_dict}
        text_idx = {
            ti["selector"].replace("input#", ""): ti
            for ti in hints.get("text_inputs", [])
        }
        tag_idx = {ti["id"]: ti for ti in hints.get("tag_input", [])}

        filled: set[str] = set()

        for step_def in sequence:
            step_n   = step_def.get("step", "?")
            desc     = step_def.get("description", "")
            fill_ids = step_def.get("fill", [])
            exp_msg  = step_def.get("expected_msg", "")
            expected = step_def.get("expected", "")
            label    = f"필수 입력 Step {step_n} ({desc})"

            # expected: "success" → 실행 생략, 확인 완료 기록만
            if expected == "success":
                report.results.append(ScanResult(
                    pattern="required_submit",
                    selector=submit_sel,
                    label=label,
                    status="pass",
                    detail=f"필수 필드 확인 완료: {fill_ids} → 저장 성공 (close_fn 담당)",
                    order=self._ORDER_REQUIRED_SUBMIT,
                ))
                continue

            # 누적 필드 채우기
            for fid in fill_ids:
                if fid in filled:
                    continue
                try:
                    if fid in text_idx:
                        ti  = text_idx[fid]
                        loc = self.page.locator(ti["selector"])
                        if loc.count() > 0:
                            loc.fill(ti.get("test_value", "[AUTO]_seq"))
                            self.page.wait_for_timeout(150)
                            filled.add(fid)
                    elif fid in tag_idx:
                        ti      = tag_idx[fid]
                        inp_loc = self.page.locator(ti["input"])
                        btn_loc = self.page.locator(ti["add_btn"])
                        if inp_loc.count() > 0 and btn_loc.count() > 0:
                            inp_loc.fill(ti.get("test_value", "scan_test"))
                            self.page.wait_for_timeout(200)
                            btn_loc.first.evaluate("el => el.click()")
                            self.page.wait_for_timeout(400)
                            filled.add(fid)
                except Exception:
                    self._log.debug(
                        f"[req_seq] 필드 채우기 실패: {fid}\n{traceback.format_exc()}"
                    )

            # submit 클릭 → 경고 메시지 검증
            try:
                self.page.locator(submit_sel).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(600)

                warn = self.page.locator(self._SEL_WARN_MODAL)
                actual_msg = ""
                if warn.count() > 0:
                    body = warn.locator(".modal-body")
                    actual_msg = body.inner_text().strip() if body.count() > 0 else ""
                    self._dismiss_warning_dialog()

                if not actual_msg:
                    main_open = self.page.locator(f"#{main_modal_sel}.in").count() > 0
                    status = "fail"
                    detail = "경고 없이 제출됨 " + ("(모달 유지)" if main_open else "(모달 닫힘)")
                elif exp_msg and actual_msg != exp_msg:
                    status = "fail"
                    detail = f"메시지 불일치 — 실제: '{actual_msg}' / 기대: '{exp_msg}'"
                else:
                    status = "pass"
                    detail = f"경고: '{actual_msg}'"

                report.results.append(ScanResult(
                    pattern="required_submit",
                    selector=submit_sel,
                    label=label,
                    status=status,
                    detail=detail,
                    order=self._ORDER_REQUIRED_SUBMIT,
                ))

            except Exception:
                self._append_error(
                    report, "required_submit", submit_sel, label, self._ORDER_REQUIRED_SUBMIT,
                )

    def _run_submit_simple(
        self, hints: dict, report: PageScanReport, submit_sel: str, mode: str
    ) -> None:
        """ADD 모달 단순 검증 — 빈 폼으로 submit 클릭 후 경고 여부 확인 (시퀀스 미정의 폴백)."""
        main_modal_sel = hints.get("modal_id", "addItemModal")
        try:
            self.page.locator(submit_sel).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(600)
            warning_appeared = self._dismiss_warning_dialog()
            main_still_open  = self.page.locator(f"#{main_modal_sel}.in").count() > 0

            if not main_still_open:
                status, detail = "fail", f"빈 채로 {mode} 시 경고 없이 모달이 닫힘"
            elif warning_appeared:
                status, detail = "pass", f"빈 채로 {mode} 시 경고 모달 정상 출력"
            else:
                status, detail = "pass", f"빈 채로 {mode} 시 모달 닫히지 않음 (필드 검증 동작)"

            report.results.append(ScanResult(
                pattern="required_submit", selector=submit_sel,
                label=f"필수 필드 미입력 {mode} 검증",
                status=status, detail=detail, order=self._ORDER_REQUIRED_SUBMIT,
            ))
        except Exception:
            self._append_error(
                report, "required_submit", submit_sel,
                f"필수 필드 미입력 {mode} 검증", self._ORDER_REQUIRED_SUBMIT,
            )

    def _run_submit_edit(
        self, hints: dict, report: PageScanReport, submit_sel: str
    ) -> None:
        """EDIT 모달 검증 — 필수 text_input 비움 → 수정 시도 → 경고 확인 → 값 복원."""
        main_modal_sel     = hints.get("modal_id", "addItemModal")
        required_input_sel = ""
        original_value     = ""

        for ti in hints.get("text_inputs", []):
            if ti.get("required") and self.page.locator(ti["selector"]).count() > 0:
                required_input_sel = ti["selector"]
                break

        if required_input_sel:
            req_loc        = self.page.locator(required_input_sel)
            original_value = req_loc.input_value()
            req_loc.fill("")
            self.page.wait_for_timeout(200)

        try:
            self.page.locator(submit_sel).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(600)
            warning_appeared = self._dismiss_warning_dialog()
            main_still_open  = self.page.locator(f"#{main_modal_sel}.in").count() > 0

            if not main_still_open:
                status, detail = "fail", "필수 필드 비운 채 수정 시 경고 없이 모달이 닫힘"
            elif warning_appeared:
                status, detail = "pass", "필수 필드 비운 채 수정 시 경고 모달 정상 출력"
            else:
                status, detail = "pass", "필수 필드 비운 채 수정 시 모달 닫히지 않음 (필드 검증 동작)"

            report.results.append(ScanResult(
                pattern="required_submit", selector=submit_sel,
                label="필수 필드 미입력 수정 검증",
                status=status, detail=detail, order=self._ORDER_REQUIRED_SUBMIT,
            ))
        except Exception:
            self._append_error(
                report, "required_submit", submit_sel,
                "필수 필드 미입력 수정 검증", self._ORDER_REQUIRED_SUBMIT,
            )
        finally:
            if required_input_sel:
                try:
                    loc = self.page.locator(required_input_sel)
                    if loc.count() > 0:
                        loc.fill(original_value)
                except Exception:
                    self._log.debug(
                        f"[required_submit] EDIT 복원 실패:\n{traceback.format_exc()}"
                    )

    # ── 자동 탐지 종속 필드 매핑 ──────────────────────────────────────────────

    def _find_dependent_fields(self, toggle_locator) -> list[str]:
        """
        toggle과 같은 컨테이너(tr / section / .form-group) 내에서
        disabled / ng-disabled 속성을 가진 input의 id 목록을 반환한다.

        YAML 없는 새 페이지 자동 탐지 시 활용.
        """
        try:
            result = toggle_locator.evaluate("""el => {
                const ancestors = ['tr', 'section', '.form-group', '.option-wrap', '.control-group'];
                let ancestor = null;
                for (const sel of ancestors) {
                    ancestor = el.closest(sel);
                    if (ancestor) break;
                }
                if (!ancestor) {
                    ancestor = el.parentElement && el.parentElement.parentElement;
                }
                if (!ancestor) return [];
                return Array.from(
                    ancestor.querySelectorAll(
                        'input[disabled], input[ng-disabled], textarea[disabled]'
                    )
                )
                .filter(inp => inp !== el)
                .map(inp => inp.id || inp.getAttribute('ng-model') || inp.name || '');
            }""")
            return [r for r in (result or []) if r]
        except Exception:
            return []

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    def _is_known_bug(self, selector: str, test_name: str) -> bool:
        """
        selector + test_name 조합이 known_bugs.yaml에 등록되어 있는지 확인한다.
        등록된 경우 해당 항목의 검증을 건너뛰고 known_bug로 마킹한다.
        """
        return any(
            bug.get("selector") == selector and bug.get("test_name") == test_name
            for bug in self._known_bugs
        )

    @staticmethod
    def _load_yaml(path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return None
