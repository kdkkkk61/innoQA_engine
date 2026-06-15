"""시큐어존 정책 — 시나리오 2: 입력 구조 (ADD 모달, read-only).

sc2a — 필드 인벤토리 (25 baseline + 2탭 + 템플릿선택 버튼 2)
sc2b — default 값 (타입=일반 / 모든 토글 OFF / 이름 빈값) — Chrome MCP 실측 2026-06-11
sc2c — maxlength (정책이름=50 / watchFileStorePath=400 / 나머지 text=null)
sc2d — default reset (채움→닫기→재오픈 복원)
sc2e — 필수 ★ 마커 (span.star == 4: 타입/정책이름/드라이브설정/제어스위트설정)

저장·picker 조작 없음 (구조만 확인). 기본반출정책 singleton 미접촉.
"""
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase


class TestSecureZonePolicyScenario2Input(SecureZonePolicyBase):
    """시큐어존 정책 — 시나리오 2: 입력 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAgentPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario2a_field_inventory(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 2a: 필드 인벤토리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        fields = [
            ("타입 — 일반",          "input#szAgentPolicyTypeDefault"),
            ("타입 — 반출",          "input#szAgentPolicyTypeTakeout"),
            ("기본반출정책",          "input#isSzAgentPolicyTypeTakeoutDefault"),
            ("정책 이름",            "input#szAgentPolicyName"),
            ("프로세스 통제기능 사용", "input#isAllowDenyProcessUse"),
            ("프로그램 종료 강제종료", "input#isAllowProcessForceStop"),
            ("예외처리 프로세스",      "input#isExceptProcess"),
            ("실행차단 프로세스",      "input#isBlockExecuteProcess"),
            ("특수폴더 사용",         "input#isManageFolder"),
            ("폴더 동기화 사용",      "input#isSyncFolder"),
            ("파일 감시기능",         "input#isWatchFile"),
            ("감시파일 보관소",       "input#watchFileStorePath"),
            ("감시할 확장자",         "input#isWatchFileExtention"),
            ("확장자 입력",          "input#watchFileExtention"),
            ("헤더 체크",            "input#isWatchFileHeader"),
            ("감시 예외 폴더",        "input#isWatchFolder"),
            ("프린트 설정 사용",      "input#isPrintUse"),
            ("프린트 허용 브랜드",     "textarea#allowPrintModel"),
            ("프린트 제외 포트",      "textarea#exceptPrintPort"),
            ("에이전트 종료 메뉴",     "input#isShowAgentShutdownMenu"),
            ("긴급 허용 코드 메뉴",    "input#isShowEmergencyCodeMenu"),
            ("오프라인 사용",         "input#isOfflineUse"),
            ("차단 대기시간",         "input#secureDriveBlockTime"),
            ("반출 드라이브 차단",     "input#isTakeoutDriveBlock"),
            ("커스텀 옵션값",         "input#customOptionText"),
        ]
        for label, sel in fields:
            present = page.page.locator(sel).count() > 0
            self._add("pass" if present else "fail",
                      f"sc2a — '{label}' 존재",
                      f"selector='{sel}' / present={present}", sc=2)

        # 2탭 + 템플릿 선택 버튼 2개
        tab_txt = " ".join(t.inner_text() for t in
                           page.page.locator(f"{page.SEL_MODAL} li a").all())
        self._add("pass" if ("기본정책" in tab_txt and "템플릿설정" in tab_txt) else "fail",
                  "sc2a — 모달 2탭(기본정책/템플릿설정)",
                  f"탭 텍스트: 기본정책={'기본정책' in tab_txt}, 템플릿설정={'템플릿설정' in tab_txt}", sc=2)
        tmpl_btns = page.page.locator(f"{page.SEL_MODAL} a.addTemplate").count()
        self._add("pass" if tmpl_btns >= 2 else "fail",
                  "sc2a — 드라이브/제어스위트 템플릿 선택 버튼 2개",
                  f"a.addTemplate count={tmpl_btns} (기대>=2)", sc=2)
        page._close_modal_if_open()

    def test_scenario2b_default_values(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 2b: default 값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        # 타입 = 일반 선택 (Chrome MCP 실측 2026-06-11)
        td = page.page.locator("input#szAgentPolicyTypeDefault").first
        self._add("pass" if td.is_checked() else "fail",
                  "sc2b — 타입 default '일반' 선택", f"checked={td.is_checked()}", sc=2)

        # 모든 토글 OFF
        off_checks = [
            "isSzAgentPolicyTypeTakeoutDefault", "isAllowDenyProcessUse",
            "isBlockExecuteProcess", "isManageFolder", "isSyncFolder",
            "isWatchFile", "isPrintUse", "isOfflineUse",
            "isShowAgentShutdownMenu", "isShowEmergencyCodeMenu",
        ]
        for cid in off_checks:
            loc = page.page.locator(f"input#{cid}").first
            actual = loc.is_checked() if loc.count() else None
            self._add("pass" if actual is False else "fail",
                      f"sc2b — '{cid}' default OFF", f"checked={actual}", sc=2)

        # 정책 이름 빈값
        nameval = page.page.locator(page.SEL_NAME).first.input_value()
        self._add("pass" if nameval == "" else "fail",
                  "sc2b — 정책 이름 default 빈값", f"value={nameval!r}", sc=2)

        # text/숫자 필드 default 빈값 (nPouch sc2c 'text/숫자 default' 대응)
        # Chrome MCP 실측 2026-06-11: secureDriveBlockTime 도 숫자 0 아닌 빈값("")
        for label, sel in [
            ("차단 대기시간", "input#secureDriveBlockTime"),
            ("확장자 입력",   "input#watchFileExtention"),
            ("커스텀 옵션값", "input#customOptionText"),
        ]:
            loc = page.page.locator(sel).first
            val = loc.input_value() if loc.count() else None
            self._add("pass" if val == "" else "fail",
                      f"sc2b — '{label}' default 빈값", f"value={val!r}", sc=2)
        page._close_modal_if_open()

    def test_scenario2c_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 2c: maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        ml_name = page.page.locator(page.SEL_NAME).first.get_attribute("maxlength")
        self._add("pass" if ml_name == "50" else "fail",
                  "sc2c — 정책 이름 maxlength=50", f"maxlength={ml_name!r}", sc=2)

        # watchFileStorePath maxlength=400 (단 붙여넣기/JS는 우회 — sc3 데이터손실 검증 별도)
        ml_store = page.page.locator("input#watchFileStorePath").first.get_attribute("maxlength")
        self._add("pass" if ml_store == "400" else "fail",
                  "sc2c — 감시파일 보관소 maxlength=400", f"maxlength={ml_store!r}", sc=2)

        # 나머지 text 필드 maxlength=null (서버측 검증)
        for label, sel in [
            ("확장자 입력",   "input#watchFileExtention"),
            ("커스텀 옵션값", "input#customOptionText"),
        ]:
            ml = page.page.locator(sel).first.get_attribute("maxlength")
            self._add("pass" if ml is None else "warn",
                      f"sc2c — '{label}' maxlength=null (클라 가드 없음)",
                      f"maxlength={ml!r}", sc=2)
        page._close_modal_if_open()

    def test_scenario2d_default_reset(self, logged_in_page, settings):
        """sc2d — 채움→닫기→재오픈 시 default 복원 (nPouch sc2c 대응)."""
        print("\n━━ [시큐어존 정책] 시나리오 2d: default 값 reset ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        # 1차: 열고 임의로 채움 (이름 + 실행차단 토글 ON)
        page.open_add_modal()
        page.page.locator(page.SEL_NAME).first.fill("[AUTO]_probe_reset")
        be = page.page.locator("input#isBlockExecuteProcess").first
        if not be.is_checked():
            be.evaluate("el => el.click()"); page.page.wait_for_timeout(150)
        page._close_modal_if_open()   # 저장 안 함 (취소)

        # 2차: 재오픈 → default 복원
        page.open_add_modal()
        checks = [
            ("정책 이름 빈값", lambda: page.page.locator(page.SEL_NAME).first.input_value() == ""),
            ("타입 일반", lambda: page.page.locator("input#szAgentPolicyTypeDefault").first.is_checked() is True),
            ("실행차단 OFF", lambda: page.page.locator("input#isBlockExecuteProcess").first.is_checked() is False),
        ]
        for label, fn in checks:
            ok = fn()
            self._add("pass" if ok else "fail",
                      f"sc2d — 재오픈 default 복원 '{label}'", f"복원={ok}", sc=2)
        page._close_modal_if_open()

    def test_scenario2e_required_star_marker(self, logged_in_page, settings):
        """sc2e — 필수 ★ 마커 (span.star) == 4 (nPouch sc2b 대응)."""
        print("\n━━ [시큐어존 정책] 시나리오 2e: 필수 ★ 마커 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()

        stars = page.page.locator(f"{page.SEL_MODAL} span.star").count()
        self._add("pass" if stars == 4 else "warn",
                  "sc2e — 필수 ★ 마커 4개 (타입/정책이름/드라이브설정/제어스위트설정)",
                  f"span.star 개수={stars} (기대=4)", sc=2)
        page._close_modal_if_open()
