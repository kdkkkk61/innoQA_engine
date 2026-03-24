"""
tests/test_rdp_policy_scan.py — RDP 정책 UI 패턴 스캔 테스트

대상 페이지: RansomCruncher > RDP 정책 (managerRansomCruncherRdpPolicy)

기존 test_ui_scan.py(탐지정책)와 역할 분리:
  탐지정책 테스트: 복잡한 토글+종속필드+태그입력+예외처리탭
  이 파일:         RDP 정책 연결설정 라디오그룹 + 요일 체크박스 + 필수 제출 검증

[스캔 항목]
  test_rdp_modal_ui_patterns      : ADD 모달 전체 UI 패턴 스캔
    - radio_group × 2 (연결 설정, 연결 시간 제한)
    - plain_checkbox × 7 (적용 요일 일~토)
    - text_input × 1 (정책 이름)
    - required_submit × 1 (이름 필수 검증)
    - 스캔 완료 후 [AUTO]_rdp_ui_scan 정책으로 저장

  test_rdp_modal_ui_patterns_edit : EDIT 모달 스캔 + 정책 삭제
    - ADD에서 생성한 [AUTO]_rdp_ui_scan 정책 사용
    - 스캔 완료 후 [AUTO] 정책 정리

실행:
  pytest tests/test_rdp_policy_scan.py -v -s
  pytest tests/ -m ui_scan -v -s
"""

import pytest
from core.ui_scanner import UIScanner, PageScanReport
from pages.rdp_policy_page import RdpPolicyPage

_STATUS_ICON = {
    "pass":      "✅",
    "fail":      "❌",
    "known_bug": "⚠️",
    "skip":      "⏭",
    "error":     "💥",
}
_PATTERN_FALLBACK = {
    "modal_open":      0,
    "text_input":      1,
    "radio_group":     2,
    "toggle_checkbox": 3,
    "plain_checkbox":  4,
    "tag_input":       5,
    "required_submit": 6,
    "auto_detect":     7,
}


def _print_scan_report(report: PageScanReport) -> None:
    """스캔 결과를 출력한다."""
    if report is None:
        print("\n[스캔 결과 없음]")
        return
    print(f"\n{report.summary()}")

    def _sort_key(r):
        if r.order is not None:
            return r.order
        return 10_000 + _PATTERN_FALLBACK.get(r.pattern, 99) * 10

    sorted_results = sorted(report.results, key=_sort_key)
    for r in sorted_results:
        icon = _STATUS_ICON.get(r.status, "?")
        print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")


@pytest.mark.ui_scan
class TestRdpPolicyScan:

    def test_rdp_modal_ui_patterns(self, logged_in_page, settings, request):
        """
        [ADD 모달] RDP 정책 추가 모달 전체 UI 패턴 스캔.
        config/scan_hints/rdp_policy.yaml 기준으로 검사.

        검증 항목:
          - radio_group × 2 (연결 설정 2옵션, 연결 시간 제한 2옵션)
          - plain_checkbox × 7 (적용 요일 일~토)
          - text_input × 1 (정책 이름 — maxlength 속성 없음, 앱 레벨 required)
          - required_submit × 1 (이름 미입력 → 경고, 이름 입력 → 저장 성공)

        스캔 완료 후 [AUTO]_rdp_ui_scan 정책으로 저장.
        """
        page_obj = RdpPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()
        page_obj.delete_all_auto_policies()

        def close_and_save():
            """스캔 완료 후 [AUTO]_rdp_ui_scan 정책으로 저장."""
            page_obj.fill(page_obj.SEL_POLICY_NAME, "[AUTO]_rdp_ui_scan")
            page_obj.click_attached(page_obj.SEL_REGISTER_BTN)
            page_obj.page.locator(page_obj.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=page_obj._TIMEOUT_MODAL
            )
            page_obj.click_attached(page_obj.SEL_CONFIRM_BTN)
            page_obj.wait_for_modal_closed()
            page_obj.wait_for(page_obj.SEL_ADD_BTN)

        scanner = UIScanner(logged_in_page, config_dir="config")
        report: PageScanReport = scanner.scan(
            "rdp_policy",
            modal_open_fn=page_obj.open_add_modal,
            modal_close_fn=close_and_save,
        )

        request.node._scan_report = report
        _print_scan_report(report)

        assert not report.failed, (
            f"UI 패턴 검사 실패 {len(report.failed)}건:\n"
            + "\n".join(
                f"  [{r.pattern}] {r.label}: {r.detail}"
                for r in report.failed
            )
        )

    def test_rdp_modal_ui_patterns_edit(self, logged_in_page, settings, request):
        """
        [EDIT 모달] RDP 정책 수정 모달 UI 패턴 스캔.

        흐름:
          ① [AUTO]_rdp_ui_scan 정책 확인 (test_rdp_modal_ui_patterns에서 생성됨)
             없으면 직접 생성 (test 1 실패 대비 fallback)
          ② EDIT 모달 열기 → UIScanner 스캔
          ③ [AUTO] 정책 삭제 (스캔 성공/실패 무관하게 항상 정리)
        """
        page_obj = RdpPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()

        test_name = "[AUTO]_rdp_ui_scan"
        if test_name not in page_obj.get_policy_names():
            test_name = page_obj.add_policy("[AUTO]_rdp_ui_scan")

        scanner = UIScanner(logged_in_page, config_dir="config")
        report: PageScanReport | None = None

        try:
            report = scanner.scan(
                "rdp_policy",
                modal_open_fn=lambda: page_obj.open_modify_modal(test_name),
                modal_close_fn=page_obj.close_modal,
            )
        finally:
            try:
                page_obj.navigate_to()
                page_obj.delete_all_auto_policies()
            except Exception:
                pass

        request.node._scan_report = report
        _print_scan_report(report)

        assert not report.failed, (
            f"UI 패턴 검사 실패 {len(report.failed)}건:\n"
            + "\n".join(
                f"  [{r.pattern}] {r.label}: {r.detail}"
                for r in report.failed
            )
        )
