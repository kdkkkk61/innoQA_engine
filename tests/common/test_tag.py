"""
tests/test_npouch_tag.py — nPouch 태그 관리 QA 테스트

파이프라인: ScanResult/PageScanReport → conftest 수집 → html_reporter HTML 생성

실행:
  pytest tests/test_npouch_tag.py -v -s
  pytest tests/test_npouch_tag.py::TestNpouchTag::test_scenario1_ui -v -s
"""
import re
import time
import yaml
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport
from pages.npouch_tag_page import NpouchTagPage
from pages.npouch_operation_process_page import NpouchOperationProcessPage

# ── scan_hints YAML 로드 ──────────────────────────────────────────
def _load_hints(page_id: str) -> dict:
    path = Path(__file__).parent.parent / "config" / "scan_hints" / f"{page_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}

# ── 스크린샷 ─────────────────────────────────────────────────────
_SS_DIR = Path(__file__).parent.parent / "reports" / "screenshots"

def _ss(page, label: str, highlight=None) -> str | None:
    """highlight (Locator) 있으면 빨간 outline 임시 주입 + 스크롤 후 캡처 → 복원.
    None 이면 기존 viewport 캡처. origin_protect _ss 와 동일 헬퍼."""
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

# ── 모듈 상수 ─────────────────────────────────────────────────────
_STATUS_ICON  = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]", "warn": "[WARN]"}
_STATUS_TO_SR = {"pass": "pass", "fail": "fail", "warn": "warn", "skip": "skip"}

_SAVE_SUCCESS_KEYWORDS = ("하시겠습니까", "저장 하였습니다", "저장하였습니다",
                           "추가되었습니다", "수정되었습니다", "하였습니다")


def _r(status: str, label: str, detail: str = "", sc: int = 0,
       page=None, highlight=None) -> tuple[str, ScanResult]:
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
    failed = [ln for ln in lines if "[FAIL]" in ln]
    if failed:
        raise AssertionError(f"{context} 실패 항목:\n" + "\n".join(failed))


# ══════════════════════════════════════════════════════════════════
@pytest.mark.npouch
class TestNpouchTag:
    PAGE_NAME = "태그 관리"
    PAGE_ID   = "common_tag"

    @pytest.fixture(autouse=True)
    def setup(self, request, logged_in_page, settings):
        self._request = request
        self.p = NpouchTagPage(logged_in_page, settings)
        self._hints = _load_hints(self.PAGE_ID)
        self.p.navigate_to()

    def _attach(self, scan_results: list[ScanResult]) -> None:
        report = PageScanReport(page_id=self.PAGE_ID)
        report.results = scan_results
        self._request.node._scan_report = report
        self._request.node._npouch_page_id = self.PAGE_ID

    def _make_r(self, sc: int):
        """이슈 감지 즉시 현재 화면을 자동 캡처하는 _r() 래퍼 생성.
        반드시 정리(모달 닫기 등) 전에 호출할 것.

        capture 규칙:
          fail  → 항상 캡처 (기본값)
          warn  → 기본 캡처 안함 (DOM 속성 등 비시각적 체크 고려)
                  capture=True 명시 시 캡처 (모달 화면 등 시각적으로 의미있는 경우)
          pass/skip → 캡처 없음
        """
        _page = self.p.page
        def r(status: str, label: str, detail: str = "",
              capture: bool = None, highlight=None) -> tuple[str, ScanResult]:
            if capture is True:
                page_to_use = _page
            elif capture is False:
                page_to_use = None
            else:  # None → fail만 자동 캡처
                page_to_use = _page if status == "fail" else None
            return _r(status, label, detail, sc=sc, page=page_to_use, highlight=highlight)
        return r

    # ── 시나리오 1: UI 구조 ────────────────────────────────────────
    def test_scenario1_ui(self):
        r = self._make_r(1)
        lines, srs = [], []
        p = self.p
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 1: UI 구조 ━━━━━━━━━━━━━━━━━━━━━━━")

        # sc1 시작 — clean slate ([AUTO] + [AUTO_KEEP] 일괄 삭제)
        try:
            p.cleanup_with_keep()
        except Exception:
            pass

        # 탭 전환 — 단일 뷰
        t, s = r("skip", "탭 전환", "단일 뷰 페이지 — 탭 없음")
        lines.append(t); srs.append(s)

        # 버튼 목록
        for btn_label, btn_sel in [
            ("추가 버튼",  p.SEL_ADD_BTN),
            ("수정 버튼",  p.SEL_MODIFY_BTN),
            ("삭제 버튼",  p.SEL_DELETE_BTN),
            ("Import 버튼", "button#importFileBtn"),
            ("Export 버튼", "button#exportFileBtn"),
        ]:
            exists = p.page.locator(btn_sel).count() > 0
            t, s = r("pass" if exists else "fail",
                     f"{btn_label} — 존재",
                     f"입력: (없음) / 결과: {'존재' if exists else '없음'}")
            lines.append(t); srs.append(s)

        # Excel 버튼 없어야 정상
        excel_exists = p.page.locator("button#excelDownBtn").count() > 0
        t, s = r("pass" if not excel_exists else "warn",
                 "EXCEL 다운로드 버튼 — 미존재 확인",
                 f"입력: (없음) / 결과: {'없음(Import/Export 방식)' if not excel_exists else '존재(예상 밖)'}")
        lines.append(t); srs.append(s)

        # 테이블 헤더
        header_text = " ".join(
            th.inner_text().strip()
            for th in p.page.locator("table thead th").all()
        )
        print(f"  실제 헤더: {header_text!r}")
        for col in ["태그 이름", "프로세스 카운트", "설명"]:
            exists = col in header_text
            t, s = r("pass" if exists else "fail",
                     f"테이블 헤더 — {col}",
                     f"입력: (없음) / 결과: {'존재' if exists else '없음'}")
            lines.append(t); srs.append(s)

        # 검색창
        t, s = r("pass" if p.page.locator("input#searchText").count() > 0 else "fail",
                 "검색창 — 존재", "입력: (없음) / 결과: 존재")
        lines.append(t); srs.append(s)

        # 검색 옵션 셀렉트 — 없음 (단일 검색)
        t, s = r("skip", "검색 옵션 셀렉트", "태그 이름 단일 검색 — 셀렉트 없음")
        lines.append(t); srs.append(s)

        # 검색 버튼
        t, s = r("pass" if p.page.locator("button#searchBtn").count() > 0 else "fail",
                 "검색 버튼 — 존재", "입력: (없음) / 결과: 존재")
        lines.append(t); srs.append(s)

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 1")

    # ── 시나리오 2: 입력 구조 ──────────────────────────────────────
    def test_scenario2_modal_fields(self):
        r = self._make_r(2)
        lines, srs = [], []
        p = self.p
        _hints = self._hints
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 2: 입력 구조 ━━━━━━━━━━━━━━━━━━━━━━━")

        # ── 모달 열기 ─────────────────────────────────────────────
        p.open_add_modal()

        # 모달 제목
        title = p.get_modal_title()
        t, s = r("pass" if title == "태그 추가" else "fail",
                 "모달 제목",
                 f"입력: 모달 오픈 / 결과: 제목={title!r}")
        lines.append(t); srs.append(s)

        # 버튼 텍스트
        submit_text = p.page.locator(p.SEL_SUBMIT_BTN).first.inner_text().strip()
        cancel_text = p.page.locator(p.SEL_CANCEL_BTN).first.inner_text().strip()
        for label, val, expected in [
            ("추가(제출) 버튼 텍스트", submit_text, "추가"),
            ("취소 버튼 텍스트",       cancel_text, "취소"),
        ]:
            t, s = r("pass" if val == expected else "fail", label,
                     f"입력: 버튼 텍스트 확인 / 결과: {val!r}")
            lines.append(t); srs.append(s)

        # ── 필드 존재 / 초기값 / DOM maxlength ─────────────────────
        for field_def in _hints.get("fields", []):
            sel   = field_def["selector"]
            label = field_def["label"]
            req   = field_def.get("required", False)
            mark  = "(*)" if req else ""

            exists = p.page.locator(sel).count() > 0
            t, s = r("pass" if exists else "fail",
                     f"{label}{mark} — 필드 존재",
                     f"입력: (없음) / 결과: {'존재' if exists else '없음'}")
            lines.append(t); srs.append(s)

            if exists:
                init_val = p.get_field_value(sel)
                t, s = r("pass", f"{label}{mark} — 초기값",
                         f"입력: 초기 상태 / 결과: {init_val!r}")
                lines.append(t); srs.append(s)

                # DOM maxlength는 아래 글자수 제한 통합 테스트에서 처리

        # ── 빈 값 제출 — tagName 필수 검증 ──────────────────────────
        p.try_submit()
        p.page.wait_for_timeout(500)
        if p.is_confirm_modal_visible():
            err_msg = p.get_modal_message()
            expected_err = "태그 이름을 입력해 주세요."
            t, s = r("pass" if expected_err in err_msg else "fail",
                     "태그 이름(*) — 빈 값 제출 경고",
                     f"입력: 이름 비운 채 제출 / 결과: {err_msg!r}")
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        else:
            t, s = r("fail", "태그 이름(*) — 빈 값 제출 경고",
                     "입력: 이름 비운 채 제출 / 결과: 모달 없음")
        lines.append(t); srs.append(s)

        # ── 태그 이름 — 글자수 제한 (DOM maxlength + 오버플로 통합) ─────
        # 빈 값 제출 후 추가 모달이 열려 있는 상태에서 바로 이어서 진행
        _ov_name_saved = False
        try:
            ml_name = p.page.locator(p.SEL_TAG_NAME).first.get_attribute("maxlength")
            _ov_tlen = (int(ml_name) + 1) if (ml_name and str(ml_name).isdigit()) else 200
            _ov_pfx  = "[AUTO]_ov_"
            _ov_tval = _ov_pfx + "X" * max(0, _ov_tlen - len(_ov_pfx))
            p.page.locator(p.SEL_TAG_NAME).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                _ov_tval
            )
            p.page.wait_for_timeout(200)
            p.try_submit()
            p.page.wait_for_timeout(600)
            if p.is_confirm_modal_visible():
                ov_tmsg = p.get_modal_message()
                if any(kw in ov_tmsg for kw in _SAVE_SUCCESS_KEYWORDS):
                    t, s = r("warn", "태그 이름 — 글자수 제한",
                             f"DOM maxlength={ml_name!r} / 실제: {_ov_tlen}자 저장됨 — 서버 제한 없음 (known issue)",
                             capture=True)
                    p.click_attached(p.SEL_CONFIRM_BTN)
                    p.wait_for_confirm_modal_closed()
                    p.wait_for(p.SEL_ADD_BTN)
                    _ov_name_saved = True
                else:
                    t, s = r("pass", "태그 이름 — 글자수 제한",
                             f"DOM maxlength={ml_name!r} / 실제: {_ov_tlen}자 서버 오류",
                             capture=True)
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
            else:
                t, s = r("warn", "태그 이름 — 글자수 제한",
                         f"DOM maxlength={ml_name!r} / 실제: {_ov_tlen}자 — 응답 모달 없음")
        except Exception as e:
            t, s = r("warn", "태그 이름 — 글자수 제한", str(e))
        finally:
            for _ in range(3):
                if p.page.locator(p.SEL_MODAL_OPEN).count() == 0:
                    break
                try:
                    p.page.locator(p.SEL_CANCEL_BTN).first.evaluate("el => el.click()")
                    p.page.wait_for_timeout(300)
                except Exception:
                    break
        lines.append(t); srs.append(s)

        # 저장된 경우 정리
        if _ov_name_saved:
            try:
                p.search_item(_ov_pfx)
                p.page.wait_for_timeout(400)
                for row in p.page.locator(p.SEL_TABLE_ROW).all():
                    tds = row.locator("td").all()
                    if tds and tds[0].inner_text().strip().startswith(_ov_pfx):
                        cb = row.locator("input[type='checkbox']").first
                        p._toggle_overlay(False)
                        try:
                            cb.click()
                        finally:
                            p._toggle_overlay(True)
                        p.page.locator(p.SEL_DELETE_BTN).first.evaluate("el => el.click()")
                        p.page.wait_for_timeout(400)
                        if p.is_confirm_modal_visible():
                            p.click_attached(p.SEL_CONFIRM_BTN)
                            p.wait_for_confirm_modal_closed()
                        p.wait_for(p.SEL_ADD_BTN)
                        break
            except Exception:
                pass

        # ── 설명 — 글자수 제한 (DOM maxlength + 오버플로 통합) ──────────
        try:
            p.open_add_modal()
            ml_desc = p.page.locator(p.SEL_DESCRIPTION).first.get_attribute("maxlength")
            _ov_dlen = (int(ml_desc) + 1) if (ml_desc and str(ml_desc).isdigit()) else 400
            p.page.locator(p.SEL_TAG_NAME).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                "[AUTO]_desc_ov"
            )
            p.page.locator(p.SEL_DESCRIPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                "D" * _ov_dlen
            )
            p.page.wait_for_timeout(200)
            p.try_submit()
            # 서버 응답 모달 출현까지 대기 (긴 값 서버 처리 지연 대응 — 즉시검사 시 느린 에러 놓침)
            _ov_modal = False
            try:
                p.page.locator(p.SEL_CONFIRM_MODAL).wait_for(
                    state="attached", timeout=6000
                )
                _ov_modal = True
            except Exception:
                _ov_modal = False
            if _ov_modal:
                ov_dmsg = p.get_modal_message()
                # 에러 키워드 먼저 — "오류가 발생 하였습니다" 가 success "하였습니다" 에 오분류 방지
                _ov_is_err = ("오류" in ov_dmsg) or ("실패" in ov_dmsg) or ("에러" in ov_dmsg)
                if (not _ov_is_err) and any(kw in ov_dmsg for kw in _SAVE_SUCCESS_KEYWORDS):
                    t, s = r("warn", "설명 — 글자수 제한",
                             f"DOM maxlength={ml_desc!r} / 실제: {_ov_dlen}자 저장됨 — 서버 제한 없음 (known issue)",
                             capture=True, highlight=p.page.locator(p.SEL_DESCRIPTION))
                    p.click_attached(p.SEL_CONFIRM_BTN)
                    p.wait_for_confirm_modal_closed()
                    p.wait_for(p.SEL_ADD_BTN)
                    try:
                        p.delete_item("[AUTO]_desc_ov")
                    except Exception:
                        pass
                else:
                    t, s = r("warn", "설명 — 글자수 제한",
                             f"DOM maxlength={ml_desc!r} / 실제: {_ov_dlen}자 generic '서버 오류' 응답 (graceful 검증 부재)",
                             capture=True, highlight=p.page.locator(p.SEL_DESCRIPTION))
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
            else:
                t, s = r("warn", "설명 — 글자수 제한",
                         f"DOM maxlength={ml_desc!r} / 실제: {_ov_dlen}자 — 응답 모달 없음")
        except Exception as e:
            t, s = r("warn", "설명 — 글자수 제한", str(e))
        finally:
            for _ in range(3):
                if p.page.locator(p.SEL_MODAL_OPEN).count() == 0:
                    break
                try:
                    p.page.locator(p.SEL_CANCEL_BTN).first.evaluate("el => el.click()")
                    p.page.wait_for_timeout(300)
                except Exception:
                    break
        lines.append(t); srs.append(s)

        # ── 특수문자 차단 여부 ────────────────────────────────────
        for sc_test in _hints.get("special_char_tests", []):
            sc_label   = sc_test["label"]
            sc_val     = sc_test["test_value"]
            sc_expect  = sc_test.get("expect_block", True)
            try:
                p.open_add_modal()
                p.page.locator(p.SEL_TAG_NAME).first.evaluate(
                    "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                    sc_val
                )
                p.try_submit()
                p.page.wait_for_timeout(600)
                if p.is_confirm_modal_visible():
                    sc_msg = p.get_modal_message()
                    saved = any(kw in sc_msg for kw in _SAVE_SUCCESS_KEYWORDS)
                    if saved:
                        p.click_attached(p.SEL_CONFIRM_BTN)
                        p.wait_for_confirm_modal_closed()
                        p.wait_for(p.SEL_ADD_BTN)
                        try:
                            p.delete_item(sc_val)
                        except Exception:
                            pass
                    else:
                        p.dismiss_confirm_modal()
                        p.wait_for_confirm_modal_closed()
                    was_blocked = not saved
                else:
                    was_blocked = False

                if sc_expect:
                    status = "pass" if was_blocked else "fail"
                    detail = "차단됨" if was_blocked else "저장됨(차단 없음)"
                else:
                    status = "pass" if not was_blocked else "warn"
                    detail = "저장됨(차단 없음)" if not was_blocked else "차단됨(예상 밖)"
                t, s = r(status, sc_label, f"입력: {sc_val!r} 제출 / 결과: {detail}")
            except Exception as e:
                t, s = r("warn", sc_label, str(e))
            finally:
                for _ in range(3):
                    if p.page.locator(p.SEL_MODAL_OPEN).count() == 0:
                        break
                    try:
                        p.page.locator(p.SEL_CANCEL_BTN).first.evaluate("el => el.click()")
                        p.page.wait_for_timeout(300)
                    except Exception:
                        break
            lines.append(t); srs.append(s)

        # ── 중복 이름 에러 (i18n 미번역 버그 확인 포함) ───────────
        # navigate_to() early return 시 검색 상태 유지 → search_item("") 으로 명시 초기화
        p.search_item("")
        p.page.wait_for_timeout(400)
        existing_names = p.get_item_names()
        if existing_names:
            dup_name = existing_names[0]
            try:
                p.open_add_modal()
                p.page.locator(p.SEL_TAG_NAME).first.evaluate(
                    "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                    dup_name
                )
                p.try_submit()
                p.page.wait_for_timeout(600)
                if p.is_confirm_modal_visible():
                    dup_msg = p.get_modal_message()
                    is_error = not any(kw in dup_msg for kw in _SAVE_SUCCESS_KEYWORDS)
                    is_raw_key = "COLUMN." in dup_msg or (dup_msg == dup_msg.upper() and len(dup_msg) > 5)
                    if is_error and is_raw_key:
                        t, s = r("warn", "태그 이름(*) — 중복 이름 에러(i18n 미번역)",
                                 f"입력: {dup_name!r} 제출 / 결과: {dup_msg!r} "
                                 f"(i18n 키 미번역 — known issue)",
                                 capture=True)
                    elif is_error:
                        t, s = r("pass", "태그 이름(*) — 중복 이름 에러",
                                 f"입력: {dup_name!r} 제출 / 결과: {dup_msg!r}")
                    else:
                        t, s = r("fail", "태그 이름(*) — 중복 이름 에러",
                                 f"입력: {dup_name!r} 제출 / 결과: 에러 없이 저장됨")
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
                else:
                    t, s = r("fail", "태그 이름(*) — 중복 이름 에러",
                             f"입력: {dup_name!r} 제출 / 결과: 모달 없음")
            except Exception as e:
                t, s = r("warn", "태그 이름(*) — 중복 이름 에러", str(e))
            finally:
                for _ in range(3):
                    if p.page.locator(p.SEL_MODAL_OPEN).count() == 0:
                        break
                    try:
                        p.page.locator(p.SEL_CANCEL_BTN).first.evaluate("el => el.click()")
                        p.page.wait_for_timeout(300)
                    except Exception:
                        break
            lines.append(t); srs.append(s)

        # ── 취소 후 재오픈 — 이름 필드 초기화 ───────────────────────
        try:
            p.open_add_modal()
            p.page.locator(p.SEL_TAG_NAME).first.fill("임시입력값")
            p.close_modal()
            p.page.wait_for_timeout(300)
            p.open_add_modal()
            reopened_val = p.get_field_value(p.SEL_TAG_NAME)
            t, s = r("pass" if reopened_val == "" else "fail",
                     "취소 후 재오픈 — 태그 이름 필드 초기화 확인",
                     f"입력: 이름 입력 후 취소 / 결과: 재오픈 시 이름={reopened_val!r}")
            p.close_modal()
        except Exception as e:
            t, s = r("warn", "취소 후 재오픈 — 태그 이름 필드 초기화 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 추가 모달 UI 구조 확인 (프로세스 테이블 + +/- 버튼) ───
        try:
            p.open_add_modal()

            # + 버튼 존재 (프로세스 추가)
            add_proc_exists = p.page.locator(p.SEL_TAG_ADD_PROC_BTN).count() > 0
            t, s = r("pass" if add_proc_exists else "fail",
                     "추가 모달 — + 버튼(프로세스 추가) 존재",
                     f"입력: (없음) / 결과: {'존재' if add_proc_exists else '없음'}")
            lines.append(t); srs.append(s)

            # - 버튼 존재 (프로세스 제거)
            rem_proc_exists = p.page.locator(p.SEL_TAG_REMOVE_PROC_BTN).count() > 0
            t, s = r("pass" if rem_proc_exists else "fail",
                     "추가 모달 — - 버튼(프로세스 제거) 존재",
                     f"입력: (없음) / 결과: {'존재' if rem_proc_exists else '없음'}")
            lines.append(t); srs.append(s)

            # 프로세스 테이블 헤더 확인
            proc_headers = [
                th.inner_text().strip()
                for th in p.page.locator("div#addItemModal table thead th").all()
            ]
            print(f"  추가 모달 프로세스 테이블 헤더: {proc_headers}")
            # 이름 컬럼 라벨은 빌드차('프로세스명'/'프로세스 이름') → 둘 다 허용
            header_specs = [
                ("프로세스명/이름", {"프로세스명", "프로세스 이름"}),
                ("서명", {"서명"}), ("SHA2", {"SHA2"}), ("설명", {"설명"}),
            ]
            for label, accept in header_specs:
                ok = any(a in proc_headers for a in accept)
                t, s = r("pass" if ok else "fail",
                         f"추가 모달 — 프로세스 테이블 헤더 '{label}'",
                         f"입력: (없음) / 결과: {'존재' if ok else '없음'}")
                lines.append(t); srs.append(s)

            # 프로세스 선택 서브모달 오픈 확인
            p.open_process_list_modal()
            sub_open = p.page.locator(p.SEL_PROC_MODAL_OPEN).count() > 0
            sub_title = ""
            if sub_open:
                sub_title = p.page.locator(
                    f"{p.SEL_PROC_MODAL} .modal-title, {p.SEL_PROC_MODAL} h4"
                ).first.inner_text().strip()
            t, s = r("pass" if sub_open and sub_title == "프로세스 선택" else "fail",
                     "프로세스 선택 서브모달 — 오픈 및 제목 확인",
                     f"입력: + 버튼 클릭 / 결과: 서브모달 제목={sub_title!r}")
            lines.append(t); srs.append(s)

            # 서브모달 검색 필드 존재
            sub_search_exists = p.page.locator(p.SEL_PROC_LIST_SEARCH).count() > 0
            t, s = r("pass" if sub_search_exists else "fail",
                     "프로세스 선택 서브모달 — 프로세스 명 검색 필드 존재",
                     f"입력: (없음) / 결과: {'존재' if sub_search_exists else '없음'}")
            lines.append(t); srs.append(s)

            # 서브모달 닫기 → 추가 모달 취소
            p.page.locator(f"{p.SEL_PROC_MODAL} .close").first.evaluate("el => el.click()")
            p.page.wait_for_timeout(300)
            p.close_modal()

        except Exception as e:
            t, s = r("fail", "추가 모달 UI 구조 확인 (+/- 버튼)", str(e))
            lines.append(t); srs.append(s)
            try:
                p.close_modal()
            except Exception:
                pass

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 2")

    # ── 시나리오 3: 동작 검증 ──────────────────────────────────────
    def test_scenario3_crud(self):
        r = self._make_r(3)
        lines, srs = [], []
        p = self.p
        _AUTO = "[AUTO]_cm_tag"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 3: 동작 검증 ━━━━━━━━━━━━━━━━━━━━━━━")

        # 사전 정리
        p.delete_all_auto_items()

        # ── 수정 버튼 미선택 경고 ─────────────────────────────────
        try:
            p.click(p.SEL_MODIFY_BTN)
            p.page.wait_for_timeout(400)
            if p.is_confirm_modal_visible():
                warn_msg = p.get_modal_message()
                t, s = r("pass" if "선택된 항목이 없습니다" in warn_msg else "fail",
                         "수정 버튼 — 미선택 시 경고",
                         f"입력: 미선택 상태로 수정 버튼 클릭 / 결과: {warn_msg!r}")
                p.dismiss_confirm_modal(); p.wait_for_confirm_modal_closed()
            else:
                t, s = r("fail", "수정 버튼 — 미선택 시 경고",
                         "입력: 미선택 상태 / 결과: 모달 없음")
        except Exception as e:
            t, s = r("warn", "수정 버튼 — 미선택 시 경고", str(e))
        lines.append(t); srs.append(s)

        # ── 삭제 버튼 미체크 경고 ─────────────────────────────────
        try:
            p.click(p.SEL_DELETE_BTN)
            p.page.wait_for_timeout(400)
            if p.is_confirm_modal_visible():
                del_msg = p.get_modal_message()
                t, s = r("pass" if "체크해 주세요" in del_msg else "fail",
                         "삭제 버튼 — 미체크 시 경고",
                         f"입력: 미체크 상태로 삭제 버튼 클릭 / 결과: {del_msg!r}")
                p.dismiss_confirm_modal(); p.wait_for_confirm_modal_closed()
            else:
                t, s = r("fail", "삭제 버튼 — 미체크 시 경고",
                         "입력: 미체크 상태 / 결과: 모달 없음")
        except Exception as e:
            t, s = r("warn", "삭제 버튼 — 미체크 시 경고", str(e))
        lines.append(t); srs.append(s)

        # ── 항목 추가 + 프로세스 등록 후 목록 확인 ──────────────
        initial_proc = ""
        try:
            initial_proc = p.add_item_with_process(_AUTO)
            p.search_item(_AUTO)
            names = p.get_item_names()
            t, s = r("pass" if _AUTO in names else "fail",
                     "항목 추가(프로세스 포함) — 목록 확인",
                     f"입력: {_AUTO!r} / 결과: 목록에 {'존재' if _AUTO in names else '없음'}")
        except Exception as e:
            t, s = r("fail", "항목 추가(프로세스 포함) — 목록 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 테이블 컬럼 표시 확인 ─────────────────────────────────
        try:
            p.search_item(_AUTO)
            rows = p.page.locator(p.SEL_TABLE_ROW).all()
            found_row = None
            for row in rows:
                tds = row.locator("td").all()
                if tds and _AUTO in tds[0].inner_text():
                    found_row = [td.inner_text().strip() for td in tds]
                    break
            t, s = r("pass" if found_row else "fail",
                     "테이블 — 태그 이름 컬럼 표시",
                     f"입력: {_AUTO!r} / 결과: {found_row}")
        except Exception as e:
            t, s = r("warn", "테이블 — 태그 이름 컬럼 표시", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 카운트 초기값 1 확인 ────────────────────────
        try:
            cnt = p.get_process_count_in_list(_AUTO)
            t, s = r("pass" if cnt == 1 else "warn",
                     "프로세스 카운트 — 초기값 1 확인",
                     f"입력: {_AUTO!r} 생성 + 프로세스 등록 직후 / 결과: {cnt}")
        except Exception as e:
            t, s = r("warn", "프로세스 카운트 — 초기값 1 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 검색 — 있는 항목 ──────────────────────────────────────
        try:
            p.search_item(_AUTO)
            names = p.get_item_names()
            t, s = r("pass" if _AUTO in names else "fail",
                     "검색(태그 이름) — 결과 확인",
                     f"입력: {_AUTO!r} / 결과: 목록에 {'존재' if _AUTO in names else '없음'}")
        except Exception as e:
            t, s = r("warn", "검색(태그 이름) — 결과 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 검색 — 없는 항목 ──────────────────────────────────────
        try:
            p.search_item("ZZZQANOTEXISTZZZTEST")
            names = p.get_item_names()
            t, s = r("pass" if len(names) == 0 else "fail",
                     "검색 — 없는 항목 검색 시 빈 목록",
                     f"입력: 'ZZZQANOTEXISTZZZTEST' 검색 / 결과: {len(names)}개 표시됨")
        except Exception as e:
            t, s = r("warn", "검색 — 없는 항목 검색 시 빈 목록", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 + 버튼: 다른 프로세스 추가 등록 ───────────
        cnt_before_add = p.get_process_count_in_list(_AUTO)
        cnt_after_add = cnt_before_add  # 기본값 (예외 시 사용)
        registered_proc_name = ""
        try:
            p.open_modify_modal(_AUTO)
            p.open_process_list_modal()
            registered_proc_name = p.select_different_process_in_modal(initial_proc)
            p.confirm_process_selection()
            proc_names = p.get_registered_process_names()
            added_new = registered_proc_name != initial_proc
            t, s = r("pass" if registered_proc_name in proc_names else "fail",
                     "프로세스 + 버튼 — 다른 프로세스 추가 등록",
                     f"입력: {initial_proc!r} 외 프로세스 선택 / "
                     f"결과: {registered_proc_name!r} 등록"
                     f"{'됨(다른 프로세스)' if added_new else '됨(동일-dedup)' if registered_proc_name in proc_names else ' 안됨'}")
            # r() 호출 후 저장 (캡처는 이미 완료)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)
        except Exception as e:
            t, s = r("fail", "프로세스 + 버튼 — 다른 프로세스 추가 등록", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 카운트 증가 확인 ─────────────────────────────
        try:
            cnt_after_add = p.get_process_count_in_list(_AUTO)
            if cnt_after_add > cnt_before_add:
                t, s = r("pass", "프로세스 카운트 — 추가 등록 후 증가 확인",
                         f"입력: 기존 {cnt_before_add}개 + 다른 프로세스 / 결과: {cnt_after_add}개")
            else:
                t, s = r("warn", "프로세스 카운트 — 추가 등록 후 증가 확인",
                         f"입력: 기존 {cnt_before_add}개 + 추가 시도 / 결과: {cnt_after_add}개 "
                         f"(시스템 프로세스 1개뿐 — 중복 dedup, 운용 프로세스 선행 실행 필요)")
        except Exception as e:
            t, s = r("warn", "프로세스 카운트 — 추가 등록 후 증가 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 - 버튼: 프로세스 제거 ──────────────────────
        try:
            p.open_modify_modal(_AUTO)
            before = p.get_registered_process_names()
            p.remove_first_registered_process()
            after = p.get_registered_process_names()
            t, s = r("pass" if len(after) < len(before) else "fail",
                     "프로세스 - 버튼 — 프로세스 제거",
                     f"입력: 첫 번째 프로세스 선택 후 - 클릭 / "
                     f"결과: 제거 전={len(before)}개, 제거 후={len(after)}개")
            # r() 호출 후 저장
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)
        except Exception as e:
            t, s = r("fail", "프로세스 - 버튼 — 프로세스 제거", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 카운트 감소 확인 ─────────────────────────────
        try:
            cnt_after_remove = p.get_process_count_in_list(_AUTO)
            expected = max(0, cnt_after_add - 1)
            t, s = r("pass" if cnt_after_remove == expected else "fail",
                     "프로세스 카운트 — 제거 후 감소 확인",
                     f"입력: {cnt_after_add}개 중 1개 제거 / 결과: {cnt_after_remove}개 (예상: {expected}개)")
        except Exception as e:
            t, s = r("warn", "프로세스 카운트 — 제거 후 감소 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 항목 삭제 ─────────────────────────────────────────────
        try:
            p.delete_item(_AUTO)
            p.search_item(_AUTO)
            names = p.get_item_names()
            t, s = r("pass" if _AUTO not in names else "fail",
                     "항목 삭제 — 목록에서 사라짐",
                     f"입력: {_AUTO!r} 삭제 / 결과: 목록에서 {'사라짐' if _AUTO not in names else '남아있음'}")
        except Exception as e:
            t, s = r("fail", "항목 삭제 — 목록에서 사라짐", str(e))
        lines.append(t); srs.append(s)

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 3")

    # ── 시나리오 4: 수정 시나리오 ─────────────────────────────────
    def test_scenario4_modify(self):
        r = self._make_r(4)
        lines, srs = [], []
        p = self.p
        _AUTO = "[AUTO]_tag_sc4"
        _DESC_ORIG = "sc4_original_desc"
        _DESC_MOD  = "sc4_modified_desc"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 4: 수정 시나리오 ━━━━━━━━━━━━━━━━━━━━━")

        # 사전 정리 + 항목 생성 + 프로세스 등록
        p.delete_all_auto_items()
        p.add_item_with_desc(_AUTO, _DESC_ORIG)
        p.register_first_process(_AUTO)

        # ── 수정 모달 제목 확인 ───────────────────────────────────
        try:
            p.open_modify_modal(_AUTO)
            mod_title = p.get_modal_title()
            t, s = r("pass" if mod_title == "태그 수정" else "fail",
                     "수정 모달 — 제목",
                     f"입력: 수정 모달 오픈 / 결과: 제목={mod_title!r}")
        except Exception as e:
            t, s = r("fail", "수정 모달 — 제목", str(e))
            p.close_modal()
        lines.append(t); srs.append(s)

        # ── 태그 이름 저장값 로드 확인 ───────────────────────────
        try:
            loaded_name = p.get_field_value(p.SEL_TAG_NAME)
            t, s = r("pass" if loaded_name == _AUTO else "fail",
                     "태그 이름(*) — 수정 모달 저장값 로드",
                     f"입력: {_AUTO!r} 저장 / 결과: {loaded_name!r}")
        except Exception as e:
            t, s = r("fail", "태그 이름(*) — 수정 모달 저장값 로드", str(e))
        lines.append(t); srs.append(s)

        # ── 설명 저장값 로드 확인 ────────────────────────────────
        try:
            loaded_desc = p.get_field_value(p.SEL_DESCRIPTION)
            t, s = r("pass" if loaded_desc == _DESC_ORIG else "fail",
                     "설명 — 수정 모달 저장값 로드",
                     f"입력: {_DESC_ORIG!r} 저장 / 결과: {loaded_desc!r}")
        except Exception as e:
            t, s = r("fail", "설명 — 수정 모달 저장값 로드", str(e))
        lines.append(t); srs.append(s)

        # ── 등록된 프로세스 존재 확인 ────────────────────────────
        try:
            proc_names = p.get_registered_process_names()
            t, s = r("pass" if len(proc_names) >= 1 else "fail",
                     "수정 모달 — 등록된 프로세스 존재 확인",
                     f"입력: 프로세스 1개 등록 후 수정 모달 / 결과: {len(proc_names)}개")
        except Exception as e:
            t, s = r("warn", "수정 모달 — 등록된 프로세스 존재 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 설명 수정 후 저장 ─────────────────────────────────────
        try:
            p.page.locator(p.SEL_DESCRIPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                _DESC_MOD
            )
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)
            t, s = r("pass", "설명 — 수정 후 저장",
                     f"입력: {_DESC_MOD!r} 수정 / 결과: 저장 완료")
        except Exception as e:
            t, s = r("fail", "설명 — 수정 후 저장", str(e))
        lines.append(t); srs.append(s)

        # ── 수정 후 재오픈 → 설명 재확인 ────────────────────────
        try:
            p.open_modify_modal(_AUTO)
            reloaded_desc = p.get_field_value(p.SEL_DESCRIPTION)
            t, s = r("pass" if reloaded_desc == _DESC_MOD else "fail",
                     "설명 — 수정 후 재확인",
                     f"입력: {_DESC_MOD!r} 수정 / 결과: {reloaded_desc!r}")
        except Exception as e:
            t, s = r("fail", "설명 — 수정 후 재확인", str(e))
            p.close_modal()
        lines.append(t); srs.append(s)

        # ── 설명 지우기 후 저장 ───────────────────────────────────
        try:
            p.page.locator(p.SEL_DESCRIPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                ""
            )
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)
            t, s = r("pass", "설명 — 지우기 후 저장",
                     "입력: 설명 삭제 후 저장 / 결과: 저장 완료")
        except Exception as e:
            t, s = r("fail", "설명 — 지우기 후 저장", str(e))
        lines.append(t); srs.append(s)

        # ── 재오픈 → 설명 빈값 유지 확인 ────────────────────────
        try:
            p.open_modify_modal(_AUTO)
            empty_desc = p.get_field_value(p.SEL_DESCRIPTION)
            t, s = r("pass" if empty_desc == "" else "fail",
                     "설명 — 지우기 후 재오픈 빈값 유지 확인",
                     f"입력: 설명 삭제 후 저장 / 결과: {empty_desc!r}")
            p.close_modal()
        except Exception as e:
            t, s = r("fail", "설명 — 지우기 후 재오픈 빈값 유지 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 사후 정리 ─────────────────────────────────────────────
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 4")

    # ── 시나리오 5: 케이스 검증 ────────────────────────────────────
    def test_scenario5_case(self):
        """케이스A: 전체 필드 채우기 → 저장 → 재오픈 → 전 필드 값 유지 확인
        케이스B: 필수 필드만 입력 → 저장 → 재오픈 → 선택 필드 빈값 + 프로세스 0개 확인
        """
        r = self._make_r(5)
        lines, srs = [], []
        p = self.p
        _FULL = "[AUTO]_sc5_full"
        _REQ  = "[AUTO]_sc5_req"
        _FULL_DESC = "sc5_full_description"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 5: 케이스 검증 ━━━━━━━━━━━━━━━━━━━━━━")

        # ── 사전 정리 ─────────────────────────────────────────────
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        # ══════════════════════════════════════════════════════════
        # 케이스A: 전체 필드 채우기
        # ══════════════════════════════════════════════════════════

        # ── A-1: [AUTO]_sc5_full 항목 생성 (이름 + 설명) ──────────
        try:
            p.add_item_with_desc(_FULL, _FULL_DESC)
            t, s = r("pass", "케이스A — 항목 생성(이름+설명)",
                     f"입력: {_FULL!r}, desc={_FULL_DESC!r} / 결과: 생성됨")
        except Exception as e:
            t, s = r("fail", "케이스A — 항목 생성(이름+설명)", str(e))
        lines.append(t); srs.append(s)

        # ── A-2: 프로세스 1개 등록 ────────────────────────────────
        try:
            p.register_first_process(_FULL)
            t, s = r("pass", "케이스A — 프로세스 등록",
                     f"입력: {_FULL!r} 에 첫 번째 프로세스 등록 / 결과: 등록됨")
        except Exception as e:
            t, s = r("fail", "케이스A — 프로세스 등록", str(e))
        lines.append(t); srs.append(s)

        # ── A-3: 수정 모달 재오픈 → 전 필드 저장값 확인 ──────────
        try:
            p.open_modify_modal(_FULL)

            # 이름 확인
            loaded_name = p.get_field_value(p.SEL_TAG_NAME)
            t, s = r("pass" if loaded_name == _FULL else "fail",
                     "케이스A — 태그 이름(*) 저장값 유지",
                     f"입력: {_FULL!r} / 결과: {loaded_name!r}")
            lines.append(t); srs.append(s)

            # 설명 확인
            loaded_desc = p.get_field_value(p.SEL_DESCRIPTION)
            t, s = r("pass" if loaded_desc == _FULL_DESC else "fail",
                     "케이스A — 설명 저장값 유지",
                     f"입력: {_FULL_DESC!r} / 결과: {loaded_desc!r}")
            lines.append(t); srs.append(s)

            # 프로세스 카운트 ≥ 1 확인
            proc_names = p.get_registered_process_names()
            t, s = r("pass" if len(proc_names) >= 1 else "fail",
                     "케이스A — 프로세스 카운트 유지(≥1)",
                     f"입력: 프로세스 1개 등록 후 재오픈 / 결과: {len(proc_names)}개")
            lines.append(t); srs.append(s)

            p.close_modal()

        except Exception as e:
            t, s = r("fail", "케이스A — 수정 모달 재오픈/확인", str(e))
            lines.append(t); srs.append(s)
            try:
                p.close_modal()
            except Exception:
                pass

        # ══════════════════════════════════════════════════════════
        # 케이스B: 필수 필드만 입력
        # ══════════════════════════════════════════════════════════

        # ── B-1: [AUTO]_sc5_req 항목 생성 (이름만, 선택 필드 미입력) ─
        try:
            p.add_item(_REQ)
            t, s = r("pass", "케이스B — 항목 생성(이름만)",
                     f"입력: {_REQ!r} (설명·프로세스 없음) / 결과: 생성됨")
        except Exception as e:
            t, s = r("fail", "케이스B — 항목 생성(이름만)", str(e))
        lines.append(t); srs.append(s)

        # ── B-2: 수정 모달 재오픈 → 선택 필드 전부 빈값 확인 ─────
        try:
            p.open_modify_modal(_REQ)

            # 설명 빈값 유지 확인
            loaded_desc_b = p.get_field_value(p.SEL_DESCRIPTION)
            t, s = r("pass" if loaded_desc_b == "" else "fail",
                     "케이스B — 설명 빈값 유지",
                     f"입력: 설명 미입력 / 결과: {loaded_desc_b!r}")
            lines.append(t); srs.append(s)

            # 프로세스 카운트 == 0 확인
            proc_names_b = p.get_registered_process_names()
            t, s = r("pass" if len(proc_names_b) == 0 else "fail",
                     "케이스B — 프로세스 카운트 0 유지",
                     f"입력: 프로세스 미등록 / 결과: {len(proc_names_b)}개")
            lines.append(t); srs.append(s)

            p.close_modal()

        except Exception as e:
            t, s = r("fail", "케이스B — 수정 모달 재오픈/확인", str(e))
            lines.append(t); srs.append(s)
            try:
                p.close_modal()
            except Exception:
                pass

        # ── 사후 정리 ─────────────────────────────────────────────
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 5")

    # ── 시나리오 6: 다음 테스트용 태그 설정 ──────────────────────
    def test_scenario6_suite_setup(self):
        """
        제어 스위트 등 다음 테스트에서 사용할 태그를 준비한다.
        [AUTO_KEEP]_sc6_cm_tag_suite 태그를 생성하고 프로세스 1개를 등록한 뒤
        삭제하지 않고 남겨둔다.

        연계 테스트(다른 test_npouch_*.py 파일에서 _SUITE_TAG 참조)가 없으면
        사전 정리 후 skip 처리한다.
        """
        r = self._make_r(6)
        lines, srs = [], []
        p = self.p
        # AUTO_KEEP_ prefix — sc1 cleanup 시 보존, 세션 간 잔존
        _SUITE_TAG = "[AUTO_KEEP]_sc6_cm_tag_suite"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 6: 다음 테스트용 태그 설정 ━━━━━━━━━━━━")

        # ── 사전 정리 (항상 실행 — 이전 실행 잔여물 제거) ────────────
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        # cross-page 차단 검증을 sc6 안에서 항상 수행 — _consumer_files 감지 skip 제거

        # ── suite 태그 — 잔존 시 재사용, 없으면 생성 ───────────────
        try:
            p.search_item(_SUITE_TAG)
            already = _SUITE_TAG in p.get_item_names()
            if already:
                t, s = r("pass", f"{_SUITE_TAG} — 태그 잔존 재사용",
                         f"결과: AUTO_KEEP 잔존 활용")
            else:
                p.add_item(_SUITE_TAG)
                p.search_item(_SUITE_TAG)
                names = p.get_item_names()
                t, s = r("pass" if _SUITE_TAG in names else "fail",
                         f"{_SUITE_TAG} — 태그 생성",
                         f"입력: 태그 추가 / 결과: {'생성됨' if _SUITE_TAG in names else '없음'}")
        except Exception as e:
            t, s = r("fail", f"{_SUITE_TAG} — 태그 생성", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 등록 (이미 등록돼 있으면 skip) ─────────────────
        # [AUTO_KEEP]_sc6_cm_proc_suite 우선 선택 (프로세스 sc6 에서 KEEP 잔존)
        _SUITE_PROC = "[AUTO_KEEP]_sc6_cm_proc_suite"
        registered_proc = ""
        try:
            existing_procs = p.get_process_names_in_list(_SUITE_TAG) if hasattr(p, "get_process_names_in_list") else []
            if _SUITE_PROC in existing_procs:
                t, s = r("pass", f"{_SUITE_TAG} — 프로세스 이미 등록 — 재사용",
                         f"결과: {_SUITE_PROC!r} 잔존 등록")
                registered_proc = _SUITE_PROC
            else:
                p.open_modify_modal(_SUITE_TAG)
                p.open_process_list_modal()
                registered_proc = p.select_process_by_name(_SUITE_PROC)
                p.confirm_process_selection()
                proc_names = p.get_registered_process_names()
                t, s = r("pass" if registered_proc in proc_names else "fail",
                         f"{_SUITE_TAG} — 프로세스 등록",
                         f"입력: {registered_proc!r} 선택 / 결과: "
                         f"{'등록됨' if registered_proc in proc_names else '등록 안됨'}")
                p.click_attached(p.SEL_SUBMIT_BTN)
                p._handle_confirm_modal()
                p.wait_for(p.SEL_ADD_BTN)
        except Exception as e:
            t, s = r("fail", f"{_SUITE_TAG} — 프로세스 등록", str(e))
        lines.append(t); srs.append(s)

        # ── 프로세스 카운트 확인 ──────────────────────────────────
        try:
            cnt = p.get_process_count_in_list(_SUITE_TAG)
            t, s = r("pass" if cnt >= 1 else "fail",
                     f"{_SUITE_TAG} — 프로세스 카운트 확인",
                     f"입력: 프로세스 등록 후 / 결과: {cnt}개")
        except Exception as e:
            t, s = r("warn", f"{_SUITE_TAG} — 프로세스 카운트 확인", str(e))
        lines.append(t); srs.append(s)

        # ── cross-page 검증: 태그 등록 중 프로세스 삭제 차단 ────────────
        # 제품 2단계 동작 (Chrome 직접 검증 2026-06-04):
        #   1) 삭제 클릭 → "선택한 항목을 삭제 하시겠습니까?" (확인/취소)
        #   2) 확인 → 서버 검증 → "태그에 해당 프로세스가 할당 되어 있습니다" (차단, 확인만)
        #   3) 프로세스 보존 (삭제 안 됨)
        # pass = 2단계에서 "할당" 차단 / fail = 차단 없이 삭제 성공 (실제 결함)
        try:
            proc_page = NpouchOperationProcessPage(self.p.page, self.p.settings)
            proc_page.navigate_to()
            proc_page.search_item(_SUITE_PROC)
            proc_names = proc_page.get_item_names()
            if _SUITE_PROC not in proc_names:
                t, s = r("warn", f"cross-page — 프로세스 페이지에서 {_SUITE_PROC} 미발견",
                         f"입력: 프로세스 페이지 search / 결과: names={proc_names}")
                lines.append(t); srs.append(s)
            else:
                row = proc_page.page.locator(proc_page.SEL_TABLE_ROW).filter(
                    has_text=_SUITE_PROC
                ).first
                checkbox = row.locator(proc_page.SEL_CHECKBOX).first
                if not checkbox.is_checked():
                    proc_page._toggle_overlay(False)
                    try:
                        checkbox.click()
                    finally:
                        proc_page._toggle_overlay(True)
                proc_page.click(proc_page.SEL_DELETE_BTN)
                # 1단계: "삭제 하시겠습니까?" confirm → 확인 클릭하여 서버 검증 진행
                proc_page.page.locator(proc_page.SEL_CONFIRM_MODAL).wait_for(
                    state="attached", timeout=proc_page._TIMEOUT_MODAL
                )
                proc_page.click_attached(proc_page.SEL_CONFIRM_BTN)
                proc_page.page.wait_for_timeout(800)
                # 2단계: 서버 응답 모달 (차단 "할당" or 삭제 성공)
                if proc_page.page.locator(proc_page.SEL_CONFIRM_MODAL).count() > 0:
                    msg2 = proc_page.page.locator(proc_page.SEL_MODAL_MSG).first.inner_text().strip()
                    is_blocked = ("할당" in msg2) or ("사용" in msg2) or ("참조" in msg2)
                else:
                    # 응답 모달 없음 = 삭제 완료 = 참조 무결성 결함
                    msg2 = "(2단계 응답 모달 없음 — 삭제 완료 추정)"
                    is_blocked = False
                t, s = r("pass" if is_blocked else "fail",
                         f"cross-page — 태그 등록 중 프로세스 삭제 차단",
                         f"입력: {_SUITE_PROC} 삭제 시도(확인) / 결과: 2단계 msg={msg2!r} "
                         f"blocked={is_blocked} "
                         f"({'정상 차단 (할당)' if is_blocked else '결함 — 차단 없이 삭제됨'})",
                         capture=(not is_blocked))
                lines.append(t); srs.append(s)
                # 2단계 모달(차단 alert) dismiss — 확인 (프로세스는 이미 보존됨)
                try:
                    proc_page.click_attached(proc_page.SEL_CONFIRM_BTN)
                except Exception:
                    pass
            # 태그 페이지 복귀
            self.p.navigate_to()
        except Exception as e:
            t, s = r("warn", f"cross-page — 프로세스 삭제 차단 검증 예외", str(e))
            lines.append(t); srs.append(s)
            try:
                self.p.navigate_to()
            except Exception:
                pass

        # ── 남겨두기 안내 ─────────────────────────────────────────
        t, s = r("skip", f"{_SUITE_TAG} — 삭제하지 않음",
                 "다음 제어 스위트 테스트에서 사용 — 의도적으로 남겨둠")
        lines.append(t); srs.append(s)

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 6")
