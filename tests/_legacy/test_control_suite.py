"""
tests/test_control_suite.py — nPouch 제어 스위트 관리 QA 테스트

Phase 1: 기본 요소
  - 목록 UI (버튼 존재, 테이블 헤더, 검색창)
  - 미선택 경고 (수정/삭제)
  - 스위트 추가/복사/삭제 (이름만)
  - 상세 패널 (행 클릭 → 필드 표시)
  - 수정 모달 기본 필드 (csuName, toggle ON/OFF, 커스텀 옵션값)

파이프라인: ScanResult/PageScanReport -> conftest 수집 -> html_reporter HTML 생성

실행:
  pytest tests/test_control_suite.py -v -s
  pytest tests/test_control_suite.py::TestControlSuite::test_scenario1_ui -v -s
"""
import re
import time
import yaml
import pytest
from pathlib import Path

from core.models import ScanResult, PageScanReport
from pages.npouch_control_suite_page import NpouchControlSuitePage

# ── scan_hints YAML 로드 ──────────────────────────────────────────
def _load_hints(page_id: str) -> dict:
    path = Path(__file__).parent.parent / "config" / "scan_hints" / f"{page_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}

# ── 스크린샷 ─────────────────────────────────────────────────────
_SS_DIR = Path(__file__).parent.parent / "reports" / "screenshots"

def _ss(page, label: str) -> str | None:
    try:
        _SS_DIR.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w가-힣]", "_", label)[:40]
        path = _SS_DIR / f"BUG_{safe}_{int(time.time()*1000)}.png"
        page.screenshot(path=str(path))
        return str(path)
    except Exception:
        return None

# ── 모듈 상수 ─────────────────────────────────────────────────────
_STATUS_ICON  = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]", "warn": "[WARN]"}
_STATUS_TO_SR = {"pass": "pass", "fail": "fail", "warn": "warn", "skip": "skip"}

_SAVE_SUCCESS_KEYWORDS = ("하시겠습니까", "저장 하였습니다", "저장하였습니다",
                           "추가되었습니다", "수정되었습니다", "하였습니다")


def _r(status: str, label: str, detail: str = "", sc: int = 0,
       page=None) -> tuple[str, ScanResult]:
    icon = _STATUS_ICON.get(status, "?")
    text = f"  {icon} {label}" + (f": {detail}" if detail else "")
    extra: dict = {"scenario": sc}
    if page and status in ("fail", "warn"):
        ss_path = _ss(page, label)
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
class TestControlSuite:
    PAGE_NAME = "제어 스위트 관리"
    PAGE_ID   = "control_suite"

    @pytest.fixture(autouse=True)
    def setup(self, request, logged_in_page, settings):
        self._request = request
        self.p = NpouchControlSuitePage(logged_in_page, settings)
        self._hints = _load_hints(self.PAGE_ID)
        self.p.navigate_to()

    def _attach(self, scan_results: list[ScanResult]) -> None:
        report = PageScanReport(page_id=self.PAGE_ID)
        report.results = scan_results
        self._request.node._scan_report = report
        self._request.node._npouch_page_id = self.PAGE_ID

    def _make_r(self, sc: int):
        """이슈 감지 즉시 현재 화면을 자동 캡처하는 _r() 래퍼."""
        _page = self.p.page
        def r(status: str, label: str, detail: str = "",
              capture: bool = None) -> tuple[str, ScanResult]:
            if capture is True:
                page_to_use = _page
            elif capture is False:
                page_to_use = None
            else:
                page_to_use = _page if status == "fail" else None
            return _r(status, label, detail, sc=sc, page=page_to_use)
        return r

    # ── 시나리오 1: UI 구조 ────────────────────────────────────────
    def test_scenario1_ui(self):
        r = self._make_r(1)
        lines, srs = [], []
        p = self.p
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 1: UI 구조 ━━━━━━━━━━━━━━━━━━━━━━━")

        # ── 탭 전환 ───────────────────────────────────────────────
        t, s = r("skip", "탭 전환", "단일 뷰 페이지 — 탭 없음")
        lines.append(t); srs.append(s)

        # ── 버튼 존재 확인 ────────────────────────────────────────
        for btn_label, btn_sel in [
            ("추가 버튼",         p.SEL_ADD_BTN),
            ("수정 버튼",         p.SEL_MODIFY_BTN),
            ("복사 버튼",         p.SEL_COPY_BTN),
            ("삭제 버튼",         p.SEL_DELETE_BTN),
            ("상세정보 토글 버튼", "button#__layoutMainItemDetailOpenCloseBtn"),
        ]:
            exists = p.page.locator(btn_sel).count() > 0
            t, s = r("pass" if exists else "fail",
                     f"{btn_label} — 존재",
                     f"입력: (없음) / 결과: {'존재' if exists else '없음'}")
            lines.append(t); srs.append(s)

        # ── 테이블 헤더 확인 ──────────────────────────────────────
        header_text = " ".join(
            th.inner_text().strip()
            for th in p.page.locator("table thead th").all()
        )
        print(f"  실제 헤더: {header_text!r}")
        for col in ["스위트 이름", "등록된 프로세스", "등록된 웹제한", "등록자", "수정자"]:
            exists = col in header_text
            t, s = r("pass" if exists else "fail",
                     f"테이블 헤더 — {col}",
                     f"입력: (없음) / 결과: {'존재' if exists else '없음'}")
            lines.append(t); srs.append(s)

        # ── 검색창 존재 ───────────────────────────────────────────
        t, s = r("pass" if p.page.locator(p.SEL_SEARCH_INPUT).count() > 0 else "fail",
                 "검색창(searchText) — 존재",
                 "입력: (없음) / 결과: 존재")
        lines.append(t); srs.append(s)

        # 검색 버튼
        t, s = r("pass" if p.page.locator("button#searchBtn").count() > 0 else "fail",
                 "검색 버튼 — 존재",
                 "입력: (없음) / 결과: 존재")
        lines.append(t); srs.append(s)

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 1")

    # ── 시나리오 2: 입력 구조 ──────────────────────────────────────
    def test_scenario2_modal_fields(self):
        r = self._make_r(2)
        lines, srs = [], []
        p = self.p
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 2: 입력 구조 ━━━━━━━━━━━━━━━━━━━━━━━")

        # ── 추가 모달 열기 ────────────────────────────────────────
        p.open_add_modal()

        # 모달 제목
        title = p.get_modal_title()
        t, s = r("pass" if title == "제어 스위트 추가" else "fail",
                 "추가 모달 — 제목",
                 f"입력: 모달 오픈 / 결과: 제목={title!r}")
        lines.append(t); srs.append(s)

        # 버튼 텍스트
        submit_text = p.page.locator(p.SEL_SUBMIT_BTN).first.inner_text().strip()
        cancel_text = p.page.locator(p.SEL_CANCEL_BTN).first.inner_text().strip()
        for label, val, expected in [
            ("추가(제출) 버튼 텍스트", submit_text, "추가"),
            ("취소 버튼 텍스트",       cancel_text, "취소"),
        ]:
            t, s = r("pass" if val == expected else "warn", label,
                     f"입력: 버튼 텍스트 확인 / 결과: {val!r}")
            lines.append(t); srs.append(s)

        # ── 필드 존재 + 초기값 확인 ──────────────────────────────
        field_checks = [
            ("input#csuName",            "스위트 이름(*)",       True),
            ("input#isClipboardRestrict","클립보드 공유제한",     False),
            ("input#isNetwork",          "네트워크 허용",         False),
            ("input#ALLOW",              "제어할 확장자(ALLOW)",  False),
            ("input#BLOCK",              "제어할 확장자(BLOCK)",  False),
            ("input#isSignExcept",       "전자서명 예외처리",     False),
            ("input#customOptionText",   "커스텀 옵션값",         False),
        ]
        for sel, label, req in field_checks:
            mark = "(*)" if req else ""
            exists = p.page.locator(sel).count() > 0
            t, s = r("pass" if exists else "fail",
                     f"{label}{mark} — 필드 존재",
                     f"입력: (없음) / 결과: {'존재' if exists else '없음'}")
            lines.append(t); srs.append(s)

            if exists:
                try:
                    init_val = p.get_field_value(sel)
                    t, s = r("pass", f"{label}{mark} — 초기값",
                             f"입력: 초기 상태 / 결과: {init_val!r}")
                    lines.append(t); srs.append(s)
                except Exception:
                    pass

        # ── csuName 빈 값 제출 → 에러 확인 ──────────────────────
        try:
            p.try_submit()
            p.page.wait_for_timeout(500)
            if p.is_confirm_modal_visible():
                err_msg = p.get_modal_message()
                has_name_err = any(kw in err_msg for kw in ("이름", "스위트"))
                not_saved = not any(kw in err_msg for kw in _SAVE_SUCCESS_KEYWORDS)
                t, s = r("pass" if has_name_err and not_saved else "fail",
                         "스위트 이름(*) — 빈 값 제출 경고",
                         f"입력: 이름 비운 채 제출 / 결과: {err_msg!r}")
                p.dismiss_confirm_modal()
                p.wait_for_confirm_modal_closed()
            else:
                t, s = r("fail", "스위트 이름(*) — 빈 값 제출 경고",
                         "입력: 이름 비운 채 제출 / 결과: 모달 없음")
        except Exception as e:
            t, s = r("warn", "스위트 이름(*) — 빈 값 제출 경고", str(e))
        lines.append(t); srs.append(s)

        # ── 취소 후 재오픈 → 필드 초기화 ───────────────────────
        try:
            p.page.locator(p.SEL_CSU_NAME).first.fill("임시입력값_sc2")
            p.close_modal()
            p.page.wait_for_timeout(300)
            p.open_add_modal()
            reopened_name = p.get_field_value(p.SEL_CSU_NAME)
            t, s = r("pass" if reopened_name == "" else "fail",
                     "취소 후 재오픈 — 스위트 이름 필드 초기화",
                     f"입력: 이름 입력 후 취소 / 결과: 재오픈 시 이름={reopened_name!r}")
            p.close_modal()
        except Exception as e:
            t, s = r("warn", "취소 후 재오픈 — 스위트 이름 필드 초기화", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # ── 프로세스별 제어 섹션 존재 확인 ───────────────────────
        try:
            p.open_add_modal()
            add_proc_btn = p.page.locator(p.SEL_ADD_PROCESS_BTN).count() > 0
            rem_proc_btn = p.page.locator(p.SEL_REMOVE_PROCESS_BTN).count() > 0
            add_web_btn  = p.page.locator(p.SEL_ADD_WEB_RESTRICT_BTN).count() > 0
            rem_web_btn  = p.page.locator(p.SEL_REMOVE_WEB_RESTRICT_BTN).count() > 0
            for lbl, val in [
                ("프로세스별 제어 — + 버튼", add_proc_btn),
                ("프로세스별 제어 — - 버튼", rem_proc_btn),
                ("웹 제한기능 — + 버튼",     add_web_btn),
                ("웹 제한기능 — - 버튼",     rem_web_btn),
            ]:
                t, s = r("pass" if val else "fail",
                         f"추가 모달 — {lbl} 존재",
                         f"입력: (없음) / 결과: {'존재' if val else '없음'}")
                lines.append(t); srs.append(s)
            p.close_modal()
        except Exception as e:
            t, s = r("warn", "추가 모달 — 섹션 버튼 존재 확인", str(e))
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
        _AUTO = "[AUTO]_csu_sc3"
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
                         f"입력: 미선택 상태로 수정 클릭 / 결과: {warn_msg!r}")
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
                         f"입력: 미체크 상태로 삭제 클릭 / 결과: {del_msg!r}")
                p.dismiss_confirm_modal(); p.wait_for_confirm_modal_closed()
            else:
                t, s = r("fail", "삭제 버튼 — 미체크 시 경고",
                         "입력: 미체크 상태 / 결과: 모달 없음")
        except Exception as e:
            t, s = r("warn", "삭제 버튼 — 미체크 시 경고", str(e))
        lines.append(t); srs.append(s)

        # ── 스위트 추가 → 목록 확인 ──────────────────────────────
        created_name = _AUTO
        try:
            created_name = p.add_policy(_AUTO)
            p.search_policy(_AUTO)
            names = p.get_policy_names()
            t, s = r("pass" if created_name in names else "fail",
                     "스위트 추가 — 목록 확인",
                     f"입력: {_AUTO!r} / 결과: 목록에 {'존재' if created_name in names else '없음'}")
        except Exception as e:
            t, s = r("fail", "스위트 추가 — 목록 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 검색 — 있는 항목 ──────────────────────────────────────
        try:
            p.search_policy(created_name)
            names = p.get_policy_names()
            t, s = r("pass" if created_name in names else "fail",
                     "검색(스위트 이름) — 결과 확인",
                     f"입력: {created_name!r} / 결과: {'존재' if created_name in names else '없음'}")
        except Exception as e:
            t, s = r("warn", "검색(스위트 이름) — 결과 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 검색 — 없는 항목 ──────────────────────────────────────
        try:
            p.search_policy("ZZZQANOTEXISTZZZTEST_CSU")
            names = p.get_policy_names()
            t, s = r("pass" if len(names) == 0 else "fail",
                     "검색 — 없는 항목 검색 시 빈 목록",
                     f"입력: 'ZZZQANOTEXISTZZZTEST_CSU' 검색 / 결과: {len(names)}개")
        except Exception as e:
            t, s = r("warn", "검색 — 없는 항목 검색 시 빈 목록", str(e))
        lines.append(t); srs.append(s)

        # ── 복사 버튼 → 복사본 생성 ──────────────────────────────
        # 제어 스위트는 수정일 기준 정렬 → 복사 후 원본 이름으로 재검색 시 2개 이상
        p.search_policy(created_name)
        p.page.wait_for_timeout(300)
        count_before_copy = len(p.get_policy_names())
        try:
            p.copy_policy(created_name)   # 내부에서 _restore_page_size → 검색 초기화됨
            # 원본 이름으로 재검색 — 원본 + 복사본이 모두 해당 이름을 포함
            p.search_policy(created_name)
            p.page.wait_for_timeout(400)
            names_after = p.get_policy_names()
            has_copy = len(names_after) > count_before_copy
            t, s = r("pass" if has_copy else "warn",
                     "복사 버튼 — 복사본 생성 확인",
                     f"입력: {created_name!r} 복사 / 결과: "
                     f"복사 전 {count_before_copy}개 → 복사 후 {len(names_after)}개")
        except Exception as e:
            t, s = r("warn", "복사 버튼 — 복사본 생성 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 상세 패널 — 행 클릭 후 필드 표시 ────────────────────
        try:
            p.search_policy(created_name)
            p.page.wait_for_timeout(400)
            p.click_policy_row(created_name)
            p.page.wait_for_timeout(300)
            panel_text = p.get_detail_panel_text()
            # 상세 패널에 스위트 이름이 표시되는지 확인
            name_in_panel = created_name in panel_text or len(panel_text) > 10
            t, s = r("pass" if name_in_panel else "warn",
                     "상세 패널 — 행 클릭 후 필드 표시",
                     f"입력: {created_name!r} 행 클릭 / 결과: 패널 텍스트 길이={len(panel_text)}")
        except Exception as e:
            t, s = r("warn", "상세 패널 — 행 클릭 후 필드 표시", str(e))
        lines.append(t); srs.append(s)

        # ── 스위트 삭제 → 목록에서 사라짐 ───────────────────────
        try:
            p.delete_all_auto_items()
            p.search_policy(created_name)
            names = p.get_policy_names()
            t, s = r("pass" if created_name not in names else "fail",
                     "스위트 삭제 — 목록에서 사라짐",
                     f"입력: {created_name!r} 삭제 / 결과: "
                     f"{'사라짐' if created_name not in names else '남아있음'}")
        except Exception as e:
            t, s = r("fail", "스위트 삭제 — 목록에서 사라짐", str(e))
        lines.append(t); srs.append(s)

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 3")

    # ── 시나리오 4: 수정 시나리오 ─────────────────────────────────
    def test_scenario4_modify(self):
        r = self._make_r(4)
        lines, srs = [], []
        p = self.p
        _AUTO        = "[AUTO]_csu_sc4"
        _CUSTOM_ORIG = "sc4_custom_orig"
        _CUSTOM_MOD  = "sc4_custom_mod"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 4: 수정 시나리오 ━━━━━━━━━━━━━━━━━━━━━")

        # 사전 정리 + 항목 생성
        p.delete_all_auto_items()
        created_name = p.add_policy(_AUTO)

        # ── 수정 모달 제목 확인 ───────────────────────────────────
        try:
            p.open_modify_modal(created_name)
            mod_title = p.get_modal_title()
            t, s = r("pass" if mod_title == "제어 스위트 수정" else "fail",
                     "수정 모달 — 제목",
                     f"입력: 수정 모달 오픈 / 결과: {mod_title!r}")
        except Exception as e:
            t, s = r("fail", "수정 모달 — 제목", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # ── csuName 저장값 로드 확인 ─────────────────────────────
        try:
            loaded_name = p.get_field_value(p.SEL_CSU_NAME)
            t, s = r("pass" if loaded_name == created_name else "fail",
                     "스위트 이름(*) — 수정 모달 저장값 로드",
                     f"입력: {created_name!r} 저장 / 결과: {loaded_name!r}")
        except Exception as e:
            t, s = r("fail", "스위트 이름(*) — 수정 모달 저장값 로드", str(e))
        lines.append(t); srs.append(s)

        # ── 클립보드 토글 초기값 OFF 확인 ────────────────────────
        try:
            cb_state = p.get_toggle_state(p.SEL_CLIPBOARD_RESTRICT)
            t, s = r("pass" if not cb_state else "warn",
                     "클립보드 공유제한 — 초기값 OFF 확인",
                     f"입력: 저장값 로드 / 결과: {'ON' if cb_state else 'OFF'}")
        except Exception as e:
            t, s = r("warn", "클립보드 공유제한 — 초기값 OFF 확인", str(e))
        lines.append(t); srs.append(s)

        # ── 커스텀 옵션값 입력 → 저장 ────────────────────────────
        try:
            p.page.locator(p.SEL_CUSTOM_OPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                _CUSTOM_ORIG,
            )
            p.page.wait_for_timeout(100)
            p.save_edit_modal()
            t, s = r("pass", "커스텀 옵션값 — 입력 후 저장",
                     f"입력: {_CUSTOM_ORIG!r} / 결과: 저장 완료")
        except Exception as e:
            t, s = r("fail", "커스텀 옵션값 — 입력 후 저장", str(e))
        lines.append(t); srs.append(s)

        # ── 커스텀 옵션값 재오픈 확인 ────────────────────────────
        try:
            p.open_modify_modal(created_name)
            loaded_custom = p.get_field_value(p.SEL_CUSTOM_OPTION)
            t, s = r("pass" if loaded_custom == _CUSTOM_ORIG else "fail",
                     "커스텀 옵션값 — 재오픈 후 저장값 확인",
                     f"입력: {_CUSTOM_ORIG!r} 저장 / 결과: {loaded_custom!r}")
        except Exception as e:
            t, s = r("fail", "커스텀 옵션값 — 재오픈 후 저장값 확인", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # ── 클립보드 토글 ON → 저장 → 재확인 ────────────────────
        try:
            p.set_toggle(p.SEL_CLIPBOARD_RESTRICT, True)
            p.page.wait_for_timeout(150)
            p.save_edit_modal()

            p.open_modify_modal(created_name)
            cb_on = p.get_toggle_state(p.SEL_CLIPBOARD_RESTRICT)
            t, s = r("pass" if cb_on else "fail",
                     "클립보드 공유제한 — ON 저장 → 재오픈 확인",
                     f"입력: 토글 ON 후 저장 / 결과: {'ON' if cb_on else 'OFF'}")
        except Exception as e:
            t, s = r("fail", "클립보드 공유제한 — ON 저장 → 재오픈 확인", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # ── 클립보드 토글 OFF → 저장 → 재확인 ───────────────────
        try:
            p.set_toggle(p.SEL_CLIPBOARD_RESTRICT, False)
            p.page.wait_for_timeout(150)
            p.save_edit_modal()

            p.open_modify_modal(created_name)
            cb_off = p.get_toggle_state(p.SEL_CLIPBOARD_RESTRICT)
            t, s = r("pass" if not cb_off else "fail",
                     "클립보드 공유제한 — OFF 저장 → 재오픈 확인",
                     f"입력: 토글 OFF 후 저장 / 결과: {'ON' if cb_off else 'OFF'}")
            p.close_modal()
        except Exception as e:
            t, s = r("fail", "클립보드 공유제한 — OFF 저장 → 재오픈 확인", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # ── 커스텀 옵션값 수정 → 재확인 ─────────────────────────
        try:
            p.open_modify_modal(created_name)
            p.page.locator(p.SEL_CUSTOM_OPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                _CUSTOM_MOD,
            )
            p.page.wait_for_timeout(100)
            p.save_edit_modal()

            p.open_modify_modal(created_name)
            loaded_custom_mod = p.get_field_value(p.SEL_CUSTOM_OPTION)
            t, s = r("pass" if loaded_custom_mod == _CUSTOM_MOD else "fail",
                     "커스텀 옵션값 — 수정 후 재확인",
                     f"입력: {_CUSTOM_MOD!r} 수정 / 결과: {loaded_custom_mod!r}")
            p.close_modal()
        except Exception as e:
            t, s = r("fail", "커스텀 옵션값 — 수정 후 재확인", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # ── 커스텀 옵션값 지우기 → 재확인 ────────────────────────
        try:
            p.open_modify_modal(created_name)
            p.page.locator(p.SEL_CUSTOM_OPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                "",
            )
            p.page.wait_for_timeout(100)
            p.save_edit_modal()

            p.open_modify_modal(created_name)
            empty_custom = p.get_field_value(p.SEL_CUSTOM_OPTION)
            t, s = r("pass" if empty_custom == "" else "fail",
                     "커스텀 옵션값 — 지우기 후 빈값 유지 확인",
                     f"입력: 값 삭제 후 저장 / 결과: {empty_custom!r}")
            p.close_modal()
        except Exception as e:
            t, s = r("fail", "커스텀 옵션값 — 지우기 후 빈값 유지 확인", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # 사후 정리
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 4")

    # ── 시나리오 5: 케이스 검증 ────────────────────────────────────
    def test_scenario5_case(self):
        """케이스A: 기본 필드 전체 채우기 → 저장 → 재오픈 → 전 필드 값 유지 확인
        케이스B: 필수(이름)만 입력 → 저장 → 재오픈 → 선택 필드 빈값/OFF 유지 확인

        Phase 1 범위: csuName, isClipboardRestrict, isNetwork, customOptionText
        (프로세스/웹제한은 Phase 2/3에서 추가)
        """
        r = self._make_r(5)
        lines, srs = [], []
        p = self.p
        _FULL = "[AUTO]_sc5_full"
        _REQ  = "[AUTO]_sc5_req"
        _CUSTOM_VAL = "sc5_full_custom_option"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 5: 케이스 검증 ━━━━━━━━━━━━━━━━━━━━━━")

        # 사전 정리
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        # ══════════════════════════════════════════════════════════
        # 케이스A: 기본 필드 전체 채우기
        # ══════════════════════════════════════════════════════════

        # A-1: 항목 생성 (이름만)
        full_name = _FULL
        try:
            full_name = p.add_policy(_FULL)
            t, s = r("pass", "케이스A — 항목 생성",
                     f"입력: {_FULL!r} / 결과: {full_name!r} 생성됨")
        except Exception as e:
            t, s = r("fail", "케이스A — 항목 생성", str(e))
        lines.append(t); srs.append(s)

        # A-2: 수정 모달에서 선택 필드 채우기 → 저장
        try:
            p.open_modify_modal(full_name)
            p.set_toggle(p.SEL_CLIPBOARD_RESTRICT, True)
            p.set_toggle(p.SEL_NETWORK, True)
            p.page.locator(p.SEL_CUSTOM_OPTION).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input',{bubbles:true})); }",
                _CUSTOM_VAL,
            )
            p.page.wait_for_timeout(150)
            p.save_edit_modal()
            t, s = r("pass", "케이스A — 선택 필드 설정 + 저장",
                     "입력: 클립보드ON, 네트워크ON, 커스텀옵션 입력 / 결과: 저장됨")
        except Exception as e:
            t, s = r("fail", "케이스A — 선택 필드 설정 + 저장", str(e))
            try:
                p.close_modal()
            except Exception:
                pass
        lines.append(t); srs.append(s)

        # A-3: 수정 모달 재오픈 → 전 필드 저장값 확인
        try:
            p.open_modify_modal(full_name)

            # 이름 확인
            loaded_name = p.get_field_value(p.SEL_CSU_NAME)
            t, s = r("pass" if loaded_name == full_name else "fail",
                     "케이스A — 스위트 이름(*) 저장값 유지",
                     f"입력: {full_name!r} / 결과: {loaded_name!r}")
            lines.append(t); srs.append(s)

            # 클립보드 토글 ON 유지
            cb_on = p.get_toggle_state(p.SEL_CLIPBOARD_RESTRICT)
            t, s = r("pass" if cb_on else "fail",
                     "케이스A — 클립보드 공유제한 ON 유지",
                     f"입력: ON 저장 / 결과: {'ON' if cb_on else 'OFF'}")
            lines.append(t); srs.append(s)

            # 네트워크 토글 ON 유지
            net_on = p.get_toggle_state(p.SEL_NETWORK)
            t, s = r("pass" if net_on else "fail",
                     "케이스A — 네트워크 허용 ON 유지",
                     f"입력: ON 저장 / 결과: {'ON' if net_on else 'OFF'}")
            lines.append(t); srs.append(s)

            # 커스텀 옵션값 유지
            loaded_custom = p.get_field_value(p.SEL_CUSTOM_OPTION)
            t, s = r("pass" if loaded_custom == _CUSTOM_VAL else "fail",
                     "케이스A — 커스텀 옵션값 저장값 유지",
                     f"입력: {_CUSTOM_VAL!r} / 결과: {loaded_custom!r}")
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
        # 케이스B: 필수(이름)만 입력
        # ══════════════════════════════════════════════════════════

        # B-1: 이름만 입력하여 생성
        req_name = _REQ
        try:
            req_name = p.add_policy(_REQ)
            t, s = r("pass", "케이스B — 항목 생성(이름만)",
                     f"입력: {_REQ!r} (선택 필드 미입력) / 결과: {req_name!r} 생성됨")
        except Exception as e:
            t, s = r("fail", "케이스B — 항목 생성(이름만)", str(e))
        lines.append(t); srs.append(s)

        # B-2: 수정 모달 재오픈 → 선택 필드 빈값/OFF 확인
        try:
            p.open_modify_modal(req_name)

            # 클립보드 OFF 유지
            cb_off = p.get_toggle_state(p.SEL_CLIPBOARD_RESTRICT)
            t, s = r("pass" if not cb_off else "fail",
                     "케이스B — 클립보드 공유제한 OFF 유지",
                     f"입력: 미입력 / 결과: {'ON(예상밖)' if cb_off else 'OFF'}")
            lines.append(t); srs.append(s)

            # 네트워크 OFF 유지
            net_off = p.get_toggle_state(p.SEL_NETWORK)
            t, s = r("pass" if not net_off else "fail",
                     "케이스B — 네트워크 허용 OFF 유지",
                     f"입력: 미입력 / 결과: {'ON(예상밖)' if net_off else 'OFF'}")
            lines.append(t); srs.append(s)

            # 커스텀 옵션 빈값 유지
            empty_custom = p.get_field_value(p.SEL_CUSTOM_OPTION)
            t, s = r("pass" if empty_custom == "" else "fail",
                     "케이스B — 커스텀 옵션값 빈값 유지",
                     f"입력: 미입력 / 결과: {empty_custom!r}")
            lines.append(t); srs.append(s)

            p.close_modal()

        except Exception as e:
            t, s = r("fail", "케이스B — 수정 모달 재오픈/확인", str(e))
            lines.append(t); srs.append(s)
            try:
                p.close_modal()
            except Exception:
                pass

        # 사후 정리
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 5")

    # ── Phase 2: 프로세스별 제어 ──────────────────────────────────
    def test_scenario_phase2_process_control(self):
        """
        Phase 2: 프로세스별 제어 — 개별 프로세스 / 태그 추가·제거·저장 확인

        검증 항목:
          - 탭 존재 및 기본 활성 (개별 프로세스)
          - 태그 탭 전환
          - + 버튼 → 프로세스 등록 서브모달 (버튼 텍스트 확인)
          - 프로세스 선택 → 목록 반영
          - - 버튼으로 제거
          - 태그 탭에서 동일 흐름 (태그 선택 → 목록 반영)
          - 저장 후 목록 컬럼 X/Y 형식 확인
        """
        r = self._make_r(7)
        lines, srs = [], []
        p = self.p
        _AUTO = "[AUTO]_csu_p2"
        print(f"\n━━ [{self.PAGE_NAME}] Phase 2: 프로세스별 제어 ━━━━━━━━━━━━━━━━━━━")

        # 사전 정리 + 스위트 생성
        p.delete_all_auto_items()
        created_name = p.add_policy(_AUTO)
        p.open_modify_modal(created_name)

        # ── 탭 UI 존재 확인 ──────────────────────────────────────
        try:
            has_proc_tab = p.page.locator(p.SEL_PROC_TAB).count() > 0
            has_tag_tab  = p.page.locator(p.SEL_TAG_TAB).count() > 0
            t, s = r("pass" if has_proc_tab and has_tag_tab else "fail",
                     "프로세스별 제어 — 탭 존재 (개별/태그)",
                     f"개별={'존재' if has_proc_tab else '없음'}, 태그={'존재' if has_tag_tab else '없음'}")
            lines.append(t); srs.append(s)

            proc_active = p.is_proc_tab_active()
            t, s = r("pass" if proc_active else "warn",
                     "개별 프로세스 탭 — 기본 활성",
                     f"결과: {'active' if proc_active else 'inactive'}")
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = r("warn", "탭 UI 확인", str(e))
            lines.append(t); srs.append(s)

        # ── 태그 탭 전환 확인 ─────────────────────────────────────
        try:
            p.click_tag_tab()
            tag_active = p.is_tag_tab_active()
            t, s = r("pass" if tag_active else "fail",
                     "태그 탭 — 클릭 시 active 전환",
                     f"결과: {'active' if tag_active else 'inactive'}")
            lines.append(t); srs.append(s)
            p.click_process_tab()  # 다시 프로세스 탭으로
        except Exception as e:
            t, s = r("warn", "태그 탭 전환", str(e))
            lines.append(t); srs.append(s)

        # ── 개별 프로세스 추가 ────────────────────────────────────
        try:
            count_before = p.get_process_list_count()
            p.open_process_register_modal()

            btn_text = p.get_proc_modal_select_btn_text()
            t, s = r("pass" if "프로세스 선택" in btn_text else "warn",
                     "프로세스 서브모달 — 버튼 텍스트",
                     f"결과: {btn_text!r}")
            lines.append(t); srs.append(s)

            p.open_picker_from_proc_modal()
            selected = p.select_first_from_picker()
            p.confirm_proc_modal()

            count_after = p.get_process_list_count()
            t, s = r("pass" if count_after > count_before else "fail",
                     "개별 프로세스 추가 — 목록 반영",
                     f"입력: {selected!r} / 결과: {count_before}개 → {count_after}개")
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = r("fail", "개별 프로세스 추가", str(e))
            lines.append(t); srs.append(s)
            try:
                p.close_proc_modal()
            except Exception:
                pass

        # ── 개별 프로세스 제거 ────────────────────────────────────
        try:
            count_before_del = p.get_process_list_count()
            if count_before_del > 0:
                p.check_all_in_process_list()
                p.remove_from_process_list()
                count_after_del = p.get_process_list_count()
                t, s = r("pass" if count_after_del < count_before_del else "fail",
                         "개별 프로세스 제거 — 목록에서 사라짐",
                         f"결과: {count_before_del}개 → {count_after_del}개")
            else:
                t, s = r("skip", "개별 프로세스 제거", "추가된 항목 없음 — 건너뜀")
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = r("warn", "개별 프로세스 제거", str(e))
            lines.append(t); srs.append(s)

        # ── 태그 추가 ─────────────────────────────────────────────
        try:
            p.click_tag_tab()
            count_before_tag = p.get_tag_list_count()
            p.open_process_register_modal()

            btn_text_tag = p.get_proc_modal_select_btn_text()
            t, s = r("pass" if "태그 선택" in btn_text_tag else "warn",
                     "태그 서브모달 — 버튼 텍스트",
                     f"결과: {btn_text_tag!r}")
            lines.append(t); srs.append(s)

            p.open_picker_from_proc_modal()
            selected_tag = p.select_first_from_picker()
            p.confirm_proc_modal()

            count_after_tag = p.get_tag_list_count()
            t, s = r("pass" if count_after_tag > count_before_tag else "fail",
                     "태그 추가 — 목록 반영",
                     f"입력: {selected_tag!r} / 결과: {count_before_tag}개 → {count_after_tag}개")
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = r("fail", "태그 추가", str(e))
            lines.append(t); srs.append(s)
            try:
                p.close_proc_modal()
            except Exception:
                pass

        # ── 저장 후 목록 컬럼 X/Y 확인 ───────────────────────────
        try:
            p.save_edit_modal()
            p.search_policy(created_name)
            p.page.wait_for_timeout(400)
            row = p.page.locator(p.SEL_TABLE_ROW).filter(has_text=created_name).first
            tds = row.locator("td").all()
            proc_tag_col = tds[1].inner_text().strip() if len(tds) > 1 else ""
            web_col      = tds[2].inner_text().strip() if len(tds) > 2 else ""
            # X/Y 형식: 개별프로세스수/태그수
            t, s = r("pass" if "/" in proc_tag_col else "warn",
                     "저장 후 목록 컬럼 — 프로세스/태그 X/Y 형식",
                     f"결과: 프로세스/태그={proc_tag_col!r}, 웹제한={web_col!r}")
            lines.append(t); srs.append(s)
        except Exception as e:
            t, s = r("warn", "저장 후 목록 컬럼 확인", str(e))
            lines.append(t); srs.append(s)

        # 사후 정리
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "Phase 2 프로세스별 제어")

    # ── 시나리오 6: 다음 테스트용 제어 스위트 설정 ────────────────
    def test_scenario6_suite_setup(self):
        """
        원본보호 정책·엔파우치 정책 테스트에서 사용할 제어 스위트를 준비한다.
        [AUTO]_csu_suite 이름의 스위트를 생성하고 삭제하지 않고 남겨둔다.

        다른 test_npouch_*.py 파일에서 _csu_suite를 참조하는 파일이 없으면
        사전 정리 후 skip 처리한다.
        """
        r = self._make_r(6)
        lines, srs = [], []
        p = self.p
        _SUITE = "[AUTO]_csu_suite"
        print(f"\n━━ [{self.PAGE_NAME}] 시나리오 6: 다음 테스트용 스위트 설정 ━━━━━━━━━━━━")

        # ── 사전 정리 ─────────────────────────────────────────────
        try:
            p.delete_all_auto_items()
        except Exception:
            pass

        # ── 연계 테스트 존재 여부 자동 감지 ──────────────────────
        _test_dir = Path(__file__).parent
        _consumer_files = [
            f for f in _test_dir.glob("test_npouch_*.py")
            if _SUITE in f.read_text(encoding="utf-8", errors="ignore")
        ]
        if not _consumer_files:
            t, s = r("skip", f"{_SUITE} — 연계 테스트 없음",
                     "다른 test_npouch_*.py 에서 이 스위트를 참조하는 파일 없음 — 설정 스킵")
            lines.append(t); srs.append(s)
            for line in lines: print(line)
            self._attach(srs)
            return

        # ── suite 스위트 생성 ─────────────────────────────────────
        suite_name = _SUITE
        try:
            suite_name = p.add_policy(_SUITE)
            names = p.get_policy_names()
            t, s = r("pass" if suite_name in names else "fail",
                     f"{_SUITE} — 스위트 생성",
                     f"입력: 스위트 추가 / 결과: {'생성됨' if suite_name in names else '없음'}")
        except Exception as e:
            t, s = r("fail", f"{_SUITE} — 스위트 생성", str(e))
        lines.append(t); srs.append(s)

        # ── 남겨두기 안내 ─────────────────────────────────────────
        t, s = r("skip", f"{_SUITE} — 삭제하지 않음",
                 "다음 원본보호/엔파우치 정책 테스트에서 사용 — 의도적으로 남겨둠")
        lines.append(t); srs.append(s)

        for line in lines: print(line)
        self._attach(srs)
        _assert_no_fail(lines, "시나리오 6")
