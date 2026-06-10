"""시큐어존 접근제어 정책 — 시나리오 6: 연계 데이터 준비 (해당 없음).

표준 sc6 = 다음 페이지가 쓸 [AUTO_<날짜>] KEEP 항목 생성 후 남겨둠.
접근제어 정책은 독립 페이지(템플릿/제어스위트 등 다른 시큐어존 페이지가 참조하지 않음) →
교차 연계 대상 없음 → SKIP 명시 (표준: '해당 시나리오 없으면 SKIP 사유 출력').
"""
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase


class TestSecureZoneAccessControlScenario6Suite(SecureZoneACBase):
    """접근제어 정책 — 시나리오 6: 연계 (해당 없음)."""

    def test_scenario6a_no_linkage(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 6: 연계 데이터 준비 (해당 없음) ━━━")
        # 페이지 객체 생성만 (세션 검증) — 실제 연계 없음
        self._page = SecureZoneAccessControlPolicyPage(logged_in_page, settings).page
        self._add("skip", "sc6 — 연계 데이터 준비 해당 없음",
                  "접근제어 정책은 독립 페이지 — 다른 시큐어존 페이지가 참조하지 않음 "
                  "([AUTO_<날짜>] KEEP 교차연계 대상 없음)", sc=6)
