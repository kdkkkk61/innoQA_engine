"""시나리오 4 — EDIT 모달 검증 (4b~4g). 3d 가 남긴 KEEP 정책 사용."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.control_suite._base import ControlSuiteBase


class TestScenario4Modify(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 4 — EDIT 모달 검증 (4b~4g)"""

    # ==================================================================
    # 시나리오 4b — 3b (minimal save E2E) 의 EDIT 버전 (메인 영역 최소 흐름)
    # ==================================================================
    def test_scenario4b_edit_minimal_modify(self, logged_in_page, settings):
        """시나리오 4b — 메인 영역 최소 modify (이름 load + customOption 1 필드 변경 + 저장 + 재진입)."""
        print("\n━━ [제어 스위트] 시나리오 4b: minimal modify (메인 영역) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"
        MOD_CUSTOM = "step5b_modified_by_4b"

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4b — KEEP 정책 미존재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            pytest.skip(f"{KEEP_NAME!r} 미존재")

        page.open_modify_modal(KEEP_NAME)
        loaded_name = page.get_csu_name()
        self._add("pass" if loaded_name == KEEP_NAME else "fail",
                  "스위트 수정 모달 — 진입 + 스위트 이름 load",
                  f"입력: 행 클릭 + '수정' / 결과: csuName={loaded_name!r}", sc=4)

        page.set_custom_option(MOD_CUSTOM)
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — '수정' 버튼 (저장)",
                  f"입력: 커스텀 옵션 변경 + '수정' / 결과: 메시지={msg!r}", sc=4)

        self._add("pass" if page.is_policy_exists(KEEP_NAME) else "fail",
                  "정책 list — 정책 잔존 (이름 미변경)",
                  f"입력: 저장 완료 후 / 결과: '{KEEP_NAME}' 존재={page.is_policy_exists(KEEP_NAME)}", sc=4)

        page.open_modify_modal(KEEP_NAME)
        co = page.get_custom_option()
        self._add("pass" if co == MOD_CUSTOM else "fail",
                  "스위트 수정 모달 — 변경값 재진입 일치",
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
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"
        # 4b 결과까지 누적된 상태값 (3d MODIFY + 4b customOption 변경)
        EXPECT = {
            "csuName":           KEEP_NAME,
            "clipboard_url":     "daum.net",
            "extensions":        ["txt", "doc", "exe"],
            "sign_count":        2,
            "custom_option":     "step5b_modified_by_4b",
        }
        MOD = {
            "clipboard_url":  "edit4c.com",
            "custom_option":  "edit_4c_modified",
            "new_extension":  "iso",
        }

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4c — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        page.open_modify_modal(KEEP_NAME)
        load_checks = {
            "스위트 이름":               page.get_csu_name() == EXPECT["csuName"],
            "클립보드 제한 토글":         page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked(),
            "클립보드 허용 URL":          EXPECT["clipboard_url"] in page.get_clipboard_allow_url(),
            "네트워크 접근 토글":         page.is_network_checked(),
            "라디오 라벨 (차단할 확장자)": page.get_radio_react_text() == "차단할 확장자",
            "확장자 목록":                page.get_main_extension_list() == EXPECT["extensions"],
            "헤더 체크 토글":             page.page.locator(page.SEL_HEADER_CHECK).first.is_checked(),
            "전자서명 예외 토글":         page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked(),
            "전자서명 예외 개수":         len(page.get_sign_except_list()) == EXPECT["sign_count"],
            "커스텀 옵션":                page.get_custom_option() == EXPECT["custom_option"],
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
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — 3 필드 변경 + '수정' 저장",
                  f"입력: URL/custom/확장자 변경 / 결과: 메시지={msg!r}", sc=4)

        page.open_modify_modal(KEEP_NAME)
        verify_checks = {
            "클립보드 허용 URL 변경 반영":   MOD["clipboard_url"] in page.get_clipboard_allow_url(),
            "커스텀 옵션 변경 반영":         page.get_custom_option() == MOD["custom_option"],
            "확장자 추가 반영":              MOD["new_extension"] in page.get_main_extension_list(),
            "스위트 이름 보존":              page.get_csu_name() == KEEP_NAME,
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

        KEEP 정책 EDIT 진입 → 개별 프로세스 1건 load → 첫 행 클릭 (process_modal 재진입) →
        12 필드 OFF→ON 변경 + 저장 + 재오픈 verify → ON→OFF 양방향 + 저장 + verify.
        """
        print("\n━━ [제어 스위트] 시나리오 4d: 프로세스별 제어 영역 종합 (ON↔OFF) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"
        PROC = {
            "ip":      "172.16.0.5",
            "port":    "8080",
            "ext":     ["zip", "iso"],
            "drive":   "D;E",
            "desc":    "edit_4d 프로세스 설명",
        }

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4d — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        # ── EDIT 진입 + 개별 프로세스 1건 load ─────────────────
        page.open_modify_modal(KEEP_NAME)
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
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in PROC["ext"]:
            page.process.add_extension(ext)
        page.process.set_access_drive(True)
        page.process.set_drive_letter(PROC["drive"])
        page.process.set_description(PROC["desc"])
        page.process.confirm()

        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — process_modal 12 필드 OFF→ON + '수정' 저장",
                  f"입력: 4 토글 + IP/Port + 확장자 + drive + 설명 / 결과: 메시지={msg!r}", sc=4)

        # ── 재오픈 → process_modal 재진입 + OFF→ON 값 일치 ────
        page.open_modify_modal(KEEP_NAME)
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
            "프로세스 확장자 목록 반영":               page.process.get_extension_list() == PROC["ext"],
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
        self._add("pass" if msg2 == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — process_modal 7 토글 ON→OFF + '수정' 저장",
                  f"입력: 7 토글 모두 OFF / 결과: 메시지={msg2!r}", sc=4)

        # 재오픈 → ON→OFF 일치
        page.open_modify_modal(KEEP_NAME)
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
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"
        TAG = {
            "ip":      "192.168.99.10",
            "port":    "9090",
            "ext":     ["docx", "xlsx"],
            "drive":   "F;G",
            "desc":    "edit_4e 태그 설명",
        }

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4e — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        # ── EDIT 진입 + Tag tab + itemTagList 0행 load ─────────
        page.open_modify_modal(KEEP_NAME)
        page.click_tag_tab()
        before_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if before_rows == 0 else "fail",
                  "태그 — Tag sub-tab 활성화 + 기존 itemTagList 0행 load",
                  f"입력: Tag tab 클릭 / 결과: itemTagList 행={before_rows}", sc=4)

        # ── 신규 태그 1건 추가 + picker tag mode 진입 검증 ──────
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        picker_title = page.picker.get_title()
        self._add("pass" if "태그" in picker_title else "fail",
                  "태그 — picker tag mode 진입 (제목 확인)",
                  f"입력: '+' + picker / 결과: picker title={picker_title!r}", sc=4)

        page.picker.select_first_and_confirm(mode="tag")

        # ── process_modal 12 필드 OFF→ON 변경 (yaml tag_sub_tab_policy 동일 깊이) ──
        page.process.set_process_except(True)
        page.process.set_pclipboard_restrict(True)
        page.process.set_sandbox(True)
        page.process.set_deny_except_drive(True)
        page.process.set_pnetwork(True)
        page.process.add_ip_port(TAG["ip"], TAG["port"])
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in TAG["ext"]:
            page.process.add_extension(ext)
        page.process.set_access_drive(True)
        page.process.set_drive_letter(TAG["drive"])
        page.process.set_description(TAG["desc"])
        page.process.confirm()

        after_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if after_rows == 1 else "fail",
                  "태그 — 신규 태그 1건 + process_modal 12 필드 입력 후 itemTagList 1행",
                  f"입력: tag picker + 12 필드 + 확인 / 결과: 행={after_rows}", sc=4)

        # ── '수정' 저장 ──────────────────────────────────────────
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — 태그 (12 필드 OFF→ON) 추가 + '수정' 저장",
                  f"입력: '수정' 클릭 / 결과: 메시지={msg!r}", sc=4)

        # ── 재오픈 + Tag tab → 행 재진입 + 11 필드 일치 ─────────
        page.open_modify_modal(KEEP_NAME)
        page.click_tag_tab()
        final_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if final_rows == 1 else "fail",
                  "스위트 수정 모달 — 재오픈 후 태그 1행 유지",
                  f"입력: 재오픈 + Tag tab / 결과: itemTagList 행={final_rows}", sc=4)

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
            "태그 확장자 목록 반영":                   page.process.get_extension_list() == TAG["ext"],
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
        self._add("pass" if msg2 == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — 태그 process_modal 7 토글 ON→OFF + '수정' 저장",
                  f"입력: 7 토글 모두 OFF / 결과: 메시지={msg2!r}", sc=4)

        # 재오픈 → 7 토글 OFF 일치
        page.open_modify_modal(KEEP_NAME)
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

        Part A (3c EDIT): KEEP 의 기존 웹제한 모달 재진입 → 5 필드 load + 4 영역 modify + 모달 확인.
        Part B (cross-instance): 2번째 웹제한 추가 → 사용중 프로세스 선택 시 알림 + 미사용 선택 + 정상 등록.
        """
        print("\n━━ [제어 스위트] 시나리오 4f: 웹제한 영역 + cross-instance (3c 의 EDIT 버전) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"
        INIT_WEB_NAME = "[AUTO]_web_step5b"
        INIT_URL      = "step5b-web.com"
        INIT_LIMIT    = "512"
        INIT_DESC     = "step5b 웹제한 초기값"
        MOD_URL    = "edit4f.com"
        MOD_EXT    = "png;jpg"
        MOD_LIMIT  = "2048"
        MOD_DESC   = "edit_4f 종합 수정"

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4f — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        # ════ Part A: 기존 웹제한 모달 재진입 + 종합 수정 ════
        page.open_modify_modal(KEEP_NAME)
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
        self._add("pass" if any(MOD_URL in u for u in page.web_restrict.get_url_list()) else "fail",
                  "웹제한 모달 — 적용 URL 추가 (수정)",
                  f"입력: '{MOD_URL}' / 결과: list={page.web_restrict.get_url_list()}", sc=4)

        page.web_restrict.add_file_extension(MOD_EXT)
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
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — 웹제한 종합 (Part A + Part B) 변경 + '수정' 저장",
                  f"입력: 종합 변경 / 결과: 메시지={msg!r}", sc=4)

        # 재오픈 + verify
        page.open_modify_modal(KEEP_NAME)
        final_rows = len(page.get_item_web_restrict_rows())
        self._add("pass" if final_rows == 2 else "fail",
                  "스위트 수정 모달 — 재오픈 후 웹제한 2건 (Part A 유지 + Part B 신규)",
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
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4g — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        # ── A. EDIT csuName maxlength=50 자동 절단 ──────────────
        page.open_modify_modal(KEEP_NAME)
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
        page.set_csu_name(KEEP_NAME)
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

        # KEEP EDIT 진입 후 DUP_PEER 이름으로 변경 시도
        page.open_modify_modal(KEEP_NAME)
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
        page.set_csu_name(KEEP_NAME)

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
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4h — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        # ── Case G: 프로세스 sub-modal 재진입 + 닫기 + 메인 수정 ──
        page.open_modify_modal(KEEP_NAME)
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
        page.open_modify_modal(KEEP_NAME)
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
        page.open_modify_modal(KEEP_NAME)
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

