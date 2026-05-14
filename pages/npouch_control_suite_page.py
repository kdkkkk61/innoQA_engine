"""
pages/npouch_control_suite_page.py — nPouch 제어 스위트 관리

Step 1: navigate + open/close                              [완료]
Step 2: 메인 모달 단독 필드                                [완료]
Step 3a: process_sub_modal 진입/탈출 + sub-tab 전환        [현재]
Step 3b-d: picker / 필드 / 통합 save                       [예정]
Step 4: 웹제한 모달                                         [예정]

composition:
  self.process = ProcessSubModal(page)   (Step 3a~)
"""
from playwright.sync_api import Page
from pages.base_page import BasePage
from pages.shared.modals.process_sub_modal import ProcessSubModal
from pages.shared.modals.web_restrict_sub_modal import WebRestrictSubModal
from pages.shared.pickers.process_picker import ProcessPicker
from pages.shared.pickers.special_folder_picker import SpecialFolderPicker
from pages.shared._overlay import overlay_off


class NpouchControlSuitePage(BasePage):
    # ── 좌측 네비게이션 ─────────────────────────────────────────────
    SEL_SYS_MGMT_ICON   = "a[data-menuid='managerSystemManagement']"
    SEL_SYS_MGMT_LIST   = "ul.managerSystemManagementList"
    SEL_UNIFIED_HEADER  = "a.managerUnifiedPolicy"
    SEL_MENU_ITEM       = "a[data-menuid='managerControlSuite']"

    # ── list 페이지 ─────────────────────────────────────────────────
    SEL_ADD_BTN         = "button#addItemBtn"
    SEL_MODIFY_BTN      = "button#modifyItemBtn"
    SEL_DELETE_BTN      = "button#removeItemBtn"
    SEL_TABLE_ROW       = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE = "table tbody tr.tActive"
    SEL_ROW_CHECKBOX    = "input[type='checkbox'][list-checkbox-item]"
    # 정책명 셀 — cursorPointer (EDIT 진입 시 클릭) — yaml row_active_timing 참조
    SEL_ROW_NAME_CELL   = "td#strProcessName"

    # ── 메인 모달 ──────────────────────────────────────────────────
    SEL_MODAL           = "div#controlSuite"
    SEL_MODAL_OPEN      = "div#controlSuite.in"
    SEL_MODAL_TITLE     = "div#controlSuite .modal-title"
    SEL_CANCEL_BTN      = "div#controlSuite .btn.btn-default"

    # ── 메인 모달 단독 필드 (Step 2) ──────────────────────────────
    SEL_CSU_NAME            = "input#csuName"
    # 클립보드 공유제한 (독립)
    SEL_CLIPBOARD_RESTRICT  = "input#isClipboardRestrict"
    SEL_CLIPBOARD_URL       = "textarea#clipboardAllowUrl"
    # 네트워크 허용
    SEL_NETWORK             = "input#isNetwork"
    # 제어할 확장자 (라디오 + tag_input)
    SEL_RADIO_ALLOW         = "input#ALLOW"
    SEL_RADIO_BLOCK         = "input#BLOCK"
    SEL_RADIO_REACT_SPAN    = "span#allowExtensionText"
    SEL_EXT_INPUT           = "input#allowExtensionInput"
    SEL_EXT_ADD             = "button#allowExtensionInputBtn"
    SEL_EXT_LIST_TAG        = "div#allowExtensionUl button.tagInput"
    # 헤더 체크 (독립)
    SEL_HEADER_CHECK        = "input#isHeaderCheck"
    # 전자서명 예외처리
    SEL_SIGN_EXCEPT_TOGGLE  = "input#isSignExcept"
    SEL_SIGN_EXCEPT_INPUT   = "input#signExceptInput"
    SEL_SIGN_EXCEPT_BTN     = "button#signExceptBtn"
    SEL_SIGN_EXCEPT_TAG     = "div#signExceptUl button.tagInput"
    # 커스텀 옵션
    SEL_CUSTOM_OPTION       = "input#customOptionText"

    # ── 프로세스별 제어 sub-tab + + 버튼 (Step 3a) ────────────────
    SEL_TAB_INDIVIDUAL      = "div#controlSuite li a.userItemTitle[rel='process']"
    SEL_TAB_TAG             = "div#controlSuite li a.userItemTitle[rel='tag']"
    SEL_ACTIVE_SUB_TAB      = "div#controlSuite li.active a.userItemTitle"
    SEL_ADD_PROCESS_BTN     = "button#addCsuProcessBtn"

    # ── 메인 모달의 itemList (등록된 프로세스/태그 행 — Step 3d) ──
    SEL_ITEM_LIST_ROW       = "div#itemList tbody tr"
    SEL_ITEM_TAG_LIST_ROW   = "div#itemTagList tbody tr"
    # 웹제한 컨테이너 — yaml 의 itemWebRestrictList 가 아니라 csuWebRestrictListTb
    # ⚠ csuWebRestrictListTb 는 div 가 아니라 TBODY 자체 (DOM enumeration 확인).
    #   tag prefix 없이 #id > tr 직접 매칭 필요.
    SEL_ITEM_WEB_LIST_ROW   = "#csuWebRestrictListTb tr"

    # ── 웹 제한기능 + 버튼 (Step 4a) ──────────────────────────────
    SEL_ADD_WEB_RESTRICT_BTN = "button#addCsuWebRestrictBtn"

    # ── 메인 저장 (Step 3d) ──────────────────────────────────────
    SEL_SUBMIT_ADD          = "div#controlSuite .btn.btn-primary:has-text('추가')"
    SEL_SUBMIT_MODIFY       = "div#controlSuite .btn.btn-primary:has-text('수정')"

    # ── 확인 모달 (stale dismiss) ─────────────────────────────────
    # 알림(확인) 모달 — 2 종류 동시 지원:
    #   1) __globalMessageModal : 메인 모달 confirm (스위트 이름 빈값/중복, 저장 메시지 등)
    #   2) registeredFolderWarning : sub-modal 내부 검증 알림 (IP/Port/확장자/URL 중복 등)
    # Chrome MCP 2026-05-18 검증 — sub-modal 알림은 #registeredFolderWarning 사용 + .modal-body-text
    SEL_CONFIRM_MODAL       = "div#__globalMessageModal, div#registeredFolderWarning"
    SEL_CONFIRM_MODAL_OPEN  = "div#__globalMessageModal.in, div#registeredFolderWarning.in"
    SEL_CONFIRM_BTN         = ("div#__globalMessageModal.in button:has-text('확인'), "
                               "div#registeredFolderWarning.in button.btn-default")
    SEL_CONFIRM_BODY        = ("div#__globalMessageModal .modal-body, "
                               "div#registeredFolderWarning .modal-body-text")

    # ── 타임아웃 ──────────────────────────────────────────────────
    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _HASH_PAGE_SIZE_100 = (
        "#!/managerControlSuite"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ==================================================================
    # 0. 생성 + composition
    # ==================================================================
    def __init__(self, page: Page, settings: dict):
        super().__init__(page, settings)
        # shared 컴포넌트 — 단계별로 추가
        self.process        = ProcessSubModal(page)
        self.web_restrict   = WebRestrictSubModal(page)
        self.picker         = ProcessPicker(page)
        self.special_folder = SpecialFolderPicker(page)

    # ==================================================================
    # 1. 네비게이션
    # ==================================================================
    def navigate_to(self) -> None:
        """
        제어 스위트 관리 페이지로 진입.

        흐름 (legacy 검증된 패턴):
          1. stale confirm modal / 열린 메인 모달 정리
          2. URL 이미 ControlSuite + addBtn visible 이면 skip
          3. manager/main.html 진입 보장
          4. 시스템 관리 아이콘 펼침 (managerSystemManagementList visible 대기)
          5. 전역정책 헤더 펼침 (managerControlSuite 메뉴가 visible 되도록)
          6. 제어 스위트 메뉴 클릭 → addBtn 대기
          7. hash 로 pageSize=100 보정
        """
        self._dismiss_stale_confirm_modal()
        # 이전 테스트에서 남은 sub-modal 정리 (picker / web_restrict / process_modal)
        self._close_leftover_submodals()
        self._close_modal_if_open()

        if ("ControlSuite" in self.page.url
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
                self._click(self.page.locator(self.SEL_UNIFIED_HEADER).first)
                self.page.wait_for_timeout(300)
            except Exception:
                pass

        self.click(self.SEL_MENU_ITEM)
        self.wait_for(self.SEL_ADD_BTN)

        # pageSize=100 보정 (이미 도착해 있어도 안전)
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)

    # ==================================================================
    # 2. 메인 모달 진입 / 탈출
    # ==================================================================
    def open_add_modal(self) -> None:
        """addBtn 클릭 → 메인 모달 #controlSuite.in attached 대기."""
        self._click(self.page.locator(self.SEL_ADD_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )

    def get_modal_title(self) -> str:
        return self.page.locator(self.SEL_MODAL_TITLE).first.inner_text().strip()

    def close_modal(self) -> None:
        """취소 버튼 클릭 → 메인 모달 detached 대기."""
        self._click(self.page.locator(self.SEL_CANCEL_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_MODAL
        )

    # ==================================================================
    # 3. 메인 모달 단독 필드 (Step 2)
    # ==================================================================

    # ── csuName ─────────────────────────────────────────────────────
    def set_csu_name(self, name: str) -> None:
        self.page.locator(self.SEL_CSU_NAME).first.fill(name)

    def get_csu_name(self) -> str:
        return self.page.locator(self.SEL_CSU_NAME).first.input_value()

    # ── 클립보드 공유제한 ───────────────────────────────────────────
    def set_clipboard_restrict_toggle(self, on: bool) -> None:
        self._set_toggle(self.SEL_CLIPBOARD_RESTRICT, on)

    def set_clipboard_allow_url(self, text: str) -> None:
        self.page.locator(self.SEL_CLIPBOARD_URL).first.fill(text)

    def get_clipboard_allow_url(self) -> str:
        return self.page.locator(self.SEL_CLIPBOARD_URL).first.input_value()

    # ── 네트워크 허용 ───────────────────────────────────────────────
    def set_network_toggle(self, on: bool) -> None:
        self._set_toggle(self.SEL_NETWORK, on)

    def is_network_checked(self) -> bool:
        return self.page.locator(self.SEL_NETWORK).first.is_checked()

    # ── 제어할 확장자 ───────────────────────────────────────────────
    # 라디오 input 자체는 hidden (Bootstrap 스타일) → _click_hidden 사용
    def click_radio_allow(self) -> None:
        """ALLOW → 차단할 확장자 (대상 지정)."""
        self._click_hidden(self.page.locator(self.SEL_RADIO_ALLOW).first)

    def click_radio_block(self) -> None:
        """BLOCK → 허용할 확장자 (전체 차단)."""
        self._click_hidden(self.page.locator(self.SEL_RADIO_BLOCK).first)

    def get_radio_react_text(self) -> str:
        """span#allowExtensionText 텍스트 — 라디오 반응 검증."""
        return self.page.locator(self.SEL_RADIO_REACT_SPAN).first.inner_text().strip()

    def add_main_extension(self, ext: str) -> None:
        """확장자 입력 + 추가. ';' 다중 구분자 일괄 등록 가능."""
        self.page.locator(self.SEL_EXT_INPUT).first.fill(ext)
        self._click(self.page.locator(self.SEL_EXT_ADD).first)

    def get_main_extension_list(self) -> list[str]:
        items = self.page.locator(self.SEL_EXT_LIST_TAG + " span")
        return [
            items.nth(i).inner_text().strip().split()[0]
            for i in range(items.count())
        ]

    def remove_main_extension(self, ext: str) -> bool:
        """메인 모달 확장자 tag 1건 삭제 (× 버튼). 삭제 성공 시 True.

        AngularJS ng-click 패턴 — Playwright click 으로 trusted event 미발화 가능 →
        JS evaluate 클릭 (el.click()) 으로 ng-click 정상 트리거.
        """
        tags = self.page.locator(self.SEL_EXT_LIST_TAG)
        cnt = tags.count()
        for i in range(cnt):
            text = tags.nth(i).inner_text().strip()
            if text.startswith(ext + " ") or text == ext or text.split()[0] == ext:
                tags.nth(i).evaluate("el => el.click()")
                return True
        return False

    # ── 헤더 체크 ───────────────────────────────────────────────────
    def set_header_check(self, on: bool) -> None:
        self._set_toggle(self.SEL_HEADER_CHECK, on)

    # ── 전자서명 예외처리 ──────────────────────────────────────────
    def set_sign_except_toggle(self, on: bool) -> None:
        self._set_toggle(self.SEL_SIGN_EXCEPT_TOGGLE, on)

    def add_sign_except(self, text: str) -> None:
        self.page.locator(self.SEL_SIGN_EXCEPT_INPUT).first.fill(text)
        self._click(self.page.locator(self.SEL_SIGN_EXCEPT_BTN).first)

    def get_sign_except_list(self) -> list[str]:
        items = self.page.locator(self.SEL_SIGN_EXCEPT_TAG + " span")
        return [
            items.nth(i).inner_text().strip().split()[0]
            for i in range(items.count())
        ]

    # ── 커스텀 옵션 ─────────────────────────────────────────────────
    def set_custom_option(self, text: str) -> None:
        self.page.locator(self.SEL_CUSTOM_OPTION).first.fill(text)

    def get_custom_option(self) -> str:
        return self.page.locator(self.SEL_CUSTOM_OPTION).first.input_value()

    # ==================================================================
    # 3.5 프로세스별 제어 sub-tab + + 버튼 (Step 3a)
    # ==================================================================
    def click_individual_process_tab(self) -> None:
        """'개별 프로세스' sub-tab 클릭."""
        self._click(self.page.locator(self.SEL_TAB_INDIVIDUAL).first)

    def click_tag_tab(self) -> None:
        """'태그' sub-tab 클릭."""
        self._click(self.page.locator(self.SEL_TAB_TAG).first)

    def get_active_sub_tab_text(self) -> str:
        """현재 활성 sub-tab 텍스트 (디버깅용)."""
        loc = self.page.locator(self.SEL_ACTIVE_SUB_TAB).first
        return loc.inner_text().strip() if loc.count() > 0 else ""

    def click_add_process_btn(self) -> None:
        """'+' 버튼 클릭 → process_sub_modal 열림."""
        self._click(self.page.locator(self.SEL_ADD_PROCESS_BTN).first)

    def click_add_web_restrict_btn(self) -> None:
        """'웹 제한기능' + 버튼 → web_restrict_sub_modal 열림 (Step 4a)."""
        self._click(self.page.locator(self.SEL_ADD_WEB_RESTRICT_BTN).first)

    # ==================================================================
    # 3.6 메인 모달 itemList 조회 + 저장 (Step 3d)
    # ==================================================================
    def get_item_list_rows(self) -> list[str]:
        """개별 프로세스 sub-tab 의 itemList 행 텍스트."""
        rows = self.page.locator(self.SEL_ITEM_LIST_ROW)
        return [rows.nth(i).inner_text().strip() for i in range(rows.count())]

    def get_item_tag_list_rows(self) -> list[str]:
        """태그 sub-tab 의 itemTagList 행 텍스트."""
        rows = self.page.locator(self.SEL_ITEM_TAG_LIST_ROW)
        return [rows.nth(i).inner_text().strip() for i in range(rows.count())]

    def click_item_list_row(self, index: int = 0) -> None:
        """개별 프로세스 itemList 의 index 번 행 클릭 → process_modal EDIT 진입.
        legacy yaml: td#strProcessName.cursorPointer 또는 행 전체 클릭으로 EDIT.
        """
        row = self.page.locator(self.SEL_ITEM_LIST_ROW).nth(index)
        # cursorPointer cell 우선, 없으면 행 자체
        cell = row.locator("td#strProcessName, td.cursorPointer").first
        target = cell if cell.count() > 0 else row
        self._toggle_overlay(False)
        try:
            target.click(force=True)
        finally:
            self._toggle_overlay(True)
        # process_modal EDIT 진입 대기
        try:
            self.page.locator(self.process.SEL_MODAL_OPEN).first.wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

    def click_item_tag_list_row(self, index: int = 0) -> None:
        """태그 itemTagList 의 index 번 행 클릭 → process_modal (태그 모드) EDIT 진입."""
        row = self.page.locator(self.SEL_ITEM_TAG_LIST_ROW).nth(index)
        cell = row.locator("td.cursorPointer").first
        target = cell if cell.count() > 0 else row
        self._toggle_overlay(False)
        try:
            target.click(force=True)
        finally:
            self._toggle_overlay(True)
        try:
            self.page.locator(self.process.SEL_MODAL_OPEN).first.wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

    def click_item_web_restrict_row(self, index: int = 0) -> None:
        """웹제한 itemWebRestrictList 의 index 번 행 클릭 → web_restrict_modal 재진입.
        yaml: web_restrict_no_edit_branch — EDIT 분기 없음, ADD 흐름이지만 기존 값 로드.
        """
        row = self.page.locator(self.SEL_ITEM_WEB_LIST_ROW).nth(index)
        cell = row.locator("td#webRestrictName, td.cursorPointer").first
        target = cell if cell.count() > 0 else row
        self._toggle_overlay(False)
        try:
            target.click(force=True)
        finally:
            self._toggle_overlay(True)
        try:
            self.page.locator(self.web_restrict.SEL_MODAL_OPEN).first.wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

    def get_item_web_restrict_rows(self) -> list[str]:
        """웹 제한기능의 itemWebRestrictList 행 텍스트.
        AngularJS 렌더링 지연 대비 첫 row attached 짧게 대기."""
        try:
            self.page.locator(self.SEL_ITEM_WEB_LIST_ROW).first.wait_for(
                state="attached", timeout=2000
            )
        except Exception:
            pass
        rows = self.page.locator(self.SEL_ITEM_WEB_LIST_ROW)
        out: list[str] = []
        for i in range(rows.count()):
            txt = rows.nth(i).inner_text().strip()
            if txt and "없습니다" not in txt:
                out.append(txt)
        return out

    def diag_web_restrict_state(self) -> dict:
        """web_restrict.confirm() 직후 진단용 상태 dump."""
        # csuWebRestrictListTb 의 실제 구조 확인
        wr_tb_info = self.page.evaluate("""
            () => {
                const el = document.querySelector('#csuWebRestrictListTb');
                if (!el) return {exists: false};
                return {
                    exists: true,
                    tag: el.tagName,
                    classes: el.className,
                    parent_tag: el.parentElement ? el.parentElement.tagName : null,
                    children_tags: Array.from(el.children).map(c => c.tagName + (c.id ? '#'+c.id : '')),
                    descendant_tr_count: el.querySelectorAll('tr').length,
                    direct_tr_count: Array.from(el.children).filter(c => c.tagName === 'TR').length,
                    descendant_button_count: el.querySelectorAll('button').length,
                    inner_html_first_500: (el.innerHTML || '').substring(0, 500)
                };
            }
        """)
        return {
            "url": self.page.url,
            "main_modal_open":     self.page.locator(self.SEL_MODAL_OPEN).count() > 0,
            "web_restrict_open":   self.page.locator(
                "div#controlSuiteWebRestricList.in"
            ).count() > 0,
            "confirm_modal_open":  self.is_confirm_modal_visible(),
            "confirm_message":     (
                self.get_confirm_message()
                if self.is_confirm_modal_visible() else ""
            ),
            "csuWebRestrictListTb": wr_tb_info,
        }

    def save_policy(self, mode: str = "add") -> str:
        """
        '추가' / '수정' 버튼 클릭 → confirm modal 메시지 반환.
        호출 후 dismiss_confirm_modal() 별도 호출 필요.
        mode: 'add' or 'modify'
        """
        sel = self.SEL_SUBMIT_ADD if mode == "add" else self.SEL_SUBMIT_MODIFY
        self._click(self.page.locator(sel).first)
        self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        return self.get_confirm_message()

    # ==================================================================
    # 3.7 정책 list (메인 페이지 — 모달 닫힘 후) (Step 3d)
    # ==================================================================
    def get_policy_names(self) -> list[str]:
        """list 페이지 행의 첫 td (정책 이름) 추출. 빈 결과 메시지 제외."""
        names: list[str] = []
        rows = self.page.locator(self.SEL_TABLE_ROW)
        for i in range(rows.count()):
            tds = rows.nth(i).locator("td")
            if tds.count() == 0:
                continue
            name = tds.first.inner_text().strip()
            if name and "없습니다" not in name:
                names.append(name)
        return names

    def is_policy_exists(self, name: str) -> bool:
        return name in self.get_policy_names()

    def check_policy_row(self, name: str) -> None:
        """행 체크박스 선택. checkbox 는 visible — JS 클릭."""
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        cb = row.locator(self.SEL_ROW_CHECKBOX).first
        self._click_hidden(cb)

    def click_policy_row(self, name: str) -> None:
        """
        EDIT 진입 사전조건 — 행 자체 클릭 → tActive 부착 (mousedown 필요).
        legacy 검증된 패턴: overlay OFF + row.click(force=True) — 좌표 클릭으로 mousedown 발생.
        ⚠ td#strProcessName 은 modal 안 itemList 의 cell ID — 메인 list 에는 없음.
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=name).first
        self._toggle_overlay(False)
        try:
            row.click(force=True)
        finally:
            self._toggle_overlay(True)
        # tActive 부착 대기
        try:
            self.page.locator(self.SEL_TABLE_ROW_ACTIVE).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    def open_modify_modal(self, name: str) -> None:
        """행 active + modifyItemBtn 클릭 → EDIT 모달 열림."""
        self.click_policy_row(name)
        self._click(self.page.locator(self.SEL_MODIFY_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )

    def is_edit_mode(self) -> bool:
        """모달 제목에 '수정' 포함 여부."""
        return "수정" in self.get_modal_title()

    def delete_policy(self, name: str) -> None:
        """check + 삭제 버튼 + confirm 확인."""
        self.check_policy_row(name)
        self._click(self.page.locator(self.SEL_DELETE_BTN).first)
        # 확인 모달 ('삭제 하시겠습니까?' 등) — 확인 버튼
        self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        self.dismiss_confirm_modal()
        # 두 번째 confirm ('삭제 하였습니다') — 있으면 dismiss
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.dismiss_confirm_modal()
        except Exception:
            pass

    def delete_all_auto_policies(self) -> int:
        """[AUTO]_ 접두사 정책 일괄 삭제 ([AUTO_KEEP]_ 제외).

        용도: 연결된 의존 테스트 (이전 테스트의 KEEP 데이터를 받아 쓰는 경우).
        예: 시나리오 4 가 시나리오 3 의 [AUTO_KEEP]_ 정책 사용.
        """
        deleted = 0
        while True:
            names = [
                n for n in self.get_policy_names()
                if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")
            ]
            if not names:
                break
            self.delete_policy(names[0])
            deleted += 1
        return deleted

    def delete_all_test_data(self) -> int:
        """[AUTO]_ + [AUTO_KEEP]_ 모두 일괄 삭제. 강력 cleanup.

        용도: 기본 cleanup — 자기 영역 깨끗히 시작 / 마지막 전체 청소.
        주의: 다음 테스트가 KEEP 데이터에 의존하는 경우 사용 금지.
        """
        deleted = 0
        while True:
            names = [
                n for n in self.get_policy_names()
                if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")
            ]
            if not names:
                break
            self.delete_policy(names[0])
            deleted += 1
        return deleted

    # ==================================================================
    # 4. 확인 (전역 메시지) 모달 처리
    # ==================================================================
    def is_confirm_modal_visible(self, timeout: int = 1500) -> bool:
        """알림 모달 (__globalMessageModal 또는 registeredFolderWarning) 노출 여부.

        attached state 까지 timeout(ms) 만큼 명시 대기 후 판단 (race condition 방어).
        """
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                state="attached", timeout=timeout
            )
            return True
        except Exception:
            return False

    def get_confirm_message(self) -> str:
        """알림 모달 메시지 — 메인 confirm + sub-modal warning 두 종류 모두 처리."""
        # visible 한 첫 modal-body 텍스트
        loc = self.page.locator(self.SEL_CONFIRM_BODY)
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
        """알림 모달 '확인' 클릭 + 닫힘 대기.
        3-stack (main → sub-modal → alert) 환경에서 backdrop 이 click 가로채는 케이스 →
        Playwright click 3s 시도 후 실패 시 JS evaluate click 으로 fallback.
        """
        btn = self.page.locator(self.SEL_CONFIRM_BTN).first
        try:
            with overlay_off(self.page):
                btn.click(timeout=3000)
        except Exception:
            # backdrop intercept fallback — JS evaluate click (좌표 무관)
            btn.evaluate("el => el.click()")
        self.page.locator(self.SEL_CONFIRM_MODAL_OPEN).wait_for(
            state="detached", timeout=self._TIMEOUT_MODAL
        )

    # ==================================================================
    # 5. 내부 헬퍼
    # ==================================================================
    def _set_toggle(self, selector: str, on: bool) -> None:
        """
        Bootstrap toggle 패턴: 실제 checkbox input 은 hidden, 보이는 건 라벨.
        좌표 클릭 불가 → JS evaluate (visible 여부 무관).
        """
        cb = self.page.locator(selector).first
        if cb.is_checked() != on:
            self._click_hidden(cb)

    def _close_leftover_submodals(self) -> None:
        """이전 테스트 실패로 남은 sub-modal 정리 — picker / web_restrict / process_modal.
        ESC 키로 닫기 시도 + JS 강제 제거 (backdrop 까지)."""
        # 1) ESC 다발 (안쪽 모달부터)
        for _ in range(5):
            try:
                if (self.page.locator("div.modal-wrap.in").count() > 0
                        or self.page.locator("div.modal-backdrop.in").count() > 0):
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(150)
                else:
                    break
            except Exception:
                break

        # 2) 그래도 남으면 JS 로 강제 제거 (Bootstrap modal API)
        try:
            self.page.evaluate("""
                () => {
                    // 모든 열린 modal 강제 닫기
                    document.querySelectorAll('div.modal-wrap.in, div.modal.in').forEach(m => {
                        m.classList.remove('in');
                        m.style.display = 'none';
                    });
                    // backdrop 제거
                    document.querySelectorAll('div.modal-backdrop').forEach(b => b.remove());
                    // body 의 modal-open 클래스 제거 (스크롤 복구)
                    document.body.classList.remove('modal-open');
                }
            """)
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL_OPEN).count() > 0:
                self._click(self.page.locator(self.SEL_CANCEL_BTN).first)
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
