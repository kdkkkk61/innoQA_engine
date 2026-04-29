"""
pages/npouch_operation_process_page.py — nPouch 운용 프로세스 페이지

공통설정 > 자원 관리 > 운용 프로세스
scan_mode: list_page
모달: div#addCommonProcess.modal-wrap.in  (Bootstrap 3 방식 아님 — 동적 생성/제거)
"""
from pages.base_page import BasePage


class NpouchOperationProcessPage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_SYS_MGMT_ICON   = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST   = "ul.managerSystemManagementList"
    SEL_RESOURCE_HEADER = "a.managerResource"
    SEL_MENU_ITEM       = "a[data-menuid='managerGlobalCommonProcess']"

    # ── 목록 버튼 ─────────────────────────────────────────────────
    SEL_ADD_BTN    = "button#addItemBtn"
    SEL_MODIFY_BTN = "button#modifyItemBtn"
    SEL_DELETE_BTN = "button#removeItemBtn"
    SEL_TABLE_ROW  = "table tbody tr"
    SEL_CHECKBOX   = "input[type='checkbox']"

    # ── 모달 (동적 생성/제거 방식) ────────────────────────────────
    SEL_MODAL        = "div#addCommonProcess"
    SEL_MODAL_OPEN   = "div#addCommonProcess.in"
    SEL_PROCESS_NAME = "input#processName"
    SEL_SIGN         = "input#sign"
    SEL_SHA2         = "textarea#sha2"
    SEL_EXEC_PATH    = "textarea#processExecutePath"
    SEL_DESCRIPTION  = "textarea#description"
    SEL_SUBMIT_BTN   = "div#addCommonProcess button.btn-primary"
    SEL_CANCEL_BTN   = "div#addCommonProcess button.btn-default"

    # ── 확인 모달 (전역 공통) ─────────────────────────────────────
    SEL_CONFIRM_MODAL  = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN    = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG      = "#__globalMessageModal .modal-body"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 5_000
    _TIMEOUT_STALE = 1_000

    _HASH_PAGE_SIZE = (
        "#!/managerGlobalCommonProcess"
        "?pageNo=1&pageSize=100&searchOption=processName&searchText="
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """운용 프로세스 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        if ("GlobalCommonProcess" in self.page.url
                and "pageSize=100" in self.page.url
                and self.is_visible(self.SEL_ADD_BTN)):
            return

        # 매니저 main.html 로드 (세션 유지 + 메뉴 초기화)
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

        # 자원 관리 섹션 펼치기 (이미 보이면 스킵)
        if not self.is_visible(self.SEL_MENU_ITEM):
            try:
                self.page.locator(self.SEL_RESOURCE_HEADER).first.evaluate("el => el.click()")
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

    def get_item_names(self) -> list[str]:
        """현재 목록의 프로세스 이름 리스트 반환.
        td가 2개 미만인 행(빈 목록 안내 메시지 등)은 제외."""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if len(tds) >= 2:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    # ── CRUD ──────────────────────────────────────────────────────

    def add_item(self, name: str, sha2: str = "", sign: str = "",
                 exec_path: str = "", description: str = "") -> None:
        """운용 프로세스 추가. [AUTO] 접두사 필수."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 생성 가능합니다")

        self.open_add_modal()

        self.fill(self.SEL_PROCESS_NAME, name)
        if sign:
            self.fill(self.SEL_SIGN, sign)
        if sha2:
            sha2_loc = self.page.locator(self.SEL_SHA2).first
            sha2_loc.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }",
                sha2
            )
            self.page.wait_for_timeout(150)
        if exec_path:
            self.page.locator(self.SEL_EXEC_PATH).first.fill(exec_path)
            self.page.wait_for_timeout(100)
        if description:
            self.page.locator(self.SEL_DESCRIPTION).first.fill(description)
            self.page.wait_for_timeout(100)

        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        # 추가 후 검색으로 항목 찾기 (알파벳순 정렬 시 목록 밖에 있을 수 있음)
        self.search_item(name)

    def delete_all_auto_items(self) -> None:
        """[AUTO] 접두사 항목 모두 삭제."""
        self.search_item("[AUTO]")
        auto_names = [n for n in self.get_item_names() if n.startswith("[AUTO]")]
        for name in auto_names:
            try:
                self.delete_item(name)
                self.search_item("[AUTO]")
            except Exception:
                pass
        self._restore_page_size()

    def delete_item(self, name: str) -> None:
        """항목 삭제. [AUTO] 접두사 필수."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 삭제 가능합니다")

        # 검색으로 행 노출
        self.search_item(name)
        self.page.wait_for_timeout(300)

        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        checkbox = row.locator(self.SEL_CHECKBOX).first
        if not checkbox.is_checked():
            self._toggle_overlay(False)
            try:
                checkbox.click()
            finally:
                self._toggle_overlay(True)

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
        try:
            row.wait_for(state="detached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    def open_modify_modal(self, name: str) -> None:
        """행 선택 → 수정 버튼 클릭 → 모달 열림 대기."""
        # 검색으로 행 노출
        self.search_item(name)
        self.page.wait_for_timeout(300)

        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        self._toggle_overlay(False)
        self.page.wait_for_timeout(80)
        try:
            row.click(force=True, timeout=3000)
        finally:
            self._toggle_overlay(True)
        self.page.wait_for_timeout(300)
        self.click(self.SEL_MODIFY_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def fill_modify_and_save(self) -> dict:
        """수정 모달에서 description 마지막 자리 변경 후 저장."""
        desc_loc = self.page.locator(self.SEL_DESCRIPTION).first
        desc_val = desc_loc.evaluate("el => el.value") or ""
        new_desc = desc_val[:-1] + ("1" if not desc_val or desc_val[-1] != "1" else "0") if desc_val else "scan_mod"
        self.page.locator(self.SEL_DESCRIPTION).first.fill(new_desc)
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        return {self.SEL_PROCESS_NAME: None}  # 이름 유지 확인용

    def get_verify_values(self, saved_name: str) -> dict:
        return {"input#processName": saved_name}

    # ── 테스트 헬퍼 (public) ──────────────────────────────────────

    def open_add_modal(self) -> None:
        """추가 버튼 클릭 → 모달 열림 대기."""
        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def close_modal(self) -> None:
        """취소 버튼으로 모달 닫기. 이미 닫혀있으면 즉시 반환."""
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() == 0:
                return
            self.click_attached(self.SEL_CANCEL_BTN)
            self.page.locator(self.SEL_MODAL_OPEN).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

    def try_submit(self) -> None:
        """제출 버튼 클릭 (결과 처리 없음 — 검증용)."""
        self.click_attached(self.SEL_SUBMIT_BTN)
        self.page.wait_for_timeout(400)

    def is_confirm_modal_visible(self) -> bool:
        """전역 확인 모달 표시 여부."""
        return self.page.locator(self.SEL_CONFIRM_MODAL).count() > 0

    def get_modal_message(self) -> str:
        """전역 확인 모달 메시지 텍스트."""
        try:
            return self.page.locator(self.SEL_MODAL_MSG).first.inner_text().strip()
        except Exception:
            return ""

    def dismiss_confirm_modal(self) -> None:
        """전역 확인 모달 닫기."""
        self.click_attached(self.SEL_CONFIRM_BTN)

    def wait_for_confirm_modal_closed(self) -> None:
        """전역 확인 모달이 사라질 때까지 대기."""
        self.page.locator(self.SEL_CONFIRM_MODAL).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )

    def search_item(self, keyword: str) -> None:
        """키워드로 검색 실행 (기본 옵션 유지)."""
        search = self.page.locator("input#searchText").first
        search.fill(keyword)
        self.page.locator("button#searchBtn").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(600)

    def search_item_with_option(self, keyword: str, option_label: str) -> None:
        """검색 옵션을 변경한 뒤 키워드로 검색. option_label: '프로세스 이름' | '서명' | '설명'"""
        try:
            self.page.locator("select#searchOption").first.select_option(label=option_label)
            self.page.wait_for_timeout(100)
        except Exception:
            pass
        self.search_item(keyword)

    def get_modal_title(self) -> str:
        """현재 열린 모달의 타이틀 텍스트."""
        try:
            return self.page.locator(
                f"{self.SEL_MODAL} .modal-title, {self.SEL_MODAL} .modal-header h4"
            ).first.inner_text().strip()
        except Exception:
            return ""

    def get_field_value(self, selector: str) -> str:
        """필드 value 속성 반환."""
        try:
            return self.page.locator(selector).first.evaluate("el => el.value")
        except Exception:
            return ""

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

    def _handle_confirm_modal(self) -> None:
        """추가/수정 후 나타나는 확인 모달 처리."""
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
