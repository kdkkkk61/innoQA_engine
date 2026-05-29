"""
core/ui_scanner.py — 통합 UI 스캐너 (오케스트레이터)

스캔 전략:
  scan_hints yaml 존재 → yaml 구동 검증 (confidence 1.0)
  scan_hints yaml 없음 → 자동 탐지 폴백 (새 페이지 첫 투입 시)

탭 복원 원칙 (readonly):
  스캔 전 현재 활성 탭을 기억하고, 스캔 완료 후 반드시 복원한다.

설계 원칙:
  - ScanResult는 selector 문자열 보관 (Playwright Locator 미보관)
  - 스캐너는 토글 ON/OFF 동작 검증 외에는 페이지 상태를 변경하지 않는다
  - known_bug 항목은 fail 카운트에서 제외 (PageScanReport.failed 미포함)
  - 검증 로직은 validators/ 파일에 위임 (ScanContext 경유)

파일 구조:
  core/models.py        → ScanResult, PageScanReport 데이터 클래스
  core/scan_context.py  → ScanContext (page + log + 공용 헬퍼)
  validators/           → 패턴별 검증 함수 (scan_toggle_checkboxes 등)
  core/ui_scanner.py    → UIScanner (스캔 오케스트레이터 + 자동 탐지 폴백)
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Callable, Optional

from playwright.sync_api import Page
from utils.scan_logger import make_scan_logger

# ── 모델 re-export (하위 호환 — test_ui_scan.py에서 직접 import 가능)
from core.models import ScanResult, PageScanReport  # noqa: F401
from core.scan_context import ScanContext

# ── validators import
from validators.initial_state   import scan_initial_state, scan_loaded_values
from validators.toggle_checkbox import scan_toggle_checkboxes
from validators.plain_checkbox  import scan_plain_checkboxes
from validators.radio_group     import scan_radio_groups
from validators.text_input      import scan_text_inputs
from validators.tag_input       import scan_tag_inputs
from validators.required_submit import scan_required_submit
from validators.button_action   import scan_button_actions


# ── B-1-A: 신규 요소 1차 자동 검증 (DOM 속성 점검만, 동작 X) ─────────────────

def _format_auto_check(attrs: dict) -> str:
    """
    DOM 속성 정보를 1차 자동 검증 결과로 포맷.

    안전 기준 (B-1-A):
      - 읽기 전용 — 클릭/입력 같은 동작 X.
      - DOM 속성 점검 결과를 사람이 읽을 수 있는 형식으로 출력.
      - 동작 검증은 yaml 등록 후 정식 시나리오에서 진행.

    추출 정보 (extract_dom_attributes 의 키):
      type, maxlength, checked, disabled, readonly, has_toggle, placeholder
    """
    if not attrs:
        return "타입: (DOM에서 정보 추출 실패)"

    t = attrs.get("type", "?")
    parts = [f"타입: {t}"]
    if attrs.get("has_toggle"):
        parts.append("toggle 속성 있음")
    if t in ("text", "textarea", "number", "password", "email"):
        ml = attrs.get("maxlength")
        parts.append(
            f"maxlength={ml} (속성 명시)" if ml is not None
            else "maxlength 속성 없음 (서버 측 제한 yaml 등록 후 검증 권장)"
        )
        ph = attrs.get("placeholder", "")
        if ph:
            parts.append(f"placeholder={ph!r}")
    elif t in ("checkbox", "radio"):
        parts.append(f"초기 상태: {'checked' if attrs.get('checked') else 'unchecked'}")
        if attrs.get("disabled"):
            parts.append("현재 disabled — 종속 관계 가능성 (yaml 등록 시 점검)")
    if attrs.get("readonly"):
        parts.append("readonly")

    body = " / ".join(parts)
    return f"자동 검증 (DOM 속성 점검):\n  {body}"


def _run_heuristic_test(page, selector: str, attrs: dict, label: str) -> tuple[str, str]:
    """B-1-C step 2 (2026-05-29) — 신규 발견 요소의 type 별 안전 휴리스틱 동작 검증.

    원칙:
      - 읽기 + 단순 click 토글까지만. 저장 / 데이터 변경 / 종속 자동 탐색 X.
      - 1 type 당 1 검증. 결과는 신규 발견 카드 detail 안 한 줄로 합침 (별도 카드 X).
      - 부작용 의심 시 'warn'. 명확한 정상 동작 시 'pass'. 실패/예외 시 'warn'.

    Returns:
      (status, line) — status: "pass"/"warn"/"skip" / line: 한 줄 텍스트.

    사용자 결정 (2026-05-29): 휴리스틱 자동 검증 방향 — testable_aspects 가이드 대신 즉시
    자동 검증 결과 카드 표시.
    """
    t = attrs.get("type", "")

    if t in ("text", "password", "email", "url", "tel", "textarea"):
        # 클라 길이 가드 부재 검출 (sc3n 패턴과 동일 신호)
        ml = attrs.get("maxlength")
        if ml is None:
            return ("warn",
                    "휴리스틱: 클라 길이 가드 부재 (maxlength=null) — 긴 입력 시 서버 generic error 위험")
        return ("pass", f"휴리스틱: maxlength={ml} (클라 가드 있음)")

    if t == "checkbox":
        # click 토글 가능 여부 — 데이터 변경 없음 (원상복구)
        try:
            loc = page.locator(selector).first
            before = loc.is_checked()
            loc.evaluate("el => el.click()")
            page.wait_for_timeout(200)
            after = loc.is_checked()
            # 원상복구
            loc.evaluate("el => el.click()")
            page.wait_for_timeout(200)
            if before == after:
                return ("warn",
                        f"휴리스틱: checkbox click 후 상태 미변화 ({before}→{after}) — disabled? 또는 종속 차단?")
            return ("pass",
                    f"휴리스틱: checkbox click 토글 정상 (초기 {before} → click {after} → 복구)")
        except Exception as e:
            return ("warn", f"휴리스틱: checkbox click 시도 실패 — {e!r}")

    if t == "radio":
        # name 그룹 옵션 수 검출 (selector 로부터 name 속성 읽기)
        try:
            name = page.locator(selector).first.get_attribute("name") or ""
            if name:
                cnt = page.locator(f'input[type="radio"][name="{name}"]').count()
                return ("warn",
                        f"휴리스틱: radio name='{name}' 그룹 {cnt}개 옵션 발견 — yaml options[] 수동 명세 권장")
        except Exception:
            pass
        return ("skip", "휴리스틱: radio name 추출 실패 — 수동 점검 필요")

    return ("skip", f"휴리스틱: type={t!r} — 자동 검증 패턴 미정의 (수동 점검)")


def _build_yaml_stub(selector: str, label: str, attrs: dict) -> str:
    """신규 발견 요소의 yaml stub 한 줄 생성 — 검수자 복붙 용도 (B-1-C step 1).

    사용 흐름:
      1. sc0 신규 기능 감지 카드 → stub 한 줄 출력
      2. 검수자가 yaml 의 적절한 section 에 복붙
      3. 다음 run 부터 UIScanner 가 yaml 명세 따라 자동 검증 시작
    """
    t = attrs.get("type", "")
    # selector 에서 id 부분만 추출 — "input#foo" / "textarea#foo" / "#foo" → "foo"
    pure_id = selector
    for prefix in ("input#", "textarea#", "select#", "button#", "#"):
        if pure_id.startswith(prefix):
            pure_id = pure_id[len(prefix):]
            break
    label_esc = (label or "").replace('"', '\\"')

    if t in ("text", "password", "email", "url", "tel"):
        ml = attrs.get("maxlength")
        ml_part = f", maxlength: {ml}" if ml is not None else ", maxlength: null  # ← 가드 부재"
        return f'- {{id: "{pure_id}", type: "text", label: "{label_esc}"{ml_part}}}'
    if t == "textarea":
        return f'- {{id: "{pure_id}", type: "textarea", label: "{label_esc}"}}'
    if t == "checkbox":
        if attrs.get("has_toggle"):
            return f'- {{id: "{pure_id}", type: "toggle_checkbox", label: "{label_esc}", dependent_controls: []  # ← 종속 명세 채우기}}'
        return f'- {{id: "{pure_id}", type: "checkbox", label: "{label_esc}", default: {bool(attrs.get("checked"))}}}'
    if t == "radio":
        return f'# radio "{pure_id}" — name 기반 그룹화 필요. options[] 수동 작성 권장.'
    if t in ("button", "submit"):
        return f'- {{id: "{pure_id}", type: "button", label: "{label_esc}"}}'
    return f'# 자동 추정 실패 — selector: {selector}, type: {t!r}'


class UIScanner:
    """
    scan_hints yaml + known_bugs yaml을 기반으로 페이지 UI를 검사한다.
    yaml이 없으면 HTML 속성 기반 자동 탐지로 폴백한다.

    사용법:
        scanner = UIScanner(page, config_dir="config")
        report  = scanner.scan("ransom_detect_policy", modal_open_fn=open_fn)
    """

    # 자동 탐지 폴백 전용 상수
    _ATTR_TOGGLE_SEL = 'input[type="checkbox"][toggle]'
    _ATTR_TEXT_INPUT = (
        'input[type="text"]:not([toggle]), '
        'input:not([type]):not([toggle]):not([hidden])'
    )
    _ATTR_NUMBER   = 'input[type="number"]'
    _SEL_TAB_LINKS = "ul#modalTabLayer li a"
    _TAB_SETTLE_MS = 300

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
        modal_open_fn:   Optional[Callable] = None,
        modal_close_fn:  Optional[Callable] = None,
        phase: int = 0,
        context_extra:   Optional[dict] = None,
    ) -> PageScanReport:
        """
        page_id에 해당하는 scan_hints를 로드하고 해당 phase의 패턴을 검사한다.

        Args:
            page_id:        config/scan_hints/{page_id}.yaml 식별자
            modal_open_fn:  모달을 열어주는 callable. None이면 현재 DOM 상태 스캔.
            modal_close_fn: 모달을 닫아주는 callable.
                            None이면 hints의 modal_actions.close 버튼을 시도한다.
            phase:          스캔 단계.
                            0 = 전체 (하위 호환, 기본값)
                            1 = Phase 1: 초기값 스냅샷 + 필수입력 검증 (ADD 모달)
                            2 = Phase 2: UI 요소 동작 검증 (ADD 모달)
                            3 = Phase 3: 수정 시나리오 검증 (EDIT 모달)
        """
        hints_path = self._config_dir / "scan_hints" / f"{page_id}.yaml"
        hints      = self._load_yaml(hints_path)
        report     = PageScanReport(page_id=page_id)
        ctx        = ScanContext(
            page=self.page,
            log=self._log,
            known_bugs=self._known_bugs,
            extra=context_extra or {},
            phase=phase,
        )

        # Phase 4 (수정 시나리오) 한정 — 4-3 위반 결과 확인용 재오픈 콜백 노출.
        # validators/required_submit.py:_run_submit_edit 가 1차 검증 후
        # 모달 재오픈 → 실제 저장값 확인에 사용 (시나리오 4-3, scenario_4_modify.md 참조).
        if phase == 4 and modal_open_fn:
            ctx.extra.setdefault("reopen_edit_fn", modal_open_fn)

        # 모달 열기
        modal_opened = False
        if modal_open_fn:
            try:
                modal_open_fn()
                modal_opened = True
            except Exception:
                trigger_sel = (hints or {}).get("modal_trigger", {}).get("add", "")
                ctx.append_error(report, "modal_open", trigger_sel, "모달 열기")
                return report

        before_count = len(report.results)
        if hints:
            self._scan_from_hints(ctx, hints, report, phase=phase)
            # 시나리오 1 — DOM 스캔 + yaml 비교 (회귀 본질, scenario_1_ui.md 참조)
            # phase 2: ADD 모달 — 시나리오 1 카드 + 시나리오 2 자동 검증
            # phase 4: EDIT 모달 — 시나리오 4-1 자동 검증 (저장값 로드)
            if modal_opened and phase in (0, 2, 4):
                self._scan_diff_yaml_dom(ctx, hints, report)
        else:
            print(f"[UIScanner] scan_hints 없음 — 자동 탐지 폴백: {hints_path}")
            self._scan_auto_fallback(report)

        # phase != 0 이면 새로 추가된 결과에 phase 번호 스탬프
        if phase != 0:
            for r in report.results[before_count:]:
                if r.phase == 0:
                    r.phase = phase

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

    def _scan_from_hints(
        self, ctx: ScanContext, hints: dict, report: PageScanReport,
        phase: int = 0,
    ) -> None:
        """
        scan_hints yaml에 정의된 패턴을 phase에 따라 검증한다.
        각 패턴 검증은 validators/ 모듈에 위임한다.

        Phase 정의:
          0 = 전체 (하위 호환): Phase 1 + Phase 2 순서로 실행
          1 = 초기값 스냅샷(터치 전) + 필수입력 검증 (ADD 모달 1회차)
          2 = UI 요소 동작 검증: 라디오, 체크박스, 텍스트, 태그 (ADD 모달 2회차)
          3 = 수정 시나리오: 필수입력 검증 (EDIT 모달)

        탭 복원 원칙 (readonly):
          스캔 시작 전 첫 번째 탭을 기억하고, 스캔 완료 후 반드시 복원한다.
        """
        tabs         = hints.get("modal_tabs", [])
        original_tab = tabs[0] if tabs else None

        report.tab_sections = sorted(
            [
                {"label": t.get("label", ""), "start_order": t["start_order"]}
                for t in tabs
                if "start_order" in t
            ],
            key=lambda t: t["start_order"],
        )

        if original_tab:
            ctx.activate_tab(original_tab)

        # 시나리오 번호 기준 (CLAUDE.md 시나리오 표준)
        # 2 = 입력 구조 (초기값 + 필수입력)
        # 3 = 동작 검증 (UI 인터랙션 + 중복 처리)
        # 4 = 수정 시나리오 (저장값 로드 + 재확인)
        run_initial       = phase in (0, 2)        # 초기값 스냅샷 (터치 전, ADD만)
        run_verify_loaded = phase == 4             # EDIT 모달 저장값 로드 확인
        run_ui            = phase in (0, 3, 4)     # UI 요소 동작 검증 (ADD + EDIT)
        run_submit        = phase in (0, 2, 3, 4)  # 필수입력 검증 — 전 시나리오 실행

        # validator별 timing 측정 (어느 검증이 hot spot인지 식별)
        import time as _time
        def _run(name, fn):
            t0 = _time.time()
            pre_count = len(report.results)
            try:
                fn(ctx, hints, report)
            finally:
                added = len(report.results) - pre_count
                print(f"[TIMING]   {name} took {_time.time()-t0:.2f}s (cards={added})")

        if run_initial:
            _run("scan_initial_state", scan_initial_state)

        if run_verify_loaded:
            _run("scan_loaded_values", scan_loaded_values)

        if run_ui:
            _run("scan_toggle_checkboxes", scan_toggle_checkboxes)
            _run("scan_plain_checkboxes",  scan_plain_checkboxes)
            _run("scan_radio_groups",      scan_radio_groups)
            _run("scan_text_inputs",       scan_text_inputs)
            _run("scan_tag_inputs",        scan_tag_inputs)
            _run("scan_button_actions",    scan_button_actions)

        if run_submit:
            _run("scan_required_submit", scan_required_submit)

        # 원래 탭으로 복원 (readonly 원칙)
        if original_tab:
            ctx.activate_tab(original_tab)

    # ── 시나리오 1: DOM 스캔 + yaml 비교 (회귀 본질) ──────────────────────────

    def _scan_diff_yaml_dom(
        self,
        ctx:    ScanContext,
        hints:  dict,
        report: PageScanReport,
    ) -> None:
        """
        yaml 정의 셀렉터 set과 모달 DOM의 실제 요소 set을 비교한다.

        - DOM에만 존재     → 🆕 신규 요소 (pattern: discovered_new, status: warn)
        - yaml에만 존재    → ❌ 제거 요소 (pattern: discovered_missing, status: warn)
        - 둘 다 존재       → 정상 (다른 시나리오에서 검증됨)

        설계 근거:
          - docs/scenario_1_ui.md "DOM 스캔 + yaml 비교"
          - docs/scan-output-format.md "신규 pattern 정렬 규칙"

        order=9 — 시나리오 1 영역 가장 앞 (검수자가 보고서에서 즉시 인지).
        extra["scenario"]=1 명시 (다른 phase에서 호출돼도 시나리오 1 영역 출력).
        """
        from core.scan_diff import (
            extract_yaml_selectors, extract_dom_selectors, compare,
            extract_yaml_labels, extract_dom_labels, extract_dom_attributes,
        )

        # 모달 컨텍스트 셀렉터 결정 (Bootstrap modal 열림 = .in)
        modal_id = hints.get("modal_id") or ""
        if not modal_id:
            return  # 컨텍스트 미정 → 비교 불가, 조용히 스킵
        context_sel = f"#{modal_id}.in"

        try:
            yaml_set = extract_yaml_selectors(hints)
            dom_set  = extract_dom_selectors(self.page, context_sel)
            diff     = compare(yaml_set, dom_set)
            # 라벨 + 속성 추출 — 신규 요소의 의미 파악 + B-1-A 자동 검증용
            new_labels     = extract_dom_labels(self.page, context_sel, diff["new"])
            new_attrs      = extract_dom_attributes(self.page, context_sel, diff["new"])
            yaml_label_map = extract_yaml_labels(hints)
        except Exception:
            ctx.append_error(
                report, "discovered_new", context_sel,
                "DOM ↔ yaml 비교 실패", order=9, phase=1,
            )
            return

        # 신규/제거 발견되면 모달 element 통째 캡처 (스크롤 영역 포함).
        # viewport 만 찍으면 길어진 모달의 위쪽만 보임 → 신규 요소가 스크롤 아래면 의미 X.
        # element_sel 사용해서 모달 전체 캡처 — 검수자가 신규 요소 위치까지 확인 가능.
        shared_ss = None
        if diff["new"] or diff["missing"]:
            try:
                shared_ss = ctx.take_screenshot(
                    "scan_diff_modal", element_sel=context_sel
                )
            except Exception:
                pass

        # 시나리오 1 카드 (신규/제거 발견) — phase 0/2 만 등록.
        # phase 4 (EDIT 모달) 에서는 같은 신규 요소가 또 발견되니 중복 방지.
        register_discovery_cards = ctx.phase in (0, 2)

        # 신규 기능 (DOM에만 존재) — DOM에서 한국어 라벨 + 속성 추출
        for sel in sorted(diff["new"]):
            ko    = (new_labels.get(sel) or "").strip()
            attrs = new_attrs.get(sel) or {}
            if not register_discovery_cards:
                continue  # phase 4: 시나리오 1 카드 등록 X (시나리오 4 카드만)
            # 라벨에 type 명시 — "[checkbox] '전체 선택' (input#listHeaderCheckBox)"
            # 사용자 요구 (2026-05-29): "기능명 + 어떤 UI 요소 이런 식으로 표현이 맞아"
            t_disp = (attrs.get("type") or "?")
            if t_disp == "checkbox" and attrs.get("has_toggle"):
                t_disp = "toggle"
            ko_disp = f' "{ko}"' if ko else " (라벨 미추출)"
            label_text = f"신규 기능 감지 — [{t_disp}]{ko_disp} ({sel})"
            # B-1-A 자동 검증 — 읽기 전용 (DOM 속성 점검만, 동작 검증 X)
            auto_check = _format_auto_check(attrs)
            # B-1-C step 1 (2026-05-29) — yaml stub 자동 제안 (휴리스틱 동작 검증의 전 단계).
            # 검수자가 보고서에서 stub 라인 복붙 → yaml 명세 추가 → 다음 run 부터 동일 type
            # 다른 요소와 똑같이 자동 검증 시작 (B-1 시리즈의 list_page 확장).
            yaml_stub = _build_yaml_stub(sel, ko, attrs)
            # B-1-C step 2 (2026-05-29) — type 별 안전 휴리스틱 자동 검증.
            # 사용자 결정: 자동 결과 카드 표시 (testable_aspects 가이드 방향 제외).
            try:
                heur_status, heur_line = _run_heuristic_test(self.page, sel, attrs, ko)
            except Exception as e:
                heur_status, heur_line = "skip", f"휴리스틱: 예외 — {e!r}"

            # extra에 자동 분류 정보 저장 — qa_runner phase 3 자동 채우기에 사용
            extra_data = {
                "scenario":     1,
                "scenario_tag": "시나리오 1",
                "auto_type":    attrs.get("type", ""),
                "auto_label":   ko,
                "auto_maxlength": attrs.get("maxlength"),
                "yaml_stub":    yaml_stub,
                "heuristic_status": heur_status,
                "heuristic_line":   heur_line,
            }
            if shared_ss:
                extra_data["screenshot"] = shared_ss
            report.results.append(ScanResult(
                pattern="discovered_new", selector=sel,
                label=label_text,
                status="warn",
                detail=(
                    "DOM에 존재 / yaml 미정의\n"
                    f"{auto_check}\n"
                    f"{heur_line}\n"
                    f"yaml stub 추천 (복붙 후 다음 run 부터 자동 검증):\n  {yaml_stub}\n"
                    "검수자 조치: stub 검토 후 yaml 적절한 section 에 추가 → 의도된 추가면 정식 검증 시작 / 임시 요소면 무시"
                ),
                order=9, phase=1,
                extra=extra_data,
            ))

        # 제거된 기능 (yaml에만 존재) — phase 0/2 만 등록 (phase 4 중복 방지)
        for sel in sorted(diff["missing"]):
            if not register_discovery_cards:
                continue
            ko = (yaml_label_map.get(sel) or "").strip()
            label_text = (
                f'제거된 기능 감지 — "{ko}" ({sel})' if ko
                else f"제거된 기능 감지 — {sel}"
            )
            extra_data = {"scenario": 1, "scenario_tag": "시나리오 1"}
            if shared_ss:
                extra_data["screenshot"] = shared_ss
            report.results.append(ScanResult(
                pattern="discovered_missing", selector=sel,
                label=label_text,
                status="warn",
                detail=(
                    "yaml 정의 / DOM 미발견\n"
                    "검수자 조치: 의도된 제거면 yaml 정리, 회귀(의도치 않음)면 제품팀 보고"
                ),
                order=9, phase=1,
                extra=extra_data,
            ))

        # ── B-1-B-1: 신규 요소 자동 분류 → 시나리오 2 자동 동작 검증 ─────────
        # 비전 B 핵심 — yaml 등록 없이도 신규 요소가 시나리오 2 검증을 받도록.
        # 임시 hints 확장 후 기존 validators 재호출. 결과는 시나리오 2 영역 카드.
        if diff["new"]:
            try:
                from core.scan_diff import (
                    expand_hints_with_discovered,
                    detect_tag_input_patterns,
                )
                # text 타입 input 후보에 한해 tag_input 패턴 사전 탐지 — text 가 아닌 타입은
                # tag_input 일 수 없음. attrs 에서 type 으로 필터.
                text_inputs_candidate = [
                    s for s in diff["new"]
                    if (new_attrs.get(s) or {}).get("type") in (
                        "text", "textarea", "number", "password", "email"
                    )
                ]
                tag_patterns = detect_tag_input_patterns(
                    self.page, context_sel, text_inputs_candidate
                ) if text_inputs_candidate else {}
                temp_hints = expand_hints_with_discovered(
                    diff["new"], new_attrs, new_labels, tag_patterns,
                )
                # 임시 hints에 모달 컨텍스트 정보도 복사 (validator 일부가 사용)
                temp_hints["modal_id"]      = hints.get("modal_id", "")
                temp_hints["modal_actions"] = hints.get("modal_actions", {})

                # 자동 분류된 항목이 있을 때만 validator 재호출
                # 라디오는 자동 분류 X — 그룹·종속 구조 복잡해 yaml 등록 의무.
                # 시나리오 1 의 discovered_new 카드로 신규 표시만 (사용자 결정 2026-05-11).
                has_auto = (
                    temp_hints.get("text_inputs") or
                    temp_hints.get("toggle_checkboxes") or
                    temp_hints.get("plain_checkboxes") or
                    temp_hints.get("tag_input")
                )
                if has_auto:
                    # 호출 전 결과 카운트 (자동 분류분만 식별 위해)
                    pre_count = len(report.results)

                    if ctx.phase in (0, 2):
                        # 시나리오 2 영역 검증 — 입력 필드 동작
                        if temp_hints.get("text_inputs"):
                            scan_text_inputs(ctx, temp_hints, report)
                        if temp_hints.get("toggle_checkboxes"):
                            scan_toggle_checkboxes(ctx, temp_hints, report)
                        if temp_hints.get("plain_checkboxes"):
                            scan_plain_checkboxes(ctx, temp_hints, report)
                        if temp_hints.get("tag_input"):
                            scan_tag_inputs(ctx, temp_hints, report)
                        target_scenario = 2
                    elif ctx.phase == 4:
                        # 시나리오 4-1 영역 검증 — 저장값 로드 확인
                        # 신규 필드 expected = 현재 DOM 값 (default 유지 = pass)
                        # ⚠ ctx.extra 의 기존 verify_values/toggles 는 첫 scan_loaded_values
                        #   호출에서 이미 검증됨 → 중복 카드 방지 위해 신규 셀렉터만 전달.
                        extra_verify  = {}
                        extra_toggles = {}
                        for sel in diff["new"]:
                            a = new_attrs.get(sel) or {}
                            t = a.get("type", "")
                            try:
                                loc = self.page.locator(sel).first
                                if loc.count() == 0:
                                    continue
                                if t in ("text", "textarea", "number", "password", "email"):
                                    extra_verify[sel] = loc.input_value()
                                elif t in ("checkbox", "radio"):
                                    extra_toggles[sel] = loc.is_checked()
                            except Exception:
                                pass
                        # ctx.extra 를 신규 항목으로만 임시 교체 — 중복 검증 방지
                        old_vv = ctx.extra.get("verify_values", {})
                        old_vt = ctx.extra.get("verify_toggles", {})
                        ctx.extra["verify_values"]  = extra_verify
                        ctx.extra["verify_toggles"] = extra_toggles
                        try:
                            scan_loaded_values(ctx, temp_hints, report)
                        finally:
                            ctx.extra["verify_values"]  = old_vv
                            ctx.extra["verify_toggles"] = old_vt
                        target_scenario = 4
                    else:
                        target_scenario = 0  # 그 외 phase — 태깅만

                    # 자동 분류 결과 표시 — label/detail에 "[신규]" 명시
                    # 검수자가 카드 목록에서 즉시 자동 분류 결과 식별 가능.
                    # CP949 환경 호환 — 이모지/em-dash 대신 한국어 텍스트만.
                    for r in report.results[pre_count:]:
                        r.label  = "[신규] " + r.label
                        r.detail = "[자동 분류 — yaml 미등록] " + r.detail
                        r.extra = {
                            **r.extra,
                            "scenario": target_scenario,
                            "scenario_tag": f"시나리오 {target_scenario}",
                        }
            except Exception:
                ctx.append_error(
                    report, "discovered_new", context_sel,
                    "신규 요소 자동 분류/검증 실패", order=9, phase=1,
                )

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
        """HTML 속성 기반 자동 탐지 — 존재 여부만 확인."""
        excluded = exclude or set()
        tab_info = f" (탭: {tab_label})" if tab_label else ""

        # ① toggle 속성 체크박스
        try:
            for cb in self.page.locator(
                f"{context} {self._ATTR_TOGGLE_SEL}"
            ).all():
                cb_id    = cb.get_attribute("id") or ""
                selector = f"input#{cb_id}" if cb_id else self._ATTR_TOGGLE_SEL
                if selector in excluded:
                    continue
                dependent = self._find_dependent_fields(cb)
                report.results.append(ScanResult(
                    pattern="auto_detect", selector=selector,
                    label=f"[자동탐지] 토글 {cb_id}{tab_info}",
                    status="pass", detail="toggle 속성 존재",
                    extra={"type": "toggle", "dependent_fields": dependent},
                ))
        except Exception:
            pass

        # ② text_input
        try:
            for inp in self.page.locator(
                f"{context} {self._ATTR_TEXT_INPUT}"
            ).all():
                inp_id   = inp.get_attribute("id") or ""
                selector = f"input#{inp_id}" if inp_id else 'input[type="text"]'
                if selector in excluded:
                    continue
                maxlen = inp.get_attribute("maxlength")
                report.results.append(ScanResult(
                    pattern="auto_detect", selector=selector,
                    label=f"[자동탐지] text_input {inp_id}{tab_info}",
                    status="pass", detail=f"text input 존재 (maxlength={maxlen})",
                    extra={"type": "text_input", "maxlength": maxlen},
                ))
        except Exception:
            pass

        # ③ number_input
        try:
            for inp in self.page.locator(
                f"{context} {self._ATTR_NUMBER}"
            ).all():
                inp_id   = inp.get_attribute("id") or ""
                selector = f"input#{inp_id}" if inp_id else 'input[type="number"]'
                if selector in excluded:
                    continue
                report.results.append(ScanResult(
                    pattern="auto_detect", selector=selector,
                    label=f"[자동탐지] number_input {inp_id}{tab_info}",
                    status="pass", detail="number input 존재",
                    extra={"type": "number_input"},
                ))
        except Exception:
            pass

    def _get_tabs_auto(self) -> list[tuple[str, str]]:
        """Bootstrap 3 탭 목록 자동 탐지 (YAML 없을 때 사용)."""
        tabs = []
        try:
            for i, tab in enumerate(self.page.locator(self._SEL_TAB_LINKS).all()):
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

    def _find_dependent_fields(self, toggle_locator) -> list[str]:
        """
        toggle과 같은 컨테이너 내에서 disabled / ng-disabled 속성 input 목록 반환.
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

    @staticmethod
    def _load_yaml(path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return None
