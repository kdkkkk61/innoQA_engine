"""시큐어존 정책(에이전트 정책) — 공유 base class + ScanResult 헬퍼.

tests/secure_zone/_base.py(접근제어) 패턴 복제. PAGE_ID 만 다름.
각 시나리오 파일(test_scenarioN_*)이 SecureZonePolicyBase 상속.

시큐어존 정책은 템플릿/제어스위트를 참조하지만, 테스트에서는 콘솔에 이미 존재하는
템플릿을 picker 로 선택만 한다(신규 템플릿 생성 안 함, 사용자 결정 2026-06-10).
cleanup 은 [AUTO] 접두사 정책만 삭제 — 73건 실데이터는 절대 건드리지 않음.
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
       page=None, highlight=None, repro=None) -> tuple[str, ScanResult]:
    icon = _STATUS_ICON.get(status, "?")
    text = f"  {icon} {label}" + (f": {detail}" if detail else "")
    extra: dict = {"scenario": sc}
    if repro:
        extra["repro"] = repro
    if page and status in ("fail", "warn"):
        ss_path = _ss(page, label, highlight=highlight)
        if ss_path:
            extra["screenshot"] = ss_path
    sr = ScanResult(
        pattern="scenario_test", selector="", label=label,
        status=_STATUS_TO_SR.get(status, status), detail=detail, extra=extra,
    )
    return text, sr


class SecureZonePolicyBase:
    """시큐어존 정책 시나리오 공통 base."""

    PAGE_ID = "secure_zone_agent_policy"

    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """session 시작 [AUTO] 일괄 정리 (1회). 73건 실데이터는 보존."""
        if SecureZonePolicyBase._SESSION_CLEANUP_DONE:
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
        SecureZonePolicyBase._SESSION_CLEANUP_DONE = True

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
                # teardown: full reload 제거(속도). 모달/백드롭만 JS로 청소.
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
             highlight=None, repro=None) -> None:
        """sub-numbering + ScanResult 누적.

        repro: 보고서 '재현 방법' 칼럼에 표시할 상세 단계(줄바꿈=\\n). 무엇을 어떤 값으로 했는지 명시.
        """
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
                  highlight=highlight if status in ("fail", "warn") else None,
                  repro=repro)
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)

    def _skip_if_missing(self, page, feat_desc: str, sels, sc: int) -> bool:
        """환경별 삭제/숨김 기능 가드 — 대상이 검증 불가면 SKIP 카드 + True 반환(호출자 return).

        sels: [selector, ...]. feature_available(존재 + 섹션 안 숨김)로 판정 —
        삭제/숨김이면 skip, 있으면(토글 CSS숨김/gating disabled 포함) 통과시켜 실제 동작 검증(깨지면 fail).
        크래시(fill/is_checked 타임아웃) 대신 graceful skip. 근거는 sc0 '숨김/제거' 카드.
        """
        for sel in sels:
            if not page.feature_available(sel):
                self._add("skip", f"{feat_desc} — 이 환경에 미표시(삭제/숨김) → 검증 건너뜀",
                          f"대상 {sel} 미표시 — sc0 '신규/제거/숨김' 카드 참조 (환경/빌드 차이)",
                          sc=sc)
                return True
        return False
