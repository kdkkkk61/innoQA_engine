"""nPouch 엔파우치 정책 — 시나리오 5 — KEEP 정책 lifecycle (5a/5b/5c).

origin_protect sc5 패턴 복제:
  - 5a: [AUTO_KEEP]_sc5_npouch_policy 정책 ADD (전부 ON + 텍스트) + 재오픈 일치
  - 5b: 필수 유지 + 나머지 모든 옵션 OFF + 텍스트 비움 + 재오픈 일치
  - 5c: 5b 상태 재오픈 + cleanup ([AUTO]_ 만 정리, [AUTO_KEEP]_ 보존)

cleanup 라이프사이클:
  - sc1 시작: AUTO + AUTO_KEEP 둘 다 cleanup
  - sc2/3/4: cleanup 없음
  - sc5c: AUTO 만 cleanup, AUTO_KEEP 보존 (sc6 / 다음 페이지 연계)

의존성: [AUTO_KEEP]_sc5_origin_protect — 원본보호 정책 연계.
"""
from pages.npouch_policy_page import NpouchPolicyPage
from tests.npouch_policy._base import NpouchPolicyBase
from tests.npouch_policy.test_scenario3_add import _save_click, _select_origin_protect_keep
from tests.npouch_policy.test_scenario4_modify import _enter_edit_modal, _safe_close_modal


# ─────────────────────────────────────────────────────────────────
# Toggle helper — 체크박스를 target 상태로 set (disabled 면 skip)
# ─────────────────────────────────────────────────────────────────
def _toggle_to(page, sel: str, target: bool):
    el = page.page.locator(sel).first
    try:
        if not el.is_enabled():
            return
        cur = el.is_checked()
    except Exception:
        cur = False
    if cur != target:
        el.evaluate("el => el.click()")
        page.page.wait_for_timeout(100)


class TestNpouchPolicyScenario5Lifecycle(NpouchPolicyBase):
    """엔파우치 정책 — sc5: KEEP 정책 lifecycle (5a → 5b → 5c)."""

    LIFECYCLE_NAME = "[AUTO_KEEP]_sc5_npouch_policy"

    # ON 상태 (sc5a 가 채움 + sc5a 재오픈 일치 검증)
    ON_VALUES = {
        "name": LIFECYCLE_NAME,
        # 필수 + 변경값
        "cert_url": "https://sc5a.lifecycle/cert",
        "is_validate_ssl": True,
        "is_max_read_count": True,
        "max_read_count": "5",
        "is_max_read_day": True,
        "max_read_day": "7",
        "is_open_pw": True,
        "pw_min": "10",
        "pw_max": "14",
        "pw_same": "4",
        "pw_continue": "4",
        "is_pw_number": True,
        "is_pw_special": True,
        "is_origin_protect": True,
        "is_print_option": True,
        "is_print_o": True,  # 인쇄 허용
        "is_file_count": True,
        "file_count": "10",
        "is_server_auth": False,  # default OFF (사용자 일관성)
        "is_ext_filter": True,
        "is_pdf_protect": True,
    }

    # OFF 상태 (sc5b 가 채움 — 메인 토글 OFF, 필수만 유지)
    OFF_VALUES = {
        "name": LIFECYCLE_NAME,         # 필수 (★)
        # 메인 토글 OFF — 종속은 서버 default restore 로 검증 제외
        "is_validate_ssl": False,
        "is_max_read_count": False,
        "is_max_read_day": False,
        "is_open_pw": False,
        "is_origin_protect": False,
        "is_print_option": False,
        "is_file_count": False,
        "is_server_auth": False,
        "is_ext_filter": False,
        "is_pdf_protect": False,
    }

    @staticmethod
    def _dump_dom(page) -> dict:
        return page.page.evaluate(
            """() => ({
                name: (document.getElementById('npPolicyName')||{}).value,
                cert_url: (document.getElementById('readFileCertificateUrl')||{}).value,
                is_validate_ssl: !!(document.getElementById('isValidateSslCert')||{}).checked,
                is_max_read_count: !!(document.getElementById('isMaxReadCount')||{}).checked,
                max_read_count: (document.getElementById('maxReadCount')||{}).value,
                is_max_read_day: !!(document.getElementById('isMaxReadDay')||{}).checked,
                max_read_day: (document.getElementById('maxReadDay')||{}).value,
                is_open_pw: !!(document.getElementById('isOpenFilePassword')||{}).checked,
                pw_min: (document.getElementById('passwordMinDigit')||{}).value,
                pw_max: (document.getElementById('passwordMaxDigit')||{}).value,
                pw_same: (document.getElementById('passwordSameLetterCount')||{}).value,
                pw_continue: (document.getElementById('passwordContinueLetterCount')||{}).value,
                is_pw_number: !!(document.getElementById('isPasswordNumberLetter')||{}).checked,
                is_pw_special: !!(document.getElementById('isPasswordSpecialLetter')||{}).checked,
                is_origin_protect: !!(document.getElementById('isOriginProtectPolicy')||{}).checked,
                is_print_option: !!(document.getElementById('isPrintOption')||{}).checked,
                is_print_o: !!(document.getElementById('isPrintO')||{}).checked,
                is_file_count: !!(document.getElementById('isNpPackageFileCreateFileCount')||{}).checked,
                file_count: (document.getElementById('npPackageFileCreateFileCount')||{}).value,
                is_server_auth: !!(document.getElementById('isServerAuthToRead')||{}).checked,
                is_ext_filter: !!(document.getElementById('isExtensionFilter')||{}).checked,
                is_pdf_protect: !!(document.getElementById('isPdfProtect')||{}).checked,
            })"""
        )

    def _verify_loaded(self, page, loaded: dict, expected: dict, scope: str):
        sel_by_key = {
            "name": page.SEL_POLICY_NAME, "cert_url": page.SEL_CERT_URL,
            "is_validate_ssl": page.SEL_VALIDATE_SSL,
            "is_max_read_count": page.SEL_MAX_READ_COUNT_TOGGLE,
            "max_read_count": page.SEL_MAX_READ_COUNT_VAL,
            "is_max_read_day": page.SEL_MAX_READ_DAY_TOGGLE,
            "max_read_day": page.SEL_MAX_READ_DAY_VAL,
            "is_open_pw": page.SEL_PW_TOGGLE,
            "pw_min": page.SEL_PW_MIN, "pw_max": page.SEL_PW_MAX,
            "pw_same": page.SEL_PW_SAME_LETTER, "pw_continue": page.SEL_PW_CONTINUE_LETTER,
            "is_pw_number": page.SEL_PW_NUMBER_LETTER,
            "is_pw_special": page.SEL_PW_SPECIAL_LETTER,
            "is_origin_protect": page.SEL_ORIGIN_PROTECT,
            "is_print_option": page.SEL_PRINT_OPTION, "is_print_o": page.SEL_PRINT_O,
            "is_file_count": page.SEL_FILE_COUNT_TOGGLE, "file_count": page.SEL_FILE_COUNT_VAL,
            "is_server_auth": page.SEL_SERVER_AUTH,
            "is_ext_filter": page.SEL_EXT_FILTER,
            "is_pdf_protect": page.SEL_PDF_PROTECT,
        }
        for k, v in expected.items():
            actual = loaded.get(k)
            ok = actual == v
            sel = sel_by_key.get(k, page.SEL_MODAL_OPEN)
            loc = page.page.locator(sel).first
            self._add("pass" if ok else "fail",
                      f"sc{scope} — 재오픈 [{k}] 일치",
                      f"기대: {v!r} / 실제: {actual!r} / 캡처위치: {sel}",
                      sc=5, highlight=loc)

    # ==================================================================
    # sc5a — lifecycle ADD: 전부 ON + 텍스트 채움 → 재오픈 일치
    # ==================================================================
    def test_scenario5a_lifecycle_add(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 5a: lifecycle ADD (전부 ON) ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        # sc1 만 cleanup 호출 (사용자 보고 2026-06-02). sc5 는 호출 안 함.

        NAME = self.LIFECYCLE_NAME
        # 잔존 시 자기 정책만 삭제 (origin_protect 패턴)
        if page.is_policy_exists(NAME):
            try:
                page.delete_policy(NAME)
                page.page.wait_for_timeout(500)
                self._add("pass", "sc5a — 이전 잔존 KEEP 정책 삭제 (풀세팅 보장)",
                          f"입력: {NAME} / 결과: 자기 정책만 정리", sc=5)
            except Exception as e:
                self._add("warn", "sc5a — 잔존 정책 삭제 예외", f"{e!r}", sc=5)

        v = self.ON_VALUES
        page.open_add_modal()
        if self._skip_if_missing(page, "sc5a lifecycle 생성(열람횟수/암호 등)",
                                 [page.SEL_MAX_READ_COUNT_VAL], sc=5):
            page.close_modal(); return
        # 필수 + 텍스트
        page.page.locator(page.SEL_POLICY_NAME).fill(v["name"])
        page.page.locator(page.SEL_CERT_URL).fill(v["cert_url"])

        # 토글 + 숫자 (default ON 인 거 그대로 두고, 값 변경)
        _toggle_to(page, page.SEL_VALIDATE_SSL, v["is_validate_ssl"])
        _toggle_to(page, page.SEL_MAX_READ_COUNT_TOGGLE, v["is_max_read_count"])
        page.page.locator(page.SEL_MAX_READ_COUNT_VAL).fill(v["max_read_count"])
        _toggle_to(page, page.SEL_MAX_READ_DAY_TOGGLE, v["is_max_read_day"])
        page.page.locator(page.SEL_MAX_READ_DAY_VAL).fill(v["max_read_day"])

        # 비번
        _toggle_to(page, page.SEL_PW_TOGGLE, v["is_open_pw"])
        page.page.locator(page.SEL_PW_MIN).fill(v["pw_min"])
        page.page.locator(page.SEL_PW_MAX).fill(v["pw_max"])
        page.page.locator(page.SEL_PW_SAME_LETTER).fill(v["pw_same"])
        page.page.locator(page.SEL_PW_CONTINUE_LETTER).fill(v["pw_continue"])
        _toggle_to(page, page.SEL_PW_NUMBER_LETTER, v["is_pw_number"])
        _toggle_to(page, page.SEL_PW_SPECIAL_LETTER, v["is_pw_special"])

        # 원본보호 + KEEP 선택
        _toggle_to(page, page.SEL_ORIGIN_PROTECT, v["is_origin_protect"])
        _select_origin_protect_keep(page)

        # 인쇄
        _toggle_to(page, page.SEL_PRINT_OPTION, v["is_print_option"])
        _toggle_to(page, page.SEL_PRINT_O, v["is_print_o"])

        # 첨부파일
        _toggle_to(page, page.SEL_FILE_COUNT_TOGGLE, v["is_file_count"])
        page.page.locator(page.SEL_FILE_COUNT_VAL).fill(v["file_count"])

        # 확장자
        _toggle_to(page, page.SEL_EXT_FILTER, v["is_ext_filter"])

        # PDF 보호 (default ON 유지)
        _toggle_to(page, page.SEL_PDF_PROTECT, v["is_pdf_protect"])

        # 저장
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved = "저장" in msg or "등록" in msg
        self._add("pass" if is_saved else "fail",
                  "sc5a — lifecycle ADD 정상 저장 (전부 ON + 텍스트)",
                  f"입력: {NAME} + 풀세팅 / msg: {msg!r}", sc=5)
        if not is_saved:
            return

        # 재오픈 일치 검증
        page.navigate_to()
        page.page.wait_for_timeout(500)
        exists = page.is_policy_exists(NAME)
        self._add("pass" if exists else "fail",
                  "sc5a — lifecycle 정책 list 등록 확인",
                  f"입력: {NAME!r} / 결과: exists={exists}", sc=5)
        if not exists:
            return

        _enter_edit_modal(page, NAME)
        loaded = self._dump_dom(page)
        self._verify_loaded(page, loaded, v, scope="5a")
        _safe_close_modal(page)

    # ==================================================================
    # sc5b — lifecycle modify: 필수만 유지 + 모든 옵션 OFF + 재오픈 일치
    # ==================================================================
    def test_scenario5b_lifecycle_modify(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 5b: lifecycle modify (전부 OFF, 필수만) ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        # sc1 만 cleanup 호출 (사용자 보고 2026-06-02). sc5 는 호출 안 함.

        NAME = self.LIFECYCLE_NAME
        if not page.is_policy_exists(NAME):
            self._add("skip", "sc5b — 5a 정책 부재 (5a 미실행)",
                      f"입력: {NAME} / sc5a 먼저 실행 필요", sc=5)
            return

        _enter_edit_modal(page, NAME)
        if self._skip_if_missing(page, "sc5b lifecycle 수정(열람횟수 등)",
                                 [page.SEL_MAX_READ_COUNT_VAL], sc=5):
            _safe_close_modal(page); return

        # 종속 먼저 OFF → 메인 OFF (시나리오 기반 순서)
        # 비번 종속 (체크박스)
        _toggle_to(page, page.SEL_PW_NUMBER_LETTER, False)
        _toggle_to(page, page.SEL_PW_SPECIAL_LETTER, False)

        # 메인 토글 OFF
        _toggle_to(page, page.SEL_VALIDATE_SSL, False)
        _toggle_to(page, page.SEL_MAX_READ_COUNT_TOGGLE, False)
        _toggle_to(page, page.SEL_MAX_READ_DAY_TOGGLE, False)
        _toggle_to(page, page.SEL_PW_TOGGLE, False)
        _toggle_to(page, page.SEL_ORIGIN_PROTECT, False)
        _toggle_to(page, page.SEL_PRINT_OPTION, False)
        _toggle_to(page, page.SEL_FILE_COUNT_TOGGLE, False)
        _toggle_to(page, page.SEL_SERVER_AUTH, False)
        _toggle_to(page, page.SEL_EXT_FILTER, False)
        _toggle_to(page, page.SEL_PDF_PROTECT, False)

        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=3000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_saved = "저장" in msg or "등록" in msg
        self._add("pass" if is_saved else "fail",
                  "sc5b — lifecycle modify 저장 (전부 OFF, 필수만)",
                  f"변경: 메인 토글 다 OFF / 필수 (정책 이름) 유지 / msg: {msg!r}", sc=5)
        if not is_saved:
            return

        # 재오픈 일치 검증
        page.navigate_to()
        page.page.wait_for_timeout(500)
        _enter_edit_modal(page, NAME)
        loaded = self._dump_dom(page)
        self._verify_loaded(page, loaded, self.OFF_VALUES, scope="5b")
        _safe_close_modal(page)

    # ==================================================================
    # sc5c — lifecycle verify + cleanup: 5b 재오픈 + AUTO cleanup (KEEP 보존)
    # ==================================================================
    def test_scenario5c_lifecycle_verify_and_cleanup(self, logged_in_page, settings):
        print("\n━━ [엔파우치 정책] 시나리오 5c: lifecycle verify + cleanup ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        # sc1 만 cleanup 호출 (사용자 보고 2026-06-02). sc5 는 호출 안 함.

        NAME = self.LIFECYCLE_NAME
        keep_existed = page.is_policy_exists(NAME)
        # 1) 5b 상태 재오픈 일치 — KEEP 정책 있을 때만 (5a 미생성 시 verify 생략).
        #    단 cleanup(2)은 KEEP 유무 무관 항상 실행 — 테스트 데이터 정리 보장
        #    (sc5a 가 기능 미표시로 skip 돼도 [AUTO]_ 잔존 정리되도록).
        if keep_existed:
            _enter_edit_modal(page, NAME)
            loaded = self._dump_dom(page)
            self._verify_loaded(page, loaded, self.OFF_VALUES, scope="5c")
            _safe_close_modal(page)
        else:
            self._add("skip", "sc5c verify — 5a/5b 미생성(기능 미표시) → verify 생략, cleanup 은 진행", "", sc=5)

        # 2) cleanup — AUTO 만 정리, AUTO_KEEP 보존
        page.navigate_to()
        page.page.wait_for_timeout(500)
        before_names = page.get_policy_names()
        before_auto = [n for n in before_names if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")]
        before_keep = [n for n in before_names if n.startswith("[AUTO_KEEP]")]

        deleted = page.delete_all_auto_policies()

        page.navigate_to()
        page.page.wait_for_timeout(500)
        after_names = page.get_policy_names()
        after_auto = [n for n in after_names if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")]
        after_keep = [n for n in after_names if n.startswith("[AUTO_KEEP]")]

        auto_cleared = len(after_auto) == 0
        keep_preserved = (NAME in after_keep)

        self._add("pass" if auto_cleared else "fail",
                  "sc5c — cleanup: [AUTO]_ 정책 전부 삭제",
                  f"before AUTO: {len(before_auto)}건 / deleted={deleted} / after AUTO: {len(after_auto)}건",
                  sc=5)
        # KEEP 보존 검증은 KEEP 이 원래 있었을 때만 (5a 미생성 시 보존 대상 없음 → false-fail 방지)
        if keep_existed:
            self._add("pass" if keep_preserved else "fail",
                      "sc5c — cleanup: [AUTO_KEEP]_ 정책 보존 (sc6 / 다음 연계용)",
                      f"before KEEP: {before_keep} / after KEEP: {after_keep} / "
                      f"lifecycle 정책 {NAME} 보존 여부={keep_preserved}", sc=5)
        else:
            self._add("skip", "sc5c — KEEP 보존 검증 (KEEP 미생성으로 생략)",
                      "5a 가 기능 미표시로 skip → 생성된 KEEP 없음", sc=5)
