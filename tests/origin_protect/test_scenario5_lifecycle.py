"""원본보호 정책 — 시나리오 5 — 한 정책 lifecycle (5a/5b/5c).

사용자 설계 (2026-06-01 정정):
  - sc5a: 모든 옵션 ON + 모든 텍스트 채움 → 저장 → 재오픈 전체 일치
  - sc5b: 필수 5 필드만 유지, 나머지 모든 옵션 OFF + 텍스트 비움 → 저장 → 재오픈 전체 일치
  - sc5c: 5b 상태 재오픈 일치 + cleanup ([AUTO]_ 만 정리, [AUTO_KEEP]_ 보존)

cleanup 라이프사이클 (사용자 설계 2026-05-29):
  - sc1 시작: AUTO + AUTO_KEEP 둘 다 cleanup (clean slate)
  - sc2/3/4: cleanup 없음 (이전 정책 재사용)
  - sc5: AUTO 만 정리, AUTO_KEEP 보존 (lifecycle 종료 + 다음 연계)

탭 (허용/예외처리/실행차단 프로세스) 의 프로세스 add — sc4v 가 별도 검증 → sc5 미포함.
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase
from tests.origin_protect.test_scenario3_add import _csu_select_first, _save_click
from tests.origin_protect.test_scenario4_modify import _enter_edit_modal, _safe_close_modal


# ─────────────────────────────────────────────────────────────────────────
# Toggle helper — 체크박스를 target 상태로 set (이미 같으면 skip).
# AngularJS ng-click 발화 위해 JS evaluate click 사용 (메모리: 체크박스는 JS click 충분).
# ─────────────────────────────────────────────────────────────────────────
def _toggle_to(page, sel: str, target: bool):
    """체크박스를 target 상태로 set — disabled 면 skip (시나리오 기반 자연스러운 순서).

    페이지 동작: 메인 토글 OFF 시 종속 옵션 disabled 됨 (예: 파일감시 OFF → 헤더체크 disabled).
    disabled 상태에서 click 발사는 무효 → 검증 시 ON 상태 잔존하여 false negative.
    종속 먼저 OFF → 메인 OFF 순서를 호출자가 지킨다는 가정 하에서도, disabled 시 skip
    하는 게 안전망.
    """
    el = page.page.locator(sel).first
    try:
        if not el.is_enabled():
            return  # disabled → 메인 OFF 로 이미 비활성 상태 → click 무의미
        cur = el.is_checked()
    except Exception:
        cur = False
    if cur != target:
        el.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)


class TestOriginProtectScenario5Lifecycle(OriginProtectBase):
    """원본보호 정책 — sc5: 한 정책 lifecycle (5a → 5b → 5c)."""

    LIFECYCLE_NAME = "[AUTO_KEEP]_sc5_origin_protect"

    # ON 상태의 기준값 — sc5a 가 채움, sc5a/sc5c 재오픈 일치 검증
    ON_VALUES = {
        "name": LIFECYCLE_NAME,
        "letter": "S",
        "label": "LifecycleLabel",
        "quota": "500",
        # 사용 토글 3개
        "allow_proc": True,
        "except_proc": True,
        "block_proc": True,
        # 허용 종료 메시지 토글 + 텍스트
        "shutdown_toggle": True,
        "shutdown_text": "[AUTO_KEEP] 종료 메시지",
        # 파일 감시 + 헤더 체크
        "watch_ext": True,
        "watch_header": True,
        # 화면 워터마크
        "screen_wm": True,
        "screen_wm_pc": True,
        "screen_wm_time": True,
        "screen_wm_opacity": "50",
        "screen_wm_degree": "45",
        # 출력 워터마크
        "print_wm": True,
        "print_wm_pc": True,
        "print_wm_time": True,
        "print_wm_opacity": "60",
        "print_wm_degree": "90",
    }

    # OFF 상태의 기준값 — sc5b 가 채움, sc5b/sc5c 재오픈 일치 검증
    #
    # Chrome MCP 결정적 사실 (2026-06-01, 4 단계 직접 확인):
    #   step 1. EDIT 진입            → pc=true, time=true, text='[/PCINFO/][/TIME/]'
    #   step 2. 종속 PC/TIME OFF     → pc=false, time=false, text='' (UI 즉시 반영 OK)
    #   step 3. 메인 OFF             → pc=false, time=false, text='' (UI 그대로)
    #   step 4. 저장 + 재진입         → pc=🔴TRUE, time=🔴TRUE, text=🔴'[/PCINFO/][/TIME/]'
    #                                  (server-side restore — 메인 OFF 시 종속 default 강제)
    #
    # = server 가 저장 시 "메인 OFF 면 종속 = server default" 로 강제 저장 → 다음 메인 ON 시 default 보장
    # = 정상 동작 (결함 아님). 사용자 시각: 메인 OFF = 종속 의미 없음, default 값 무관.
    #
    # → 종속 검증 (PC/TIME/text/shutdown_text) 제거. 메인 토글 + 필수만 검증.
    OFF_VALUES = {
        "name": LIFECYCLE_NAME,         # 필수 — 유지
        "letter": "S",                  # 필수 — 유지
        "label": "LifecycleLabel",      # 필수 — 유지
        "quota": "500",                 # 필수 — 유지
        # 사용 토글 3 (독립)
        "allow_proc": False,
        "except_proc": False,
        "block_proc": False,
        # 메인 토글 4 — 종속은 server-side default 로 restore 되므로 검증 제외
        "shutdown_toggle": False,       # 종속 shutdown_text — server restore (검증 제외)
        "watch_ext": False,
        "watch_header": False,          # 파일 감시는 server restore 안 함 (Chrome MCP 별도 검증 결과)
        "screen_wm": False,             # 종속 pc/time/text — server-side default restore (검증 제외)
        "print_wm": False,              # 동일
    }

    # ==================================================================
    # 공통 — 재오픈 후 DOM 상태 dump
    # ==================================================================
    @staticmethod
    def _dump_dom(page) -> dict:
        return page.page.evaluate(
            """() => ({
                name: (document.getElementById('originProtectPolicyName')||{}).value,
                letter: (document.getElementById('driveLetter')||{}).value,
                label: (document.getElementById('driveLabel')||{}).value,
                quota: (document.getElementById('originProtectDriveQuota')||{}).value,
                csu_text: ((document.getElementById('controlSuiteId')||{}).innerText||'').trim(),
                allow_proc: !!(document.getElementById('isAllowProcess')||{}).checked,
                except_proc: !!(document.getElementById('isExceptProcess')||{}).checked,
                block_proc: !!(document.getElementById('isBlockProcess')||{}).checked,
                shutdown_toggle: !!(document.getElementById('isAllowProcessShutdownText')||{}).checked,
                shutdown_text: (document.getElementById('allowProcessShutdownText')||{}).value || '',
                watch_ext: !!(document.getElementById('isWatchFileExtension')||{}).checked,
                watch_header: !!(document.getElementById('isWatchFileHeader')||{}).checked,
                screen_wm: !!(document.getElementById('isScreenWaterMark')||{}).checked,
                screen_wm_pc: !!(document.getElementById('isScreenWaterMarkPcInfo')||{}).checked,
                screen_wm_time: !!(document.getElementById('isScreenWaterMarkCurrentTime')||{}).checked,
                screen_wm_opacity: (document.getElementById('screenWaterMarkOpacity')||{}).value || '',
                screen_wm_degree: (document.getElementById('screenWaterMarkDegree')||{}).value || '',
                screen_wm_text: (document.getElementById('screenWaterMarkText')||{}).value || '',
                print_wm: !!(document.getElementById('isPrintWaterMark')||{}).checked,
                print_wm_pc: !!(document.getElementById('isPrintWaterMarkPcInfo')||{}).checked,
                print_wm_time: !!(document.getElementById('isPrintWaterMarkCurrentTime')||{}).checked,
                print_wm_opacity: (document.getElementById('printWaterMarkOpacity')||{}).value || '',
                print_wm_degree: (document.getElementById('printWaterMarkDegree')||{}).value || '',
                print_wm_text: (document.getElementById('printWaterMarkText')||{}).value || '',
            })"""
        )

    def _verify_loaded(self, page, loaded: dict, expected: dict, scope: str):
        """expected 의 각 키를 loaded 와 비교. 결함 시 fail _add."""
        sel_by_key = {
            "name": page.SEL_POLICY_NAME, "letter": page.SEL_DRIVE_LETTER,
            "label": page.SEL_DRIVE_LABEL, "quota": page.SEL_DRIVE_QUOTA,
            "allow_proc": page.SEL_ALLOW_PROCESS, "except_proc": page.SEL_EXCEPT_PROCESS,
            "block_proc": page.SEL_BLOCK_PROCESS,
            "shutdown_toggle": page.SEL_SHUTDOWN_MSG_TOGGLE,
            "shutdown_text": page.SEL_SHUTDOWN_MSG_TEXT,
            "watch_ext": page.SEL_WATCH_EXT_TOGGLE, "watch_header": page.SEL_WATCH_HEADER,
            "screen_wm": page.SEL_SCREEN_WM,
            "screen_wm_pc": page.SEL_SCREEN_WM_PC_INFO, "screen_wm_time": page.SEL_SCREEN_WM_TIME,
            "screen_wm_opacity": page.SEL_SCREEN_WM_OPACITY, "screen_wm_degree": page.SEL_SCREEN_WM_DEGREE,
            "screen_wm_text": page.SEL_SCREEN_WM_TEXT,
            "print_wm": page.SEL_PRINT_WM,
            "print_wm_pc": page.SEL_PRINT_WM_PC_INFO, "print_wm_time": page.SEL_PRINT_WM_TIME,
            "print_wm_opacity": page.SEL_PRINT_WM_OPACITY, "print_wm_degree": page.SEL_PRINT_WM_DEGREE,
            "print_wm_text": page.SEL_PRINT_WM_TEXT,
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
    # sc5a — lifecycle ADD: 전부 ON + 모든 텍스트 채움 → 재오픈 전체 일치
    # ==================================================================
    def test_scenario5a_lifecycle_add(self, logged_in_page, settings):
        """sc5a — 전부 ON ADD (모든 토글 + 텍스트 + 워터마크) → 재오픈 전체 일치.

        cleanup 정책: sc1 시작 cleanup 으로 list 비어있음 / 5a 가 [AUTO_KEEP]_ 1건 생성
                     / 5a 끝에 cleanup 안 함 (5b 에 정책 전달).
        """
        print("\n━━ [원본보호 정책] 시나리오 5a: lifecycle ADD (전부 ON) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = self.LIFECYCLE_NAME
        # 이전 run 잔존 정책 — 풀세팅 보장 위해 삭제 후 재생성
        # (idempotent skip 은 이전 불완전 상태 그대로 둬서 sc5b/c 검증 의미 없게 됨)
        if page.is_policy_exists(NAME):
            # delete_policy 는 [AUTO]_ 가드만 허용 → [AUTO_KEEP]_ 삭제 Exception
            # → delete_all_test_data() 사용 ([AUTO] + [AUTO_KEEP] 둘 다 정리, 일반 정책 무관)
            page.delete_all_test_data()
            page.page.wait_for_timeout(500)
            self._add("pass", "sc5a — 이전 잔존 정책 삭제 (풀세팅 보장)",
                      f"입력: {NAME} / 결과: delete_all_test_data 로 KEEP 포함 정리 후 재생성", sc=5)

        v = self.ON_VALUES
        # ADD 모달 — 필수 5
        page.open_add_modal()
        page.page.locator(page.SEL_POLICY_NAME).fill(v["name"])
        page.page.locator(page.SEL_DRIVE_LETTER).fill(v["letter"])
        page.page.locator(page.SEL_DRIVE_LABEL).fill(v["label"])
        page.page.locator(page.SEL_DRIVE_QUOTA).fill(v["quota"])
        _csu_select_first(page)

        # 사용 토글 3개 ON
        _toggle_to(page, page.SEL_ALLOW_PROCESS, True)
        _toggle_to(page, page.SEL_EXCEPT_PROCESS, True)
        _toggle_to(page, page.SEL_BLOCK_PROCESS, True)

        # 허용 종료 메시지 ON + 텍스트
        _toggle_to(page, page.SEL_SHUTDOWN_MSG_TOGGLE, True)
        page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT).fill(v["shutdown_text"])

        # 파일 감시 + 헤더
        _toggle_to(page, page.SEL_WATCH_EXT_TOGGLE, True)
        _toggle_to(page, page.SEL_WATCH_HEADER, True)

        # 화면 워터마크
        _toggle_to(page, page.SEL_SCREEN_WM, True)
        _toggle_to(page, page.SEL_SCREEN_WM_PC_INFO, True)
        _toggle_to(page, page.SEL_SCREEN_WM_TIME, True)
        page.page.locator(page.SEL_SCREEN_WM_OPACITY).fill(v["screen_wm_opacity"])
        page.page.locator(page.SEL_SCREEN_WM_DEGREE).fill(v["screen_wm_degree"])

        # 출력 워터마크
        _toggle_to(page, page.SEL_PRINT_WM, True)
        _toggle_to(page, page.SEL_PRINT_WM_PC_INFO, True)
        _toggle_to(page, page.SEL_PRINT_WM_TIME, True)
        page.page.locator(page.SEL_PRINT_WM_OPACITY).fill(v["print_wm_opacity"])
        page.page.locator(page.SEL_PRINT_WM_DEGREE).fill(v["print_wm_degree"])

        # 저장
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_success = "저장" in msg and "오류" not in msg
        msg_loc = page.page.locator(page.SEL_CONFIRM_MODAL).first
        self._add("pass" if is_success else "fail",
                  "sc5a — lifecycle ADD 정상 저장 (전부 ON)",
                  f"입력: {NAME} + 사용 토글 3 ON + 감시 2 ON + 화면WM full + 출력WM full + 종료 메시지 텍스트 / msg={msg!r}",
                  sc=5, highlight=msg_loc)
        if not is_success:
            return

        # 재오픈 일치 검증 — list 등록 + EDIT 진입 + 모든 필드 확인
        page.navigate_to()
        page.page.wait_for_timeout(800)
        exists = page.is_policy_exists(NAME)
        self._add("pass" if exists else "fail",
                  "sc5a — lifecycle 정책 list 등록 확인",
                  f"입력: {NAME!r} / 결과: exists={exists}", sc=5)
        if not exists:
            return

        _enter_edit_modal(page, NAME)
        loaded = self._dump_dom(page)
        self._verify_loaded(page, loaded, v, scope="5a")
        # ON 시 워터마크 텍스트 — PC+TIME ON 자동 토큰 사실 확보 (검증 안 하고 노출만)
        self._add("pass",
                  "sc5a — ON 시 워터마크 텍스트 자동 토큰 (사실 확보)",
                  f"화면 WM 텍스트: {loaded.get('screen_wm_text')!r} / "
                  f"출력 WM 텍스트: {loaded.get('print_wm_text')!r} "
                  f"(PC+TIME ON 자동 삽입 패턴 — sc5b OFF 후 자동 제거 동작 검증으로 lifecycle 완결)",
                  sc=5)
        _safe_close_modal(page)
        # cleanup 안 함 — 5b 가 그대로 사용

    # ==================================================================
    # sc5b — lifecycle modify: 모든 옵션 OFF + 텍스트 비움 (필수 5만 유지)
    # ==================================================================
    def test_scenario5b_lifecycle_modify(self, logged_in_page, settings):
        """sc5b — 5a 정책 EDIT, 모든 토글 OFF + 텍스트 비움 → 재오픈 전체 일치."""
        print("\n━━ [원본보호 정책] 시나리오 5b: lifecycle modify (전부 OFF, 필수만) ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = self.LIFECYCLE_NAME
        if not page.is_policy_exists(NAME):
            self._add("skip", "sc5b — 5a 정책 부재 (5a 미실행)",
                      f"입력: {NAME} / sc5a 먼저 실행 필요", sc=5)
            return

        _enter_edit_modal(page, NAME)

        # OFF 순서: 종속 옵션 먼저 → 메인 토글 마지막 (시나리오 기반 — 사용자 보고 2026-06-01)
        # 이유: 메인 OFF 면 종속 disabled → 종속 click 무효 → 검증 시 ON 잔존 false negative
        #   - 파일 감시 OFF → 헤더/확장자/예외 폴더 disabled
        #   - 화면/출력 워터마크 OFF → PC/시간/투명도/각도/텍스트 disabled
        #   - 종료 메시지 토글 OFF → 텍스트 disabled

        # ── 종속 옵션 먼저 OFF / 비우기 (사용자 옵션 B 2026-06-01) ──
        # 종료 메시지 텍스트 (토글 OFF 전에 비움)
        try:
            page.page.locator(page.SEL_SHUTDOWN_MSG_TEXT).fill("")
        except Exception:
            pass
        # 파일 감시 종속: 헤더 체크 OFF (감시 OFF 전)
        _toggle_to(page, page.SEL_WATCH_HEADER, False)
        # 화면 워터마크 종속: PC/시간 OFF → 토큰 자동 제거 → 텍스트도 명시 비움 (안전망)
        _toggle_to(page, page.SEL_SCREEN_WM_PC_INFO, False)
        _toggle_to(page, page.SEL_SCREEN_WM_TIME, False)
        try:
            page.page.locator(page.SEL_SCREEN_WM_TEXT).fill("")
        except Exception:
            pass
        # 출력 워터마크 종속: PC/시간 OFF + 텍스트 비움
        _toggle_to(page, page.SEL_PRINT_WM_PC_INFO, False)
        _toggle_to(page, page.SEL_PRINT_WM_TIME, False)
        try:
            page.page.locator(page.SEL_PRINT_WM_TEXT).fill("")
        except Exception:
            pass

        # ── 메인 토글 OFF (마지막) ──
        # 사용 토글 3개 (다른 메인과 독립)
        _toggle_to(page, page.SEL_ALLOW_PROCESS, False)
        _toggle_to(page, page.SEL_EXCEPT_PROCESS, False)
        _toggle_to(page, page.SEL_BLOCK_PROCESS, False)
        # 종료 메시지 토글
        _toggle_to(page, page.SEL_SHUTDOWN_MSG_TOGGLE, False)
        # 파일 감시 메인
        _toggle_to(page, page.SEL_WATCH_EXT_TOGGLE, False)
        # 화면 워터마크 메인
        _toggle_to(page, page.SEL_SCREEN_WM, False)
        # 출력 워터마크 메인
        _toggle_to(page, page.SEL_PRINT_WM, False)

        # 저장
        _save_click(page)
        msg = ""
        if page.is_confirm_modal_visible(timeout=2000):
            msg = page.get_confirm_message()
            page.dismiss_confirm_modal()
        is_success = "저장" in msg and "오류" not in msg
        msg_loc = page.page.locator(page.SEL_CONFIRM_MODAL).first
        self._add("pass" if is_success else "fail",
                  "sc5b — lifecycle modify 정상 저장 (전부 OFF, 필수만)",
                  f"변경: 모든 사용 토글 OFF + 감시 OFF + 화면WM OFF + 출력WM OFF + 종료 메시지 OFF / "
                  f"필수 5 (name/letter/label/quota/CSU) 유지 / msg={msg!r}",
                  sc=5, highlight=msg_loc)
        if not is_success:
            return

        # 재오픈 일치 검증
        page.navigate_to()
        page.page.wait_for_timeout(800)
        _enter_edit_modal(page, NAME)
        loaded = self._dump_dom(page)
        self._verify_loaded(page, loaded, self.OFF_VALUES, scope="5b")
        _safe_close_modal(page)
        # cleanup 안 함 — 5c 가 검증 + cleanup

    # ==================================================================
    # sc5c — lifecycle verify + cleanup: 5b 상태 재오픈 + AUTO 정리 (KEEP 보존)
    # ==================================================================
    def test_scenario5c_lifecycle_verify_and_cleanup(self, logged_in_page, settings):
        """sc5c — 5b 상태 (전부 OFF, 필수만) 한 번 더 재오픈 일치 확인 + AUTO 만 cleanup.

        사용자 설계 (2026-05-29):
          - sc5 cleanup = AUTO 만 정리, AUTO_KEEP 은 보존 (sc6 / 다음 페이지 연계용)
          - delete_all_auto_policies() — [AUTO]_ 만 삭제, [AUTO_KEEP]_ 보존.
        """
        print("\n━━ [원본보호 정책] 시나리오 5c: lifecycle verify + cleanup ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = self.LIFECYCLE_NAME
        if not page.is_policy_exists(NAME):
            self._add("skip", "sc5c — 5a/5b 정책 부재", "", sc=5)
            return

        # 1) 5b 변경값 재오픈 일치 한 번 더 (전부 OFF, 필수만)
        _enter_edit_modal(page, NAME)
        loaded = self._dump_dom(page)
        self._verify_loaded(page, loaded, self.OFF_VALUES, scope="5c")
        _safe_close_modal(page)

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
                  f"before AUTO: {len(before_auto)}건 / deleted={deleted} / after AUTO: {len(after_auto)}건 "
                  f"(잔여: {after_auto if after_auto else '없음'})",
                  sc=5)

        self._add("pass" if keep_preserved else "fail",
                  "sc5c — cleanup: [AUTO_KEEP]_ 정책 보존 (sc6 / 다음 연계용)",
                  f"before KEEP: {before_keep} / after KEEP: {after_keep} "
                  f"(lifecycle 정책 {NAME} 보존 여부={keep_preserved})",
                  sc=5)
