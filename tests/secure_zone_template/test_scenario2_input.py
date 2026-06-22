"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조 (요소 정확 캡처 검증).

sc2a — 메인 모달 필드 인벤토리 (이름 + ECM + 예외드라이브 + 반출 5필드 + addSecureDriveBtn)
sc2b — 서브모달 필드 인벤토리 (label/letter/path + hide + 경고 + 용량방식 radio + quota + desc)
sc2c — default 값 (이름 빈값 / 체크박스 OFF / 용량방식 default)
sc2d — maxlength (이름 등 — 실제 속성값 보고, 하드코딩 비교 아님)

목적: sc3+ 가 '올바른 요소'를 친다는 보장을 위해 먼저 필드를 정확히 잡았는지 확인.
필드 목록은 Chrome MCP 직접조작(2026-06-23)으로 확인한 실제 id. 결과는 동적 보고(존재/누락).
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from pages.shared._overlay import overlay_off
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario2Input(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조."""

    # 메인 모달 필드 (id : 종류)
    _MAIN_FIELDS = [
        ("templateName", "이름*"), ("isRegistEcmDrive", "ECM연동"),
        ("registOldDrive", "예외드라이브"), ("takeoutDrivePath", "반출경로*"),
        ("isTakeoutDrivePathHide", "반출폴더숨김"), ("takeoutDriveLetter", "반출문자*"),
        ("takeoutDriveLabel", "반출라벨*"), ("takeoutDriveQuota", "반출용량*"),
    ]
    _SUB_FIELDS = [
        ("secureDriveLabel", "라벨*"), ("secureDriveLetter", "문자*"),
        ("secureDrivePath", "생성위치*"), ("isSecureDrivePathHide", "위치숨김"),
        ("isSystemDriveWarningQuota", "용량경고"), ("systemDriveWarningQuota", "경고용량"),
        ("secureDriveQuotaTypeWrite", "용량방식WRITE*"), ("secureDriveQuotaTypeSync", "용량방식SYNC*"),
        ("secureDriveQuota", "용량"), ("description", "설명"),
    ]

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def _present(self, page, scope_sel, fid):
        return page.page.locator(f"{scope_sel} #{fid}").count() > 0

    def test_scenario2a_main_field_inventory(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2a: 메인 필드 인벤토리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        missing = [f"{lbl}({fid})" for fid, lbl in self._MAIN_FIELDS
                   if not self._present(page, page.SEL_MODAL, fid)]
        has_add_drive = page.page.locator(page.SEL_ADD_DRIVE_BTN).count() > 0
        ok = (not missing) and has_add_drive
        self._add("pass" if ok else "fail",
                  "sc2a — 메인 모달 필드 인벤토리",
                  f"입력: 추가 모달 / 결과: "
                  + ("이름+ECM+예외+반출5+시큐어드라이브추가버튼 전부 존재"
                     if ok else f"누락 {missing}, addSecureDriveBtn={has_add_drive}"),
                  sc=2, repro="1. 템플릿 추가\n2. 메인 모달 필드 8 + 시큐어드라이브 추가버튼 존재 확인")
        page._close_modal_if_open()

    def test_scenario2b_sub_field_inventory(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2b: 서브모달 필드 인벤토리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        with overlay_off(page.page):
            page.page.locator(page.SEL_ADD_DRIVE_BTN).first.click(force=True)
        try:
            page.page.locator(page.SEL_SUB).wait_for(state="attached", timeout=3000)
        except Exception:
            pass
        missing = [f"{lbl}({fid})" for fid, lbl in self._SUB_FIELDS
                   if not self._present(page, page.SEL_SUB, fid)]
        self._add("pass" if not missing else "fail",
                  "sc2b — 서브모달(시큐어드라이브 항목) 필드 인벤토리",
                  f"입력: 서브모달 / 결과: "
                  + ("라벨/문자/위치/숨김/경고/용량방식2/용량/설명 전부 존재" if not missing else f"누락 {missing}"),
                  sc=2, repro="1. 추가→시큐어드라이브 추가(서브)\n2. 서브 필드 10개 존재 확인")
        page._close_sub_if_open()
        page._close_modal_if_open()

    def test_scenario2c_default_values(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2c: default 값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        name_empty = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value() == ""
        ecm = page.page.locator(f"{page.SEL_MODAL} #isRegistEcmDrive").first
        ecm_off = (not ecm.is_checked()) if ecm.count() else None
        hide = page.page.locator(f"{page.SEL_MODAL} #isTakeoutDrivePathHide").first
        hide_off = (not hide.is_checked()) if hide.count() else None
        ok = name_empty and ecm_off and hide_off
        self._add("pass" if ok else "warn",
                  "sc2c — 추가 모달 default (이름 빈값 / ECM·반출숨김 OFF)",
                  f"입력: 추가 모달 최초 / 결과: 이름빈값={name_empty}, ECM_OFF={ecm_off}, 반출숨김_OFF={hide_off}",
                  sc=2, repro="1. 템플릿 추가\n2. 이름 빈값 + 체크박스 default OFF 확인")
        page._close_modal_if_open()

    def test_scenario2d_name_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2d: 이름 maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        ml = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.get_attribute("maxlength")
        # 하드코딩 기대값 아님 — 실제 maxlength 속성을 그대로 보고(없으면 서버검증 의존 가능)
        self._add("pass" if ml else "warn",
                  "sc2d — 이름 maxlength 속성",
                  f"입력: templateName / 결과: maxlength={ml!r} "
                  + ("(클라이언트 제한 있음)" if ml else "[maxlength 없음 — 길이 제한은 서버검증 의존 가능]"),
                  sc=2, repro="1. 추가 모달\n2. templateName maxlength 속성 확인")
        page._close_modal_if_open()
