"""
tests/test_ui_scan.py — UIScanner 기반 UI 패턴 스캔 테스트

기존 test_ransom_detect_policy.py와 역할 분리:
  기존 테스트: 비즈니스 로직 (정책 추가/수정/삭제) / 정확한 에러 메시지 검증
  이 파일:     UI 패턴 존재 / 속성 / 동작 구조 검증 (새 페이지 확장 대상)

실행:
  pytest tests/test_ui_scan.py -v -s
  pytest tests/ -m ui_scan -v -s   # ui_scan 마커만 선택 실행

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


@pytest.mark.ui_scan
class TestRansomDetectPolicyScan:

    def test_modal_ui_patterns(self, logged_in_page, settings, request):
        """
        정책 추가 모달 전체 UI 패턴 스캔.
        config/scan_hints/ransom_detect_policy.yaml 기준으로 검사.

        검증 항목:
          - toggle_checkbox × 6 (종속 필드 ON/OFF 동작 포함, known_bug 1건 제외)
          - plain_checkbox  × 4 (존재 여부)
          - radio_group     × 1 (4개 옵션 모두 존재)
          - text_input      × 1 (maxlength=20, required)
          - tag_input       × 4 (정책정보탭 1개 + 예외처리탭 3개)
        """
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()

        scanner = UIScanner(logged_in_page, config_dir="config")

        def open_modal() -> None:
            # open_add_modal() = click(SEL_ADD_BTN) + wait_for(SEL_ADD_MODAL)
            # QA AI의 click_add_button() + wait_for_modal() 분리 방식을 통합
            page_obj.open_add_modal()

        def close_modal() -> None:
            page_obj.close_modal()

        report: PageScanReport = scanner.scan(
            "ransom_detect_policy",
            modal_open_fn=open_modal,
            modal_close_fn=close_modal,
        )

        # request.node에 report 첨부 (tests/conftest.py의 hook에서 활용)
        request.node._scan_report = report

        # 결과 출력 (pytest -s 옵션으로 확인)
        print(f"\n{report.summary()}")
        status_icon = {
            "pass":      "✅",
            "fail":      "❌",
            "known_bug": "⚠️",
            "skip":      "⏭",
            "error":     "💥",
        }
        # 정렬: YAML order 값 우선 → 없으면 패턴 타입 순 폴백
        # YAML order가 있는 항목끼리 먼저 (0~), 없는 항목은 뒤로 (10000+)
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
        def _sort_key(r):
            if r.order is not None:
                return r.order
            return 10_000 + _PATTERN_FALLBACK.get(r.pattern, 99) * 10

        def _tab_for_order(order):
            """r.order가 속하는 탭 라벨 반환 (start_order 구간 판단)."""
            if order is None or not report.tab_sections:
                return None
            current = None
            for ts in report.tab_sections:
                if order >= ts["start_order"]:
                    current = ts["label"]
            return current

        sorted_results  = sorted(report.results, key=_sort_key)
        current_tab_label = None

        for r in sorted_results:
            # ── 탭 구간 헤더 (required_submit은 탭 구분 제외 — 종합 검증 항목)
            if r.pattern != "required_submit":
                tab_label = _tab_for_order(r.order)
                if tab_label != current_tab_label:
                    current_tab_label = tab_label
                    if current_tab_label:
                        bar = "─" * 14
                        print(f"\n  {bar} [ {current_tab_label} ] {bar}")

            icon = status_icon.get(r.status, "?")
            print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")
            # toggle_checkbox 종속 필드 서브아이템 — 각 필드 개별 상태로 아이콘 결정
            if r.pattern == "toggle_checkbox":
                dep_labels  = r.extra.get("dependent_labels",  [])
                dep_types   = r.extra.get("dependent_types",   [])
                dep_results = r.extra.get("dependent_results", [])
                for i, dep_label in enumerate(dep_labels):
                    dep_type   = dep_types[i]   if i < len(dep_types)   else "field"
                    dep_res    = dep_results[i]  if i < len(dep_results) else {}
                    dep_status = dep_res.get("status", "skip")
                    dep_icon   = status_icon.get(dep_status, "?")
                    print(f"       └ {dep_icon} [{dep_type}] {dep_label}")

        # known_bug는 fail 카운트에서 제외됨 (PageScanReport.failed 미포함)
        assert not report.failed, (
            f"UI 패턴 검사 실패 {len(report.failed)}건:\n"
            + "\n".join(
                f"  [{r.pattern}] {r.label}: {r.detail}"
                for r in report.failed
            )
        )
