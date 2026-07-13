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


PickerMode = Literal["single", "tag", "multi", "tag_multi"]
# tag_multi: 태그 checkbox(name=selectProcessTag) — 시큐어존 프로세스 L3 실측 2026-07-08
#   (control_suite 태그=radio 와 달리 이 호출 컨텍스트에선 checkbox 로 렌더됨)


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
    SEL_CHECKBOX_TAG       = "div#globalProcessList input[type='checkbox'][name='selectProcessTag']"

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

        ⚠ multi(체크박스) 함정 (2026-05-28 사용자 보고 #27 BUG):
          - picker 재오픈 시 DOM checked 와 AngularJS ng-model 가 어긋난 상태일 수 있음
            (예: DOM 은 체크 잔존, 모델은 reset).
          - 단순 JS click 은 토글 → 어긋난 상태에서 unchecked 로 빠지거나 모델 미갱신.
          - 단순 is_checked() 가드 (no-op) 은 모델 동기화 안 됨 → confirm 후 wr#2 적용
            프로세스 0건 → '선택된 프로세스가 없습니다.' 메시지.
        → Playwright `check(force=True)` 사용: checkbox 전용 idempotent, 실제 event
          sequence 로 AngularJS ng-change/ng-model 까지 sync. force=True 로 hidden
          input 도 actionability 우회.
        single/tag(라디오) 는 click 이 토글 아님 → 종전대로 JS click 유지.
        """
        sel = {
            "single":    self.SEL_RADIO_PROCESS,
            "tag":       self.SEL_RADIO_TAG,
            "multi":     self.SEL_CHECKBOX_PROCESS,
            "tag_multi": self.SEL_CHECKBOX_TAG,
        }[mode]
        loc = self.page.locator(sel).first
        if mode in ("multi", "tag_multi"):
            try:
                loc.check(force=True)
            except Exception:
                # fallback: 강제 checked 설정 + change/click dispatch (AngularJS digest)
                loc.evaluate(
                    "el => { el.checked = true; "
                    "el.dispatchEvent(new Event('change', {bubbles: true})); "
                    "el.dispatchEvent(new Event('click', {bubbles: true})); }"
                )
            return
        self._click_hidden(loc)

    # ── 액션 ────────────────────────────────────────────────────────
    def confirm(self) -> None:
        """확인 → picker 닫고 호출 모달로 선택값 반환.
        ★4탭 템플릿 페이지는 래퍼(div#globalProcessList.modal-wrap)가 w=0 로 공존해
        native click 이 visible 대기 timeout 나는 케이스 있음(13:57 run sc3c).
        JS click fallback — Chrome 실측(2026-07-13): 래퍼 확인 버튼 JS click 으로
        선택 반영·닫힘 정상 동작 확인."""
        btn = self.page.locator(self.SEL_CONFIRM_BTN).first
        try:
            with overlay_off(self.page):
                btn.click(timeout=2000)
        except Exception:
            btn.evaluate("el => el.click()")

    def cancel(self) -> None:
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)

    def select_nth(self, idx: int, mode: PickerMode) -> None:
        """모드별 N번째 행 선택 (idempotent for multi).

        용도: 한 정책 안 다른 web_restrict 에 '다른' 프로세스를 할당해야 할 때
              (yaml :287 cross_instance_ADD_flow — 동일 프로세스 재선택 시 silent 거부).
        """
        sel = {
            "single":    self.SEL_RADIO_PROCESS,
            "tag":       self.SEL_RADIO_TAG,
            "multi":     self.SEL_CHECKBOX_PROCESS,
            "tag_multi": self.SEL_CHECKBOX_TAG,
        }[mode]
        loc = self.page.locator(sel).nth(idx)
        if mode in ("multi", "tag_multi"):
            try:
                loc.check(force=True)
            except Exception:
                loc.evaluate(
                    "el => { el.checked = true; "
                    "el.dispatchEvent(new Event('change', {bubbles: true})); "
                    "el.dispatchEvent(new Event('click', {bubbles: true})); }"
                )
            return
        self._click_hidden(loc)

    # ── 표준 흐름 헬퍼 ──────────────────────────────────────────────
    # ── 검색 + 이름 선택 (날짜본 seed 소비용 — 2026-07-08) ──────────
    SEL_SEARCH_INPUT = "div#globalProcessList input#searchText"
    SEL_SEARCH_BTN2  = "div#globalProcessList button#searchBtn, div#globalProcessList .fa-search"

    def search(self, term: str) -> None:
        """picker 내 검색 — ng-model 갱신 + Enter + 검색버튼 (AngularJS 호환, 태그 페이지
        select_process_by_name 검증 패턴 일반화)."""
        inp = self.page.locator(self.SEL_SEARCH_INPUT)
        if inp.count() == 0:
            return
        inp.first.evaluate(
            "(el, v) => { el.value = v;"
            " el.dispatchEvent(new Event('input',{bubbles:true}));"
            " el.dispatchEvent(new Event('change',{bubbles:true})); }", term)
        try:
            inp.first.press("Enter")
        except Exception:
            pass
        try:
            btn = self.page.locator(self.SEL_SEARCH_BTN2)
            if btn.count() > 0:
                btn.first.evaluate("el => (el.closest('button,a') || el).click()")
        except Exception:
            pass
        self.page.wait_for_timeout(800)

    def select_by_name(self, name: str, mode: PickerMode,
                       search_term: str = "[AUTO") -> str:
        """검색 후 이름(두 번째 셀) **정확 일치** 행 선택 — fallback 금지(오선택 방지).
        미발견 시 raise — 호출측이 후보 순회/skip 판단. 확인(confirm)은 호출측 책임."""
        self.wait_open()
        self.search(search_term)
        rows = self.page.locator(self.SEL_ROW).all()
        for i, row in enumerate(rows):
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[1].inner_text().strip() == name:
                self.select_nth(i, mode)
                return name
        raise Exception(f"picker 검색 결과에 {name!r} 없음 (검색어 {search_term!r})")

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

    def select_nth_and_confirm(self, idx: int, mode: PickerMode) -> str:
        """N번째 행 선택 + 확인 → 선택된 행 텍스트 반환.

        용도 (sc3f Case7 / sc4l E — 2026-05-28 Chrome MCP 확정):
          한 정책 안 wr#2 에 wr#1 과 '다른' 프로세스 할당 필요. wr#1 이 idx=0 사용했으면
          wr#2 는 idx=1 사용. 동일 idx 재선택 시 제품이 silent 거부 + cross_instance
          알림 메시지 ('{name}은 이미 등록되어 있어 생략되었습니다.(타 웹제한 포함)').
        """
        self.wait_open()
        try:
            self.page.locator(self.SEL_ROW).first.wait_for(
                state="attached", timeout=3000
            )
        except Exception:
            pass
        cnt = self.get_row_count()
        if cnt <= idx:
            raise RuntimeError(f"ProcessPicker: 행 {cnt}건, idx={idx} 요청")
        text = self.page.locator(self.SEL_ROW).nth(idx).locator("td").nth(1).inner_text().strip()
        self.select_nth(idx, mode)
        self.confirm()
        self.wait_closed()
        return text
