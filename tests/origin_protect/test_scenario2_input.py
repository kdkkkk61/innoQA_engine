"""원본보호 정책 — 시나리오 2: 입력 구조 검증 (ADD 모달 기본설정 탭).

yaml 사실 (config/scan_hints/npouch_origin_protect_policy.yaml) 그대로:
  - 26 input 인벤토리 (visible 22 + hidden toggle 4)
  - default = 모든 text "", checkbox false (close→reopen 시 reset)
  - maxlength = 전부 null (DOM 제한 없음, 서버 검증 의존)
  - required marker = <span class="star"> 3개 (정책 이름 / 드라이브 설정 / CSU 선택)

⚠ ADD 모달은 '기본 설정' 탭만 활성 — 비기본 3탭 UI 는 EDIT 영역(sc4)에서 검증.
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase


class TestOriginProtectScenario2Input(OriginProtectBase):
    """원본보호 정책 — 시나리오 2: ADD 모달 입력 구조."""

    def test_scenario2a_field_inventory(self, logged_in_page, settings):
        """sc2a — ADD 모달 26 필드 존재 (그룹별 한글 라벨)."""
        print("\n━━ [원본보호 정책] 시나리오 2a: 필드 인벤토리 (26개) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 그룹별 인벤토리 — (라벨, selector, type 표시용)
        groups = {
            "기본": [
                ("정책 이름",                page.SEL_POLICY_NAME),
                ("원본보호 드라이브 - 문자",  page.SEL_DRIVE_LETTER),
                ("원본보호 드라이브 - 라벨",  page.SEL_DRIVE_LABEL),
                ("원본보호 드라이브 - 용량",  page.SEL_DRIVE_QUOTA),
                ("제어 스위트 선택 버튼",    page.SEL_CSU_SELECT_BTN),
                ("제어 스위트 결과 span",    page.SEL_CSU_ID_SPAN),
            ],
            "프로세스 사용 토글": [
                ("허용 프로세스 사용",     page.SEL_ALLOW_PROCESS),
                ("예외처리 프로세스 사용", page.SEL_EXCEPT_PROCESS),
                ("실행차단 프로세스 사용", page.SEL_BLOCK_PROCESS),
            ],
            "파일 감시": [
                ("파일 감시 기능 토글",      page.SEL_WATCH_EXT_TOGGLE),
                ("감시할 파일 확장자 input", page.SEL_WATCH_EXT_INPUT),
                ("감시할 파일 확장자 추가",  page.SEL_WATCH_EXT_BTN),
                ("헤더 체크 토글",          page.SEL_WATCH_HEADER),
                ("감시 예외 폴더 input",    page.SEL_WATCH_EXCEPT_INPUT),
                ("감시 예외 폴더 추가",     page.SEL_WATCH_EXCEPT_BTN),
            ],
            "프로세스 종료 알림": [
                ("종료 알림 토글",    page.SEL_SHUTDOWN_MSG_TOGGLE),
                ("종료 알림 텍스트",  page.SEL_SHUTDOWN_MSG_TEXT),
            ],
            "화면 워터마크": [
                ("화면 워터마크 토글", page.SEL_SCREEN_WM),
                ("워터마크 텍스트",    page.SEL_SCREEN_WM_TEXT),
                ("PC 정보 포함",       page.SEL_SCREEN_WM_PC_INFO),
                ("현재 시각 포함",     page.SEL_SCREEN_WM_TIME),
                ("투명도",            page.SEL_SCREEN_WM_OPACITY),
                ("각도",              page.SEL_SCREEN_WM_DEGREE),
            ],
            "출력 워터마크": [
                ("출력 워터마크 토글", page.SEL_PRINT_WM),
                ("워터마크 텍스트",    page.SEL_PRINT_WM_TEXT),
                ("PC 정보 포함",       page.SEL_PRINT_WM_PC_INFO),
                ("현재 시각 포함",     page.SEL_PRINT_WM_TIME),
                ("투명도",            page.SEL_PRINT_WM_OPACITY),
                ("각도",              page.SEL_PRINT_WM_DEGREE),
            ],
            "기타": [
                ("2차 반출", page.SEL_SECOND_TAKEOUT),
            ],
        }
        for group_label, items in groups.items():
            for label, sel in items:
                present = page.page.locator(sel).count() > 0
                self._add("pass" if present else "fail",
                          f"sc2a — [{group_label}] '{label}' 존재",
                          f"selector='{sel}' / 결과: present={present}", sc=2)

        page.close_modal()

    def test_scenario2b_required_star_markers(self, logged_in_page, settings):
        """sc2b — 필수 marker `span.star` 정확 3개 (정책 이름 / 드라이브 설정 / 제어 스위트 선택).

        yaml required_fields: 진짜 마커는 라벨 안 * 가 아니라 별도 <span class="star">.
        """
        print("\n━━ [원본보호 정책] 시나리오 2b: 필수 marker (span.star 3개) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # span.star 개수 정확 3개?
        stars = page.page.locator("div#addItemModal span.star")
        cnt = stars.count()
        self._add("pass" if cnt == 3 else "fail",
                  "sc2b — 필수 marker span.star 정확 3개",
                  f"결과: count={cnt} (yaml 기대=3)", sc=2)

        page.close_modal()

    def test_scenario2c_default_values_reset(self, logged_in_page, settings):
        """sc2c — ADD 모달 default 정확 검증.

        Chrome MCP 직접 확인 2026-05-28 (사용자 통찰 후 재검증):
          - 모든 text/textarea = "" (13개)
          - hidden switch (parent.class='switch') 4개 = default ON
              isWatchFileExtension / isAllowProcessShutdownText
              isScreenWaterMark / isPrintWaterMark
          - 일반 visible checkbox 9개 = default OFF
        close → re-open 시 위 상태로 일관 reset.
        """
        print("\n━━ [원본보호 정책] 시나리오 2c: default 값 + reset ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        # 1차: 임의로 채움 후 close
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill("[AUTO]_probe_default")
        page.page.locator(page.SEL_DRIVE_LETTER).fill("Z")
        page.page.locator(page.SEL_DRIVE_LABEL).fill("ProbeLabel")
        page.page.locator(page.SEL_DRIVE_QUOTA).fill("100")
        page.close_modal()

        # 2차: 재오픈 — 모든 text 필드 default = "" 검증
        page.open_add_modal()
        text_defaults = {
            "정책 이름":                 page.SEL_POLICY_NAME,
            "원본보호 드라이브 - 문자":  page.SEL_DRIVE_LETTER,
            "원본보호 드라이브 - 라벨":  page.SEL_DRIVE_LABEL,
            "원본보호 드라이브 - 용량":  page.SEL_DRIVE_QUOTA,
            "감시할 파일 확장자 input":  page.SEL_WATCH_EXT_INPUT,
            "감시 예외 폴더 input":      page.SEL_WATCH_EXCEPT_INPUT,
            "종료 알림 텍스트":          page.SEL_SHUTDOWN_MSG_TEXT,
            "화면 워터마크 텍스트":      page.SEL_SCREEN_WM_TEXT,
            "화면 워터마크 투명도":      page.SEL_SCREEN_WM_OPACITY,
            "화면 워터마크 각도":        page.SEL_SCREEN_WM_DEGREE,
            "출력 워터마크 텍스트":      page.SEL_PRINT_WM_TEXT,
            "출력 워터마크 투명도":      page.SEL_PRINT_WM_OPACITY,
            "출력 워터마크 각도":        page.SEL_PRINT_WM_DEGREE,
        }
        for label, sel in text_defaults.items():
            val = page.page.locator(sel).input_value()
            self._add("pass" if val == "" else "fail",
                      f"sc2c — '{label}' default 빈값",
                      f"결과: value={val!r}", sc=2)

        # hidden switch 4종 default = ON (true) — Bootstrap 'switch' 패턴
        switch_default_on = {
            "파일 감시 기능 토글":  page.SEL_WATCH_EXT_TOGGLE,
            "종료 알림 토글":       page.SEL_SHUTDOWN_MSG_TOGGLE,
            "화면 워터마크 토글":   page.SEL_SCREEN_WM,
            "출력 워터마크 토글":   page.SEL_PRINT_WM,
        }
        for label, sel in switch_default_on.items():
            checked = page.page.locator(sel).is_checked()
            self._add("pass" if checked is True else "fail",
                      f"sc2c — '{label}' default ON (hidden switch)",
                      f"결과: checked={checked} (기대 True)", sc=2)

        # 일반 checkbox 9종 default = OFF (false)
        checkbox_default_off = {
            "허용 프로세스 사용":        page.SEL_ALLOW_PROCESS,
            "예외처리 프로세스 사용":    page.SEL_EXCEPT_PROCESS,
            "실행차단 프로세스 사용":    page.SEL_BLOCK_PROCESS,
            "헤더 체크 토글":            page.SEL_WATCH_HEADER,
            "화면 워터마크 PC 정보":     page.SEL_SCREEN_WM_PC_INFO,
            "화면 워터마크 현재 시각":   page.SEL_SCREEN_WM_TIME,
            "출력 워터마크 PC 정보":     page.SEL_PRINT_WM_PC_INFO,
            "출력 워터마크 현재 시각":   page.SEL_PRINT_WM_TIME,
            "2차 반출":                  page.SEL_SECOND_TAKEOUT,
        }
        for label, sel in checkbox_default_off.items():
            checked = page.page.locator(sel).is_checked()
            self._add("pass" if checked is False else "fail",
                      f"sc2c — '{label}' default OFF",
                      f"결과: checked={checked} (기대 False)", sc=2)

        page.close_modal()

    def test_scenario2d_maxlength_all_null(self, logged_in_page, settings):
        """sc2d — 모든 input maxlength=null (DOM 제한 없음, 서버 측 검증 의존).

        yaml maxlength_inventory: 34 inputs maxlength=null.
        """
        print("\n━━ [원본보호 정책] 시나리오 2d: maxlength 전체 null ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        page.open_add_modal()

        # 검증 대상 — text/textarea input 만 (checkbox 는 maxlength 무관)
        text_inputs = {
            "정책 이름":                 page.SEL_POLICY_NAME,
            "원본보호 드라이브 - 문자":  page.SEL_DRIVE_LETTER,
            "원본보호 드라이브 - 라벨":  page.SEL_DRIVE_LABEL,
            "원본보호 드라이브 - 용량":  page.SEL_DRIVE_QUOTA,
            "감시할 파일 확장자 input":  page.SEL_WATCH_EXT_INPUT,
            "감시 예외 폴더 input":      page.SEL_WATCH_EXCEPT_INPUT,
            "종료 알림 텍스트":          page.SEL_SHUTDOWN_MSG_TEXT,
            "화면 워터마크 텍스트":      page.SEL_SCREEN_WM_TEXT,
            "화면 워터마크 투명도":      page.SEL_SCREEN_WM_OPACITY,
            "화면 워터마크 각도":        page.SEL_SCREEN_WM_DEGREE,
            "출력 워터마크 텍스트":      page.SEL_PRINT_WM_TEXT,
            "출력 워터마크 투명도":      page.SEL_PRINT_WM_OPACITY,
            "출력 워터마크 각도":        page.SEL_PRINT_WM_DEGREE,
        }
        for label, sel in text_inputs.items():
            ml = page.page.locator(sel).get_attribute("maxlength")
            self._add("pass" if ml is None else "fail",
                      f"sc2d — '{label}' maxlength=null (서버 측 검증)",
                      f"결과: maxlength={ml!r}", sc=2)

        page.close_modal()
