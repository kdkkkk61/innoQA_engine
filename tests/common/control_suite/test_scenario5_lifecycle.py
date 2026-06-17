"""시나리오 5 — 한 정책 lifecycle (5a/5b/5c)."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.common.control_suite._base import ControlSuiteBase


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

        # 방어적 idempotent — 이전 run zz 가 [AUTO_KEEP] 보존 + sc1 cleanup 실패 시
        # NAME 이 잔존할 수 있음 → '이미 등록된 이름' 으로 sc5a 실패 (2026-05-28 사용자 보고).
        # session_cleanup 이 정상 동작했으면 is_policy_exists=False 라 no-op.
        if page.is_policy_exists(NAME):
            print(f"[sc5a 방어] NAME='{NAME}' 잔존 → 삭제 후 진행")
            try:
                page.delete_policy(NAME)
            except Exception as e:
                print(f"[sc5a 방어] 삭제 예외: {e!r}")

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
        # 메인 11 필드 — (일치여부, 실제값) 튜플로 실제 들어있는 값 표시
        _cb = "ON" if page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked() else "OFF"
        _nw = "ON" if page.is_network_checked() else "OFF"
        _hd = "ON" if page.page.locator(page.SEL_HEADER_CHECK).first.is_checked() else "OFF"
        _sg = "ON" if page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked() else "OFF"
        _url = page.get_clipboard_allow_url()
        _ext = page.get_main_extension_list()
        _sign = page.get_sign_except_list()
        checks_main = {
            "스위트 이름":          (page.get_csu_name() == NAME, page.get_csu_name()),
            "클립보드 공유제한":    (_cb == "ON", _cb),
            "클립보드 허용 URL":    (DATA["clipboard_url"] in _url, _url),
            "네트워크 허용":        (page.is_network_checked(), _nw),
            "제어할 확장자 라디오": (page.get_radio_react_text() == "차단할 확장자", page.get_radio_react_text()),
            "차단할 확장자 list":   (_ext == DATA["ext_list"], ", ".join(_ext)),
            "헤더 체크":            (_hd == "ON", _hd),
            "전자서명 예외 토글":   (_sg == "ON", _sg),
            "전자서명 예외 list":   (len(_sign) == len(DATA["sign_excepts"]), ", ".join(_sign)),
            "커스텀 옵션":          (page.get_custom_option() == DATA["custom_option"], page.get_custom_option()),
        }
        for k, (ok, val) in checks_main.items():
            self._add("pass" if ok else "fail",
                      f"시나리오 5a — 메인 필드 재오픈: {k}",
                      f"입력: 재오픈 / 결과: 실제값={val!r}", sc=5)

        # ── 개별 프로세스 itemList → process_modal 재진입 + 안 데이터 일치 ──
        page.click_individual_process_tab()
        proc_rows = len(page.get_item_list_rows())
        self._add("pass" if proc_rows == 1 else "fail",
                  "시나리오 5a — 개별 프로세스 itemList 1행 유지",
                  f"입력: 수정 모달 재오픈 / 결과: 행={proc_rows}", sc=5)

        if proc_rows >= 1:
            page.click_item_list_row(0)
            # process_modal 재진입 후 안 데이터 일치 검증
            _p_ip = page.process.get_ip_list()
            _p_ext = page.process.get_extension_list()
            _p_drv = page.process.get_drive_letter()
            _p_desc = page.process.get_description()
            _b = lambda sel: "ON" if page.process.is_toggle_checked(sel) else "OFF"
            checks_proc = {
                "프로세스 제외 토글":   (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT), _b(page.process.SEL_TOGGLE_PROC_EXCEPT)),
                "클립보드 제어 토글":   (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD), _b(page.process.SEL_TOGGLE_PCLIPBOARD)),
                "샌드박스 토글":        (page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX), _b(page.process.SEL_TOGGLE_SANDBOX)),
                "예외드라이브차단 토글":(page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE), _b(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE)),
                "네트워크 토글":        (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK), _b(page.process.SEL_TOGGLE_PNETWORK)),
                "허용 IP/Port":         (any(DATA["proc_ip"] in x and DATA["proc_port"] in x for x in _p_ip), ", ".join(_p_ip)),
                "확장자 제어 토글":     (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT), _b(page.process.SEL_TOGGLE_PCONTROL_EXT)),
                "제어 확장자 list":     (_p_ext == DATA["proc_ext"], ", ".join(_p_ext)),
                "접근 드라이브 토글":   (page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE), _b(page.process.SEL_TOGGLE_ACCESS_DRIVE)),
                "드라이브 letter":      (_p_drv == DATA["proc_drive"], _p_drv),
                "설명":                 (DATA["proc_desc"] in _p_desc, _p_desc),
            }
            for k, (ok, val) in checks_proc.items():
                self._add("pass" if ok else "fail",
                          f"시나리오 5a — 프로세스 등록 모달 재진입: {k}",
                          f"입력: itemList 행 클릭 (재진입) / 결과: 실제값={val!r}", sc=5)
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
            _t_ip = page.process.get_ip_list()
            _t_ext = page.process.get_extension_list()
            _t_drv = page.process.get_drive_letter()
            _t_desc = page.process.get_description()
            _tb = lambda sel: "ON" if page.process.is_toggle_checked(sel) else "OFF"
            checks_tag = {
                "프로세스 제외 토글":   (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT), _tb(page.process.SEL_TOGGLE_PROC_EXCEPT)),
                "클립보드 제어 토글":   (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD), _tb(page.process.SEL_TOGGLE_PCLIPBOARD)),
                "샌드박스 토글":        (page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX), _tb(page.process.SEL_TOGGLE_SANDBOX)),
                "예외드라이브차단 토글":(page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE), _tb(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE)),
                "네트워크 토글":        (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK), _tb(page.process.SEL_TOGGLE_PNETWORK)),
                "허용 IP/Port":         (any(DATA["tag_ip"] in x and DATA["tag_port"] in x for x in _t_ip), ", ".join(_t_ip)),
                "확장자 제어 토글":     (page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT), _tb(page.process.SEL_TOGGLE_PCONTROL_EXT)),
                "제어 확장자 list":     (_t_ext == DATA["tag_ext"], ", ".join(_t_ext)),
                "접근 드라이브 토글":   (page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE), _tb(page.process.SEL_TOGGLE_ACCESS_DRIVE)),
                "드라이브 letter":      (_t_drv == DATA["tag_drive"], _t_drv),
                "설명":                 (DATA["tag_desc"] in _t_desc, _t_desc),
            }
            for k, (ok, val) in checks_tag.items():
                self._add("pass" if ok else "fail",
                          f"시나리오 5a — 태그 등록 모달 재진입: {k}",
                          f"입력: itemTagList 행 클릭 (재진입) / 결과: 실제값={val!r}", sc=5)
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
            # web_ext "doc;xls" → list ["doc","xls"] 기대 (세미콜론 다중 등록)
            expected_web_exts = [e for e in DATA["web_ext"].split(";") if e]
            wr_ext_list = page.web_restrict.get_file_extension_list()
            wr_procs = page.web_restrict.get_process_rows()
            wr_urls = page.web_restrict.get_url_list()
            checks_web = {
                "웹제한 이름":      (wr_name == DATA["web_name"], wr_name),
                "프로세스 (multi)": (len(wr_procs) >= 1, ", ".join(wr_procs)),
                "URL 사용 토글":    (wr_isurl is True, "ON" if wr_isurl else "OFF"),
                "적용 URL":         (any(DATA["web_url"] in u for u in wr_urls), ", ".join(wr_urls)),
                "업로드 확장자":    (all(e in wr_ext_list for e in expected_web_exts), ", ".join(wr_ext_list)),
                "업로드 제한용량":  (wr_limit == DATA["web_limit"], wr_limit),
                "설명":             (DATA["web_desc"] in wr_desc, wr_desc),
            }
            for k, (ok, val) in checks_web.items():
                self._add("pass" if ok else "fail",
                          f"시나리오 5a — 웹제한 모달 재진입: {k}",
                          f"입력: itemWebRestrictList 행 클릭 / 결과: 실제값={val!r}", sc=5)
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
        """시나리오 5b — 5a 정책 EDIT → 전체 OFF (메인 + sub-modal 토글) → 재오픈 OFF 확인.

        사용자 lifecycle 흐름 (2026-05-27): 생성 ON → 전체 OFF 확인 → (5c) 요소 제거
          - 메인 토글 4개 OFF
          - 프로세스/태그 행 재진입 → 안의 토글(7개) OFF → 저장 (행/list 는 유지)
          - 웹제한 행 재진입 → is_url 토글 OFF
          → 재오픈 시 메인 + sub-modal 토글 전부 OFF 확인 (sub-modal OFF 검증이 핵심 — 기존 누락분)

        5a 정책이 list 에 없으면 skip.
        """
        print("\n━━ [제어 스위트] 시나리오 5b: 한 정책 lifecycle — 전체 OFF (메인+sub-modal) + 재오픈 OFF 확인 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        NAME = self.LIFECYCLE_NAME
        P = page.process
        PROC_TOGGLES = [P.SEL_TOGGLE_PROC_EXCEPT, P.SEL_TOGGLE_PCLIPBOARD, P.SEL_TOGGLE_SANDBOX,
                        P.SEL_TOGGLE_DENY_EXCEPT_DRIVE, P.SEL_TOGGLE_PNETWORK,
                        P.SEL_TOGGLE_PCONTROL_EXT, P.SEL_TOGGLE_ACCESS_DRIVE]

        def _proc_all_off():
            page.process.set_process_except(False)
            page.process.set_pclipboard_restrict(False)
            page.process.set_sandbox(False)
            page.process.set_deny_except_drive(False)
            page.process.set_pnetwork(False)
            page.process.set_pcontrol_extension(False)
            page.process.set_access_drive(False)

        page.navigate_to()
        if not page.is_policy_exists(NAME):
            self._add("skip",
                      "시나리오 5b — 5a 정책 ([AUTO_KEEP]_sc5_step1) 부재로 skip",
                      "입력: 5a 미실행/실패 / 결과: skip", sc=5)
            return

        # ── 전체 OFF — 메인 토글 + sub-modal 재진입 토글 OFF (행/list 유지) ──
        page.open_modify_modal(NAME)
        # 1. 메인 토글 4개 OFF
        page.set_clipboard_restrict_toggle(False)
        page.set_network_toggle(False)
        page.set_header_check(False)
        page.set_sign_except_toggle(False)
        # 2. 개별 프로세스 재진입 → 7토글 OFF
        page.click_individual_process_tab()
        if len(page.get_item_list_rows()) >= 1:
            page.click_item_list_row(0)
            page.process.wait_open()
            _proc_all_off()
            page.process.confirm()
        # 3. 태그 재진입 → 7토글 OFF
        page.click_tag_tab()
        if len(page.get_item_tag_list_rows()) >= 1:
            page.click_item_tag_list_row(0)
            page.process.wait_open()
            _proc_all_off()
            page.process.confirm()
        # 4. 웹제한 재진입 → is_url 토글 OFF
        page.click_individual_process_tab()
        if len(page.get_item_web_restrict_rows()) >= 1:
            page.click_item_web_restrict_row(0)
            page.web_restrict.wait_open()
            page.web_restrict.set_is_url(False)
            page.web_restrict.confirm()
        # 5. 메인 저장
        page.click_individual_process_tab()
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg in ("저장 하였습니다", "수정된 항목이 없습니다.") else "fail",
                  "시나리오 5b — 전체 OFF 수정 저장",
                  f"입력: 메인4토글 + 프로세스/태그 7토글 + 웹제한 is_url OFF / 결과: 메시지={msg!r}", sc=5)
        page.close_modal()

        # ── 재오픈 → 메인 + sub-modal 토글 전부 OFF 확인 ──────
        page.navigate_to()
        page.open_modify_modal(NAME)
        # 메인 4토글
        _mb = lambda sel: "ON" if page.page.locator(sel).first.is_checked() else "OFF"
        main_off = {
            "클립보드 공유제한": _mb(page.SEL_CLIPBOARD_RESTRICT),
            "네트워크 허용":     _mb(page.SEL_NETWORK) if hasattr(page, "SEL_NETWORK") else ("ON" if page.is_network_checked() else "OFF"),
            "헤더 체크":         _mb(page.SEL_HEADER_CHECK),
            "전자서명 예외":     _mb(page.SEL_SIGN_EXCEPT_TOGGLE),
        }
        for k, v in main_off.items():
            self._add("pass" if v == "OFF" else "fail",
                      f"시나리오 5b — 재오픈 메인 토글 OFF: {k}",
                      f"입력: 재오픈 / 결과: 실제값={v!r}", sc=5)
        # 프로세스 재진입 7토글 OFF
        page.click_individual_process_tab()
        if len(page.get_item_list_rows()) >= 1:
            page.click_item_list_row(0)
            page.process.wait_open()
            for sel in PROC_TOGGLES:
                off = not page.process.is_toggle_checked(sel)
                self._add("pass" if off else "fail",
                          f"시나리오 5b — 재오픈 프로세스 토글 OFF: {sel.split('#')[-1]}",
                          f"입력: itemList 재진입 / 결과: 실제값={'OFF' if off else 'ON'}", sc=5)
            page.process.close()
        # 태그 재진입 7토글 OFF
        page.click_tag_tab()
        if len(page.get_item_tag_list_rows()) >= 1:
            page.click_item_tag_list_row(0)
            page.process.wait_open()
            for sel in PROC_TOGGLES:
                off = not page.process.is_toggle_checked(sel)
                self._add("pass" if off else "fail",
                          f"시나리오 5b — 재오픈 태그 토글 OFF: {sel.split('#')[-1]}",
                          f"입력: itemTagList 재진입 / 결과: 실제값={'OFF' if off else 'ON'}", sc=5)
            page.process.close()
        page.close_modal()

    # ==================================================================
    # 시나리오 5c — 한 정책 lifecycle: 5b 변경값 재오픈 일치 확인 + cleanup
    # ==================================================================

    # ==================================================================
    # 시나리오 5c — 한 정책 lifecycle: 5b 변경값 재오픈 일치 확인 + cleanup
    # ==================================================================
    def test_scenario5c_lifecycle_verify(self, logged_in_page, settings):
        """시나리오 5c — 5b(전체 OFF) 후 모든 요소(내용/행) 제거 → 재오픈 이름만 확인 → cleanup.

        사용자 lifecycle 흐름 (2026-05-27): 생성 ON → 전체 OFF(5b) → 요소 제거(5c)
          - 5b 가 토글을 OFF 해서 클립보드 URL / 전자서명 list 가 숨겨진 상태
          - 제거하려면 해당 토글 ON 복귀 → list/URL 노출 → 제거 → 다시 OFF
            ("다시 ON 하고 지우고 다시 OFF" — 사용자 표현)
          - 확장자 list (라디오 영역, 토글 무관) / 커스텀 / 프로세스·태그·웹제한 행 삭제
          → 재오픈 시 이름만 + 전부 OFF + 전부 비움
          → (검증 완료 후) sc6 연계용으로 프로세스 1건 재채움 → 내용 있는 [AUTO_KEEP] 보존

        5b 정책이 list 에 없으면 skip.
        """
        print("\n━━ [제어 스위트] 시나리오 5c: 한 정책 lifecycle — 모든 요소 제거 + 이름만 확인 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        NAME = self.LIFECYCLE_NAME

        page.navigate_to()
        if not page.is_policy_exists(NAME):
            self._add("skip",
                      "시나리오 5c — 5b 정책 부재로 skip",
                      "입력: 5b 미실행/실패 / 결과: skip", sc=5)
            return

        # ── 요소 제거 — 토글 ON 복귀 → 숨겨진 list/URL 제거 → 다시 OFF ──
        page.open_modify_modal(NAME)
        # 1. 클립보드 토글 ON 복귀 → URL 제거 (5b 에서 OFF 되어 숨겨진 상태)
        page.set_clipboard_restrict_toggle(True)
        page.set_clipboard_allow_url("")
        # 2. 전자서명 토글 ON 복귀 → list 제거
        page.set_sign_except_toggle(True)
        removed_sign = page.remove_all_sign_except()
        # 3. 차단할 확장자 list 제거 (라디오 영역 — 토글 무관, 항상 노출)
        for ext in list(page.get_main_extension_list()):
            try:
                page.remove_main_extension(ext)
            except Exception:
                pass
        # 4. 커스텀 옵션 빈값
        page.set_custom_option("")
        # 5. 프로세스/태그/웹제한 행 전부 삭제
        removed_proc = page.remove_all_process_items()
        removed_tag  = page.remove_all_tag_items()
        removed_web  = page.remove_all_web_restrict_items()
        page.click_individual_process_tab()
        self._add("pass" if (removed_proc + removed_tag + removed_web) >= 1 else "fail",
                  "시나리오 5c — 요소(행) 제거 (프로세스/태그/웹제한)",
                  f"입력: 전체선택+삭제 / 결과: 프로세스={removed_proc} 태그={removed_tag} 웹제한={removed_web} (전자서명={removed_sign})", sc=5)
        # 6. 다시 OFF — 빈 정책 = 전부 OFF (제거 위해 ON 복귀했던 토글 원복)
        page.set_clipboard_restrict_toggle(False)
        page.set_network_toggle(False)
        page.set_header_check(False)
        page.set_sign_except_toggle(False)
        # 7. 저장 → 빈 정책 결과 판별
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        if msg in ("저장 하였습니다", "수정된 항목이 없습니다."):
            self._add("pass", "시나리오 5c — 모든 요소 제거 + 전부 OFF 저장 (빈 정책 = 이름만)",
                      f"입력: list/행 제거 + 토글 OFF + 수정 / 결과: 메시지={msg!r}", sc=5)
        elif ("서버" in msg and "오류" in msg) or "발생" in msg:
            self._add("warn", "[UX 결함] 빈 정책 (이름만) 저장 시 서버 오류 (sub-modal 단계에서 안내되어야 정상)",
                      f"입력: 모든 요소 제거 + 수정 / 결과: 메시지={msg!r}", sc=5)
        else:
            self._add("pass", "시나리오 5c — 빈 정책 저장 차단 메시지 (정상 가드)",
                      f"입력: 모든 요소 제거 + 수정 / 결과: 메시지={msg!r}", sc=5)
        page.close_modal()

        # ── 재오픈 → 이름만 + 전부 OFF + 전부 비움 확인 ────────
        page.navigate_to()
        page.open_modify_modal(NAME)
        _c_cb = "ON" if page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked() else "OFF"
        _c_nw = "ON" if page.is_network_checked() else "OFF"
        _c_hd = "ON" if page.page.locator(page.SEL_HEADER_CHECK).first.is_checked() else "OFF"
        _c_sg = "ON" if page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked() else "OFF"
        _c_url = page.get_clipboard_allow_url().strip()
        _c_ext = page.get_main_extension_list()
        _c_sign = page.get_sign_except_list()
        _c_custom = page.get_custom_option()
        verify_checks = {
            "필수 — 스위트 이름 유지":  (page.get_csu_name() == NAME, page.get_csu_name()),
            "클립보드 공유제한 OFF":    (_c_cb == "OFF", _c_cb),
            "네트워크 허용 OFF":        (_c_nw == "OFF", _c_nw),
            "헤더 체크 OFF":            (_c_hd == "OFF", _c_hd),
            "전자서명 예외 OFF":        (_c_sg == "OFF", _c_sg),
            "클립보드 허용 URL 비움":   (_c_url == "", _c_url or "(빈값)"),
            "차단할 확장자 list 비움":  (len(_c_ext) == 0, ", ".join(_c_ext) or "(0건)"),
            "전자서명 예외 list 비움":  (len(_c_sign) == 0, ", ".join(_c_sign) or "(0건)"),
            "커스텀 옵션 빈값":         (_c_custom == "", _c_custom or "(빈값)"),
            "개별 프로세스 행 비움":    (len(page.get_item_list_rows()) == 0, f"{len(page.get_item_list_rows())}행"),
            "태그 행 비움":             (len(page.get_item_tag_list_rows()) == 0, f"{len(page.get_item_tag_list_rows())}행"),
            "웹제한 행 비움":           (len(page.get_item_web_restrict_rows()) == 0, f"{len(page.get_item_web_restrict_rows())}행"),
        }
        for k, (ok, val) in verify_checks.items():
            self._add("pass" if ok else "fail",
                      f"시나리오 5c — 빈 정책 (이름만) 재오픈 일치: {k}",
                      f"입력: 재오픈 / 결과: 실제값={val!r}", sc=5)

        page.close_modal()

        # ── sc6 연계용 — [AUTO_KEEP] 정책 최소 내용 재채움 (빈 정책으로 남기지 않음) ──
        # 사용자 결정 (2026-05-28): "5 종료 시 keep 을 가진(내용 있는) 정책이 남아야 함 — sc6 가 사용".
        # 위 lifecycle 제거 검증(빈 정책)은 그대로 유지하고, 그 뒤 프로세스 1건 추가 저장 →
        # 내용 있는 [AUTO_KEEP] 보존. (lifecycle 검증 결과 ≠ sc6 핸드오프 상태 분리)
        page.navigate_to()
        page.open_modify_modal(NAME)
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()
        repop_msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        # 재오픈 → 내용(프로세스 1건) 보존 확인
        page.navigate_to()
        page.open_modify_modal(NAME)
        page.click_individual_process_tab()
        keep_rows = len(page.get_item_list_rows())
        self._add("pass" if keep_rows >= 1 else "fail",
                  "시나리오 5c — [AUTO_KEEP] 정책 재채움 (sc6 연계용 내용 보존)",
                  f"입력: 프로세스 1건 추가 저장 / 결과: 메시지={repop_msg!r}, 프로세스 행={keep_rows}", sc=5)
        page.close_modal()

        # 시나리오 5 종료 — [AUTO] 만 정리, [AUTO_KEEP]_sc5_step1 은 보존 (sc6 연계).
        # ⚠ close_modal 직후 list 의 삭제 버튼 click 잔해 timeout 방지 → navigate_to (F5) 로 list 안정화
        page.navigate_to()
        page.delete_all_auto_policies()   # [AUTO] 만 삭제, [AUTO_KEEP]_ (내용 보유) 보존

