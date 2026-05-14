"""nPouch 제어 스위트 — 공유 base class + ScanResult/스크린샷 헬퍼.

각 시나리오 파일 (test_scenario{1..5}*.py / test_zz_cleanup.py) 는
`ControlSuiteBase` 를 상속받아 자기 시나리오 메서드만 정의한다.
"""
import re
import time
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport


# ── 스크린샷 헬퍼 ──────────────────────────────────────────────────
_SS_DIR = Path(__file__).parent.parent.parent / "reports" / "screenshots"


def _ss(page, label: str) -> str | None:
    """warn/fail 시점 스크린샷 저장 → 경로 반환."""
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
    """print 라인 + ScanResult 동시 생성. warn/fail 이면 스크린샷 자동 첨부.
    sc = 시나리오 번호 (1~5)."""
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


def _assert_no_fail(lines: list[str], context: str = "") -> None:
    """[FAIL] 항목이 없어야 통과."""
    failed = [r for r in lines if "[FAIL]" in r]
    if failed:
        raise AssertionError(f"{context} 실패 항목:\n" + "\n".join(failed))


class ControlSuiteBase:
    """nPouch 제어 스위트 시나리오 공통 base.

    각 시나리오 class 는 이 base 를 상속받아 자기 시나리오 메서드만 정의한다.
    """

    PAGE_ID = "npouch_control_suite"

    def _attach(self, scan_results: list[ScanResult]) -> None:
        """PageScanReport 를 test node 에 첨부 — conftest 가 수집해서 html_reporter 로 전달."""
        report = PageScanReport(page_id=self.PAGE_ID)
        report.results = scan_results
        self._request.node._scan_report    = report
        self._request.node._npouch_page_id = self.PAGE_ID

    def _emit_pass(self, label: str, sc: int) -> None:
        """test 가 통과되면 끝에 호출 — 단일 pass ScanResult 첨부."""
        sr = ScanResult(
            pattern="scenario_test", selector="", label=label,
            status="pass", detail="", extra={"scenario": sc},
        )
        self._attach([sr])

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        """매 테스트 시작 — request + ScanResult 누적 리스트 초기화."""
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None    # _add 의 fail 스크린샷용 — test 메서드가 세팅
        yield
        # ScanResult fallback attach
        if self._srs and not getattr(self._request.node, "_scan_report", None):
            self._attach(self._srs)
        # 매 테스트 끝 — modal/backdrop 강제 정리 (다음 테스트 영향 방지)
        page_obj = request.node.funcargs.get("logged_in_page")
        if page_obj is not None:
            try:
                page_obj.evaluate("""
                    () => {
                        document.querySelectorAll('div.modal-wrap.in, div.modal.in').forEach(m => {
                            m.classList.remove('in');
                            m.style.display = 'none';
                        });
                        document.querySelectorAll('div.modal-backdrop').forEach(b => b.remove());
                        document.body.classList.remove('modal-open');
                        document.body.style.paddingRight = '';
                        document.body.style.overflow = '';
                    }
                """)
            except Exception:
                pass

    def _add(self, status: str, label: str, detail: str = "", sc: int = 0) -> None:
        """한 줄로 print + ScanResult 누적. 각 검증 블록 단위 호출."""
        t, s = _r(status, label, detail, sc=sc,
                  page=self._page if status in ("fail", "warn") else None)
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)

    def _finish(self, context: str = "") -> None:
        """메서드 끝 호출 — attach + FAIL 어서션."""
        self._attach(self._srs)
        _assert_no_fail(self._lines, context=context)
