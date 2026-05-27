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
    SEL_EXT_LIST_TAG        = "div#allowExtensionUl button.tagInput:visible"
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

    # ── itemList 행 전체 삭제 (헤더 체크박스 전체선택 + 삭제 버튼) — Chrome MCP 2026-05-27 검증 ──
    # ⚠ 모달 스코프 (div#controlSuite) 필수 — list 페이지의 button#removeItemBtn (정책 삭제) 과
    #   ID 충돌 회피. 모달 안 삭제 버튼은 removeCsuProcessBtn (프로세스/태그 공용) / removeCsuWebRestrictBtn.
    SEL_ITEM_LIST_HEADER_CHK = "div#controlSuite input#listHeaderCheckBox"
    SEL_ITEM_TAG_HEADER_CHK  = "div#controlSuite input#listTagHeaderCheckBox"
    SEL_ITEM_WEB_HEADER_CHK  = "div#controlSuite input#listWebRestrictHeaderCheckBox"
    SEL_REMOVE_ITEM_BTN      = "div#controlSuite button#removeCsuProcessBtn"      # 개별 프로세스 삭제 (모달 안)
    SEL_REMOVE_TAG_BTN       = "div#controlSuite button#removeCsuProcessBtn"      # 태그 삭제 (탭 전환 후 동일 버튼)
    SEL_REMOVE_WEB_BTN       = "div#controlSuite button#removeCsuWebRestrictBtn"  # 웹제한 삭제 (모달 안)

    # ── 웹 제한기능 + 버튼 (Step 4a) ──────────────────────────────
    SEL_ADD_WEB_RESTRICT_BTN = "button#addCsuWebRestrictBtn"

    # ── 메인 저장 (Step 3d) ──────────────────────────────────────
    SEL_SUBMIT_ADD          = "div#controlSuite .btn.btn-primary:has-text('추가')"
    SEL_SUBMIT_MODIFY       = "div#controlSuite .btn.btn-primary:has-text('수정')"

    # ── 확인 모달 (stale dismiss) ─────────────────────────────────
    # 알림(확인) 모달 — 5 종류 동시 지원:
    #   1) __globalMessageModal : 메인 모달 confirm (스위트 이름 빈값/중복, 저장 메시지 등)
    #   2) registeredFolderWarning : sub-modal 내부 중복 알림 (IP/Port/확장자/URL 중복 등)
    #   3) nullEnteredWarning : input 빈값 또는 invalid 입력 자동 reset 알림 (Chrome MCP 2026-05-19 본서버 발견)
    #      예: "허용할 IP를 입력해주세요" — invalid IP 입력 시 input reset → 빈값 알림
    #   4) registeredProcessExtentionWarning : process picker 중복 / 확장자 중복 알림 (Chrome MCP 2026-05-19 본서버 발견)
    #      예: "이미 등록된 프로세스 입니다" — yaml :1234 의 modal_id 가 잘못 기록 (실제 ID 는 별도)
    #   5) registeredTagExtentionWarning : tag picker 중복 알림 (Chrome MCP 2026-05-26 sc4 4e fail 진단)
    #      예: "이미 등록된 태그 입니다" — sc3c 가 이미 첫 태그 등록한 정책에 sc4 가 같은 picker 첫 행 재선택 시
    #      → 이 ID 가 우리 SEL 에 없어서 sc4 가 알림 못 잡음 → picker stuck → wait_closed timeout cascade
    SEL_CONFIRM_MODAL       = ("div#__globalMessageModal, div#registeredFolderWarning, "
                                "div#nullEnteredWarning, div#registeredProcessExtentionWarning, "
                                "div#registeredTagExtentionWarning")
    SEL_CONFIRM_MODAL_OPEN  = ("div#__globalMessageModal.in, "
                               "div#registeredFolderWarning.in, "
                               "div#nullEnteredWarning.in, "
                               "div#registeredProcessExtentionWarning.in, "
                               "div#registeredTagExtentionWarning.in")
    SEL_CONFIRM_BTN         = ("div#__globalMessageModal.in button:has-text('확인'), "
                               "div#registeredFolderWarning.in button.btn-default, "
                               "div#nullEnteredWarning.in button.btn-default, "
                               "div#registeredProcessExtentionWarning.in button.btn-default, "
                               "div#registeredTagExtentionWarning.in button.btn-default")
    SEL_CONFIRM_BODY        = ("div#__globalMessageModal .modal-body, "
                               "div#registeredFolderWarning .modal-body-text, "
                               "div#nullEnteredWarning .modal-body-text, "
                               "div#nullEnteredWarning .modal-body, "
                               "div#registeredProcessExtentionWarning .modal-body-text, "
                               "div#registeredProcessExtentionWarning .modal-body, "
                               "div#registeredTagExtentionWarning .modal-body-text, "
                               "div#registeredTagExtentionWarning .modal-body")

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
    def _cleanup_modal_backdrop(self) -> None:
        """Bootstrap 3 modal 잔해 정리 — 조건부: 열린 modal-wrap.in 이 없을 때만 실행.

        진단 결과 (2026-05-20):
        sc3g fail 원인 = 무조건 cleanup 이 새 모달의 'body.modal-open' 을 떼서
        Bootstrap 이 즉시 .in 제거 → modal display:none → input not visible.

        Karpathy 원칙: 동작 중인 modal 건드리지 않기. 정말 stale 잔해만 정리.
        """
        try:
            self.page.evaluate("""
                () => {
                    // 열린 modal-wrap.in 이 하나라도 있으면 cleanup 스킵 (정상 modal 보호)
                    const open = document.querySelectorAll('div.modal-wrap.in, div.modal.in').length;
                    if (open > 0) return 'skip: modal open';
                    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                    document.body.classList.remove('modal-open');
                    document.body.style.paddingRight = '';
                    return 'cleaned';
                }
            """)
        except Exception:
            pass

    def navigate_to_clean(self) -> None:
        """F5 reload + navigate_to — 테스트 내부 case 전환 시 깨끗한 상태 보장.

        진단 결과 (sc3i / sc3j cascade fail):
        - 테스트 끝 F5 만으로는 부족 — 한 테스트 안에 여러 modal open/close 사이클이
          AngularJS Bootstrap modal directive 내부 state 누적 → 4번째 / 5번째 open 에서
          modal element 가 .in 잠깐 붙었다 박탈 → display:none → fill timeout.
        - F5 reload 가 가장 확실한 정리. user 의도: "f5 쓴경우 모달 찌꺼기 싹 날라간다".
        - 이 메서드는 case 사이에서만 호출. 테스트 시작 시는 navigate_to() 사용 (F5 불필요).
        """
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=15000)
            self.page.wait_for_timeout(500)
        except Exception:
            pass
        self.navigate_to()

    def navigate_to(self) -> None:
        """제어 스위트 관리 페이지로 진입.

        cascade fail 진단 결과 (2026-05-20):
        - 이전 테스트 끝 modal.in 은 닫혔지만 .modal-backdrop div + body.modal-open
          클래스가 잔존 → 다음 테스트 input fill timeout (backdrop pointer-events 차단)
        - 진입 직후 + alert dismiss 후 + modal close 후 backdrop cleanup
          (reload 미봉책이 아닌 잔해만 surgical 제거 — Karpathy 원칙 준수)
        """
        # _cleanup_modal_backdrop() 호출 제거 — 사용자 평가: 추가 cleanup 이 cascade 트리거 가능성.
        # F5 reload (teardown) 만으로 깨끗한 상태 유지. (2026-05-20 진단 결과)
        # self._cleanup_modal_backdrop()
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
        """addBtn 클릭 → 메인 모달 #controlSuite.in attached 대기.

        진단 (2026-05-20 sc3g hang): .in 부착 후 input#csuName 비가시 케이스 dump.
        backdrop 이 visibility 차단 안 함 → 다른 원인 (parent display / z-index 가림)
        가능성 확인용 인라인 dump.
        """
        self._click(self.page.locator(self.SEL_ADD_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        # ── 진단: 모달 .in 부착 후 csuName 실제 가시성 / parent state dump ─
        try:
            diag = self.page.evaluate("""
                () => {
                    const m = document.querySelector('div#controlSuite');
                    const inp = document.querySelector('input#csuName');
                    if (!inp) return {error: 'csuName not in DOM'};
                    const r = inp.getBoundingClientRect();
                    const cs = getComputedStyle(inp);
                    const mcs = m ? getComputedStyle(m) : null;
                    // 위에 가리는 element 확인 (input 중앙 좌표 elementFromPoint)
                    const cx = r.left + r.width/2;
                    const cy = r.top + r.height/2;
                    const top = document.elementFromPoint(cx, cy);
                    return {
                        modal_classes: m ? m.className : null,
                        modal_display: mcs ? mcs.display : null,
                        modal_visibility: mcs ? mcs.visibility : null,
                        input_rect: {x:r.x|0, y:r.y|0, w:r.width|0, h:r.height|0},
                        input_display: cs.display,
                        input_visibility: cs.visibility,
                        input_opacity: cs.opacity,
                        backdrops: document.querySelectorAll('.modal-backdrop').length,
                        body_cls: document.body.className,
                        top_at_input: top ? (top.tagName + '#' + top.id + '.' + top.className).slice(0,80) : null,
                        open_modals: Array.from(document.querySelectorAll('.modal.in'))
                                          .map(x => x.id || x.className),
                    };
                }
            """)
            print(f"[진단 OPEN_MODAL] {diag}")
        except Exception as e:
            print(f"[진단 OPEN_MODAL] dump 실패: {e}")

    def get_modal_title(self) -> str:
        return self.page.locator(self.SEL_MODAL_TITLE).first.inner_text().strip()

    def close_modal(self) -> None:
        """취소 버튼 클릭 → 메인 모달 detached 대기 + 잔해 정리.

        EDIT 모달 close 진단 (2026-05-26 4g/4h/4i fail 스크린샷 검증):
        - 4g E 섹션: set_csu_name('') → 수정 → 알림 dismiss → set_csu_name(원복) → close_modal
        - close_modal 시점: AngularJS form dirty (csuName 왕복 변경) → cancel 클릭이 confirm 트리거 가능성
        - 기존 _click(locator).click() 은 actionability check (5s) 또는 alert intercept 로 silent 실패
        - 기존 ESC fallback 은 Bootstrap data-keyboard='false' 환경에서 무력
        - fix: JS native click 으로 cancel 직접 트리거 → 그래도 안 닫히면 alert dismiss 후 재시도 → 최종 force JS close
        """
        # 잔존 alert 먼저 dismiss (이전 단계에서 떠 있던 알림)
        self._dismiss_alert_if_any()
        if not self.is_visible(self.SEL_MODAL_OPEN):
            self._cleanup_modal_residue()
            return

        # 1차: native JS click on cancel (Playwright actionability check 우회)
        self._js_click_cancel()
        if self._wait_modal_closed(timeout=1500):
            self._cleanup_modal_residue()
            return

        # 2차: cancel-click 후 confirm alert 가 떴을 수 있음 → dismiss 후 한 번 더 JS click
        self._dismiss_alert_if_any()
        self._js_click_cancel()
        if self._wait_modal_closed(timeout=1500):
            self._cleanup_modal_residue()
            return

        # 3차: 그래도 안 닫힘 → JS force-close (AngularJS modal-wrap.in 제거)
        try:
            self.page.evaluate("""() => {
                document.querySelectorAll('div.modal-wrap.in, div.modal.in').forEach(m => {
                    m.classList.remove('in');
                    m.style.display = 'none';
                });
            }""")
        except Exception:
            pass
        self._cleanup_modal_residue()

    def _dismiss_alert_if_any(self) -> None:
        """alert 떠 있으면 dismiss. timeout 짧게 (race 회피).

        주의 (허점 #4 보완 2026-05-26): close_modal context 에서는 cancel-click 이
        '변경 내용을 저장하시겠습니까?' confirm 을 트리거할 가능성. dismiss_confirm_modal 의
        '확인' 클릭은 "저장 진행" 을 의미하므로 EDIT 의도 (취소) 와 정반대.
        → 메시지에 '저장' 단어 있으면 ESC 로 회피 (저장도 닫기도 아닌 중립적 dismiss).
        """
        try:
            if not self.is_confirm_modal_visible(timeout=300):
                return
            msg = ""
            try:
                msg = self.get_confirm_message()
            except Exception:
                pass
            # '저장하시겠습니까?' 류 위험 confirm — ESC 로 cancel
            if "저장" in msg and ("하시겠" in msg or "할까요" in msg):
                for _ in range(2):
                    try:
                        self.page.keyboard.press("Escape")
                        self.page.wait_for_timeout(150)
                        if not self.is_confirm_modal_visible(timeout=100):
                            break
                    except Exception:
                        break
            else:
                # 단순 alert / '정말 닫으시겠습니까?' — '확인' 클릭 = 의도 부합
                self.dismiss_confirm_modal()
        except Exception:
            pass

    def _js_click_cancel(self) -> None:
        """cancel 버튼 native JS click — actionability check / overlay intercept 우회."""
        try:
            self.page.evaluate(f"""() => {{
                const btn = document.querySelector("{self.SEL_CANCEL_BTN}");
                if (btn) btn.click();
            }}""")
        except Exception:
            pass

    def _wait_modal_closed(self, timeout: int) -> bool:
        """SEL_MODAL_OPEN (#controlSuite.in) detach 대기 — 성공 시 True."""
        try:
            self.page.locator(self.SEL_MODAL_OPEN).wait_for(state="detached", timeout=timeout)
            return True
        except Exception:
            return False

    def _cleanup_modal_residue(self) -> None:
        """모달 close 직후 잔해 정리 — backdrop / body.modal-open / padding-right.

        2026-05-26 수정: skip 조건 제거. modal-wrap.in 잔존 시 force-close 는
        close_modal 의 3차 fallback 에서 이미 수행됨 → 여기서는 backdrop/body 정리만 책임.
        """
        try:
            self.page.evaluate("""() => {
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
                document.body.style.paddingRight = '';
            }""")
        except Exception:
            pass

    # ==================================================================
    # 3. 메인 모달 단독 필드 (Step 2)
    # ==================================================================

    # ── csuName ─────────────────────────────────────────────────────
    def set_csu_name(self, name: str, timeout: int = 5000) -> None:
        # 명시적 timeout=5000 — 기본 30s 가 set_default_timeout 으로 안 잡히는 케이스 대응
        self.page.locator(self.SEL_CSU_NAME).first.fill(name, timeout=timeout)

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
        """메인 모달 확장자 tag 1건 삭제. 삭제 성공 시 True.

        yaml :224 verified — `i.extentionDeleteBtn` ng-click 패턴.
        ng-click 은 untrusted JS click 으로도 발화. count check 로 timeout 방지.
        """
        tags = self.page.locator(self.SEL_EXT_LIST_TAG)
        cnt = tags.count()
        for i in range(cnt):
            text = tags.nth(i).inner_text().strip()
            if text.startswith(ext + " ") or text == ext or text.split()[0] == ext:
                sub = tags.nth(i).locator("i.extentionDeleteBtn")
                if sub.count() == 0:
                    return False
                sub.first.evaluate("el => el.click()")
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

    def remove_all_sign_except(self) -> int:
        """전자서명 예외 list 전부 삭제. 삭제된 개수 반환.

        전자서명 tag 의 삭제 버튼 = i.extentionDeleteBtn (확장자와 동일 class — Chrome MCP 2026-05-27 검증).
        ⚠ 전자서명 토글 ON 상태에서만 list 노출 → OFF 면 삭제 불가 (호출 전 토글 ON 보장 필요).
        """
        removed = 0
        while removed < 50:  # 안전장치
            tags = self.page.locator(self.SEL_SIGN_EXCEPT_TAG)
            if tags.count() == 0:
                break
            sub = tags.first.locator("i.extentionDeleteBtn")
            if sub.count() == 0:
                break
            sub.first.evaluate("el => el.click()")
            removed += 1
        return removed

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

    # ── itemList 행 전체 삭제 (헤더 체크박스 전체선택 + 삭제 버튼) ──
    def _remove_all_rows(self, header_chk_sel: str, remove_btn_sel: str,
                         row_sel: str, tab_switch=None) -> int:
        """sub-tab 의 등록 행 전체 삭제. 삭제된 행 수 반환.

        흐름: (탭 전환) → 행 0건이면 no-op → 헤더 체크박스 전체선택 →
              삭제 버튼 → 확인 alert dismiss → 행 0 확인.
        체크박스/버튼 disabled 또는 미존재 시 안전 no-op.
        """
        if tab_switch:
            try:
                tab_switch()
            except Exception:
                pass
        before = self.page.locator(row_sel).count()
        if before == 0:
            return 0
        # 헤더 체크박스 전체선택 (JS click — hidden checkbox 대응)
        try:
            chk = self.page.locator(header_chk_sel).first
            if chk.count() == 0:
                return 0
            chk.evaluate("el => { if (!el.checked) el.click(); }")
        except Exception:
            return 0
        # 삭제 버튼 클릭
        try:
            self._click(self.page.locator(remove_btn_sel).first)
        except Exception:
            return 0
        # 삭제 확인 alert dismiss (있으면)
        try:
            if self.is_confirm_modal_visible(timeout=1000):
                self.dismiss_confirm_modal()
        except Exception:
            pass
        after = self.page.locator(row_sel).count()
        return max(0, before - after)

    def remove_all_process_items(self) -> int:
        """개별 프로세스 itemList 행 전체 삭제."""
        return self._remove_all_rows(
            self.SEL_ITEM_LIST_HEADER_CHK, self.SEL_REMOVE_ITEM_BTN,
            self.SEL_ITEM_LIST_ROW, tab_switch=self.click_individual_process_tab)

    def remove_all_tag_items(self) -> int:
        """태그 itemTagList 행 전체 삭제."""
        return self._remove_all_rows(
            self.SEL_ITEM_TAG_HEADER_CHK, self.SEL_REMOVE_TAG_BTN,
            self.SEL_ITEM_TAG_LIST_ROW, tab_switch=self.click_tag_tab)

    def remove_all_web_restrict_items(self) -> int:
        """웹제한 itemWebRestrictList 행 전체 삭제."""
        return self._remove_all_rows(
            self.SEL_ITEM_WEB_HEADER_CHK, self.SEL_REMOVE_WEB_BTN,
            self.SEL_ITEM_WEB_LIST_ROW, tab_switch=None)

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

    def _find_policy_row(self, name: str):
        """정책 이름 정확 일치 (첫 td 셀 텍스트 == name) 행 반환.

        사용자 안전 우려 (2026-05-22) 해결:
        - 기존 filter(has_text=name) 는 substring 매칭 → 다른 정책 이름의 일부와 충돌 위험
        - exact match 만 허용 — 매칭 실패 시 RuntimeError 발생 (잘못 선택 사고 방지)
        """
        rows = self.page.locator(self.SEL_TABLE_ROW)
        for i in range(rows.count()):
            tds = rows.nth(i).locator("td")
            if tds.count() == 0:
                continue
            cell_text = tds.first.inner_text().strip()
            if cell_text == name:
                return rows.nth(i)
        raise RuntimeError(
            f"정책 '{name}' 을 list 에서 찾을 수 없음 — "
            f"존재하지 않거나 페이지네이션 (pageSize=100 초과) 확인 필요"
        )

    def check_policy_row(self, name: str) -> None:
        """행 체크박스 선택 — 정확 일치 매칭 (substring 충돌 방지)."""
        row = self._find_policy_row(name)
        cb = row.locator(self.SEL_ROW_CHECKBOX).first
        self._click_hidden(cb)

    def click_policy_row(self, name: str) -> None:
        """
        EDIT 진입 사전조건 — 행 자체 클릭 → tActive 부착 (mousedown 필요).
        legacy 검증된 패턴: overlay OFF + row.click(force=True) — 좌표 클릭으로 mousedown 발생.
        ⚠ td#strProcessName 은 modal 안 itemList 의 cell ID — 메인 list 에는 없음.
        정확 일치 매칭 — substring 충돌 방지 (2026-05-22).
        """
        row = self._find_policy_row(name)
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
        """행 active + modifyItemBtn 클릭 → EDIT 모달 열림 + verify (잘못 선택 안전망).

        verify: 모달 진입 후 csuName == name 확인 (사용자 안전 우려 2026-05-22).
        불일치 시 RuntimeError → 사고 (잘못된 정책 EDIT) 즉시 감지.
        """
        self.click_policy_row(name)
        self._click(self.page.locator(self.SEL_MODIFY_BTN).first)
        self.page.locator(self.SEL_MODAL_OPEN).first.wait_for(
            state="attached", timeout=self._TIMEOUT_MODAL
        )
        # ── 안전망: 진입한 EDIT 모달의 csuName 이 기대한 정책 이름과 일치하는가 ──
        try:
            loaded = self.get_csu_name()
        except Exception:
            loaded = "<load 실패>"
        if loaded != name:
            raise RuntimeError(
                f"EDIT 모달 잘못 진입 — 기대 정책 '{name}', "
                f"실제 load 된 csuName '{loaded}'. "
                f"잘못 선택 사고 방지를 위해 즉시 중단."
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
        # alert 닫힘 직후 backdrop 잔해 정리 — server error 후 누적 방지 (2026-05-20 fix)
        # _cleanup_modal_backdrop() 호출 제거 — 사용자 평가: 추가 cleanup 이 cascade 트리거 가능성.
        # F5 reload (teardown) 만으로 깨끗한 상태 유지. (2026-05-20 진단 결과)
        # self._cleanup_modal_backdrop()

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
        # _cleanup_modal_backdrop() 호출 제거 — 사용자 평가: 추가 cleanup 이 cascade 트리거 가능성.
        # F5 reload (teardown) 만으로 깨끗한 상태 유지. (2026-05-20 진단 결과)
        # self._cleanup_modal_backdrop()  # 닫힘 / no-op 모두 잔해 정리

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
        # _cleanup_modal_backdrop() 호출 제거 — 사용자 평가: 추가 cleanup 이 cascade 트리거 가능성.
        # F5 reload (teardown) 만으로 깨끗한 상태 유지. (2026-05-20 진단 결과)
        # self._cleanup_modal_backdrop()  # stale alert dismiss 후 잔해 정리
