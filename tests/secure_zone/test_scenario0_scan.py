"""시큐어존 접근제어 정책 — 시나리오 0: UIScanner 신규 기능 감지 + UI 자동 검증.

origin_protect sc0(tests/origin_protect/test_scenario0_scan.py) 동일 구조.
config/scan_hints/secure_zone_access_control.yaml ↔ 실제 DOM 비교 → 자동 처리:
  1. 신규 기능 감지 (yaml 미명시 요소 → "신규 기능 감지" 카드 + DOM 속성 + 휴리스틱 + yaml stub)
  2. 제거 기능 감지 (yaml에 있는데 DOM에 없음 → 회귀 후보)
  3. yaml 명세 UI 요소 자동 검증 (toggle gating / text maxlength / required submit)

phase=2 단발 (ADD 모달, 저장 안 함). 혹시 모를 제품 UI 변경(신규/제거) 회귀 감지용.
"""
from core.ui_scanner import UIScanner
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase


class TestSecureZoneAccessControlScenario0Scan(SecureZoneACBase):
    """접근제어 정책 — UIScanner 기반 자동 스캔 (시나리오 0)."""

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 0a: UIScanner ADD 모달 자동 스캔 ━━━")
        page = SecureZoneAccessControlPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_access_control",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page.close_modal,
        )

        new_features = [r for r in report.results if r.pattern == "discovered_new"]
        missing      = [r for r in report.results if r.pattern == "discovered_missing"]
        scan_fails   = [r for r in report.results
                        if r.status == "fail" and r.pattern not in ("discovered_new", "discovered_missing")]
        scan_warns   = [r for r in report.results
                        if r.status == "warn" and r.pattern not in ("discovered_new", "discovered_missing")]
        scan_pass    = [r for r in report.results if r.status == "pass"]

        self._add("warn" if (new_features or missing) else "pass",
                  "sc0a — [UIScanner] 신규/제거 기능 감지 자동 스캔 (yaml ↔ DOM diff)",
                  f"결과: 신규={len(new_features)}건, 제거={len(missing)}건, "
                  f"UI 검증 fail={len(scan_fails)}, warn={len(scan_warns)}, pass={len(scan_pass)}",
                  sc=0)

        # 신규/제거 카드 개별 노출 (UIScanner 풍부 detail 그대로)
        for r in new_features + missing:
            extra = r.extra or {}
            lines = [r.detail or ""]
            if extra.get("screenshot"):
                lines.append(f"캡처: {extra['screenshot']}")
            self._add("warn", r.label, "\n".join(lines), sc=0)

        # yaml 명세 UI 자동 검증 fail/warn 개별 노출
        for r in scan_fails + scan_warns:
            self._add(r.status, f"sc0a — [UI 패턴] {r.label}",
                      r.detail or f"selector: {r.selector!r}", sc=0)
