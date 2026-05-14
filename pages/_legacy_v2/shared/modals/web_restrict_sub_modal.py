"""
pages/shared/modals/web_restrict_sub_modal.py — 공통 웹제한 sub-modal

대상 모달: div#controlSuiteWebRestricList   (제품 코드 typo: 'Restric')
호출처:
  - npouch_control_suite 메인 모달의 웹 제한기능 + 버튼
  - 메인 모달 itemWebRestrictList 행 클릭 시도 → EDIT 분기 없음 (ADD 흐름 그대로, 기존 값만 로드)

yaml 참조: config/scan_hints/control_suite.yaml — web_restrict_modal 섹션
inspection_notes:
  - web_restrict_no_edit_branch: 항상 ADD 흐름 — 제목 '웹 제한 목록 추가' / 빈값 '이름을 입력해 주세요.'
  - auth_text_sync_once_only: 권한 라디오 sync 첫 1회만 동작 (제품 buggy 확정)
  - allow_url_mode_combinations: 허용 URL + isFileUploadEncrypt 조합 가능 / 복호화 → enc 자동 disabled
  - description_server_limit_300: 1000자 입력 시 '설명의 입력 가능 글자수는 최대 300자 까지 가능합니다.'

설계 원칙:
  - 화면 순서대로 메서드 그룹
  - 권한 영역은 ▼ expand 사전조건 명시
  - isUrl 토글 종속 (isDataDecrypt + attachAllowUrl 4건) 동작 검증 헬퍼
"""
from playwright.sync_api import Page
from pages.shared._overlay import overlay_off


class WebRestrictSubModal:
    """controlSuiteWebRestricList — 웹제한 sub-modal (ADD/EDIT 분기 없음)."""

    # ------------------------------------------------------------------
    # Selectors (yaml web_restrict_modal 섹션)
    # ------------------------------------------------------------------
    SEL_MODAL              = "div#controlSuiteWebRestricList"
    SEL_MODAL_OPEN         = "div#controlSuiteWebRestricList.in"
    SEL_TITLE              = "div#controlSuiteWebRestricList .modal-title"

    # 웹 제한 이름
    SEL_NAME               = "div#controlSuiteWebRestricList #webRestrictName"

    # 적용 프로세스 영역
    SEL_ADD_PROCESS_BTN    = "div#controlSuiteWebRestricList #addWebRestrictProcess"
    SEL_PROCESS_TABLE_ROW  = "div#controlSuiteWebRestricList table tbody tr"
    SEL_BASE_PATH          = "div#controlSuiteWebRestricList #basePath"
    SEL_TOGGLE_PROC_OPT    = "div#controlSuiteWebRestricList #isProcessOption"

    # 권한 영역 (▼ expand 사전조건)
    SEL_EXPAND_BTN         = "div#controlSuiteWebRestricList #optionTextBtn"
    SEL_PROC_AUTH_TEXT     = "div#controlSuiteWebRestricList #processAuthText"
    SEL_OTHER_AUTH_TEXT    = "div#controlSuiteWebRestricList #otherFolderAccessAuthText"
    SEL_PROC_AUTH_DIV      = "#processAuthDiv"
    SEL_OTHER_AUTH_DIV     = "#otherFolderAccessAuthDiv"
    SEL_PROC_AUTH_RADIO    = "input[name='processAuth']"
    SEL_OTHER_AUTH_RADIO   = "input[name='otherFolderAccessAuth']"

    # 적용 URL 영역 (isUrl 토글 + 종속)
    SEL_TOGGLE_IS_URL      = "div#controlSuiteWebRestricList #isUrl"
    SEL_RADIO_DECRYPT_0    = "div#controlSuiteWebRestricList input[name='isDataDecrypt'][value='0']"
    SEL_RADIO_DECRYPT_1    = "div#controlSuiteWebRestricList input[name='isDataDecrypt'][value='1']"
    SEL_URL_INPUT          = "div#controlSuiteWebRestricList #attachAllowUrl"
    SEL_URL_ADD_BTN        = "div#controlSuiteWebRestricList #attachAllowUrlBtn"
    SEL_URL_LIST_TAG       = "div#controlSuiteWebRestricList button.tagInput"   # 컨테이너 별도 분리 필요 시 수정

    # 업로드 시 암호화
    SEL_FILE_ENCRYPT       = "div#controlSuiteWebRestricList #isFileUploadEncrypt"

    # 업로드 허용 확장자
    SEL_FILE_EXT_INPUT     = "div#controlSuiteWebRestricList #allowFileExtention"   # 제품 typo: Extention
    SEL_FILE_EXT_ADD       = "div#controlSuiteWebRestricList #addAllowFileExtention"

    # 헤더 체크 (독립)
    SEL_HEADER_CHECK       = "div#controlSuiteWebRestricList #isAllowFileHeaderCheck"

    # 업로드 제한용량
    SEL_UPLOAD_LIMIT       = "div#controlSuiteWebRestricList #uploadLimitSize"

    # 설명
    SEL_DESCRIPTION        = "div#controlSuiteWebRestricList #description"

    # 액션
    SEL_CONFIRM_BTN        = "div#controlSuiteWebRestricList .btn.btn-primary"
    SEL_CLOSE_BTN          = "div#controlSuiteWebRestricList .close"

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
        """항상 '웹 제한 목록 추가' (EDIT 분기 없음 — yaml inspection_notes 참조)."""
        loc = self.page.locator(self.SEL_TITLE).first
        return loc.inner_text().strip() if loc.count() > 0 else ""

    # ------------------------------------------------------------------
    # 웹 제한 이름
    # ------------------------------------------------------------------
    def set_name(self, name: str) -> None:
        self.page.locator(self.SEL_NAME).first.fill(name)

    def get_name(self) -> str:
        return self.page.locator(self.SEL_NAME).first.input_value()

    # ------------------------------------------------------------------
    # 적용 프로세스
    # ------------------------------------------------------------------
    def click_add_process_btn(self) -> None:
        """프로세스 추가 → globalProcessList (multi_select 모드) picker 호출."""
        self._click(self.page.locator(self.SEL_ADD_PROCESS_BTN).first)

    def get_process_rows(self) -> list[str]:
        """등록된 적용 프로세스 행 텍스트."""
        rows = self.page.locator(self.SEL_PROCESS_TABLE_ROW)
        return [rows.nth(i).inner_text().strip() for i in range(rows.count())]

    def set_base_path(self, text: str) -> None:
        self.page.locator(self.SEL_BASE_PATH).first.fill(text)

    def set_process_option_toggle(self, on: bool) -> None:
        """기본폴더 지정 토글 — UI disabled 영향 없는 저장 flag (inspection_notes)."""
        self._set_toggle(self.SEL_TOGGLE_PROC_OPT, on)

    # ------------------------------------------------------------------
    # 권한 영역 (▼ expand + 라디오)
    # ------------------------------------------------------------------
    def click_expand_btn(self) -> None:
        """▼ 클릭 → processAuthDiv / otherFolderAccessAuthDiv display:flex 전환."""
        self._click(self.page.locator(self.SEL_EXPAND_BTN).first)

    def is_auth_expanded(self) -> bool:
        """권한 라디오 영역이 펼쳐졌는지."""
        try:
            disp = self.page.locator(self.SEL_PROC_AUTH_DIV).first.evaluate(
                "el => window.getComputedStyle(el).display"
            )
            return disp != "none"
        except Exception:
            return False

    def set_process_auth(self, value: str) -> None:
        """
        기타 프로세스 권한 라디오 — value: '1'(거부) / '2'(읽기) / '3'(쓰기).
        ⚠ buggy: 첫 변경만 inline text sync, 두 번째부터 stuck (yaml auth_text_sync_once_only).
        """
        self._click(self.page.locator(f"{self.SEL_PROC_AUTH_RADIO}[value='{value}']").first)

    def set_other_folder_access_auth(self, value: str) -> None:
        """타폴더 접근권한 라디오 — value: '1'(거부) / '2'(읽기) / '3'(쓰기). (동일 buggy)"""
        self._click(self.page.locator(f"{self.SEL_OTHER_AUTH_RADIO}[value='{value}']").first)

    def get_process_auth_text(self) -> str:
        """span#processAuthText 의 현재 표시 텍스트 — buggy sync 검증용."""
        return self.page.locator(self.SEL_PROC_AUTH_TEXT).first.inner_text().strip()

    def get_other_auth_text(self) -> str:
        return self.page.locator(self.SEL_OTHER_AUTH_TEXT).first.inner_text().strip()

    # ------------------------------------------------------------------
    # 적용 URL 영역 (isUrl 토글 + 종속)
    # ------------------------------------------------------------------
    def set_is_url(self, on: bool) -> None:
        """isUrl 토글 — OFF: isDataDecrypt+attachAllowUrl+addBtn disabled / ON: 모두 활성."""
        self._set_toggle(self.SEL_TOGGLE_IS_URL, on)

    def click_decrypt_allow(self) -> None:
        """허용 URL (val=0) 라디오 — isFileUploadEncrypt 자유 체크 가능."""
        self._click(self.page.locator(self.SEL_RADIO_DECRYPT_0).first)

    def click_decrypt_target(self) -> None:
        """복호화 대상 지정 (val=1) → isFileUploadEncrypt 자동 체크 + disabled 강제."""
        self._click(self.page.locator(self.SEL_RADIO_DECRYPT_1).first)

    def add_url(self, url: str) -> None:
        """URL input + 추가. 형식 검증 없음 ('not a url' 도 등록됨)."""
        self.page.locator(self.SEL_URL_INPUT).first.fill(url)
        self._click(self.page.locator(self.SEL_URL_ADD_BTN).first)

    def get_url_list(self) -> list[str]:
        """등록된 URL 목록 (button.tagInput span 텍스트). 다른 tag_input 과 selector 겹침 주의."""
        # TODO: url list 전용 container selector 확정 시 좁힐 것
        items = self.page.locator(self.SEL_URL_LIST_TAG + " span")
        return [items.nth(i).inner_text().strip() for i in range(items.count())]

    # ------------------------------------------------------------------
    # 업로드 시 암호화 / 헤더 체크
    # ------------------------------------------------------------------
    def set_file_encrypt(self, on: bool) -> None:
        """isFileUploadEncrypt — isDataDecrypt=1 일 때 disabled 강제."""
        self._set_toggle(self.SEL_FILE_ENCRYPT, on)

    def is_file_encrypt_disabled(self) -> bool:
        return self.page.locator(self.SEL_FILE_ENCRYPT).first.is_disabled()

    def set_header_check(self, on: bool) -> None:
        """헤더 체크 기능 사용 — uploadLimitSize 와 독립."""
        self._set_toggle(self.SEL_HEADER_CHECK, on)

    # ------------------------------------------------------------------
    # 업로드 허용 확장자
    # ------------------------------------------------------------------
    def add_file_extension(self, ext: str) -> None:
        """업로드 허용 확장자 — ';' 다중 구분자 일괄 등록 가능."""
        self.page.locator(self.SEL_FILE_EXT_INPUT).first.fill(ext)
        self._click(self.page.locator(self.SEL_FILE_EXT_ADD).first)

    # ------------------------------------------------------------------
    # 업로드 제한용량
    # ------------------------------------------------------------------
    def set_upload_limit(self, value: str) -> None:
        """양의 정수 strict: 'abc' → '0', '-1' → '1', 9자리 OK."""
        self.page.locator(self.SEL_UPLOAD_LIMIT).first.fill(value)

    def get_upload_limit(self) -> str:
        return self.page.locator(self.SEL_UPLOAD_LIMIT).first.input_value()

    # ------------------------------------------------------------------
    # 설명
    # ------------------------------------------------------------------
    def set_description(self, text: str) -> None:
        """description — 서버 제한 300자 (yaml inspection_notes description_server_limit_300)."""
        self.page.locator(self.SEL_DESCRIPTION).first.fill(text)

    # ------------------------------------------------------------------
    # 액션
    # ------------------------------------------------------------------
    def confirm(self) -> None:
        """확인 → 메인 모달의 itemWebRestrictList 에 행 등록."""
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)

    def close(self) -> None:
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)

    # ------------------------------------------------------------------
    # 검증 헬퍼
    # ------------------------------------------------------------------
    def get_isurl_dependent_disabled(self) -> dict[str, bool]:
        """isUrl 토글 종속 4건 disabled 상태."""
        return {
            "isDataDecrypt_0":   self.page.locator(self.SEL_RADIO_DECRYPT_0).first.is_disabled(),
            "isDataDecrypt_1":   self.page.locator(self.SEL_RADIO_DECRYPT_1).first.is_disabled(),
            "attachAllowUrl":    self.page.locator(self.SEL_URL_INPUT).first.is_disabled(),
            "attachAllowUrlBtn": self.page.locator(self.SEL_URL_ADD_BTN).first.is_disabled(),
        }

    def get_verify_values(self) -> dict:
        """EDIT 재오픈 시 정합성 비교용."""
        return {
            "title":               self.get_title(),
            "name":                self.get_name(),
            "process_rows":        self.get_process_rows(),
            "process_auth_text":   self.get_process_auth_text(),
            "other_auth_text":     self.get_other_auth_text(),
            "is_url_checked":      self.page.locator(self.SEL_TOGGLE_IS_URL).first.is_checked(),
            "url_list":            self.get_url_list(),
            "file_encrypt":        self.page.locator(self.SEL_FILE_ENCRYPT).first.is_checked(),
            "file_encrypt_disabled": self.is_file_encrypt_disabled(),
            "header_check":        self.page.locator(self.SEL_HEADER_CHECK).first.is_checked(),
            "upload_limit":        self.get_upload_limit(),
            "description":         self.page.locator(self.SEL_DESCRIPTION).first.input_value(),
        }

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _set_toggle(self, selector: str, on: bool) -> None:
        cb = self.page.locator(selector).first
        if cb.is_checked() != on:
            self._click(cb)
