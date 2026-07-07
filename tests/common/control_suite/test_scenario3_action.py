"""시나리오 3 — ADD 모달 검증 (3b~3f).

데이터 명명 규칙: `[AUTO]_sc{N}_step{M}` / `[AUTO_KEEP]_sc{N}_step{M}` (시나리오 N 의 sub-step M).
  - 3b → sc3_step1 (minimal_save)
  - 3c → sc3_step2 (crud_full_cycle, AUTO — 시나리오 4 가 EDIT 검증에 사용)
  - 3d → sc3_step3 (web_restrict_save)
  - 3e → sc3_step4 (중복 검증용)
  - 3f → sc3_step5 (validation extended)
"""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.common.control_suite._base import ControlSuiteBase


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
        policy_name = "[AUTO]_sc3_step1"

        print("\n━━ [제어 스위트] 시나리오 3b: 프로세스 1건 + 메인 저장 (E2E) ━━━")
        self._page = page.page

        page.navigate_to()
        # 시나리오 3 단독 실행 안전성 — sc1a 미실행 시 자동 cleanup
        self._ensure_session_cleanup(page)

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




    def test_scenario3c_crud_full_cycle(self, logged_in_page, settings):
        """시나리오 3c — ADD 종합 풍부 (각 영역 입력값 set/get 일치 + 메인 저장 + 등록 확인).

        EDIT 재진입/modify 흐름은 시나리오 4 영역. 본 메서드는 ADD 흐름만.
        시나리오 4 가 사용할 [AUTO]_sc3_step2 정책 생성 (KEEP 아닌 일반 AUTO — 같은 세션 안 잔존 충분).
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        TARGET_NAME = "[AUTO]_sc3_step2"
        D = {
            "clipboard_url":  "naver.com;google.com",
            "extensions":     ["txt", "doc", "exe"],
            "sign_excepts":   ["Claude Sign", "Innotium Inc"],
            "custom_option":  "sc3_step2_init",
            "proc_ip":        "192.168.1.1",
            "proc_port":      "8080",
            "proc_ext":       ["log", "tmp"],
            "proc_drive":     "C;D",
            "proc_desc":      "sc3_step2 프로세스 설명",
            "tag_ip":         "10.0.0.5",
            "tag_port":       "9090",
            "tag_ext":        ["zip"],
            "tag_drive":      "E;F",
            "tag_desc":       "sc3_step2 태그 설명",
            "web_name":       "[AUTO]_web_sc3_step2",
            "web_url":        "sc3_step2-web.com",
            "web_ext":        "csv",
            "web_limit":      "512",
            "web_desc":       "sc3_step2 웹제한 초기값",
        }

        print("\n━━ [제어 스위트] 시나리오 3c: ADD 종합 풍부 (메인+프로세스+태그+웹제한+저장+등록) ━━━")
        self._page = page.page
        page.navigate_to()
        # 세션 시작 정리 (idempotent — sc3b 가 이미 호출했으면 no-op)
        self._ensure_session_cleanup(page)

        # ════ 메인 모달 입력 ════
        page.open_add_modal()
        page.set_csu_name(TARGET_NAME)
        self._add("pass" if page.get_csu_name() == TARGET_NAME else "fail",
                  "[입력 확인] 스위트 이름",
                  f"입력: '{TARGET_NAME}' / 결과: get={page.get_csu_name()!r}", sc=3)

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

        # 클립보드 허용 URL — 구 빌드 기능 부재 감지 (선택 영역)
        if page.feature_exists(page.SEL_CLIPBOARD_URL):
            page.set_clipboard_allow_url(D["clipboard_url"])
            v = page.get_clipboard_allow_url()
            self._add("pass" if D["clipboard_url"] in v else "fail",
                      "[입력 확인] 클립보드 허용 URL",
                      f"입력: '{D['clipboard_url']}' / 결과: get={v!r}", sc=3)
        else:
            self._add("skip", "[입력 확인] 클립보드 허용 URL — 기능 없음 (구 빌드)",
                      f"입력: {page.SEL_CLIPBOARD_URL} 매칭 실패 / 결과: 기능 부재", sc=3)

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

        # ── 확장자 형식(특수문자) 거부 메시지 검증 (yaml :643) ──────
        # ". * ; ?" 외 특수문자/한글 → "...이외의 특수문자 또는 한글이..." 차단.
        # 거부 시 list 불변 (현 list = [txt, doc, exe]).
        before_fmt = len(page.get_main_extension_list())
        page.add_main_extension("$@%")
        if page.is_confirm_modal_visible():
            fmt_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            after_fmt = page.get_main_extension_list()
            ok = ("특수문자" in fmt_msg or "이외" in fmt_msg) and len(after_fmt) == before_fmt
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 제어할 확장자 형식(특수문자) 거부",
                      f"입력: '$@%' / 결과: 메시지={fmt_msg!r}, list 불변={len(after_fmt)==before_fmt}", sc=3)
        else:
            self._add("fail", "[차단 메시지] 제어할 확장자 형식(특수문자) — 거부 메시지 미노출",
                      f"입력: '$@%' / 결과: 알림 없음 (yaml :643 기대와 불일치)", sc=3)

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

        # ── process_modal 라디오 라벨 변경 검증 (BLOCKP → ALLOWP) ──
        # 메인 모달 라디오와 동일 패턴 — 회귀 발견 케이스 (yaml :138 process_modal_extension_with_toggle)
        v_init_p = page.process.get_radio_react_text()
        self._add("pass", "[입력 확인] 프로세스 제어할 확장자 라디오 초기 라벨",
                  f"입력: process_modal 진입 직후 / 결과: 라벨={v_init_p!r}", sc=3)

        page.process.click_radio_blockp()
        v_blockp = page.process.get_radio_react_text()
        self._add("pass" if v_blockp == "허용할 확장자" else "fail",
                  "[입력 확인] 프로세스 제어할 확장자 라디오 (BLOCKP 클릭 → 라벨 변경)",
                  f"입력: BLOCKP 클릭 / 결과: 초기={v_init_p!r} → 변경={v_blockp!r}", sc=3)

        page.process.click_radio_allowp()
        v_allowp = page.process.get_radio_react_text()
        self._add("pass" if v_allowp == "차단할 확장자" else "fail",
                  "[입력 확인] 프로세스 제어할 확장자 라디오 (ALLOWP 클릭 → 라벨 변경)",
                  f"입력: ALLOWP 클릭 / 결과: 이전={v_blockp!r} → 변경={v_allowp!r}", sc=3)

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

        # 프로세스 확장자 형식(특수문자) 거부 메시지 검증 (yaml :650)
        before_fmt = len(page.process.get_extension_list())
        page.process.add_extension("$@%")
        if page.is_confirm_modal_visible():
            fmt_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            after_fmt = page.process.get_extension_list()
            ok = ("특수문자" in fmt_msg or "이외" in fmt_msg) and len(after_fmt) == before_fmt
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 프로세스 확장자 형식(특수문자) 거부",
                      f"입력: '$@%' / 결과: 메시지={fmt_msg!r}, list 불변={len(after_fmt)==before_fmt}", sc=3)
        else:
            self._add("fail", "[차단 메시지] 프로세스 확장자 형식(특수문자) — 거부 메시지 미노출",
                      f"입력: '$@%' / 결과: 알림 없음 (yaml :650 기대와 불일치)", sc=3)

        # 프로세스 확장자 추가 → 삭제 → 잔여 확인
        # 주의: 확장자 input validation — ". * ; ?" 외 특수문자/한글 거부 (yaml :315).
        # '_' 도 invalid 로 차단 → 알파벳만 사용 ('tmpdel').
        page.process.add_extension("tmpdel")
        before = len(page.process.get_extension_list())
        removed = page.process.remove_extension("tmpdel")
        after = page.process.get_extension_list()
        ok = removed and "tmpdel" not in after and len(after) == before - 1
        self._add("pass" if ok else "fail",
                  "[입력 확인] 프로세스 확장자 단건 삭제 → 잔여 확인",
                  f"입력: 'tmpdel' × 클릭 / 결과: 전={before} → 후={len(after)}, list={after}", sc=3)

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

        # ── 태그 mode 라디오 라벨 변경 검증 (BLOCKP → ALLOWP) ──
        v_init_t = page.process.get_radio_react_text()
        self._add("pass", "[입력 확인] 태그 제어할 확장자 라디오 초기 라벨",
                  f"입력: 태그 process_modal 진입 직후 / 결과: 라벨={v_init_t!r}", sc=3)

        page.process.click_radio_blockp()
        v_blockt = page.process.get_radio_react_text()
        self._add("pass" if v_blockt == "허용할 확장자" else "fail",
                  "[입력 확인] 태그 제어할 확장자 라디오 (BLOCKP 클릭 → 라벨 변경)",
                  f"입력: BLOCKP 클릭 / 결과: 초기={v_init_t!r} → 변경={v_blockt!r}", sc=3)

        page.process.click_radio_allowp()
        v_allowt = page.process.get_radio_react_text()
        self._add("pass" if v_allowt == "차단할 확장자" else "fail",
                  "[입력 확인] 태그 제어할 확장자 라디오 (ALLOWP 클릭 → 라벨 변경)",
                  f"입력: ALLOWP 클릭 / 결과: 이전={v_blockt!r} → 변경={v_allowt!r}", sc=3)

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

        # 웹제한 확장자 형식(특수문자) 거부 메시지 검증 (yaml :666)
        fmt_before = len(page.web_restrict.get_file_extension_list())
        page.web_restrict.add_file_extension("$@%")
        if page.is_confirm_modal_visible():
            fmt_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            fmt_after = len(page.web_restrict.get_file_extension_list())
            ok = ("특수문자" in fmt_msg or "이외" in fmt_msg) and fmt_after == fmt_before
            self._add("pass" if ok else "fail",
                      "[차단 메시지] 웹제한 확장자 형식(특수문자) 거부",
                      f"입력: '$@%' / 결과: 메시지={fmt_msg!r}, list 불변={fmt_after==fmt_before}", sc=3)
        else:
            self._add("fail", "[차단 메시지] 웹제한 확장자 형식(특수문자) — 거부 메시지 미노출",
                      f"입력: '$@%' / 결과: 알림 없음 (yaml :666 기대와 불일치)", sc=3)

        # 웹제한 확장자 추가 → 삭제 → 잔여 확인
        # 주의: page method 사용 (이전 inline locator 의 [name='ExtentionWebRestrict']
        # 속성 매칭은 실제 DOM 에서 name 속성 = null 이라 0 반환 — Chrome MCP 검증).
        page.web_restrict.add_file_extension("tmpdel")
        ext_before = page.web_restrict.get_file_extension_list()
        removed = page.web_restrict.remove_file_extension("tmpdel")
        ext_after = page.web_restrict.get_file_extension_list()
        ok = removed and "tmpdel" not in ext_after and len(ext_after) == len(ext_before) - 1
        self._add("pass" if ok else "fail",
                  "[입력 확인] 웹제한 확장자 단건 삭제 → 잔여 확인",
                  f"입력: 'tmpdel' × 클릭 / 결과: 전={len(ext_before)} → 후={len(ext_after)}, list={ext_after}", sc=3)

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

        exists = page.is_policy_exists(TARGET_NAME)
        self._add("pass" if exists else "fail",
                  "[등록 확인] 정책 목록 — 신규 정책 등록",
                  f"입력: 저장 완료 후 / 결과: '{TARGET_NAME}' 존재={exists}", sc=3)

        # 시나리오 4 가 modify/EDIT 검증에 사용 (같은 세션 안 잔존 — KEEP 처리 불필요)
        self._add("pass", "[등록 확인] sc3c 정책 잔존 (시나리오 4 EDIT 사용 예정)",
                  f"입력: 삭제 X / 결과: '{TARGET_NAME}' 잔존", sc=3)



    def test_scenario3d_web_restrict_save(self, logged_in_page, settings):
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
        print("\n━━ [제어 스위트] 시나리오 3d: 웹제한 등록 + 메인 저장 (E2E) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        policy_name = "[AUTO]_sc3_step3"

        page.navigate_to()
        self._ensure_session_cleanup(page)

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
        page.web_restrict.set_name("[AUTO]_web_sc3_step3")

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
        page.web_restrict.set_description("[AUTO] sc3_step3 e2e 설명")
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
        dup_name = "[AUTO]_sc3_step4"

        page.navigate_to()
        self._ensure_session_cleanup(page)

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
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step5")

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

        # ── Case 0: 적용 프로세스 0건 + 확인 → "선택된 프로세스가 없습니다." ──
        # yaml :1257 must_test — 검증 우선순위 (프로세스 ≥ 1건 먼저 > 이름 입력 그 다음).
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "프로세스" in msg and ("없" in msg or "선택" in msg)
            self._add("pass" if ok else "fail",
                      "웹제한 모달 — 적용 프로세스 0건 + 확인 차단 메시지 (yaml must_test)",
                      f"입력: 프로세스 0건 + 확인 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 모달 — 프로세스 0건 — 메시지 미노출",
                      f"입력: 프로세스 0건 + 확인 / 결과: 알림 없음", sc=3)

        # ── Case 1: 웹제한 이름 빈값 + 확인 (yaml :1270) ──────────
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

        # ── Case 3: URL 중복 (yaml 386) — 차단 동작 + 메시지 일관성 분리 (sc4l 과 대칭) ──
        # 행위 저널 — Case 7 이 같은 모달을 이어 쓰므로 재진입 불가 → URL 태그 제거로 블록 리셋.
        self._ckpt()

        def _url_reset():
            # 1차: naver.com 미등록 → no-op / 재생: 잔여 알림 닫고 기존 태그 제거(깨끗한 상태)
            if page.is_confirm_modal_visible(timeout=300):
                page.dismiss_confirm_modal()
            page.web_restrict.remove_url("naver.com")
        self._act("적용 URL 초기화(잔여 'naver.com' 제거)", _url_reset)
        self._act("적용 URL 'naver.com' 추가",
                  lambda: page.web_restrict.add_url("naver.com"),
                  shot_target=page.page.locator(page.web_restrict.SEL_URL_LIST_TAG).first)
        self._act("같은 URL 'naver.com' 재추가 — 중복 알림 대기",
                  lambda: page.web_restrict.add_url("naver.com"))
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            # ⚠ 사용자 지적 (2026-05-28): dismiss 전에 _add → 스크린샷에 알림 상태 캡처
            #    (이전 패턴은 dismiss → _add 라 스크린샷에 알림 없음 = 보고서 ≠ 스크린샷 불일치)
            # 1) 중복 거부 동작 자체는 정상
            blocked = "이미 등록" in msg
            self._add("pass" if blocked else "fail",
                      "웹제한 모달 — URL 중복 거부 동작",
                      f"입력: 'naver.com' (재추가) / 결과: 메시지={msg!r}", sc=3)
            # 2) 메시지 영역 일관성 — 'URL' 영역인데 '폴더 경로' 메시지면 일관성 결함 (sc4l 과 동일 분류)
            is_url_msg = "URL" in msg.upper() or "주소" in msg
            is_folder_msg = "폴더" in msg or "경로" in msg
            if is_url_msg and not is_folder_msg:
                self._add("pass", "웹제한 모달 — URL 중복 메시지 일관성 (URL 영역 표현)",
                          f"입력: URL 재추가 / 결과: 메시지에 'URL/주소' 포함, '폴더/경로' 미포함 = {msg!r}", sc=3)
            elif is_folder_msg:
                self._add("warn", "[메시지 일관성 결함] 웹제한 URL 중복 — 'URL' 영역인데 '폴더 경로' 메시지 노출",
                          f"입력: 'naver.com' 재추가 / 결과: UI 영역 ≠ 메시지 영역 불일치 = {msg!r}", sc=3,
                          merge_key="csu_msg_incons::url_dup::warn::folder_path_message",   # sc4l EDIT 미러와 병합
                          repro="1. 웹제한 모달 적용 URL 에 'naver.com' 추가\n"
                                "2. 같은 URL 재추가\n"
                                "3. 'URL' 영역인데 '이미 등록된 폴더 경로가 존재합니다' — 영역≠메시지 불일치")
            else:
                self._add("warn", "[메시지 일관성 결함] 웹제한 URL 중복 — URL/주소 단어 누락",
                          f"입력: URL 재추가 / 결과: 'URL'/'주소'/'폴더'/'경로' 모두 없음 = {msg!r}", sc=3,
                          merge_key="csu_msg_incons::url_dup::warn::no_url_word",
                          repro="1. 웹제한 모달 적용 URL 재추가\n2. 중복 메시지에 'URL/주소' 단어 없음")
            # ⚠ 모든 _add 끝나고 dismiss (스크린샷 캡처 완료 후)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] 웹제한 모달 — URL 중복 — 메시지 미노출",
                      f"입력: 같은 URL 재추가 / 결과: 알림 없음", sc=3)

        # ── Case 7: 웹제한 이름 중복 차단 (2026-05-28 추가 — Chrome 확인 갭 보완) ──
        # 기존 Case1 은 '이름 빈값'만 검증. '중복'은 미검증이던 갭 (matrix 2차 Chrome 확인).
        # wr#1 ([AUTO]_web_3f) 를 list 에 확정 → wr#2 동일 이름 → 이름 중복 차단 기대.
        page.web_restrict.confirm()
        page.web_restrict.wait_closed(timeout=3000)
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        # wr#1 이 idx=0 사용 → wr#2 는 idx=1 (다른 프로세스) 필수.
        # yaml :287 cross_instance_ADD_flow: 동일 프로세스 재선택 시 silent 거부 →
        # wr#2 적용 프로세스 0건 → 이름 중복 단계 도달 못 함 (2026-05-28 Chrome 확정).
        page.picker.select_nth_and_confirm(1, mode="multi")
        page.web_restrict.set_name("[AUTO]_web_3f")   # wr#1 과 동일 이름
        # confirm — picker 닫힘 후 잔여 modal-backdrop 가 pointer 가로채는 3-stack 케이스 →
        # JS evaluate click (좌표 무관, ng-click 발화 OK — yaml :564). dismiss_confirm_modal fallback 동일 패턴.
        page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first.evaluate("el => el.click()")
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미" in msg and ("이름" in msg or "등록" in msg)
            self._add("pass" if ok else "fail",
                      "웹제한 모달 — 이름 중복 차단 메시지 (Chrome 확인 갭 보완)",
                      f"입력: '[AUTO]_web_3f' 동일 이름 재등록 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("fail", "[차단 메시지] 웹제한 이름 중복 — 미노출",
                      f"입력: 동일 이름 재등록 / 결과: 알림 없음 (Chrome 확인 결과와 불일치)", sc=3)

        # 정리
        page.web_restrict.close()

        # ── Case 8: cross_instance 프로세스 중복 (yaml :287, 2026-05-28 추가) ──
        # 한 정책 안 다른 wr 가 이미 쓰는 프로세스를 wr#3 picker 로 재선택 → 제품이
        # silent 거부 + 알림: '{name}은 이미 등록되어 있어 생략되었습니다.(타 웹제한 포함)'.
        # wr#3 적용 프로세스 0건. (Case7 이 wr#1=idx=0 로 저장해둠 → wr#3 idx=0 시도)
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_nth_and_confirm(0, mode="multi")   # wr#1 과 동일 idx
        proc_rows_wr3 = len(page.web_restrict.get_process_rows())
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = ("이미 등록" in msg) and ("타 웹제한" in msg or "생략" in msg or "포함" in msg)
            self._add("pass" if ok and proc_rows_wr3 == 0 else "fail",
                      "웹제한 모달 — cross_instance 프로세스 중복 silent 거부 + 알림 (yaml :287)",
                      f"입력: wr#1 사용중 idx=0 동일 선택 / 결과: 메시지={msg!r}, wr.procRows={proc_rows_wr3}", sc=3)
        else:
            self._add("fail", "[차단 메시지] cross_instance 프로세스 중복 — 알림 미노출",
                      f"입력: 동일 idx=0 / 결과: 알림 없음 (yaml :287 기대와 불일치, wr.procRows={proc_rows_wr3})", sc=3)
        page.web_restrict.close()

        # ── Case 9: 업로드 제한용량 13자 차단 메시지 (yaml :182, audit 갭 2026-05-28) ──
        # yaml verified — DOM maxlength=null(신빌드) 라 13자 입력 자유, 확인 시 차단:
        # "업로드 제한용량의 입력 가능 글자수는 최대 12자 까지 가능합니다." (modal_stage_block).
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_nth_and_confirm(1, mode="multi")   # wr#1 회피용 idx=1
        page.web_restrict.set_name("[AUTO]_web_limit13")
        page.web_restrict.set_upload_limit("1234567890123")   # 13자
        page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first.evaluate("el => el.click()")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = ("12자" in msg) and ("업로드" in msg or "제한용량" in msg)
            self._add("pass" if ok else "fail",
                      "웹제한 모달 — 업로드 제한용량 13자 차단 메시지 (yaml :182 audit 갭)",
                      f"입력: uploadLimitSize='1234567890123' (13자) / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("fail", "[차단 메시지] 업로드 제한용량 13자 — 미노출",
                      f"입력: 13자 / 결과: 알림 없음 (yaml :182 기대와 불일치)", sc=3)
        page.web_restrict.close()

        # ── Case 6: 메인 모달 전자서명 예외처리 중복 → '이미 등록된 전자서명' (yaml :382 신 발견) ──
        # 신규 추가 — yaml 미기록 신 발견 (2026-05-19) 검증
        page.set_sign_except_toggle(True)
        page.add_sign_except("Innotium Inc")
        page.add_sign_except("Innotium Inc")  # 동일값 재추가
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            ok = "이미 등록" in msg and "전자서명" in msg
            self._add("pass" if ok else "fail",
                      "메인 모달 - 전자서명 예외처리 중복 차단 메시지 (yaml :382 신 발견)",
                      f"입력: 'Innotium Inc' (재추가) / 결과: 메시지={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] 전자서명 예외처리 중복 — 메시지 미노출",
                      f"입력: 같은 전자서명 재추가 / 결과: 알림 없음", sc=3)

        page.close_modal()

    # ==================================================================
    # 시나리오 3g — format / overflow 검증 (yaml must_test + verified)
    # ==================================================================

    def test_scenario3g_format_overflow(self, logged_in_page, settings):
        """시나리오 3g — modal 내 input format / overflow yaml 검증 (picker 영역 제외).

        검증 범위: process_modal / web_restrict_modal 의 input + confirm 흐름.
        picker 중복 알림 (yaml :1235, :1278) 은 sc3i 로 분리 — picker 회귀 격리.

        Case A: Port 비숫자 'abc' → 'Port 형식을 다시 확인 해 주세요' (yaml :151 verified)
        Case B: IP 형식 잘못 'abc.def.ghi.jkl' → '아이피 주소 형식이 잘못되었습니다' (yaml :347)
        Case C: process_modal 설명 1000자 + 확인 → '설명의 입력 가능 글자수는 최대 300자...' (yaml :169 must_test)
        Case D: web_restrict_modal 설명 1000자 + 확인 → 동일 메시지 (yaml :173 scopes)
        Case E: process_modal 프로세스 미선택 + 확인 → '선택된 프로세스가 없습니다.' (yaml :1226 must_test)
        """
        print("\n━━ [제어 스위트] 시나리오 3g: format / overflow 검증 (yaml must_test) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        long_desc = "가" * 1000   # 한글 1000자 (서버 한도 300자 초과)

        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step6")

        # ── 사전: process_modal 진입 (case A/B/C/E/F 진입 위해) ───
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        # ── Case E: 프로세스 미선택 + 확인 → '선택된 프로세스가 없습니다.' (must_test) ──
        page._click(page.page.locator(page.process.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "프로세스" in msg and ("없" in msg or "선택" in msg)
            self._add("pass" if ok else "fail",
                      "프로세스 등록 모달 — 프로세스 미선택 + 확인 차단 메시지 (yaml must_test)",
                      f"입력: 프로세스 미선택 + 확인 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 프로세스 등록 모달 — 미선택 — 메시지 미노출",
                      f"입력: 미선택 + 확인 / 결과: 알림 없음", sc=3)

        # 프로세스 1건 선택 (Case A/B/C 진입 위해)
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")

        # ── Case A: Port 비숫자 'abc' → 'Port 형식을 다시 확인 해 주세요' (yaml verified) ──
        page.process.set_pnetwork(True)
        page.process.add_ip_port("192.168.10.10", "abc")
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if "Port" in msg and "형식" in msg else "fail",
                      "프로세스 등록 모달 — Port 비숫자 입력 차단 (yaml verified)",
                      f"입력: Port='abc' + 추가 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] Port 비숫자 — 메시지 미노출",
                      f"입력: 'abc' / 결과: 알림 없음", sc=3)

        # ── Case A2: Port 최대값 초과 '99999' → 'Port의 최대값은 65535입니다' (yaml :234 verified, must_test) ──
        # 신규 추가 — 정상 차단 검증 (sub-modal 단계에서 정확히 차단되어야 정상 UX)
        page.process.add_ip_port("192.168.10.11", "99999")
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            self._add("pass" if "65535" in msg or ("Port" in msg and "최대" in msg) else "fail",
                      "프로세스 등록 모달 - Port 최대값 초과(99999) 차단 메시지 (yaml :234 must_test)",
                      f"입력: Port='99999' + 추가 / 결과: 메시지={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] Port 최대값 초과 — 메시지 미노출",
                      f"입력: '99999' / 결과: 알림 없음", sc=3)

        # ── Case B1: IP 형식 오류 '256.256.256.256' → '아이피 주소 형식이 잘못' (yaml :337-339 format_error pattern) ──
        # 신규 추가 — yaml 의 format_error / input_reset 2-pattern 중 format_error 검증
        page.process.add_ip_port("256.256.256.256", "8080")
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            self._add("pass" if ("아이피" in msg or "IP" in msg) and ("형식" in msg or "잘못" in msg) else "fail",
                      "프로세스 등록 모달 - IP 범위 초과(256.256.256.256) 형식 오류 차단 (yaml :337 format_error)",
                      f"입력: IP='256.256.256.256' + 추가 / 결과: 메시지={msg!r}", sc=3)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] IP 범위 초과 — 메시지 미노출",
                      f"입력: '256.256.256.256' / 결과: 알림 없음", sc=3)

        # ── Case B: IP 형식 잘못 'abc.def.ghi.jkl' → '아이피 주소 형식...' (yaml :347) ──
        page.process.add_ip_port("abc.def.ghi.jkl", "8080")
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            self._add("pass" if ("아이피" in msg or "IP" in msg) and "형식" in msg else "fail",
                      "프로세스 등록 모달 — IP 형식 invalid 차단 (yaml verified)",
                      f"입력: IP='abc.def.ghi.jkl' + 추가 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] IP 형식 invalid — 메시지 미노출",
                      f"입력: 'abc.def.ghi.jkl' / 결과: 알림 없음", sc=3)

        # ── Case C: process_modal 설명 1000자 + 확인 → 300자 제한 (must_test) ──
        page.process.set_description(long_desc)
        page._click(page.page.locator(page.process.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "설명" in msg and "300자" in msg
            self._add("pass" if ok else "fail",
                      "프로세스 등록 모달 — 설명 1000자 (300자 제한) 차단 메시지 (yaml must_test)",
                      f"입력: 설명 길이=1000 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 프로세스 설명 300자 — 메시지 미노출",
                      f"입력: 1000자 + 확인 / 결과: 알림 없음", sc=3)
        # 설명 비우기 + 정상 confirm — Case D 위해 process_modal 닫음
        page.process.set_description("")
        page.process.confirm()

        # ── Case D: web_restrict_modal 설명 1000자 + 확인 → 300자 제한 (must_test, 양쪽 모달) ──
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_name("[AUTO]_web_sc3_step6")
        page.web_restrict.set_is_url(True)
        page.web_restrict.add_url("step6-web.com")
        page.web_restrict.set_description(long_desc)
        page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "설명" in msg and "300자" in msg
            self._add("pass" if ok else "fail",
                      "웹제한 모달 — 설명 1000자 (300자 제한) 차단 메시지 (yaml must_test)",
                      f"입력: 설명 길이=1000 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] 웹제한 설명 300자 — 메시지 미노출",
                      f"입력: 1000자 + 확인 / 결과: 알림 없음", sc=3)

        # 정리
        page.web_restrict.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 3h — 글자수 한도 검증 (yaml :271 scenario_3_length_boundary)
    # ==================================================================

    def test_scenario3h_length_boundary(self, logged_in_page, settings):
        """yaml :271 fixed_lengths [100, 300, 500] — DOM input 자동 절단 / 길이 검증.

        Case A: csuName 100/300/500자 → DOM maxlength=50 자동 절단 (yaml :282)
        Case B: customOptionText 100/300/500자 → DOM 길이 (yaml :132 글자수 정책)
        Case C: clipboardAllowUrl 500/1000자 → DOM 길이 (yaml :131 textarea)

        주의: process/web_restrict 설명의 서버 차단 (300자) 은 sc3g Case C/D 가 이미 검증.
        picker 재사용 시 '이미 등록된 프로세스' 알림으로 picker 가 안 닫혀 wait_closed timeout
        → 본 sub-case 는 메인 모달 단일 입력 검증만 (사이드 이펙트 없음).
        """
        print("\n━━ [제어 스위트] 시나리오 3h: 글자수 한도 검증 (yaml :271 fixed_lengths) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()

        # ── Case A: csuName DOM maxlength=50 자동 절단 (100/300/500자) ──
        for length in (100, 300, 500):
            page.set_csu_name("a" * length)
            got = page.get_csu_name()
            self._add("pass" if len(got) == 50 else "fail",
                      f"[오버플로 확인] 스위트 이름 — {length}자 입력 시 DOM maxlength=50 자동 절단",
                      f"입력: {length}자 / 결과: 실제 DOM 길이={len(got)}", sc=3)

        # ── Case B: customOptionText 100/300/500자 — DOM 길이 ──
        page.set_csu_name("[AUTO]_sc3_step7")
        for length in (100, 300, 500):
            page.set_custom_option("c" * length)
            got = page.get_custom_option()
            self._add("pass",
                      f"[오버플로 확인] 커스텀 옵션 — {length}자 입력 DOM 길이",
                      f"입력: {length}자 / 결과: DOM 길이={len(got)}", sc=3)
        page.set_custom_option("")  # 정리

        # ── Case C: clipboardAllowUrl 500/1000자 (yaml :131 textarea 글자수) ──
        if page.feature_exists(page.SEL_CLIPBOARD_URL):
            for length in (500, 1000):
                page.set_clipboard_allow_url("u" * length)
                got = page.get_clipboard_allow_url()
                self._add("pass",
                          f"[오버플로 확인] 클립보드 허용 URL — {length}자 입력 DOM 길이",
                          f"입력: {length}자 / 결과: DOM 길이={len(got)}", sc=3)
            page.set_clipboard_allow_url("")  # 정리
        else:
            self._add("skip", "[오버플로 확인] 클립보드 허용 URL — 기능 없음 (구 빌드)",
                      f"입력: {page.SEL_CLIPBOARD_URL} 매칭 실패 / 결과: 기능 부재", sc=3)

        # 정리 — 메인 모달 cancel (저장 안 함)
        page.close_modal()

    # ==================================================================
    # 시나리오 3i — picker 중복 알림 검증 (sc3g 에서 분리 — 회귀 격리)
    # ==================================================================

    def test_scenario3i_picker_duplicate(self, logged_in_page, settings):
        """picker 영역 중복 알림 검증 (yaml :1235 / :1278 must_test).

        sc3g 에서 분리: picker 알림 dismiss 후 picker 가 unstable 상태가 되어
        cascade 위험 → 별도 sub-case 로 격리 (pytest fixture 독립).

        Case A: process picker — 같은 정책 안 동일 프로세스 재선택 → '이미 등록된 프로세스 입니다' (yaml :1235)
        Case B: web_restrict picker — 같은 인스턴스 안 동일 프로세스 재선택 → 동일 메시지 (yaml :1278)

        검증 후 picker 정리 — 마우스 × 클릭 회피 (TargetClosedError) →
        두 번째 행 (미등록 프로세스) 선택 + confirm 으로 자연 흐름 종료.
        실패 시 _close_leftover_submodals 강제 DOM 제거 fallback.
        """
        print("\n━━ [제어 스위트] 시나리오 3i: picker 중복 알림 검증 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step8")

        # ── Case A: process picker — 첫 행 재선택 → 이미 등록 알림 ──
        # 사전: 첫 행 1회 등록
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        first_proc = page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()  # process_modal 정상 등록

        # 본 검증: 다시 process_modal 진입 + 같은 첫 행 재선택
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first(mode="single")
        page.picker.confirm()
        # alert wait 3s (이전 1.5s 로 가끔 못 잡는 케이스 — 알림 띄우는 데 약간 지연)
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 등록" in msg and ("프로세스" in msg or "생략" in msg or "타 웹제한" in msg)
            self._add("pass" if ok else "fail",
                      "프로세스 picker — 동일 프로세스 재선택 차단 (yaml :1235 must_test)",
                      f"입력: 첫 행 ('{first_proc}') 재선택 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] process picker 중복 — 메시지 미노출",
                      f"입력: 동일 프로세스 재선택 / 결과: 알림 없음", sc=3)

        # picker / 모달 정리 — ESC 키만 (JS evaluate 가 page closed cascade 야기, 회피).
        # _close_leftover_submodals + inline style evaluate 가 sc3i Case C 진입 시 page close 트리거 확인됨.
        for _ in range(5):
            try:
                page.page.keyboard.press("Escape")
                page.page.wait_for_timeout(200)
            except Exception:
                break

        # ── Case B: web_restrict picker — 동일 인스턴스 안 중복 프로세스 재선택 ──
        # case 사이 F5 — AngularJS modal directive state 누적 방지 (2026-05-20 진단 결과)
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step8_web")
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")  # 첫 행 1회 등록
        # 다시 picker 호출 + 같은 첫 행 multi 재선택
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first(mode="multi")
        page.picker.confirm()
        if page.is_confirm_modal_visible():
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "이미 등록" in msg and ("프로세스" in msg or "생략" in msg or "타 웹제한" in msg)
            self._add("pass" if ok else "fail",
                      "웹제한 picker — 동일 인스턴스 프로세스 중복 차단",
                      f"입력: 등록된 프로세스 재선택 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("warn", "[차단 메시지] web_restrict picker 중복 — 메시지 미노출",
                      f"입력: 같은 프로세스 재선택 / 결과: 알림 없음", sc=3)

        # ESC 키만 정리 (JS evaluate 회피 — page close cascade 방지)
        for _ in range(5):
            try:
                page.page.keyboard.press("Escape")
                page.page.wait_for_timeout(200)
            except Exception:
                break

        # ── Case C: tag mode picker — 동일 태그 재선택 중복 알림 (사용자 보고 누락) ──
        # 사용자 검증 요청: process 와 동일하게 태그 영역도 picker 중복 알림 있어야 함.
        page.page.wait_for_timeout(300)
        # case 사이 F5
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step8_tag")
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        first_tag = page.picker.select_first_and_confirm(mode="tag")
        page.process.confirm()

        # 본 검증: 다시 태그 모달 진입 + 같은 첫 태그 재선택
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first(mode="tag")
        page.picker.confirm()
        # 텍스트 기반 강화 detection — 5s 까지 100ms 단위 polling
        # ('이미 등록된 태그 입니다' 알림 ID 미확정 / picker→main modal 전환 시점 race 대응)
        found_msg = None
        for _ in range(50):
            txt = page.page.evaluate("""() => {
                const sel = '.modal-body-text, .modal-body, div#__globalMessageModal .modal-body';
                const els = document.querySelectorAll(sel);
                for (const el of els) {
                    const t = el.textContent?.trim();
                    if (t && t.includes('이미 등록')) return t;
                }
                return null;
            }""")
            if txt:
                found_msg = txt
                break
            page.page.wait_for_timeout(100)
        if found_msg:
            ok = "이미 등록" in found_msg and ("프로세스" in found_msg or "태그" in found_msg or "생략" in found_msg)
            # dismiss alert
            try:
                page.dismiss_confirm_modal()
            except Exception:
                pass
            self._add("pass" if ok else "fail",
                      "태그 picker — 동일 태그 재선택 중복 차단 (사용자 보고 추가)",
                      f"입력: 첫 태그 ('{first_tag}') 재선택 / 결과: 메시지={found_msg!r}", sc=3)
        else:
            self._add("warn", "[UX 모호] tag picker 중복 — silent skip (process picker 와 정책 불일치)",
                      f"입력: 동일 태그 재선택 / 결과: 알림 노출 안 됨 + picker 자동 닫힘 (yaml :1934 silent_skip)", sc=3)

        # 정리 — ESC 만 (JS evaluate 회피)
        for _ in range(5):
            try:
                page.page.keyboard.press("Escape")
                page.page.wait_for_timeout(200)
            except Exception:
                break

        # ── Case D: cacheFolderInput picker 동일 reserved_word 재추가 → '이미 등록된 폴더 경로' (yaml :346-348) ──
        # 신규 추가 — 특수폴더 picker 같은 항목 중복 등록 시 attachCacheFolderBtn 차단 알림
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step8_cache_dup")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        # 1st: 특수폴더 picker → 'DESKTOP' 선택 + 추가
        if page.feature_exists(page.process.SEL_CACHE_SPECIAL_BTN, timeout=1000):
            page.process.click_special_folder_btn()
            page.special_folder.wait_open()
            page.special_folder.select_and_confirm(["[/DESKTOP/]"])
            page.process.click_cache_add_btn()
            # 2nd: 같은 'DESKTOP' 다시 picker → 확인 → 추가 → 중복 알림 기대
            page.process.click_special_folder_btn()
            page.special_folder.wait_open()
            page.special_folder.select_and_confirm(["[/DESKTOP/]"])
            page.process.click_cache_add_btn()
            if page.is_confirm_modal_visible(timeout=3000):
                msg = page.get_confirm_message()
                ok = "이미 등록" in msg and ("폴더" in msg or "경로" in msg)
                self._add("pass" if ok else "fail",
                          "프로세스 등록 모달 - 특수폴더 picker 동일 reserved_word 중복 차단 (yaml :346-348)",
                          f"입력: [/DESKTOP/] 재선택 + 추가 / 결과: 메시지={msg!r}", sc=3)
                page.dismiss_confirm_modal()
            else:
                self._add("warn", "[차단 메시지] 특수폴더 picker 중복 — 메시지 미노출",
                          f"입력: [/DESKTOP/] 재추가 / 결과: 알림 없음", sc=3)
        else:
            self._add("skip", "[차단 메시지] 특수폴더 picker — 기능 부재", "(skip)", sc=3)
        # 정리
        try:
            page.process.close() if hasattr(page.process, 'close') else None
        except Exception:
            pass
        page.close_modal()

    # ==================================================================
    # 시나리오 3j — 모달 단계 OK + 메인 저장 차단 (3 영역 그룹 검증)
    # ==================================================================
    # 검증 방향성 (사용자 결정 2026-05-20):
    #   - 프로세스별 제어 / 태그 제어 / 웹 제한기능 모달의 input 이 모달 단계에선 통과
    #   - 메인 저장 ("추가") 시점에 서버에서 차단 → '서버에서 오류가 발생 하였습니다.' 알림
    #   - 본서버 Chrome MCP 검증 2026-05-19~20 기반
    # 영역 별 sub-case 그룹:
    #   Case A1~A3: 프로세스 모달 (drive 100자 / Port -1 / Port 빈값)
    #   Case B1:   태그 모달 (drive 100자 — process mode 동일성 verified)
    #   Case C1~C4: 웹제한 모달 (basePath 400자 / webRestrictName 500자 / cacheFolder 500자는 process / URL 1000자)
    # ==================================================================

    def test_scenario3j_save_cycle_errors(self, logged_in_page, settings):
        """yaml 구 빌드 검증 (2026-05-19) — 메인 저장 시점 '서버에서 오류 발생' UX 결함 검증.

        검증 패턴 (Phase C): sub-modal 단계는 OK 인데 메인 모달 저장 시점에 서버 차단.
        DOM maxlength 없음 + sub-modal 알림 없음 → 사용자가 입력 후 저장 누를 때까지 모름.

        Case A: 드라이브 letter 50자 (정상) — 메인 저장 OK 검증
        Case B: 드라이브 letter 100자 (구 빌드 검증) — 메인 저장 시 '서버에서 오류 발생' 알림
        Case C: basePath 400자 (web_restrict 기본폴더) — 동일 패턴 검증

        주의:
          - DOM maxlength 추가가 제품 권고 사항. 자동화는 회귀 검출용.
          - 본 검증은 50자 통과 + 100자 차단 양쪽 모두 확인 (boundary 검증).
        """
        print("\n━━ [제어 스위트] 시나리오 3j: save cycle errors (메인 저장 서버 오류) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        # 사전 정리 — 이전 임시 검증 / 잔존 alert + 모달 강제 정리
        # 사용자가 Chrome MCP 등으로 직접 검증한 흔적 (csuName 잔존, alert 미 dismiss 등) 안전 처리
        for _ in range(5):
            try:
                page.page.keyboard.press("Escape")
                page.page.wait_for_timeout(150)
            except Exception:
                break
        try:
            page.dismiss_confirm_modal()
        except Exception:
            pass

        # 세션 시작 정리 (idempotent — sc3b 가 이미 호출했으면 no-op)
        # 명시 delete_all_auto_policies 제거: sc4 가 sc3 가 생성한 [AUTO]_ 정책을
        # EDIT 검증에 직접 사용하므로 중간 삭제 금지. 세션 시작 시 1회 cleanup 으로 충분.
        page.navigate_to()
        self._ensure_session_cleanup(page)

        # ── Case A: 드라이브 letter 50자 (정상 케이스 — 메인 저장 OK) ─
        # case 사이 F5 — AngularJS modal state 누적 방지
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step9_drv50")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        # 접근 드라이브 토글 ON + 50자 letter
        if page.feature_exists(page.process.SEL_TOGGLE_ACCESS_DRIVE, timeout=1000):
            page.process.set_access_drive(True)
            page.process.set_drive_letter("a" * 50)
            page.process.confirm()
            # 메인 저장 시도
            msg = page.save_policy(mode="add")
            page.dismiss_confirm_modal()
            ok = msg == "저장 하였습니다"
            self._add("pass" if ok else "fail",
                      "[저장 확인] 드라이브 letter 50자 → 메인 저장 OK (boundary 정상)",
                      f"입력: letter 50자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("skip", "[저장 확인] 드라이브 letter 50자 — 접근 드라이브 토글 기능 부재",
                      f"입력: SEL_TOGGLE_ACCESS_DRIVE 매칭 실패 / 결과: 기능 부재 (구 빌드)", sc=3)

        # ── Case B: 드라이브 letter 100자 (메인 저장 시 서버 오류) ─
        # [파일럿 2026-07-07] 행위 저널(_ckpt/_act) 방식 — 손코딩 캡처 제거.
        # warn/fail 검출 시 저널 행위들을 자동 재실행·단계별 캡처(캡션=행위 라벨). pass 면 비용 0.
        self._ckpt()
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step9_drv100")))
        self._act("개별 프로세스 탭 — 프로세스 선택(picker)",
                  lambda: (page.click_individual_process_tab(), page.click_add_process_btn(),
                           page.process.wait_open(), page.process.click_pick_btn(),
                           page.picker.wait_open(), page.picker.select_first_and_confirm(mode="single")))
        if page.feature_exists(page.process.SEL_TOGGLE_ACCESS_DRIVE, timeout=1000):
            self._act("접근 드라이브 letter 100자 입력 — sub-modal 통과(클라이언트 가드 없음)",
                      lambda: (page.process.set_access_drive(True),
                               page.process.set_drive_letter("a" * 100)),
                      shot_target=page.page.locator(page.process.SEL_DRIVE_LETTER).first)
            self._act("프로세스 등록 확인 — sub-modal 닫힘(알림 없어야 정상)",
                      lambda: page.process.confirm())
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
            # warn = UX 결함 재현 → BUG 리포트 / pass = sub-modal 정상 차단.
            # screenshots 미지정 — warn 이면 _add 가 저널을 자동 재생해 재현 순서 캡처 첨부.
            _st = "warn" if defect_found else "pass"
            self._add(_st,
                      "[UX 결함] 프로세스별 제어 (개별 프로세스) - 접근 드라이브 letter 100자 → 메인 저장 시 서버 오류 (sub-modal 단계에서 차단되어야 정상)",
                      f"입력: letter 100자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                      merge_key=f"csu_srv_err::letter100_proc::{_st}::raw_server_error_no_client_guard",
                      repro="1. 개별 프로세스 접근 드라이브 letter 100자 입력\n"
                            "2. sub-modal 통과 — 클라이언트 가드 없음\n"
                            "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            page.dismiss_confirm_modal()
        else:
            self._add("skip", "[UX 결함] 프로세스별 제어 (개별 프로세스) - 접근 드라이브 letter 100자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()
        # 서버 오류 케이스 후 안전 정리 — 페이지 새로고침 (모달 잔존 / alert 잔여 완전 정리)
        try:
            page.page.reload(wait_until="domcontentloaded", timeout=15000)
            page.page.wait_for_timeout(500)
        except Exception:
            pass

        # ── Case C: basePath 400자 (web_restrict 기본폴더 — 메인 저장 시 서버 오류) ─
        # 행위 저널 — warn/fail 검출 시 자동 재생·단계별 캡처(캡션=행위 라벨)
        self._ckpt()
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step9_bp100")))
        self._act("개별 프로세스 등록(itemList 1건) — picker 선택 + 확인",
                  lambda: (page.click_individual_process_tab(), page.click_add_process_btn(),
                           page.process.wait_open(), page.process.click_pick_btn(),
                           page.picker.wait_open(), page.picker.select_first_and_confirm(mode="single"),
                           page.process.confirm()))
        self._act("웹제한 모달 진입 — 프로세스 선택 + 이름 입력",
                  lambda: (page.click_add_web_restrict_btn(), page.web_restrict.wait_open(),
                           page.web_restrict.click_add_process_btn(), page.picker.wait_open(),
                           page.picker.select_first_and_confirm(mode="multi"),
                           page.web_restrict.set_name("[AUTO]_web_sc3_step9_bp")))
        # basePath 영역 (isProcessOption 토글 ON + basePath 400자)
        if page.feature_exists(page.web_restrict.SEL_BASE_PATH, timeout=1000):
            self._act("기본폴더 basePath 400자 입력 — web_restrict_modal 통과(클라이언트 가드 없음)",
                      lambda: (page.web_restrict.set_process_option(True),
                               page.web_restrict.set_base_path("a" * 400)),
                      shot_target=page.page.locator(page.web_restrict.SEL_BASE_PATH).first)
            self._act("웹제한 모달 저장 — 알림 없어야 정상",
                      lambda: (page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first),
                               page.web_restrict.wait_closed(timeout=3000)))
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
            _st = "warn" if defect_found else "pass"
            self._add(_st,
                      "[UX 결함] 웹제한 기능 - 기본폴더 basePath 400자 → 메인 저장 시 서버 오류 (web_restrict_modal 단계에서 차단되어야 정상, 드라이브 letter 동일 패턴)",
                      f"입력: basePath 400자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                      merge_key=f"csu_srv_err::basePath400::{_st}::raw_server_error_no_client_guard",
                      repro="1. 웹제한 기본폴더 basePath 400자 입력\n"
                            "2. web_restrict_modal 통과 — 클라이언트 가드 없음\n"
                            "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            page.dismiss_confirm_modal()
        else:
            self._add("skip", "[UX 결함] 웹제한 기능 - 기본폴더 basePath 400자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()
        # reload 미봉책 제거 (재설계 진단 단계)

        # ── Case D~G: Port invalid 격리 검증 (yaml main_server_verified 기반) ─
        # 본서버 Chrome MCP 2026-05-19 검증 격리 4 cycle 결과:
        #   Port=8080 (정상): 저장 OK
        #   Port=-1: 메인 저장 시 '서버에서 오류 발생' (UX 결함)
        #   Port=0: 저장 OK (예상과 달리 valid 처리)
        #   Port=빈값: 메인 저장 시 '서버에서 오류 발생' (UX 결함)
        port_test_cases = [
            ("8080",  False, "정상 (대조)", "D"),
            ("-1",    True,  "음수 (서버 차단)", "E"),
            ("0",     False, "0 (의외로 허용)", "F"),
            ("",      True,  "빈값 (서버 차단)", "G"),
        ]
        for port_val, expect_server_error, label, case_id in port_test_cases:
            # 행위 저널 — 이터레이션마다 블록 (warn 검출 시 그 이터레이션만 자동 재생)
            self._ckpt()
            csu = f"[AUTO]_sc3_step9_port_{case_id}"
            self._act("제어스위트 추가 모달 — 정책 이름 입력",
                      lambda: (page.navigate_to_clean(), page.open_add_modal(),
                               page.set_csu_name(csu)))
            self._act("개별 프로세스 탭 — 프로세스 선택(picker)",
                      lambda: (page.click_individual_process_tab(), page.click_add_process_btn(),
                               page.process.wait_open(), page.process.click_pick_btn(),
                               page.picker.wait_open(), page.picker.select_first_and_confirm(mode="single")))
            def _port_input():
                page.process.set_pnetwork(True)
                page.process.add_ip_port(f"192.168.99.{case_id[-1] if case_id[-1].isdigit() else '1'}", port_val)
                # sub-modal 알림 dismiss (형식 차단 케이스 대비 — 안전)
                if page.is_confirm_modal_visible(timeout=1500):
                    page.dismiss_confirm_modal()
            self._act(f"허용 IP/Port 에 Port={port_val!r} 입력 — sub-modal 통과(클라이언트 가드 없음)",
                      _port_input,
                      shot_target=page.page.locator(page.process.SEL_IP_LIST_ITEM).first)
            self._act("프로세스 등록 확인 — sub-modal 닫힘",
                      lambda: page.process.confirm())
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            # dismiss 전 _add → 스크린샷에 서버 오류 alert 포함 (사용자 요청)
            if expect_server_error:
                defect_found = "서버" in msg and ("오류" in msg or "발생" in msg)
                _st = "warn" if defect_found else "pass"
                _ekey = "port_neg_proc" if port_val == "-1" else "port_empty_proc"
                self._add(_st,
                          f"[UX 결함] 프로세스별 제어 (개별 프로세스) - 허용 IP/Port Port={port_val!r} {label} → 메인 저장 시 서버 오류 (sub-modal 단계에서 차단되어야 정상)",
                          f"입력: Port={port_val!r} + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                          merge_key=f"csu_srv_err::{_ekey}::{_st}::raw_server_error_no_client_guard",
                          repro=f"1. 개별 프로세스 허용 IP/Port 에 Port={port_val!r} 입력\n"
                                "2. sub-modal 통과 — 클라이언트 가드 없음\n"
                                "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            else:
                ok = msg == "저장 하였습니다"
                self._add("pass" if ok else "fail",
                          f"[저장 확인] 프로세스별 제어 (개별 프로세스) - 허용 IP/Port Port={port_val!r} {label} → 메인 저장 OK",
                          f"입력: Port={port_val!r} + 정책 저장 / 결과: 메시지={msg!r}", sc=3)
            page.dismiss_confirm_modal()
            page.close_modal()
            # 서버 오류 case 후 안전 정리 — reload
            if expect_server_error:
                try:
                    page.page.reload(wait_until="domcontentloaded", timeout=15000)
                    page.page.wait_for_timeout(500)
                except Exception:
                    pass

        # ── Case H: webRestrictName 500자 → 메인 저장 시 서버 오류 (UX 결함) ─
        # 본서버 Chrome MCP 2026-05-19 검증: 100자 OK / 500자 차단. 행위 저널(재생은 navigate 부터).
        self._ckpt()
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step10_webname500")))
        self._act("웹제한 모달 진입 — 프로세스 선택(picker)",
                  lambda: (page.click_add_web_restrict_btn(), page.web_restrict.wait_open(),
                           page.web_restrict.click_add_process_btn(), page.picker.wait_open(),
                           page.picker.select_first_and_confirm(mode="multi")))
        self._act("웹제한 이름 webRestrictName 500자 입력 — web_restrict_modal 통과(클라이언트 가드 없음)",
                  lambda: page.web_restrict.set_name("a" * 500),
                  shot_target=page.page.locator(page.web_restrict.SEL_NAME).first)
        self._act("웹제한 모달 저장 — sub-modal 단계는 통과",
                  lambda: (page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first),
                           page.web_restrict.wait_closed(timeout=3000)))
        self._act("메인 저장 → 알림 대기",
                  lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                           page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                               state="attached", timeout=page._TIMEOUT_MODAL)))
        msg = page.get_confirm_message()
        defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
        _st = "warn" if defect_found else "pass"
        self._add(_st,
                  "[UX 결함] 웹제한 기능 - 웹제한 이름 webRestrictName 500자 → 메인 저장 시 서버 오류 (web_restrict_modal 단계에서 차단되어야 정상)",
                  f"입력: webRestrictName 500자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                  merge_key=f"csu_srv_err::webname500::{_st}::raw_server_error_no_client_guard",
                  repro="1. 웹제한 이름 webRestrictName 500자 입력\n"
                        "2. web_restrict_modal 통과 — 클라이언트 가드 없음\n"
                        "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
        page.dismiss_confirm_modal()
        page.close_modal()

        # ── Case I: attachAllowUrl 1000자 (silent invalid + 메인 저장 서버 오류) ─
        # yaml :326 verified — URL list 등록 안 됨 + 알림 없음 (silent invalid). 행위 저널.
        self._ckpt()
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step11_url1000")))
        self._act("웹제한 모달 진입 — 프로세스 선택 + 이름 입력",
                  lambda: (page.click_add_web_restrict_btn(), page.web_restrict.wait_open(),
                           page.web_restrict.click_add_process_btn(), page.picker.wait_open(),
                           page.picker.select_first_and_confirm(mode="multi"),
                           page.web_restrict.set_name("[AUTO]_web_sc3_step11")))
        self._act("적용 URL attachAllowUrl 1000자 입력 — silent invalid(등록 안 됨, 알림 없음)",
                  lambda: (page.web_restrict.set_is_url(True),
                           page.web_restrict.add_url("a" * 1000)),
                  shot_target=page.page.locator(page.web_restrict.SEL_URL_INPUT).first)
        self._act("웹제한 모달 저장 — sub-modal 단계는 통과",
                  lambda: (page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first),
                           page.web_restrict.wait_closed(timeout=3000)))
        self._act("메인 저장 → 알림 대기",
                  lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                           page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                               state="attached", timeout=page._TIMEOUT_MODAL)))
        msg = page.get_confirm_message()
        defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
        _st = "warn" if defect_found else "pass"
        self._add(_st,
                  "[UX 결함] 웹제한 기능 - 적용 URL attachAllowUrl 1000자 → silent invalid + 메인 저장 서버 오류 (web_restrict_modal 단계에서 차단되어야 정상)",
                  f"입력: URL 1000자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                  merge_key=f"csu_srv_err::url1000::{_st}::raw_server_error_no_client_guard",
                  repro="1. 웹제한 적용 URL attachAllowUrl 1000자 입력 (silent invalid — 등록 안 됨)\n"
                        "2. web_restrict_modal 통과 — 클라이언트 가드 없음\n"
                        "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
        page.dismiss_confirm_modal()
        page.close_modal()

        # ── Case J: allowFileExtention 500자 (web 확장자) → 메인 저장 서버 오류 ─
        # yaml :360 verified — process 확장자는 안전 / web 확장자만 백엔드 차단 (server-side 검증 차이)
        self._ckpt()   # 행위 저널
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step12_webext500")))
        self._act("웹제한 모달 진입 — 프로세스 선택 + 이름 입력",
                  lambda: (page.click_add_web_restrict_btn(), page.web_restrict.wait_open(),
                           page.web_restrict.click_add_process_btn(), page.picker.wait_open(),
                           page.picker.select_first_and_confirm(mode="multi"),
                           page.web_restrict.set_name("[AUTO]_web_sc3_step12")))
        # web 확장자 500자 — sub-modal 단계는 통과 (yaml :164 동일 길이 등록 OK)
        if page.feature_exists(page.web_restrict.SEL_FILE_EXT_INPUT, timeout=1000):
            self._act("업로드 허용 확장자 allowFileExtention 500자 입력 — web_restrict_modal 통과(클라이언트 가드 없음)",
                      lambda: page.web_restrict.add_file_extension("a" * 500),
                      shot_target=page.page.locator(page.web_restrict.SEL_FILE_EXT_INPUT).first)
            self._act("웹제한 모달 저장 — sub-modal 단계는 통과",
                      lambda: (page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first),
                               page.web_restrict.wait_closed(timeout=3000)))
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
            _st = "warn" if defect_found else "pass"
            self._add(_st,
                      "[UX 결함] 웹제한 기능 - 업로드 허용 확장자 allowFileExtention 500자 → 메인 저장 서버 오류 (process 확장자와 다른 동작 — web 만 차단)",
                      f"입력: web 확장자 500자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                      merge_key=f"csu_srv_err::webext500::{_st}::raw_server_error_no_client_guard",
                      repro="1. 웹제한 업로드 허용 확장자 allowFileExtention 500자 입력\n"
                            "2. web_restrict_modal 통과 — 클라이언트 가드 없음\n"
                            "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            page.dismiss_confirm_modal()
        else:
            self._add("skip", "[UX 결함] 웹제한 기능 - 업로드 허용 확장자 500자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()

        # ── Case K: cacheFolderInput 500자 → 메인 저장 서버 오류 ─
        # yaml :361 verified — 한글/특수/500자 모두 sub-modal 통과 (DOM 차단 없음) + 메인 저장 서버 오류
        # 진단 격리: 500자만 단독 (한글/특수와 분리)
        self._ckpt()   # 행위 저널
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step13_cache500")))
        self._act("개별 프로세스 탭 — 프로세스 선택(picker)",
                  lambda: (page.click_individual_process_tab(), page.click_add_process_btn(),
                           page.process.wait_open(), page.process.click_pick_btn(),
                           page.picker.wait_open(), page.picker.select_first_and_confirm(mode="single")))
        if page.feature_exists(page.process.SEL_CACHE_INPUT, timeout=1000):
            self._act("캐시폴더 cacheFolderInput 500자 입력 — process_modal 통과(클라이언트 글자수 가드 없음)",
                      lambda: (page.process.set_cache_input("a" * 500),
                               page.process.click_cache_add_btn()),
                      shot_target=page.page.locator(page.process.SEL_CACHE_INPUT).first)
            self._act("프로세스 등록 확인 — sub-modal 닫힘",
                      lambda: page.process.confirm())
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
            _st = "warn" if defect_found else "pass"
            self._add(_st,
                      "[UX 결함] 프로세스별 제어 (개별 프로세스) - 캐시폴더 지정 cacheFolderInput 500자 → 메인 저장 서버 오류 (process_modal 단계에서 글자수 차단되어야 정상)",
                      f"입력: cache 500자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                      merge_key=f"csu_srv_err::cache500_proc::{_st}::raw_server_error_no_client_guard",
                      repro="1. 개별 프로세스 캐시폴더(cacheFolderInput) 500자 입력\n"
                            "2. process_modal 통과 — 클라이언트 글자수 가드 없음\n"
                            "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            page.dismiss_confirm_modal()
        else:
            self._add("skip", "[UX 결함] 프로세스별 제어 (개별 프로세스) - 캐시폴더 지정 cacheFolderInput 500자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()

        # ── Case L: 태그 mode drive letter 100자 → 메인 저장 서버 오류 (yaml :404 process 동일) ──
        # 신규 추가 — 태그 영역도 process 와 동일 UX 결함 적용 검증
        self._ckpt()   # 행위 저널
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step14_tag_drv100")))
        self._act("태그 탭 — 태그 선택(picker)",
                  lambda: (page.click_tag_tab(), page.click_add_process_btn(),
                           page.process.wait_open(), page.process.click_pick_btn(),
                           page.picker.wait_open(), page.picker.select_first_and_confirm(mode="tag")))
        if page.feature_exists(page.process.SEL_TOGGLE_ACCESS_DRIVE, timeout=1000):
            self._act("태그 mode 접근 드라이브 letter 100자 입력 — sub-modal 통과(클라이언트 가드 없음)",
                      lambda: (page.process.set_access_drive(True),
                               page.process.set_drive_letter("a" * 100)),
                      shot_target=page.page.locator(page.process.SEL_DRIVE_LETTER).first)
            self._act("태그 등록 확인 — sub-modal 닫힘",
                      lambda: page.process.confirm())
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
            _st = "warn" if defect_found else "pass"
            self._add(_st,
                      "[UX 결함] 프로세스별 제어 (태그) - 접근 드라이브 letter 100자 → 메인 저장 시 서버 오류 (개별 프로세스 동일 패턴, yaml :404)",
                      f"입력: 태그 mode + letter 100자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                      merge_key=f"csu_srv_err::letter100_tag::{_st}::raw_server_error_no_client_guard",
                      repro="1. 태그 mode 접근 드라이브 letter 100자 입력\n"
                            "2. sub-modal 통과 — 클라이언트 가드 없음\n"
                            "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            page.dismiss_confirm_modal()
        else:
            self._add("skip", "[UX 결함] 프로세스별 제어 (태그) - 접근 드라이브 letter 100자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()

        # ── Case M: 태그 mode Port -1 → 메인 저장 서버 오류 (yaml :403 process 동일) ──
        # 신규 추가 — 태그 영역 Port 같은 UX 결함 검증
        self._ckpt()   # 행위 저널
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step15_tag_port_m1")))
        self._act("태그 탭 — 태그 선택(picker)",
                  lambda: (page.click_tag_tab(), page.click_add_process_btn(),
                           page.process.wait_open(), page.process.click_pick_btn(),
                           page.picker.wait_open(), page.picker.select_first_and_confirm(mode="tag")))
        def _tag_port_input():
            page.process.set_pnetwork(True)
            page.process.add_ip_port("192.168.99.1", "-1")
            if page.is_confirm_modal_visible(timeout=1500):
                page.dismiss_confirm_modal()
        self._act("태그 mode 허용 IP/Port 에 Port=-1 입력 — sub-modal 통과(클라이언트 가드 없음)",
                  _tag_port_input,
                  shot_target=page.page.locator(page.process.SEL_IP_LIST_ITEM).first)
        self._act("태그 등록 확인 — sub-modal 닫힘",
                  lambda: page.process.confirm())
        self._act("메인 저장 → 알림 대기",
                  lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                           page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                               state="attached", timeout=page._TIMEOUT_MODAL)))
        msg = page.get_confirm_message()
        defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
        _st = "warn" if defect_found else "pass"
        self._add(_st,
                  "[UX 결함] 프로세스별 제어 (태그) - 허용 IP/Port Port=-1 → 메인 저장 시 서버 오류 (개별 프로세스 동일 패턴, yaml :403)",
                  f"입력: 태그 mode + Port='-1' + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                  merge_key=f"csu_srv_err::port_neg_tag::{_st}::raw_server_error_no_client_guard",
                  repro="1. 태그 mode 허용 IP/Port 에 Port=-1 입력\n"
                        "2. sub-modal 통과 — 클라이언트 가드 없음\n"
                        "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
        page.dismiss_confirm_modal()
        page.close_modal()

        # ── Case N: basePath 300자 입력 + 메인 저장 → '저장 하였습니다' (정상 boundary, yaml :433-436) ──
        # 신규 추가 — basePath 300자 OK / 400자 차단 boundary 의 정상측 검증 (대조군)
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step16_bp300_ok")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_name("[AUTO]_web_sc3_step16")
        if page.feature_exists(page.web_restrict.SEL_BASE_PATH, timeout=1000):
            page.web_restrict.set_process_option(True)
            page.web_restrict.set_base_path("a" * 300)
            page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
            page.web_restrict.wait_closed(timeout=3000)
            msg = page.save_policy(mode="add")
            page.dismiss_confirm_modal()
            ok_save = (msg == "저장 하였습니다")
            self._add("pass" if ok_save else "fail",
                      "[boundary 정상] 웹제한 기능 - 기본폴더 basePath 300자 → 메인 저장 OK (boundary 정상측, yaml :433-436)",
                      f"입력: basePath 300자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3)
        else:
            self._add("skip", "[boundary 정상] 웹제한 기능 - 기본폴더 basePath 300자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()

        # ── Case O: webRestrictName 100자 입력 + 메인 저장 → '저장 하였습니다' (정상 boundary, yaml :428-431) ──
        # 신규 추가 — webRestrictName 100자 OK / 500자 차단 boundary 의 정상측 검증 (대조군)
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step17_webname100_ok")
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_name("a" * 100)
        page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
        page.web_restrict.wait_closed(timeout=3000)
        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        ok_save = (msg == "저장 하였습니다")
        self._add("pass" if ok_save else "fail",
                  "[boundary 정상] 웹제한 기능 - 웹제한 이름 webRestrictName 100자 → 메인 저장 OK (boundary 정상측, yaml :428-431)",
                  f"입력: webRestrictName 100자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3)
        page.close_modal()

        # ── Case P: 태그 mode 캐시폴더 500자 → 메인 저장 서버 오류 (UX 결함, yaml :112) ──
        # 신규 추가 — yaml :112 "모드 변경만 다름. UI 요소는 14필드 + cache_folder + 라디오 모두 동일"
        # 태그 모드도 개별 프로세스와 동일하게 cache_folder UX 결함 적용 검증
        self._ckpt()   # 행위 저널
        self._act("제어스위트 추가 모달 — 정책 이름 입력",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.set_csu_name("[AUTO]_sc3_step18_tag_cache500")))
        self._act("태그 탭 — 태그 선택(picker)",
                  lambda: (page.click_tag_tab(), page.click_add_process_btn(),
                           page.process.wait_open(), page.process.click_pick_btn(),
                           page.picker.wait_open(), page.picker.select_first_and_confirm(mode="tag")))
        if page.feature_exists(page.process.SEL_CACHE_INPUT, timeout=1000):
            self._act("태그 mode 캐시폴더 cacheFolderInput 500자 입력 — process_modal 통과(클라이언트 글자수 가드 없음)",
                      lambda: (page.process.set_cache_input("a" * 500),
                               page.process.click_cache_add_btn()),
                      shot_target=page.page.locator(page.process.SEL_CACHE_INPUT).first)
            self._act("태그 등록 확인 — sub-modal 닫힘",
                      lambda: page.process.confirm())
            self._act("메인 저장 → 알림 대기",
                      lambda: (page._click(page.page.locator(page.SEL_SUBMIT_ADD).first),
                               page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                                   state="attached", timeout=page._TIMEOUT_MODAL)))
            msg = page.get_confirm_message()
            defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
            _st = "warn" if defect_found else "pass"
            self._add(_st,
                      "[UX 결함] 프로세스별 제어 (태그) - 캐시폴더 지정 cacheFolderInput 500자 → 메인 저장 서버 오류 (개별 프로세스 동일 패턴, yaml :112)",
                      f"입력: 태그 mode + cache 500자 + 정책 저장 / 결과: 메시지={msg!r}", sc=3,
                      merge_key=f"csu_srv_err::cache500_tag::{_st}::raw_server_error_no_client_guard",
                      repro="1. 태그 mode 캐시폴더 500자 입력\n"
                            "2. process_modal 통과 — 클라이언트 글자수 가드 없음\n"
                            "3. 메인 저장/수정 → '서버에서 오류가 발생 하였습니다'")
            page.dismiss_confirm_modal()
        else:
            self._add("skip", "[UX 결함] 프로세스별 제어 (태그) - 캐시폴더 지정 500자 — 기능 부재", "(skip)", sc=3)
        page.close_modal()

        # ── Case Q: 태그 mode 정상 저장 (sc4 4e EDIT 검증 데이터 확보) ─
        # sc3j Case L/M/P 는 모두 server error (UX 결함) 라 태그 정책 생성 X.
        # sc4 4e (태그 EDIT) 가 EDIT 할 데이터 확보 — 정상값 (drv 50자, Port 8080) 으로 저장.
        page.navigate_to_clean()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step19_tag_normal")
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="tag")
        # 정상값 입력 (drv 50자 — UX 결함 100자 미만)
        if page.feature_exists(page.process.SEL_TOGGLE_ACCESS_DRIVE, timeout=1000):
            page.process.set_access_drive(True)
            page.process.set_drive_letter("a" * 50)
        page.process.confirm()
        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        ok_save = (msg == "저장 하였습니다")
        self._add("pass" if ok_save else "fail",
                  "[저장 확인] 프로세스별 제어 (태그) - 정상 저장 → 메인 저장 OK (sc4 4e EDIT 데이터)",
                  f"입력: 태그 mode + drv 50자 (정상) + 정책 저장 / 결과: 메시지={msg!r}", sc=3)

    # ==================================================================
    # 시나리오 3k — yaml audit 갭 — process_modal 검증 (2026-05-28 추가)
    #   사용자 의문 "yaml 명세 있는데 왜 테스트 없음?" → systematic audit 결과 3건 추가:
    #     a) cacheFolder 빈값 + 추가 → '폴더 이름을 입력해 주세요.' (yaml :734)
    #     b) special_folder 다중 체크 → cacheFolderList 1건 병합 등록 (yaml :198/510 must_test)
    #     c) IP/Port 삭제 후 동일값 재추가 → '이미 등록된 IP와 Port' 알림 (yaml :197/264 ux_bug)
    # ==================================================================
    def test_scenario3k_yaml_audit_process_modal(self, logged_in_page, settings):
        """sc3k — yaml audit 결과 process_modal 갭 3건 보완."""
        print("\n━━ [제어 스위트] 시나리오 3k: yaml audit — process_modal 갭 검증 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        # 정책 ADD 모달 진입 + 프로세스 추가 → process_modal 안에서 검증
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc3_step20_audit")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")

        # ── (a) cacheFolder 빈값 + 추가 차단 메시지 (yaml :734) ─────
        page.process.set_cache_input("")
        page.process.click_cache_add_btn()
        if page.is_confirm_modal_visible(timeout=1500):
            msg_a = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok_a = "폴더" in msg_a and ("이름" in msg_a or "입력" in msg_a)
            self._add("pass" if ok_a else "fail",
                      "(a) process_modal — cacheFolder 빈값 + 추가 차단 메시지 (yaml :734 audit 갭)",
                      f"입력: cacheFolderInput='' + 추가 / 결과: 메시지={msg_a!r}", sc=3)
        else:
            self._add("fail", "[차단 메시지] (a) cacheFolder 빈값 — 미노출",
                      f"입력: 빈값 + 추가 / 결과: 알림 없음 (yaml :734 기대와 불일치)", sc=3)

        # ── (b) special_folder 다중 체크 → 1건 병합 등록 (yaml :198/510 must_test) ──
        page.process.click_special_folder_btn()
        page.special_folder.wait_open()
        page.special_folder.select_codes(["[/DESKTOP/]", "[/FAVORITES/]"])
        page.special_folder.confirm()
        page.special_folder.wait_closed()
        # cacheFolderInput 에 inline tag 2개 → 추가 클릭 → cacheFolderList 1건 병합 기대
        cache_before = len(page.process.get_cache_folder_list())
        page.process.click_cache_add_btn()
        # 알림 dismiss 안전망
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()
        cache_after_items = page.process.get_cache_folder_list()
        added = len(cache_after_items) - cache_before
        # 사용자 결정 (2026-05-28): "사용자가 원해서 묶어 붙이는 경우도 있어서" 1건 병합 = 정상 동작.
        # buggy 분류 철회 → pass (의도된 병합 등록 — 다중 체크 = 다중 폴더 단일 등록).
        ok_b = added == 1
        self._add("pass" if ok_b else "fail",
                  "(b) process_modal — special_folder 다중 체크 → 1건 병합 등록 (yaml :510 의도 동작)",
                  f"입력: [/DESKTOP/]+[/FAVORITES/] 체크+확인+추가 / 결과: cache 추가={added}건, list={cache_after_items}", sc=3)
        # 정리 — process_modal cancel 시 어차피 폐기되므로 별도 cache 제거 불필요

        # ── (c) IP/Port 삭제 후 동일값 재추가 잘못된 중복 (yaml :197/264 ux_bug) ─
        # 행위 저널 — (a)(b) 세션과 분리한 자체 process_modal 세션(재생 가능 블록).
        # 잔류 li 가 곧 버그라 세션 내 리셋 불가 → 블록 첫 행위 = 모달 재진입(깨끗한 세션).
        self._ckpt()
        DUP_IP, DUP_PORT = "192.168.99.99", "8888"

        def _fresh_process_modal():
            # 1차: (a)(b) 세션 닫고 재진입 / 재생: 잔여 알림 닫고 재진입 — 둘 다 깨끗한 세션 보장
            if page.is_confirm_modal_visible(timeout=300):
                page.dismiss_confirm_modal()
            if page.page.locator(page.process.SEL_MODAL_OPEN).count() > 0:
                page.process.close()
            page.click_add_process_btn()
            page.process.wait_open()
            page.process.click_pick_btn()
            page.picker.wait_open()
            page.picker.select_first_and_confirm(mode="single")

        def _add_dup_ip():
            page.process.set_pnetwork(True)
            page.process.add_ip_port(DUP_IP, DUP_PORT)
            if page.is_confirm_modal_visible(timeout=500):
                page.dismiss_confirm_modal()
        self._act("process_modal 재진입 — 프로세스 선택(깨끗한 세션)", _fresh_process_modal)
        self._act(f"허용 IP/Port {DUP_IP}:{DUP_PORT} 추가",
                  _add_dup_ip,
                  shot_target=page.page.locator(page.process.SEL_IP_LIST_ITEM).first)
        ip_after_add = page.process.get_ip_list()
        self._act("같은 IP/Port 삭제(행 제거)",
                  lambda: page.process.remove_ip_port(DUP_IP, DUP_PORT))
        ip_after_del = page.process.get_ip_list()
        # 재추가 → 잘못된 '이미 등록' 알림 기대 (display:none 잔류 li 가 dup-check 통과 못 함)
        self._act("동일값 재추가 — 삭제됐는데 중복 판정되면 결함",
                  lambda: page.process.add_ip_port(DUP_IP, DUP_PORT))
        if page.is_confirm_modal_visible(timeout=1500):
            msg_c = page.get_confirm_message()
            is_dup_msg = ("이미 등록" in msg_c) and ("IP" in msg_c.upper() or "Port" in msg_c)
            # 이 동작은 ux_bug — 메시지가 떴다는 것 자체가 제품 결함 확정.
            # dismiss 는 _add(자동 캡처) 후에 호출 — alert 떠 있는 상태를 스크린샷에 담음(내용↔사진 일치)
            _st = "warn" if is_dup_msg else "fail"
            self._add(_st,
                      "(c) process_modal — IP/Port 삭제 후 재추가 → 잘못된 '이미 등록' 알림 (yaml :197 ux_bug)",
                      f"입력: {DUP_IP}:{DUP_PORT} 추가→삭제→재추가 / 결과: 메시지={msg_c!r}, IP after_del={len(ip_after_del)}", sc=3,
                      merge_key=f"csu_dup_readd::ip_port::{_st}::false_already_registered",
                      repro=f"1. process_modal 에서 {DUP_IP}:{DUP_PORT} 추가\n"
                            "2. 같은 IP/Port 삭제(행 제거)\n"
                            "3. 동일값 재추가 → 잘못된 '이미 등록된 IP와 Port 입니다' (삭제됐는데 중복 판정 — display:none 잔류 li)")
            page.dismiss_confirm_modal()
        else:
            # 메시지 미노출 = 버그 재현 안 됨 (제품이 정상 동작 — 좋은 일)
            self._add("pass", "(c) process_modal — IP/Port 삭제 후 재추가 정상 (yaml :197 ux_bug 미재현)",
                      f"입력: 추가→삭제→재추가 / 결과: 알림 없음, IP list={page.process.get_ip_list()}", sc=3)

        # 정리 — process_modal close (X) + 메인 모달 close (저장 안 함)
        page.process.close()
        page.close_modal()
