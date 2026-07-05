"""태그 관리 — 시나리오 3: 동작 검증 (재구성 2026-07-03).

3a — 미선택 수정/미체크 삭제 경고 (reload 로 미선택 전제 보장 — 프로세스 sc3a 오탐 교훈)
3b — 추가(이름+설명) → 목록 + 리스트 컬럼 표시(요소별: 이름/설명/카운트 0)
3c — 검색(이름 / 없는 항목 — 옵션 select 없음, 단일 검색)
3d — 추가 후 저장값 확인(수정 모달 재오픈, 요소별)
3e — 이름 특수문자(yaml special_char_tests — sc4e rename 특수문자와 merge)
3f — 중복 이름 차단([AUTO] 간 — sc4d rename 중복과 merge)
3g — 글자수 제한 스캔(tagName/description — 요소별 + 오류 시 2컷, sc4g 수정판과 merge)
3h — 생성 검증 메시지 i18n 키 노출 전수(sweep 1카드 — sc4h 수정판과 merge)
3i — 프로세스 등록/제거(+피커 → 등록 목록 → 저장 → 행 카운트 → 재오픈 유지 → '-' 제거 → 카운트 0)
3j — Export/Import 왕복(Export 실감지+저장 → [AUTO] 전용 사본 → 삭제 → Import 복원) — 존재 확인(sc1a)과 별개
※ 삭제 동작은 sc5 소관. 생성분은 중간 삭제 없이 sc5d 일괄 cleanup — '[AUTO' 필터 유지 흐름.
"""
import yaml
from pathlib import Path

from pages.npouch_tag_page import NpouchTagPage
from tests.common.tag._base import TagBase

_AUTO_TAG  = "[AUTO]_cm_tag"
_DESC_VAL  = "auto_tag_desc_test"


def _load_hints(page_id: str) -> dict:
    path = Path(__file__).parent.parent.parent.parent / "config" / "scan_hints" / f"{page_id}.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


class TestTagScenario3Action(TagBase):
    """태그 관리 — 시나리오 3: 동작 검증."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchTagPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _row_cells(self, p, name):
        # 이름 셀 정확 일치 — 접두사 이름 충돌로 다른 행을 잡는 오탐 방지(2026-07-03)
        for row in p.page.locator(p.SEL_TABLE_ROW).all():
            tds = row.locator("td").all()
            if tds and tds[0].inner_text().strip() == name:
                return row, [td.inner_text().strip() for td in tds]
        return None, []

    def test_scenario3a_no_selection_warnings(self, logged_in_page, settings):
        """미선택 전제 보장 — 선행 시나리오의 행 선택(tActive) 잔존 방지(reload)."""
        print("\n━━ [태그 관리] sc3a: 미선택/미체크 경고 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.page.reload()
        p.navigate_to()
        for btn, label in [
            ("button#modifyItemBtn", "수정 버튼 — 미선택 경고"),
            ("button#removeItemBtn", "삭제 버튼 — 미체크 경고"),
        ]:
            p.page.locator(btn).first.evaluate("el => el.click()")
            p.page.wait_for_timeout(400)
            if p.is_confirm_modal_visible():
                msg = p.get_modal_message()
                ok = ("선택" in msg) or ("체크" in msg)
                self._add("pass" if ok else "warn", f"sc3a — {label}",
                          f"결과: {msg!r}", sc=3)
                p.dismiss_confirm_modal()
                p.wait_for_confirm_modal_closed()
            elif p.page.locator(p.SEL_MODAL_OPEN).count() > 0:
                shot = self._shot(f"{label}_모달열림",
                                  caption="1. 미선택 상태에서 클릭 → 경고 대신 편집 모달 열림")
                self._add("warn", f"sc3a — {label}",
                          "경고 모달 대신 편집 모달이 열림 — 행 선택 상태 잔존 여부 확인 필요", sc=3,
                          screenshot=False, screenshots=[shot] if shot else None)
                p._close_modal_if_open()
            else:
                self._add("warn", f"sc3a — {label}", "에러 모달 없음", sc=3)

    def test_scenario3b_add_and_row_display(self, logged_in_page, settings):
        """추가(이름+설명) → 목록 등록 + 리스트 컬럼 표시(요소별 — 3점의 리스트 계층)."""
        print("\n━━ [태그 관리] sc3b: 추가 + 행 표시 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        self._ensure_session_cleanup(p)
        p.add_item_with_desc(_AUTO_TAG, _DESC_VAL)
        p.ensure_auto_filter()
        exists = _AUTO_TAG in p.get_item_names()
        self._add("pass" if exists else "fail", "sc3b — 태그 추가 → 목록 등록",
                  f"입력: {_AUTO_TAG!r} + 설명 / 결과: {'존재' if exists else '없음'}", sc=3,
                  repro="1. 추가 모달 이름+설명 입력\n2. 추가\n3. 목록 등장")
        if not exists:
            return
        row_loc, cells = self._row_cells(p, _AUTO_TAG)
        for col_label, expected in [("태그 이름", _AUTO_TAG), ("설명", _DESC_VAL), ("프로세스 카운트", "0")]:
            found = expected in cells
            self._add("pass" if found else "warn", f"sc3b — 행 표시: {col_label} 컬럼",
                      f"입력/기대: {expected!r} / 결과: {'표시' if found else '없음'} (행={cells})", sc=3,
                      highlight=(None if found else row_loc))

    def test_scenario3c_search(self, logged_in_page, settings):
        """검색 기능 자체 검증 — 개별 검색 유지(필터 통일 예외)."""
        print("\n━━ [태그 관리] sc3c: 검색 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        try:
            p.search_item(_AUTO_TAG)
            self._add("pass" if _AUTO_TAG in p.get_item_names() else "fail",
                      "sc3c — 검색(태그 이름)", f"입력: {_AUTO_TAG!r}", sc=3)
            p.search_item("ZZZQANOTEXISTZZZTEST")
            empty = p.get_item_names()
            self._add("pass" if not empty else "warn", "sc3c — 없는 항목 검색 → 빈 목록",
                      f"결과: {len(empty)}개" + (f" — {empty}" if empty else ""), sc=3,
                      highlight=(None if not empty else p.page.locator("table tbody")))
            p._restore_page_size()
        except Exception as e:
            self._add("warn", "sc3c — 검색 기능 테스트", str(e), sc=3)

    def test_scenario3d_saved_values(self, logged_in_page, settings):
        print("\n━━ [태그 관리] sc3d: 저장값 확인 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _AUTO_TAG not in p.get_item_names():
            p.add_item_with_desc(_AUTO_TAG, _DESC_VAL)
        p.open_modify_modal(_AUTO_TAG)
        for sel, label, expected in [
            (p.SEL_TAG_NAME,    "태그 이름", _AUTO_TAG),
            (p.SEL_DESCRIPTION, "설명",      _DESC_VAL),
        ]:
            loaded = p.get_field_value(sel)
            ok = loaded == expected
            self._add("pass" if ok else "fail", f"sc3d — {label} 저장값 확인",
                      f"입력: {expected!r} / 결과: {loaded!r}", sc=3,
                      highlight=(None if ok else p.page.locator(sel)))
        p.close_modal()

    def test_scenario3e_special_char_name(self, logged_in_page, settings):
        """이름 특수문자(yaml) — 차단 여부 + 저장 시 목록 등재. sc4e(rename)와 merge."""
        print("\n━━ [태그 관리] sc3e: 이름 특수문자(yaml) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        _hints = _load_hints(self.PAGE_ID)
        tests = _hints.get("special_char_tests", []) or [
            {"label": "태그 이름 — 특수문자 입력 차단 여부",
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
                      sc=3, merge_key=f"tag_name_special::{cls}",
                      repro=f"1. 이름에 특수문자({_value!r})\n2. 추가\n3. 허용/차단 여부")

    def test_scenario3f_duplicate_name(self, logged_in_page, settings):
        """중복 이름 차단([AUTO] 간 — 실데이터 미사용). sc4d(rename 중복)와 merge."""
        print("\n━━ [태그 관리] sc3f: 중복 이름 차단 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _AUTO_TAG not in p.get_item_names():
            p.add_item(_AUTO_TAG)
        p.open_add_modal()
        p.fill(p.SEL_TAG_NAME, _AUTO_TAG)
        p.try_submit()
        p.page.wait_for_timeout(600)
        if p.is_confirm_modal_visible():
            msg = p.get_modal_message()
            blocked = ("이미 등록된" in msg) or ("ALREADY" in msg.upper())
            self._add("pass" if blocked else "warn", "sc3f — 중복 이름 차단(생성)",
                      f"입력: {_AUTO_TAG!r}(기존 [AUTO] 태그명) / 결과: {msg!r}", sc=3,
                      merge_key=f"tag_name_dup::{'blocked' if blocked else 'not_blocked'}",
                      highlight=(None if blocked else p.page.locator(p.SEL_CONFIRM_MODAL)))
            p.dismiss_confirm_modal()
            p.wait_for_confirm_modal_closed()
        else:
            self._add("warn", "sc3f — 중복 이름 차단(생성)", "에러 모달 없음", sc=3,
                      merge_key="tag_name_dup::not_blocked")
        p.close_modal()

    def test_scenario3g_overflow_scan(self, logged_in_page, settings):
        """글자수 제한 스캔(생성) — yaml overflow_scan 필드(tagName/description) 요소별 + 2컷.
        sc4g(수정 컨텍스트)와 같은 요소·같은 결과면 merge."""
        print("\n━━ [태그 관리] sc3g: 글자수 제한 스캔(생성) ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        _hints = _load_hints(self.PAGE_ID)
        for field_def in _hints.get("fields", []):
            if not field_def.get("overflow_scan"):
                continue
            self._overflow_scan_field(p, field_def, mode="생성", tag="sc3g", sc=3)
        p._restore_page_size()

    def test_scenario3h_i18n_message_sweep(self, logged_in_page, settings):
        """생성 검증 메시지 전수 — raw i18n 키 노출 없는지(sweep 1카드). sc4h 와 merge."""
        print("\n━━ [태그 관리] sc3h: 생성 검증 메시지 i18n 전수 ━━━")
        import re as _re
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _AUTO_TAG not in p.get_item_names():
            p.add_item(_AUTO_TAG)
        _KEY = _re.compile(r"[A-Z][A-Z0-9]*(?:\.[A-Z0-9_]+)+")
        collected, leak_shots = [], []
        for trig_label, name_value in [("이름 빈값 제출", ""), (f"중복 이름 제출({_AUTO_TAG})", _AUTO_TAG)]:
            try:
                p.open_add_modal()
                if name_value:
                    p.fill(p.SEL_TAG_NAME, name_value)
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
        self._add("warn" if leaks else "pass", "sc3h — 생성 검증 메시지 i18n 키 노출 전수",
                  (f"raw i18n 키 노출: {leaks} — " if leaks else "노출 없음(깨끗한 한글) — ") + detail,
                  sc=3, screenshot=False, screenshots=leak_shots or None,
                  merge_key=f"tag_i18n::{','.join(leaks) or 'clean'}",
                  repro="1. 검증 경고 유발(빈값/중복)\n2. 메시지에 COLUMN.* 류 키 노출 여부")

    def test_scenario3j_export_import_roundtrip(self, logged_in_page, settings):
        """Export/Import 왕복 검증 (실측 설계 2026-07-03).

        Export 는 필터 무시 전체 목록(GET getTagExport 파라미터 없음 — 실측)이라 그대로 재업로드하면
        실데이터 중복/변조 위험 → 사본에서 **헤더 + 프로브([AUTO]) 행만 남겨** 업로드(실데이터 행 제거).
        흐름: 프로브 생성 → Export 저장 → [AUTO] 전용 사본 → 프로브 삭제 → Import(div#addTagUpload,
        input#addFile — 네이티브 대화상자 아님) → 프로브 복원 확인. 파일이 텍스트가 아니면 수동 warn."""
        print("\n━━ [태그 관리] sc3j: Export/Import 왕복 ━━━")
        from pathlib import Path as _P
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        probe = "[AUTO]_cm_tag_ie"
        p.ensure_auto_filter()
        if probe not in p.get_item_names():
            p.add_item(probe)
        # ① Export — 다운로드 실감지 + 파일 저장
        dl_dir = _P(__file__).parent.parent.parent.parent / "reports" / "downloads"
        dl_dir.mkdir(parents=True, exist_ok=True)
        try:
            with p.page.expect_download(timeout=10_000) as dl_info:
                p.page.locator("button#exportFileBtn").first.evaluate("el => el.click()")
            dl = dl_info.value
            fname = dl.suggested_filename
            saved = dl_dir / fname
            dl.save_as(str(saved))
            self._add("pass", "sc3j — Export 버튼 다운로드 동작",
                      f"입력: Export 클릭 / 결과: 다운로드 발생 — 파일명 {fname!r} ({saved.stat().st_size}B)",
                      sc=3, repro="1. Export 클릭\n2. 파일 다운로드 발생 확인")
        except Exception as e:
            self._add("warn", "sc3j — Export 버튼 다운로드 동작",
                      f"다운로드 이벤트 미감지({type(e).__name__}) — 동작/환경 확인 필요", sc=3)
            return
        # ② [AUTO] 전용 사본 — 프로브 항목만 남김(실데이터 항목 제거).
        #    형식 = JSON (실측 2026-07-03: GlobalProcessTag_Json.json) → 파싱 필터.
        #    JSON 파싱 실패 시 CSV 라인 필터 fallback, 둘 다 아니면 수동 warn.
        import json as _json
        try:
            raw = saved.read_bytes()
            text = raw.decode("utf-8-sig")
            copy_path = dl_dir / f"import_auto_only_{fname}"
            try:
                data = _json.loads(text)
                _keep = lambda e: probe in _json.dumps(e, ensure_ascii=False)
                if isinstance(data, list):
                    data = [e for e in data if _keep(e)]
                    kept = len(data)
                elif isinstance(data, dict):
                    kept = 0
                    for k, v in data.items():
                        if isinstance(v, list):
                            data[k] = [e for e in v if _keep(e)]
                            kept += len(data[k])
                else:
                    raise ValueError(f"예상 밖 JSON 최상위 타입: {type(data).__name__}")
                assert kept >= 1, "export JSON 에 프로브 항목 없음"
                copy_path.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
            except _json.JSONDecodeError:
                lines = text.splitlines()
                keep = [lines[0]] + [l for l in lines[1:] if probe in l]
                assert len(keep) >= 2, f"export 에 프로브 행 없음(총 {len(lines)}행)"
                copy_path.write_text("\n".join(keep) + "\n", encoding="utf-8-sig")
        except (UnicodeDecodeError, AssertionError, ValueError) as e:
            self._add("warn", "sc3j — Import 왕복 [수동 확인 필요]",
                      f"Export 파일({fname!r})에서 [AUTO] 전용 사본 생성 불가({e!r}) — 형식/구조 확인 필요. "
                      "Export 는 전체 목록이라 원본 재업로드는 실데이터 위험 → 수동 검증 필요.",
                      sc=3, screenshot=False,
                      repro="1. Export 파일 확인\n2. 테스트 항목만 남겨 Import\n3. 목록 반영 확인")
            return
        # ③ 프로브 삭제 → Import → 복원 확인 (왕복)
        p.delete_item(probe)
        p.ensure_auto_filter()
        assert probe not in p.get_item_names()
        p.open_import_modal()
        msg = p.upload_import_file(str(copy_path))
        p.ensure_auto_filter()
        restored = probe in p.get_item_names()
        self._add("pass" if restored else "warn", "sc3j — Import 업로드 → 목록 복원(왕복)",
                  f"입력: [AUTO] 전용 사본({copy_path.name}) 업로드 / 결과: 응답={msg!r}, "
                  f"프로브 {'복원됨(왕복 성공)' if restored else '미복원 — 형식/파서 확인 필요'}", sc=3,
                  highlight=(None if restored else p.page.locator("table tbody")),
                  repro="1. Export 파일에서 [AUTO] 행만 남긴 사본 생성\n2. 항목 삭제\n"
                        "3. Import 업로드 → 등록\n4. 목록 복원 확인")

    def test_scenario3i_process_register_remove(self, logged_in_page, settings):
        """프로세스 등록/제거 — 태그의 핵심 동작(요소별 카드).
        +피커 등록 → 모달 등록 목록 → 저장 → 행 카운트 → 재오픈 유지 → '-' 제거 → 카운트 0."""
        print("\n━━ [태그 관리] sc3i: 프로세스 등록/제거 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        p.ensure_auto_filter()
        if _AUTO_TAG not in p.get_item_names():
            p.add_item(_AUTO_TAG)
        # ① 등록: 수정 모달 → + 피커 → 첫 프로세스 선택 → 확인
        p.open_modify_modal(_AUTO_TAG)
        p.open_process_list_modal()
        proc_name = p.select_first_process_in_modal()
        p.confirm_process_selection()
        in_modal = proc_name in p.get_registered_process_names()
        self._add("pass" if in_modal else "fail", "sc3i — 피커 선택 → 모달 등록 목록 반영",
                  f"입력: {proc_name!r} 선택 / 결과: {'등록 목록에 표시' if in_modal else '미표시'}", sc=3,
                  highlight=(None if in_modal else p.page.locator("div#addItemModal table")))
        p.click_attached(p.SEL_SUBMIT_BTN)
        p._handle_confirm_modal()
        p.wait_for(p.SEL_ADD_BTN)
        # ② 행 카운트 반영
        p.ensure_auto_filter()
        cnt = p.get_process_count_in_list(_AUTO_TAG)
        self._add("pass" if cnt == 1 else "warn", "sc3i — 행 표시: 프로세스 카운트 반영",
                  f"입력: 1개 등록 저장 / 결과: 카운트={cnt}", sc=3,
                  highlight=(None if cnt == 1 else p.page.locator("table tbody")))
        # ③ 재오픈 유지
        p.open_modify_modal(_AUTO_TAG)
        kept = proc_name in p.get_registered_process_names()
        self._add("pass" if kept else "fail", "sc3i — 재오픈: 등록 프로세스 유지",
                  f"결과: {proc_name!r} {'유지' if kept else '사라짐'}", sc=3,
                  highlight=(None if kept else p.page.locator("div#addItemModal table")))
        # ④ '-' 제거 → 저장 → 카운트 0
        p.remove_first_registered_process()
        p.click_attached(p.SEL_SUBMIT_BTN)
        p._handle_confirm_modal()
        p.wait_for(p.SEL_ADD_BTN)
        p.ensure_auto_filter()
        cnt2 = p.get_process_count_in_list(_AUTO_TAG)
        self._add("pass" if cnt2 == 0 else "warn", "sc3i — 프로세스 제거(-) → 카운트 0",
                  f"입력: 등록 1개 제거 저장 / 결과: 카운트={cnt2}", sc=3,
                  highlight=(None if cnt2 == 0 else p.page.locator("table tbody")),
                  repro="1. 수정 모달 등록 프로세스 체크\n2. '-' 제거\n3. 저장 → 행 카운트 0")
