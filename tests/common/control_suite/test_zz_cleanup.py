"""최종 정리 — [AUTO]_ 만 삭제 / [AUTO_KEEP]_ 은 보존 (sc6 연계 핸드오프)."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.common.control_suite._base import ControlSuiteBase


class TestZzCleanup(ControlSuiteBase):
    """nPouch 제어 스위트 — 최종 정리.

    cleanup 책임 분담 (사용자 결정 2026-05-28):
      - sc1 시작 (_ensure_session_cleanup) : AUTO + AUTO_KEEP 전부 삭제 (clean slate)
      - sc5 완료 (5c)                       : AUTO 만 삭제, AUTO_KEEP 보존
      - sc6                                 : AUTO_KEEP 존재/내용 확인 (다음 연계 사용 신호)
      - zz (여기)                           : AUTO 안전망 정리, AUTO_KEEP 보존
        → 다음 run 의 sc1 시작이 AUTO_KEEP 최종 정리 (zz 가 keep 을 지우면 sc6 '남겨둠' 의도와 충돌).
    """

    def test_zz_cleanup_keep(self, logged_in_page, settings):
        """[AUTO]_ 만 일괄 삭제 / [AUTO_KEEP]_ 보존 (다음 연계 대비)."""
        print("\n━━ [제어 스위트] 최종 cleanup (AUTO 만, AUTO_KEEP 보존) ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        deleted = page.delete_all_auto_policies()   # AUTO 만 삭제, AUTO_KEEP 보존
        names = page.get_policy_names()
        auto_leftover = [n for n in names if n.startswith("[AUTO]") and not n.startswith("[AUTO_KEEP]")]
        keep_left = [n for n in names if n.startswith("[AUTO_KEEP]")]

        self._add("pass" if not auto_leftover else "fail",
                  "최종 cleanup — [AUTO]_ 정책 전부 삭제",
                  f"입력: delete_all_auto_policies / 결과: 삭제={deleted}건, [AUTO] 잔여={auto_leftover}", sc=6)
        self._add("pass",
                  "최종 cleanup — [AUTO_KEEP]_ 보존 확인 (다음 연계/다음 run sc1 정리)",
                  f"결과: 보존된 [AUTO_KEEP]={keep_left or '(없음)'}", sc=6)
