"""
pages/shared/modals/web_restrict_sub_modal.py — 웹 제한 sub-modal

[Step 4a — 최소: 진입/탈출 + name 필드]

대상 모달: div#controlSuiteWebRestricList
  ⚠ 제품 코드 typo: 'Restric' (정상 표기는 'Restrict'). yaml 에 사실 그대로 기록.

호출처: npouch_control_suite 메인 모달의 '웹 제한기능' + 버튼

이후 단계 (Step 4b~4c) 에서 추가 예정:
  - 프로세스 추가 picker (multi 모드)
  - 기본폴더 / 권한 expand + 라디오
  - isUrl + isDataDecrypt + URL list
  - isFileUploadEncrypt + 헤더체크 + 확장자 + 제한용량
  - description / confirm (등록)

inspection_notes (yaml):
  - auth_text_sync_once_only: 권한 라디오 sync 첫 1회만 (제품 buggy)
  - AngularJS ng-change: Playwright trusted click 만 sync 발화
"""
from playwright.sync_api import Page

from pages.shared._overlay import overlay_off


class WebRestrictSubModal:
    """controlSuiteWebRestricList — 웹제한 sub-modal."""

    # ── Selectors ──────────────────────────────────────────────────
    SEL_MODAL          = "div#controlSuiteWebRestricList"
    SEL_MODAL_OPEN     = "div#controlSuiteWebRestricList.in"
    SEL_TITLE          = "div#controlSuiteWebRestricList .modal-title"

    # 웹 제한 이름
    SEL_NAME           = "div#controlSuiteWebRestricList #webRestrictName"

    # ── 적용 프로세스 영역 (Step 4b) ───────────────────────────────
    SEL_ADD_PROCESS_BTN    = "div#controlSuiteWebRestricList #addWebRestrictProcess"
    SEL_PROCESS_TABLE_ROW  = "div#controlSuiteWebRestricList table tbody tr"
    SEL_BASE_PATH          = "div#controlSuiteWebRestricList #basePath"
    SEL_TOGGLE_PROC_OPT    = "div#controlSuiteWebRestricList #isProcessOption"

    # ── 권한 영역 (▼ expand + 라디오 + inline text) (Step 4c) ────
    SEL_EXPAND_BTN         = "div#controlSuiteWebRestricList #optionTextBtn"
    SEL_PROC_AUTH_TEXT     = "div#controlSuiteWebRestricList #processAuthText"
    SEL_OTHER_AUTH_TEXT    = "div#controlSuiteWebRestricList #otherFolderAccessAuthText"
    SEL_PROC_AUTH_DIV      = "div#controlSuiteWebRestricList #processAuthDiv"
    SEL_OTHER_AUTH_DIV     = "div#controlSuiteWebRestricList #otherFolderAccessAuthDiv"
    SEL_PROC_AUTH_RADIO    = "div#controlSuiteWebRestricList input[name='processAuth']"
    SEL_OTHER_AUTH_RADIO   = "div#controlSuiteWebRestricList input[name='otherFolderAccessAuth']"

    # ── 적용 URL 영역 (isUrl 토글 + 종속) (Step 4c) ───────────────
    SEL_TOGGLE_IS_URL      = "div#controlSuiteWebRestricList #isUrl"
    SEL_RADIO_DECRYPT_0    = "div#controlSuiteWebRestricList input[name='isDataDecrypt'][value='0']"
    SEL_RADIO_DECRYPT_1    = "div#controlSuiteWebRestricList input[name='isDataDecrypt'][value='1']"
    SEL_URL_INPUT          = "div#controlSuiteWebRestricList #attachAllowUrl"
    SEL_URL_ADD_BTN        = "div#controlSuiteWebRestricList #attachAllowUrlBtn"
    # URL tag — 부모 `div#allowUrl`, 삭제 후 display:none 잔류 → :visible 필수 (Chrome MCP 2026-05-19 검증)
    SEL_URL_LIST_TAG       = "div#controlSuiteWebRestricList div#allowUrl button.tagInput:visible"
    # 확장자 tag — 부모 `div#extension`, 삭제 후 display:none 잔류 → :visible 필수 (Chrome MCP 2026-05-19 검증)
    SEL_FILE_EXT_LIST_TAG  = "div#controlSuiteWebRestricList div#extension button.tagInput:visible"

    # ── 업로드 시 암호화 / 헤더 체크 (Step 4c) ────────────────────
    SEL_FILE_ENCRYPT       = "div#controlSuiteWebRestricList #isFileUploadEncrypt"
    SEL_HEADER_CHECK       = "div#controlSuiteWebRestricList #isAllowFileHeaderCheck"

    # ── 업로드 허용 확장자 (제품 typo: Extention) (Step 4c) ───────
    SEL_FILE_EXT_INPUT     = "div#controlSuiteWebRestricList #allowFileExtention"
    SEL_FILE_EXT_ADD       = "div#controlSuiteWebRestricList #addAllowFileExtention"

    # ── 업로드 제한용량 (Step 4c) ─────────────────────────────────
    SEL_UPLOAD_LIMIT       = "div#controlSuiteWebRestricList #uploadLimitSize"

    # ── 설명 (Step 4c) ────────────────────────────────────────────
    SEL_DESCRIPTION        = "div#controlSuiteWebRestricList #description"

    # 액션
    SEL_CONFIRM_BTN    = "div#controlSuiteWebRestricList .btn.btn-primary"
    SEL_CLOSE_BTN      = "div#controlSuiteWebRestricList .close"

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
        """hidden input (Bootstrap toggle/라디오) — JS evaluate."""
        locator.evaluate("el => el.click()")

    def _set_toggle(self, selector: str, on: bool) -> None:
        cb = self.page.locator(selector).first
        if cb.is_checked() != on:
            self._click_hidden(cb)

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
        """항상 '웹 제한 목록 추가' (yaml inspection_notes: EDIT 분기 없음)."""
        return self.page.locator(self.SEL_TITLE).first.inner_text().strip()

    # ── 웹 제한 이름 ────────────────────────────────────────────────
    def set_name(self, name: str) -> None:
        self.page.locator(self.SEL_NAME).first.fill(name)

    def get_name(self) -> str:
        return self.page.locator(self.SEL_NAME).first.input_value()

    # ──────────────────────────────────────────────────────────────
    # Step 4b — 적용 프로세스 영역 (process_picker multi 호출)
    # ──────────────────────────────────────────────────────────────
    def click_add_process_btn(self) -> None:
        """'프로세스 추가' 클릭 → globalProcessList picker 호출 (multi 모드)."""
        self._click(self.page.locator(self.SEL_ADD_PROCESS_BTN).first)

    def get_process_rows(self) -> list[str]:
        """적용 프로세스 테이블의 행 텍스트 (Header 행 제외)."""
        rows = self.page.locator(self.SEL_PROCESS_TABLE_ROW)
        out: list[str] = []
        for i in range(rows.count()):
            txt = rows.nth(i).inner_text().strip()
            if txt and "없습니다" not in txt:
                out.append(txt)
        return out

    def set_base_path(self, text: str) -> None:
        self.page.locator(self.SEL_BASE_PATH).first.fill(text)

    def get_base_path(self) -> str:
        return self.page.locator(self.SEL_BASE_PATH).first.input_value()

    def set_process_option(self, on: bool) -> None:
        """기본폴더 지정 토글. ON 상태여야 ▼ expand 활성 (yaml 사전조건)."""
        self._set_toggle(self.SEL_TOGGLE_PROC_OPT, on)

    def is_process_option_checked(self) -> bool:
        return self.page.locator(self.SEL_TOGGLE_PROC_OPT).first.is_checked()

    # ──────────────────────────────────────────────────────────────
    # Step 4c — 권한 영역 (▼ expand + 2 라디오 그룹 + inline text sync)
    # ──────────────────────────────────────────────────────────────
    def click_expand_btn(self) -> None:
        """▼ 클릭 → processAuthDiv/otherFolderAccessAuthDiv display:none→flex.
        ⚠ yaml 사전조건: isProcessOption ON 상태여야 expand 활성.
        """
        self._click(self.page.locator(self.SEL_EXPAND_BTN).first)

    def is_auth_expanded(self) -> bool:
        """권한 라디오 영역 펼침 여부 (computedStyle.display)."""
        try:
            disp = self.page.locator(self.SEL_PROC_AUTH_DIV).first.evaluate(
                "el => window.getComputedStyle(el).display"
            )
            return disp != "none"
        except Exception:
            return False

    def set_process_auth(self, value: str) -> None:
        """기타 프로세스 권한 라디오 — value: '1' 거부 / '2' 읽기 / '3' 쓰기.
        ⚠ buggy: 첫 변경만 inline text sync (yaml auth_text_sync_once_only).
        """
        self._click_hidden(self.page.locator(
            f"{self.SEL_PROC_AUTH_RADIO}[value='{value}']"
        ).first)

    def set_other_folder_access_auth(self, value: str) -> None:
        """타폴더 접근권한 라디오 — 동일 buggy."""
        self._click_hidden(self.page.locator(
            f"{self.SEL_OTHER_AUTH_RADIO}[value='{value}']"
        ).first)

    def get_process_auth_text(self) -> str:
        """span#processAuthText 현재 텍스트 (buggy sync 검증)."""
        return self.page.locator(self.SEL_PROC_AUTH_TEXT).first.inner_text().strip()

    def get_other_auth_text(self) -> str:
        return self.page.locator(self.SEL_OTHER_AUTH_TEXT).first.inner_text().strip()

    # ──────────────────────────────────────────────────────────────
    # Step 4c — 적용 URL 영역 (isUrl 토글 + 종속)
    # ──────────────────────────────────────────────────────────────
    def set_is_url(self, on: bool) -> None:
        """isUrl 토글 — OFF: isDataDecrypt+attachAllowUrl+addBtn disabled."""
        self._set_toggle(self.SEL_TOGGLE_IS_URL, on)

    def is_url_checked(self) -> bool:
        return self.page.locator(self.SEL_TOGGLE_IS_URL).first.is_checked()

    def click_decrypt_allow(self) -> None:
        """허용 URL (val=0) 라디오 — isFileUploadEncrypt 자유 체크."""
        self._click_hidden(self.page.locator(self.SEL_RADIO_DECRYPT_0).first)

    def click_decrypt_target(self) -> None:
        """복호화 대상 지정 (val=1) → isFileUploadEncrypt 자동 체크+disabled."""
        self._click_hidden(self.page.locator(self.SEL_RADIO_DECRYPT_1).first)

    def add_url(self, url: str) -> None:
        """URL input + 추가. yaml 인용: 형식 검증 없음 ('not a url' 도 등록)."""
        self.page.locator(self.SEL_URL_INPUT).first.fill(url)
        self._click(self.page.locator(self.SEL_URL_ADD_BTN).first)

    def get_url_list(self) -> list[str]:
        """등록된 URL tag list. ⚠ 다른 tag_input 과 selector 겹침 — 컨테이너 확정 시 좁힐 것."""
        items = self.page.locator(self.SEL_URL_LIST_TAG + " span")
        return [items.nth(i).inner_text().strip() for i in range(items.count())]

    def remove_url(self, url: str) -> bool:
        """웹제한 URL tag × 삭제. 성공 시 True.

        Chrome MCP 2026-05-19 검증 — 부모 `div#allowUrl` 안 `button.tagInput`.
        delete icon = `i.urlDeleteBtn` (확장자의 extentionDeleteBtn 과 별도 이름).
        ng-click 패턴 — JS `el.click()` 으로 발화.
        """
        tags = self.page.locator(self.SEL_URL_LIST_TAG)
        cnt = tags.count()
        for i in range(cnt):
            text = tags.nth(i).inner_text().strip()
            if url in text:
                sub = tags.nth(i).locator("i.urlDeleteBtn")
                if sub.count() == 0:
                    return False
                sub.first.evaluate("el => el.click()")
                return True
        return False

    def remove_file_extension(self, ext: str) -> bool:
        """웹제한 확장자 tag × 삭제. 성공 시 True.

        Chrome MCP 2026-05-19 검증 — 부모 `div#extension` 안 `button.tagInput`.
        delete icon = `i.extentionDeleteBtn` (메인 확장자 패턴 동일, P 없음).
        """
        tags = self.page.locator(self.SEL_FILE_EXT_LIST_TAG)
        cnt = tags.count()
        for i in range(cnt):
            text = tags.nth(i).inner_text().strip()
            if text.startswith(ext + " ") or text == ext or text.split()[0] == ext:
                sub = tags.nth(i).locator("i.extentionDeleteBtn")
                if sub.count() == 0:
                    return False
                sub.first.evaluate("el => el.click()")
                return True
        return False

    def get_url_dependent_disabled(self) -> dict[str, bool]:
        """isUrl 토글 종속 4건 disabled 상태."""
        return {
            "isDataDecrypt_0":   self.page.locator(self.SEL_RADIO_DECRYPT_0).first.is_disabled(),
            "isDataDecrypt_1":   self.page.locator(self.SEL_RADIO_DECRYPT_1).first.is_disabled(),
            "attachAllowUrl":    self.page.locator(self.SEL_URL_INPUT).first.is_disabled(),
            "attachAllowUrlBtn": self.page.locator(self.SEL_URL_ADD_BTN).first.is_disabled(),
        }

    # ──────────────────────────────────────────────────────────────
    # Step 4c — 업로드 시 암호화 / 헤더 체크 (독립)
    # ──────────────────────────────────────────────────────────────
    def set_file_encrypt(self, on: bool) -> None:
        """isFileUploadEncrypt — isDataDecrypt=1 일 때 disabled 강제."""
        self._set_toggle(self.SEL_FILE_ENCRYPT, on)

    def is_file_encrypt_checked(self) -> bool:
        return self.page.locator(self.SEL_FILE_ENCRYPT).first.is_checked()

    def is_file_encrypt_disabled(self) -> bool:
        return self.page.locator(self.SEL_FILE_ENCRYPT).first.is_disabled()

    def set_header_check(self, on: bool) -> None:
        """헤더 체크 기능 사용 — yaml: uploadLimitSize 와 독립."""
        self._set_toggle(self.SEL_HEADER_CHECK, on)

    # ──────────────────────────────────────────────────────────────
    # Step 4c — 업로드 허용 확장자 (제품 typo: Extention)
    # ──────────────────────────────────────────────────────────────
    def add_file_extension(self, ext: str) -> None:
        """업로드 허용 확장자 추가 — ';' 다중 구분자 일괄 등록."""
        self.page.locator(self.SEL_FILE_EXT_INPUT).first.fill(ext)
        self._click(self.page.locator(self.SEL_FILE_EXT_ADD).first)

    def get_file_extension_list(self) -> list[str]:
        """등록된 업로드 허용 확장자 tag list (visible 만).

        Chrome MCP 2026-05-19 검증: 부모 `div#extension` 안 `button.tagInput`,
        삭제 후 display:none 잔류 → SEL_FILE_EXT_LIST_TAG 에 `:visible` 적용.
        """
        items = self.page.locator(self.SEL_FILE_EXT_LIST_TAG + " span")
        return [
            items.nth(i).inner_text().strip().split()[0]
            for i in range(items.count())
        ]

    # ──────────────────────────────────────────────────────────────
    # Step 4c — 업로드 제한용량
    # ──────────────────────────────────────────────────────────────
    def set_upload_limit(self, value: str) -> None:
        """양의 정수 strict (yaml: 'abc' → '0', '-1' → '1', 9자리 OK)."""
        self.page.locator(self.SEL_UPLOAD_LIMIT).first.fill(value)

    def get_upload_limit(self) -> str:
        return self.page.locator(self.SEL_UPLOAD_LIMIT).first.input_value()

    # ──────────────────────────────────────────────────────────────
    # Step 4c — 설명
    # ──────────────────────────────────────────────────────────────
    def set_description(self, text: str) -> None:
        self.page.locator(self.SEL_DESCRIPTION).first.fill(text)

    def get_description(self) -> str:
        return self.page.locator(self.SEL_DESCRIPTION).first.input_value()

    # ──────────────────────────────────────────────────────────────
    # Step 4d — 저장 / 닫기
    # ──────────────────────────────────────────────────────────────
    def confirm(self) -> None:
        """확인 → 메인 모달 itemWebRestrictList 에 행 등록 + 모달 닫힘.
        yaml: 필수 — webRestrictName + 적용 프로세스 ≥ 1건.
        """
        self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)
        self.wait_closed()

    def close(self) -> None:
        """× 버튼 → 모달 detached (저장 안 함)."""
        self._click(self.page.locator(self.SEL_CLOSE_BTN).first)
        self.wait_closed()
