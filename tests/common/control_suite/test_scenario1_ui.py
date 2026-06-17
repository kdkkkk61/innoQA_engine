"""시나리오 1 — UI 진입 (1a/1b/1c).

    세션 첫 시작 정리 포함."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.common.control_suite._base import ControlSuiteBase, _r, _assert_no_fail


class TestScenario1Ui(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 1 — UI 진입 (1a/1b/1c)"""

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

        # 1. navigate + 세션 시작 정리 (auto + keep 모두) — _base helper 통일
        page.navigate_to()
        self._ensure_session_cleanup(page)
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
        page.set_csu_name("[AUTO]_sc1_step1")

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



    def test_scenario1c_web_restrict_open(self, logged_in_page, settings):
        """시나리오 1c — web_restrict_sub_modal 진입 + name 필드."""
        print("\n━━ [제어 스위트] 시나리오 1c: web_restrict 진입 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page

        page.navigate_to()
        page.open_add_modal()
        page.set_csu_name("[AUTO]_sc1_step2")

        # ── 웹 제한기능 + 버튼 → 모달 진입 ─────────────────────
        page.click_add_web_restrict_btn()
        page.web_restrict.wait_open()
        title = page.web_restrict.get_title()
        self._add("pass" if title == "웹 제한 목록 추가" else "fail",
                  "웹 제한기능 — '+' 버튼 → 모달 진입",
                  f"입력: '+' 클릭 / 결과: title={title!r}, is_open={page.web_restrict.is_open()}", sc=1)

        # ── webRestrictName 필드 ──────────────────────────────
        page.web_restrict.set_name("[AUTO]_web_sc1_step2")
        got = page.web_restrict.get_name()
        self._add("pass" if got == "[AUTO]_web_sc1_step2" else "fail",
                  "웹 제한 이름",
                  f"입력: '[AUTO]_web_sc1_step2' / 결과: get={got!r}", sc=1)

        # ── 모달 close ────────────────────────────────────────
        page.web_restrict.close()
        self._add("pass" if not page.web_restrict.is_open() else "fail",
                  "web_restrict_modal — × 버튼 close",
                  f"입력: close 클릭 / 결과: is_open={page.web_restrict.is_open()}", sc=1)
        page.close_modal()

