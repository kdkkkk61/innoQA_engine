"""
pages/shared/pickers/special_folder_picker.py — 공통 예약어 (특수폴더) picker

대상 모달: div#selectReservedWordControl
호출처:
  - process_modal.cache_folder_section → button.specialFolderBtn 클릭 시
  - (향후) 다른 cache_folder 영역 사용처

yaml 참조: config/scan_hints/control_suite.yaml — special_folder_picker 섹션

설계 원칙:
  - 11개 예약어를 클래스 상수로 노출 (코드/설명 매핑)
  - 다중 체크 + 클릭 순서 보존 (yaml order_preservation rule 반영)
  - 검색 기능 없음 (단순 다중 체크 picker)
"""
from playwright.sync_api import Page
from pages.shared._overlay import overlay_off


class SpecialFolderPicker:
    """selectReservedWordControl 예약어 picker — 다중 선택 + 순서 보존."""

    # ------------------------------------------------------------------
    # 11 예약어 코드 (yaml special_folder_picker.reserved_words)
    # ------------------------------------------------------------------
    RESERVED_WORDS: dict[str, str] = {
        "[/DESKTOP/]":        "바탕화면",
        "[/MYDOC/]":          "내문서",
        "[/FAVORITES/]":      "즐겨찾기",
        "[/USER/]":           "%USERPROFILE%",
        "[/APPDATA/]":        "User\\AppData\\Roaming",
        "[/LOCAL_APPDATA/]":  "%USERPROFILE%\\AppData\\Local",
        "[/COMPUTERNAME/]":   "실행 중인 컴퓨터의 이름 (EX. DESKTOP-70D7BB0)",
        "[/MACADDR/]":        "실행 중인 컴퓨터의 MAC Address",
        "[/USERID/]":         "로그인한 클라이언트 아이디",
        "[/DNAME/]":          "드라이브 이름으로 드라이브를 선택",
        "[/DMODEL/]":         "드라이브 모델로 드라이브를 선택",
    }

    # ------------------------------------------------------------------
    # Selectors
    # ------------------------------------------------------------------
    SEL_MODAL          = "div#selectReservedWordControl"
    SEL_MODAL_OPEN     = "div#selectReservedWordControl.in"
    SEL_TITLE          = "div#selectReservedWordControl .modal-title"
    SEL_ROW            = "div#selectReservedWordControl table tbody tr"
    SEL_CHECKBOX       = "div#selectReservedWordControl input[type='checkbox'][name='selectReservedWord']"
    SEL_CONFIRM_BTN    = "div#selectReservedWordControl .btn.btn-primary"
    SEL_CANCEL_BTN     = "div#selectReservedWordControl .btn.btn-default, div#selectReservedWordControl .close"

    _TIMEOUT_OPEN      = 3000
    _TIMEOUT_CLOSE     = 3000

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
        return self.page.locator(self.SEL_MODAL_OPEN).count() > 0

    def wait_open(self, timeout: int | None = None) -> None:
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=timeout or self._TIMEOUT_OPEN
        )

    def wait_closed(self, timeout: int | None = None) -> None:
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="detached", timeout=timeout or self._TIMEOUT_CLOSE
        )

    def get_title(self) -> str:
        loc = self.page.locator(self.SEL_TITLE).first
        return loc.inner_text().strip() if loc.count() > 0 else ""

    def get_checked_codes(self) -> list[str]:
        """현재 체크된 예약어 코드 목록 (DOM 순서)."""
        rows = self.page.locator(self.SEL_ROW)
        out: list[str] = []
        for i in range(rows.count()):
            row = rows.nth(i)
            cb = row.locator("input[type='checkbox']").first
            if cb.is_checked():
                code = row.locator("td").nth(1).inner_text().strip()
                out.append(code)
        return out

    # ------------------------------------------------------------------
    # 선택
    # ------------------------------------------------------------------
    def select_codes(self, codes: list[str]) -> None:
        """
        예약어 코드 리스트 순서대로 클릭.
        yaml order_preservation: cacheFolderInput 안 inline tag 가 클릭 순서대로 좌→우 삽입.
        """
        for code in codes:
            if code not in self.RESERVED_WORDS:
                raise ValueError(
                    f"SpecialFolderPicker: 알 수 없는 예약어 '{code}' "
                    f"(가능: {list(self.RESERVED_WORDS.keys())})"
                )
            row = self.page.locator(self.SEL_ROW).filter(has_text=code).first
            cb = row.locator("input[type='checkbox']").first
            if not cb.is_checked():
                self._click(cb)

    def select_indices(self, indices: list[int]) -> None:
        """0-based index 리스트 순서대로 체크."""
        cbs = self.page.locator(self.SEL_CHECKBOX)
        for i in indices:
            cb = cbs.nth(i)
            if not cb.is_checked():
                self._click(cb)

    def uncheck_all(self) -> None:
        """모든 체크 해제 (사이클 reset)."""
        cbs = self.page.locator(self.SEL_CHECKBOX)
        for i in range(cbs.count()):
            cb = cbs.nth(i)
            if cb.is_checked():
                self._click(cb)

    # ------------------------------------------------------------------
    # 액션
    # ------------------------------------------------------------------
    def confirm(self) -> None:
        """확인 → picker 닫고 cacheFolderInput 안에 inline tag 삽입 (클릭 순서대로)."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)

    def cancel(self) -> None:
        self._click(self.page.locator(self.SEL_CANCEL_BTN).first)

    # ------------------------------------------------------------------
    # 표준 흐름 헬퍼
    # ------------------------------------------------------------------
    def select_and_confirm(self, codes: list[str]) -> list[str]:
        """
        예약어 codes 순서대로 체크 + 확인.
        return: 확정 선택된 코드 (클릭 순서 보존 검증 가능)
        """
        self.wait_open()
        self.select_codes(codes)
        # 확인 전 sanity check — 체크 상태가 DOM 순서이므로 클릭 순서와 다를 수 있음
        # (cacheFolderInput 의 inline tag 순서 = 클릭 순서, 검증은 호출자가 수행)
        self.confirm()
        self.wait_closed()
        return codes
