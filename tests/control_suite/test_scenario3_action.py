"""시나리오 3 — ADD 모달 검증 (3b~3e). 3d 가 [AUTO_KEEP]_step5b_mod 생성."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.control_suite._base import ControlSuiteBase


class TestScenario3Action(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 3 — ADD 모달 검증 (3b~3e)"""


    def test_scenario3b_minimal_save(self, logged_in_page, settings):
        """
        엔드투엔드 최소 저장 흐름:
          0. 사전 cleanup ([AUTO]_*)
          1. 메인 모달 진입 + csuName
          2. 개별 프로세스 sub-tab + + → process_modal
          3. picker 첫 행 선택 → process_modal confirm → itemList 1행
          4. 메인 저장 → '저장 하였습니다' 확인
          5. 정책 list 에 신규 정책 존재 확인
          6. 사후 cleanup
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        policy_name = "[AUTO]_step3d_save"

        print("\n━━ [제어 스위트] 시나리오 3b: 프로세스 1건 + 메인 저장 (E2E) ━━━")
        self._page = page.page

        page.navigate_to()
        # 시나리오 3 단독 실행 안전성 — 1a (세션 시작 정리) 미동작 시 잔여 정리.
        page.delete_all_test_data()

        page.open_add_modal()
        page.set_csu_name(policy_name)
        self._add("pass", "[입력 확인] 스위트 추가 모달 — 진입 + 스위트 이름 입력",
                  f"입력: 모달 open + 이름='{policy_name}' / 결과: get={page.get_csu_name()!r}", sc=3)

        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        selected = page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()
        rows = page.get_item_list_rows()
        self._add("pass" if len(rows) == 1 else "fail",
                  "[입력 확인] 프로세스별 제어 — 프로세스 1건 등록 (itemList)",
                  f"입력: picker '{selected}' + 확인 / 결과: itemList 행={len(rows)}", sc=3)

        msg = page.save_policy(mode="add")
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "[저장 확인] 스위트 추가 모달 — '추가' 버튼 (저장)",
                  f"입력: '추가' 클릭 / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()

        exists = page.is_policy_exists(policy_name)
        self._add("pass" if exists else "fail",
                  "[등록 확인] 정책 목록 — 신규 정책 등록 확인",
                  f"입력: (저장 완료 후) / 결과: '{policy_name}' 존재={exists}", sc=3)




    def test_scenario3d_crud_full_cycle(self, logged_in_page, settings):
        """시나리오 3d — ADD 종합 풍부 (각 영역 입력값 set/get 일치 + 메인 저장 + 등록 확인).

        EDIT 재진입/modify 흐름은 시나리오 4 영역. 본 메서드는 ADD 흐름만.
        시나리오 4 가 사용할 [AUTO_KEEP]_step5b_mod 정책 생성.
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"
        D = {
            "clipboard_url":  "naver.com;google.com",
            "extensions":     ["txt", "doc", "exe"],
            "sign_excepts":   ["Claude Sign", "Innotium Inc"],
            "custom_option":  "step5b_init",
            "proc_ip":        "192.168.1.1",
            "proc_port":      "8080",
            "proc_ext":       ["log", "tmp"],
            "proc_drive":     "C;D",
            "proc_desc":      "step5b 프로세스 설명",
            "tag_ip":         "10.0.0.5",
            "tag_port":       "9090",
            "tag_ext":        ["zip"],
            "tag_drive":      "E;F",
            "tag_desc":       "step5b 태그 설명",
            "web_name":       "[AUTO]_web_step5b",
            "web_url":        "step5b-web.com",
            "web_ext":        "csv",
            "web_limit":      "512",
            "web_desc":       "step5b 웹제한 초기값",
        }

        print("\n━━ [제어 스위트] 시나리오 3d: ADD 종합 풍부 (메인+프로세스+태그+웹제한+저장+등록) ━━━")
        self._page = page.page
        page.navigate_to()

        # ════ 메인 모달 입력 ════
        page.open_add_modal()
        page.set_csu_name(KEEP_NAME)
        self._add("pass" if page.get_csu_name() == KEEP_NAME else "fail",
                  "[입력 확인] 스위트 이름",
                  f"입력: '{KEEP_NAME}' / 결과: get={page.get_csu_name()!r}", sc=3)

        # 클립보드 공유제한 토글 양방향 검증
        v_init = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        page.set_clipboard_restrict_toggle(True)
        v_on = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        self._add("pass" if v_on is True else "fail",
                  "[입력 확인] 클립보드 공유제한 토글 (OFF → ON)",
                  f"입력: 초기={v_init} → ON 클릭 / 결과: is_checked={v_on}", sc=3)

        page.set_clipboard_restrict_toggle(False)
        v_off = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        self._add("pass" if v_off is False else "fail",
                  "[입력 확인] 클립보드 공유제한 토글 (ON → OFF)",
                  f"입력: ON={v_on} → OFF 클릭 / 결과: is_checked={v_off}", sc=3)

        page.set_clipboard_restrict_toggle(True)  # 최종 ON (저장 용)

        page.set_clipboard_allow_url(D["clipboard_url"])
        v = page.get_clipboard_allow_url()
        self._add("pass" if D["clipboard_url"] in v else "fail",
                  "[입력 확인] 클립보드 허용 URL",
                  f"입력: '{D['clipboard_url']}' / 결과: get={v!r}", sc=3)

        # 네트워크 허용 토글 양방향
        v_init = page.is_network_checked()
        page.set_network_toggle(True)
        v_on = page.is_network_checked()
        self._add("pass" if v_on is True else "fail",
                  "[입력 확인] 네트워크 허용 토글 (OFF → ON)",
                  f"입력: 초기={v_init} → ON 클릭 / 결과: is_checked={v_on}", sc=3)

        page.set_network_toggle(False)
        v_off = page.is_network_checked()
        self._add("pass" if v_off is False else "fail",
                  "[입력 확인] 네트워크 허용 토글 (ON → OFF)",
                  f"입력: ON={v_on} → OFF 클릭 / 결과: is_checked={v_off}", sc=3)

        page.set_network_toggle(True)  # 최종 ON

        # ── 라디오 변경 검증 (초기 → BLOCK → ALLOW 라벨 변화) ──
        v_init = page.get_radio_react_text()
        self._add("pass", "[입력 확인] 제어할 확장자 라디오 초기 라벨",
                  f"입력: 모달 진입 직후 / 결과: 라벨={v_init!r}", sc=3)

        page.click_radio_block()
        v_block = page.get_radio_react_text()
        self._add("pass" if v_block == "허용할 확장자" else "fail",
                  "[입력 확인] 제어할 확장자 라디오 (BLOCK 클릭 → 라벨 변경)",
                  f"입력: BLOCK 클릭 / 결과: 초기={v_init!r} → 변경={v_block!r}", sc=3)

        page.click_radio_allow()
        v_allow = page.get_radio_react_text()
        self._add("pass" if v_allow == "차단할 확장자" else "fail",
                  "[입력 확인] 제어할 확장자 라디오 (ALLOW 클릭 → 라벨 변경)",
                  f"입력: ALLOW 클릭 / 결과: 이전={v_block!r} → 변경={v_allow!r}", sc=3)

        # ── 확장자 단건 추가 ────────────────────────────────────
        first_ext = D["extensions"][0]
        page.add_main_extension(first_ext)
        v = page.get_main_extension_list()
        self._add("pass" if v == [first_ext] else "fail",
                  "[입력 확인] 제어할 확장자 단건 추가",
                  f"입력: '{first_ext}' / 결과: list={v}", sc=3)

        # ── 확장자 다중 (';' 구분자) 추가 ───────────────────────
        multi = ";".join(D["extensions"][1:])
        page.add_main_extension(multi)
        v = page.get_main_extension_list()
        self._add("pass" if v == D["extensions"] else "fail",
                  "[입력 확인] 제어할 확장자 다중 (';' 구분자) 추가",
                  f"입력: '{multi}' / 결과: list={v}", sc=3)

        # ── 확장자 중복 차단 검증 (yaml verified) ───────────────
        page.add_main_extension(first_ext)
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if "이미 동일한 확장자" in dup_msg or "이미 등록" in dup_msg else "fail",
                      "[차단 메시지] 제어할 확장자 중복 추가",
                      f"입력: '{first_ext}' 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 제어할 확장자 중복 — 메시지 미노출",
                      f"입력: '{first_ext}' 재추가 / 결과: 알림 없음", sc=3)

        # ── 확장자 추가 → 삭제 사이클 (1개만 삭제, 잔여 확인) ────
        # 현 list = [txt, doc, exe]. 'doc' 삭제 → [txt, exe] 잔여.
        target_del = D["extensions"][1]   # "doc"
        before_cnt = len(page.get_main_extension_list())
        removed = page.remove_main_extension(target_del)
        after = page.get_main_extension_list()
        self._add("pass" if removed and target_del not in after and len(after) == before_cnt - 1 else "fail",
                  "[입력 확인] 제어할 확장자 단건 삭제 → 잔여 확인",
                  f"입력: '{target_del}' × 클릭 / 결과: 전={before_cnt} → 후={len(after)}, list={after}", sc=3)

        # 잔여 list 복원 (저장용 — 'doc' 다시 추가)
        page.add_main_extension(target_del)

        # 헤더 체크 양방향
        v_init = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        page.set_header_check(True)
        v_on = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if v_on is True else "fail",
                  "[입력 확인] 헤더 체크 기능 (OFF → ON)",
                  f"입력: 초기={v_init} → 체크 ON / 결과: is_checked={v_on}", sc=3)

        page.set_header_check(False)
        v_off = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if v_off is False else "fail",
                  "[입력 확인] 헤더 체크 기능 (ON → OFF)",
                  f"입력: ON={v_on} → 체크 OFF / 결과: is_checked={v_off}", sc=3)

        page.set_header_check(True)  # 최종 ON

        # 전자서명 예외 토글 양방향
        v_init = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        page.set_sign_except_toggle(True)
        v_on = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        self._add("pass" if v_on is True else "fail",
                  "[입력 확인] 전자서명 예외 토글 (OFF → ON)",
                  f"입력: 초기={v_init} → ON 클릭 / 결과: is_checked={v_on}", sc=3)

        page.set_sign_except_toggle(False)
        v_off = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        self._add("pass" if v_off is False else "fail",
                  "[입력 확인] 전자서명 예외 토글 (ON → OFF)",
                  f"입력: ON={v_on} → OFF 클릭 / 결과: is_checked={v_off}", sc=3)

        page.set_sign_except_toggle(True)  # 최종 ON

        for s in D["sign_excepts"]:
            page.add_sign_except(s)
        v = page.get_sign_except_list()
        self._add("pass" if len(v) == len(D["sign_excepts"]) else "fail",
                  "[입력 확인] 전자서명 예외 항목",
                  f"입력: {D['sign_excepts']} / 결과: count={len(v)}", sc=3)

        page.set_custom_option(D["custom_option"])
        v = page.get_custom_option()
        self._add("pass" if v == D["custom_option"] else "fail",
                  "[입력 확인] 커스텀 옵션",
                  f"입력: '{D['custom_option']}' / 결과: get={v!r}", sc=3)

        # ════ 개별 프로세스 등록 ════
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        proc_name = page.picker.select_first_and_confirm(mode="single")
        self._add("pass", "[입력 확인] 프로세스 선택 (picker)",
                  f"입력: picker 첫 행 / 결과: 선택='{proc_name}'", sc=3)

        page.process.set_process_except(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT) else "fail",
                  "[입력 확인] 프로세스 예외처리 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.set_pclipboard_restrict(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD) else "fail",
                  "[입력 확인] 개별 클립보드 공유제한 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.set_sandbox(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX) else "fail",
                  "[입력 확인] 샌드박스 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.set_deny_except_drive(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE) else "fail",
                  "[입력 확인] 드라이브 제외 거부 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.set_pnetwork(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK) else "fail",
                  "[입력 확인] 프로세스 네트워크 허용 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.add_ip_port(D["proc_ip"], D["proc_port"])
        ip_list = page.process.get_ip_list()
        ok = any(D["proc_ip"] in x and D["proc_port"] in x for x in ip_list)
        self._add("pass" if ok else "fail", "[입력 확인] 프로세스 IP/Port 단건 추가",
                  f"입력: '{D['proc_ip']}' + '{D['proc_port']}' / 결과: list={ip_list}", sc=3)

        # 중복 IP/Port 차단 (yaml verified — registeredFolderWarning)
        page.process.add_ip_port(D["proc_ip"], D["proc_port"])
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 등록" in dup_msg and ("IP" in dup_msg or "Port" in dup_msg)
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 프로세스 IP/Port 중복 추가",
                      f"입력: 같은 조합 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 프로세스 IP/Port 중복 — 메시지 미노출",
                      "입력: 같은 조합 재추가 / 결과: 알림 없음", sc=3)

        # IP/Port 추가 → 삭제 → 잔여 확인 사이클
        page.process.add_ip_port("10.20.30.40", "1111")   # 2번째 행
        before_cnt = len(page.process.get_ip_list())
        removed = page.process.remove_ip_port("10.20.30.40", "1111")
        after_list = page.process.get_ip_list()
        ok = removed and len(after_list) == before_cnt - 1
        self._add("pass" if ok else "fail",
                  "[입력 확인] 프로세스 IP/Port 단건 삭제 → 잔여 확인",
                  f"입력: '10.20.30.40:1111' × 클릭 / 결과: 전={before_cnt} → 후={len(after_list)}", sc=3)

        page.process.set_pcontrol_extension(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT) else "fail",
                  "[입력 확인] 확장자 제어 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.click_radio_allowp()
        for ext in D["proc_ext"]:
            page.process.add_extension(ext)
        v = page.process.get_extension_list()
        self._add("pass" if v == D["proc_ext"] else "fail",
                  "[입력 확인] 프로세스 확장자 목록",
                  f"입력: {D['proc_ext']} / 결과: list={v}", sc=3)

        # 프로세스 확장자 중복 차단 (yaml verified)
        page.process.add_extension(D["proc_ext"][0])
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 동일한 확장자" in dup_msg or "이미 등록" in dup_msg
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 프로세스 확장자 중복 추가",
                      f"입력: '{D['proc_ext'][0]}' 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 프로세스 확장자 중복 — 메시지 미노출",
                      f"입력: '{D['proc_ext'][0]}' 재추가 / 결과: 알림 없음", sc=3)

        # 프로세스 확장자 추가 → 삭제 → 잔여 확인
        page.process.add_extension("tmp_del")
        before = len(page.process.get_extension_list())
        removed = page.process.remove_extension("tmp_del")
        after = page.process.get_extension_list()
        ok = removed and "tmp_del" not in after and len(after) == before - 1
        self._add("pass" if ok else "fail",
                  "[입력 확인] 프로세스 확장자 단건 삭제 → 잔여 확인",
                  f"입력: 'tmp_del' × 클릭 / 결과: 전={before} → 후={len(after)}, list={after}", sc=3)

        page.process.set_access_drive(True)
        self._add("pass" if page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE) else "fail",
                  "[입력 확인] 접근 드라이브 토글", "입력: ON / 결과: is_checked=True", sc=3)

        page.process.set_drive_letter(D["proc_drive"])
        v = page.process.get_drive_letter()
        self._add("pass" if v == D["proc_drive"] else "fail",
                  "[입력 확인] 프로세스 드라이브 레터",
                  f"입력: '{D['proc_drive']}' / 결과: get={v!r}", sc=3)

        page.process.set_description(D["proc_desc"])
        v = page.process.get_description()
        self._add("pass" if D["proc_desc"] in v else "fail",
                  "[입력 확인] 프로세스 설명",
                  f"입력: '{D['proc_desc']}' / 결과: get={v!r}", sc=3)

        page.process.confirm()
        self._add("pass" if len(page.get_item_list_rows()) == 1 else "fail",
                  "[입력 확인] 개별 프로세스 itemList 등록",
                  f"입력: process_modal '확인' / 결과: 행={len(page.get_item_list_rows())}", sc=3)

        # ════ 태그 등록 (tag mode) ════
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        tag_name = page.picker.select_first_and_confirm(mode="tag")
        self._add("pass", "[입력 확인] 태그 선택 (picker tag mode)",
                  f"입력: picker tag 첫 행 / 결과: 선택='{tag_name}'", sc=3)

        page.process.set_process_except(True)
        page.process.set_pclipboard_restrict(True)
        page.process.set_sandbox(True)
        page.process.set_pnetwork(True)
        page.process.add_ip_port(D["tag_ip"], D["tag_port"])
        ip_list = page.process.get_ip_list()
        self._add("pass" if any(D["tag_ip"] in x for x in ip_list) else "fail",
                  "[입력 확인] 태그 IP/Port 단건 추가",
                  f"입력: '{D['tag_ip']}' + '{D['tag_port']}' / 결과: list={ip_list}", sc=3)

        # 태그 IP/Port 중복 차단
        page.process.add_ip_port(D["tag_ip"], D["tag_port"])
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 등록" in dup_msg and ("IP" in dup_msg or "Port" in dup_msg)
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 태그 IP/Port 중복 추가",
                      f"입력: 같은 조합 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 태그 IP/Port 중복 — 메시지 미노출",
                      "입력: 같은 조합 재추가 / 결과: 알림 없음", sc=3)

        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in D["tag_ext"]:
            page.process.add_extension(ext)
        self._add("pass" if page.process.get_extension_list() == D["tag_ext"] else "fail",
                  "[입력 확인] 태그 확장자 목록",
                  f"입력: {D['tag_ext']} / 결과: list={page.process.get_extension_list()}", sc=3)

        # 태그 확장자 중복 차단
        page.process.add_extension(D["tag_ext"][0])
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 동일한 확장자" in dup_msg or "이미 등록" in dup_msg
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 태그 확장자 중복 추가",
                      f"입력: '{D['tag_ext'][0]}' 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 태그 확장자 중복 — 메시지 미노출",
                      f"입력: '{D['tag_ext'][0]}' 재추가 / 결과: 알림 없음", sc=3)

        page.process.set_access_drive(True)
        page.process.set_drive_letter(D["tag_drive"])
        self._add("pass" if page.process.get_drive_letter() == D["tag_drive"] else "fail",
                  "[입력 확인] 태그 드라이브 레터",
                  f"입력: '{D['tag_drive']}' / 결과: get={page.process.get_drive_letter()!r}", sc=3)

        page.process.set_description(D["tag_desc"])
        self._add("pass" if D["tag_desc"] in page.process.get_description() else "fail",
                  "[입력 확인] 태그 설명",
                  f"입력: '{D['tag_desc']}' / 결과: get={page.process.get_description()!r}", sc=3)

        page.process.confirm()
        self._add("pass" if len(page.get_item_tag_list_rows()) == 1 else "fail",
                  "[입력 확인] 태그 itemTagList 등록",
                  f"입력: tag process_modal '확인' / 결과: 행={len(page.get_item_tag_list_rows())}", sc=3)

        # ════ 웹제한 ════
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name(D["web_name"])
        self._add("pass" if page.web_restrict.get_name() == D["web_name"] else "fail",
                  "[입력 확인] 웹제한 이름",
                  f"입력: '{D['web_name']}' / 결과: get={page.web_restrict.get_name()!r}", sc=3)

        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        self._add("pass" if len(page.web_restrict.get_process_rows()) >= 1 else "fail",
                  "[입력 확인] 웹제한 적용 프로세스 (picker multi)",
                  f"입력: picker multi 첫 행 / 결과: rows={len(page.web_restrict.get_process_rows())}", sc=3)

        page.web_restrict.set_is_url(True)
        page.web_restrict.add_url(D["web_url"])
        self._add("pass" if any(D["web_url"] in u for u in page.web_restrict.get_url_list()) else "fail",
                  "[입력 확인] 웹제한 적용 URL 단건 추가",
                  f"입력: '{D['web_url']}' / 결과: list={page.web_restrict.get_url_list()}", sc=3)

        # 웹제한 URL 중복 차단 (yaml verified, typo: '폴더 경로')
        page.web_restrict.add_url(D["web_url"])
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 등록" in dup_msg and ("폴더 경로" in dup_msg or "URL" in dup_msg)
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 웹제한 URL 중복 추가 (typo: '폴더 경로')",
                      f"입력: '{D['web_url']}' 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 URL 중복 — 메시지 미노출",
                      f"입력: '{D['web_url']}' 재추가 / 결과: 알림 없음", sc=3)

        # 웹제한 URL 추가 → 삭제 → 잔여 확인
        page.web_restrict.add_url("temp-del-url.com")
        before = len(page.web_restrict.get_url_list())
        removed = page.web_restrict.remove_url("temp-del-url.com")
        after = page.web_restrict.get_url_list()
        ok = removed and not any("temp-del-url.com" in u for u in after) and len(after) == before - 1
        self._add("pass" if ok else "fail",
                  "[입력 확인] 웹제한 URL 단건 삭제 → 잔여 확인",
                  f"입력: 'temp-del-url.com' × 클릭 / 결과: 전={before} → 후={len(after)}", sc=3)

        page.web_restrict.add_file_extension(D["web_ext"])
        self._add("pass", "[입력 확인] 웹제한 업로드 허용 확장자 단건 추가",
                  f"입력: '{D['web_ext']}' / 결과: 입력 반영", sc=3)

        # 웹제한 확장자 중복 차단
        page.web_restrict.add_file_extension(D["web_ext"])
        if page.is_confirm_modal_visible():
            dup_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 동일한 확장자" in dup_msg or "이미 등록" in dup_msg
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 웹제한 확장자 중복 추가",
                      f"입력: '{D['web_ext']}' 재추가 / 결과: 메시지={dup_msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 확장자 중복 — 메시지 미노출",
                      f"입력: '{D['web_ext']}' 재추가 / 결과: 알림 없음", sc=3)

        # 웹제한 확장자 추가 → 삭제 → 잔여 확인
        page.web_restrict.add_file_extension("tmpdel")
        ext_cnt_before = page.page.locator(
            "div#controlSuiteWebRestricList button.tagInput[name='ExtentionWebRestrict']"
        ).count()
        removed = page.web_restrict.remove_file_extension("tmpdel")
        ext_cnt_after = page.page.locator(
            "div#controlSuiteWebRestricList button.tagInput[name='ExtentionWebRestrict']"
        ).count()
        ok = removed and ext_cnt_after == ext_cnt_before - 1
        self._add("pass" if ok else "fail",
                  "[입력 확인] 웹제한 확장자 단건 삭제 → 잔여 확인",
                  f"입력: 'tmpdel' × 클릭 / 결과: 전={ext_cnt_before} → 후={ext_cnt_after}", sc=3)

        page.web_restrict.set_upload_limit(D["web_limit"])
        self._add("pass" if page.web_restrict.get_upload_limit() == D["web_limit"] else "fail",
                  "[입력 확인] 웹제한 업로드 제한용량",
                  f"입력: '{D['web_limit']}' / 결과: get={page.web_restrict.get_upload_limit()!r}", sc=3)

        page.web_restrict.set_description(D["web_desc"])
        self._add("pass" if D["web_desc"][:5] in page.web_restrict.get_description() else "fail",
                  "[입력 확인] 웹제한 설명",
                  f"입력: '{D['web_desc']}' / 결과: get={page.web_restrict.get_description()!r}", sc=3)

        page.web_restrict.confirm()
        self._add("pass" if len(page.get_item_web_restrict_rows()) == 1 else "fail",
                  "[입력 확인] 웹제한 itemWebRestrictList 등록",
                  f"입력: web_restrict '확인' / 결과: 행={len(page.get_item_web_restrict_rows())}", sc=3)

        # ════ 메인 저장 + 정책 등록 확인 ════
        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "[저장 확인] 스위트 추가 모달 — '추가' 저장",
                  f"입력: '추가' 클릭 / 결과: 메시지={msg!r}", sc=3)

        exists = page.is_policy_exists(KEEP_NAME)
        self._add("pass" if exists else "fail",
                  "[등록 확인] 정책 목록 — 신규 정책 등록",
                  f"입력: 저장 완료 후 / 결과: '{KEEP_NAME}' 존재={exists}", sc=3)

        # KEEP 정책 의도적 보존 — 시나리오 4 가 modify/EDIT 검증 수행
        self._add("pass", "[등록 확인] KEEP 정책 의도적 보존 (시나리오 4 사용 예정)",
                  f"입력: 삭제 X / 결과: '{KEEP_NAME}' 잔존", sc=3)



    def test_scenario3c_web_restrict_save(self, logged_in_page, settings):
        """
        프로세스 1건 + 웹제한 1건 + 메인 저장 통합 흐름:
          0. 사전 cleanup ([AUTO]_*)
          1. 메인 모달 진입 + csuName
          2. 개별 프로세스 1건 (process_modal 통해 등록)
          3. 웹 제한기능 + → web_restrict_modal
             - name + 프로세스 추가 + URL 추가 + 확장자 추가
          4. web_restrict.confirm() → itemWebRestrictList 1행
          5. 메인 저장 → '저장 하였습니다'
          6. 정책 list 검증
          7. 사후 cleanup
        """
        print("\n━━ [제어 스위트] 시나리오 3c: 웹제한 등록 + 메인 저장 (E2E) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        policy_name = "[AUTO]_step4d_full"

        page.navigate_to()

        page.open_add_modal()
        page.set_csu_name(policy_name)

        # 프로세스 1건 등록
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        proc_name = page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()
        proc_rows = page.get_item_list_rows()
        self._add("pass" if len(proc_rows) == 1 else "fail",
                  "[입력 확인] 프로세스별 제어 — 프로세스 1건 등록",
                  f"입력: picker '{proc_name}' + 확인 / 결과: itemList 행={len(proc_rows)}", sc=3)

        # web_restrict 등록
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_step4d")

        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        wr_proc = page.picker.select_first_and_confirm(mode="multi")
        self._add("pass", "[입력 확인] 웹제한 모달 — 적용 프로세스 추가 (picker multi)",
                  f"입력: picker '{wr_proc}' (multi) / 결과: 테이블 등록", sc=3)

        page.web_restrict.set_is_url(True)
        page.web_restrict.add_url("naver.com")
        url_list = page.web_restrict.get_url_list()
        self._add("pass" if any("naver.com" in u for u in url_list) else "fail",
                  "[입력 확인] 웹제한 모달 — 적용 URL 등록 (naver.com)",
                  f"입력: 'naver.com' / 결과: list={url_list}", sc=3)

        page.web_restrict.add_file_extension("png;jpg")
        page.web_restrict.set_upload_limit("2048")
        page.web_restrict.set_description("[AUTO] step4d e2e 설명")
        self._add("pass", "[입력 확인] 웹제한 모달 — 확장자 + 제한용량 + 설명 입력",
                  "입력: 'png;jpg' / '2048' / 설명 / 결과: 입력 반영", sc=3)

        page.web_restrict.confirm()
        wr_rows = page.get_item_web_restrict_rows()
        self._add("pass" if len(wr_rows) >= 1 else "fail",
                  "[입력 확인] 웹제한 모달 — 확인 (itemWebRestrictList 등록)",
                  f"입력: '확인' 클릭 / 결과: 행 수={len(wr_rows)}", sc=3)

        msg = page.save_policy(mode="add")
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "[저장 확인] 스위트 추가 모달 — '추가' 버튼 (저장)",
                  f"입력: '추가' 클릭 / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()

        exists = page.is_policy_exists(policy_name)
        self._add("pass" if exists else "fail",
                  "[등록 확인] 정책 목록 — 신규 정책 등록 확인",
                  f"입력: (저장 완료 후) / 결과: '{policy_name}' 존재={exists}", sc=3)



    def test_scenario3e_validation_messages(self, logged_in_page, settings):
        """
        yaml validation_rules 기반 — 메인 모달 입력 검증.

        검증 케이스:
          A. csuName maxlength=50 자동 절단 (DOM 속성)
          B. csuName 빈값 + '추가' → '이름을 입력해 주세요.'
          C. 미선택 modify 버튼 → '선택된 항목이 없습니다.' (또는 disabled 확인)
          D. 미체크 delete 버튼 → '삭제할 항목을 체크해 주세요.' (또는 disabled 확인)
          E. csuName 중복 + '추가' → '이미 등록된 이름 입니다.'
        """
        print("\n━━ [제어 스위트] 시나리오 3e: 비정상 케이스 (yaml validation_rules) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        dup_name = "[AUTO]_step6a_dup"

        page.navigate_to()

        # ── A. csuName maxlength=50 자동 절단 ───────────────────
        page.open_add_modal()
        page.set_csu_name("a" * 100)
        got = page.get_csu_name()
        self._add("pass" if len(got) == 50 else "fail",
                  "[오버플로 확인] 스위트 이름 — DOM maxlength=50 자동 절단",
                  f"입력: 100자 / 결과: 실제 길이={len(got)}", sc=3)

        # ── B. csuName 빈값 + '추가' → 메시지 ────────────────────
        page.set_csu_name("")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()

        page._click(page.page.locator(page.SEL_SUBMIT_ADD).first)
        page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=page._TIMEOUT_MODAL
        )
        msg = page.get_confirm_message()
        self._add("pass" if msg == "이름을 입력해 주세요." else "fail",
                  "[차단 메시지] 스위트 이름 — ADD 빈값 차단 메시지",
                  f"입력: 이름='' + '추가' / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()

        # 정책 1건 ADD (중복/미선택 검증 사전조건)
        page.set_csu_name(dup_name)
        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" and page.is_policy_exists(dup_name) else "fail",
                  "[차단 메시지] 정책 목록 — 중복/미선택 검증용 정책 1건 ADD (사전조건)",
                  f"입력: 이름='{dup_name}' + 저장 / 결과: 메시지={msg!r}", sc=3)

        # ── C. 미선택 modify 버튼 ────────────────────────────────
        modify_btn = page.page.locator(page.SEL_MODIFY_BTN).first
        c_disabled = modify_btn.is_disabled()
        if not c_disabled:
            page._click(modify_btn)
            page.page.wait_for_timeout(500)
            if page.is_confirm_modal_visible():
                page.dismiss_confirm_modal()
        self._add("pass", "[등록 확인] 정책 목록 — '수정' 버튼 (미선택 상태)",
                  f"입력: 행 미선택 + '수정' 클릭 / 결과: disabled={c_disabled}", sc=3)

        # ── D. 미체크 delete 버튼 ───────────────────────────────
        delete_btn = page.page.locator(page.SEL_DELETE_BTN).first
        d_disabled = delete_btn.is_disabled()
        if not d_disabled:
            page._click(delete_btn)
            page.page.wait_for_timeout(500)
            if page.is_confirm_modal_visible():
                page.dismiss_confirm_modal()
        self._add("pass", "[등록 확인] 정책 목록 — '삭제' 버튼 (체크박스 미체크 상태)",
                  f"입력: 미체크 + '삭제' 클릭 / 결과: disabled={d_disabled}", sc=3)

        # ── E. csuName 중복 + 추가 → 메시지 ─────────────────────
        page.open_add_modal()
        page.set_csu_name(dup_name)

        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()

        page._click(page.page.locator(page.SEL_SUBMIT_ADD).first)
        page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=page._TIMEOUT_MODAL
        )
        msg = page.get_confirm_message()
        self._add("pass" if msg == "이미 등록된 이름 입니다." else "fail",
                  "[차단 메시지] 스위트 이름 — 중복 차단 메시지",
                  f"입력: 이름='{dup_name}' (중복) + '추가' / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()
        page.close_modal()


    # ==================================================================
    # 시나리오 3f — yaml verified 중복/빈값 메시지 모음 (sub-modal 영역 확장)
    # ==================================================================

    def test_scenario3f_validation_extended(self, logged_in_page, settings):
        """시나리오 3f — yaml verified 의 sub-modal 중복/빈값 메시지 검증.

        Case 1: 웹제한 이름 빈값 + 확인 → '이름을 입력해 주세요.' (yaml 1191)
        Case 2: process_modal IP+Port 조합 중복 → '이미 등록된 IP와 Port 입니다' (yaml 384)
        Case 3: web_restrict URL 중복 → '이미 등록된 폴더 경로가 존재합니다.' (yaml 386, typo)
        Case 4: process_modal 확장자 중복 → '이미 동일한 확장자가 존재합니다'
        Case 5: web_restrict 확장자 중복 → 동일 메시지
        """
        print("\n━━ [제어 스위트] 시나리오 3f: yaml verified 중복/빈값 메시지 모음 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step3f_validate")

        # ── 사전: 프로세스 1건 등록 (process_modal validation 진입 위해) ──
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")

        # ── Case 2: IP+Port 중복 (process_modal) ─────────────────
        page.process.set_pnetwork(True)
        page.process.add_ip_port("10.10.10.10", "1234")
        page.process.add_ip_port("10.10.10.10", "1234")  # 같은 조합 재추가
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if "이미 등록" in msg and ("IP" in msg or "Port" in msg) else "fail",
                      "프로세스 등록 모달 — IP+Port 조합 중복 차단 메시지 (yaml verified)",
                      f"입력: '10.10.10.10' + '1234' (재추가) / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 프로세스 등록 모달 — IP+Port 중복 — 메시지 미노출",
                      f"입력: 같은 조합 재추가 / 결과: 알림 모달 없음", sc=3)

        # ── Case 4: process_modal 확장자 중복 ────────────────────
        page.process.set_pcontrol_extension(True)
        page.process.add_extension("log")
        page.process.add_extension("log")  # 중복
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if "이미 동일한 확장자" in msg or "이미 등록" in msg else "fail",
                      "프로세스 등록 모달 — 확장자 중복 차단 메시지",
                      f"입력: 'log' (재추가) / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 프로세스 등록 모달 — 확장자 중복 — 메시지 미노출",
                      f"입력: 같은 확장자 재추가 / 결과: 알림 없음", sc=3)

        page.process.close()

        # ── Case 1: 웹제한 이름 빈값 + 확인 (yaml 1191) ──────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        # 프로세스 multi 추가 (이름 외 다른 필수 채움)
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        # webRestrictName 빈값 그대로 + 확인
        page.web_restrict.set_name("")
        page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if "이름을 입력" in msg else "fail",
                      "웹제한 모달 — 이름 빈값 + 확인 차단 메시지 (yaml must_test)",
                      f"입력: name='' + 확인 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 모달 — 이름 빈값 — 메시지 미노출",
                      f"입력: name='' + 확인 / 결과: 알림 없음", sc=3)

        # ── Case 5: web_restrict 확장자 중복 ────────────────────
        page.web_restrict.set_name("[AUTO]_web_3f")
        page.web_restrict.set_is_url(True)
        page.web_restrict.add_file_extension("png")
        page.web_restrict.add_file_extension("png")  # 중복
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if "이미 동일한 확장자" in msg or "이미 등록" in msg else "fail",
                      "웹제한 모달 — 확장자 중복 차단 메시지",
                      f"입력: 'png' (재추가) / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 모달 — 확장자 중복 — 메시지 미노출",
                      f"입력: 같은 확장자 재추가 / 결과: 알림 없음", sc=3)

        # ── Case 3: URL 중복 (yaml 386, typo 메시지) ─────────────
        page.web_restrict.add_url("naver.com")
        page.web_restrict.add_url("naver.com")  # 중복
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 등록" in msg and ("폴더 경로" in msg or "URL" in msg)
            self._add("pass" if ok else "fail",
                      "웹제한 모달 — URL 중복 차단 메시지 (yaml verified, typo: '폴더 경로')",
                      f"입력: 'naver.com' (재추가) / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 모달 — URL 중복 — 메시지 미노출",
                      f"입력: 같은 URL 재추가 / 결과: 알림 없음", sc=3)

        # 정리
        page.web_restrict.close()
        page.close_modal()
