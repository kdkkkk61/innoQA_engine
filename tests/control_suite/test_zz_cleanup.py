"""최종 정리 — [AUTO]_ + [AUTO_KEEP]_ 일괄 삭제."""
import pytest

from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.control_suite._base import ControlSuiteBase


class TestZzCleanup(ControlSuiteBase):
    """nPouch 제어 스위트 — 최종 정리 — [AUTO]_ + [AUTO_KEEP]_ 일괄 삭제"""


    def test_zz_cleanup_keep(self, logged_in_page, settings):
        """모든 [AUTO]_ + [AUTO_KEEP]_ 정책 일괄 삭제 (테스트 종료 정리)."""
        print("\n━━ [제어 스위트] 최종 cleanup ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()

        deleted = page.delete_all_test_data()
        names = page.get_policy_names()
        leftover = [n for n in names if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]

