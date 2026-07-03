"""운용 프로세스 — 시나리오 2: 입력 구조 (재구성 2026-07-03).

2a — ADD 모달 제목/버튼 텍스트
2b — 전 필드 존재/초기값/DOM maxlength (요소별)
2c — 이름 빈값 제출 경고(필수검증 — sc4g 수정판과 merge)
2d — 취소 후 재오픈 초기화
※ 오류탐지류(중복/포맷/특수문자/글자수 스캔)는 sc3 소관으로 이동(2026-07-03, 특수폴더 분할 기준).
"""
from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase


class TestOperationProcessScenario2Input(OperationProcessBase):
    """운용 프로세스 — 시나리오 2: 입력 구조."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario2a_modal_title_buttons(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc2a: 모달 제목/버튼 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.open_add_modal()
        title = p.get_modal_title()
        self._add("pass" if "추가" in title else "warn", "sc2a — 모달 제목",
                  f"결과: 제목={title!r}", sc=2)
        submit_text = p.page.locator(p.SEL_SUBMIT_BTN).first.inner_text().strip()
        cancel_text = p.page.locator(p.SEL_CANCEL_BTN).first.inner_text().strip()
        for txt, expected, label in [(submit_text, "추가", "제출 버튼 텍스트"),
                                     (cancel_text, "취소", "취소 버튼 텍스트")]:
            self._add("pass" if txt == expected else "warn", f"sc2a — {label}",
                      f"결과: {txt!r}(기대 {expected!r})", sc=2)
        p.close_modal()

    def test_scenario2b_fields_inventory(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc2b: 필드 존재/초기값/maxlength ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.open_add_modal()
        for sel, label in [
            (p.SEL_PROCESS_NAME, "프로세스 이름(*)"),
            (p.SEL_SIGN,         "서명"),
            (p.SEL_SHA2,         "SHA2"),
            (p.SEL_EXEC_PATH,    "실행경로"),
            (p.SEL_DESCRIPTION,  "설명"),
        ]:
            exists = p.page.locator(sel).count() > 0
            self._add("pass" if exists else "fail", f"sc2b — {label} 필드 존재",
                      f"결과: {'존재' if exists else '없음'}", sc=2)
            if not exists:
                continue
            val = p.get_field_value(sel)
            self._add("pass" if val == "" else "warn", f"sc2b — {label} 초기값",
                      f"결과: {val!r}(기대 빈값)", sc=2)
            ml = p.page.locator(sel).first.get_attribute("maxlength")
            self._add("pass", f"sc2b — {label} DOM maxlength",
                      f"결과: {ml!r}" + (" (client 제한 없음 — 길이 검증은 sc3h 글자수 스캔 참조)" if ml is None else ""),
                      sc=2)
        p.close_modal()

    def test_scenario2c_required_empty(self, logged_in_page, settings):
        """이름(유일한 필수) 빈값 제출 → 경고. 같은 결과의 sc4g(수정 컨텍스트 비움)와 merge."""
        print("\n━━ [운용 프로세스] sc2c: 이름 빈값 제출 경고 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.open_add_modal()
        p.try_submit()
        p.page.wait_for_timeout(500)
        if p.is_confirm_modal_visible():
            msg = p.get_modal_message()
            expected = "프로세스 이름을 입력해 주세요."
            ok = msg == expected
            self._add("pass" if ok else "warn", "sc2c — 이름 빈값 제출 경고",
                      f"입력: 이름 비운 채 제출 / 결과: {msg!r}(기대 {expected!r})", sc=2,
                      merge_key=f"cm_req_empty::프로세스이름::{'blocked' if ok else 'unclear'}",
                      highlight=(None if ok else p.page.locator(p.SEL_CONFIRM_MODAL)))
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        else:
            self._add("fail", "sc2c — 이름 빈값 제출 경고", "에러 모달 미표시", sc=2,
                      merge_key="cm_req_empty::프로세스이름::not_blocked")
        p.close_modal()

    def test_scenario2d_cancel_resets(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc2d: 취소 후 재오픈 초기화 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.open_add_modal()
        p.fill(p.SEL_PROCESS_NAME, "[AUTO]_cancel_field_test")
        p.close_modal()
        p.open_add_modal()
        leftover = p.get_field_value(p.SEL_PROCESS_NAME)
        ok = leftover == ""
        self._add("pass" if ok else "warn", "sc2d — 취소 후 재오픈 시 필드 초기화",
                  f"입력: 이름 입력 후 취소 → 재오픈 / 결과: {leftover!r}(기대 빈값)", sc=2,
                  highlight=(None if ok else p.page.locator(p.SEL_PROCESS_NAME)),
                  repro="1. 추가 모달 이름 입력\n2. 취소\n3. 재오픈 → 빈값 확인")
        p.close_modal()
