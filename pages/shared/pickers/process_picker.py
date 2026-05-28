"""
pages/shared/pickers/process_picker.py — globalProcessList 모달 picker

[Step 3b — 최소: single / tag 모드, 첫 행 선택, confirm]

대상 모달: div#globalProcessList
호출처:
  - process_sub_modal#csuProcessBtn (개별 프로세스 sub-tab)  → mode='single'
  - process_sub_modal#csuProcessBtn (태그 sub-tab)           → mode='tag'
  - (예정) web_restrict#addWebRestrictProcess                → mode='multi'

mode 별 선택 input:
  single → input[type='radio'][name='selectProcess']
  tag    → input[type='radio'][name='selectProcessTag']
  multi  → input[type='checkbox'][name='selectProcess']

라디오/체크박스 input 은 Bootstrap 스타일로 hidden → _click_hidden 사용.
"""
from typing import Literal
from playwright.sync_api import Page

from pages.shared._overlay import overlay_off


PickerMode = Literal["single", "tag", "multi"]


class ProcessPicker:
    """globalProcessList 모달 picker — 3 모드 지원 (Step 3b: single/tag)."""

    # ── Selectors ──────────────────────────────────────────────────
    SEL_MODAL              = "div#globalProcessList"
    SEL_MODAL_OPEN         = "div#globalProcessList.in"
    SEL_TITLE              = "div#globalProcessList .modal-title"

    SEL_ROW                = "div#globalProcessList table tbody tr"
    SEL_RADIO_PROCESS      = "div#globalProcessList input[type='radio'][name='selectProcess']"
    SEL_RADIO_TAG          = "div#globalProcessList input[type='radio'][name='selectProcessTag']"
    SEL_CHECKBOX_PROCESS   = "div#globalProcessList input[type='checkbox'][name='selectProcess']"

    SEL_CONFIRM_BTN        = "div#globalProcessList .btn.btn-primary"
    SEL_CLOSE_BTN          = "div#globalProcessList .close"

    _TIMEOUT_OPEN          = 3000
    _TIMEOUT_CLOSE         = 3000

    # ── 생성 ────────────────────────────────────────────────────────
    def __init__(self, page: Page):
        self.page = page

    def _click(self, locator) -> None:
        """visible button — overlay OFF → native click → overlay ON."""
        with overlay_off(self.page):
            locator.click()

    def _click_hidden(self, locator) -> None:
        """hidden input — JS evaluate click (좌표 무관)."""
        locator.evaluate("el => el.click()")

    # ── 상태 ────────────────────────────────────────────────────────
    def is_open(self) -> bool:
        return self.page.locator(self.SEL_MODAL_OPEN).count() > 0

    def wait_open(self, timeout: int | None = None) -> None:
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=timeout or self._TIMEOUT_OPEN
        )
        # picker open 직후 modal-backdrop.in 수를 기록 (wait_closed 에서 비교).
        self._backdrop_count_on_open = self.page.locator("div.modal-backdrop.in").count()

    def wait_closed(self, timeout: int | None = None) -> None:
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="detached", timeout=timeout or self._TIMEOUT_CLOSE
        )
        # picker 가 추가한 topmost modal-backdrop 도 detach 될 때까지 대기.
        # 3-stack (EDIT → web_restrict → picker) 닫힘 직후 다음 클릭이
        # 잔여 backdrop 에 가로채이는 케이스 방어 (4f).
        expected = max(0, getattr(self, "_backdrop_count_on_open", 1) - 1)
        try:
            self.page.wait_for_function(
                "(n) => document.querySelectorAll('div.modal-backdrop.in').length <= n",
                arg=expected,
                timeout=1500,
            )
        except Exception:
            pass

    def get_title(self) -> str:
        return self.page.locator(self.SEL_TITLE).first.inner_text().strip()

    def get_row_count(self) -> int:
        return self.page.locator(self.SEL_ROW).count()

    def get_first_row_text(self) -> str:
        """첫 행 두번째 td (프로세스명 or 태그명) — 0번 td 는 radio/checkbox."""
        row = self.page.locator(self.SEL_ROW).first
        return row.locator("td").nth(1).inner_text().strip()

    # ── 선택 ────────────────────────────────────────────────────────
    def select_first(self, mode: PickerMode) -> None:
        """모드별 첫 행의 input '선택' (idempotent).

        ⚠ multi(체크박스) 는 click 이 토글이라, picker 재오픈 시 이전 체크 상태가
        남아있으면 click 으로 언체크됨 → 결과적으로 선택 0건 (sc3f Case7 / sc4l E
        backdrop fix 후에도 wr#2 적용 프로세스 0건으로 confirm 시 '선택된 프로세스가
        없습니다.' 메시지 발생 — 2026-05-28 사용자 보고).
        → multi 모드는 is_checked() 가드: 이미 체크면 no-op, 아니면 click.
        single/tag(라디오) 는 click 이 토글 아님 → 항상 click.
        """
        sel = {
            "single": self.SEL_RADIO_PROCESS,
            "tag":    self.SEL_RADIO_TAG,
            "multi":  self.SEL_CHECKBOX_PROCESS,
        }[mode]
        loc = self.page.locator(sel).first
        if mode == "multi":
            try:
                if loc.is_checked():
                    return
            except Exception:
                pass
        self._click_hidden(loc)

    # ── 액션 ────────────────────────────────────────────────────────
    def confirm(self) -> None:
        """확인 → picker 닫고 호출 모달로 선택값 반환."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)

    def cancel(self) -> None:
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)

    # ── 표준 흐름 헬퍼 ──────────────────────────────────────────────
    def select_first_and_confirm(self, mode: PickerMode) -> str:
        """첫 행 선택 + 확인 → 선택된 행 텍스트 반환."""
        self.wait_open()
        # AngularJS 데이터 로드 지연 대비 — 첫 행 attached 까지 대기
        try:
            self.page.locator(self.SEL_ROW).first.wait_for(
                state="attached", timeout=3000
            )
        except Exception:
            pass
        if self.get_row_count() == 0:
            raise RuntimeError("ProcessPicker: 선택 가능한 행이 0건")
        first_text = self.get_first_row_text()
        self.select_first(mode)
        self.confirm()
        self.wait_closed()
        return first_text
