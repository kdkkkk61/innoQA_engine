"""시큐어존 템플릿(특수폴더) — UIScanner 기반 자동 스캔 (sc0).

npouch_policy/test_scenario0_scan.py 패턴 복제 (사용자 지시 2026-07-02 — 기능 삭제 감지 포함).
yaml ↔ 실제 DOM 비교 → 변경사항 3종 감지:
  추가(discovered_new)     = DOM에만 존재 (yaml 미정의 — 신규 기능)
  삭제(discovered_missing) = yaml에만 존재, DOM 미발견 (기능 삭제)
  숨김(discovered_hidden)  = yaml+DOM 둘 다 있으나 display:none (detect_hidden 켠 yaml 만)

특수폴더는 모달이 3개라 스캔도 3개(yaml 파일 분리):
  0a — 1단계 템플릿 모달 (secure_zone_template_manage_folder.yaml)
  0b — 내용 모달(바로가기 SHORTCUT) (…_content.yaml)
  0c — 내용 모달(레지스트리 MODIFY_REGIST) (…_content_regist.yaml)
⚠ 원본/대상위치(contenteditable div)는 UIScanner DOM 추출 미지원 → diff 대상 아님(수동 sc1~5 담당).
"""
import re as _re

import pytest

from core.ui_scanner import UIScanner
from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario0Scan(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — UIScanner 자동 스캔 (시나리오 0)."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _report_scan(self, report, tag: str) -> None:
        """scan 결과 분류 → 카드 (npouch_policy sc0 과 동일 분류)."""
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
        # 변경사항 카드 개별 노출 (요소별) — 스크린샷 없음: 삭제=요소 없음/숨김=display:none 이라 화면 증거 무의미
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
        print("\n━━ [특수폴더] 시나리오 0a: UIScanner 1단계 모달 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_manage_folder",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page._close_modal_if_open,
        )
        self._report_scan(report, "sc0a(1단계 모달)")

    # ── 0b: 내용 모달 (바로가기 SHORTCUT) ─────────────────────────────
    def test_scenario0b_content_shortcut_scan(self, logged_in_page, settings):
        print("\n━━ [특수폴더] 시나리오 0b: UIScanner 내용 모달(바로가기) 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_sc0"
        page.ensure_template(tpl, "SHORTCUT")

        def _open():
            page.open_folder_modal(tpl)
            page.open_content_add()

        def _close():
            page.close_content_modal()
            page.close_folder_modal()

        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_manage_folder_content",
            phase=2,
            modal_open_fn=_open,
            modal_close_fn=_close,
        )
        self._report_scan(report, "sc0b(내용 모달·바로가기)")

    # ── 0c: 내용 모달 (레지스트리 MODIFY_REGIST) ──────────────────────
    def test_scenario0c_content_regist_scan(self, logged_in_page, settings):
        print("\n━━ [특수폴더] 시나리오 0c: UIScanner 내용 모달(레지스트리) 스캔 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_sc0r"
        page.ensure_template(tpl, "MODIFY_REGIST")

        def _open():
            page.open_folder_modal(tpl)
            page.open_content_add()

        def _close():
            page.close_content_modal()
            page.close_folder_modal()

        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="secure_zone_template_manage_folder_content_regist",
            phase=2,
            modal_open_fn=_open,
            modal_close_fn=_close,
        )
        self._report_scan(report, "sc0c(내용 모달·레지스트리)")
