"""
pages/shared/pickers/process_picker.py — 공통 프로세스/태그 선택 picker

대상 모달: div#globalProcessList
호출처:
  - process_modal#csuProcessBtn (개별 프로세스 sub-tab)  → mode='single'
  - process_modal#csuProcessBtn (태그 sub-tab)           → mode='tag_single'
  - web_restrict_modal#addWebRestrictProcess             → mode='multi'

yaml 참조: config/scan_hints/control_suite.yaml — process_picker 섹션

설계 원칙:
  - 호출자가 mode 명시 (자동 감지 X — 의도 명확화)
  - selector 상수 모듈 하단에 집중
  - 모든 액션은 Playwright locator 정식 dispatch (trusted event)
  - 결과는 dict 또는 list 로 반환 (qa_runner 가 yaml 과 비교)
"""
from typing import Literal
from playwright.sync_api import Page
from pages.shared._overlay import overlay_off


PickerMode = Literal["single", "multi", "tag_single"]


class ProcessPicker:
    """globalProcessList 모달 picker — 3 모드 지원."""

    # ------------------------------------------------------------------
    # Selectors (yaml process_picker 섹션과 동기화)
    # ------------------------------------------------------------------
    SEL_MODAL              = "div#globalProcessList"
    SEL_MODAL_OPEN         = "div#globalProcessList.in"
    SEL_TITLE              = "div#globalProcessList .modal-title"

    # 검색
    SEL_SEARCH_INPUT       = "div#globalProcessList input#searchText"
    SEL_SEARCH_BTN         = "div#globalProcessList button#searchBtn"
    SEL_CATEGORY_SELECT    = "div#globalProcessList select"   # multi_select 모드에서만 노출

    # 결과 테이블
    SEL_ROW                = "div#globalProcessList table tbody tr"

    # 선택 input — mode 별 다름
    SEL_RADIO_PROCESS      = "div#globalProcessList input[type='radio'][name='selectProcess']"
    SEL_CHECKBOX_PROCESS   = "div#globalProcessList input[type='checkbox'][name='selectProcess']"
    SEL_RADIO_TAG          = "div#globalProcessList input[type='radio'][name='selectProcessTag']"

    # 액션 버튼
    SEL_ADD_NEW_BTN        = "div#globalProcessList button#addItemBtn"   # '프로세스 추가' (4단계 모달)
    SEL_CONFIRM_BTN        = "div#globalProcessList .btn.btn-primary"
    SEL_CLOSE_BTN          = "div#globalProcessList .close"

    # 총 건수 표시 ('등록된 프로세스 : 1249 건' / '등록된 태그 : 116 건')
    SEL_TOTAL_COUNT_TEXT   = "div#globalProcessList .totalCount, div#globalProcessList span.blueTxt"

    _TIMEOUT_OPEN          = 3000
    _TIMEOUT_CLOSE         = 3000

    # ------------------------------------------------------------------
    # 생성
    # ------------------------------------------------------------------
    def __init__(self, page: Page):
        self.page = page

    def _click(self, locator) -> None:
        """overlay OFF -> native click -> overlay ON. 사람 입력 차단 유지."""
        with overlay_off(self.page):
            locator.click()

    # ------------------------------------------------------------------
    # 상태 조회
    # ------------------------------------------------------------------
    def is_open(self) -> bool:
        """picker 모달이 열려있는지."""
        return self.page.locator(self.SEL_MODAL_OPEN).count() > 0

    def get_title(self) -> str:
        """모달 제목 — '프로세스 선택' 또는 '태그 선택'."""
        loc = self.page.locator(self.SEL_TITLE).first
        return loc.inner_text().strip() if loc.count() > 0 else ""

    def wait_open(self, timeout: int | None = None) -> None:
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=timeout or self._TIMEOUT_OPEN
        )

    def wait_closed(self, timeout: int | None = None) -> None:
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="detached", timeout=timeout or self._TIMEOUT_CLOSE
        )

    # ------------------------------------------------------------------
    # 검색
    # ------------------------------------------------------------------
    def search(self, text: str) -> None:
        """검색어 입력 + Enter (button#searchBtn 클릭이 ng-model 미동기 케이스 있어 Enter 우선)."""
        inp = self.page.locator(self.SEL_SEARCH_INPUT).first
        self._click(inp)
        inp.fill(text)
        inp.press("Enter")

    def get_row_texts(self) -> list[str]:
        """현재 표시된 행 텍스트 목록."""
        rows = self.page.locator(self.SEL_ROW)
        return [rows.nth(i).inner_text().strip() for i in range(rows.count())]

    # ------------------------------------------------------------------
    # 선택 — mode 별 분리 (호출자 의도 명확)
    # ------------------------------------------------------------------
    def select_single(self, row_text: str | None = None, *, by_index: int = 0) -> None:
        """
        single_select 모드 (process_modal#csuProcessBtn 호출).
        row_text 지정 시 해당 행의 radio, 미지정 시 by_index 번째 행.
        """
        radio = self._find_select_input(self.SEL_RADIO_PROCESS, row_text, by_index)
        self._click(radio)

    def select_multi(self, row_texts: list[str] | None = None, *, indices: list[int] | None = None) -> None:
        """
        multi_select 모드 (web_restrict#addWebRestrictProcess 호출).
        row_texts 또는 indices 지정.
        """
        if row_texts:
            for t in row_texts:
                cb = self._find_select_input(self.SEL_CHECKBOX_PROCESS, t)
                self._click(cb)
        elif indices:
            cbs = self.page.locator(self.SEL_CHECKBOX_PROCESS)
            for i in indices:
                self._click(cbs.nth(i))
        else:
            raise ValueError("select_multi: row_texts 또는 indices 필요")

    def select_tag(self, row_text: str | None = None, *, by_index: int = 0) -> None:
        """
        tag_single_select 모드 (process_modal 태그 sub-tab 호출).
        """
        radio = self._find_select_input(self.SEL_RADIO_TAG, row_text, by_index)
        self._click(radio)

    # ------------------------------------------------------------------
    # 액션
    # ------------------------------------------------------------------
    def confirm(self) -> None:
        """확인 버튼 클릭 — picker 닫고 호출 모달로 선택값 반환."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)

    def cancel(self) -> None:
        """× 버튼 클릭 — 선택 취소."""
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)

    def click_add_new_process(self) -> None:
        """
        '프로세스 추가' 버튼 (single_select / multi_select 모드에서만 노출).
        4단계 모달 (운용 프로세스 등록) 호출. tag_single_select 모드에는 없음.
        """
        self._click(self.page.locator(self.SEL_ADD_NEW_BTN).first)

    # ------------------------------------------------------------------
    # 표준 흐름 헬퍼 (selection_flow 단순 통과)
    # ------------------------------------------------------------------
    def select_first_and_confirm(self, mode: PickerMode) -> str:
        """
        picker 의 첫 행 선택 + 확인.
        return: 선택된 행 텍스트 (첫 컬럼)
        """
        self.wait_open()
        rows = self.page.locator(self.SEL_ROW)
        if rows.count() == 0:
            raise RuntimeError("ProcessPicker: 선택 가능한 행이 0건")
        first_row = rows.first
        # 행 첫 td 의 텍스트 (프로세스 명 또는 태그 명)
        first_cell_text = first_row.locator("td").nth(1).inner_text().strip()

        if mode == "single":
            self.select_single(by_index=0)
        elif mode == "multi":
            self.select_multi(indices=[0])
        elif mode == "tag_single":
            self.select_tag(by_index=0)
        else:
            raise ValueError(f"unknown mode: {mode}")

        self.confirm()
        self.wait_closed()
        return first_cell_text

    def search_select_confirm(self, mode: PickerMode, search_text: str, *, row_text: str | None = None) -> str:
        """
        검색 → 첫 결과 (또는 row_text 일치) 선택 → 확인.
        시나리오 6 의 [AUTO_KEEP] 검색 등에 활용.
        """
        self.wait_open()
        self.search(search_text)
        rows = self.page.locator(self.SEL_ROW)
        if rows.count() == 0:
            raise RuntimeError(f"ProcessPicker: '{search_text}' 검색 결과 0건")
        target_text = row_text or rows.first.locator("td").nth(1).inner_text().strip()

        if mode == "single":
            self.select_single(row_text=target_text)
        elif mode == "multi":
            self.select_multi(row_texts=[target_text])
        elif mode == "tag_single":
            self.select_tag(row_text=target_text)
        else:
            raise ValueError(f"unknown mode: {mode}")

        self.confirm()
        self.wait_closed()
        return target_text

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _find_select_input(self, selector: str, row_text: str | None, by_index: int = 0):
        """row_text 일치하는 행의 input 또는 by_index 번째 input 반환."""
        if row_text:
            row = self.page.locator(self.SEL_ROW).filter(has_text=row_text).first
            if row.count() == 0:
                raise RuntimeError(f"ProcessPicker: '{row_text}' 행 미발견")
            return row.locator(selector.split(' ')[-1]).first
        return self.page.locator(selector).nth(by_index)
