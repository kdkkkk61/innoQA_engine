"""
tests/test_npouch.py — nPouch QA 테스트

파이프라인: ScanResult/PageScanReport → conftest 수집 → html_reporter HTML 생성
           (랜섬크런처와 동일 파이프라인, 클래스 구조만 다름)

실행:
  pytest tests/test_npouch.py -m npouch -v -s
  pytest tests/test_npouch.py::TestNpouchOperationProcess -v -s
"""
import re
import time
import yaml
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport
from pages.npouch_operation_process_page import NpouchOperationProcessPage

# ── scan_hints YAML 로드 ──────────────────────────────────────────
def _load_hints(page_id: str) -> dict:
    path = Path(__file__).parent.parent / "config" / "scan_hints" / f"{page_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}

# ── 스크린샷 저장 ─────────────────────────────────────────────────
_SS_DIR = Path(__file__).parent.parent / "reports" / "screenshots"

def _ss(page, label: str, highlight=None) -> str | None:
    """warn/fail 시점 스크린샷 저장 → 경로 반환. 실패하면 None.

    highlight (Locator) 가 있으면 빨간 outline 임시 주입 + 스크롤 후 캡처 → 복원.
    None 이면 기존 동작 (viewport 캡처). origin_protect _ss 와 동일 헬퍼.
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

# ── 모듈 상수 ─────────────────────────────────────────────────────────────────
_AUTO_PROCESS   = "[AUTO]_cm_process"
_AUTO_PROC_FULL = "[AUTO]_cm_proc_full"
_AUTO_PROC_REQ  = "[AUTO]_cm_proc_req"
_SHA2_VALID     = "AABB112233445566778899001122334455667788990011223344556677889900"
_EXEC_TEST      = r"C:\auto\test_proc.exe"   # 실행경로 테스트용

_STATUS_ICON  = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]", "warn": "[WARN]"}
_STATUS_TO_SR = {"pass": "pass", "fail": "fail", "warn": "warn", "skip": "skip"}

# 성공 메시지 키워드 — "저장 하였습니다" / "하시겠습니까" 등 페이지마다 다름
_SAVE_SUCCESS_KEYWORDS = ("하시겠습니까", "저장 하였습니다", "저장하였습니다",
                           "추가되었습니다", "수정되었습니다", "하였습니다")


def _r(status: str, label: str, detail: str = "", sc: int = 0,
       page=None, highlight=None, repro=None, merge_key: str = None) -> tuple[str, ScanResult]:
    """print용 문자열 + ScanResult 동시 생성.
    page 전달 시 warn/fail 이면 스크린샷 자동 저장 → extra["screenshot"] 첨부.
    highlight (Locator) 전달 시 캡처에 빨간 outline 표시 (origin_protect 와 동일).
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


# ══════════════════════════════════════════════════════════════════════════════
# 1. 운용 프로세스
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.npouch
class TestNpouchOperationProcess:
    PAGE_NAME = "운용 프로세스"
    PAGE_ID   = "common_operation_process"

    @pytest.fixture(autouse=True)
    def setup(self, request, logged_in_page, settings):
        self._request = request
        self.p = NpouchOperationProcessPage(logged_in_page, settings)
        self._hints = _load_hints(self.PAGE_ID)
        self.p.navigate_to()

    def _attach(self, scan_results: list[ScanResult]) -> None:
        """PageScanReport 를 test node 에 첨부 — conftest 가 수집함."""
        report = PageScanReport(page_id=self.PAGE_ID)
        report.results = scan_results
        self._request.node._scan_report    = report
        self._request.node._npouch_page_id = self.PAGE_ID

    # ── 시나리오 1: UI 구조 ───────────────────────────────────────────────────
    def test_scenario1_ui(self):
        """시나리오 1: UI 구조 — 탭(skip) / 버튼 / 테이블 헤더 / 검색창"""
        print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 1: UI 구조 ━━━━━━━━━━━━━━━━━━━━━━━━")
        page = self.p.page
        lines, srs = [], []

        # sc1 시작 — clean slate ([AUTO] + [AUTO_KEEP] 일괄 삭제)
        try:
            self.p.cleanup_with_keep()
        except Exception:
            pass

        # 탭 전환 — 해당 없음 (단일 뷰)
        t, s = _r("skip", "탭 전환", "단일 뷰 페이지 — 탭 없음", sc=1)
        lines.append(t); srs.append(s)

        # 버튼 존재
        for btn_id, label in [
            ("addItemBtn",     "추가 버튼"),
            ("modifyItemBtn",  "수정 버튼"),
            ("removeItemBtn",  "삭제 버튼"),
            ("excelDownload",  "EXCEL 다운로드 버튼"),
            ("importFileBtn",  "가져오기 버튼"),
            ("downloadFileBtn","내보내기 버튼"),
        ]:
            exists = page.locator(f"button#{btn_id}").count() > 0
            t, s = _r(
                "pass" if exists else "fail",
                f"{label} — 존재",
                f"입력: (없음) / 결과: {'존재' if exists else '없음'}",
                sc=1,
            )
            lines.append(t); srs.append(s)

        # 테이블 헤더 (이름 컬럼 라벨은 빌드차: '프로세스명'/'프로세스 이름' 둘 다 허용)
        headers = [th.inner_text().strip() for th in page.locator("table thead th").all()]
        print(f"  실제 헤더: {headers}")
        header_specs = [
            ("프로세스명/이름", {"프로세스명", "프로세스 이름"}),
            ("서명", {"서명"}), ("설명", {"설명"}),
            ("등록일", {"등록일"}), ("수정일", {"수정일"}),
        ]
        for label, accept in header_specs:
            ok = any(a in headers for a in accept)
            t, s = _r(
                "pass" if ok else "fail",
                f"테이블 헤더 — {label}",
                f"입력: (없음) / 결과: {'존재' if ok else '없음'}",
                sc=1,
            )
            lines.append(t); srs.append(s)

        # 검색 영역
        search_inp = page.locator("input#searchText")
        search_sel = page.locator("select#searchOption")
        search_btn = page.locator("button#searchBtn")
        for loc, label in [
            (search_inp, "검색창 — 존재"),
            (search_sel, "검색 옵션 셀렉트 — 존재"),
            (search_btn, "검색 버튼 — 존재"),
        ]:
            exists = loc.count() > 0
            t, s = _r(
                "pass" if exists else "fail",
                label,
                f"입력: (없음) / 결과: {'존재' if exists else '없음'}",
                sc=1,
            )
            lines.append(t); srs.append(s)

        if search_sel.count() > 0:
            options = [opt.inner_text().strip() for opt in search_sel.locator("option").all()]
            print(f"  검색 옵션: {options}")
            t, s = _r("pass", "검색 옵션 목록", str(options), sc=1)
            lines.append(t); srs.append(s)

        for r in lines:
            print(r)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 1")

    # ── 시나리오 2: 입력 구조 ─────────────────────────────────────────────────
    def test_scenario2_modal_fields(self):
        """시나리오 2: 입력 구조 — 모달 필드 / 초기값 / maxlength(전 필드) / 필수 검증"""
        print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 2: 입력 구조 ━━━━━━━━━━━━━━━━━━━━━━━")
        p = self.p
        page = p.page
        lines, srs = [], []
        _hints = self._hints   # field_constraint_tests 루프보다 먼저 정의

        p.open_add_modal()

        # 모달 제목 / 버튼 텍스트
        title = p.get_modal_title()
        t, s = _r("pass" if "추가" in title else "warn", "모달 제목",
                  f"입력: 모달 오픈 / 결과: 제목={title!r}", sc=2)
        lines.append(t); srs.append(s)

        submit_text = page.locator(p.SEL_SUBMIT_BTN).first.inner_text().strip()
        cancel_text = page.locator(p.SEL_CANCEL_BTN).first.inner_text().strip()
        for txt, expected, label in [
            (submit_text, "추가", "추가(제출) 버튼 텍스트"),
            (cancel_text, "취소", "취소 버튼 텍스트"),
        ]:
            t, s = _r("pass" if txt == expected else "warn", label,
                      f"입력: 버튼 텍스트 확인 / 결과: {txt!r}", sc=2)
            lines.append(t); srs.append(s)

        # 전체 필드: 존재 / 초기값 / DOM maxlength (필수/선택 무관하게 전부 확인)
        fields = [
            (p.SEL_PROCESS_NAME, "프로세스 이름(*)"),
            (p.SEL_SIGN,         "서명"),
            (p.SEL_SHA2,         "SHA2"),
            (p.SEL_EXEC_PATH,    "실행경로"),
            (p.SEL_DESCRIPTION,  "설명"),
        ]
        for sel, label in fields:
            exists = page.locator(sel).count() > 0
            t, s = _r("pass" if exists else "fail", f"{label} — 필드 존재",
                      f"입력: (없음) / 결과: {'존재' if exists else '없음'}", sc=2)
            lines.append(t); srs.append(s)
            if not exists:
                continue
            val = p.get_field_value(sel)
            t, s = _r("pass" if val == "" else "warn", f"{label} — 초기값",
                      f"입력: 초기 상태 / 결과: {val!r}", sc=2)
            lines.append(t); srs.append(s)
            # DOM maxlength 는 사실 정보만 (None = client 제한 없음).
            # 실제 길이 검증 결함은 overflow_scan 이 입력+저장+서버응답으로 잡음 (중복 warn 제거).
            ml = page.locator(sel).first.get_attribute("maxlength")
            t, s = _r("pass", f"{label} — DOM maxlength",
                      f"결과: {ml!r}"
                      + (" (client 제한 없음 — 길이 검증은 글자수 제한 스캔 참조)" if ml is None else ""),
                      sc=2)
            lines.append(t); srs.append(s)

        # SHA2 추가 정보
        if page.locator(p.SEL_SHA2).count() > 0:
            t, s = _r("pass", "SHA2 — 필수 여부",
                      "입력: (없음) / 결과: 선택(optional)", sc=2)
            lines.append(t); srs.append(s)
            t, s = _r("warn", "SHA2 — 포맷 검증",
                      "입력: hex 이외 문자열 / 결과: 포맷 검증 없음", sc=2)
            lines.append(t); srs.append(s)

        # 빈 이름 제출 검증
        p.try_submit()
        p.page.wait_for_timeout(500)
        if p.is_confirm_modal_visible():
            msg = p.get_modal_message()
            expected_empty = "프로세스 이름을 입력해 주세요."
            t, s = _r("pass" if msg == expected_empty else "warn",
                      "프로세스 이름(*) — 빈 값 제출 경고",
                      f"입력: 이름 비운 채 제출 / 결과: {msg!r}", sc=2,
                      page=p.page if msg != expected_empty else None)
            lines.append(t); srs.append(s)
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        else:
            t, s = _r("fail", "프로세스 이름(*) — 빈 값 제출 경고",
                      "에러 모달 미표시", sc=2)
            lines.append(t); srs.append(s)

        # overflow 스캔은 각자 모달을 새로 열므로, 여기서 반드시 닫아야 함
        p.close_modal()

        # ── 자동 글자수 제한 스캔 (overflow_scan: true 필드만) ──────────
        # YAML 설정 불필요 — [101, 501, 1001]자 순서로 시도해 첫 서버 오류 지점 탐색
        _OV_LENS = [101, 501, 1001]
        for field_def in _hints.get("fields", []):
            if not field_def.get("overflow_scan"):
                continue
            _ov_label  = field_def["label"] + " — 글자수 제한 스캔"
            _ov_sel    = field_def["selector"]
            _ov_prefix = field_def.get("overflow_prefix", "[AUTO]_ov_")
            # prefix 끝 "_" 제거한 짧은 검색어 — 검색창에 짧게 입력하기 위함
            _ov_search = _ov_prefix.rstrip("_")
            _ov_error_at   = None   # 첫 서버 오류 발생 길이
            _ov_any_saved  = False  # 하나라도 저장됐으면 cleanup 필요
            _ov_ss         = None   # 에러 모달 스크린샷 경로
            # 비-이름 필드는 유효 processName 먼저 채워야 함
            # (이름 빈값이면 "프로세스 이름을 입력해 주세요" 가 먼저 떠 필드 길이검증 못 함)
            _ov_is_name  = (field_def.get("id") == "processName")
            _ov_name_val = _ov_prefix + (field_def.get("id") or "fld")  # 저장 시 검색용 이름 ([AUTO]_ov_sign 등)
            for _ov_len in _OV_LENS:
                _ov_remain = max(0, _ov_len - len(_ov_prefix))
                if _ov_is_name:
                    _ov_value = _ov_prefix + "A" * _ov_remain   # 긴 값 자체가 이름
                else:
                    _ov_value = "A" * _ov_len                    # 긴 값 = 대상 필드 (이름은 별도)
                try:
                    p.open_add_modal()
                    if not _ov_is_name:
                        # 유효 이름 먼저 채움 (검색 가능한 짧은 이름)
                        p.page.locator(p.SEL_PROCESS_NAME).first.evaluate(
                            "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }",
                            _ov_name_val
                        )
                    p.page.locator(_ov_sel).first.evaluate(
                        "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }",
                        _ov_value
                    )
                    p.page.wait_for_timeout(200)
                    p.try_submit()
                    # 서버 응답 모달 출현까지 대기 — 긴 값(1001자 등)은 서버 처리가 600ms 보다 느림.
                    # 즉시 count() 검사 시 느린 500 에러 모달을 놓쳐 '저장됨' 으로 오판 (사용자 보고 2026-06-04).
                    _ov_modal = False
                    try:
                        p.page.locator(p.SEL_CONFIRM_MODAL).wait_for(
                            state="attached", timeout=6000
                        )
                        _ov_modal = True
                    except Exception:
                        _ov_modal = False
                    if _ov_modal:
                        msg_ov = p.get_modal_message()
                        # 에러 키워드 먼저 검사 — "오류가 발생 하였습니다" 가 success "하였습니다" 에 오분류되는 것 방지
                        _ov_is_err = ("오류" in msg_ov) or ("실패" in msg_ov) or ("에러" in msg_ov)
                        if (not _ov_is_err) and any(kw in msg_ov for kw in _SAVE_SUCCESS_KEYWORDS):
                            p.click_attached(p.SEL_CONFIRM_BTN)
                            p.wait_for_confirm_modal_closed()
                            p.wait_for(p.SEL_ADD_BTN)
                            _ov_any_saved = True
                        else:
                            # "서버에서 오류가 발생 하였습니다" 등 → 글자수 제한 지점
                            # 에러 모달 떠 있는 동안 캡처 (dismiss 전) — 문제 필드 빨간 하이라이트 (헬퍼 위임)
                            _ov_ss = _ss(p.page, f"{_ov_label}_{_ov_len}자_서버오류",
                                         highlight=p.page.locator(_ov_sel))
                            p.dismiss_confirm_modal()
                            p.wait_for_confirm_modal_closed()
                            _ov_error_at = _ov_len
                    else:
                        # 모달 안 뜸 — 재검색으로 실제 저장 여부 확인 (no-modal=저장 가정 금지)
                        try:
                            p.search_item(_ov_search)
                            p.page.wait_for_timeout(300)
                            _saved_now = any(
                                n.startswith(_ov_search) for n in p.get_item_names()
                            )
                        except Exception:
                            _saved_now = False
                        if _saved_now:
                            _ov_any_saved = True
                        else:
                            _ov_error_at = _ov_len
                except Exception:
                    _ov_error_at = _ov_len
                finally:
                    for _ in range(3):
                        if p.page.locator(p.SEL_MODAL_OPEN).count() == 0:
                            break
                        try:
                            p.page.locator(p.SEL_CANCEL_BTN).first.evaluate("el => el.click()")
                            p.page.wait_for_timeout(300)
                        except Exception:
                            break
                if _ov_error_at:
                    break   # 오류 지점 발견 → 더 이상 시도 불필요

            # ── 결과 보고 (스크린샷 먼저 → 삭제 나중) ──────────────
            if _ov_error_at:
                prev = [l for l in _OV_LENS if l < _ov_error_at]
                if prev:
                    detail_ov = (str(prev[-1]) + "자 허용, " + str(_ov_error_at)
                                 + "자 이상 입력 시 generic '서버에서 오류가 발생' 응답 "
                                 "(graceful 글자수 검증 메시지 부재 — known_bug)")
                else:
                    detail_ov = (str(_ov_error_at) + "자 이상 입력 시 generic '서버에서 오류가 발생' 응답 "
                                 "(graceful 글자수 검증 메시지 부재 — known_bug)")
                # generic 500 = 일반 결함 (🔴 높음 아님) → 일반 warn + 캡처
                t, s = _r("warn", _ov_label, detail_ov, sc=2)
                if _ov_ss:
                    s.extra["screenshot"] = _ov_ss   # 에러 모달 캡처 첨부 (defect 카드에 렌더링)
            else:
                detail_ov = (str(_OV_LENS[-1]) + "자까지 입력 가능 "
                             "— 서버 측 글자수 제한 없음 (known issue)")
                t, s = _r("warn", _ov_label, detail_ov, sc=2)
            lines.append(t); srs.append(s)

            # ── cleanup: prefix로 검색 → 한 번에 한 개씩 삭제 ────────
            # delete_item(1001자 이름) 대신 짧은 prefix 검색으로 우회
            if _ov_any_saved:
                try:
                    for _ in range(len(_OV_LENS)):  # 최대 OV_LENS 개수만큼 반복
                        p.search_item(_ov_search)
                        p.page.wait_for_timeout(400)
                        _ov_found = False
                        for _ov_row in p.page.locator(p.SEL_TABLE_ROW).all():
                            _ov_tds = _ov_row.locator("td").all()
                            if (len(_ov_tds) >= 2
                                    and _ov_tds[0].inner_text().strip().startswith(_ov_prefix)):
                                _ov_cb = _ov_row.locator("input[type='checkbox']").first
                                p._toggle_overlay(False)
                                try:
                                    _ov_cb.click()
                                finally:
                                    p._toggle_overlay(True)
                                p.page.locator(p.SEL_DELETE_BTN).first.evaluate("el => el.click()")
                                p.page.wait_for_timeout(400)
                                if p.is_confirm_modal_visible():
                                    p.click_attached(p.SEL_CONFIRM_BTN)
                                    p.wait_for_confirm_modal_closed()
                                p.wait_for(p.SEL_ADD_BTN)
                                _ov_found = True
                                break
                        if not _ov_found:
                            break  # 더 이상 삭제할 항목 없음
                except Exception:
                    pass
            p._restore_page_size()

        # 중복 이름 에러 (notepad.exe — 시스템에 항상 존재하는 프로세스명 사용)
        # 매번 독립적으로 모달 열기 (앞 테스트 상태에 의존하지 않음)
        try:
            p.open_add_modal()
            p.fill(p.SEL_PROCESS_NAME, "notepad.exe")
            p.try_submit()
            p.page.wait_for_timeout(600)
            if p.is_confirm_modal_visible():
                msg_dup = p.get_modal_message()
                expected_dup = "이미 등록된 프로세스 입니다"
                ok_dup = msg_dup == expected_dup
                t, s = _r("pass" if ok_dup else "warn",
                          "프로세스 이름(*) — 중복 이름 에러",
                          f"입력: 'notepad.exe'(기존 등록명) 제출 / 결과: {msg_dup!r}",
                          sc=2, page=p.page if not ok_dup else None)
                lines.append(t); srs.append(s)
                p.dismiss_confirm_modal()
                p.wait_for_confirm_modal_closed()
            else:
                t, s = _r("warn", "프로세스 이름(*) — 중복 이름 에러",
                          "에러 모달 없음 (확인 필요 — notepad.exe 미등록?)",
                          sc=2, page=p.page)
                lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("warn", "프로세스 이름(*) — 중복 이름 에러", str(e), sc=2)
            lines.append(t); srs.append(s)

        p.close_modal()

        # ── YAML 기반 포맷 검증 테스트 (페이지마다 다름 — yaml 없으면 스킵) ──
        for fv in _hints.get("format_validation_tests", []):
            _fv_label     = fv.get("label", "포맷 검증 테스트")
            _fv_value     = fv.get("test_value", "INVALID")
            _fv_expect    = fv.get("expect_validation", True)
            _fv_field     = fv.get("field", "sha2")
            _fv_item_name = fv.get("item_name", f"[AUTO]_fv_{_fv_field}")
            _fv_sel = next(
                (f["selector"] for f in _hints.get("fields", []) if f["id"] == _fv_field),
                f"textarea#{_fv_field}"
            )
            p.open_add_modal()
            p.fill(p.SEL_PROCESS_NAME, _fv_item_name)
            fv_loc = p.page.locator(_fv_sel).first
            fv_loc.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }",
                _fv_value
            )
            p.page.wait_for_timeout(200)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p.page.wait_for_timeout(600)
            if p.is_confirm_modal_visible():
                msg_fv = p.get_modal_message()
                if any(kw in msg_fv for kw in _SAVE_SUCCESS_KEYWORDS):
                    p.click_attached(p.SEL_CONFIRM_BTN)
                    p.wait_for_confirm_modal_closed()
                    p.wait_for(p.SEL_ADD_BTN)
                    actual_validated = False
                else:
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
                    actual_validated = True
            else:
                actual_validated = False
            # expect_validation:false = 검증 없음이 알려진 이슈 → 여전히 없으면 warn(스크린샷), 생기면 pass(개선)
            # expect_validation:true  = 검증이 있어야 함        → 있으면 pass, 없으면 fail(스크린샷)
            if not _fv_expect:
                status_fv = "pass" if actual_validated else "warn"
            else:
                status_fv = "pass" if actual_validated else "fail"
            # 저장된 경우: 해당 항목 검색 → 목록에 보인 상태로 스크린샷
            t, s = _r(status_fv, _fv_label,
                      f"입력: {_fv_value!r} 제출 / 결과: {'검증됨(에러)' if actual_validated else '검증 없이 저장됨 (known issue)'}",
                      sc=2)
            lines.append(t); srs.append(s)
            p.close_modal()
            # 저장된 항목 정리
            if not actual_validated:
                try:
                    p.delete_item(_fv_item_name)
                except Exception:
                    pass
            p._restore_page_size()

        # ── YAML 기반 특수문자 테스트 (페이지마다 다름 — yaml 없으면 스킵) ──
        for sc_test in _hints.get("special_char_tests", []):
            _sc_label   = sc_test.get("label", "특수문자 테스트")
            _sc_value   = sc_test.get("test_value", "")
            _sc_expect  = sc_test.get("expect_block", False)
            p.open_add_modal()
            p.fill(p.SEL_PROCESS_NAME, _sc_value)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p.page.wait_for_timeout(600)
            if p.is_confirm_modal_visible():
                msg_sc = p.get_modal_message()
                if any(kw in msg_sc for kw in _SAVE_SUCCESS_KEYWORDS):  # 저장됨
                    p.click_attached(p.SEL_CONFIRM_BTN)
                    p.wait_for_confirm_modal_closed()
                    p.wait_for(p.SEL_ADD_BTN)
                    actual_blocked = False
                else:                                                     # 에러 → 차단됨
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
                    actual_blocked = True
            else:
                actual_blocked = False
            # expect_block:false = 차단 없음이 알려진 이슈 → 여전히 없으면 warn(스크린샷), 생기면 pass(개선)
            # expect_block:true  = 차단이 있어야 함        → 있으면 pass, 없으면 fail(스크린샷)
            if not _sc_expect:
                status_sc = "pass" if actual_blocked else "warn"
            else:
                status_sc = "pass" if actual_blocked else "fail"
            t, s = _r(status_sc, _sc_label,
                      f"입력: {_sc_value!r} 제출 / 결과: {'차단됨' if actual_blocked else '저장됨(차단 없음)'}",
                      sc=2)
            lines.append(t); srs.append(s)
            p.close_modal()
            # 저장된 항목 정리
            if not actual_blocked:
                try:
                    p.delete_item(_sc_value)
                except Exception:
                    pass
            p._restore_page_size()

        # 취소 후 재오픈 → 이름 필드 초기화 확인
        p.open_add_modal()
        p.fill(p.SEL_PROCESS_NAME, "[AUTO]_cancel_field_test")
        p.close_modal()
        p.open_add_modal()
        val_after_cancel = p.get_field_value(p.SEL_PROCESS_NAME)
        t, s = _r("pass" if val_after_cancel == "" else "fail",
                  "취소 후 재오픈 — 이름 필드 초기화 확인",
                  f"입력: 이름 입력 후 취소 / 결과: 재오픈 시 이름={val_after_cancel!r}", sc=2)
        lines.append(t); srs.append(s)
        p.close_modal()

        for r in lines:
            print(r)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 2")

    # ── 시나리오 3: 동작 검증 ─────────────────────────────────────────────────
    def test_scenario3_crud(self):
        """시나리오 3: 동작 검증 — 미선택 에러 / CRUD 전체 흐름 / 전 필드 저장값 확인"""
        print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 3: 동작 검증 ━━━━━━━━━━━━━━━━━━━━━━━")
        p = self.p
        page = p.page
        lines, srs = [], []

        # 비정상 케이스: 미선택 수정
        page.locator("button#modifyItemBtn").first.evaluate("el => el.click()")
        p.page.wait_for_timeout(400)
        if p.is_confirm_modal_visible():
            msg = p.get_modal_message()
            expected_nosel = "선택된 항목이 없습니다."
            t, s = _r("pass" if msg == expected_nosel else "warn",
                      "수정 버튼 — 미선택 시 경고",
                      f"입력: 미선택 상태로 수정 버튼 클릭 / 결과: {msg!r}", sc=3)
            lines.append(t); srs.append(s)
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        else:
            t, s = _r("warn", "수정 버튼 — 미선택 시 경고", "에러 모달 없음", sc=3)
            lines.append(t); srs.append(s)

        # 비정상 케이스: 미체크 삭제
        page.locator("button#removeItemBtn").first.evaluate("el => el.click()")
        p.page.wait_for_timeout(400)
        if p.is_confirm_modal_visible():
            msg = p.get_modal_message()
            expected_nocheck = "삭제할 항목을 체크해 주세요."
            t, s = _r("pass" if msg == expected_nocheck else "warn",
                      "삭제 버튼 — 미체크 시 경고",
                      f"입력: 미체크 상태로 삭제 버튼 클릭 / 결과: {msg!r}", sc=3)
            lines.append(t); srs.append(s)
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        else:
            t, s = _r("warn", "삭제 버튼 — 미체크 시 경고", "에러 모달 없음", sc=3)
            lines.append(t); srs.append(s)

        # 사전 정리
        p.delete_all_auto_items()
        p._restore_page_size()

        # ① 추가 — 전체 필드 채워서 생성 (서명/SHA2/실행경로/설명 포함)
        _SIGN_VAL = "auto_sign_test"
        _DESC_VAL = "auto_desc_test"
        try:
            p.add_item(_AUTO_PROCESS, sha2=_SHA2_VALID, sign=_SIGN_VAL,
                       exec_path=_EXEC_TEST, description=_DESC_VAL)
            p.ensure_auto_filter()
            exists = _AUTO_PROCESS in p.get_item_names()
            t, s = _r("pass" if exists else "fail",
                      "항목 추가 — 목록 확인",
                      f"입력: {_AUTO_PROCESS!r} + 전체 필드(서명/SHA2/실행경로/설명) / 결과: {'목록에 존재' if exists else '없음'}", sc=3)
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("fail", "항목 추가 — 목록 확인", str(e), sc=3)
            lines.append(t); srs.append(s)
            for r in lines: print(r)
            self._attach(srs)
            pytest.fail("추가 실패로 이후 시나리오 중단")

        # ① 테이블 컬럼 표시 확인 (이름/서명/설명이 행에 올바르게 표시되는지)
        try:
            p.ensure_auto_filter()
            tbl_row = None
            for row in page.locator(p.SEL_TABLE_ROW).all():
                tds = row.locator("td").all()
                if tds and _AUTO_PROCESS in tds[0].inner_text():
                    tbl_row = row
                    break
            if tbl_row:
                col_texts = [td.inner_text().strip() for td in tbl_row.locator("td").all()]
                for col_label, col_expected in [
                    ("이름",   _AUTO_PROCESS),
                    ("서명",   _SIGN_VAL),
                    ("설명",   _DESC_VAL),
                ]:
                    found = col_expected in col_texts
                    t, s = _r("pass" if found else "warn",
                              f"테이블 — {col_label} 컬럼 표시",
                              f"입력: {col_expected!r} / 결과: {'표시됨' if found else '없음'} (전체={col_texts})", sc=3)
                    lines.append(t); srs.append(s)
            else:
                t, s = _r("warn", "테이블 — 컬럼 값 확인",
                          "입력: 행 탐색 / 결과: 행 찾기 실패", sc=3)
                lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("warn", "테이블 — 컬럼 값 확인", str(e), sc=3)
            lines.append(t); srs.append(s)

        # ① 검색 기능 테스트 — 옵션별 검색 동작 확인
        try:
            # 프로세스 이름 옵션으로 검색
            p.search_item_with_option(_AUTO_PROCESS, "프로세스 이름")
            names_by_name = p.get_item_names()
            t, s = _r("pass" if _AUTO_PROCESS in names_by_name else "fail",
                      "검색(프로세스 이름) — 결과 확인",
                      f"입력: {_AUTO_PROCESS!r} / 결과: {'목록에 존재' if _AUTO_PROCESS in names_by_name else '없음'}", sc=3)
            lines.append(t); srs.append(s)

            # 서명 옵션으로 검색
            p.search_item_with_option(_SIGN_VAL, "서명")
            names_by_sign = p.get_item_names()
            t, s = _r("pass" if _AUTO_PROCESS in names_by_sign else "warn",
                      "검색(서명) — 결과 확인",
                      f"입력: {_SIGN_VAL!r} / 결과: {'목록에 존재' if _AUTO_PROCESS in names_by_sign else '없음'}", sc=3)
            lines.append(t); srs.append(s)

            # 설명 옵션으로 검색
            p.search_item_with_option(_DESC_VAL, "설명")
            names_by_desc = p.get_item_names()
            t, s = _r("pass" if _AUTO_PROCESS in names_by_desc else "warn",
                      "검색(설명) — 결과 확인",
                      f"입력: {_DESC_VAL!r} / 결과: {'목록에 존재' if _AUTO_PROCESS in names_by_desc else '없음'}", sc=3)
            lines.append(t); srs.append(s)

            # 없는 항목 검색 → 빈 목록
            p.search_item_with_option("ZZZQANOTEXISTZZZTEST", "프로세스 이름")
            empty_names = p.get_item_names()
            _empty_detail = (
                f"입력: 'ZZZQANOTEXISTZZZTEST' 검색 / 결과: {len(empty_names)}개 표시됨"
                + (f" — {empty_names}" if empty_names else "")
            )
            t, s = _r("pass" if not empty_names else "warn",
                      "검색 — 없는 항목 검색 시 빈 목록",
                      _empty_detail, sc=3,
                      page=p.page if empty_names else None)
            lines.append(t); srs.append(s)
            p._restore_page_size()
        except Exception as e:
            t, s = _r("warn", "검색 기능 테스트", str(e), sc=3)
            lines.append(t); srs.append(s)

        # ② 추가 후 전 필드 저장값 확인 (수정 모달) — 실행경로 포함
        try:
            p.open_modify_modal(_AUTO_PROCESS)
            for sel, label, expected in [
                (p.SEL_PROCESS_NAME, "프로세스 이름(*) — 저장값 확인", _AUTO_PROCESS),
                (p.SEL_SIGN,         "서명 — 저장값 확인",             _SIGN_VAL),
                (p.SEL_EXEC_PATH,    "실행경로 — 저장값 확인",          _EXEC_TEST),
                (p.SEL_DESCRIPTION,  "설명 — 저장값 확인",             _DESC_VAL),
            ]:
                loaded = p.get_field_value(sel)
                ok_ld = loaded == expected
                t, s = _r("pass" if ok_ld else "fail", label,
                          f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=3,
                          page=(None if ok_ld else p.page),
                          highlight=(None if ok_ld else p.page.locator(sel)))
                lines.append(t); srs.append(s)
            # SHA2: 값 존재 여부 + 앞 20자 표시
            loaded_sha2 = p.get_field_value(p.SEL_SHA2)
            t, s = _r("pass" if loaded_sha2.strip() else "fail",
                      "SHA2 — 저장값 확인",
                      f"입력: {_SHA2_VALID[:20]}... 저장 / 결과: {loaded_sha2[:20]!r}{'...' if len(loaded_sha2) > 20 else ''}", sc=3)
            lines.append(t); srs.append(s)
            p.close_modal()
        except Exception as e:
            t, s = _r("fail", "추가 후 전 필드 저장값 확인", str(e), sc=3)
            lines.append(t); srs.append(s)

        # ③ 수정 (설명 변경) → 목록 잔존 + 수정값 재확인
        _DESC_MOD = "auto_desc_modified"
        try:
            p.open_modify_modal(_AUTO_PROCESS)
            p.page.locator(p.SEL_DESCRIPTION).first.fill(_DESC_MOD)
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)
            p.ensure_auto_filter()
            names = p.get_item_names()
            t, s = _r("pass" if _AUTO_PROCESS in names else "fail",
                      "항목 수정 — 수정 후 목록 잔존",
                      f"입력: 설명 수정 후 저장 / 결과: {'목록에 존재' if _AUTO_PROCESS in names else '없음'}", sc=3)
            lines.append(t); srs.append(s)
            # 수정된 설명 재확인
            p.open_modify_modal(_AUTO_PROCESS)
            loaded_desc = p.get_field_value(p.SEL_DESCRIPTION)
            t, s = _r("pass" if loaded_desc == _DESC_MOD else "fail",
                      "설명 — 수정 후 재확인",
                      f"입력: {_DESC_MOD!r} 수정 / 결과: {loaded_desc!r}", sc=3)
            lines.append(t); srs.append(s)
            p.close_modal()
        except Exception as e:
            t, s = _r("fail", "항목 수정 — 수정 후 목록 잔존", str(e), sc=3)
            lines.append(t); srs.append(s)

        # ④ 삭제 → 목록에서 사라짐 확인
        try:
            p.delete_item(_AUTO_PROCESS)
            p.ensure_auto_filter()
            gone = _AUTO_PROCESS not in p.get_item_names()
            t, s = _r("pass" if gone else "fail",
                      "항목 삭제 — 목록에서 사라짐",
                      f"입력: {_AUTO_PROCESS!r} 삭제 / 결과: {'목록에서 사라짐' if gone else '아직 존재'}", sc=3)
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("fail", "항목 삭제 — 목록에서 사라짐", str(e), sc=3)
            lines.append(t); srs.append(s)

        for r in lines: print(r)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 3")

    # ── 시나리오 4: 수정 시나리오 ─────────────────────────────────────────────
    def test_scenario4_modify(self):
        """시나리오 4: 수정 시나리오 — 4-1 저장값 로드 확인 / 4-2 수정 후 재확인"""
        print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 4: 수정 시나리오 ━━━━━━━━━━━━━━━━━━━━")
        p = self.p
        lines, srs = [], []

        p.delete_all_auto_items()
        p._restore_page_size()

        # 전체 필드 채워서 저장 — 로드 검증에 기댓값이 있어야 의미 있음
        _SIGN_VAL4 = "auto_sign_sc4"
        _DESC_VAL4 = "auto_desc_sc4"
        try:
            p.add_item(_AUTO_PROCESS, sha2=_SHA2_VALID, sign=_SIGN_VAL4,
                       exec_path=_EXEC_TEST, description=_DESC_VAL4)
        except Exception as e:
            t, s = _r("fail", "사전 항목 추가", str(e), sc=4)
            lines.append(t); srs.append(s)
            for r in lines: print(r)
            self._attach(srs)
            pytest.fail("사전 추가 실패")

        # 4-1. 수정 모달 열기 → 전 필드 로드 확인 (저장값과 == 비교)
        try:
            p.open_modify_modal(_AUTO_PROCESS)

            title = p.get_modal_title()
            t, s = _r("pass" if "수정" in title else "warn", "수정 모달 — 제목",
                      f"입력: 수정 모달 오픈 / 결과: 제목={title!r}", sc=4)
            lines.append(t); srs.append(s)

            # 일반 필드: 저장값과 일치하는지 비교
            for sel, label, expected in [
                (p.SEL_PROCESS_NAME, "프로세스 이름(*)", _AUTO_PROCESS),
                (p.SEL_SIGN,         "서명",             _SIGN_VAL4),
                (p.SEL_EXEC_PATH,    "실행경로",          _EXEC_TEST),
                (p.SEL_DESCRIPTION,  "설명",             _DESC_VAL4),
            ]:
                loaded = p.get_field_value(sel)
                ok_ld = loaded == expected
                t, s = _r("pass" if ok_ld else "fail",
                          f"{label} — 수정 모달 로드",
                          f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=4,
                          page=(None if ok_ld else p.page),
                          highlight=(None if ok_ld else p.page.locator(sel)))
                lines.append(t); srs.append(s)

            # SHA2: 값 존재 여부 + 앞 20자 (전체 비교 대신 존재 확인)
            loaded_sha2 = p.get_field_value(p.SEL_SHA2)
            sha2_short = (loaded_sha2[:20] + "...") if len(loaded_sha2) > 20 else (loaded_sha2 or "(비어있음)")
            t, s = _r("pass" if loaded_sha2.strip() else "fail",
                      "SHA2 — 수정 모달 로드",
                      f"입력: {_SHA2_VALID[:20]}... 저장 / 결과: {sha2_short!r}", sc=4)
            lines.append(t); srs.append(s)

            # 4-2. 수정 후 재확인 — 3점 대조(입력 ↔ 리스트 행 표시 ↔ 재오픈 로드)
            #      행 표시 계층 추가(2026-07-02): 제어스위트 클립보드·네트워크 '행 표시 stale' 버그 클래스 검출용.
            _DESC_MOD4 = "sc4_modified_desc"
            p.page.locator(p.SEL_DESCRIPTION).first.fill(_DESC_MOD4)
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)

            # ② 리스트 행 '설명' 컬럼 표시
            p.ensure_auto_filter()
            row_cells, row_loc = [], None
            for _row in p.page.locator(p.SEL_TABLE_ROW).all():
                _tds = _row.locator("td").all()
                if _tds and _AUTO_PROCESS in _tds[0].inner_text():
                    row_loc = _row
                    row_cells = [td.inner_text().strip() for td in _tds]
                    break
            row_shows = _DESC_MOD4 in row_cells
            # ③ 재오픈 로드
            p.open_modify_modal(_AUTO_PROCESS)
            loaded_new = p.get_field_value(p.SEL_DESCRIPTION)
            if loaded_new != _DESC_MOD4:
                # 저장 계층 fail — 모달 열린 채 설명 필드 하이라이트(캡처 지점=판정 지점)
                t, s = _r("fail", "설명 — 수정 후 행 표시+재오픈 재확인(3점)",
                          f"입력: {_DESC_MOD4!r} 수정 / 행 표시={row_shows}, 재오픈={loaded_new!r} "
                          "— 재오픈에 미반영(수정 저장 실패)",
                          sc=4, page=p.page, highlight=p.page.locator(p.SEL_DESCRIPTION))
                lines.append(t); srs.append(s)
                p.close_modal()
            else:
                p.close_modal()
                if row_shows:
                    t, s = _r("pass", "설명 — 수정 후 행 표시+재오픈 재확인(3점)",
                              f"입력: {_DESC_MOD4!r} 수정 / 행 표시·재오픈 모두 반영", sc=4)
                else:
                    # 두 화면 대비 2장(사용자 지시 2026-07-03): ①재오픈 모달=새 값(데이터 정상) ②행=옛값(stale)
                    p.open_modify_modal(_AUTO_PROCESS)
                    shot1 = _ss(p.page, "설명수정_모달에는_반영됨",
                                highlight=p.page.locator(p.SEL_DESCRIPTION))
                    p.close_modal()
                    t, s = _r("warn", "설명 — 수정 후 행 표시+재오픈 재확인(3점)",
                              f"입력: {_DESC_MOD4!r} 수정 / 재오픈 일치(스크린샷① 모달=새 값) "
                              "— 리스트 행 '설명' 컬럼만 옛값(스크린샷② 행 표시 stale)",
                              sc=4, page=p.page, highlight=row_loc)
                    if shot1:
                        s.extra["screenshots"] = [shot1]
                lines.append(t); srs.append(s)

        except Exception as e:
            t, s = _r("fail", "수정 모달 — 필드 로드/재확인", str(e), sc=4)
            lines.append(t); srs.append(s)

        # 4-3. 선택 필드 지우기 → 저장 → 재오픈 → 빈값 유지 확인
        #      (가끔 저장 후 이전 값이 복원되는 버그 감지용)
        try:
            p.open_modify_modal(_AUTO_PROCESS)
            p.page.locator(p.SEL_EXEC_PATH).first.fill("")
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)

            p.open_modify_modal(_AUTO_PROCESS)
            cleared_exec = p.get_field_value(p.SEL_EXEC_PATH)
            t, s = _r("pass" if cleared_exec == "" else "fail",
                      "실행경로 — 지우기 후 재오픈 빈값 유지 확인",
                      f"입력: 실행경로 삭제 후 저장 / 결과: {cleared_exec!r}",
                      sc=4, page=(None if cleared_exec == "" else p.page),
                      highlight=(None if cleared_exec == "" else p.page.locator(p.SEL_EXEC_PATH)))
            lines.append(t); srs.append(s)
            p.close_modal()
        except Exception as e:
            t, s = _r("warn", "실행경로 — 지우기 후 빈값 유지 확인", str(e), sc=4)
            lines.append(t); srs.append(s)

        try:
            p.delete_item(_AUTO_PROCESS)
        except Exception:
            pass

        for r in lines: print(r)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 4")

    # ── 시나리오 5: 케이스 검증 ───────────────────────────────────────────────
    def test_scenario5_full_and_required(self):
        """시나리오 5: 케이스 검증 — 케이스A(전체 필드) / 케이스B(필수만) — 전 필드 재확인"""
        print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 5: 케이스 검증 ━━━━━━━━━━━━━━━━━━━━━━")
        p = self.p
        page = p.page
        lines, srs = [], []

        # 사전 정리 — '[AUTO' 필터 1회로 두 이름 확인(개별 재검색 제거)
        try:
            p.ensure_auto_filter()
            names_now = p.get_item_names()
            for name in [_AUTO_PROC_FULL, _AUTO_PROC_REQ]:
                if name in names_now:
                    p.delete_item(name)
        except Exception:
            pass
        p._restore_page_size()

        # ── 케이스 A: 전체 필드 채우기 ─────────────────────────────────────
        print("\n  --- 케이스A: 전체 필드 채우기 ---")
        _SIGN_FULL = "auto_sign_full"
        _EXEC_FULL = r"C:\auto\proc_full.exe"
        _DESC_FULL = "full_case_auto_desc"
        try:
            p.add_item(_AUTO_PROC_FULL, sha2=_SHA2_VALID, sign=_SIGN_FULL,
                       exec_path=_EXEC_FULL, description=_DESC_FULL)
            p.ensure_auto_filter()
            exists = _AUTO_PROC_FULL in p.get_item_names()
            t, s = _r("pass" if exists else "fail",
                      "케이스A — 전체 채우기 저장 확인",
                      f"입력: 전체 필드(이름+서명+SHA2+실행경로+설명) 저장 / 결과: {'목록에 존재' if exists else '없음'}", sc=5)
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("fail", "케이스A — 전체 채우기 저장", str(e), sc=5)
            lines.append(t); srs.append(s)

        # 케이스A 전 필드 재확인
        try:
            p.open_modify_modal(_AUTO_PROC_FULL)
            for sel, label, expected in [
                (p.SEL_PROCESS_NAME, "케이스A — 프로세스 이름 로드", _AUTO_PROC_FULL),
                (p.SEL_SIGN,         "케이스A — 서명 로드",         _SIGN_FULL),
                (p.SEL_EXEC_PATH,    "케이스A — 실행경로 로드",      _EXEC_FULL),
                (p.SEL_DESCRIPTION,  "케이스A — 설명 로드",         _DESC_FULL),
            ]:
                loaded = p.get_field_value(sel)
                ok_ld = loaded == expected
                t, s = _r("pass" if ok_ld else "warn", label,
                          f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=5,
                          page=(None if ok_ld else p.page),
                          highlight=(None if ok_ld else p.page.locator(sel)))
                lines.append(t); srs.append(s)
            # SHA2: 값 존재 여부 + 앞 20자 표시
            loaded_sha2 = p.get_field_value(p.SEL_SHA2)
            sha2_short = (loaded_sha2[:20] + "...") if len(loaded_sha2) > 20 else (loaded_sha2 or "(비어있음)")
            t, s = _r("pass" if loaded_sha2.strip() else "warn",
                      "케이스A — SHA2 로드",
                      f"입력: {_SHA2_VALID[:20]}... / 결과: {sha2_short!r}", sc=5)
            lines.append(t); srs.append(s)
            p.close_modal()
        except Exception as e:
            t, s = _r("fail", "케이스A — 저장값 재확인", str(e), sc=5)
            lines.append(t); srs.append(s)

        # ── 케이스 B: 필수 필드만 ──────────────────────────────────────────
        print("\n  --- 케이스B: 필수 필드만 채우기 ---")
        try:
            p.add_item(_AUTO_PROC_REQ)   # 이름만, 선택 필드 모두 비움
            p.ensure_auto_filter()
            exists_b = _AUTO_PROC_REQ in p.get_item_names()
            t, s = _r("pass" if exists_b else "fail",
                      "케이스B — 필수만 저장 확인",
                      f"입력: {_AUTO_PROC_REQ!r} 이름만 저장 / 결과: {'목록에 존재' if exists_b else '없음'}", sc=5)
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("fail", "케이스B — 필수만 저장", str(e), sc=5)
            lines.append(t); srs.append(s)

        # 케이스B: 필수 필드 로드 + 선택 필드 전부 빈값 확인 (실행경로 포함)
        try:
            p.open_modify_modal(_AUTO_PROC_REQ)
            loaded_name = p.get_field_value(p.SEL_PROCESS_NAME)
            t, s = _r("pass" if loaded_name == _AUTO_PROC_REQ else "fail",
                      "케이스B — 프로세스 이름 로드",
                      f"입력: {_AUTO_PROC_REQ!r} 저장 / 결과: {loaded_name!r}", sc=5)
            lines.append(t); srs.append(s)
            for sel, label in [
                (p.SEL_SIGN,        "케이스B — 서명(선택 필드) 빈 값 유지"),
                (p.SEL_SHA2,        "케이스B — SHA2(선택 필드) 빈 값 유지"),
                (p.SEL_EXEC_PATH,   "케이스B — 실행경로(선택 필드) 빈 값 유지"),
                (p.SEL_DESCRIPTION, "케이스B — 설명(선택 필드) 빈 값 유지"),
            ]:
                loaded = p.get_field_value(sel)
                ok_empty = loaded.strip() == ""
                t, s = _r("pass" if ok_empty else "warn", label,
                          f"입력: 선택 필드 미입력 / 결과: {loaded!r}", sc=5,
                          page=(None if ok_empty else p.page),
                          highlight=(None if ok_empty else p.page.locator(sel)))
                lines.append(t); srs.append(s)
            p.close_modal()
        except Exception as e:
            t, s = _r("fail", "케이스B — 저장값 재확인", str(e), sc=5)
            lines.append(t); srs.append(s)

        # 정리
        for name in [_AUTO_PROC_FULL, _AUTO_PROC_REQ]:
            try:
                p.delete_item(name)
            except Exception:
                pass

        # sc5 마무리 — AUTO 일괄 삭제 (AUTO_KEEP 보존)
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        for r in lines: print(r)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 5")

    # ── 시나리오 6: 연계 데이터 준비 ─────────────────────────────────────────────
    def test_scenario6_suite_setup(self):
        """시나리오 6: 연계 데이터 준비 — [AUTO_KEEP]_sc6_cm_proc_suite 생성 후 태그 테스트에 남겨둠

        연계 테스트(다른 test_npouch_*.py 파일에서 _SUITE 참조)가 없으면
        정리만 하고 skip 처리한다.
        """
        print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 6: 연계 데이터 준비 ━━━━━━━━━━━━━━━━━━")
        p = self.p
        lines, srs = [], []

        # AUTO_KEEP_ prefix — sc1 cleanup 시 보존, 세션 간 잔존
        # ※ 날짜본([AUTO_<MMDD>]) 미적용 레거시 — 마이그레이션 별도 결정(2026-06-30, 미정). 그대로 유지.
        _SUITE = "[AUTO_KEEP]_sc6_cm_proc_suite"

        # AUTO_KEEP 잔존 — 정리 안 함 (세션 간 보존이 의도).
        # '[AUTO' 필터로 잔존 확인('[AUTO_KEEP]' 도 prefix 매칭 — 개별 재검색 제거).
        p.ensure_auto_filter()
        _already_exists = _SUITE in p.get_item_names()
        p._restore_page_size()

        # 연계 검증은 같은 세션 안 태그 sc6 cross-page 에서 수행 — 항상 진행
        # (이전 _consumer_files 자동 감지 skip 제거 — sc6 self-contained 검증 활성화)

        # 연계 항목 — 잔존 시 그대로 활용, 없으면 생성 (fail 시 자동 screenshot)
        try:
            if _already_exists:
                t, s = _r("pass", "연계 프로세스 잔존 — 재사용",
                          f"입력: {_SUITE!r} 이미 존재 / 결과: AUTO_KEEP 잔존 활용", sc=6)
            else:
                p.add_item(_SUITE)
                p.ensure_auto_filter()
                exists = _SUITE in p.get_item_names()
                t, s = _r("pass" if exists else "fail",
                          "연계 프로세스 생성 — 목록 확인",
                          f"입력: {_SUITE!r} 생성 / 결과: {'목록에 존재' if exists else '없음'}",
                          sc=6, page=(None if exists else p.page))
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = _r("fail", "연계 프로세스 생성", str(e), sc=6, page=p.page)
            lines.append(t); srs.append(s)

        # 삭제하지 않고 종료 — 태그 관리 시나리오 6에서 사용
        t, s = _r("skip", "연계 데이터 남겨두기",
                  f"{_SUITE!r} — 태그 관리(시나리오 6)에서 태그에 등록 예정", sc=6)
        lines.append(t); srs.append(s)

        for r in lines: print(r)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 6")
