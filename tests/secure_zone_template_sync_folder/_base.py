"""시큐어존 템플릿(폴더동기화) 시나리오 공통 base — 특수폴더 base 미러.

정책 _base 의 _ss/_r 재사용. PAGE_ID + cleanup 만 다름.
cleanup 라이프사이클: sc1 시작 = delete_all_test_data([AUTO]+[AUTO_날짜]) / sc6 = delete_all_auto([AUTO]만).
_R 리턴 재생 = fail 전용 (control_suite 와 동일 원칙 — 행위별 조건부 캡처가 기본).
"""
import re
import pytest

from core.models import ScanResult, PageScanReport
from tests.secure_zone_policy._base import _ss, _r   # 공유 헬퍼(crop 스크린샷 포함)
from tests.shared_journal import ActionJournalMixin


class SecureZoneTemplateSyncFolderBase(ActionJournalMixin):
    """시큐어존 템플릿(폴더동기화) 공통 base."""

    PAGE_ID = "secure_zone_template_sync_folder"

    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """sc1 시작 clean slate — [AUTO] + [AUTO_<날짜>] 둘 다 삭제 (1회). 실데이터 보존."""
        if SecureZoneTemplateSyncFolderBase._SESSION_CLEANUP_DONE:
            return
        try:
            page.page.wait_for_timeout(200)
            before = [n for n in page.get_template_names() if page._AUTO_ANY.match(n)]
            page.delete_all_test_data()
            if hasattr(self, "_add"):
                self._add("pass",
                          "sc1 — session 시작 cleanup ([AUTO]+[AUTO_날짜] 일괄 삭제, clean slate)",
                          f"잔여: {len(before)}건 {before}", sc=1)
        except Exception as e:
            if hasattr(self, "_add"):
                self._add("warn", "sc1 — session cleanup 예외", f"예외: {e!r}", sc=1)
        SecureZoneTemplateSyncFolderBase._SESSION_CLEANUP_DONE = True

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
    _REPLAY_ON_FAIL = True
    _REPLAY_MAX_FRAMES = 10

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None
        self._replay_mode = False
        self._replay_frames: list = []
        request.node._npouch_page_id = self.PAGE_ID
        try:
            if "logged_in_page" in request.fixturenames:
                p = request.getfixturevalue("logged_in_page")
                p.set_default_timeout(self._SC_DEFAULT_TIMEOUT)
        except Exception:
            pass
        yield
        # ── 자동 리턴 재생(_R): 예기치 못한 fail 시 같은 테스트를 캡처 모드로 1회 재실행 ──
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
                        kwargs[pname] = request.getfixturevalue(pname)
                    try:
                        fn(**kwargs)
                    except Exception:
                        pass
                self._replay_mode = False
                if self._replay_frames:
                    t, s = _r("warn", f"{fn_name.replace('test_', '')} — 리턴 재생(_R) 스텝 캡처",
                              f"fail 발생으로 같은 흐름을 1회 재실행하며 검증 지점마다 캡처 "
                              f"({len(self._replay_frames)}장, 최대 {self._REPLAY_MAX_FRAMES}).", sc=0)
                    s.extra["screenshots"] = self._replay_frames[:self._REPLAY_MAX_FRAMES]
                    s.extra["scenario"] = (self._srs[0].extra or {}).get("scenario", 0) if self._srs else 0
                    self._lines.append(t)
                    self._srs.append(s)
        except Exception:
            pass
        if self._srs and not getattr(self._request.node, "_scan_report", None):
            self._attach(self._srs)
        try:
            p = (self._request.node.funcargs.get("logged_in_page")
                 or self._request.node.funcargs.get("fresh_page"))
            if p is not None:
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

    def _shot(self, label: str, highlight=None, caption: str = None):
        try:
            p = _ss(self._page, label, highlight=highlight)
            if p and caption:
                return {"path": p, "caption": caption}
            return p
        except Exception:
            return None

    def _add(self, status: str, label: str, detail: str = "", sc: int = 0,
             highlight=None, repro=None, screenshot=True, merge_key: str = None,
             screenshots: list = None) -> None:
        # 리턴 재생(_R) 모드: 카드 미생성, 검증 지점 화면만 수집
        if getattr(self, "_replay_mode", False):
            if len(self._replay_frames) < self._REPLAY_MAX_FRAMES:
                p = _ss(self._page, f"R_{label}", highlight=highlight)
                if p:
                    icon = {"pass": "[OK]", "fail": "[FAIL]", "warn": "[WARN]", "skip": "[SKIP]"}.get(status, "?")
                    self._replay_frames.append(
                        {"path": p, "caption": f"R{len(self._replay_frames) + 1}. {icon} {label}"})
            return
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
        # ── 행위 저널 자동 재생 (tests/shared_journal.ActionJournalMixin) ──
        screenshots = self._journal_frames_for_issue(status, screenshots)
        cap = self._page if (status in ("fail", "warn") and screenshot
                             and not screenshots) else None
        t, s = _r(status, label, detail, sc=sc,
                  page=cap,
                  highlight=highlight if (status in ("fail", "warn") and screenshot
                                          and not screenshots) else None,
                  repro=repro)
        if merge_key:
            s.extra["merge_key"] = merge_key
        if screenshots:
            s.extra["screenshots"] = [p for p in screenshots if p]
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)
