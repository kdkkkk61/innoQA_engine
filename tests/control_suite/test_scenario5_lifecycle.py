"""시나리오 5 — 한 정책 lifecycle (5a/5b/5c)."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.control_suite._base import ControlSuiteBase


class TestScenario5Lifecycle(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 5 — 한 정책 lifecycle (5a/5b/5c)"""


    # ==================================================================
    # 시나리오 5a — 한 정책 lifecycle: ADD (종합) + 재오픈 일치 → 정책 보존
    # ==================================================================
    # [AUTO_KEEP]_sc5_step1 정책을 5a → 5b → 5c 에서 공유 사용.
    # 5a 는 cleanup 하지 않고 다음 단계에 정책을 넘긴다.
    LIFECYCLE_NAME = "[AUTO_KEEP]_sc5_step1"
    LIFECYCLE_ADD = {
        "clipboard_url":   "naver.com;daum.net",
        "ext_list":        ["pdf", "doc", "exe"],
        "sign_excepts":    ["Sign A", "Sign B"],
        "custom_option":   "lifecycle_init",
        "proc_ip":         "10.0.0.1",
        "proc_port":       "443",
        "proc_ext":        ["log", "tmp"],
        "proc_drive":      "C;D",
        "proc_desc":       "lifecycle 프로세스 설명",
        # 태그 sub-tab process_modal 필드 (yaml tag_sub_tab_policy 동일 깊이)
        "tag_ip":          "10.0.0.2",
        "tag_port":        "8443",
        "tag_ext":         ["zip", "rar"],
        "tag_drive":       "E;F",
        "tag_desc":        "lifecycle 태그 설명",
        "web_name":        "[AUTO]_web_lifecycle",
        "web_url":         "company.com",
        "web_ext":         "doc;xls",
        "web_limit":       "1024",
        "web_desc":        "lifecycle 웹제한 설명",
    }
    LIFECYCLE_MOD = {
        "clipboard_url":   "modified.com",
        "custom_option":   "lifecycle_modified",
    }

    # ==================================================================
    # 시나리오 5a — 메인 + 프로세스 + 태그 + 웹제한 종합 + 저장 + 재오픈 (정책 보존)
    # ==================================================================
    def test_scenario5a_lifecycle_add(self, logged_in_page, settings):
        """시나리오 5a — 전체 필드 (필수+선택) 채워서 저장 + 재오픈 모든 값 일치 → 정책 보존 ([AUTO_KEEP]_).

        흐름 (종합):
          1. 메인 모달 11 필드 (csuName + 클립보드+URL + 네트워크 + 라디오 + 확장자 + 헤더 + 전자서명+list + 커스텀)
          2. 개별 프로세스 등록 (process_modal 다중 필드: 4 토글 + 네트워크+IP/Port + 확장자+라디오 + drive + 설명)
          3. 태그 등록 (process_modal 태그 sub-tab)
          4. 웹제한 등록 (web_restrict_modal: 이름 + 프로세스 multi + URL + 확장자 + 제한용량 + 설명)
          5. 메인 저장
          6. 재오픈 → 메인 11 필드 + 3개 list 행 수 + sub-modal 재진입 일부 필드 일치
        """
        print("\n━━ [제어 스위트] 시나리오 5a: 한 정책 lifecycle — ADD (종합 — 메인+프로세스+태그+웹제한) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        NAME = self.LIFECYCLE_NAME
        DATA = self.LIFECYCLE_ADD

        page.navigate_to()
        # 1a 에서 이미 전체 정리됨 — AUTO 잔여만 정리 (시나리오 4 KEEP 보존).

        # ── 1. 메인 모달 — 11 필드 ─────────────────────────────
        page.open_add_modal()
        page.set_csu_name(NAME)
        page.set_clipboard_restrict_toggle(True)
        page.set_clipboard_allow_url(DATA["clipboard_url"])
        page.set_network_toggle(True)
        page.click_radio_allow()
        for ext in DATA["ext_list"]:
            page.add_main_extension(ext)
        page.set_header_check(True)
        page.set_sign_except_toggle(True)
        for sgn in DATA["sign_excepts"]:
            page.add_sign_except(sgn)
        page.set_custom_option(DATA["custom_option"])

        # ── 2. 개별 프로세스 + process_modal 다중 필드 ─────────
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        # 4 단독 토글
        page.process.set_process_except(True)
        page.process.set_pclipboard_restrict(True)
        page.process.set_sandbox(True)
        page.process.set_deny_except_drive(True)
        # 네트워크 + IP/Port
        page.process.set_pnetwork(True)
        page.process.add_ip_port(DATA["proc_ip"], DATA["proc_port"])
        # 확장자 제어
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in DATA["proc_ext"]:
            page.process.add_extension(ext)
        # drive + 설명
        page.process.set_access_drive(True)
        page.process.set_drive_letter(DATA["proc_drive"])
        page.process.set_description(DATA["proc_desc"])
        page.process.confirm()

        # ── 3. 태그 sub-tab + 태그 1건 + process_modal 12 필드 ─────
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="tag")
        # 태그 모드 process_modal 도 4 토글 + IP/Port + 확장자 + drive + 설명 입력
        page.process.set_process_except(True)
        page.process.set_pclipboard_restrict(True)
        page.process.set_sandbox(True)
        page.process.set_deny_except_drive(True)
        page.process.set_pnetwork(True)
        page.process.add_ip_port(DATA["tag_ip"], DATA["tag_port"])
        page.process.set_pcontrol_extension(True)
        page.process.click_radio_allowp()
        for ext in DATA["tag_ext"]:
            page.process.add_extension(ext)
        page.process.set_access_drive(True)
        page.process.set_drive_letter(DATA["tag_drive"])
        page.process.set_description(DATA["tag_desc"])
        page.process.confirm()

        # ── 4. 웹제한 모달 ────────────────────────────────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name(DATA["web_name"])
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_is_url(True)
        page.web_restrict.add_url(DATA["web_url"])
        page.web_restrict.add_file_extension(DATA["web_ext"])
        page.web_restrict.set_upload_limit(DATA["web_limit"])
        page.web_restrict.set_description(DATA["web_desc"])
        page.web_restrict.confirm()

        # ── 5. 메인 저장 ──────────────────────────────────────
        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" and page.is_policy_exists(NAME) else "fail",
                  "시나리오 5a — 종합 ADD (메인+프로세스+태그+웹제한) 저장",
                  f"입력: 메인 11 + process 12 + 태그 1 + web 6 / 결과: 메시지={msg!r}", sc=5)

        # ── 6. 재오픈 → 모든 값 일치 ──────────────────────────
        page.open_modify_modal(NAME)
        # 메인 11 필드
        checks_main = {
            "csu_name":          page.get_csu_name() == NAME,
            "clipboard_toggle":  page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked(),
            "clipboard_url":     DATA["clipboard_url"] in page.get_clipboard_allow_url(),
            "network":           page.is_network_checked(),
            "radio_label":       page.get_radio_react_text() == "차단할 확장자",
            "ext_list":          page.get_main_extension_list() == DATA["ext_list"],
            "header_check":      page.page.locator(page.SEL_HEADER_CHECK).first.is_checked(),
            "sign_toggle":       page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked(),
            "sign_count":        len(page.get_sign_except_list()) == len(DATA["sign_excepts"]),
            "custom_option":     page.get_custom_option() == DATA["custom_option"],
        }
        for k, ok in checks_main.items():
            self._add("pass" if ok else "fail",
                      f"시나리오 5a — 메인 필드 재오픈 일치: {k}",
                      f"입력: 수정 모달 재오픈 / 결과: 일치={ok}", sc=5)

        # ── 개별 프로세스 itemList → process_modal 재진입 + 안 데이터 일치 ──
        page.click_individual_process_tab()
        proc_rows = len(page.get_item_list_rows())
        self._add("pass" if proc_rows == 1 else "fail",
                  "시나리오 5a — 개별 프로세스 itemList 1행 유지",
                  f"입력: 수정 모달 재오픈 / 결과: 행={proc_rows}", sc=5)

        if proc_rows >= 1:
            page.click_item_list_row(0)
            # process_modal 재진입 후 안 데이터 일치 검증
            checks_proc = {
                "isProcessExcept_ON":       page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT),
                "isPClipboardRestrict_ON":  page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD),
                "isSandbox_ON":             page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX),
                "isDenyExceptDrive_ON":     page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE),
                "isPNetwork_ON":            page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK),
                "ip_port_registered":       any(DATA["proc_ip"] in x and DATA["proc_port"] in x
                                                for x in page.process.get_ip_list()),
                "isPControlExtension_ON":   page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT),
                "proc_ext_list":            page.process.get_extension_list() == DATA["proc_ext"],
                "isAccessDrive_ON":         page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE),
                "drive_letter":             page.process.get_drive_letter() == DATA["proc_drive"],
                "description":              DATA["proc_desc"] in page.process.get_description(),
            }
            for k, ok in checks_proc.items():
                self._add("pass" if ok else "fail",
                          f"시나리오 5a — 프로세스 등록 모달 재진입 일치: {k}",
                          f"입력: itemList 행 클릭 (재진입) / 결과: 일치={ok}", sc=5)
            page.process.close()

        # ── 태그 itemTagList → process_modal 재진입 ──
        page.click_tag_tab()
        tag_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if tag_rows == 1 else "fail",
                  "시나리오 5a — 태그 itemTagList 1행 유지",
                  f"입력: 수정 모달 재오픈 / 결과: 행={tag_rows}", sc=5)
        if tag_rows >= 1:
            page.click_item_tag_list_row(0)
            # 태그 모드 process_modal 재진입 — selected_display 가 미선택 아님
            tag_disp = page.process.get_selected_display_text()
            self._add("pass" if "미선택" not in tag_disp else "fail",
                      "시나리오 5a — 태그 등록 모달 재진입 (선택 표시 유지)",
                      f"입력: itemTagList 행 클릭 / 결과: display={tag_disp!r}", sc=5)

            # ── 태그 process_modal 12 필드 일치 (프로세스와 동일 깊이) ──
            checks_tag = {
                "isProcessExcept_ON":       page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT),
                "isPClipboardRestrict_ON":  page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD),
                "isSandbox_ON":             page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX),
                "isDenyExceptDrive_ON":     page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE),
                "isPNetwork_ON":            page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK),
                "tag_ip_port_registered":   any(DATA["tag_ip"] in x and DATA["tag_port"] in x
                                                for x in page.process.get_ip_list()),
                "isPControlExtension_ON":   page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT),
                "tag_ext_list":             page.process.get_extension_list() == DATA["tag_ext"],
                "isAccessDrive_ON":         page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE),
                "tag_drive_letter":         page.process.get_drive_letter() == DATA["tag_drive"],
                "tag_description":          DATA["tag_desc"] in page.process.get_description(),
            }
            for k, ok in checks_tag.items():
                self._add("pass" if ok else "fail",
                          f"시나리오 5a — 태그 등록 모달 재진입 일치: {k}",
                          f"입력: itemTagList 행 클릭 (재진입) / 결과: 일치={ok}", sc=5)
            page.process.close()

        # ── 웹제한 itemWebRestrictList → web_restrict 재진입 ──
        web_rows = len(page.get_item_web_restrict_rows())
        self._add("pass" if web_rows == 1 else "fail",
                  "시나리오 5a — 웹제한 itemWebRestrictList 1행 유지",
                  f"입력: 수정 모달 재오픈 / 결과: 행={web_rows}", sc=5)
        if web_rows >= 1:
            page.click_item_web_restrict_row(0)
            # web_restrict 재진입 후 안 데이터 일치
            wr_name = page.web_restrict.get_name()
            wr_limit = page.web_restrict.get_upload_limit()
            wr_desc = page.web_restrict.get_description()
            wr_isurl = page.web_restrict.is_url_checked()
            checks_web = {
                "name":          wr_name == DATA["web_name"],
                "isUrl_ON":      wr_isurl is True,
                "url_in_list":   any(DATA["web_url"] in u for u in page.web_restrict.get_url_list()),
                "upload_limit":  wr_limit == DATA["web_limit"],
                "description":   DATA["web_desc"] in wr_desc,
            }
            for k, ok in checks_web.items():
                self._add("pass" if ok else "fail",
                          f"시나리오 5a — 웹제한 모달 재진입 일치: {k}",
                          f"입력: itemWebRestrictList 행 클릭 / 결과: 일치={ok}", sc=5)
            page.web_restrict.close()

        page.close_modal()
        # [AUTO_KEEP]_ 정책은 보존 — 5b/5c 에서 lifecycle 이어 사용.

    # ==================================================================
    # 시나리오 5b — 한 정책 lifecycle: 5a 정책 EDIT → 입력값 변경 → 저장
    # ==================================================================

    # ==================================================================
    # 시나리오 5b — 한 정책 lifecycle: 5a 정책 EDIT → 입력값 변경 → 저장
    # ==================================================================
    def test_scenario5b_lifecycle_modify(self, logged_in_page, settings):
        """시나리오 5b — 5a 가 남긴 [AUTO_KEEP]_sc5_step1 정책의 EDIT 진입 → 메인 필드 변경 → 저장.

        5a 정책이 list 에 없으면 (5a 미실행/실패) skip — 5a 의존성 명시.
        """
        print("\n━━ [제어 스위트] 시나리오 5b: 한 정책 lifecycle — EDIT 변경 + 저장 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        NAME = self.LIFECYCLE_NAME
        MOD = self.LIFECYCLE_MOD

        page.navigate_to()
        if not page.is_policy_exists(NAME):
            self._add("skip",
                      "시나리오 5b — 5a 정책 ([AUTO_KEEP]_sc5_step1) 부재로 skip",
                      "입력: 5a 미실행/실패 / 결과: skip", sc=5)
            return

        # ── EDIT 진입 → 메인 필드 변경 ────────────────────────
        page.open_modify_modal(NAME)
        # 클립보드 토글 OFF + URL 변경
        page.set_clipboard_restrict_toggle(False)
        page.set_clipboard_restrict_toggle(True)  # 토글 재오픈 (URL 입력란 노출 유지)
        page.set_clipboard_allow_url(MOD["clipboard_url"])
        # 네트워크 OFF
        page.set_network_toggle(False)
        # 라디오 라벨 토글 (5a 의 click_radio_allow → 5b 에서 click_radio_block 으로 변경)
        page.click_radio_block()
        # 헤더 OFF, 전자서명 OFF
        page.set_header_check(False)
        page.set_sign_except_toggle(False)
        # 커스텀 변경
        page.set_custom_option(MOD["custom_option"])

        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "시나리오 5b — lifecycle 정책 EDIT 변경 + 저장",
                  f"입력: 클립보드URL/네트워크/라디오/헤더/전자서명/커스텀 / 결과: 메시지={msg!r}", sc=5)

    # ==================================================================
    # 시나리오 5c — 한 정책 lifecycle: 5b 변경값 재오픈 일치 확인 + cleanup
    # ==================================================================

    # ==================================================================
    # 시나리오 5c — 한 정책 lifecycle: 5b 변경값 재오픈 일치 확인 + cleanup
    # ==================================================================
    def test_scenario5c_lifecycle_verify(self, logged_in_page, settings):
        """시나리오 5c — 5b 변경 후 lifecycle 정책 재오픈 → 변경값 정상 적용 확인 → cleanup.

        5b 정책이 list 에 없으면 skip.
        """
        print("\n━━ [제어 스위트] 시나리오 5c: 한 정책 lifecycle — 변경값 재오픈 일치 확인 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        NAME = self.LIFECYCLE_NAME
        MOD = self.LIFECYCLE_MOD
        ADD = self.LIFECYCLE_ADD

        page.navigate_to()
        if not page.is_policy_exists(NAME):
            self._add("skip",
                      "시나리오 5c — 5b 정책 부재로 skip",
                      "입력: 5b 미실행/실패 / 결과: skip", sc=5)
            return

        page.open_modify_modal(NAME)
        verify_checks = {
            "클립보드 허용 URL 변경 반영":   MOD["clipboard_url"] in page.get_clipboard_allow_url(),
            "네트워크 접근 토글 (ON→OFF)":   page.is_network_checked() is False,
            "헤더 체크 토글 (ON→OFF)":       page.page.locator(page.SEL_HEADER_CHECK).first.is_checked() is False,
            "전자서명 예외 토글 (ON→OFF)":   page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked() is False,
            "커스텀 옵션 변경 반영":         page.get_custom_option() == MOD["custom_option"],
            # 미변경 필드 보존
            "스위트 이름 보존":              page.get_csu_name() == NAME,
            "확장자 목록 보존":              page.get_main_extension_list() == ADD["ext_list"],
        }
        for k, ok in verify_checks.items():
            self._add("pass" if ok else "fail",
                      f"시나리오 5c — lifecycle 변경값 재오픈 일치: {k}",
                      f"입력: 수정 모달 재오픈 / 결과: 일치={ok}", sc=5)

        page.close_modal()
        # 시나리오 5 종료 — 시나리오 6 가 새 KEEP 을 만들 예정이므로 전체 정리.
        page.delete_all_test_data()

