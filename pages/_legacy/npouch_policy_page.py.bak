"""
pages/npouch_policy_page.py — nPouch 엔파우치 정책 페이지

엔파우치 > 엔파우치 정책
scan_mode: modal_form
모달: div#addItemModal.modal-wrap.in  (동적 생성/제거 방식)
탭: 정책 정보 / PDF문서 보호 기능 설정

[의존성]
- 원본보호 정책 (managerNpouchOriginProtectPolicy) 이 먼저 존재해야 원본보호 옵션 선택 가능
"""
from pages.base_page import BasePage


class NpouchPolicyPage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_APP_SETTING_ICON = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_LIST = "ul.managerAppSettingList"
    SEL_NPOUCH_HEADER    = "a.managerNpouch"
    SEL_MENU_ITEM        = "a[data-menuid='managerNpouchPolicy']"

    # ── 목록 버튼 ─────────────────────────────────────────────────
    SEL_ADD_BTN    = "button#addItemBtn"
    SEL_MODIFY_BTN = "button#modifyItemBtn"
    SEL_COPY_BTN   = "button#copyItemBtn"
    SEL_DELETE_BTN = "button#removeItemBtn"
    SEL_TABLE_ROW  = "table tbody tr"
    SEL_TABLE_ACTIVE = "table tbody tr.tActive"
    SEL_CHECKBOX   = "input[type='checkbox']"
    SEL_SEARCH_INPUT = "input#searchText"

    # ── 모달 ─────────────────────────────────────────────────────
    SEL_MODAL      = "div#addItemModal"
    SEL_MODAL_OPEN = "div#addItemModal.in"

    # [정책 정보 탭] 기본 필드
    SEL_POLICY_NAME         = "input#npPolicyName"
    SEL_CERT_URL            = "input#readFileCertificateUrl"
    SEL_VALIDATE_SSL        = "input#isValidateSslCert"
    SEL_MAX_READ_COUNT      = "input#isMaxReadCount"
    SEL_MAX_READ_COUNT_VAL  = "input#maxReadCount"
    SEL_MAX_READ_DAY        = "input#isMaxReadDay"
    SEL_MAX_READ_DAY_VAL    = "input#maxReadDay"
    # 비밀번호 정책
    SEL_PW_MIN              = "input#passwordMinDigit"
    SEL_PW_MAX              = "input#passwordMaxDigit"
    SEL_PW_SAME_LETTER      = "input#passwordSameLetterCount"
    SEL_PW_CONTINUE_LETTER  = "input#passwordContinueLetterCount"
    SEL_PW_NUMBER           = "input#isPasswordNumberLetter"
    SEL_PW_SPECIAL          = "input#isPasswordSpecialLetter"
    # 뷰어 앱
    SEL_INCLUDE_READER      = "input#includeReaderApp"
    SEL_NOT_INCLUDE_READER  = "input#notIncludeReaderApp"
    # 원본보호 정책
    SEL_ORIGIN_PROTECT      = "input#isOriginProtectPolicy"
    SEL_ORIGIN_PROTECT_BTN  = "button#addNpouchOriginProtectPolicyBtn"
    # 인쇄 옵션
    SEL_PRINT_OPTION        = "input#isPrintOption"
    SEL_PRINT_X             = "input#isPrintX"
    SEL_PRINT_O             = "input#isPrintO"
    SEL_ALLOW_PRINT_BRAND   = "textarea#allowPrintBrandText"
    SEL_EXCEPT_PRINT_PORT   = "textarea#exceptPrintPortText"
    # 생성 파일 카운트
    SEL_FILE_COUNT_TOGGLE   = "input#isNpPackageFileCreateFileCount"
    SEL_FILE_COUNT_VAL      = "input#npPackageFileCreateFileCount"
    # 기타
    SEL_SERVER_AUTH         = "input#isServerAuthToRead"
    SEL_COLLECT_LOCATION    = "input#isCollectLocationInfo"
    SEL_ALLOW_OFFLINE       = "input#isAllowOfflineViewing"
    SEL_DENY_OFFLINE        = "input#isDenyOfflineViewing"
    SEL_EXT_FILTER          = "input#isExtensionFilter"
    SEL_EXT_INCLUDE         = "input#includeFileExtension"
    SEL_EXT_EXCEPT          = "input#exceptFileExtension"
    SEL_EXT_INPUT           = "input#extensions"
    SEL_EXT_ADD_BTN         = "button#addExtensions"
    SEL_LOGO_IMG            = "input#logoImges"
    SEL_HTML_DOC_NAME       = "input#htmlDocumentName"
    SEL_HTML_CONTACT        = "input#htmlContactNumber"
    SEL_CUSTOM_OPTION       = "input#customOptionText"

    # [PDF 보호 탭]
    SEL_PDF_PROTECT         = "input#isPdfProtect"
    SEL_PDF_PRINT           = "input#isPdfPrint"
    SEL_PDF_WATERMARK       = "input#isPdfWaterMark"
    SEL_SHOOT_PREVENT_WM    = "input#isShootPreventWaterMark"
    SEL_SHOOT_WM_TEXT       = "input#shootPreventWaterMarkText"
    SEL_SHOOT_WM_PC_INFO    = "input#shootPreventWaterMarkPcInfo"
    SEL_SHOOT_WM_TIME       = "input#shootPreventWaterMarkCurrentTime"
    SEL_SHOOT_WM_OPACITY    = "input#shootPreventWaterMarkOpacity"
    SEL_PDF_WM_MAIN         = "input#isPdfWaterMarkMain"
    SEL_PDF_WM_TEXT         = "input#pdfWaterMarkAddText"
    SEL_PDF_WM_SIZE         = "input#pdfWaterMarkAddTextSize"
    SEL_PDF_WM_OPACITY      = "input#pdfWaterMarkAddTextOpacity"
    SEL_PDF_WM_DEGREE       = "input#pdfWaterMarkAddTextDegree"
    SEL_PDF_WM_COLOR        = "input#pdfWaterMarkAddTextColor"

    # 모달 버튼
    SEL_SUBMIT_BTN = "div#addItemModal button.btn-primary"
    SEL_CANCEL_BTN = "div#addItemModal button.btn-default"

    # ── 확인 모달 (전역) ─────────────────────────────────────────
    SEL_CONFIRM_MODAL = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN   = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG     = "div.modal-body-text"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 5_000
    _TIMEOUT_STALE = 1_000

    _HASH_PAGE_SIZE = (
        "#!/managerNpouchPolicy"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """엔파우치 정책 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        if ("managerNpouchPolicy?" in self.page.url
                and "pageSize=100" in self.page.url
                and self.is_visible(self.SEL_ADD_BTN)):
            return

        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_APP_SETTING_LIST).wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

        if not self.is_visible(self.SEL_APP_SETTING_LIST):
            self.click(self.SEL_APP_SETTING_ICON)
            self.wait_for(self.SEL_APP_SETTING_LIST)

        if not self.is_visible(self.SEL_MENU_ITEM):
            try:
                self.page.locator(self.SEL_NPOUCH_HEADER).first.evaluate("el => el.click()")
                self.page.wait_for_timeout(300)
            except Exception:
                pass

        self.click(self.SEL_MENU_ITEM)
        self.wait_for(self.SEL_ADD_BTN)
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ── 목록 조회 ─────────────────────────────────────────────────

    def get_policy_names(self) -> list[str]:
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    def is_policy_exists(self, name: str) -> bool:
        return name in self.get_policy_names()

    # ── 행 선택 ──────────────────────────────────────────────────

    def click_policy_row(self, name: str) -> None:
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        for attempt in range(3):
            self._toggle_overlay(False)
            self.page.wait_for_timeout(80)
            try:
                row.click(force=True, timeout=3000)
            finally:
                self._toggle_overlay(True)
            try:
                self.page.locator(self.SEL_TABLE_ACTIVE).filter(
                    has_text=name
                ).first.wait_for(state="attached", timeout=3000)
                return
            except Exception:
                pass
        raise Exception(f"행 선택 실패 (3회): {name}")

    def check_policy_row(self, name: str) -> None:
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 정책([AUTO] 접두사)만 조작 가능합니다")
        checkbox = (
            self.page.locator(self.SEL_TABLE_ROW)
            .filter(has_text=name).first
            .locator(self.SEL_CHECKBOX).first
        )
        if not checkbox.is_checked():
            self._toggle_overlay(False)
            try:
                checkbox.click()
            finally:
                self._toggle_overlay(True)

    # ── 탭 전환 ──────────────────────────────────────────────────

    def activate_tab(self, tab_text: str) -> None:
        tab_sel = f"div#addItemModal ul.nav li a:has-text('{tab_text}')"
        tab = self.page.locator(tab_sel).first
        tab.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        tab.evaluate("el => el.click()")
        self.page.wait_for_timeout(200)

    # ── CRUD ──────────────────────────────────────────────────────

    def add_policy(self, name: str) -> str:
        """엔파우치 정책 추가. [AUTO] 접두사 필수. 실제 생성된 이름 반환."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 정책([AUTO] 접두사)만 생성 가능합니다")

        actual_name = [name]

        def _attempt():
            self.click(self.SEL_ADD_BTN)
            self.page.locator(self.SEL_MODAL_OPEN).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.page.wait_for_timeout(200)
            self.fill(self.SEL_POLICY_NAME, actual_name[0])
            self.click_attached(self.SEL_SUBMIT_BTN)
            for suffix in range(2, 11):
                try:
                    self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                        state="attached", timeout=self._TIMEOUT_MODAL
                    )
                except Exception:
                    break
                msg = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                    state="detached", timeout=self._TIMEOUT_TABLE
                )
                if "이미 등록" not in msg:
                    break
                actual_name[0] = f"{name}_{suffix}"
                loc = self.page.locator(self.SEL_POLICY_NAME).first
                loc.evaluate("el => { el.value = ''; }")
                loc.fill(actual_name[0])
                loc.evaluate("el => el.dispatchEvent(new Event('input', {bubbles:true}))")
                self.click_attached(self.SEL_SUBMIT_BTN)
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except Exception as e:
            print(f"\n[add_policy] 1차 실패: {e} — navigate_to 후 재시도")
            self.navigate_to()
            actual_name[0] = name
            _attempt()

        return actual_name[0]

    def delete_all_auto_policies(self) -> None:
        for name in [n for n in self.get_policy_names() if n.startswith("[AUTO]")]:
            try:
                self.delete_policy(name)
            except Exception:
                pass

    def delete_policy(self, name: str) -> None:
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 정책([AUTO] 접두사)만 삭제 가능합니다")

        def _attempt():
            self.check_policy_row(name)
            self.click(self.SEL_DELETE_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            msg = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
            if "하시겠습니까" not in msg:
                self.click_attached(self.SEL_CONFIRM_BTN)
                raise Exception(f"삭제 에러 모달: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
            self.wait_for(self.SEL_ADD_BTN)
            self._restore_page_size()

        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_policy] 1차 실패: {e} — navigate_to 후 재시도")
            self.navigate_to()
            _attempt()

    # ── UIScanner 인터페이스 ──────────────────────────────────────

    AUTO_NAME_PREFIX = "[AUTO]_npp"

    def open_add_modal(self) -> None:
        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )

    def open_modify_modal(self, policy_name: str) -> None:
        self.click_policy_row(policy_name)
        self.click(self.SEL_MODIFY_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )

    def close_modal(self) -> None:
        self.click_attached(self.SEL_CANCEL_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    def save_policy(self, name: str) -> None:
        self.fill(self.SEL_POLICY_NAME, name)
        self.click_attached(self.SEL_SUBMIT_BTN)
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
        self.wait_for(self.SEL_ADD_BTN)

    def get_verify_values(self, saved_name: str) -> dict:
        return {"input#npPolicyName": saved_name}

    def save_edit_modal(self) -> None:
        self.click_attached(self.SEL_SUBMIT_BTN)
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
        self.wait_for(self.SEL_ADD_BTN)

    def close_edit_modal(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    # ── 내부 유틸 ─────────────────────────────────────────────────

    def _restore_page_size(self) -> None:
        if "pageSize=100" in self.page.url:
            return
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() > 0:
                self.click_attached(self.SEL_CANCEL_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
