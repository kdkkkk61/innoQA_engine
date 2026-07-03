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

    # 전역 리턴 재생(사용자 설계 2026-07-03): fail 카드 발생 시 같은 테스트를 '_R' 모드로 1회
    # 재실행 — _add 지점마다 자동 캡처(카드 미생성) → "… 리턴 재생(_R)" 카드 1장으로 등록.
    # 재실행이 위험한(비멱등) 클래스는 이 플래그를 False 로 opt-out.
    _REPLAY_ON_FAIL = True
    _REPLAY_MAX_FRAMES = 10

    @pytest.fixture(autouse=True)
    def _setup(self, request):
        self._request = request
        self._lines: list[str] = []
        self._srs:   list[ScanResult] = []
        self._page = None
        self._replay_mode = False
        self._replay_frames: list[str] = []
        request.node._npouch_page_id = self.PAGE_ID   # crash 시 error 등록 보장
        try:
            if "logged_in_page" in request.fixturenames:
                p = request.getfixturevalue("logged_in_page")
                p.set_default_timeout(self._SC_DEFAULT_TIMEOUT)
        except Exception:
            pass
        yield
        # ── 전역 리턴 재생(_R): fail 이 있으면 같은 테스트를 캡처 모드로 1회 재실행 ──
        try:
            # 조건: fail 카드가 있고, 그 fail 이 '큐레이션 스텝 스토리(screenshots)' 를 이미 갖고 있지 않을 때만.
            # (수동 _replay_shots 가 붙은 fail 은 _R 이 판정 순간만 또 찍는 중복 — 사용자 지적 2026-07-03)
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
                        fn(**kwargs)          # 재생 중 _add 는 캡처만 수집(카드 미생성)
                    except Exception:
                        pass                  # 재생 중단돼도 그때까지 캡처는 유효(끊긴 지점=오류 지점)
                self._replay_mode = False
                if self._replay_frames:
                    t, s = _r("warn", f"{fn_name.replace('test_', '')} — 리턴 재생(_R) 스텝 캡처",
                              f"fail 발생으로 같은 흐름을 1회 재실행하며 검증 지점마다 캡처 "
                              f"({len(self._replay_frames)}장, 최대 {self._REPLAY_MAX_FRAMES}). "
                              "재현 여부·끊긴 지점은 스텝 이미지로 확인.", sc=0)
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

    def _replay_shots(self, steps) -> list[str]:
        """이슈 확정 후 '1회 리턴 재생'(사용자 설계 2026-07-03) — 스텝을 다시 실행하며 단계별
        캡처(빨간 표시 포함) → 반환 경로들을 _add(screenshots=...) 로 카드에 붙임.

        steps: [(라벨, 동작fn 또는 None, 캡처대상 Locator 또는 None=전체 화면), ...]
        - pass 경로에선 호출하지 말 것(발생 시 전용 — 실행 비용은 이슈일 때만).
        - 스텝 실행 중 예외면 그 시점 화면을 찍고 중단 → 어느 스텝에서 끊겼는지가 곧 오류 지점.
        - 리턴 재생도 데이터를 만지므로 [AUTO] 데이터 한정(기존 데이터 안전 규칙 그대로)."""
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

    def _shot(self, label: str, highlight=None, caption: str = None):
        """중간 시점 추가 캡처 — 판정이 두 화면의 대조로 확정될 때만 사용(기본은 _add 1장).
        예: '데이터는 비워짐(편집 모달) + 속성엔 옛값(속성 모달)' — 두 화면이 모두 증거인 경우.
        반환값을 _add(screenshots=[...]) 로 전달. 남용 금지(리포트 크기).
        caption 지정 시 {"path","caption"} — 리포트에서 이미지 위에 스텝 라벨 표시(스토리와 동일 형식)."""
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
        """sub-numbering + ScanResult 누적. repro: 보고서 '재현 방법' 단계(줄바꿈=\\n).
        screenshot=False 면 fail/warn 이어도 캡처 생략.
        merge_key: 같은 페이지에서 같은 키의 결함 항목을 리포트 결함 카드 1장으로 묶음
        (완전 동일 내용의 sc3/sc4 [수동 확인 필요] 등 — 검증 항목 표에는 각각 남음).
        screenshots: _shot() 으로 찍은 이전 시점 캡처 경로들 — 카드에 시간순으로 함께 표시."""
        # 리턴 재생(_R) 모드: 카드를 만들지 않고 검증 지점 화면만 수집(스텝 스토리용).
        # 캡션(순번+검증 라벨+판정)을 붙여 리포트에서 '어떤 식으로 진행됐는지' 순서대로 읽히게(사용자 지시 2026-07-03).
        if getattr(self, "_replay_mode", False):
            if len(self._replay_frames) < self._REPLAY_MAX_FRAMES:
                p = _ss(self._page, f"R_{label}", highlight=highlight)
                if p:
                    icon = {"pass": "[OK]", "fail": "[FAIL]", "warn": "[WARN]", "skip": "[SKIP]"}.get(status, "?")
                    # 캡션 접두어 'R' = 리턴 재생 캡처임을 이미지만 봐도 식별(사용자 요청 2026-07-03)
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
        cap = self._page if (status in ("fail", "warn") and screenshot) else None
        t, s = _r(status, label, detail, sc=sc,
                  page=cap,
                  highlight=highlight if (status in ("fail", "warn") and screenshot) else None,
                  repro=repro)
        if merge_key:
            s.extra["merge_key"] = merge_key
        if screenshots:
            s.extra["screenshots"] = [p for p in screenshots if p]
        print(t)
        self._lines.append(t)
        self._srs.append(s)
        self._attach(self._srs)
