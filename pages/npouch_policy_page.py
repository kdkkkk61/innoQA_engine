"""pages/npouch_policy_page.py — nPouch 엔파우치 정책 페이지.

작성: 2026-06-01 (사용자 명령 — origin_protect 패턴 복제)
이전 버전: pages/_legacy/npouch_policy_page.py.bak (참고용)

[의존성]
- 원본보호 정책 ([AUTO_KEEP]_sc5_origin_protect) — 원본보호 정책 선택 시 연계

[페이지 구조 — Chrome MCP 확인 2026-06-01]
- URL: #!/managerNpouchPolicy
- 모달: div#addItemModal.in (정책 추가 / 정책 수정)
- 탭: "정책 정보" / "PDF문서 보호 기능 설정"
- 입력 필드: 51개 (정책 정보 37 + PDF 14)
"""
from pages.base_page import BasePage


class NpouchPolicyPage(BasePage):
    """nPouch 엔파우치 정책 페이지 — origin_protect 패턴 복제."""

    PAGE_ID = "npouch_policy"

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_APP_SETTING_ICON  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_LIST  = "ul.managerAppSettingList"
    SEL_NPOUCH_HEADER     = "a.managerNpouch"
    SEL_MENU_ITEM         = "a[data-menuid='managerNpouchPolicy']"

    # ── 목록 ──────────────────────────────────────────────────────
    SEL_ADD_BTN              = "button#addItemBtn"
    SEL_MODIFY_BTN           = "button#modifyItemBtn"
    SEL_COPY_BTN             = "button#copyItemBtn"
    SEL_DELETE_BTN           = "button#removeItemBtn"
    SEL_INTEGRATED_BTN       = "button:has-text('통합정책')"   # 특수
    SEL_PUBLIC_IP_BTN        = "button:has-text('엔파우치 열람 가능 공인IP')"  # 특수
    SEL_TABLE_ROW            = "table tbody tr"
    SEL_TABLE_ACTIVE         = "table tbody tr.tActive"
    SEL_CHECKBOX             = "input[type='checkbox']"
    SEL_SEARCH_INPUT         = "input#searchText"

    # ── 모달 ─────────────────────────────────────────────────────
    SEL_MODAL                = "div#addItemModal"
    SEL_MODAL_OPEN           = "div#addItemModal.in"
    SEL_SUBMIT_BTN           = "div#addItemModal.in .modal-footer button.btn-primary:visible"
    SEL_CANCEL_BTN           = "div#addItemModal.in button:has-text('취소')"

    # 탭
    SEL_TAB_BASIC            = "div#addItemModal.in ul.nav li a:has-text('정책 정보')"
    SEL_TAB_PDF              = "div#addItemModal.in ul.nav li a:has-text('PDF문서 보호 기능 설정')"

    # ── [정책 정보 탭] 필수/기본 ──────────────────────────────────
    SEL_POLICY_NAME              = "input#npPolicyName"
    SEL_CERT_URL                 = "input#readFileCertificateUrl"
    SEL_VALIDATE_SSL             = "input#isValidateSslCert"

    # 열람 제한
    SEL_MAX_READ_COUNT_TOGGLE    = "input#isMaxReadCount"
    SEL_MAX_READ_COUNT_VAL       = "input#maxReadCount"
    SEL_MAX_READ_DAY_TOGGLE      = "input#isMaxReadDay"
    SEL_MAX_READ_DAY_VAL         = "input#maxReadDay"

    # 비밀번호
    SEL_PW_TOGGLE                = "input#isOpenFilePassword"
    SEL_PW_MIN                   = "input#passwordMinDigit"
    SEL_PW_MAX                   = "input#passwordMaxDigit"
    SEL_PW_SAME_LETTER           = "input#passwordSameLetterCount"
    SEL_PW_CONTINUE_LETTER       = "input#passwordContinueLetterCount"
    SEL_PW_NUMBER_LETTER         = "input#isPasswordNumberLetter"
    SEL_PW_SPECIAL_LETTER        = "input#isPasswordSpecialLetter"

    # 뷰어 앱
    SEL_INCLUDE_READER           = "input#includeReaderApp"
    SEL_NOT_INCLUDE_READER       = "input#notIncludeReaderApp"

    # 원본보호 정책
    SEL_ORIGIN_PROTECT           = "input#isOriginProtectPolicy"
    SEL_ORIGIN_PROTECT_BTN       = "button#addNpouchOriginProtectPolicyBtn"  # text="정책선택"

    # 인쇄
    SEL_PRINT_OPTION             = "input#isPrintOption"
    SEL_PRINT_X                  = "input#isPrintX"
    SEL_PRINT_O                  = "input#isPrintO"
    SEL_ALLOW_PRINT_BRAND        = "textarea#allowPrintBrandText"
    SEL_EXCEPT_PRINT_PORT        = "textarea#exceptPrintPortText"

    # 첨부파일
    SEL_FILE_COUNT_TOGGLE        = "input#isNpPackageFileCreateFileCount"
    SEL_FILE_COUNT_VAL           = "input#npPackageFileCreateFileCount"

    # 서버 통신
    SEL_SERVER_AUTH              = "input#isServerAuthToRead"
    SEL_COLLECT_LOCATION         = "input#isCollectLocationInfo"
    SEL_OFFLINE_POLICY           = "input#isOfflinePolicy"
    SEL_ALLOW_OFFLINE            = "input#isAllowOfflineViewing"
    SEL_DENY_OFFLINE             = "input#isDenyOfflineViewing"

    # 확장자
    SEL_EXT_FILTER               = "input#isExtensionFilter"
    SEL_EXT_INCLUDE              = "input#includeFileExtension"
    SEL_EXT_EXCEPT               = "input#exceptFileExtension"
    SEL_EXT_INPUT                = "input#extensions"

    # HTML 가이드
    SEL_LOGO_IMG                 = "input#logoImges"
    SEL_HTML_DOC_NAME            = "input#htmlDocumentName"
    SEL_HTML_CONTACT             = "input#htmlContactNumber"

    # 커스텀
    SEL_CUSTOM_OPTION            = "input#customOptionText"

    # ── [PDF문서 보호 기능 설정 탭] ─────────────────────────────
    SEL_PDF_PROTECT              = "input#isPdfProtect"
    SEL_PDF_PRINT                = "input#isPdfPrint"
    SEL_PDF_WATERMARK            = "input#isPdfWaterMark"

    # 촬영방지 워터마크 (바둑판)
    SEL_SHOOT_WM                 = "input#isShootPreventWaterMark"
    SEL_SHOOT_WM_TEXT            = "input#shootPreventWaterMarkText"
    SEL_SHOOT_WM_PC              = "input#shootPreventWaterMarkPcInfo"
    SEL_SHOOT_WM_TIME            = "input#shootPreventWaterMarkCurrentTime"
    SEL_SHOOT_WM_OPACITY         = "input#shootPreventWaterMarkOpacity"

    # 화면 중앙 워터마크
    SEL_CENTER_WM                = "input#isPdfWaterMarkMain"
    SEL_CENTER_WM_TEXT           = "input#pdfWaterMarkAddText"
    SEL_CENTER_WM_SIZE           = "input#pdfWaterMarkAddTextSize"
    SEL_CENTER_WM_OPACITY        = "input#pdfWaterMarkAddTextOpacity"
    SEL_CENTER_WM_DEGREE         = "input#pdfWaterMarkAddTextDegree"
    SEL_CENTER_WM_COLOR          = "input#pdfWaterMarkAddTextColor"  # ★ color picker

    # 워터마크 표시 위치 (3x3 grid — Chrome MCP 확인 2026-06-01)
    SEL_WM_POSITION_TABLE        = "table#tempTable.tempTable"
    SEL_WM_POSITION_CELL_FMT     = "table#tempTable td[data-split-location='{}']"  # POSITION 변수
    WM_POSITIONS = [
        "TOP_LEFT", "TOP_CENTER", "TOP_RIGHT",
        "MIDDLE_LEFT", "MIDDLE_CENTER", "MIDDLE_RIGHT",
        "BOTTOM_LEFT", "BOTTOM_CENTER", "BOTTOM_RIGHT",
    ]

    # ── 특수 모달 (Chrome MCP 확인 2026-06-01) ──
    SEL_INTEGRATED_MODAL         = "div.modal-wrap.in:has-text('정책 부서,사용자 추가/삭제')"
    SEL_IP_SETTING_MODAL         = "div.modal-wrap.in:has-text('엔파우치 열람 가능 공인IP 설정')"

    # ── 모달 메시지 ──────────────────────────────────────────────
    SEL_CONFIRM_MODAL            = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN              = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG                = "div#__globalMessageModal .modal-body, div#__globalMessageModal .modal-body-text"

    _TIMEOUT_MODAL = 5000
    _TIMEOUT_TABLE = 10000

    # ── 네비게이션 (origin_protect 패턴 복제 2026-06-01) ───────
    def navigate_to(self) -> None:
        """엔파우치 정책 페이지로 이동."""
        try:
            self._dismiss_stale_confirm_modal()
        except Exception:
            pass
        try:
            self._close_modal_if_open()
        except Exception:
            pass

        if "managerNpouchPolicy" in (self.page.url or "") and self.is_visible(self.SEL_ADD_BTN):
            return

        if "manager/main.html" not in (self.page.url or ""):
            self.page.goto(f"{self.host_origin}/manager/main.html")
            try:
                self._dismiss_stale_confirm_modal()
            except Exception:
                pass

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

    def _dismiss_stale_confirm_modal(self) -> None:
        """잔존 confirm 모달 닫기 (origin_protect 패턴)."""
        try:
            if self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0:
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.page.wait_for_timeout(200)
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        """addItem 모달 잔존 닫기."""
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() > 0:
                self.click_attached(self.SEL_CANCEL_BTN)
                self.page.wait_for_timeout(200)
        except Exception:
            pass

    # ── list 조회 ─────────────────────────────────────────────────
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

    # ── row 선택 ─────────────────────────────────────────────────
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
        # [AUTO] OR [AUTO_KEEP] 둘 다 허용 (origin_protect 의 결함 fix 패턴)
        if not (name.startswith("[AUTO]") or name.startswith("[AUTO_KEEP]")):
            raise Exception("테스트 정책([AUTO]/[AUTO_KEEP] 접두사)만 조작 가능합니다")
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

    # ── 탭 ──────────────────────────────────────────────────────
    def activate_tab(self, tab_text: str) -> None:
        tab_sel = f"div#addItemModal ul.nav li a:has-text('{tab_text}')"
        tab = self.page.locator(tab_sel).first
        tab.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        tab.evaluate("el => el.click()")
        self.page.wait_for_timeout(200)

    # ── 모달 ──────────────────────────────────────────────────────
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

    # ── confirm 모달 ─────────────────────────────────────────────
    def is_confirm_modal_visible(self, timeout: int = 1500) -> bool:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(state="attached", timeout=timeout)
            return True
        except Exception:
            return False

    def get_confirm_message(self) -> str:
        try:
            return self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        except Exception:
            return ""

    def dismiss_confirm_modal(self) -> None:
        try:
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(state="detached", timeout=3000)
        except Exception:
            pass

    # ── 삭제 ─────────────────────────────────────────────────────
    def delete_policy(self, name: str) -> None:
        if not (name.startswith("[AUTO]") or name.startswith("[AUTO_KEEP]")):
            raise Exception("테스트 정책([AUTO]/[AUTO_KEEP] 접두사)만 삭제 가능합니다")

        def _attempt():
            self.check_policy_row(name)
            self.click(self.SEL_DELETE_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            msg = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
            if "하시겠습니까" not in msg:
                self.click_attached(self.SEL_CONFIRM_BTN)
                raise Exception(f"삭제 에러: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_policy] 1차 실패: {e} — navigate_to 후 재시도")
            self.navigate_to()
            _attempt()

    def delete_all_auto_policies(self) -> int:
        """[AUTO]_ 만 삭제, [AUTO_KEEP]_ 보존."""
        deleted = 0
        for name in [n for n in self.get_policy_names()
                     if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")]:
            try:
                self.delete_policy(name)
                deleted += 1
            except Exception:
                pass
        return deleted

    def delete_all_test_data(self) -> int:
        """[AUTO]_ + [AUTO_KEEP]_ 모두 삭제 — session 시작 clean slate 용."""
        deleted = 0
        for name in [n for n in self.get_policy_names()
                     if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]:
            try:
                self.delete_policy(name)
                deleted += 1
            except Exception:
                pass
        return deleted

    # ── UIScanner 인터페이스 ─────────────────────────────────────
    AUTO_NAME_PREFIX = "[AUTO]_npp"

    def get_required_fields(self) -> list[str]:
        return [self.SEL_POLICY_NAME]
