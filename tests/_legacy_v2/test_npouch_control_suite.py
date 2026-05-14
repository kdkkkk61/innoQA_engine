"""
nPouch 제어 스위트 관리 테스트 — yaml v42 기반

yaml: config/scan_hints/control_suite.yaml
page: pages/npouch_control_suite_page.py (composition)

테스트 시나리오 구조 (docs/test_scenario_standard.md):
  scenario_1_ui         UI 구조 스캔
  scenario_2_input      입력 구조 (필드 존재 / 초기값 / maxlength / 필수 검증 1차)
  scenario_3_add        ADD 흐름 + 동작 검증 (글자수/입력 형식/중복/다중 구분자)
  scenario_4_modify     EDIT 흐름 + 저장 정합성 + ADD-EDIT 회귀 검증
  scenario_5_case       정상 입력 조합별 저장 정합성 (cross-field)
  scenario_6_setup      cross-page data prep ([AUTO_KEEP]_*)

데이터 안전 규칙 (CLAUDE.md):
  - [AUTO] 접두사만 생성/삭제 가능
  - [AUTO_KEEP] 접두사: 시나리오 6 cross-page 데이터, 세션 보존

자동화 한계 (yaml inspection_notes):
  - row_active_timing_after_modal_close — reload 후 첫 click 권장
  - auth_text_sync_once_only — 제품 buggy, EDIT 재오픈 시 라디오 V 기준 저장값 검증
  - cache_folder_no_duplicate_check / no_multi_separator — 의도/회귀 구분
  - add_vs_edit_csu_name_empty_message_diff — must_test
"""
import pytest
from pages.npouch_control_suite_page import NpouchControlSuitePage


class TestNpouchControlSuite:

    # ==================================================================
    # 시나리오 3 — ADD 흐름 + 동작 검증
    # ==================================================================
    @pytest.mark.dependency(name="suite_add_lifecycle")
    def test_scenario3_add_full_cycle(self, logged_in_page, settings):
        """
        ADD 전체 사이클 — 메인 모달 + process_modal + web_restrict + 저장.
        모든 동작 한 사이클로 — 시나리오 3 의 핵심 자동 검증.
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        page.navigate_to()

        # 잔여 [AUTO] 정리
        page.delete_all_auto_policies()

        # 1. 메인 모달 진입
        page.open_add_modal()
        assert page.get_modal_title() == "제어 스위트 추가"

        # 2. csuName 글자수 절단 검증 (100자 → 50자)
        long_name = "a" * 100
        page.set_csu_name(long_name)
        assert len(page.get_csu_name()) == 50, "DOM maxlength=50 자동 절단 실패"

        # 3. 정상 이름 + 메인 필드
        page.set_csu_name("[AUTO]_scenario3_full")
        page.set_clipboard_restrict_toggle(True)
        page.set_clipboard_allow_url("naver.com;google.com")

        # 4. 라디오 반응 검증 (ALLOW↔BLOCK)
        page.click_radio_block()
        assert page.get_radio_react_text() == "허용할 확장자"
        page.click_radio_allow()
        assert page.get_radio_react_text() == "차단할 확장자"

        # 5. 확장자 — 한글 차단 / 다중 분리 / 중복 차단
        page.add_main_extension("한글확장자")
        assert page.is_confirm_modal_visible()
        assert "한글이 포함된 확장자" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        page.add_main_extension("txt;doc;exe")
        assert page.get_main_extension_list() == ["txt", "doc", "exe"], "; 다중 분리 실패"

        page.add_main_extension("txt")
        assert page.is_confirm_modal_visible()
        assert "이미 동일한 확장자가 존재합니다" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        # 6. 전자서명 — 추가/삭제
        page.set_sign_except_toggle(True)
        page.add_sign_except("Claude Code Sign")
        page.add_sign_except("Innotium Inc Signing")
        signs = page.get_sign_except_list()
        assert len(signs) == 2
        page.delete_sign_except("Claude Code Sign")
        assert len(page.get_sign_except_list()) == 1

        # 7. process_modal 진입
        page.click_individual_process_tab()
        page.click_add_process_btn()
        assert page.process.get_title() == "프로세스 등록"
        assert page.process.detect_mode() == "process"

        # 8. 프로세스 선택 (single_select)
        page.process.click_pick_btn()
        page.picker.wait_open()
        assert page.picker.get_title() == "프로세스 선택"
        page.picker.select_first_and_confirm(mode="single")

        # 9. process_modal 토글 + 종속
        page.process.set_pnetwork(True)
        page.process.add_ip_port("192.168.1.1", "8080")
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        text, cls = page.process.get_radio_react_span()
        assert text == "차단할 확장자" and "redTxt" in cls
        page.process.add_extension("log;tmp;bak")
        assert page.process.get_extension_list() == ["log", "tmp", "bak"]

        # 10. cache_folder + 특수폴더
        page.process.set_cache_input("C:\\test_cache")
        page.process.click_cache_add_btn()
        assert "C:\\test_cache" in page.process.get_cache_folder_list()

        page.process.click_special_folder_btn()
        page.special_folder.select_and_confirm(["[/DESKTOP/]", "[/FAVORITES/]"])
        page.process.click_cache_add_btn()
        # 특수폴더 다중 → 1건 병합 의도된 디자인
        assert any("[/DESKTOP/]" in v and "[/FAVORITES/]" in v
                   for v in page.process.get_cache_folder_list())

        # 11. process_modal 저장 → 메인 itemList 등록
        page.process.confirm()
        page.process.wait_closed()
        rows = page.get_item_list_rows()
        assert len(rows) == 1, "process_modal 저장 후 itemList 1행 등록 실패"

        # 12. 메인 저장
        msg = page.save_policy(mode="add")
        assert msg == "저장 하였습니다"
        assert page.is_policy_exists("[AUTO]_scenario3_full")

    # ==================================================================
    # 시나리오 3 — 입력 검증 메시지 (validation_rules)
    # ==================================================================
    @pytest.mark.dependency(name="suite_input_validation")
    def test_scenario3_input_validation(self, logged_in_page, settings):
        """ADD 흐름 안 IP/Port/URL/description 의 검증 메시지 캡처."""
        page = NpouchControlSuitePage(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_input_validation")

        # process_modal 진입
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.click_pick_btn()
        page.picker.select_first_and_confirm(mode="single")

        # IP 비정상
        page.process.set_pnetwork(True)
        page.process.add_ip_port("abc.def.ghi.jkl", "8080")
        assert "아이피 주소 형식" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        # Port 형식
        page.process.add_ip_port("192.168.1.1", "abc")
        assert "Port 형식" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        # Port 최대값 초과
        page.process.add_ip_port("192.168.1.1", "70000")
        assert "Port의 최대값은 65535" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        # 정상 IP+Port 등록
        page.process.add_ip_port("192.168.1.1", "80")

        # IP+Port 중복
        page.process.add_ip_port("192.168.1.1", "80")
        assert "이미 등록된 IP와 Port" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        # description 1000자 → 서버 제한 300자
        page.process.set_description("가" * 1000)
        page.process.confirm()
        assert "최대 300자" in page.get_confirm_message()
        page.dismiss_confirm_modal()

        # 정리 — 모달 취소
        page.process.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 4 — EDIT 흐름 + ADD-EDIT 회귀 검증
    # ==================================================================
    @pytest.mark.dependency(name="suite_edit_cycle", depends=["suite_add_lifecycle"])
    def test_scenario4_edit_full_cycle(self, logged_in_page, settings):
        """
        시나리오 3 에서 만든 [AUTO]_scenario3_full 정책 EDIT.
        값 정합성 + ADD-EDIT 회귀 + csuName 빈값 메시지 차이 검증.
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        page.navigate_to()

        if not page.is_policy_exists("[AUTO]_scenario3_full"):
            pytest.skip("[AUTO]_scenario3_full 정책 없음 — 시나리오 3 먼저 실행 필요")

        # EDIT 진입 + 제목 회귀 검증
        page.open_modify_modal("[AUTO]_scenario3_full")
        assert page.get_modal_title() == "제어 스위트 수정"
        assert page.is_edit_mode()

        # 값 로드 정합성
        v = page.get_verify_values()
        assert v["csu_name"] == "[AUTO]_scenario3_full"
        assert v["clipboard_restrict"] is True
        assert "naver.com" in v["clipboard_url"]

        # csuName 빈값 — EDIT 메시지 차이 (must_test)
        page.set_csu_name("")
        page.click_submit_modify()
        assert page.is_confirm_modal_visible()
        msg = page.get_confirm_message()
        assert msg == "정책 이름을 입력해 주세요.", \
            f"EDIT csuName 빈값 메시지 회귀: {msg!r}"
        page.dismiss_confirm_modal()

        # 정상 변경 + 저장
        page.set_csu_name("[AUTO]_scenario4")
        save_msg = page.save_policy(mode="modify")
        assert save_msg == "저장 하였습니다"
        assert page.is_policy_exists("[AUTO]_scenario4")

    # ==================================================================
    # 시나리오 4 — 권한 라디오 sync stuck (제품 buggy 회귀 검증)
    # ==================================================================
    def test_scenario4_auth_text_sync_stuck(self, logged_in_page, settings):
        """
        yaml auth_text_sync_once_only: 권한 라디오 → inline text sync 첫 변경만 동작.
        제품 buggy 확정 — 회귀 시 stuck 사라지면 fail.
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_auth_sync_test")

        # process_modal 통해 프로세스 1건 등록 (메인 저장 가능 조건)
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.click_pick_btn()
        page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()
        page.process.wait_closed()

        # web_restrict 진입
        page.click_add_web_restrict_btn()
        page.web_restrict.set_name("[AUTO]_web_sync")
        page.web_restrict.click_add_process_btn()
        page.picker.select_first_and_confirm(mode="multi")

        # 권한 영역 expand + 라디오 사이클 — stuck 검증
        page.web_restrict.click_expand_btn()
        assert page.web_restrict.is_auth_expanded()

        page.web_restrict.set_process_auth("3")    # 쓰기
        first_text = page.web_restrict.get_process_auth_text()
        assert first_text == "쓰기", "첫 sync 실패"

        page.web_restrict.set_process_auth("1")    # 거부 — stuck 예상
        stuck_text_1 = page.web_restrict.get_process_auth_text()
        page.web_restrict.set_process_auth("2")    # 읽기 — stuck 예상
        stuck_text_2 = page.web_restrict.get_process_auth_text()

        # 제품 buggy: 두 번째 이후 sync 안 됨
        assert stuck_text_1 == "쓰기", \
            f"sync stuck 해소? (회귀 가능성): text={stuck_text_1!r}"
        assert stuck_text_2 == "쓰기", \
            f"sync stuck 해소? (회귀 가능성): text={stuck_text_2!r}"

        # 정리
        page.web_restrict.close()
        page.close_modal()

    # ==================================================================
    # 정리 — [AUTO] 정책 일괄 삭제
    # ==================================================================
    def test_cleanup_auto_policies(self, logged_in_page, settings):
        """모든 [AUTO] 접두사 정책 삭제. [AUTO_KEEP] 은 보존."""
        page = NpouchControlSuitePage(logged_in_page, settings)
        page.navigate_to()
        page.delete_all_auto_policies()
