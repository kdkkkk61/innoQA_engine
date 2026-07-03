"""운용 프로세스 — 시나리오 3: 동작 검증 (재구성 2026-07-03, 오류탐지류 sc2→sc3 이동 반영).

3a — 미선택 수정/미체크 삭제 경고
3b — 추가(전체 필드) → 목록 + 리스트 컬럼 표시(요소별: 이름/서명/설명)
3c — 검색 옵션 4종(이름/서명/설명/없는항목 — 검색 기능 자체 검증이라 개별 검색 유지)
3d — 추가 후 전 필드 저장값 확인(수정 모달 로드, 요소별)
3e — 이름 특수문자(yaml special_char_tests — 차단 여부 + 저장 시 목록 등재, sc4f 수정판과 merge)
3f — 중복 이름 차단(notepad.exe 실데이터 — sc4e rename 중복과 merge)
3g — YAML 포맷 검증(format_validation_tests — 저장 시 재오픈 잔존 2컷 증거)
3h — 글자수 제한 스캔(요소별 + 오류 시 2컷 — sc4h 수정판과 같은 결과면 merge)
3i — 생성 검증 메시지 i18n 키 노출 전수(sweep 1카드 — sc4i 수정판과 merge)
※ 수정 동작은 sc4 소관, 삭제 동작은 sc5 소관(시나리오 책임 분리: 삭제=sc1 세션 cleanup/sc5).
※ sc3 생성분은 중간 삭제하지 않고 sc5d cleanup 이 일괄 정리 — '[AUTO' 필터 유지 흐름.
"""
import yaml
from pathlib import Path

from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase

_AUTO_PROCESS = "[AUTO]_cm_process"
_SHA2_VALID   = "AABB112233445566778899001122334455667788990011223344556677889900"
_EXEC_TEST    = r"C:\auto\test_proc.exe"
_SIGN_VAL     = "auto_sign_test"
_DESC_VAL     = "auto_desc_test"


def _load_hints(page_id: str) -> dict:
    path = Path(__file__).parent.parent.parent.parent / "config" / "scan_hints" / f"{page_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


class TestOperationProcessScenario3Action(OperationProcessBase):
    """운용 프로세스 — 시나리오 3: 동작 검증."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario3a_no_selection_warnings(self, logged_in_page, settings):
        """미선택 전제 보장 필수 — 선행 시나리오(sc1d 속성 모달)의 행 선택(tActive)이
        SPA 상태로 잔존해 '경고' 대신 수정 모달이 열리는 오탐 발생(리포트 #1, 2026-07-03) → reload 로 초기화."""
        print("\n━━ [운용 프로세스] sc3a: 미선택/미체크 경고 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.page.reload()          # 행 선택/상세 패널 잔존 제거 — 미선택 전제 보장
        p.navigate_to()
        for btn, expected, label in [
            ("button#modifyItemBtn", "선택된 항목이 없습니다.",  "수정 버튼 — 미선택 경고"),
            ("button#removeItemBtn", "삭제할 항목을 체크해 주세요.", "삭제 버튼 — 미체크 경고"),
        ]:
            p.page.locator(btn).first.evaluate("el => el.click()")
            p.page.wait_for_timeout(400)
            if p.is_confirm_modal_visible():
                msg = p.get_modal_message()
                self._add("pass" if msg == expected else "warn", f"sc3a — {label}",
                          f"결과: {msg!r}(기대 {expected!r})", sc=3)
                p.dismiss_confirm_modal()
                p.wait_for_confirm_modal_closed()
            elif p.page.locator(p.SEL_MODAL_OPEN).count() > 0:
                # 미선택인데 편집 모달이 열림 — 판정 지점(열린 모달) 캡처
                shot = self._shot(f"{label}_모달열림",
                                  caption="1. 미선택 상태에서 클릭 → 경고 대신 편집 모달 열림")
                self._add("warn", f"sc3a — {label}",
                          "경고 모달 대신 편집 모달이 열림 — 행 선택 상태 잔존 여부 확인 필요", sc=3,
                          screenshot=False, screenshots=[shot] if shot else None)
                p._close_modal_if_open()
            else:
                self._add("warn", f"sc3a — {label}", "에러 모달 없음", sc=3)

    def test_scenario3b_add_and_row_display(self, logged_in_page, settings):
        """전체 필드 추가 → 목록 등록 + 리스트 컬럼 표시(요소별 — 3점의 리스트 계층)."""
        print("\n━━ [운용 프로세스] sc3b: 추가 + 행 표시 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        # 중간 delete_all 금지 — sc1 세션 cleanup 이 clean slate 담당(sc3 단독 실행 시에만 여기서 1회 수행)
        self._ensure_session_cleanup(p)
        p.add_item(_AUTO_PROCESS, sha2=_SHA2_VALID, sign=_SIGN_VAL,
                   exec_path=_EXEC_TEST, description=_DESC_VAL)
        p.ensure_auto_filter()
        exists = _AUTO_PROCESS in p.get_item_names()
        self._add("pass" if exists else "fail", "sc3b — 항목 추가 → 목록 등록",
                  f"입력: {_AUTO_PROCESS!r} + 전체 필드 / 결과: {'존재' if exists else '없음'}", sc=3,
                  repro="1. 추가 모달 전체 필드 입력\n2. 추가\n3. 목록 등장")
        if not exists:
            return
        # 리스트 컬럼 표시 — 요소별 카드
        row_loc, cells = None, []
        for row in p.page.locator(p.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds and _AUTO_PROCESS in tds[0].inner_text():
                row_loc = row
                cells = [td.inner_text().strip() for td in tds]
                break
        for col_label, expected in [("이름", _AUTO_PROCESS), ("서명", _SIGN_VAL), ("설명", _DESC_VAL)]:
            found = expected in cells
            self._add("pass" if found else "warn", f"sc3b — 행 표시: {col_label} 컬럼",
                      f"입력: {expected!r} / 결과: {'표시' if found else '없음'} (행={cells})", sc=3,
                      highlight=(None if found else row_loc))

    def test_scenario3c_search_options(self, logged_in_page, settings):
        """검색 옵션별 동작 — 검색 기능 자체 검증이라 개별 검색 유지(필터 통일 예외)."""
        print("\n━━ [운용 프로세스] sc3c: 검색 옵션 4종 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        try:
            p.search_item_with_option(_AUTO_PROCESS, "프로세스 이름")
            self._add("pass" if _AUTO_PROCESS in p.get_item_names() else "fail",
                      "sc3c — 검색(프로세스 이름)", f"입력: {_AUTO_PROCESS!r}", sc=3)
            p.search_item_with_option(_SIGN_VAL, "서명")
            self._add("pass" if _AUTO_PROCESS in p.get_item_names() else "warn",
                      "sc3c — 검색(서명)", f"입력: {_SIGN_VAL!r}", sc=3)
            p.search_item_with_option(_DESC_VAL, "설명")
            self._add("pass" if _AUTO_PROCESS in p.get_item_names() else "warn",
                      "sc3c — 검색(설명)", f"입력: {_DESC_VAL!r}", sc=3)
            p.search_item_with_option("ZZZQANOTEXISTZZZTEST", "프로세스 이름")
            empty = p.get_item_names()
            self._add("pass" if not empty else "warn", "sc3c — 없는 항목 검색 → 빈 목록",
                      f"결과: {len(empty)}개" + (f" — {empty}" if empty else ""), sc=3,
                      highlight=(None if not empty else p.page.locator("table tbody")))
            p._restore_page_size()
        except Exception as e:
            self._add("warn", "sc3c — 검색 기능 테스트", str(e), sc=3)

    def test_scenario3d_saved_values(self, logged_in_page, settings):
        """추가 후 전 필드 저장값 확인 (수정 모달 로드, 요소별)."""
        print("\n━━ [운용 프로세스] sc3d: 저장값 확인 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _AUTO_PROCESS not in p.get_item_names():
            p.add_item(_AUTO_PROCESS, sha2=_SHA2_VALID, sign=_SIGN_VAL,
                       exec_path=_EXEC_TEST, description=_DESC_VAL)
        p.open_modify_modal(_AUTO_PROCESS)
        for sel, label, expected in [
            (p.SEL_PROCESS_NAME, "프로세스 이름", _AUTO_PROCESS),
            (p.SEL_SIGN,         "서명",          _SIGN_VAL),
            (p.SEL_EXEC_PATH,    "실행경로",       _EXEC_TEST),
            (p.SEL_DESCRIPTION,  "설명",          _DESC_VAL),
        ]:
            loaded = p.get_field_value(sel)
            ok = loaded == expected
            self._add("pass" if ok else "fail", f"sc3d — {label} 저장값 확인",
                      f"입력: {expected!r} / 결과: {loaded!r}", sc=3,
                      highlight=(None if ok else p.page.locator(sel)))
        sha2 = p.get_field_value(p.SEL_SHA2)
        self._add("pass" if sha2.strip() else "fail", "sc3d — SHA2 저장값 확인",
                  f"결과: {sha2[:20]!r}{'...' if len(sha2) > 20 else ''}", sc=3,
                  highlight=(None if sha2.strip() else p.page.locator(p.SEL_SHA2)))
        p.close_modal()

    def test_scenario3e_special_char_name(self, logged_in_page, settings):
        """이름 특수문자(yaml special_char_tests) — 차단 여부 + 저장 시 목록 등재.
        같은 결과의 sc4f(rename 특수문자)와 merge_key 로 결함 카드 묶음."""
        print("\n━━ [운용 프로세스] sc3e: 이름 특수문자(yaml) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        _hints = _load_hints(self.PAGE_ID)
        tests = _hints.get("special_char_tests", []) or [
            {"label": "프로세스 이름 — 특수문자 입력 차단 여부",
             "test_value": "[AUTO]_sc';!@#$", "expect_block": False}]
        for sc_test in tests:
            _label  = sc_test.get("label", "특수문자 테스트")
            _value  = sc_test.get("test_value", "")
            _expect = sc_test.get("expect_block", False)
            try:
                p.add_item(_value)   # 중간 삭제 없음 — sc5d cleanup 이 일괄 정리
                p.ensure_auto_filter()
                created = _value in p.get_item_names()
            except Exception:
                created = False
            cls = "allowed" if created else "blocked"
            status = ("pass" if not created else "warn") if _expect \
                else ("pass" if created else "warn")
            self._add(status, f"sc3e — {_label}",
                      f"입력: {_value!r} 추가 / 결과: {'저장·목록 등재(차단 없음)' if created else '차단됨'}",
                      sc=3, merge_key=f"cm_name_special::{cls}",
                      repro=f"1. 이름에 특수문자({_value!r})\n2. 추가\n3. 허용/차단 여부")

    def test_scenario3f_duplicate_name(self, logged_in_page, settings):
        """중복 이름 차단(notepad.exe — 시스템 상시 존재명, 읽기 전용).
        같은 결과의 sc4e(rename 중복)와 merge_key 로 묶음."""
        print("\n━━ [운용 프로세스] sc3f: 중복 이름 차단 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        try:
            p.open_add_modal()
            p.fill(p.SEL_PROCESS_NAME, "notepad.exe")
            p.try_submit()
            p.page.wait_for_timeout(600)
            if p.is_confirm_modal_visible():
                msg = p.get_modal_message()
                blocked = ("이미 등록된" in msg) or ("ALREADY" in msg.upper())
                self._add("pass" if blocked else "warn", "sc3f — 중복 이름 차단(생성)",
                          f"입력: 'notepad.exe'(기존 등록명) / 결과: {msg!r}", sc=3,
                          merge_key=f"cm_name_dup::{'blocked' if blocked else 'not_blocked'}",
                          highlight=(None if blocked else p.page.locator(p.SEL_CONFIRM_MODAL)))
                p.dismiss_confirm_modal()
                p.wait_for_confirm_modal_closed()
            else:
                self._add("warn", "sc3f — 중복 이름 차단(생성)",
                          "에러 모달 없음 (notepad.exe 미등록?)", sc=3,
                          merge_key="cm_name_dup::not_blocked")
        except Exception as e:
            self._add("warn", "sc3f — 중복 이름 차단(생성)", str(e), sc=3)
        p.close_modal()

    def test_scenario3g_format_validation(self, logged_in_page, settings):
        """YAML 기반 포맷 검증(format_validation_tests) — 서버가 형식을 검증하는지."""
        print("\n━━ [운용 프로세스] sc3g: 포맷 검증(yaml) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        _hints = _load_hints(self.PAGE_ID)
        from tests.common.operation_process._base import _SAVE_SUCCESS_KEYWORDS
        for fv in _hints.get("format_validation_tests", []):
            _fv_label     = fv.get("label", "포맷 검증 테스트")
            _fv_value     = fv.get("test_value", "INVALID")
            _fv_expect    = fv.get("expect_validation", True)
            _fv_field     = fv.get("field", "sha2")
            _fv_item_name = fv.get("item_name", f"[AUTO]_fv_{_fv_field}")
            _fv_sel = next((f["selector"] for f in _hints.get("fields", []) if f["id"] == _fv_field),
                           f"textarea#{_fv_field}")
            p.open_add_modal()
            p.fill(p.SEL_PROCESS_NAME, _fv_item_name)
            p.page.locator(_fv_sel).first.evaluate(
                "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); }", _fv_value)
            p.page.wait_for_timeout(200)
            # 판정 지점 증거 1컷: 제출 직전 잘못된 형식 입력 상태
            shot_input = self._shot(f"{_fv_field}_입력상태", highlight=p.page.locator(_fv_sel),
                                    caption=f"1. {_fv_field.upper()} 필드에 {_fv_value!r} 입력(잘못된 형식)")
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
            p._close_modal_if_open()
            shots, saved_val = None, ""
            if not actual_validated:
                # 판정 지점 증거 2컷: 저장 후 재오픈 — 잘못된 값이 그대로 저장된 장면
                try:
                    p.ensure_auto_filter()
                    p.open_modify_modal(_fv_item_name)
                    saved_val = p.get_field_value(_fv_sel)
                    shot_saved = self._shot(f"{_fv_field}_재오픈잔존", highlight=p.page.locator(_fv_sel),
                                            caption=f"2. 재오픈 — {saved_val!r} 그대로 저장됨(검증 부재 증거)")
                    p.close_modal()
                    shots = [s for s in (shot_input, shot_saved) if s] or None
                except Exception:
                    shots = [shot_input] if shot_input else None
            status_fv = ("pass" if actual_validated else "warn") if not _fv_expect \
                else ("pass" if actual_validated else "fail")
            self._add(status_fv, f"sc3g — {_fv_label}",
                      f"입력: {_fv_value!r} 제출 / 결과: "
                      + (f"검증됨(에러)" if actual_validated
                         else f"검증 없이 저장됨 — 재오픈 값={saved_val!r} (known issue)"),
                      sc=3, screenshot=False, screenshots=shots,
                      repro=f"1. 추가 모달 {_fv_field} 에 {_fv_value!r}\n2. 추가\n3. 재오픈 → 값 그대로면 검증 부재")
            # 저장분([AUTO]_fv_*)은 중간 삭제하지 않음 — sc5d cleanup 이 일괄 정리
            p._restore_page_size()

    def test_scenario3i_i18n_message_sweep(self, logged_in_page, settings):
        """생성 검증 메시지 전수 — raw i18n 키(COLUMN.NAME.* 류) 노출 없는지.
        카테고리 sweep 1카드(필드별 일회성 금지 원칙). sc4i(수정 컨텍스트)와 같은 결과면 merge."""
        print("\n━━ [운용 프로세스] sc3i: 생성 검증 메시지 i18n 전수 ━━━")
        import re as _re
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        _KEY = _re.compile(r"[A-Z][A-Z0-9]*(?:\.[A-Z0-9_]+)+")   # 예: COLUMN.NAME.WR_ALREADY_PROCESS
        collected, leak_shots = [], []
        for trig_label, name_value in [("이름 빈값 제출", ""), ("중복 이름 제출(notepad.exe)", "notepad.exe")]:
            try:
                p.open_add_modal()
                if name_value:
                    p.fill(p.SEL_PROCESS_NAME, name_value)
                p.try_submit()
                p.page.wait_for_timeout(600)
                msg = p.get_modal_message() if p.is_confirm_modal_visible() else "(경고 없음)"
                leaked = bool(_KEY.search(msg))
                collected.append((trig_label, msg, leaked))
                if leaked and p.is_confirm_modal_visible():
                    s = self._shot(f"i18n_{trig_label}",
                                   caption=f"{len(leak_shots) + 1}. {trig_label} → raw i18n 키 노출: {msg!r}")
                    if s:
                        leak_shots.append(s)
                if p.is_confirm_modal_visible():
                    p.dismiss_confirm_modal()
                    p.wait_for_confirm_modal_closed()
            except Exception as e:
                collected.append((trig_label, f"(예외: {e!r})", False))
            finally:
                p._close_modal_if_open()
        leaks = sorted({_KEY.search(m).group(0) for _, m, lk in collected if lk})
        detail = " / ".join(f"{t}→{m!r}" for t, m, _ in collected)
        self._add("warn" if leaks else "pass", "sc3i — 생성 검증 메시지 i18n 키 노출 전수",
                  (f"raw i18n 키 노출: {leaks} — " if leaks else "노출 없음(깨끗한 한글) — ") + detail,
                  sc=3, screenshot=False, screenshots=leak_shots or None,
                  merge_key=f"cm_i18n::{','.join(leaks) or 'clean'}",
                  repro="1. 검증 경고 유발(빈값/중복)\n2. 메시지에 COLUMN.* 류 키 노출 여부")

    def test_scenario3h_overflow_scan(self, logged_in_page, settings):
        """글자수 제한 스캔(생성) — yaml overflow_scan 필드 요소별 + 오류 시 2컷.
        sc4h(수정 컨텍스트)와 같은 요소·같은 결과면 merge_key 로 결함 카드 묶음."""
        print("\n━━ [운용 프로세스] sc3h: 글자수 제한 스캔(생성) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        _hints = _load_hints(self.PAGE_ID)
        for field_def in _hints.get("fields", []):
            if not field_def.get("overflow_scan"):
                continue
            self._overflow_scan_field(p, field_def, mode="생성", tag="sc3h", sc=3)
        p._restore_page_size()
