"""nPouch 원본보호 정책 — 공유 base class + ScanResult 헬퍼.

제어 스위트(tests/control_suite/_base.py) 패턴 복제.
각 시나리오 파일 (test_scenario1..6, test_zz_cleanup) 이 OriginProtectBase 상속.

의존성: 제어 스위트 [AUTO_KEEP]_sc5_step1 (sc5 lifecycle 종료 후 보존 정책) 을
       원본보호 정책 ADD 시 CSU select 로 연계.
"""
import re
import time
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport


# ── 스크린샷 헬퍼 (control_suite _base 와 동일) ────────────────────
_SS_DIR = Path(__file__).parent.parent.parent / "reports" / "screenshots"


def _ss(page, label: str) -> str | None:
    try:
        _SS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w가-힣]", "_", label)[:40]
        path = _SS_DIR / f"BUG_{safe}_{int(time.time()*1000)}.png"
        page.screenshot(path=str(path))
        return str(path)
    except Exception:
        return None


_STATUS_ICON  = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]", "warn": "[WARN]"}
_STATUS_TO_SR = {"pass": "pass", "fail": "fail", "warn": "warn", "skip": "skip"}


def _r(status: str, label: str, detail: str = "", sc: int = 0,
       page=None) -> tuple[str, ScanResult]:
    icon = _STATUS_ICON.get(status, "?")
    text = f"  {icon} {label}" + (f": {detail}" if detail else "")
    extra: dict = {"scenario": sc}
    if page and status in ("fail", "warn"):
        ss_path = _ss(page, label)
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


class OriginProtectBase:
    """nPouch 원본보호 정책 시나리오 공통 base."""

    PAGE_ID = "npouch_origin_protect"

    # session-level cleanup 1회 flag (control_suite 와 별도 영역)
    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """session 시작 [AUTO]_ + [AUTO_KEEP]_ 일괄 정리 (1회).

        TODO: page 클래스에 delete_all_test_data() 메서드 구현 후 활성화.
              현재는 페이지 자체 cleanup helper 가 없어 no-op (sc1 추가 시 보강).
        """
        if OriginProtectBase._SESSION_CLEANUP_DONE:
            return
        try:
            if hasattr(page, "delete_all_test_data"):
                page.page.wait_for_timeout(500)
                before = [n for n in page.get_policy_names()
                          if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
                if before:
                    print(f"[session cleanup] 원본보호 시작 잔여 {len(before)}건: {before}")
                deleted = page.delete_all_test_data()
                print(f"[session cleanup] 원본보호 삭제 {deleted}건")
        except Exception as e:
            print(f"[session cleanup] 원본보호 예외: {e!r}")
        OriginProtectBase._SESSION_CLEANUP_DONE = True

    def _attach(self, scan_results: list[ScanResult]) -> None:
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
                p.wait_for_timeout(500)
        except Exception:
            pass

    def _add(self, status: str, label: str, detail: str = "", sc: int = 0) -> None:
        # sub-numbering — 메서드 이름 'test_scenarioNX_...' 에서 자동 추출 → sc = N*100 + sub
        # (sn*100 체계: a~z 전부 안전 — sc3j/sc3k 같은 j/k 도 충돌 없음)
        try:
            nm = self._request.node.name
            m = re.match(r"test_scenario(\d+)([a-z])_", nm)
            if m:
                sn = int(m.group(1))
                sub = ord(m.group(2)) - ord("a") + 1
                if sc in (0, sn):
                    sc = sn * 100 + sub
        except Exception:
            pass
        t, s = _r(status, label, detail, sc=sc,
                  page=self._page if status in ("fail", "warn") else None)
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)
