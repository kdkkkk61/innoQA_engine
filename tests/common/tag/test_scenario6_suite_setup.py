"""태그 관리 — 시나리오 6: 연계 데이터 준비 + cross-page 검증 (재구성 2026-07-03).

체인: 프로세스 sc6([AUTO_<MMDD>]_cm_proc) → 태그 sc6(날짜본 태그에 등록) → 제어스위트가 사용.
6a — 날짜본 태그([AUTO_<MMDD>]_cm_tag) 생성/재사용 + 연계 프로세스(날짜본 우선, 레거시 KEEP fallback) 등록
6b — cross-page: 태그에 등록된 프로세스 삭제 시도 → 참조 잠금 차단 + 원본 보존 (삭제되면 결함)
6c — cross-page: 프로세스 속성 모달 '※사용처 확인'에 태그명 표시 (사용처 값 검증)
삭제하지 않고 종료 — 제어스위트/다음 run 이 사용. 날짜본 정리는 다음 run 시작 cleanup 담당.
"""
import time

from pages.npouch_operation_process_page import NpouchOperationProcessPage
from pages.npouch_tag_page import NpouchTagPage
from tests.common.tag._base import TagBase


class TestTagScenario6SuiteSetup(TagBase):
    """태그 관리 — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchTagPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario6a_dated_handoff(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc6a: 연계 날짜본 태그 + 프로세스 등록 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        date = time.strftime("%m%d")
        dated_tag = f"[AUTO_{date}]_cm_tag"
        proc_candidates = [f"[AUTO_{date}]_cm_proc", "[AUTO_KEEP]_sc6_cm_proc_suite"]
        # 태그 — 같은 날 재실행은 재사용
        p.ensure_auto_filter()
        if dated_tag in p.get_item_names():
            self._add("pass", "sc6a — 연계 날짜본 태그 잔존 재사용",
                      f"입력: {dated_tag!r} 이미 존재 / 결과: 재사용", sc=6)
        else:
            p.add_item(dated_tag)
            p.ensure_auto_filter()
            exists = dated_tag in p.get_item_names()
            self._add("pass" if exists else "fail", "sc6a — 연계 날짜본 태그 생성",
                      f"입력: {dated_tag!r} 생성 / 결과: {'목록에 존재' if exists else '없음'}", sc=6)
            if not exists:
                return
        # 연계 프로세스 등록 — 날짜본 우선, 레거시 KEEP fallback
        registered = ""
        p.open_modify_modal(dated_tag)
        regs = p.get_registered_process_names()
        hit = next((c for c in proc_candidates if c in regs), None)
        if hit:
            registered = hit
            p.close_modal()
            self._add("pass", "sc6a — 연계 프로세스 이미 등록 — 재사용",
                      f"결과: {registered!r} 잔존 등록", sc=6)
        else:
            p.open_process_list_modal()
            for cand in proc_candidates:
                try:
                    registered = p.select_process_by_name(cand)
                    break
                except Exception:
                    continue
            if registered:
                p.confirm_process_selection()
                now = p.get_registered_process_names()
                ok = registered in now
                p.click_attached(p.SEL_SUBMIT_BTN)
                p._handle_confirm_modal()
                p.wait_for(p.SEL_ADD_BTN)
                self._add("pass" if ok else "fail", "sc6a — 연계 프로세스 등록",
                          f"입력: {registered!r} 선택 / 결과: {'등록됨' if ok else '등록 안됨'}", sc=6)
            else:
                p._close_modal_if_open()
                self._add("fail", "sc6a — 연계 프로세스 등록",
                          f"후보 미발견: {proc_candidates} — 프로세스 sc6 선행 필요", sc=6)
                return
        # 카운트 확인
        p.ensure_auto_filter()
        cnt = p.get_process_count_in_list(dated_tag)
        self._add("pass" if cnt >= 1 else "fail", "sc6a — 행 표시: 프로세스 카운트",
                  f"결과: {cnt}개", sc=6)
        self._request.node._suite_proc = registered   # 6b/6c 에서 사용
        TestTagScenario6SuiteSetup._SUITE_PROC = registered
        TestTagScenario6SuiteSetup._SUITE_TAG = dated_tag
        self._add("skip", "sc6a — 연계 데이터 남겨두기(삭제 안 함)",
                  f"{dated_tag!r} ← {registered!r} — 제어스위트/다음 run 사용 예정. "
                  "휘발성 정리는 sc5d, 날짜본 정리는 다음 run 시작 cleanup 담당.", sc=6,
                  screenshot=False)

    def test_scenario6b_cross_page_delete_block(self, logged_in_page, settings):
        """cross-page: 태그에 등록된 프로세스 삭제 시도 → 참조 잠금 차단 + 보존 (삭제되면 결함).
        ※ 검증만 — 사용처 제거(강제 삭제)는 여기서 안 함(연계 데이터 보존)."""
        print("\n━━ [태그 관리] sc6b: cross-page 프로세스 삭제 차단 ━━━")
        proc_name = getattr(TestTagScenario6SuiteSetup, "_SUITE_PROC", "")
        if not proc_name:
            self._add("skip", "sc6b — cross-page 삭제 차단", "sc6a 등록 실패로 skip", sc=6, screenshot=False)
            return
        pp = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = pp.page
        pp.navigate_to()
        pp.ensure_auto_filter()
        if proc_name not in pp.get_item_names():
            self._add("warn", "sc6b — cross-page 삭제 차단",
                      f"{proc_name!r} 프로세스 목록에 없음(선행 상태 확인 필요)", sc=6)
            return
        msg2 = pp._delete_checked_row(proc_name)
        blocked = ("할당" in msg2) or ("사용" in msg2) or ("참조" in msg2)
        shot = None
        if blocked:
            shot = self._shot("삭제차단_경고", caption=f"1. 삭제 시도 → 참조 잠금 차단 {msg2!r}")
        if msg2:
            pp.click_attached(pp.SEL_CONFIRM_BTN)
            pp.wait_for_confirm_modal_closed()
        pp.ensure_auto_filter()
        kept = proc_name in pp.get_item_names()
        st = "pass" if (blocked and kept) else ("fail" if not kept else "warn")
        self._add(st, "sc6b — 태그 등록 프로세스 삭제 차단(참조 잠금)",
                  f"입력: {proc_name!r} 삭제 시도 / 결과: 경고={msg2!r}, 보존={kept}"
                  + (" — 차단 정상(삭제되면 결함)" if st == "pass" else ""), sc=6,
                  screenshot=(st != "pass"), screenshots=[shot] if (shot and st == "pass") else None,
                  repro="1. 태그에 등록된 프로세스 행 체크\n2. 삭제 → 확인\n3. '할당' 차단 + 프로세스 보존")

    def test_scenario6c_cross_page_usage_display(self, logged_in_page, settings):
        """cross-page: 프로세스 속성 모달 '※사용처 확인'에 등록 태그명 표시 — 사용처 값 검증."""
        print("\n━━ [태그 관리] sc6c: cross-page 사용처 표시 ━━━")
        proc_name = getattr(TestTagScenario6SuiteSetup, "_SUITE_PROC", "")
        tag_name = getattr(TestTagScenario6SuiteSetup, "_SUITE_TAG", "")
        if not (proc_name and tag_name):
            self._add("skip", "sc6c — cross-page 사용처 표시", "sc6a 등록 실패로 skip", sc=6, screenshot=False)
            return
        pp = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = pp.page
        pp.navigate_to()
        pp.ensure_auto_filter()
        try:
            pp.open_detail_modal(proc_name)
            dtext = pp.detail_modal_text()
            shown = tag_name in dtext
            has_section = "사용처" in dtext
            self._add("pass" if shown else "fail", "sc6c — 프로세스 사용처에 태그명 표시",
                      f"입력: {tag_name!r} 에 등록된 {proc_name!r} 속성 열람 / "
                      f"결과: 사용처 섹션={has_section}, 태그명 표시={shown}", sc=6,
                      repro="1. 프로세스 행 가운데 더블클릭(속성)\n2. ※사용처 확인 → '태그 관리'에 태그명 chip")
            pp.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc6c — 프로세스 사용처 표시 검증", f"예외: {e!r}", sc=6)
