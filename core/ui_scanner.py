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
from validators.initial_state   import scan_initial_state
from validators.toggle_checkbox import scan_toggle_checkboxes
from validators.plain_checkbox  import scan_plain_checkboxes
from validators.radio_group     import scan_radio_groups
from validators.text_input      import scan_text_inputs
from validators.tag_input       import scan_tag_inputs
from validators.required_submit import scan_required_submit


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
        modal_open_fn:  Optional[Callable] = None,
        modal_close_fn: Optional[Callable] = None,
        phase: int = 0,
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
        )

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

        run_initial = phase in (0, 1)     # 초기값 스냅샷 (터치 전 필수)
        run_ui      = phase in (0, 2)     # UI 요소 동작 검증
        run_submit  = phase in (0, 1, 3)  # 필수입력 검증 (ADD=1, EDIT=3, 전체=0)

        if run_initial:
            scan_initial_state(ctx, hints, report)

        if run_ui:
            scan_toggle_checkboxes(ctx, hints, report)
            scan_plain_checkboxes(ctx, hints, report)
            scan_radio_groups(ctx, hints, report)
            scan_text_inputs(ctx, hints, report)
            scan_tag_inputs(ctx, hints, report)

        if run_submit:
            scan_required_submit(ctx, hints, report)

        # 원래 탭으로 복원 (readonly 원칙)
        if original_tab:
            ctx.activate_tab(original_tab)

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
