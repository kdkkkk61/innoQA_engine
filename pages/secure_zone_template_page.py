"""pages/secure_zone_template_page.py — 시큐어존 템플릿 관리 (시큐어 드라이브 탭)

공통설정 > SecureZone > 템플릿 관리, 상단 탭 [시큐어 드라이브] (selectedTab=SECURE_DRIVE)
방식 B (list_page + sc0 UIScanner). 구조 전부 Chrome MCP 직접조작 확정(2026-06-23, 192.168.13.141).
yaml: config/scan_hints/secure_zone_template_secure_drive.yaml

[구조]
- 리스트 툴바: addItemBtn(추가)/modifyItemBtn(수정)/copyItemBtn(복사)/removeItemBtn(삭제)
- 메인 모달 addModifySecureZoneSecureDriveTemplate, 저장 버튼=**확인**
  templateName + isRegistEcmDrive + registOldDrive + 반출4(takeoutDrivePath*/Letter*/Label*/Quota*) + addSecureDriveBtn
- 서브 모달 addSecureDrive: label*/letter*/path* + hide + 경고(조건부) + 용량방식(WRITE/SYNC)* + quota(조건부) + desc
  · '추가' 시 정상이면 항목을 메인 리스트에 커밋 + **서브모달 자동 닫힘**(실측)
- 저장 필수: 이름 + 시큐어드라이브 항목 ≥1 + 반출4. 메시지: 빈값="템플릿 이름을 입력해 주세요." / 성공="저장 하였습니다."
- 속성 모달 detailSecureZoneTemplate: 행 td[1] 더블클릭, 읽기전용, 대부분 텍스트 표시

[명명/cleanup — 연계(정책이 템플릿 참조)]
- [AUTO]_sztpl_sd... = 휘발성(sc5c cleanup 대상). [AUTO_<날짜>]_sztpl_sd... = KEEP(연계, sc5c 보존).
- delete_all_test_data(): [AUTO] + [AUTO_<날짜>] 둘 다 (sc1 시작). delete_all_auto(): [AUTO] 만 (sc5c).
"""
import re

from pages.base_page import BasePage
from pages.shared._overlay import overlay_off


class SecureZoneTemplateSecureDrivePage(BasePage):
    """시큐어존 템플릿 — 시큐어 드라이브 탭 (방식 B)."""

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
    SEL_TABLE_ROW        = "table tbody tr"
    SEL_TABLE_ROW_ACTIVE = "table tbody tr.tActive"
    SEL_CHECKBOX         = "input[type='checkbox']"

    # ── 메인 모달 ─────────────────────────────────────────────────
    SEL_MODAL     = "div#addModifySecureZoneSecureDriveTemplate.in"
    SEL_NAME      = "input#templateName"
    SEL_SAVE_BTN  = "div#addModifySecureZoneSecureDriveTemplate.in button:has-text('확인')"
    SEL_CLOSE_BTN = ("div#addModifySecureZoneSecureDriveTemplate.in button:has-text('닫기'), "
                     "div#addModifySecureZoneSecureDriveTemplate.in button[data-dismiss='modal']")

    # ── 확인/경고 모달 ────────────────────────────────────────────
    SEL_CONFIRM_MODAL_OPENED = "div#__globalMessageModal.in"
    SEL_CONFIRM_BTN          = "div#__globalMessageModal button:has-text('확인')"
    SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

    _TIMEOUT_TABLE = 5000
    _TIMEOUT_MODAL = 3000
    _TIMEOUT_STALE = 1000

    _AUTO_ANY = re.compile(r"^\[AUTO(_\d{4,8})?\]")   # [AUTO] 또는 [AUTO_0623] 둘 다

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
        self.page.evaluate(f"window.location.hash = '{self._HASH_SECURE_DRIVE}';")
        self.wait_for(self.SEL_ADD_BTN)
        try:
            self.page.locator(self.SEL_TABLE_ROW).first.wait_for(
                state="attached", timeout=self._TIMEOUT_TABLE)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 목록 / 행
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

    def check_row(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
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
    # 삭제 / cleanup (방식 B 라이프사이클)
    # ──────────────────────────────────────────────────────────────
    def delete_all_test_data(self) -> None:
        """[AUTO] + [AUTO_<날짜>] 둘 다 삭제 — sc1 시작 clean slate."""
        for name in [n for n in self.get_template_names() if self._AUTO_ANY.match(n)]:
            self.delete_template(name)

    def delete_all_auto(self) -> None:
        """[AUTO] (날짜 없음) 만 삭제, [AUTO_<날짜>] KEEP 보존 — sc5c."""
        for name in [n for n in self.get_template_names() if n.startswith("[AUTO]")]:
            self.delete_template(name)

    def delete_template(self, name: str) -> None:
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")

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
    # 모달 열기/닫기 (sc0 UIScanner modal_open_fn/modal_close_fn 용)
    # ──────────────────────────────────────────────────────────────
    def open_add_modal(self) -> None:
        self.click(self.SEL_ADD_BTN)
        try:
            self.wait_for(self.SEL_MODAL, state="attached")
        except Exception as e:
            raise Exception(f"템플릿 추가 모달이 열리지 않음: {e}") from e

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

    # ── 메인 모달 필드 / 서브모달 (sc1+ UI 구조용) ────────────────
    SEL_ECM           = "div#addModifySecureZoneSecureDriveTemplate.in input#isRegistEcmDrive"
    SEL_OLD_DRIVE     = "div#addModifySecureZoneSecureDriveTemplate.in textarea#registOldDrive"
    SEL_TAKEOUT_PATH  = "div#addModifySecureZoneSecureDriveTemplate.in input#takeoutDrivePath"
    SEL_TAKEOUT_LETTER= "div#addModifySecureZoneSecureDriveTemplate.in input#takeoutDriveLetter"
    SEL_TAKEOUT_LABEL = "div#addModifySecureZoneSecureDriveTemplate.in input#takeoutDriveLabel"
    SEL_TAKEOUT_QUOTA = "div#addModifySecureZoneSecureDriveTemplate.in input#takeoutDriveQuota"
    SEL_ADD_DRIVE_BTN = "div#addModifySecureZoneSecureDriveTemplate.in button#addSecureDriveBtn"
    SEL_TAKEOUT_HIDE  = "div#addModifySecureZoneSecureDriveTemplate.in input#isTakeoutDrivePathHide"

    SEL_SUB        = "div#addSecureDrive.in"
    SEL_SUB_LABEL  = "div#addSecureDrive.in input#secureDriveLabel"
    SEL_SUB_LETTER = "div#addSecureDrive.in input#secureDriveLetter"
    SEL_SUB_PATH   = "div#addSecureDrive.in input#secureDrivePath"
    SEL_SUB_QTYPE_WRITE = "div#addSecureDrive.in input#secureDriveQuotaTypeWrite"
    SEL_SUB_QTYPE_SYNC  = "div#addSecureDrive.in input#secureDriveQuotaTypeSync"
    SEL_SUB_CLOSE  = ("div#addSecureDrive.in button:has-text('닫기'), "
                      "div#addSecureDrive.in button[data-dismiss='modal']")

    def column_headers(self) -> list[str]:
        """리스트 컬럼 헤더 텍스트."""
        return [h.inner_text().strip()
                for h in self.page.locator("table thead th").all()
                if h.inner_text().strip()]

    def field_present(self, selector: str) -> bool:
        return self.page.locator(selector).count() > 0

    def open_sub_modal(self) -> None:
        """메인 모달에서 시큐어드라이브 추가(addSecureDriveBtn) → 서브모달(addSecureDrive) 열림.
        실측 2026-06-23: 정상 입력 후 '추가' 시 서브 자동 닫힘 / '닫기'로 메인 복귀(항목 미커밋)."""
        with overlay_off(self.page):
            self.page.locator(self.SEL_ADD_DRIVE_BTN).first.click(force=True)
        self.page.locator(self.SEL_SUB).wait_for(state="attached", timeout=self._TIMEOUT_MODAL)

    def close_sub_modal(self) -> None:
        """서브모달 '닫기' (항목 미커밋, 메인 모달 유지)."""
        try:
            with overlay_off(self.page):
                self.page.locator(self.SEL_SUB_CLOSE).first.click(force=True, timeout=2000)
            self.page.locator(self.SEL_SUB).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    def type_clamped(self, selector: str, text: str) -> int:
        """실제 per-key 타이핑 → 입력된 실제 길이 반환 (maxlength 클램핑 검증용).

        ⚠️ fill() 은 maxlength 무시(value 직접 설정)라 클램핑 검증 불가 → press_sequentially 사용.
        qa-block-overlay 때문에 raw click 은 타임아웃 → overlay OFF + force click 후 타이핑(정책 type_block_time 패턴).
        """
        loc = self.page.locator(selector).first
        with overlay_off(self.page):
            loc.click(force=True)
        loc.fill("")
        loc.press_sequentially(text, delay=2)
        self.page.wait_for_timeout(150)
        return len(loc.input_value())

    def submit_and_message(self) -> str:
        """메인 '확인'(저장) 클릭 → 확인/경고 모달 메시지 반환 + dismiss. 성공 시 목록 복귀.
        sc2 필수검증(빈값→경고) / sc3 CRUD 공용."""
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
        if (self.page.locator(self.SEL_ADD_BTN).count() > 0
                and self.page.locator(self.SEL_MODAL).count() == 0):
            self.wait_for(self.SEL_ADD_BTN)
        return msg

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
