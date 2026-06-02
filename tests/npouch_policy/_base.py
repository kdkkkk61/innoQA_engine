"""nPouch 엔파우치 정책 — 공유 base class + ScanResult 헬퍼.

origin_protect/_base.py 패턴 복제 (사용자 명령 2026-06-01).
각 시나리오 파일 (test_scenario0..6) 이 NpouchPolicyBase 상속.

cleanup 정책 (origin_protect 동일):
  - sc1 시작: AUTO + AUTO_KEEP 둘 다 cleanup (clean slate)
  - sc2/3/4: cleanup 없음
  - sc5c: AUTO 만 cleanup, KEEP 보존 (sc6 / 다음 페이지 연계)

의존성: 원본보호 정책 [AUTO_KEEP]_sc5_origin_protect 를 정책 ADD 시 원본보호 정책 선택으로 연계.
"""
import re
import time
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport


# ── 스크린샷 헬퍼 (origin_protect _base 와 동일) ────────────────
_SS_DIR = Path(__file__).parent.parent.parent / "reports" / "screenshots"


def _ss(page, label: str, highlight=None) -> str | None:
    """fail/warn 캡처 — highlight (Locator) 있으면 빨간 outline + 스크롤 후 캡처."""
    try:
        _SS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w가-힣]", "_", label)[:40]
        path = _SS_DIR / f"BUG_{safe}_{int(time.time()*1000)}.png"
        injected = False
        if highlight is not None:
            try:
                highlight.first.scroll_into_view_if_needed(timeout=1000)
                highlight.first.evaluate(
                    "el => { el.setAttribute('data-qa-hl','1');"
                    " el.style.outline='3px solid #ff2d2d';"
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
                    "el => { el.style.outline='';"
                    " el.style.outlineOffset='';"
                    " el.style.boxShadow='';"
                    " el.removeAttribute('data-qa-hl'); }"
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
        pattern="scenario_test",
        selector="",
        label=label,
        status=_STATUS_TO_SR.get(status, status),
        detail=detail,
        extra=extra,
    )
    return text, sr


class NpouchPolicyBase:
    """nPouch 엔파우치 정책 시나리오 공통 base."""

    PAGE_ID = "npouch_policy"

    # session-level cleanup 1회 flag (origin_protect 와 별도 영역)
    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """session 시작 [AUTO]_ + [AUTO_KEEP]_ 일괄 정리 (1회).

        사용자 설계 (origin_protect 동일):
          - sc1 시작: AUTO + AUTO_KEEP 둘 다 cleanup (clean slate)
          - sc2/3/4: cleanup 없음
          - sc5c: AUTO 만 cleanup, KEEP 보존
        """
        if NpouchPolicyBase._SESSION_CLEANUP_DONE:
            return
        try:
            if hasattr(page, "delete_all_test_data"):
                page.page.wait_for_timeout(200)
                before = [n for n in page.get_policy_names()
                          if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
                deleted = page.delete_all_test_data()
                if hasattr(self, "_add"):
                    self._add("pass",
                              "sc1 — session 시작 cleanup ([AUTO] + [AUTO_KEEP] 일괄 삭제, clean slate)",
                              f"잔여: {len(before)}건 {before} / deleted={deleted} (sc3 ADD 중복 방지)",
                              sc=1)
                else:
                    print(f"[session cleanup] nPouch 정책 잔여 {len(before)}건 / 삭제 {deleted}건")
        except Exception as e:
            if hasattr(self, "_add"):
                self._add("warn", "sc1 — session cleanup 예외", f"예외: {e!r}", sc=1)
            else:
                print(f"[session cleanup] nPouch 정책 예외: {e!r}")
        NpouchPolicyBase._SESSION_CLEANUP_DONE = True

    def _attach(self, scan_results: list[ScanResult]) -> None:
        # 자동 sub-num 재태깅 안전망
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
                p.set_default_timeout(30000)
                p.reload(wait_until="domcontentloaded", timeout=15000)
                p.wait_for_timeout(200)
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
        """sub-numbering + ScanResult 누적."""
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
        # 매 _add 호출 시 _attach — hook 이 call 단계에서 _scan_report 잡을 수 있게
        # (origin_protect _base.py:223 패턴, 사용자 보고 2026-06-01 HTML 보고서 누락 fix)
        self._attach(self._srs)
