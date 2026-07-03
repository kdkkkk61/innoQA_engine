"""운용 프로세스 — 시나리오 1: UI 구조 (재구성 2026-07-03, 기존 test_operation_process sc1 이관).

1a — session cleanup + 리스트 버튼 6종
1b — 테이블 헤더 5종
1c — 검색 영역(입력/옵션/버튼) + 옵션 목록
1d — 속성 모달 열림/닫힘 (신규 — 직접조작 실측 2026-07-03: 행 가운데 더블클릭 → detailGlobalProcess)
"""
from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase


class TestOperationProcessScenario1Ui(OperationProcessBase):
    """운용 프로세스 — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc1a: 리스트 버튼 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        for btn_id, label in [
            ("addItemBtn",      "추가 버튼"),
            ("modifyItemBtn",   "수정 버튼"),
            ("removeItemBtn",   "삭제 버튼"),
            ("excelDownload",   "EXCEL 다운로드 버튼"),
            ("importFileBtn",   "가져오기 버튼"),
            ("downloadFileBtn", "내보내기 버튼"),
        ]:
            exists = page.page.locator(f"button#{btn_id}").count() > 0
            self._add("pass" if exists else "fail", f"sc1a — {label} 존재",
                      f"결과: {'존재' if exists else '없음'}", sc=1)

    def test_scenario1b_table_headers(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc1b: 테이블 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = [th.inner_text().strip() for th in page.page.locator("table thead th").all()]
        print(f"  실제 헤더: {headers}")
        for label, accept in [
            ("프로세스명/이름", {"프로세스명", "프로세스 이름"}),
            ("서명", {"서명"}), ("설명", {"설명"}),
            ("등록일", {"등록일"}), ("수정일", {"수정일"}),
        ]:
            ok = any(a in headers for a in accept)
            self._add("pass" if ok else "fail", f"sc1b — 테이블 헤더 '{label}'",
                      f"결과: {'존재' if ok else '없음'} (전체={headers})", sc=1)

    def test_scenario1c_search_area(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc1c: 검색 영역 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for sel, label in [
            ("input#searchText",    "검색창"),
            ("select#searchOption", "검색 옵션 셀렉트"),
            ("button#searchBtn",    "검색 버튼"),
        ]:
            exists = page.page.locator(sel).count() > 0
            self._add("pass" if exists else "fail", f"sc1c — {label} 존재",
                      f"결과: {'존재' if exists else '없음'}", sc=1)
        opt = page.page.locator("select#searchOption")
        if opt.count() > 0:
            options = [o.inner_text().strip() for o in opt.locator("option").all()]
            self._add("pass", "sc1c — 검색 옵션 목록", str(options), sc=1)

    def test_scenario1d_detail_modal_open_close(self, logged_in_page, settings):
        """속성 모달(detailGlobalProcess) 열림/닫힘 — 행 가운데 더블클릭(직접조작 실측 2026-07-03)."""
        print("\n━━ [운용 프로세스] sc1d: 속성 모달 열림/닫힘 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_cm_sc1_detail"
        page.add_item(tpl)   # 중간 삭제 없음 — sc5d cleanup 이 일괄 정리
        page.open_detail_modal(tpl)
        dtext = page.detail_modal_text()
        opened = tpl in dtext
        has_usage = "사용처" in dtext
        self._add("pass" if opened else "fail",
                  "sc1d — 속성 모달 열림(행 가운데 더블클릭) + 이름 표시",
                  f"결과: 모달에 이름 표시={opened}, 사용처 섹션={has_usage}", sc=1,
                  repro="1. 행 가운데(서명 셀) 더블클릭\n2. '운용 프로세스 속성' 모달 + 사용처 확인")
        page.close_detail_modal()
        closed = page.page.locator(page.SEL_DETAIL_MODAL).count() == 0
        self._add("pass" if closed else "fail", "sc1d — 속성 모달 닫힘",
                  f"결과: 닫힘={closed}", sc=1)
