"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조 (충실 검증).

sc2 = 입력 구조의 주관 시나리오 — 필드별 default 값 / maxlength / 필수 marker 를 꼼꼼히 본다.
(sc0 은 변경 감지(추가/삭제/숨김)가 본질, sc1 은 요소 '존재'. sc2 는 '값/제약'.)
메인 모달 + 서브모달(addSecureDrive) 둘 다 — 서브모달은 sc0 가 스캔조차 안 하므로 특히 sc2 가 책임.
사실은 Chrome MCP 직접조작(2026-06-23) 확인. maxlength 는 실제 속성을 동적 보고(있으면 클라 가드).

sc2a — 메인 default 값 (토글 OFF / 텍스트 빈값, 필드별)
sc2b — 메인 maxlength (이름/반출4, 필드별)
sc2c — 메인 필수 marker (이름+반출4+시큐어드라이브설정)
sc2d — 서브모달 default 값 (용량방식 WRITE / 텍스트 빈값, 필드별)
sc2e — 서브모달 maxlength (라벨/문자/위치/용량, 필드별)
sc2f — 서브모달 필수 marker
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario2Input(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def _check_default_off(self, page, label, sel):
        loc = page.page.locator(sel).first
        checked = loc.is_checked() if loc.count() else None
        self._add("pass" if checked is False else "warn" if checked is None else "fail",
                  f"sc2 — '{label}' default OFF",
                  f"입력: 최초 열림 / 결과: checked={checked} (기대 False)", sc=2,
                  repro=f"1. 모달 열기\n2. '{label}' default OFF 확인")

    def _check_text_empty(self, page, label, sel):
        loc = page.page.locator(sel).first
        if loc.count() == 0:
            self._add("skip", f"sc2 — '{label}' default 빈값", "대상 미존재", sc=2)
            return
        val = loc.input_value()
        self._add("pass" if val == "" else "fail",
                  f"sc2 — '{label}' default 빈값",
                  f"입력: 최초 열림 / 결과: value={val!r} (기대 빈값)", sc=2,
                  repro=f"1. 모달 열기\n2. '{label}' 빈값 확인")

    def _check_maxlength(self, page, label, sel):
        loc = page.page.locator(sel).first
        if loc.count() == 0:
            self._add("skip", f"sc2 — '{label}' maxlength", "대상 미존재", sc=2)
            return
        ml = loc.get_attribute("maxlength")
        has_guard = ml is not None
        self._add("pass" if has_guard else "warn",
                  f"sc2 — '{label}' maxlength",
                  f"입력: {label} / 결과: maxlength={ml!r} "
                  + ("(클라 길이 가드 있음)" if has_guard else "[null — 서버검증 의존 가능, 긴 입력 시 서버오류 위험]"),
                  sc=2, repro=f"1. 모달 열기\n2. '{label}' maxlength 속성 확인")

    # ══ 메인 모달 ══════════════════════════════════════════════════
    def test_scenario2a_main_defaults(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2a: 메인 default 값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        self._check_default_off(page, "ECM드라이브 연동", page.SEL_ECM)
        self._check_default_off(page, "반출 폴더 숨김", page.SEL_TAKEOUT_HIDE)
        self._check_text_empty(page, "템플릿 이름", f"{page.SEL_MODAL} {page.SEL_NAME}")
        self._check_text_empty(page, "예외 드라이브", page.SEL_OLD_DRIVE)
        self._check_text_empty(page, "반출 생성위치", page.SEL_TAKEOUT_PATH)
        self._check_text_empty(page, "반출 드라이브 문자", page.SEL_TAKEOUT_LETTER)
        self._check_text_empty(page, "반출 드라이브 라벨", page.SEL_TAKEOUT_LABEL)
        self._check_text_empty(page, "반출 드라이브 용량", page.SEL_TAKEOUT_QUOTA)
        page._close_modal_if_open()

    def test_scenario2b_main_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2b: 메인 maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        self._check_maxlength(page, "템플릿 이름", f"{page.SEL_MODAL} {page.SEL_NAME}")
        self._check_maxlength(page, "예외 드라이브", page.SEL_OLD_DRIVE)
        self._check_maxlength(page, "반출 생성위치", page.SEL_TAKEOUT_PATH)
        self._check_maxlength(page, "반출 드라이브 문자", page.SEL_TAKEOUT_LETTER)
        self._check_maxlength(page, "반출 드라이브 라벨", page.SEL_TAKEOUT_LABEL)
        self._check_maxlength(page, "반출 드라이브 용량", page.SEL_TAKEOUT_QUOTA)
        page._close_modal_if_open()

    def test_scenario2c_main_required_markers(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2c: 메인 필수 marker ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        stars = page.page.locator(f"{page.SEL_MODAL} span.star")
        cnt = stars.count()
        rows = []
        for i in range(min(cnt, 10)):
            try:
                rows.append(" ".join(stars.nth(i).locator("xpath=..").inner_text().split())[:24])
            except Exception:
                pass
        self._add("pass" if cnt >= 1 else "warn",
                  "sc2c — 메인 필수 marker(span.star)",
                  f"입력: ADD 모달 / 결과: 별표 {cnt}개 (이름+반출4+시큐어드라이브설정 등): {rows}", sc=2,
                  repro="1. ADD 모달\n2. 필수(*) 마커 개수/위치 확인")
        page._close_modal_if_open()

    # ══ 서브모달 (sc0 미스캔 — sc2 가 책임) ════════════════════════
    def test_scenario2d_sub_defaults(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2d: 서브모달 default 값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        w = page.page.locator(page.SEL_SUB_QTYPE_WRITE).first
        s = page.page.locator(page.SEL_SUB_QTYPE_SYNC).first
        w_chk = w.is_checked() if w.count() else None
        s_chk = s.is_checked() if s.count() else None
        self._add("pass" if (w_chk is True and s_chk is False) else "warn",
                  "sc2d — 용량방식 default = 직접입력(WRITE)",
                  f"입력: 서브모달 최초 / 결과: WRITE={w_chk}, SYNC={s_chk} (기대 WRITE True)", sc=2,
                  repro="1. 시큐어드라이브 추가(서브)\n2. 용량방식 default 확인")
        self._check_text_empty(page, "서브 드라이브 라벨", page.SEL_SUB_LABEL)
        self._check_text_empty(page, "서브 드라이브 문자", page.SEL_SUB_LETTER)
        self._check_text_empty(page, "서브 생성위치", page.SEL_SUB_PATH)
        self._check_text_empty(page, "서브 용량", f"{page.SEL_SUB} #secureDriveQuota")
        self._check_text_empty(page, "서브 설명", f"{page.SEL_SUB} #description")
        self._check_default_off(page, "서브 생성위치 숨김", f"{page.SEL_SUB} #isSecureDrivePathHide")
        self._check_default_off(page, "서브 용량부족 경고", f"{page.SEL_SUB} #isSystemDriveWarningQuota")
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2e_sub_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2e: 서브모달 maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        self._check_maxlength(page, "서브 드라이브 라벨", page.SEL_SUB_LABEL)
        self._check_maxlength(page, "서브 드라이브 문자", page.SEL_SUB_LETTER)
        self._check_maxlength(page, "서브 생성위치", page.SEL_SUB_PATH)
        self._check_maxlength(page, "서브 용량", f"{page.SEL_SUB} #secureDriveQuota")
        self._check_maxlength(page, "서브 경고 용량", f"{page.SEL_SUB} #systemDriveWarningQuota")
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2f_sub_required_markers(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2f: 서브모달 필수 marker ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        scnt = page.page.locator(f"{page.SEL_SUB} span.star").count()
        self._add("pass" if scnt >= 1 else "warn",
                  "sc2f — 서브모달 필수 marker(span.star)",
                  f"입력: 서브모달 / 결과: 별표 {scnt}개 (라벨/문자/위치/용량방식)", sc=2,
                  repro="1. 서브모달\n2. 필수(*) 마커 확인")
        page.close_sub_modal()
        page._close_modal_if_open()
