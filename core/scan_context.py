"""
core/scan_context.py — ScanContext

UIScanner 와 각 validator가 공유하는 상태·헬퍼 모음.
page, log, known_bugs를 하나의 객체로 묶어 validators에 전달한다.
"""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from playwright.sync_api import Page

from core.models import PageScanReport, ScanResult


@dataclass
class ScanContext:
    """
    스캔 컨텍스트 — validators에 전달되는 공유 상태 + 헬퍼.

    Attributes:
        page              : Playwright Page 객체
        log               : scan_logger 인스턴스
        known_bugs        : known_bugs.yaml 로드 결과
        extra             : 테스트 파일에서 주입하는 런타임 컨텍스트
                            (existing_name, verify_values 등)
        phase             : 현재 스캔 단계 (1/2/3/0)
        last_warning_text : dismiss_warning_dialog 호출 시 캡처된 경고 메시지
    """
    page:              Page
    log:               object                  # scan_logger (duck-typed)
    known_bugs:        list[dict] = field(default_factory=list)
    extra:             dict       = field(default_factory=dict)
    phase:             int        = 0
    last_warning_text: str        = ""

    # ── 공용 상수 ──────────────────────────────────────────────────────────────
    # 앱 공통 경고 다이얼로그 (login_page.py SEL_ERROR_MODAL과 동일)
    SEL_WARN_MODAL: str = "div#__globalMessageModal.in"
    TAB_SETTLE_MS:  int = 300

    # ── 탭 활성화 ─────────────────────────────────────────────────────────────

    def activate_tab(self, tab: dict) -> bool:
        """
        YAML에 정의된 탭을 활성화한다 (data_tab 속성 기준).

        반환:
            True  = 탭 정상 활성화
            False = 경고 다이얼로그 출현으로 탭 전환 차단됨
        """
        data_tab = tab.get("data_tab", "")
        self.log.debug(f"[tab] 활성화 시도: data_tab={data_tab!r}")
        try:
            tab_link = self.page.locator(f'a[data-tab="{data_tab}"]')
            if tab_link.count() > 0:
                tab_link.first.evaluate("el => el.click()")
                self.page.wait_for_timeout(self.TAB_SETTLE_MS)
                if self.dismiss_warning_dialog():
                    self.log.debug(f"[tab] 경고 다이얼로그로 차단됨: {data_tab!r}")
                    return False
            else:
                self.log.debug(f"[tab] 탭 링크 없음: a[data-tab={data_tab!r}]")
        except Exception:
            self.log.debug(f"[tab] 예외 발생:\n{traceback.format_exc()}")
        self.log.debug(f"[tab] 활성화 완료: {data_tab!r}")
        return True

    # ── 경고 다이얼로그 ────────────────────────────────────────────────────────

    def dismiss_warning_dialog(self) -> bool:
        """
        탭 전환 등으로 출현하는 경고 다이얼로그를 감지하고 닫는다.

        주의: .modal.in 전체 탐색 금지 → addItemModal의 닫기 버튼까지 포함되어
              메인 모달이 닫힘 — 반드시 #__globalMessageModal 직접 지정 필요.

        부수효과:
            self.last_warning_text 에 경고 메시지 텍스트를 저장한다.
            경고 없으면 빈 문자열로 초기화.

        반환:
            True  = 다이얼로그가 있었고 닫음
            False = 다이얼로그 없음
        """
        self.last_warning_text = ""
        try:
            warn_modal = self.page.locator(self.SEL_WARN_MODAL)
            if warn_modal.count() == 0:
                return False
            self.log.debug(f"[warn_dialog] 경고 모달 감지됨 ({self.SEL_WARN_MODAL})")
            # 텍스트 캡처 (dismiss 전)
            try:
                body = warn_modal.locator(".modal-body")
                if body.count() > 0:
                    self.last_warning_text = body.inner_text().strip()
                    self.log.debug(f"[warn_dialog] 텍스트: {self.last_warning_text!r}")
            except Exception:
                pass
            confirm = warn_modal.locator("button")
            if confirm.count() > 0:
                self.log.debug("[warn_dialog] 확인 버튼 클릭")
                confirm.first.evaluate("el => el.click()")
                self.page.wait_for_timeout(300)
                return True
            else:
                self.log.debug("[warn_dialog] 버튼 없음 — 닫기 불가")
        except Exception:
            self.log.debug(f"[warn_dialog] 예외 발생:\n{traceback.format_exc()}")
        return False

    # ── 결과 헬퍼 ────────────────────────────────────────────────────────────

    def append_error(
        self,
        report:   PageScanReport,
        pattern:  str,
        selector: str,
        label:    str,
        order=None,
    ) -> None:
        """예외 발생 시 로그 기록 후 ScanResult(error)를 report에 추가한다."""
        tb = traceback.format_exc()
        self.log.error(f"[{pattern}] {label!r} ({selector}) 예외 발생:\n{tb}")
        report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="error", detail=tb, order=order,
        ))

    def is_known_bug(self, selector: str, test_name: str) -> bool:
        """
        selector + test_name 조합이 known_bugs에 등록되어 있는지 확인한다.

        status 처리:
          "open"   (기본값) → known_bug 처리 (fail 카운트 제외, 추적 중)
          "fixed"           → known_bug 아님 → 여전히 실패하면 fail (회귀 감지)
          "wont_fix"        → known_bug 처리 (의도된 동작으로 확정)
        """
        for bug in self.known_bugs:
            if bug.get("selector") == selector and bug.get("test_name") == test_name:
                status = bug.get("status", "open")
                return status != "fixed"
        return False

    @staticmethod
    def status_detail(failures: list[str], checks: list[str]) -> tuple[str, str]:
        """failures/checks 리스트에서 status·detail 문자열을 생성한다."""
        status = "fail" if failures else "pass"
        detail = "; ".join(failures) if failures else " + ".join(checks)
        return status, detail
