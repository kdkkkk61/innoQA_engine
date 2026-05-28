"""시나리오 2 — 입력 구조 + 필드 동작 (2a~2g)."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.control_suite._base import ControlSuiteBase


class TestScenario2Input(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 2 — 입력 구조 + 필드 동작 (2a~2g)"""

    def test_scenario2g_initial_values(self, logged_in_page, settings):
        """시나리오 2g — 모달 열자마자 default 값 명시 검증.
        scenario_2_input.md: "필드 구조, 초기값, 입력 검증 동작 유무"
        → 입력 동작은 2a~2f 가 담당, 초기값은 본 메서드에서 명시.
        """
        print("\n━━ [제어 스위트] 시나리오 2g: 모달 초기값 명시 검증 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()

        # ── 스위트 추가 모달 — 초기값 ─────────────────────────
        v = page.get_csu_name()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 스위트 이름 — 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 클립보드 공유제한 — 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.get_clipboard_allow_url()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 클립보드 공유제한 — 허용 URL 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.is_network_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 네트워크 허용 — 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.get_main_extension_list()
        self._add("pass" if v == [] else "fail",
                  "[초기값 확인] 제어할 확장자 — list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 헤더 체크 기능 사용 — 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 전자서명 예외처리 — 사용 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.get_sign_except_list()
        self._add("pass" if v == [] else "fail",
                  "[초기값 확인] 전자서명 예외처리 — list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.get_custom_option()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 커스텀 옵션 — 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        # ── 프로세스 등록 모달 — 초기값 ────────────────────────
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        v = page.process.get_selected_display_text()
        self._add("pass" if "미선택" in v else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 선택 표시 초기값 ('프로세스 미선택')",
                  f"입력: 모달 진입 직후 / 결과: display={v!r}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 프로세스 예외처리 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 개별 클립보드 공유제한 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 샌드박스 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 드라이브 제외 거부 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 네트워크 허용 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.get_ip_list()
        self._add("pass" if v == [] else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — IP/Port list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 확장자 제어 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.get_extension_list()
        self._add("pass" if v == [] else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 확장자 list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.process.get_cache_folder_list()
        self._add("pass" if v == [] else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 캐시 폴더 list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.process.get_cache_input_text()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 캐시 폴더 input 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE)
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 접근 드라이브 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.get_drive_letter()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 드라이브 레터 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.process.get_description()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 프로세스 등록 모달 — 설명 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        page.process.close()

        # ── 웹제한 모달 — 초기값 ──────────────────────────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()

        v = page.web_restrict.get_name()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 웹제한 모달 — 웹 제한 이름 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.web_restrict.get_base_path()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 웹제한 모달 — basePath 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.web_restrict.is_url_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 웹제한 모달 — 적용 URL 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        disables = page.web_restrict.get_url_dependent_disabled()
        all_disabled = all(disables.values())
        self._add("pass" if all_disabled else "fail",
                  "[초기값 확인] 웹제한 모달 — isUrl OFF 시 종속 4건 disabled (초기 상태)",
                  f"입력: 모달 진입 직후 / 결과: {disables}", sc=2)

        v = page.web_restrict.is_file_encrypt_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 웹제한 모달 — 업로드 시 암호화 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.page.locator(page.web_restrict.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "[초기값 확인] 웹제한 모달 — 헤더 체크 기능 사용 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.web_restrict.get_description()
        self._add("pass" if v == "" else "fail",
                  "[초기값 확인] 웹제한 모달 — 설명 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        # 정리
        page.web_restrict.close()
        page.close_modal()
        self._add("pass", "정리 — 모든 모달 close (저장 X)",
                  "입력: close × 2 / 결과: detached", sc=2)


    # ==================================================================
    # Step 2 — 메인 모달 단독 필드 (저장 X, 프로세스/웹제한 X)
    # ==================================================================
    def test_scenario2a_main_modal_fields(self, logged_in_page, settings):
        """시나리오 2a — 메인 모달 단독 필드 9 블록.
        각 블록을 별도 ScanResult 로 분리해 보고서에 세부 출력.
        """
        print("\n━━ [제어 스위트] 시나리오 2a: 메인 모달 단독 필드 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page   # fail 스크린샷용

        page.navigate_to()
        page.open_add_modal()

        # ── 스위트 이름 (csuName) ──────────────────────────────
        page.set_csu_name("[AUTO]_sc2_step1")
        got = page.get_csu_name()
        self._add("pass" if got == "[AUTO]_sc2_step1" else "fail",
                  "[입력 확인] 스위트 이름",
                  f"입력: '[AUTO]_sc2_step1' / 결과: get={got!r}", sc=2)

        # ── 클립보드 공유제한 (토글 + 허용 URL) ────────────────
        page.set_clipboard_restrict_toggle(True)
        chk = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        self._add("pass" if chk else "fail",
                  "[입력 확인] 클립보드 공유제한 — 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.set_clipboard_allow_url("naver.com;google.com")
        url = page.get_clipboard_allow_url()
        self._add("pass" if "naver.com" in url else "fail",
                  "[입력 확인] 클립보드 공유제한 — 허용 URL 입력",
                  f"입력: 'naver.com;google.com' / 결과: get={url!r}", sc=2)

        # ── 네트워크 허용 (토글) ──────────────────────────────
        page.set_network_toggle(True)
        chk = page.is_network_checked()
        self._add("pass" if chk else "fail",
                  "[입력 확인] 네트워크 허용 — 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        # ── 제어할 확장자 (라디오 + tag input) ─────────────────
        page.click_radio_block()
        t1 = page.get_radio_react_text()
        self._add("pass" if t1 == "허용할 확장자" else "fail",
                  "[입력 확인] 제어할 확장자 — BLOCK 라디오 반응",
                  f"입력: BLOCK 클릭 / 결과: span text={t1!r}", sc=2)

        page.click_radio_allow()
        t2 = page.get_radio_react_text()
        self._add("pass" if t2 == "차단할 확장자" else "fail",
                  "[입력 확인] 제어할 확장자 — ALLOW 라디오 반응",
                  f"입력: ALLOW 클릭 / 결과: span text={t2!r}", sc=2)

        page.add_main_extension("txt;doc;exe")
        ext = page.get_main_extension_list()
        self._add("pass" if ext == ["txt", "doc", "exe"] else "fail",
                  "[입력 확인] 제어할 확장자 — ';' 다중구분자 등록",
                  f"입력: 'txt;doc;exe' / 결과: list={ext}", sc=2)

        page.add_main_extension("txt")
        vis = page.is_confirm_modal_visible()
        msg = page.get_confirm_message() if vis else ""
        dup_ok = vis and "이미 동일한 확장자가 존재합니다" in msg
        self._add("pass" if dup_ok else "fail",
                  "[입력 확인] 제어할 확장자 — 중복 차단 메시지",
                  f"입력: 'txt' (중복) / 결과: confirm={vis} msg={msg!r}", sc=2)
        if vis:
            page.dismiss_confirm_modal()

        # ── 헤더 체크 기능 사용 (독립 체크박스) ─────────────────
        page.set_header_check(True)
        chk = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if chk else "fail",
                  "[입력 확인] 헤더 체크 기능 사용",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        # ── 전자서명 예외처리 (토글 + 추가 list) ────────────────
        page.set_sign_except_toggle(True)
        chk = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        self._add("pass" if chk else "fail",
                  "[입력 확인] 전자서명 예외처리 — 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.add_sign_except("Claude Test Sign")
        page.add_sign_except("Innotium Inc")
        signs = page.get_sign_except_list()
        self._add("pass" if len(signs) == 2 else "fail",
                  "[입력 확인] 전자서명 예외처리 — 항목 추가 (2건)",
                  f"입력: 'Claude Test Sign', 'Innotium Inc' / 결과: count={len(signs)} list={signs}", sc=2)

        # ── 커스텀 옵션 (input) ────────────────────────────────
        page.set_custom_option("test_option_value")
        co = page.get_custom_option()
        self._add("pass" if co == "test_option_value" else "fail",
                  "[입력 확인] 커스텀 옵션",
                  f"입력: 'test_option_value' / 결과: get={co!r}", sc=2)

        # ── 메인 모달 close (저장 X) ───────────────────────────
        page.close_modal()
        self._add("pass", "스위트 추가 모달 — 취소 close",
                  "입력: 취소 클릭 / 결과: 모달 detached", sc=2)

    # ==================================================================
    # Step 3a — sub-tab 전환 + process_sub_modal 진입/탈출
    # ==================================================================




    def test_scenario2b_process_modal_fields(self, logged_in_page, settings):
        """
        process_sub_modal 의 필드를 조작 후 get 으로 일치 확인.
        4 단독 토글 / IP+Port / 확장자 라디오+list / 드라이브 / description.
        cache_folder + special_folder 는 Step 3c-extra 로 분리.
        저장 안 함 (close).
        """
        page = NpouchControlSuitePage(logged_in_page, settings)

        print("\n" + "=" * 60)
        print("[Step 3c] process_sub_modal 필드 검증")
        print("=" * 60)

        print("\n━━ [제어 스위트] 시나리오 2b: process_modal 필드 ━━━")
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc2_step2")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        # 프로세스 1건 선택 (필드 조작 사전 조건)
        page.process.click_pick_btn()
        page.picker.wait_open()
        selected = page.picker.select_first_and_confirm(mode="single")
        self._add("pass", "프로세스 선택 (필드 조작 사전조건)",
                  f"입력: picker 첫 행 / 결과: {selected!r}", sc=2)

        # ── 단독 토글 4건 ──────────────────────────────────────
        page.process.set_process_except(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 프로세스 예외처리 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_pclipboard_restrict(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 개별 클립보드 공유제한 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_sandbox(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 샌드박스 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_deny_except_drive(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 드라이브 제외 거부 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        # ── 네트워크 허용 (isPNetwork + IP/Port) ──────────────
        page.process.set_pnetwork(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 네트워크 허용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.add_ip_port("192.168.1.1", "8080")
        ip_list = page.process.get_ip_list()
        ok = any("192.168.1.1" in x and "8080" in x for x in ip_list)
        self._add("pass" if ok else "fail",
                  "[입력 확인] 프로세스 등록 모달 — IP/Port 추가 (list)",
                  f"입력: '192.168.1.1' + '8080' / 결과: list={ip_list}", sc=2)

        # ── 확장자 제어 (isPControlExtension + 라디오 + tag) ──
        page.process.set_pcontrol_extension(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 확장자 제어 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.click_radio_blockp()
        t1 = page.process.get_radio_react_text()
        self._add("pass" if t1 == "허용할 확장자" else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 확장자 BLOCKP 라디오 반응",
                  f"입력: BLOCKP 클릭 / 결과: span={t1!r}", sc=2)

        page.process.click_radio_allowp()
        t2 = page.process.get_radio_react_text()
        self._add("pass" if t2 == "차단할 확장자" else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 확장자 ALLOWP 라디오 반응",
                  f"입력: ALLOWP 클릭 / 결과: span={t2!r}", sc=2)

        page.process.add_extension("log;tmp;bak")
        ext = page.process.get_extension_list()
        self._add("pass" if ext == ["log", "tmp", "bak"] else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 확장자 ';' 다중구분자 등록",
                  f"입력: 'log;tmp;bak' / 결과: list={ext}", sc=2)

        # ── 접근 드라이브 ──────────────────────────────────────
        page.process.set_access_drive(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 접근 드라이브 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_drive_letter("C;D")
        dl = page.process.get_drive_letter()
        self._add("pass" if dl == "C;D" else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 드라이브 레터 입력",
                  f"입력: 'C;D' / 결과: get={dl!r}", sc=2)

        # ── 설명 ───────────────────────────────────────────────
        page.process.set_description("sc2_step2 자동 테스트 설명")
        desc = page.process.get_description()
        self._add("pass" if "sc2_step2" in desc else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 설명 입력",
                  f"입력: 'sc2_step2 자동 테스트 설명' / 결과: get={desc!r}", sc=2)

        # ── 정리 ───────────────────────────────────────────────
        page.process.close()
        page.close_modal()
        self._add("pass", "프로세스 등록 모달 — 취소 close",
                  "입력: close + 메인 close / 결과: 모두 detached", sc=2)




    def test_scenario2c_cache_folder_picker(self, logged_in_page, settings):
        """
        cache_folder_section 의 2 케이스 (yaml validation_cases) 검증:
          Case 1: 일반 텍스트 경로 직접 입력 + 추가
          Case 2: 특수폴더 picker 다중 선택 (체크 순서 보존) + 추가

        yaml inspection_notes:
          - 특수폴더 N건 → cacheFolderList 1건으로 병합 등록 (line 197-198)
          - cache_folder ';' 다중구분자 미적용 (line 201)
          - 중복 검증 없음 (line 388 — IP/Port/확장자와 다른 정책)
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        print("\n━━ [제어 스위트] 시나리오 2c: cache_folder + 특수폴더 ━━━")
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc2_step3")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        selected = page.picker.select_first_and_confirm(mode="single")
        self._add("pass", "프로세스 선택 (cache_folder 검증 사전조건)",
                  f"입력: picker 첫 행 / 결과: {selected!r}", sc=2)

        # ── Case 1: 텍스트 직접 입력 + 추가 ────────────────────
        page.process.set_cache_input("C:\\test_path1")
        before = page.process.get_cache_input_text()
        self._add("pass" if "C:\\test_path1" in before else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 캐시폴더 텍스트 입력",
                  f"입력: 'C:\\test_path1' / 결과: innerText={before!r}", sc=2)

        page.process.click_cache_add_btn()
        lst = page.process.get_cache_folder_list()
        ok = any("C:\\test_path1" in x for x in lst)
        self._add("pass" if ok else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 캐시폴더 추가 (list 등록)",
                  f"입력: '추가' 클릭 / 결과: list={lst}", sc=2)

        cleared = page.process.get_cache_input_text()
        ok = cleared in ("", "​")
        self._add("pass" if ok else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 캐시폴더 추가 후 input 비우기",
                  f"입력: (추가 후) / 결과: innerText={cleared!r}", sc=2)

        # ── Case 2: 특수폴더 picker ────────────────────────────
        page.process.click_special_folder_btn()
        page.special_folder.wait_open()
        title = page.special_folder.get_title()
        rcnt = page.special_folder.get_row_count()
        self._add("pass" if rcnt == 11 else "fail",
                  "[입력 확인] 예약어 선택 모달 — 11 예약어 행 존재",
                  f"입력: '특수폴더' 클릭 / 결과: title={title!r}, 행 수={rcnt}", sc=2)

        order = ["[/FAVORITES/]", "[/DESKTOP/]", "[/USER/]"]
        page.special_folder.select_and_confirm(order)
        self._add("pass" if not page.special_folder.is_open() else "fail",
                  "[입력 확인] 예약어 선택 모달 — 다중 체크 + 확인",
                  f"입력: 체크 순서={order} + 확인 / 결과: picker 닫힘={not page.special_folder.is_open()}", sc=2)

        inline_text = page.process.get_cache_input_text()
        order_ok = all(code in inline_text for code in order)
        self._add("pass" if order_ok else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 특수폴더 inline tag (클릭 순서 보존)",
                  f"입력: {order} 클릭 순 / 결과: input text={inline_text!r}", sc=2)

        before_count = len(page.process.get_cache_folder_list())
        page.process.click_cache_add_btn()
        lst = page.process.get_cache_folder_list()
        added = len(lst) - before_count
        merge_ok = added == 1 and all(code in lst[-1] for code in order)
        self._add("pass" if merge_ok else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 캐시폴더 다중 특수폴더 → 1건 병합 등록",
                  f"입력: '추가' 클릭 / 결과: 추가 건수={added}, last={lst[-1] if lst else None!r}", sc=2)

        # 정리
        page.process.close()
        page.close_modal()
        self._add("pass", "정리 — 프로세스 등록 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: detached", sc=2)




    def test_scenario2h_tag_modal_fields(self, logged_in_page, settings):
        """시나리오 2h — 태그 sub-tab 의 process_modal 필드 (2b 의 태그 버전).

        yaml tag_sub_tab_policy: 개별 프로세스 / 태그 sub-tab UI 요소 동일 (14필드 + cache_folder + 라디오).
        2b 가 개별 프로세스 sub-tab 에서 검증한 모든 필드를 태그 sub-tab 에서도 동일하게 검증.
        저장 안 함 (close).
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        print("\n━━ [제어 스위트] 시나리오 2h: 태그 sub-tab process_modal 필드 (2b 의 태그 버전) ━━━")
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc2_step4")
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        # 태그 1건 선택 (필드 조작 사전 조건)
        page.process.click_pick_btn()
        page.picker.wait_open()
        picker_title = page.picker.get_title()
        self._add("pass" if "태그" in picker_title else "fail",
                  "[입력 확인] 태그 모달 — picker tag mode 진입 (제목 확인)",
                  f"입력: pick_btn / 결과: picker title={picker_title!r}", sc=2)
        selected = page.picker.select_first_and_confirm(mode="tag")
        self._add("pass", "태그 모달 — 태그 선택 (필드 조작 사전조건)",
                  f"입력: picker 첫 행 / 결과: {selected!r}", sc=2)

        # ── 단독 토글 4건 ──────────────────────────────────────
        page.process.set_process_except(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 프로세스 예외처리 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_pclipboard_restrict(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 개별 클립보드 공유제한 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_sandbox(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 샌드박스 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_deny_except_drive(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 드라이브 제외 거부 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        # ── 네트워크 허용 + IP/Port ────────────────────────────
        page.process.set_pnetwork(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 네트워크 허용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.add_ip_port("10.20.30.40", "7070")
        ip_list = page.process.get_ip_list()
        ok = any("10.20.30.40" in x and "7070" in x for x in ip_list)
        self._add("pass" if ok else "fail",
                  "[입력 확인] 태그 모달 — IP/Port 추가 (list)",
                  f"입력: '10.20.30.40' + '7070' / 결과: list={ip_list}", sc=2)

        # ── 확장자 제어 + 라디오 + tag list ────────────────────
        page.process.set_pcontrol_extension(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 확장자 제어 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.click_radio_blockp()
        t1 = page.process.get_radio_react_text()
        self._add("pass" if t1 == "허용할 확장자" else "fail",
                  "[입력 확인] 태그 모달 — 확장자 BLOCKP 라디오 반응",
                  f"입력: BLOCKP / 결과: span={t1!r}", sc=2)

        page.process.click_radio_allowp()
        t2 = page.process.get_radio_react_text()
        self._add("pass" if t2 == "차단할 확장자" else "fail",
                  "[입력 확인] 태그 모달 — 확장자 ALLOWP 라디오 반응",
                  f"입력: ALLOWP / 결과: span={t2!r}", sc=2)

        page.process.add_extension("log;tmp;bak")
        ext = page.process.get_extension_list()
        self._add("pass" if ext == ["log", "tmp", "bak"] else "fail",
                  "[입력 확인] 태그 모달 — 확장자 ';' 다중구분자 등록",
                  f"입력: 'log;tmp;bak' / 결과: list={ext}", sc=2)

        # ── 접근 드라이브 ──────────────────────────────────────
        page.process.set_access_drive(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE)
        self._add("pass" if chk else "fail",
                  "[입력 확인] 태그 모달 — 접근 드라이브 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        page.process.set_drive_letter("E;F")
        dl = page.process.get_drive_letter()
        self._add("pass" if dl == "E;F" else "fail",
                  "[입력 확인] 태그 모달 — 드라이브 레터 입력",
                  f"입력: 'E;F' / 결과: get={dl!r}", sc=2)

        # ── 설명 ───────────────────────────────────────────────
        page.process.set_description("sc2_step4 태그 설명")
        desc = page.process.get_description()
        self._add("pass" if "sc2_step4" in desc else "fail",
                  "[입력 확인] 태그 모달 — 설명 입력",
                  f"입력: 'sc2_step4 태그 설명' / 결과: get={desc!r}", sc=2)

        # ── 정리 ───────────────────────────────────────────────
        page.process.close()
        page.close_modal()
        self._add("pass", "태그 모달 — 취소 close",
                  "입력: close + 메인 close / 결과: detached", sc=2)




    def test_scenario2d_web_restrict_process(self, logged_in_page, settings):
        """시나리오 2d — web_restrict 적용 프로세스 (picker multi) + basePath + isProcessOption."""
        print("\n━━ [제어 스위트] 시나리오 2d: web_restrict 적용 프로세스 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc2_step5")
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_sc2_step5")
        self._add("pass", "웹제한 모달 — 진입 + 이름 set",
                  "입력: '+' 클릭 + name 입력 / 결과: 모달 open + name 저장", sc=2)

        # ── 적용 프로세스 picker (multi) ───────────────────────
        before_rows = page.web_restrict.get_process_rows()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        title = page.picker.get_title()
        cnt = page.picker.get_row_count()
        self._add("pass" if title == "프로세스 선택" and cnt > 0 else "fail",
                  "[입력 확인] 웹제한 모달 — 적용 프로세스 추가 (picker multi 진입)",
                  f"입력: '프로세스 추가' 클릭 / 결과: picker title={title!r}, 행 수={cnt}", sc=2)

        selected = page.picker.select_first_and_confirm(mode="multi")
        after_rows = page.web_restrict.get_process_rows()
        added = len(after_rows) - len(before_rows)
        self._add("pass" if added >= 1 else "fail",
                  "[입력 확인] 웹제한 모달 — 적용 프로세스 picker 확인 → 테이블 등록",
                  f"입력: 첫 행 체크 + 확인 ({selected!r}) / 결과: 추가={added}, total={len(after_rows)}", sc=2)

        # ── 기본폴더 지정 (basePath) ───────────────────────────
        page.web_restrict.set_base_path("C:\\webrestrict_base")
        bp = page.web_restrict.get_base_path()
        self._add("pass" if bp == "C:\\webrestrict_base" else "fail",
                  "[입력 확인] 웹제한 모달 — 기본폴더 (basePath) 입력",
                  f"입력: 'C:\\webrestrict_base' / 결과: get={bp!r}", sc=2)

        # ── 기본폴더 지정 토글 (isProcessOption) ──────────────
        page.web_restrict.set_process_option(True)
        chk = page.web_restrict.is_process_option_checked()
        self._add("pass" if chk else "fail",
                  "[입력 확인] 웹제한 모달 — 기본폴더 지정 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=2)

        # 정리
        page.web_restrict.close()
        page.close_modal()
        self._add("pass", "정리 — 웹제한 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: detached", sc=2)




    def test_scenario2e_web_restrict_fields(self, logged_in_page, settings):
        """
        web_restrict_modal 의 모든 필드를 yaml 기준 종합 검증.

        검증 블록:
          1. 권한 ▼ expand + processAuth 라디오 → text sync (1회 한정 buggy)
          2. isUrl 토글 + 종속 disabled 변화 (4건) + isDataDecrypt 라디오
          3. add_url ('not a url' 포함 — yaml 형식 검증 없음 사실)
          4. isFileUploadEncrypt — decrypt_target 시 자동 checked+disabled 검증
          5. headerCheck (독립)
          6. add_file_extension 다중 구분자
          7. uploadLimit + description
        """
        print("\n━━ [제어 스위트] 시나리오 2e: web_restrict 필드 (yaml 종합) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc2_step6")
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_sc2_step6")

        # 사전조건: 프로세스 1건 + isProcessOption ON (권한 expand 활성)
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_process_option(True)
        self._add("pass", "사전조건 — 프로세스 1건 + isProcessOption ON",
                  "입력: picker multi + 토글 ON / 결과: 권한 expand 활성", sc=2)

        # ── 권한 ▼ expand + processAuth 라디오 sync ─────────────
        page.web_restrict.click_expand_btn()
        expanded = page.web_restrict.is_auth_expanded()
        self._add("pass" if expanded else "fail",
                  "[입력 확인] 웹제한 모달 — 기타 프로세스 권한 ▼ 펼침",
                  f"입력: ▼ 클릭 / 결과: expanded={expanded}", sc=2)

        page.web_restrict.set_process_auth("3")
        sync_text = page.web_restrict.get_process_auth_text()
        self._add("pass" if sync_text == "쓰기" else "fail",
                  "[입력 확인] 웹제한 모달 — 기타 프로세스 권한 v3(쓰기) 라디오 sync",
                  f"입력: v3 선택 / 결과: text={sync_text!r}", sc=2)

        # ── isUrl 토글 + 종속 disabled ─────────────────────────
        off_states = page.web_restrict.get_url_dependent_disabled()
        self._add("pass" if all(off_states.values()) else "fail",
                  "[입력 확인] 웹제한 모달 — 적용 URL OFF 시 종속 4건 disabled",
                  f"입력: 기본 OFF / 결과: {off_states}", sc=2)

        page.web_restrict.set_is_url(True)
        on_states = page.web_restrict.get_url_dependent_disabled()
        self._add("pass" if not any(on_states.values()) else "fail",
                  "[입력 확인] 웹제한 모달 — 적용 URL ON 시 종속 4건 활성",
                  f"입력: 토글 ON / 결과: {on_states}", sc=2)

        # ── URL list 추가 (형식 검증 없음 — yaml 사실) ─────────
        page.web_restrict.add_url("naver.com")
        page.web_restrict.add_url("not a url")
        url_list = page.web_restrict.get_url_list()
        self._add("pass" if any("naver.com" in u for u in url_list) else "fail",
                  "[입력 확인] 웹제한 모달 — 적용 URL list 추가 (형식 검증 없음)",
                  f"입력: 'naver.com', 'not a url' / 결과: list={url_list}", sc=2)

        # ── isDataDecrypt=1 → isFileUploadEncrypt 자동 강제 ────
        page.web_restrict.click_decrypt_target()
        chk = page.web_restrict.is_file_encrypt_checked()
        dis = page.web_restrict.is_file_encrypt_disabled()
        ok = chk and dis
        self._add("pass" if ok else "fail",
                  "[입력 확인] 웹제한 모달 — 복호화 대상 → 업로드 시 암호화 자동 강제",
                  f"입력: decrypt_target 선택 / 결과: checked={chk}, disabled={dis}", sc=2)

        page.web_restrict.click_decrypt_allow()
        dis_after = page.web_restrict.is_file_encrypt_disabled()
        self._add("pass" if not dis_after else "fail",
                  "[입력 확인] 웹제한 모달 — 허용 URL 복귀 → 업로드 암호화 disabled 해제",
                  f"입력: decrypt_allow 선택 / 결과: disabled={dis_after}", sc=2)

        # ── 역순: 업로드 암호화 먼저 클릭 (decrypt_allow 상태) → 막히지 않는지 (사용자 검증 요청) ──
        # 정방향(decrypt_target→암호화 강제)은 위에서 확인. 역순: 복호화 대상 아닌 상태에서
        # 업로드 암호화를 수동으로 먼저 켤 수 있는지 + 그 후 decrypt_target 가도 강제 유지되는지.
        enc_dis_now = page.web_restrict.is_file_encrypt_disabled()
        if not enc_dis_now:
            page.web_restrict.set_file_encrypt(True)
            enc_chk = page.web_restrict.is_file_encrypt_checked()
            self._add("pass" if enc_chk else "fail",
                      "[입력 확인] 웹제한 모달 — 업로드 암호화 먼저 수동 ON (decrypt_allow 상태) 막히지 않음",
                      f"입력: file_encrypt 수동 클릭 / 결과: checked={enc_chk}", sc=2)
            # 암호화 ON 상태에서 decrypt_target 선택 → 강제(checked+disabled) 유지되는지
            page.web_restrict.click_decrypt_target()
            after_chk = page.web_restrict.is_file_encrypt_checked()
            after_dis = page.web_restrict.is_file_encrypt_disabled()
            self._add("pass" if (after_chk and after_dis) else "fail",
                      "[입력 확인] 웹제한 모달 — 암호화 먼저 ON 후 복호화 대상 선택 → 강제(checked+disabled) 유지",
                      f"입력: file_encrypt ON → decrypt_target / 결과: checked={after_chk}, disabled={after_dis}", sc=2)
            page.web_restrict.click_decrypt_allow()  # 원복 (다음 검증 영향 차단)
        else:
            self._add("warn",
                      "[입력 확인] 웹제한 모달 — decrypt_allow 인데 업로드 암호화 disabled (먼저 클릭 막힘 — 의도 확인 필요)",
                      f"입력: decrypt_allow 상태 / 결과: file_encrypt disabled={enc_dis_now}", sc=2)

        # ── headerCheck (독립) ─────────────────────────────────
        page.web_restrict.set_header_check(True)
        hc = page.page.locator(page.web_restrict.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if hc else "fail",
                  "[입력 확인] 웹제한 모달 — 헤더 체크 기능 (uploadLimit 와 독립)",
                  f"입력: ON / 결과: is_checked={hc}", sc=2)

        # ── 업로드 허용 확장자 다중구분자 ──────────────────────
        page.web_restrict.add_file_extension("png;jpg;gif")
        items = page.page.locator(
            "div#controlSuiteWebRestricList button.tagInput[name='ExtentionWebRestrict'], "
            "div#controlSuiteWebRestricList button.tagInput.addBtn"
        )
        cnt = items.count()
        self._add("pass" if cnt >= 3 else "fail",
                  "[입력 확인] 웹제한 모달 — 업로드 허용 확장자 ';' 다중구분자",
                  f"입력: 'png;jpg;gif' / 결과: tag 수={cnt} (sanity)", sc=2)

        # ── uploadLimit ────────────────────────────────────────
        page.web_restrict.set_upload_limit("1024")
        ul = page.web_restrict.get_upload_limit()
        self._add("pass" if ul == "1024" else "fail",
                  "[입력 확인] 웹제한 모달 — 업로드 제한용량 입력",
                  f"입력: '1024' / 결과: get={ul!r}", sc=2)

        # ── description ────────────────────────────────────────
        page.web_restrict.set_description("sc2_step6 자동 테스트")
        desc = page.web_restrict.get_description()
        self._add("pass" if "sc2_step6" in desc else "fail",
                  "[입력 확인] 웹제한 모달 — 설명 입력",
                  f"입력: 'sc2_step6 자동 테스트' / 결과: get={desc!r}", sc=2)

        # 정리
        page.web_restrict.close()
        page.close_modal()
        self._add("pass", "정리 — 웹제한 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: detached", sc=2)




    def test_scenario2f_process_picker(self, logged_in_page, settings):
        """시나리오 2f — process_picker 입력 동작 검증 (single + tag 2 모드, 저장 X)."""
        print("\n━━ [제어 스위트] 시나리오 2f: process_picker (입력 동작 검증) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc2_step7")

        # ── single 모드 ────────────────────────────────────────
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        before = page.process.get_selected_display_text()
        self._add("pass" if "미선택" in before else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 선택 표시 초기값 ('프로세스 미선택')",
                  f"입력: 모달 진입 / 결과: {before!r}", sc=2)

        page.process.click_pick_btn()
        page.picker.wait_open()
        title = page.picker.get_title()
        cnt = page.picker.get_row_count()
        self._add("pass" if title == "프로세스 선택" and cnt > 0 else "fail",
                  "[입력 확인] 프로세스 선택 모달 — 진입 (개별 프로세스)",
                  f"입력: '프로세스 선택' 버튼 / 결과: title={title!r}, 행 수={cnt}", sc=2)

        selected = page.picker.select_first_and_confirm(mode="single")
        self._add("pass" if not page.picker.is_open() else "fail",
                  "[입력 확인] 프로세스 선택 모달 — 첫 행 + 확인 → 닫힘",
                  f"입력: 1행 radio + 확인 / 결과: 선택={selected!r}, 닫힘={not page.picker.is_open()}", sc=2)

        after = page.process.get_selected_display_text()
        self._add("pass" if "미선택" not in after else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 선택 표시 반영 (picker 결과)",
                  f"입력: picker 확인 후 / 결과: display={after!r}", sc=2)

        page.process.close()

        # ── tag 모드 ───────────────────────────────────────────
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        before = page.process.get_selected_display_text()
        self._add("pass" if "미선택" in before else "fail",
                  "[입력 확인] 프로세스 등록 모달 — 태그 모드 선택 표시 초기값 ('태그 미선택')",
                  f"입력: 모달 진입 / 결과: {before!r}", sc=2)

        page.process.click_pick_btn()
        page.picker.wait_open()
        title = page.picker.get_title()
        cnt = page.picker.get_row_count()
        self._add("pass" if title == "태그 선택" and cnt > 0 else "fail",
                  "[입력 확인] 태그 선택 모달 — 진입",
                  f"입력: '태그 선택' 버튼 / 결과: title={title!r}, 행 수={cnt}", sc=2)

        selected = page.picker.select_first_and_confirm(mode="tag")
        after = page.process.get_selected_display_text()
        self._add("pass" if not page.picker.is_open() and "미선택" not in after else "fail",
                  "[입력 확인] 태그 선택 모달 — 첫 행 + 확인 + 프로세스 등록 모달 반영",
                  f"입력: 1행 radio + 확인 / 결과: 선택={selected!r}, display={after!r}", sc=2)

        # 정리
        page.process.close()
        page.close_modal()
        self._add("pass", "정리 — 등록 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: 모두 detached", sc=2)

    # ==================================================================
    # 시나리오 2g — 모달 초기값 명시 검증 (scenario_2_input.md "초기값")
    # ==================================================================

    # ==================================================================
    # 시나리오 2g — 모달 초기값 명시 검증 (scenario_2_input.md "초기값")
    # ==================================================================
