"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 4: 수정 (docs/scenario_4_modify.md 준수).

수정 흐름 전체 정합성: 4-1 로드 / 4-2 수정후재확인 / 4-3 위반 저장값 + 생성(sc3) 검증을 수정 모달에서 재실행.
sc3 캐리오버(수정 컨텍스트): clamp / 서브검증 / 반출형식 / 멀티추가·중복 / 이름중복(rename) / 특수문자 / 오버플로 / i18n전수 / 토글 / 항목제거.
제외(생성·리스트 전용): 정상생성→목록(정상수정으로 대체) / 복사 / 검색 / 복사충돌.

진행: 4a 로드 / 4b 수정-저장=update(중복X+변경반영, 확정됨 2026-06-29) / 4c 4-3 필수누락 위반저장값 / 4d 형식검증(수정).
※ 수정 모달 저장 버튼은 '수정'(modifybtn) — '확인'(addbtn)은 추가용/수정시 숨김. 잘못된 '확인' 클릭이 생성-충돌나던 것 page._click_save 로 해결.
※ Chrome 합성 행선택은 수정 모달 데이터 로드가 불안정(blank) → 수정 검증은 Playwright run 으로 확정(수정 모달=추가와 동일 모달·검증).
(이후 캐리오버: clamp/서브검증/중복규칙/i18n전수/토글 — 수정 컨텍스트 재실행)

cleanup: sc2_3_4 = cleanup 없음(재사용). 수정 대상 [AUTO]_sztpl_sd_mod 는 sc5c 가 정리.
"""
import re
import time

from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase

_I18N_RAW_KEY = re.compile(r"[A-Za-z][A-Za-z._]{3,}")  # 한글 메시지 안 Latin 식별자 4자+ = raw 키 의심


class TestSecureZoneTemplateScenario4Modify(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 4: 수정."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def _ensure_target(self, page, name):
        """수정 대상 [AUTO] 템플릿 보장(없으면 생성)."""
        if name not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(name, sd_letter="Q", to_letter="T", to_path="C:\\sc4")
            page.navigate_to()

    # ══ 4a: 4-1 로드 확인 — 수정 모달 전 필드 저장값 로드 ══════════
    def test_scenario4a_load(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4a: 수정 모달 로드(4-1) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)
        nm = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        to_path = page.page.locator(page.SEL_TAKEOUT_PATH).first.input_value()
        to_letter = page.page.locator(page.SEL_TAKEOUT_LETTER).first.input_value()
        rows = page.secure_drive_rows()
        loaded = (nm == name) and bool(to_path) and bool(to_letter) and (len(rows) >= 1)
        self._add("pass" if loaded else "fail",
                  "sc4a — 수정 모달 전 필드 로드(4-1)",
                  f"입력: '{name}' 수정 모달 오픈 / 결과: 이름='{nm}', 반출경로='{to_path}', "
                  f"반출문자='{to_letter}', 시큐어드라이브 {len(rows)}행={rows}", sc=4,
                  repro="1. 템플릿 수정 모달 열기\n2. 이름·반출·시큐어드라이브 항목이 저장값으로 로드되는지")
        page.close_modal()

    # ══ 4b: 4-2 수정 후 재확인 + ★update 재검증(중복 생성 아닌지) ══
    def test_scenario4b_modify_is_update(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4b: 수정 저장=update 재검증(4-2) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        before_count = page.get_template_names().count(name)
        new_label = f"mod{int(time.time()) % 100000}"   # 매 실행 고유값
        page.open_modify_modal(name)
        page.fill(page.SEL_TAKEOUT_LABEL, new_label)     # 반출 라벨만 변경(이름 유지)
        msg = page.submit_and_message()
        page.navigate_to()
        after_count = page.get_template_names().count(name)
        # 재오픈 → 변경값 반영 확인
        loaded_label = ""
        if name in page.get_template_names():
            page.open_modify_modal(name)
            loaded_label = page.page.locator(page.SEL_TAKEOUT_LABEL).first.input_value()
            page.close_modal()
        is_update = (after_count == before_count)        # 수정이 새 항목을 만들지 않음
        changed = (loaded_label == new_label)
        ok = ("저장" in msg) and is_update and changed
        self._add("pass" if ok else "fail",
                  "sc4b — 수정 저장 = update(중복 생성 아님) + 변경값 반영(4-2)",
                  f"입력: 이름 유지 + 반출라벨→'{new_label}' 저장 / 결과: {msg!r}, "
                  f"목록 개수 {before_count}→{after_count}(update={is_update}), "
                  f"재오픈 반출라벨='{loaded_label}'(기대 '{new_label}') "
                  + ("" if ok else "[update 실패 — 중복 생성/미반영/저장차단 확인 필요]"), sc=4,
                  repro="1. 수정 모달에서 반출라벨 변경(이름 유지)\n2. 저장→'저장 하였습니다'\n"
                        "3. 목록에 원본만 1개(중복 X) + 재오픈 시 변경값 반영")

    # ══ 4c: 4-3 필수 누락 위반 → 재오픈 시 실제 저장값 ════════════
    def test_scenario4c_required_empty_violation(self, logged_in_page, settings):
        """4-3: 필수 필드 비우고 저장 시도 → 재오픈 시 실제 저장값 분기(추정 금지).
        빈값=fail(데이터 손상) / 원본+경고=pass(차단·보존) / 원본+무경고=warn(silent) / 다른값=fail.
        수정 모달은 추가와 동일 검증 — 수정 시에도 필수 검증 적용되는지 + 위반 시 데이터 처리 확인."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4c: 4-3 필수 누락 위반 저장값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        fields = [
            ("이름", f"{page.SEL_MODAL} {page.SEL_NAME}"),
            ("반출 생성위치", page.SEL_TAKEOUT_PATH),
            ("반출 문자", page.SEL_TAKEOUT_LETTER),
            ("반출 라벨", page.SEL_TAKEOUT_LABEL),
            ("반출 용량", page.SEL_TAKEOUT_QUOTA),
        ]
        for label, sel in fields:
            page.open_modify_modal(name)
            original = page.page.locator(sel).first.input_value()
            page.fill(sel, "")
            msg = page.submit_and_message()        # 차단 시 경고 + 편집 모달 잔존
            page._close_modal_if_open()             # 미저장 닫기
            page.navigate_to()
            actual = "(미확인)"
            if name in page.get_template_names():
                page.open_modify_modal(name)
                actual = page.page.locator(sel).first.input_value()
                page.close_modal()
            if actual == "":
                status, note = "fail", "빈값 저장됨 — 데이터 손상"
            elif actual == original:
                status = "pass" if msg else "warn"
                note = "차단 + 원본 유지(" + ("경고 있음 — 정상" if msg else "silent — UX 혼란") + ")"
            else:
                status, note = "fail", f"예상 못한 값 '{actual}'"
            self._add(status,
                      f"sc4c — 4-3 필수 '{label}' 비움 후 실제 저장값",
                      f"입력: '{label}' 비우고 저장 / 경고: {msg!r} / 재오픈값='{actual}'(원본='{original}') [{note}]", sc=4,
                      repro=f"1. 수정 모달에서 '{label}' 비움\n2. 저장 시도\n3. 재오픈 시 실제 값(빈값=손상/원본=차단)")

    # ══ 4d: 형식 검증 (수정 모달) — 반출문자 A-Z / 반출경로 누락 ══
    def test_scenario4d_format_in_modify(self, logged_in_page, settings):
        """수정 시에도 형식 검증 적용되는지(추가 sc3e/3f 를 수정 컨텍스트로). 동일 모달 → 동일 결과 기대:
        반출 문자 '1'→A-Z 차단(정상) / 반출 경로 'qwe'→형식검증 없음(저장됨=버그, 3e 미러). 경로는 검증 후 원복."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4d: 형식 검증(수정 모달) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        # (1) 반출 문자 '1' → A-Z 차단 기대
        page.open_modify_modal(name)
        page.fill(page.SEL_TAKEOUT_LETTER, "1")
        msg_letter = page.submit_and_message()
        page._close_modal_if_open()
        blocked = "A-Z" in msg_letter
        self._add("pass" if blocked else "warn",
                  "sc4d — 수정: 반출 문자 형식 검증(A-Z)",
                  f"입력: 반출문자→'1' 수정 저장 / 결과: {msg_letter!r} "
                  + ("(A-Z 차단 — 정상)" if blocked else "[차단 안 됨]"), sc=4,
                  repro="1. 수정 모달 반출문자→'1'\n2. 저장→'A-Z' 차단되는지")
        # (2) 반출 경로 'qwe' → 형식검증 없으면 저장됨(버그). 재오픈해 'qwe' 필드 highlight 캡처(3e 동일 품질)
        page.open_modify_modal(name)
        page.fill(page.SEL_TAKEOUT_PATH, "qwe")
        msg_path = page.submit_and_message()
        page.navigate_to()
        if name in page.get_template_names():
            page.open_modify_modal(name)          # 재오픈 — 'qwe' 가 필드에 로드된 상태에서 캡처
            path_after = page.page.locator(page.SEL_TAKEOUT_PATH).first.input_value()
            saved_qwe = (path_after == "qwe")
            self._add("warn" if saved_qwe else "pass",
                      "sc4d — 수정: 반출 경로 형식 검증",
                      f"입력: 반출경로→'qwe' 수정 저장 / 결과: {msg_path!r}, 재오픈='{path_after}' "
                      + ("[형식 검증 없음 — 수정에서도 'qwe' 저장됨(3e 동일 버그)]" if saved_qwe else "(형식 검증으로 차단)"),
                      sc=4, highlight=(page.page.locator(page.SEL_TAKEOUT_PATH) if saved_qwe else None),
                      repro="1. 수정 모달 반출경로→'qwe'\n2. 저장\n3. 재오픈 'qwe' 그대로면 형식검증 없음(버그)")
            page.fill(page.SEL_TAKEOUT_PATH, "C:\\sc4")   # 원복(다음 실행 위해)
            page.submit_and_message()
        else:
            self._add("pass", "sc4d — 수정: 반출 경로 형식 검증",
                      f"입력: 반출경로→'qwe' / 결과: {msg_path!r} (차단/미저장)", sc=4,
                      repro="1. 수정 모달 반출경로→'qwe'\n2. 저장→차단되는지")

    # ══ 4e: 글자수 clamp(수정 모달) — sc3c 미러 ════════════════════
    def test_scenario4e_clamp_in_modify(self, logged_in_page, settings):
        """글자수 제한 실입력 — 수정 모달에서도 maxlength 클램핑 동작하는지(sc3c 미러). 저장 안 함."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4e: 글자수 clamp(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)

        def _clamp(label, sel):
            loc = page.page.locator(sel).first
            if loc.count() == 0:
                self._add("skip", f"sc4e — '{label}' 글자수", "대상 미존재", sc=4); return
            ml = loc.get_attribute("maxlength")
            if not (ml and ml.isdigit()):
                self._add("pass", f"sc4e — '{label}' 글자수", "결과: maxlength 없음 — 서버측(클램핑 해당 없음)", sc=4); return
            limit = int(ml)
            actual = page.type_clamped(sel, "a" * (limit + 5))
            self._add("pass" if actual <= limit else "fail",
                      f"sc4e — '{label}' maxlength({limit}) 초과 입력 시 잘림(수정)",
                      f"입력: {limit+5}자 / 결과: 실제 {actual}자 " + ("(잘림)" if actual <= limit else "[미적용]"),
                      sc=4, repro=f"1. 수정 모달 '{label}'에 {limit+5}자\n2. {limit}자로 잘리는지")

        page.open_modify_modal(name)
        for label, sel in [("템플릿 이름", f"{page.SEL_MODAL} {page.SEL_NAME}"),
                           ("반출 생성위치", page.SEL_TAKEOUT_PATH), ("반출 문자", page.SEL_TAKEOUT_LETTER),
                           ("반출 라벨", page.SEL_TAKEOUT_LABEL), ("반출 용량", page.SEL_TAKEOUT_QUOTA)]:
            _clamp(label, sel)
        page.open_sub_modal()
        for label, sel in [("서브 라벨", page.SEL_SUB_LABEL), ("서브 문자", page.SEL_SUB_LETTER),
                           ("서브 생성위치", page.SEL_SUB_PATH), ("서브 용량", page.SEL_SUB_QUOTA)]:
            _clamp(label, sel)
        page.close_sub_modal()
        page._close_modal_if_open()

    # ══ 4f: 서브 입력검증(필수+형식, 수정 모달) — sc3d 미러 ═════════
    def test_scenario4f_sub_validation_in_modify(self, logged_in_page, settings):
        """서브모달 입력검증 — 수정 모달에서도 동일 검증 적용(sc3d 미러). 검증 순서 문자→라벨→경로→용량."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4f: 서브 입력검증(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)
        page.open_sub_modal()
        cases = [
            ("secureDriveLetter", "",    "시큐어드라이브 문자를 입력해 주세요.", "문자 빈값"),
            ("secureDriveLetter", "Q",   None, None),
            ("secureDriveLabel",  "",    "시큐어드라이브 라벨을 입력해 주세요.", "라벨 빈값"),
            ("secureDriveLabel",  "lbl", None, None),
            ("secureDriveLetter", "1",   "A-Z",                                "문자 '1'(A-Z)"),
            ("secureDriveLetter", "Q",   None, None),
            ("secureDrivePath",   "qwe", "정상적인 경로를 입력해 주세요.",       "경로 'qwe'"),
            ("secureDrivePath",   "C:\\sdtest", None, None),
            ("secureDriveQuota",  "50",  "100MB",                              "용량 '50'(min)"),
        ]
        for fid, val, expect, desc in cases:
            page.fill(f"{page.SEL_SUB} input#{fid}", val)
            if desc is None:
                continue
            msg = page.sub_add_message()
            self._add("pass" if expect in msg else "fail",
                      f"sc4f — 서브 {desc} → 경고(수정)",
                      f"입력: {desc} 후 추가 / 결과: {msg!r} (기대 포함 {expect!r})", sc=4,
                      repro=f"1. 수정 모달 서브 {desc}\n2. 추가 → 경고 확인")
        page.close_sub_modal()
        page._close_modal_if_open()

    # ══ 4g: 시큐어드라이브 항목 추가(수정 모달) — sc3g 미러 ═════════
    def test_scenario4g_secure_drive_add_in_modify(self, logged_in_page, settings):
        """수정 모달에서 시큐어드라이브 항목 추가 → 리스트 증가(sc3g 미러). 다른 루트/문자로. 저장 안 함."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4g: 시큐어드라이브 추가(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)
        before = len(page.secure_drive_rows())
        page.add_secure_drive("m_add", "R", "D:\\m_add", "WRITE", "100")   # 기존(Q/C:)와 다른 루트·문자
        after = len(page.secure_drive_rows())
        self._add("pass" if after == before + 1 else "fail",
                  "sc4g — 수정 모달에서 시큐어드라이브 추가 → 리스트 증가",
                  f"입력: 기존 {before}건에 1건 추가(R/D:) / 결과: {after}건", sc=4,
                  repro="1. 수정 모달\n2. 시큐어드라이브 추가(다른 루트/문자)\n3. 리스트 +1")
        page._close_modal_if_open()

    # ══ 4h: 항목 중복 규칙(수정 모달) — sc3h 미러 ══════════════════
    def test_scenario4h_duplicate_rules_in_modify(self, logged_in_page, settings):
        """수정 모달에서 시큐어드라이브 중복 규칙 — 기존 항목(Q/C:)과 생성위치·문자 충돌 차단(sc3h 미러). 저장 안 함."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4h: 항목 중복 규칙(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)   # 기존 sd: 문자 Q / 경로 C:\sztpl_sd (C: 루트)
        m_loc = page.add_secure_drive("dl", "S", "C:\\dup_other_m", "WRITE", "100")   # 같은 C: 루트
        self._add("pass" if (m_loc and "생성위치" in m_loc) else "fail",
                  "sc4h — 생성위치 중복 차단(수정, 같은 루트)",
                  f"입력: 기존 C: 루트에 C:\\dup_other_m 추가 / 결과: {m_loc!r}", sc=4,
                  repro="1. 수정 모달\n2. 기존과 같은 C: 루트 추가\n3. '생성위치와 동일' 차단")
        m_letter = page.add_secure_drive("dl2", "Q", "E:\\dup_q_m", "WRITE", "100")   # 같은 문자 Q
        self._add("pass" if (m_letter and "문자" in m_letter) else "fail",
                  "sc4h — 드라이브 문자 중복 차단(수정)",
                  f"입력: 기존 문자 Q 중복(다른 루트 E:) / 결과: {m_letter!r}", sc=4,
                  repro="1. 수정 모달\n2. 기존과 같은 문자 Q 추가\n3. '이미 등록된 드라이브 문자' 차단")
        page._close_modal_if_open()

    # ══ 4i: 이름 중복 차단(rename, 수정 모달) — sc3i 미러 ═══════════
    def test_scenario4i_rename_duplicate(self, logged_in_page, settings):
        """수정 시 다른 기존 템플릿 이름으로 변경 → '이미 등록된 이름' 차단(sc3i 미러)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4i: 이름 중복(rename) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        other = f"{page.AUTO_NAME_PREFIX}_other"
        self._ensure_target(page, name)
        if other not in page.get_template_names():
            page.open_add_modal()
            page.create_basic_template(other, sd_letter="W", to_letter="X", to_path="E:\\other")
            page.navigate_to()
        page.open_modify_modal(name)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", other)   # 기존 다른 이름으로 변경 시도
        msg = page.submit_and_message()
        blocked = "이미 등록된 이름" in msg
        self._add("pass" if blocked else "fail",
                  "sc4i — 이름 중복 차단(rename → 기존 이름)",
                  f"입력: '{name}'→'{other}'(기존) 변경 / 결과: {msg!r} "
                  + ("(중복 차단)" if blocked else "[차단 실패]"), sc=4,
                  repro=f"1. 수정 모달에서 이름을 기존 '{other}'로 변경\n2. 저장\n3. '이미 등록된 이름' 차단")
        page._close_modal_if_open()

    # ══ 4j: 이름 특수문자(rename, 수정 모달) — sc3j 미러 ═══════════
    def test_scenario4j_special_char_rename(self, logged_in_page, settings):
        """수정 시 이름을 특수문자로 변경 → 허용/차단(sc3j 미러). 검증 후 원복."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4j: 특수문자 rename ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        special = f"{page.AUTO_NAME_PREFIX}_!@#mod"
        page.open_modify_modal(name)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", special)
        msg = page.submit_and_message()
        page.navigate_to()
        renamed = special in page.get_template_names()
        self._add("pass" if renamed else "warn",
                  "sc4j — 이름 특수문자 변경(수정)",
                  f"입력: '{name}'→'{special}' / 결과: {msg!r}, 변경됨={renamed} "
                  + ("(특수문자 허용)" if renamed else "(차단됨)"), sc=4,
                  repro="1. 수정 모달 이름에 특수문자\n2. 저장\n3. 허용/차단 확인")
        if renamed:   # 원복
            page.open_modify_modal(special)
            page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", name)
            page.submit_and_message()
        page._close_modal_if_open()

    # ══ 4k: 오버플로(예외 드라이브, 수정 모달) — sc3k 미러 ═════════
    def test_scenario4k_overflow_in_modify(self, logged_in_page, settings):
        """수정 시 예외 드라이브 3000자 → 서버측 최대 500자 차단(sc3k 미러)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4k: 오버플로(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)
        page.fill(page.SEL_OLD_DRIVE, "a" * 3000)
        msg = page.submit_and_message()
        blocked = ("500자" in msg or "최대" in msg)
        self._add("pass" if blocked else "warn",
                  "sc4k — 예외 드라이브 오버플로(3000자) 서버 검증(수정)",
                  f"입력: 예외 드라이브 3000자 저장 / 결과: {msg!r} "
                  + ("(최대 500자 차단)" if blocked else "[제한 미동작]"), sc=4,
                  repro="1. 수정 모달 예외 드라이브 3000자\n2. 저장→'최대 500자' 차단")
        page._close_modal_if_open()

    # ══ 4l: 검증 메시지 i18n 전수(수정 모달) — sc3o 미러 ═══════════
    def test_scenario4l_validation_message_i18n_sweep_in_modify(self, logged_in_page, settings):
        """검증 메시지 i18n 전수 — 수정 모달에서도 raw 키 누출 자동판정(sc3o 미러, 수정에서도 동일 누출인지)."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4l: 검증 메시지 i18n 전수(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        n = 0
        for label, msg in page.iter_validation_messages(modify_name=name):
            n += 1
            m = _I18N_RAW_KEY.search(msg or "")
            leaked = bool(m)
            self._add("warn" if leaked else "pass",
                      f"sc4l — 검증 메시지 i18n(수정): {label}",
                      f"결과: {msg!r} "
                      + (f"[버그: raw i18n 키 '{m.group(0)}' 노출 — 번역 누락]" if leaked else "(정상 번역)"),
                      sc=4,
                      highlight=(page.page.locator(f"{page.SEL_CONFIRM_MODAL_OPENED} {page.SEL_MODAL_BODY_TEXT}")
                                 if leaked else None),
                      repro=f"1. 수정 모달에서 {label} 검증 트리거\n2. 한글 경고에 raw i18n 키 노출되는지")
        if n == 0:
            self._add("fail", "sc4l — 검증 메시지 i18n(수정)", "결과: 메시지 수집 실패(0건)", sc=4)

    # ══ 4m: 토글 상호작용(수정 모달) — sc3p 미러 ═══════════════════
    def test_scenario4m_toggle_in_modify(self, logged_in_page, settings):
        """체크박스/라디오 토글 — 수정 모달에서도 정상 토글/상호배타(sc3p 미러). 저장 안 함."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4m: 토글(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)
        for label, sel in [("ECM드라이브 연동", page.SEL_ECM), ("반출 폴더 숨김", page.SEL_TAKEOUT_HIDE)]:
            ok = page.checkbox_toggles(sel)
            self._add("pass" if ok else ("skip" if ok is None else "fail"),
                      f"sc4m — 토글(수정): {label}",
                      "결과: " + ("on↔off 정상 반전" if ok else ("대상 미존재" if ok is None else "[토글 안 됨]")),
                      sc=4, repro=f"1. 수정 모달 {label} 클릭\n2. 반전\n3. 다시 클릭→복귀")
        page.open_sub_modal()
        for label, sel in [("생성위치 숨김", page.SEL_SUB_PATH_HIDE), ("용량부족 경고", page.SEL_SUB_WARN_TOGGLE)]:
            ok = page.checkbox_toggles(sel)
            self._add("pass" if ok else ("skip" if ok is None else "fail"),
                      f"sc4m — 토글(수정): 서브 {label}",
                      "결과: " + ("on↔off 정상 반전" if ok else ("대상 미존재" if ok is None else "[토글 안 됨]")),
                      sc=4, repro=f"1. 수정 모달 서브 {label} 클릭\n2. 반전\n3. 복귀")
        a_ok, b_ok, exclusive = page.radio_exclusive(page.SEL_SUB_QTYPE_WRITE, page.SEL_SUB_QTYPE_SYNC)
        self._add("pass" if exclusive else "fail",
                  "sc4m — 토글(수정): 용량방식 라디오 상호배타",
                  f"결과: WRITE={a_ok}, SYNC={b_ok}, 상호배타={exclusive}", sc=4,
                  repro="1. WRITE→WRITE만\n2. SYNC→SYNC만")
        page.close_sub_modal()
        page._close_modal_if_open()

    # ══ 4n: 시큐어드라이브 항목 삭제 규칙 (메인 삭제불가 / 비메인 삭제) ══
    def test_scenario4n_secure_drive_delete_rules(self, logged_in_page, settings):
        """수정 모달에서 시큐어드라이브 항목 삭제 규칙 — 직접조작 확정 2026-06-29:
        메인 드라이브(첫 항목 '*') 삭제 → '메인 드라이브는 삭제 할 수 없습니다' 차단 /
        비-메인 항목 → 확인 없이 즉시 제거. (항목 편집은 불가 — 행 클릭 핸들러 없음) 저장 안 함."""
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 4n: 시큐어드라이브 삭제 규칙 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = f"{page.AUTO_NAME_PREFIX}_mod"
        self._ensure_target(page, name)
        page.open_modify_modal(name)
        # (1) 메인(첫 항목) 삭제 → 차단
        msg_main = page.delete_secure_drive_row(0)
        main_blocked = bool(msg_main) and ("메인 드라이브" in msg_main)
        self._add("pass" if main_blocked else "fail",
                  "sc4n — 메인 드라이브 삭제 불가",
                  f"입력: 첫 항목(메인 '*') 삭제 시도 / 결과: {msg_main!r} "
                  + ("(차단 — 메인 드라이브 삭제 불가)" if main_blocked else "[차단 안 됨 — 메인이 삭제됨?]"), sc=4,
                  repro="1. 수정 모달\n2. 첫(메인 *) 항목 X 클릭\n3. '메인 드라이브는 삭제 할 수 없습니다' 차단")
        # (2) 비-메인 항목 추가 후 삭제 → 즉시 제거
        before = len(page.secure_drive_rows())
        page.add_secure_drive("del2", "R", "D:\\del2_m", "WRITE", "100")
        mid = len(page.secure_drive_rows())
        msg_non = page.delete_secure_drive_row(1)
        after = len(page.secure_drive_rows())
        removed = (mid == before + 1) and (after == before) and (msg_non is None)
        self._add("pass" if removed else "fail",
                  "sc4n — 비-메인 항목 삭제(즉시 제거)",
                  f"입력: 2번째(비메인) 추가({before}→{mid}) 후 삭제 / 결과: {after}건, 경고={msg_non!r} "
                  + ("(확인 없이 즉시 제거)" if removed else "[제거 실패/예상외]"), sc=4,
                  repro="1. 비메인 항목 추가\n2. 그 항목 X 클릭\n3. 확인 없이 즉시 제거")
        page._close_modal_if_open()

