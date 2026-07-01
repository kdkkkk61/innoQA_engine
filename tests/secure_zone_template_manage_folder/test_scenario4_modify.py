"""시큐어존 템플릿(특수폴더) — 시나리오 4: 수정 흐름.

표준(scenario_4_modify.md): 4-1 로드 / 4-2 수정 후 재확인 / 4-3 위반 저장값.
+ 사용자 지시: sc3 검증을 '수정 컨텍스트'로 미러 → 상태 의존 버그(생성 땐 되는데 수정 뒤 안 되는 등) 포착.
수집(2026-07-01): 템플릿 수정=행 선택+'수정'(이름/용도/상태 로드, 저장='수정') / 폴더 항목 수정='설정명' 링크 클릭(로드, 저장='수정').
※ 삭제(리스트 단위)=sc1/sc5. 여기 '폴더 항목 제거'는 모달 내 매핑 제거(수정 컨텍스트 재검증).

4a 템플릿 로드(4-1) / 4b 상태 수정=update+반영(4-2) / 4c 4-3 이름 비움 위반 저장값
4d rename 중복 차단 / 4e 특수문자 rename
4f 폴더 항목 로드+설명 update / 4g 폴더 항목 제거(수정 컨텍스트) / 4h 폴더 설명 오버플로(수정)
"""
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
        page.open_modify_modal(self._M4)
        delete_checked = page.page.locator(page.SEL_STATUS_DELETE).first.is_checked()
        ok = (cnt == 1) and delete_checked
        self._add("pass" if ok else "fail",
                  "sc4b — 상태 수정(활성→비활성) = update(중복 생성 아님) + 재확인",
                  f"입력: 상태 비활성 저장 / 결과: 동명 {cnt}개(기대 1=update), 재오픈 비활성 checked={delete_checked}", sc=4,
                  repro="1. 수정 모달\n2. 상태 비활성\n3. 수정 저장\n4. 재오픈 → 비활성 유지 + 중복 아님")
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
        page.ensure_template(tpl, "SHORTCUT")
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
        page.ensure_template(tpl, "SHORTCUT")
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
        """4-3 (필수 전부): 폴더 내용 필수(설정명/원본/대상)를 수정에서 각각 비우고 저장 → 전부 차단(데이터 안전)인지.
        실측(2026-07-01): 설정명/원본위치 각각 '~을 입력해 주세요.'로 차단, 미커밋. 빈값 저장되면 데이터 손상=fail."""
        print("\n━━ [특수폴더] sc4i: 폴더 내용 필수 비움(수정) 4-3 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_mf_m4i"
        page.ensure_template(tpl, "SHORTCUT")
        self._ensure_folder_item(page, tpl, "req_edit")
        page.open_folder_item_edit("req_edit")
        results = {}
        # 설정명 비움 → 저장
        page.fill(page.SEL_C_NAME, "")
        results["설정명"] = page.content_save_message()
        page.fill(page.SEL_C_NAME, "req_edit")            # 복구
        # 원본위치 비움 → 저장
        page.set_content_path(page.SEL_C_SOURCE, "")
        results["원본위치"] = page.content_save_message()
        page.set_content_path(page.SEL_C_SOURCE, "[/DESKTOP/]")  # 복구
        # 대상위치 비움 → 저장
        page.set_content_path(page.SEL_C_TARGET, "")
        results["대상위치"] = page.content_save_message()
        all_blocked = all("입력해" in (v or "") for v in results.values())
        self._add("pass" if all_blocked else "fail",
                  "sc4i — 폴더 내용 필수(설정명/원본/대상) 비움 수정 → 전부 차단(데이터 안전)",
                  f"입력: 각 필수 비우고 수정 / 결과: {results} "
                  + ("(전부 명확히 차단 — 빈값 저장 없음)" if all_blocked else "[일부 미차단 — 빈값 저장 위험]"), sc=4,
                  repro="1. 폴더 항목 편집\n2. 설정명/원본/대상 각각 비우고 수정\n3. 전부 필수 경고로 차단되는지")
        page.close_content_modal()
        page.close_folder_modal()
