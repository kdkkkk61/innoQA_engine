"""시큐어존 템플릿(특수폴더) 시나리오 공통 base — 방식 B (list_page + sc0).

정책 _base 의 _ss(불일치 필드 crop 캡처)/_r(ScanResult 빌더) 재사용. PAGE_ID + cleanup 만 다름.
cleanup 라이프사이클(연계): sc1 시작 = delete_all_test_data([AUTO]+[AUTO_날짜]) / sc6 = delete_all_auto([AUTO]만).
crash 시점 page_id 미리 attach (방식 B 필수 — conftest error 등록 보장).
"""
import re
import pytest

from core.models import ScanResult, PageScanReport
from tests.secure_zone_policy._base import _ss, _r   # 공유 헬퍼(crop 스크린샷 포함)


class SecureZoneTemplateManageFolderBase:
    """시큐어존 템플릿(특수폴더) 공통 base."""

    PAGE_ID = "secure_zone_template_manage_folder"

    _SESSION_CLEANUP_DONE = False

    def _ensure_session_cleanup(self, page) -> None:
        """sc1 시작 clean slate — [AUTO] + [AUTO_<날짜>] 둘 다 삭제 (1회). 실데이터 보존."""
        if SecureZoneTemplateManageFolderBase._SESSION_CLEANUP_DONE:
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
        SecureZoneTemplateManageFolderBase._SESSION_CLEANUP_DONE = True

    def _attach(self, scan_results: list[ScanResult]) -> None:
        try:
            nm = self._request.node.name
            m = re.match(r"test_scenario(\d+)([a-z])_", nm)
            if m:
                sn = int(m.group(1))
                sub = ord(m.group(2)) - ord("a") + 1
                if sn != 0:   # sc0 시리즈는 sub-num 매핑 skip (방식 B 규칙)
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
        request.node._npouch_page_id = self.PAGE_ID   # crash 시 error 등록 보장
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
             highlight=None, repro=None, screenshot=True) -> None:
        """sub-numbering + ScanResult 누적. repro: 보고서 '재현 방법' 단계(줄바꿈=\\n).
        screenshot=False 면 fail/warn 이어도 캡처 생략."""
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
        cap = self._page if (status in ("fail", "warn") and screenshot) else None
        t, s = _r(status, label, detail, sc=sc,
                  page=cap,
                  highlight=highlight if (status in ("fail", "warn") and screenshot) else None,
                  repro=repro)
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)
