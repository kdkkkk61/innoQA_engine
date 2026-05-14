"""
pages/npouch_control_suite_page.py — nPouch 제어 스위트 관리 페이지

공통설정 > 전역정책 관리 > 제어 스위트 관리
scan_mode: modal_form
yaml: config/scan_hints/control_suite.yaml (v42)

설계:
  - 메인 페이지 (NpouchControlSuitePage) = 네비/list/메인 모달 책임
  - composition 으로 shared/ 컴포넌트 참조:
      self.process       = ProcessSubModal           (controlSuiteProcessList)
      self.web_restrict  = WebRestrictSubModal       (controlSuiteWebRestricList)
      self.picker        = ProcessPicker             (globalProcessList — 3 모드)
      self.special_folder= SpecialFolderPicker       (selectReservedWordControl)

ADD-EDIT 차이 (yaml inspection_notes):
  - 메인 모달 제목: "제어 스위트 추가" (ADD) / "제어 스위트 수정" (EDIT)
  - footer 버튼: "추가" / "수정"
  - EDIT 진입 = list 행 td#strProcessName.cursorPointer 클릭 후 modify_btn
  - csuName 빈값 메시지: "이름을 입력해 주세요." (ADD) / "정책 이름을 입력해 주세요." (EDIT)
"""
import time
from contextlib import contextmanager
from playwright.sync_api import Page

from pages.base_page import BasePage
from pages.shared.modals.process_sub_modal import ProcessSubModal
from pages.shared.modals.web_restrict_sub_modal import WebRestrictSubModal
from pages.shared.pickers.process_picker import ProcessPicker
from pages.shared.pickers.special_folder_picker import SpecialFolderPicker


@contextmanager
def _t(label: str):
    """TIMING 헬퍼 — [TIMING] {label} took {sec}s"""
    t0 = time.time()
    try:
        yield
    finally:
        print(f"[TIMING] {label} took {time.time()-t0:.2f}s")


class NpouchControlSuitePage(BasePage):
    # ==================================================================
    # 1. Selectors
    # ==================================================================

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_SYS_MGMT_ICON   = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST   = "ul.managerSystemManagementList"
    SEL_UNIFIED_HEADER  = "a.managerUnifiedPolicy"
    SEL_MENU_ITEM       = "a[data-menuid='managerControlSuite']"

    # ── list 페이지 ───────────────────────────────────────────────
    SEL_SEARCH_INPUT    = "input#searchText"
    SEL_SEARCH_BTN      = "button#searchBtn"
    SEL_ADD_BTN         = "button#addItemBtn"
    SEL_MODIFY_BTN      = "button#modifyItemBtn"
    SEL_COPY_BTN        = "button#copyItemBtn"
    SEL_DELETE_BTN      = "button#removeItemBtn"
    SEL_TABLE_ROW       = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE = "table tbody tr.tActive"
    SEL_ROW_CHECKBOX    = "input[type='checkbox'][list-checkbox-item]"
    SEL_ROW_NAME_CELL   = "td#strProcessName"   # cursorPointer — EDIT 진입 시 클릭

    # ── 메인 모달 (#controlSuite) ────────────────────────────────
    SEL_MODAL           = "div#controlSuite"
    SEL_MODAL_OPEN      = "div#controlSuite.in"
    SEL_MODAL_TITLE     = "div#controlSuite .modal-title"

    # 메인 필드
    SEL_CSU_NAME            = "input#csuName"

    # 클립보드 공유제한 (독립 — yaml clipboard_pair_independent)
    SEL_CLIPBOARD_RESTRICT  = "input#isClipboardRestrict"
    SEL_CLIPBOARD_URL       = "textarea#clipboardAllowUrl"

    # 네트워크 허용 (메인)
    SEL_NETWORK             = "input#isNetwork"

    # 제어할 확장자 — 라디오 + tag_input + 라벨 반응 span
    SEL_RADIO_ALLOW         = "input#ALLOW"
    SEL_RADIO_BLOCK         = "input#BLOCK"
    SEL_RADIO_REACT_SPAN    = "span#allowExtensionText"
    SEL_EXT_INPUT           = "input#allowExtensionInput"
    SEL_EXT_ADD             = "button#allowExtensionInputBtn"
    SEL_EXT_LIST            = "div#allowExtensionUl"
    SEL_EXT_LIST_TAG        = "div#allowExtensionUl button.tagInput"
    SEL_EXT_DELETE_ICON     = "i.extentionDeleteBtn"

    # 헤더 체크 기능 사용 (독립 체크박스 — 메인의 isHeaderCheck)
    SEL_HEADER_CHECK        = "input#isHeaderCheck"

    # 전자서명 예외처리
    SEL_SIGN_EXCEPT_TOGGLE  = "input#isSignExcept"
    SEL_SIGN_EXCEPT_INPUT   = "input#signExceptInput"
    SEL_SIGN_EXCEPT_BTN     = "button#signExceptBtn"
    SEL_SIGN_EXCEPT_LIST    = "div#signExceptUl"
    SEL_SIGN_EXCEPT_TAG     = "div#signExceptUl button.tagInput"

    # 프로세스별 제어 (sub-tab + +/-)
    SEL_TAB_INDIVIDUAL      = "div#controlSuite li a.userItemTitle[rel='process']"
    SEL_TAB_TAG             = "div#controlSuite li a.userItemTitle[rel='tag']"
    SEL_ACTIVE_SUB_TAB      = "div#controlSuite li.active a.userItemTitle"
    SEL_ADD_PROCESS_BTN     = "button#addCsuProcessBtn"
    SEL_REMOVE_PROCESS_BTN  = "button#removeCsuProcessBtn"
    SEL_ITEM_LIST           = "div#itemList"
    SEL_ITEM_LIST_ROW       = "div#itemList tbody tr"
    SEL_ITEM_LIST_NAME_CELL = "div#itemList tbody tr td#strProcessName"  # cursorPointer
    SEL_ITEM_TAG_LIST       = "div#itemTagList"
    SEL_ITEM_TAG_LIST_ROW   = "div#itemTagList tbody tr"

    # 웹 제한기능
    SEL_ADD_WEB_RESTRICT_BTN    = "button#addCsuWebRestrictBtn"
    SEL_REMOVE_WEB_RESTRICT_BTN = "button#removeCsuWebRestrictBtn"
    SEL_ITEM_WEB_LIST_ROW       = "div#controlSuite table tbody tr"   # 컨테이너 별도 분리 어려움
    SEL_WEB_NAME_CELL           = "td#webRestrictName"   # cursorPointer — EDIT 진입

    # 커스텀 옵션
    SEL_CUSTOM_OPTION       = "input#customOptionText"

    # 액션 버튼 (footer — ADD: '추가', EDIT: '수정')
    SEL_SUBMIT_ADD          = "div#controlSuite .btn.btn-primary:has-text('추가')"
    SEL_SUBMIT_MODIFY       = "div#controlSuite .btn.btn-primary:has-text('수정')"
    SEL_CANCEL_BTN          = "div#controlSuite .btn.btn-default"

    # ── 확인 모달 (전역) ─────────────────────────────────────────
    SEL_CONFIRM_MODAL       = "div#__globalMessageModal"
    SEL_CONFIRM_MODAL_OPEN  = "div#__globalMessageModal.in"
    SEL_CONFIRM_BODY        = "div#__globalMessageModal .modal-body"
    SEL_CONFIRM_BTN         = "div#__globalMessageModal button:has-text('확인')"

    # ── 타임아웃 ─────────────────────────────────────────────────
    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    # 정책 list pageSize 복원 해시 (필요 시)
    _HASH_PAGE_SIZE_100 = (
        "#!/managerControlSuite"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ==================================================================
    # 2. 생성 + composition
    # ==================================================================
    def __init__(self, page: Page, settings: dict):
        super().__init__(page, settings)
        # shared 컴포넌트 composition
        self.process        = ProcessSubModal(page)
        self.web_restrict   = WebRestrictSubModal(page)
        self.picker         = ProcessPicker(page)
        self.special_folder = SpecialFolderPicker(page)

    # ==================================================================
    # 3. 네비게이션
    # ==================================================================
    def navigate_to(self) -> None:
        """제어 스위트 관리 페이지로 진입.

        legacy pattern 그대로 — 시스템 관리 아이콘 → 전역정책 헤더 펼침 →
        managerControlSuite 메뉴 클릭 → hash URL 로 pageSize=100 보정.
        """
        self._dismiss_stale_confirm_modal()
        self._close_modal_if_open()

        # 이미 제어스위트 list + addBtn 보이면 skip
        if ("ControlSuite" in self.page.url
                and self.is_visible(self.SEL_ADD_BTN)):
            return

        # manager/main.html 로 진입 (좌측 nav 보장)
        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_SYS_MGMT_LIST).wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

        # 시스템 관리 아이콘 펼치기
        if not self.is_visible(self.SEL_SYS_MGMT_LIST):
            self.click(self.SEL_SYS_MGMT_ICON)
            self.wait_for(self.SEL_SYS_MGMT_LIST)

        # 전역정책 헤더 펼치기 (managerControlSuite 가 그 하위)
        if not self.is_visible(self.SEL_MENU_ITEM):
            try:
                self._click(self.page.locator(self.SEL_UNIFIED_HEADER).first)
                self.page.wait_for_timeout(300)
            except Exception:
                pass

        # 제어 스위트 메뉴 클릭
        self.click(self.SEL_MENU_ITEM)
        self.wait_for(self.SEL_ADD_BTN)

        # pageSize=100 보정
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

    # ==================================================================
    # 4. list 페이지 조작
    # ==================================================================
    def search(self, text: str) -> None:
        inp = self.page.locator(self.SEL_SEARCH_INPUT).first
        inp.click()
        inp.fill(text)
        inp.press("Enter")
        # 결과 표시 대기
        self.page.wait_for_timeout(500)

    def get_policy_names(self) -> list[str]:
        rows = self.page.locator(self.SEL_TABLE_ROW)
        out: list[str] = []
        for i in range(rows.count()):
            tds = rows.nth(i).locator("td")
            if tds.count() >= 2:
                out.append(tds.nth(1).inner_text().strip())
        return out

    def is_policy_exists(self, name: str) -> bool:
        return name in self.get_policy_names()

    def click_policy_row(self, name: str) -> None:
        """행 클릭 → tActive 부착 (EDIT 진입 사전 조건). yaml row_active_timing 메모 참조.

        tActive 는 mousedown 핸들러로 부착 — el.click() 은 mousedown 없어 미반응.
        overlay 잠시 끄고 force=True 좌표 클릭 사용 (MEMORY.md 규칙).
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        self._toggle_overlay(False)
        try:
            row.click(force=True)
        finally:
            self._toggle_overlay(True)
        row.wait_for(state="attached", timeout=self._TIMEOUT_TABLE)

    def check_policy_row(self, name: str) -> None:
        """행 체크박스 선택 (copy/delete 흐름용). JS 직접 호출 — overlay 무관."""
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        self._click(row.locator("input[type='checkbox']").first)
    def get_active_policy_name(self) -> str | None:
        active = self.page.locator(self.SEL_TABLE_ROW_ACTIVE).first
        if active.count() == 0:
            return None
        tds = active.locator("td")
        if tds.count() < 2:
            return None
        return tds.nth(1).inner_text().strip()

    # ==================================================================
    # 5. CRUD 흐름
    # ==================================================================
    def delete_all_auto_policies(self) -> None:
        """[AUTO] 접두사 정책 일괄 삭제 ([AUTO_KEEP] 제외)."""
        for name in self.get_policy_names():
            if name.startswith("[AUTO]") and not name.startswith("[AUTO_KEEP]"):
                self.delete_policy(name)

    def delete_policy(self, name: str) -> None:
        self.check_policy_row(name)
        self._click(self.page.locator(self.SEL_DELETE_BTN).first)
        # 삭제 확인 알림 처리
        self.dismiss_confirm_modal()

    # ==================================================================
    # 6. 메인 모달 진입/종료
    # ==================================================================
    def open_add_modal(self) -> None:
        # overlay 막힘 회피 — JS 직접 호출
        self._click(self.page.locator(self.SEL_ADD_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )

    def open_modify_modal(self, name: str) -> None:
        """행 active + modify_btn 클릭. yaml row_active_timing 이슈 시 reload 권장."""
        self.click_policy_row(name)
        self._click(self.page.locator(self.SEL_MODIFY_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )

    def close_modal(self) -> None:
        """× 또는 취소."""
        self._click(self.page.locator(self.SEL_CANCEL_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_MODAL
        )

    def get_modal_title(self) -> str:
        """ADD: '제어 스위트 추가' / EDIT: '제어 스위트 수정'."""
        return self.page.locator(self.SEL_MODAL_TITLE).first.inner_text().strip()

    def is_edit_mode(self) -> bool:
        return "수정" in self.get_modal_title()

    # ==================================================================
    # 7. 메인 모달 필드 조작
    # ==================================================================
    def set_csu_name(self, name: str) -> None:
        self.page.locator(self.SEL_CSU_NAME).first.fill(name)

    def get_csu_name(self) -> str:
        return self.page.locator(self.SEL_CSU_NAME).first.input_value()

    def set_clipboard_restrict_toggle(self, on: bool) -> None:
        self._set_toggle(self.SEL_CLIPBOARD_RESTRICT, on)

    def set_clipboard_allow_url(self, text: str) -> None:
        """textarea — 'naver.com;google.com' 같은 ; 구분 다중 입력 가능."""
        self.page.locator(self.SEL_CLIPBOARD_URL).first.fill(text)

    def set_network_toggle(self, on: bool) -> None:
        self._set_toggle(self.SEL_NETWORK, on)

    def click_radio_allow(self) -> None:
        """ALLOW (확장자 대상지정) — span = '차단할 확장자'"""
        self._click(self.page.locator(self.SEL_RADIO_ALLOW).first)
    def click_radio_block(self) -> None:
        """BLOCK (확장자 전체차단) — span = '허용할 확장자'"""
        self._click(self.page.locator(self.SEL_RADIO_BLOCK).first)
    def get_radio_react_text(self) -> str:
        return self.page.locator(self.SEL_RADIO_REACT_SPAN).first.inner_text().strip()

    def set_header_check(self, on: bool) -> None:
        self._set_toggle(self.SEL_HEADER_CHECK, on)

    def add_main_extension(self, ext: str) -> None:
        """메인 확장자 input + 추가. ';' 다중 구분자 일괄 등록 가능."""
        self.page.locator(self.SEL_EXT_INPUT).first.fill(ext)
        self._click(self.page.locator(self.SEL_EXT_ADD).first)
    def get_main_extension_list(self) -> list[str]:
        items = self.page.locator(self.SEL_EXT_LIST_TAG + " span")
        return [items.nth(i).inner_text().strip().split()[0] for i in range(items.count())]

    def delete_main_extension(self, ext: str) -> None:
        btn = self.page.locator(self.SEL_EXT_LIST_TAG).filter(has_text=ext).first
        self._click(btn.locator("i").first)
    def set_sign_except_toggle(self, on: bool) -> None:
        self._set_toggle(self.SEL_SIGN_EXCEPT_TOGGLE, on)

    def add_sign_except(self, sign: str) -> None:
        """전자서명 예외처리 input + 추가. 한글/영어 모두 허용."""
        self.page.locator(self.SEL_SIGN_EXCEPT_INPUT).first.fill(sign)
        self._click(self.page.locator(self.SEL_SIGN_EXCEPT_BTN).first)
    def get_sign_except_list(self) -> list[str]:
        items = self.page.locator(self.SEL_SIGN_EXCEPT_TAG)
        return [items.nth(i).inner_text().strip() for i in range(items.count())]

    def delete_sign_except(self, sign: str) -> None:
        btn = self.page.locator(self.SEL_SIGN_EXCEPT_TAG).filter(has_text=sign).first
        self._click(btn.locator("i").first)
    def set_custom_option(self, text: str) -> None:
        self.page.locator(self.SEL_CUSTOM_OPTION).first.fill(text)

    # ==================================================================
    # 8. 메인 모달 안 sub-tab + sub-modal 진입
    # ==================================================================
    def click_individual_process_tab(self) -> None:
        """프로세스별 제어 — 개별 프로세스 sub-tab."""
        self._click(self.page.locator(self.SEL_TAB_INDIVIDUAL).first)
    def click_tag_tab(self) -> None:
        """프로세스별 제어 — 태그 sub-tab."""
        self._click(self.page.locator(self.SEL_TAB_TAG).first)
    def get_active_sub_tab(self) -> str:
        """현재 활성 sub-tab 텍스트 — '개별 프로세스' / '태그'."""
        loc = self.page.locator(self.SEL_ACTIVE_SUB_TAB).first
        return loc.inner_text().strip() if loc.count() > 0 else ""

    def click_add_process_btn(self) -> None:
        """프로세스별 제어 + 버튼 → process_sub_modal 열림 (현 sub-tab 모드)."""
        self._click(self.page.locator(self.SEL_ADD_PROCESS_BTN).first)
        self.process.wait_open()

    def click_add_web_restrict_btn(self) -> None:
        """웹 제한기능 + 버튼 → web_restrict_sub_modal 열림."""
        self._click(self.page.locator(self.SEL_ADD_WEB_RESTRICT_BTN).first)
        self.web_restrict.wait_open()

    # ==================================================================
    # 9. itemList / itemTagList / itemWebRestrictList
    # ==================================================================
    def get_item_list_rows(self) -> list[str]:
        """개별 프로세스 itemList 행 텍스트."""
        rows = self.page.locator(self.SEL_ITEM_LIST_ROW)
        return [rows.nth(i).inner_text().strip() for i in range(rows.count())]

    def get_item_tag_list_rows(self) -> list[str]:
        rows = self.page.locator(self.SEL_ITEM_TAG_LIST_ROW)
        return [rows.nth(i).inner_text().strip() for i in range(rows.count())]

    def click_item_list_row(self, name: str) -> None:
        """itemList 행의 cursorPointer td 클릭 → process_sub_modal EDIT 모드."""
        td = self.page.locator(self.SEL_ITEM_LIST_NAME_CELL).filter(has_text=name).first
        td.click()
        self.process.wait_open()

    # ==================================================================
    # 10. 저장 / 확인 모달
    # ==================================================================
    def click_submit_add(self) -> None:
        """ADD 모드의 '추가' 버튼."""
        self._click(self.page.locator(self.SEL_SUBMIT_ADD).first)
    def click_submit_modify(self) -> None:
        """EDIT 모드의 '수정' 버튼."""
        self._click(self.page.locator(self.SEL_SUBMIT_MODIFY).first)
    def is_confirm_modal_visible(self) -> bool:
        return self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).count() > 0

    def get_confirm_message(self) -> str:
        """전역 알림 메시지 — 시나리오 2/3/4 검증 메시지 캡처용."""
        if not self.is_confirm_modal_visible():
            return ""
        return self.page.locator(self.SEL_CONFIRM_BODY).first.inner_text().strip()

    def dismiss_confirm_modal(self) -> None:
        if self.is_confirm_modal_visible():
            self._click(self.page.locator(self.SEL_CONFIRM_BTN).first)
            self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL
            )

    # ==================================================================
    # 11. 표준 인터페이스 (qa_runner 가 호출)
    # ==================================================================
    def save_policy(self, mode: str = "add") -> str:
        """
        메인 모달 저장.
        mode: 'add' → '추가' 버튼 / 'modify' → '수정' 버튼.
        return: 알림 메시지 (성공 시 "저장 하였습니다")
        """
        if mode == "add":
            self.click_submit_add()
        elif mode == "modify":
            self.click_submit_modify()
        else:
            raise ValueError(f"unknown mode: {mode}")
        self.page.wait_for_timeout(1500)   # 알림 출현 대기
        msg = self.get_confirm_message()
        self.dismiss_confirm_modal()
        return msg

    def close_edit_modal(self) -> None:
        """EDIT 모달 취소로 종료."""
        self.close_modal()

    def get_verify_values(self) -> dict:
        """EDIT 재오픈 시 정합성 비교용 — 메인 모달 전 필드."""
        return {
            "title":              self.get_modal_title(),
            "csu_name":           self.get_csu_name(),
            "clipboard_restrict": self.page.locator(self.SEL_CLIPBOARD_RESTRICT).first.is_checked(),
            "clipboard_url":      self.page.locator(self.SEL_CLIPBOARD_URL).first.input_value(),
            "is_network":         self.page.locator(self.SEL_NETWORK).first.is_checked(),
            "is_allow_extension": self.page.locator(self.SEL_RADIO_ALLOW).first.is_checked(),
            "is_block_extension": self.page.locator(self.SEL_RADIO_BLOCK).first.is_checked(),
            "radio_react_text":   self.get_radio_react_text(),
            "header_check":       self.page.locator(self.SEL_HEADER_CHECK).first.is_checked(),
            "main_extensions":    self.get_main_extension_list(),
            "is_sign_except":     self.page.locator(self.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked(),
            "sign_excepts":       self.get_sign_except_list(),
            "active_sub_tab":     self.get_active_sub_tab(),
            "item_list":          self.get_item_list_rows(),
            "item_tag_list":      self.get_item_tag_list_rows(),
            "custom_option":      self.page.locator(self.SEL_CUSTOM_OPTION).first.input_value(),
        }

    # ==================================================================
    # 12. 내부 헬퍼
    # ==================================================================
    def _set_toggle(self, selector: str, on: bool) -> None:
        cb = self.page.locator(selector).first
        if cb.is_checked() != on:
            cb.click()
