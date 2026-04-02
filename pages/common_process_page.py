"""
pages/common_process_page.py — RansomCruncher 공통 프로세스 페이지

scan_mode: list_page — 모달 기반 정책 페이지가 아닌 목록 관리 페이지.
navigate_to(), delete_all_auto_items(), add_item(), delete_item() 구현.
"""
from pages.base_page import BasePage


class CommonProcessPage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_LEFT_NAV          = "ul.leftNavList"
    SEL_APP_SETTING_MENU  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"
    SEL_RC_SECTION_HEADER = "a.managerRansomCruncher"
    SEL_RC_COMMON_PROCESS = "a[data-menuid='managerRansomCruncherCommonProcess']"

    # ── 목록 ─────────────────────────────────────────────────────
    SEL_ADD_BTN    = "button#addItemBtn"
    SEL_MODIFY_BTN = "button#modifyItemBtn"
    SEL_DELETE_BTN = "button#removeItemBtn"
    SEL_TABLE_ROW  = "table tbody tr"
    SEL_CHECKBOX   = "input[type='checkbox']"

    # ── 모달 ─────────────────────────────────────────────────────
    SEL_ADD_MODAL    = "div#addItemModal"
    SEL_MODAL_OPEN   = "div#addItemModal.in"   # .in = Bootstrap 3 열림 상태
    SEL_REGISTER_BTN = "button[add-btn]"
    SEL_MODIFY_SUBMIT_BTN = "button[modify-btn]"
    SEL_CANCEL_BTN   = "button.btn-default"
    SEL_CLOSE_BTN    = "button[data-dismiss='modal']"
    SEL_PROCESS_NAME = "input#processName"
    SEL_SHA2         = "textarea#sha2"
    SEL_SIGN         = "input#sign"

    # ── 확인 모달 ─────────────────────────────────────────────────
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 3_000
    _TIMEOUT_STALE = 1_000

    # 예외 프로세스 탭 + pageSize=100 해시
    _HASH_EXCEPT = (
        "#!/managerRansomCruncherCommonProcess"
        "?pageNo=1&pageSize=100&searchText=&processType=EXCEPT_PROCESS"
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """공통 프로세스 페이지(예외 프로세스 탭, pageSize=100)로 이동."""
        self._close_modal_if_open()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "CommonProcess" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        # CommonProcess 페이지가 아니면 항상 main.html 재로드
        # (메뉴 아코디언이 이미 열린 상태가 아닐 때 JS 클릭이 동작하지 않는 문제 방지)
        if "CommonProcess" not in self.page.url or "pageSize=100" not in self.page.url:
            host = self.base_url.split("/#!/")[0].rstrip("/")
            self.page.goto(f"{host}/manager/main.html")
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

        if not self.is_visible(self.SEL_RC_COMMON_PROCESS):
            self.click(self.SEL_RC_SECTION_HEADER)
            self.wait_for(self.SEL_RC_COMMON_PROCESS)

        self.click(self.SEL_RC_COMMON_PROCESS)
        self.wait_for(self.SEL_ADD_BTN)
        self.page.evaluate(f"window.location.hash = '{self._HASH_EXCEPT}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ── 목록 조회 ─────────────────────────────────────────────────

    def get_item_names(self) -> list[str]:
        """현재 목록의 프로세스 이름 리스트 반환."""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    # ── CRUD ──────────────────────────────────────────────────────

    def add_item(self, name: str, sha2: str) -> None:
        """항목 추가. [AUTO] 접두사 필수."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 생성 가능합니다")

        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(300)

        self.fill(self.SEL_PROCESS_NAME, name)

        # SHA2 textarea — evaluate로 직접 값 설정 후 input 이벤트 트리거
        sha2_loc = self.page.locator(self.SEL_SHA2).first
        sha2_loc.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        sha2_loc.evaluate(
            "(el, value) => { el.value = value; "
            "el.dispatchEvent(new Event('input', {bubbles:true})); }",
            sha2
        )
        self.page.wait_for_timeout(200)

        self.click_attached(self.SEL_REGISTER_BTN)

        # 확인 모달 처리 (등록 성공 또는 에러)
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

        self.wait_for(self.SEL_ADD_BTN)
        self._restore_page_size()

    def open_modify_modal(self, name: str) -> None:
        """항목 이름으로 행을 native click 선택 후 수정 버튼 클릭.

        AngularJS contents-list-item directive는 CDP 마우스 이벤트에 반응하지 않으므로
        오버레이를 잠시 제거한 뒤 Playwright native click을 사용한다.
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        self._toggle_overlay(False)
        try:
            row.click()
        finally:
            self._toggle_overlay(True)
        self.page.wait_for_timeout(300)
        self.click(self.SEL_MODIFY_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def switch_tab(self, label: str) -> None:
        """탭 레이블로 탭 전환 후 목록 로드 대기."""
        self.page.locator(f"a:has-text('{label}')").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(500)
        self.wait_for(self.SEL_ADD_BTN)

    def try_add_item(self, name: str, sha2: str) -> tuple[bool, str]:
        """항목 추가 시도. 성공/에러 여부와 모달 메시지 반환.
        성공: (True, 메시지), 에러: (False, 에러 메시지)
        """
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 생성 가능합니다")

        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(300)

        self.fill(self.SEL_PROCESS_NAME, name)

        sha2_loc = self.page.locator(self.SEL_SHA2).first
        sha2_loc.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        sha2_loc.evaluate(
            "(el, value) => { el.value = value; "
            "el.dispatchEvent(new Event('input', {bubbles:true})); }",
            sha2
        )
        self.page.wait_for_timeout(200)

        self.click_attached(self.SEL_REGISTER_BTN)

        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            msg = self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception as e:
            msg = str(e)

        # 추가 모달이 아직 열려 있으면 에러로 저장 실패한 것 → 닫기
        if self.page.locator(self.SEL_MODAL_OPEN).count() > 0:
            try:
                self.click_attached(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
            except Exception:
                pass
            return False, msg

        self.wait_for(self.SEL_ADD_BTN)
        self._restore_page_size()
        return True, msg

    def delete_all_auto_items(self) -> None:
        """[AUTO] 접두사 항목을 예외/차단 탭 모두에서 삭제한다."""
        for tab_label in ("예외 프로세스", "차단 프로세스"):
            try:
                self.switch_tab(tab_label)
            except Exception:
                pass
            for name in [n for n in self.get_item_names() if n.startswith("[AUTO]")]:
                try:
                    self.delete_item(name)
                except Exception:
                    pass
        # 예외 탭으로 복귀
        try:
            self.switch_tab("예외 프로세스")
        except Exception:
            pass

    def delete_item(self, name: str) -> None:
        """항목 삭제. [AUTO] 접두사 필수."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 삭제 가능합니다")

        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        checkbox = row.locator(self.SEL_CHECKBOX).first
        if not checkbox.is_checked():
            self._toggle_overlay(False)
            try:
                checkbox.click()
            finally:
                self._toggle_overlay(True)

        self.click(self.SEL_DELETE_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        msg = self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()
        if "하시겠습니까" not in msg:
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
            raise Exception(f"삭제 중 에러 모달: {msg!r}")

        self.click_attached(self.SEL_CONFIRM_BTN)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )
        self.wait_for(self.SEL_ADD_BTN)
        self._restore_page_size()

    # ── 내부 유틸 ─────────────────────────────────────────────────

    def _restore_page_size(self) -> None:
        if "pageSize=100" in self.page.url:
            return
        self.page.evaluate(f"window.location.hash = '{self._HASH_EXCEPT}';")
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
                self.click_attached(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ── Universal Scanner 인터페이스 (list_page 모드는 미사용) ────
    # qa_runner.run_list_page_scan()이 직접 page_obj 메서드를 호출하므로
    # save_policy / close_edit_modal / get_verify_values 불필요.

    def fill_modify_and_save(self) -> dict:
        """이미 열린 수정 모달에서 SHA2 마지막 자리를 변경하여 저장한다.
        open_modify_modal() 호출 후 사용.
        반환값: 저장 후 재확인용 {selector: expected_value}.

        ※ 제품 버그 (확인: 2026-04-01 Chrome MCP):
            전자서명(sign) 변경 시 AngularJS 내부 SHA2 상태 변수가 초기화됨.
            JS DOM 조작(el.value = ...) 으로는 내부 상태 복원 불가.
            → sign 변경 없이 SHA2를 Playwright fill()로 직접 변경하여 저장.
            → sign→SHA2 초기화 버그는 _scan_modify() 에서 known_bug로 별도 기록.
        """
        # SHA2 현재값 읽기 → 마지막 자리 순환 변경 (0↔1)
        sha2_val = self.page.locator(self.SEL_SHA2).first.evaluate("el => el.value")
        last_char = sha2_val[-1] if sha2_val else "0"
        new_last  = "1" if last_char == "0" else "0"
        new_sha2  = sha2_val[:-1] + new_last

        # Playwright fill() → 접근성 트리 기반 실제 입력 → 내부 상태 동기화
        self.page.locator(self.SEL_SHA2).first.fill(new_sha2)
        self.page.wait_for_timeout(200)
        self.click_attached(self.SEL_MODIFY_SUBMIT_BTN)
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass
        self.wait_for(self.SEL_ADD_BTN)
        return {self.SEL_SHA2: new_sha2}

    def get_verify_values(self, saved_name: str) -> dict:
        """수정 모달 로드 후 프로세스 이름 필드 값 확인 (기존 3-Phase 방식과 동일)."""
        return {"input#processName": saved_name}

    def save_policy(self, name: str) -> None:
        raise NotImplementedError("CommonProcessPage는 list_page 모드 — save_policy 미사용")
