"""
pages/npouch_control_suite_page.py — nPouch 제어 스위트 관리 페이지

공통설정 > 전역정책 관리 > 제어 스위트 관리
scan_mode: modal_form
모달: div#controlSuite.modal-wrap.in  (동적 생성/제거 방식)
"""
from pages.base_page import BasePage


class NpouchControlSuitePage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_SYS_MGMT_ICON     = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST     = "ul.managerSystemManagementList"
    SEL_UNIFIED_HEADER    = "a.managerUnifiedPolicy"
    SEL_MENU_ITEM         = "a[data-menuid='managerControlSuite']"

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
    SEL_MODAL      = "div#controlSuite"
    SEL_MODAL_OPEN = "div#controlSuite.in"
    SEL_CSU_NAME   = "input#csuName"
    # 클립보드 공유제한
    SEL_CLIPBOARD_RESTRICT = "input#isClipboardRestrict"
    SEL_CLIPBOARD_URL      = "textarea#clipboardAllowUrl"
    # 네트워크
    SEL_NETWORK    = "input#isNetwork"
    # 제어할 확장자
    SEL_EXT_ALLOW  = "input#ALLOW"
    SEL_EXT_BLOCK  = "input#BLOCK"
    SEL_EXT_INPUT  = "input#allowExtensionInput"
    SEL_EXT_ADD    = "button#allowExtensionInputBtn"
    SEL_HEADER_CHECK = "input#isHeaderCheck"
    # 전자서명 예외처리
    SEL_SIGN_EXCEPT       = "input#isSignExcept"
    SEL_SIGN_EXCEPT_INPUT = "input#signExceptInput"
    SEL_SIGN_EXCEPT_BTN   = "button#signExceptBtn"
    # 프로세스별 제어 (주 모달 내 탭)
    SEL_ADD_PROCESS_BTN    = "button#addCsuProcessBtn"
    SEL_REMOVE_PROCESS_BTN = "button#removeCsuProcessBtn"
    SEL_PROC_TAB           = "div#controlSuite a.userItemTitle[rel='process']"
    SEL_TAG_TAB            = "div#controlSuite a.userItemTitle[rel='tag']"
    SEL_PROC_LIST_TBODY    = "tbody#csuProcessListTb"
    SEL_TAG_LIST_TBODY     = "tbody#csuTagListTb"

    # 프로세스/태그 등록 서브모달 (공용)
    SEL_PROC_MODAL_OPEN  = "div#controlSuiteProcessList.in"
    SEL_PROC_SELECT_BTN  = "div#controlSuiteProcessList button#csuProcessBtn"
    SEL_PROC_CONFIRM     = "div#controlSuiteProcessList .btn.btn-primary"
    SEL_PROC_CLOSE       = "div#controlSuiteProcessList .close"

    # 프로세스/태그 선택 서브서브모달 (공용)
    SEL_PICKER_MODAL_OPEN = "div#globalProcessList.in"
    SEL_PICKER_CONFIRM    = "div#globalProcessList .btn.btn-primary"
    SEL_PICKER_CLOSE      = "div#globalProcessList .close"

    # 웹 제한기능
    SEL_ADD_WEB_RESTRICT_BTN    = "button#addCsuWebRestrictBtn"
    SEL_REMOVE_WEB_RESTRICT_BTN = "button#removeCsuWebRestrictBtn"
    # 커스텀 옵션
    SEL_CUSTOM_OPTION = "input#customOptionText"
    # 모달 버튼
    SEL_SUBMIT_BTN = "div#controlSuite button.btn-primary"
    SEL_CANCEL_BTN = "div#controlSuite button.btn-default"

    # ── 확인 모달 (전역) ─────────────────────────────────────────
    SEL_CONFIRM_MODAL = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN   = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG     = "div.modal-body-text"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 5_000
    _TIMEOUT_STALE = 1_000

    _HASH_PAGE_SIZE = (
        "#!/managerControlSuite"
        "?pageNo=1&pageSize=100&searchText="
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """제어 스위트 관리 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        if ("ControlSuite" in self.page.url
                and "pageSize=100" in self.page.url
                and self.is_visible(self.SEL_ADD_BTN)):
            return

        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_SYS_MGMT_LIST).wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

        if not self.is_visible(self.SEL_SYS_MGMT_LIST):
            self.click(self.SEL_SYS_MGMT_ICON)
            self.wait_for(self.SEL_SYS_MGMT_LIST)

        if not self.is_visible(self.SEL_MENU_ITEM):
            try:
                self.page.locator(self.SEL_UNIFIED_HEADER).first.evaluate("el => el.click()")
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
                # "검색된 내용이 없습니다." 등 빈 결과 메시지 행 제외
                if name and "없습니다" not in name:
                    names.append(name)
        return names

    def is_policy_exists(self, name: str) -> bool:
        return name in self.get_policy_names()

    # ── 행 선택 ──────────────────────────────────────────────────

    def click_policy_row(self, name: str) -> None:
        """정책 이름으로 행 클릭 (tActive 확인)."""
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

    # ── CRUD ──────────────────────────────────────────────────────

    def add_policy(self, name: str) -> str:
        """제어 스위트 추가. [AUTO] 접두사 필수. 실제 생성된 이름 반환."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 정책([AUTO] 접두사)만 생성 가능합니다")

        actual_name = [name]

        def _attempt():
            self.click(self.SEL_ADD_BTN)
            self.page.locator(self.SEL_MODAL_OPEN).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.page.wait_for_timeout(200)
            self.fill(self.SEL_CSU_NAME, actual_name[0])
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
                loc = self.page.locator(self.SEL_CSU_NAME).first
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

        # 검색 필터 초기화 — 추가 후 새 항목이 목록 최상단에 보이도록
        try:
            self.search_policy("")
            self.page.wait_for_timeout(200)
        except Exception:
            pass
        return actual_name[0]

    def delete_all_auto_policies(self) -> None:
        # 검색 필터 초기화 — 필터 중에는 일부 [AUTO] 항목이 숨겨져 삭제 누락됨
        try:
            self.search_policy("")
            self.page.wait_for_timeout(300)
        except Exception:
            pass
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

    AUTO_NAME_PREFIX = "[AUTO]_csu"

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
        self.fill(self.SEL_CSU_NAME, name)
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
        return {"input#csuName": saved_name}

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

    # ── 검색 / 복사 ──────────────────────────────────────────────────

    def search_policy(self, query: str) -> None:
        """검색창에 query 입력 후 검색 버튼 클릭."""
        self.page.locator(self.SEL_SEARCH_INPUT).first.evaluate(
            "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
            query,
        )
        self.click("button#searchBtn")
        self.page.wait_for_timeout(400)

    def copy_policy(self, name: str) -> None:
        """행 선택 후 복사 버튼 클릭. 복사본 생성 확인 모달 처리."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 정책([AUTO] 접두사)만 조작 가능합니다")
        self.click_policy_row(name)
        self.click(self.SEL_COPY_BTN)
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
        self._restore_page_size()

    # ── 모달 유틸 ─────────────────────────────────────────────────

    def get_modal_title(self) -> str:
        try:
            return self.page.locator(
                f"{self.SEL_MODAL_OPEN} .modal-title, "
                f"{self.SEL_MODAL_OPEN} h4"
            ).first.inner_text().strip()
        except Exception:
            return ""

    def get_field_value(self, selector: str) -> str:
        try:
            loc = self.page.locator(selector).first
            loc.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
            tag = loc.evaluate("el => el.tagName.toLowerCase()")
            if tag in ("input", "textarea"):
                return loc.input_value()
            return loc.inner_text().strip()
        except Exception:
            return ""

    def get_toggle_state(self, selector: str) -> bool:
        try:
            return self.page.locator(selector).first.is_checked()
        except Exception:
            return False

    def set_toggle(self, selector: str, on: bool) -> None:
        """토글(checkbox) 상태 설정. 이미 목표 상태면 건드리지 않음."""
        current = self.get_toggle_state(selector)
        if current != on:
            self.page.locator(selector).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(200)

    def try_submit(self) -> None:
        """모달 제출 버튼 클릭 (결과 대기 없음)."""
        self.click_attached(self.SEL_SUBMIT_BTN)

    def is_confirm_modal_visible(self) -> bool:
        try:
            return self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0
        except Exception:
            return False

    def get_modal_message(self) -> str:
        try:
            return self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        except Exception:
            return ""

    def dismiss_confirm_modal(self) -> None:
        self.click_attached(self.SEL_CONFIRM_BTN)

    def wait_for_confirm_modal_closed(self) -> None:
        self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )

    def _handle_confirm_modal(self) -> None:
        """확인 모달이 있으면 '확인' 클릭 후 닫힘 대기. 없으면 무시."""
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

    def delete_all_auto_items(self) -> None:
        """delete_all_auto_policies 별칭 — 타 테스트 파일과 명칭 통일."""
        self.delete_all_auto_policies()

    # ── 상세 패널 ─────────────────────────────────────────────────

    SEL_DETAIL_PANEL  = "#__layoutMainItemContentsDetail"
    SEL_DETAIL_TOGGLE = "button#__layoutMainItemDetailOpenCloseBtn"

    def open_detail_panel(self) -> None:
        """상세 패널이 닫혀 있으면 토글 버튼 클릭하여 열기."""
        panel = self.page.locator(self.SEL_DETAIL_PANEL)
        try:
            panel.wait_for(state="visible", timeout=1_000)
            return
        except Exception:
            pass
        self.click(self.SEL_DETAIL_TOGGLE)
        self.page.wait_for_timeout(400)

    def get_detail_panel_text(self) -> str:
        """상세 패널 전체 텍스트 반환."""
        try:
            return self.page.locator(self.SEL_DETAIL_PANEL).first.inner_text().strip()
        except Exception:
            return ""

    # ── 내부 유틸 ─────────────────────────────────────────────────

    # ── Phase 2: 프로세스별 제어 ──────────────────────────────────────

    def click_process_tab(self) -> None:
        """주 모달 내 '개별 프로세스' 탭 클릭."""
        self.page.locator(self.SEL_PROC_TAB).evaluate("el => el.click()")
        self.page.wait_for_timeout(200)

    def click_tag_tab(self) -> None:
        """주 모달 내 '태그' 탭 클릭."""
        self.page.locator(self.SEL_TAG_TAB).evaluate("el => el.click()")
        self.page.wait_for_timeout(200)

    def is_proc_tab_active(self) -> bool:
        try:
            return self.page.locator(self.SEL_PROC_TAB).evaluate(
                "el => el.parentElement.classList.contains('active')"
            )
        except Exception:
            return False

    def is_tag_tab_active(self) -> bool:
        try:
            return self.page.locator(self.SEL_TAG_TAB).evaluate(
                "el => el.parentElement.classList.contains('active')"
            )
        except Exception:
            return False

    def open_process_register_modal(self) -> None:
        """+ 버튼 클릭 → 프로세스/태그 등록 서브모달 열기."""
        self.page.locator(self.SEL_ADD_PROCESS_BTN).evaluate("el => el.click()")
        self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def get_proc_modal_select_btn_text(self) -> str:
        """등록 서브모달의 선택 버튼 텍스트 (프로세스 선택 / 태그 선택)."""
        try:
            return self.page.locator(self.SEL_PROC_SELECT_BTN).first.inner_text().strip()
        except Exception:
            return ""

    def open_picker_from_proc_modal(self) -> None:
        """등록 서브모달에서 선택 버튼 클릭 → 피커 모달 열기."""
        self.page.locator(self.SEL_PROC_SELECT_BTN).evaluate("el => el.click()")
        self.page.locator(self.SEL_PICKER_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(300)

    def select_first_from_picker(self) -> str:
        """피커 모달 첫 번째 항목 radio 선택 → 확인 → 모달 닫힘. 선택 항목명 반환."""
        first_row = self.page.locator(
            f"{self.SEL_PICKER_MODAL_OPEN} table tbody tr"
        ).first
        first_row.locator("input[type='radio']").evaluate("el => el.click()")
        item_text = first_row.inner_text().strip().split("\t")[0].strip()
        self.click_attached(self.SEL_PICKER_CONFIRM)
        self.page.locator(self.SEL_PICKER_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )
        return item_text

    def confirm_proc_modal(self) -> None:
        """등록 서브모달 확인 → 닫힘 대기. 주 모달은 유지."""
        self.click_attached(self.SEL_PROC_CONFIRM)
        self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )
        self.page.wait_for_timeout(200)

    def close_proc_modal(self) -> None:
        """등록 서브모달 닫기 (× 버튼)."""
        try:
            self.page.locator(self.SEL_PROC_CLOSE).evaluate("el => el.click()")
            self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def get_process_list_count(self) -> int:
        """개별 프로세스 목록 행 수 (체크박스 있는 데이터 행 기준)."""
        return self.page.locator(
            f"{self.SEL_PROC_LIST_TBODY} tr td input[type='checkbox']"
        ).count()

    def get_tag_list_count(self) -> int:
        """태그 목록 행 수."""
        return self.page.locator(
            f"{self.SEL_TAG_LIST_TBODY} tr td input[type='checkbox']"
        ).count()

    def check_all_in_process_list(self) -> None:
        """개별 프로세스 목록 전체 체크박스 선택."""
        for cb in self.page.locator(
            f"{self.SEL_PROC_LIST_TBODY} tr td input[type='checkbox']"
        ).all():
            if not cb.is_checked():
                cb.evaluate("el => el.click()")

    def check_all_in_tag_list(self) -> None:
        """태그 목록 전체 체크박스 선택."""
        for cb in self.page.locator(
            f"{self.SEL_TAG_LIST_TBODY} tr td input[type='checkbox']"
        ).all():
            if not cb.is_checked():
                cb.evaluate("el => el.click()")

    def remove_from_process_list(self) -> None:
        """체크된 프로세스/태그 - 버튼으로 제거. 전역 확인 모달 처리 (주 모달 안에서 호출)."""
        self.page.locator(self.SEL_REMOVE_PROCESS_BTN).evaluate("el => el.click()")
        self.page.wait_for_timeout(400)
        # 주 모달 내부이므로 wait_for(SEL_ADD_BTN) 없이 확인 모달만 처리
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
        self.page.wait_for_timeout(300)

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
