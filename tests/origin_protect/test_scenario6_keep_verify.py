"""원본보호 정책 — 시나리오 6 — KEEP 정책 존재 확인 (단일 페이지 마무리).

사용자 설계 (docs/scan-architecture.md 6.6 / 2026-06-01):
  - 단일 페이지 테스트: sc6 = KEEP 정책 존재 확인 1건 (간단)
  - 여러 페이지 통합: sc6 = KEEP 다음 페이지 연계 (별도 — 원본보호 미해당)

원본보호 = 단일 페이지 → sc6 = sc5 lifecycle 완결 후 KEEP 보존 사실 확인.
"""
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase
# pytest 가 import 된 Test* 클래스를 또 수집하지 않도록 alias 사용
# (alias 없이 import 시 sc6 파일에서 sc5 클래스가 재수집돼 sc5a/b/c 가 2회 실행됨)
from tests.origin_protect.test_scenario5_lifecycle import (
    TestOriginProtectScenario5Lifecycle as _Sc5Lifecycle,
)


class TestOriginProtectScenario6KeepVerify(OriginProtectBase):
    """원본보호 정책 — sc6: KEEP 정책 존재 확인 (lifecycle 완결)."""

    def test_scenario6_keep_policy_exists(self, logged_in_page, settings):
        """sc6 — KEEP 정책 ([AUTO_KEEP]_sc5_origin_protect) 존재 확인."""
        print("\n━━ [원본보호 정책] 시나리오 6: KEEP 정책 보존 확인 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        NAME = _Sc5Lifecycle.LIFECYCLE_NAME
        exists = page.is_policy_exists(NAME)
        self._add("pass" if exists else "fail",
                  "sc6 — KEEP 정책 보존 확인 (lifecycle 완결)",
                  f"입력: {NAME!r} / 결과: exists={exists} "
                  f"(sc5 lifecycle 종료 후 보존 여부 — 단일 페이지 마무리)",
                  sc=6)
