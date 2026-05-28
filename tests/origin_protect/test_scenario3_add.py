"""원본보호 정책 — 시나리오 3: ADD 동작 검증.

yaml 사실 그대로 1:1 assert (추정 0):
  sc3a 필수 빈값 메시지 5건 (α/β1/β2/β3/γ) + 발화순서 1순위(δ=α)
  sc3b 정책 이름 중복 차단 메시지
  sc3c driveLetter 형식 — alert + value reset
  sc3d 확장자 list (중복/형식/빈값/다중구분자)
  sc3e 예외폴더 list (중복/형식 없음/빈값 typo 결함 — warn)
  sc3f 워터마크 토큰 ([/PCINFO/]·[/TIME/]) — 자동 삽입/제거 + 저장/재오픈 sync
  sc3g 정상 저장 + CSU picker (KEEP 활용)

⚠ 모든 모달 버튼 클릭은 qa-block-overlay 우회 위해 evaluate("el=>el.click()") 사용
   (sc1c 함정 이후 패턴 적용).
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase


# CSU picker 단축 헬퍼 — radio 첫 행 선택 + 확인
def _csu_select_first(page):
    page.page.locator(page.SEL_CSU_SELECT_BTN).first.evaluate("el => el.click()")
    page.page.wait_for_timeout(1200)
    page.page.locator(
        "#selectCommonPolicyItemModal input[type='radio'][name='selectTemplate']"
    ).first.evaluate("el => el.click()")
    page.page.wait_for_timeout(300)
    page.page.locator("#selectCommonPolicyItemModal .btn-primary").first.evaluate("el => el.click()")
    page.page.wait_for_timeout(1200)


def _csu_search_and_select(page, keyword):
    """CSU picker 검색 input 에 keyword 입력 + 첫 매칭 radio 선택."""
    page.page.locator(page.SEL_CSU_SELECT_BTN).first.evaluate("el => el.click()")
    page.page.wait_for_timeout(1200)
    si = page.page.locator("#selectCommonPolicyItemModal input#searchText").first
    si.fill(keyword)
    page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate("el => el.click()")
    page.page.wait_for_timeout(800)
    radios = page.page.locator("#selectCommonPolicyItemModal input[type='radio'][name='selectTemplate']")
    if radios.count() > 0:
        radios.first.evaluate("el => el.click()")
        page.page.wait_for_timeout(300)
    page.page.locator("#selectCommonPolicyItemModal .btn-primary").first.evaluate("el => el.click()")
    page.page.wait_for_timeout(1200)


def _save_click(page):
    """ADD 모달 저장 버튼 클릭 (overlay 우회)."""
    page.page.locator(page.SEL_SUBMIT_BTN).first.evaluate("el => el.click()")
    page.page.wait_for_timeout(1500)


class TestOriginProtectScenario3Add(OriginProtectBase):
    """원본보호 정책 — sc3: ADD 동작 검증."""

    # ==================================================================
    # sc3a — 필수 빈값 메시지 5건 (α/β1/β2/β3/γ) + 발화순서 1순위 (δ=α)
    # ==================================================================
    def test_scenario3a_required_empty_messages(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3a: 필수 빈값 메시지 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        def _fill(name=None, drvL=None, drvLb=None, quota=None, csu=False):
            if name:  page.page.locator(page.SEL_POLICY_NAME).fill(name)
            if drvL:  page.page.locator(page.SEL_DRIVE_LETTER).fill(drvL)
            if drvLb: page.page.locator(page.SEL_DRIVE_LABEL).fill(drvLb)
            if quota: page.page.locator(page.SEL_DRIVE_QUOTA).fill(quota)
            if csu:   _csu_select_first(page)

        cases = [
            ("α",  "정책 이름 빈값",
             dict(drvL="Z", drvLb="L", quota="100", csu=True),
             "정책 이름을 입력해 주세요."),
            ("β1", "driveLetter 빈값",
             dict(name="[AUTO]_probe_b1", drvLb="L", quota="100", csu=True),
             "드라이브 문자를 입력해 주세요."),
            ("β2", "driveLabel 빈값",
             dict(name="[AUTO]_probe_b2", drvL="Z", quota="100", csu=True),
             "드라이브 라벨을 입력해 주세요."),
            ("β3", "Quota 빈값",
             dict(name="[AUTO]_probe_b3", drvL="Z", drvLb="L", csu=True),
             "원본보호 드라이브 용량을 입력해 주세요."),
            ("γ",  "CSU 미선택",
             dict(name="[AUTO]_probe_g", drvL="Z", drvLb="L", quota="100", csu=False),
             "제어 스위트를 선택해 주세요."),
        ]
        for case_id, label, fill_args, expected in cases:
            page.open_add_modal()
            _fill(**fill_args)
            _save_click(page)
            if page.is_confirm_modal_visible(timeout=1500):
                msg = page.get_confirm_message()
                ok = msg == expected
                self._add("pass" if ok else "fail",
                          f"sc3a {case_id} — '{label}' 차단 메시지",
                          f"입력: {fill_args} / 결과: msg={msg!r} (기대 {expected!r})", sc=3)
                page.dismiss_confirm_modal()
            else:
                self._add("fail", f"sc3a {case_id} — '{label}' 메시지 미노출",
                          f"입력: {fill_args} / 결과: 알림 없음 (기대 {expected!r})", sc=3)
            page.close_modal()

        # δ — 다 빈 → α 와 동일 메시지 → 발화 1순위 = 정책 이름
        page.open_add_modal()
        _save_click(page)
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            ok = msg == "정책 이름을 입력해 주세요."
            self._add("pass" if ok else "fail",
                      "sc3a δ — 다 빈 → 발화 1순위 = 정책 이름",
                      f"입력: 모든 필드 빈 / 결과: msg={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3a δ — 다 빈 → 메시지 미노출",
                      "결과: 알림 없음", sc=3)
        page.close_modal()

    # ==================================================================
    # sc3b — 정책 이름 중복 차단 메시지 (control_suite 와 다른 텍스트)
    # ==================================================================
    def test_scenario3b_name_duplicate(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3b: 이름 중복 차단 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = "[AUTO]_sc3b_dup"
        # 1차 — 사전 정책 저장 (self-contained)
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Z")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("L")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        _csu_select_first(page)
        _save_click(page)
        if page.is_confirm_modal_visible():
            page.dismiss_confirm_modal()

        # 2차 — 같은 이름으로 다시 저장 → 차단 메시지
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Z")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("L")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        _csu_select_first(page)
        _save_click(page)
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            expected = "정책 이름이 이미 등록되어 있습니다."
            ok = msg == expected
            self._add("pass" if ok else "fail",
                      "sc3b — 정책 이름 중복 차단 메시지",
                      f"입력: 동일 '{NAME}' 재저장 / 결과: msg={msg!r} (기대 {expected!r})", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3b — 이름 중복 메시지 미노출",
                      f"입력: 동일 '{NAME}' / 결과: 알림 없음", sc=3)
        page.close_modal()

    # ==================================================================
    # sc3c — driveLetter 형식 검증 (alert + value reset 동시)
    # ==================================================================
    def test_scenario3c_drive_letter_format(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3c: driveLetter 형식 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        dl = page.page.locator(page.SEL_DRIVE_LETTER)
        expected_invalid_msg = "드라이브 문자는 영문자만 입력할 수 있습니다."

        # invalid 입력 — 숫자/한글/특수 각각 → alert + value reset
        invalid_cases = [
            ("숫자 1", "1"),
            ("한글 가", "가"),
            ("특수 @", "@"),
        ]
        for label, val in invalid_cases:
            dl.fill(val)
            page.page.wait_for_timeout(500)
            if page.is_confirm_modal_visible(timeout=1500):
                msg = page.get_confirm_message()
                after_value = dl.input_value()
                ok = msg == expected_invalid_msg and after_value == ""
                self._add("pass" if ok else "fail",
                          f"sc3c — driveLetter invalid '{label}' alert + value reset",
                          f"입력: {val!r} / 결과: msg={msg!r}, value_after={after_value!r}", sc=3)
                page.dismiss_confirm_modal()
            else:
                self._add("fail", f"sc3c — driveLetter '{label}' 메시지 미노출",
                          f"입력: {val!r} / 결과: 알림 없음", sc=3)

        # valid 입력 — 대문자 Z / 소문자 z(→Z 변환)
        valid_cases = [
            ("대문자 Z", "Z", "Z"),
            ("소문자 z", "z", "Z"),
        ]
        for label, inp, expected_val in valid_cases:
            dl.fill(inp)
            page.page.wait_for_timeout(300)
            actual = dl.input_value()
            self._add("pass" if actual == expected_val else "fail",
                      f"sc3c — driveLetter valid '{label}' (대문자 변환)",
                      f"입력: {inp!r} / 결과: value={actual!r} (기대 {expected_val!r})", sc=3)

        page.close_modal()

    # ==================================================================
    # sc3d — 확장자 list (중복 / 형식 / 빈값 / 다중구분자)
    # ==================================================================
    def test_scenario3d_extension_list_validation(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3d: 확장자 list 검증 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        ext_inp = page.page.locator(page.SEL_WATCH_EXT_INPUT)
        add_btn = page.page.locator(page.SEL_WATCH_EXT_BTN)

        def _add_ext(val):
            ext_inp.fill(val)
            page.page.wait_for_timeout(150)
            add_btn.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(500)

        # 1) 다중 구분자 'asd;sdf;dfg' → 3건 일괄 등록 (알림 없음)
        _add_ext("asd;sdf;dfg")
        tags = page.page.locator("div#addItemModal button.tagInput").all_inner_texts()
        added = [t.strip().split()[0] for t in tags if t.strip()]
        ok_multi = "asd" in added and "sdf" in added and "dfg" in added
        self._add("pass" if ok_multi else "fail",
                  "sc3d — 확장자 다중구분자 'asd;sdf;dfg' 3건 일괄 등록",
                  f"입력: 'asd;sdf;dfg' / 결과: list={added}", sc=3)

        # 2) 중복 'asd' 재추가 → '이미 동일한 확장자가 존재합니다.'
        _add_ext("asd")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            expected = "이미 동일한 확장자가 존재합니다."
            ok = msg == expected
            self._add("pass" if ok else "fail",
                      "sc3d — 확장자 중복 차단 메시지",
                      f"입력: 'asd' 재추가 / 결과: msg={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3d — 확장자 중복 메시지 미노출", "결과: 알림 없음", sc=3)

        # 3) 형식 '$@%' → ". * ; ? 이외의 특수문자 또는 한글이 포함된 확장자는 제외합니다."
        _add_ext("$@%")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            expected = ". * ; ? 이외의 특수문자 또는 한글이 포함된 확장자는 제외합니다."
            ok = msg == expected
            self._add("pass" if ok else "fail",
                      "sc3d — 확장자 형식(특수문자) 차단 메시지",
                      f"입력: '$@%' / 결과: msg={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3d — 확장자 형식 메시지 미노출", "결과: 알림 없음", sc=3)

        # 4) 빈값 '' + 추가 → '확장자를 입력하세요'
        _add_ext("")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            expected = "확장자를 입력하세요"
            ok = msg == expected
            self._add("pass" if ok else "fail",
                      "sc3d — 확장자 빈값 차단 메시지",
                      f"입력: '' / 결과: msg={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3d — 확장자 빈값 메시지 미노출", "결과: 알림 없음", sc=3)

        page.close_modal()

    # ==================================================================
    # sc3e — 예외 폴더 list (중복 / 형식 없음(free text) / 빈값 typo 결함)
    # ==================================================================
    def test_scenario3e_except_folder_list_validation(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3e: 예외폴더 list 검증 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        inp = page.page.locator(page.SEL_WATCH_EXCEPT_INPUT)
        add_btn = page.page.locator(page.SEL_WATCH_EXCEPT_BTN)

        def _add_folder(val):
            inp.fill(val)
            page.page.wait_for_timeout(150)
            add_btn.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(500)

        # 1) 정상 폴더 'C:\\Temp' → 등록
        _add_folder("C:\\Temp")
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()

        # 2) 중복 → '이미 등록된 폴더 경로가 존재합니다.'
        _add_folder("C:\\Temp")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            expected = "이미 등록된 폴더 경로가 존재합니다."
            ok = msg == expected
            self._add("pass" if ok else "fail",
                      "sc3e — 예외폴더 중복 차단 메시지",
                      f"입력: 동일 'C:\\Temp' / 결과: msg={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3e — 예외폴더 중복 메시지 미노출", "결과: 알림 없음", sc=3)

        # 3) 형식 검증 없음 — '$@%' 그대로 등록 (free text)
        _add_folder("$@%")
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()
            self._add("warn", "sc3e — 예외폴더 형식 '$@%' 알림? (yaml 기대: 검증 없음)",
                      "결과: 알림 노출 — yaml '형식 없음' 사실과 불일치", sc=3)
        else:
            self._add("pass", "sc3e — 예외폴더 형식 '$@%' 알림 없음 (free text 확인)",
                      "결과: 알림 없음 (yaml: 검증 없음)", sc=3)

        # 4) 빈값 → 'typo 결함' — 메시지가 "확장자를 입력하세요" 잘못 노출
        _add_folder("")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            is_typo = msg == "확장자를 입력하세요"   # ⚠ yaml known_bug
            self._add("warn" if is_typo else "fail",
                      "sc3e — [메시지 일관성 결함] 예외폴더 빈값 → '확장자를 입력하세요' (영역 ≠ 메시지)",
                      f"입력: '' / 결과: msg={msg!r} (yaml known_bug:watch_except_folder_empty_wrong_message)", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3e — 예외폴더 빈값 메시지 미노출", "결과: 알림 없음", sc=3)

        page.close_modal()

    # ==================================================================
    # sc3f — 워터마크 토큰 [/PCINFO/]·[/TIME/] 자동 삽입/제거 + 단방향 sync 결함
    # ==================================================================
    def test_scenario3f_watermark_token_behavior(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3f: 워터마크 토큰 동작 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        wm = page.page.locator(page.SEL_SCREEN_WM_TEXT)
        pc = page.page.locator(page.SEL_SCREEN_WM_PC_INFO)
        tm = page.page.locator(page.SEL_SCREEN_WM_TIME)

        def _click_cb(loc):
            loc.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(400)

        # 1) 초기 text 빈값
        self._add("pass" if wm.input_value() == "" else "fail",
                  "sc3f — 초기 워터마크 text 빈값", f"결과: value={wm.input_value()!r}", sc=3)

        # 2) PC 체크 → text="[/PCINFO/]"
        _click_cb(pc)
        v1 = wm.input_value()
        self._add("pass" if v1 == "[/PCINFO/]" else "fail",
                  "sc3f — PC 정보 체크 → '[/PCINFO/]' 자동 삽입",
                  f"결과: value={v1!r}", sc=3)

        # 3) 시각 추가 체크 → text="[/PCINFO/][/TIME/]"
        _click_cb(tm)
        v2 = wm.input_value()
        self._add("pass" if v2 == "[/PCINFO/][/TIME/]" else "fail",
                  "sc3f — 현재 시각 추가 체크 → '[/PCINFO/][/TIME/]'",
                  f"결과: value={v2!r}", sc=3)

        # 4) PC 해제 → text="[/TIME/]" (해당 토큰만 제거)
        _click_cb(pc)
        v3 = wm.input_value()
        self._add("pass" if v3 == "[/TIME/]" else "fail",
                  "sc3f — PC 해제 → '[/TIME/]' (해당 토큰만 제거)",
                  f"결과: value={v3!r}", sc=3)

        # 5) 시각 해제 → text=""
        _click_cb(tm)
        v4 = wm.input_value()
        self._add("pass" if v4 == "" else "fail",
                  "sc3f — 모두 해제 → text 빈값",
                  f"결과: value={v4!r}", sc=3)

        # 6) 수동 입력 'ABC' + PC 체크 → 'ABC[/PCINFO/]' (수동 텍스트 보존)
        wm.fill("ABC")
        page.page.wait_for_timeout(200)
        _click_cb(pc)
        v5 = wm.input_value()
        self._add("pass" if v5 == "ABC[/PCINFO/]" else "fail",
                  "sc3f — 수동 'ABC' + PC 체크 → 'ABC[/PCINFO/]' (수동 보존)",
                  f"결과: value={v5!r}", sc=3)

        # 7) 단방향 sync 결함 — text 의 토큰 수동 삭제 → 체크박스는 ON 그대로
        wm.fill("")
        page.page.wait_for_timeout(400)
        pc_after = pc.is_checked()
        self._add("warn" if pc_after is True else "fail",
                  "sc3f — [단방향 sync 결함] text 수동 삭제해도 체크박스 ON 유지",
                  f"입력: text='' (수동) / 결과: pc.checked={pc_after} (기대 known_bug 재현: True)", sc=3)

        # 정리 — 체크박스 해제
        if pc_after:
            _click_cb(pc)

        page.close_modal()

    # ==================================================================
    # sc3g — 정상 저장 + CSU picker (KEEP 검색 → 첫행 fallback)
    # ==================================================================
    def test_scenario3g_normal_save_with_csu(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3g: 정상 저장 + CSU picker ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = "[AUTO]_sc3g_normal_save"
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Y")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("Sc3gLabel")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("200")

        # CSU picker — [AUTO_KEEP]_sc5_step1 검색 시도, 없으면 첫 행 fallback
        try:
            _csu_search_and_select(page, "[AUTO_KEEP]_sc5_step1")
        except Exception:
            # picker 미열림 또는 검색 실패 — 다시 첫 행 시도
            try:
                _csu_select_first(page)
            except Exception:
                pass
        csu_bound_len = len(page.page.locator(page.SEL_CSU_ID_SPAN).inner_text().strip())
        self._add("pass" if csu_bound_len > 0 else "fail",
                  "sc3g — CSU picker 선택 → controlSuiteId span 바인딩",
                  f"결과: csuId len={csu_bound_len}", sc=3)

        # 저장
        _save_click(page)
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            ok = "저장" in msg and ("하였습니다" in msg or "완료" in msg or msg.endswith("."))
            self._add("pass" if ok else "fail",
                      "sc3g — 정상 저장 메시지",
                      f"입력: 필수 다 채움 + CSU 선택 / 결과: msg={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3g — 정상 저장 메시지 미노출", "결과: 알림 없음", sc=3)

        # 정책 list 에 추가됐는지
        page.navigate_to()
        added = page.is_policy_exists(NAME)
        self._add("pass" if added else "fail",
                  "sc3g — 새 정책 list 등록 확인",
                  f"입력: '{NAME}' / 결과: exists={added}", sc=3)

    # ==================================================================
    # sc3h — Quota 마스킹 (숫자만 / 음수·소수점 제거 / 13자리 OK / leading zero 제거)
    # yaml numeric_input_masking.originProtectDriveQuota (control_suite uploadLimit '1.5→0' 과 다름)
    # ==================================================================
    def test_scenario3h_quota_masking(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3h: Quota 마스킹 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        quota = page.page.locator(page.SEL_DRIVE_QUOTA)

        def _try(v):
            quota.fill("")
            page.page.wait_for_timeout(80)
            quota.evaluate(f"(el, v) => {{ el.value = v; el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}})); }}", v)
            page.page.wait_for_timeout(250)
            return quota.input_value()

        cases = [
            ("abc",            "",              "문자 전부 제거"),
            ("-5",             "5",             "음수 부호 제거"),
            ("1.5",            "15",            "소수점 제거 — 숫자만 (control_suite uploadLimit '1.5→0' 과 다름)"),
            ("12ab34",         "1234",          "문자만 제거"),
            ("0100",           "100",           "leading zero 제거"),
            ("999999999999",   "999999999999",  "12자리 그대로"),
            ("9999999999999",  "9999999999999", "13자리도 그대로 (DOM 길이 제한 없음)"),
        ]
        for inp, expected, note in cases:
            actual = _try(inp)
            ok = actual == expected
            self._add("pass" if ok else "fail",
                      f"sc3h — Quota '{inp}' → '{expected}' ({note})",
                      f"입력: {inp!r} / 결과: value={actual!r} (기대 {expected!r})", sc=3)

        # maxlength=null + alert 없음 확인
        ml = quota.get_attribute("maxlength")
        self._add("pass" if ml is None else "fail",
                  "sc3h — Quota maxlength=null (DOM 제한 없음, 서버 측 검증)",
                  f"결과: maxlength={ml!r}", sc=3)
        gm = page.is_confirm_modal_visible(timeout=500)
        self._add("pass" if not gm else "fail",
                  "sc3h — Quota 마스킹은 silent (alert 없음)",
                  f"결과: gm={gm}", sc=3)
        if gm:
            page.dismiss_confirm_modal()
        page.close_modal()

    # ==================================================================
    # sc3i — 워터마크 투명도(0~100 cap) / 각도(0~360 cap) 마스킹
    # ==================================================================
    def test_scenario3i_watermark_opacity_degree_cap(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3i: 워터마크 투명도/각도 cap ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        op = page.page.locator(page.SEL_SCREEN_WM_OPACITY)
        dg = page.page.locator(page.SEL_SCREEN_WM_DEGREE)

        def _try(loc, v):
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.evaluate(f"(el, v) => {{ el.value = v; el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}})); }}", v)
            page.page.wait_for_timeout(250)
            return loc.input_value()

        # 투명도 0~100 cap
        op_cases = [
            ("abc", "",    "문자 제거"),
            ("-50", "50",  "음수 부호 제거"),
            ("50",  "50",  "정상"),
            ("150", "100", "100 초과 → 100 cap"),
        ]
        for inp, expected, note in op_cases:
            actual = _try(op, inp)
            ok = actual == expected
            self._add("pass" if ok else "fail",
                      f"sc3i — 투명도 '{inp}' → '{expected}' ({note})",
                      f"입력: {inp!r} / 결과: value={actual!r}", sc=3)

        # 각도 0~360 cap
        dg_cases = [
            ("abc", "",    "문자 제거"),
            ("-90", "90",  "음수 부호 제거"),
            ("360", "360", "정상 최대"),
            ("361", "360", "361 → 360 cap"),
            ("720", "360", "720 → 360 cap"),
        ]
        for inp, expected, note in dg_cases:
            actual = _try(dg, inp)
            ok = actual == expected
            self._add("pass" if ok else "fail",
                      f"sc3i — 각도 '{inp}' → '{expected}' ({note})",
                      f"입력: {inp!r} / 결과: value={actual!r}", sc=3)

        page.close_modal()

    # ==================================================================
    # sc3j — free text input (driveLabel / 종료 알림 textarea) — 한글/특수/긴 입력 허용
    # yaml free_text_inputs
    # ==================================================================
    def test_scenario3j_free_text_inputs(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3j: free text inputs ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        # driveLabel — 한글/특수/숫자/200자 모두 OK
        lb = page.page.locator(page.SEL_DRIVE_LABEL)
        for inp, label in [("한글라벨", "한글"), ("$@%", "특수문자"), ("123", "숫자"), ("a"*200, "200자")]:
            lb.fill(inp)
            page.page.wait_for_timeout(150)
            actual = lb.input_value()
            ok = actual == inp
            self._add("pass" if ok else "fail",
                      f"sc3j — driveLabel '{label}' 그대로 등록 (free text)",
                      f"입력: '{inp[:20]}...'({len(inp)}자) / 결과: 보존={ok}", sc=3)

        # 종료 알림 textarea — 한글 OK / 500자 OK / maxlength=null
        sh = page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT)
        sh.fill("한글종료알림")
        page.page.wait_for_timeout(150)
        self._add("pass" if sh.input_value() == "한글종료알림" else "fail",
                  "sc3j — 종료 알림 textarea 한글 입력 (free text)",
                  f"결과: 보존={sh.input_value() == '한글종료알림'}", sc=3)
        sh.fill("a"*500)
        page.page.wait_for_timeout(150)
        self._add("pass" if len(sh.input_value()) == 500 else "fail",
                  "sc3j — 종료 알림 textarea 500자 OK (maxlength 없음)",
                  f"결과: len={len(sh.input_value())}", sc=3)
        ml = sh.get_attribute("maxlength")
        self._add("pass" if ml is None else "fail",
                  "sc3j — 종료 알림 textarea maxlength=null",
                  f"결과: maxlength={ml!r}", sc=3)

        # 알림 미노출 (silent)
        gm = page.is_confirm_modal_visible(timeout=500)
        self._add("pass" if not gm else "fail",
                  "sc3j — free text inputs alert 없음 (silent)",
                  f"결과: gm={gm}", sc=3)
        if gm:
            page.dismiss_confirm_modal()
        page.close_modal()

    # ==================================================================
    # sc3k — 워터마크 저장+재오픈 sync 복구 (text 우선, 체크박스 재계산)
    # yaml watermark_token_auto_insert.save_and_reopen_sync
    # ==================================================================
    def test_scenario3k_watermark_save_reopen_sync(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3k: 워터마크 저장+재오픈 sync 복구 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = "[AUTO]_sc3k_wm_sync"
        # 1) ADD: 필수 채움 + PC/Time 체크 → text='[/PCINFO/][/TIME/]' → 수동으로 text=''
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME)
        page.page.locator(page.SEL_DRIVE_LETTER).fill("X")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("SyncLabel")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        _csu_select_first(page)
        page.page.locator(page.SEL_SCREEN_WM_PC_INFO).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(400)
        page.page.locator(page.SEL_SCREEN_WM_TIME).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(400)
        before_text = page.page.locator(page.SEL_SCREEN_WM_TEXT).input_value()
        before_pc = page.page.locator(page.SEL_SCREEN_WM_PC_INFO).is_checked()
        before_time = page.page.locator(page.SEL_SCREEN_WM_TIME).is_checked()
        self._add("pass" if before_text == "[/PCINFO/][/TIME/]" and before_pc and before_time else "fail",
                  "sc3k — 저장 전: PC+Time 체크 → text='[/PCINFO/][/TIME/]'",
                  f"결과: text={before_text!r}, pc={before_pc}, time={before_time}", sc=3)

        # 수동으로 text 비움 (단방향 sync 결함 — 체크박스 그대로 ON)
        page.page.locator(page.SEL_SCREEN_WM_TEXT).fill("")
        page.page.wait_for_timeout(300)
        cleared_pc = page.page.locator(page.SEL_SCREEN_WM_PC_INFO).is_checked()
        self._add("warn" if cleared_pc is True else "fail",
                  "sc3k — text 수동 비움 → 체크박스 sync 안 됨 (단방향 결함, known_bug)",
                  f"결과: text='', pc.checked={cleared_pc} (기대: True 재현)", sc=3)

        # 저장
        _save_click(page)
        if page.is_confirm_modal_visible():
            page.dismiss_confirm_modal()

        # 2) EDIT 재진입 — 정책 검색 + 행 선택 (td mousedown 시퀀스)
        page.navigate_to()
        search = page.page.locator(page.SEL_SEARCH_INPUT)
        search.fill(NAME)
        page.page.locator("button#searchBtn").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(1500)
        row = page.page.locator("table tbody tr").first
        td = row.locator("td").first
        td.evaluate("""el => {
          ['mousedown','mouseup','click'].forEach(ev =>
            el.dispatchEvent(new MouseEvent(ev, {bubbles:true,cancelable:true,view:window,button:0}))
          );
        }""")
        page.page.wait_for_timeout(500)
        page.page.locator("button#modifyItemBtn").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(1500)

        # 3) EDIT 재진입 상태 확인 — text 우선 (text='') / 체크박스 재계산 (false)
        if not page.page.locator(page.SEL_MODAL_OPEN).count():
            self._add("fail", "sc3k — EDIT 모달 미진입", "결과: 모달 열림 실패", sc=3)
            return
        reopen_text = page.page.locator(page.SEL_SCREEN_WM_TEXT).input_value()
        reopen_pc = page.page.locator(page.SEL_SCREEN_WM_PC_INFO).is_checked()
        reopen_time = page.page.locator(page.SEL_SCREEN_WM_TIME).is_checked()
        wm_toggle = page.page.locator(page.SEL_SCREEN_WM).is_checked()
        self._add("pass" if reopen_text == "" else "fail",
                  "sc3k — 저장 후 EDIT 재진입: text 빈값 보존 (저장 시 text 우선)",
                  f"결과: text={reopen_text!r}", sc=3)
        self._add("pass" if reopen_pc is False and reopen_time is False else "fail",
                  "sc3k — 저장 후 EDIT 재진입: PC/Time 체크박스 재계산 (False) — 단방향 sync 자동 복구",
                  f"결과: pc={reopen_pc}, time={reopen_time}", sc=3)
        self._add("pass" if wm_toggle is True else "fail",
                  "sc3k — 저장 후 EDIT 재진입: 워터마크 토글 자체는 독립 — ON 유지",
                  f"결과: wm_toggle={wm_toggle}", sc=3)

        page.close_modal()

    # ==================================================================
    # sc3l — driveLetter 같은 값 정책 2건 공존 가능 (도메인 의도 — 결함 아님)
    # yaml domain_behaviors.drive_letter_duplication
    # ==================================================================
    def test_scenario3l_drive_letter_can_duplicate(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3l: driveLetter 같은 값 정책 2건 공존 (도메인) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        SAME_LETTER = "Y"
        NAME1 = "[AUTO]_sc3l_letter_first"
        NAME2 = "[AUTO]_sc3l_letter_second"

        # 1차 정책 저장
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME1)
        page.page.locator(page.SEL_DRIVE_LETTER).fill(SAME_LETTER)
        page.page.locator(page.SEL_DRIVE_LABEL).fill("First")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        _csu_select_first(page)
        _save_click(page)
        if page.is_confirm_modal_visible():
            page.dismiss_confirm_modal()

        # 2차 정책 — 같은 letter 사용, 다른 이름
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME2)
        page.page.locator(page.SEL_DRIVE_LETTER).fill(SAME_LETTER)
        page.page.locator(page.SEL_DRIVE_LABEL).fill("Second")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        _csu_select_first(page)
        _save_click(page)
        save_ok = False
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            save_ok = "저장" in msg and "오류" not in msg
            page.dismiss_confirm_modal()
        modal_closed = not page.page.locator(page.SEL_MODAL_OPEN).count()

        # 결과 — 2건 다 등록됐는지
        page.navigate_to()
        first_exists = page.is_policy_exists(NAME1)
        second_exists = page.is_policy_exists(NAME2)
        both_ok = first_exists and second_exists
        self._add("pass" if both_ok else "fail",
                  "sc3l — driveLetter='Y' 정책 2건 공존 (도메인 의도 — 충돌 검증 안 함)",
                  f"입력: 같은 letter+다른 이름 / 결과: 1차={first_exists}, 2차={second_exists}, 저장ok={save_ok}, modal닫힘={modal_closed}", sc=3)
