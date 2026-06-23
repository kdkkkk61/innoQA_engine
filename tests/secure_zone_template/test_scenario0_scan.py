"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 0: UIScanner 자동 스캔 (방식 B).

nPouch 정책 sc0(tests/npouch_policy/test_scenario0_scan.py) 패턴 — 가장 최근.
config/scan_hints/secure_zone_template_secure_drive.yaml ↔ 실제 DOM(메인 ADD 모달) 비교:
  변경사항 3종 — 추가(discovered_new) / 삭제(discovered_missing) / 숨김(discovered_hidden, detect_hidden:true)
  + yaml 명세 UI 요소 자동 검증(text maxlength / checkbox 토글 / 필수제출).
phase=2 단발 (ADD 모달, 저장 안 함). 제품 UI 변경(신규/제거/숨김) 회귀 감지 + 요소 자동 캡처.

⚠️ 시큐어드라이브 항목은 서브모달(addSecureDrive)이라 메인 모달 스캔엔 안 잡힘 → 수동 sc2/sc3 검증.
"""
from core.ui_scanner import UIScanner
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario0Scan(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — UIScanner 자동 스캔 (시나리오 0)."""

    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 0a: UIScanner ADD 모달 자동 스캔 ━━━")
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_secure_drive",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page.close_modal,
        )

        _DISCOVERY = ("discovered_new", "discovered_missing", "discovered_hidden")
        added   = [r for r in report.results if r.pattern == "discovered_new"]
        deleted = [r for r in report.results if r.pattern == "discovered_missing"]
        hidden  = [r for r in report.results if r.pattern == "discovered_hidden"]
        scan_fails = [r for r in report.results
                      if r.status == "fail" and r.pattern not in _DISCOVERY]
        scan_warns = [r for r in report.results
                      if r.status == "warn" and r.pattern not in _DISCOVERY]
        scan_pass  = [r for r in report.results if r.status == "pass"]

        changed = len(added) + len(deleted) + len(hidden)
        self._add("warn" if changed else "pass",
                  "sc0a — [UIScanner] 변경사항 감지 (baseline yaml ↔ 실제 DOM diff)",
                  f"변경사항: 추가={len(added)}건, 삭제={len(deleted)}건, 숨김={len(hidden)}건 / "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, pass={len(scan_pass)}건",
                  sc=0)

        import re as _re
        for kind, items in (("추가", added), ("삭제", deleted), ("숨김", hidden)):
            for r in items:
                name = _re.sub(r"^(신규|제거된|숨겨진) 기능 감지 — ", "", r.label or "")
                self._add("warn", f"변경사항({kind}) — {name}",
                          r.detail or "", sc=0, screenshot=False)

        for r in scan_fails + scan_warns:
            self._add(r.status, f"sc0a — [UI 패턴] {r.label}",
                      r.detail or f"selector: {r.selector!r}", sc=0)
