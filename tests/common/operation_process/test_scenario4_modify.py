"""운용 프로세스 — 시나리오 4: 수정 (재구성 2026-07-03, 기존 sc4 이관 + 보강).

4a — 수정 모달 제목 + 전 필드 로드(4-1, 요소별)
4b — 설명 수정 → 3점 대조(행 표시+재오픈) — 기존 이관
4c — 서명 수정 → 3점 대조(행 '서명' 컬럼 표시) — 신규 보강
4d — 실행경로 값→값 수정 → 재오픈 (리스트 컬럼 없음 → 2점) — 신규 보강
4e — rename 중복(기존 [AUTO] 이름으로) — sc3f 생성 중복과 merge
4f — rename 특수문자 — sc3e 생성 특수문자와 merge
4g — 이름 비움 4-3(위반 저장값) — sc2c 생성 빈값과 merge
4h — 글자수 제한 스캔(수정 컨텍스트, 이름 제외) — sc3h 생성판과 같은 결과면 merge
4i — 수정 검증 메시지 i18n 키 노출 전수(sweep 1카드) — sc3i 생성판과 같은 결과면 merge
※ 선택 필드 비움(실행경로 등)은 sc5c(되돌리기) 소관으로 이동.
"""
import yaml
from pathlib import Path
from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase

_AUTO   = "[AUTO]_cm_sc4"
_OTHER  = "[AUTO]_cm_sc4_other"
_SIGN4  = "auto_sign_sc4"
_DESC4  = "auto_desc_sc4"
_SHA2_VALID = "AABB112233445566778899001122334455667788990011223344556677889900"
_EXEC4  = r"C:\auto\sc4_proc.exe"


class TestOperationProcessScenario4Modify(OperationProcessBase):
    """운용 프로세스 — 시나리오 4: 수정."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _ensure_target(self, p):
        p.ensure_auto_filter()
        if _AUTO not in p.get_item_names():
            p.add_item(_AUTO, sha2=_SHA2_VALID, sign=_SIGN4,
                       exec_path=_EXEC4, description=_DESC4)

    def _row_cells(self, p, name):
        # 이름 셀 정확 일치 — 접두사 이름 충돌로 다른 행을 잡는 오탐 방지(2026-07-03)
        for row in p.page.locator(p.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds and tds[0].inner_text().strip() == name:
                return row, [td.inner_text().strip() for td in tds]
        return None, []

    def test_scenario4a_load(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc4a: 수정 모달 로드(4-1) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        p.open_modify_modal(_AUTO)
        title = p.get_modal_title()
        self._add("pass" if "수정" in title else "warn", "sc4a — 수정 모달 제목",
                  f"결과: {title!r}", sc=4)
        for sel, label, expected in [
            (p.SEL_PROCESS_NAME, "프로세스 이름", _AUTO),
            (p.SEL_SIGN,         "서명",          _SIGN4),
            (p.SEL_EXEC_PATH,    "실행경로",       _EXEC4),
            (p.SEL_DESCRIPTION,  "설명",          _DESC4),
        ]:
            loaded = p.get_field_value(sel)
            ok = loaded == expected
            self._add("pass" if ok else "fail", f"sc4a — {label} 로드",
                      f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=4,
                      highlight=(None if ok else p.page.locator(sel)))
        sha2 = p.get_field_value(p.SEL_SHA2)
        self._add("pass" if sha2.strip() else "fail", "sc4a — SHA2 로드",
                  f"결과: {sha2[:20]!r}...", sc=4,
                  highlight=(None if sha2.strip() else p.page.locator(p.SEL_SHA2)))
        p.close_modal()

    def _modify_and_verify_3pt(self, p, sel, field_label, new_val, col_in_row: bool, sc_label: str):
        """공통: 필드 수정 저장 → 행 표시(col_in_row 시) + 재오픈 로드 — 계층 판정."""
        p.open_modify_modal(_AUTO)
        p.page.locator(sel).first.fill(new_val)
        p.page.wait_for_timeout(150)
        p.click_attached(p.SEL_SUBMIT_BTN)
        p._handle_confirm_modal()
        p.wait_for(p.SEL_ADD_BTN)
        p.ensure_auto_filter()
        row_loc, cells = self._row_cells(p, _AUTO)
        row_shows = new_val in cells
        p.open_modify_modal(_AUTO)
        loaded = p.get_field_value(sel)
        if loaded != new_val:
            self._add("fail", sc_label,
                      f"입력: {new_val!r} 수정 / 재오픈={loaded!r} — 재오픈에 미반영(수정 저장 실패)",
                      sc=4, highlight=p.page.locator(sel))
            p.close_modal()
        elif col_in_row and not row_shows:
            p.close_modal()
            shot1 = self._shot(f"{field_label}_모달반영", highlight=None,
                               caption=f"1. 재오픈 모달 — {field_label} 새 값 반영(데이터 정상)")
            self._add("warn", sc_label,
                      f"입력: {new_val!r} 수정 / 재오픈 일치 — 리스트 행 '{field_label}' 컬럼이 옛값(행 표시 stale)",
                      sc=4, screenshots=[shot1] if shot1 else None, highlight=row_loc)
        else:
            p.close_modal()
            self._add("pass", sc_label,
                      f"입력: {new_val!r} 수정 / " +
                      ("행 표시·재오픈 모두 반영" if col_in_row else "재오픈 반영(리스트 컬럼 없음 — 2점)"),
                      sc=4)

    def test_scenario4b_desc_modify_3pt(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc4b: 설명 수정 3점 대조 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        self._modify_and_verify_3pt(p, p.SEL_DESCRIPTION, "설명", "sc4_modified_desc",
                                    col_in_row=True, sc_label="sc4b — 설명 수정 → 행 표시+재오픈(3점)")

    def test_scenario4c_sign_modify_3pt(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc4c: 서명 수정 3점 대조 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        self._modify_and_verify_3pt(p, p.SEL_SIGN, "서명", "sc4_modified_sign",
                                    col_in_row=True, sc_label="sc4c — 서명 수정 → 행 표시+재오픈(3점)")

    def test_scenario4d_exec_path_modify(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc4d: 실행경로 값→값 수정 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        self._modify_and_verify_3pt(p, p.SEL_EXEC_PATH, "실행경로", r"C:\auto\sc4_mod.exe",
                                    col_in_row=False, sc_label="sc4d — 실행경로 수정 → 재오픈")

    def test_scenario4e_rename_duplicate(self, logged_in_page, settings):
        """기존 [AUTO] 이름으로 rename → 중복 차단 여부.
        차단 판정은 한글 메시지 + raw i18n 키(예 COLUMN.NAME.WR_ALREADY_PROCESS) 둘 다 인식
        (실측 2026-07-03: rename 경로는 i18n 키를 노출 — 메시지 품질은 sc4i sweep 카드가 별도 판정)."""
        print("\n━━ [운용 프로세스] sc4e: rename 중복 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        p.ensure_auto_filter()
        if _OTHER not in p.get_item_names():
            p.add_item(_OTHER)
        p.open_modify_modal(_AUTO)
        p.page.locator(p.SEL_PROCESS_NAME).first.fill(_OTHER)
        p.page.wait_for_timeout(150)
        p.click_attached(p.SEL_SUBMIT_BTN)
        p.page.wait_for_timeout(600)
        blocked, msg = False, ""
        if p.is_confirm_modal_visible():
            msg = p.get_modal_message()
            blocked = ("이미 등록된" in msg) or ("ALREADY" in msg.upper())
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        shots = None
        if blocked:
            # 판정 지점 2컷: ①중복 이름 입력 상태 ②저장 재시도 → 차단 경고 재발생
            shot1 = self._shot("rename중복_입력상태", highlight=p.page.locator(p.SEL_PROCESS_NAME),
                               caption=f"1. 수정 모달 — 이름을 기존 {_OTHER!r} 로 변경한 상태")
            shot2 = None
            try:
                p.click_attached(p.SEL_SUBMIT_BTN)
                p.page.locator(p.SEL_CONFIRM_MODAL).wait_for(state="attached", timeout=6000)
                p.page.wait_for_timeout(300)
                shot2 = self._shot("rename중복_차단경고", caption=f"2. 저장 → 중복 차단 경고 {msg!r}")
                p.dismiss_confirm_modal()
                p.wait_for_confirm_modal_closed()
            except Exception:
                pass
            shots = [s for s in (shot1, shot2) if s] or None
        p._close_modal_if_open()
        p.ensure_auto_filter()
        kept = _AUTO in p.get_item_names()
        self._add("pass" if (blocked and kept) else "warn", "sc4e — 기존 이름으로 rename → 중복 차단",
                  f"입력: {_AUTO!r} → {_OTHER!r} / 결과: 경고={msg!r}, 원본 유지={kept}"
                  + (" — 차단 정상(메시지 품질은 sc4i 참조)" if (blocked and kept) else ""), sc=4,
                  merge_key=f"cm_name_dup::{'blocked' if (blocked and kept) else 'not_blocked'}",
                  screenshot=not shots, screenshots=shots,
                  highlight=(None if shots or (blocked and kept) else p.page.locator(p.SEL_PROCESS_NAME)),
                  repro="1. 수정 모달 이름을 기존 [AUTO] 이름으로\n2. 저장\n3. 중복 차단 + 원본 유지")

    def test_scenario4f_rename_special_char(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc4f: rename 특수문자 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        newname = "[AUTO]_cm_sc4!@#$"   # HTML <> 금지 — inner_text 파싱 실패(yaml note)
        p.ensure_auto_filter()
        if newname in p.get_item_names():   # 재실행 잔존 가드(정상 흐름에선 발동 안 함)
            p.delete_item(newname)
        p.open_modify_modal(_AUTO)
        p.page.locator(p.SEL_PROCESS_NAME).first.fill(newname)
        p.page.wait_for_timeout(150)
        p.click_attached(p.SEL_SUBMIT_BTN)
        p._handle_confirm_modal()
        p.wait_for(p.SEL_ADD_BTN)
        p.ensure_auto_filter()
        renamed = newname in p.get_item_names()
        self._add("pass" if renamed else "warn", "sc4f — 특수문자로 rename",
                  f"입력: {_AUTO!r} → {newname!r} / 결과: 변경됨={renamed} (허용/차단 실측 기록)", sc=4,
                  merge_key=f"cm_name_special::{'allowed' if renamed else 'blocked'}")
        # 원복(이후 시나리오가 _AUTO 사용)
        if renamed:
            p.open_modify_modal(newname)
            p.page.locator(p.SEL_PROCESS_NAME).first.fill(_AUTO)
            p.page.wait_for_timeout(150)
            p.click_attached(p.SEL_SUBMIT_BTN)
            p._handle_confirm_modal()
            p.wait_for(p.SEL_ADD_BTN)

    def test_scenario4g_name_empty_violation(self, logged_in_page, settings):
        """4-3: 이름 비우고 저장 → 실제 저장값 확인 (신규 보강 — 특수폴더 sc4c 대응)."""
        print("\n━━ [운용 프로세스] sc4g: 이름 비움 위반 저장값(4-3) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        p.open_modify_modal(_AUTO)
        p.page.locator(p.SEL_PROCESS_NAME).first.fill("")
        p.page.wait_for_timeout(150)
        p.click_attached(p.SEL_SUBMIT_BTN)
        p.page.wait_for_timeout(600)
        block_msg = ""
        if p.is_confirm_modal_visible():
            block_msg = p.get_modal_message()
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        p._close_modal_if_open()
        p.ensure_auto_filter()
        still = _AUTO in p.get_item_names()
        if still and ("입력해" in block_msg):
            st, detail, cls = "pass", f"명확한 경고로 차단({block_msg!r}) + 원본 유지 — 데이터 안전", "blocked"
        elif still:
            st, detail, cls = "warn", f"원본 유지되나 경고 불명확({block_msg!r}) — 저장됐다 착각 가능(UX)", "unclear"
        else:
            st, detail, cls = "fail", "이름 비움 저장 후 목록에서 사라짐(데이터 손상 의심)", "not_blocked"
        self._add(st, "sc4g — 이름 비움 후 실제 저장값(4-3)",
                  f"입력: 이름 비우고 저장 / 결과: {detail}", sc=4,
                  merge_key=f"cm_req_empty::프로세스이름::{cls}",
                  repro="1. 수정 모달 이름 비움\n2. 저장\n3. 차단 경고 + 원본 유지 확인")

    def test_scenario4i_i18n_message_sweep_in_modify(self, logged_in_page, settings):
        """수정 검증 메시지 전수 — raw i18n 키 노출 없는지 (sc3i 생성판의 수정 미러).
        실측(리포트 #8, 2026-07-03): rename 중복 경고가 'COLUMN.NAME.WR_ALREADY_PROCESS' raw 키 노출."""
        print("\n━━ [운용 프로세스] sc4i: 수정 검증 메시지 i18n 전수 ━━━")
        import re as _re
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_target(p)
        p.ensure_auto_filter()
        if _OTHER not in p.get_item_names():
            p.add_item(_OTHER)
        _KEY = _re.compile(r"[A-Z][A-Z0-9]*(?:\.[A-Z0-9_]+)+")
        collected, leak_shots = [], []
        for trig_label, new_name in [("이름 비움 저장", ""), ("rename 중복 저장", _OTHER)]:
            try:
                p.open_modify_modal(_AUTO)
                p.page.locator(p.SEL_PROCESS_NAME).first.fill(new_name)
                p.page.wait_for_timeout(150)
                p.click_attached(p.SEL_SUBMIT_BTN)
                p.page.wait_for_timeout(600)
                msg = p.get_modal_message() if p.is_confirm_modal_visible() else "(경고 없음)"
                leaked = bool(_KEY.search(msg))
                collected.append((trig_label, msg, leaked))
                if leaked and p.is_confirm_modal_visible():
                    s = self._shot(f"i18n수정_{trig_label}",
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
        self._add("warn" if leaks else "pass", "sc4i — 수정 검증 메시지 i18n 키 노출 전수",
                  (f"raw i18n 키 노출: {leaks} — " if leaks else "노출 없음(깨끗한 한글) — ") + detail,
                  sc=4, screenshot=False, screenshots=leak_shots or None,
                  merge_key=f"cm_i18n::{','.join(leaks) or 'clean'}",
                  repro="1. 수정 경로에서 검증 경고 유발(비움/중복)\n2. 메시지에 COLUMN.* 류 키 노출 여부")

    def test_scenario4h_overflow_scan_in_modify(self, logged_in_page, settings):
        """글자수 제한 스캔(수정 컨텍스트) — sc3h 생성판의 미러(이름 제외: rename 되면 항목 추적 불가).
        전용 항목 [AUTO]_cm_ov_mod 사용(값 오염 무관 — sc5d 가 정리). 같은 결과는 sc3h 와 merge."""
        print("\n━━ [운용 프로세스] sc4h: 글자수 제한 스캔(수정) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        ov_item = "[AUTO]_cm_ov_mod"
        p.ensure_auto_filter()
        if ov_item not in p.get_item_names():
            p.add_item(ov_item)
        _hints_path = Path(__file__).parent.parent.parent.parent / "config" / "scan_hints" / f"{self.PAGE_ID}.yaml"
        _hints = yaml.safe_load(_hints_path.read_text(encoding="utf-8")) if _hints_path.exists() else {}
        for field_def in (_hints or {}).get("fields", []):
            if not field_def.get("overflow_scan") or field_def.get("id") == "processName":
                continue
            self._overflow_scan_field(p, field_def, mode="수정", tag="sc4h", item=ov_item, sc=4)
        p._restore_page_size()
