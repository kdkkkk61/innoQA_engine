"""
tests/test_ui_scan.py — UIScanner 기반 UI 패턴 스캔 테스트

기존 test_ransom_detect_policy.py와 역할 분리:
  기존 테스트: 비즈니스 로직 (정책 추가/수정/삭제) / 정확한 에러 메시지 검증
  이 파일:     UI 패턴 존재 / 속성 / 동작 구조 검증 (새 페이지 확장 대상)

실행:
  pytest tests/test_ui_scan.py -v -s
  pytest tests/ -m ui_scan -v -s   # ui_scan 마커만 선택 실행

[두 가지 스캔 단계 — ADD 모달은 전체 흐름에서 1회만 열림]
  test_modal_ui_patterns      : ADD 모달 스캔 + [AUTO] 정책 생성
    - ADD 모달 열기 → 전체 UI 패턴 스캔 → 스캔 완료 후 [AUTO]_ui_scan 으로 저장
    - 예외처리 탭 이동 차단 확인 (ADD 모달 특성)
    - 저장된 정책을 test_modal_ui_patterns_edit 에서 재사용 (ADD 모달 중복 열기 방지)
  test_modal_ui_patterns_edit : EDIT 모달 스캔 + 정책 삭제
    - test_modal_ui_patterns 에서 생성한 [AUTO]_ui_scan 정책 사용
    - 정책 없을 경우(test 1 실패 등) 직접 생성 (fallback)
    - EDIT 모달에서 탭 이동 자유 → tag 추가/삭제 동작 테스트 실행
    - 예외처리 탭 (파일경로/프로세스경로/전자서명 예외처리) 동작 검증 포함
    - 스캔 완료 후 [AUTO] 정책 정리 (성공/실패 무관)

[버그 수정 이력]
  QA AI 원본 버그 ①: pytest.current_test_context() — 존재하지 않는 API
    수정: request fixture 파라미터로 받아 request.node에 직접 첨부

  QA AI 원본 버그 ②: page_obj.click_add_button() — 존재하지 않는 메서드
  QA AI 원본 버그 ③: page_obj.wait_for_modal()   — 존재하지 않는 메서드
    수정: open_add_modal() 하나로 통합 (click + wait 내부 처리)
"""

import pytest
from core.ui_scanner import UIScanner, PageScanReport
from pages.ransom_detect_policy_page import RansomDetectPolicyPage

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
    """스캔 결과를 탭 구간 헤더 포함하여 출력한다."""
    print(f"\n{report.summary()}")

    def _sort_key(r):
        if r.order is not None:
            return r.order
        return 10_000 + _PATTERN_FALLBACK.get(r.pattern, 99) * 10

    def _tab_for_order(order):
        if order is None or not report.tab_sections:
            return None
        current = None
        for ts in report.tab_sections:
            if order >= ts["start_order"]:
                current = ts["label"]
        return current

    sorted_results    = sorted(report.results, key=_sort_key)
    current_tab_label = None

    for r in sorted_results:
        if r.pattern != "required_submit":
            tab_label = _tab_for_order(r.order)
            if tab_label != current_tab_label:
                current_tab_label = tab_label
                if current_tab_label:
                    bar = "─" * 14
                    print(f"\n  {bar} [ {current_tab_label} ] {bar}")

        icon = _STATUS_ICON.get(r.status, "?")
        print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")
        if r.pattern == "toggle_checkbox":
            dep_labels  = r.extra.get("dependent_labels",  [])
            dep_types   = r.extra.get("dependent_types",   [])
            dep_results = r.extra.get("dependent_results", [])
            for i, dep_label in enumerate(dep_labels):
                dep_type   = dep_types[i]   if i < len(dep_types)   else "field"
                dep_res    = dep_results[i]  if i < len(dep_results) else {}
                dep_status = dep_res.get("status", "skip")
                dep_icon   = _STATUS_ICON.get(dep_status, "?")
                dep_detail = dep_res.get("detail", "")
                detail_str = f" — {dep_detail}" if dep_detail else ""
                print(f"       └ {dep_icon} [{dep_type}] {dep_label}{detail_str}")


@pytest.mark.ui_scan
class TestRansomDetectPolicyScan:

    def test_modal_ui_patterns(self, logged_in_page, settings, request):
        """
        [ADD 모달] 정책 추가 모달 전체 UI 패턴 스캔.
        config/scan_hints/ransom_detect_policy.yaml 기준으로 검사.

        검증 항목:
          - toggle_checkbox × 6 (종속 필드 ON/OFF+입력 동작 포함, known_bug 1건 제외)
          - plain_checkbox  × 4 (라벨 클릭 동작)
          - radio_group     × 1 (4개 옵션 존재 + 클릭 변경)
          - text_input      × 1 (maxlength=20, required)
          - tag_input       × 4 (ADD 모달 예외처리 탭 차단 → 동작 테스트 자동 스킵)

        스캔 완료 후 [AUTO]_ui_scan 정책으로 저장 → test_modal_ui_patterns_edit 선행 조건.
        (ADD 모달을 스캔과 정책 생성에 중복 사용하지 않도록 close_fn에서 저장 처리)
        """
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()
        page_obj.delete_all_auto_policies()   # 이전 실행 잔여 정리

        def close_and_save():
            """스캔 완료 후 [AUTO]_ui_scan 정책으로 저장."""
            # 스캐너가 extension "txt" 를 추가했으므로 이름만 채우고 저장
            page_obj.fill(page_obj.SEL_POLICY_NAME, "[AUTO]_ui_scan")
            page_obj.click(page_obj.SEL_REGISTER_BTN)
            page_obj.page.locator(page_obj.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=page_obj._TIMEOUT_MODAL
            )
            page_obj.click_attached(page_obj.SEL_CONFIRM_BTN)
            page_obj.wait_for_modal_closed()
            page_obj.wait_for(page_obj.SEL_ADD_BTN)

        scanner = UIScanner(logged_in_page, config_dir="config")

        report: PageScanReport = scanner.scan(
            "ransom_detect_policy",
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

    def test_modal_ui_patterns_edit(self, logged_in_page, settings, request):
        """
        [EDIT 모달] 수정 모달 UI 패턴 스캔.
        ADD 모달에서 불가했던 tag 추가/삭제 동작 + 예외처리 탭 검증 포함.

        흐름:
          ① [AUTO]_ui_scan 정책 확인 (test_modal_ui_patterns에서 생성됨)
             없으면 직접 생성 (test 1 실패 대비 fallback — ADD 모달 이때만 열림)
          ② EDIT 모달 열기 → UIScanner 스캔
             - 탭 이동 자유 → 예외처리 탭 접근 가능
             - tag 추가/삭제 동작 테스트 실행
          ③ [AUTO] 정책 삭제 (스캔 성공/실패 무관하게 항상 정리)
        """
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()

        # ① [AUTO]_ui_scan 정책 확인 — test_modal_ui_patterns close_fn에서 생성됨
        # 없는 경우(test 1 실패 등) fallback 생성 (이때만 ADD 모달 추가 열림)
        test_name = "[AUTO]_ui_scan"
        if test_name not in page_obj.get_policy_names():
            test_name = page_obj.add_policy("[AUTO]_ui_scan", ["txt"])

        scanner = UIScanner(logged_in_page, config_dir="config")
        report: PageScanReport | None = None

        try:
            report = scanner.scan(
                "ransom_detect_policy",
                modal_open_fn=lambda: page_obj.open_modify_modal(test_name),
                modal_close_fn=page_obj.close_modal,
            )
        finally:
            # ③ 임시 정책 삭제 (scan 예외 발생해도 반드시 정리)
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
