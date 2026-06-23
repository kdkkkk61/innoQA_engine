"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조 (값 기반).

표준 sc2 = 입력 구조(default/maxlength/필수마커). 요소 '존재'는 sc1 이 함 — 여기선 '값'을 본다.
빈값 제출 경고(입력검증 동작)는 방식 B 에선 sc3(CRUD)에서 다룸.
사실은 Chrome MCP 직접조작(2026-06-23)으로 확인 — maxlength 는 실제 속성을 동적 보고(있으면 클라 가드/없으면 서버검증).

sc2a — 메인 default (토글 OFF / 텍스트 빈값)
sc2b — 필수 marker (span.star) — 이름+반출4+시큐어드라이브설정
sc2c — 메인 maxlength (이름/반출4 — 실제 속성 보고)
sc2d — 서브모달 default (용량방식 WRITE default / 텍스트 빈값 / 필수 marker)
sc2e — 서브모달 maxlength (라벨/문자/위치/용량)
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario2Input(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조(값)."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def _maxlen(self, page, sel):
        loc = page.page.locator(sel).first
        return loc.get_attribute("maxlength") if loc.count() else "(미존재)"

    def test_scenario2a_main_defaults(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2a: 메인 default ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        # 토글 default OFF
        for label, sel in {"ECM드라이브 연동": page.SEL_ECM, "반출 폴더 숨김": page.SEL_TAKEOUT_HIDE}.items():
            loc = page.page.locator(sel).first
            checked = loc.is_checked() if loc.count() else None
            self._add("pass" if checked is False else "warn" if checked is None else "fail",
                      f"sc2a — '{label}' default OFF",
                      f"입력: 최초 열림 / 결과: checked={checked} (기대 False)", sc=2,
                      repro="1. 템플릿 추가\n2. 체크박스 default OFF 확인")
        # 텍스트 빈값
        texts = {"템플릿 이름": f"{page.SEL_MODAL} {page.SEL_NAME}", "예외 드라이브": page.SEL_OLD_DRIVE,
                 "반출 생성위치": page.SEL_TAKEOUT_PATH, "반출 문자": page.SEL_TAKEOUT_LETTER,
                 "반출 라벨": page.SEL_TAKEOUT_LABEL, "반출 용량": page.SEL_TAKEOUT_QUOTA}
        empties = {lbl: page.page.locator(sel).first.input_value() for lbl, sel in texts.items()
                   if page.page.locator(sel).count()}
        bad = {k: v for k, v in empties.items() if v != ""}
        self._add("pass" if not bad else "fail",
                  "sc2a — 메인 텍스트필드 default 빈값",
                  f"입력: 최초 열림 / 결과: " + ("전부 빈값" if not bad else f"비어있지 않음 {bad}"), sc=2,
                  repro="1. 템플릿 추가\n2. 이름·예외·반출4 빈값 확인")
        page._close_modal_if_open()

    def test_scenario2b_required_markers(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2b: 필수 marker(별표) ━━━")
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
                  "sc2b — 필수 marker(span.star) 존재",
                  f"입력: ADD 모달 / 결과: 별표 {cnt}개 (이름+반출4+시큐어드라이브설정 등): {rows}", sc=2,
                  repro="1. ADD 모달\n2. 필수(*) 마커 개수/위치 확인")
        page._close_modal_if_open()

    def test_scenario2c_main_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2c: 메인 maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        fields = {"템플릿 이름": f"{page.SEL_MODAL} {page.SEL_NAME}", "반출 생성위치": page.SEL_TAKEOUT_PATH,
                  "반출 문자": page.SEL_TAKEOUT_LETTER, "반출 라벨": page.SEL_TAKEOUT_LABEL,
                  "반출 용량": page.SEL_TAKEOUT_QUOTA}
        for label, sel in fields.items():
            ml = self._maxlen(page, sel)
            # 실제 속성 동적 보고 — 있으면 클라 가드(pass) / null 이면 서버검증 의존(warn)
            has_guard = ml not in (None, "(미존재)")
            self._add("pass" if has_guard else "warn",
                      f"sc2c — '{label}' maxlength",
                      f"입력: {label} / 결과: maxlength={ml!r} "
                      + ("(클라 길이 가드 있음)" if has_guard else "[null — 서버검증 의존 가능]"), sc=2,
                      repro="1. ADD 모달\n2. 필드 maxlength 속성 확인")
        page._close_modal_if_open()

    def test_scenario2d_sub_defaults(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2d: 서브모달 default ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        # 용량방식 default — WRITE(직접입력) 선택 (실측)
        w = page.page.locator(page.SEL_SUB_QTYPE_WRITE).first
        s = page.page.locator(page.SEL_SUB_QTYPE_SYNC).first
        w_chk = w.is_checked() if w.count() else None
        s_chk = s.is_checked() if s.count() else None
        self._add("pass" if (w_chk is True and s_chk is False) else "warn",
                  "sc2d — 용량방식 default = 직접입력(WRITE)",
                  f"입력: 서브모달 최초 / 결과: WRITE={w_chk}, SYNC={s_chk} (기대 WRITE True)", sc=2,
                  repro="1. 시큐어드라이브 추가(서브)\n2. 용량방식 default 확인")
        # 텍스트 빈값
        sub_texts = {"라벨": page.SEL_SUB_LABEL, "문자": page.SEL_SUB_LETTER, "생성위치": page.SEL_SUB_PATH,
                     "용량": f"{page.SEL_SUB} #secureDriveQuota", "설명": f"{page.SEL_SUB} #description"}
        empties = {lbl: page.page.locator(sel).first.input_value() for lbl, sel in sub_texts.items()
                   if page.page.locator(sel).count()}
        bad = {k: v for k, v in empties.items() if v != ""}
        self._add("pass" if not bad else "fail",
                  "sc2d — 서브모달 텍스트 default 빈값",
                  f"입력: 서브 최초 / 결과: " + ("전부 빈값" if not bad else f"비어있지 않음 {bad}"), sc=2,
                  repro="1. 서브모달\n2. 라벨·문자·위치·용량·설명 빈값 확인")
        # 서브 필수 marker
        scnt = page.page.locator(f"{page.SEL_SUB} span.star").count()
        self._add("pass" if scnt >= 1 else "warn",
                  "sc2d — 서브모달 필수 marker(별표)",
                  f"입력: 서브모달 / 결과: 별표 {scnt}개 (라벨/문자/위치/용량방식)", sc=2,
                  repro="1. 서브모달\n2. 필수(*) 마커 확인")
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2e_sub_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2e: 서브모달 maxlength ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        fields = {"드라이브 라벨": page.SEL_SUB_LABEL, "드라이브 문자": page.SEL_SUB_LETTER,
                  "생성위치": page.SEL_SUB_PATH, "용량": f"{page.SEL_SUB} #secureDriveQuota"}
        for label, sel in fields.items():
            ml = self._maxlen(page, sel)
            has_guard = ml not in (None, "(미존재)")
            self._add("pass" if has_guard else "warn",
                      f"sc2e — 서브 '{label}' maxlength",
                      f"입력: {label} / 결과: maxlength={ml!r} "
                      + ("(클라 길이 가드 있음)" if has_guard else "[null — 서버검증 의존 가능]"), sc=2,
                      repro="1. 서브모달\n2. 필드 maxlength 확인")
        page.close_sub_modal()
        page._close_modal_if_open()
