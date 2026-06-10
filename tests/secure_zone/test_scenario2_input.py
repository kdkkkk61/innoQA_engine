"""시큐어존 접근제어 정책 — 시나리오 2: 입력 구조 (ADD 모달).

sc2a — 필드 인벤토리 (이름 + 마스터토글 + 드라이브3 + 시스템도구3 + USB radio3 + 종료해제)
sc2b — default 값 (마스터 OFF / 체크박스 OFF / USB '거부' 선택 / 이름 빈값) — Chrome MCP 실측 2026-06-09
sc2c — maxlength (이름=50 / 드라이브3=null 서버검증)
"""
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase


class TestSecureZoneAccessControlScenario2Input(SecureZoneACBase):
    """접근제어 정책 — 시나리오 2: 입력 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAccessControlPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario2a_field_inventory(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 2a: 필드 인벤토리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        fields = [
            ("정책 이름",                "input#szAccessControlPolicyName"),
            ("접근제어 사용 (마스터)",    "input#isAccessControl"),
            ("지정 드라이브 숨기기",      "input#pickHideDrive"),
            ("지정 드라이브 접근금지",    "input#pickDenyDrive"),
            ("지정 드라이브 예외처리",    "input#pickExceptDrive"),
            ("명령프롬프트(CMD) 사용",    "input#isCmd"),
            ("Regedit 사용",             "input#isRegedit"),
            ("MMC, Gpedit 사용",         "input#isMmc"),
            ("휴대용 디바이스 — 거부",    "input#usbControlDeny"),
            ("휴대용 디바이스 — 읽기",    "input#usbControlRead"),
            ("휴대용 디바이스 — 읽기/쓰기", "input#usbControlReadWrite"),
            ("종료 시 접근제어 해제",     "input#isShutdownAccessControl"),
        ]
        for label, sel in fields:
            present = page.page.locator(sel).count() > 0
            self._add("pass" if present else "fail",
                      f"sc2a — '{label}' 존재",
                      f"selector='{sel}' / present={present}", sc=2)
        page._close_modal_if_open()

    def test_scenario2b_default_values(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 2b: default 값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        # checkbox/radio default (Chrome MCP 실측 2026-06-09)
        # 마스터·시스템도구·종료해제 = OFF / USB 거부 = 선택 / USB 읽기·읽기쓰기 = 미선택
        cr_defaults = [
            ("접근제어 사용 (마스터)",  "input#isAccessControl",        False),
            ("명령프롬프트(CMD) 사용",  "input#isCmd",                  False),
            ("Regedit 사용",           "input#isRegedit",              False),
            ("MMC, Gpedit 사용",       "input#isMmc",                  False),
            ("종료 시 접근제어 해제",   "input#isShutdownAccessControl", False),
            ("USB 권한 — 거부",         "input#usbControlDeny",         True),
            ("USB 권한 — 읽기",         "input#usbControlRead",         False),
            ("USB 권한 — 읽기/쓰기",    "input#usbControlReadWrite",    False),
        ]
        for label, sel, exp in cr_defaults:
            loc = page.page.locator(sel).first
            actual = loc.is_checked() if loc.count() else None
            self._add("pass" if actual == exp else "fail",
                      f"sc2b — '{label}' default {'선택' if exp else '미선택'}",
                      f"checked={actual} / 기대={exp}", sc=2)

        # 정책 이름 default 빈값
        nameval = page.page.locator(page.SEL_NAME).first.input_value()
        self._add("pass" if nameval == "" else "fail",
                  "sc2b — 정책 이름 default 빈값",
                  f"value={nameval!r}", sc=2)
        page._close_modal_if_open()

    def test_scenario2c_maxlength(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 2c: maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        # 정책 이름 maxlength=50 (DOM 클라 가드)
        ml_name = page.page.locator(page.SEL_NAME).first.get_attribute("maxlength")
        self._add("pass" if ml_name == "50" else "fail",
                  "sc2c — 정책 이름 maxlength=50",
                  f"maxlength={ml_name!r}", sc=2)

        # 드라이브 3종 maxlength=null (DOM 제한 없음 → 서버 측 검증)
        for label, sel in [
            ("지정 드라이브 숨기기",   "input#pickHideDrive"),
            ("지정 드라이브 접근금지", "input#pickDenyDrive"),
            ("지정 드라이브 예외처리", "input#pickExceptDrive"),
        ]:
            ml = page.page.locator(sel).first.get_attribute("maxlength")
            self._add("pass" if ml is None else "fail",
                      f"sc2c — '{label}' maxlength=null (서버 측 검증)",
                      f"maxlength={ml!r}", sc=2)
        page._close_modal_if_open()

    def test_scenario2d_default_reset(self, logged_in_page, settings):
        """sc2d — 채움→닫기→재오픈 시 default 복원 (nPouch sc2c 대응)."""
        print("\n━━ [접근제어 정책] 시나리오 2d: default 값 reset ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        # 1차: 열고 임의로 채움 (이름 + 마스터 ON + CMD ON)
        page.open_add_modal()
        page.page.locator(page.SEL_NAME).first.fill("[AUTO]_probe_reset")
        m = page.page.locator("input#isAccessControl").first
        if not m.is_checked():
            m.evaluate("el => el.click()"); page.page.wait_for_timeout(300)
        cmd = page.page.locator("input#isCmd").first
        if not cmd.is_checked():
            cmd.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
        page._close_modal_if_open()   # 저장 안 함 (취소)

        # 2차: 재오픈 → default 복원 확인
        page.open_add_modal()
        checks = [
            ("정책 이름 빈값", lambda: page.page.locator(page.SEL_NAME).first.input_value() == ""),
            ("마스터 OFF", lambda: page.page.locator("input#isAccessControl").first.is_checked() is False),
            ("CMD OFF", lambda: page.page.locator("input#isCmd").first.is_checked() is False),
            ("USB 거부", lambda: page.page.locator("input#usbControlDeny").first.is_checked() is True),
        ]
        for label, fn in checks:
            ok = fn()
            self._add("pass" if ok else "fail",
                      f"sc2d — 재오픈 default 복원 '{label}'",
                      f"복원={ok}", sc=2)
        page._close_modal_if_open()

    def test_scenario2e_required_star_marker(self, logged_in_page, settings):
        """sc2e — 필수 ★ 마커 (span.star) — 정책 이름 1개 (nPouch sc2b 대응)."""
        print("\n━━ [접근제어 정책] 시나리오 2e: 필수 ★ 마커 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        stars = page.page.locator(f"{page.SEL_MODAL} span.star").count()
        self._add("pass" if stars == 1 else "warn",
                  "sc2e — 필수 ★ 마커 (span.star) 정확 1개 (정책 이름)",
                  f"span.star 개수={stars} (기대=1)", sc=2)
        page._close_modal_if_open()
