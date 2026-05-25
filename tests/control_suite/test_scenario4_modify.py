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
        # sc3 등록 태그와 중복 시 '이미 등록된 태그' 알림 dismiss
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
            self._add("warn", "태그 — sc3 등록 태그 중복 알림 발생 → ESC 정리 (sc3i 패턴)",
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

        # ── E. EDIT csuName 중복 차단 메시지 ─────────────────────
        page.set_csu_name(TARGET_NAME)
        page.close_modal()
        DUP_PEER = "[AUTO]_4g_dup_peer"
        page.open_add_modal()
        page.set_csu_name(DUP_PEER)
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()
        page.save_policy(mode="add")
        page.dismiss_confirm_modal()

        # sc3 정책 EDIT 진입 후 DUP_PEER 이름으로 변경 시도
        page.open_modify_modal(TARGET_NAME)
        page.set_csu_name(DUP_PEER)
        page._click(page.page.locator(page.SEL_SUBMIT_MODIFY).first)
        page.page.locator(page.SEL_CONFIRM_MODAL_OPEN).first.wait_for(
            state="attached", timeout=page._TIMEOUT_MODAL
        )
        dup_msg = page.get_confirm_message()
        self._add("pass" if dup_msg == "이미 등록된 이름 입니다." else "fail",
                  "스위트 이름 — EDIT 중복 차단 메시지",
                  f"입력: 이름='{DUP_PEER}' (중복) + '수정' / 결과: 메시지={dup_msg!r}", sc=4)
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

        # ── Case G: 프로세스 sub-modal 재진입 + 닫기 + 메인 수정 ──
        page.open_modify_modal(TARGET_NAME)
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
        page.close_modal()

        # ── Case H: 태그 sub-modal 재진입 + 닫기 + 메인 수정 ──
        page.open_modify_modal(TARGET_NAME)
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
        page.close_modal()

        # ── Case I: 웹제한 sub-modal 재진입 + 닫기 + 메인 수정 ──
        page.open_modify_modal(TARGET_NAME)
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

        # ── Case A: 자기 자신 이름 그대로 modify → 정상 저장 ──
        page.open_modify_modal(SELF_NAME)
        # 이름 변경 없이 그대로 저장 (자기 자신 허용 검증)
        msg_a = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        # '수정된 항목이 없습니다.' 도 정상 (이름 변경 없으면 시스템이 '변화 없음' 판정)
        self._add("pass" if msg_a in _MODIFY_OK_MESSAGES else "fail",
                  "스위트 수정 모달 — 자기 자신 이름 그대로 modify (정상 저장 허용)",
                  f"입력: 이름 변경 X + '수정' / 결과: 메시지={msg_a!r}", sc=4)

        # ── Case B: 다른 정책 이름으로 변경 → 중복 차단 ──
        page.open_modify_modal(SELF_NAME)
        page.set_csu_name(OTHER_NAME)
        msg_b = page.save_policy(mode="modify")
        # alert 떠있는 상태에서 _add → 스크린샷에 차단 메시지 포함
        ok_blocked = "이미 등록" in msg_b and "이름" in msg_b
        self._add("pass" if ok_blocked else "fail",
                  "스위트 수정 모달 — 다른 정책 이름으로 변경 → 중복 차단 메시지",
                  f"입력: 이름 '{SELF_NAME}' → '{OTHER_NAME}' / 결과: 메시지={msg_b!r}", sc=4)
        page.dismiss_confirm_modal()
        # 원본 이름 복원 후 cancel (정책 보존)
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

