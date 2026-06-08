"""
pages/npouch_origin_protect_policy_page.py — nPouch 원본보호 정책 페이지

엔파우치 > 원본보호 정책
scan_mode: modal_form
모달: div#addItemModal.modal-wrap.in  (동적 생성/제거 방식)
탭: 기본 설정 / 허용 프로세스 / 예외처리 프로세스 / 실행차단 프로세스

[의존성]
- 제어 스위트 (managerControlSuite) 가 먼저 존재해야 정책 생성 가능
"""
from pages.base_page import BasePage


class NpouchOriginProtectPolicyPage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_APP_SETTING_ICON  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_LIST  = "ul.managerAppSettingList"
    SEL_NPOUCH_HEADER     = "a.managerNpouch"
    SEL_MENU_ITEM         = "a[data-menuid='managerNpouchOriginProtectPolicy']"

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
    # 기본 설정 탭
    SEL_POLICY_NAME      = "input#originProtectPolicyName"
    SEL_DRIVE_LETTER     = "input#driveLetter"
    SEL_DRIVE_LABEL      = "input#driveLabel"
    SEL_DRIVE_QUOTA      = "input#originProtectDriveQuota"
    # 제어 스위트 선택 (버튼 + 결과 span)
    SEL_CSU_SELECT_BTN   = "div#addItemModal button.addBtn.smallBtn.addTemplate"
    SEL_CSU_ID_SPAN      = "span#controlSuiteId"
    # 프로세스 사용 체크박스
    SEL_ALLOW_PROCESS    = "input#isAllowProcess"
    SEL_EXCEPT_PROCESS   = "input#isExceptProcess"
    SEL_BLOCK_PROCESS    = "input#isBlockProcess"
    # 파일 감시
    SEL_WATCH_EXT_TOGGLE = "input#isWatchFileExtension"
    SEL_WATCH_EXT_INPUT  = "input#watchFileExtensions"
    SEL_WATCH_EXT_BTN    = "button#watchFileExtensionAddBtn"
    SEL_WATCH_HEADER     = "input#isWatchFileHeader"
    SEL_WATCH_EXCEPT_INPUT = "input#watchExceptFolders"
    SEL_WATCH_EXCEPT_BTN   = "button#watchExceptFolderAddBtn"
    # 종료 메시지
    SEL_SHUTDOWN_MSG_TOGGLE = "input#isAllowProcessShutdownText"
    SEL_SHUTDOWN_MSG_TEXT   = "textarea#allowProcessShutdownText"
    # 화면 워터마크
    SEL_SCREEN_WM         = "input#isScreenWaterMark"
    SEL_SCREEN_WM_TEXT    = "input#screenWaterMarkText"
    SEL_SCREEN_WM_PC_INFO = "input#isScreenWaterMarkPcInfo"
    SEL_SCREEN_WM_TIME    = "input#isScreenWaterMarkCurrentTime"
    SEL_SCREEN_WM_OPACITY = "input#screenWaterMarkOpacity"
    SEL_SCREEN_WM_DEGREE  = "input#screenWaterMarkDegree"
    # 출력물 워터마크
    SEL_PRINT_WM         = "input#isPrintWaterMark"
    SEL_PRINT_WM_TEXT    = "input#printWaterMarkText"
    SEL_PRINT_WM_PC_INFO = "input#isPrintWaterMarkPcInfo"
    SEL_PRINT_WM_TIME    = "input#isPrintWaterMarkCurrentTime"
    SEL_PRINT_WM_OPACITY = "input#printWaterMarkOpacity"
    SEL_PRINT_WM_DEGREE  = "input#printWaterMarkDegree"
    # 재위탁
    SEL_SECOND_TAKEOUT   = "input#isSecondTakeout"
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
        "#!/managerNpouchOriginProtectPolicy"
        "?pageNo=1&pageSize=100&searchText="
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """원본보호 정책 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        if ("NpouchOriginProtectPolicy" in self.page.url
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
        # [AUTO]_ 또는 [AUTO_KEEP]_ 둘 다 허용 (사용자 보고 2026-06-01 결함 fix)
        # 이전: '[AUTO]' 만 허용 → '[AUTO_KEEP]_X'.startswith('[AUTO]') = False
        # → delete_all_test_data 의 [AUTO_KEEP] cleanup 실패 (silent skip) → KEEP 잔존
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

    # ── 탭 전환 ──────────────────────────────────────────────────

    def activate_tab(self, tab_text: str) -> None:
        """모달 탭 전환. ul.nav li a 텍스트 기준."""
        tab_sel = f"div#addItemModal ul.nav li a:has-text('{tab_text}')"
        tab = self.page.locator(tab_sel).first
        tab.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        tab.evaluate("el => el.click()")
        self.page.wait_for_timeout(200)

    # ── CRUD ──────────────────────────────────────────────────────

    def add_policy(self, name: str, drive_letter: str = "Z",
                   drive_label: str = "NPouch") -> str:
        """원본보호 정책 추가. [AUTO] 접두사 필수. 실제 생성된 이름 반환."""
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
            self.fill(self.SEL_DRIVE_LETTER, drive_letter)
            self.fill(self.SEL_DRIVE_LABEL, drive_label)
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

    def delete_all_auto_policies(self) -> int:
        """[AUTO]_ 만 삭제, [AUTO_KEEP]_ 보존 (control_suite 패턴 일치).
        [AUTO]_DELME_ 는 제외 (삭제 차단된 잔존물 — 테스터 수동 정리 대상)."""
        deleted = 0
        for name in [n for n in self.get_policy_names()
                     if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")
                     and not n.startswith("[AUTO]_DELME_")]:
            try:
                self.delete_policy(name)
                deleted += 1
            except Exception:
                pass
        return deleted

    def delete_all_test_data(self) -> int:
        """[AUTO]_ + [AUTO_KEEP]_ 모두 삭제 — session 시작 clean slate 용 (control_suite 패턴).
        [AUTO]_DELME_ 는 제외 (참조 잠금으로 못 지운 잔존물 — 재rename 방지)."""
        deleted = 0
        for name in [n for n in self.get_policy_names()
                     if (n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]"))
                     and not n.startswith("[AUTO]_DELME_")]:
            try:
                self.delete_policy(name)
                deleted += 1
            except Exception:
                pass
        return deleted

    def delete_policy(self, name: str) -> str:
        """정책 삭제. 반환: 'deleted' | 'blocked'(참조 중 — 삭제 차단, 정상) | 'skipped'.

        참조 잠금(엔파우치 정책이 이 원본보호 정책 부여 중 → DELETE 422)으로 삭제 차단 시:
        5초 timeout 으로 멈추지 않고 ~1.2초 만에 차단 감지 → skip (재사용). hang/rename 없음.
        """
        if not (name.startswith("[AUTO]") or name.startswith("[AUTO_KEEP]")):
            raise Exception("테스트 정책([AUTO]/[AUTO_KEEP] 접두사)만 삭제 가능합니다")

        self.check_policy_row(name)
        self.click(self.SEL_DELETE_BTN)
        # 1단계: "삭제 하시겠습니까?" confirm
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            return "skipped"
        msg = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        if "하시겠습니까" not in msg:
            # 이미 차단/에러 모달 (참조 등) → dismiss 후 skip
            try:
                self.click_attached(self.SEL_CONFIRM_BTN)
            except Exception:
                pass
            print(f"[delete_policy] 삭제 차단(참조 중) skip: {name!r} / {msg!r}")
            return "blocked"
        # 확인 → 삭제 요청
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.page.wait_for_timeout(1200)   # 서버 응답 짧게 대기 (422 차단 모달 출현 시간)
        # 2단계: 모달 잔존 = 참조 잠금(DELETE 422) 차단 → skip (재사용)
        if self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0:
            try:
                msg2 = self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
            except Exception:
                msg2 = "(차단 모달)"
            try:
                self.click_attached(self.SEL_CONFIRM_BTN)
            except Exception:
                pass
            print(f"[delete_policy] 삭제 차단(참조 중) skip: {name!r} / {msg2!r}")
            return "blocked"
        # 삭제 성공
        try:
            self.wait_for(self.SEL_ADD_BTN)
            self._restore_page_size()
        except Exception:
            pass
        return "deleted"

    # ── UIScanner 인터페이스 ──────────────────────────────────────

    AUTO_NAME_PREFIX = "[AUTO]_opp"

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

    # ── 확인 모달 (전역 알림) 헬퍼 — control_suite 패턴 복제 ──────────
    def is_confirm_modal_visible(self, timeout: int = 1500) -> bool:
        """__globalMessageModal 알림 노출 여부 (attached 대기 포함)."""
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).first.wait_for(
                state="attached", timeout=timeout
            )
            return True
        except Exception:
            return False

    def get_confirm_message(self) -> str:
        """알림 메시지 텍스트."""
        loc = self.page.locator(
            "div#__globalMessageModal .modal-body, div#__globalMessageModal .modal-body-text"
        )
        cnt = loc.count()
        for i in range(cnt):
            try:
                t = loc.nth(i).inner_text().strip()
                if t:
                    return t
            except Exception:
                continue
        return ""

    def dismiss_confirm_modal(self) -> None:
        """알림 '확인' 클릭 + 닫힘 대기."""
        try:
            self.click_attached(self.SEL_CONFIRM_BTN)
        except Exception:
            # fallback — JS click (좌표 무관)
            self.page.locator(self.SEL_CONFIRM_BTN).first.evaluate("el => el.click()")
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

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
        return {"input#originProtectPolicyName": saved_name}

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
