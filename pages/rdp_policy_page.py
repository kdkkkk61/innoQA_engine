from pages.base_page import BasePage


class RdpPolicyPage(BasePage):
    # ------------------------------------------------------------------
    # Selectors
    # ------------------------------------------------------------------

    # 메뉴 네비게이션
    SEL_LEFT_NAV          = "ul.leftNavList"
    SEL_APP_SETTING_MENU  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"
    SEL_RC_SECTION_HEADER = "a.managerRansomCruncher"
    SEL_RC_RDP_POLICY     = "a[data-menuid='managerRansomCruncherRdpPolicy']"

    # 목록
    SEL_TABLE_ROW         = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE  = "table tbody tr.tActive"
    SEL_CHECKBOX          = "input[type='checkbox']"

    # 버튼 (목록 페이지)
    SEL_ADD_BTN           = "button#addItemBtn"
    SEL_MODIFY_BTN        = "button#modifyItemBtn"
    SEL_COPY_BTN          = "button#copyItemBtn"
    SEL_DELETE_BTN        = "button#removeItemBtn"

    # 모달 컨테이너 (modal-wrap in — RansomDetect의 modal in과 다른 클래스)
    # Bootstrap 3 열림 상태: .in 클래스 추가 → attached+.in 으로 판단
    SEL_ADD_MODAL         = "div#addItemModal.in"
    SEL_POLICY_NAME       = "input#rcRdpPolicyName"

    # 모달 하단 버튼
    SEL_REGISTER_BTN      = "button[add-btn]"
    SEL_SAVE_BTN          = "button[modify-btn]"
    SEL_CLOSE_BTN         = "button[data-dismiss='modal']"

    # 확인 모달 (공통)
    SEL_CONFIRM_MODAL        = "div#__globalMessageModal"
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    # ------------------------------------------------------------------
    # 타임아웃 상수
    # ------------------------------------------------------------------
    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _HASH_PAGE_SIZE_100 = (
        "#!/managerRansomCruncherRdpPolicy"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ------------------------------------------------------------------
    # 네비게이션
    # ------------------------------------------------------------------
    def navigate_to(self) -> None:
        """
        RDP 정책 페이지로 이동.
        1. 잔여 모달 닫기
        2. 이미 RDP 정책 페이지 + pageSize=100이면 즉시 반환
        3. 매니저 루트로 goto
        4. leftNavList 없으면 세션 만료로 판단
        5. App Setting → RansomCruncher → RDP 정책 순서로 클릭
        """
        self._close_modal_if_open()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "RdpPolicy" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_LEFT_NAV).first.wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
        if not self.is_visible(self.SEL_LEFT_NAV):
            raise RuntimeError(
                "매니저 페이지 UI 없음 — 세션 만료 또는 접근 권한 없음.\n"
                "pytest를 재실행해 주세요."
            )

        if not self.is_visible(self.SEL_APP_SETTING_PANEL):
            self.click(self.SEL_APP_SETTING_MENU)
            self.wait_for(self.SEL_APP_SETTING_PANEL)

        if not self.is_visible(self.SEL_RC_RDP_POLICY):
            self.click(self.SEL_RC_SECTION_HEADER)
            self.wait_for(self.SEL_RC_RDP_POLICY)

        self.click(self.SEL_RC_RDP_POLICY)
        self.wait_for(self.SEL_ADD_BTN)
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 목록 조회
    # ------------------------------------------------------------------
    def get_policy_names(self) -> list[str]:
        """현재 목록의 정책 이름 리스트 반환"""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    def is_policy_exists(self, policy_name: str) -> bool:
        return policy_name in self.get_policy_names()

    # ------------------------------------------------------------------
    # 행 선택
    # ------------------------------------------------------------------
    def click_policy_row(self, policy_name: str) -> None:
        """
        정책 이름으로 행 클릭 (단일 선택 → tActive 확인).
        오버레이 pointer-events 일시 비활성화 후 force=True 클릭.
        force=True: actionability 30초 대기 없이 즉시 좌표 클릭.
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=policy_name).first
        for attempt in range(3):
            self._toggle_overlay(False)
            self.page.wait_for_timeout(80)
            try:
                row.click(force=True, timeout=3000)
            finally:
                self._toggle_overlay(True)
            try:
                self.page.locator(self.SEL_TABLE_ROW_ACTIVE).filter(
                    has_text=policy_name
                ).first.wait_for(state="attached", timeout=5000)
                return
            except Exception:
                print(f"\n[click_policy_row] tActive 미확인 ({attempt+1}회), 재시도...")
        raise Exception(f"행 선택 실패 (3회 재시도): {policy_name}")

    def check_policy_row(self, policy_name: str) -> None:
        """
        정책 이름 행의 체크박스 체크.
        [AUTO] 접두사 정책만 허용.
        JS el.click() 직접 호출 → hit-testing/actionability 대기 완전 우회.
        """
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")
        checkbox = (
            self.page.locator(self.SEL_TABLE_ROW)
            .filter(has_text=policy_name)
            .first.locator(self.SEL_CHECKBOX)
            .first
        )
        if checkbox.is_checked():
            return
        checkbox.evaluate("el => el.click()")
        if not checkbox.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크 상태: {policy_name}")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add_policy(self, name: str) -> str:
        """
        정책 추가 (이름만 입력 후 등록).
        중복 이름 시 suffix(_2, _3, ...) 붙여 재시도.
        반환값: 실제 생성된 정책 이름
        """
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 생성 가능합니다")

        actual_name = [name]

        def _attempt():
            self.click(self.SEL_ADD_BTN)
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
            self.fill(self.SEL_POLICY_NAME, actual_name[0])
            self.click_attached(self.SEL_REGISTER_BTN)
            for suffix in range(2, 11):
                try:
                    self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                        state="attached", timeout=self._TIMEOUT_MODAL
                    )
                except Exception:
                    break
                msg = self.get_modal_message()
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                if "이미 등록되어 있습니다" not in msg:
                    break
                actual_name[0] = f"{name}_{suffix}"
                loc = self.page.locator(self.SEL_POLICY_NAME).first
                loc.evaluate("el => { el.value = ''; }")
                loc.fill(actual_name[0])
                loc.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                self.click_attached(self.SEL_REGISTER_BTN)
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except Exception as e:
            print(f"\n[add_policy] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            actual_name[0] = name
            _attempt()

        return actual_name[0]

    def delete_all_auto_policies(self) -> None:
        """[AUTO] 접두사 정책을 모두 삭제한다."""
        auto_names = [n for n in self.get_policy_names() if n.startswith("[AUTO]")]
        for name in auto_names:
            self.delete_policy(name)

    def delete_policy(self, policy_name: str) -> None:
        """정책 삭제. [AUTO] 접두사 정책만 허용."""
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")

        def _attempt():
            self.check_policy_row(policy_name)
            self.click(self.SEL_DELETE_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("삭제 버튼 클릭 후 모달이 나타나지 않음")
            msg = self.get_modal_message()
            if "하시겠습니까" not in msg:
                self.take_screenshot("delete_error_modal")
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                raise Exception(f"삭제 중 에러 모달: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)
            self._restore_page_size()

        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_policy] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    # ------------------------------------------------------------------
    # UIScanner 스캔용 헬퍼
    # ------------------------------------------------------------------
    def open_add_modal(self) -> None:
        """정책추가 버튼 클릭 → 모달 열림 대기"""
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"정책 추가 모달이 열리지 않음: {e}") from e

    def open_modify_modal(self, policy_name: str) -> None:
        """정책 행 선택 → 수정 버튼 클릭 → 모달 열림 대기"""
        self.click_policy_row(policy_name)
        self.click(self.SEL_MODIFY_BTN)
        self._fail_if_modal(self._TIMEOUT_MODAL)
        try:
            self.wait_for(self.SEL_ADD_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"정책 수정 모달이 열리지 않음: {e}") from e

    def close_modal(self) -> None:
        """모달 닫기 버튼 클릭 → 목록 페이지 복귀 대기"""
        self.click(self.SEL_CLOSE_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    # ------------------------------------------------------------------
    # 모달 유틸
    # ------------------------------------------------------------------
    def get_modal_message(self) -> str:
        return self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()

    def is_confirm_modal_visible(self) -> bool:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            return True
        except Exception:
            return False

    def wait_for_modal_closed(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _restore_page_size(self) -> None:
        if "pageSize=100" in self.page.url:
            return
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.click(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass

    def _fail_if_modal(self, timeout: int = _TIMEOUT_TABLE) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=timeout
            )
        except Exception:
            return
        msg = self.get_modal_message()
        self.take_screenshot("unexpected_modal")
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        raise Exception(f"예상치 못한 모달 발생: {msg!r}")

    # ------------------------------------------------------------------
    # Universal Scanner 표준 인터페이스 구현
    # ------------------------------------------------------------------

    # AUTO_NAME_PREFIX: 이름 길이 일관성 (10자 → _p1/_p2 추가 시 최대 13자)
    AUTO_NAME_PREFIX = "[AUTO]_rdp"

    def save_policy(self, name: str) -> None:
        """Phase 1/2 완료 후 정책 저장 (이름 + 연결 설정 라디오 필수).

        연결 설정 라디오(isConnect)가 미선택 상태이면 '연결 자단'을 기본으로 선택.
        Phase 1은 radio scan을 건너뛰므로 라디오가 null 상태로 남아 저장 불가.
        """
        deny_radio = self.page.locator("input#isDenyConnect")
        allow_radio = self.page.locator("input#isAllowConnect")
        if not deny_radio.is_checked() and not allow_radio.is_checked():
            deny_radio.evaluate("el => el.click()")
            self.page.wait_for_timeout(200)
        self.fill(self.SEL_POLICY_NAME, name)
        self.click_attached(self.SEL_REGISTER_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        self.wait_for(self.SEL_ADD_BTN)

    def close_edit_modal(self) -> None:
        """Phase 3 EDIT 모달 닫기 — 조건부 (already closed 대응)."""
        try:
            if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def save_edit_modal(self) -> None:
        """Phase 4: 수정 모달에서 변경 내용 저장 (수정 저장 버튼 클릭 + 확인 처리)."""
        self.click_attached(self.SEL_SAVE_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        self.wait_for(self.SEL_ADD_BTN)

    def get_verify_values(self, saved_name: str) -> dict:
        """Phase 3: EDIT 모달 로드 후 정책 이름 필드 값 확인."""
        return {"input#rcRdpPolicyName": saved_name}
