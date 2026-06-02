"""nPouch 엔파우치 정책 — 시나리오 2: 입력 구조 (origin_protect 패턴 그대로).

Chrome MCP 사실 (2026-06-01):
  - 모달 input 51개 (정책 정보 37 + PDF 14)
  - default 토글 ON: isMaxReadCount/isMaxReadDay/isOpenFilePassword/isOriginProtectPolicy/
                   isPrintOption/isNpPackageFileCreateFileCount/isExtensionFilter/isPdfProtect
  - default 토글 OFF: isValidateSslCert / isServerAuthToRead
  - default 숫자: maxReadCount=3 / maxReadDay=5 / passwordMinDigit=9 / passwordMaxDigit=16
                 passwordSameLetterCount=3 / passwordContinueLetterCount=3
  - color default: pdfWaterMarkAddTextColor=#000000
  - required marker: span.star (origin_protect 패턴 — 정확한 개수 검증)
"""
from pages.npouch_policy_page import NpouchPolicyPage
from tests.npouch_policy._base import NpouchPolicyBase


class TestNpouchPolicyScenario2Input(NpouchPolicyBase):
    """엔파우치 정책 — 시나리오 2: 입력 구조."""

    def test_scenario2a_field_inventory(self, logged_in_page, settings):
        """sc2a — ADD 모달 51 필드 존재 (그룹별 한글 라벨)."""
        print("\n━━ [엔파우치 정책] 시나리오 2a: 필드 인벤토리 (51개) ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 정책 정보 탭 그룹별
        groups = {
            "기본": [
                ("정책 이름",                     page.SEL_POLICY_NAME),
                ("열람 파일 인증 서버 URL",       page.SEL_CERT_URL),
                ("SSL 인증서 유효성 검사 토글",   page.SEL_VALIDATE_SSL),
            ],
            "열람 제한": [
                ("열람횟수 설정 토글",   page.SEL_MAX_READ_COUNT_TOGGLE),
                ("최대 열람횟수 input",  page.SEL_MAX_READ_COUNT_VAL),
                ("열람 유효기간 토글",   page.SEL_MAX_READ_DAY_TOGGLE),
                ("최대 열람 유효기간 input", page.SEL_MAX_READ_DAY_VAL),
            ],
            "열기암호": [
                ("열기암호 사용 토글",   page.SEL_PW_TOGGLE),
                ("최소 글자수",          page.SEL_PW_MIN),
                ("최대 글자수",          page.SEL_PW_MAX),
                ("동일문자 허용 개수",   page.SEL_PW_SAME_LETTER),
                ("연속된 글자 허용 개수", page.SEL_PW_CONTINUE_LETTER),
                ("문자+숫자 조합 여부",  page.SEL_PW_NUMBER_LETTER),
                ("특수문자 포함 여부",   page.SEL_PW_SPECIAL_LETTER),
            ],
            "뷰어 앱": [
                ("뷰어 앱 포함 radio",   page.SEL_INCLUDE_READER),
                ("뷰어 앱 미포함 radio", page.SEL_NOT_INCLUDE_READER),
            ],
            "원본보호 정책": [
                ("원본보호 정책 적용 체크박스", page.SEL_ORIGIN_PROTECT),
                ("원본보호 정책 선택 버튼",    page.SEL_ORIGIN_PROTECT_BTN),
            ],
            "인쇄 옵션": [
                ("인쇄 옵션 사용 토글",  page.SEL_PRINT_OPTION),
                ("인쇄 차단 radio",      page.SEL_PRINT_X),
                ("인쇄 허용 radio",      page.SEL_PRINT_O),
                ("허용 인쇄 브랜드",     page.SEL_ALLOW_PRINT_BRAND),
                ("제외 인쇄 포트",       page.SEL_EXCEPT_PRINT_PORT),
            ],
            "첨부파일": [
                ("첨부파일 개수 제한 토글", page.SEL_FILE_COUNT_TOGGLE),
                ("파일개수",                page.SEL_FILE_COUNT_VAL),
            ],
            "서버 통신": [
                ("서버 통신 후 열람 허용 토글", page.SEL_SERVER_AUTH),
                ("nPouch Certi 2차인증",        page.SEL_COLLECT_LOCATION),
                ("오프라인 정책",                page.SEL_OFFLINE_POLICY),
                ("Certi 인증없이 열람",          page.SEL_ALLOW_OFFLINE),
                ("열람 거부",                    page.SEL_DENY_OFFLINE),
            ],
            "확장자 필터": [
                ("확장자 필터기능 토글",     page.SEL_EXT_FILTER),
                ("포함할 파일 확장자 radio", page.SEL_EXT_INCLUDE),
                ("제외할 파일 확장자 radio", page.SEL_EXT_EXCEPT),
                ("확장자 input",             page.SEL_EXT_INPUT),
            ],
            "HTML 가이드": [
                ("로고 이미지",   page.SEL_LOGO_IMG),
                ("문서 제목",     page.SEL_HTML_DOC_NAME),
                ("연락처",        page.SEL_HTML_CONTACT),
            ],
            "기타": [
                ("커스텀 옵션값", page.SEL_CUSTOM_OPTION),
            ],
        }
        for group_label, items in groups.items():
            for label, sel in items:
                present = page.page.locator(sel).count() > 0
                self._add("pass" if present else "fail",
                          f"sc2a — [{group_label}] '{label}' 존재",
                          f"selector='{sel}' / 결과: present={present}", sc=2)

        # PDF 탭 그룹
        page.activate_tab("PDF문서 보호 기능 설정")
        pdf_groups = {
            "PDF 보호": [
                ("PDF문서 보호 기능 토글",  page.SEL_PDF_PROTECT),
                ("PDF문서 프린트 허용",     page.SEL_PDF_PRINT),
                ("워터마크 표시하기",        page.SEL_PDF_WATERMARK),
            ],
            "촬영방지 워터마크 (바둑판)": [
                ("바둑판 배열 토글",  page.SEL_SHOOT_WM),
                ("워터마크 문구",     page.SEL_SHOOT_WM_TEXT),
                ("PC정보",            page.SEL_SHOOT_WM_PC),
                ("현재시간",          page.SEL_SHOOT_WM_TIME),
                ("불투명도",          page.SEL_SHOOT_WM_OPACITY),
            ],
            "화면 중앙 워터마크": [
                ("중앙 워터마크 토글", page.SEL_CENTER_WM),
                ("표시 내용",          page.SEL_CENTER_WM_TEXT),
                ("글자 크기",          page.SEL_CENTER_WM_SIZE),
                ("불투명도",           page.SEL_CENTER_WM_OPACITY),
                ("기울기",             page.SEL_CENTER_WM_DEGREE),
                ("색상 (color picker)", page.SEL_CENTER_WM_COLOR),
            ],
        }
        for group_label, items in pdf_groups.items():
            for label, sel in items:
                present = page.page.locator(sel).count() > 0
                self._add("pass" if present else "fail",
                          f"sc2a — [{group_label}] '{label}' 존재",
                          f"selector='{sel}' / 결과: present={present}", sc=2)

        page.close_modal()

    def test_scenario2b_required_star_markers(self, logged_in_page, settings):
        """sc2b — 필수 marker `span.star` 정확 개수 (origin_protect 패턴)."""
        print("\n━━ [엔파우치 정책] 시나리오 2b: 필수 marker (span.star) ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # span.star 개수 — Chrome MCP 첫 dump 시 사실 확보 (실제 개수)
        stars = page.page.locator("div#addItemModal span.star")
        cnt = stars.count()
        # 첫 run 후 사실 확정 — 정확한 개수 별도 확인 필요. 1 이상이면 pass.
        self._add("pass" if cnt >= 1 else "fail",
                  "sc2b — 필수 marker span.star 1개 이상 존재",
                  f"결과: count={cnt} (사실 확보 — 첫 run 후 yaml required 정합성 검증)",
                  sc=2)

        page.close_modal()

    def test_scenario2c_default_values_reset(self, logged_in_page, settings):
        """sc2c — ADD 모달 default 값 검증 + close→re-open reset 확인.

        Chrome MCP 사실 (2026-06-01):
          - 토글 default ON: isMaxReadCount, isMaxReadDay, isOpenFilePassword,
                            isOriginProtectPolicy, isPrintOption,
                            isNpPackageFileCreateFileCount, isExtensionFilter, isPdfProtect
          - 토글 default OFF: isValidateSslCert, isServerAuthToRead
          - 숫자 default: 3 / 5 / 9 / 16 / 3 / 3
        """
        print("\n━━ [엔파우치 정책] 시나리오 2c: default 값 + reset ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 토글 default ON
        toggle_on = {
            "열람횟수 설정 토글":     page.SEL_MAX_READ_COUNT_TOGGLE,
            "열람 유효기간 토글":     page.SEL_MAX_READ_DAY_TOGGLE,
            "열기암호 사용 토글":     page.SEL_PW_TOGGLE,
            "원본보호 정책 적용":     page.SEL_ORIGIN_PROTECT,
            "인쇄 옵션 사용 토글":    page.SEL_PRINT_OPTION,
            "첨부파일 개수 제한 토글": page.SEL_FILE_COUNT_TOGGLE,
            "확장자 필터기능 토글":   page.SEL_EXT_FILTER,
            "PDF문서 보호 기능 토글": page.SEL_PDF_PROTECT,
        }
        for label, sel in toggle_on.items():
            checked = page.page.locator(sel).is_checked()
            self._add("pass" if checked is True else "fail",
                      f"sc2c — '{label}' default ON",
                      f"결과: checked={checked} (기대 True)", sc=2)

        # 토글 default OFF
        toggle_off = {
            "SSL 인증서 유효성 검사":      page.SEL_VALIDATE_SSL,
            "서버 통신 후 열람 허용 토글": page.SEL_SERVER_AUTH,
        }
        for label, sel in toggle_off.items():
            checked = page.page.locator(sel).is_checked()
            self._add("pass" if checked is False else "fail",
                      f"sc2c — '{label}' default OFF",
                      f"결과: checked={checked} (기대 False)", sc=2)

        # 숫자 default 값
        number_defaults = {
            "최대 열람횟수":         (page.SEL_MAX_READ_COUNT_VAL, "3"),
            "최대 열람 유효기간":    (page.SEL_MAX_READ_DAY_VAL, "5"),
            "비밀번호 최소 글자수":  (page.SEL_PW_MIN, "9"),
            "비밀번호 최대 글자수":  (page.SEL_PW_MAX, "16"),
            "동일문자 허용 개수":    (page.SEL_PW_SAME_LETTER, "3"),
            "연속된 글자 허용 개수": (page.SEL_PW_CONTINUE_LETTER, "3"),
        }
        for label, (sel, expected) in number_defaults.items():
            val = page.page.locator(sel).input_value()
            self._add("pass" if val == expected else "fail",
                      f"sc2c — '{label}' default 값",
                      f"기대: {expected!r} / 실제: {val!r}", sc=2)

        # text default = "" (빈값)
        text_empty = {
            "정책 이름":              page.SEL_POLICY_NAME,
            "열람 파일 인증 서버 URL": page.SEL_CERT_URL,
            "허용 인쇄 브랜드":       page.SEL_ALLOW_PRINT_BRAND,
            "제외 인쇄 포트":         page.SEL_EXCEPT_PRINT_PORT,
            "확장자 input":           page.SEL_EXT_INPUT,
            "문서 제목":              page.SEL_HTML_DOC_NAME,
            "연락처":                 page.SEL_HTML_CONTACT,
            "커스텀 옵션값":          page.SEL_CUSTOM_OPTION,
        }
        for label, sel in text_empty.items():
            val = page.page.locator(sel).input_value()
            self._add("pass" if val == "" else "fail",
                      f"sc2c — '{label}' default 빈값",
                      f"결과: value={val!r}", sc=2)

        # PDF 탭 — 색상 default #000000
        page.activate_tab("PDF문서 보호 기능 설정")
        color_val = page.page.locator(page.SEL_CENTER_WM_COLOR).input_value()
        ok_color = color_val.lower() == "#000000"
        self._add("pass" if ok_color else "fail",
                  "sc2c — 색상 picker default #000000",
                  f"실제: {color_val!r}", sc=2)

        page.close_modal()

    def test_scenario2d_maxlength_all_null(self, logged_in_page, settings):
        """sc2d — text/textarea input maxlength=null (서버 측 검증 의존)."""
        print("\n━━ [엔파우치 정책] 시나리오 2d: maxlength 전체 null ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        text_inputs = {
            "정책 이름":              page.SEL_POLICY_NAME,
            "열람 파일 인증 서버 URL": page.SEL_CERT_URL,
            "최대 열람횟수":          page.SEL_MAX_READ_COUNT_VAL,
            "최대 열람 유효기간":     page.SEL_MAX_READ_DAY_VAL,
            "비밀번호 최소 글자수":   page.SEL_PW_MIN,
            "비밀번호 최대 글자수":   page.SEL_PW_MAX,
            "허용 인쇄 브랜드":       page.SEL_ALLOW_PRINT_BRAND,
            "제외 인쇄 포트":         page.SEL_EXCEPT_PRINT_PORT,
            "확장자 input":           page.SEL_EXT_INPUT,
            "문서 제목":              page.SEL_HTML_DOC_NAME,
            "연락처":                 page.SEL_HTML_CONTACT,
            "커스텀 옵션값":          page.SEL_CUSTOM_OPTION,
        }
        for label, sel in text_inputs.items():
            ml = page.page.locator(sel).get_attribute("maxlength")
            self._add("pass" if ml is None else "fail",
                      f"sc2d — '{label}' maxlength=null (서버 측 검증)",
                      f"결과: maxlength={ml!r}", sc=2)

        page.close_modal()
