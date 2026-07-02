"""시큐어존 템플릿(특수폴더) — 시나리오 4: 수정 흐름.

표준(scenario_4_modify.md): 4-1 로드 / 4-2 수정 후 재확인 / 4-3 위반 저장값.
+ 사용자 지시: sc3 검증을 '수정 컨텍스트'로 미러 → 상태 의존 버그(생성 땐 되는데 수정 뒤 안 되는 등) 포착.
수집(2026-07-01): 템플릿 수정=행 선택+'수정'(이름/용도/상태 로드, 저장='수정') / 폴더 항목 수정='설정명' 링크 클릭(로드, 저장='수정').
※ 삭제(리스트 단위)=sc1/sc5. 여기 '폴더 항목 제거'는 모달 내 매핑 제거(수정 컨텍스트 재검증).

4a 템플릿 로드(4-1) / 4b 상태 수정=update+반영(4-2) / 4c 4-3 이름 비움 위반 저장값
4d rename 중복 차단 / 4e 특수문자 rename
4f 폴더 항목 로드+설명 update / 4g 폴더 항목 제거(수정 컨텍스트) / 4h 폴더 설명 오버플로(수정)
4i 폴더 내용 필수 비움(4-3 전수)
[sc3 미러 보강 — 수정 컨텍스트]
4j 경로(원본/대상) 수정→재확인(3c/3k 미러) / 4k 항목 설정명 rename 중복(3q 미러)
4l 설정명 clamp 30(3i 미러) / 4m 관리자 예약어 게이팅(3f 미러, 수동확인 warn 은 sc3f 와 카드 묶음)
4n 수정 검증 메시지 i18n 전수(3o 미러) / 4o 경로 3000자 오버플로(3s 미러, 사용자 발견)
4p 템플릿 이름 clamp(3t 미러) / 4q 폴더 항목 상태 수정(무검증 필드 보강) / 4r 항목 설정명 특수문자(3u 미러)
※ 용도 분산(사용자 지시 2026-07-02): 4e/4g/4l/4r/4m = 레지변경(MODIFY_REGIST), 나머지 = 바로가기 — 용도별 차이 부수 포착.
※ 3점 대조(사용자 지시 2026-07-02): 상태류 수정은 입력값 ↔ 리스트 표시 ↔ 재오픈 로드 셋 다 대조(4b/4q) — 표시/저장 계층 분리 버그 구분.
※ 복사/검색/필터/복사충돌(3g/3h/3m/3p)은 리스트 액션 — 수정 컨텍스트 무관, sc3 책임 유지(미러 안 함).
"""
import re

from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from pages.shared._overlay import overlay_off
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario4Modify(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — 시나리오 4: 수정."""

    _M4 = "[AUTO]_sz_mf_m4"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _ensure_folder_item(self, page, tpl, setting):
        """tpl 에 folder 항목(setting) 보장. 폴더 모달 열린 채 반환."""
        page.open_folder_modal(tpl)
        if not page.folder_row_values(setting):
            page.open_content_add()
            page.add_folder_mapping(setting, use_picker=True, src_index=0, tgt_index=1)

    # ── 4-1 / 4-2 / 4-3 (템플릿 수정) ─────────────────────────────────
    def test_scenario4a_template_load(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc4a: 템플릿 수정 모달 로드(4-1) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.ensure_template(self._M4, "SHORTCUT")
        page.open_modify_modal(self._M4)
        name = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        # 용도는 생성에서만 정함 — 수정 모달에선 용도 선택 UI가 사라짐(변경 불가)이 정상(실측 2026-07-01).
        # (라디오는 DOM 에 남지만 숨김 → is_visible 로 판정, is_checked 로 보면 숨은 요소 오판)
        sc_vis = page.page.locator(page.SEL_TYPE_SHORTCUT).first.is_visible()
        rg_vis = page.page.locator(page.SEL_TYPE_REGIST).first.is_visible()
        type_hidden = (not sc_vis) and (not rg_vis)
        self._add("pass" if (name == self._M4 and type_hidden) else "fail",
                  "sc4a — 수정 모달 로드(이름) + 용도 변경 불가(선택 UI 미표시=정상)",
                  f"입력: 수정 모달 오픈 / 결과: 이름={name!r}(기대 {self._M4!r}), "
                  f"용도 선택 표시={sc_vis or rg_vis}(기대 미표시 — 수정 시 용도 고정)", sc=4,
                  repro="1. 템플릿 행 선택+수정\n2. 이름 로드 + 용도 선택 사라짐(수정 불가) 확인")
        page._close_modal_if_open()

    def test_scenario4b_status_update(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc4b: 상태 수정 = update + 반영(4-2) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._M4, "SHORTCUT")
        page.open_modify_modal(self._M4)
        with overlay_off(page.page):
            page.page.locator(page.SEL_STATUS_DELETE).first.evaluate("el => el.click()")  # 비활성
        page.submit_and_message()
        page.navigate_to()
        cnt = page.get_template_names().count(self._M4)
        # 3점 대조(사용자 지시 2026-07-02): 입력값 ↔ ①리스트 표시 ↔ ②재오픈 로드 — 표시/저장 계층이 따로 틀어지는 버그 구분
        list_status = page._row_locator(self._M4).locator("td").nth(3).inner_text().strip()
        page.open_modify_modal(self._M4)
        delete_checked = page.page.locator(page.SEL_STATUS_DELETE).first.is_checked()
        ok = (cnt == 1) and (list_status == "비활성") and delete_checked
        self._add("pass" if ok else "fail",
                  "sc4b — 상태 수정(활성→비활성) = update + 리스트/재오픈 3점 대조",
                  f"입력: 상태 비활성 저장 / 결과: 동명 {cnt}개(기대 1=update), "
                  f"리스트 상태={list_status!r}(기대 비활성), 재오픈 비활성 checked={delete_checked}", sc=4,
                  highlight=page._row_locator(self._M4),
                  repro="1. 수정 모달\n2. 상태 비활성\n3. 수정 저장\n4. 리스트 상태 열 = 비활성\n5. 재오픈 → 비활성 유지 + 중복 아님")
        # 원복(활성)
        with overlay_off(page.page):
            page.page.locator(page.SEL_STATUS_CREATE).first.evaluate("el => el.click()")
        page.submit_and_message()
        page._close_modal_if_open()

    def test_scenario4c_required_empty_violation(self, logged_in_page, settings):
        """4-3: 이름 비우고 수정 저장 → 실제 저장값 확인.
        분기: 빈값 저장=fail(손상) / 명확한 경고로 차단+원본 유지=pass(안전) / 경고 없이 원본 유지=warn(착각) / 그외=fail."""
        print("\n━━ [특수폴더] sc4c: 4-3 이름 비움 위반 저장값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4c"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_modify_modal(tpl)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "")
        block_msg = page.submit_and_message()   # 차단 경고 캡처(있으면)
        page._close_modal_if_open()
        page.navigate_to()
        still = tpl in page.get_template_names()
        blocked_clearly = ("입력해" in block_msg) or ("이름" in block_msg and block_msg.strip() != "")
        if still:
            page.open_modify_modal(tpl)
            actual = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
            page._close_modal_if_open()
            if actual == "":
                st, detail = "fail", "빈값 그대로 저장됨 — 데이터 손상"
            elif actual == tpl and blocked_clearly:
                st, detail = "pass", f"이름 필수 → 명확한 경고로 차단({block_msg!r}) + 원본 유지 → 데이터 안전(정상)"
            elif actual == tpl:
                st, detail = "warn", "경고 없이 원본 유지 — 사용자가 저장됐다 착각 가능(UX)"
            else:
                st, detail = "fail", f"예상 못한 동작 — 이름={actual!r}"
        else:
            st, detail = "fail", "이름 비움 저장 후 목록에서 사라짐(예상 못한 동작)"
        self._add(st, "sc4c — 이름 비움 후 실제 저장값(4-3)",
                  f"입력: 이름 비우고 수정 저장 / 결과: {detail}", sc=4,
                  repro="1. 수정 모달 이름 비움\n2. 저장\n3. 차단 경고 + 재오픈 실제 저장값 확인")

    def test_scenario4d_rename_duplicate(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc4d: rename 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4d"
        other = "[AUTO]_sz_mf_link"
        page.ensure_template(tpl, "SHORTCUT")
        page.ensure_template(other, "SHORTCUT")
        page.open_modify_modal(tpl)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", other)   # 기존 이름으로 rename
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        tpl_kept = tpl in page.get_template_names()
        blocked = "이미 등록된 이름" in msg
        self._add("pass" if (blocked and tpl_kept) else "warn",
                  "sc4d — 기존 이름으로 rename → 중복 차단",
                  f"입력: '{tpl}' → '{other}' rename / 결과: 경고={msg!r}, 원본 유지={tpl_kept}", sc=4,
                  repro="1. 수정 모달 이름을 기존 이름으로\n2. 저장\n3. 중복 차단 + 원본 이름 유지")

    def test_scenario4e_special_char_rename(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc4e: 특수문자 rename ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4e"
        newname = "[AUTO]_sz_mf_m4e<>!@#"
        page.ensure_template(tpl, "MODIFY_REGIST")   # 용도 분산 — 레지변경에서도 동일한지(사용자 지시 2026-07-02)
        if newname in page.get_template_names():
            page.delete_template(newname); page.navigate_to()
        page.open_modify_modal(tpl)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", newname)
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        renamed = newname in page.get_template_names()
        self._add("pass" if renamed else "warn",
                  "sc4e — 특수문자로 rename",
                  f"입력: '{tpl}' → '{newname}' / 결과: 경고={msg!r}, 변경됨={renamed} (실측: 특수문자 허용)", sc=4,
                  repro="1. 수정 모달 이름을 특수문자로\n2. 저장\n3. 허용/차단 여부")

    # ── 폴더 항목 수정 (수정 컨텍스트 미러) ────────────────────────────
    def test_scenario4f_folder_item_load_update(self, logged_in_page, settings):
        """폴더 항목 설정명 링크 → 로드 확인 + 설명 변경 → 수정 저장 → 재오픈 반영(4-1/4-2 폴더판)."""
        print("\n━━ [특수폴더] sc4f: 폴더 항목 로드 + 설명 update ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4f"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "f4item")
        # 로드 확인
        page.open_folder_item_edit("f4item")
        loaded = page.page.locator(page.SEL_C_NAME).first.input_value()
        src = page.page.locator(page.SEL_C_SOURCE).first.inner_text().strip()
        self._add("pass" if (loaded == "f4item" and "[/DESKTOP/]" in src) else "fail",
                  "sc4f — 폴더 항목 로드(설정명 링크 → 내용 로드)",
                  f"결과: 설정명={loaded!r}, 원본={src!r}", sc=4,
                  repro="1. 폴더모달 설정명 링크 클릭\n2. 설정명/원본 로드 확인")
        # 설명 변경 → 수정 저장
        page.fill(page.SEL_C_DESC, "mod_f4_desc")
        page.content_save_message()
        page.close_folder_modal()
        # 재오픈 → 반영 확인
        page.open_folder_modal(tpl)
        page.open_folder_item_edit("f4item")
        desc_after = page.page.locator(page.SEL_C_DESC).first.input_value()
        self._add("pass" if desc_after == "mod_f4_desc" else "fail",
                  "sc4f — 폴더 항목 설명 수정 → 재확인",
                  f"입력: 설명='mod_f4_desc' 수정 / 결과: 재오픈 설명={desc_after!r}", sc=4,
                  repro="1. 항목 설명 변경\n2. 수정 저장\n3. 재오픈 → 변경 반영")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario4g_folder_item_remove_in_modify(self, logged_in_page, settings):
        """수정 컨텍스트(기존 템플릿)에서 폴더 항목 제거 → 등록 -1 (상태 의존 버그 포착)."""
        print("\n━━ [특수폴더] sc4g: 폴더 항목 제거(수정 컨텍스트) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4g"
        page.ensure_template(tpl, "MODIFY_REGIST")   # 용도 분산 — 레지변경 폴더 항목 제거
        self._ensure_folder_item(page, tpl, "rm_target")
        before = page.folder_item_count()
        msg = page.remove_folder_item(0)
        after = page.folder_item_count()
        ok = ("삭제 하시겠습니까" in msg) and (after == before - 1)
        self._add("pass" if ok else "fail",
                  "sc4g — 폴더 항목 제거(수정 컨텍스트) → 등록 -1",
                  f"입력: 항목 선택+제거 / 결과: 확인={msg!r}, 등록 {before}→{after}", sc=4,
                  repro="1. 기존 템플릿 폴더모달\n2. 항목 제거\n3. '삭제 하시겠습니까?' 확인 → 등록 감소")
        page.close_folder_modal()

    def test_scenario4h_folder_desc_overflow_in_modify(self, logged_in_page, settings):
        """수정 저장 경로에서도 설명 오버플로(3000자) 서버 처리 — 생성(sc3j)과 동일한지."""
        print("\n━━ [특수폴더] sc4h: 폴더 설명 오버플로(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4h"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "ovf_item")
        page.open_folder_item_edit("ovf_item")
        big = "B" * 3000
        page.fill(page.SEL_C_DESC, big)
        msg = page.content_save_message()
        page.close_folder_modal()
        # 재오픈 → 3000자 저장됐나
        page.open_folder_modal(tpl)
        page.open_folder_item_edit("ovf_item")
        saved_len = len(page.page.locator(page.SEL_C_DESC).first.input_value())
        self._add("pass" if (msg.strip() == "" and saved_len == 3000) else "warn",
                  "sc4h — 수정 경로 설명 3000자 오버플로 → 서버 처리",
                  f"입력: 수정으로 설명 3000자 / 결과: 경고={msg!r}, 재오픈 길이={saved_len} "
                  "(생성 sc3j와 동일하게 무제한 저장 기대)", sc=4,
                  repro="1. 항목 설명 3000자로 수정\n2. 저장\n3. 재오픈 → 3000자 유지")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario4i_content_required_violation_in_modify(self, logged_in_page, settings):
        """4-3 (필수 전수, 요소별 카드): 폴더 내용 필수(설정명/원본/대상)를 수정에서 각각 비우고 저장 → 요소별 차단 판정.
        실측(2026-07-01): 각각 '~을 입력해 주세요.'로 차단, 미커밋. 빈값 저장되면 데이터 손상=fail."""
        print("\n━━ [특수폴더] sc4i: 폴더 내용 필수 비움(수정) 4-3 (요소별) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4i"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "req_edit")
        page.open_folder_item_edit("req_edit")
        cases = [
            ("설정명",   page.SEL_C_NAME,
             lambda: page.fill(page.SEL_C_NAME, ""),
             lambda: page.fill(page.SEL_C_NAME, "req_edit")),
            ("원본위치", page.SEL_C_SOURCE,
             lambda: page.set_content_path(page.SEL_C_SOURCE, ""),
             lambda: page.set_content_path(page.SEL_C_SOURCE, "[/DESKTOP/]")),
            ("대상위치", page.SEL_C_TARGET,
             lambda: page.set_content_path(page.SEL_C_TARGET, ""),
             lambda: page.set_content_path(page.SEL_C_TARGET, "[/MYDOC/]")),
        ]
        for elem, sel, blank, restore in cases:
            blank()
            msg = page.content_save_message()
            blocked = "입력해" in (msg or "")
            self._add("pass" if blocked else "fail",
                      f"sc4i — {elem} 필수 비움 수정 → 차단(4-3)",
                      f"입력: {elem} 비우고 수정 / 결과: 경고={msg!r} "
                      + ("(명확히 차단 — 빈값 저장 없음)" if blocked else "[미차단 — 빈값 저장 위험]"), sc=4,
                      highlight=page.page.locator(sel),
                      merge_key=f"content_required_empty::{elem}::{'pass' if blocked else 'fail'}",
                      repro=f"1. 폴더 항목 편집\n2. {elem} 비우고 수정\n3. 필수 경고로 차단되는지")
            restore()
        page.close_content_modal()
        page.close_folder_modal()

    # ── sc3 미러 보강 (수정 컨텍스트) ──────────────────────────────────
    def test_scenario4j_folder_path_update(self, logged_in_page, settings):
        """폴더 항목 경로(원본/대상) 수정 → 재오픈 반영 (3c/3k 미러 — 4f는 설명만, 핵심 필드는 여기서)."""
        print("\n━━ [특수폴더] sc4j: 폴더 항목 경로 수정 → 재확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4j"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "path_edit")   # [/DESKTOP/]→[/MYDOC/]
        page.open_folder_item_edit("path_edit")
        # picker 는 기존 값에 append(실측 2026-07-02) → '교체' 검증을 위해 먼저 비우고 선택
        page.set_content_path(page.SEL_C_SOURCE, "")
        page.set_content_path(page.SEL_C_TARGET, "")
        page.pick_path("source", 2)
        page.pick_path("target", 3)
        new_src = page.page.locator(page.SEL_C_SOURCE).first.inner_text().strip()
        new_tgt = page.page.locator(page.SEL_C_TARGET).first.inner_text().strip()
        msg = page.content_save_message()
        page.close_folder_modal()
        page.open_folder_modal(tpl)
        _n = lambda s: re.sub(r"\s+", "", s or "")   # 개행/공백 차이 무시 대조
        vals = _n(" ".join(page.folder_row_values("path_edit")))
        ok = (msg.strip() == "") and _n(new_src) and (_n(new_src) in vals) \
            and (_n(new_tgt) in vals) and ("[/DESKTOP/]" not in vals)   # 옛 원본이 사라져야 '교체'
        self._add("pass" if ok else "fail",
                  "sc4j — 폴더 항목 경로(원본/대상) 수정 → 재오픈 반영(교체)",
                  f"입력: 원본={new_src!r}/대상={new_tgt!r} 로 교체 / 결과: 경고={msg!r}, 재오픈 행값={vals!r} "
                  "(옛 경로 [/DESKTOP/] 은 없어야)", sc=4,
                  highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr", has_text="path_edit"),
                  repro="1. 항목 편집\n2. 원본/대상 비우고 picker 로 재선택\n3. 수정 저장\n4. 재오픈 → 새 경로만 반영")
        page.close_folder_modal()

    def test_scenario4k_folder_item_rename_duplicate(self, logged_in_page, settings):
        """항목 설정명을 기존 다른 항목 이름으로 rename → 중복 차단? (3q 생성 중복의 수정판)."""
        print("\n━━ [특수폴더] sc4k: 항목 설정명 rename 중복 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4k"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "k_one")
        if not page.folder_row_values("k_two"):
            page.open_content_add()
            page.add_folder_mapping("k_two", use_picker=True, src_index=2, tgt_index=3)
        page.open_folder_item_edit("k_two")
        page.fill(page.SEL_C_NAME, "k_one")
        msg = page.content_save_message()
        blocked = "이미 등록된 이름" in msg
        self._add("pass" if blocked else "warn",
                  "sc4k — 항목 설정명 rename 중복(기존 항목명으로 수정) → 차단",
                  f"입력: 'k_two' → 'k_one' rename / 결과: 경고={msg!r} "
                  + ("(생성 sc3q 와 동일하게 차단)" if blocked else "[미차단 — 생성 중복검사(sc3q)와 불일치, 수정 우회 구멍]"), sc=4,
                  highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr", has_text="k_one"),
                  repro="1. 항목 2개(k_one/k_two)\n2. k_two 편집 → 설정명 k_one\n3. 수정 → 중복 차단되는지")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario4l_content_name_clamp_in_modify(self, logged_in_page, settings):
        """수정 모달에서도 설정명 maxlength=30 clamp 유지되는지 (3i 미러, 실타이핑 — fill 금지)."""
        print("\n━━ [특수폴더] sc4l: 설정명 글자수 clamp(수정 컨텍스트) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4l"
        page.ensure_template(tpl, "MODIFY_REGIST")   # 용도 분산 — 레지변경 내용 모달도 clamp 30 인지
        self._ensure_folder_item(page, tpl, "clamp_item")
        page.open_folder_item_edit("clamp_item")
        accepted = page.type_real(page.SEL_C_NAME, "A" * 35)
        self._add("pass" if accepted == 30 else "warn",
                  "sc4l — 설정명 글자수 clamp(수정 컨텍스트, maxlength 30)",
                  f"입력: 편집 모달에서 35자 실타이핑 / 결과: 실제 수용 {accepted}자 (생성 sc3i 와 동일 30 기대)", sc=4,
                  highlight=page.page.locator(page.SEL_C_NAME),
                  repro="1. 항목 편집\n2. 설정명 35자 실타이핑\n3. 30자 clamp 유지되는지")
        page.close_content_modal()   # 저장 안 함 — 원본 무변경
        page.close_folder_modal()

    def test_scenario4m_admin_reserved_word_gating_in_modify(self, logged_in_page, settings):
        """수정 경로에서도 관리자 예약어 게이팅 되는지 (3f 미러 — 안 되면 수정 우회 구멍).
        비번 인증/암호화/복호화는 sc3f 와 동일하게 자동화 제외 → 수동확인 warn(sc3f 와 카드 묶음)."""
        print("\n━━ [특수폴더] sc4m: 관리자 예약어 게이팅(수정 컨텍스트) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4m"
        page.ensure_template(tpl, "MODIFY_REGIST")
        self._ensure_folder_item(page, tpl, "adm_edit")
        page.open_folder_item_edit("adm_edit")
        page.set_content_path(page.SEL_C_SOURCE, "[/RUN/]")
        page.set_content_path(page.SEL_C_TARGET, "[/DSEC/]")
        msg = page.content_save_message()
        gated = "관리자 전용 예약어가 감지되었습니다" in msg
        lic_vis = (page.field_present(page.SEL_C_LICENSE_PW)
                   and page.page.locator(page.SEL_C_LICENSE_PW).first.is_visible())
        self._add("pass" if gated and lic_vis else "fail",
                  "sc4m — 관리자 예약어로 경로 수정 → 비밀번호 인증 게이팅(생성 sc3f 와 동일)",
                  f"입력: 편집에서 원본/대상을 [/RUN/]/[/DSEC/] 로 수정 / "
                  f"결과: 차단메시지={msg!r}, 관리자비번 필드 표시={lic_vis}", sc=4,
                  highlight=page.page.locator(page.SEL_C_SOURCE),
                  repro="1. 레지변경 항목 편집\n2. 경로를 관리자 예약어로 변경\n3. 수정\n"
                        "4. '관리자 전용 예약어 감지' 차단 + 비밀번호 인증 필드 노출")
        self._add("warn",
                  "sc4m — [수동 확인 필요] 관리자 암호 인증 → 저장 → 설명 암호화 → 재오픈 복호화",
                  "관리자 암호가 필요한 구간이라 자동화 제외(안전규칙: 비밀번호 입력 금지). "
                  "게이팅 '존재'까지만 자동 검증됨 — 실제 인증 통과/암호화/복호화는 담당자가 관리자 암호로 수동 테스트해야 함. "
                  "(자동 pass 아님을 리포트에 남기기 위한 표식)", sc=4, screenshot=False,
                  merge_key="manual_admin_pw_crypto",   # sc3f(생성 컨텍스트) 동일 항목과 결함 카드 묶음
                  repro="1. 관리자 암호로 인증\n2. 저장 후 설명 암호화 확인\n3. 재오픈 → 복호화 버튼 → 암호로 복호화\n(모두 수동)")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario4n_i18n_sweep_in_modify(self, logged_in_page, settings):
        """수정 경로 검증 메시지 전수 — raw i18n 키(COLUMN.NAME... 류) 노출 없는지 (3o 생성판의 수정판)."""
        print("\n━━ [특수폴더] sc4n: 수정 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        _KEY = re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")   # 미번역 키 패턴(sc3o 와 동일)
        tpl = "[AUTO]_sz_mf_m4n"
        page.ensure_template(tpl, "SHORTCUT")
        msgs = {}
        page.open_modify_modal(tpl)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "")
        msgs["템플릿 이름 비움(수정)"] = page.submit_and_message()
        page._close_modal_if_open()
        self._ensure_folder_item(page, tpl, "i18n_item")
        page.open_folder_item_edit("i18n_item")
        page.fill(page.SEL_C_NAME, "")
        msgs["항목 설정명 비움(수정)"] = page.content_save_message()
        page.close_content_modal()
        page.close_folder_modal()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc4n — 수정 검증 메시지 i18n 키 노출 전수",
                  f"입력: 수정 경로 검증 메시지 수집 / 결과: {msgs} / 키 누출={leaks or '없음'}", sc=4,
                  repro="1. 수정 경로 검증 경고 유발(이름/설정명 비움)\n2. 메시지에 raw i18n 키 없는지")

    def test_scenario4o_path_overflow_in_modify(self, logged_in_page, settings):
        """수정 경로 3000자 오버플로 — 원본/대상 **요소별 개별 판정·카드**(sc3s 미러, 사용자 지시 2026-07-02).
        동일 결과는 merge_key 로 sc3s 카드와도 묶임. 실측 기대: raw '서버에서 오류'(사용자 발견)."""
        print("\n━━ [특수폴더] sc4o: 경로 오버플로(수정 컨텍스트, 요소별) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4o"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "povf_edit")
        big = "B" * 3000
        restore = {"원본위치": "[/DESKTOP/]", "대상위치": "[/MYDOC/]"}
        page.open_folder_item_edit("povf_edit")
        for elem, sel in (("원본위치", page.SEL_C_SOURCE), ("대상위치", page.SEL_C_TARGET)):
            page.set_content_path(sel, big)
            msg = page.content_save_message()
            saved = page.page.locator(page.SEL_C_NAME).count() == 0   # 내용 모달 닫힘 = 커밋됨
            if ("입력해" in msg) or ("초과" in msg):
                st, note = "pass", "명확한 경고로 차단(데이터 안전)"
            elif "서버" in msg:
                st, note = "warn", "raw 서버 오류 노출 — 클라 길이 가드 부재"
            else:
                st, note = "warn", "차단 없이 저장됨 — 확인 필요" if saved else "경고 없음·미커밋 — 확인 필요"
            # 라벨은 sc3s 와 동일 문구(prefix 만 다름) — 묶인 카드 제목 dedup 용(컨텍스트는 시나리오 배지가 구분)
            self._add(st, f"sc4o — {elem} 3000자 오버플로 → 처리",
                      f"입력: 편집에서 {elem} 3000자 + 수정 / 결과: 경고={msg!r}, 커밋={saved} / {note}", sc=4,
                      highlight=page.page.locator(sel),
                      merge_key=f"path_ovf::{elem}::{st}::{note}",   # sc3s(생성)의 같은 요소·같은 결과와만 묶임
                      repro=f"1. 폴더 항목 편집\n2. {elem}에 3000자\n3. 수정\n4. 경고 종류 확인(서버 오류면 검증 부재)")
            if saved:   # 3000자가 저장돼 버린 경우 재진입해 복구
                page.open_folder_item_edit("povf_edit")
                page.set_content_path(sel, restore[elem])
                page.content_save_message()
                page.open_folder_item_edit("povf_edit")
            else:       # 모달 열린 채 — 값만 복구
                page.set_content_path(sel, restore[elem])
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario4p_template_name_clamp_in_modify(self, logged_in_page, settings):
        """수정 모달에서도 템플릿 이름 clamp 유지되는지 (sc3t 미러 — 저장 안 함)."""
        print("\n━━ [특수폴더] sc4p: 템플릿 이름 글자수 clamp(수정 모달) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4p"
        page.ensure_template(tpl, "SHORTCUT")
        page.open_modify_modal(tpl)
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "A" * 35)
        self._add("pass" if accepted == 30 else "warn",
                  "sc4p — 템플릿 이름 글자수 clamp(수정 모달)",
                  f"입력: 수정 모달 이름에 35자 실타이핑 / 결과: 실제 수용 {accepted}자 (생성 sc3t 와 동일 30 기대)", sc=4,
                  highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 템플릿 수정 모달 이름에 35자 실타이핑\n2. 30자 clamp 유지되는지")
        page._close_modal_if_open()

    def test_scenario4q_folder_item_status_update(self, logged_in_page, settings):
        """폴더 항목 상태(활성→비활성) 수정 → 행 반영 (내용 모달 상태 radio — 검증 없던 필드 보강) + 원복."""
        print("\n━━ [특수폴더] sc4q: 폴더 항목 상태 수정 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4q"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "st_item")
        page.open_folder_item_edit("st_item")
        page.page.locator(f"{page.SEL_CONTENT_SHORTCUT} input#DELETE").first.evaluate("el => el.click()")
        msg = page.content_save_message()
        vals = " ".join(page.folder_row_values("st_item"))          # ① 행(리스트) 표시
        page.open_folder_item_edit("st_item")                        # ② 재오픈 로드 — 3점 대조
        reopen_del = page.page.locator(f"{page.SEL_CONTENT_SHORTCUT} input#DELETE").first.is_checked()
        # 원복(활성) — 열린 김에
        page.page.locator(f"{page.SEL_CONTENT_SHORTCUT} input#CREATE").first.evaluate("el => el.click()")
        page.content_save_message()
        ok = (msg.strip() == "") and ("비활성" in vals) and reopen_del
        self._add("pass" if ok else "fail",
                  "sc4q — 폴더 항목 상태(활성→비활성) 수정 → 행/재오픈 3점 대조",
                  f"입력: 항목 상태 비활성 + 수정 / 결과: 경고={msg!r}, 행값={vals!r}(비활성 기대), "
                  f"재오픈 비활성 checked={reopen_del}", sc=4,
                  highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr", has_text="st_item"),
                  repro="1. 항목 편집\n2. 상태 비활성\n3. 수정\n4. 행 상태 열 = 비활성\n5. 재오픈 → 비활성 유지")
        page.close_folder_modal()

    def test_scenario4r_content_name_special_char_rename(self, logged_in_page, settings):
        """항목 설정명을 특수문자로 rename (템플릿 rename sc4e 의 폴더판 — sc3u 미러)."""
        print("\n━━ [특수폴더] sc4r: 항목 설정명 특수문자 rename ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4r"
        page.ensure_template(tpl, "MODIFY_REGIST")   # 용도 분산 — 레지변경 항목 rename
        self._ensure_folder_item(page, tpl, "r_item")
        newname = "r_item<>!@#"
        page.open_folder_item_edit("r_item")
        page.fill(page.SEL_C_NAME, newname)
        msg = page.content_save_message()
        renamed = bool(page.folder_row_values(newname))
        self._add("pass" if renamed else "warn",
                  "sc4r — 항목 설정명 특수문자 rename",
                  f"입력: 'r_item' → '{newname}' / 결과: 경고={msg!r}, 변경됨={renamed} "
                  "(템플릿 rename sc4e 와 동일하게 허용 기대)", sc=4,
                  highlight=page.page.locator(f"{page.SEL_FOLDER_MODAL} tbody tr", has_text="r_item"),
                  repro="1. 항목 편집 설정명을 특수문자로\n2. 수정\n3. 허용/차단 여부")
        page.close_content_modal()
        page.close_folder_modal()
