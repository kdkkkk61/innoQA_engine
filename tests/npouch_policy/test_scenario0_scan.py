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

        # 결과 분류 — 변경사항 3종: 추가/삭제/숨김 (baseline yaml ↔ 실제 DOM diff).
        #   추가(discovered_new)     = DOM에만 존재 (yaml 미정의)
        #   삭제(discovered_missing) = yaml에만 존재, DOM 미발견 (그냥 삭제)
        #   숨김(discovered_hidden)  = yaml+DOM 둘 다 있으나 display:none (있는데 안 보임)
        _DISCOVERY = ("discovered_new", "discovered_missing", "discovered_hidden")
        added   = [r for r in report.results if r.pattern == "discovered_new"]
        deleted = [r for r in report.results if r.pattern == "discovered_missing"]
        hidden  = [r for r in report.results if r.pattern == "discovered_hidden"]
        scan_fails  = [r for r in report.results
                       if r.status == "fail" and r.pattern not in _DISCOVERY]
        scan_warns  = [r for r in report.results
                       if r.status == "warn" and r.pattern not in _DISCOVERY]
        scan_pass   = [r for r in report.results if r.status == "pass"]

        # 요약 — 변경사항 통합
        changed = len(added) + len(deleted) + len(hidden)
        self._add("warn" if changed else "pass",
                  "sc0a — [UIScanner] 변경사항 감지 (baseline yaml ↔ 실제 DOM diff)",
                  f"변경사항: 추가={len(added)}건, 삭제={len(deleted)}건, 숨김={len(hidden)}건 / "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, pass={len(scan_pass)}건",
                  sc=0)

        # 변경사항 카드 개별 노출 — "변경사항(종류) — 기능명 (selector)" 로 간결화.
        #   r.label 의 "신규/제거된/숨겨진 기능 감지 — " prefix 는 변경사항(종류)와 중복 → 제거.
        #   스크린샷 없음: 삭제=요소 없음 / 숨김=display:none / 모달도 이미 닫힘 → 기본화면만 찍혀 무의미.
        import re as _re
        for kind, items in (("추가", added), ("삭제", deleted), ("숨김", hidden)):
            for r in items:
                name = _re.sub(r"^(신규|제거된|숨겨진) 기능 감지 — ", "", r.label or "")
                self._add("warn", f"변경사항({kind}) — {name}",
                          r.detail or "", sc=0, screenshot=False)

        # UI 검증 fail/warn 개별 노출
        for r in scan_fails + scan_warns:
            self._add(r.status, f"sc0a — [UI 패턴] {r.label}",
                      r.detail or f"selector: {r.selector!r}", sc=0)
