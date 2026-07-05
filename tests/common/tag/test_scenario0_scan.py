"""태그 관리 — UIScanner 기반 자동 스캔 (sc0, 재구성 2026-07-03).

yaml ↔ 실제 DOM 비교 → 추가(discovered_new)/삭제(discovered_missing)/숨김(discovered_hidden) 감지.
ADD 모달(addItemModal) 1개 → 스캔 1개(0a).
yaml: config/scan_hints/common_tag.yaml — text_inputs 2필드 + plain_checkboxes 1(전체선택).
보고는 _base._report_scan (카드 규칙 준수판 — 변경 요소 재캡처+빨간 표시, 사람이 읽는 설명).
"""
from core.ui_scanner import UIScanner
from pages.npouch_tag_page import NpouchTagPage
from tests.common.tag._base import TagBase


class TestTagScenario0Scan(TagBase):
    """태그 관리 — UIScanner 자동 스캔 (시나리오 0)."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchTagPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        print("\n━━ [태그 관리] 시나리오 0a: UIScanner ADD 모달 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="common_tag",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page._close_modal_if_open,
        )
        self._report_scan(report, "sc0a(ADD 모달)", page=page,
                          modal_open_fn=page.open_add_modal,
                          modal_close_fn=page._close_modal_if_open)
