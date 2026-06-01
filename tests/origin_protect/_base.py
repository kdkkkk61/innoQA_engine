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


def _ss(page, label: str, highlight=None) -> str | None:
    """fail/warn 캡처 — highlight (Locator) 가 있으면 빨간 outline + 스크롤 후 전체 캡처.

    highlight 가 None 이면 기존 동작 (전체 페이지). 모달 안 검증처럼 어느 영역인지
    시각적으로 명확해야 하는 경우 호출부에서 locator 를 넘긴다.
    """
    try:
        _SS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w가-힣]", "_", label)[:40]
        path = _SS_DIR / f"BUG_{safe}_{int(time.time()*1000)}.png"
        injected = False
        if highlight is not None:
            try:
                # 보이는 영역으로 스크롤 + 빨간 outline 임시 주입
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


class OriginProtectBase:
    """nPouch 원본보호 정책 시나리오 공통 base."""

    PAGE_ID = "npouch_origin_protect"

    # session-level cleanup 1회 flag (control_suite 와 별도 영역)
    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """session 시작 [AUTO]_ + [AUTO_KEEP]_ 일괄 정리 (1회).

        사용자 설계 (2026-05-29):
          - sc1 시작: AUTO + AUTO_KEEP 둘 다 cleanup (clean slate, 중복 이름 방지)
          - sc2/3/4: cleanup 없음
          - sc5c: AUTO 만 cleanup, KEEP 보존

        보고서에 cleanup 행위 명시 (사용자 보고 2026-06-01):
          - 이전: print 만 → 보고서에 cleanup 행위 표시 안 됨
          - 수정: _add 호출하여 sc=1 로 보고서에 명시
        """
        if OriginProtectBase._SESSION_CLEANUP_DONE:
            return
        try:
            if hasattr(page, "delete_all_test_data"):
                page.page.wait_for_timeout(500)
                before = [n for n in page.get_policy_names()
                          if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
                deleted = page.delete_all_test_data()
                # 보고서 명시 — sc1 의 첫 _add 로 cleanup 행위 노출
                if hasattr(self, "_add"):
                    self._add("pass",
                              "sc1 — session 시작 cleanup ([AUTO] + [AUTO_KEEP] 일괄 삭제, clean slate)",
                              f"잔여: {len(before)}건 {before} / deleted={deleted} (sc3 ADD 중복 방지)",
                              sc=1)
                else:
                    print(f"[session cleanup] 원본보호 잔여 {len(before)}건 / 삭제 {deleted}건")
        except Exception as e:
            if hasattr(self, "_add"):
                self._add("warn", "sc1 — session cleanup 예외", f"예외: {e!r}", sc=1)
            else:
                print(f"[session cleanup] 원본보호 예외: {e!r}")
        OriginProtectBase._SESSION_CLEANUP_DONE = True

    def _attach(self, scan_results: list[ScanResult]) -> None:
        # 자동 sub-num 재태깅 안전망 — _add 우회 호출 cover (control_suite 와 동일 패턴)
        try:
            nm = self._request.node.name
            m = re.match(r"test_scenario(\d+)([a-z])_", nm)
            if m:
                sn = int(m.group(1))
                sub = ord(m.group(2)) - ord("a") + 1
                # sn=0 (sc0 시리즈) 는 sub-numbering 안 함 — sn*100+sub=sub 가 다른 시나리오
                # parent sc=1,2,... 와 충돌. sc=0 raw 유지 → html_reporter `0:` 키 lookup.
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
        # crash 시점에 hook 이 page_id 추출 가능하도록 미리 attach (사용자 지적 2026-05-29
        # — _add 호출 전 crash 발생 시 ScanResult 어디에도 안 잡힘 → error 카운트 0).
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
                p.wait_for_timeout(500)
                # Bootstrap modal 잔존물 강제 cleanup (사용자 보고 2026-05-29 sc3k FAIL —
                # backdrops=2 잔존으로 sc3l click intercept). reload 후에도 modal-backdrop /
                # body padding-right 잔존 케이스 fix.
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
        """sub-numbering + ScanResult 누적.

        highlight (optional, Playwright Locator): fail/warn 시 캡처에서 해당
        요소에 빨간 outline 임시 주입 → 어느 영역의 이슈인지 시각적으로 표시.
        모달 안 검증처럼 영역 구분이 필요한 곳에서만 넘기면 된다.
        """
        # sub-numbering — 메서드 이름 'test_scenarioNX_...' 에서 자동 추출 → sc = N*100 + sub
        # (sn*100 체계: a~z 전부 안전 — sc3j/sc3k 같은 j/k 도 충돌 없음)
        try:
            nm = self._request.node.name
            m = re.match(r"test_scenario(\d+)([a-z])_", nm)
            if m:
                sn = int(m.group(1))
                sub = ord(m.group(2)) - ord("a") + 1
                # sn=0 은 sub-num skip (다른 시나리오 parent sc 와 충돌 방지)
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
