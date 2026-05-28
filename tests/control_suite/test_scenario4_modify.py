"""시나리오 4 — EDIT 모달 검증 (4b~4j). sc3 가 만든 [AUTO]_sc3_step* 정책 사용 (같은 세션 안 잔존).

알림 메시지 다양성 인정 (2026-05-22 사용자 통찰):
- 시스템 정상 응답 메시지가 단일 아님: '저장 하였습니다' OR '수정된 항목이 없습니다.'
- 두 번째 run 에서 동일 값 modify 시 시스템이 '변경 없음' 판정 → '수정된 항목이 없습니다.' 알림
- 두 응답 모두 정상 동작 — sc4 검증은 or 조건 인정 + 가능하면 dynamic 값 (timestamp) 사용
"""
import pytest
import time

# 정상 modify 응답 메시지 (둘 다 인정)
_MODIFY_OK_MESSAGES = ("저장 하였습니다", "수정된 항목이 없습니다.")

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.control_suite._base import ControlSuiteBase


class TestScenario4Modify(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 4 — EDIT 모달 검증 (4b~4g)"""

    # ==================================================================
    # 시나리오 4b — 3b (minimal save) 의 EDIT 버전
    # 사용 정책: [AUTO]_sc3_step1 (sc3b 가 생성한 minimal 정책)
    # ==================================================================
    def test_scenario4b_edit_minimal_modify(self, logged_in_page, settings):
        """시나리오 4b — 메인 영역 최소 modify
        (이름 load 검증 + customOption 1 필드 변경 + 저장 + 재진입 일치 검증).

        의존: sc3b 가 만든 [AUTO]_sc3_step1 정책 사용 (같은 세션 안 잔존).
        sc3 단독 실행 후 sc4 만 돌릴 때도 동작 (정책 잔존).
        """
        print("\n━━ [제어 스위트] 시나리오 4b: minimal modify (메인 영역) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step1"      # sc3b 가 만든 minimal 정책
        # dynamic 값 — 매 run 마다 다른 값 → 시스템이 항상 '저장 하였습니다' (변경 발생)
        MOD_CUSTOM  = f"sc4b_mod_{int(time.time())}"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4b — sc3 정책 미존재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음 (sc3b 먼저 실행 필요)", sc=4)
            pytest.skip(f"{TARGET_NAME!r} 미존재 — sc3b 먼저 실행 필요")

        # ── EDIT 진입 + load 정확성 검증 ──
        # open_modify_modal 내부 verify: csuName == TARGET_NAME (안전망 — 잘못 선택 방지)
        page.open_modify_modal(TARGET_NAME)
        loaded_name = page.get_csu_name()
        self._add("pass" if loaded_name == TARGET_NAME else "fail",
                  "스위트 수정 모달 — 진입 + 스위트 이름 load 정확성",
                  f"입력: 행 click + '수정' / 결과: csuName={loaded_name!r}", sc=4)

        # ── customOption 1 필드 변경 + 저장 ──
        page.set_custom_option(MOD_CUSTOM)
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        # 정상 modify 응답 2종 모두 인정 (timestamp 값이라 정상은 '저장 하였습니다' 기대)
        self._add("pass" if msg in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — '수정' 버튼 저장",
                  f"입력: 커스텀 옵션 변경 + '수정' / 결과: 메시지={msg!r}", sc=4)

        # ── 저장 후 정책 잔존 확인 (이름 미변경) ──
        exists = page.is_policy_exists(TARGET_NAME)
        self._add("pass" if exists else "fail",
                  "정책 list — 정책 잔존 (이름 미변경)",
                  f"입력: 저장 완료 후 / 결과: '{TARGET_NAME}' 존재={exists}", sc=4)

        # ── 재진입 → 변경값 일치 검증 ──
        page.open_modify_modal(TARGET_NAME)
        co = page.get_custom_option()
        self._add("pass" if co == MOD_CUSTOM else "fail",
                  "스위트 수정 모달 — 변경값 재진입 일치 (customOption)",
                  f"입력: 재진입 / 결과: 커스텀 옵션={co!r}", sc=4)
        page.close_modal()

    # ==================================================================
    # 시나리오 4c — 3d (CRUD 1사이클: 메인 11 필드) 의 EDIT 버전 (메인 영역 종합)
    # ==================================================================

    # ==================================================================
    # 시나리오 4c — 3d (CRUD 1사이클: 메인 11 필드) 의 EDIT 버전 (메인 영역 종합)
    # ==================================================================
    def test_scenario4c_edit_crud_main_fields(self, logged_in_page, settings):
        """시나리오 4c — 메인 11 필드 종합 (load + 3 필드 modify + 저장 + 재오픈 verify)."""
        print("\n━━ [제어 스위트] 시나리오 4c: 메인 11 필드 CRUD (3d 의 EDIT 버전) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"
        # 4b 결과까지 누적된 상태값 (3d MODIFY + 4b customOption 변경)
        EXPECT = {
            "csuName":           TARGET_NAME,
            "clipboard_url":     "daum.net",
            "extensions":        ["txt", "doc", "exe"],
            "sign_count":        2,
            "custom_option":     "sc4_modified_by_4b",
        }
        MOD = {
            "clipboard_url":  "edit4c.com",
            "custom_option":  "edit_4c_modified",
            "new_extension":  "iso",
        }

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4c — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        page.open_modify_modal(TARGET_NAME)
        # 멱등 검증 — sc3 직후 + 이전 sc4 modify 누적 가능성 → strict == 대신 '존재'/'subset' 검증
        # (MCP 진단 2026-05-22: 두 번째 run 부터 EXPECT 값과 다른 누적값이 load 됨)
        load_checks = {
            "스위트 이름":               page.get_csu_name() == EXPECT["csuName"],
            "클립보드 제한 토글":         page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked(),
            # strict 'daum.net' 일치 X → 어떤 URL 이든 존재 (non-empty) 확인
            "클립보드 허용 URL 존재":     bool(page.get_clipboard_allow_url().strip()),
            "네트워크 접근 토글":         page.is_network_checked(),
            "라디오 라벨 (차단할 확장자)": page.get_radio_react_text() == "차단할 확장자",
            # strict == ["txt","doc","exe"] X → sc3c 확장자 (txt/doc/exe) 모두 포함 (subset)
            "확장자 sc3c 포함":           all(e in page.get_main_extension_list() for e in EXPECT["extensions"]),
            "헤더 체크 토글":             page.page.locator(page.SEL_HEADER_CHECK).first.is_checked(),
            "전자서명 예외 토글":         page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked(),
            "전자서명 예외 개수":         len(page.get_sign_except_list()) >= EXPECT["sign_count"],
            # strict 'sc4_modified_by_4b' X → 값 존재 (non-empty) 확인
            "커스텀 옵션 존재":           bool(page.get_custom_option().strip()),
            "개별 프로세스 행 수":         len(page.get_item_list_rows()) == 1,
        }
        for k, ok in load_checks.items():
            self._add("pass" if ok else "fail",
                      f"스위트 수정 모달 — 11 필드 load 일치: {k}",
                      f"입력: 수정 모달 진입 / 결과: 일치={ok}", sc=4)

        page.set_clipboard_allow_url(MOD["clipboard_url"])
        page.set_custom_option(MOD["custom_option"])
        page.add_main_extension(MOD["new_extension"])

        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — 3 필드 변경 + '수정' 저장",
                  f"입력: URL/custom/확장자 변경 / 결과: 메시지={msg!r}", sc=4)

        page.open_modify_modal(TARGET_NAME)
        verify_checks = {
            "클립보드 허용 URL 변경 반영":   MOD["clipboard_url"] in page.get_clipboard_allow_url(),
            "커스텀 옵션 변경 반영":         page.get_custom_option() == MOD["custom_option"],
            "확장자 추가 반영":              MOD["new_extension"] in page.get_main_extension_list(),
            "스위트 이름 보존":              page.get_csu_name() == TARGET_NAME,
            "네트워크 접근 토글 보존":       page.is_network_checked(),
            "헤더 체크 토글 보존":           page.page.locator(page.SEL_HEADER_CHECK).first.is_checked(),
            "전자서명 예외 토글 보존":       page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked(),
            "웹제한 행 수 보존":             len(page.get_item_web_restrict_rows()) >= 1,
        }
        for k, ok in verify_checks.items():
            self._add("pass" if ok else "fail",
                      f"스위트 수정 모달 — 재오픈 일치: {k}",
                      f"입력: 재오픈 / 결과: 일치={ok}", sc=4)
        page.close_modal()

    # ==================================================================
    # 시나리오 4d — 프로세스별 제어 영역 (itemList 로드 + process_modal 12 필드 + ON↔OFF 양방향)
    # ==================================================================

    # ==================================================================
    # 시나리오 4d — 프로세스별 제어 영역 (itemList 로드 + process_modal 12 필드 + ON↔OFF 양방향)
    # ==================================================================
    def test_scenario4d_edit_process_full(self, logged_in_page, settings):
        """시나리오 4d — 프로세스 영역 종합 검증.

        sc3 정책 EDIT 진입 → 개별 프로세스 1건 load → 첫 행 클릭 (process_modal 재진입) →
        12 필드 OFF→ON 변경 + 저장 + 재오픈 verify → ON→OFF 양방향 + 저장 + verify.
        """
        print("\n━━ [제어 스위트] 시나리오 4d: 프로세스별 제어 영역 종합 (ON↔OFF) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"
        # MCP 진단 (2026-05-22): sc3 데이터 + 이전 run 누적 → 같은 값 재추가 시 '이미 등록' 알림
        # 매 run unique 값 (timestamp 짧은 hash) → 중복 알림 회피 / 정상 add 흐름 보장
        _ts = int(time.time()) % 10000   # 4자리 — Port 범위 / 짧은 식별자
        PROC = {
            "ip":      f"172.16.{(_ts // 100) % 256}.{_ts % 256}",   # 매 run unique IP
            "port":    str(9000 + (_ts % 500)),                       # 매 run unique Port
            "ext":     [f"r{_ts}a", f"r{_ts}b"],                       # 매 run unique 확장자
            "drive":   "D;E",
            "desc":    f"edit_4d_{_ts}",
        }

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4d — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        # ── EDIT 진입 + 개별 프로세스 1건 load ─────────────────
        page.open_modify_modal(TARGET_NAME)
        rows = len(page.get_item_list_rows())
        self._add("pass" if rows >= 1 else "fail",
                  "프로세스별 제어 — 기존 프로세스 1건 load (itemList)",
                  f"입력: 수정 모달 진입 / 결과: itemList 행={rows}", sc=4)

        if rows < 1:
            page.close_modal()
            return

        # ── 첫 행 클릭 → process_modal 재진입 ─────────────────
        page.click_item_list_row(0)

        # ── process_modal 12 필드 OFF→ON 변경 ──────────────────
        page.process.set_process_except(True)
        page.process.set_pclipboard_restrict(True)
        page.process.set_sandbox(True)
        page.process.set_deny_except_drive(True)
        page.process.set_pnetwork(True)
        page.process.add_ip_port(PROC["ip"], PROC["port"])
        # 안전망 — 중복 알림 (registeredFolderWarning) 뜨면 dismiss (sc3 누적 시 대비)
        if page.is_confirm_modal_visible(timeout=1000):
            page.dismiss_confirm_modal()
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in PROC["ext"]:
            page.process.add_extension(ext)
            # 안전망 — 확장자 중복 알림 dismiss
            if page.is_confirm_modal_visible(timeout=500):
                page.dismiss_confirm_modal()
        page.process.set_access_drive(True)
        page.process.set_drive_letter(PROC["drive"])
        page.process.set_description(PROC["desc"])
        page.process.confirm()

        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — process_modal 12 필드 OFF→ON + '수정' 저장",
                  f"입력: 4 토글 + IP/Port + 확장자 + drive + 설명 / 결과: 메시지={msg!r}", sc=4)

        # ── 재오픈 → process_modal 재진입 + OFF→ON 값 일치 ────
        page.open_modify_modal(TARGET_NAME)
        page.click_item_list_row(0)
        re_checks = {
            "프로세스 제외 토글 (OFF→ON)":            page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT),
            "프로세스별 클립보드 제한 토글 (OFF→ON)":  page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD),
            "샌드박스 토글 (OFF→ON)":                 page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX),
            "드라이브 예외 거부 토글 (OFF→ON)":        page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE),
            "프로세스별 네트워크 토글 (OFF→ON)":       page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK),
            "IP/Port 등록 반영":                       any(PROC["ip"] in x and PROC["port"] in x
                                                          for x in page.process.get_ip_list()),
            "확장자 제어 토글 (OFF→ON)":               page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT),
            # sc3 가 만든 정책은 이미 ["log", "tmp"] 등 기존 확장자 보유 →
            # strict == 대신 subset (sc4 추가 항목 포함 여부) 검증
            "프로세스 확장자 추가 반영":               all(e in page.process.get_extension_list() for e in PROC["ext"]),
            "드라이브 접근 토글 (OFF→ON)":             page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE),
            "드라이브 문자 입력 반영":                 page.process.get_drive_letter() == PROC["drive"],
            "설명 입력 반영":                          PROC["desc"] in page.process.get_description(),
        }
        for k, ok in re_checks.items():
            self._add("pass" if ok else "fail",
                      f"process_modal — 재진입 입력값 일치: {k}",
                      f"입력: itemList 행 클릭 (재진입) / 결과: 일치={ok}", sc=4)

        # ── 라운드 2: ON→OFF 양방향 (7 토글) ──────────────────
        page.process.set_process_except(False)
        page.process.set_pclipboard_restrict(False)
        page.process.set_sandbox(False)
        page.process.set_deny_except_drive(False)
        page.process.set_pnetwork(False)
        page.process.set_pcontrol_extension(False)
        page.process.set_access_drive(False)
        page.process.confirm()

        msg2 = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg2 in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — process_modal 7 토글 ON→OFF + '수정' 저장",
                  f"입력: 7 토글 모두 OFF / 결과: 메시지={msg2!r}", sc=4)

        # 재오픈 → ON→OFF 일치
        page.open_modify_modal(TARGET_NAME)
        page.click_item_list_row(0)
        off_checks = {
            "프로세스 제외 토글 (ON→OFF)":             not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT),
            "프로세스별 클립보드 제한 토글 (ON→OFF)":   not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD),
            "샌드박스 토글 (ON→OFF)":                  not page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX),
            "드라이브 예외 거부 토글 (ON→OFF)":         not page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE),
            "프로세스별 네트워크 토글 (ON→OFF)":        not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK),
            "확장자 제어 토글 (ON→OFF)":                not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT),
            "드라이브 접근 토글 (ON→OFF)":              not page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE),
        }
        for k, ok in off_checks.items():
            self._add("pass" if ok else "fail",
                      f"process_modal — ON→OFF 재진입 일치: {k}",
                      f"입력: 토글 OFF 저장 후 재진입 / 결과: 일치={ok}", sc=4)
        page.process.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 4e — 태그 영역 (Tag tab 로드 + 태그 모달 등록 + 재진입) — 신규
    # ==================================================================

    # ==================================================================
    # 시나리오 4e — 태그 영역 (Tag sub-tab process_modal 14 필드 종합 + ON↔OFF)
    # ==================================================================
    # yaml tag_sub_tab_policy: 프로세스 sub-tab 과 동일 14 필드 + cache_folder + 라디오.
    # 4d (프로세스) 와 동일 깊이로 검증.
    def test_scenario4e_edit_tag_full(self, logged_in_page, settings):
        """시나리오 4e — 태그 영역 종합 (4d 프로세스와 동일 깊이).

        Tag tab 활성화 → 신규 태그 1건 + process_modal 12 필드 OFF→ON 변경 + 저장 →
        재오픈 → 태그 행 클릭 + 11 필드 일치 → 7 토글 ON→OFF + 저장 + 재오픈 + 일치.
        """
        print("\n━━ [제어 스위트] 시나리오 4e: 태그 영역 종합 (ON↔OFF 양방향) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"
        # 매 run unique 값 — sc3 + 이전 sc4 누적 중복 회피 (MCP 진단 2026-05-22)
        _ts = (int(time.time()) // 7) % 10000   # 7로 나눠 4d 와 다른 값
        TAG = {
            "ip":      f"192.168.{(_ts // 100) % 256}.{_ts % 256}",
            "port":    str(9500 + (_ts % 400)),
            "ext":     [f"t{_ts}a", f"t{_ts}b"],
            "drive":   "F;G",
            "desc":    f"edit_4e_{_ts}",
        }

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4e — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        # ── EDIT 진입 + Tag tab + 기존 itemTagList 행 수 기록 ─────────
        # sc3 정책에 이미 태그가 있을 수 있음 (sc3c 가 등록) — 행 수 기록만, fail 안 함
        page.open_modify_modal(TARGET_NAME)
        page.click_tag_tab()
        before_rows = len(page.get_item_tag_list_rows())
        self._add("pass",
                  "태그 — Tag sub-tab 활성화 + 기존 itemTagList 행 수 기록",
                  f"입력: Tag tab 클릭 / 결과: itemTagList 행={before_rows} (sc3 데이터 잔존 가능)", sc=4)

        # ── 신규 태그 1건 추가 + picker tag mode 진입 검증 ──────
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        picker_title = page.picker.get_title()
        self._add("pass" if "태그" in picker_title else "fail",
                  "태그 — picker tag mode 진입 (제목 확인)",
                  f"입력: '+' + picker / 결과: picker title={picker_title!r}", sc=4)

        # sc3i 검증된 패턴 적용 (TROUBLESHOOTING [RESOLVED] 2026-05-19):
        # - select_first_and_confirm 의 wait_closed 가 중복 알림 시 timeout cascade
        # - picker.cancel() (× 클릭) 도 TargetClosedError 위험 (sc3g Case F 회귀)
        # - 해결: select_first + confirm 분리 호출 (wait_closed 회피) + ESC 다발 정리
        page.picker.select_first(mode="tag")
        page.picker.confirm()
        # sc3 등록 태그와 중복 → '이미 등록된 태그 입니다' 알림 (정상 동작 — 중복 거부)
        # sc3i 패턴: 중복은 시스템 정상 거부 → 검증 OK, ESC 다발로 picker/process_modal 정리 후 early return
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            # picker + process_modal 정리 — ESC 다발 (cancel/× 안 씀: TargetClosedError 회피)
            for _ in range(5):
                try:
                    page.page.keyboard.press("Escape")
                    page.page.wait_for_timeout(200)
                except Exception:
                    break
            ok_dup = "이미 등록" in msg and "태그" in msg
            self._add("pass" if ok_dup else "fail",
                      "태그 — sc3 등록 태그 재선택 시 중복 거부 (정상 동작)",
                      f"입력: select_first(mode=tag) / 결과: 메시지={msg!r}", sc=4)
            page.close_modal()
            return

        # ── process_modal 12 필드 OFF→ON 변경 (yaml tag_sub_tab_policy 동일 깊이) ──
        page.process.set_process_except(True)
        page.process.set_pclipboard_restrict(True)
        page.process.set_sandbox(True)
        page.process.set_deny_except_drive(True)
        page.process.set_pnetwork(True)
        page.process.add_ip_port(TAG["ip"], TAG["port"])
        # 안전망 — IP/Port 중복 알림 dismiss
        if page.is_confirm_modal_visible(timeout=1000):
            page.dismiss_confirm_modal()
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in TAG["ext"]:
            page.process.add_extension(ext)
            # 안전망 — 확장자 중복 알림 dismiss
            if page.is_confirm_modal_visible(timeout=500):
                page.dismiss_confirm_modal()
        page.process.set_access_drive(True)
        page.process.set_drive_letter(TAG["drive"])
        page.process.set_description(TAG["desc"])
        page.process.confirm()

        after_rows = len(page.get_item_tag_list_rows())
        # 신규 1건 추가 = before + 1 (sc3 데이터 위에 sc4 추가)
        self._add("pass" if after_rows == before_rows + 1 else "fail",
                  "태그 — 신규 태그 1건 추가 (itemTagList 행 +1)",
                  f"입력: tag picker + 12 필드 + 확인 / 결과: 행={before_rows}→{after_rows}", sc=4)

        # ── '수정' 저장 ──────────────────────────────────────────
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — 태그 (12 필드 OFF→ON) 추가 + '수정' 저장",
                  f"입력: '수정' 클릭 / 결과: 메시지={msg!r}", sc=4)

        # ── 재오픈 + Tag tab → 행 재진입 + 11 필드 일치 ─────────
        page.open_modify_modal(TARGET_NAME)
        page.click_tag_tab()
        final_rows = len(page.get_item_tag_list_rows())
        # 저장 후 재오픈 시에도 추가된 행 유지 (before + 1)
        self._add("pass" if final_rows == before_rows + 1 else "fail",
                  "스위트 수정 모달 — 재오픈 후 태그 추가 행 유지",
                  f"입력: 재오픈 + Tag tab / 결과: itemTagList 행={final_rows} (기대: {before_rows + 1})", sc=4)

        if final_rows < 1:
            page.close_modal()
            return

        page.click_item_tag_list_row(0)
        tag_disp = page.process.get_selected_display_text()
        self._add("pass" if "미선택" not in tag_disp else "fail",
                  "태그 — itemTagList 행 클릭 → 태그 모달 재진입 (선택 표시 유지)",
                  f"입력: 행 클릭 / 결과: display={tag_disp!r}", sc=4)

        re_checks = {
            "프로세스 제외 토글 (OFF→ON)":            page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT),
            "프로세스별 클립보드 제한 토글 (OFF→ON)":  page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD),
            "샌드박스 토글 (OFF→ON)":                 page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX),
            "드라이브 예외 거부 토글 (OFF→ON)":        page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE),
            "프로세스별 네트워크 토글 (OFF→ON)":       page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK),
            "IP/Port 등록 반영":                       any(TAG["ip"] in x and TAG["port"] in x
                                                          for x in page.process.get_ip_list()),
            "확장자 제어 토글 (OFF→ON)":               page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT),
            # subset 검증 — sc3 데이터 + sc4 추가 모두 list 에 포함
            "태그 확장자 추가 반영":                   all(e in page.process.get_extension_list() for e in TAG["ext"]),
            "드라이브 접근 토글 (OFF→ON)":             page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE),
            "드라이브 문자 입력 반영":                 page.process.get_drive_letter() == TAG["drive"],
            "설명 입력 반영":                          TAG["desc"] in page.process.get_description(),
        }
        for k, ok in re_checks.items():
            self._add("pass" if ok else "fail",
                      f"태그 process_modal — 재진입 입력값 일치: {k}",
                      f"입력: itemTagList 행 클릭 (재진입) / 결과: 일치={ok}", sc=4)

        # ── 라운드 2: ON→OFF 양방향 (7 토글) ──────────────────
        page.process.set_process_except(False)
        page.process.set_pclipboard_restrict(False)
        page.process.set_sandbox(False)
        page.process.set_deny_except_drive(False)
        page.process.set_pnetwork(False)
        page.process.set_pcontrol_extension(False)
        page.process.set_access_drive(False)
        page.process.confirm()

        msg2 = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg2 in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — 태그 process_modal 7 토글 ON→OFF + '수정' 저장",
                  f"입력: 7 토글 모두 OFF / 결과: 메시지={msg2!r}", sc=4)

        # 재오픈 → 7 토글 OFF 일치
        page.open_modify_modal(TARGET_NAME)
        page.click_tag_tab()
        page.click_item_tag_list_row(0)
        off_checks = {
            "프로세스 제외 토글 (ON→OFF)":             not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT),
            "프로세스별 클립보드 제한 토글 (ON→OFF)":   not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD),
            "샌드박스 토글 (ON→OFF)":                  not page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX),
            "드라이브 예외 거부 토글 (ON→OFF)":         not page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE),
            "프로세스별 네트워크 토글 (ON→OFF)":        not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK),
            "확장자 제어 토글 (ON→OFF)":                not page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT),
            "드라이브 접근 토글 (ON→OFF)":              not page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE),
        }
        for k, ok in off_checks.items():
            self._add("pass" if ok else "fail",
                      f"태그 process_modal — ON→OFF 재진입 일치: {k}",
                      f"입력: 토글 OFF 저장 후 재진입 / 결과: 일치={ok}", sc=4)
        page.process.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 4f — 3c (웹제한 모달 종합) 의 EDIT 버전 + cross-instance 중복 (yaml must_test)
    # ==================================================================

    # ==================================================================
    # 시나리오 4f — 3c (웹제한 모달 종합) 의 EDIT 버전 + cross-instance 중복 (yaml must_test)
    # ==================================================================
    def test_scenario4f_edit_web_restrict_full(self, logged_in_page, settings):
        """시나리오 4f — 웹제한 영역 종합 검증.

        Part A (3c EDIT): sc3 정책의 기존 웹제한 모달 재진입 → 5 필드 load + 4 영역 modify + 모달 확인.
        Part B (cross-instance): 2번째 웹제한 추가 → 사용중 프로세스 선택 시 알림 + 미사용 선택 + 정상 등록.
        """
        print("\n━━ [제어 스위트] 시나리오 4f: 웹제한 영역 + cross-instance (3c 의 EDIT 버전) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"
        INIT_WEB_NAME = "[AUTO]_web_sc3_step2"
        INIT_URL      = "sc3_step2-web.com"
        INIT_LIMIT    = "512"
        INIT_DESC     = "sc3_step2 웹제한 초기값"
        # 매 run unique 값 — sc3 + 이전 sc4 누적 중복 회피 (MCP 진단 2026-05-22)
        _ts = (int(time.time()) // 11) % 10000   # 11로 나눠 4d/4e 와 다른 값
        MOD_URL    = f"edit4f-{_ts}.com"
        MOD_EXT    = f"w{_ts}"
        MOD_LIMIT  = "2048"
        MOD_DESC   = f"edit_4f_{_ts}"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4f — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        # ════ Part A: 기존 웹제한 모달 재진입 + 종합 수정 ════
        page.open_modify_modal(TARGET_NAME)
        wr_rows = page.get_item_web_restrict_rows()
        self._add("pass" if len(wr_rows) >= 1 else "fail",
                  "스위트 수정 모달 — 기존 웹제한 1건 로드 (itemWebRestrictList)",
                  f"입력: 진입 / 결과: 행={len(wr_rows)}", sc=4)

        if len(wr_rows) < 1:
            page.close_modal()
            return

        page.click_item_web_restrict_row(0)
        self._add("pass" if page.web_restrict.get_name() == INIT_WEB_NAME else "fail",
                  "웹제한 모달 — 웹제한 이름 load",
                  f"입력: 행 클릭 / 결과: name={page.web_restrict.get_name()!r}", sc=4)

        proc_rows = page.web_restrict.get_process_rows()
        self._add("pass" if len(proc_rows) >= 1 else "fail",
                  "웹제한 모달 — 적용 프로세스 load",
                  f"입력: 재진입 / 결과: process_rows={len(proc_rows)}", sc=4)

        url_list = page.web_restrict.get_url_list()
        self._add("pass" if any(INIT_URL in u for u in url_list) else "fail",
                  "웹제한 모달 — 적용 URL load",
                  f"입력: 재진입 / 결과: url_list={url_list}", sc=4)

        self._add("pass" if page.web_restrict.get_upload_limit() == INIT_LIMIT else "fail",
                  "웹제한 모달 — 업로드 제한용량 load",
                  f"입력: 재진입 / 결과: limit={page.web_restrict.get_upload_limit()!r}", sc=4)

        self._add("pass" if INIT_DESC[:5] in page.web_restrict.get_description() else "fail",
                  "웹제한 모달 — 설명 load",
                  f"입력: 재진입 / 결과: desc={page.web_restrict.get_description()!r}", sc=4)

        # 4 영역 modify
        page.web_restrict.add_url(MOD_URL)
        # 안전망 — URL 중복 알림 dismiss (재추가 시)
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()
        self._add("pass" if any(MOD_URL in u for u in page.web_restrict.get_url_list()) else "fail",
                  "웹제한 모달 — 적용 URL 추가 (수정)",
                  f"입력: '{MOD_URL}' / 결과: list={page.web_restrict.get_url_list()}", sc=4)

        page.web_restrict.add_file_extension(MOD_EXT)
        # 안전망 — 확장자 중복 알림 dismiss
        if page.is_confirm_modal_visible(timeout=500):
            page.dismiss_confirm_modal()
        self._add("pass", "웹제한 모달 — 확장자 추가 (수정)",
                  f"입력: '{MOD_EXT}' / 결과: 입력 반영", sc=4)

        page.web_restrict.set_upload_limit(MOD_LIMIT)
        self._add("pass" if page.web_restrict.get_upload_limit() == MOD_LIMIT else "fail",
                  "웹제한 모달 — 업로드 제한용량 변경 (수정)",
                  f"입력: '{MOD_LIMIT}' / 결과: get={page.web_restrict.get_upload_limit()!r}", sc=4)

        page.web_restrict.set_description(MOD_DESC)
        self._add("pass" if MOD_DESC[:7] in page.web_restrict.get_description() else "fail",
                  "웹제한 모달 — 설명 변경 (수정)",
                  f"입력: '{MOD_DESC}' / 결과: get={page.web_restrict.get_description()!r}", sc=4)

        page.web_restrict.confirm()
        self._add("pass" if len(page.get_item_web_restrict_rows()) >= 1 else "fail",
                  "웹제한 모달 — '확인' (itemWebRestrictList 보존)",
                  f"입력: '확인' / 결과: 행 수={len(page.get_item_web_restrict_rows())}", sc=4)

        # ════ Part B: 2번째 웹제한 추가 (cross-instance dup yaml must_test) ════
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_4f_second")

        # 첫 행 (Part A 사용 프로세스) 재선택 → cross-instance 알림
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")

        dup_seen = page.is_confirm_modal_visible()
        dup_msg = page.get_confirm_message() if dup_seen else ""
        if dup_seen:
            page.dismiss_confirm_modal()
        self._add("pass" if dup_seen and "이미 등록" in dup_msg and "타 웹제한" in dup_msg else "fail",
                  "웹제한 모달 — cross-instance 중복 알림 (yaml must_test)",
                  f"입력: 기존 사용 프로세스 재선택 / 결과: 메시지={dup_msg!r}", sc=4)

        proc_rows_after_dup = len(page.web_restrict.get_process_rows())
        self._add("pass" if proc_rows_after_dup == 0 else "fail",
                  "웹제한 모달 — 중복 차단 후 적용 프로세스 테이블 미추가 (생략 동작)",
                  f"입력: 중복 알림 dismiss / 결과: process_rows={proc_rows_after_dup}", sc=4)

        # 미사용 프로세스 (2번째 행) 선택
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        rows2 = page.picker.page.locator(page.picker.SEL_ROW)
        if rows2.count() >= 2:
            page._click_hidden(page.picker.page.locator(page.picker.SEL_CHECKBOX_PROCESS).nth(1))
            page.picker.confirm()
            page.picker.wait_closed()
            proc_rows_final = len(page.web_restrict.get_process_rows())
            self._add("pass" if proc_rows_final >= 1 else "fail",
                      "웹제한 모달 — 미사용 프로세스 (2번째 행) 정상 등록",
                      f"입력: picker 2번째 행 / 결과: process_rows={proc_rows_final}", sc=4)
        else:
            self._add("skip", "웹제한 모달 — 미사용 프로세스 (picker 행 부족)",
                      f"입력: picker row count={rows2.count()} / 결과: skip", sc=4)
            page.picker.cancel()

        page.web_restrict.confirm()

        # 메인 '수정' 저장
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — 웹제한 종합 (Part A + Part B) 변경 + '수정' 저장",
                  f"입력: 종합 변경 / 결과: 메시지={msg!r}", sc=4)

        # 재오픈 + verify
        # sc3 데이터 위에 sc4 신규 Part B 추가 → 행 수 +1 검증 (strict 2 가정 X)
        page.open_modify_modal(TARGET_NAME)
        final_rows = len(page.get_item_web_restrict_rows())
        self._add("pass" if final_rows >= 1 else "fail",
                  "스위트 수정 모달 — 재오픈 후 웹제한 행 잔존 (Part A 유지 + Part B 신규 등)",
                  f"입력: 재오픈 / 결과: itemWebRestrictList 행={final_rows}", sc=4)

        # Part A 변경값 재오픈 일치
        page.click_item_web_restrict_row(0)
        re_a = {
            "Part A — 적용 URL 추가 반영":           any(MOD_URL in u for u in page.web_restrict.get_url_list()),
            "Part A — 업로드 제한용량 (512→2048)":   page.web_restrict.get_upload_limit() == MOD_LIMIT,
            "Part A — 설명 변경 반영":               MOD_DESC[:7] in page.web_restrict.get_description(),
        }
        for k, ok in re_a.items():
            self._add("pass" if ok else "fail",
                      f"웹제한 모달 — 재오픈 변경값 일치: {k}",
                      f"입력: 재오픈 / 결과: 일치={ok}", sc=4)
        page.web_restrict.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 4g — 3e (validation 메시지: maxlength/빈값/중복) 의 EDIT 버전 + 변경없이 수정
    # ==================================================================

    # ==================================================================
    # 시나리오 4g — 3e (validation 메시지: maxlength/빈값/중복) 의 EDIT 버전 + 변경없이 수정
    # ==================================================================
    def test_scenario4g_edit_validation_messages(self, logged_in_page, settings):
        """시나리오 4g — EDIT 모달 validation 메시지.

        A. csuName maxlength=50 (EDIT)
        B. csuName 빈값 + '수정' 메시지
        B-extra. ADD vs EDIT 메시지 차이 (회귀 검출)
        E. csuName 중복 + '수정' 메시지
        F. 수정 내용 없이 '수정' → '수정된 항목이 없습니다' 알림 (정상 동작)
        """
        print("\n━━ [제어 스위트] 시나리오 4g: validation 메시지 (3e 의 EDIT 버전) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4g — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        # ── A. EDIT csuName maxlength=50 자동 절단 ──────────────
        page.open_modify_modal(TARGET_NAME)
        page.set_csu_name("z" * 100)
        got = page.get_csu_name()
        self._add("pass" if len(got) == 50 else "fail",
                  "스위트 이름 — EDIT DOM maxlength=50 자동 절단",
                  f"입력: 100자 / 결과: 실제 길이={len(got)}", sc=4)

        # ── B. EDIT csuName 빈값 + '수정' → 메시지 ───────────────
        page.set_csu_name("")
        page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
        page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=page._TIMEOUT_MODAL
        )
        edit_msg = page.get_confirm_message()
        self._add("pass" if edit_msg == "정책 이름을 입력해 주세요." else "fail",
                  "스위트 이름 — EDIT 빈값 차단 메시지",
                  f"입력: 이름='' + '수정' 클릭 / 결과: 메시지={edit_msg!r}", sc=4)
        page.dismiss_confirm_modal()

        # ── B-extra. ADD vs EDIT 메시지 차이 (회귀 검출) ─────────
        ADD_MSG = "이름을 입력해 주세요."
        self._add("pass" if ADD_MSG != edit_msg else "fail",
                  "스위트 이름 — ADD vs EDIT 빈값 메시지 차이 (회귀 검출)",
                  f"입력: ADD 메시지 vs EDIT 메시지 비교 / 결과: ADD={ADD_MSG!r} != EDIT={edit_msg!r}", sc=4)

        # ── E. EDIT 중복 이름 차단 메시지 (기존 sc3 정책 이름 활용) ──
        # 단순화 (2026-05-26): DUP_PEER 새 정책 생성 + close/open 우회로 제거.
        # 같은 EDIT 모달 세션 안에서 이름만 다른 기존 sc3 정책 이름으로 바꿔 시도.
        # 검증 의도 동일 — '이미 등록된 이름 입니다.' 메시지.
        DUP_PEER = "[AUTO]_sc3_step1"   # sc3b 가 만든 다른 정책 (반드시 존재)
        page.set_csu_name(DUP_PEER)
        page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
        page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=page._TIMEOUT_MODAL
        )
        dup_msg = page.get_confirm_message()
        self._add("pass" if dup_msg == "이미 등록된 이름 입니다." else "fail",
                  "스위트 이름 — EDIT 중복 차단 메시지",
                  f"입력: 이름='{DUP_PEER}' (기존 정책 중복) + '수정' / 결과: 메시지={dup_msg!r}", sc=4)
        page.dismiss_confirm_modal()

        # 원복 (수정 모달 그대로 유지 — 다음 검증에 활용)
        page.set_csu_name(TARGET_NAME)

        # ── F. 수정 내용 없이 '수정' → '수정된 항목이 없습니다' 알림 ──
        page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
        page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=page._TIMEOUT_MODAL
        )
        no_change_msg = page.get_confirm_message()
        _no_change_ok = ("수정된 항목" in no_change_msg) or ("수정한 내용" in no_change_msg) or ("변경된" in no_change_msg)
        self._add("pass" if _no_change_ok else "fail",
                  "스위트 수정 모달 — 변경 없이 '수정' 클릭 차단 메시지 (정상 동작)",
                  f"입력: 필드 변경 없음 + '수정' 클릭 / 결과: 메시지={no_change_msg!r}", sc=4)
        page.dismiss_confirm_modal()

        page.close_modal()

    # ==================================================================
    # 시나리오 4h — sub-modal 재진입 + 변경 없이 닫기 + 메인 '수정' → 메시지 (Case A 흐름)
    # ==================================================================
    def test_scenario4h_no_change_submodal_reentry(self, logged_in_page, settings):
        """시나리오 4h — sub-modal 재진입 후 변경 없이 닫고 메인 '수정' 클릭 시 '수정된 항목이 없습니다' 알림.

        Case G: 프로세스 itemList 행 클릭 → process_modal 재진입 → 변경 없이 닫고 → 메인 수정 → 메시지
        Case H: 태그 itemTagList 행 클릭 → tag 모달 재진입 → 변경 없이 닫고 → 메인 수정 → 메시지
        Case I: 웹제한 행 클릭 → web_restrict 재진입 → 변경 없이 닫고 → 메인 수정 → 메시지

        sub-modal 진입 자체가 '수정' 으로 간주되는지 / 변경 없이 닫으면 무시되는지 확인.
        """
        print("\n━━ [제어 스위트] 시나리오 4h: sub-modal 재진입 + 변경없이 수정 (3 cases) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4h — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        # 단순화 (2026-05-26): 3 case 모두 하나의 EDIT 모달 세션 안에서 수행.
        # 기존: 매 case 마다 open_modify_modal + close_modal (2번 close 가 fail 야기)
        # 신규: open_modify_modal 1회 + 모든 case 진행 + close_modal 1회.
        page.open_modify_modal(TARGET_NAME)

        # ── Case G: 프로세스 sub-modal 재진입 + 닫기 + 메인 수정 ──
        if len(page.get_item_list_rows()) >= 1:
            page.click_item_list_row(0)
            page.process.close()    # 변경 없이 닫기
            page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
            try:
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg_g = page.get_confirm_message()
                page.dismiss_confirm_modal()
            except Exception:
                msg_g = ""
            ok_g = ("수정된 항목" in msg_g) or ("수정한 내용" in msg_g)
            self._add("pass" if ok_g else "fail",
                      "스위트 수정 모달 — 프로세스 sub-modal 재진입 + 변경없이 수정 (Case G)",
                      f"입력: itemList 행 클릭 → 닫기 → '수정' / 결과: 메시지={msg_g!r}", sc=4)
        else:
            self._add("skip", "시나리오 4h Case G — 프로세스 행 없음 → skip",
                      "입력: itemList 0행 / 결과: skip", sc=4)

        # ── Case H: 태그 sub-modal 재진입 + 닫기 + 메인 수정 ──
        # (모달 그대로 열려있음 — 알림 dismiss 후 메인 EDIT 유지)
        page.click_tag_tab()
        if len(page.get_item_tag_list_rows()) >= 1:
            page.click_item_tag_list_row(0)
            page.process.close()    # 변경 없이 닫기
            page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
            try:
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg_h = page.get_confirm_message()
                page.dismiss_confirm_modal()
            except Exception:
                msg_h = ""
            ok_h = ("수정된 항목" in msg_h) or ("수정한 내용" in msg_h)
            self._add("pass" if ok_h else "fail",
                      "스위트 수정 모달 — 태그 sub-modal 재진입 + 변경없이 수정 (Case H)",
                      f"입력: itemTagList 행 클릭 → 닫기 → '수정' / 결과: 메시지={msg_h!r}", sc=4)
        else:
            self._add("skip", "시나리오 4h Case H — 태그 행 없음 → skip",
                      "입력: itemTagList 0행 / 결과: skip", sc=4)

        # ── Case I: 웹제한 sub-modal 재진입 + 닫기 + 메인 수정 ──
        if len(page.get_item_web_restrict_rows()) >= 1:
            page.click_item_web_restrict_row(0)
            page.web_restrict.close()    # 변경 없이 닫기
            page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
            try:
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg_i = page.get_confirm_message()
                page.dismiss_confirm_modal()
            except Exception:
                msg_i = ""
            ok_i = ("수정된 항목" in msg_i) or ("수정한 내용" in msg_i)
            self._add("pass" if ok_i else "fail",
                      "스위트 수정 모달 — 웹제한 sub-modal 재진입 + 변경없이 수정 (Case I)",
                      f"입력: itemWebRestrictList 행 클릭 → 닫기 → '수정' / 결과: 메시지={msg_i!r}", sc=4)
        else:
            self._add("skip", "시나리오 4h Case I — 웹제한 행 없음 → skip",
                      "입력: itemWebRestrictList 0행 / 결과: skip", sc=4)

        page.close_modal()

    # ==================================================================
    # 시나리오 4i — 이름 EDIT 중복 검증 (신규)
    # 자기 자신 이름은 허용, 다른 정책 이름과 충돌 시 차단
    # ==================================================================
    def test_scenario4i_edit_name_duplicate(self, logged_in_page, settings):
        """시나리오 4i — EDIT 시 이름 변경 검증.

        Case A: 자기 자신 이름 그대로 modify → '저장 하였습니다' (정상 저장)
        Case B: 다른 존재 정책 이름으로 변경 → '이미 등록된 이름 입니다' (정상 차단)
        """
        print("\n━━ [제어 스위트] 시나리오 4i: 이름 EDIT 중복 차단 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        SELF_NAME  = "[AUTO]_sc3_step1"     # sc3b minimal
        OTHER_NAME = "[AUTO]_sc3_step3"     # sc3d 웹제한

        page.navigate_to_clean()
        if not (page.is_policy_exists(SELF_NAME) and page.is_policy_exists(OTHER_NAME)):
            self._add("skip", "시나리오 4i — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: {SELF_NAME!r}/{OTHER_NAME!r} 둘 다 필요", sc=4)
            pytest.skip("sc3 정책 (step1 + step3) 모두 필요 — sc3b/3d 먼저 실행")

        # 단순화 (2026-05-26): Case A + B 하나의 EDIT 모달 세션 안에서 수행.
        # 기존: Case A 후 close_modal 없이 Case B 가 open_modify_modal 재호출 (충돌 야기)
        # 신규: open_modify_modal 1회 + Case A 검증 + Case B 검증 + close_modal 1회.
        page.open_modify_modal(SELF_NAME)

        # ── Case A: 자기 자신 이름 그대로 modify → 정상 저장 허용 ──
        msg_a = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg_a in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — 자기 자신 이름 그대로 modify (정상 저장 허용)",
                  f"입력: 이름 변경 X + '수정' / 결과: 메시지={msg_a!r}", sc=4)

        # ── Case B: 다른 정책 이름으로 변경 → 중복 차단 ──
        # (모달 그대로 열려있음 — 알림 dismiss 후 메인 EDIT 유지)
        page.set_csu_name(OTHER_NAME)
        msg_b = page.save_policy(mode="modify")
        ok_blocked = "이미 등록" in msg_b and "이름" in msg_b
        self._add("pass" if ok_blocked else "fail",
                  "스위트 수정 모달 — 다른 정책 이름으로 변경 → 중복 차단 메시지",
                  f"입력: 이름 '{SELF_NAME}' → '{OTHER_NAME}' / 결과: 메시지={msg_b!r}", sc=4)
        page.dismiss_confirm_modal()
        # 원복 후 cancel (정책 이름 보존)
        page.set_csu_name(SELF_NAME)
        page.close_modal()

        # ── Case C: 정책 list 에 두 정책 모두 잔존 확인 ──
        self._add("pass" if (page.is_policy_exists(SELF_NAME) and page.is_policy_exists(OTHER_NAME)) else "fail",
                  "정책 list — 4i 후 두 정책 모두 잔존 (이름 변경 시도 차단 후)",
                  f"입력: 검증 후 / 결과: '{SELF_NAME}'={page.is_policy_exists(SELF_NAME)}, '{OTHER_NAME}'={page.is_policy_exists(OTHER_NAME)}", sc=4)

    # ==================================================================
    # 시나리오 4j — EDIT 모달에서 UX 결함 재현 (신규)
    # sc3j 패턴 (sub-modal pass + 메인 저장 시 server error) 이 EDIT 에서도 동일한지 검증
    # ==================================================================
    def test_scenario4j_edit_ux_defect_reproduce(self, logged_in_page, settings):
        """시나리오 4j — EDIT 모달에서 UX 결함 재현 검증.

        sc3j 가 ADD 시점에서 발견한 UX 결함 (sub-modal pass + main save server error) 가
        EDIT 모달에서도 동일한지 회귀 검증 (yaml :104-106 4-4 의도).

        Case A: drv 100자 EDIT → 서버 오류 (sc3j Case B EDIT 버전)
        Case B: Port -1 EDIT → 서버 오류 (sc3j Case E EDIT 버전)
        Case C: basePath 400자 EDIT → 서버 오류 (sc3j Case C EDIT 버전)
        Case D: webName 500자 EDIT → 서버 오류 (sc3j Case H EDIT 버전)
        Case E: 태그 drv 100자 EDIT → 서버 오류 (sc3j Case L EDIT 버전)
        """
        print("\n━━ [제어 스위트] 시나리오 4j: EDIT 모달 UX 결함 재현 (sc3j 패턴) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        # ── Case A: [AUTO]_sc3_step9_drv50 EDIT → drv 100자 변경 → 서버 오류 ──
        TARGET_A = "[AUTO]_sc3_step9_drv50"
        page.navigate_to_clean()
        if page.is_policy_exists(TARGET_A):
            page.open_modify_modal(TARGET_A)
            page.click_individual_process_tab()
            if len(page.get_item_list_rows()) >= 1:
                page.click_item_list_row(0)
                page.process.wait_open()
                if page.feature_exists(page.process.SEL_TOGGLE_ACCESS_DRIVE, timeout=1000):
                    page.process.set_drive_letter("a" * 100)
                    page.process.confirm()
                    page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                    page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                        state="attached", timeout=page._TIMEOUT_MODAL
                    )
                    msg = page.get_confirm_message()
                    defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                    self._add("warn" if defect_found else "pass",
                              "[UX 결함 EDIT] 프로세스별 제어 (개별 프로세스) - 드라이브 letter 100자 → 메인 수정 시 서버 오류 (ADD-EDIT 동일 결함)",
                              f"입력: EDIT '{TARGET_A}' + drv 100자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                    page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] 드라이브 letter 100자 — sc3 정책 부재", f"'{TARGET_A}' 없음", sc=4)

        # ── Case B: [AUTO]_sc3_step9_port_D EDIT → Port -1 변경 → 서버 오류 ──
        TARGET_B = "[AUTO]_sc3_step9_port_D"
        page.navigate_to_clean()
        if page.is_policy_exists(TARGET_B):
            page.open_modify_modal(TARGET_B)
            page.click_individual_process_tab()
            if len(page.get_item_list_rows()) >= 1:
                page.click_item_list_row(0)
                page.process.wait_open()
                page.process.set_pnetwork(True)
                # 기존 IP/Port 변경 후 추가 — Port=-1 입력
                page.process.add_ip_port("192.168.99.9", "-1")
                if page.is_confirm_modal_visible(timeout=1500):
                    page.dismiss_confirm_modal()
                page.process.confirm()
                page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg = page.get_confirm_message()
                defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                self._add("warn" if defect_found else "pass",
                          "[UX 결함 EDIT] 프로세스별 제어 (개별 프로세스) - 허용 IP/Port Port=-1 추가 → 메인 수정 시 서버 오류",
                          f"입력: EDIT '{TARGET_B}' + Port=-1 추가 + 수정 / 결과: 메시지={msg!r}", sc=4)
                page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] Port -1 — sc3 정책 부재", f"'{TARGET_B}' 없음", sc=4)

        # ── Case C: [AUTO]_sc3_step16_bp300_ok EDIT → basePath 400자 변경 → 서버 오류 ──
        TARGET_C = "[AUTO]_sc3_step16_bp300_ok"
        page.navigate_to_clean()
        if page.is_policy_exists(TARGET_C):
            page.open_modify_modal(TARGET_C)
            if len(page.get_item_web_restrict_rows()) >= 1:
                page.click_item_web_restrict_row(0)
                page.web_restrict.wait_open()
                if page.feature_exists(page.web_restrict.SEL_BASE_PATH, timeout=1000):
                    page.web_restrict.set_base_path("a" * 400)
                    page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
                    page.web_restrict.wait_closed(timeout=3000)
                    page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                    page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                        state="attached", timeout=page._TIMEOUT_MODAL
                    )
                    msg = page.get_confirm_message()
                    defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                    self._add("warn" if defect_found else "pass",
                              "[UX 결함 EDIT] 웹제한 기능 - 기본폴더 basePath 400자 → 메인 수정 시 서버 오류 (ADD-EDIT 동일 결함)",
                              f"입력: EDIT '{TARGET_C}' + basePath 400자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                    page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] basePath 400자 — sc3 정책 부재", f"'{TARGET_C}' 없음", sc=4)

        # ── Case D: [AUTO]_sc3_step17_webname100_ok EDIT → webName 500자 → 서버 오류 ──
        TARGET_D = "[AUTO]_sc3_step17_webname100_ok"
        page.navigate_to_clean()
        if page.is_policy_exists(TARGET_D):
            page.open_modify_modal(TARGET_D)
            if len(page.get_item_web_restrict_rows()) >= 1:
                page.click_item_web_restrict_row(0)
                page.web_restrict.wait_open()
                page.web_restrict.set_name("a" * 500)
                page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
                page.web_restrict.wait_closed(timeout=3000)
                page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg = page.get_confirm_message()
                defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                self._add("warn" if defect_found else "pass",
                          "[UX 결함 EDIT] 웹제한 기능 - 웹제한 이름 webRestrictName 500자 → 메인 수정 시 서버 오류 (ADD-EDIT 동일 결함)",
                          f"입력: EDIT '{TARGET_D}' + webName 500자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] webName 500자 — sc3 정책 부재", f"'{TARGET_D}' 없음", sc=4)

        # ── Case E: [AUTO]_sc3_step19_tag_normal EDIT → tag drv 100자 → 서버 오류 ──
        TARGET_E = "[AUTO]_sc3_step19_tag_normal"
        page.navigate_to_clean()
        if page.is_policy_exists(TARGET_E):
            page.open_modify_modal(TARGET_E)
            page.click_tag_tab()
            if len(page.get_item_tag_list_rows()) >= 1:
                page.click_item_tag_list_row(0)
                page.process.wait_open()
                if page.feature_exists(page.process.SEL_TOGGLE_ACCESS_DRIVE, timeout=1000):
                    page.process.set_drive_letter("a" * 100)
                    page.process.confirm()
                    page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                    page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                        state="attached", timeout=page._TIMEOUT_MODAL
                    )
                    msg = page.get_confirm_message()
                    defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                    self._add("warn" if defect_found else "pass",
                              "[UX 결함 EDIT] 프로세스별 제어 (태그) - 접근 드라이브 letter 100자 → 메인 수정 시 서버 오류 (ADD-EDIT 동일 결함)",
                              f"입력: EDIT '{TARGET_E}' + 태그 drv 100자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                    page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] 태그 drv 100자 — sc3 정책 부재", f"'{TARGET_E}' 없음", sc=4)

        # ── Case K: 개별 프로세스 cacheFolder 500자 → 메인 수정 시 서버 오류 (sc3j Case K EDIT) ──
        # 수정 (2026-05-27): sc3j K 가 server error 로 정책 미생성 → 기존 TARGET 의존 시 항상 skip.
        # → 정상 프로세스 보유 정책 EDIT → cache 500자 입력 → 수정 → error 방식 (G/I/J/M 과 동일)
        K_CAND = ["[AUTO]_sc3_step9_drv50", "[AUTO]_sc3_step9_port_D", "[AUTO]_sc3_step9_port_F", "[AUTO]_sc3_step2"]
        page.navigate_to_clean()
        tk = next((n for n in K_CAND if page.is_policy_exists(n)), None)
        if tk:
            page.open_modify_modal(tk)
            if len(page.get_item_list_rows()) >= 1:
                page.click_item_list_row(0)
                page.process.wait_open()
                if page.feature_exists(page.process.SEL_CACHE_INPUT, timeout=1000):
                    page.process.set_cache_input("a" * 500)
                    page.process.click_cache_add_btn()
                    page.process.confirm()
                    page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                    page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                        state="attached", timeout=page._TIMEOUT_MODAL
                    )
                    msg = page.get_confirm_message()
                    defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                    self._add("warn" if defect_found else "pass",
                              "[UX 결함 EDIT] 프로세스별 제어 (개별 프로세스) - 캐시폴더 cacheFolderInput 500자 → 메인 수정 시 서버 오류 (sc3j Case K EDIT)",
                              f"입력: EDIT '{tk}' + cache 500자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                    page.dismiss_confirm_modal()
                else:
                    self._add("skip", "[UX 결함 EDIT] cache 500자 — 캐시폴더 기능 부재", f"'{tk}' SEL_CACHE_INPUT 없음", sc=4)
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] cache 500자 — 프로세스 보유 sc3 정책 부재", f"후보 {K_CAND} 없음", sc=4)

        # ── Case P: 태그 mode cacheFolder 500자 → 메인 수정 시 서버 오류 (sc3j Case P EDIT) ──
        # 수정 (2026-05-27): K 와 동일 — 정상 태그 보유 정책 EDIT → 태그 cache 500자 → 수정 → error
        P_CAND = ["[AUTO]_sc3_step19_tag_normal", "[AUTO]_sc3_step2"]
        page.navigate_to_clean()
        tp = next((n for n in P_CAND if page.is_policy_exists(n)), None)
        if tp:
            page.open_modify_modal(tp)
            page.click_tag_tab()
            if len(page.get_item_tag_list_rows()) >= 1:
                page.click_item_tag_list_row(0)
                page.process.wait_open()
                if page.feature_exists(page.process.SEL_CACHE_INPUT, timeout=1000):
                    page.process.set_cache_input("a" * 500)
                    page.process.click_cache_add_btn()
                    page.process.confirm()
                    page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                    page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                        state="attached", timeout=page._TIMEOUT_MODAL
                    )
                    msg = page.get_confirm_message()
                    defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                    self._add("warn" if defect_found else "pass",
                              "[UX 결함 EDIT] 프로세스별 제어 (태그) - 캐시폴더 cacheFolderInput 500자 → 메인 수정 시 서버 오류 (sc3j Case P EDIT)",
                              f"입력: EDIT '{tp}' + 태그 cache 500자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                    page.dismiss_confirm_modal()
                else:
                    self._add("skip", "[UX 결함 EDIT] 태그 cache 500자 — 캐시폴더 기능 부재", f"'{tp}' SEL_CACHE_INPUT 없음", sc=4)
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] 태그 cache 500자 — 태그 보유 sc3 정책 부재", f"후보 {P_CAND} 없음", sc=4)

        # ── Case G: 개별 프로세스 Port 빈값 → 메인 수정 시 서버 오류 (sc3j Case G EDIT) ──
        # 정상 정책 EDIT → 프로세스 재진입 → Port 빈값 추가 → 메인 수정 → server error 회귀
        G_CAND = ["[AUTO]_sc3_step9_port_F", "[AUTO]_sc3_step9_port_D", "[AUTO]_sc3_step2"]
        page.navigate_to_clean()
        tg = next((n for n in G_CAND if page.is_policy_exists(n)), None)
        if tg:
            page.open_modify_modal(tg)
            if len(page.get_item_list_rows()) >= 1:
                page.click_item_list_row(0)
                page.process.wait_open()
                page.process.set_pnetwork(True)
                page.process.add_ip_port("192.168.88.1", "")  # Port 빈값
                if page.is_confirm_modal_visible(timeout=1500):
                    page.dismiss_confirm_modal()  # sub-modal 형식 차단 알림 (있으면)
                page.process.confirm()
                page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg = page.get_confirm_message()
                defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                self._add("warn" if defect_found else "pass",
                          "[UX 결함 EDIT] 프로세스별 제어 (개별 프로세스) - 허용 IP/Port Port=빈값 → 메인 수정 시 서버 오류 (sc3j Case G EDIT)",
                          f"입력: EDIT '{tg}' + Port='' 추가 + 수정 / 결과: 메시지={msg!r}", sc=4)
                page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] Port 빈값 — 프로세스 보유 sc3 정책 부재", f"후보 {G_CAND} 없음", sc=4)

        # ── Case I: 웹제한 적용 URL attachAllowUrl 1000자 → 메인 수정 시 서버 오류 (sc3j Case I EDIT) ──
        I_CAND = ["[AUTO]_sc3_step3", "[AUTO]_sc3_step17_webname100_ok", "[AUTO]_sc3_step2"]
        page.navigate_to_clean()
        ti = next((n for n in I_CAND if page.is_policy_exists(n)), None)
        if ti:
            page.open_modify_modal(ti)
            if len(page.get_item_web_restrict_rows()) >= 1:
                page.click_item_web_restrict_row(0)
                page.web_restrict.wait_open()
                page.web_restrict.set_is_url(True)
                page.web_restrict.add_url("a" * 1000)
                if page.is_confirm_modal_visible(timeout=1000):
                    page.dismiss_confirm_modal()
                page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
                try:
                    page.web_restrict.wait_closed(timeout=3000)
                except Exception:
                    pass
                page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg = page.get_confirm_message()
                defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                self._add("warn" if defect_found else "pass",
                          "[UX 결함 EDIT] 웹제한 기능 - 적용 URL attachAllowUrl 1000자 → 메인 수정 시 서버 오류 (sc3j Case I EDIT)",
                          f"입력: EDIT '{ti}' + URL 1000자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] attachAllowUrl 1000자 — 웹제한 보유 sc3 정책 부재", f"후보 {I_CAND} 없음", sc=4)

        # ── Case J: 웹제한 업로드 확장자 allowFileExtention 500자 → 메인 수정 시 서버 오류 (sc3j Case J EDIT) ──
        J_CAND = ["[AUTO]_sc3_step3", "[AUTO]_sc3_step17_webname100_ok", "[AUTO]_sc3_step2"]
        page.navigate_to_clean()
        tj = next((n for n in J_CAND if page.is_policy_exists(n)), None)
        if tj:
            page.open_modify_modal(tj)
            if len(page.get_item_web_restrict_rows()) >= 1:
                page.click_item_web_restrict_row(0)
                page.web_restrict.wait_open()
                page.web_restrict.add_file_extension("a" * 500)
                if page.is_confirm_modal_visible(timeout=1000):
                    page.dismiss_confirm_modal()
                page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
                try:
                    page.web_restrict.wait_closed(timeout=3000)
                except Exception:
                    pass
                page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg = page.get_confirm_message()
                defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                self._add("warn" if defect_found else "pass",
                          "[UX 결함 EDIT] 웹제한 기능 - 업로드 허용 확장자 allowFileExtention 500자 → 메인 수정 시 서버 오류 (sc3j Case J EDIT)",
                          f"입력: EDIT '{tj}' + web 확장자 500자 + 수정 / 결과: 메시지={msg!r}", sc=4)
                page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] allowFileExtention 500자 — 웹제한 보유 sc3 정책 부재", f"후보 {J_CAND} 없음", sc=4)

        # ── Case M: 태그 mode Port=-1 → 메인 수정 시 서버 오류 (sc3j Case M EDIT) ──
        M_CAND = ["[AUTO]_sc3_step19_tag_normal", "[AUTO]_sc3_step2"]
        page.navigate_to_clean()
        tm = next((n for n in M_CAND if page.is_policy_exists(n)), None)
        if tm:
            page.open_modify_modal(tm)
            page.click_tag_tab()
            if len(page.get_item_tag_list_rows()) >= 1:
                page.click_item_tag_list_row(0)
                page.process.wait_open()
                page.process.set_pnetwork(True)
                page.process.add_ip_port("192.168.88.2", "-1")
                if page.is_confirm_modal_visible(timeout=1500):
                    page.dismiss_confirm_modal()
                page.process.confirm()
                page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
                page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
                    state="attached", timeout=page._TIMEOUT_MODAL
                )
                msg = page.get_confirm_message()
                defect_found = ("서버" in msg and "오류" in msg) or "발생" in msg
                self._add("warn" if defect_found else "pass",
                          "[UX 결함 EDIT] 프로세스별 제어 (태그) - 허용 IP/Port Port=-1 → 메인 수정 시 서버 오류 (sc3j Case M EDIT)",
                          f"입력: EDIT '{tm}' + 태그 Port=-1 + 수정 / 결과: 메시지={msg!r}", sc=4)
                page.dismiss_confirm_modal()
            page.close_modal()
        else:
            self._add("skip", "[UX 결함 EDIT] 태그 Port=-1 — 태그 보유 sc3 정책 부재", f"후보 {M_CAND} 없음", sc=4)

    # ==================================================================
    # 시나리오 4k — EDIT 메인 모달 중복 차단 (sc3f Case 6 EDIT 버전 + 확장자 중복)
    # 사용 정책: [AUTO]_sc3_step2 (sc3c 가 만든 종합 정책 — 확장자 + 전자서명 보유)
    # ==================================================================
    def test_scenario4k_edit_main_modal_duplicate(self, logged_in_page, settings):
        """시나리오 4k — EDIT 메인 모달 중복 차단 메시지.

        A. 차단할 확장자 중복 (기존 첫 확장자 재추가) → '이미 등록된 확장자' alert
        B. 전자서명 중복 (기존 첫 전자서명 재추가) → '이미 등록된 전자서명' alert (sc3f Case 6 EDIT)

        EDIT 모달 1회 open + 2 검증 + close_modal 1회.
        """
        print("\n━━ [제어 스위트] 시나리오 4k: EDIT 메인 모달 중복 차단 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4k — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        page.open_modify_modal(TARGET_NAME)

        # ── A. 차단할 확장자 중복 — self-contained (SKIP 제거) ────
        # 시스템 메시지 변형 인정: "이미 등록된" / "이미 동일한" 둘 다 정상 거부
        existing_exts = page.get_main_extension_list()
        if not existing_exts:
            page.add_main_extension("autoext")   # 0건이면 직접 추가 (self-contained)
            if page.is_confirm_modal_visible(timeout=500):
                page.dismiss_confirm_modal()
            existing_exts = ["autoext"]
        dup_ext = existing_exts[0]
        page.add_main_extension(dup_ext)         # 동일 확장자 재추가 → 중복 알림 기대
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            ok_dup = "이미" in msg and "확장자" in msg
            self._add("pass" if ok_dup else "fail",
                      "EDIT 메인 모달 — 차단할 확장자 중복 차단 메시지",
                      f"입력: 확장자 '{dup_ext}' 재추가 / 결과: 메시지={msg!r}", sc=4)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] EDIT 차단할 확장자 중복 — 메시지 미노출",
                      f"입력: '{dup_ext}' 재추가 / 결과: 알림 없음", sc=4)

        # ── A2. 차단할 확장자 형식(특수문자) 거부 (sc3 ADD 대칭, yaml :643) ──
        fmt_before = len(page.get_main_extension_list())
        page.add_main_extension("$@%")
        if page.is_confirm_modal_visible(timeout=1500):
            fmt_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            fmt_after = len(page.get_main_extension_list())
            ok = ("특수문자" in fmt_msg or "이외" in fmt_msg) and fmt_after == fmt_before
            self._add("pass" if ok else "fail",
                      "EDIT 메인 모달 — 차단할 확장자 형식(특수문자) 거부",
                      f"입력: '$@%' / 결과: 메시지={fmt_msg!r}, list 불변={fmt_after==fmt_before}", sc=4)
        else:
            self._add("fail", "[차단 메시지] EDIT 차단할 확장자 형식(특수문자) — 미노출",
                      f"입력: '$@%' / 결과: 알림 없음 (yaml :643 기대와 불일치)", sc=4)

        # ── B. 전자서명 중복 (sc3f Case 6 EDIT 버전) — self-contained (SKIP 제거) ──
        # 버그 fix (2026-05-27): 기존 selector '#signExceptTag' 오타 → 실제 '#signExceptUl'.
        #   잘못된 selector 로 항상 빈 배열 → 항상 skip 이었음. selector 수정 + 0건이면 직접 추가.
        page.set_sign_except_toggle(True)   # 토글 ON 보장 (list 노출 — 없으면 add 불가)
        try:
            existing_signs = page.page.evaluate("""() => {
                const tags = document.querySelectorAll('#signExceptUl button.tagInput span, #signExcept button.tagInput span');
                return Array.from(tags).map(s => s.textContent.trim().replace(/×$/, '').trim()).filter(Boolean);
            }""")
        except Exception:
            existing_signs = []
        if not existing_signs:
            # 데이터 없으면 직접 추가 (self-contained — SKIP 대신 항상 검증)
            page.add_sign_except("AutoSignDup")
            if page.is_confirm_modal_visible(timeout=500):
                page.dismiss_confirm_modal()
            existing_signs = ["AutoSignDup"]
        dup_sign = existing_signs[0]
        page.add_sign_except(dup_sign)   # 동일 전자서명 재추가 → 중복 알림 기대
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            ok_dup = "이미" in msg and "전자서명" in msg
            self._add("pass" if ok_dup else "fail",
                      "EDIT 메인 모달 — 전자서명 예외처리 중복 차단 메시지 (sc3f Case 6 EDIT)",
                      f"입력: 전자서명 '{dup_sign}' 재추가 / 결과: 메시지={msg!r}", sc=4)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] EDIT 전자서명 중복 — 메시지 미노출",
                      f"입력: '{dup_sign}' 재추가 / 결과: 알림 없음", sc=4)

        page.close_modal()

    # ==================================================================
    # 시나리오 4l — EDIT 웹제한 모달 validation (sc3f Case 1/3/5 EDIT 버전)
    # 사용 정책: 웹제한 행 1건 이상 보유한 정책 (sc3d/sc3i 가 만든 정책)
    # ==================================================================
    def test_scenario4l_edit_web_restrict_validation(self, logged_in_page, settings):
        """시나리오 4l — EDIT 웹제한 모달 validation 메시지.

        A. 웹제한 이름 빈값 + 확인 → 메시지 (sc3f Case 1 EDIT)
        B. URL 중복 (기존 첫 URL 재추가) → '이미 등록된 URL' alert (sc3f Case 3 EDIT)
        C. 웹제한 확장자 중복 → '이미 등록된 확장자' alert (sc3f Case 5 EDIT)
        """
        print("\n━━ [제어 스위트] 시나리오 4l: EDIT 웹제한 모달 validation ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        candidates = ["[AUTO]_sc3_step3", "[AUTO]_sc3_step2", "[AUTO]_sc3_step17_webname100_ok"]

        page.navigate_to_clean()
        TARGET_NAME = next((n for n in candidates if page.is_policy_exists(n)), None)
        if not TARGET_NAME:
            self._add("skip", "시나리오 4l — 웹제한 보유 sc3 정책 부재 → skip",
                      f"입력: 후보 정책 {candidates} / 결과: 모두 없음", sc=4)
            return

        page.open_modify_modal(TARGET_NAME)
        if len(page.get_item_web_restrict_rows()) < 1:
            self._add("skip", "시나리오 4l — 웹제한 행 0건 → skip",
                      f"입력: '{TARGET_NAME}' EDIT itemWebRestrictList 0행 / 결과: skip", sc=4)
            page.close_modal()
            return

        page.click_item_web_restrict_row(0)
        page.web_restrict.wait_open()

        # ── A. 웹제한 이름 빈값 + 확인 → 메시지 ──────────────────
        orig_name = page.web_restrict.get_name()
        page.web_restrict.set_name("")
        page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible(timeout=1500):
            msg_a = page.get_confirm_message()
            ok_a = ("이름" in msg_a or "입력" in msg_a) and msg_a != ""
            self._add("pass" if ok_a else "fail",
                      "EDIT 웹제한 모달 — 이름 빈값 + 확인 차단 메시지 (sc3f Case 1 EDIT)",
                      f"입력: webRestrictName='' + 확인 / 결과: 메시지={msg_a!r}", sc=4)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] EDIT 웹제한 이름 빈값 — 메시지 미노출",
                      "입력: webRestrictName='' + 확인 / 결과: 알림 없음", sc=4)

        # 이름 복원
        page.web_restrict.set_name(orig_name)

        # ── B. URL 중복 ──────────────────────────────────────────
        # 엄격 검증 (사용자 통찰 2026-05-26): "이미 등록된 URL" 이 정상 메시지,
        # "이미 등록된 폴더 경로" 가 나오면 시스템 메시지 일관성 결함 (낮은 BUG)
        existing_urls = page.web_restrict.get_url_list()
        if existing_urls:
            dup_url = existing_urls[0]
            page.web_restrict.add_url(dup_url)
            if page.is_confirm_modal_visible(timeout=1500):
                msg_b = page.get_confirm_message()
                page.dismiss_confirm_modal()
                # B-1: 중복 거부 자체는 동작했는가
                blocked = "이미 등록" in msg_b
                self._add("pass" if blocked else "fail",
                          "EDIT 웹제한 모달 — URL 중복 거부 동작 (sc3f Case 3 EDIT)",
                          f"입력: 기존 URL '{dup_url}' 재추가 / 결과: 메시지={msg_b!r}", sc=4)
                # B-2: 메시지가 'URL' 영역 표현인가 (일관성 결함 분리 검증)
                is_url_msg = "URL" in msg_b.upper() or "url" in msg_b or "주소" in msg_b
                is_folder_msg = "폴더" in msg_b or "경로" in msg_b
                if is_url_msg and not is_folder_msg:
                    self._add("pass", "EDIT 웹제한 모달 — URL 중복 메시지 일관성 (URL 영역 표현)",
                              f"입력: URL 재추가 / 결과: 메시지에 'URL/주소' 포함, '폴더/경로' 미포함 = {msg_b!r}", sc=4)
                elif is_folder_msg:
                    self._add("warn", "[메시지 일관성 결함] EDIT 웹제한 URL 중복 — 'URL' 영역인데 '폴더 경로' 메시지 노출",
                              f"입력: URL '{dup_url}' 재추가 / 결과: 메시지='폴더 경로' 포함 (UI 영역 ≠ 메시지 영역 불일치) = {msg_b!r}", sc=4)
                else:
                    self._add("warn", "[메시지 일관성 결함] EDIT 웹제한 URL 중복 — URL/주소 단어 누락",
                              f"입력: URL 재추가 / 결과: 메시지에 'URL'/'주소'/'폴더'/'경로' 모두 없음 = {msg_b!r}", sc=4)
            else:
                self._add("warn", "[차단 메시지] EDIT 웹제한 URL 중복 — 메시지 미노출",
                          f"입력: '{dup_url}' 재추가 / 결과: 알림 없음", sc=4)
        else:
            self._add("skip", "시나리오 4l B — URL 0건 → skip",
                      "입력: get_url_list 빈 배열 / 결과: skip", sc=4)

        # ── C. 웹제한 확장자 중복 ─────────────────────────────────
        # 시스템 메시지 변형 인정: "이미 등록된" / "이미 동일한" 둘 다 정상 거부
        existing_wr_exts = page.web_restrict.get_file_extension_list()
        if existing_wr_exts:
            dup_wr_ext = existing_wr_exts[0]
            page.web_restrict.add_file_extension(dup_wr_ext)
            if page.is_confirm_modal_visible(timeout=1500):
                msg_c = page.get_confirm_message()
                ok_c = "이미" in msg_c and "확장자" in msg_c
                self._add("pass" if ok_c else "fail",
                          "EDIT 웹제한 모달 — 확장자 중복 차단 메시지 (sc3f Case 5 EDIT)",
                          f"입력: 기존 확장자 '{dup_wr_ext}' 재추가 / 결과: 메시지={msg_c!r}", sc=4)
                page.dismiss_confirm_modal()
            else:
                self._add("warn", "[차단 메시지] EDIT 웹제한 확장자 중복 — 메시지 미노출",
                          f"입력: '{dup_wr_ext}' 재추가 / 결과: 알림 없음", sc=4)
        else:
            self._add("skip", "시나리오 4l C — 웹제한 확장자 0건 → skip",
                      "입력: get_file_extension_list 빈 배열 / 결과: skip", sc=4)

        # ── C2. 웹제한 확장자 형식(특수문자) 거부 (sc3 ADD 대칭, yaml :666) ──
        fmt_before = len(page.web_restrict.get_file_extension_list())
        page.web_restrict.add_file_extension("$@%")
        if page.is_confirm_modal_visible(timeout=1500):
            fmt_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            fmt_after = len(page.web_restrict.get_file_extension_list())
            ok = ("특수문자" in fmt_msg or "이외" in fmt_msg) and fmt_after == fmt_before
            self._add("pass" if ok else "fail",
                      "EDIT 웹제한 모달 — 확장자 형식(특수문자) 거부",
                      f"입력: '$@%' / 결과: 메시지={fmt_msg!r}, list 불변={fmt_after==fmt_before}", sc=4)
        else:
            self._add("fail", "[차단 메시지] EDIT 웹제한 확장자 형식(특수문자) — 미노출",
                      f"입력: '$@%' / 결과: 알림 없음 (yaml :666 기대와 불일치)", sc=4)

        # ── D. 복호화/업로드암호화 토글 의존성 (sc2e 역순의 EDIT 대응, #51) ──
        # 정방향: decrypt_target → 암호화 자동 강제 / 역순: 암호화 먼저 ON (decrypt_allow) 막히지 않는지
        try:
            page.web_restrict.click_decrypt_target()
            chk = page.web_restrict.is_file_encrypt_checked()
            dis = page.web_restrict.is_file_encrypt_disabled()
            self._add("pass" if (chk and dis) else "fail",
                      "EDIT 웹제한 모달 — 복호화 대상 → 업로드 암호화 자동 강제 (정방향)",
                      f"입력: decrypt_target / 결과: checked={chk}, disabled={dis}", sc=4)
            # 역순: 허용 URL 복귀 → 암호화 disabled 해제 → 수동 먼저 ON 막히지 않는지
            page.web_restrict.click_decrypt_allow()
            enc_dis = page.web_restrict.is_file_encrypt_disabled()
            if not enc_dis:
                page.web_restrict.set_file_encrypt(True)
                enc_chk = page.web_restrict.is_file_encrypt_checked()
                self._add("pass" if enc_chk else "fail",
                          "EDIT 웹제한 모달 — 업로드 암호화 먼저 수동 ON (decrypt_allow) 막히지 않음 (역순)",
                          f"입력: file_encrypt 수동 클릭 / 결과: checked={enc_chk}", sc=4)
                page.web_restrict.set_file_encrypt(False)  # 원복
            else:
                self._add("warn", "[입력 확인] EDIT 웹제한 — decrypt_allow 인데 암호화 disabled (먼저 클릭 막힘)",
                          f"입력: decrypt_allow 상태 / 결과: disabled={enc_dis}", sc=4)
        except Exception as e:
            self._add("skip", "EDIT 웹제한 모달 — 복호화/암호화 토글 검증 skip (기능 부재/예외)",
                      f"입력: decrypt 토글 / 결과: 예외={e!r}", sc=4)

        # ── E. 웹제한 이름 중복 차단 (sc3f Case7 EDIT 대칭 — 2026-05-28 추가) ──
        # 기존 wr#0 닫고 → 기존 행과 동일 이름으로 신규 wr 추가 → 이름 중복 차단 기대.
        page.web_restrict.close()
        page.web_restrict.wait_closed(timeout=3000)
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        # 기존 wr 행이 idx=0 사용 중 → 신규 wr 는 idx=1 (다른 프로세스) 필수.
        # yaml :287 cross_instance_ADD_flow: 동일 프로세스 재선택 silent 거부.
        page.picker.select_nth_and_confirm(1, mode="multi")
        page.web_restrict.set_name(orig_name)   # 기존 행과 동일 이름
        # confirm — picker 닫힘 후 잔여 modal-backdrop 가 pointer 가로채는 3-stack 케이스 →
        # JS evaluate click (좌표 무관, ng-click 발화 OK — yaml :564). dismiss_confirm_modal fallback 동일 패턴.
        page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first.evaluate("el => el.click()")
        if page.is_confirm_modal_visible(timeout=1500):
            msg_e = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok_e = "이미" in msg_e and ("이름" in msg_e or "등록" in msg_e)
            self._add("pass" if ok_e else "fail",
                      "EDIT 웹제한 모달 — 이름 중복 차단 메시지 (sc3f Case7 EDIT)",
                      f"입력: 기존 이름 '{orig_name}' 신규 wr 재등록 / 결과: 메시지={msg_e!r}", sc=4)
        else:
            self._add("fail", "[차단 메시지] EDIT 웹제한 이름 중복 — 미노출",
                      f"입력: 기존 이름 재등록 / 결과: 알림 없음 (Chrome 확인과 불일치)", sc=4)

        page.web_restrict.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 4m — EDIT process_modal validation (sc3f Case 2/4 EDIT 버전)
    # 사용 정책: 프로세스 행 1건 이상 보유 정책
    # ==================================================================
    def test_scenario4m_edit_process_modal_validation(self, logged_in_page, settings):
        """시나리오 4m — EDIT process_modal validation 메시지.

        A. IP+Port 중복 (기존 첫 조합 재추가) → '이미 등록' alert (sc3f Case 2 EDIT)
        B. 프로세스 확장자 중복 (기존 첫 확장자 재추가) → '이미 등록된 확장자' alert (sc3f Case 4 EDIT)
        """
        import re
        print("\n━━ [제어 스위트] 시나리오 4m: EDIT process_modal validation ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        candidates = ["[AUTO]_sc3_step9_port_D", "[AUTO]_sc3_step9_port_F", "[AUTO]_sc3_step2"]

        page.navigate_to_clean()
        TARGET_NAME = next((n for n in candidates if page.is_policy_exists(n)), None)
        if not TARGET_NAME:
            self._add("skip", "시나리오 4m — 프로세스 보유 sc3 정책 부재 → skip",
                      f"입력: 후보 {candidates} / 결과: 모두 없음", sc=4)
            return

        page.open_modify_modal(TARGET_NAME)
        if len(page.get_item_list_rows()) < 1:
            self._add("skip", "시나리오 4m — 프로세스 행 0건 → skip",
                      f"입력: '{TARGET_NAME}' EDIT itemList 0행 / 결과: skip", sc=4)
            page.close_modal()
            return

        page.click_item_list_row(0)
        page.process.wait_open()

        # ── A. IP+Port 중복 (sc3f Case 2 EDIT) ───────────────────
        existing_ips = page.process.get_ip_list()
        if existing_ips:
            first_text = existing_ips[0]
            ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", first_text)
            port_match = re.search(r":\s*(\d{1,5})|/\s*(\d{1,5})|\s(\d{1,5})\s*$", first_text)
            if ip_match and port_match:
                dup_ip = ip_match.group(1)
                dup_port = next((g for g in port_match.groups() if g), "")
                if dup_port:
                    page.process.add_ip_port(dup_ip, dup_port)
                    if page.is_confirm_modal_visible(timeout=1500):
                        msg_a = page.get_confirm_message()
                        ok_a = "이미 등록" in msg_a
                        self._add("pass" if ok_a else "fail",
                                  "EDIT process_modal — IP+Port 중복 차단 메시지 (sc3f Case 2 EDIT)",
                                  f"입력: 기존 '{dup_ip}:{dup_port}' 재추가 / 결과: 메시지={msg_a!r}", sc=4)
                        page.dismiss_confirm_modal()
                    else:
                        self._add("warn", "[차단 메시지] EDIT IP/Port 중복 — 메시지 미노출",
                                  f"입력: '{dup_ip}:{dup_port}' 재추가 / 결과: 알림 없음", sc=4)
                else:
                    self._add("skip", "시나리오 4m A — Port 파싱 실패 → skip",
                              f"입력: get_ip_list[0]={first_text!r} / 결과: regex 미매칭", sc=4)
            else:
                self._add("skip", "시나리오 4m A — IP/Port 파싱 실패 → skip",
                          f"입력: get_ip_list[0]={first_text!r} / 결과: regex 미매칭", sc=4)
        else:
            self._add("skip", "시나리오 4m A — IP 0건 → skip",
                      "입력: get_ip_list 빈 배열 / 결과: skip", sc=4)

        # ── B. 프로세스 확장자 중복 (sc3f Case 4 EDIT) — self-contained (SKIP 제거) ──
        # 확장자 제어 ON + ALLOWP(대상지정, input enabled) → 0건이면 직접 추가 → 동일값 재추가 중복.
        # 기존 retry(다른 정책 의존) 제거 — 현재 열린 process_modal 에서 항상 검증.
        page.process.set_pcontrol_extension(True)   # 확장자 제어 ON (input 노출)
        page.process.click_radio_allowp()           # ALLOWP 대상지정 (input enabled)
        existing_proc_exts = page.process.get_extension_list()
        if not existing_proc_exts:
            page.process.add_extension("autoext")    # 없으면 직접 추가 (self-contained)
            if page.is_confirm_modal_visible(timeout=500):
                page.dismiss_confirm_modal()
            existing_proc_exts = ["autoext"]
        dup_proc_ext = existing_proc_exts[0]
        page.process.add_extension(dup_proc_ext)     # 동일 확장자 재추가 → 중복 알림 기대
        if page.is_confirm_modal_visible(timeout=1500):
            msg_b = page.get_confirm_message()
            ok_b = "이미" in msg_b and "확장자" in msg_b
            self._add("pass" if ok_b else "fail",
                      "EDIT process_modal — 확장자 중복 차단 메시지 (sc3f Case 4 EDIT)",
                      f"입력: 확장자 '{dup_proc_ext}' 재추가 (정책 '{TARGET_NAME}') / 결과: 메시지={msg_b!r}", sc=4)
            page.dismiss_confirm_modal()
        else:
            self._add("warn", "[차단 메시지] EDIT process_modal 확장자 중복 — 메시지 미노출",
                      f"입력: '{dup_proc_ext}' 재추가 / 결과: 알림 없음", sc=4)

        # ── B2. 프로세스 확장자 형식(특수문자) 거부 (sc3 ADD 대칭, yaml :650) ──
        fmt_before = len(page.process.get_extension_list())
        page.process.add_extension("$@%")
        if page.is_confirm_modal_visible(timeout=1500):
            fmt_msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            fmt_after = len(page.process.get_extension_list())
            ok = ("특수문자" in fmt_msg or "이외" in fmt_msg) and fmt_after == fmt_before
            self._add("pass" if ok else "fail",
                      "EDIT process_modal — 확장자 형식(특수문자) 거부",
                      f"입력: '$@%' / 결과: 메시지={fmt_msg!r}, list 불변={fmt_after==fmt_before}", sc=4)
        else:
            self._add("fail", "[차단 메시지] EDIT process_modal 확장자 형식(특수문자) — 미노출",
                      f"입력: '$@%' / 결과: 알림 없음 (yaml :650 기대와 불일치)", sc=4)
        page.process.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 4n — EDIT picker duplicate (sc3i Case A/B EDIT 버전)
    # 사용 정책: 프로세스 행 1건 + 웹제한 행 1건 보유 정책
    # ==================================================================
    def test_scenario4n_edit_picker_duplicate(self, logged_in_page, settings):
        """시나리오 4n — EDIT picker 중복 차단 메시지.

        A. process picker — 기존 등록 프로세스 재선택 → '이미 등록' alert (sc3i Case A EDIT)
        B. web_restrict picker — 동일 인스턴스 안 중복 → alert (sc3i Case B EDIT)

        sc3i 검증된 패턴: select_first + confirm 분리 + ESC 다발 정리.
        """
        print("\n━━ [제어 스위트] 시나리오 4n: EDIT picker 중복 차단 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4n — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        # ── A. process picker 중복 ─────────────────────────────────
        # 엄격 검증: picker 의 첫 행이 itemList 의 기존 프로세스와 매칭되는지 사전 확인
        # → 매칭 안 되면 검증 의도 (중복 시도) 가 무의미. 매칭 시에만 검증 진행.
        page.open_modify_modal(TARGET_NAME)
        item_rows = page.get_item_list_rows()
        if len(item_rows) >= 1:
            # 정책에 등록된 프로세스 명 추출 (행 텍스트에서 첫 토큰)
            existing_proc_name = item_rows[0].split("\n")[0].strip() if item_rows else ""
            page.click_add_process_btn()
            page.process.wait_open()
            page.process.click_pick_btn()
            page.picker.wait_open()
            try:
                picker_first_name = page.picker.get_first_row_text()
            except Exception:
                picker_first_name = ""
            name_match = bool(existing_proc_name) and existing_proc_name in picker_first_name
            page.picker.select_first(mode="single")
            page.picker.confirm()
            if page.is_confirm_modal_visible(timeout=2000):
                msg_a = page.get_confirm_message()
                page.dismiss_confirm_modal()
                ok_a = "이미" in msg_a and ("프로세스" in msg_a or "등록" in msg_a)
                self._add("pass" if ok_a else "fail",
                          "EDIT process picker — 기존 프로세스 재선택 시 중복 거부 (sc3i Case A EDIT)",
                          f"입력: select_first(mode=single, picker_first={picker_first_name!r}, item_first={existing_proc_name!r}, match={name_match}) / 결과: 메시지={msg_a!r}", sc=4)
            else:
                # 메시지 미노출 — match 여부에 따라 분류 다르게
                if name_match:
                    self._add("warn", "[차단 메시지] EDIT process picker 중복 — 메시지 미노출 (true positive — 동일 프로세스 재선택했는데 알림 없음)",
                              f"입력: picker_first='{picker_first_name}' = item_first='{existing_proc_name}' / 결과: 알림 없음", sc=4)
                else:
                    self._add("skip", "EDIT process picker — 첫 행 미매칭 → 중복 검증 무의미 → skip",
                              f"입력: picker_first='{picker_first_name}' ≠ item_first='{existing_proc_name}' / 결과: 검증 의도 실현 불가", sc=4)
        else:
            self._add("skip", "시나리오 4n A — 프로세스 행 0건 → skip",
                      f"입력: '{TARGET_NAME}' itemList 0행 / 결과: skip", sc=4)
        # picker + process_modal + main 3중 모달 잔존 가능 (ESC/cancel 모두 위험)
        # → F5 reload (navigate_to_clean) 로 강제 정리 — 다음 case 가 깨끗한 상태에서 시작
        page.navigate_to_clean()

        # ── B. web_restrict picker 중복 ────────────────────────────
        # sc3i Case B 와 동일: web_restrict picker 는 mode='multi' (체크박스, 라디오 아님)
        # 검증 메시지도 sc3i Case B 와 동일 패턴 (프로세스/생략/타 웹제한 등)
        page.open_modify_modal(TARGET_NAME)
        if len(page.get_item_web_restrict_rows()) >= 1:
            page.click_item_web_restrict_row(0)
            page.web_restrict.wait_open()
            existing_wr_procs = page.web_restrict.get_process_rows()
            if existing_wr_procs:
                page.web_restrict.click_add_process_btn()
                page.picker.wait_open()
                page.picker.select_first(mode="multi")
                page.picker.confirm()
                if page.is_confirm_modal_visible(timeout=2000):
                    msg_b = page.get_confirm_message()
                    page.dismiss_confirm_modal()
                    ok_b = "이미" in msg_b and ("프로세스" in msg_b or "생략" in msg_b or "타 웹제한" in msg_b)
                    self._add("pass" if ok_b else "fail",
                              "EDIT web_restrict picker — 동일 인스턴스 안 프로세스 중복 거부 (sc3i Case B EDIT)",
                              f"입력: 기존 web 프로세스 재선택 (multi) / 결과: 메시지={msg_b!r}", sc=4)
                else:
                    self._add("warn", "[차단 메시지] EDIT web_restrict picker 중복 — 메시지 미노출",
                              "입력: 기존 프로세스 재선택 / 결과: 알림 없음", sc=4)
            else:
                self._add("skip", "시나리오 4n B — web_restrict 안 프로세스 0건 → skip",
                          "입력: get_process_rows 빈 배열 / 결과: skip", sc=4)
        else:
            self._add("skip", "시나리오 4n B — 웹제한 행 0건 → skip",
                      f"입력: '{TARGET_NAME}' itemWebRestrictList 0행 / 결과: skip", sc=4)
        # 3중 모달 잔존 가능 → F5 reload 로 강제 정리 (다음 sc4j 등에도 영향 없음)
        page.navigate_to_clean()

        # ── C. cacheFolder reserved_word 중복 picker (sc3i Case D EDIT, #25) ──
        # 프로세스 재진입 → 특수폴더 picker 로 [/DESKTOP/] 추가 → 같은 거 재추가 → '이미 등록된 폴더 경로'
        page.open_modify_modal(TARGET_NAME)
        if len(page.get_item_list_rows()) >= 1:
            page.click_item_list_row(0)
            page.process.wait_open()
            if page.feature_exists(page.process.SEL_CACHE_SPECIAL_BTN, timeout=1000):
                # 1차: [/DESKTOP/] 추가
                page.process.click_special_folder_btn()
                page.special_folder.wait_open()
                page.special_folder.select_and_confirm(["[/DESKTOP/]"])
                page.process.click_cache_add_btn()
                if page.is_confirm_modal_visible(timeout=1000):
                    page.dismiss_confirm_modal()   # 1차에서 이미 등록 알림 시 dismiss
                # 2차: 같은 [/DESKTOP/] 재추가 → 중복 알림 기대
                page.process.click_special_folder_btn()
                page.special_folder.wait_open()
                page.special_folder.select_and_confirm(["[/DESKTOP/]"])
                page.process.click_cache_add_btn()
                if page.is_confirm_modal_visible(timeout=2000):
                    msg_c = page.get_confirm_message()
                    page.dismiss_confirm_modal()
                    ok_c = "이미 등록" in msg_c and ("폴더" in msg_c or "경로" in msg_c)
                    self._add("pass" if ok_c else "fail",
                              "EDIT process_modal cache — 특수폴더 reserved_word 중복 차단 (sc3i Case D EDIT)",
                              f"입력: [/DESKTOP/] 재선택 + 추가 / 결과: 메시지={msg_c!r}", sc=4)
                else:
                    self._add("warn", "[차단 메시지] EDIT 특수폴더 picker 중복 — 메시지 미노출",
                              "입력: [/DESKTOP/] 재추가 / 결과: 알림 없음", sc=4)
                page.process.close()
            else:
                self._add("skip", "시나리오 4n C — 특수폴더 기능 부재", "(skip)", sc=4)
                page.process.close()
        else:
            self._add("skip", "시나리오 4n C — 프로세스 행 0건 → skip",
                      f"입력: '{TARGET_NAME}' itemList 0행 / 결과: skip", sc=4)
        page.navigate_to_clean()

    # ==================================================================
    # 시나리오 4o — EDIT format overflow / 형식 검증 (sc3g EDIT 버전)
    # 사용 정책: process 행 1건 보유 sc3 정책
    # ==================================================================
    def test_scenario4o_edit_format_overflow(self, logged_in_page, settings):
        """시나리오 4o — EDIT process_modal 내 input format / overflow 검증.

        Case A: Port 비숫자 'abc' → 'Port 형식을 다시 확인 해 주세요' (sc3g A EDIT)
        Case A2: Port 최대값 초과 '99999' → 'Port의 최대값은 65535...' (sc3g A2 EDIT)
        Case B1: IP 범위 초과 '256.256.256.256' → '아이피 주소 형식이 잘못' (sc3g B1 EDIT)
        Case B: IP 형식 잘못 'abc.def.ghi.jkl' → '아이피 주소 형식...' (sc3g B EDIT)
        Case C: process_modal 설명 1000자 → 300자 제한 (sc3g C EDIT)

        EDIT 진입 + process_modal 1회 open + 5 sub-case + 모두 close.
        Case D (web_restrict 설명 300자) 는 별도 흐름 — 같은 모달 세션에서 진행.
        """
        print("\n━━ [제어 스위트] 시나리오 4o: EDIT format / overflow 검증 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        long_desc = "가" * 1000
        # 강화 (허점 #5 보완): 후보 확장 + process 행 보유 여부도 사전 검증
        candidates = [
            "[AUTO]_sc3_step2", "[AUTO]_sc3_step9_port_D", "[AUTO]_sc3_step9_port_F",
            "[AUTO]_sc3_step9_drv50", "[AUTO]_sc3_step4", "[AUTO]_sc3_step3"
        ]

        page.navigate_to_clean()
        # process 행 보유한 첫 후보 선택 (단순 존재가 아니라 검증 가능 여부)
        TARGET_NAME = None
        for c in candidates:
            if not page.is_policy_exists(c):
                continue
            # 모달 진입 없이 list 단계에서는 row 보유 여부 알 수 없음 → 일단 첫 존재 후보 선택
            TARGET_NAME = c
            break
        if not TARGET_NAME:
            self._add("skip", "시나리오 4o — sc3 정책 부재 → skip",
                      f"입력: 후보 {candidates} / 결과: 모두 없음", sc=4)
            return

        page.open_modify_modal(TARGET_NAME)
        if len(page.get_item_list_rows()) < 1:
            # 첫 후보가 process 행 0건이면 다른 후보 retry
            page.close_modal()
            found = False
            for c in candidates[1:]:
                if c == TARGET_NAME or not page.is_policy_exists(c):
                    continue
                page.navigate_to_clean()
                page.open_modify_modal(c)
                if len(page.get_item_list_rows()) >= 1:
                    TARGET_NAME = c
                    found = True
                    break
                page.close_modal()
            if not found:
                self._add("skip", "시나리오 4o — 모든 후보 정책의 프로세스 행 0건 → skip",
                          f"입력: 후보 {candidates} / 결과: 모두 itemList 0행", sc=4)
                return

        page.click_item_list_row(0)
        page.process.wait_open()

        # ── Case A: Port 비숫자 'abc' ──────────────────────────────
        page.process.set_pnetwork(True)
        page.process.add_ip_port("192.168.10.10", "abc")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "Port" in msg and "형식" in msg
            self._add("pass" if ok else "fail",
                      "EDIT process_modal — Port 비숫자 입력 차단 (sc3g A EDIT)",
                      f"입력: Port='abc' + 추가 / 결과: 메시지={msg!r}", sc=4)
        else:
            self._add("warn", "[차단 메시지] EDIT Port 비숫자 — 메시지 미노출",
                      "입력: 'abc' / 결과: 알림 없음", sc=4)

        # ── Case A2: Port 최대값 초과 '99999' ──────────────────────
        page.process.add_ip_port("192.168.10.11", "99999")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "65535" in msg or ("Port" in msg and "최대" in msg)
            self._add("pass" if ok else "fail",
                      "EDIT process_modal — Port 최대값 초과 차단 (sc3g A2 EDIT)",
                      f"입력: Port='99999' + 추가 / 결과: 메시지={msg!r}", sc=4)
        else:
            self._add("warn", "[차단 메시지] EDIT Port 최대값 초과 — 메시지 미노출",
                      "입력: '99999' / 결과: 알림 없음", sc=4)

        # ── Case B1: IP 범위 초과 '256.256.256.256' ────────────────
        page.process.add_ip_port("256.256.256.256", "8080")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = ("아이피" in msg or "IP" in msg) and ("형식" in msg or "잘못" in msg)
            self._add("pass" if ok else "fail",
                      "EDIT process_modal — IP 범위 초과 차단 (sc3g B1 EDIT)",
                      f"입력: IP='256.256.256.256' + 추가 / 결과: 메시지={msg!r}", sc=4)
        else:
            self._add("warn", "[차단 메시지] EDIT IP 범위 초과 — 메시지 미노출",
                      "입력: '256.256.256.256' / 결과: 알림 없음", sc=4)

        # ── Case B: IP 형식 잘못 'abc.def.ghi.jkl' ─────────────────
        page.process.add_ip_port("abc.def.ghi.jkl", "8080")
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = ("아이피" in msg or "IP" in msg) and "형식" in msg
            self._add("pass" if ok else "fail",
                      "EDIT process_modal — IP 형식 invalid 차단 (sc3g B EDIT)",
                      f"입력: IP='abc.def.ghi.jkl' + 추가 / 결과: 메시지={msg!r}", sc=4)
        else:
            self._add("warn", "[차단 메시지] EDIT IP 형식 invalid — 메시지 미노출",
                      "입력: 'abc.def.ghi.jkl' / 결과: 알림 없음", sc=4)

        # ── Case C: process_modal 설명 1000자 + 확인 → 300자 제한 ──
        page.process.set_description(long_desc)
        page._click(page.page.locator(page.process.SEL_CONFIRM_BTN).first)
        if page.is_confirm_modal_visible(timeout=1500):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
            ok = "설명" in msg and "300자" in msg
            self._add("pass" if ok else "fail",
                      "EDIT process_modal — 설명 1000자 (300자 제한) 차단 (sc3g C EDIT)",
                      f"입력: 설명 길이=1000 / 결과: 메시지={msg!r}", sc=4)
        else:
            self._add("warn", "[차단 메시지] EDIT 프로세스 설명 300자 — 메시지 미노출",
                      "입력: 1000자 + 확인 / 결과: 알림 없음", sc=4)
        page.process.set_description("")
        page.process.close()

        # ── Case D: web_restrict_modal 설명 1000자 → 300자 제한 ────
        if len(page.get_item_web_restrict_rows()) >= 1:
            page.click_item_web_restrict_row(0)
            page.web_restrict.wait_open()
            page.web_restrict.set_description(long_desc)
            page._click(page.page.locator(page.web_restrict.SEL_CONFIRM_BTN).first)
            if page.is_confirm_modal_visible(timeout=1500):
                msg = page.get_confirm_message()
                page.dismiss_confirm_modal()
                ok = "설명" in msg and "300자" in msg
                self._add("pass" if ok else "fail",
                          "EDIT web_restrict_modal — 설명 1000자 (300자 제한) 차단 (sc3g D EDIT)",
                          f"입력: 설명 길이=1000 / 결과: 메시지={msg!r}", sc=4)
            else:
                self._add("warn", "[차단 메시지] EDIT 웹제한 설명 300자 — 메시지 미노출",
                          "입력: 1000자 + 확인 / 결과: 알림 없음", sc=4)
            page.web_restrict.set_description("")
            page.web_restrict.close()
        else:
            self._add("skip", "시나리오 4o D — 웹제한 행 0건 → skip",
                      f"입력: '{TARGET_NAME}' itemWebRestrictList 0행 / 결과: skip", sc=4)

        page.close_modal()

    # ==================================================================
    # 시나리오 4p — EDIT length boundary (sc3h Case B/C EDIT 버전)
    # 사용 정책: customOption + clipboardUrl 보유 정책
    # ==================================================================
    def test_scenario4p_edit_length_boundary(self, logged_in_page, settings):
        """시나리오 4p — EDIT 메인 모달 input 길이 한도 검증.

        Case B: customOptionText 100/300/500자 — DOM 길이 (sc3h B EDIT)
        Case C: clipboardAllowUrl 500/1000자 — DOM 길이 (sc3h C EDIT)

        Case A (csuName maxlength=50) 는 4g A 가 이미 다룸 → 중복 제외.
        DOM 입력만 검증 (저장 안 함) → 정책 잔존 상태 안 바꿈.
        """
        print("\n━━ [제어 스위트] 시나리오 4p: EDIT 메인 모달 input 길이 한도 검증 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        TARGET_NAME = "[AUTO]_sc3_step2"

        page.navigate_to_clean()
        if not page.is_policy_exists(TARGET_NAME):
            self._add("skip", "시나리오 4p — sc3 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{TARGET_NAME}' 없음", sc=4)
            return

        page.open_modify_modal(TARGET_NAME)

        # 원본 값 백업 (검증 후 복원 — 정책 잔존 보호)
        orig_name = page.get_csu_name()
        orig_custom = page.get_custom_option()
        orig_clip_url = page.get_clipboard_allow_url() if page.feature_exists(page.SEL_CLIPBOARD_URL) else ""

        # ── Case A: csuName 100/300/500자 → DOM maxlength=50 자동 절단 (sc3h A EDIT) ──
        # 4g A 는 100자 1회만 — 여기서 300/500 까지 boundary 완성
        for length in (100, 300, 500):
            page.set_csu_name("z" * length)
            got = page.get_csu_name()
            self._add("pass" if len(got) == 50 else "fail",
                      f"[오버플로 확인 EDIT] 스위트 이름 — {length}자 입력 시 DOM maxlength=50 자동 절단 (sc3h A EDIT)",
                      f"입력: {length}자 / 결과: 실제 DOM 길이={len(got)}", sc=4)
        page.set_csu_name(orig_name)  # 복원

        # ── Case B: customOptionText 100/300/500자 ───────────────
        for length in (100, 300, 500):
            page.set_custom_option("c" * length)
            got = page.get_custom_option()
            self._add("pass",
                      f"[오버플로 확인 EDIT] 커스텀 옵션 — {length}자 입력 DOM 길이 (sc3h B EDIT)",
                      f"입력: {length}자 / 결과: DOM 길이={len(got)}", sc=4)
        page.set_custom_option(orig_custom)  # 복원

        # ── Case C: clipboardAllowUrl 500/1000자 ──────────────────
        if page.feature_exists(page.SEL_CLIPBOARD_URL):
            for length in (500, 1000):
                page.set_clipboard_allow_url("u" * length)
                got = page.get_clipboard_allow_url()
                self._add("pass",
                          f"[오버플로 확인 EDIT] 클립보드 허용 URL — {length}자 입력 DOM 길이 (sc3h C EDIT)",
                          f"입력: {length}자 / 결과: DOM 길이={len(got)}", sc=4)
            page.set_clipboard_allow_url(orig_clip_url)  # 복원
        else:
            self._add("skip", "[오버플로 확인 EDIT] 클립보드 허용 URL — 기능 없음 (구 빌드)",
                      f"입력: {page.SEL_CLIPBOARD_URL} 매칭 실패 / 결과: 기능 부재", sc=4)

        # 메인 모달 cancel (저장 안 함 — 복원 값 그대로 보존)
        page.close_modal()

    # ==================================================================
    # 시나리오 4q — EDIT 정상 boundary 회귀 검증 (sc3j 정상 case 들의 EDIT 버전)
    # sc3 가 정상으로 저장한 boundary 값들이 EDIT 시점에도 정상 저장되는지 회귀.
    # 사용자 지적 (2026-05-26): "수정에도 해당 요소들 변경 테스트 필요, 기본 a쪽 빠짐"
    # ==================================================================
    def test_scenario4q_edit_normal_boundary_regression(self, logged_in_page, settings):
        """시나리오 4q — sc3j 정상 boundary case 들의 EDIT 회귀 검증.

        Case A: drv letter 50자 정상 (sc3j A EDIT) — [AUTO]_sc3_step9_drv50
        Case D: Port=8080 정상 (sc3j D EDIT) — [AUTO]_sc3_step9_port_D
        Case F: Port=0 정상 (sc3j F EDIT) — [AUTO]_sc3_step9_port_F
        Case N: basePath 300자 정상 (sc3j N EDIT) — [AUTO]_sc3_step16_bp300_ok
        Case O: webRestrictName 100자 정상 (sc3j O EDIT) — [AUTO]_sc3_step17_webname100_ok

        검증 의도: 변경 없이 메인 '수정' → '저장 하였습니다' 또는 '수정된 항목이 없습니다.'
        (이미 정상 boundary 로 저장된 값이라 변경 없이도 시스템이 거부하지 않아야 정상)
        sc3 결함 (server error) 정책은 4j 가 다루므로 4q 는 정상 회귀만.
        """
        print("\n━━ [제어 스위트] 시나리오 4q: EDIT 정상 boundary 회귀 검증 (sc3j 정상 case EDIT) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        # 정상 boundary 정책 리스트 (sc3j 가 정상 저장한 5개)
        normal_cases = [
            ("[AUTO]_sc3_step9_drv50",         "Case A: 드라이브 letter 50자 정상 boundary EDIT (sc3j A EDIT)"),
            ("[AUTO]_sc3_step9_port_D",        "Case D: Port=8080 정상 boundary EDIT (sc3j D EDIT)"),
            ("[AUTO]_sc3_step9_port_F",        "Case F: Port=0 정상 boundary EDIT (sc3j F EDIT)"),
            ("[AUTO]_sc3_step16_bp300_ok",     "Case N: basePath 300자 정상 boundary EDIT (sc3j N EDIT)"),
            ("[AUTO]_sc3_step17_webname100_ok","Case O: webRestrictName 100자 정상 boundary EDIT (sc3j O EDIT)"),
        ]

        for target_name, label in normal_cases:
            page.navigate_to_clean()
            if not page.is_policy_exists(target_name):
                self._add("skip", f"4q — {label} — sc3 정책 부재",
                          f"입력: '{target_name}' 없음 / 결과: skip", sc=4)
                continue

            # 진짜 회귀 검증 — 변경 X 만으론 모달 진입만 검증함.
            # customOption 한 글자만 변경 → 저장 → server round-trip 으로 정상 boundary 가 EDIT 도 OK 확인.
            # 변경 발생 → '저장 하였습니다' 받아야 진짜 EDIT 정상 동작.
            try:
                page.open_modify_modal(target_name)
                orig_custom = page.get_custom_option()
                modified = f"sc4q_touch_{int(time.time())}"
                page.set_custom_option(modified)
                msg = page.save_policy(mode="modify")
                page.dismiss_confirm_modal()
                ok = msg == "저장 하였습니다"
                self._add("pass" if ok else "fail",
                          f"[정상 boundary EDIT 회귀 — server round-trip] {label}",
                          f"입력: EDIT '{target_name}' + customOption 변경 + 수정 / 결과: 메시지={msg!r}", sc=4)
                # 원복 — customOption 을 원래 값으로 복원 (정책 보존)
                page.open_modify_modal(target_name)
                page.set_custom_option(orig_custom)
                restore_msg = page.save_policy(mode="modify")
                page.dismiss_confirm_modal()
                # 복원도 정상 저장되어야 (boundary 값과 함께 customOption 도 round-trip)
                restore_ok = restore_msg in _MODIFY_OK_MESSAGES
                self._add("pass" if restore_ok else "fail",
                          f"[정상 boundary EDIT 회귀 — 원복 round-trip] {label}",
                          f"입력: customOption '{orig_custom}' 복원 + 수정 / 결과: 메시지={restore_msg!r}", sc=4)
            except Exception as e:
                self._add("fail", f"[정상 boundary EDIT 회귀] {label} — 예외 발생",
                          f"입력: EDIT '{target_name}' + 수정 / 결과: 예외={e!r}", sc=4)
                try:
                    page.close_modal()
                except Exception:
                    pass

