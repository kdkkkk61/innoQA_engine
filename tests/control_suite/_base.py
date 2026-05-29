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


def _ss(page, label: str, highlight=None) -> str | None:
    """warn/fail 시점 스크린샷 저장 → 경로 반환.

    highlight (Locator) 가 있으면 빨간 outline + 스크롤 후 전체 캡처
    → 모달 안 어느 영역인지 시각적으로 표시.
    """
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
    """print 라인 + ScanResult 동시 생성. warn/fail 이면 스크린샷 자동 첨부.
    sc = 시나리오 번호 (1~5). highlight=Locator 면 캡처에 빨간 outline 표시."""
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

    # session-level cleanup 1회 flag — sc1a 미실행 시 sc3/4/5 등 단독 실행 안전 보장.
    # 사용자 평가 (2026-05-20): "이미 등록된 이름 차단은 시스템 정상 동작 — sc1 cleanup
    # 미실행이 진짜 원인". → session 시작 시 무조건 1회 cleanup.
    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """session 시작 시 [AUTO]_ + [AUTO_KEEP]_ 1회 일괄 정리.

        sc1a 가 이미 cleanup 했으면 (delete_all_test_data) idempotent — 추가 정리 없음.
        sc1a 가 안 실행됐으면 (subset run: pytest sc3 만) 여기서 cleanup.

        강화 (2026-05-28): 이전 run 의 zz 가 [AUTO_KEEP] 보존 → 다음 run 시작 시 잔여 있음.
          - silent + 예외 swallow 였던 기존 구현이 실패를 못 보여 sc5a "이미 등록된 이름" 발생.
          - 가시성 log + 재시도 + AngularJS 비동기 list 렌더 대기 추가.
        """
        if ControlSuiteBase._SESSION_CLEANUP_DONE:
            return
        try:
            # AngularJS 비동기 list 렌더 안정화 대기 (navigate_to 직후 row 비어있을 수 있음)
            page.page.wait_for_timeout(500)
            before = [n for n in page.get_policy_names()
                      if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
            if before:
                print(f"[session cleanup] 시작 잔여 {len(before)}건: {before}")
            deleted = page.delete_all_test_data()
            after = [n for n in page.get_policy_names()
                     if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
            if after:
                # 1차 후 잔여 — list 미갱신 / 비동기 race 가능성 → 재시도
                print(f"[session cleanup] 1차 후 잔여 {len(after)}건 — 재시도: {after}")
                page.page.wait_for_timeout(500)
                deleted += page.delete_all_test_data()
                after = [n for n in page.get_policy_names()
                         if n.startswith("[AUTO]") or n.startswith("[AUTO_KEEP]")]
            print(f"[session cleanup] 완료: 삭제 {deleted}건, 최종 잔여={after}")
        except Exception as e:
            print(f"[session cleanup] 예외: {e!r}")
        ControlSuiteBase._SESSION_CLEANUP_DONE = True

    def _attach(self, scan_results: list[ScanResult]) -> None:
        """PageScanReport 를 test node 에 첨부 — conftest 가 수집해서 html_reporter 로 전달.

        자동 sub-num 재태깅 (2026-05-29 — _add 우회 호출 cover):
          메서드 이름 'test_scenarioNX_...' → sc = N*100 + sub_idx.
          _r() + _attach() 옛 패턴(sc1a) 도 자동 매핑되도록 _attach 에서 일괄 처리.
        """
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

    def _emit_pass(self, label: str, sc: int) -> None:
        """test 가 통과되면 끝에 호출 — 단일 pass ScanResult 첨부."""
        sr = ScanResult(
            pattern="scenario_test", selector="", label=label,
            status="pass", detail="", extra={"scenario": sc},
        )
        self._attach([sr])

    # 짧은 default timeout — cascade 시 wait 시간 폭증 방지 (5s).
    # 진단 hook 으로 fail 시점 정보는 그대로 수집 → 차후 원인 분석 가능.
    _SC_DEFAULT_TIMEOUT = 5000

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        """매 테스트 시작 — short timeout 적용 + 끝 F5 + 진단 정보 유지."""
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None
        # crash 시점에 hook 이 page_id 추출 가능하도록 미리 attach (사용자 지적 2026-05-29
        # — _add 호출 전 crash 발생 시 보고서에 error 0 으로 누락 방지).
        request.node._npouch_page_id = self.PAGE_ID
        # 시작 — page default timeout 단축 (cascade hang 시간 폭증 방지)
        try:
            if "logged_in_page" in request.fixturenames:
                page = request.getfixturevalue("logged_in_page")
                page.set_default_timeout(self._SC_DEFAULT_TIMEOUT)
        except Exception:
            pass
        yield
        # ScanResult fallback attach
        if self._srs and not getattr(self._request.node, "_scan_report", None):
            self._attach(self._srs)
        # 끝 — timeout 원복 + page.reload() (실용 복구)
        # 사용자 평가: "이전 무식한 F5 가 더 유용" → reload 유지
        # 진단 hook 은 그대로 → fail 시 [진단 OPEN_MODAL/DOM/NET] 누적
        try:
            page = (self._request.node.funcargs.get("logged_in_page")
                    or self._request.node.funcargs.get("fresh_page"))
            if page is not None:
                page.set_default_timeout(30000)   # 원복
                page.reload(wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(500)
        except Exception:
            pass

    def _add(self, status: str, label: str, detail: str = "", sc: int = 0,
             highlight=None) -> None:
        """한 줄로 print + ScanResult 누적. 각 검증 블록 단위 호출.

        highlight (optional, Playwright Locator): fail/warn 시 캡처에 빨간 outline
        임시 주입 — 어느 영역의 이슈인지 시각적으로 표시.

        sub-numbering 자동 매핑 (2026-05-29 — 원본보호와 통일):
          메서드 이름 'test_scenarioNX_...' → sc = N*100 + sub_idx (a=1, b=2, ..., r=18, ...)
          sc3a → 301 / sc3j → 310 / sc3k → 311 / sc4r → 418 / sc5a → 501 / ...
          a~z 전부 안전 (sn*10 방식의 j/k 충돌 회피).
        """
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

    def _finish(self, context: str = "") -> None:
        """메서드 끝 호출 — attach + FAIL 어서션."""
        self._attach(self._srs)
        _assert_no_fail(self._lines, context=context)
