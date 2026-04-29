"""
pages/npouch_tag_page.py — nPouch 태그 관리 페이지

공통설정 > 자원 관리 > 태그 관리
scan_mode: list_page
모달: div#addItemModal.modal-wrap.in  (동적 생성/제거 방식)
"""
from pages.base_page import BasePage


class NpouchTagPage(BasePage):

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_SYS_MGMT_ICON   = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST   = "ul.managerSystemManagementList"
    SEL_RESOURCE_HEADER = "a.managerResource"
    SEL_MENU_ITEM       = "a[data-menuid='managerGlobalProcessTag']"

    # ── 목록 버튼 ─────────────────────────────────────────────────
    SEL_ADD_BTN    = "button#addItemBtn"
    SEL_MODIFY_BTN = "button#modifyItemBtn"
    SEL_DELETE_BTN = "button#removeItemBtn"
    SEL_TABLE_ROW  = "table tbody tr"
    SEL_CHECKBOX   = "input[type='checkbox']"

    # ── 모달 ─────────────────────────────────────────────────────
    SEL_MODAL      = "div#addItemModal"
    SEL_MODAL_OPEN = "div#addItemModal.in"
    SEL_TAG_NAME   = "input#tagName"
    SEL_DESCRIPTION = "textarea#description"
    SEL_SUBMIT_BTN = "div#addItemModal button.btn-primary"
    SEL_CANCEL_BTN = "div#addItemModal button.btn-default"

    # ── 수정 모달 내 프로세스 관리 (+/-) ─────────────────────────
    SEL_TAG_ADD_PROC_BTN     = "div#addItemModal button#addItemBtn"    # + 버튼
    SEL_TAG_REMOVE_PROC_BTN  = "div#addItemModal button#removeItemBtn" # - 버튼
    SEL_PROC_TABLE_ROW       = "div#addItemModal table tbody tr"       # 등록된 프로세스 목록
    SEL_PROC_TABLE_CHECKBOX  = "div#addItemModal table tbody input[type='checkbox']"

    # ── 프로세스 선택 서브모달 (#globalProcessList) ──────────────
    SEL_PROC_MODAL        = "div#globalProcessList"
    SEL_PROC_MODAL_OPEN   = "div#globalProcessList.in"
    SEL_PROC_LIST_ROW     = "div#globalProcessList table tbody tr"
    SEL_PROC_LIST_CB      = "input[name='selectProcess']"
    SEL_PROC_LIST_ALL_CB  = "input#mainListHeaderCheckBox"
    SEL_PROC_LIST_CONFIRM = "div#globalProcessList button.btn-primary"
    SEL_PROC_LIST_SEARCH  = "input#searchNameText"   # 프로세스 명 검색

    # ── 확인 모달 (전역) ─────────────────────────────────────────
    SEL_CONFIRM_MODAL = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN   = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_MSG     = "#__globalMessageModal .modal-body"

    _TIMEOUT_TABLE = 5_000
    _TIMEOUT_MODAL = 5_000
    _TIMEOUT_STALE = 1_000

    _HASH_PAGE_SIZE = (
        "#!/managerGlobalProcessTag"
        "?pageNo=1&pageSize=100&searchText="
    )

    # ── 네비게이션 ────────────────────────────────────────────────

    def navigate_to(self) -> None:
        """태그 관리 페이지로 이동."""
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        if ("GlobalProcessTag" in self.page.url
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
        """현재 목록의 태그 이름 리스트 반환."""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            # 실제 데이터 행은 최소 2열 이상 (1열짜리는 "검색된 내용이 없습니다." colspan 행)
            if len(tds) >= 2:
                name = tds[0].inner_text().strip()
                if name:
                    names.append(name)
        return names

    # ── CRUD ──────────────────────────────────────────────────────

    def add_item(self, name: str) -> None:
        """태그 추가. [AUTO] 접두사 필수."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 생성 가능합니다")

        self.open_add_modal()
        self.fill(self.SEL_TAG_NAME, name)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        # 추가 후 검색으로 항목 확인
        self.search_item(name)

    def register_first_process(self, name: str) -> str:
        """이름으로 태그를 찾아 첫 번째 프로세스를 등록하고 저장. 등록된 프로세스 이름 반환."""
        self.open_modify_modal(name)
        self.open_process_list_modal()
        proc_name = self.select_first_process_in_modal()
        self.confirm_process_selection()
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        return proc_name

    def add_item_with_process(self, name: str) -> str:
        """태그 추가 후 첫 번째 프로세스 등록. [AUTO] 접두사 필수. 등록된 프로세스 이름 반환."""
        self.add_item(name)
        return self.register_first_process(name)

    def add_item_with_desc(self, name: str, desc: str) -> None:
        """태그 추가 (이름 + 설명). [AUTO] 접두사 필수."""
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 항목([AUTO] 접두사)만 생성 가능합니다")

        self.open_add_modal()
        self.fill(self.SEL_TAG_NAME, name)
        self.page.locator(self.SEL_DESCRIPTION).first.evaluate(
            "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
            desc
        )
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        self.search_item(name)

    def delete_all_auto_items(self) -> None:
        """[AUTO] 접두사 태그 모두 삭제."""
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
        """태그 삭제. [AUTO] 접두사 필수."""
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
        """수정 모달에서 description 변경 후 저장."""
        desc_loc = self.page.locator(self.SEL_DESCRIPTION).first
        desc_val = desc_loc.evaluate("el => el.value") or ""
        new_desc = "scan_mod_tag" if not desc_val else (desc_val + "_m")
        self.page.locator(self.SEL_DESCRIPTION).first.fill(new_desc)
        self.page.wait_for_timeout(150)
        self.click_attached(self.SEL_SUBMIT_BTN)
        self._handle_confirm_modal()
        self.wait_for(self.SEL_ADD_BTN)
        return {self.SEL_TAG_NAME: None}

    def get_verify_values(self, saved_name: str) -> dict:
        return {"input#tagName": saved_name}

    # ── 테스트 헬퍼 (public) ──────────────────────────────────────

    def open_add_modal(self) -> None:
        """추가 버튼 클릭 → 모달 열림 대기."""
        self.click(self.SEL_ADD_BTN)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(200)

    def close_modal(self) -> None:
        """취소 버튼으로 모달 닫기."""
        try:
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

    # ── 프로세스 등록/해제 (수정 모달 내) ────────────────────────

    def open_process_list_modal(self) -> None:
        """수정 모달 내 + 버튼 클릭 → 프로세스 선택 서브모달 열림 대기."""
        self.click_attached(self.SEL_TAG_ADD_PROC_BTN)
        self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.page.wait_for_timeout(300)

    def select_first_process_in_modal(self) -> str:
        """프로세스 선택 모달에서 첫 번째 프로세스 체크박스 선택 → 이름 반환."""
        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        if not rows:
            raise Exception("프로세스 선택 모달에 프로세스 없음")
        first_row = rows[0]
        proc_name = first_row.locator("td").nth(1).inner_text().strip()
        cb = first_row.locator("input[type='checkbox']").first
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        return proc_name

    def select_process_by_name(self, name: str) -> str:
        """프로세스 선택 모달에서 이름으로 검색 후 해당 항목 체크박스 선택 → 선택된 이름 반환.
        찾지 못하면 첫 번째 항목 선택 후 이름 반환 (fallback).
        """
        # 서브모달 검색창에 이름 입력 (있는 경우)
        try:
            search_input = self.page.locator(self.SEL_PROC_LIST_SEARCH)
            if search_input.count() > 0:
                search_input.first.evaluate(
                    "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                    name
                )
                self.page.wait_for_timeout(400)
        except Exception:
            pass

        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        if not rows:
            raise Exception(f"프로세스 선택 모달에 프로세스 없음 (검색어: {name!r})")

        # 이름 일치 행 찾기
        for row in rows:
            tds = row.locator("td").all()
            if len(tds) >= 2:
                row_name = tds[1].inner_text().strip()
                if row_name == name:
                    cb = row.locator("input[type='checkbox']").first
                    self._toggle_overlay(False)
                    try:
                        cb.click()
                    finally:
                        self._toggle_overlay(True)
                    return row_name

        # fallback: 첫 번째 항목 선택
        first_row = rows[0]
        proc_name = first_row.locator("td").nth(1).inner_text().strip()
        cb = first_row.locator("input[type='checkbox']").first
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        return proc_name

    def select_different_process_in_modal(self, exclude_name: str) -> str:
        """프로세스 선택 모달에서 프로세스 선택. 우선순위:
        1) [AUTO] 프로세스 검색 → 있으면 선택
        2) [AUTO] 없으면 exclude_name 이 아닌 첫 번째 프로세스 선택
        3) fallback: 첫 번째 항목 (중복 dedup 가능)
        선택된 프로세스 이름 반환."""

        def _click_row(row) -> str:
            proc_name = row.locator("td").nth(1).inner_text().strip()
            cb = row.locator("input[type='checkbox']").first
            self._toggle_overlay(False)
            try:
                cb.click()
            finally:
                self._toggle_overlay(True)
            return proc_name

        def _search_modal(keyword: str) -> None:
            try:
                si = self.page.locator(self.SEL_PROC_LIST_SEARCH)
                if si.count() > 0:
                    si.first.evaluate(
                        "(el, v) => { el.value = v;"
                        " el.dispatchEvent(new Event('input',{bubbles:true})); }",
                        keyword
                    )
                    self.page.wait_for_timeout(400)
            except Exception:
                pass

        # 1순위: [AUTO] 검색
        _search_modal("[AUTO]")
        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        for row in rows:
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[1].inner_text().strip().startswith("[AUTO]"):
                return _click_row(row)

        # 2순위: 검색 초기화 후 exclude_name 이 아닌 프로세스
        _search_modal("")
        rows = self.page.locator(self.SEL_PROC_LIST_ROW).all()
        if not rows:
            raise Exception("프로세스 선택 모달에 프로세스 없음")
        for row in rows:
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[1].inner_text().strip() != exclude_name:
                return _click_row(row)

        # fallback: 첫 번째 항목
        return _click_row(rows[0])

    def confirm_process_selection(self) -> None:
        """프로세스 선택 모달 확인 버튼 클릭 → 모달 닫힘 대기."""
        self.click_attached(self.SEL_PROC_LIST_CONFIRM)
        self.page.locator(self.SEL_PROC_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_TABLE
        )
        self.page.wait_for_timeout(200)

    def get_registered_process_names(self) -> list[str]:
        """수정 모달 내 등록된 프로세스 이름 목록 반환."""
        names = []
        for row in self.page.locator(self.SEL_PROC_TABLE_ROW).all():
            tds = row.locator("td").all()
            if len(tds) >= 2:
                name = tds[1].inner_text().strip()
                if name:
                    names.append(name)
        return names

    def remove_first_registered_process(self) -> None:
        """수정 모달 내 첫 번째 등록 프로세스 선택 → - 버튼 클릭."""
        rows = self.page.locator(self.SEL_PROC_TABLE_ROW).all()
        if not rows:
            raise Exception("등록된 프로세스 없음")
        cb = rows[0].locator("input[type='checkbox']").first
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        self.page.wait_for_timeout(100)
        self.click_attached(self.SEL_TAG_REMOVE_PROC_BTN)
        self.page.wait_for_timeout(300)

    def get_process_count_in_list(self, tag_name: str) -> int:
        """목록 페이지에서 태그의 프로세스 카운트 컬럼 값 반환."""
        self.search_item(tag_name)
        self.page.wait_for_timeout(300)
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if len(tds) >= 2 and tds[0].inner_text().strip() == tag_name:
                try:
                    return int(tds[1].inner_text().strip())
                except ValueError:
                    return 0
        return -1  # 태그 없음

    def search_item(self, keyword: str) -> None:
        """키워드로 검색 실행."""
        search = self.page.locator("input#searchText").first
        search.fill(keyword)
        self.page.locator("button#searchBtn").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(600)

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
