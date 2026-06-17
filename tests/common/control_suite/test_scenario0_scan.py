"""제어 스위트 — UIScanner 기반 신규 기능 감지 + UI 패턴 자동 검증 (간편 스캔).

기존 시나리오 1~6 은 수동 검증 중심. 본 메서드는 UIScanner 호출 1회로
config/scan_hints/control_suite.yaml ↔ 실제 DOM 비교 → 두 가지 자동 처리:

  1. 신규 기능 감지 (시나리오 1 카드)
     - yaml 에 명시 안 됐는데 DOM 에 존재하는 input/checkbox/radio/textarea
     - "신규 기능 감지 — '한글라벨' (selector)" 형식으로 ScanResult 추가
     - 모달 영역 스크린샷 자동 첨부 → 검수자가 위치 확인 가능

  2. UI 요소 동작 자동 검증 (시나리오 2 카드)
     - text_input: maxlength / required / placeholder
     - toggle_checkbox / plain_checkbox: 클릭 동작 + 종속 필드 활성/비활성
     - radio_group: 초기값 / 옵션 클릭 동작

phase=2 단발 (ADD 모달만) — 정책 저장 안 함 / cancel 로 종료. 사용자 요구 "간편 실행".

다른 시나리오 (sc1~sc6) 와 완전 독립 — sc0 결과는 보고서에 별도 카드로 노출.
"""
import pytest

from core.ui_scanner import UIScanner
from pages.npouch_control_suite_page import NpouchControlSuitePage
from tests.common.control_suite._base import ControlSuiteBase


class TestScenario0Scan(ControlSuiteBase):
    """제어 스위트 — UIScanner 기반 자동 스캔 (시나리오 0)."""

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        """ADD 모달 — yaml ↔ DOM diff + UI 패턴 자동 검증."""
        print("\n━━ [제어 스위트] 시나리오 0a: UIScanner ADD 모달 자동 스캔 ━━━")
        page = NpouchControlSuitePage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        scanner = UIScanner(logged_in_page, config_dir="config")

        # phase=2 — ADD 모달 yaml ↔ DOM diff (시나리오 1) + UI 요소 자동 검증 (시나리오 2)
        # yaml 의 page_id="control_suite" 호출 (npouch_control_suite.yaml 가 referenced).
        report = scanner.scan(
            page_id="control_suite",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page.close_modal,
        )

        # 결과 분류 — sc0 라벨로 묶어 보고서 인라인 노출
        new_features = [r for r in report.results
                        if r.pattern == "discovered_new"]
        scan_fails  = [r for r in report.results
                       if r.status == "fail" and r.pattern != "discovered_new"]
        scan_warns  = [r for r in report.results
                       if r.status == "warn" and r.pattern != "discovered_new"]
        scan_pass   = [r for r in report.results
                       if r.status == "pass"]

        # 신규 기능 감지 라벨에 sc0 prefix 부착 + scenario tag (sub-num: sc0 = sn*100+1 = 1)
        for r in new_features:
            r.extra = r.extra or {}
            r.extra["scenario"] = 1   # sc0a 자동 매핑은 _attach 에서 처리
            if not r.label.startswith("sc0"):
                r.label = f"sc0a — {r.label}"

        # 자동 검증 결과 요약 (한 줄 통계 카드)
        self._add("warn" if new_features else "pass",
                  "sc0a — [UIScanner] 신규 기능 감지 자동 스캔 (yaml ↔ DOM diff)",
                  f"결과: 신규 감지={len(new_features)}건, "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, "
                  f"pass={len(scan_pass)}건",
                  sc=0)

        # 신규 기능 감지 카드 개별 노출 — UIScanner 가 만든 풍부한 detail 그대로 표시
        # (휴리스틱 결과 + yaml stub 추천 + DOM 속성 dump 다 포함).
        # 사용자 지적 (2026-05-29): 이전 코드가 r.detail 무시하고 selector 만 출력 → 휴리스틱
        # 검증 결과/stub 이 보고서에서 안 보이는 결함. 이제 r.detail 그대로 통과.
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
