"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조 (docs/scenario_2_input.md 준수).

개념별 분리(묶지 않음): 존재 / 초기값 / maxlength / 필수marker / 필수검증1차 / 글자수.
- maxlength=null 은 '서버 측 검증' 정상 상태 → PASS (버그 아님, nPouch sc2 동일). 클라 가드 있으면 값 보고.
- 초기값 빈값은 필수/선택 무관 정상 → PASS (선택 필드 빈값을 문제처럼 적지 않음).
중복은 sc3(데이터 필요), 위반입력 저장값(2차)은 sc4-3.
메인+서브모달(addSecureDrive) 둘 다. 사실은 Chrome MCP 직접조작(2026-06-23) 확인.

sc2a — 모달 기본(제목/저장/닫기)
sc2b — 필드 존재 (메인+서브, 전체)
sc2c — 초기값 (토글 OFF / 텍스트 빈값 / 용량방식 WRITE)
sc2d — maxlength (전체, 값 보고 — null=서버검증/N=클라가드, 둘 다 PASS)
sc2e — 필수 marker(별표) 메인/서브
sc2f — 필수 검증 1차: 빈값 제출 → 경고 떴는가
sc2g — 글자수 제한: 이름 maxlength 초과 → 잘림
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario2Input(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 2: 입력 구조."""

    # (라벨, 셀렉터(id), 종류, 필수여부)
    _MAIN_FIELDS = [
        ("템플릿 이름",       "templateName",          "text",     True),
        ("ECM드라이브 연동",   "isRegistEcmDrive",      "checkbox", False),
        ("예외 드라이브",      "registOldDrive",        "text",     False),
        ("반출 생성위치",      "takeoutDrivePath",      "text",     True),
        ("반출 폴더 숨김",     "isTakeoutDrivePathHide","checkbox", False),
        ("반출 드라이브 문자", "takeoutDriveLetter",    "text",     True),
        ("반출 드라이브 라벨", "takeoutDriveLabel",     "text",     True),
        ("반출 드라이브 용량", "takeoutDriveQuota",     "text",     True),
    ]
    _SUB_FIELDS = [
        ("드라이브 라벨", "secureDriveLabel",          "text",     True),
        ("드라이브 문자", "secureDriveLetter",         "text",     True),
        ("생성위치",      "secureDrivePath",           "text",     True),
        ("생성위치 숨김", "isSecureDrivePathHide",     "checkbox", False),
        ("용량부족 경고", "isSystemDriveWarningQuota", "checkbox", False),
        ("경고 용량",     "systemDriveWarningQuota",   "text",     False),
        ("용량",          "secureDriveQuota",          "text",     False),
        ("설명",          "description",               "text",     False),
    ]

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    # ── 개념별 검증 헬퍼 (한 필드 = 한 카드, 묶지 않음) ──────────────
    def _exists(self, page, scope, label, fid):
        present = page.page.locator(f"{scope} #{fid}").count() > 0
        self._add("pass" if present else "skip",
                  f"sc2 — '{label}' 필드 존재",
                  f"결과: present={present}" + ("" if present else " (sc0 변경사항 참조)"), sc=2)

    def _default(self, page, scope, label, fid, kind, required):
        loc = page.page.locator(f"{scope} #{fid}").first
        if loc.count() == 0:
            self._add("skip", f"sc2 — '{label}' 초기값", "대상 미존재", sc=2); return
        tag = "필수" if required else "선택"
        if kind == "checkbox":
            self._add("pass" if loc.is_checked() is False else "warn",
                      f"sc2 — '{label}' 초기값 OFF",
                      f"결과: checked={loc.is_checked()} (기대 OFF)", sc=2)
        else:
            val = loc.input_value()
            self._add("pass" if val == "" else "warn",
                      f"sc2 — '{label}'({tag}) 초기값 빈값",
                      f"결과: value={val!r}" + ("" if val == "" else " (기대 빈값)"), sc=2)

    def _maxlength(self, page, scope, label, fid):
        loc = page.page.locator(f"{scope} #{fid}").first
        if loc.count() == 0:
            self._add("skip", f"sc2 — '{label}' maxlength", "대상 미존재", sc=2); return
        ml = loc.get_attribute("maxlength")
        # null=서버 측 검증(정상), 값=클라 가드 — 둘 다 PASS(구조 문서화).
        self._add("pass", f"sc2 — '{label}' maxlength",
                  f"결과: maxlength={ml!r} " + ("(클라 길이 가드)" if ml is not None else "(null — 서버 측 검증)"),
                  sc=2)

    # ══ 카드 ══════════════════════════════════════════════════════
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
        ok = bool(title) and save_seen
        self._add("pass" if ok else "warn",
                  "sc2a — 모달 기본 (제목 / 저장'확인' / 닫기)",
                  f"입력: 추가 모달 / 결과: 제목={title!r}, 저장버튼={save_seen}", sc=2,
                  repro="1. 템플릿 추가\n2. 제목·저장·닫기 버튼 확인")
        page._close_modal_if_open()

    def test_scenario2b_field_existence(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2b: 필드 존재(메인+서브) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        for label, fid, _, _ in self._MAIN_FIELDS:
            self._exists(page, page.SEL_MODAL, label, fid)
        page.open_sub_modal()
        for label, fid, _, _ in self._SUB_FIELDS:
            self._exists(page, page.SEL_SUB, "서브-" + label, fid)
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2c_initial_values(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2c: 초기값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        for label, fid, kind, req in self._MAIN_FIELDS:
            self._default(page, page.SEL_MODAL, label, fid, kind, req)
        page.open_sub_modal()
        # 용량방식 default = WRITE
        w = page.page.locator(page.SEL_SUB_QTYPE_WRITE).first
        s = page.page.locator(page.SEL_SUB_QTYPE_SYNC).first
        self._add("pass" if (w.count() and w.is_checked() and s.count() and not s.is_checked()) else "warn",
                  "sc2c — 용량방식 초기값 = 직접입력(WRITE)",
                  f"결과: WRITE={w.is_checked() if w.count() else None}, SYNC={s.is_checked() if s.count() else None}", sc=2)
        for label, fid, kind, req in self._SUB_FIELDS:
            self._default(page, page.SEL_SUB, "서브-" + label, fid, kind, req)
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2d_maxlength(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2d: maxlength(값 보고) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        for label, fid, kind, _ in self._MAIN_FIELDS:
            if kind == "text":
                self._maxlength(page, page.SEL_MODAL, label, fid)
        page.open_sub_modal()
        for label, fid, kind, _ in self._SUB_FIELDS:
            if kind == "text":
                self._maxlength(page, page.SEL_SUB, "서브-" + label, fid)
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2e_required_markers(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2e: 필수 marker(별표) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        main_cnt = page.page.locator(f"{page.SEL_MODAL} span.star").count()
        self._add("pass" if main_cnt >= 1 else "warn",
                  "sc2e — 메인 필수 marker(별표)",
                  f"결과: 메인 별표 {main_cnt}개 (이름+반출4+시큐어드라이브설정)", sc=2,
                  repro="1. ADD 모달\n2. 필수(*) 마커 확인")
        page.open_sub_modal()
        sub_cnt = page.page.locator(f"{page.SEL_SUB} span.star").count()
        self._add("pass" if sub_cnt >= 1 else "warn",
                  "sc2e — 서브모달 필수 marker(별표)",
                  f"결과: 서브 별표 {sub_cnt}개 (라벨/문자/위치/용량방식)", sc=2,
                  repro="1. 서브모달\n2. 필수(*) 마커 확인")
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2f_required_submit_sequence(self, logged_in_page, settings):
        """md: 필수 검증 1차 — 저장 누르며 '무엇을 입력하라'는 경고가 필드 순서대로 뜨는지.

        직접조작 확인 순서(2026-06-23): 빈값→이름 / 이름→반출경로 / +경로→반출문자
        / +문자→반출라벨 / +라벨→반출용량(최소100MB) / +용량→시큐어드라이브 등록.
        각 단계 = 해당 필수 필드 미입력 시 그 필드를 짚는 경고가 뜨는가(추정 금지, 메시지 == 비교).
        + 메시지에 raw i18n 키(COLUMN.NAME...) 노출 시 별도 버그 카드.
        """
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2f: 필수 입력 순서(저장 시 경고 순서) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        # (직전에 채울 필드 id·값, 기대 경고 부분문자열, 단계 설명)
        steps = [
            (None,                            "템플릿 이름을 입력해 주세요.",            "전부 빈값"),
            (("templateName", "[AUTO]_sztpl_seq"), "반출드라이브 생성위치를 입력해 주세요.", "이름만"),
            (("takeoutDrivePath", "C:\\seq_to"),   "반출드라이브 문자를 입력해 주세요.",      "+반출경로"),
            (("takeoutDriveLetter", "T"),          "반출드라이브 라벨을 입력해 주세요.",      "+반출문자"),
            (("takeoutDriveLabel", "seqlbl"),      "용량",                                  "+반출라벨(용량 경고)"),
            (("takeoutDriveQuota", "1024"),        "시큐어드라이브를 등록해 주세요.",         "+반출용량"),
        ]
        for fill, expect_sub, desc in steps:
            if fill:
                page.fill(f"{page.SEL_MODAL} input#{fill[0]}", fill[1])
            msg = page.submit_and_message()
            hit = expect_sub in msg
            self._add("pass" if hit else "fail",
                      f"sc2f — 필수 순서: {desc} → 경고",
                      f"입력: {desc} 후 저장 / 결과: 경고={msg!r} (기대 포함 {expect_sub!r})", sc=2,
                      repro=f"1. {desc} 상태로 저장\n2. 해당 필수 필드 짚는 경고 확인")
        page._close_modal_if_open()

    def test_scenario2g_maxlength_clamp(self, logged_in_page, settings):
        """md: 글자수 제한 — 경계값+1 입력 → 실제 잘림 (maxlength 있는 필드)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2g: 글자수 제한(이름) ━━━")
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
            self._add("pass", "sc2g — 이름 글자수 제한",
                      "결과: maxlength 없음 — 서버 측 검증 의존(클램핑 검증 해당 없음)", sc=2)
            page._close_modal_if_open(); return
        actual = page.type_clamped(sel, "a" * (limit + 5))
        clamped = actual <= limit
        self._add("pass" if clamped else "fail",
                  "sc2g — 이름 maxlength 초과 입력 시 잘림",
                  f"입력: {limit+5}자 타이핑(maxlength={limit}) / 결과: 실제 {actual}자 "
                  + ("(잘림 — 클라 가드 동작)" if clamped else "[미적용 — 초과 입력됨]"), sc=2,
                  highlight=loc, repro=f"1. 이름에 {limit+5}자\n2. {limit}자로 잘리는지 확인")
        page._close_modal_if_open()

    def test_scenario2h_sub_field_validation(self, logged_in_page, settings):
        """서브모달(시큐어드라이브 항목) 입력 검증 전수 — 필수 + 형식(문자 A-Z / 경로 / 용량 min).

        직접조작(2026-06-23): 문자 빈값→"문자 입력"(라벨* 있어도 문자부터) / 문자 '1'→"A-Z 하나만"
        / 경로 'qwe'→"정상적인 경로" / 용량 '50'(<100)→"시큐어드라이브...최소 100MB"(번역 정상).
        """
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2h: 서브모달 입력 검증(필수+형식) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        page.fill(page.SEL_SUB_LABEL, "lbl")  # 라벨 채워둠

        # (필드 id, 넣을 값, 기대 경고 부분문자열, 단계 설명) — 매 추가 시 1개만 위반
        cases = [
            ("secureDriveLetter", "",    "시큐어드라이브 문자를 입력해 주세요.", "문자 빈값(필수)"),
            ("secureDriveLetter", "1",   "A-Z",                                "문자 '1'(형식: A-Z 하나)"),
            ("secureDriveLetter", "Q",   None,                                  None),  # 문자 정상화
            ("secureDrivePath",   "qwe", "정상적인 경로를 입력해 주세요.",       "생성위치 'qwe'(경로 형식)"),
            ("secureDrivePath",   "C:\\sdtest", None, None),                            # 경로 정상화
            ("secureDriveQuota",  "50",  "100MB",                              "용량 '50'(min 100)"),
        ]
        for fid, val, expect_sub, desc in cases:
            page.fill(f"{page.SEL_SUB} input#{fid}", val)
            if desc is None:
                continue  # 값 정상화만(검증 안 함)
            msg = page.sub_add_message()
            hit = expect_sub in msg
            self._add("pass" if hit else "fail",
                      f"sc2h — 서브 {desc} → 경고",
                      f"입력: {desc} 후 추가 / 결과: 경고={msg!r} (기대 포함 {expect_sub!r})", sc=2,
                      repro=f"1. 서브모달 {desc}\n2. 추가 → 경고 확인")
        page.close_sub_modal()
        page._close_modal_if_open()

    def test_scenario2i_takeout_quota_i18n(self, logged_in_page, settings):
        """반출 용량 경고 메시지 i18n 키 미번역 — 경고 떠 있는 채 캡처(어디가 문제인지 보이게).

        직접조작(2026-06-23): 반출 용량 < 100 저장 시 경고가 'COLUMN.NAME.TAKEOUT_DRIVE_QUOTA의
        입력 가능 용량은 최소 100MB...' — raw i18n 키 노출(서브모달 용량 경고는 '시큐어드라이브...'로 번역됨).
        ※ 반출 경로/문자 형식 검증 누락(서브엔 있음)은 '전부 유효+저장' 으로 확인해야 확실 → sc3(CRUD).
        """
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 2i: 반출 용량 경고 i18n 키 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "[AUTO]_sztpl_i18n")
        page.fill(page.SEL_TAKEOUT_PATH, "C:\\to")
        page.fill(page.SEL_TAKEOUT_LETTER, "T")
        page.fill(page.SEL_TAKEOUT_LABEL, "lbl")
        page.fill(page.SEL_TAKEOUT_QUOTA, "50")          # min 100 미만 → 용량 경고
        msg = page.submit_no_dismiss()                    # 경고 닫지 않고 둠(캡처용)
        leaked = "COLUMN." in msg or "NAME." in msg
        self._add("warn" if leaked else "pass",
                  "sc2i — 반출 용량 경고 i18n 키 번역",
                  f"입력: 반출용량='50'(min 미만) 저장 / 결과 경고: {msg!r} "
                  + ("[버그: raw i18n 키(COLUMN.NAME.TAKEOUT_DRIVE_QUOTA) 노출 — 서브는 '시큐어드라이브'로 번역됨]"
                     if leaked else "(정상 번역)"),
                  sc=2,
                  highlight=page.page.locator(f"{page.SEL_CONFIRM_MODAL_OPENED} {page.SEL_MODAL_BODY_TEXT}"),
                  repro="1. 반출용량 '50'\n2. 저장\n3. 경고 팝업에 COLUMN.NAME raw 키 노출되는지")
        page.dismiss_confirm()
        page._close_modal_if_open()
