"""
tests/test_ui_scan.py

UIScanner 기반 테스트.
기존 test_ransom_detect_policy.py와 역할 분리:
  - 기존 테스트: 비즈니스 로직 / 정확한 에러 메시지 검증
  - 이 파일:     UI 패턴 존재 / 속성 / 동작 구조 검증 (새 페이지 확장 대상)
"""

import pytest
from core.ui_scanner import UIScanner
from pages.ransom_detect_policy_page import RansomDetectPolicyPage


@pytest.mark.ui_scan
class TestRansomDetectPolicyScan:

    def test_modal_ui_patterns(self, logged_in_page, settings):
        """
        정책 추가 모달 전체 UI 패턴 스캔.
        scan_hints/ransom_detect_policy.yaml 기준으로 검사.
        """
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()

        scanner = UIScanner(logged_in_page, config_dir="config")

        def open_modal():
            page_obj.click_add_button()   # button#addItemBtn — AngularJS ng-click
            page_obj.wait_for_modal()

        def close_modal():
            page_obj.close_modal()

        report = scanner.scan(
            "ransom_detect_policy",
            modal_open_fn=open_modal,
            modal_close_fn=close_modal,
        )

        # 테스트 아이템에 report 첨부 (conftest teardown에서 활용)
        request = pytest.current_test_context()  # conftest에서 item에 주입
        if hasattr(request, "node"):
            request.node._scan_report = report

        # 결과 출력 (pytest -s 옵션으로 확인)
        print(f"\n{report.summary()}")
        for r in report.results:
            mark = {"pass": "✅", "fail": "❌", "known_bug": "⚠️", "skip": "⏭", "error": "💥"}.get(r.status, "?")
            print(f"  {mark} [{r.pattern}] {r.label}: {r.detail}")

        # known_bug는 fail 카운트에서 제외됨
        assert not report.failed, (
            f"UI 패턴 검사 실패 {len(report.failed)}건:\n"
            + "\n".join(f"  [{r.pattern}] {r.label}: {r.detail}" for r in report.failed)
        )
