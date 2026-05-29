"""원본보호 정책 — UIScanner 기반 신규 기능 감지 + UI 패턴 자동 검증 (간편 스캔).

제어스위트 sc0 (tests/control_suite/test_scenario0_scan.py) 와 동일 구조.
config/scan_hints/npouch_origin_protect_policy.yaml ↔ 실제 DOM 비교 → 자동 처리:

  1. 신규 기능 감지 (시나리오 1 카드)
     - yaml 미명시 요소 발견 시 "신규 기능 감지 — [type] '한글라벨' (selector)" 카드
     - DOM 속성 자동 dump + 휴리스틱 click 토글 결과 + yaml stub 추천 detail 안에 합침
     - 모달 영역 스크린샷 자동 첨부

  2. UI 요소 동작 자동 검증 (시나리오 2 카드, yaml 명세된 요소에 한해)
     - text_input: maxlength / required
     - toggle_checkbox: 클릭 동작 + 종속 disabled
     - radio_group: 초기값 / 옵션 클릭

phase=2 단발 (ADD 모달만) — 정책 저장 안 함 / cancel 로 종료. "간편 실행".

다른 시나리오 (sc1~sc3o) 와 완전 독립 — sc0 결과는 보고서에 별도 카드 그룹으로 노출.
"""
import pytest

from core.ui_scanner import UIScanner
from pages.npouch_origin_protect_policy_page import NpouchOriginProtectPolicyPage
from tests.origin_protect._base import OriginProtectBase


class TestScenario0Scan(OriginProtectBase):
    """원본보호 정책 — UIScanner 기반 자동 스캔 (시나리오 0)."""

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        """ADD 모달 — yaml ↔ DOM diff + UI 패턴 자동 검증."""
        print("\n━━ [원본보호 정책] 시나리오 0a: UIScanner ADD 모달 자동 스캔 ━━━")
        page = NpouchOriginProtectPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        scanner = UIScanner(logged_in_page, config_dir="config")

        # phase=2 — ADD 모달 yaml ↔ DOM diff (시나리오 1) + UI 요소 자동 검증 (시나리오 2)
        # yaml page_id="npouch_origin_protect" 호출.
        report = scanner.scan(
            page_id="npouch_origin_protect",
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

        # 자동 검증 결과 요약 (한 줄 통계 카드)
        self._add("warn" if new_features else "pass",
                  "sc0a — [UIScanner] 신규 기능 감지 자동 스캔 (yaml ↔ DOM diff)",
                  f"결과: 신규 감지={len(new_features)}건, "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, "
                  f"pass={len(scan_pass)}건",
                  sc=0)

        # 신규 기능 감지 카드 개별 노출 — UIScanner 가 만든 풍부한 detail 그대로 표시
        # (휴리스틱 결과 + yaml stub 추천 + DOM 속성 dump 다 포함).
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
