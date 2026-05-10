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
        page                    : Playwright Page 객체
        log                     : scan_logger 인스턴스
        known_bugs              : known_bugs.yaml 로드 결과
        extra                   : 테스트 파일에서 주입하는 런타임 컨텍스트
                                  (existing_name, verify_values 등)
        phase                   : 현재 스캔 단계 (1/2/3/0)
        last_warning_text       : dismiss_warning_dialog 호출 시 캡처된 경고 메시지
        last_warning_screenshot : dismiss_warning_dialog 호출 시 dismiss 직전에
                                  캡처된 스크린샷 경로 (모달 + cause가 한 프레임에 담김).
                                  None = 경고 모달 없었거나 캡처 실패.
                                  validator는 status 판정 후 fail/warn에만 사용한다.
    """
    page:                    Page
    log:                     object                  # scan_logger (duck-typed)
    known_bugs:              list[dict]    = field(default_factory=list)
    extra:                   dict          = field(default_factory=dict)
    phase:                   int           = 0
    last_warning_text:       str           = ""
    last_warning_screenshot: str | None    = None

    # ── 공용 상수 ──────────────────────────────────────────────────────────────
    # 앱 공통 경고 다이얼로그 (login_page.py SEL_ERROR_MODAL과 동일)
    SEL_WARN_MODAL: str = "div#__globalMessageModal.in"
    TAB_SETTLE_MS:  int = 300

    # ── 탭 활성화 ─────────────────────────────────────────────────────────────

    def activate_tab(self, tab: dict) -> bool:
        """
        YAML에 정의된 탭을 활성화한다.

        우선순위:
          1. data_tab 속성 기준  (data_tab 키 사용)
          2. 텍스트 기준 폴백    (tab_text 키 사용 — data-tab 없는 제품, 예: innoMark)

        반환:
            True  = 탭 정상 활성화
            False = 경고 다이얼로그 출현으로 탭 전환 차단됨
        """
        import time as _time
        t0 = _time.time()
        data_tab = tab.get("data_tab", "")
        tab_text = tab.get("tab_text", "")
        hint     = data_tab or tab_text or "(unknown)"
        self.log.debug(f"[tab] 활성화 시도: {hint!r}")
        result = True
        try:
            tab_link = None
            # ① data_tab 속성 기준 (기존 방식)
            if data_tab:
                loc = self.page.locator(f'a[data-tab="{data_tab}"]')
                if loc.count() > 0:
                    tab_link = loc.first
                else:
                    self.log.debug(f"[tab] data-tab 탭 없음: {data_tab!r}")

            # ② 텍스트 기준 폴백 (innoMark 등 data-tab 없는 제품)
            if tab_link is None and tab_text:
                loc = self.page.locator(f'ul.nav li a:has-text("{tab_text}")')
                if loc.count() > 0:
                    tab_link = loc.first
                else:
                    self.log.debug(f"[tab] tab_text 탭 없음: {tab_text!r}")

            if tab_link is not None:
                tab_link.evaluate("el => el.click()")
                self.page.wait_for_timeout(self.TAB_SETTLE_MS)
                if self.dismiss_warning_dialog():
                    self.log.debug(f"[tab] 경고 다이얼로그로 차단됨: {hint!r}")
                    print(f"[TIMING]   activate_tab {hint!r} BLOCKED {(_time.time()-t0)*1000:.0f}ms")
                    return False
            else:
                self.log.debug(f"[tab] 탭 링크 미발견 — data_tab={data_tab!r} / tab_text={tab_text!r}")
                print(f"[TIMING]   activate_tab {hint!r} NO-LINK {(_time.time()-t0)*1000:.0f}ms")
                return True
        except Exception:
            self.log.debug(f"[tab] 예외 발생:\n{traceback.format_exc()}")
            print(f"[TIMING]   activate_tab {hint!r} EXC {(_time.time()-t0)*1000:.0f}ms")
            return True
        self.log.debug(f"[tab] 활성화 완료: {hint!r}")
        print(f"[TIMING]   activate_tab {hint!r} OK {(_time.time()-t0)*1000:.0f}ms")
        return True

    # ── 경고 다이얼로그 ────────────────────────────────────────────────────────

    def dismiss_warning_dialog(self) -> bool:
        """
        탭 전환 등으로 출현하는 경고 다이얼로그를 감지하고 닫는다.

        주의: .modal.in 전체 탐색 금지 → addItemModal의 닫기 버튼까지 포함되어
              메인 모달이 닫힘 — 반드시 #__globalMessageModal 직접 지정 필요.

        부수효과:
            self.last_warning_text       : 경고 메시지 텍스트 (없으면 "")
            self.last_warning_screenshot : dismiss 직전 캡처 경로 (없으면 None)
                                           → 모달 + 뒤로 비치는 입력값이 한 프레임에 담김

        반환:
            True  = 다이얼로그가 있었고 닫음
            False = 다이얼로그 없음
        """
        import time as _time
        t0 = _time.time()
        self.last_warning_text       = ""
        self.last_warning_screenshot = None
        try:
            warn_modal = self.page.locator(self.SEL_WARN_MODAL)
            if warn_modal.count() == 0:
                print(f"[TIMING]     dismiss_warning_dialog: no-modal {(_time.time()-t0)*1000:.0f}ms")
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
            # 스크린샷 캡처 (dismiss 전 — cause + effect 한 프레임)
            # validator가 status 판정 후 fail/warn일 때만 ScanResult.extra에 첨부.
            t_ss = _time.time()
            try:
                self.last_warning_screenshot = self.take_screenshot("warning_dialog")
            except Exception:
                self.log.debug(
                    f"[warn_dialog] 스크린샷 실패:\n{traceback.format_exc()}"
                )
            ss_ms = (_time.time()-t_ss)*1000
            confirm = warn_modal.locator("button")
            if confirm.count() > 0:
                self.log.debug("[warn_dialog] 확인 버튼 클릭")
                confirm.first.evaluate("el => el.click()")
                self.page.wait_for_timeout(300)
                total_ms = (_time.time()-t0)*1000
                print(
                    f"[TIMING]     dismiss_warning_dialog: dismissed total={total_ms:.0f}ms "
                    f"ss={ss_ms:.0f}ms text={self.last_warning_text!r:.60}"
                )
                return True
            else:
                self.log.debug("[warn_dialog] 버튼 없음 — 닫기 불가")
        except Exception:
            self.log.debug(f"[warn_dialog] 예외 발생:\n{traceback.format_exc()}")
        print(f"[TIMING]     dismiss_warning_dialog: fallthrough {(_time.time()-t0)*1000:.0f}ms")
        return False

    # ── 결과 헬퍼 ────────────────────────────────────────────────────────────

    def append_error(
        self,
        report:   PageScanReport,
        pattern:  str,
        selector: str,
        label:    str,
        order=None,
        phase:    int = 0,
    ) -> None:
        """예외 발생 시 로그 기록 후 ScanResult(error)를 report에 추가한다."""
        tb = traceback.format_exc()
        self.log.error(f"[{pattern}] {label!r} ({selector}) 예외 발생:\n{tb}")
        report.results.append(ScanResult(
            pattern=pattern, selector=selector, label=label,
            status="error", detail=tb, order=order, phase=phase,
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

    def take_screenshot(self, label: str, element_sel: str | None = None) -> str | None:
        """결함 발견 시점 스크린샷 저장.

        element_sel:
          None      : viewport 캡처 (기본 — 보이는 영역만)
          CSS sel   : 해당 element 전체 캡처 (스크롤 영역 포함)
                      모달처럼 viewport보다 큰 영역 통째 보고 싶을 때 사용.
        """
        import time as _time
        t0 = _time.time()
        mode = "element" if element_sel else "viewport"
        try:
            from pathlib import Path
            from datetime import datetime
            ss_dir = Path("reports/screenshots")
            ss_dir.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now().strftime("%H%M%S_%f")[:9]
            safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in label)[:35]
            path = ss_dir / f"BUG_{safe}_{ts}.png"
            # overlay 항상 ON 유지 — hide/show evaluate 제거.
            # 스크린샷에 overlay (0.15 검정 + 배너) 살짝 비침 → "테스트 진행 중" 표식 활용.
            # Playwright loc.screenshot(timeout=N) 파라미터가 무시되어 30초 hang 발생 (실측).
            # 원인: actionability/stability 내부 대기가 timeout 무시.
            # 해결: element 캡처 시도 자체 안 함 → 항상 viewport 캡처.
            # 손실: 모달 스크롤 아래 영역 캡처 X. 그러나 원래도 30초 hang 후 fail로 캡처 안 됐음.
            # element_sel 인자는 mode 라벨용으로만 사용.
            self.page.screenshot(path=str(path))
            if element_sel:
                mode = f"viewport(skip-element:{element_sel})"
            ms = (_time.time()-t0)*1000
            print(f"[TIMING]       take_screenshot {label!r} {mode} {ms:.0f}ms → {path.name}")
            return str(path)
        except Exception as e:
            ms = (_time.time()-t0)*1000
            print(f"[TIMING]       take_screenshot {label!r} FAILED {ms:.0f}ms: {e}")
            return None

    @staticmethod
    def status_detail(failures: list[str], checks: list[str]) -> tuple[str, str]:
        """failures/checks 리스트에서 status·detail 문자열을 생성한다."""
        status = "fail" if failures else "pass"
        detail = "; ".join(failures) if failures else " + ".join(checks)
        return status, detail
