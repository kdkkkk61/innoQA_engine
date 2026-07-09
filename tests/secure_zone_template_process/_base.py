"""시큐어존 템플릿(프로세스) 시나리오 공통 base — sync_folder base 미러 (타입종속 4중 모달 탭).

정책 _base 의 _ss/_r 재사용. PAGE_ID + cleanup 만 다름.
cleanup 라이프사이클: sc1 시작 = delete_all_test_data([AUTO]+[AUTO_날짜]) / sc6 = delete_all_auto([AUTO]만).
_R 리턴 재생 = fail 전용 (control_suite 와 동일 원칙 — 행위별 조건부 캡처가 기본).
"""
import re
import pytest

from core.models import ScanResult, PageScanReport
from tests.secure_zone_policy._base import _ss, _r   # 공유 헬퍼(crop 스크린샷 포함)
from tests.shared_journal import ActionJournalMixin


class SecureZoneTemplateProcessBase(ActionJournalMixin):
    """시큐어존 템플릿(프로세스) 공통 base."""

    PAGE_ID = "secure_zone_template_process"

    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """sc1 시작 clean slate — [AUTO] + [AUTO_<날짜>] 둘 다 삭제 (1회). 실데이터 보존."""
        if SecureZoneTemplateProcessBase._SESSION_CLEANUP_DONE:
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
        SecureZoneTemplateProcessBase._SESSION_CLEANUP_DONE = True

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
        # ── 자동 리턴 재생(_R): 예기치 못한 fail 시 같은 테스트를 캡처 모드로 1회 재실행.
        #    ★설계(사용자 지시 2026-07-09): 별도 '_R 스텝 캡처' 카드를 만들지 않는다 —
        #    재실행 중 이슈(fail/warn) 지점을 만나면 '직전 이슈 이후의 스텝들'을 **그 이슈
        #    티켓의 screenshots** 로 직접 첨부(a 티켓엔 a 스토리, b 티켓엔 b 스토리).
        try:
            _need_replay = any(
                s.status == "fail" and not (s.extra or {}).get("screenshots")
                for s in self._srs
            )
            if self._REPLAY_ON_FAIL and not self._replay_mode and _need_replay:
                self._replay_mode = True
                self._replay_frames = []
                self._replay_idx = 0
                self._orig_cards = list(self._srs)   # 원본 카드 — 재실행 _add 순서로 매칭
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
                # 마지막 이슈 이후 남은 pass 스텝 프레임은 소속 이슈가 없음 — 버림
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
        # 리턴 재생(_R) 모드: 카드 미생성 — 스텝 화면을 모아 '해당 이슈 티켓'에 직접 첨부.
        if getattr(self, "_replay_mode", False):
            if len(self._replay_frames) < self._REPLAY_MAX_FRAMES:
                p = _ss(self._page, f"R_{label}", highlight=highlight)
                if p:
                    icon = {"pass": "[OK]", "fail": "[FAIL]", "warn": "[WARN]", "skip": "[SKIP]"}.get(status, "?")
                    self._replay_frames.append({"path": p, "caption": f"{icon} {label}"})
            # 이슈 지점 도달 → 직전 이슈 이후의 스텝들 = 이 이슈의 스토리 → 원본 카드에 첨부
            idx = getattr(self, "_replay_idx", 0)
            self._replay_idx = idx + 1
            if status in ("fail", "warn") and idx < len(getattr(self, "_orig_cards", [])):
                card = self._orig_cards[idx]
                if card.extra is None:
                    card.extra = {}
                if not card.extra.get("screenshots") and self._replay_frames:
                    frames = self._replay_frames[:self._REPLAY_MAX_FRAMES]
                    for i, f in enumerate(frames, 1):
                        f["caption"] = f"{i}. {f['caption']}"
                    card.extra["screenshots"] = frames
                self._replay_frames = []
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
