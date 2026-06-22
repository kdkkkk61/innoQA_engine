"""
pages/secure_zone_agent_policy_page.py — 시큐어존 정책 (에이전트 정책) 페이지

공통설정(App Setting) > SecureZone > 시큐어존 정책
URL: #!/managerSecureZoneAgentPolicy
모달: div#addItemModal.in (ADD/EDIT 공용, 2탭: 기본정책/템플릿설정), 제목 "시큐어존 에이전트 정책 등록"

[구조 — Chrome MCP 확인 2026-06-10]
- 툴바: 정책추가 addAgentPolicy / 정책할당·회수 addRemoveItemUserBtn(보류·에이전트)
        / 수정 modifyItemBtn / 복사 copyItemBtn / 삭제 removeItemBtn / 검색 searchText
- 정책이름 input#szAgentPolicyName (maxlength=50)
- 저장 등록=button.btn-primary / 취소=button.btn-default
- ⚠️ isSzAgentPolicyTypeTakeoutDefault(기본반출정책) = 전역 singleton — 확인 시 타 정책 플래그 제거.
  테스트에서 절대 '확인' 금지(취소만). (save/템플릿 picker 로직은 sc3 단계에서 추가)
"""
from pages.base_page import BasePage
from pages.shared._overlay import overlay_off


class SecureZoneAgentPolicyPage(BasePage):
    """시큐어존 정책 — list_page + 2탭 모달 (접근제어 페이지 패턴 적응)."""

    PAGE_ID = "secure_zone_agent_policy"
    AUTO_NAME_PREFIX = "[AUTO]_szp"   # maxlength=50 여유 충분

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_LEFT_NAV          = "ul.leftNavList"
    SEL_APP_SETTING_MENU  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"
    SEL_SZ_SECTION_HEADER = "a.managerSecureZone"
    SEL_POLICY_MENU       = "a[data-menuid='managerSecureZoneAgentPolicy']"

    # ── 목록 ──────────────────────────────────────────────────────
    SEL_ADD_BTN          = "button#addAgentPolicy"
    SEL_MODIFY_BTN       = "button#modifyItemBtn"
    SEL_DELETE_BTN       = "button#removeItemBtn"
    SEL_COPY_BTN         = "button#copyItemBtn"
    SEL_SEARCH           = "input#searchText"
    SEL_TABLE_ROW        = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE = "table tbody tr.tActive"
    SEL_CHECKBOX         = "input[type='checkbox']"

    # ── 모달 (ADD/EDIT 공용) ──────────────────────────────────────
    SEL_MODAL     = "div#addItemModal.in"
    SEL_NAME      = "input#szAgentPolicyName"
    SEL_SAVE_BTN  = "div#addItemModal.in button.btn-primary"
    SEL_CLOSE_BTN = (
        "div#addItemModal.in button.btn-default, "
        "div#addItemModal.in button[data-dismiss='modal']"
    )

    # ── 확인 모달 (전역 공통) ─────────────────────────────────────
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _HASH_PAGE_SIZE_100 = (
        "#!/managerSecureZoneAgentPolicy"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ──────────────────────────────────────────────────────────────
    # 네비게이션
    # ──────────────────────────────────────────────────────────────
    def navigate_to(self) -> None:
        """시큐어존 정책 페이지로 이동 (접근제어 페이지 navigate_to 패턴)."""
        self._close_all_modals()          # 잔류 모달/picker 강제 정리 (연쇄 실패 방지)
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "SecureZoneAgentPolicy" in self.page.url
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

        # App Setting 패널 열기
        if not self.is_visible(self.SEL_APP_SETTING_PANEL):
            self.click(self.SEL_APP_SETTING_MENU)
            self.wait_for(self.SEL_APP_SETTING_PANEL)

        # SecureZone 아코디언 펼치기
        if not self.is_visible(self.SEL_POLICY_MENU):
            self.click(self.SEL_SZ_SECTION_HEADER)
            self.wait_for(self.SEL_POLICY_MENU)

        self.click(self.SEL_POLICY_MENU)
        self.wait_for(self.SEL_ADD_BTN)
        # pageSize=100 확장
        self.page.evaluate(f"window.location.hash = '{self._HASH_PAGE_SIZE_100}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 목록 조회
    # ──────────────────────────────────────────────────────────────
    def get_policy_names(self) -> list[str]:
        """현재 목록의 정책 이름 리스트 (행에서 첫 비어있지 않은 셀 = 정책이름)."""
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            texts = [td.inner_text().strip() for td in row.locator("td").all()]
            name  = next((t for t in texts if t), "")
            if name:
                names.append(name)
        return names

    # ──────────────────────────────────────────────────────────────
    # 행 선택
    # ──────────────────────────────────────────────────────────────
    def _row_locator(self, policy_name: str, active: bool = False):
        """정책 이름 '정확' 매칭 행 locator (행 data-name 속성 사용).

        ⚠️ has_text=policy_name 은 substring 매칭 → '[AUTO]_szp_sc4' 가 'sc4t'/'sc4ren' 까지 잡아
           .first 가 엉뚱한 행 선택(실측 2026-06-22 sc4 타임아웃/오선택). data-name 정확 매칭으로 해결.
        active=True 면 tActive 행만. data-name 없으면 has_text fallback.
        """
        sel = self.SEL_TABLE_ROW_ACTIVE if active else self.SEL_TABLE_ROW
        safe = policy_name.replace("\\", "\\\\").replace('"', '\\"')
        exact = self.page.locator(f'{sel}[data-name="{safe}"]')
        try:
            if exact.count() > 0:
                return exact.first
        except Exception:
            pass
        return self.page.locator(sel).filter(has_text=policy_name).first

    def click_policy_row(self, policy_name: str) -> None:
        """정책 이름 행 클릭 (단일 선택, tr.tActive 확인). 최대 3회 재시도.

        ⚠️ 이미 이 정책 행이 tActive 면 재클릭 생략 — 이미 선택된(tActive) AngularJS 행을
           다시 click 하면 actionability 로 5초 타임아웃(실측 2026-06-22 sc4f/4l). 잔류 tActive 원인:
           ① 직전 테스트가 선택한 채 끝나고 navigate_to 가 '이미 그 페이지면 리로드 생략', 또는
           ② 호출자 이중오픈(open_modify_modal 직후 또 호출). 선택돼 있으면 그대로 사용.
        """
        try:
            if self._row_locator(policy_name, active=True).count() > 0:
                return
        except Exception:
            pass
        row = self._row_locator(policy_name)
        for attempt in range(3):
            self._toggle_overlay(False)
            try:
                row.click(force=True)   # force: 중복행/잔류 backdrop actionability 우회 (AngularJS 행 선택)
            finally:
                self._toggle_overlay(True)
            try:
                self._row_locator(policy_name, active=True).wait_for(
                    state="attached", timeout=self._TIMEOUT_MODAL)
                return
            except Exception:
                print(f"\n[click_policy_row] tActive 미확인 ({attempt+1}회), 재시도...")
        raise Exception(f"행 선택 실패 (3회 재시도): {policy_name}")

    def check_policy_row(self, policy_name: str) -> None:
        """정책 이름 행 체크박스 체크. [AUTO] 접두사만 허용."""
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")
        checkbox = self._row_locator(policy_name).locator(self.SEL_CHECKBOX).first
        if checkbox.is_checked():
            return
        self._toggle_overlay(False)
        try:
            checkbox.click()
        finally:
            self._toggle_overlay(True)
        if not checkbox.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크 상태: {policy_name}")

    # ──────────────────────────────────────────────────────────────
    # CRUD (삭제만 — 생성/수정 save 는 sc3 단계에서 추가)
    # ──────────────────────────────────────────────────────────────
    def delete_all_auto_policies(self) -> None:
        """[AUTO] 접두사 정책 전부 삭제."""
        auto_names = [n for n in self.get_policy_names() if n.startswith("[AUTO]")]
        for name in auto_names:
            self.delete_policy(name)

    def delete_policy(self, policy_name: str) -> None:
        """정책 삭제. [AUTO] 접두사만 허용. 실패 시 navigate_to 후 1회 재시도."""
        if not policy_name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 조작 가능합니다")

        def _attempt():
            self.check_policy_row(policy_name)
            self.click(self.SEL_DELETE_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("삭제 버튼 클릭 후 모달이 나타나지 않음")
            msg = self.get_modal_message()
            if "하시겠습니까" not in msg:
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

    # ──────────────────────────────────────────────────────────────
    # 모달 열기/닫기
    # ──────────────────────────────────────────────────────────────
    def open_add_modal(self) -> None:
        """정책추가 버튼 클릭 → 모달 열림 대기."""
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"정책 추가 모달이 열리지 않음: {e}") from e

    def close_modal(self) -> None:
        """모달 닫기(취소) → 목록 복귀."""
        self.click(self.SEL_CLOSE_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL).count() > 0:
                self.click(self.SEL_CLOSE_BTN)
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def _close_all_modals(self) -> None:
        """열려있는 모든 모달/picker 를 위(topmost)부터 닫는다 (취소/닫기/확인).

        한 테스트가 모달/picker 를 열린 채 실패해도 다음 테스트가 연쇄 실패하지 않도록
        navigate_to 시작 시 강제 정리. (teardown reload 제거 환경 대비)
        """
        for _ in range(6):
            modals = self.page.locator(".modal-wrap.in, .modal.in")
            if modals.count() == 0:
                return
            top = modals.last
            clicked = False
            for label in ("취소", "닫기", "확인"):
                btn = top.locator(f"button:has-text('{label}')")
                if btn.count() > 0:
                    try:
                        with overlay_off(self.page):
                            btn.first.click(force=True, timeout=2000)
                        clicked = True
                        break
                    except Exception:
                        pass
            if not clicked:
                # 버튼 못 찾으면 .in 클래스 제거(최후 수단) + backdrop 정리
                try:
                    top.evaluate("el => el.classList.remove('in')")
                except Exception:
                    pass
            self.page.wait_for_timeout(300)

    def open_modify_modal(self, policy_name: str) -> None:
        """행 선택 → 수정 버튼 → 모달 열림 대기 (저장 안 함). 접근제어 페이지 패턴."""
        self.click_policy_row(policy_name)
        self.click(self.SEL_MODIFY_BTN)
        race_sel = f"{self.SEL_CONFIRM_MODAL_OPENED}, {self.SEL_MODAL}"
        try:
            self.page.locator(race_sel).first.wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL
            )
        except Exception as e:
            raise Exception(f"정책 수정 모달이 열리지 않음: {e}") from e
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            raise Exception(f"예상치 못한 모달 발생: {msg!r}")

    def close_edit_modal(self) -> None:
        """수정 모달 닫기 (조건부 — 이미 닫혔을 수 있음)."""
        try:
            if self.page.locator(self.SEL_MODAL).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 저장 + 템플릿 picker (sc3 생성 흐름)
    # ──────────────────────────────────────────────────────────────
    # 템플릿 선택 버튼 (실측 2026-06-11):
    #   기본정책 탭 '템플릿 선택' = button.addTemplate (2개: [0]드라이브 [1]제어스위트)
    #   템플릿설정 탭 '설정'      = a.addTemplate (hidden) → 태그로 구분됨
    SEL_TEMPLATE_BTN = "div#addItemModal.in button.addTemplate"
    # 템플릿 picker 모달 (실측 id 2026-06-11) — Bootstrap 모달이라 attached 로 대기.
    SEL_PICKER       = "div#selectCommonPolicyItemModal.in"

    def submit_and_message(self) -> str:
        """등록 버튼 클릭 → 확인/경고 모달 메시지 반환 + dismiss.

        생성·수정 '액션' 검증용. 모달 없으면 '' 반환.
        성공 시('저장 하였습니다') 목록 복귀 + pageSize 복원.
        ⚠️ btn-primary 가 ADD=등록 / EDIT=수정 2개 공존(ng-show) → 보이는 버튼 클릭(실측 2026-06-18).
        """
        save = self._first_visible(self.page.locator(self.SEL_SAVE_BTN))
        if save is not None:
            with overlay_off(self.page):
                save.click(force=True)
        else:
            self.click_attached(self.SEL_SAVE_BTN)   # fallback (attached 만 잡힐 때)
        self.page.wait_for_timeout(600)
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        # 저장 성공 시에만 모달이 닫히고 목록 복귀
        if self.page.locator(self.SEL_ADD_BTN).count() > 0 and self.page.locator(self.SEL_MODAL).count() == 0:
            self.wait_for(self.SEL_ADD_BTN)
            self._restore_page_size()
        return msg

    def set_value_raw(self, selector: str, value: str) -> int:
        """maxlength 우회하여 input/textarea 에 긴 값 주입 (overflow 테스트용). 반환: 실제 들어간 길이.

        native value setter + input/change 이벤트로 AngularJS ng-model 동기화.
        ⚠️ 단순 el.value=... +input 만으론 ng-model 미동기(실측 2026-06-22: 저장 시 '수정된 항목 없음').
        native prototype setter 를 거쳐야 저장에 반영됨(라이브 검증). Playwright fill 은 maxlength 적용돼 초과 불가라 이걸 씀.
        """
        return self.page.locator(selector).first.evaluate(
            """(el, v) => {
                const proto = el.tagName === 'TEXTAREA'
                    ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                return el.value.length;
            }""", value)

    def _wait_picker_rows(self, picker) -> None:
        """picker 행 async 로드 대기 — 첫 행 attached + settle(300ms). select/assign/검색 picker 공통.
        안 기다리면 rows.count()==0 으로 매칭 실패(빈값)·false '비어있음' skip (실측 2026-06-18)."""
        try:
            picker.locator("table tbody tr").first.wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass
        self.page.wait_for_timeout(300)

    def _first_visible(self, locator):
        """locator 매칭 중 첫 '보이는' 요소 (ng-show 로 숨겨진 동형 요소 skip). 없으면 None.

        시큐어존 모달은 동형 요소를 ng-show 로 토글 (DOM 엔 다 존재):
        - 저장 btn-primary = [등록(ADD), 수정(EDIT)] — 모드별 1개만 visible (실측 2026-06-18).
        - 템플릿설정 할당해제 링크 = 6행 전부 존재, 할당된 행만 visible.
        .first 로 잡으면 숨김 요소를 클릭해 force=True 에도 'not visible' 실패.
        """
        for i in range(locator.count()):
            cand = locator.nth(i)
            try:
                if cand.is_visible():
                    return cand
            except Exception:
                continue
        return None

    def select_template_top(self, btn_index: int) -> str:
        """기본정책 탭 '템플릿 선택' 버튼(0=드라이브,1=제어스위트) → picker 첫 행 선택 → 확인.

        picker 검색 미동작(실측 2026-06-11) + [AUTO_ 템플릿 미확인 → 맨 위 행 fallback.
        반환: 선택한 템플릿 이름.
        """
        # ⚠️ picker 열기/선택은 반드시 오버레이 OFF + 실제 click(force) (사용자 지정 2026-06-11).
        #    picker 행 radio 는 테이블 행(tActive)처럼 real mousedown 필요 → el.click() 으론 선택 안 됨.
        # button.addTemplate = 기본정책 탭 2개 ([0]드라이브 [1]제어스위트)
        with overlay_off(self.page):
            self.page.locator(self.SEL_TEMPLATE_BTN).nth(btn_index).click(force=True)
        picker = self.page.locator(self.SEL_PICKER)
        picker.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        self._wait_picker_rows(picker)
        first_row = picker.locator("table tbody tr").first
        name = ""
        try:
            cells = [c.inner_text().strip() for c in first_row.locator("td").all()]
            name = next((t for t in cells if t), "")
        except Exception:
            pass
        with overlay_off(self.page):
            first_row.locator("input[type='radio']").first.click(force=True)
            picker.locator("button:has-text('확인')").first.click(force=True)
        picker.wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        return name

    def create_basic_policy(self, name: str) -> str:
        """일반 정책 최소 생성: 이름 + 드라이브/제어스위트 템플릿(맨 위) + 등록.

        [AUTO] 접두사만 허용(데이터 안전). 반환: 저장 결과 메시지.
        ⚠️ 기본반출정책(singleton) 미접촉 — 타입 일반 기본값 유지.
        """
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 생성 정책([AUTO] 접두사)만 허용합니다")
        self.fill(self.SEL_NAME, name)
        self.select_template_top(0)   # 드라이브
        self.select_template_top(1)   # 제어스위트
        return self.submit_and_message()

    # ── 토글/체크박스 ─────────────────────────────────────────────
    def set_toggle(self, css_id: str, on: bool) -> None:
        """모달 내 체크박스/토글 상태 설정 (el.click — checkbox 는 JS 직접 호출로 충분)."""
        loc = self.page.locator(f"div#addItemModal.in input#{css_id}").first
        if loc.count() and loc.is_enabled() and loc.is_checked() != on:
            loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(150)

    def field_state(self, css_id: str) -> dict:
        """모달 내 필드 상태 {checked, disabled, value}."""
        loc = self.page.locator(f"div#addItemModal.in #{css_id}").first
        if loc.count() == 0:
            return {"present": False}
        out = {"present": True, "disabled": loc.is_disabled()}
        try:
            out["checked"] = loc.is_checked()
        except Exception:
            out["checked"] = None
        try:
            out["value"] = loc.input_value()
        except Exception:
            out["value"] = None
        return out

    def feature_available(self, selector: str) -> bool:
        """요소가 '검증 가능' 상태인가 = DOM 존재 + 섹션이 display:none 아님.

        - 삭제(미존재) / 섹션(또는 탭) display:none → False (→ sc3 테스트 skip)
        - 토글 스위치처럼 input 자체만 CSS 숨김(부모 섹션은 보임) → True (강제 동작 가능 = 검증 대상)
        - gating(disabled, 보임) → True (disabled 동작 자체가 검증 대상)
        sc0 의 숨김(extract_dom_hidden) 판정과 동일 기준 — 삭제/숨김 vs 동작결함 정확 구분용.
        """
        try:
            return bool(self.page.evaluate(
                """(sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;                       // 삭제(미존재)
                    if (el.offsetParent !== null) return true;   // 명확히 보임
                    let node = el.parentElement;                 // 자신의 CSS숨김은 무시(토글)
                    while (node) {
                        if (getComputedStyle(node).display === 'none') return false;  // 섹션/탭 숨김
                        node = node.parentElement;
                    }
                    return true;                                 // 토글 등 자체만 숨김 → 검증 가능
                }""", selector))
        except Exception:
            return False

    # ── 파일 감시 확장자 tag-input (isWatchFile ON 필요) ──────────
    SEL_WATCH_EXT_INPUT = "div#addItemModal.in input#watchFileExtention"
    SEL_WATCH_EXT_ADD   = "div#addItemModal.in button#addSzWatchFileExtention"
    SEL_WATCH_EXT_LIST  = "div#addItemModal.in div#secureZoneWatchFileExtentionList"

    def add_watch_extension(self, value: str) -> None:
        """확장자 입력 + 추가 버튼 (overlay OFF + force)."""
        self.fill(self.SEL_WATCH_EXT_INPUT, value)
        with overlay_off(self.page):
            self.page.locator(self.SEL_WATCH_EXT_ADD).first.click(force=True)
        self.page.wait_for_timeout(250)

    def add_extension_msg(self, value: str) -> tuple[list[str], str]:
        """확장자 추가 시도 → (현재 리스트, 경고 메시지) 반환 + 경고 dismiss.

        빈값/중복/특수문자 등 차단 케이스의 메시지 확인용.
        """
        self.fill(self.SEL_WATCH_EXT_INPUT, value)
        with overlay_off(self.page):
            self.page.locator(self.SEL_WATCH_EXT_ADD).first.click(force=True)
        self.page.wait_for_timeout(300)
        msg = ""
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return self.watch_extension_items(), msg

    def watch_extension_items(self) -> list[str]:
        """확장자 리스트의 현재 항목 텍스트들."""
        return [b.inner_text().strip()
                for b in self.page.locator(
                    f"{self.SEL_WATCH_EXT_LIST} button[contents-list-item]").all()]

    def delete_first_watch_extension(self) -> None:
        """확장자 리스트 첫 항목 삭제 (x 아이콘, overlay OFF + force)."""
        with overlay_off(self.page):
            self.page.locator(
                f"{self.SEL_WATCH_EXT_LIST} button[contents-list-item] i.extentionDeleteBtn"
            ).first.click(force=True)
        self.page.wait_for_timeout(200)

    # 파일 감시 예외 폴더 = [특수폴더] picker 방식 (자유 텍스트 입력칸 없음, 실측 2026-06-11).
    SEL_WATCH_FOLDER_SPECIAL = "div#addItemModal.in button.specialFolderBtn"
    SEL_WATCH_FOLDER_ADD     = "div#addItemModal.in button#addSzWatchFolder"
    SEL_WATCH_FOLDER_LIST    = "div#addItemModal.in div#secureZoneWatchFolderList"

    # 파일감시(master=isWatchFile) 하위 요소 전체 — master gating 검증용.
    # 실측 2026-06-12: master OFF → 아래 전부 disabled. (보관소 '지정' 버튼은 별 id 없어 field 로 대표)
    _FILEWATCH_SUB = [
        ("보관소 지정", "input#watchFileStorePath"),
        ("확장자 사용 체크박스", "input#isWatchFileExtention"),
        ("확장자 입력", "input#watchFileExtention"),
        ("확장자 추가버튼", "button#addSzWatchFileExtention"),
        ("예외폴더 사용 체크박스", "input#isWatchFolder"),
        ("예외폴더 특수폴더버튼", "button.specialFolderBtn"),
        ("예외폴더 추가버튼", "button#addSzWatchFolder"),
        ("헤더 체크 체크박스", "input#isWatchFileHeader"),
    ]

    def filewatch_sub_disabled(self) -> dict:
        """파일감시 하위 요소별 disabled 상태 {label: True/False/None}. None=요소 없음."""
        out = {}
        for label, sel in self._FILEWATCH_SUB:
            loc = self.page.locator(f"div#addItemModal.in {sel}").first
            out[label] = loc.is_disabled() if loc.count() else None
        return out

    # ── 차단 대기시간 (오프라인) — 실타이핑(per-key, 12자 JS검증 발화) ──
    SEL_BLOCK_TIME = "div#addItemModal.in input#secureDriveBlockTime"

    def type_block_time(self, value: str) -> tuple[str, str]:
        """차단 대기시간에 실제 per-key 타이핑 → (필드값, 경고 메시지) 반환 + 경고 dismiss.

        12자 초과 경고는 keypress 기반이라 fill() 아닌 press_sequentially 사용.
        """
        loc = self.page.locator(self.SEL_BLOCK_TIME).first
        with overlay_off(self.page):
            loc.click(force=True)
        loc.fill("")
        loc.press_sequentially(value, delay=30)
        self.page.wait_for_timeout(300)
        msg = ""
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return loc.input_value(), msg

    # ── 프린트 설정 (isPrintUse ON) ───────────────────────────────
    def set_print_radio(self, value: str) -> None:
        """프린트 radio 선택 ('0'=차단 / '1'=허용). overlay OFF + force."""
        with overlay_off(self.page):
            (self.page.locator(f"div#addItemModal.in input[name='isPrint'][value='{value}']")
                .first.click(force=True))
        self.page.wait_for_timeout(150)

    def print_radio_value(self) -> str:
        """현재 선택된 프린트 radio value ('0'차단/'1'허용)."""
        for v in ("0", "1"):
            loc = self.page.locator(f"div#addItemModal.in input[name='isPrint'][value='{v}']").first
            if loc.count() and loc.is_checked():
                return v
        return ""

    # ── 템플릿 picker 검색 (제품 버그 검출용 — 검색 동작 여부 확인) ──
    SEL_PICKER_SEARCH = "div#selectCommonPolicyItemModal.in input#searchText"

    def picker_search_filters(self, btn_index: int, query: str, tab: str = "기본정책") -> dict:
        """템플릿 picker 검색 → 결과 건수 변하는지.

        tab="기본정책": SEL_TEMPLATE_BTN(button.addTemplate) 드라이브(0)/제어스위트(1).
        tab="템플릿설정": a.addTemplate [설정] (0허용/거부 1예외처리 2실행차단 3바로가기 4레지스트리 5폴더동기화).
        모든 picker 가 동일 div#selectCommonPolicyItemModal 단일 요소 재사용 → 검색 동작도 공유.

        반환: {before, after, filtered(bool)}. filtered=False 면 검색 미동작(결함).
        ⚠️ picker 는 '열어둔 채' 반환 — 호출자가 검색창 캡처(highlight) 후 close_picker() 호출.
        """
        if tab == "템플릿설정":
            self.goto_modal_tab("템플릿설정")
            opener = self.page.locator("div#addItemModal.in a.addTemplate")
        else:
            opener = self.page.locator(self.SEL_TEMPLATE_BTN)
        with overlay_off(self.page):
            opener.nth(btn_index).click(force=True)
        picker = self.page.locator(self.SEL_PICKER)
        picker.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        # 행 async 로드 대기 — 안 기다리면 드라이브 picker 는 0건에서 재서
        # 검색 후 로드된 건수와 비교돼 filtered=True 로 false PASS 됨(실측 2026-06-12)
        self._wait_picker_rows(picker)
        before = picker.locator("table tbody tr").count()
        self.fill(self.SEL_PICKER_SEARCH, query)
        with overlay_off(self.page):
            picker.locator("button#searchBtn").first.click(force=True)
        self.page.wait_for_timeout(600)
        after = picker.locator("table tbody tr").count()
        return {"before": before, "after": after, "filtered": before != after}

    def reselect_template(self, btn_index: int, row_index: int) -> str:
        """기본정책 템플릿 버튼 → picker 의 특정 행(row_index) 선택 → 확인. 재설정(변경) 검증용."""
        with overlay_off(self.page):
            self.page.locator(self.SEL_TEMPLATE_BTN).nth(btn_index).click(force=True)
        picker = self.page.locator(self.SEL_PICKER)
        picker.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        row = picker.locator("table tbody tr").nth(row_index)
        row.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        name = ""
        try:
            cells = [c.inner_text().strip() for c in row.locator("td").all()]
            name = next((t for t in cells if t), "")
        except Exception:
            pass
        with overlay_off(self.page):
            row.locator("input[type='radio']").first.click(force=True)
            picker.locator("button:has-text('확인')").first.click(force=True)
        picker.wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        return name

    def drive_row_text(self) -> str:
        """기본정책 탭 '드라이브 설정' 행 텍스트(선택된 템플릿명 포함)."""
        t = " ".join(self.page.locator("div#addItemModal.in").inner_text().split())
        i = t.find("드라이브 설정")
        return t[i:i + 45] if i >= 0 else t[:45]

    # ── 템플릿설정 탭: 프로세스 템플릿(허용/거부) 할당 (검증 A/B) ──
    def goto_modal_tab(self, name: str) -> None:
        """모달 탭 전환 ('기본정책' / '템플릿설정')."""
        tab = next((a for a in self.page.locator("div#addItemModal.in li a").all()
                    if name in a.inner_text()), None)
        if tab:
            with overlay_off(self.page):
                tab.evaluate("el => el.click()")
            self.page.wait_for_timeout(300)

    def assign_process_template(self, kind: str) -> str:
        """템플릿설정 탭 → 허용/거부 프로세스 [설정] → picker 에서 kind('허용'/'거부') 행 선택 → 확인.

        반환: 선택한 템플릿명. (검증A/B 용 — picker 는 허용·거부 혼재 라디오 단일선택)
        """
        self.goto_modal_tab("템플릿설정")
        # 허용/거부 프로세스 행의 [설정] 버튼 = 템플릿설정 탭 첫 a.addTemplate
        with overlay_off(self.page):
            (self.page.locator("div#addItemModal.in a.addTemplate").first
                .click(force=True))
        picker = self.page.locator(self.SEL_PICKER)
        picker.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        self._wait_picker_rows(picker)   # 실측 2026-06-18: 허용 첫 할당 빈값 → sc3g/3u/3w false skip 방지
        rows = picker.locator("table tbody tr")
        target = None
        name = ""
        for i in range(rows.count()):
            r = rows.nth(i)
            txt = r.inner_text()
            if kind in txt:
                target = r
                name = " ".join(txt.split())[:25]
                break
        if target is None:
            self.close_picker()
            return ""
        with overlay_off(self.page):
            target.locator("input[type='radio']").first.click(force=True)
            picker.locator("button:has-text('확인')").first.click(force=True)
        picker.wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        return name

    def assign_template_setting(self, btn_index: int) -> str:
        """템플릿설정 탭 [설정] 버튼(btn_index) → picker 맨 위 행 선택 → 확인. 반환: 선택명('' if 없음/실패).

        [설정] index(실측): 0허용/거부 1예외처리 2실행차단 3바로가기 4레지스트리 5폴더동기화.
        검증A 일반화용 — 템플릿 없거나 실패해도 throw 안 함.
        """
        try:
            self.goto_modal_tab("템플릿설정")
            btns = self.page.locator("div#addItemModal.in a.addTemplate")
            if btns.count() <= btn_index:
                return ""
            with overlay_off(self.page):
                btns.nth(btn_index).click(force=True)
            picker = self.page.locator(self.SEL_PICKER)
            picker.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
            self._wait_picker_rows(picker)   # 실측 2026-06-18: sc3h false '비어있음' skip 방지
            rows = picker.locator("table tbody tr")
            if rows.count() == 0:
                self.close_picker()
                return ""
            name = ""
            try:
                cells = [c.inner_text().strip() for c in rows.first.locator("td").all()]
                name = next((t for t in cells if t), "")
            except Exception:
                pass
            with overlay_off(self.page):
                rows.first.locator("input[type='radio'], input[type='checkbox']").first.click(force=True)
                picker.locator("button:has-text('확인')").first.click(force=True)
            picker.wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
            return name
        except Exception:
            return ""

    def process_template_area_text(self) -> str:
        """템플릿설정 탭 '프로세스 템플릿' 영역 텍스트 (허용/거부 등록 표시 확인용)."""
        self.goto_modal_tab("템플릿설정")
        t = " ".join(self.page.locator("div#addItemModal.in").inner_text().split())
        i = t.find("프로세스 템플릿")
        return t[i:i + 70] if i >= 0 else ""

    def process_control_label(self) -> str:
        """기본정책 탭 '프로세스 통제기능 사용' 옆 상태 라벨 텍스트 (cross-tab 반영 확인용).

        허용/거부 프로세스 템플릿 할당 시 이 라벨이 함께 바뀜 (직접조작 확인 2026-06-18):
        미선택='[허용/거부 템플릿 미선택]' / 허용='[허용프로세스] 사용중' / 거부='[거부프로세스] 사용중'.
        """
        self.goto_modal_tab("기본정책")
        t = " ".join(self.page.locator("div#addItemModal.in").inner_text().split())
        i = t.find("프로세스 통제기능")
        return t[i:i + 40] if i >= 0 else ""

    def template_tab_text(self) -> str:
        """템플릿설정 탭 전체 가시 텍스트 (6행 전부 — 예외처리/레지스트리 등록 표시 확인용)."""
        self.goto_modal_tab("템플릿설정")
        return " ".join(self.page.locator("div#addItemModal.in").inner_text().split())

    def unassign_template_setting(self) -> bool:
        """템플릿설정 탭에서 첫 '보이는' [할당해제] 링크 클릭 → 해제. 확인 다이얼로그 시 '확인'.

        반환: 보이는 [할당해제] 링크가 있어서 클릭했으면 True (없으면 False — 할당된 행 없음).
        드라이브/제어스위트는 할당해제 버튼 없음(필수*) → 템플릿설정 탭 행 전용.
        ⚠️ 할당해제 링크(a.removeTemplate)는 6행 전부 DOM 에 존재하고 ng-show 로 visible 만 토글됨.
           .first 로 잡으면 미할당 행(예: 허용/거부)의 '숨김' 링크가 잡혀 force click 도 'not visible'
           실패(실측 2026-06-18: sc3v 예외처리만 할당 시 첫 DOM 링크=허용/거부 숨김). → 첫 '보이는' 링크 선택.
        """
        self.goto_modal_tab("템플릿설정")
        link = self._first_visible(self.page.locator(
            "div#addItemModal.in a:has-text('할당해제'), "
            "div#addItemModal.in button:has-text('할당해제')"))
        if link is None:
            return False
        with overlay_off(self.page):
            link.click(force=True)
        self.page.wait_for_timeout(300)
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return True

    # ── 예외폴더 특수폴더(예약어) picker (추가 동작 검증) ──────────
    def add_watch_folder_reserved(self, macro_keyword: str) -> tuple[list[str], str]:
        """[특수폴더] → 예약어 picker macro 체크 → 확인(칩) → [추가] → (리스트, 경고메시지).

        흐름(실측 2026-06-12): 특수폴더 → 예약어 체크 → 확인 → 칩이 div#secureZoneWatchFolder 에 →
        반드시 [추가](addSzWatchFolder) 클릭해야 리스트(secureZoneWatchFolderList)로 이동. (확인만으론 안 됨!)
        예약어 picker 는 addItemModal 외 topmost 모달. 중복 시 '이미 등록된 폴더 경로' 경고.
        """
        try:
            with overlay_off(self.page):
                self.page.locator(self.SEL_WATCH_FOLDER_SPECIAL).first.click(force=True)
            self.page.wait_for_timeout(800)
            picker = None
            modals = self.page.locator(".modal-wrap.in")
            for i in range(modals.count()):
                if (modals.nth(i).get_attribute("id") or "") != "addItemModal":
                    picker = modals.nth(i)
            if picker is not None:
                row = picker.locator("table tbody tr").filter(has_text=macro_keyword).first
                if row.count():
                    with overlay_off(self.page):
                        row.locator("input[type='checkbox']").first.click(force=True)
                with overlay_off(self.page):
                    picker.locator("button:has-text('확인')").first.click(force=True)
                self.page.wait_for_timeout(400)
            # 확인 후 칩이 들어옴 → [추가] 눌러야 리스트로 이동
            with overlay_off(self.page):
                self.page.locator(self.SEL_WATCH_FOLDER_ADD).first.click(force=True)
            self.page.wait_for_timeout(400)
        except Exception:
            pass
        msg = ""
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        items = [b.inner_text().strip()
                 for b in self.page.locator(
                     f"{self.SEL_WATCH_FOLDER_LIST} button[contents-list-item]").all()]
        return items, msg

    def watch_folder_items(self) -> list[str]:
        """예외폴더 리스트 현재 항목들."""
        return [b.inner_text().strip()
                for b in self.page.locator(
                    f"{self.SEL_WATCH_FOLDER_LIST} button[contents-list-item]").all()]

    def delete_first_watch_folder(self) -> bool:
        """예외폴더 리스트 첫 항목 삭제 (x 아이콘 = folderDeleteBtn, 확장자와 클래스 다름). 항목 없으면 False."""
        btn = self.page.locator(
            f"{self.SEL_WATCH_FOLDER_LIST} button[contents-list-item] i.folderDeleteBtn")
        if btn.count() == 0:
            return False
        with overlay_off(self.page):
            btn.first.click(force=True)
        self.page.wait_for_timeout(200)
        return True

    def close_picker(self) -> None:
        """열린 템플릿 picker 닫기(선택 안 함)."""
        picker = self.page.locator(self.SEL_PICKER)
        try:
            if picker.count() > 0:
                with overlay_off(self.page):
                    picker.locator("button:has-text('닫기')").first.click(force=True)
                picker.wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 속성 모달 (상세정보 보기) — 행 가운데 셀 더블클릭 시 팝업 (읽기전용)
    # ──────────────────────────────────────────────────────────────
    # Chrome MCP 실측 2026-06-22: 모달 id = detailSecureZoneAgentPolicy.
    #   제목 "시큐어존 에이전트 정책 상세정보 보기", 2탭(기본정책/템플릿설정),
    #   모든 input disabled(읽기전용). 토글/텍스트/라디오 id 가 수정 모달(addItemModal)과 동일
    #   → 같은 읽기 로직 재사용(접근제어 _read_ac_state 패턴). 값은 활성 탭과 무관하게 DOM 에서 읽힘.
    SEL_DETAIL_MODAL = "div#detailSecureZoneAgentPolicy.in"
    SEL_DETAIL_CLOSE = (
        "div#detailSecureZoneAgentPolicy.in button:has-text('닫기'), "
        "div#detailSecureZoneAgentPolicy.in button[data-dismiss='modal']"
    )

    # 속성/수정 모달 공통 읽기 대상 (id 동일) — 전 토글 + 텍스트필드.
    _DETAIL_TOGGLES = (
        "isAllowDenyProcessUse", "isAllowProcessForceStop", "isExceptProcess",
        "isBlockExecuteProcess", "isManageFolder", "isSyncFolder",
        "isWatchFile", "isWatchFileExtention", "isWatchFileHeader", "isWatchFolder",
        "isPrintUse", "isShowAgentShutdownMenu", "isShowEmergencyCodeMenu",
        "isOfflineUse", "isTakeoutDriveBlock",
    )
    _DETAIL_TEXTS = (
        "watchFileStorePath", "allowPrintModel", "exceptPrintPort",
        "secureDriveBlockTime", "customOptionText",
    )

    def open_detail_modal(self, policy_name: str) -> None:
        """행 가운데(비이름 셀) 더블클릭 → 속성 모달(상세정보 보기) 열기.

        행 dblclick 핸들러는 JS 이벤트 위임(ng-dblclick 속성 아님) → 오버레이/좌표/actionability
        무관하게 evaluate 로 mousedown/up/click 시퀀스 + dblclick 디스패치(접근제어와 동일 메커니즘).
        이름 셀(td[0]) 제외하고 td[1] 사용.
        """
        row = self._row_locator(policy_name)
        cell = row.locator("td").nth(1)
        cell.evaluate(
            "el => ['mousedown','mouseup','click','mousedown','mouseup','click','dblclick']"
            ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))"
        )
        self.wait_for(self.SEL_DETAIL_MODAL, state="attached")

    def _read_modal_state(self, modal_sel: str) -> dict:
        """주어진 모달(속성/수정) 안의 전 토글+텍스트 상태 dict.

        반환: {"toggle": {id: bool|None}, "text": {id: str|None}, "print_radio": "0"/"1"/""}.
        토글/텍스트/라디오 id 가 속성·수정 모달 동일 → 공통. 미존재 필드는 None.
        """
        out: dict = {"toggle": {}, "text": {}}
        for cid in self._DETAIL_TOGGLES:
            loc = self.page.locator(f"{modal_sel} #{cid}").first
            try:
                out["toggle"][cid] = loc.is_checked() if loc.count() > 0 else None
            except Exception:
                out["toggle"][cid] = None
        for tid in self._DETAIL_TEXTS:
            loc = self.page.locator(f"{modal_sel} #{tid}").first
            try:
                out["text"][tid] = loc.input_value() if loc.count() > 0 else None
            except Exception:
                out["text"][tid] = None
        pr = ""
        for v in ("0", "1"):
            r = self.page.locator(f"{modal_sel} input[name='isPrint'][value='{v}']").first
            if r.count() > 0 and r.is_checked():
                pr = v
        out["print_radio"] = pr
        return out

    def read_detail_modal(self) -> dict:
        """열린 속성 모달의 토글/텍스트/프린트 상태 dict (읽기전용 round-trip 검증용)."""
        return self._read_modal_state(self.SEL_DETAIL_MODAL)

    def read_modify_modal_state(self) -> dict:
        """열린 수정 모달의 토글/텍스트/프린트 상태 dict (속성 모달과 값 비교용)."""
        return self._read_modal_state(self.SEL_MODAL)

    def detail_modal_readonly(self) -> bool:
        """속성 모달의 '핵심 정책 필드'(토글/텍스트/라디오)가 전부 disabled(읽기전용)인지.

        ⚠️ 'div 내 모든 input' 으로 보면 파일감시 ON 등에서 나타나는 보조 입력(확장자/예외폴더
           tag-input 등)이 disabled 가 아니라 false WARN 이 남(실측 2026-06-22 sc5a-②). 핵심 필드만 본다.
           실제 클릭 변경 여부는 detail_modal_try_change 로 별도 능동 검증.
        """
        m = self.SEL_DETAIL_MODAL
        sels = ([f"#{t}" for t in self._DETAIL_TOGGLES]
                + [f"#{t}" for t in self._DETAIL_TEXTS]
                + ["input[name='isPrint']", "input[name='szAgentPolicyType']"])
        seen = False
        for sel in sels:
            for loc in self.page.locator(f"{m} {sel}").all():
                seen = True
                if not loc.is_disabled():
                    return False
        return seen

    # 능동 읽기전용 검증 대상 (속성 모달 토글/라디오 대표 — 클릭해도 안 바뀌어야 정상).
    _DETAIL_TRY_CLICK = (
        "#isBlockExecuteProcess", "#isManageFolder", "#isWatchFileHeader",
        "#isShowAgentShutdownMenu", "input[name='isPrint'][value='1']",
    )

    def detail_modal_try_change(self) -> dict:
        """속성 모달 요소에 실제 클릭 시도 → 값이 바뀌는지(읽기전용 우회/UI 변동 버그) 능동 검출.

        disabled 속성만으론 못 잡는 '읽기전용인데 실제로는 클릭에 반응' 케이스 검출.
        반환: {selector: {'before','after','changed'}}. 바뀌었으면 원복 시도. (직접조작 확인 2026-06-22:
        정상 빌드에선 disabled 라 전부 changed=False — 하나라도 True 면 결함 가능)
        """
        m = self.SEL_DETAIL_MODAL
        out: dict = {}
        for sel in self._DETAIL_TRY_CLICK:
            loc = self.page.locator(f"{m} {sel}").first
            if loc.count() == 0:
                continue
            try:
                before = loc.is_checked()
            except Exception:
                continue
            try:
                loc.evaluate("el => el.click()")
                self.page.wait_for_timeout(100)
            except Exception:
                pass
            try:
                after = loc.is_checked()
            except Exception:
                after = before
            out[sel] = {"before": before, "after": after, "changed": before != after}
            if before != after:   # 읽기전용 우회됨 → 원복 시도
                try:
                    loc.evaluate("el => el.click()")
                except Exception:
                    pass
        return out

    def detail_modal_text(self) -> str:
        """속성 모달 본문 텍스트 (드라이브/허용 라벨·확장자 등 label 텍스트는 포함 여부로 검증)."""
        m = self.page.locator(self.SEL_DETAIL_MODAL).first
        if m.count() == 0:
            return ""
        body = m.locator(".modal-body")
        target = body if body.count() > 0 else m
        return " ".join(target.first.inner_text().split())

    def close_detail_modal(self) -> None:
        """속성 모달 닫기."""
        try:
            self.page.locator(self.SEL_DETAIL_CLOSE).first.evaluate("el => el.click()")
            self.page.locator(self.SEL_DETAIL_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL
            )
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 모달 헬퍼 (확인/경고 모달)
    # ──────────────────────────────────────────────────────────────
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

    def cancel_confirm_modal(self) -> str:
        """확인/취소 다이얼로그에서 '취소' 클릭 (메시지 반환). 기본반출정책 singleton 안전 처리용."""
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            try:
                self.page.locator(
                    f"{self.SEL_CONFIRM_MODAL_OPENED} button:has-text('취소')"
                ).first.evaluate("el => el.click()")
                self.wait_for_modal_closed()
            except Exception:
                pass
        return msg

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass

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
