"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조 (docs/scenario_2_input.md 준수).

md "반드시 커버": 모달 기본(제목/버튼) / 필드 존재(전체) / 초기값 / maxlength(전체)
/ 필수 검증 1차(빈값 제출→경고 떴는가, 추정 금지) / 글자수 제한(경계값+1→결과).
중복 검증은 데이터 생성 필요 → sc3(CRUD). 위반입력 후 저장값(2차)은 sc4-3.
메인 + 서브모달(addSecureDrive) 둘 다. 사실은 Chrome MCP 직접조작(2026-06-23) 확인.

sc2a — 모달 기본(제목 / 저장'확인' / 닫기 버튼)
sc2b — 메인 필드 전수: 존재 + 초기값 + maxlength (필드별)
sc2c — 메인 필수 marker(별표)
sc2d — 필수 검증 1차: 빈값 제출 → 경고 떴는가 (추정 금지)
sc2e — 글자수 제한: 이름 maxlength 초과 입력 → 잘림 확인
sc2f — 서브모달 필드 전수: 존재 + 초기값 + maxlength + 용량방식 default
sc2g — 서브모달 필수 marker(별표)
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario2Input(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조."""

    # 메인 모달 필드: (라벨, 셀렉터, 종류 text/checkbox)
    _MAIN_FIELDS = [
        ("템플릿 이름",        "input#templateName",        "text"),
        ("ECM드라이브 연동",    "input#isRegistEcmDrive",    "checkbox"),
        ("예외 드라이브",       "textarea#registOldDrive",   "text"),
        ("반출 생성위치",       "input#takeoutDrivePath",    "text"),
        ("반출 폴더 숨김",      "input#isTakeoutDrivePathHide", "checkbox"),
        ("반출 드라이브 문자",  "input#takeoutDriveLetter",  "text"),
        ("반출 드라이브 라벨",  "input#takeoutDriveLabel",   "text"),
        ("반출 드라이브 용량",  "input#takeoutDriveQuota",   "text"),
    ]
    _SUB_FIELDS = [
        ("드라이브 라벨",   "input#secureDriveLabel",          "text"),
        ("드라이브 문자",   "input#secureDriveLetter",         "text"),
        ("생성위치",        "input#secureDrivePath",           "text"),
        ("생성위치 숨김",   "input#isSecureDrivePathHide",     "checkbox"),
        ("용량부족 경고",   "input#isSystemDriveWarningQuota", "checkbox"),
        ("경고 용량",       "input#systemDriveWarningQuota",   "text"),
        ("용량",            "input#secureDriveQuota",          "text"),
        ("설명",            "textarea#description",            "text"),
    ]

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def _field_card(self, page, scope, label, sel, kind):
        """필드 1개: 존재 + 초기값 + maxlength 를 묶어 검증(md 패턴)."""
        loc = page.page.locator(f"{scope} {sel}").first
        if loc.count() == 0:
            self._add("skip", f"sc2 — '{label}' 필드",
                      f"결과: 미존재 (sc0 변경사항 참조)", sc=2)
            return
        if kind == "checkbox":
            checked = loc.is_checked()
            self._add("pass" if checked is False else "warn",
                      f"sc2 — '{label}' 존재 + 초기값 OFF",
                      f"입력: 최초 열림 / 결과: 존재=True, checked={checked} (기대 False)", sc=2)
        else:
            val = loc.input_value()
            ml = loc.get_attribute("maxlength")
            ml_ok = ml is not None
            self._add("pass" if (val == "" and ml_ok) else "warn",
                      f"sc2 — '{label}' 존재 + 초기값 빈값 + maxlength",
                      f"입력: 최초 열림 / 결과: 존재=True, 초기값={val!r}, maxlength={ml!r}"
                      + ("" if ml_ok else " [maxlength null — 서버검증 의존]"), sc=2)

    # ══ 메인 모달 ══════════════════════════════════════════════════
    def test_scenario2a_modal_basics(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2a: 모달 기본 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        m = page.page.locator(page.SEL_MODAL).first
        title = ""
        try:
            title = m.locator(".modal-title, h3, h4").first.inner_text().strip()
        except Exception:
            pass
        save_seen = page.page.locator(page.SEL_SAVE_BTN).count() > 0
        close_seen = page.field_present(page.SEL_CLOSE_BTN.split(",")[0])
        ok = bool(title) and save_seen and close_seen
        self._add("pass" if ok else "warn",
                  "sc2a — 모달 기본 (제목 / 저장'확인' / 닫기)",
                  f"입력: 추가 모달 / 결과: 제목={title!r}, 저장버튼={save_seen}, 닫기버튼={close_seen}", sc=2,
                  repro="1. 템플릿 추가\n2. 제목·저장(확인)·닫기 버튼 확인")
        page._close_modal_if_open()

    def test_scenario2b_main_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2b: 메인 필드 전수(존재+초기값+maxlength) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        for label, sel, kind in self._MAIN_FIELDS:
            self._field_card(page, page.SEL_MODAL, label, sel, kind)
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
                  f"입력: ADD 모달 / 결과: 별표 {cnt}개: {rows}", sc=2,
                  repro="1. ADD 모달\n2. 필수(*) 마커 개수/위치 확인")
        page._close_modal_if_open()

    def test_scenario2d_required_empty_warning(self, logged_in_page, settings):
        """md: 필수 검증 1차 — 빈값 제출 → 경고 떴는가 (추정 금지, '경고 떴는가'만)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2d: 필수 검증 1차(빈값→경고) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        msg = page.submit_and_message()
        warned = ("저장" not in msg) and bool(msg)
        self._add("pass" if warned else "fail",
                  "sc2d — 필수 빈값 제출 → 경고",
                  f"입력: 전 필드 빈값 + 확인 / 결과: 경고={msg!r} "
                  + ("(경고 떴음)" if warned else "[경고 없이 통과 — 클라 검증 누락]"), sc=2,
                  highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 추가 모달\n2. 빈값으로 확인\n3. 필수 경고 떴는지 확인(추정 금지)")
        page._close_modal_if_open()

    def test_scenario2e_maxlength_clamp(self, logged_in_page, settings):
        """md: 글자수 제한 — 경계값+1 입력 → 실제 잘림 확인 (maxlength 있는 필드)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2e: 글자수 제한(이름 maxlength 초과) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        sel = f"{page.SEL_MODAL} {page.SEL_NAME}"
        loc = page.page.locator(sel).first
        ml = loc.get_attribute("maxlength")
        try:
            limit = int(ml)
        except Exception:
            limit = None
        if limit is None:
            self._add("warn", "sc2e — 이름 글자수 제한",
                      "결과: maxlength 속성 없음 — 클라 클램핑 검증 불가(서버검증 의존)", sc=2)
            page._close_modal_if_open(); return
        actual = page.type_clamped(sel, "a" * (limit + 5))
        clamped = actual <= limit
        self._add("pass" if clamped else "fail",
                  "sc2e — 이름 maxlength 초과 입력 시 잘림",
                  f"입력: {limit+5}자 타이핑(maxlength={limit}) / 결과: 실제 {actual}자 "
                  + ("(잘림 — 클라 가드 동작)" if clamped else "[미적용 — maxlength 초과 입력됨]"), sc=2,
                  highlight=loc, repro=f"1. 이름에 {limit+5}자 입력\n2. {limit}자로 잘리는지 확인")
        page._close_modal_if_open()

    # ══ 서브모달 (sc0 미스캔 — sc2 가 책임) ════════════════════════
    def test_scenario2f_sub_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2f: 서브모달 필드 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        # 용량방식 default = WRITE
        w = page.page.locator(page.SEL_SUB_QTYPE_WRITE).first
        s = page.page.locator(page.SEL_SUB_QTYPE_SYNC).first
        w_chk = w.is_checked() if w.count() else None
        s_chk = s.is_checked() if s.count() else None
        self._add("pass" if (w_chk is True and s_chk is False) else "warn",
                  "sc2f — 용량방식 default = 직접입력(WRITE)",
                  f"입력: 서브 최초 / 결과: WRITE={w_chk}, SYNC={s_chk} (기대 WRITE True)", sc=2,
                  repro="1. 시큐어드라이브 추가(서브)\n2. 용량방식 default 확인")
        for label, sel, kind in self._SUB_FIELDS:
            self._field_card(page, page.SEL_SUB, label, sel, kind)
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2g_sub_required_markers(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2g: 서브모달 필수 marker ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        scnt = page.page.locator(f"{page.SEL_SUB} span.star").count()
        self._add("pass" if scnt >= 1 else "warn",
                  "sc2g — 서브모달 필수 marker(span.star)",
                  f"입력: 서브모달 / 결과: 별표 {scnt}개 (라벨/문자/위치/용량방식)", sc=2,
                  repro="1. 서브모달\n2. 필수(*) 마커 확인")
        page.close_sub_modal()
        page._close_modal_if_open()
