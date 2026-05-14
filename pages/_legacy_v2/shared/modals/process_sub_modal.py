"""
pages/shared/modals/process_sub_modal.py — 공통 프로세스 등록 sub-modal

대상 모달: div#controlSuiteProcessList
호출처:
  - npouch_control_suite 메인 모달의 프로세스별 제어 + 버튼
  - (향후) 시큐어존 등 동일 모달 사용 페이지

모달은 메인 모달의 '개별 프로세스' / '태그' sub-tab 활성 상태에 따라 모드 변경:
  - process_mode: 라벨 '프로세스명 *', pick_btn 텍스트 '프로세스 선택'
  - tag_mode:     라벨 '태그명 *',     pick_btn 텍스트 '태그 선택'

yaml 참조: config/scan_hints/control_suite.yaml — process_modal 섹션 + cache_folder_section

설계 원칙:
  - 14 필드 + cache_folder + 권한 영역을 메서드 그룹으로 정리
  - 화면 순서대로 메서드 배열 (yaml process_modal.fields 주석 일치)
  - picker / special_folder 는 page 의 composition 으로 호출자가 주입
  - inspection_notes 의 buggy 패턴은 메서드 docstring 에 명시
"""
from typing import Literal
from playwright.sync_api import Page
from pages.shared._overlay import overlay_off


ProcessMode = Literal["process", "tag"]


class ProcessSubModal:
    """controlSuiteProcessList — 개별 프로세스/태그 등록 sub-modal."""

    # ------------------------------------------------------------------
    # Selectors (yaml process_modal 섹션과 동기화)
    # ------------------------------------------------------------------
    SEL_MODAL              = "div#controlSuiteProcessList"
    SEL_MODAL_OPEN         = "div#controlSuiteProcessList.in"
    SEL_TITLE              = "div#controlSuiteProcessList .modal-title"

    # 프로세스/태그 선택 (모드 토글 — 텍스트만 변경, selector 동일)
    SEL_PICK_BTN           = "div#controlSuiteProcessList #csuProcessBtn"
    SEL_SELECTED_DISPLAY   = "div#controlSuiteProcessList #csuProcessName"
    # selected_display default text — 'process_modal.selected_display.default_text'
    #   process_mode: '프로세스 미선택'
    #   tag_mode:     '태그 미선택'

    # 단독 토글
    SEL_TOGGLE_PROC_EXCEPT       = "div#controlSuiteProcessList #isProcessExcept"
    SEL_TOGGLE_PCLIPBOARD        = "div#controlSuiteProcessList #isPClipboardRestrict"
    SEL_TOGGLE_SANDBOX           = "div#controlSuiteProcessList #isSandbox"
    SEL_TOGGLE_DENY_EXCEPT_DRIVE = "div#controlSuiteProcessList #isDenyExceptDrive"

    # isPNetwork + 종속 (IP/Port + 추가 + list)
    SEL_TOGGLE_PNETWORK    = "div#controlSuiteProcessList #isPNetwork"
    SEL_IP_INPUT           = "div#controlSuiteProcessList #accessAllowIp"
    SEL_PORT_INPUT         = "div#controlSuiteProcessList #accessAllowPort"
    SEL_IP_ADD_BTN         = "div#controlSuiteProcessList #allowIpAddressBtn"
    SEL_IP_LIST            = "div#controlSuiteProcessList #allowIpAddressList"
    SEL_IP_LIST_ITEM       = "div#controlSuiteProcessList #allowIpAddressList li"

    # isPControlExtension + 종속 (라디오 + 확장자 input + list)
    SEL_TOGGLE_PCONTROL_EXT = "div#controlSuiteProcessList #isPControlExtension"
    SEL_RADIO_ALLOWP        = "div#controlSuiteProcessList #ALLOWP"
    SEL_RADIO_BLOCKP        = "div#controlSuiteProcessList #BLOCKP"
    SEL_RADIO_REACT_SPAN    = "div#controlSuiteProcessList #allowExtensionTextP"
    SEL_EXT_INPUT_P         = "div#controlSuiteProcessList #allowExtensionInputP"
    SEL_EXT_ADD_P           = "div#controlSuiteProcessList #allowExtensionInputBtnP"
    SEL_EXT_LIST_P          = "div#controlSuiteProcessList #allowExtensionUlP"
    SEL_EXT_LIST_TAG_P      = "div#controlSuiteProcessList #allowExtensionUlP button.tagInput"
    SEL_EXT_DELETE_ICON_P   = "div#controlSuiteProcessList i.extentionDeleteBtnP"

    # 캐시폴더 (cache_folder_section)
    SEL_CACHE_INPUT         = "div#controlSuiteProcessList #cacheFolderInput"
    SEL_CACHE_SPECIAL_BTN   = "div#controlSuiteProcessList button.specialFolderBtn"
    SEL_CACHE_ADD_BTN       = "div#controlSuiteProcessList #attachCacheFolderBtn"
    SEL_CACHE_LIST          = "div#controlSuiteProcessList #cacheFolderList"
    SEL_CACHE_LIST_ITEM     = "div#controlSuiteProcessList #cacheFolderList button.tagInput"
    SEL_CACHE_DELETE_ICON   = "div#controlSuiteProcessList i.folderDeleteBtn"

    # isAccessDrive + 종속
    SEL_TOGGLE_ACCESS_DRIVE = "div#controlSuiteProcessList #isAccessDrive"
    SEL_DRIVE_LETTER        = "div#controlSuiteProcessList #accessDriveLetter"

    # description
    SEL_DESCRIPTION         = "div#controlSuiteProcessList #description"

    # 액션
    SEL_CONFIRM_BTN         = "div#controlSuiteProcessList .btn.btn-primary"
    SEL_CLOSE_BTN           = "div#controlSuiteProcessList .close"

    _TIMEOUT_OPEN           = 3000
    _TIMEOUT_CLOSE          = 3000

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
    # 상태 / 진입
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

    def detect_mode(self) -> ProcessMode:
        """버튼 텍스트로 현재 모드 감지 — '프로세스 선택' or '태그 선택'."""
        txt = self.page.locator(self.SEL_PICK_BTN).first.inner_text().strip()
        if "태그" in txt:
            return "tag"
        return "process"

    def get_selected_display_text(self) -> str:
        """span#csuProcessName 의 현재 텍스트 (선택된 프로세스/태그명 또는 '미선택')."""
        return self.page.locator(self.SEL_SELECTED_DISPLAY).first.inner_text().strip()

    # ------------------------------------------------------------------
    # 프로세스/태그 선택
    # ------------------------------------------------------------------
    def click_pick_btn(self) -> None:
        """'프로세스 선택' or '태그 선택' 버튼 클릭 → globalProcessList picker 호출."""
        self._click(self.page.locator(self.SEL_PICK_BTN).first)

    # ------------------------------------------------------------------
    # 단독 토글
    # ------------------------------------------------------------------
    def set_process_except(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PROC_EXCEPT, on)

    def set_pclipboard_restrict(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PCLIPBOARD, on)

    def set_sandbox(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_SANDBOX, on)

    def set_deny_except_drive(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_DENY_EXCEPT_DRIVE, on)

    # ------------------------------------------------------------------
    # 네트워크 허용 영역 (isPNetwork + IP/Port)
    # ------------------------------------------------------------------
    def set_pnetwork(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PNETWORK, on)

    def add_ip_port(self, ip: str, port: str) -> None:
        """IP + Port 입력 후 '추가' — 검증 메시지는 호출자가 dismiss."""
        self.page.locator(self.SEL_IP_INPUT).first.fill(ip)
        self.page.locator(self.SEL_PORT_INPUT).first.fill(port)
        self._click(self.page.locator(self.SEL_IP_ADD_BTN).first)

    def get_ip_list(self) -> list[str]:
        """IP+Port list 항목 텍스트."""
        items = self.page.locator(self.SEL_IP_LIST_ITEM)
        return [items.nth(i).inner_text().strip() for i in range(items.count())]

    # ------------------------------------------------------------------
    # 제어할 확장자 (개별) 영역 (isPControlExtension + 라디오 + 확장자)
    # ------------------------------------------------------------------
    def set_pcontrol_extension(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_PCONTROL_EXT, on)

    def click_radio_allowp(self) -> None:
        """ALLOWP (확장자 대상지정) → span = '차단할 확장자' wid80 redTxt"""
        self._click(self.page.locator(self.SEL_RADIO_ALLOWP).first)

    def click_radio_blockp(self) -> None:
        """BLOCKP (확장자 전체차단) → span = '허용할 확장자' wid80 blueTxt"""
        self._click(self.page.locator(self.SEL_RADIO_BLOCKP).first)

    def get_radio_react_span(self) -> tuple[str, str]:
        """현재 span#allowExtensionTextP 의 텍스트 + class. 라디오 반응 검증용."""
        span = self.page.locator(self.SEL_RADIO_REACT_SPAN).first
        return span.inner_text().strip(), span.get_attribute("class") or ""

    def add_extension(self, ext: str) -> None:
        """확장자 input + '추가'. ";" 다중 구분자 일괄 등록 가능 (예: 'txt;doc;exe')."""
        self.page.locator(self.SEL_EXT_INPUT_P).first.fill(ext)
        self._click(self.page.locator(self.SEL_EXT_ADD_P).first)

    def get_extension_list(self) -> list[str]:
        """등록된 확장자 list 의 span 텍스트 (분리된 코드 목록)."""
        items = self.page.locator(self.SEL_EXT_LIST_TAG_P + " span")
        return [items.nth(i).inner_text().strip().split()[0] for i in range(items.count())]

    def delete_extension(self, ext: str) -> None:
        """list 안 ext 항목의 삭제 아이콘 클릭."""
        btn = self.page.locator(self.SEL_EXT_LIST_TAG_P).filter(has_text=ext).first
        self._click(btn.locator("i").first)

    # ------------------------------------------------------------------
    # 캐시폴더 영역 (cache_folder_section)
    # ------------------------------------------------------------------
    def set_cache_input(self, text: str) -> None:
        """contenteditable DIV — innerText 직접 설정 + input 이벤트."""
        # Playwright fill 은 contenteditable 도 지원 (실험적), 안전하게 evaluate 사용
        ci = self.page.locator(self.SEL_CACHE_INPUT).first
        self._click(ci)
        ci.evaluate(
            "(el, text) => { el.innerText = text; el.dispatchEvent(new Event('input', {bubbles: true})); }",
            text,
        )

    def click_special_folder_btn(self) -> None:
        """'특수폴더' 버튼 → selectReservedWordControl picker 호출."""
        self._click(self.page.locator(self.SEL_CACHE_SPECIAL_BTN).first)

    def click_cache_add_btn(self) -> None:
        """'추가' 버튼 → cacheFolderInput 의 inline tag 를 cacheFolderList 로 이동."""
        self._click(self.page.locator(self.SEL_CACHE_ADD_BTN).first)

    def get_cache_folder_list(self) -> list[str]:
        """등록된 cache_folder data-cache-folder 속성 목록 (병합된 단일 문자열 포함)."""
        items = self.page.locator(self.SEL_CACHE_LIST_ITEM + " span")
        out: list[str] = []
        for i in range(items.count()):
            v = items.nth(i).get_attribute("data-cache-folder")
            if v is not None:
                out.append(v)
        return out

    def delete_cache_folder(self, value: str) -> None:
        """data-cache-folder 일치 항목 삭제."""
        item = self.page.locator(
            f"{self.SEL_CACHE_LIST_ITEM} span[data-cache-folder='{value}']"
        ).first
        self._click(item.locator("i.folderDeleteBtn").first)

    # ------------------------------------------------------------------
    # 접근 드라이브
    # ------------------------------------------------------------------
    def set_access_drive(self, on: bool) -> None:
        self._set_toggle(self.SEL_TOGGLE_ACCESS_DRIVE, on)

    def set_drive_letter(self, value: str) -> None:
        """드라이브 레터 'C;D;E' 형식."""
        self.page.locator(self.SEL_DRIVE_LETTER).first.fill(value)

    # ------------------------------------------------------------------
    # 설명
    # ------------------------------------------------------------------
    def set_description(self, text: str) -> None:
        """description (textarea) — 서버 제한 300자 (시나리오 3-B inspection)."""
        self.page.locator(self.SEL_DESCRIPTION).first.fill(text)

    # ------------------------------------------------------------------
    # 액션
    # ------------------------------------------------------------------
    def confirm(self) -> None:
        """확인 → 메인 모달 itemList / itemTagList 에 행 등록 (모드별)."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)

    def close(self) -> None:
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)

    # ------------------------------------------------------------------
    # 검증 헬퍼
    # ------------------------------------------------------------------
    def get_toggle_states(self) -> dict[str, bool]:
        """모든 토글 checked 상태."""
        return {
            "isProcessExcept":       self.page.locator(self.SEL_TOGGLE_PROC_EXCEPT).first.is_checked(),
            "isPClipboardRestrict":  self.page.locator(self.SEL_TOGGLE_PCLIPBOARD).first.is_checked(),
            "isPNetwork":            self.page.locator(self.SEL_TOGGLE_PNETWORK).first.is_checked(),
            "isPControlExtension":   self.page.locator(self.SEL_TOGGLE_PCONTROL_EXT).first.is_checked(),
            "isSandbox":             self.page.locator(self.SEL_TOGGLE_SANDBOX).first.is_checked(),
            "isAccessDrive":         self.page.locator(self.SEL_TOGGLE_ACCESS_DRIVE).first.is_checked(),
            "isDenyExceptDrive":     self.page.locator(self.SEL_TOGGLE_DENY_EXCEPT_DRIVE).first.is_checked(),
        }

    def get_dependent_disabled_states(self) -> dict[str, bool]:
        """종속 필드 disabled 상태 (yaml dependent_controls 검증)."""
        return {
            "accessAllowIp":          self.page.locator(self.SEL_IP_INPUT).first.is_disabled(),
            "accessAllowPort":        self.page.locator(self.SEL_PORT_INPUT).first.is_disabled(),
            "allowIpAddressBtn":      self.page.locator(self.SEL_IP_ADD_BTN).first.is_disabled(),
            "ALLOWP":                 self.page.locator(self.SEL_RADIO_ALLOWP).first.is_disabled(),
            "BLOCKP":                 self.page.locator(self.SEL_RADIO_BLOCKP).first.is_disabled(),
            "allowExtensionInputP":   self.page.locator(self.SEL_EXT_INPUT_P).first.is_disabled(),
            "accessDriveLetter":      self.page.locator(self.SEL_DRIVE_LETTER).first.is_disabled(),
        }

    def get_verify_values(self) -> dict:
        """EDIT 재오픈 시 정합성 비교용 — yaml 4-1 책임."""
        return {
            "title":                  self.get_title(),
            "mode":                   self.detect_mode(),
            "selected_display":       self.get_selected_display_text(),
            "toggles":                self.get_toggle_states(),
            "ip_list":                self.get_ip_list(),
            "extension_list":         self.get_extension_list(),
            "cache_folder_list":      self.get_cache_folder_list(),
            "radio_react_span_text":  self.get_radio_react_span()[0],
            "drive_letter":           self.page.locator(self.SEL_DRIVE_LETTER).first.input_value(),
            "description":            self.page.locator(self.SEL_DESCRIPTION).first.input_value(),
        }

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _set_toggle(self, selector: str, on: bool) -> None:
        cb = self.page.locator(selector).first
        if cb.is_checked() != on:
            self._click(cb)
