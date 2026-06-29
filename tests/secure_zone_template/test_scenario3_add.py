"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 3: 동작 검증 (생성 시나리오 기반, 요소별).

원칙(사용자 지정): sc3 = 생성하며 발견되는 것. **삭제·제거·수정은 sc3 에 없음**(삭제=sc1/sc5, 제거/수정=sc4/sc5).
생성한 [AUTO] 는 정리 안 함 — sc5 가 정리(라이프사이클). 직접조작 수집(2026-06-23) 위에 작성.

카드(연속 a~m, 직접조작 수집 2026-06-23 기반):
  3a 정상생성 / 3b 저장값확인 / 3c 글자수 clamp(실입력, sc2서 이동) / 3d 서브 입력검증(필수+형식, sc2서 이동) /
  3e 반출경로 형식누락(버그) / 3f 반출문자 A-Z 검증(정상) / 3g 시큐어드라이브 N건 추가(다른 루트) /
  3h 항목 중복 규칙(생성위치·문자 차단 / 라벨 허용) / 3i 이름 중복 차단 / 3j 이름 특수문자(허용) /
  3k 오버플로(예외드라이브 3000자→서버측 500자 차단) / 3l 복사(원본+'_copy') / 3m 검색 필터 /
  3n 복사 이름 충돌(원본_copy 존재 시 재복사→중복 이름 silent 생성=버그) /
  3o 검증 메시지 i18n 전수(sweep): 모든 검증 메시지 트리거·수집 → raw 키 누출 자동판정
     (반출용량·경고용량 노출 / 나머지 정상 — 구 sc2h·단일 경고용량 카드를 카테고리 전수로 통합).
  3p 체크박스/라디오 토글 상호작용 전수(ECM/반출숨김/생성위치숨김/용량부족경고 토글, 용량방식 라디오 상호배타).
  ※ 시큐어드라이브 항목 제거(저장 전 모달 편집)는 삭제 소유가 sc1/sc5 → 생성 시나리오에서 제외.
  ※ 항목 중복 차단(문자/생성위치 차단, 라벨 허용)은 3h 에서 검증.

역할 분리(2026-06-23): sc2=구조·속성+필수1차 / sc3=실제 값 입력 동작(clamp·형식검증·CRUD·복사·검색).
캡처 원칙: 리스트 캡처는 '어디가 버그인지' 불명 → 형식버그(3e)는 수정 모달 재오픈해
저장된 잘못된 값 필드를 highlight 캡처(직관적 증거).
"""
import re

from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase

# raw i18n 키 의심 = 한글 메시지 안의 Latin 식별자 4자+ (MB/GB/A-Z 등 2~3자 제외)
_I18N_RAW_KEY = re.compile(r"[A-Za-z][A-Za-z._]{3,}")


class TestSecureZoneTemplateScenario3Add(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 3: 생성 동작."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ 3a: 정상 생성 → 목록 등록 ══════════════════════════════════
    def test_scenario3a_create_normal(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3a: 정상 생성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        name = f"{page.AUTO_NAME_PREFIX}_a"
        page.open_add_modal()
        msg = page.create_basic_template(name, sd_letter="Q", to_letter="T")
        page.navigate_to()
        exists = name in page.get_template_names()
        ok = ("저장" in msg) and exists
        self._add("pass" if ok else "fail",
                  "sc3a — 정상 생성(이름+시큐어드라이브1+반출4) → 목록 등록",
                  f"입력: '{name}' 전 요소 / 결과: {msg!r}, 목록존재={exists}", sc=3,
                  repro="1. 템플릿 추가\n2. 이름·시큐어드라이브 항목·반출드라이브 입력\n3. 확인\n4. 목록 등록 확인")

    # ══ 3b: 저장값 확인 (수정 재오픈 → 전 요소 대조, 읽기) ═══════════
    def test_scenario3b_saved_values(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3b: 저장값 확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_b"
        if name not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(name, sd_letter="R", to_letter="U", to_path="C:\\sztpl_b")
            page.navigate_to()
        if name not in page.get_template_names():
            self._add("skip", "sc3b — 저장값 확인", f"입력: - / 결과: {name} 미생성", sc=3); return
        page.open_modify_modal(name)
        nm = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        to_path = page.page.locator(page.SEL_TAKEOUT_PATH).first.input_value()
        to_letter = page.page.locator(page.SEL_TAKEOUT_LETTER).first.input_value()
        rows = page.secure_drive_rows()
        loaded = (nm == name) and ("C:\\sztpl_b" in to_path) and (to_letter == "U") and (len(rows) >= 1)
        self._add("pass" if loaded else "fail",
                  "sc3b — 생성 후 수정 재오픈 시 저장값 로드(전 요소 대조)",
                  f"입력: '{name}' 생성 후 수정 재오픈 / 결과: 이름='{nm}', 반출경로='{to_path}', "
                  f"반출문자='{to_letter}', 시큐어드라이브 {len(rows)}행={rows}", sc=3,
                  repro="1. 생성한 템플릿 수정 재오픈\n2. 이름·반출·시큐어드라이브 항목이 저장값으로 뜨는지")
        page.close_modal()

    # ══ 3c: 글자수 제한(maxlength) 실입력 클램핑 — sc2에서 이동(동작 검증) ══
    def _clamp_card(self, page, label, sel):
        """maxlength 있는 필드: 경계값+5 타이핑 → 실제 잘림 확인."""
        loc = page.page.locator(sel).first
        if loc.count() == 0:
            self._add("skip", f"sc3c — '{label}' 글자수 제한", "대상 미존재", sc=3); return
        ml = loc.get_attribute("maxlength")
        try:
            limit = int(ml)
        except Exception:
            self._add("pass", f"sc3c — '{label}' 글자수 제한",
                      "결과: maxlength 없음 — 서버 측 검증 의존(클램핑 해당 없음)", sc=3); return
        actual = page.type_clamped(sel, "a" * (limit + 5))
        clamped = actual <= limit
        self._add("pass" if clamped else "fail",
                  f"sc3c — '{label}' maxlength({limit}) 초과 입력 시 잘림",
                  f"입력: {limit+5}자 타이핑 / 결과: 실제 {actual}자 "
                  + ("(잘림 — 클라 가드 동작)" if clamped else "[미적용 — 초과 입력됨]"), sc=3,
                  highlight=loc, repro=f"1. {label}에 {limit+5}자\n2. {limit}자로 잘리는지 확인")

    def test_scenario3c_maxlength_clamp(self, logged_in_page, settings):
        """글자수 제한 실입력 — maxlength 있는 모든 필드(메인 이름·반출4 + 서브 4) 경계값+5 입력 → 잘림.
        (sc2d=maxlength 속성 보고 / sc3c=실제 입력 동작 — 역할 분리 2026-06-23. 데이터 생성/저장 없음)"""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3c: 글자수 제한 실입력(전 필드) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        for label, sel in [
            ("템플릿 이름", f"{page.SEL_MODAL} {page.SEL_NAME}"),
            ("반출 생성위치", page.SEL_TAKEOUT_PATH),
            ("반출 문자", page.SEL_TAKEOUT_LETTER),
            ("반출 라벨", page.SEL_TAKEOUT_LABEL),
            ("반출 용량", page.SEL_TAKEOUT_QUOTA),
        ]:
            self._clamp_card(page, label, sel)
        page.open_sub_modal()
        for label, sel in [
            ("서브 드라이브 라벨", page.SEL_SUB_LABEL),
            ("서브 드라이브 문자", page.SEL_SUB_LETTER),
            ("서브 생성위치", page.SEL_SUB_PATH),
            ("서브 용량", f"{page.SEL_SUB} #secureDriveQuota"),
        ]:
            self._clamp_card(page, label, sel)
        page.close_sub_modal()
        page._close_modal_if_open()

    # ══ 3d: 서브모달 입력 검증(필수+형식) — sc2에서 이동(형식검증=동작) ══
    def test_scenario3d_sub_field_validation(self, logged_in_page, settings):
        """서브모달(시큐어드라이브 항목) 입력 검증 전수 — 필수 + 형식(문자 A-Z / 경로 / 용량 min).

        직접조작(2026-06-23): 검증 순서 문자→라벨→경로→용량 (시각상 라벨이 위지만 문자부터 = 경미한 UX 불편).
        전부 빈값→"문자 입력"(라벨 비어도 문자 먼저) / 문자 채운 뒤 라벨 빈값→"라벨 입력"(라벨 검증 동작함) /
        문자 '1'→"A-Z 하나만" / 경로 'qwe'→"정상적인 경로" / 용량 '50'(<100)→"시큐어드라이브...최소 100MB".
        ※ 메인 반출 경로/문자 중 '경로'만 형식검증 누락(버그) → 3e. 서브는 라벨·문자·경로·용량 모두 검증(불일치). 데이터 저장 없음.
        """
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3d: 서브모달 입력 검증(필수+형식) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        # (필드 id, 넣을 값, 기대 경고 부분문자열, 단계 설명) — 매 추가 시 1개만 위반
        # 검증 순서(실측 2026-06-23): 문자 → 라벨 → 경로 → 용량.
        #   ※ 시각상 라벨이 위인데 '문자'부터 검증 → 전부 빈값이면 라벨 비어도 "문자 입력"이 먼저(경미한 UX 불편).
        cases = [
            ("secureDriveLetter", "",    "시큐어드라이브 문자를 입력해 주세요.", "문자 빈값(1순위 — 라벨 비어도 문자부터)"),
            ("secureDriveLetter", "Q",   None,                                  None),  # 문자 정상화 → 라벨 검증 노출
            ("secureDriveLabel",  "",    "시큐어드라이브 라벨을 입력해 주세요.", "라벨 빈값(문자 다음 — 검증 동작 확인)"),
            ("secureDriveLabel",  "lbl", None,                                  None),  # 라벨 정상화
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
                      f"sc3d — 서브 {desc} → 경고",
                      f"입력: {desc} 후 추가 / 결과: 경고={msg!r} (기대 포함 {expect_sub!r})", sc=3,
                      repro=f"1. 서브모달 {desc}\n2. 추가 → 경고 확인")
        page.close_sub_modal()
        page._close_modal_if_open()

    # ══ 3e: 반출 생성위치 경로 형식 검증 (전부 유효+저장 → qwe 저장됨=버그) ══
    def test_scenario3e_takeout_path_format(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3e: 반출 경로 형식(생성 시) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_e"
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", name)
        page.add_secure_drive("sd", "S", "C:\\sd_e", "WRITE", "100")
        page.fill_takeout("qwe", "V", "lbl", "1024")    # 반출경로 'qwe'(잘못된 경로)
        msg = page.submit_and_message()
        page.navigate_to()
        saved = name in page.get_template_names()
        # 서브 생성위치는 'qwe' 차단(정상적인 경로). 반출 경로는 형식 검증 없으면 'qwe' 로 저장됨 = 버그.
        if saved:
            # 버그 증거: 저장된 잘못된 경로를 수정 모달 재오픈해 해당 필드 highlight 캡처(직관적)
            page.open_modify_modal(name)
            to_path = page.page.locator(page.SEL_TAKEOUT_PATH).first.input_value()
            self._add("warn", "sc3e — 반출 생성위치 경로 형식 검증",
                      f"입력: 전 요소 유효 + 반출경로='qwe'(잘못된 경로) 저장 / 결과: {msg!r}, "
                      f"수정 재오픈 시 반출경로='{to_path}' [형식 검증 없음 — 잘못된 경로 그대로 저장. "
                      f"서브 생성위치는 '정상적인 경로' 차단(불일치)]",
                      sc=3, highlight=page.page.locator(page.SEL_TAKEOUT_PATH),
                      repro="1. 반출경로 'qwe'+나머지 유효\n2. 저장→저장됨\n3. 수정 재오픈→반출경로 'qwe' 그대로(형식검증 없음=버그)")
            page.close_modal()
        else:
            self._add("pass", "sc3e — 반출 생성위치 경로 형식 검증",
                      f"입력: 반출경로='qwe' / 결과: {msg!r} (형식 검증으로 차단)", sc=3,
                      repro="1. 반출경로 'qwe'\n2. 저장→차단")

    # ══ 3f: 반출 드라이브 문자 형식 검증 (1 저장됨=버그) ════════════
    def test_scenario3f_takeout_letter_format(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3f: 반출 문자 형식(생성 시) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_f"
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", name)
        page.add_secure_drive("sd", "W", "C:\\sd_f", "WRITE", "100")
        page.fill_takeout("C:\\to_f", "1", "lbl", "1024")   # 반출문자 '1'(숫자)
        msg = page.submit_and_message()
        page.navigate_to()
        saved = name in page.get_template_names()
        if saved:
            page.open_modify_modal(name)
            to_letter = page.page.locator(page.SEL_TAKEOUT_LETTER).first.input_value()
            self._add("warn", "sc3f — 반출 드라이브 문자 형식 검증(A-Z)",
                      f"입력: 전 요소 유효 + 반출문자='1'(숫자) 저장 / 결과: {msg!r}, "
                      f"수정 재오픈 시 반출문자='{to_letter}' [형식 검증 없음 — '1' 그대로 저장. "
                      f"서브 문자는 'A-Z 하나' 차단(불일치)]",
                      sc=3, highlight=page.page.locator(page.SEL_TAKEOUT_LETTER),
                      repro="1. 반출문자 '1'+나머지 유효\n2. 저장→저장됨\n3. 수정 재오픈→반출문자 '1' 그대로(A-Z 검증 없음=버그)")
            page.close_modal()
        else:
            self._add("pass", "sc3f — 반출 드라이브 문자 형식 검증(A-Z)",
                      f"입력: 반출문자='1' / 결과: {msg!r} (형식 검증으로 차단)", sc=3,
                      repro="1. 반출문자 '1'\n2. 저장→차단")

    # ══ 3g: 시큐어드라이브 항목 N건 추가(WRITE C: + SYNC D:, 다른 루트) → 리스트 ══
    def test_scenario3g_secure_drive_multi_add(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3g: 시큐어드라이브 N건 추가 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", f"{page.AUTO_NAME_PREFIX}_h")
        # 생성위치 중복검사(같은 루트 차단) 회피 위해 서로 다른 루트(C:/D:) 사용 — 실측 2026-06-23
        page.add_secure_drive("lbl_w", "Y", "C:\\sd_h_w", "WRITE", "100")
        rows1 = page.secure_drive_rows()
        page.add_secure_drive("lbl_s", "Z", "D:\\sd_h_s", "SYNC")
        rows2 = page.secure_drive_rows()
        ok = (len(rows1) >= 1) and (len(rows2) >= 2)
        self._add("pass" if ok else "fail",
                  "sc3g — 시큐어드라이브 WRITE(C:)+SYNC(D:) 2건 추가 → 메인 리스트 반영",
                  f"입력: WRITE C:\\ 1건 + SYNC D:\\ 1건(다른 루트) / 결과: 1건후 {len(rows1)}행, "
                  f"2건후 {len(rows2)}행={rows2}", sc=3,
                  repro="1. 시큐어드라이브 추가→WRITE(C:)\n2. 다시 추가→SYNC(D:, 다른 루트)\n3. 메인 리스트 2건 반영 확인")
        # 첫 추가 항목이 '메인 드라이브(*)' 로 지정되는지 (생성쪽 — sc4n '메인 삭제불가'의 짝, 실측 2026-06-29)
        main_ok = (len(rows2) >= 2) and ("*" in rows2[0]) and ("*" not in rows2[1])
        self._add("pass" if main_ok else "fail",
                  "sc3g — 첫 추가 항목이 메인 드라이브(*) 지정",
                  f"결과: 1행='{rows2[0] if rows2 else ''}'(* 포함={'*' in (rows2[0] if rows2 else '')}), "
                  f"2행='{rows2[1] if len(rows2)>1 else ''}'(* 포함={'*' in (rows2[1] if len(rows2)>1 else '')}) "
                  "[첫 항목=메인, 메인은 삭제불가(sc4n)]", sc=3,
                  repro="1. 시큐어드라이브 2건 추가\n2. 첫 항목에만 '*'(메인) 표시되는지")
        page._close_modal_if_open()

    # ══ 3h: 시큐어드라이브 항목 중복 규칙 (생성위치·문자 차단 / 라벨 허용) ══
    def test_scenario3h_drive_duplicate_rules(self, logged_in_page, settings):
        """시큐어드라이브 항목 중복 규칙(실측 2026-06-23):
        생성위치(같은 루트)·문자 → 차단 / 라벨 → 허용(검사 없음 — 라벨은 키 아님)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3h: 항목 중복 규칙 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", f"{page.AUTO_NAME_PREFIX}_dr")
        page.add_secure_drive("base", "Y", "C:\\dr_base", "WRITE", "100")   # 기준 항목
        # (1) 생성위치 중복 — 같은 C: 루트, 다른 폴더/문자/라벨
        m_loc = page.add_secure_drive("other", "Z", "C:\\dr_other", "WRITE", "100")
        self._add("pass" if (m_loc and "생성위치" in m_loc) else "fail",
                  "sc3h — 생성위치 중복 차단(같은 루트)",
                  f"입력: C:\\dr_base 후 C:\\dr_other(같은 C: 루트, 다른 폴더) / 결과: {m_loc!r}", sc=3,
                  repro="1. C:\\ 루트 항목 추가\n2. 같은 C:\\ 루트 다른 폴더 추가\n3. '생성위치와 동일' 차단")
        # (2) 문자 중복 — 같은 Y, 다른 루트
        m_letter = page.add_secure_drive("other2", "Y", "D:\\dr_y", "WRITE", "100")
        self._add("pass" if (m_letter and "문자" in m_letter) else "fail",
                  "sc3h — 드라이브 문자 중복 차단",
                  f"입력: 문자 Y 중복(다른 루트 D:) / 결과: {m_letter!r}", sc=3,
                  repro="1. 문자 Y 항목 추가\n2. 같은 문자 Y 추가\n3. '이미 등록된 드라이브 문자' 차단")
        # (3) 라벨 중복 — 같은 'base' 라벨, 다른 문자/루트 → 허용(검사 없음)
        before = len(page.secure_drive_rows())
        m_label = page.add_secure_drive("base", "R", "E:\\dr_lbl", "WRITE", "100")
        after = len(page.secure_drive_rows())
        allowed = (m_label is None) and (after > before)
        self._add("pass" if allowed else "warn",
                  "sc3h — 드라이브 라벨 중복(허용 — 검사 없음)",
                  f"입력: 라벨 'base' 중복(다른 문자 R/루트 E:) / 결과: {'추가됨' if allowed else '차단/실패'} "
                  f"({before}→{after}행) [문자·생성위치는 차단하나 라벨은 미검사 — 라벨은 키 아님]", sc=3,
                  repro="1. 라벨 'base' 항목 추가\n2. 같은 라벨 다른 문자/루트 추가\n3. 차단 없이 추가됨(라벨 미검사)")
        page._close_modal_if_open()

    # ══ 3i: 이름 중복 차단 ══════════════════════════════════════════
    def test_scenario3i_name_duplicate(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3i: 이름 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        base = f"{page.AUTO_NAME_PREFIX}_dup"
        if base not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(base, sd_letter="J", to_letter="K", to_path="E:\\dup1")
            page.navigate_to()
        # 같은 이름으로 재생성 시도 → 차단 기대(실측 2026-06-23)
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", base)
        page.add_secure_drive("d", "L", "E:\\dup2", "WRITE", "100")
        page.fill_takeout("E:\\dup2to", "M", "lbl", "1024")
        msg = page.submit_and_message()
        ok = "이미 등록된 이름" in msg
        self._add("pass" if ok else "fail",
                  "sc3i — 이름 중복 차단",
                  f"입력: 기존 '{base}' 이름으로 재생성 / 결과: {msg!r} "
                  + ("(중복 차단)" if ok else "[차단 실패 — 중복 저장?]"), sc=3,
                  repro=f"1. '{base}' 생성\n2. 같은 이름으로 재생성 시도\n3. '이미 등록된 이름 입니다.' 차단")
        page._close_modal_if_open()

    # ══ 3j: 이름 특수문자 (허용/검증) ═══════════════════════════════
    def test_scenario3j_special_char_name(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3j: 이름 특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_!@#%^&()"
        if name not in page.get_template_names():
            page.open_add_modal()
            msg = page.create_basic_template(name, sd_letter="J", to_letter="K", to_path="H:\\sp")
            page.navigate_to()
        else:
            msg = "(이미 존재)"
        saved = name in page.get_template_names()
        # 직접조작(2026-06-23): 특수문자 이름 → "저장 하였습니다"(허용, 제한/새니타이즈 없음)
        self._add("pass" if saved else "warn",
                  "sc3j — 이름 특수문자 입력(생성 시)",
                  f"입력: 이름='{name}' / 결과: {msg!r}, 저장됨={saved} "
                  + ("(특수문자 허용 — 이름 제한/새니타이즈 없음)" if saved else "(특수문자 차단됨)"), sc=3,
                  repro="1. 이름에 특수문자(!@#%^&()) 포함\n2. 저장\n3. 허용/차단 확인")

    # ══ 3k: 오버플로 (예외 드라이브 500자 초과 → 서버 차단) ═════════
    def test_scenario3k_overflow_old_drive(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3k: 오버플로(예외 드라이브 3000자) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_ovf"
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", name)
        page.fill(page.SEL_OLD_DRIVE, "a" * 3000)   # 예외 드라이브(클라 maxlength 없음) 3000자
        page.add_secure_drive("d", "J", "I:\\ovf", "WRITE", "100")
        page.fill_takeout("I:\\ovfto", "K", "lbl", "1024")
        msg = page.submit_and_message()
        page.navigate_to()
        saved = name in page.get_template_names()
        blocked = ("500자" in msg or "최대" in msg) and not saved
        # 직접조작(2026-06-23): 3000자 → "예외드라이브 문자의 입력 가능 글자수는 최대 500자..." 차단(서버측, 명확)
        self._add("pass" if blocked else "warn",
                  "sc3k — 예외 드라이브 글자수 오버플로(3000자) 서버 검증",
                  f"입력: 예외 드라이브 3000자 저장 / 결과: {msg!r}, 저장됨={saved} "
                  + ("(서버측 최대 500자 제한 — 명확한 메시지로 차단)" if blocked
                     else "[제한 미동작 또는 generic 오류 — 확인 필요]"), sc=3,
                  repro="1. 예외 드라이브에 3000자\n2. 저장\n3. '최대 500자' 차단 확인")
        page._close_modal_if_open()

    # ══ 3l: 복사 (체크 + 복사 버튼 → 복사본 생성) ═══════════════════
    def test_scenario3l_copy(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3l: 복사 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        base = f"{page.AUTO_NAME_PREFIX}_cp"
        if base not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(base, sd_letter="J", to_letter="K", to_path="E:\\cp")
            page.navigate_to()
        copy_name = page.copy_template(base)
        page.navigate_to()
        exists = copy_name in page.get_template_names()
        self._add("pass" if exists else "fail",
                  "sc3l — 복사: 체크+복사 → 복사본(원본+'_copy') 생성",
                  f"입력: '{base}' 복사 / 결과: 복사본 '{copy_name}' 목록존재={exists}", sc=3,
                  repro="1. 항목 체크\n2. 복사 → '복사 하시겠습니까?' 확인\n3. 원본+'_copy' 생성 확인")

    # ══ 3m: 검색 필터 (생성한 [AUTO] 찾기) ══════════════════════════
    def test_scenario3m_search_filter(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3m: 검색 필터 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        seed = f"{page.AUTO_NAME_PREFIX}_a"          # 검색 대상 최소 1개 보장
        if seed not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(seed, sd_letter="J", to_letter="K", to_path="E:\\se")
            page.navigate_to()
        total = len(page.get_template_names())
        page.search(page.AUTO_NAME_PREFIX)           # "[AUTO]_sztpl_sd"
        filtered = page.get_template_names()
        all_match = bool(filtered) and all(page.AUTO_NAME_PREFIX in n for n in filtered)
        page.search("ZZZ_no_such_xyz_000")           # 없는 값
        none_rows = page.get_template_names()
        page.search("")                               # 초기화 → 전체 복귀
        reset = len(page.get_template_names())
        ok = all_match and (len(filtered) <= total) and (reset >= len(filtered))
        self._add("pass" if ok else "fail",
                  "sc3m — 검색 필터(템플릿 이름 부분일치) + 초기화",
                  f"입력: 검색 '{page.AUTO_NAME_PREFIX}' / 결과: 전체 {total} → 필터 {len(filtered)}건"
                  f"(전부 일치={all_match}) / 없는값 {len(none_rows)}행 / 초기화 {reset}건", sc=3,
                  repro="1. 검색창에 이름 일부 입력\n2. 검색 버튼\n3. 일치 항목만 필터 / 초기화 시 전체 복귀")

    # ══ 3n: 복사 이름 충돌 — '원본_copy' 존재 시 재복사 → 중복 이름 생성(버그) ══
    def test_scenario3n_copy_name_collision(self, logged_in_page, settings):
        """복사 경로 이름 중복검사 누락 — '원본_copy'가 이미 있는데 원본을 또 복사하면
        동일 이름('원본_copy')이 중복 생성됨. 수동 생성은 '이미 등록된 이름' 차단하는데 복사는 미검사(불일치).
        직접조작 확정 2026-06-23: 서버오류 아님, 조용히 중복 생성(반복 시 누적)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3n: 복사 이름 충돌 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        base = f"{page.AUTO_NAME_PREFIX}_coll"
        copy_name = f"{base}_copy"
        # 원본 + 원본_copy 둘 다 확보
        if base not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(base, sd_letter="J", to_letter="K", to_path="E:\\coll")
            page.navigate_to()
        if copy_name not in page.get_template_names():
            page.copy_template(base)          # 1차 복사 → 원본_copy 생성
            page.navigate_to()
        before = page.get_template_names().count(copy_name)
        # 원본을 다시 복사 → 자동이름이 기존 '원본_copy' 와 충돌
        page.copy_template(base)
        page.navigate_to()
        after = page.get_template_names().count(copy_name)
        dup_created = after > before
        self._add("warn" if dup_created else "pass",
                  "sc3n — 복사 이름 중복검사(원본_copy 존재 시 재복사)",
                  f"입력: '{base}'+'{copy_name}' 존재 상태에서 '{base}' 재복사 / "
                  f"결과: '{copy_name}' 개수 {before}→{after} "
                  + ("[버그: 복사 경로는 이름 중복검사 없이 동일 이름 중복 생성. 수동생성은 차단함(불일치)]"
                     if dup_created else "(중복 차단 — 정상)"), sc=3,
                  highlight=page.page.locator(f'{page.SEL_TABLE_ROW}[data-name="{copy_name}"]'),
                  repro=f"1. '{base}' 와 '{copy_name}' 둘 다 존재\n2. '{base}' 다시 복사\n"
                        f"3. 동일 '{copy_name}' 또 생성되는지(중복=버그)")

    # (시큐어드라이브 항목 제거(저장 전 모달 편집)는 삭제 동작 소유가 sc1/sc5 → 생성 시나리오에서 제외)

    # ══ 3o: 검증 메시지 i18n 전수(sweep) — 카테고리 전수, raw 키 누출 자동판정 ══
    def test_scenario3o_validation_message_i18n_sweep(self, logged_in_page, settings):
        """검증 메시지 i18n 전수 — 모든 min/max/길이/형식 검증을 트리거·수집해 raw i18n 키 누출 자동판정.
        spot-check(필드별 일회성)가 아닌 카테고리 전수: 반출용량·예외드라이브·서브용량·경고용량·서브문자·서브경로.
        직접조작 확정 2026-06-24: 반출용량(COLUMN.NAME.TAKEOUT_DRIVE_QUOTA)·경고용량(systemDriveWarningQuota)이
        한글 메시지 안에 raw i18n 키 노출(번역 누락). 나머지는 정상 번역. (구 sc2h/단일 경고용량 카드를 이 전수로 통합)"""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3o: 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        n = 0
        # 제너레이터가 각 경고를 '열어둔 채' yield → 누출 행은 그 경고 모달을 highlight 캡처
        for label, msg in page.iter_validation_messages():
            n += 1
            m = _I18N_RAW_KEY.search(msg or "")
            leaked = bool(m)
            self._add("warn" if leaked else "pass",
                      f"sc3o — 검증 메시지 i18n: {label}",
                      f"결과: {msg!r} "
                      + (f"[버그: 한글 메시지에 raw i18n 키 '{m.group(0)}' 노출 — 번역 누락]"
                         if leaked else "(정상 번역)"),
                      sc=3,
                      # 누출(warn) 행만 경고 모달 캡처(열린 상태). 정상 행은 _add 가 캡처 안 함
                      highlight=(page.page.locator(f"{page.SEL_CONFIRM_MODAL_OPENED} {page.SEL_MODAL_BODY_TEXT}")
                                 if leaked else None),
                      repro=f"1. {label} 검증 트리거\n2. 한글 경고 메시지에 raw i18n 키가 섞여 노출되는지")
        if n == 0:
            self._add("fail", "sc3o — 검증 메시지 i18n 전수", "결과: 메시지 수집 실패(0건)", sc=3)

    # ══ 3p: 체크박스/라디오 토글 상호작용 전수 ══════════════════════
    def test_scenario3p_toggle_interaction(self, logged_in_page, settings):
        """체크박스/라디오 토글 상호작용 전수 — 각 토글이 클릭 시 상태 반전(체크박스 on↔off), 라디오 상호배타.
        직접조작 확정 2026-06-24: ECM연동/반출폴더숨김/생성위치숨김/용량부족경고 정상 토글, 용량방식 WRITE/SYNC 상호배타.
        (sc2c=초기 default 상태, sc2g=용량방식 종속효과 / 3p=토글 자체 동작)"""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 3p: 토글 상호작용 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        # 메인 모달 체크박스
        for label, sel in [("ECM드라이브 연동", page.SEL_ECM), ("반출 폴더 숨김", page.SEL_TAKEOUT_HIDE)]:
            ok = page.checkbox_toggles(sel)
            self._add("pass" if ok else ("skip" if ok is None else "fail"),
                      f"sc3p — 토글: {label}",
                      "결과: " + ("클릭 시 on↔off 정상 반전" if ok else ("대상 미존재" if ok is None else "[토글 안 됨]")),
                      sc=3, repro=f"1. {label} 클릭\n2. 체크 반전\n3. 다시 클릭→복귀")
        # 서브모달 체크박스
        page.open_sub_modal()
        for label, sel in [("생성위치 숨김", page.SEL_SUB_PATH_HIDE), ("용량부족 경고", page.SEL_SUB_WARN_TOGGLE)]:
            ok = page.checkbox_toggles(sel)
            self._add("pass" if ok else ("skip" if ok is None else "fail"),
                      f"sc3p — 토글: 서브 {label}",
                      "결과: " + ("클릭 시 on↔off 정상 반전" if ok else ("대상 미존재" if ok is None else "[토글 안 됨]")),
                      sc=3, repro=f"1. 서브 {label} 클릭\n2. 체크 반전\n3. 다시 클릭→복귀")
        # 용량방식 라디오 상호배타
        a_ok, b_ok, exclusive = page.radio_exclusive(page.SEL_SUB_QTYPE_WRITE, page.SEL_SUB_QTYPE_SYNC)
        self._add("pass" if exclusive else "fail",
                  "sc3p — 토글: 용량방식 라디오(WRITE/SYNC) 상호배타",
                  f"결과: WRITE 선택={a_ok}, SYNC 선택={b_ok}, 상호배타={exclusive}", sc=3,
                  repro="1. WRITE 선택→WRITE만\n2. SYNC 선택→SYNC만(상호배타)")
        page.close_sub_modal()
        page._close_modal_if_open()

