"""운용 프로세스 시나리오 공통 base — 특수폴더 base 이식 (재구성 2026-07-03).

특수폴더(tests/secure_zone_template_manage_folder/_base.py)에서 검증된 자산 전부 포함:
sub-numbering(_add) / merge_key / _shot(캡션) / _replay_shots(큐레이션 리턴 재생) / _R 자동 안전망.
정책 _base 의 _ss(crop 캡처)/_r(ScanResult 빌더) 재사용. PAGE_ID + cleanup 만 다름.
cleanup: sc1 시작 = cleanup_with_keep([AUTO]+[AUTO_KEEP] 전부, clean slate) — 기존 스위트와 동일.
"""
import re
import pytest

from core.models import ScanResult, PageScanReport
from tests.secure_zone_policy._base import _ss, _r   # 공유 헬퍼(crop 스크린샷 포함)

_SAVE_SUCCESS_KEYWORDS = ("하시겠습니까", "저장 하였습니다", "저장하였습니다",
                          "추가되었습니다", "수정되었습니다", "하였습니다")


class OperationProcessBase:
    """운용 프로세스 공통 base."""

    PAGE_ID = "common_operation_process"

    _SESSION_CLEANUP_DONE = False
    _SC_DEFAULT_TIMEOUT = 8000

    # 전역 리턴 재생: fail 카드 발생 시 같은 테스트를 '_R' 모드로 1회 재실행 —
    # _add 지점마다 자동 캡처 → "… 리턴 재생(_R)" 카드 1장. 큐레이션(screenshots) 있는 fail 은 제외.
    _REPLAY_ON_FAIL = True
    _REPLAY_MAX_FRAMES = 10

    def _ensure_session_cleanup(self, page) -> None:
        """sc1 시작 clean slate — [AUTO] + [AUTO_KEEP] 일괄 삭제 (1회). 실데이터 보존."""
        if OperationProcessBase._SESSION_CLEANUP_DONE:
            return
        try:
            page.page.wait_for_timeout(200)
            page.cleanup_with_keep()
            if hasattr(self, "_add"):
                self._add("pass", "sc1 — session 시작 cleanup ([AUTO]+[AUTO_KEEP] 일괄 삭제, clean slate)",
                          "잔여 테스트 데이터 정리 완료", sc=1)
        except Exception as e:
            if hasattr(self, "_add"):
                self._add("warn", "sc1 — session cleanup 예외", f"예외: {e!r}", sc=1)
        OperationProcessBase._SESSION_CLEANUP_DONE = True

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
        # ── 전역 리턴 재생(_R): 큐레이션 없는 fail 이 있으면 같은 테스트를 캡처 모드로 1회 재실행 ──
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

    def _replay_shots(self, steps) -> list:
        """이슈 확정 후 '1회 리턴 재생' — 스텝을 다시 실행하며 단계별 캡처(캡션 포함).
        steps: [(라벨, 동작fn 또는 None, 캡처대상 Locator 또는 None=전체 화면), ...]"""
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

    # ── 글자수 제한 스캔 (생성/수정 공용 — sc3/sc4 미러가 같은 헬퍼 사용) ──
    _OV_LENS = (101, 501, 1001)

    def _overflow_scan_field(self, p, field_def: dict, mode: str, tag: str,
                             item: str = None, sc: int = 0) -> None:
        """한 필드를 [101,501,1001] 사다리로 첫 서버 오류 지점 탐색 → 카드 1장(요소별).

        mode='생성'(ADD 모달, 길이별 유니크 이름 — 중복 오탐 방지) / '수정'(item 수정 모달, 이름 제외).
        오류 시 리턴 재생 2컷(특수폴더 sc3s 패턴): ①오류 위치(입력 상태) ②제출 재클릭 → 경고 모달 재발생.
        merge_key='cm_ovf::필드::판정::결과분류' — 생성/수정 간 같은 요소·같은 결과만 결함 카드 1장으로 묶임.
        """
        label, sel, fid = field_def["label"], field_def["selector"], field_def.get("id", "fld")
        is_name = (fid == "processName")
        error_at, err_msg, shots = None, "", None
        for ln in self._OV_LENS:
            big = "A" * ln
            try:
                if mode == "생성":
                    p.open_add_modal()
                    if is_name:
                        # 이름 필드 자체 스캔 — 값이 길이별로 달라 자연 유니크
                        big = "[AUTO]_ov_" + "A" * max(1, ln - 10)
                    else:
                        # 길이별 유니크 이름 — 이전 길이 저장 성공 시 중복 에러가 오류로 오탐되는 것 방지
                        p.page.locator(p.SEL_PROCESS_NAME).first.evaluate(
                            "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }",
                            f"[AUTO]_ov_{fid}_{ln}")
                else:
                    p.open_modify_modal(item)
                p.page.locator(sel).first.evaluate(
                    "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }", big)
                p.page.wait_for_timeout(200)
                p.try_submit()
                modal_shown = False
                try:
                    p.page.locator(p.SEL_CONFIRM_MODAL).wait_for(state="attached", timeout=6000)
                    modal_shown = True
                except Exception:
                    pass
                if modal_shown:
                    msg = p.get_modal_message()
                    is_err = ("오류" in msg) or ("실패" in msg) or ("에러" in msg)
                    if (not is_err) and any(kw in msg for kw in _SAVE_SUCCESS_KEYWORDS):
                        p.click_attached(p.SEL_CONFIRM_BTN)
                        p.wait_for_confirm_modal_closed()
                        p.wait_for(p.SEL_ADD_BTN)
                        continue
                    # 오류 — 2컷: 모달 dismiss(값 잔존) → ①필드 입력상태 → 제출 재클릭 → ②경고 재발생
                    error_at, err_msg = ln, msg
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
                    shot_field = self._shot(f"{label}_{ln}자_입력상태",
                                            highlight=p.page.locator(sel),
                                            caption=f"1. {label} — {ln}자 입력 상태(오류 위치)")
                    shot_modal = None
                    try:
                        p.try_submit()
                        p.page.locator(p.SEL_CONFIRM_MODAL).wait_for(state="attached", timeout=6000)
                        p.page.wait_for_timeout(300)
                        shot_modal = self._shot(f"{label}_{ln}자_경고모달",
                                                caption=f"2. 저장 재시도 → 경고 모달 {msg!r}")
                        p.dismiss_confirm_modal()
                        p.wait_for_confirm_modal_closed()
                    except Exception:
                        pass
                    shots = [s for s in (shot_field, shot_modal) if s] or None
                else:
                    # 경고 없음 — 커밋 여부 확인
                    if mode == "생성":
                        p.ensure_auto_filter()
                        saved = any(n.startswith("[AUTO]_ov_") for n in p.get_item_names())
                    else:
                        p._close_modal_if_open()
                        p.open_modify_modal(item)
                        saved = len(p.get_field_value(sel)) >= ln
                        p.close_modal()
                    if not saved:
                        error_at, err_msg = ln, "(경고 모달 없음 · 미커밋)"
            except Exception as e:
                error_at, err_msg = ln, f"(예외: {e!r})"
            finally:
                for _ in range(3):
                    if p.page.locator(p.SEL_MODAL_OPEN).count() == 0:
                        break
                    try:
                        p.page.locator(p.SEL_CANCEL_BTN).first.evaluate("el => el.click()")
                        p.page.wait_for_timeout(300)
                    except Exception:
                        break
            if error_at:
                break
        if error_at:
            prev = [l for l in self._OV_LENS if l < error_at]
            cls = f"err@{error_at}"
            detail = ((f"{prev[-1]}자 허용, " if prev else "")
                      + f"{error_at}자 입력 시 경고={err_msg!r} "
                      "(graceful 글자수 검증 메시지 부재 — known_bug)")
        else:
            cls = "nolimit"
            detail = f"{self._OV_LENS[-1]}자까지 입력 가능 — 서버 측 글자수 제한 없음 (known issue)"
        self._add("warn", f"{tag} — {label} 글자수 제한 스캔({mode})",
                  f"입력: {label}에 {'/'.join(map(str, self._OV_LENS))}자 사다리 / 결과: {detail}",
                  sc=sc, screenshot=not shots, screenshots=shots,
                  merge_key=f"cm_ovf::{label}::warn::{cls}",   # 같은 요소 + 같은 결과만 묶임(생성/수정 간)
                  repro=f"1. {'추가' if mode == '생성' else '수정'} 모달 {label}에 장문 입력\n"
                        f"2. 저장\n3. 경고 종류 확인(서버 오류면 검증 부재)")

    def _shot(self, label: str, highlight=None, caption: str = None):
        """중간 시점 추가 캡처 — 두 화면 대조/부재 대비 판정 전용. caption 지정 시 스텝 라벨 표시."""
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
        """sub-numbering + ScanResult 누적 (특수폴더 _add 와 동일 규약)."""
        # 리턴 재생(_R) 모드: 카드 대신 검증 지점 화면만 수집(캡션 = 순번+판정+라벨)
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
