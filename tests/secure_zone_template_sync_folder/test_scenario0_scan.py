"""시큐어존 템플릿(폴더동기화) — UIScanner 기반 자동 스캔 (sc0). 특수폴더 sc0 미러.

yaml ↔ 실제 DOM 비교 → 변경사항 3종 감지:
  추가(discovered_new)     = DOM에만 존재 (yaml 미정의 — 신규 기능)
  삭제(discovered_missing) = yaml에만 존재, DOM 미발견 (기능 삭제)
  숨김(discovered_hidden)  = yaml+DOM 둘 다 있으나 display:none (detect_hidden)

폴더동기화는 모달 2개라 스캔 2개(yaml 파일 분리):
  0a — 1단계 템플릿 모달 (secure_zone_template_sync_folder.yaml)
  0b — 내용 모달 (…_content.yaml)
⚠ 원본/대상위치(contenteditable div)·isExtensionInclude radio(id 없음)·스케줄 조건부 하위필드(기본 숨김)는
  스키마에서 의도적 제외(오탐 방지) → sc1/sc2 수동 검증 담당.
"""
import re as _re

from core.ui_scanner import UIScanner
from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase


class TestSecureZoneTemplateSyncFolderScenario0Scan(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — UIScanner 자동 스캔 (시나리오 0)."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _report_scan(self, report, tag: str) -> None:
        """scan 결과 분류 → 카드 (추가/삭제/숨김 + UI 패턴 fail/warn)."""
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
        print("\n━━ [폴더동기화] 시나리오 0a: UIScanner 1단계 모달 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_sync_folder",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page._close_modal_if_open,
        )
        self._report_scan(report, "sc0a(1단계 모달)")

    # ── 0b: 내용 모달 ─────────────────────────────────────────────────
    def test_scenario0b_content_modal_scan(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] 시나리오 0b: UIScanner 내용 모달 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_sync_sc0"
        page.ensure_template(tpl)
        page.navigate_to()

        def _open():
            page.open_folder_modal(tpl)
            page.open_content_add()

        def _close():
            page.close_content_modal()
            page.close_folder_modal()

        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_sync_folder_content",
            phase=2,
            modal_open_fn=_open,
            modal_close_fn=_close,
        )
        self._report_scan(report, "sc0b(내용 모달)")
