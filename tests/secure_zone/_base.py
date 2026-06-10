"""시큐어존 접근제어 정책 — 공유 base class + ScanResult 헬퍼.

nPouch origin_protect(tests/origin_protect/_base.py) 패턴 복제.
각 시나리오 파일(test_scenario1..5)이 SecureZoneACBase 상속.

접근제어 정책은 템플릿/제어스위트 의존 없는 독립 페이지 →
교차 연계([AUTO_KEEP])는 없고, 페이지 내부 시나리오 lifecycle(sc3 ADD → sc4 EDIT)만 연계.
"""
import re
import time
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport

_SS_DIR = Path(__file__).parent.parent.parent / "reports" / "screenshots"


def _ss(page, label: str, highlight=None) -> str | None:
    """fail/warn 캡처 — highlight(Locator) 있으면 빨간 outline + 스크롤 후 캡처."""
    try:
        _SS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w가-힣]", "_", label)[:40]
        path = _SS_DIR / f"BUG_{safe}_{int(time.time()*1000)}.png"
        injected = False
        if highlight is not None:
            try:
                highlight.first.scroll_into_view_if_needed(timeout=1000)
                highlight.first.evaluate(
                    "el => { el.style.outline='3px solid #ff2d2d';"
                    " el.style.outlineOffset='2px';"
                    " el.style.boxShadow='0 0 0 6px rgba(255,45,45,0.25)'; }"
                )
                injected = True
            except Exception:
                injected = False
        page.screenshot(path=str(path))
        if injected:
            try:
                highlight.first.evaluate(
                    "el => { el.style.outline=''; el.style.outlineOffset='';"
                    " el.style.boxShadow=''; }"
                )
            except Exception:
                pass
        return str(path)
    except Exception:
        return None


_STATUS_ICON  = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]", "warn": "[WARN]"}
_STATUS_TO_SR = {"pass": "pass", "fail": "fail", "warn": "warn", "skip": "skip"}


def _r(status: str, label: str, detail: str = "", sc: int = 0,
       page=None, highlight=None) -> tuple[str, ScanResult]:
    icon = _STATUS_ICON.get(status, "?")
    text = f"  {icon} {label}" + (f": {detail}" if detail else "")
    extra: dict = {"scenario": sc}
    if page and status in ("fail", "warn"):
        ss_path = _ss(page, label, highlight=highlight)
        if ss_path:
            extra["screenshot"] = ss_path
    sr = ScanResult(
        pattern="scenario_test", selector="", label=label,
        status=_STATUS_TO_SR.get(status, status), detail=detail, extra=extra,
    )
    return text, sr


class SecureZoneACBase:
    """시큐어존 접근제어 정책 시나리오 공통 base."""

    PAGE_ID = "secure_zone_access_control"

    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """session 시작 [AUTO] 일괄 정리 (1회). 접근제어는 [AUTO_KEEP] 없음(독립 페이지)."""
        if SecureZoneACBase._SESSION_CLEANUP_DONE:
            return
        try:
            page.page.wait_for_timeout(200)
            before = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
            page.delete_all_auto_policies()
            if hasattr(self, "_add"):
                self._add("pass",
                          "sc1 — session 시작 cleanup ([AUTO] 일괄 삭제, clean slate)",
                          f"잔여: {len(before)}건 {before} (sc3 ADD 중복 방지)", sc=1)
        except Exception as e:
            if hasattr(self, "_add"):
                self._add("warn", "sc1 — session cleanup 예외", f"예외: {e!r}", sc=1)
        SecureZoneACBase._SESSION_CLEANUP_DONE = True

    def _attach(self, scan_results: list[ScanResult]) -> None:
        try:
            nm = self._request.node.name
            m = re.match(r"test_scenario(\d+)([a-z])_", nm)
            if m:
                sn = int(m.group(1))
                sub = ord(m.group(2)) - ord("a") + 1
                if sn != 0:
                    new_sc = sn * 100 + sub
                    for r in scan_results:
                        cur = (r.extra or {}).get("scenario")
                        if cur in (None, 0, sn):
                            if r.extra is None:
                                r.extra = {}
                            r.extra["scenario"] = new_sc
        except Exception:
            pass
        report = PageScanReport(page_id=self.PAGE_ID)
        report.results = scan_results
        self._request.node._scan_report    = report
        self._request.node._npouch_page_id = self.PAGE_ID

    _SC_DEFAULT_TIMEOUT = 5000

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None
        # crash 시점 page_id 추출 보장 (error 카운트 누락 방지)
        request.node._npouch_page_id = self.PAGE_ID
        try:
            if "logged_in_page" in request.fixturenames:
                p = request.getfixturevalue("logged_in_page")
                p.set_default_timeout(self._SC_DEFAULT_TIMEOUT)
        except Exception:
            pass
        yield
        if self._srs and not getattr(self._request.node, "_scan_report", None):
            self._attach(self._srs)
        try:
            p = (self._request.node.funcargs.get("logged_in_page")
                 or self._request.node.funcargs.get("fresh_page"))
            if p is not None:
                # teardown: full reload 제거(속도 — 39회 reload + 풀 네비게이션 비용 제거).
                # 모달/백드롭만 JS로 청소하면 다음 테스트 navigate_to 의 early-return 가드가
                # 유지돼 App Setting→SecureZone 아코디언 재네비게이션을 건너뛴다.
                # 열린 모달은 다음 navigate_to 의 _close_modal_if_open() 가 닫음.
                try:
                    p.evaluate(
                        "() => { "
                        "document.querySelectorAll('.modal-backdrop').forEach(b => b.remove()); "
                        "document.body.classList.remove('modal-open'); "
                        "document.body.style.removeProperty('padding-right'); "
                        "}"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _add(self, status: str, label: str, detail: str = "", sc: int = 0,
             highlight=None) -> None:
        """sub-numbering + ScanResult 누적 (origin_protect _base 동일)."""
        try:
            nm = self._request.node.name
            m = re.match(r"test_scenario(\d+)([a-z])_", nm)
            if m:
                sn = int(m.group(1))
                sub = ord(m.group(2)) - ord("a") + 1
                if sn != 0 and sc in (0, sn):
                    sc = sn * 100 + sub
        except Exception:
            pass
        t, s = _r(status, label, detail, sc=sc,
                  page=self._page if status in ("fail", "warn") else None,
                  highlight=highlight if status in ("fail", "warn") else None)
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)
