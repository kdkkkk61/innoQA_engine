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
        # 이전 호출이 남긴 빨간 outline 전부 제거 — locator 재해결 실패로 잔류하는 red 줄 방지
        # (highlight.first 로 지우면 요소 re-render/detach 시 DOM 에 남아 다음 캡처 배경에 나타남)
        try:
            page.evaluate(
                "() => document.querySelectorAll('[data-qa-hl]').forEach(el => {"
                " el.style.outline=''; el.style.outlineOffset=''; el.style.boxShadow='';"
                " el.removeAttribute('data-qa-hl'); })"
            )
        except Exception:
            pass
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
       page=None, highlight=None, repro=None, merge_key: str = None) -> tuple[str, ScanResult]:
    """print 라인 + ScanResult 동시 생성. warn/fail 이면 스크린샷 자동 첨부.
    sc = 시나리오 번호 (1~5). highlight=Locator 면 캡처에 빨간 outline 표시.
    repro: 결함 카드 '재현 방법' / merge_key: 동일 내용 결함 카드 묶음(docs/issue-card-rules.md)."""
    icon = _STATUS_ICON.get(status, "?")
    text = f"  {icon} {label}" + (f": {detail}" if detail else "")
    extra: dict = {"scenario": sc}
    if repro:
        extra["repro"] = repro
    if merge_key:
        extra["merge_key"] = merge_key
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

    PAGE_ID = "common_control_suite"

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
        if getattr(self, "_replay_mode", False):
            return   # 리턴 재생 중에는 보고서 덮어쓰기 금지 (프레임만 _add 가 수집)
        sr = ScanResult(
            pattern="scenario_test", selector="", label=label,
            status="pass", detail="", extra={"scenario": sc},
        )
        self._attach([sr])

    # 짧은 default timeout — cascade 시 wait 시간 폭증 방지 (5s).
    # 진단 hook 으로 fail 시점 정보는 그대로 수집 → 차후 원인 분석 가능.
    _SC_DEFAULT_TIMEOUT = 5000

    # 자동 리턴 재생(_R): 큐레이션 캡처 없는 fail 발생 시 같은 테스트를 1회 재실행하며
    # _add 지점마다 자동 캡처 → "리턴 재생(_R)" 카드로 어디서 끊겼는지 스텝별 확인
    # (operation_process/tag base 미러). 실패한 테스트만 재실행하므로 정상 run 은 무영향.
    _REPLAY_ON_FAIL = True
    _REPLAY_MAX_FRAMES = 10

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        """매 테스트 시작 — short timeout 적용 + 끝 F5 + 진단 정보 유지."""
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None
        self._replay_mode = False
        self._replay_frames: list = []
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
        # ── 자동 리턴 재생(_R): 예기치 못한 fail(assert 실패 등) 시 같은 테스트를 캡처 모드로 1회 재실행 ──
        # warn(알려진 제품결함)은 각 행위에서 조건부 다중 캡처(입력→오류)로 처리 → 여기선 fail 만 대상
        # (warn 까지 넣으면 test 전체를 재실행해 10프레임 뭉뚱그리는 문제 → 행위별 정밀 재현이 목표).
        try:
            _need_replay = any(
                s.status == "fail" and not (s.extra or {}).get("screenshots")
                for s in self._srs
            )
            if self._REPLAY_ON_FAIL and not self._replay_mode and _need_replay:
                self._replay_mode = True
                fn_name = getattr(request.node, "originalname", None) or request.node.name.split("[")[0]
                fn = getattr(self, fn_name, None)
                if fn is not None:
                    import inspect
                    kwargs = {}
                    for pname in inspect.signature(fn).parameters:
                        try:
                            kwargs[pname] = request.getfixturevalue(pname)
                        except Exception:
                            pass
                    try:
                        fn(**kwargs)
                    except Exception:
                        pass
                self._replay_mode = False
                if self._replay_frames:
                    _sc0 = (self._srs[0].extra or {}).get("scenario", 0) if self._srs else 0
                    t, s = _r("warn", f"{fn_name.replace('test_', '')} — 리턴 재생(_R) 스텝 캡처",
                              f"fail 발생으로 같은 흐름을 1회 재실행하며 검증 지점마다 캡처 "
                              f"({len(self._replay_frames)}장, 최대 {self._REPLAY_MAX_FRAMES}). "
                              "재현 여부·끊긴 지점은 스텝 이미지로 확인.", sc=_sc0)
                    s.extra["screenshots"] = self._replay_frames[:self._REPLAY_MAX_FRAMES]
                    self._lines.append(t)
                    self._srs.append(s)
                    self._attach(self._srs)
        except Exception:
            pass
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
             highlight=None, repro=None, merge_key: str = None,
             screenshots: list = None) -> None:
        """한 줄로 print + ScanResult 누적. 각 검증 블록 단위 호출.

        highlight (optional, Playwright Locator): fail/warn 시 캡처에 빨간 outline
        임시 주입 — 어느 영역의 이슈인지 시각적으로 표시.

        screenshots (optional, list): _replay_shots 등으로 만든 다중 캡처(캡션 포함)를
        결함 카드에 재현 순서로 첨부. [str | {"path","caption"}] — html_reporter 가 렌더.

        sub-numbering 자동 매핑 (2026-05-29 — 원본보호와 통일):
          메서드 이름 'test_scenarioNX_...' → sc = N*100 + sub_idx (a=1, b=2, ..., r=18, ...)
          sc3a → 301 / sc3j → 310 / sc3k → 311 / sc4r → 418 / sc5a → 501 / ...
          a~z 전부 안전 (sn*10 방식의 j/k 충돌 회피).
        """
        # 리턴 재생(_R) 모드: 카드 누적 대신 검증 지점 화면만 수집(캡션 = 순번+판정+라벨)
        if getattr(self, "_replay_mode", False):
            if len(self._replay_frames) < self._REPLAY_MAX_FRAMES:
                p = _ss(self._page, f"R_{label}", highlight=highlight)
                if p:
                    icon = _STATUS_ICON.get(status, "?")
                    self._replay_frames.append(
                        {"path": p, "caption": f"R{len(self._replay_frames) + 1}. {icon} {label}"})
            return
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
        # ── 행위 저널 자동 재생: warn/fail 검출 + 큐레이션 캡처 없음 + _ckpt 블록 활성 시
        #    저널 행위들을 그대로 재실행하며 단계별 캡처(캡션=행위 라벨) → 재현 순서 자동 첨부.
        #    재생은 블록당 1회 — 같은 블록의 후속 warn/fail 카드는 같은 프레임을 공유(재실행 없음).
        if (status in ("fail", "warn") and not screenshots
                and getattr(self, "_journal", None)):
            if not getattr(self, "_journal_replayed", True):
                self._journal_replayed = True
                # 재생 전 alert 상태 스냅샷 — 본 흐름이 직접 dismiss 할 alert(서버오류 등)가
                # 이미 열려 있으면 재생 후에도 그대로 둬야 함(닫으면 본 흐름 dismiss 가
                # timeout — sc3j 회귀 2026-07-07). 재생이 '새로' 만든 alert 만 정리 대상.
                _alert_before = False
                try:
                    _alert_before = self._page.locator(
                        "div#__globalMessageModal.in").count() > 0
                except Exception:
                    pass
                self._journal_frames = self._replay_shots(list(self._journal))
                if not _alert_before:
                    # 재생이 새로 띄운 alert 정리 (예: no-op 확인의 '수정된 항목이 없습니다'
                    # — sc4d 중단 원인). 원래 없던 것만 닫아 본 흐름 상태 계약 유지.
                    try:
                        _btn = self._page.locator(
                            "div#__globalMessageModal.in button:has-text('확인')")
                        if _btn.count() > 0:
                            _btn.first.evaluate("el => el.click()")
                            self._page.wait_for_timeout(300)
                        self._page.evaluate(
                            "() => { if (!document.querySelector('.modal-wrap.in, .modal.in')) {"
                            " document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());"
                            " document.body.classList.remove('modal-open'); } }")
                    except Exception:
                        pass
            _frames = getattr(self, "_journal_frames", None)
            screenshots = list(_frames) if _frames else None
        # screenshots(큐레이션 다중 캡처)가 있으면 자동 단일 캡처는 생략 — 중복 방지
        _auto_cap = status in ("fail", "warn") and not screenshots
        t, s = _r(status, label, detail, sc=sc,
                  page=self._page if _auto_cap else None,
                  highlight=highlight if _auto_cap else None,
                  repro=repro, merge_key=merge_key)
        if screenshots:
            s.extra["screenshots"] = [x for x in screenshots if x]
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)

    # ── 행위 저널 + 자동 리턴재생 (전역 캡처 지원, 사용자 설계 2026-07-07) ──
    # 목표: 오류가 '손코딩해둔 지점'이 아니어도 같은 품질의 재현 캡처가 자동으로 나오게.
    # 사용: 케이스 시작에 _ckpt() → 행위를 _act("라벨", fn, 캡처대상)로 실행(기록만, 캡처 0)
    #       → _add 가 warn/fail 검출 시 저널 행위들을 재실행하며 단계별 캡처(캡션=라벨) 자동 첨부.
    # 재생 가능 조건: 블록 첫 행위가 상태 리셋(navigate_to_clean 등)이어야 함([AUTO] 데이터 한정).
    def _ckpt(self) -> None:
        """행위 블록 시작 — 이후 warn/fail 검출 시 여기서부터 재생. 블록당 재생 1회(프레임 공유)."""
        self._journal = []
        self._journal_replayed = False
        self._journal_frames = None

    def _act(self, label: str, fn, shot_target=None) -> None:
        """행위 실행 + 저널 기록. 1차 실행에선 캡처하지 않음(검출 시에만 재생 캡처)."""
        fn()
        if not hasattr(self, "_journal"):
            self._journal, self._journal_replayed = [], False
        self._journal.append((label, fn, shot_target))

    def _shot(self, label: str, highlight=None, caption: str = None):
        """중간 시점 추가 캡처 — 두 화면 대조/재현 순서 전용(운용프로세스 _shot 미러).
        caption 지정 시 {"path","caption"} 반환(스텝 라벨), 아니면 경로 문자열."""
        if self._page is None:
            return None
        p = _ss(self._page, label, highlight=highlight)
        if p and caption:
            return {"path": p, "caption": caption}
        return p

    def _replay_shots(self, steps) -> list:
        """이슈 확정 후 '리턴 재생' — 스텝을 다시 실행하며 단계별 캡처(캡션 포함).
        운용프로세스 _replay_shots 미러. steps: [(라벨, 동작fn 또는 None, 캡처대상 Locator 또는 None), ...]"""
        shots = []
        for label, action, target in steps:
            try:
                if action:
                    action()
                self._page.wait_for_timeout(300)
                p = _ss(self._page, f"replay_{label}", highlight=target)
                if p:
                    shots.append({"path": p, "caption": f"{len(shots) + 1}. {label}"})
            except Exception:
                p = _ss(self._page, f"replay_{label}_예외중단")
                if p:
                    shots.append({"path": p, "caption": f"{len(shots) + 1}. {label} — 예외로 중단(오류 지점)"})
                break
        return shots

    def _finish(self, context: str = "") -> None:
        """메서드 끝 호출 — attach + FAIL 어서션."""
        self._attach(self._srs)
        _assert_no_fail(self._lines, context=context)
