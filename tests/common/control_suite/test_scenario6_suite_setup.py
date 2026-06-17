"""시나리오 6 — 연계 데이터 준비 (핸드오프 확인).

설계 (scenario_6_suite_setup.md) + 사용자 결정 (2026-05-28):
  - sc6 의 본래 의도: 다음 페이지(통합정책) 연계용 데이터를 남겨둔다.
  - 현재 다운스트림(통합정책) 테스트 미구현 → "생성" 대신 sc5 가 남긴
    [AUTO_KEEP]_sc5_step1 이 핸드오프 가능한 상태인지 **확인/표시만** 한다.
    (없는 소비자를 위한 추측 구현 금지 — Karpathy 2번 원칙)
  - 동작: 존재 확인 + 내용(이름/프로세스 행) 표시 + "다음 연계에서 사용" 신호.
    수정·삭제 안 함 → keep 그대로 남김. 최종 정리는 다음 run 의 sc1 시작.

순서: scenario5(생성·보존) < scenario6(확인) < zz_cleanup(AUTO 정리, keep 보존)
"""
from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.common.control_suite._base import ControlSuiteBase


class TestScenario6SuiteSetup(ControlSuiteBase):
    """nPouch 제어 스위트 — 시나리오 6: 연계 데이터 핸드오프 확인."""

    # sc5 가 lifecycle 종료 후 보존하는 정책 (내용=프로세스 1건 보유).
    KEEP_NAME = "[AUTO_KEEP]_sc5_step1"

    def test_scenario6_keep_handoff(self, logged_in_page, settings):
        """sc5 보존 [AUTO_KEEP] 존재/내용 확인 → 다음 연계 사용 신호 (삭제 안 함)."""
        print("\n━━ [제어 스위트] 시나리오 6: 연계 데이터 핸드오프 확인 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        NAME = self.KEEP_NAME

        # ⚠ sc6 는 cleanup 호출 안 함 — sc5 가 남긴 keep 에 의존 (읽기 전용 핸드오프).
        page.navigate_to()
        if not page.is_policy_exists(NAME):
            # 상위(sc5) 미실행 — fail 아닌 warn (문서 규칙: 연계 항목 없을 때 fail 금지)
            self._add("warn",
                      "시나리오 6 — 연계 keep 정책 부재 (sc5 미실행/실패)",
                      f"입력: '{NAME}' 조회 / 결과: 목록에 없음 → 핸드오프 불가", sc=6)
            return

        # ── 존재 + 내용 확인/표시 ────────────────────────────────
        page.open_modify_modal(NAME)
        csu_name = page.get_csu_name()
        page.click_individual_process_tab()
        proc_rows = len(page.get_item_list_rows())
        web_rows = len(page.get_item_web_restrict_rows())
        page.close_modal()

        self._add("pass" if csu_name == NAME else "fail",
                  "시나리오 6 — 연계 keep 정책 존재 확인",
                  f"입력: '{NAME}' 재오픈 / 결과: 이름={csu_name!r}", sc=6)
        self._add("pass" if proc_rows >= 1 else "warn",
                  "시나리오 6 — 연계 keep 정책 내용 보유 (다음 연계 사용 가능)",
                  f"결과: 프로세스 행={proc_rows}, 웹제한 행={web_rows}", sc=6)

        # ── 핸드오프 신호 — 삭제하지 않고 남김 ───────────────────
        self._add("skip",
                  "시나리오 6 — 연계 데이터 남겨두기 (다음 페이지 연계에서 사용)",
                  f"'{NAME}' 보존 — 통합정책 테스트 구현 시 이 keep 을 연계에 사용. zz 도 보존, 다음 run sc1 이 정리.", sc=6)
