"""
pages/shared/pickers/special_folder_picker.py — 예약어 (특수폴더) 다중 선택 picker

[Step 3c-extra] cache_folder_section 의 specialFolderBtn 클릭 시 출현.

대상 모달: div#selectReservedWordControl
호출처: process_modal.cache_folder_section
11 예약어 코드 (Chrome MCP 검증 2026-05-12 — yaml special_folder_picker.reserved_words)

핵심 규칙 (yaml order_preservation):
  - 체크 순서대로 cacheFolderInput 에 inline tag 좌→우 삽입 (DOM 순 X)
  - 결과 list 도 동일 순서 보존

체크박스 input 자체는 hidden (Bootstrap 패턴) → JS evaluate click 사용.
"""
from playwright.sync_api import Page

from pages.shared._overlay import overlay_off


class SpecialFolderPicker:
    """selectReservedWordControl — 11 예약어 다중 선택 + 순서 보존."""

    # ── 11 예약어 코드 (yaml special_folder_picker.reserved_words) ─
    RESERVED_WORDS: dict[str, str] = {
        "[/DESKTOP/]":        "바탕화면",
        "[/MYDOC/]":          "내문서",
        "[/FAVORITES/]":      "즐겨찾기",
        "[/USER/]":           "%USERPROFILE%",
        "[/APPDATA/]":        "User\\AppData\\Roaming",
        "[/LOCAL_APPDATA/]":  "%USERPROFILE%\\AppData\\Local",
        "[/COMPUTERNAME/]":   "실행 중인 컴퓨터의 이름",
        "[/MACADDR/]":        "실행 중인 컴퓨터의 MAC Address",
        "[/USERID/]":         "로그인한 클라이언트 아이디",
        "[/DNAME/]":          "드라이브 이름으로 드라이브를 선택",
        "[/DMODEL/]":         "드라이브 모델로 드라이브를 선택",
    }

    # ── Selectors ──────────────────────────────────────────────────
    SEL_MODAL          = "div#selectReservedWordControl"
    SEL_MODAL_OPEN     = "div#selectReservedWordControl.in"
    SEL_TITLE          = "div#selectReservedWordControl .modal-title"
    SEL_ROW            = "div#selectReservedWordControl table tbody tr"
    SEL_CHECKBOX       = (
        "div#selectReservedWordControl "
        "input[type='checkbox'][name='selectReservedWord']"
    )
    SEL_CONFIRM_BTN    = "div#selectReservedWordControl button.btn-primary"
    SEL_CANCEL_BTN     = "div#selectReservedWordControl button.btn-default"

    _TIMEOUT_OPEN      = 3000
    _TIMEOUT_CLOSE     = 3000

    # ── 생성 ────────────────────────────────────────────────────────
    def __init__(self, page: Page):
        self.page = page

    def _click(self, locator) -> None:
        """visible button — overlay OFF → native click → overlay ON."""
        with overlay_off(self.page):
            locator.click()

    def _click_hidden(self, locator) -> None:
        """hidden input (체크박스) — JS evaluate click."""
        locator.evaluate("el => el.click()")

    # ── 상태 ────────────────────────────────────────────────────────
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
        return self.page.locator(self.SEL_TITLE).first.inner_text().strip()

    def get_row_count(self) -> int:
        return self.page.locator(self.SEL_ROW).count()

    # ── 선택 (체크 순서 = 결과 순서) ──────────────────────────────
    def select_codes(self, codes: list[str]) -> None:
        """
        예약어 코드 리스트 순서대로 클릭.
        yaml order_preservation: cacheFolderInput 에 클릭 순서대로 좌→우 삽입.
        """
        for code in codes:
            if code not in self.RESERVED_WORDS:
                raise ValueError(
                    f"SpecialFolderPicker: 알 수 없는 예약어 {code!r}. "
                    f"가능: {list(self.RESERVED_WORDS.keys())}"
                )
            row = self.page.locator(self.SEL_ROW).filter(has_text=code).first
            cb = row.locator("input[type='checkbox']").first
            if not cb.is_checked():
                self._click_hidden(cb)

    def get_checked_codes(self) -> list[str]:
        """현재 체크된 예약어 코드 (DOM 순서)."""
        rows = self.page.locator(self.SEL_ROW)
        out: list[str] = []
        for i in range(rows.count()):
            row = rows.nth(i)
            cb = row.locator("input[type='checkbox']").first
            if cb.is_checked():
                code = row.locator("td").nth(1).inner_text().strip()
                out.append(code)
        return out

    # ── 액션 ────────────────────────────────────────────────────────
    def confirm(self) -> None:
        """확인 → picker 닫고 cacheFolderInput 에 inline tag 삽입."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)

    def cancel(self) -> None:
        self._click(self.page.locator(self.SEL_CANCEL_BTN).first)

    # ── 표준 흐름 ──────────────────────────────────────────────────
    def select_and_confirm(self, codes: list[str]) -> list[str]:
        """codes 순서대로 체크 + 확인. return: 전달한 codes (검증용)."""
        self.wait_open()
        self.select_codes(codes)
        self.confirm()
        self.wait_closed()
        return codes
