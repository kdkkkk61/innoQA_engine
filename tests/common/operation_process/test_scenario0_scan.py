"""운용 프로세스 — UIScanner 기반 자동 스캔 (sc0, 신설 2026-07-03).

특수폴더 test_scenario0_scan.py 패턴 복제 (기능 삭제 감지 포함).
yaml ↔ 실제 DOM 비교 → 변경사항 3종 감지:
  추가(discovered_new)     = DOM에만 존재 (yaml 미정의 — 신규 기능)
  삭제(discovered_missing) = yaml에만 존재, DOM 미발견 (기능 삭제)
  숨김(discovered_hidden)  = yaml+DOM 둘 다 있으나 display:none (detect_hidden 켠 yaml 만)

운용 프로세스는 ADD 모달(addCommonProcess) 1개 → 스캔 1개(0a).
yaml: config/scan_hints/common_operation_process.yaml — text_inputs 5필드.
"""
import re as _re

from core.ui_scanner import UIScanner
from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase


class TestOperationProcessScenario0Scan(OperationProcessBase):
    """운용 프로세스 — UIScanner 자동 스캔 (시나리오 0)."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _report_scan(self, report, tag: str) -> None:
        """scan 결과 분류 → 카드 (특수폴더/npouch_policy sc0 과 동일 분류)."""
        _DISCOVERY = ("discovered_new", "discovered_missing", "discovered_hidden")
        added   = [r for r in report.results if r.pattern == "discovered_new"]
        deleted = [r for r in report.results if r.pattern == "discovered_missing"]
        hidden  = [r for r in report.results if r.pattern == "discovered_hidden"]
        scan_fails = [r for r in report.results
                      if r.status == "fail" and r.pattern not in _DISCOVERY]
        scan_warns = [r for r in report.results
                      if r.status == "warn" and r.pattern not in _DISCOVERY]
        scan_pass  = [r for r in report.results if r.status == "pass"]

        changed = len(added) + len(deleted) + len(hidden)
        self._add("warn" if changed else "pass",
                  f"{tag} — [UIScanner] 변경사항 감지 (yaml ↔ DOM diff)",
                  f"변경사항: 추가={len(added)}건, 삭제={len(deleted)}건, 숨김={len(hidden)}건 / "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, pass={len(scan_pass)}건",
                  sc=0)
        # 변경사항 카드 개별 노출 (요소별) — 스크린샷 없음: 삭제=요소 없음/숨김=display:none 이라 화면 증거 무의미
        for kind, items in (("추가", added), ("삭제", deleted), ("숨김", hidden)):
            for r in items:
                name = _re.sub(r"^(신규|제거된|숨겨진) 기능 감지 — ", "", r.label or "")
                self._add("warn", f"{tag} — 변경사항({kind}) — {name}",
                          r.detail or "", sc=0, screenshot=False)
        for r in scan_fails + scan_warns:
            self._add(r.status, f"{tag} — [UI 패턴] {r.label}",
                      r.detail or f"selector: {r.selector!r}", sc=0)

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] 시나리오 0a: UIScanner ADD 모달 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="common_operation_process",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page._close_modal_if_open,
        )
        self._report_scan(report, "sc0a(ADD 모달)")
