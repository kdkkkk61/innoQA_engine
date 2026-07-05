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
    # 오버플로 헬퍼의 이름 필드(필수 필드) — 서브클래스(태그 등)가 재정의해 재사용
    NAME_FIELD_SEL_ATTR = "SEL_PROCESS_NAME"
    NAME_FIELD_ID = "processName"

    _CLEANUP_DONE_PAGES: set = set()   # 페이지별 세션 cleanup 1회 플래그 (서브클래스 공유 dict)
    _SC_DEFAULT_TIMEOUT = 8000

    # 전역 리턴 재생: fail 카드 발생 시 같은 테스트를 '_R' 모드로 1회 재실행 —
    # _add 지점마다 자동 캡처 → "… 리턴 재생(_R)" 카드 1장. 큐레이션(screenshots) 있는 fail 은 제외.
    _REPLAY_ON_FAIL = True
    _REPLAY_MAX_FRAMES = 10

    def _ensure_session_cleanup(self, page) -> None:
        """시작 clean slate — [AUTO]+[AUTO_KEEP]+날짜본 일괄 삭제 (페이지당 세션 1회). 실데이터 보존."""
        if self.PAGE_ID in OperationProcessBase._CLEANUP_DONE_PAGES:
            return
        try:
            page.page.wait_for_timeout(200)
            page.cleanup_with_keep()
            if hasattr(self, "_add"):
                self._add("pass", "session 시작 cleanup ([AUTO]+[AUTO_KEEP]+날짜본 일괄 삭제, clean slate)",
                          "잔여 테스트 데이터 정리 완료", sc=1)
        except Exception as e:
            if hasattr(self, "_add"):
                self._add("warn", "session cleanup 예외", f"예외: {e!r}", sc=1)
        OperationProcessBase._CLEANUP_DONE_PAGES.add(self.PAGE_ID)

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

    # ── sc0 UIScanner 결과 보고 (공용 — 카드 규칙 준수판, 2026-07-03 재설계) ──
    def _report_scan(self, report, tag: str, page=None,
                     modal_open_fn=None, modal_close_fn=None) -> None:
        """yaml↔DOM diff 결과 → 카드.

        레거시(건수 나열 + 기계 텍스트) 대체:
        - 요약 카드: 변경 요소를 이름으로 명시(건수만 X), 자동 캡처 없음(모달 닫힌 뒤라 판정 지점 아님).
        - 변경 카드(요소별): 사람이 읽는 설명 + 모달을 다시 열어 해당 요소를 빨간 표시로 캡처(판정 지점).
          삭제(=요소 없음)는 '있어야 할 모달 현재 상태' 전체 컷으로 부재 증거.
        """
        _DISCOVERY = ("discovered_new", "discovered_missing", "discovered_hidden")
        added   = [r for r in report.results if r.pattern == "discovered_new"]
        deleted = [r for r in report.results if r.pattern == "discovered_missing"]
        hidden  = [r for r in report.results if r.pattern == "discovered_hidden"]
        scan_fails = [r for r in report.results
                      if r.status == "fail" and r.pattern not in _DISCOVERY]
        scan_warns = [r for r in report.results
                      if r.status == "warn" and r.pattern not in _DISCOVERY]
        scan_pass  = [r for r in report.results if r.status == "pass"]

        def _sel_of(r):
            if getattr(r, "selector", None):
                return r.selector
            m = re.search(r"\(((?:input|textarea|select|button|div)#[\w-]+)\)", r.label or "")
            return m.group(1) if m else ""

        # 요약 — 변경 요소를 이름으로 명시
        changed_names = ([f"추가 {_sel_of(r)}" for r in added]
                         + [f"삭제 {_sel_of(r)}" for r in deleted]
                         + [f"숨김 {_sel_of(r)}" for r in hidden])
        changed = len(changed_names)
        self._add("warn" if changed else "pass",
                  f"{tag} — [UIScanner] 변경사항 감지 (yaml ↔ DOM 명세 대조)",
                  (f"명세와 다른 요소 {changed}건: " + " / ".join(changed_names) + " — 아래 요소별 카드 참조. "
                   if changed else "변경 없음 — yaml 명세와 DOM 일치. ")
                  + f"(요소 검증 pass={len(scan_pass)}건, fail={len(scan_fails)}건, warn={len(scan_warns)}건)",
                  sc=0, screenshot=False)
        # 변경 카드 — 요소별, 판정 지점(모달 안 해당 요소) 재캡처
        for kind, items, why in (
                ("추가", added,   "yaml 명세에 없는 요소가 모달 DOM에 존재 — 신규 기능 등장 또는 명세 누락"),
                ("삭제", deleted, "yaml 명세 요소가 모달 DOM에서 사라짐 — 기능 삭제 또는 셀렉터 변경 의심"),
                ("숨김", hidden,  "요소가 DOM에 있으나 display:none — 기능 숨김/조건부 노출 의심")):
            for r in items:
                sel = _sel_of(r)
                shot = None
                if page is not None and modal_open_fn is not None:
                    try:
                        modal_open_fn()
                        page.page.wait_for_timeout(500)
                        if kind == "삭제" or not sel:
                            shot = self._shot(f"sc0_{kind}_{sel or 'unknown'}",
                                              caption=f"1. 모달 현재 상태 — {sel!r} 요소가 있어야 하나 미존재")
                        else:
                            shot = self._shot(f"sc0_{kind}_{sel}",
                                              highlight=page.page.locator(sel),
                                              caption=f"1. 모달 — 명세와 다른 요소(빨간 표시): {sel}")
                    except Exception:
                        shot = None
                    finally:
                        try:
                            if modal_close_fn is not None:
                                modal_close_fn()
                        except Exception:
                            pass
                self._add("warn", f"{tag} — 변경사항({kind}) — {sel or (r.label or '')}",
                          f"{why}. 요소: {sel or '(셀렉터 미상)'} / "
                          "조치: 의도된 변경이면 yaml 명세 갱신 후 정식 검증, 아니면 제품 확인 필요.",
                          sc=0, screenshot=False, screenshots=[shot] if shot else None,
                          repro=f"1. 모달 열기\n2. {sel or '해당 요소'} {'부재' if kind == '삭제' else '존재/상태'} 확인\n"
                                "3. yaml 명세와 대조")
        for r in scan_fails + scan_warns:
            self._add(r.status, f"{tag} — [UI 패턴] {r.label}",
                      r.detail or f"selector: {getattr(r, 'selector', '')!r}", sc=0)

    # ── 다운로드 버튼 동작 검증 (존재 확인 ≠ 동작 검증 — 실감지) ──
    def _verify_download_button(self, p, btn_sel: str, label: str, tag: str, sc: int) -> None:
        """버튼 클릭 → Playwright download 이벤트 실감지. 파일은 저장하지 않음(감지 후 cancel).
        내용 검증은 수동 범위 — 카드에 명시."""
        if p.page.locator(btn_sel).count() == 0:
            self._add("fail", f"{tag} — {label} 버튼 다운로드 동작",
                      f"버튼 없음: {btn_sel}", sc=sc)
            return
        try:
            with p.page.expect_download(timeout=10_000) as dl_info:
                p.page.locator(btn_sel).first.evaluate("el => el.click()")
            dl = dl_info.value
            fname = dl.suggested_filename
            try:
                dl.cancel()
            except Exception:
                pass
            self._add("pass", f"{tag} — {label} 버튼 다운로드 동작",
                      f"입력: {label} 클릭 / 결과: 다운로드 발생 — 파일명 {fname!r} (파일 내용 검증은 수동)",
                      sc=sc, repro=f"1. {label} 버튼 클릭\n2. 파일 다운로드 발생 확인")
        except Exception as e:
            # 다운로드 대신 경고 모달이 뜨는 경우 포함 — 현재 화면 상태로 판정 지점 캡처
            msg = ""
            try:
                if p.is_confirm_modal_visible():
                    msg = p.get_modal_message()
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
            except Exception:
                pass
            self._add("warn", f"{tag} — {label} 버튼 다운로드 동작",
                      f"입력: {label} 클릭 / 결과: 다운로드 이벤트 미감지({type(e).__name__})"
                      + (f", 경고={msg!r}" if msg else "") + " — 동작/환경 확인 필요", sc=sc,
                      repro=f"1. {label} 버튼 클릭\n2. 다운로드/경고 여부 확인")

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
        name_sel = getattr(p, self.NAME_FIELD_SEL_ATTR)
        is_name = (fid == self.NAME_FIELD_ID)
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
                        p.page.locator(name_sel).first.evaluate(
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
