"""시큐어존 템플릿(프로세스) — UIScanner 자동 스캔 (sc0). 폴더동기화 sc0 미러.

yaml ↔ DOM diff → 추가(discovered_new)/삭제(discovered_missing)/숨김(discovered_hidden) 감지.
프로세스 탭은 모달이 5개(1단계 + 타입종속 L3 4종) → 스캔 5개(yaml 분리).
0a — 1단계 템플릿 모달 / 0b~0e — L3 허용/거부/예외처리/실행차단.
⚠ EXCEPT 드라이브 권한 radio 는 id(#ALLOW/#BLOCK) 중복 — yaml 에 쌍 1회 등재(존재 감지),
  그룹별 동작은 sc2/sc3 수동 담당 (docs/scenario_0_scan.md §3).
"""
import re as _re

from core.ui_scanner import UIScanner
from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario0Scan(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — UIScanner 자동 스캔 (시나리오 0)."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _report_scan(self, report, tag: str) -> None:
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
                  f"{tag} — [UIScanner] 변경사항 감지 (yaml ↔ DOM diff)",
                  f"변경사항: 추가={len(added)}건, 삭제={len(deleted)}건, 숨김={len(hidden)}건 / "
                  f"UI 검증 fail={len(scan_fails)}건, warn={len(scan_warns)}건, pass={len(scan_pass)}건",
                  sc=0)
        for kind, items in (("추가", added), ("삭제", deleted), ("숨김", hidden)):
            for r in items:
                name = _re.sub(r"^(신규|제거된|숨겨진) 기능 감지 — ", "", r.label or "")
                self._add("warn", f"{tag} — 변경사항({kind}) — {name}",
                          r.detail or "", sc=0, screenshot=False)
        for r in scan_fails + scan_warns:
            self._add(r.status, f"{tag} — [UI 패턴] {r.label}",
                      r.detail or f"selector: {r.selector!r}", sc=0)

    # ── 0a: 1단계 템플릿 모달 ─────────────────────────────────────────
    def test_scenario0a_stage1_modal_scan(self, logged_in_page, settings):
        print("\n━━ [프로세스] 시나리오 0a: UIScanner 1단계 모달 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_process",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page._close_modal_if_open,
        )
        self._report_scan(report, "sc0a(1단계 모달)")

    # ── 0b~0e: L3 타입종속 4종 ────────────────────────────────────────
    def _scan_l3(self, logged_in_page, settings, ttype: str, key: str, tag: str):
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = f"[AUTO]_sz_proc_sc0_{key}"
        page.ensure_template(tpl, ttype)
        page.navigate_to()

        def _open():
            page.open_l2_modal(tpl)
            page.open_l3_add(ttype)

        def _close():
            page.close_l3_modal(ttype)
            page.close_l2_modal()

        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id=f"secure_zone_template_process_l3_{key}",
            phase=2,
            modal_open_fn=_open,
            modal_close_fn=_close,
        )
        self._report_scan(report, tag)

    def test_scenario0b_l3_allow_scan(self, logged_in_page, settings):
        print("\n━━ [프로세스] 시나리오 0b: L3 허용 스캔 ━━━")
        self._scan_l3(logged_in_page, settings, "ALLOW_PROCESS", "allow", "sc0b(L3 허용)")

    def test_scenario0c_l3_deny_scan(self, logged_in_page, settings):
        print("\n━━ [프로세스] 시나리오 0c: L3 거부 스캔 ━━━")
        self._scan_l3(logged_in_page, settings, "DENY_PROCESS", "deny", "sc0c(L3 거부)")

    def test_scenario0d_l3_except_scan(self, logged_in_page, settings):
        print("\n━━ [프로세스] 시나리오 0d: L3 예외처리 스캔 ━━━")
        self._scan_l3(logged_in_page, settings, "EXCEPT_PROCESS", "except", "sc0d(L3 예외처리)")

    def test_scenario0e_l3_block_scan(self, logged_in_page, settings):
        print("\n━━ [프로세스] 시나리오 0e: L3 실행차단 스캔 ━━━")
        self._scan_l3(logged_in_page, settings, "BLOCK_PROCESS", "block", "sc0e(L3 실행차단)")
