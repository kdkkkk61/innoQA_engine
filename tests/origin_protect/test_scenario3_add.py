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
def _csu_select_first(page, prefer_keyword="AUTO"):
    """CSU picker 선택 — AUTO 검색 → 매칭 첫 행 / 없으면 전체 list 첫 행 (사용자 정책 2026-05-29).

    동작:
      1. picker 열기
      2. prefer_keyword ("AUTO" default) 검색 → KEEP 정책 우선 매칭
      3. radio 있는 row 0건 시 검색 reset → 전체 list 첫 행 fallback
      4. 첫 행 raw JS click (ng-click directive 발화 → radio.checked + ng-model 동기화)
      5. 확인 버튼 click

    호출부 변경 없이 정책 적용 — 모든 _csu_select_first(page) 가 자동으로
    AUTO 검색 → KEEP 우선 / 없으면 첫 행 fallback.
    """
    page.page.locator(page.SEL_CSU_SELECT_BTN).first.evaluate("el => el.click()")
    page.page.locator("#selectCommonPolicyItemModal.in").wait_for(
        state="attached", timeout=5000
    )
    # AUTO 검색 시도 — KEEP 정책 매칭
    try:
        si = page.page.locator("#selectCommonPolicyItemModal input#searchText").first
        si.fill(prefer_keyword)
        page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate(
            "el => el.click()"
        )
        page.page.wait_for_timeout(800)
    except Exception:
        pass
    # radio 있는 row 0건 시 검색 reset
    radios = page.page.locator(
        "#selectCommonPolicyItemModal input[type='radio'][name='selectTemplate']"
    )
    if radios.count() == 0:
        try:
            si.fill("")
            page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate(
                "el => el.click()"
            )
            page.page.wait_for_timeout(800)
        except Exception:
            pass
    # 첫 행 (tr) raw JS click — ng-click directive 발화
    page.page.locator("#selectCommonPolicyItemModal table tbody tr").first.evaluate(
        "el => el.click()"
    )
    page.page.wait_for_timeout(500)
    page.page.locator("#selectCommonPolicyItemModal .btn-primary").first.evaluate(
        "el => el.click()"
    )
    page.page.wait_for_timeout(1500)


def _csu_search_and_select(page, keyword):
    """CSU picker 검색 + 첫 매칭 선택. 검색 0건 (message row 포함) 시 검색 reset.

    사용자 보고 2026-05-29: AngularJS picker 가 검색 결과 0건일 때 "검색된 내용이
    없습니다." message row 표시 → tbody.tr.count() 가 1 이지만 radio 없음 → fallback
    skip → message row click → controlSuiteId 미설정 → 저장 시 차단.
    수정: radio 있는 row 만 count (radios locator 사용).
    """
    page.page.locator(page.SEL_CSU_SELECT_BTN).first.evaluate("el => el.click()")
    page.page.locator("#selectCommonPolicyItemModal.in").wait_for(
        state="attached", timeout=5000
    )
    si = page.page.locator("#selectCommonPolicyItemModal input#searchText").first
    si.fill(keyword)
    page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate("el => el.click()")
    page.page.wait_for_timeout(800)
    # radio 있는 row 만 count — message row ("검색된 내용이 없습니다.") 제외
    radios = page.page.locator(
        "#selectCommonPolicyItemModal input[type='radio'][name='selectTemplate']"
    )
    if radios.count() == 0:
        # 검색 결과 0건 — 검색 reset + 전체 list 첫 행 fallback
        si.fill("")
        page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(800)
    # radio 있는 tr 중 첫 행 click — AngularJS ng-click 핸들러 발화
    valid_rows = page.page.locator(
        "#selectCommonPolicyItemModal table tbody tr:has(input[type='radio'][name='selectTemplate'])"
    )
    if valid_rows.count() > 0:
        valid_rows.first.evaluate("el => el.click()")
        page.page.wait_for_timeout(300)
    page.page.locator("#selectCommonPolicyItemModal .btn-primary").first.evaluate("el => el.click()")
    page.page.wait_for_timeout(1500)


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
                      "sc3e — [예외 폴더] 중복 차단 메시지",
                      f"입력: 동일 'C:\\Temp' / 결과: msg={msg!r}", sc=3, highlight=inp)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3e — [예외 폴더] 중복 메시지 미노출", "결과: 알림 없음", sc=3,
                      highlight=inp)

        # 3) 형식 검증 없음 — '$@%' 그대로 등록 (free text)
        _add_folder("$@%")
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()
            self._add("warn", "sc3e — [예외 폴더] 형식 '$@%' 알림? (yaml 기대: 검증 없음)",
                      "결과: 알림 노출 — yaml '형식 없음' 사실과 불일치", sc=3, highlight=inp)
        else:
            self._add("pass", "sc3e — [예외 폴더] 형식 '$@%' 알림 없음 (free text 확인)",
                      "결과: 알림 없음 (yaml: 검증 없음)", sc=3)

        # 4) 빈값 → 'typo 결함' — 메시지가 "확장자를 입력하세요" 잘못 노출
        _add_folder("")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            is_typo = msg == "확장자를 입력하세요"   # ⚠ yaml known_bug
            self._add("warn" if is_typo else "fail",
                      "sc3e — [예외 폴더] [메시지 일관성 결함] 빈값 → '확장자를 입력하세요' (영역 ≠ 메시지)",
                      f"입력: '' / 결과: msg={msg!r} (yaml known_bug:watch_except_folder_empty_wrong_message)",
                      sc=3, highlight=inp)
            page.dismiss_confirm_modal()
        else:
            self._add("fail", "sc3e — [예외 폴더] 빈값 메시지 미노출", "결과: 알림 없음", sc=3,
                      highlight=inp)

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
                  "sc3f — [화면 워터마크] 초기 워터마크 text 빈값",
                  f"결과: value={wm.input_value()!r}", sc=3, highlight=wm)

        # 2) PC 체크 → text="[/PCINFO/]"
        _click_cb(pc)
        v1 = wm.input_value()
        self._add("pass" if v1 == "[/PCINFO/]" else "fail",
                  "sc3f — [화면 워터마크] PC 정보 체크 → '[/PCINFO/]' 자동 삽입",
                  f"결과: value={v1!r}", sc=3, highlight=wm)

        # 3) 시각 추가 체크 → text="[/PCINFO/][/TIME/]"
        _click_cb(tm)
        v2 = wm.input_value()
        self._add("pass" if v2 == "[/PCINFO/][/TIME/]" else "fail",
                  "sc3f — [화면 워터마크] 현재 시각 추가 체크 → '[/PCINFO/][/TIME/]'",
                  f"결과: value={v2!r}", sc=3, highlight=wm)

        # 4) PC 해제 → text="[/TIME/]" (해당 토큰만 제거)
        _click_cb(pc)
        v3 = wm.input_value()
        self._add("pass" if v3 == "[/TIME/]" else "fail",
                  "sc3f — [화면 워터마크] PC 해제 → '[/TIME/]' (해당 토큰만 제거)",
                  f"결과: value={v3!r}", sc=3, highlight=wm)

        # 5) 시각 해제 → text=""
        _click_cb(tm)
        v4 = wm.input_value()
        self._add("pass" if v4 == "" else "fail",
                  "sc3f — [화면 워터마크] 모두 해제 → text 빈값",
                  f"결과: value={v4!r}", sc=3, highlight=wm)

        # 6) 수동 입력 'ABC' + PC 체크 → 'ABC[/PCINFO/]' (수동 텍스트 보존)
        wm.fill("ABC")
        page.page.wait_for_timeout(200)
        _click_cb(pc)
        v5 = wm.input_value()
        self._add("pass" if v5 == "ABC[/PCINFO/]" else "fail",
                  "sc3f — [화면 워터마크] 수동 'ABC' + PC 체크 → 'ABC[/PCINFO/]' (수동 보존)",
                  f"결과: value={v5!r}", sc=3, highlight=wm)

        # 7~8) [화면 워터마크] 단방향 sync 결함 — yaml manual_token_deletion transitions
        # 사용자 재확정 (2026-05-29) + Chrome MCP 직접 검증 (2026-05-29):
        #   state2 ([/PCINFO/] 만 수동 삭제) → text='[/TIME/]' / pc=true 유지 / time=true 유지 (결함)
        #   state3 (text 전체 비움)          → text=''         / pc=true 유지 / time=true 유지 (결함)
        # 사용자 중복 지적 (2026-05-29): "체크박스 넣고 지우고 두 번 하는 것" — state1 (PC+TIME 체크
        #   → '[/PCINFO/][/TIME/]') 검증 줄 제거. case 3 (시각 추가 체크 → '[/PCINFO/][/TIME/]') 와
        #   100% 동일 검증이라 중복. state1 은 setup 만 하고 검증 없이 진행.
        wm.fill("")
        _click_cb(pc)  # PC OFF — 초기화
        page.page.wait_for_timeout(200)
        # state1 setup만 (검증 줄 제거 — case 3 과 중복)
        _click_cb(pc)
        _click_cb(tm)
        # state2: [/PCINFO/] 만 수동 삭제 → text='[/TIME/]', pc/time 유지 (단방향 sync 결함)
        wm.fill("[/TIME/]")
        page.page.wait_for_timeout(400)
        s2_text, s2_pc, s2_time = wm.input_value(), pc.is_checked(), tm.is_checked()
        s2_defect = (s2_pc is True and s2_time is True)
        self._add("warn" if s2_defect else "pass",
                  "sc3f — [화면 워터마크] state2 결함 — '[/PCINFO/]' 만 수동 삭제 → PC/TIME 둘 다 ON 유지",
                  f"입력: text='[/TIME/]' (수동) / 결과: text={s2_text!r}, pc={s2_pc}, time={s2_time} "
                  f"(결함 재현 시 pc=time=True)",
                  sc=3, highlight=pc)
        # state3: text 전체 비움 → pc/time 둘 다 ON 유지 (단방향 sync 결함)
        wm.fill("")
        page.page.wait_for_timeout(400)
        s3_text, s3_pc, s3_time = wm.input_value(), pc.is_checked(), tm.is_checked()
        s3_defect = (s3_pc is True and s3_time is True)
        self._add("warn" if s3_defect else "pass",
                  "sc3f — [화면 워터마크] state3 결함 — text 전체 비움 → PC/TIME 둘 다 ON 유지",
                  f"입력: text='' (수동) / 결과: text={s3_text!r}, pc={s3_pc}, time={s3_time} "
                  f"(결함 재현 시 pc=time=True)",
                  sc=3, highlight=tm)

        # 정리 — 체크박스 해제
        if pc.is_checked():
            _click_cb(pc)
        if tm.is_checked():
            _click_cb(tm)

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

        # CSU picker — AUTO 검색 → KEEP 매칭 / 없으면 전체 첫 행 fallback (통합 helper)
        _csu_select_first(page, "AUTO")
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
                      f"sc3h — [드라이브 용량] '{inp}' → '{expected}' ({note})",
                      f"입력: {inp!r} / 결과: value={actual!r} (기대 {expected!r})",
                      sc=3, highlight=quota)

        # 마스킹은 silent 인지만 추가 검증 (maxlength=null 줄은 sc3n 과 중복이라 제거)
        gm = page.is_confirm_modal_visible(timeout=500)
        self._add("pass" if not gm else "fail",
                  "sc3h — [드라이브 용량] 마스킹은 silent (alert 없음)",
                  f"결과: gm={gm}", sc=3, highlight=quota)
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

        def _try(loc, v):
            loc.fill("")
            page.page.wait_for_timeout(80)
            loc.evaluate(f"(el, v) => {{ el.value = v; el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}})); }}", v)
            page.page.wait_for_timeout(250)
            return loc.input_value()

        op_cases = [
            ("abc", "",    "문자 제거"),
            ("-50", "50",  "음수 부호 제거"),
            ("50",  "50",  "정상"),
            ("150", "100", "100 초과 → 100 cap"),
        ]
        dg_cases = [
            ("abc", "",    "문자 제거"),
            ("-90", "90",  "음수 부호 제거"),
            ("360", "360", "정상 최대"),
            ("361", "360", "361 → 360 cap"),
            ("720", "360", "720 → 360 cap"),
        ]

        # 화면 워터마크 + 출력 워터마크 동일 검증 (사용자 지적 2026-05-29: "출력물 워터마크도 똑같은건데")
        targets = [
            ("화면 워터마크", page.page.locator(page.SEL_SCREEN_WM_OPACITY),
                             page.page.locator(page.SEL_SCREEN_WM_DEGREE)),
            ("출력 워터마크", page.page.locator(page.SEL_PRINT_WM_OPACITY),
                             page.page.locator(page.SEL_PRINT_WM_DEGREE)),
        ]
        for area_name, op, dg in targets:
            for inp, expected, note in op_cases:
                actual = _try(op, inp)
                ok = actual == expected
                self._add("pass" if ok else "fail",
                          f"sc3i — [{area_name}] 투명도 '{inp}' → '{expected}' ({note})",
                          f"입력: {inp!r} / 결과: value={actual!r}", sc=3, highlight=op)
            for inp, expected, note in dg_cases:
                actual = _try(dg, inp)
                ok = actual == expected
                self._add("pass" if ok else "fail",
                          f"sc3i — [{area_name}] 각도 '{inp}' → '{expected}' ({note})",
                          f"입력: {inp!r} / 결과: value={actual!r}", sc=3, highlight=dg)

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
                      f"sc3j — [드라이브 레이블] '{label}' 그대로 등록 (free text)",
                      f"입력: '{inp[:20]}...'({len(inp)}자) / 결과: 보존={ok}", sc=3)

        # 종료 알림 textarea — 한글 OK (free text 동작만)
        # 중복 제거 (사용자 지적 2026-05-29): '500자 OK / maxlength=null' 줄 제거.
        #   → sc3n 의 functional save reject 검증 + yaml full_inventory dump 가 같은 사실 cover.
        sh = page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT)
        sh.fill("한글종료알림")
        page.page.wait_for_timeout(150)
        self._add("pass" if sh.input_value() == "한글종료알림" else "fail",
                  "sc3j — [허용 프로세스 종료 시 알림] textarea 한글 입력 (free text)",
                  f"결과: 보존={sh.input_value() == '한글종료알림'}", sc=3)

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
        # 중복 제거 (사용자 지적 2026-05-29):
        #   - "저장 전 PC+Time 체크 → '[/PCINFO/][/TIME/]'" 검증 줄 제거 (sc3f case 3 과 동일)
        #   - "text 수동 비움 → 체크박스 ON 유지" 검증 줄 제거 (sc3f state3 과 동일)
        #   sc3k 는 setup 만 하고 진짜 핵심 = 저장 후 EDIT 재진입 시 text 우선 정상 동작 검증.
        assert before_text == "[/PCINFO/][/TIME/]" and before_pc and before_time, \
            f"sc3k setup precondition 실패: text={before_text!r}, pc={before_pc}, time={before_time}"

        # 수동으로 text 비움 (setup 만 — 결함 재현 검증은 sc3f state3 가 담당)
        page.page.locator(page.SEL_SCREEN_WM_TEXT).fill("")
        page.page.wait_for_timeout(300)

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
                  "sc3k — [화면 워터마크] 저장 후 EDIT 재진입: text 빈값 보존 (저장 시 text 우선)",
                  f"결과: text={reopen_text!r}", sc=3,
                  highlight=page.page.locator(page.SEL_SCREEN_WM_TEXT))
        self._add("pass" if reopen_pc is False and reopen_time is False else "fail",
                  "sc3k — [화면 워터마크] 저장 후 EDIT 재진입: PC/Time 체크박스 재계산 (False) — 저장 시 text 우선 정상 동작",
                  f"결과: pc={reopen_pc}, time={reopen_time}", sc=3,
                  highlight=page.page.locator(page.SEL_SCREEN_WM_PC_INFO))
        self._add("pass" if wm_toggle is True else "fail",
                  "sc3k — 저장 후 EDIT 재진입: 워터마크 토글 자체는 독립 — ON 유지",
                  f"결과: wm_toggle={wm_toggle}", sc=3)

        page.close_modal()
        # 검색 input 비우기 — sc3k 끝 후 검색 잔존 시 후속 메서드 (sc3l/sc4) 영향
        try:
            si = page.page.locator(page.SEL_SEARCH_INPUT)
            if si.count() > 0 and si.input_value():
                si.fill("")
                page.page.locator("button#searchBtn").first.evaluate("el => el.click()")
                page.page.wait_for_timeout(500)
        except Exception:
            pass

    # ==================================================================
    # sc3l — [드라이브 문자] 같은 letter 로 정책 2건 등록 허용 (도메인 의도)
    # 사용자 알림 (2026-05-29): "드라이브 레터는 같아도 된다, 상관이 아예 없다"
    #   → 원본보호 정책은 가상 드라이브 생성 단위. 나중에 nPouch 정책에서 1:1 매핑.
    #   → 같은 letter 라도 정책 이름만 다르면 등록 정상. 충돌 메시지 없어야 함.
    # 검증: 2차 저장 시 letter 중복으로 인한 차단 메시지/오류 없이 성공하는가
    # ==================================================================
    def test_scenario3l_drive_letter_can_duplicate(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3l: 같은 driveLetter 로 정책 2건 등록 허용 ━━━")
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
        first_msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            first_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        first_save_ok = ("저장" in first_msg) and ("오류" not in first_msg) and ("실패" not in first_msg)

        # 2차 정책 — 같은 letter 사용, 다른 이름 → 차단 없이 저장돼야 정상
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(NAME2)
        page.page.locator(page.SEL_DRIVE_LETTER).fill(SAME_LETTER)
        page.page.locator(page.SEL_DRIVE_LABEL).fill("Second")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        _csu_select_first(page)
        _save_click(page)
        second_msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            second_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        # 도메인 의도: 같은 letter 라도 letter 중복 관련 차단 메시지 없어야 함
        letter_blocked = any(k in second_msg for k in ("드라이브", "letter", "중복", "이미"))
        second_save_ok = ("저장" in second_msg) and ("오류" not in second_msg) and not letter_blocked

        ok = first_save_ok and second_save_ok
        self._add("pass" if ok else "fail",
                  "sc3l — [드라이브 문자] 같은 letter='Y' 로 정책 2건 등록 허용 (도메인 의도)",
                  f"입력: 1차 NAME='{NAME1}' / 2차 NAME='{NAME2}' (같은 letter)"
                  f" / 결과: 1차 저장 msg='{first_msg}', 2차 저장 msg='{second_msg}',"
                  f" letter 중복 차단={letter_blocked} (기대 False)", sc=3)

    # ==================================================================
    # sc3m — [출력 워터마크] 토큰 자동 삽입/제거 + 단방향 sync 결함 (sc3f 의 print 버전)
    # 사용자 지적 (2026-05-29): "출력물 워터마크는 왜 검증 안 해? 똑같은건데"
    # 화면 워터마크와 동일 패턴 — 토큰 [/PCINFO/]·[/TIME/] 자동 삽입/제거, 단방향 sync.
    # ==================================================================
    def test_scenario3m_print_watermark_token_behavior(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3m: 출력 워터마크 토큰 동작 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        wm = page.page.locator(page.SEL_PRINT_WM_TEXT)
        pc = page.page.locator(page.SEL_PRINT_WM_PC_INFO)
        tm = page.page.locator(page.SEL_PRINT_WM_TIME)

        def _click_cb(loc):
            loc.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(400)

        # 1) 초기 text 빈값
        self._add("pass" if wm.input_value() == "" else "fail",
                  "sc3m — [출력 워터마크] 초기 워터마크 text 빈값",
                  f"결과: value={wm.input_value()!r}", sc=3, highlight=wm)

        # 2) PC 체크 → text="[/PCINFO/]"
        _click_cb(pc)
        v1 = wm.input_value()
        self._add("pass" if v1 == "[/PCINFO/]" else "fail",
                  "sc3m — [출력 워터마크] PC 정보 체크 → '[/PCINFO/]' 자동 삽입",
                  f"결과: value={v1!r}", sc=3, highlight=wm)

        # 3) 시각 추가 체크 → text="[/PCINFO/][/TIME/]"
        _click_cb(tm)
        v2 = wm.input_value()
        self._add("pass" if v2 == "[/PCINFO/][/TIME/]" else "fail",
                  "sc3m — [출력 워터마크] 현재 시각 추가 체크 → '[/PCINFO/][/TIME/]'",
                  f"결과: value={v2!r}", sc=3, highlight=wm)

        # 4) PC 해제 → text="[/TIME/]"
        _click_cb(pc)
        v3 = wm.input_value()
        self._add("pass" if v3 == "[/TIME/]" else "fail",
                  "sc3m — [출력 워터마크] PC 해제 → '[/TIME/]' (해당 토큰만 제거)",
                  f"결과: value={v3!r}", sc=3, highlight=wm)

        # 5) 시각 해제 → text=""
        _click_cb(tm)
        v4 = wm.input_value()
        self._add("pass" if v4 == "" else "fail",
                  "sc3m — [출력 워터마크] 모두 해제 → text 빈값",
                  f"결과: value={v4!r}", sc=3, highlight=wm)

        # 6) 수동 'ABC' + PC → 'ABC[/PCINFO/]'
        wm.fill("ABC")
        page.page.wait_for_timeout(200)
        _click_cb(pc)
        v5 = wm.input_value()
        self._add("pass" if v5 == "ABC[/PCINFO/]" else "fail",
                  "sc3m — [출력 워터마크] 수동 'ABC' + PC 체크 → 'ABC[/PCINFO/]' (수동 보존)",
                  f"결과: value={v5!r}", sc=3, highlight=wm)

        # 7~8) [출력 워터마크] 단방향 sync 결함 — Chrome MCP 직접 검증 (2026-05-29):
        #   화면 워터마크와 완전 동일 패턴 (yaml print_watermark.equivalence_with_screen 확인됨).
        # 중복 제거 (2026-05-29): state1 검증 줄 제거 — case 3 과 동일.
        wm.fill("")
        _click_cb(pc)  # PC OFF — 초기화
        page.page.wait_for_timeout(200)
        # state1 setup만 (검증 줄 제거 — case 3 과 중복)
        _click_cb(pc)
        _click_cb(tm)
        # state2: '[/PCINFO/]' 만 수동 삭제 → 단방향 sync 결함
        wm.fill("[/TIME/]")
        page.page.wait_for_timeout(400)
        s2_text, s2_pc, s2_time = wm.input_value(), pc.is_checked(), tm.is_checked()
        s2_defect = (s2_pc is True and s2_time is True)
        self._add("warn" if s2_defect else "pass",
                  "sc3m — [출력 워터마크] state2 결함 — '[/PCINFO/]' 만 수동 삭제 → PC/TIME 둘 다 ON 유지",
                  f"입력: text='[/TIME/]' (수동) / 결과: text={s2_text!r}, pc={s2_pc}, time={s2_time} "
                  f"(결함 재현 시 pc=time=True)",
                  sc=3, highlight=pc)
        # state3: text 전체 비움 → 단방향 sync 결함
        wm.fill("")
        page.page.wait_for_timeout(400)
        s3_text, s3_pc, s3_time = wm.input_value(), pc.is_checked(), tm.is_checked()
        s3_defect = (s3_pc is True and s3_time is True)
        self._add("warn" if s3_defect else "pass",
                  "sc3m — [출력 워터마크] state3 결함 — text 전체 비움 → PC/TIME 둘 다 ON 유지",
                  f"입력: text='' (수동) / 결과: text={s3_text!r}, pc={s3_pc}, time={s3_time} "
                  f"(결함 재현 시 pc=time=True)",
                  sc=3, highlight=tm)

        # 정리
        if pc.is_checked():
            _click_cb(pc)
        if tm.is_checked():
            _click_cb(tm)

        page.close_modal()

    # ==================================================================
    # sc3n — 텍스트 길이 클라 가드 부재 + 서버 generic error 재현
    # yaml known_bugs_origin_protect.text_length_no_client_guard_generic_server_error
    # 사용자 지적 (2026-05-29): "글자 수 제한을 주든 알려주든 해야하는데 그런게 없다고"
    # Chrome MCP 직접 검증 2026-05-29: 3 필드 각 3000자 + 저장 → "서버에서 오류가 발생 하였습니다."
    # ==================================================================
    def test_scenario3n_text_length_no_client_guard(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3n: 텍스트 길이 클라 가드 부재 + 서버 generic error ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        # 사용자 지적 (2026-05-29): "이슈 내용을 두 번 테스트하는 거 같은데"
        #   → Part 1 (maxlength=null 가드 부재 dump) 제거. 동일 결함을 attribute 와 functional 로
        #     2회 검증하는 중복이었음. yaml full_inventory 가 13 필드 dump truth source.
        #     본 메서드는 functional (실제 저장 시 reject 동작) 만 검증.
        # 5 필드 각각 3000자 + 저장 → server error 메시지 재현
        #   (yaml verified_save_rejection: shutdown/screen/print 3건 Chrome MCP 확인
        #    yaml unverified_save_rejection: name/label 2건 — 본 테스트가 추가 검증)
        SERVER_ERR = "서버에서 오류가 발생 하였습니다."
        long_text = "X" * 3000
        cases = [
            ("정책 이름",                   "[AUTO]_sc3n_name",     page.SEL_POLICY_NAME,        True),
            ("드라이브 레이블",             "[AUTO]_sc3n_label",    page.SEL_DRIVE_LABEL,        False),
            ("화면 워터마크 텍스트",        "[AUTO]_sc3n_screen",   page.SEL_SCREEN_WM_TEXT,     False),
            ("출력 워터마크 텍스트",        "[AUTO]_sc3n_print",    page.SEL_PRINT_WM_TEXT,      False),
            ("허용 프로세스 종료 시 알림", "[AUTO]_sc3n_shutdown", page.SEL_SHUTDOWN_MSG_TEXT, False),
        ]
        for area, default_name, target_sel, name_is_target in cases:
            page.open_add_modal()
            # 정책 이름 자체가 검증 대상이면 3000자, 아니면 일반 short name 사용
            policy_name = long_text if name_is_target else default_name
            page.page.locator(page.SEL_POLICY_NAME).fill(policy_name)
            page.page.locator(page.SEL_DRIVE_LETTER).fill("X")
            page.page.locator(page.SEL_DRIVE_LABEL).fill(long_text if target_sel == page.SEL_DRIVE_LABEL else "LenProbe")
            page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
            _csu_select_first(page)
            # 대상 필드 3000자 (이름·레이블은 위에서 처리, 나머지는 여기서)
            if target_sel not in (page.SEL_POLICY_NAME, page.SEL_DRIVE_LABEL):
                page.page.locator(target_sel).fill(long_text)
            page.page.wait_for_timeout(300)
            _save_click(page)
            msg = ""
            if page.is_confirm_modal_visible(timeout=3000):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
            is_generic_err = msg == SERVER_ERR
            has_explicit_limit = ("최대" in msg) or ("자 이하" in msg) or ("길이" in msg)
            # 결함 재현 시 warn / 명확한 "최대 N자" 류 메시지면 pass / 둘 다 아니면 fail
            self._add("warn" if is_generic_err else ("pass" if has_explicit_limit else "fail"),
                      f"sc3n — [{area}] 3000자 저장 → server generic error 재현 (사유 미노출)",
                      f"입력: '{area}' = 'X'*3000 / 결과: msg={msg!r} "
                      f"(generic '서버에서 오류가 발생 하였습니다.' 재현 시 warn = known_bug)",
                      sc=3, highlight=page.page.locator(target_sel))
            # 모달 정리
            try:
                page.close_modal()
            except Exception:
                pass
            page.navigate_to()


    # ==================================================================
    # sc3o — 토글 종속 disabled 검증 (4 토글 × 종속 16건)
    # yaml toggle_dependencies (Chrome MCP 직접 검증 2026-05-29)
    # 사용자 지적: "토글 종속 disabled 검증 신규 추가"
    # ==================================================================
    def test_scenario3o_toggle_dependency_disabled(self, logged_in_page, settings):
        print("\n━━ [원본보호 정책] 시나리오 3o: 토글 OFF → 종속 필드 disabled 검증 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        # 토글 → 종속 필드 매핑 (yaml toggle_dependencies 미러)
        toggle_specs = [
            ("파일 감시 기능",       "isWatchFileExtension", [
                "watchFileExtensions", "watchExceptFolders",
                "isWatchFileHeader",
                "watchFileExtensionAddBtn", "watchExceptFolderAddBtn",
            ]),
            ("종료 알림 출력",       "isAllowProcessShutdownText", [
                "allowProcessShutdownText",
            ]),
            ("화면 워터마크",        "isScreenWaterMark", [
                "screenWaterMarkText",
                "isScreenWaterMarkPcInfo", "isScreenWaterMarkCurrentTime",
                "screenWaterMarkOpacity", "screenWaterMarkDegree",
            ]),
            ("출력 워터마크",        "isPrintWaterMark", [
                "printWaterMarkText",
                "isPrintWaterMarkPcInfo", "isPrintWaterMarkCurrentTime",
                "printWaterMarkOpacity", "printWaterMarkDegree",
            ]),
        ]

        for area, toggle_id, dep_ids in toggle_specs:
            toggle_loc = page.page.locator(f"input#{toggle_id}")
            # default ON 가정 — 토글 클릭으로 OFF
            toggle_loc.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(400)

            # 종속 필드 disabled 상태 dump
            disabled_states = page.page.evaluate(
                "(ids) => ids.map(id => { const el=document.getElementById(id); "
                "return {id, exists:!!el, disabled: el? el.disabled : null}; })",
                dep_ids
            )
            not_disabled = [s["id"] for s in disabled_states if s["disabled"] is not True]
            all_disabled = not not_disabled and all(s["exists"] for s in disabled_states)

            self._add("pass" if all_disabled else "fail",
                      f"sc3o — [{area}] 토글 OFF → 종속 {len(dep_ids)}건 모두 disabled",
                      f"토글: {toggle_id} / 종속: {dep_ids} / "
                      f"결과: {'전부 disabled' if all_disabled else 'disabled 안 된 필드=' + str(not_disabled)}",
                      sc=3, highlight=page.page.locator(f"input#{dep_ids[0]}"))

            # 다시 ON 복구 — 다음 토글 검증에 영향 없도록
            toggle_loc.first.evaluate("el => el.click()")
            page.page.wait_for_timeout(300)

        # 추가 검증 (Chrome MCP 직접 재현 2026-05-29): 파일 감시 토글 OFF 시 tag [X]
        # (i.extentionDeleteBtn) 가 disabled 안 되고 실제 click 시 tag 삭제됨 = 결함 재현.
        # yaml known_bugs.toggle_off_tag_delete_still_clickable 매칭 검증.
        # tag 1건씩 등록 (확장자/예외폴더) → 토글 OFF → click → 삭제 여부 확인
        ext_input = page.page.locator(page.SEL_WATCH_EXT_INPUT)
        ext_input.fill("txt")
        page.page.locator(page.SEL_WATCH_EXT_BTN).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(400)
        fld_input = page.page.locator(page.SEL_WATCH_EXCEPT_INPUT)
        fld_input.fill("C:\\Temp_sc3o")
        page.page.locator(page.SEL_WATCH_EXCEPT_BTN).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(400)

        # 토글 OFF
        page.page.locator(page.SEL_WATCH_EXT_TOGGLE).first.evaluate("el => el.click()")
        page.page.wait_for_timeout(400)

        # tag [X] click 시도 → 삭제되면 결함 재현 (warn)
        before_cnt = page.page.locator("#addItemModal i.extentionDeleteBtn").count()
        if before_cnt > 0:
            page.page.locator("#addItemModal i.extentionDeleteBtn").first.evaluate("el => el.click()")
            page.page.wait_for_timeout(400)
        after_cnt = page.page.locator("#addItemModal i.extentionDeleteBtn").count()
        defect_reproduced = (before_cnt > 0 and after_cnt < before_cnt)
        self._add("warn" if defect_reproduced else "pass",
                  "sc3o — [파일 감시 기능] 토글 OFF 시 tag [X] 삭제 결함 재현 (known_bug)",
                  f"입력: 토글 OFF 후 i.extentionDeleteBtn click / "
                  f"결과: tags_before={before_cnt}, tags_after={after_cnt}, "
                  f"deleted={defect_reproduced} (yaml known_bug:toggle_off_tag_delete_still_clickable)",
                  sc=3, highlight=page.page.locator("#addItemModal i.extentionDeleteBtn").first)

        page.close_modal()
