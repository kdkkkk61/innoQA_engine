"""
pages/secure_zone_access_control_policy_page.py — 시큐어존 접근제어 정책 페이지

공통설정(App Setting) > SecureZone > 접근제어 정책
scan_mode: modal_form (방식 A) — 단일 플랫 모달, UIScanner 자동 검증
모달: div#addModifySecureZoneAccessControlPolicy.in (ADD/EDIT 공용)

[구조 — Chrome MCP 확인 2026-06-09]
- URL: #!/managerSecureZoneAccessControlPolicy
- 마스터 토글 isAccessControl OFF → 하위 컨트롤 전부 disabled
- 저장 버튼: button.btn-primary (add-btn/modify-btn 속성 없음)
"""
from pages.base_page import BasePage


class SecureZoneAccessControlPolicyPage(BasePage):
    """시큐어존 접근제어 정책 — modal_form 패턴 (RansomDetectPolicyPage 참조)."""

    PAGE_ID = "secure_zone_access_control"
    # maxlength=50 — 여유 충분
    AUTO_NAME_PREFIX = "[AUTO]_sac"

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_LEFT_NAV          = "ul.leftNavList"
    SEL_APP_SETTING_MENU  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"
    SEL_SZ_SECTION_HEADER = "a.managerSecureZone"
    SEL_AC_MENU           = "a[data-menuid='managerSecureZoneAccessControlPolicy']"

    # ── 목록 ──────────────────────────────────────────────────────
    SEL_ADD_BTN          = "button#addItem"
    SEL_MODIFY_BTN       = "button#modifyItem"
    SEL_DELETE_BTN       = "button#removeItem"
    SEL_TABLE_ROW        = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE = "table tbody tr.tActive"
    SEL_CHECKBOX         = "input[type='checkbox']"

    # ── 모달 (ADD/EDIT 공용) ──────────────────────────────────────
    SEL_MODAL     = "div#addModifySecureZoneAccessControlPolicy.in"
    SEL_NAME      = "input#szAccessControlPolicyName"
    SEL_SAVE_BTN  = "div#addModifySecureZoneAccessControlPolicy.in button.btn-primary"
    SEL_CLOSE_BTN = (
        "div#addModifySecureZoneAccessControlPolicy.in button.btn-default, "
        "div#addModifySecureZoneAccessControlPolicy.in button[data-dismiss='modal']"
    )

    # ── 확인 모달 (전역 공통) ─────────────────────────────────────
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _HASH_PAGE_SIZE_100 = (
        "#!/managerSecureZoneAccessControlPolicy"
        "?pageNo=1&pageSize=100&searchText=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ──────────────────────────────────────────────────────────────
    # 네비게이션
    # ──────────────────────────────────────────────────────────────
    def navigate_to(self) -> None:
        """접근제어 정책 페이지로 이동 (RansomDetectPolicyPage.navigate_to 패턴)."""
        self._close_modal_if_open()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "SecureZoneAccessControlPolicy" in self.page.url
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
        if not self.is_visible(self.SEL_AC_MENU):
            self.click(self.SEL_SZ_SECTION_HEADER)
            self.wait_for(self.SEL_AC_MENU)

        self.click(self.SEL_AC_MENU)
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
    def click_policy_row(self, policy_name: str) -> None:
        """정책 이름 행 클릭 (단일 선택, tr.tActive 확인). 최대 3회 재시도."""
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=policy_name).first
        for attempt in range(3):
            self._toggle_overlay(False)
            try:
                row.click()
            finally:
                self._toggle_overlay(True)
            try:
                self.page.locator(self.SEL_TABLE_ROW_ACTIVE).filter(
                    has_text=policy_name
                ).first.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
                return
            except Exception:
                print(f"\n[click_policy_row] tActive 미확인 ({attempt+1}회), 재시도...")
        raise Exception(f"행 선택 실패 (3회 재시도): {policy_name}")

    def check_policy_row(self, policy_name: str) -> None:
        """정책 이름 행 체크박스 체크. [AUTO] 접두사만 허용."""
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
        self._toggle_overlay(False)
        try:
            checkbox.click()
        finally:
            self._toggle_overlay(True)
        if not checkbox.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크 상태: {policy_name}")

    # ──────────────────────────────────────────────────────────────
    # CRUD
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
    # UIScanner 표준 인터페이스
    # ──────────────────────────────────────────────────────────────
    def open_add_modal(self) -> None:
        """정책추가 버튼 클릭 → 모달 열림 대기."""
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"정책 추가 모달이 열리지 않음: {e}") from e

    def open_modify_modal(self, policy_name: str) -> None:
        """행 선택 → 수정 버튼 클릭 → 모달 열림 대기 (저장 안 함)."""
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
            self.take_screenshot("unexpected_modal")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            raise Exception(f"예상치 못한 모달 발생: {msg!r}")

    def save_policy(self, name: str) -> None:
        """모달 열린 상태에서 이름 입력 + 저장 + 확인 모달 처리."""
        self.fill(self.SEL_NAME, name)
        self.click_attached(self.SEL_SAVE_BTN)
        self._dismiss_modal()
        self.wait_for(self.SEL_ADD_BTN)
        self._restore_page_size()

    def submit_and_message(self) -> str:
        """열린 모달에서 저장 클릭 → 확인/경고 모달 메시지 반환 + dismiss.

        생성·수정 '액션' 검증용 — 'NN 저장 하였습니다' 등 결과 메시지를 호출자가 확인.
        모달 없으면 '' 반환. 저장 성공 시 목록 복귀 + pageSize 복원.
        """
        self.click_attached(self.SEL_SAVE_BTN)
        self.page.wait_for_timeout(600)
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        self.wait_for(self.SEL_ADD_BTN)
        self._restore_page_size()
        return msg

    def close_modal(self) -> None:
        """모달 닫기 → 목록 복귀."""
        self.click(self.SEL_CLOSE_BTN)
        self.wait_for(self.SEL_ADD_BTN)

    def close_edit_modal(self) -> None:
        """EDIT 모달 닫기 (조건부 — 이미 닫혔을 수 있음)."""
        try:
            if self.page.locator(self.SEL_MODAL).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    def get_verify_values(self, saved_name: str) -> dict:
        """EDIT 모달 로드 후 정책 이름 필드 값 확인용 dict."""
        return {self.SEL_NAME: saved_name}

    # ── 속성 모달 (상세정보 보기) — 행 가운데(비이름 셀) 더블클릭 시 팝업 ──
    # Chrome MCP 실측 2026-06-09: 모달 id = detailSecureZoneAccessControlPolicy.
    #   토글=disabled 체크박스(id로 상태), USB=name='usbControlAuth' radio, 드라이브=label 텍스트.
    #   (※ 우측 #__layoutMainItemContentsDetail 패널은 별개 — 수정/상세 모달과 다름)
    SEL_DETAIL_MODAL = "div#detailSecureZoneAccessControlPolicy.in"
    SEL_DETAIL_CLOSE = (
        "div#detailSecureZoneAccessControlPolicy.in button:has-text('닫기'), "
        "div#detailSecureZoneAccessControlPolicy.in button[data-dismiss='modal']"
    )

    def open_detail_modal(self, policy_name: str) -> None:
        """행 가운데(비이름 셀) 더블클릭 → 속성 모달(상세정보 보기) 열기.

        Chrome MCP 검증 2026-06-09: 행 dblclick 핸들러는 ng-dblclick 속성이 아니라
        JS 이벤트 위임. click 시퀀스+dblclick 디스패치로 모달 열림 확인 →
        오버레이/좌표/actionability 무관한 evaluate 디스패치 사용 (이름 셀 td[0] 제외, td[1]).
        """
        row = self.page.locator(self.SEL_TABLE_ROW).filter(has_text=policy_name).first
        cell = row.locator("td").nth(1)   # 2번째 셀 (접근제어 사용) — 이름 셀 아님
        cell.evaluate(
            "el => ['mousedown','mouseup','click','mousedown','mouseup','click','dblclick']"
            ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))"
        )
        self.wait_for(self.SEL_DETAIL_MODAL, state="attached")

    # 접근제어 토글/USB 상태 — 속성 모달·수정 모달 공통 (id·name 동일)
    _AC_CHECKS = ("isAccessControl", "isCmd", "isRegedit", "isMmc",
                  "isShutdownAccessControl")
    _USB_LABELS = ["거부", "읽기", "읽기/쓰기"]

    def _read_ac_state(self, modal_sel: str) -> dict:
        """주어진 모달(속성/수정) 안의 접근제어 토글+USB 상태를 dict 로 반환.

        반환: {isAccessControl..isShutdownAccessControl: bool|None, usb: str}
        체크박스 id·USB radio name(usbControlAuth)은 속성/수정 모달 동일 → 공통.
        """
        out: dict = {}
        for cid in self._AC_CHECKS:
            loc = self.page.locator(f"{modal_sel} #{cid}").first
            out[cid] = loc.is_checked() if loc.count() > 0 else None
        radios = self.page.locator(f"{modal_sel} input[name='usbControlAuth']").all()
        idx = next((i for i, r in enumerate(radios) if r.is_checked()), -1)
        out["usb"] = self._USB_LABELS[idx] if 0 <= idx < 3 else "(미선택)"
        return out

    def read_detail_modal(self) -> dict:
        """열린 속성 모달의 토글/USB 상태 dict (읽기전용 검증용)."""
        return self._read_ac_state(self.SEL_DETAIL_MODAL)

    def read_modify_modal_state(self) -> dict:
        """열린 수정 모달의 토글/USB 상태 dict (속성 모달과 값 비교용)."""
        return self._read_ac_state(self.SEL_MODAL)

    def detail_modal_readonly(self) -> bool:
        """속성 모달의 모든 input 이 disabled(읽기전용=수정 불가)인지."""
        inputs = self.page.locator(f"{self.SEL_DETAIL_MODAL} input").all()
        if not inputs:
            return False
        return all(i.is_disabled() for i in inputs)

    def detail_modal_try_change(self) -> dict:
        """속성 모달 UI 요소(체크박스/라디오)에 실제 클릭 시도 → 값이 바뀌는지 확인.

        disabled 속성만으론 못 잡는 '읽기전용인데 실제로는 변경됨' 케이스 능동 검출.
        반환: {selector: {'before':bool,'after':bool,'changed':bool}}. 바뀌었으면 원복 시도.
        """
        m = self.SEL_DETAIL_MODAL
        out: dict = {}
        for sel in ("#isCmd", "#isRegedit", "#usbControlRead", "#usbControlReadWrite"):
            loc = self.page.locator(f"{m} {sel}").first
            if loc.count() == 0:
                continue
            before = loc.is_checked()
            try:
                loc.evaluate("el => el.click()")
                self.page.wait_for_timeout(120)
            except Exception:
                pass
            after = loc.is_checked()
            out[sel] = {"before": before, "after": after, "changed": before != after}
            if before != after:   # 읽기전용 우회됨 → 원복 시도
                try:
                    loc.evaluate("el => el.click()")
                except Exception:
                    pass
        return out

    def detail_modal_text(self) -> str:
        """속성 모달 본문 텍스트 (드라이브 값 등은 label 텍스트라 포함 여부로 검증).

        예: 마스터 ON 시 '지정 드라이브 숨기기 C;D;E ... 예외처리 S,W' 식으로 값 포함.
        """
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
    # 모달 헬퍼
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

    def _dismiss_modal(self) -> None:
        """정상 흐름 확인 모달 처리 (감지 → 확인 → 닫힘 대기)."""
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE
            )
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass

    def _close_modal_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL).count() > 0:
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
