"""태그 관리 — 시나리오 1: UI 구조 (재구성 2026-07-03, 직접조작 실측 반영).

1a — 리스트 버튼 6종 (실측 2026-07-03: add/modify/import/export/remove/search)
1b — 테이블 헤더 3종 (태그 이름/프로세스 카운트/설명)
1c — 검색 영역 (input#searchText + button#searchBtn — 검색 옵션 select 없음이 정상)
1d — 속성 모달(div#detailGlobalTag) 열림/닫힘 + 등록 프로세스 테이블·사용처 섹션 존재
"""
from pages.npouch_tag_page import NpouchTagPage
from tests.common.tag._base import TagBase


class TestTagScenario1Ui(TagBase):
    """태그 관리 — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchTagPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc1a: 리스트 버튼 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        for btn_id, label in [
            ("addItemBtn",    "추가 버튼"),
            ("modifyItemBtn", "수정 버튼"),
            ("removeItemBtn", "삭제 버튼"),
            ("importFileBtn", "가져오기 버튼"),
            ("exportFileBtn", "내보내기 버튼"),
            ("searchBtn",     "검색 버튼"),
        ]:
            exists = page.page.locator(f"button#{btn_id}").count() > 0
            self._add("pass" if exists else "fail", f"sc1a — {label} 존재",
                      f"결과: {'존재' if exists else '없음'}", sc=1)

    def test_scenario1b_table_headers(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc1b: 테이블 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = [th.inner_text().strip() for th in page.page.locator("table thead th").all()]
        print(f"  실제 헤더: {headers}")
        for label in ["태그 이름", "프로세스 카운트", "설명"]:
            ok = label in headers
            self._add("pass" if ok else "fail", f"sc1b — 테이블 헤더 '{label}'",
                      f"결과: {'존재' if ok else '없음'} (전체={headers})", sc=1)

    def test_scenario1c_search_area(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc1c: 검색 영역 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for sel, label in [
            ("input#searchText", "검색창"),
            ("button#searchBtn", "검색 버튼"),
        ]:
            exists = page.page.locator(sel).count() > 0
            self._add("pass" if exists else "fail", f"sc1c — {label} 존재",
                      f"결과: {'존재' if exists else '없음'}", sc=1)
        # 검색 옵션 select 없음이 현재 구조(실측 2026-07-03) — 생기면 신규 기능 감지
        opt_cnt = page.page.locator("select#searchOption").count()
        self._add("pass" if opt_cnt == 0 else "warn", "sc1c — 검색 옵션 select 부재(단일 검색)",
                  f"결과: select#searchOption {opt_cnt}개 (0=현재 구조, 1+=신규 기능 등장)", sc=1)

    def test_scenario1d_detail_modal_open_close(self, logged_in_page, settings):
        """속성 모달(detailGlobalTag) — 행 가운데 더블클릭(직접조작 실측 2026-07-03)."""
        print("\n━━ [태그 관리] sc1d: 속성 모달 열림/닫힘 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_cm_tag_sc1_detail"
        page.add_item(tpl)   # 중간 삭제 없음 — sc5d cleanup 이 일괄 정리
        page.open_detail_modal(tpl)
        dtext = page.detail_modal_text()
        opened = tpl in dtext
        has_proc_table = page.page.locator("div#detailGlobalTag tbody#globalProcessTbBd").count() > 0
        has_usage = "사용처" in dtext
        self._add("pass" if opened else "fail",
                  "sc1d — 속성 모달 열림(행 가운데 더블클릭) + 이름 표시",
                  f"결과: 이름 표시={opened}, 등록 프로세스 테이블={has_proc_table}, 사용처 섹션={has_usage}", sc=1,
                  repro="1. 행 가운데(카운트 셀) 더블클릭\n2. '태그 속성' 모달 + 프로세스 테이블·사용처 확인")
        page.close_detail_modal()
        closed = page.page.locator(page.SEL_DETAIL_MODAL).count() == 0
        self._add("pass" if closed else "fail", "sc1d — 속성 모달 닫힘",
                  f"결과: 닫힘={closed}", sc=1)
