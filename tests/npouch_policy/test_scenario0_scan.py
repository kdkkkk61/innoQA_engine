"""nPouch 엔파우치 정책 — UIScanner 기반 자동 스캔 (sc0).

origin_protect/test_scenario0_scan.py 패턴 복제.
config/scan_hints/npouch_policy.yaml ↔ 실제 DOM 비교 → 자동 처리:
  1. 신규 기능 감지 (yaml 미명시 요소 발견)
  2. UI 요소 동작 자동 검증 (text/toggle/radio)

phase=2 단발 (ADD 모달만, 정책 저장 안 함).
"""
import pytest

from core.ui_scanner import UIScanner
from pages.npouch_policy_page import NpouchPolicyPage
from tests.npouch_policy._base import NpouchPolicyBase


class TestScenario0Scan(NpouchPolicyBase):
    """엔파우치 정책 — UIScanner 기반 자동 스캔 (시나리오 0)."""

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        """ADD 모달 — yaml ↔ DOM diff + UI 패턴 자동 검증."""
        print("\n━━ [엔파우치 정책] 시나리오 0a: UIScanner ADD 모달 자동 스캔 ━━━")
        page = NpouchPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        scanner = UIScanner(logged_in_page, config_dir="config")

        # phase=2 — ADD 모달 yaml ↔ DOM diff + UI 자동 검증
        report = scanner.scan(
            page_id="npouch_policy",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page.close_modal,
        )

        # 결과 분류
        new_features = [r for r in report.results if r.pattern == "discovered_new"]
        scan_fails  = [r for r in report.results
                       if r.status == "fail" and r.pattern != "discovered_new"]
        scan_warns  = [r for r in report.results
                       if r.status == "warn" and r.pattern != "discovered_new"]
        scan_pass   = [r for r in report.results if r.status == "pass"]

        # 요약
        self._add("warn" if new_features else "pass",
                  "sc0a — [UIScanner] 신규 기능 감지 자동 스캔 (yaml ↔ DOM diff)",
                  f"결과: 신규 감지={len(new_features)}건, "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, "
                  f"pass={len(scan_pass)}건",
                  sc=0)

        # 신규 기능 감지 카드 개별 노출
        for r in new_features:
            extra = r.extra or {}
            ss = extra.get("screenshot")
            detail_lines = [r.detail or ""]
            if ss:
                detail_lines.append(f"캡처: {ss}")
            self._add("warn", r.label, "\n".join(detail_lines), sc=0)

        # UI 검증 fail/warn 개별 노출
        for r in scan_fails + scan_warns:
            self._add(r.status, f"sc0a — [UI 패턴] {r.label}",
                      r.detail or f"selector: {r.selector!r}", sc=0)
