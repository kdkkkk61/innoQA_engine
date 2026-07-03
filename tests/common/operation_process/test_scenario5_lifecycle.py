"""운용 프로세스 — 시나리오 5: lifecycle (재구성 2026-07-03, 기존 sc5 이관 + 보강).

5a — 케이스A(전체 필드): 저장 → 재오픈 요소별 + 속성 모달 표시 요소별(신규 계층)
5b — 케이스B(필수만): 저장 → 선택 필드 빈값 유지 요소별 + 속성 모달
5c — 되돌리기(값→비움): 서명/실행경로/설명 비움 수정 → 재오픈 잔존 확인
     (특수폴더 sc5c 에서 확정된 '값→빈값 silent 무시' 제품 버그 클래스 — fail 시 리턴 재생 스토리)
5d — 삭제 검증(단건 → 사라짐, sc3 에서 이동: 삭제=sc1/5 소관) + [AUTO] 휘발성 일괄 cleanup (AUTO_KEEP 보존)
"""
from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase

_FULL = "[AUTO]_cm_proc_full"
_REQ  = "[AUTO]_cm_proc_req"
_SHA2_VALID = "AABB112233445566778899001122334455667788990011223344556677889900"
_SIGN_FULL = "auto_sign_full"
_EXEC_FULL = r"C:\auto\proc_full.exe"
_DESC_FULL = "full_case_auto_desc"


class TestOperationProcessScenario5Lifecycle(OperationProcessBase):
    """운용 프로세스 — 시나리오 5: lifecycle."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario5a_full_case(self, logged_in_page, settings):
        """케이스A: 전체 필드 저장 → 재오픈(요소별) + 속성 모달 표시(요소별)."""
        print("\n━━ [운용 프로세스] sc5a: 케이스A 전체 필드 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _FULL in p.get_item_names():   # 재실행 잔존 가드(정상 흐름에선 발동 안 함)
            p.delete_item(_FULL)
        p.add_item(_FULL, sha2=_SHA2_VALID, sign=_SIGN_FULL,
                   exec_path=_EXEC_FULL, description=_DESC_FULL)
        p.ensure_auto_filter()
        exists = _FULL in p.get_item_names()
        self._add("pass" if exists else "fail", "sc5a — 케이스A 전체 채우기 저장",
                  f"입력: 전체 필드(이름+서명+SHA2+실행경로+설명) / 결과: {'목록에 존재' if exists else '없음'}", sc=5)
        if not exists:
            return
        # ① 재오픈 — 요소별
        p.open_modify_modal(_FULL)
        for sel, label, expected in [
            (p.SEL_PROCESS_NAME, "프로세스 이름", _FULL),
            (p.SEL_SIGN,         "서명",          _SIGN_FULL),
            (p.SEL_EXEC_PATH,    "실행경로",       _EXEC_FULL),
            (p.SEL_DESCRIPTION,  "설명",          _DESC_FULL),
        ]:
            loaded = p.get_field_value(sel)
            ok = loaded == expected
            self._add("pass" if ok else "fail", f"sc5a — 재오픈: {label}",
                      f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=5,
                      highlight=(None if ok else p.page.locator(sel)))
        sha2 = p.get_field_value(p.SEL_SHA2)
        self._add("pass" if sha2.strip() else "fail", "sc5a — 재오픈: SHA2",
                  f"결과: {sha2[:20]!r}{'...' if len(sha2) > 20 else ''}", sc=5,
                  highlight=(None if sha2.strip() else p.page.locator(p.SEL_SHA2)))
        p.close_modal()
        # ② 속성 모달 표시 — 요소별 (신규 계층, 행 가운데 더블클릭 실측 2026-07-03)
        try:
            p.open_detail_modal(_FULL)
            dtext = p.detail_modal_text()
            for label, expected in [
                ("프로세스 이름", _FULL), ("서명", _SIGN_FULL),
                ("실행경로", _EXEC_FULL), ("설명", _DESC_FULL),
                ("SHA2", _SHA2_VALID),
            ]:
                shown = expected in dtext
                self._add("pass" if shown else "warn", f"sc5a — 속성 모달 표시: {label}",
                          f"입력: {expected[:30]!r} / 결과: {'표시' if shown else '속성 모달에 없음'}", sc=5)
            p.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc5a — 속성 모달 표시 검증", f"예외: {e!r}", sc=5)

    def test_scenario5b_required_case(self, logged_in_page, settings):
        """케이스B: 필수만 저장 → 선택 필드 빈값 유지(요소별) + 속성 모달."""
        print("\n━━ [운용 프로세스] sc5b: 케이스B 필수만 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _REQ in p.get_item_names():   # 재실행 잔존 가드(정상 흐름에선 발동 안 함)
            p.delete_item(_REQ)
        p.add_item(_REQ)   # 이름만
        p.ensure_auto_filter()
        exists = _REQ in p.get_item_names()
        self._add("pass" if exists else "fail", "sc5b — 케이스B 필수만 저장",
                  f"입력: {_REQ!r} 이름만 / 결과: {'목록에 존재' if exists else '없음'}", sc=5)
        if not exists:
            return
        p.open_modify_modal(_REQ)
        name_loaded = p.get_field_value(p.SEL_PROCESS_NAME)
        self._add("pass" if name_loaded == _REQ else "fail", "sc5b — 재오픈: 프로세스 이름",
                  f"입력: {_REQ!r} / 결과: {name_loaded!r}", sc=5)
        for sel, label in [
            (p.SEL_SIGN,        "서명"), (p.SEL_SHA2, "SHA2"),
            (p.SEL_EXEC_PATH,   "실행경로"), (p.SEL_DESCRIPTION, "설명"),
        ]:
            loaded = p.get_field_value(sel)
            ok = loaded.strip() == ""
            self._add("pass" if ok else "warn", f"sc5b — 재오픈: {label}(선택) 빈값 유지",
                      f"입력: 미입력 / 결과: {loaded!r}", sc=5,
                      highlight=(None if ok else p.page.locator(sel)))
        p.close_modal()
        # 속성 모달 — 이름 표시 + 열림 자체 확인 (빈 선택 필드는 표시값 없음이 정상)
        try:
            p.open_detail_modal(_REQ)
            dtext = p.detail_modal_text()
            self._add("pass" if _REQ in dtext else "warn", "sc5b — 속성 모달: 이름 표시",
                      f"결과: {'표시' if _REQ in dtext else '없음'}", sc=5)
            p.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc5b — 속성 모달 검증", f"예외: {e!r}", sc=5)

    def test_scenario5c_clear_optional_fields(self, logged_in_page, settings):
        """되돌리기: 선택 필드 값→비움 수정 → 재오픈 잔존 확인 (요소별).

        특수폴더에서 확정된 '값→빈값 수정 silent 무시' 제품 버그 클래스의 이 페이지 검증.
        fail 시 리턴 재생 스토리(지움→저장→재오픈 잔존) 큐레이션.
        """
        print("\n━━ [운용 프로세스] sc5c: 선택 필드 값→비움 되돌리기 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _FULL not in p.get_item_names():
            p.add_item(_FULL, sha2=_SHA2_VALID, sign=_SIGN_FULL,
                       exec_path=_EXEC_FULL, description=_DESC_FULL)
        for sel, label in [
            (p.SEL_SIGN,        "서명"),
            (p.SEL_EXEC_PATH,   "실행경로"),
            (p.SEL_DESCRIPTION, "설명"),
        ]:
            p.open_modify_modal(_FULL)
            p.page.locator(sel).first.fill("")
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)
            p.ensure_auto_filter()
            p.open_modify_modal(_FULL)
            loaded = p.get_field_value(sel)
            cleared = loaded.strip() == ""
            if cleared:
                p.close_modal()
                self._add("pass", f"sc5c — {label} 값→비움 수정 반영",
                          f"입력: {label} 비우고 저장 / 결과: 재오픈 빈값(정상 반영)", sc=5)
            else:
                p.close_modal()
                # 리턴 재생 스토리: 지움 → 저장 → 재오픈 잔존(이슈 지점)
                shots = self._replay_shots([
                    (f"{label} 지움", lambda s_=sel: (
                        p.open_modify_modal(_FULL),
                        p.page.locator(s_).first.fill("")), p.page.locator(sel)),
                    ("저장", lambda: (
                        p.click_attached(p.SEL_SUBMIT_BTN),
                        p._handle_confirm_modal(),
                        p.wait_for(p.SEL_ADD_BTN),
                        p.ensure_auto_filter()), None),
                    (f"재오픈 — {label} 잔존(이슈)", lambda: p.open_modify_modal(_FULL),
                     p.page.locator(sel)),
                ])
                try:
                    p.close_modal()
                except Exception:
                    pass
                self._add("fail", f"sc5c — {label} 값→비움 수정 silent 무시",
                          f"입력: {label} 비우고 저장(경고 없음) / 결과: 재오픈={loaded!r} 잔존 — "
                          "빈값 수정이 조용히 무시됨(특수폴더와 동일 버그 클래스)", sc=5,
                          screenshots=shots,
                          repro=f"1. 수정 모달 {label} 전체 지움\n2. 저장(경고 없음)\n3. 재오픈 → 옛값 잔존")

    def test_scenario5d_delete_and_cleanup(self, logged_in_page, settings):
        """삭제 검증(단건, sc3 에서 이동) + [AUTO] 휘발성 일괄 cleanup — AUTO_KEEP(sc6 연계) 보존."""
        print("\n━━ [운용 프로세스] sc5d: 삭제 검증 + cleanup ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        # ① 단건 삭제 동작 검증 — sc5a~c 가 쓰던 _FULL 을 명시 삭제 → 목록에서 사라짐
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
        # ② 일괄 cleanup — 나머지 [AUTO] 휘발성 전부
        p.delete_all_auto_items()
        p.ensure_auto_filter()
        leftover = [n for n in p.get_item_names()
                    if n.startswith("[AUTO]")]
        p._restore_page_size()
        self._add("pass" if not leftover else "warn", "sc5d — [AUTO] 휘발성 일괄 삭제(cleanup)",
                  f"결과: 잔여 {len(leftover)}개" + (f" — {leftover}" if leftover else " (AUTO_KEEP 보존)"),
                  sc=5, highlight=(None if not leftover else p.page.locator("table tbody")))
