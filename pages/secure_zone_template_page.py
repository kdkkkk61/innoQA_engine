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
- [AUTO]_sztpl_sd... = 휘발성(sc5 cleanup 대상). [AUTO_<날짜>]_sztpl_sd... = 날짜본(영속·연계, sc5 보존).
- delete_all_test_data(): [AUTO] + [AUTO_<날짜>] 둘 다 (sc1 시작). delete_all_auto(): [AUTO] 만 (sc5).
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
    # 저장 버튼: 추가 모달='확인'(addbtn) / 수정 모달='수정'(modifybtn) — 같은 모달 id, 모드별 표시 토글(실측 2026-06-29)
    SEL_SAVE_ADD    = "div#addModifySecureZoneSecureDriveTemplate.in button[addbtn]"
    SEL_SAVE_MODIFY = "div#addModifySecureZoneSecureDriveTemplate.in button[modifybtn]"
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
        """[AUTO] (날짜 없음) 만 삭제, [AUTO_<날짜>] 날짜본 보존 — sc5."""
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

    def open_modify_modal(self, name: str) -> None:
        """행 활성화(tActive) → 수정 버튼 → 수정 모달(저장값 로드).
        실측 2026-06-23: 수정은 체크박스 선택 미반영('선택된 항목이 없습니다') →
        실제 행 클릭(tActive) 필요. 클릭 후 modifyItemBtn → 저장값 로드된 모달."""
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        with overlay_off(self.page):
            self._row_locator(name).click(force=True)
        self.page.wait_for_timeout(200)
        self.click(self.SEL_MODIFY_BTN)
        self.wait_for(self.SEL_MODAL, state="attached")

    # ── 속성(상세) 모달 — sc5 표시 검증 ──────────────────────────────
    SEL_DETAIL_MODAL = "div#detailSecureZoneTemplate.in"
    SEL_DETAIL_CLOSE = "div#detailSecureZoneTemplate.in button:has-text('닫기')"

    def open_detail_modal(self, name: str) -> None:
        """행 td[1] 더블클릭 → 속성(상세정보 보기) 모달. 읽기전용 표시 검증용(실측 2026-06-29)."""
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        # 합성 더블클릭으로 행 열기 + 재시도. Bootstrap3 모달은 position 오프셋으로 Playwright visible 체크 실패 →
        # .in 클래스 + state="attached" 로 감지(메모리/실측). visible 로 바꾸면 모달이 열려도 30s 타임아웃(2026-06-30 회귀 정정)
        cell = self._row_locator(name).locator("td").nth(1)
        det = self.page.locator(self.SEL_DETAIL_MODAL)
        for _ in range(3):
            cell.evaluate(
                "el => ['mousedown','mouseup','click','mousedown','mouseup','click','dblclick']"
                ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))"
            )
            try:
                det.wait_for(state="attached", timeout=4000)   # 짧게 — 실패해도 빠르게
                self.page.wait_for_timeout(400)                # 비동기 표시값 렌더 대기(텍스트 대조 전)
                return
            except Exception:
                self.page.wait_for_timeout(300)
        raise Exception(f"속성 모달이 열리지 않음(3회 재시도 실패): {name}")

    def detail_modal_try_change(self) -> dict:
        """속성 모달 체크박스에 실제 클릭 시도 → 값이 바뀌는지(능동 읽기전용 검증). 바뀌면 원복."""
        out: dict = {}
        for sel in ("#isRegistEcmDrive", "#isTakeoutDrivePathHide"):
            loc = self.page.locator(f"{self.SEL_DETAIL_MODAL} {sel}").first
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
            if before != after:
                try:
                    loc.evaluate("el => el.click()")
                except Exception:
                    pass
        return out

    def detail_modal_text(self) -> str:
        """속성 모달 본문 텍스트(이름·반출·시큐어드라이브 항목 등은 텍스트라 포함 여부로 표시 검증)."""
        m = self.page.locator(self.SEL_DETAIL_MODAL).first
        if m.count() == 0:
            return ""
        return " ".join(m.inner_text().split())

    def detail_modal_ecm_hide(self) -> dict:
        """속성 모달의 체크박스 2개 상태(수정 모달값과 대조용)."""
        out = {}
        for cid in ("isRegistEcmDrive", "isTakeoutDrivePathHide"):
            loc = self.page.locator(f"{self.SEL_DETAIL_MODAL} #{cid}").first
            out[cid] = loc.is_checked() if loc.count() > 0 else None
        return out

    def close_detail_modal(self) -> None:
        try:
            self.page.locator(self.SEL_DETAIL_CLOSE).first.evaluate("el => el.click()")
            self.page.locator(self.SEL_DETAIL_MODAL).wait_for(state="detached", timeout=self._TIMEOUT_MODAL)
        except Exception:
            pass

    def open_sd_detail_warn_quota(self) -> str:
        """속성 모달의 시큐어드라이브 문자(첫 행) 클릭 → 중첩 'sd 상세'(id=addSecureDrive, 읽기전용) → 경고용량 표시 텍스트 반환.
        실측 2026-06-29: 경고용량 단위가 입력(GB)과 달리 MB 로 표시(단위 불일치). 중첩 닫기는 close_sd_detail()."""
        cell = self.page.locator(f"{self.SEL_DETAIL_MODAL} table tbody tr").first.locator("td").first
        nested = self.page.locator("div#addSecureDrive.in")
        for _ in range(2):
            cell.evaluate("el => ['mousedown','mouseup','click']"
                          ".forEach(t => el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})))")
            try:
                nested.first.wait_for(state="attached", timeout=3000)   # Bootstrap3 중첩 모달 → attached(visible 체크 실패)
                self.page.wait_for_timeout(400)
                break
            except Exception:
                self.page.wait_for_timeout(300)
        if nested.count() == 0:
            return ""
        t = " ".join(nested.first.inner_text().split())
        i = t.find("경고용량")
        return t[i:i + 18] if i >= 0 else ""

    def close_sd_detail(self) -> None:
        """중첩 sd 상세(addSecureDrive 읽기전용) 닫기."""
        try:
            self.page.locator("div#addSecureDrive.in button:has-text('닫기')").first.evaluate("el => el.click()")
            self.page.wait_for_timeout(300)
        except Exception:
            pass

    def set_checkbox(self, selector: str, checked: bool) -> None:
        """체크박스를 원하는 상태로 설정 — 현재와 다르면 JS 클릭(overlay/visibility 무관)."""
        loc = self.page.locator(selector).first
        if loc.count() > 0 and loc.is_checked() != checked:
            loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(120)

    def read_modify_modal_state(self) -> dict:
        """열린 수정 모달의 전 필드 저장값 — sc5 저장 round-trip 검증용(속성 표시와 대조)."""
        def _v(sel):
            loc = self.page.locator(sel).first
            return loc.input_value() if loc.count() > 0 else ""
        def _c(sel):
            loc = self.page.locator(sel).first
            return loc.is_checked() if loc.count() > 0 else None
        return {
            "name": _v(f"{self.SEL_MODAL} {self.SEL_NAME}"),
            "to_path": _v(self.SEL_TAKEOUT_PATH), "to_letter": _v(self.SEL_TAKEOUT_LETTER),
            "to_label": _v(self.SEL_TAKEOUT_LABEL), "to_quota": _v(self.SEL_TAKEOUT_QUOTA),
            "old_drive": _v(self.SEL_OLD_DRIVE),
            "ecm": _c(self.SEL_ECM), "hide": _c(self.SEL_TAKEOUT_HIDE),
            "sd_rows": self.secure_drive_rows(),
        }

    SEL_SEARCH_INPUT = "input#searchText"
    SEL_SEARCH_BTN   = "span#searchBtn"
    SEL_SUB_PATH_HIDE   = "div#addSecureDrive.in input#isSecureDrivePathHide"
    SEL_SUB_WARN_TOGGLE = "div#addSecureDrive.in input#isSystemDriveWarningQuota"

    def checkbox_toggles(self, selector: str):
        """체크박스 토글 동작 — 클릭 시 상태 반전, 다시 클릭 시 복귀하는지. 반환 bool / 미존재 None."""
        loc = self.page.locator(selector).first
        if loc.count() == 0:
            return None
        before = loc.is_checked()
        with overlay_off(self.page):
            loc.click(force=True)
        self.page.wait_for_timeout(120)
        mid = loc.is_checked()
        with overlay_off(self.page):
            loc.click(force=True)
        self.page.wait_for_timeout(120)
        end = loc.is_checked()
        return (mid != before) and (end == before)

    def radio_exclusive(self, sel_a: str, sel_b: str):
        """라디오 상호배타 — A 선택 시 A만/ B 선택 시 B만 체크되는지. 반환 (a_ok, b_ok, exclusive)."""
        a = self.page.locator(sel_a).first
        b = self.page.locator(sel_b).first
        with overlay_off(self.page):
            a.click(force=True)
        self.page.wait_for_timeout(120)
        a_ok = a.is_checked() and not b.is_checked()
        with overlay_off(self.page):
            b.click(force=True)
        self.page.wait_for_timeout(120)
        b_ok = b.is_checked() and not a.is_checked()
        return a_ok, b_ok, (a_ok and b_ok)

    def search(self, query: str) -> None:
        """리스트 검색(템플릿 이름 필터). searchText 입력 + span#searchBtn 클릭.
        실측 2026-06-23: searchTextOption=templateName 으로 이름 부분일치 필터. 빈값=전체 복귀."""
        self.fill(self.SEL_SEARCH_INPUT, query)
        with overlay_off(self.page):
            self.page.locator(self.SEL_SEARCH_BTN).first.click(force=True)
        self.page.wait_for_timeout(800)

    def copy_template(self, name: str) -> str:
        """체크박스 선택 + 복사 버튼 → '복사 하시겠습니까?' 확인 → 복사본(원본+'_copy') 생성.
        반환: 복사본 이름. 실측 2026-06-23: 복사는 체크박스 선택(tActive 아님), 확인 시 즉시 복사.
        [AUTO]/[AUTO_날짜] 접두사만 허용(데이터 안전 — 복사본도 접두사 유지)."""
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 조작 가능합니다")
        self.check_row(name)
        self.click(self.SEL_COPY_BTN)
        if not self.is_confirm_modal_visible():
            raise Exception("복사 버튼 클릭 후 확인 모달 없음")
        msg = self.get_modal_message()
        if "복사" not in msg:
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
            raise Exception(f"복사 확인 모달 예상과 다름: {msg!r}")
        self.click_attached(self.SEL_CONFIRM_BTN)
        self.page.wait_for_timeout(500)
        # 성공 메시지 모달이 따로 뜨면 닫기
        if self.is_confirm_modal_visible():
            self.click_attached(self.SEL_CONFIRM_BTN)
        self.wait_for_modal_closed()
        self.wait_for(self.SEL_ADD_BTN)
        return f"{name}_copy"

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

    SEL_SUB_ADD = "div#addSecureDrive.in button:has-text('추가')"

    def sub_add_message(self) -> str:
        """서브모달 '추가' 클릭 → 경고 메시지 반환 + dismiss (서브 필수/경로형식 검증용).
        정상이면 항목 커밋 후 서브 자동 닫힘 → '' 반환."""
        with overlay_off(self.page):
            self.page.locator(self.SEL_SUB_ADD).first.click(force=True)
        self.page.wait_for_timeout(500)
        msg = ""
        if self.is_confirm_modal_visible():
            try:
                msg = self.get_modal_message()
            except Exception:
                msg = ""
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()
        return msg

    def _click_save(self) -> None:
        """모드별 저장 버튼 클릭 — 추가='확인'(addbtn) / 수정='수정'(modifybtn) 중 visible 한 것.
        JS 직접 클릭(재렌더/overlay 무관). 수정 모달에서 숨겨진 addbtn 을 눌러 생성-충돌나던 버그 방지(실측 2026-06-29)."""
        for sel in (self.SEL_SAVE_MODIFY, self.SEL_SAVE_ADD):
            loc = self.page.locator(sel).first
            try:
                if loc.count() > 0 and loc.is_visible():
                    loc.evaluate("el => el.click()")
                    return
            except Exception:
                pass
        self.page.locator(self.SEL_SAVE_BTN).first.evaluate("el => el.click()")  # fallback

    def submit_no_dismiss(self) -> str:
        """메인 저장 클릭 → 경고 메시지 반환하되 '닫지 않고 둠'(경고 떠 있는 채 스크린샷용).
        이후 호출자가 dismiss_confirm() 로 닫아야 함."""
        self._click_save()
        self.page.wait_for_timeout(600)
        if self.is_confirm_modal_visible():
            try:
                return self.get_modal_message()
            except Exception:
                return ""
        return ""

    def dismiss_confirm(self) -> None:
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.wait_for_modal_closed()

    SEL_SUB_QUOTA = "div#addSecureDrive.in input#secureDriveQuota"
    SEL_SUB_ADD   = "div#addSecureDrive.in button:has-text('추가')"

    def add_secure_drive(self, label: str, letter: str, path: str,
                         quota_type: str = "WRITE", quota: str = "100", warn_quota=None):
        """addSecureDriveBtn → 서브모달 채우기 → '추가'.
        - 정상: 항목 커밋 + 서브 자동 닫힘 → None 반환.
        - 검증실패(예: 생성위치 중복): 경고 모달 메시지 반환 + dismiss + 서브 닫기.
        warn_quota 지정 시 '생성위치 용량부족시 경고' 체크 ON(게이팅 해제) 후 경고용량(GB 입력) 설정.
        실측 2026-06-23: 생성위치는 같은 루트(C:\\)면 폴더가 달라도
        '이미 등록된 드라이브의 생성위치와 동일합니다' 차단(정상 검증). 다른 루트(D:\\)는 추가됨.
        SYNC 선택 시 용량(MB) 필드 숨김(sc2j)."""
        self.open_sub_modal()
        self.fill(self.SEL_SUB_LABEL, label)
        self.fill(self.SEL_SUB_LETTER, letter)
        self.fill(self.SEL_SUB_PATH, path)
        rid = self.SEL_SUB_QTYPE_WRITE if quota_type == "WRITE" else self.SEL_SUB_QTYPE_SYNC
        with overlay_off(self.page):
            self.page.locator(rid).first.click(force=True)
        self.page.wait_for_timeout(150)
        if quota_type == "WRITE":
            self.fill(self.SEL_SUB_QUOTA, quota)
        if warn_quota is not None:
            self.set_checkbox(self.SEL_SUB_WARN_TOGGLE, True)   # 용량부족경고 ON → 경고용량 입력 가능
            self.fill(self.SEL_SUB_WARN_QUOTA, warn_quota)      # 경고용량(GB 단위로 입력)
        with overlay_off(self.page):
            self.page.locator(self.SEL_SUB_ADD).first.click(force=True)
        self.page.wait_for_timeout(400)
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            msg = self.page.locator(
                f"{self.SEL_CONFIRM_MODAL_OPENED} {self.SEL_MODAL_BODY_TEXT}").first.inner_text().strip()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.wait_for_timeout(200)
            self.close_sub_modal()
            return msg
        if self.page.locator(self.SEL_SUB).count() > 0:
            self.close_sub_modal()
        return None

    SEL_SUB_WARN_QUOTA = "div#addSecureDrive.in input#systemDriveWarningQuota"

    def iter_validation_messages(self, modify_name=None):
        """검증 메시지 i18n 전수 — 모든 min/max/길이/형식 검증을 하나씩 트리거하며 (라벨, 메시지)를 yield.
        ★경고 모달을 '열어둔 채' yield → 호출자가 그 시점에 캡처(빨간박스) 가능. resume 시 닫고 다음으로.
        raw i18n 키 누출 판정은 호출측(sweep). 데이터 저장 없음.
        modify_name 지정 시 수정 모달(전 필드 로드됨)에서 동일 전수 — sc4 캐리오버용.
        spot-check 아닌 카테고리 전수 — 실측 2026-06-24: 반출용량(COLUMN.NAME.TAKEOUT_DRIVE_QUOTA)·
        경고용량(systemDriveWarningQuota) raw 키 노출, 나머지 번역 정상."""
        try:
            if modify_name:
                self.open_modify_modal(modify_name)   # 수정 모달(전 필드 로드, sd 항목 이미 존재)
            else:
                self.open_add_modal()
                self.fill(f"{self.SEL_MODAL} {self.SEL_NAME}", f"{self.AUTO_NAME_PREFIX}_i18n")
            # ── 서브모달 검증 메시지 ──
            self.open_sub_modal()
            self.fill(self.SEL_SUB_LABEL, "lbl")
            self.fill(self.SEL_SUB_LETTER, "Q")
            self.fill(self.SEL_SUB_PATH, "C:\\sw")
            with overlay_off(self.page):
                self.page.locator(self.SEL_SUB_QTYPE_WRITE).first.click(force=True)
            self.page.wait_for_timeout(150)
            self.fill(self.SEL_SUB_QUOTA, "100")

            def _sub_trigger(sel, bad):
                self.fill(sel, bad)
                with overlay_off(self.page):
                    self.page.locator(self.SEL_SUB_ADD).first.click(force=True)
                self.page.wait_for_timeout(450)
                if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
                    return self.page.locator(
                        f"{self.SEL_CONFIRM_MODAL_OPENED} {self.SEL_MODAL_BODY_TEXT}").first.inner_text().strip()
                return ""

            sub_cases = [
                (self.SEL_SUB_QUOTA, "50", "100", "서브 용량(min 100)"),
                (self.SEL_SUB_WARN_QUOTA, "1234567890123", "", "경고용량(길이 12)"),
                (self.SEL_SUB_LETTER, "1", "Q", "서브 문자(형식 A-Z)"),
                (self.SEL_SUB_PATH, "qwe", "C:\\sw", "서브 경로(형식)"),
            ]
            for sel, bad, good, label in sub_cases:
                msg = _sub_trigger(sel, bad)
                yield label, msg                 # 경고 열린 채 yield(캡처)
                self.dismiss_confirm()            # resume 후 닫고 정상화
                self.fill(sel, good)
            # 메인 반출 검증 도달: add 는 sd 1건 커밋 필요 / modify 는 이미 sd 있음 → 닫기만(문자 Q 중복 회피)
            if modify_name:
                self.close_sub_modal()
            else:
                with overlay_off(self.page):
                    self.page.locator(self.SEL_SUB_ADD).first.click(force=True)
                self.page.wait_for_timeout(450)
                if self.page.locator(self.SEL_SUB).count() > 0:
                    self.close_sub_modal()
            # ── 메인 반출 검증 메시지 ──
            self.fill_takeout("C:\\to", "T", "lbl", "1024")
            main_cases = [
                (self.SEL_TAKEOUT_QUOTA, "50", "1024", "반출 용량(min 100)"),
                (self.SEL_OLD_DRIVE, "a" * 3000, "", "예외드라이브(길이 500)"),
            ]
            for sel, bad, good, label in main_cases:
                self.fill(sel, bad)
                msg = self.submit_no_dismiss()    # 경고 열어둠
                yield label, msg
                self.dismiss_confirm()
                self.fill(sel, good)
        finally:
            self._close_modal_if_open()

    def fill_takeout(self, path: str, letter: str, label: str, quota: str) -> None:
        """반출드라이브 4필수 필드 입력."""
        self.fill(self.SEL_TAKEOUT_PATH, path)
        self.fill(self.SEL_TAKEOUT_LETTER, letter)
        self.fill(self.SEL_TAKEOUT_LABEL, label)
        self.fill(self.SEL_TAKEOUT_QUOTA, quota)

    def secure_drive_rows(self) -> list[str]:
        """메인 모달의 시큐어드라이브 항목 리스트 행 텍스트."""
        m = self.page.locator(self.SEL_MODAL).first
        if m.count() == 0:
            return []
        return [r.inner_text().replace("\n", " ").strip()
                for r in m.locator("table tbody tr").all()]

    def delete_secure_drive_row(self, index: int = 0):
        """메인 모달 시큐어드라이브 리스트 index 행의 삭제(X) 클릭 → 경고 메시지 반환(없으면 None).
        실측 2026-06-29: 메인 드라이브(첫 항목 '*')는 '메인 드라이브는 삭제 할 수 없습니다' 차단,
        비-메인은 확인 없이 즉시 제거(None). JS 직접 클릭(overlay/visibility 무관)."""
        rows = self.page.locator(f"{self.SEL_MODAL} table tbody tr")
        rows.nth(index).locator("td").last.locator("button").first.evaluate("el => el.click()")
        self.page.wait_for_timeout(400)
        if self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            msg = self.page.locator(
                f"{self.SEL_CONFIRM_MODAL_OPENED} {self.SEL_MODAL_BODY_TEXT}").first.inner_text().strip()
            self.click_attached(self.SEL_CONFIRM_BTN)
            self.page.wait_for_timeout(200)
            return msg
        return None

    def create_basic_template(self, name: str, sd_letter: str = "Q", to_letter: str = "T",
                              to_path: str = "C:\\sztpl_to", two_drives: bool = False) -> str:
        """정상 생성: 이름 + 시큐어드라이브 항목(1건, two_drives=True 면 2건) + 반출드라이브 4필드 → 확인. 반환: 결과 메시지.
        2번째 드라이브는 다른 루트(D:)·다른 문자(Z, sd_letter 와 충돌 시 Y)·SYNC — 생성위치/문자 중복 회피.
        [AUTO]/[AUTO_날짜] 접두사만 허용(데이터 안전)."""
        if not self._AUTO_ANY.match(name):
            raise Exception("테스트 생성 템플릿([AUTO]/[AUTO_날짜] 접두사)만 허용")
        self.fill(f"{self.SEL_MODAL} {self.SEL_NAME}", name)
        self.add_secure_drive("sd_lbl", sd_letter, "C:\\sztpl_sd", "WRITE", "100")
        if two_drives:
            second = "Z" if sd_letter != "Z" else "Y"
            self.add_secure_drive("sd_lbl2", second, "D:\\sztpl_sd2", "SYNC")
        self.fill_takeout(to_path, to_letter, "to_lbl", "1024")
        return self.submit_and_message()

    def submit_and_message(self) -> str:
        """메인 '확인'(저장) 클릭 → 확인/경고 모달 메시지 반환 + dismiss. 성공 시 목록 복귀.
        sc2 필수검증(빈값→경고) / sc3 CRUD / sc4 수정 공용."""
        # 저장 — 모드별 버튼(추가='확인' / 수정='수정') visible 한 것 JS 직접 클릭
        self._click_save()
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
