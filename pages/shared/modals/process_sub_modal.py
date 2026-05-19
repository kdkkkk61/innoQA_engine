"""
pages/shared/modals/process_sub_modal.py — 공통 프로세스/태그 등록 sub-modal

[Step 3a — 최소: 진입/탈출 + title/mode 감지]

대상 모달: div#controlSuiteProcessList
호출처: npouch_control_suite 메인 모달의 프로세스별 제어 + 버튼
모드 자동 감지:
  - process: pick_btn 텍스트 = '프로세스 선택'
  - tag:     pick_btn 텍스트 = '태그 선택'

이후 단계에서 picker 호출 / 필드 조작 / confirm 추가 예정.
"""
from typing import Literal
from playwright.sync_api import Page

from pages.shared._overlay import overlay_off


ProcessMode = Literal["process", "tag"]


class ProcessSubModal:
    """controlSuiteProcessList — 프로세스/태그 등록 sub-modal."""

    # ── Selectors ──────────────────────────────────────────────────
    SEL_MODAL          = "div#controlSuiteProcessList"
    SEL_MODAL_OPEN     = "div#controlSuiteProcessList.in"
    SEL_TITLE          = "div#controlSuiteProcessList .modal-title"

    # 프로세스/태그 선택 버튼 (모드 감지 + picker 호출)
    SEL_PICK_BTN           = "div#controlSuiteProcessList #csuProcessBtn"
    SEL_SELECTED_DISPLAY   = "div#controlSuiteProcessList #csuProcessName"
    # default text:
    #   process mode: '프로세스 미선택'
    #   tag mode:     '태그 미선택'

    # ── Step 3c 단독 토글 + 종속 영역 ──────────────────────────────
    SEL_TOGGLE_PROC_EXCEPT       = "div#controlSuiteProcessList #isProcessExcept"
    SEL_TOGGLE_PCLIPBOARD        = "div#controlSuiteProcessList #isPClipboardRestrict"
    SEL_TOGGLE_SANDBOX           = "div#controlSuiteProcessList #isSandbox"
    SEL_TOGGLE_DENY_EXCEPT_DRIVE = "div#controlSuiteProcessList #isDenyExceptDrive"

    # isPNetwork + 종속
    SEL_TOGGLE_PNETWORK    = "div#controlSuiteProcessList #isPNetwork"
    SEL_IP_INPUT           = "div#controlSuiteProcessList #accessAllowIp"
    SEL_PORT_INPUT         = "div#controlSuiteProcessList #accessAllowPort"
    SEL_IP_ADD_BTN         = "div#controlSuiteProcessList #allowIpAddressBtn"
    # IP/Port list 행 — visible 만 매칭 (삭제 후 display:none 으로 잔류 — Chrome MCP 2026-05-19 검증)
    SEL_IP_LIST_ITEM       = "div#controlSuiteProcessList #allowIpAddressList li:visible"
    # 행 내부 삭제 버튼 — class 'deleteBtn' (id 는 모든 행에 중복) — Chrome MCP 2026-05-19 검증
    SEL_IP_DELETE_BTN      = "button.deleteBtn"

    # isPControlExtension + 종속 (라디오 + 확장자 input/list)
    SEL_TOGGLE_PCONTROL_EXT = "div#controlSuiteProcessList #isPControlExtension"
    SEL_RADIO_ALLOWP        = "div#controlSuiteProcessList #ALLOWP"
    SEL_RADIO_BLOCKP        = "div#controlSuiteProcessList #BLOCKP"
    SEL_RADIO_REACT_SPAN    = "div#controlSuiteProcessList #allowExtensionTextP"
    SEL_EXT_INPUT_P         = "div#controlSuiteProcessList #allowExtensionInputP"
    SEL_EXT_ADD_P           = "div#controlSuiteProcessList #allowExtensionInputBtnP"
    SEL_EXT_LIST_TAG_P      = "div#controlSuiteProcessList #allowExtensionUlP button.tagInput:visible"

    # cache_folder_section (contenteditable div input + 특수폴더 + 추가 + list)
    SEL_CACHE_INPUT         = "div#controlSuiteProcessList #cacheFolderInput"
    SEL_CACHE_SPECIAL_BTN   = "div#controlSuiteProcessList button.specialFolderBtn"
    SEL_CACHE_ADD_BTN       = "div#controlSuiteProcessList #attachCacheFolderBtn"
    SEL_CACHE_LIST          = "div#controlSuiteProcessList #cacheFolderList"
    SEL_CACHE_LIST_ITEM_BTN = "div#controlSuiteProcessList #cacheFolderList button[contents-list-item]"

    # isAccessDrive + 종속
    SEL_TOGGLE_ACCESS_DRIVE = "div#controlSuiteProcessList #isAccessDrive"
    SEL_DRIVE_LETTER        = "div#controlSuiteProcessList #accessDriveLetter"

    # description
    SEL_DESCRIPTION         = "div#controlSuiteProcessList #description"

    # 액션
    SEL_CONFIRM_BTN    = "div#controlSuiteProcessList .btn.btn-primary"
    SEL_CLOSE_BTN      = "div#controlSuiteProcessList .close"
    SEL_CANCEL_BTN     = "div#controlSuiteProcessList .btn.btn-default"

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
        """hidden input (Bootstrap toggle checkbox / 라디오) — JS evaluate."""
        locator.evaluate("el => el.click()")

    def _set_toggle(self, selector: str, on: bool) -> None:
        cb = self.page.locator(selector).first
        if cb.is_checked() != on:
            self._click_hidden(cb)

    # ── 상태 / 진입 ────────────────────────────────────────────────
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

    def detect_mode(self) -> ProcessMode:
        """pick_btn 텍스트로 모드 감지 — '태그 선택' 포함 시 tag."""
        txt = self.page.locator(self.SEL_PICK_BTN).first.inner_text().strip()
        return "tag" if "태그" in txt else "process"

    def get_pick_btn_text(self) -> str:
        return self.page.locator(self.SEL_PICK_BTN).first.inner_text().strip()

    # ── 프로세스/태그 선택 picker 호출 + 선택값 표시 (Step 3b) ────
    def click_pick_btn(self) -> None:
        """'프로세스 선택' or '태그 선택' 클릭 → globalProcessList picker 호출."""
        self._click(self.page.locator(self.SEL_PICK_BTN).first)

    def get_selected_display_text(self) -> str:
        """span#csuProcessName — 현재 선택된 프로세스/태그명 또는 '미선택' 텍스트."""
        return self.page.locator(self.SEL_SELECTED_DISPLAY).first.inner_text().strip()

    # ──────────────────────────────────────────────────────────────
    # Step 3c — 필드 메서드
    # ──────────────────────────────────────────────────────────────

    # ── 단독 토글 ──────────────────────────────────────────────────
    def set_process_except(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PROC_EXCEPT, on)

    def set_pclipboard_restrict(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PCLIPBOARD, on)

    def set_sandbox(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_SANDBOX, on)

    def set_deny_except_drive(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_DENY_EXCEPT_DRIVE, on)

    def is_toggle_checked(self, selector: str) -> bool:
        return self.page.locator(selector).first.is_checked()

    # ── 네트워크 허용 (isPNetwork + IP/Port) ────────────────────────
    def set_pnetwork(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PNETWORK, on)

    def add_ip_port(self, ip: str, port: str) -> None:
        """IP + Port 입력 후 '추가'. 검증 메시지는 호출자가 처리."""
        self.page.locator(self.SEL_IP_INPUT).first.fill(ip)
        self.page.locator(self.SEL_PORT_INPUT).first.fill(port)
        self._click(self.page.locator(self.SEL_IP_ADD_BTN).first)

    def get_ip_list(self) -> list[str]:
        items = self.page.locator(self.SEL_IP_LIST_ITEM)
        return [items.nth(i).inner_text().strip() for i in range(items.count())]

    def remove_ip_port(self, ip: str, port: str) -> bool:
        """IP/Port list 행 삭제. 성공 시 True.

        Chrome MCP 2026-05-19 검증 결과:
          - DOM: `<li><span data-access-allow-ip-address>...<button class='deleteBtn'>`
          - 삭제 핸들러는 **trusted event 만 받음** — JS `el.click()`, `dispatchEvent`
            모두 미발화. Playwright `locator.click()` (CDP trusted) 정답.
          - 삭제 후 li 는 DOM 잔류 + `display:none` 처리 → list selector 에 `:visible` 필수.
        """
        items = self.page.locator(self.SEL_IP_LIST_ITEM)
        cnt = items.count()
        for i in range(cnt):
            text = items.nth(i).inner_text()
            if ip in text and port in text:
                del_btn = items.nth(i).locator(self.SEL_IP_DELETE_BTN).first
                with overlay_off(self.page):
                    del_btn.click()
                return True
        return False

    # ── 확장자 제어 (isPControlExtension + 라디오 + tag) ──────────
    def set_pcontrol_extension(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PCONTROL_EXT, on)

    def click_radio_allowp(self) -> None:
        """ALLOWP (대상 지정) → span '차단할 확장자' redTxt"""
        self._click_hidden(self.page.locator(self.SEL_RADIO_ALLOWP).first)

    def click_radio_blockp(self) -> None:
        """BLOCKP (전체 차단) → span '허용할 확장자' blueTxt"""
        self._click_hidden(self.page.locator(self.SEL_RADIO_BLOCKP).first)

    def get_radio_react_text(self) -> str:
        return self.page.locator(self.SEL_RADIO_REACT_SPAN).first.inner_text().strip()

    def add_extension(self, ext: str) -> None:
        """확장자 input + '추가'. ';' 다중 구분자 일괄 등록."""
        self.page.locator(self.SEL_EXT_INPUT_P).first.fill(ext)
        self._click(self.page.locator(self.SEL_EXT_ADD_P).first)

    def get_extension_list(self) -> list[str]:
        items = self.page.locator(self.SEL_EXT_LIST_TAG_P + " span")
        return [
            items.nth(i).inner_text().strip().split()[0]
            for i in range(items.count())
        ]

    def remove_extension(self, ext: str) -> bool:
        """process_modal 확장자 tag × 삭제. 성공 시 True.

        yaml :331 verified + Chrome MCP 2026-05-19 직접 인용:
          DOM: `<span>txt<i class="extentionDeleteBtnP fa fa-times"></i></span>`
          → **P 접미사** (메인 확장자의 `extentionDeleteBtn` 과 구분).
        """
        tags = self.page.locator(self.SEL_EXT_LIST_TAG_P)
        cnt = tags.count()
        for i in range(cnt):
            text = tags.nth(i).inner_text().strip()
            if text.startswith(ext + " ") or text == ext or text.split()[0] == ext:
                sub = tags.nth(i).locator("i.extentionDeleteBtnP")
                if sub.count() == 0:
                    return False
                sub.first.evaluate("el => el.click()")
                return True
        return False

    # ── 캐시폴더 (contenteditable div + 특수폴더 picker + 추가) ───
    def set_cache_input(self, text: str) -> None:
        """
        cacheFolderInput 은 <div contenteditable=true> — 일반 fill 불가.
        innerText 직접 설정 + input 이벤트 dispatch.
        """
        ci = self.page.locator(self.SEL_CACHE_INPUT).first
        ci.evaluate(
            "(el, text) => { el.innerText = text; "
            "el.dispatchEvent(new Event('input', {bubbles: true})); }",
            text,
        )

    def get_cache_input_text(self) -> str:
        return self.page.locator(self.SEL_CACHE_INPUT).first.inner_text().strip()

    def click_special_folder_btn(self) -> None:
        """'특수폴더' 버튼 → selectReservedWordControl picker 호출."""
        self._click(self.page.locator(self.SEL_CACHE_SPECIAL_BTN).first)

    def click_cache_add_btn(self) -> None:
        """'추가' → cacheFolderInput 의 inline tag/text 를 cacheFolderList 로 이동."""
        self._click(self.page.locator(self.SEL_CACHE_ADD_BTN).first)

    def get_cache_folder_list(self) -> list[str]:
        """
        cacheFolderList 의 button[contents-list-item] 의 data-cache-folder 속성값 목록.
        특수폴더 다중 선택 케이스에서는 코드들이 1건으로 병합되어 등록됨 (yaml line 197-198).
        """
        items = self.page.locator(self.SEL_CACHE_LIST_ITEM_BTN)
        out: list[str] = []
        for i in range(items.count()):
            v = items.nth(i).get_attribute("data-cache-folder")
            if v is None:
                # 내부 span 의 data-cache-folder fallback
                inner = items.nth(i).locator("[data-cache-folder]").first
                v = inner.get_attribute("data-cache-folder") if inner.count() > 0 else None
            if v is not None:
                out.append(v)
        return out

    # ── 접근 드라이브 ───────────────────────────────────────────────
    def set_access_drive(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_ACCESS_DRIVE, on)

    def set_drive_letter(self, value: str) -> None:
        """'C;D;E' 형식."""
        self.page.locator(self.SEL_DRIVE_LETTER).first.fill(value)

    def get_drive_letter(self) -> str:
        return self.page.locator(self.SEL_DRIVE_LETTER).first.input_value()

    # ── 설명 ────────────────────────────────────────────────────────
    def set_description(self, text: str) -> None:
        self.page.locator(self.SEL_DESCRIPTION).first.fill(text)

    def get_description(self) -> str:
        return self.page.locator(self.SEL_DESCRIPTION).first.input_value()

    # ──────────────────────────────────────────────────────────────
    # 저장 / 닫기
    # ──────────────────────────────────────────────────────────────
    def confirm(self) -> None:
        """'확인' 버튼 → 메인 모달의 itemList (or itemTagList) 에 행 등록 + 모달 닫힘."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)
        self.wait_closed()

    def close(self) -> None:
        """× 버튼 클릭 → 모달 detached 대기 (저장 안 함)."""
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)
        self.wait_closed()
