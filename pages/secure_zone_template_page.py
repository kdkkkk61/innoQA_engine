"""pages/secure_zone_template_page.py — 시큐어존 템플릿 관리 (시큐어 드라이브 탭)

공통설정(App Setting) > SecureZone > 템플릿 관리, 상단 탭 [시큐어 드라이브] (selectedTab=SECURE_DRIVE)
URL: #!/managerSecureZoneTemplate?...&selectedTab=SECURE_DRIVE

[구조 — Chrome MCP 직접조작 확정 2026-06-23, 콘솔 192.168.13.141]
- 리스트 툴바: 템플릿추가 addItemBtn / 수정 modifyItemBtn / 복사 copyItemBtn / 삭제 removeItemBtn
- 메인 모달 addModifySecureZoneSecureDriveTemplate "시큐어존 시큐어드라이브 추가/수정", 저장 버튼=**확인**
  · templateName(이름) / isRegistEcmDrive(ECM연동 체크) / registOldDrive(예외드라이브 textarea)
  · 반출드라이브(필수): takeoutDrivePath* / isTakeoutDrivePathHide / takeoutDriveLetter* / takeoutDriveLabel* / takeoutDriveQuota*
  · addSecureDriveBtn(추가) → 서브모달
- 서브 모달 addSecureDrive "시큐어드라이브 추가/수정": secureDriveLabel* / secureDriveLetter* / secureDrivePath*
  / isSecureDrivePathHide / isSystemDriveWarningQuota(→systemDriveWarningQuota 조건부)
  / secureDriveQuotaTypeWrite(WRITE)·secureDriveQuotaTypeSync(SYNC) radio* / secureDriveQuota(조건부 WRITE) / description
  · 서브 '추가' = 항목을 메인 리스트에 커밋 + 필드 클리어 + **서브 열린 채 유지(multi-add)** → '닫기'로 메인 복귀
- 저장 필수: 이름 + 시큐어드라이브 항목 ≥1(서브) + 반출드라이브 4필드. (반출 누락 시 '반출드라이브 생성위치를 입력해 주세요')
- 속성(상세) 모달 detailSecureZoneTemplate "템플릿 상세정보 보기": 행 더블클릭, 읽기전용,
  대부분 텍스트 표시(input 은 체크박스 isRegistEcmDrive/isTakeoutDrivePathHide 2개뿐) → 값은 모달 텍스트로 대조.
"""
from pages.base_page import BasePage
from pages.shared._overlay import overlay_off


class SecureZoneTemplateSecureDrivePage(BasePage):
    """시큐어존 템플릿 — 시큐어 드라이브 탭 (탭/서브모달 인식)."""

    PAGE_ID = "secure_zone_template_secure_drive"
    AUTO_NAME_PREFIX = "[AUTO]_sztpl_sd"

    # ── 네비게이션 ────────────────────────────────────────────────
    SEL_LEFT_NAV          = "ul.leftNavList"
    SEL_APP_SETTING_MENU  = "a[data-menuid='managerAppSetting']"
    SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"
    SEL_SZ_SECTION_HEADER = "a.managerSecureZone"
    SEL_TEMPLATE_MENU     = "a[data-menuid='managerSecureZoneTemplate']"

    # ── 목록 ──────────────────────────────────────────────────────
    SEL_ADD_BTN          = "button#addItemBtn"
    SEL_MODIFY_BTN       = "button#modifyItemBtn"
    SEL_DELETE_BTN       = "button#removeItemBtn"
    SEL_COPY_BTN         = "button#copyItemBtn"
    SEL_SEARCH           = "input#searchText"
    SEL_TABLE_ROW        = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE = "table tbody tr.tActive"
    SEL_CHECKBOX         = "input[type='checkbox']"

    # ── 메인 모달 (ADD/EDIT 공용) ─────────────────────────────────
    SEL_MODAL      = "div#addModifySecureZoneSecureDriveTemplate.in"
    SEL_NAME       = "input#templateName"
    SEL_SAVE_BTN   = "div#addModifySecureZoneSecureDriveTemplate.in button:has-text('확인')"
    SEL_CLOSE_BTN  = ("div#addModifySecureZoneSecureDriveTemplate.in button:has-text('닫기'), "
                      "div#addModifySecureZoneSecureDriveTemplate.in button[data-dismiss='modal']")
    SEL_ADD_DRIVE_BTN = "div#addModifySecureZoneSecureDriveTemplate.in button#addSecureDriveBtn"

    # 반출드라이브 (메인 모달, 필수)
    SEL_TAKEOUT_PATH  = "input#takeoutDrivePath"
    SEL_TAKEOUT_LETTER= "input#takeoutDriveLetter"
    SEL_TAKEOUT_LABEL = "input#takeoutDriveLabel"
    SEL_TAKEOUT_QUOTA = "input#takeoutDriveQuota"

    # ── 서브 모달 (시큐어드라이브 항목) ───────────────────────────
    SEL_SUB        = "div#addSecureDrive.in"
    SEL_SUB_LABEL  = "div#addSecureDrive.in input#secureDriveLabel"
    SEL_SUB_LETTER = "div#addSecureDrive.in input#secureDriveLetter"
    SEL_SUB_PATH   = "div#addSecureDrive.in input#secureDrivePath"
    SEL_SUB_QUOTA  = "div#addSecureDrive.in input#secureDriveQuota"
    SEL_SUB_ADD    = "div#addSecureDrive.in button:has-text('추가')"
    SEL_SUB_CLOSE  = ("div#addSecureDrive.in button:has-text('닫기'), "
                      "div#addSecureDrive.in button[data-dismiss='modal']")

    # ── 속성(상세) 모달 ───────────────────────────────────────────
    SEL_DETAIL_MODAL = "div#detailSecureZoneTemplate.in"
    SEL_DETAIL_CLOSE = ("div#detailSecureZoneTemplate.in button:has-text('닫기'), "
                        "div#detailSecureZoneTemplate.in button[data-dismiss='modal']")

    # ── 확인/경고 모달 (전역) ─────────────────────────────────────
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _HASH_SECURE_DRIVE = (
        "#!/managerSecureZoneTemplate"
        "?pageNo=1&pageSize=100&searchText=&selectedTab=SECURE_DRIVE"
        "&szTemplateType=&status=&startIndex=0&sortIndex=0&sortOrder=0"
    )

    # ──────────────────────────────────────────────────────────────
    # 네비게이션
    # ──────────────────────────────────────────────────────────────
    def navigate_to(self) -> None:
        """템플릿 관리 > 시큐어 드라이브 탭 (selectedTab=SECURE_DRIVE, pageSize=100)."""
        self._close_all_modals()
        self._dismiss_stale_confirm_modal()

        if (self.is_visible(self.SEL_ADD_BTN)
                and "managerSecureZoneTemplate" in self.page.url
                and "selectedTab=SECURE_DRIVE" in self.page.url
                and "pageSize=100" in self.page.url):
            return

        if "manager/main.html" not in self.page.url:
            self.page.goto(f"{self.host_origin}/manager/main.html")
            self._dismiss_stale_confirm_modal()

        try:
            self.page.locator(self.SEL_LEFT_NAV).first.wait_for(
                state="visible", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass
        if not self.is_visible(self.SEL_LEFT_NAV):
            raise RuntimeError(
                "매니저 페이지 UI 없음 — 세션 만료 또는 접근 권한 없음.\npytest를 재실행해 주세요.")

        if not self.is_visible(self.SEL_APP_SETTING_PANEL):
            self.click(self.SEL_APP_SETTING_MENU)
            self.wait_for(self.SEL_APP_SETTING_PANEL)
        if not self.is_visible(self.SEL_TEMPLATE_MENU):
            self.click(self.SEL_SZ_SECTION_HEADER)
            self.wait_for(self.SEL_TEMPLATE_MENU)
        self.click(self.SEL_TEMPLATE_MENU)
        self.wait_for(self.SEL_ADD_BTN)
        # 시큐어 드라이브 탭 + pageSize=100 (hash)
        self.page.evaluate(f"window.location.hash = '{self._HASH_SECURE_DRIVE}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 목록 조회 / 행 선택
    # ──────────────────────────────────────────────────────────────
    def get_template_names(self) -> list[str]:
        names = []
        for row in self.page.locator(self.SEL_TABLE_ROW).all():
            dn = row.get_attribute("data-name")
            if dn:
                names.append(dn)
                continue
            texts = [td.inner_text().strip() for td in row.locator("td").all()]
            name = next((t for t in texts if t), "")
            if name:
                names.append(name)
        return names

    def get_auto_names(self) -> list[str]:
        return [n for n in self.get_template_names() if n.startswith("[AUTO]")]

    def _row_locator(self, name: str, active: bool = False):
        sel = self.SEL_TABLE_ROW_ACTIVE if active else self.SEL_TABLE_ROW
        safe = name.replace("\\", "\\\\").replace('"', '\\"')
        exact = self.page.locator(f'{sel}[data-name="{safe}"]')
        try:
            if exact.count() > 0:
                return exact.first
        except Exception:
            pass
        return self.page.locator(sel).filter(has_text=name).first

    def click_row(self, name: str) -> None:
        """행 클릭(tActive). 이미 선택돼 있으면 생략. 최대 3회 재시도 (mousedown 필요 → force)."""
        try:
            if self._row_locator(name, active=True).count() > 0:
                return
        except Exception:
            pass
        row = self._row_locator(name)
        for attempt in range(3):
            self._toggle_overlay(False)
            try:
                row.click(force=True)
            finally:
                self._toggle_overlay(True)
            try:
                self._row_locator(name, active=True).wait_for(
                    state="attached", timeout=self._TIMEOUT_MODAL)
                return
            except Exception:
                print(f"\n[click_row] tActive 미확인 ({attempt+1}회), 재시도...")
        raise Exception(f"행 선택 실패 (3회): {name}")

    def check_row(self, name: str) -> None:
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 생성 템플릿([AUTO] 접두사)만 조작 가능합니다")
        cb = self._row_locator(name).locator(self.SEL_CHECKBOX).first
        if cb.is_checked():
            return
        self._toggle_overlay(False)
        try:
            cb.click()
        finally:
            self._toggle_overlay(True)
        if not cb.is_checked():
            raise Exception(f"체크박스 클릭 후 미체크: {name}")

    # ──────────────────────────────────────────────────────────────
    # 삭제 ([AUTO] 만)
    # ──────────────────────────────────────────────────────────────
    def delete_all_auto(self) -> None:
        for name in self.get_auto_names():
            self.delete_template(name)

    def delete_template(self, name: str) -> None:
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 생성 템플릿([AUTO] 접두사)만 조작 가능합니다")

        def _attempt():
            self.check_row(name)
            self.click(self.SEL_DELETE_BTN)
            if not self.is_confirm_modal_visible():
                raise Exception("삭제 버튼 클릭 후 모달 없음")
            msg = self.get_modal_message()
            if "하시겠습니까" not in msg:
                self.click_attached(self.SEL_CONFIRM_BTN)
                self.wait_for_modal_closed()
                raise Exception(f"삭제 중 에러 모달: {msg!r}")
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self.wait_for(self.SEL_ADD_BTN)

        try:
            _attempt()
        except Exception as e:
            print(f"\n[delete_template] 1차 실패: {e}\nnavigate_to() 후 재시도...")
            self.navigate_to()
            _attempt()

    # ──────────────────────────────────────────────────────────────
    # 모달 열기/닫기
    # ──────────────────────────────────────────────────────────────
    def open_add_modal(self) -> None:
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"템플릿 추가 모달이 열리지 않음: {e}") from e

    def open_modify_modal(self, name: str) -> None:
        self.click_row(name)
        self.click(self.SEL_MODIFY_BTN)
        race = f"{self.SEL_CONFIRM_MODAL_OPENED}, {self.SEL_MODAL}"
        try:
            self.page.locator(race).first.wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        except Exception as e:
            raise Exception(f"템플릿 수정 모달이 열리지 않음: {e}") from e
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            msg = self.get_modal_message()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            raise Exception(f"예상치 못한 모달: {msg!r}")

    def close_modal(self) -> None:
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
        for _ in range(6):
            modals = self.page.locator(".modal-wrap.in, .modal.in")
            if modals.count() == 0:
                return
            top = modals.last
            clicked = False
            for label in ("닫기", "취소", "확인"):
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
                try:
                    top.evaluate("el => el.classList.remove('in')")
                except Exception:
                    pass
            self.page.wait_for_timeout(300)

    # ──────────────────────────────────────────────────────────────
    # 시큐어드라이브 항목 (서브모달) — 이 탭의 핵심
    # ──────────────────────────────────────────────────────────────
    def add_secure_drive(self, label: str, letter: str, path: str,
                         quota_type: str = "WRITE", quota: str = "100") -> None:
        """addSecureDriveBtn → 서브모달 채우기 → '추가'(메인 리스트 커밋) → 서브 '닫기'.

        quota_type: 'WRITE'(직접입력→quota MB) | 'SYNC'(잔여용량 동기화). 서브 '추가'는
        항목 커밋 후 필드 클리어하고 서브를 열린 채 둠(multi-add) → 닫기로 메인 복귀(실측 2026-06-23).
        """
        with overlay_off(self.page):
            self.page.locator(self.SEL_ADD_DRIVE_BTN).first.click(force=True)
        self.page.locator(self.SEL_SUB).wait_for(state="attached", timeout=self._TIMEOUT_MODAL)
        self.fill(self.SEL_SUB_LABEL, label)
        self.fill(self.SEL_SUB_LETTER, letter)
        self.fill(self.SEL_SUB_PATH, path)
        rid = "secureDriveQuotaTypeWrite" if quota_type == "WRITE" else "secureDriveQuotaTypeSync"
        with overlay_off(self.page):
            self.page.locator(f"{self.SEL_SUB} input#{rid}").first.click(force=True)
        self.page.wait_for_timeout(150)
        if quota_type == "WRITE":
            self.fill(self.SEL_SUB_QUOTA, quota)
        with overlay_off(self.page):
            self.page.locator(self.SEL_SUB_ADD).first.click(force=True)
        self.page.wait_for_timeout(400)
        # 추가 후 경고 모달(검증 실패 등) 있으면 surface 위해 닫지 않고 둠 — 정상이면 서브만 닫기
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() == 0:
            with overlay_off(self.page):
                self.page.locator(self.SEL_SUB_CLOSE).first.click(force=True)
            try:
                self.page.locator(self.SEL_SUB).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
            except Exception:
                pass

    def add_secure_drive_msg(self, label: str, letter: str, path: str,
                             quota_type: str = "WRITE", quota: str = "100") -> str:
        """add_secure_drive 시도 → 경고 메시지 반환 + dismiss (필수 누락/중복 등 검증용). 정상이면 ''."""
        self.add_secure_drive(label, letter, path, quota_type, quota)
        msg = ""
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            self._close_sub_if_open()
        return msg

    def _close_sub_if_open(self) -> None:
        try:
            if self.page.locator(self.SEL_SUB).count() > 0:
                with overlay_off(self.page):
                    self.page.locator(self.SEL_SUB_CLOSE).first.click(force=True)
        except Exception:
            pass

    def secure_drive_rows(self) -> list[str]:
        """메인 모달의 시큐어드라이브 항목 리스트 행 텍스트."""
        m = self.page.locator(self.SEL_MODAL).first
        if m.count() == 0:
            return []
        return [r.inner_text().replace("\n", " ").strip()
                for r in m.locator("table tbody tr").all()]

    def fill_takeout(self, path: str, letter: str, label: str, quota: str) -> None:
        """반출드라이브 4필수 필드 입력."""
        self.fill(f"{self.SEL_MODAL} {self.SEL_TAKEOUT_PATH}", path)
        self.fill(f"{self.SEL_MODAL} {self.SEL_TAKEOUT_LETTER}", letter)
        self.fill(f"{self.SEL_MODAL} {self.SEL_TAKEOUT_LABEL}", label)
        self.fill(f"{self.SEL_MODAL} {self.SEL_TAKEOUT_QUOTA}", quota)

    # ──────────────────────────────────────────────────────────────
    # 저장
    # ──────────────────────────────────────────────────────────────
    def submit_and_message(self) -> str:
        """메인 '확인' 클릭 → 확인/경고 모달 메시지 반환 + dismiss. 성공 시 목록 복귀."""
        with overlay_off(self.page):
            self.page.locator(self.SEL_SAVE_BTN).first.click(force=True)
        self.page.wait_for_timeout(600)
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        if self.page.locator(self.SEL_ADD_BTN).count() > 0 and self.page.locator(self.SEL_MODAL).count() == 0:
            self.wait_for(self.SEL_ADD_BTN)
        return msg

    def create_basic_template(self, name: str, sd_letter: str = "Q", to_letter: str = "T") -> str:
        """최소 정상 생성: 이름 + 시큐어드라이브 항목 1건 + 반출드라이브 4필드 → 확인.

        [AUTO] 접두사만 허용. 반환: 저장 결과 메시지.
        sd_letter/to_letter 로 드라이브 문자 변경 가능(중복 이름 테스트에서 문자 충돌과 분리용).
        """
        if not name.startswith("[AUTO]"):
            raise Exception("테스트 생성 템플릿([AUTO] 접두사)만 허용합니다")
        self.fill(self.SEL_NAME, name)
        self.add_secure_drive("sd_lbl", sd_letter, "C:\\sztpl", "WRITE", "100")
        self.fill_takeout("C:\\sztpl_to", to_letter, "to_lbl", "1024")
        return self.submit_and_message()

    # ──────────────────────────────────────────────────────────────
    # 속성(상세) 모달 — 더블클릭, 읽기전용
    # ──────────────────────────────────────────────────────────────
    def open_detail_modal(self, name: str) -> None:
        row = self._row_locator(name)
        cell = row.locator("td").nth(1)
        cell.evaluate(
            "el => ['mousedown','mouseup','click','mousedown','mouseup','click','dblclick']"
            ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))")
        self.wait_for(self.SEL_DETAIL_MODAL, state="attached")

    def detail_modal_text(self) -> str:
        m = self.page.locator(self.SEL_DETAIL_MODAL).first
        if m.count() == 0:
            return ""
        body = m.locator(".modal-body")
        target = body if body.count() > 0 else m
        return " ".join(target.first.inner_text().split())

    def detail_modal_readonly(self) -> bool:
        """속성 모달의 input(체크박스 2개)이 전부 disabled 인지."""
        inputs = self.page.locator(f"{self.SEL_DETAIL_MODAL} input").all()
        if not inputs:
            return False
        return all(i.is_disabled() for i in inputs)

    def close_detail_modal(self) -> None:
        try:
            self.page.locator(self.SEL_DETAIL_CLOSE).first.evaluate("el => el.click()")
            self.page.locator(self.SEL_DETAIL_MODAL).wait_for(
                state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    def read_modify_field(self, css_id: str) -> str:
        """수정 모달 필드 값(저장 검증 기준)."""
        loc = self.page.locator(f"{self.SEL_MODAL} #{css_id}").first
        if loc.count() == 0:
            return ""
        try:
            return loc.input_value()
        except Exception:
            return ""

    def close_edit_modal(self) -> None:
        try:
            if self.page.locator(self.SEL_MODAL).count() > 0:
                self.close_modal()
            else:
                self.wait_for(self.SEL_ADD_BTN)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 확인/경고 모달 헬퍼
    # ──────────────────────────────────────────────────────────────
    def get_modal_message(self) -> str:
        return self.page.locator(self.SEL_MODAL_BODY_TEXT).first.inner_text().strip()

    def is_confirm_modal_visible(self) -> bool:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_MODAL)
            return True
        except Exception:
            return False

    def wait_for_modal_closed(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="detached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    def _dismiss_stale_confirm_modal(self) -> None:
        try:
            self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=self._TIMEOUT_STALE)
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        except Exception:
            pass
