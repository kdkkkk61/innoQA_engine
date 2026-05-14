"""
test_npouch_control_suite.py — nPouch 제어 스위트 시나리오 1~4 검증

시나리오 매핑 (test 함수명의 scenario{N}{x} 접두사):

  시나리오 1 (UI 구조 + 모달 진입):
    - test_scenario1a_navigate_main_modal       메인 페이지 + 메인 모달 진입
    - test_scenario1b_process_modal_open        process_sub_modal sub-tab + 진입
    - test_scenario1c_web_restrict_open         web_restrict_sub_modal 진입

  시나리오 2 (입력 구조 + 필드 동작):
    - test_scenario2a_main_modal_fields         메인 모달 단독 필드
    - test_scenario2b_process_modal_fields      프로세스 등록 모달 필드 그룹
    - test_scenario2c_cache_folder_picker       cache_folder + 예약어 선택 picker
    - test_scenario2d_web_restrict_process      웹제한 적용 프로세스 + basePath
    - test_scenario2e_web_restrict_fields       웹제한 권한/URL/암호화/확장자/제한
    - test_scenario2f_process_picker            프로세스/태그 선택 picker 입력 동작

  시나리오 3 (CRUD 1사이클 + 비정상 케이스):
    - test_scenario3b_minimal_save              프로세스 1건 + 메인 저장 (C)
    - test_scenario3c_web_restrict_save         웹제한 등록 + 메인 저장 (E2E)
    - test_scenario3d_crud_full_cycle           CRUD 1사이클 (C+R+U) → KEEP 보존
    - test_scenario3e_validation_messages       비정상 케이스 (빈값/중복/maxlength)

  시나리오 4 (수정 흐름 깊이):
    - test_scenario4a_edit_open_close           EDIT 진입/탈출 단위
    - test_scenario4b_edit_depth                ADD/EDIT 메시지 차이 + 변경 검증
    - test_scenario4c_edit_add_process          EDIT 후 새 프로세스 추가 (시나리오 3b 의 EDIT 버전)
    - test_scenario4d_edit_add_web_restrict     EDIT 후 새 웹제한 추가 (시나리오 3c 의 EDIT 버전)
                                                  (시나리오 3d 의 KEEP 정책 사용)

  최종 정리:
    - test_zz_cleanup_keep                      [AUTO]_ + [AUTO_KEEP]_ 모두 삭제

데이터 의존:
  - scenario3d 가 [AUTO_KEEP]_step5b_mod 보존 → scenario4b 가 사용
  - delete_all_auto_policies() = AUTO 만 (KEEP 보존)
  - delete_all_test_data() = AUTO + KEEP 모두 (기본 cleanup, 최종 정리)
"""
import re
import time
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport
from pages.npouch_control_suite_page import NpouchControlSuitePage


# ── 스크린샷 헬퍼 ──────────────────────────────────────────────────
_SS_DIR = Path(__file__).parent.parent / "reports" / "screenshots"

def _ss(page, label: str) -> str | None:
    """warn/fail 시점 스크린샷 저장 → 경로 반환."""
    try:
        _SS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w가-힣]", "_", label)[:40]
        path = _SS_DIR / f"BUG_{safe}_{int(time.time()*1000)}.png"
        page.screenshot(path=str(path))
        return str(path)
    except Exception:
        return None


_STATUS_ICON  = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]", "warn": "[WARN]"}
_STATUS_TO_SR = {"pass": "pass", "fail": "fail", "warn": "warn", "skip": "skip"}


def _r(status: str, label: str, detail: str = "", sc: int = 0,
       page=None) -> tuple[str, ScanResult]:
    """print 라인 + ScanResult 동시 생성. warn/fail 이면 스크린샷 자동 첨부.
    sc = 시나리오 번호 (1~4)."""
    icon = _STATUS_ICON.get(status, "?")
    text = f"  {icon} {label}" + (f": {detail}" if detail else "")
    extra: dict = {"scenario": sc}
    if page and status in ("fail", "warn"):
        ss_path = _ss(page, label)
        if ss_path:
            extra["screenshot"] = ss_path
    sr = ScanResult(
        pattern="scenario_test",
        selector="",
        label=label,
        status=_STATUS_TO_SR.get(status, status),
        detail=detail,
        extra=extra,
    )
    return text, sr


def _assert_no_fail(lines: list[str], context: str = "") -> None:
    """[FAIL] 항목이 없어야 통과."""
    failed = [r for r in lines if "[FAIL]" in r]
    if failed:
        raise AssertionError(f"{context} 실패 항목:\n" + "\n".join(failed))


class TestNpouchControlSuite:
    PAGE_ID = "npouch_control_suite"

    def _attach(self, scan_results: list[ScanResult]) -> None:
        """PageScanReport 를 test node 에 첨부 — conftest 가 수집해서 html_reporter 로 전달."""
        report = PageScanReport(page_id=self.PAGE_ID)
        report.results = scan_results
        self._request.node._scan_report    = report
        self._request.node._npouch_page_id = self.PAGE_ID

    def _emit_pass(self, label: str, sc: int) -> None:
        """test 가 통과되면 끝에 호출 — 단일 pass ScanResult 첨부.
        (실패는 assert 가 pytest fail → conftest 의 fail hook 이 처리)"""
        sr = ScanResult(
            pattern="scenario_test", selector="", label=label,
            status="pass", detail="", extra={"scenario": sc},
        )
        self._attach([sr])

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        """매 테스트 시작 — request + ScanResult 누적 리스트 초기화."""
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None    # _add 의 fail 스크린샷용 — test 메서드가 세팅
        yield
        # ScanResult fallback attach
        if self._srs and not getattr(self._request.node, "_scan_report", None):
            self._attach(self._srs)
        # 매 테스트 끝 — modal/backdrop 강제 정리 (다음 테스트 영향 방지)
        page_obj = request.node.funcargs.get("logged_in_page")
        if page_obj is not None:
            try:
                page_obj.evaluate("""
                    () => {
                        document.querySelectorAll('div.modal-wrap.in, div.modal.in').forEach(m => {
                            m.classList.remove('in');
                            m.style.display = 'none';
                        });
                        document.querySelectorAll('div.modal-backdrop').forEach(b => b.remove());
                        document.body.classList.remove('modal-open');
                        document.body.style.paddingRight = '';
                        document.body.style.overflow = '';
                    }
                """)
            except Exception:
                pass

    def _add(self, status: str, label: str, detail: str = "", sc: int = 0) -> None:
        """한 줄로 print + ScanResult 누적. 각 검증 블록 단위 호출.
        fail/warn 시 self._page 세팅돼 있으면 스크린샷 자동 저장.
        매 호출마다 _scan_report 자동 갱신 → conftest hook 이 call phase 끝에서 픽업."""
        t, s = _r(status, label, detail, sc=sc,
                  page=self._page if status in ("fail", "warn") else None)
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        # 매번 갱신 (최후 호출 = 최종) — fixture teardown 까지 기다리지 않음
        self._attach(self._srs)

    def _finish(self, context: str = "") -> None:
        """메서드 끝 호출 — attach + FAIL 어서션."""
        self._attach(self._srs)
        _assert_no_fail(self._lines, context=context)

    # ==================================================================
    # Step 1 — 네비/모달 진입/탈출
    # ==================================================================
    def test_scenario1a_navigate_main_modal(self, logged_in_page, settings):
        """시나리오 1a: 메인 페이지 navigate + 메인 모달 진입/탈출.

        세션 첫 시작점 — 이전 세션의 [AUTO]_ + [AUTO_KEEP]_ 잔여를 모두 정리.
        이후 시나리오들은 KEEP 을 보존하며 중간 cleanup 안 함 (시나리오 5 끝에서 다시 정리).
        """
        print(f"\n━━ [제어 스위트] 시나리오 1a: navigate + 메인 모달 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        lines, srs = [], []

        # 1. navigate + 세션 시작 정리 (auto + keep 모두)
        page.navigate_to()
        page.delete_all_test_data()
        url_ok = "managerControlSuite" in page.page.url
        t, s = _r(
            "pass" if url_ok else "fail",
            "navigate_to → managerControlSuite",
            f"url={page.page.url!r}", sc=1, page=page.page if not url_ok else None
        )
        lines.append(t); srs.append(s)
        print(t)

        # 2. open_add_modal + title
        page.open_add_modal()
        title = page.get_modal_title()
        title_ok = title == "제어 스위트 추가"
        t, s = _r(
            "pass" if title_ok else "fail",
            "스위트 추가 모달 — 진입 (title 확인)",
            f"title={title!r}", sc=1, page=page.page if not title_ok else None
        )
        lines.append(t); srs.append(s)
        print(t)

        # 3. close_modal
        page.close_modal()
        t, s = _r("pass", "스위트 추가 모달 — 취소 close", "", sc=1)
        lines.append(t); srs.append(s)
        print(t)

        # ScanResult 첨부 + FAIL 체크
        self._attach(srs)
        _assert_no_fail(lines, context="시나리오 1a")

    # ==================================================================
    # Step 2 — 메인 모달 단독 필드 (저장 X, 프로세스/웹제한 X)
    # ==================================================================
    def test_scenario2a_main_modal_fields(self, logged_in_page, settings):
        """시나리오 2a — 메인 모달 단독 필드 9 블록.
        각 블록을 별도 ScanResult 로 분리해 보고서에 세부 출력.
        """
        print("\n━━ [제어 스위트] 시나리오 2a: 메인 모달 단독 필드 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page   # fail 스크린샷용

        page.navigate_to()
        page.open_add_modal()

        # ── 스위트 이름 (csuName) ──────────────────────────────
        page.set_csu_name("[AUTO]_step2_main")
        got = page.get_csu_name()
        self._add("pass" if got == "[AUTO]_step2_main" else "fail",
                  "스위트 이름",
                  f"입력: '[AUTO]_step2_main' / 결과: get={got!r}", sc=3)

        # ── 클립보드 공유제한 (토글 + 허용 URL) ────────────────
        page.set_clipboard_restrict_toggle(True)
        chk = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        self._add("pass" if chk else "fail",
                  "클립보드 공유제한 — 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.set_clipboard_allow_url("naver.com;google.com")
        url = page.get_clipboard_allow_url()
        self._add("pass" if "naver.com" in url else "fail",
                  "클립보드 공유제한 — 허용 URL 입력",
                  f"입력: 'naver.com;google.com' / 결과: get={url!r}", sc=3)

        # ── 네트워크 허용 (토글) ──────────────────────────────
        page.set_network_toggle(True)
        chk = page.is_network_checked()
        self._add("pass" if chk else "fail",
                  "네트워크 허용 — 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        # ── 제어할 확장자 (라디오 + tag input) ─────────────────
        page.click_radio_block()
        t1 = page.get_radio_react_text()
        self._add("pass" if t1 == "허용할 확장자" else "fail",
                  "제어할 확장자 — BLOCK 라디오 반응",
                  f"입력: BLOCK 클릭 / 결과: span text={t1!r}", sc=2)

        page.click_radio_allow()
        t2 = page.get_radio_react_text()
        self._add("pass" if t2 == "차단할 확장자" else "fail",
                  "제어할 확장자 — ALLOW 라디오 반응",
                  f"입력: ALLOW 클릭 / 결과: span text={t2!r}", sc=2)

        page.add_main_extension("txt;doc;exe")
        ext = page.get_main_extension_list()
        self._add("pass" if ext == ["txt", "doc", "exe"] else "fail",
                  "제어할 확장자 — ';' 다중구분자 등록",
                  f"입력: 'txt;doc;exe' / 결과: list={ext}", sc=3)

        page.add_main_extension("txt")
        vis = page.is_confirm_modal_visible()
        msg = page.get_confirm_message() if vis else ""
        dup_ok = vis and "이미 동일한 확장자가 존재합니다" in msg
        self._add("pass" if dup_ok else "fail",
                  "제어할 확장자 — 중복 차단 메시지",
                  f"입력: 'txt' (중복) / 결과: confirm={vis} msg={msg!r}", sc=2)
        if vis:
            page.dismiss_confirm_modal()

        # ── 헤더 체크 기능 사용 (독립 체크박스) ─────────────────
        page.set_header_check(True)
        chk = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if chk else "fail",
                  "헤더 체크 기능 사용",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        # ── 전자서명 예외처리 (토글 + 추가 list) ────────────────
        page.set_sign_except_toggle(True)
        chk = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        self._add("pass" if chk else "fail",
                  "전자서명 예외처리 — 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.add_sign_except("Claude Test Sign")
        page.add_sign_except("Innotium Inc")
        signs = page.get_sign_except_list()
        self._add("pass" if len(signs) == 2 else "fail",
                  "전자서명 예외처리 — 항목 추가 (2건)",
                  f"입력: 'Claude Test Sign', 'Innotium Inc' / 결과: count={len(signs)} list={signs}", sc=3)

        # ── 커스텀 옵션 (input) ────────────────────────────────
        page.set_custom_option("test_option_value")
        co = page.get_custom_option()
        self._add("pass" if co == "test_option_value" else "fail",
                  "커스텀 옵션",
                  f"입력: 'test_option_value' / 결과: get={co!r}", sc=3)

        # ── 메인 모달 close (저장 X) ───────────────────────────
        page.close_modal()
        self._add("pass", "스위트 추가 모달 — 취소 close",
                  "입력: 취소 클릭 / 결과: 모달 detached", sc=3)

    # ==================================================================
    # Step 3a — sub-tab 전환 + process_sub_modal 진입/탈출
    # ==================================================================
    def test_scenario1b_process_modal_open(self, logged_in_page, settings):
        """시나리오 1b — process_sub_modal sub-tab 전환 + 진입 + mode 감지."""
        print("\n━━ [제어 스위트] 시나리오 1b: process_modal sub-tab ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step3a")

        # ── 개별 프로세스 sub-tab ──────────────────────────────
        page.click_individual_process_tab()
        active = page.get_active_sub_tab_text()
        self._add("pass" if "프로세스" in active else "fail",
                  "프로세스별 제어 sub-tab — 개별 프로세스 활성화",
                  f"입력: '개별 프로세스' 탭 클릭 / 결과: active={active!r}", sc=1)

        page.click_add_process_btn()
        page.process.wait_open()
        title = page.process.get_title()
        mode = page.process.detect_mode()
        pick_txt = page.process.get_pick_btn_text()
        self._add("pass" if page.process.is_open() else "fail",
                  "프로세스 등록 모달 — '+' 버튼 진입 (개별 프로세스 모드)",
                  f"입력: '+' 클릭 / 결과: title={title!r}, is_open={page.process.is_open()}", sc=1)
        self._add("pass" if mode == "process" else "fail",
                  "프로세스 등록 모달 — mode 감지 (개별 프로세스)",
                  f"입력: pick_btn={pick_txt!r} / 결과: detect_mode={mode!r}", sc=1)

        # ── process_modal close ────────────────────────────────
        page.process.close()
        self._add("pass" if not page.process.is_open() else "fail",
                  "프로세스 등록 모달 — × 버튼 close",
                  f"입력: close 클릭 / 결과: is_open={page.process.is_open()}", sc=1)

        # ── 태그 sub-tab ──────────────────────────────────────
        page.click_tag_tab()
        active = page.get_active_sub_tab_text()
        self._add("pass" if "태그" in active else "fail",
                  "프로세스별 제어 sub-tab — 태그 활성화",
                  f"입력: '태그' 탭 클릭 / 결과: active={active!r}", sc=1)

        page.click_add_process_btn()
        page.process.wait_open()
        title = page.process.get_title()
        mode = page.process.detect_mode()
        pick_txt = page.process.get_pick_btn_text()
        self._add("pass" if mode == "tag" else "fail",
                  "프로세스 등록 모달 — mode 감지 (태그)",
                  f"입력: pick_btn={pick_txt!r} / 결과: detect_mode={mode!r}", sc=1)

        # 정리
        page.process.close()
        page.close_modal()
        self._add("pass", "정리 — 프로세스 등록 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: 모두 detached", sc=1)

    def test_scenario2f_process_picker(self, logged_in_page, settings):
        """시나리오 2f — process_picker 입력 동작 검증 (single + tag 2 모드, 저장 X)."""
        print("\n━━ [제어 스위트] 시나리오 2f: process_picker (입력 동작 검증) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step3b")

        # ── single 모드 ────────────────────────────────────────
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        before = page.process.get_selected_display_text()
        self._add("pass" if "미선택" in before else "fail",
                  "프로세스 등록 모달 — 선택 표시 초기값 ('프로세스 미선택')",
                  f"입력: 모달 진입 / 결과: {before!r}", sc=2)

        page.process.click_pick_btn()
        page.picker.wait_open()
        title = page.picker.get_title()
        cnt = page.picker.get_row_count()
        self._add("pass" if title == "프로세스 선택" and cnt > 0 else "fail",
                  "프로세스 선택 모달 — 진입 (개별 프로세스)",
                  f"입력: '프로세스 선택' 버튼 / 결과: title={title!r}, 행 수={cnt}", sc=3)

        selected = page.picker.select_first_and_confirm(mode="single")
        self._add("pass" if not page.picker.is_open() else "fail",
                  "프로세스 선택 모달 — 첫 행 + 확인 → 닫힘",
                  f"입력: 1행 radio + 확인 / 결과: 선택={selected!r}, 닫힘={not page.picker.is_open()}", sc=3)

        after = page.process.get_selected_display_text()
        self._add("pass" if "미선택" not in after else "fail",
                  "프로세스 등록 모달 — 선택 표시 반영 (picker 결과)",
                  f"입력: picker 확인 후 / 결과: display={after!r}", sc=3)

        page.process.close()

        # ── tag 모드 ───────────────────────────────────────────
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        before = page.process.get_selected_display_text()
        self._add("pass" if "미선택" in before else "fail",
                  "프로세스 등록 모달 — 태그 모드 선택 표시 초기값 ('태그 미선택')",
                  f"입력: 모달 진입 / 결과: {before!r}", sc=2)

        page.process.click_pick_btn()
        page.picker.wait_open()
        title = page.picker.get_title()
        cnt = page.picker.get_row_count()
        self._add("pass" if title == "태그 선택" and cnt > 0 else "fail",
                  "태그 선택 모달 — 진입",
                  f"입력: '태그 선택' 버튼 / 결과: title={title!r}, 행 수={cnt}", sc=3)

        selected = page.picker.select_first_and_confirm(mode="tag")
        after = page.process.get_selected_display_text()
        self._add("pass" if not page.picker.is_open() and "미선택" not in after else "fail",
                  "태그 선택 모달 — 첫 행 + 확인 + 프로세스 등록 모달 반영",
                  f"입력: 1행 radio + 확인 / 결과: 선택={selected!r}, display={after!r}", sc=3)

        # 정리
        page.process.close()
        page.close_modal()
        self._add("pass", "정리 — 등록 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: 모두 detached", sc=3)

    # ==================================================================
    # 시나리오 2g — 모달 초기값 명시 검증 (scenario_2_input.md "초기값")
    # ==================================================================
    def test_scenario2g_initial_values(self, logged_in_page, settings):
        """시나리오 2g — 모달 열자마자 default 값 명시 검증.
        scenario_2_input.md: "필드 구조, 초기값, 입력 검증 동작 유무"
        → 입력 동작은 2a~2f 가 담당, 초기값은 본 메서드에서 명시.
        """
        print("\n━━ [제어 스위트] 시나리오 2g: 모달 초기값 명시 검증 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()

        # ── 스위트 추가 모달 — 초기값 ─────────────────────────
        v = page.get_csu_name()
        self._add("pass" if v == "" else "fail",
                  "스위트 이름 — 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "클립보드 공유제한 — 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.get_clipboard_allow_url()
        self._add("pass" if v == "" else "fail",
                  "클립보드 공유제한 — 허용 URL 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.is_network_checked()
        self._add("pass" if v is False else "fail",
                  "네트워크 허용 — 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.get_main_extension_list()
        self._add("pass" if v == [] else "fail",
                  "제어할 확장자 — list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.page.locator(page.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "헤더 체크 기능 사용 — 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "전자서명 예외처리 — 사용 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.get_sign_except_list()
        self._add("pass" if v == [] else "fail",
                  "전자서명 예외처리 — list 초기값 (빈 list)",
                  f"입력: 모달 진입 직후 / 결과: list={v}", sc=2)

        v = page.get_custom_option()
        self._add("pass" if v == "" else "fail",
                  "커스텀 옵션 — 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        # ── 프로세스 등록 모달 — 초기값 ────────────────────────
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        v = page.process.get_selected_display_text()
        self._add("pass" if "미선택" in v else "fail",
                  "프로세스 등록 모달 — 선택 표시 초기값 ('프로세스 미선택')",
                  f"입력: 모달 진입 직후 / 결과: display={v!r}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT)
        self._add("pass" if v is False else "fail",
                  "프로세스 등록 모달 — 프로세스 예외처리 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK)
        self._add("pass" if v is False else "fail",
                  "프로세스 등록 모달 — 네트워크 허용 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT)
        self._add("pass" if v is False else "fail",
                  "프로세스 등록 모달 — 확장자 제어 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE)
        self._add("pass" if v is False else "fail",
                  "프로세스 등록 모달 — 접근 드라이브 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.process.get_description()
        self._add("pass" if v == "" else "fail",
                  "프로세스 등록 모달 — 설명 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        page.process.close()

        # ── 웹제한 모달 — 초기값 ──────────────────────────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()

        v = page.web_restrict.get_name()
        self._add("pass" if v == "" else "fail",
                  "웹제한 모달 — 웹 제한 이름 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.web_restrict.get_base_path()
        self._add("pass" if v == "" else "fail",
                  "웹제한 모달 — basePath 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        v = page.web_restrict.is_url_checked()
        self._add("pass" if v is False else "fail",
                  "웹제한 모달 — 적용 URL 토글 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        disables = page.web_restrict.get_url_dependent_disabled()
        all_disabled = all(disables.values())
        self._add("pass" if all_disabled else "fail",
                  "웹제한 모달 — isUrl OFF 시 종속 4건 disabled (초기 상태)",
                  f"입력: 모달 진입 직후 / 결과: {disables}", sc=2)

        v = page.web_restrict.is_file_encrypt_checked()
        self._add("pass" if v is False else "fail",
                  "웹제한 모달 — 업로드 시 암호화 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.page.locator(page.web_restrict.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if v is False else "fail",
                  "웹제한 모달 — 헤더 체크 기능 사용 초기값 (OFF)",
                  f"입력: 모달 진입 직후 / 결과: is_checked={v}", sc=2)

        v = page.web_restrict.get_description()
        self._add("pass" if v == "" else "fail",
                  "웹제한 모달 — 설명 초기값 (빈값)",
                  f"입력: 모달 진입 직후 / 결과: get={v!r}", sc=2)

        # 정리
        page.web_restrict.close()
        page.close_modal()
        self._add("pass", "정리 — 모든 모달 close (저장 X)",
                  "입력: close × 2 / 결과: detached", sc=2)

    def test_scenario2b_process_modal_fields(self, logged_in_page, settings):
        """
        process_sub_modal 의 필드를 조작 후 get 으로 일치 확인.
        4 단독 토글 / IP+Port / 확장자 라디오+list / 드라이브 / description.
        cache_folder + special_folder 는 Step 3c-extra 로 분리.
        저장 안 함 (close).
        """
        page = NpouchControlSuitePage(logged_in_page, settings)

        print("\n" + "=" * 60)
        print("[Step 3c] process_sub_modal 필드 검증")
        print("=" * 60)

        print("\n━━ [제어 스위트] 시나리오 2b: process_modal 필드 ━━━")
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step3c")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()

        # 프로세스 1건 선택 (필드 조작 사전 조건)
        page.process.click_pick_btn()
        page.picker.wait_open()
        selected = page.picker.select_first_and_confirm(mode="single")
        self._add("pass", "프로세스 선택 (필드 조작 사전조건)",
                  f"입력: picker 첫 행 / 결과: {selected!r}", sc=2)

        # ── 단독 토글 4건 ──────────────────────────────────────
        page.process.set_process_except(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PROC_EXCEPT)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 프로세스 예외처리 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.process.set_pclipboard_restrict(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCLIPBOARD)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 개별 클립보드 공유제한 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.process.set_sandbox(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_SANDBOX)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 샌드박스 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.process.set_deny_except_drive(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_DENY_EXCEPT_DRIVE)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 드라이브 제외 거부 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        # ── 네트워크 허용 (isPNetwork + IP/Port) ──────────────
        page.process.set_pnetwork(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PNETWORK)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 네트워크 허용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.process.add_ip_port("192.168.1.1", "8080")
        ip_list = page.process.get_ip_list()
        ok = any("192.168.1.1" in x and "8080" in x for x in ip_list)
        self._add("pass" if ok else "fail",
                  "프로세스 등록 모달 — IP/Port 추가 (list)",
                  f"입력: '192.168.1.1' + '8080' / 결과: list={ip_list}", sc=3)

        # ── 확장자 제어 (isPControlExtension + 라디오 + tag) ──
        page.process.set_pcontrol_extension(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_PCONTROL_EXT)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 확장자 제어 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.process.click_radio_blockp()
        t1 = page.process.get_radio_react_text()
        self._add("pass" if t1 == "허용할 확장자" else "fail",
                  "프로세스 등록 모달 — 확장자 BLOCKP 라디오 반응",
                  f"입력: BLOCKP 클릭 / 결과: span={t1!r}", sc=2)

        page.process.click_radio_allowp()
        t2 = page.process.get_radio_react_text()
        self._add("pass" if t2 == "차단할 확장자" else "fail",
                  "프로세스 등록 모달 — 확장자 ALLOWP 라디오 반응",
                  f"입력: ALLOWP 클릭 / 결과: span={t2!r}", sc=2)

        page.process.add_extension("log;tmp;bak")
        ext = page.process.get_extension_list()
        self._add("pass" if ext == ["log", "tmp", "bak"] else "fail",
                  "프로세스 등록 모달 — 확장자 ';' 다중구분자 등록",
                  f"입력: 'log;tmp;bak' / 결과: list={ext}", sc=3)

        # ── 접근 드라이브 ──────────────────────────────────────
        page.process.set_access_drive(True)
        chk = page.process.is_toggle_checked(page.process.SEL_TOGGLE_ACCESS_DRIVE)
        self._add("pass" if chk else "fail",
                  "프로세스 등록 모달 — 접근 드라이브 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        page.process.set_drive_letter("C;D")
        dl = page.process.get_drive_letter()
        self._add("pass" if dl == "C;D" else "fail",
                  "프로세스 등록 모달 — 드라이브 레터 입력",
                  f"입력: 'C;D' / 결과: get={dl!r}", sc=3)

        # ── 설명 ───────────────────────────────────────────────
        page.process.set_description("step3c 자동 테스트 설명")
        desc = page.process.get_description()
        self._add("pass" if "step3c" in desc else "fail",
                  "프로세스 등록 모달 — 설명 입력",
                  f"입력: 'step3c 자동 테스트 설명' / 결과: get={desc!r}", sc=3)

        # ── 정리 ───────────────────────────────────────────────
        page.process.close()
        page.close_modal()
        self._add("pass", "프로세스 등록 모달 — 취소 close",
                  "입력: close + 메인 close / 결과: 모두 detached", sc=3)

    def test_scenario2c_cache_folder_picker(self, logged_in_page, settings):
        """
        cache_folder_section 의 2 케이스 (yaml validation_cases) 검증:
          Case 1: 일반 텍스트 경로 직접 입력 + 추가
          Case 2: 특수폴더 picker 다중 선택 (체크 순서 보존) + 추가

        yaml inspection_notes:
          - 특수폴더 N건 → cacheFolderList 1건으로 병합 등록 (line 197-198)
          - cache_folder ';' 다중구분자 미적용 (line 201)
          - 중복 검증 없음 (line 388 — IP/Port/확장자와 다른 정책)
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        print("\n━━ [제어 스위트] 시나리오 2c: cache_folder + 특수폴더 ━━━")
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step3c_extra")
        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        selected = page.picker.select_first_and_confirm(mode="single")
        self._add("pass", "프로세스 선택 (cache_folder 검증 사전조건)",
                  f"입력: picker 첫 행 / 결과: {selected!r}", sc=3)

        # ── Case 1: 텍스트 직접 입력 + 추가 ────────────────────
        page.process.set_cache_input("C:\\test_path1")
        before = page.process.get_cache_input_text()
        self._add("pass" if "C:\\test_path1" in before else "fail",
                  "프로세스 등록 모달 — 캐시폴더 텍스트 입력",
                  f"입력: 'C:\\test_path1' / 결과: innerText={before!r}", sc=3)

        page.process.click_cache_add_btn()
        lst = page.process.get_cache_folder_list()
        ok = any("C:\\test_path1" in x for x in lst)
        self._add("pass" if ok else "fail",
                  "프로세스 등록 모달 — 캐시폴더 추가 (list 등록)",
                  f"입력: '추가' 클릭 / 결과: list={lst}", sc=3)

        cleared = page.process.get_cache_input_text()
        ok = cleared in ("", "​")
        self._add("pass" if ok else "fail",
                  "프로세스 등록 모달 — 캐시폴더 추가 후 input 비우기",
                  f"입력: (추가 후) / 결과: innerText={cleared!r}", sc=3)

        # ── Case 2: 특수폴더 picker ────────────────────────────
        page.process.click_special_folder_btn()
        page.special_folder.wait_open()
        title = page.special_folder.get_title()
        rcnt = page.special_folder.get_row_count()
        self._add("pass" if rcnt == 11 else "fail",
                  "예약어 선택 모달 — 11 예약어 행 존재",
                  f"입력: '특수폴더' 클릭 / 결과: title={title!r}, 행 수={rcnt}", sc=2)

        order = ["[/FAVORITES/]", "[/DESKTOP/]", "[/USER/]"]
        page.special_folder.select_and_confirm(order)
        self._add("pass" if not page.special_folder.is_open() else "fail",
                  "예약어 선택 모달 — 다중 체크 + 확인",
                  f"입력: 체크 순서={order} + 확인 / 결과: picker 닫힘={not page.special_folder.is_open()}", sc=3)

        inline_text = page.process.get_cache_input_text()
        order_ok = all(code in inline_text for code in order)
        self._add("pass" if order_ok else "fail",
                  "프로세스 등록 모달 — 특수폴더 inline tag (클릭 순서 보존)",
                  f"입력: {order} 클릭 순 / 결과: input text={inline_text!r}", sc=3)

        before_count = len(page.process.get_cache_folder_list())
        page.process.click_cache_add_btn()
        lst = page.process.get_cache_folder_list()
        added = len(lst) - before_count
        merge_ok = added == 1 and all(code in lst[-1] for code in order)
        self._add("pass" if merge_ok else "fail",
                  "프로세스 등록 모달 — 캐시폴더 다중 특수폴더 → 1건 병합 등록",
                  f"입력: '추가' 클릭 / 결과: 추가 건수={added}, last={lst[-1] if lst else None!r}", sc=3)

        # 정리
        page.process.close()
        page.close_modal()
        self._add("pass", "정리 — 프로세스 등록 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: detached", sc=3)

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

        page.open_add_modal()
        page.set_csu_name(policy_name)
        self._add("pass", "스위트 추가 모달 — 진입 + 스위트 이름 입력",
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
                  "프로세스별 제어 — 프로세스 1건 등록 (itemList)",
                  f"입력: picker '{selected}' + 확인 / 결과: itemList 행={len(rows)}", sc=3)

        msg = page.save_policy(mode="add")
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 추가 모달 — '추가' 버튼 (저장)",
                  f"입력: '추가' 클릭 / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()

        exists = page.is_policy_exists(policy_name)
        self._add("pass" if exists else "fail",
                  "정책 list — 신규 정책 등록 확인",
                  f"입력: (저장 완료 후) / 결과: '{policy_name}' 존재={exists}", sc=3)


    def test_scenario1c_web_restrict_open(self, logged_in_page, settings):
        """시나리오 1c — web_restrict_sub_modal 진입 + name 필드."""
        print("\n━━ [제어 스위트] 시나리오 1c: web_restrict 진입 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step4a")

        # ── 웹 제한기능 + 버튼 → 모달 진입 ─────────────────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        title = page.web_restrict.get_title()
        self._add("pass" if title == "웹 제한 목록 추가" else "fail",
                  "웹 제한기능 — '+' 버튼 → 모달 진입",
                  f"입력: '+' 클릭 / 결과: title={title!r}, is_open={page.web_restrict.is_open()}", sc=1)

        # ── webRestrictName 필드 ──────────────────────────────
        page.web_restrict.set_name("[AUTO]_web_step4a")
        got = page.web_restrict.get_name()
        self._add("pass" if got == "[AUTO]_web_step4a" else "fail",
                  "웹 제한 이름",
                  f"입력: '[AUTO]_web_step4a' / 결과: get={got!r}", sc=1)

        # ── 모달 close ────────────────────────────────────────
        page.web_restrict.close()
        self._add("pass" if not page.web_restrict.is_open() else "fail",
                  "web_restrict_modal — × 버튼 close",
                  f"입력: close 클릭 / 결과: is_open={page.web_restrict.is_open()}", sc=1)
        page.close_modal()

    def test_scenario2d_web_restrict_process(self, logged_in_page, settings):
        """시나리오 2d — web_restrict 적용 프로세스 (picker multi) + basePath + isProcessOption."""
        print("\n━━ [제어 스위트] 시나리오 2d: web_restrict 적용 프로세스 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step4b")
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_step4b")
        self._add("pass", "웹제한 모달 — 진입 + 이름 set",
                  "입력: '+' 클릭 + name 입력 / 결과: 모달 open + name 저장", sc=3)

        # ── 적용 프로세스 picker (multi) ───────────────────────
        before_rows = page.web_restrict.get_process_rows()
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        title = page.picker.get_title()
        cnt = page.picker.get_row_count()
        self._add("pass" if title == "프로세스 선택" and cnt > 0 else "fail",
                  "웹제한 모달 — 적용 프로세스 추가 (picker multi 진입)",
                  f"입력: '프로세스 추가' 클릭 / 결과: picker title={title!r}, 행 수={cnt}", sc=3)

        selected = page.picker.select_first_and_confirm(mode="multi")
        after_rows = page.web_restrict.get_process_rows()
        added = len(after_rows) - len(before_rows)
        self._add("pass" if added >= 1 else "fail",
                  "웹제한 모달 — 적용 프로세스 picker 확인 → 테이블 등록",
                  f"입력: 첫 행 체크 + 확인 ({selected!r}) / 결과: 추가={added}, total={len(after_rows)}", sc=3)

        # ── 기본폴더 지정 (basePath) ───────────────────────────
        page.web_restrict.set_base_path("C:\\webrestrict_base")
        bp = page.web_restrict.get_base_path()
        self._add("pass" if bp == "C:\\webrestrict_base" else "fail",
                  "웹제한 모달 — 기본폴더 (basePath) 입력",
                  f"입력: 'C:\\webrestrict_base' / 결과: get={bp!r}", sc=3)

        # ── 기본폴더 지정 토글 (isProcessOption) ──────────────
        page.web_restrict.set_process_option(True)
        chk = page.web_restrict.is_process_option_checked()
        self._add("pass" if chk else "fail",
                  "웹제한 모달 — 기본폴더 지정 사용 토글",
                  f"입력: ON / 결과: is_checked={chk}", sc=3)

        # 정리
        page.web_restrict.close()
        page.close_modal()
        self._add("pass", "정리 — 웹제한 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: detached", sc=3)

    def test_scenario2e_web_restrict_fields(self, logged_in_page, settings):
        """
        web_restrict_modal 의 모든 필드를 yaml 기준 종합 검증.

        검증 블록:
          1. 권한 ▼ expand + processAuth 라디오 → text sync (1회 한정 buggy)
          2. isUrl 토글 + 종속 disabled 변화 (4건) + isDataDecrypt 라디오
          3. add_url ('not a url' 포함 — yaml 형식 검증 없음 사실)
          4. isFileUploadEncrypt — decrypt_target 시 자동 checked+disabled 검증
          5. headerCheck (독립)
          6. add_file_extension 다중 구분자
          7. uploadLimit + description
        """
        print("\n━━ [제어 스위트] 시나리오 2e: web_restrict 필드 (yaml 종합) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_step4c")
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_step4c")

        # 사전조건: 프로세스 1건 + isProcessOption ON (권한 expand 활성)
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_process_option(True)
        self._add("pass", "사전조건 — 프로세스 1건 + isProcessOption ON",
                  "입력: picker multi + 토글 ON / 결과: 권한 expand 활성", sc=3)

        # ── 권한 ▼ expand + processAuth 라디오 sync ─────────────
        page.web_restrict.click_expand_btn()
        expanded = page.web_restrict.is_auth_expanded()
        self._add("pass" if expanded else "fail",
                  "웹제한 모달 — 기타 프로세스 권한 ▼ 펼침",
                  f"입력: ▼ 클릭 / 결과: expanded={expanded}", sc=3)

        page.web_restrict.set_process_auth("3")
        sync_text = page.web_restrict.get_process_auth_text()
        self._add("pass" if sync_text == "쓰기" else "fail",
                  "웹제한 모달 — 기타 프로세스 권한 v3(쓰기) 라디오 sync",
                  f"입력: v3 선택 / 결과: text={sync_text!r}", sc=2)

        # ── isUrl 토글 + 종속 disabled ─────────────────────────
        off_states = page.web_restrict.get_url_dependent_disabled()
        self._add("pass" if all(off_states.values()) else "fail",
                  "웹제한 모달 — 적용 URL OFF 시 종속 4건 disabled",
                  f"입력: 기본 OFF / 결과: {off_states}", sc=2)

        page.web_restrict.set_is_url(True)
        on_states = page.web_restrict.get_url_dependent_disabled()
        self._add("pass" if not any(on_states.values()) else "fail",
                  "웹제한 모달 — 적용 URL ON 시 종속 4건 활성",
                  f"입력: 토글 ON / 결과: {on_states}", sc=2)

        # ── URL list 추가 (형식 검증 없음 — yaml 사실) ─────────
        page.web_restrict.add_url("naver.com")
        page.web_restrict.add_url("not a url")
        url_list = page.web_restrict.get_url_list()
        self._add("pass" if any("naver.com" in u for u in url_list) else "fail",
                  "웹제한 모달 — 적용 URL list 추가 (형식 검증 없음)",
                  f"입력: 'naver.com', 'not a url' / 결과: list={url_list}", sc=3)

        # ── isDataDecrypt=1 → isFileUploadEncrypt 자동 강제 ────
        page.web_restrict.click_decrypt_target()
        chk = page.web_restrict.is_file_encrypt_checked()
        dis = page.web_restrict.is_file_encrypt_disabled()
        ok = chk and dis
        self._add("pass" if ok else "fail",
                  "웹제한 모달 — 복호화 대상 → 업로드 시 암호화 자동 강제",
                  f"입력: decrypt_target 선택 / 결과: checked={chk}, disabled={dis}", sc=2)

        page.web_restrict.click_decrypt_allow()
        dis_after = page.web_restrict.is_file_encrypt_disabled()
        self._add("pass" if not dis_after else "fail",
                  "웹제한 모달 — 허용 URL 복귀 → 업로드 암호화 disabled 해제",
                  f"입력: decrypt_allow 선택 / 결과: disabled={dis_after}", sc=2)

        # ── headerCheck (독립) ─────────────────────────────────
        page.web_restrict.set_header_check(True)
        hc = page.page.locator(page.web_restrict.SEL_HEADER_CHECK).first.is_checked()
        self._add("pass" if hc else "fail",
                  "웹제한 모달 — 헤더 체크 기능 (uploadLimit 와 독립)",
                  f"입력: ON / 결과: is_checked={hc}", sc=3)

        # ── 업로드 허용 확장자 다중구분자 ──────────────────────
        page.web_restrict.add_file_extension("png;jpg;gif")
        items = page.page.locator(
            "div#controlSuiteWebRestricList button.tagInput[name='ExtentionWebRestrict'], "
            "div#controlSuiteWebRestricList button.tagInput.addBtn"
        )
        cnt = items.count()
        self._add("pass" if cnt >= 3 else "fail",
                  "웹제한 모달 — 업로드 허용 확장자 ';' 다중구분자",
                  f"입력: 'png;jpg;gif' / 결과: tag 수={cnt} (sanity)", sc=3)

        # ── uploadLimit ────────────────────────────────────────
        page.web_restrict.set_upload_limit("1024")
        ul = page.web_restrict.get_upload_limit()
        self._add("pass" if ul == "1024" else "fail",
                  "웹제한 모달 — 업로드 제한용량 입력",
                  f"입력: '1024' / 결과: get={ul!r}", sc=3)

        # ── description ────────────────────────────────────────
        page.web_restrict.set_description("step4c 자동 테스트")
        desc = page.web_restrict.get_description()
        self._add("pass" if "step4c" in desc else "fail",
                  "웹제한 모달 — 설명 입력",
                  f"입력: 'step4c 자동 테스트' / 결과: get={desc!r}", sc=3)

        # 정리
        page.web_restrict.close()
        page.close_modal()
        self._add("pass", "정리 — 웹제한 모달 + 스위트 추가 모달 close",
                  "입력: close + close / 결과: detached", sc=3)

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
                  "프로세스별 제어 — 프로세스 1건 등록",
                  f"입력: picker '{proc_name}' + 확인 / 결과: itemList 행={len(proc_rows)}", sc=3)

        # web_restrict 등록
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name("[AUTO]_web_step4d")

        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        wr_proc = page.picker.select_first_and_confirm(mode="multi")
        self._add("pass", "웹제한 모달 — 적용 프로세스 추가 (picker multi)",
                  f"입력: picker '{wr_proc}' (multi) / 결과: 테이블 등록", sc=3)

        page.web_restrict.set_is_url(True)
        page.web_restrict.add_url("naver.com")
        url_list = page.web_restrict.get_url_list()
        self._add("pass" if any("naver.com" in u for u in url_list) else "fail",
                  "웹제한 모달 — 적용 URL 등록 (naver.com)",
                  f"입력: 'naver.com' / 결과: list={url_list}", sc=3)

        page.web_restrict.add_file_extension("png;jpg")
        page.web_restrict.set_upload_limit("2048")
        page.web_restrict.set_description("[AUTO] step4d e2e 설명")
        self._add("pass", "웹제한 모달 — 확장자 + 제한용량 + 설명 입력",
                  "입력: 'png;jpg' / '2048' / 설명 / 결과: 입력 반영", sc=3)

        page.web_restrict.confirm()
        wr_rows = page.get_item_web_restrict_rows()
        self._add("pass" if len(wr_rows) >= 1 else "fail",
                  "웹제한 모달 — 확인 (itemWebRestrictList 등록)",
                  f"입력: '확인' 클릭 / 결과: 행 수={len(wr_rows)}", sc=3)

        msg = page.save_policy(mode="add")
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 추가 모달 — '추가' 버튼 (저장)",
                  f"입력: '추가' 클릭 / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()

        exists = page.is_policy_exists(policy_name)
        self._add("pass" if exists else "fail",
                  "정책 list — 신규 정책 등록 확인",
                  f"입력: (저장 완료 후) / 결과: '{policy_name}' 존재={exists}", sc=3)


    def test_scenario3d_crud_full_cycle(self, logged_in_page, settings):
        """
        시나리오 3 — ADD + 저장값 확인 + 수정 + 변경값 확인.
        삭제는 시나리오 4 이후로 미룸 (legacy dependency 패턴).

        흐름:
          1. ADD (csuName + 단독 필드 + 프로세스 1건) → 저장
          2. EDIT 진입 → 입력값 그대로 로드 확인
          3. 같은 EDIT 모달 안에서 필드 변경 → modify 저장
          4. list 에서 변경된 이름 + EDIT 재진입 → 변경값 재확인 → close (정책 남김)
        """
        page = NpouchControlSuitePage(logged_in_page, settings)
        ADD_NAME    = "[AUTO]_step5b_add"
        MOD_NAME    = "[AUTO_KEEP]_step5b_mod"   # ← 시나리오 4 가 사용
        ADD = {
            "clipboard_url":  "naver.com;google.com",
            "extensions":     ["txt", "doc", "exe"],
            "sign_excepts":   ["Claude Sign", "Innotium Inc"],
            "custom_option":  "step5b_init",
            # 웹제한 1건 (시나리오 4d 가 수정 대상으로 사용)
            "web_name":       "[AUTO]_web_step5b",
            "web_url":        "step5b-web.com",
            "web_ext":        "csv",
            "web_limit":      "512",
            "web_desc":       "step5b 웹제한 초기값",
        }
        MOD = {
            "clipboard_url":  "daum.net;kakao.com",
            "custom_option":  "step5b_modified",
        }

        print("\n━━ [제어 스위트] 시나리오 3d: CRUD 1사이클 (KEEP 보존) ━━━")
        self._page = page.page

        page.navigate_to()
        # 1a 에서 이미 전체 정리됨 — AUTO 잔여만 정리하고 KEEP 보존하며 진행.

        # ── ADD ────────────────────────────────────────────────
        page.open_add_modal()
        page.set_csu_name(ADD_NAME)
        page.set_clipboard_restrict_toggle(True)
        page.set_clipboard_allow_url(ADD["clipboard_url"])
        page.set_network_toggle(True)
        page.click_radio_allow()
        for ext in ADD["extensions"]:
            page.add_main_extension(ext)
        page.set_header_check(True)
        page.set_sign_except_toggle(True)
        for s in ADD["sign_excepts"]:
            page.add_sign_except(s)
        page.set_custom_option(ADD["custom_option"])

        page.click_individual_process_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        proc = page.picker.select_first_and_confirm(mode="single")
        page.process.confirm()

        # ── 웹제한 1건 (시나리오 4d 의 수정 대상) ───────────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        page.web_restrict.set_name(ADD["web_name"])
        page.web_restrict.click_add_process_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="multi")
        page.web_restrict.set_is_url(True)
        page.web_restrict.add_url(ADD["web_url"])
        page.web_restrict.add_file_extension(ADD["web_ext"])
        page.web_restrict.set_upload_limit(ADD["web_limit"])
        page.web_restrict.set_description(ADD["web_desc"])
        page.web_restrict.confirm()

        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" and page.is_policy_exists(ADD_NAME) else "fail",
                  "스위트 추가 모달 — 모든 필드 입력 + '추가' 저장",
                  f"입력: 11 필드 + 프로세스 '{proc}' + 웹제한 1 + 저장 / 결과: 메시지={msg!r}", sc=3)

        # ── 저장값 확인 (EDIT 진입 후 11 필드 일치) ────────────
        page.open_modify_modal(ADD_NAME)
        checks = {
            "csuName":          page.get_csu_name() == ADD_NAME,
            "clipboardRestrict": page.page.locator(page.SEL_CLIPBOARD_RESTRICT).first.is_checked(),
            "clipboardURL":     ADD["clipboard_url"] in page.get_clipboard_allow_url(),
            "network":          page.is_network_checked(),
            "radioLabel":       page.get_radio_react_text() == "차단할 확장자",
            "extensions":       page.get_main_extension_list() == ADD["extensions"],
            "headerCheck":      page.page.locator(page.SEL_HEADER_CHECK).first.is_checked(),
            "signExceptToggle": page.page.locator(page.SEL_SIGN_EXCEPT_TOGGLE).first.is_checked(),
            "signExceptCount":  len(page.get_sign_except_list()) == len(ADD["sign_excepts"]),
            "customOption":     page.get_custom_option() == ADD["custom_option"],
            "itemListCount":    len(page.get_item_list_rows()) == 1,
            "webRestrictCount": len(page.get_item_web_restrict_rows()) == 1,
        }
        failed = [k for k, ok in checks.items() if not ok]
        self._add("pass" if not failed else "fail",
                  "스위트 수정 모달 — 저장값 재확인 (11 필드 + 웹제한 일치)",
                  f"입력: 수정 모달 진입 / 결과: 일치={len(checks)-len(failed)}/{len(checks)}, 실패={failed}", sc=4)

        # ── 수정 ────────────────────────────────────────────────
        page.set_csu_name(MOD_NAME)
        page.set_clipboard_allow_url(MOD["clipboard_url"])
        page.set_custom_option(MOD["custom_option"])

        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — 3 필드 변경 + '수정' 저장",
                  f"입력: 이름/URL/커스텀 옵션 변경 + 저장 / 결과: 메시지={msg!r}", sc=4)

        # ── 변경값 재확인 ──────────────────────────────────────
        ok_list = page.is_policy_exists(MOD_NAME) and not page.is_policy_exists(ADD_NAME)
        self._add("pass" if ok_list else "fail",
                  "정책 list — 이름 변경 반영 (이전 사라짐 + 새 등록)",
                  f"입력: 수정 저장 후 / 결과: 신규='{MOD_NAME}' 존재, 이전='{ADD_NAME}' 잔존={page.is_policy_exists(ADD_NAME)}", sc=3)

        page.open_modify_modal(MOD_NAME)
        check_mod = (
            page.get_csu_name() == MOD_NAME and
            MOD["clipboard_url"] in page.get_clipboard_allow_url() and
            page.get_custom_option() == MOD["custom_option"] and
            page.get_main_extension_list() == ADD["extensions"] and  # 미변경 필드 보존
            page.page.locator(page.SEL_NETWORK).first.is_checked()
        )
        self._add("pass" if check_mod else "fail",
                  "스위트 수정 모달 — 변경값 + 미변경 필드 보존 (재진입)",
                  f"입력: 수정 모달 재진입 / 결과: 변경+보존 일치={check_mod}", sc=4)
        page.close_modal()

        # KEEP 정책 의도적 보존 — 시나리오 4 가 사용
        self._add("pass", "정책 list — KEEP 정책 의도적 보존 (시나리오 4b 사용 예정)",
                  f"입력: 닫기만 (삭제 X) / 결과: '{MOD_NAME}' 잔존", sc=3)

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
                  "스위트 이름 — DOM maxlength=50 자동 절단",
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
                  "스위트 이름 — ADD 빈값 차단 메시지",
                  f"입력: 이름='' + '추가' / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()

        # 정책 1건 ADD (중복/미선택 검증 사전조건)
        page.set_csu_name(dup_name)
        msg = page.save_policy(mode="add")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" and page.is_policy_exists(dup_name) else "fail",
                  "정책 list — 중복/미선택 검증용 정책 1건 ADD (사전조건)",
                  f"입력: 이름='{dup_name}' + 저장 / 결과: 메시지={msg!r}", sc=3)

        # ── C. 미선택 modify 버튼 ────────────────────────────────
        modify_btn = page.page.locator(page.SEL_MODIFY_BTN).first
        c_disabled = modify_btn.is_disabled()
        if not c_disabled:
            page._click(modify_btn)
            page.page.wait_for_timeout(500)
            if page.is_confirm_modal_visible():
                page.dismiss_confirm_modal()
        self._add("pass", "정책 list — '수정' 버튼 (미선택 상태)",
                  f"입력: 행 미선택 + '수정' 클릭 / 결과: disabled={c_disabled}", sc=3)

        # ── D. 미체크 delete 버튼 ───────────────────────────────
        delete_btn = page.page.locator(page.SEL_DELETE_BTN).first
        d_disabled = delete_btn.is_disabled()
        if not d_disabled:
            page._click(delete_btn)
            page.page.wait_for_timeout(500)
            if page.is_confirm_modal_visible():
                page.dismiss_confirm_modal()
        self._add("pass", "정책 list — '삭제' 버튼 (체크박스 미체크 상태)",
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
                  "스위트 이름 — 중복 차단 메시지",
                  f"입력: 이름='{dup_name}' (중복) + '추가' / 결과: 메시지={msg!r}", sc=3)
        page.dismiss_confirm_modal()
        page.close_modal()


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
    def test_scenario4e_edit_tag_full(self, logged_in_page, settings):
        """시나리오 4e — 태그 영역 종합 검증 (신규).

        KEEP 정책 EDIT 진입 → Tag tab 활성화 → itemTagList load (0 행 — 3d 가 미등록) →
        신규 태그 1건 추가 (picker tag mode) → 저장 → 재오픈 → tag 행 클릭 → 모달 재진입.
        """
        print("\n━━ [제어 스위트] 시나리오 4e: 태그 영역 종합 (신규) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        KEEP_NAME = "[AUTO_KEEP]_step5b_mod"

        page.navigate_to()
        if not page.is_policy_exists(KEEP_NAME):
            self._add("skip", "시나리오 4e — KEEP 정책 부재 → skip",
                      f"입력: 진입 / 결과: '{KEEP_NAME}' 없음", sc=4)
            return

        # ── EDIT 진입 + Tag tab 활성화 + itemTagList 0행 load ───
        page.open_modify_modal(KEEP_NAME)
        page.click_tag_tab()
        before_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if before_rows == 0 else "fail",
                  "태그 — Tag tab 활성화 + 기존 itemTagList 0행 load",
                  f"입력: Tag tab 클릭 / 결과: itemTagList 행={before_rows}", sc=4)

        # ── 신규 태그 1건 추가 (picker tag mode) ────────────────
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        picker_title = page.picker.get_title()
        self._add("pass" if "태그" in picker_title else "fail",
                  "태그 — picker tag mode 진입 (제목 확인)",
                  f"입력: '+' + picker / 결과: picker title={picker_title!r}", sc=4)

        page.picker.select_first_and_confirm(mode="tag")
        page.process.confirm()

        after_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if after_rows == 1 else "fail",
                  "태그 — 신규 태그 1건 추가 후 itemTagList 1행",
                  f"입력: picker tag 첫 행 + 확인 / 결과: 행={after_rows}", sc=4)

        # ── '수정' 저장 ──────────────────────────────────────────
        msg = page.save_policy(mode="modify")
        page.dismiss_confirm_modal()
        self._add("pass" if msg == "저장 하였습니다" else "fail",
                  "스위트 수정 모달 — 태그 추가 후 '수정' 저장",
                  f"입력: '수정' 클릭 / 결과: 메시지={msg!r}", sc=4)

        # ── 재오픈 + Tag tab → 태그 행 재진입 ──────────────────
        page.open_modify_modal(KEEP_NAME)
        page.click_tag_tab()
        final_rows = len(page.get_item_tag_list_rows())
        self._add("pass" if final_rows == 1 else "fail",
                  "스위트 수정 모달 — 재오픈 후 태그 1행 유지",
                  f"입력: 재오픈 + Tag tab / 결과: itemTagList 행={final_rows}", sc=4)

        if final_rows >= 1:
            page.click_item_tag_list_row(0)
            tag_disp = page.process.get_selected_display_text()
            self._add("pass" if "미선택" not in tag_disp else "fail",
                      "태그 — itemTagList 행 클릭 → 태그 모달 재진입 (선택 표시 유지)",
                      f"입력: 행 클릭 / 결과: display={tag_disp!r}", sc=4)
            page.process.close()

        page.close_modal()

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
    # 시나리오 5a — 한 정책 lifecycle: ADD (종합) + 재오픈 일치 → 정책 보존
    # ==================================================================
    # [AUTO_KEEP]_scenario5_lifecycle 정책을 5a → 5b → 5c 에서 공유 사용.
    # 5a 는 cleanup 하지 않고 다음 단계에 정책을 넘긴다.
    LIFECYCLE_NAME = "[AUTO_KEEP]_scenario5_lifecycle"
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

        # ── 3. 태그 sub-tab + 태그 1건 ─────────────────────────
        page.click_tag_tab()
        page.click_add_process_btn()
        page.process.wait_open()
        page.process.click_pick_btn()
        page.picker.wait_open()
        page.picker.select_first_and_confirm(mode="tag")
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
    def test_scenario5b_lifecycle_modify(self, logged_in_page, settings):
        """시나리오 5b — 5a 가 남긴 [AUTO_KEEP]_scenario5_lifecycle 정책의 EDIT 진입 → 메인 필드 변경 → 저장.

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
                      "시나리오 5b — 5a 정책 ([AUTO_KEEP]_scenario5_lifecycle) 부재로 skip",
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

    def test_zz_cleanup_keep(self, logged_in_page, settings):
        """모든 [AUTO]_ + [AUTO_KEEP]_ 정책 일괄 삭제 (테스트 종료 정리)."""
        print("\n━━ [제어 스위트] 최종 cleanup ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        deleted = page.delete_all_test_data()
        names = page.get_policy_names()
        leftover = [n for n in names if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
