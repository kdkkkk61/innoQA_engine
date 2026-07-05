"""태그 관리 — 시나리오 5: lifecycle (재구성 2026-07-03).

5a — 케이스A(이름+설명+프로세스 1개): 저장 → 재오픈 요소별 + 속성 모달 표시 요소별(등록 프로세스 포함)
5b — 케이스B(필수만=이름): 선택 필드 빈값 유지 + 카운트 0 + 속성 모달
5c — 되돌리기(설명 값→비움): 재오픈 잔존 확인 — '값→빈값 silent 무시' 버그 클래스, fail 시 리턴 재생
5d — 삭제 검증(단건 → 사라짐) + [AUTO] 휘발성 일괄 cleanup (날짜본·KEEP 보존)
"""
from pages.npouch_tag_page import NpouchTagPage
from tests.common.tag._base import TagBase

_FULL = "[AUTO]_cm_tag_full"
_REQ  = "[AUTO]_cm_tag_req"
_DESC_FULL = "full_case_tag_desc"


class TestTagScenario5Lifecycle(TagBase):
    """태그 관리 — 시나리오 5: lifecycle."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchTagPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario5a_full_case(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc5a: 케이스A 전체 필드 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _FULL in p.get_item_names():   # 재실행 잔존 가드(정상 흐름에선 발동 안 함)
            p.delete_item(_FULL)
        p.add_item_with_desc(_FULL, _DESC_FULL)
        proc = p.register_first_process(_FULL)
        p.ensure_auto_filter()
        exists = _FULL in p.get_item_names()
        self._add("pass" if exists else "fail", "sc5a — 케이스A(이름+설명+프로세스) 저장",
                  f"입력: {_FULL!r} + 설명 + 프로세스({proc!r}) / 결과: {'목록에 존재' if exists else '없음'}", sc=5)
        if not exists:
            return
        # ① 재오픈 — 요소별
        p.open_modify_modal(_FULL)
        for sel, label, expected in [
            (p.SEL_TAG_NAME,    "태그 이름", _FULL),
            (p.SEL_DESCRIPTION, "설명",      _DESC_FULL),
        ]:
            loaded = p.get_field_value(sel)
            ok = loaded == expected
            self._add("pass" if ok else "fail", f"sc5a — 재오픈: {label}",
                      f"입력: {expected!r} / 결과: {loaded!r}", sc=5,
                      highlight=(None if ok else p.page.locator(sel)))
        regs = p.get_registered_process_names()
        self._add("pass" if proc in regs else "fail", "sc5a — 재오픈: 등록 프로세스",
                  f"입력: {proc!r} 등록 / 결과: {'유지' if proc in regs else '사라짐'} (목록={regs})", sc=5,
                  highlight=(None if proc in regs else p.page.locator("div#addItemModal table")))
        p.close_modal()
        # ② 속성 모달 표시 — 요소별 (행 가운데 더블클릭)
        try:
            p.open_detail_modal(_FULL)
            dtext = p.detail_modal_text()
            for label, expected in [("태그 이름", _FULL), ("설명", _DESC_FULL)]:
                shown = expected in dtext
                self._add("pass" if shown else "warn", f"sc5a — 속성 모달 표시: {label}",
                          f"입력: {expected!r} / 결과: {'표시' if shown else '속성 모달에 없음'}", sc=5)
            det_regs = p.detail_registered_process_names()
            self._add("pass" if proc in det_regs else "warn", "sc5a — 속성 모달 표시: 등록 프로세스",
                      f"입력: {proc!r} / 결과: {'표시' if proc in det_regs else '없음'} (목록={det_regs})", sc=5)
            p.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc5a — 속성 모달 표시 검증", f"예외: {e!r}", sc=5)

    def test_scenario5b_required_case(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc5b: 케이스B 필수만 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _REQ in p.get_item_names():   # 재실행 잔존 가드
            p.delete_item(_REQ)
        p.add_item(_REQ)   # 이름만
        p.ensure_auto_filter()
        exists = _REQ in p.get_item_names()
        self._add("pass" if exists else "fail", "sc5b — 케이스B 필수만 저장",
                  f"입력: {_REQ!r} 이름만 / 결과: {'목록에 존재' if exists else '없음'}", sc=5)
        if not exists:
            return
        p.open_modify_modal(_REQ)
        name_loaded = p.get_field_value(p.SEL_TAG_NAME)
        self._add("pass" if name_loaded == _REQ else "fail", "sc5b — 재오픈: 태그 이름",
                  f"입력: {_REQ!r} / 결과: {name_loaded!r}", sc=5)
        desc = p.get_field_value(p.SEL_DESCRIPTION)
        self._add("pass" if desc.strip() == "" else "warn", "sc5b — 재오픈: 설명(선택) 빈값 유지",
                  f"입력: 미입력 / 결과: {desc!r}", sc=5,
                  highlight=(None if desc.strip() == "" else p.page.locator(p.SEL_DESCRIPTION)))
        regs = p.get_registered_process_names()
        self._add("pass" if not regs else "warn", "sc5b — 재오픈: 등록 프로세스 없음 유지",
                  f"결과: {len(regs)}개" + (f" — {regs}" if regs else ""), sc=5)
        p.close_modal()
        p.ensure_auto_filter()
        cnt = p.get_process_count_in_list(_REQ)
        self._add("pass" if cnt == 0 else "warn", "sc5b — 행 표시: 카운트 0",
                  f"결과: 카운트={cnt}", sc=5)

    def test_scenario5c_clear_desc(self, logged_in_page, settings):
        """되돌리기: 설명 값→비움 수정 → 재오픈 잔존 확인 ('silent 무시' 버그 클래스).
        fail 시 리턴 재생 스토리(지움→저장→재오픈 잔존) 큐레이션."""
        print("\n━━ [태그 관리] sc5c: 설명 값→비움 되돌리기 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _FULL not in p.get_item_names():
            p.add_item_with_desc(_FULL, _DESC_FULL)
        p.open_modify_modal(_FULL)
        p.page.locator(p.SEL_DESCRIPTION).first.fill("")
        p.page.wait_for_timeout(150)
        p.click_attached(p.SEL_SUBMIT_BTN)
        p._handle_confirm_modal()
        p.wait_for(p.SEL_ADD_BTN)
        p.ensure_auto_filter()
        p.open_modify_modal(_FULL)
        loaded = p.get_field_value(p.SEL_DESCRIPTION)
        cleared = loaded.strip() == ""
        if cleared:
            p.close_modal()
            self._add("pass", "sc5c — 설명 값→비움 수정 반영",
                      "입력: 설명 비우고 저장 / 결과: 재오픈 빈값(정상 반영)", sc=5)
        else:
            p.close_modal()
            shots = self._replay_shots([
                ("설명 지움", lambda: (
                    p.open_modify_modal(_FULL),
                    p.page.locator(p.SEL_DESCRIPTION).first.fill("")), p.page.locator(p.SEL_DESCRIPTION)),
                ("저장", lambda: (
                    p.click_attached(p.SEL_SUBMIT_BTN),
                    p._handle_confirm_modal(),
                    p.wait_for(p.SEL_ADD_BTN),
                    p.ensure_auto_filter()), None),
                ("재오픈 — 설명 잔존(이슈)", lambda: p.open_modify_modal(_FULL),
                 p.page.locator(p.SEL_DESCRIPTION)),
            ])
            try:
                p.close_modal()
            except Exception:
                pass
            self._add("fail", "sc5c — 설명 값→비움 수정 silent 무시",
                      f"입력: 설명 비우고 저장(경고 없음) / 결과: 재오픈={loaded!r} 잔존 — "
                      "빈값 수정이 조용히 무시됨(특수폴더와 동일 버그 클래스)", sc=5,
                      screenshots=shots,
                      repro="1. 수정 모달 설명 전체 지움\n2. 저장(경고 없음)\n3. 재오픈 → 옛값 잔존")

    def test_scenario5d_delete_and_cleanup(self, logged_in_page, settings):
        """삭제 검증(단건) + [AUTO] 휘발성 일괄 cleanup — 날짜본·KEEP(연계) 보존."""
        print("\n━━ [태그 관리] sc5d: 삭제 검증 + cleanup ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _FULL not in p.get_item_names():
            p.add_item(_FULL)
        p.delete_item(_FULL)
        p.ensure_auto_filter()
        gone = _FULL not in p.get_item_names()
        self._add("pass" if gone else "fail", "sc5d — 단건 삭제 → 목록에서 사라짐",
                  f"입력: {_FULL!r} 삭제 / 결과: {'사라짐' if gone else '잔존'}", sc=5,
                  highlight=(None if gone else p.page.locator("table tbody")),
                  repro="1. 행 체크\n2. 삭제\n3. 확인 → 목록에서 제거")
        p.delete_all_auto_items()
        p.ensure_auto_filter()
        leftover = [n for n in p.get_item_names() if n.startswith("[AUTO]")]
        p._restore_page_size()
        self._add("pass" if not leftover else "warn", "sc5d — [AUTO] 휘발성 일괄 삭제(cleanup)",
                  f"결과: 잔여 {len(leftover)}개" + (f" — {leftover}" if leftover else " (날짜본·KEEP 보존)"),
                  sc=5, highlight=(None if not leftover else p.page.locator("table tbody")))
