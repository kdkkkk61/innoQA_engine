"""시큐어존 템플릿(프로세스) — 시나리오 3: 동작.

캡처 컨벤션 = docs/issue-screenshot-rules.md (특수폴더 sc3 레퍼런스와 동일):
  _add(status, ..., highlight=<이슈 요소 locator>) → base 가 fail/warn 에서만 빨간 crop 자동 캡처,
  pass/skip 은 캡처 없음. 저널(_ckpt/_act)·수동 _shot·screenshots= 미사용(임의 시스템 배제).

sc3a 타입별 생성 4종 / sc3b 동명 중복 스코프(같은 타입 차단·다른 타입 공존)
sc3c 등록(단일+다중, checkbox) / sc3d 인라인 옵션 토글(재시작) / sc3e 태그 등록 / sc3f 제거(개별+일괄)
sc3g 다중 중복 처리(부분/전체) / sc3h 이름(clamp·특수문자) / sc3i 설명(특수문자·장문)
sc3j ★미선택 필수 경고 4타입 전수 / sc3k ★등록+옵션 4타입 전수 / sc3l 설명 3000자 오버플로 4타입
sc3m ★저장값 roundtrip(예외처리 옵션·설명 설정→저장→재오픈 일치 — 특수폴더 sc3k 미러)
sc3n ★여러 프로세스 등록·활용(서로 다른 3개 등록→각 이름 검증→행별 옵션 개별 적용→1개 부분 제거)
sc3o ★검색 등록(picker 검색 필터 동작 — '[AUTO' seed 있으면 확인 + 'notepad' 무조건 존재로 안정 검증)
sc3p 리스트 필터(타입 4종 변별 — sync sc3p 위임분 + 상태) / sc3q 복사(_copy·★딥카피·충돌)
sc3r L2 등록항목 검색(정확·부분·빈검색 복귀 — 부분 일치 일관성 수집) / sc3s i18n sweep
※ 등록 picker=checkbox plain click(실측). L3 타입별 모달 별개 → 타입 종속 검증은 4타입 전수.
※ seed 연계는 sc6. sc2=속성(maxlength 존재·초기값), sc3=실제 동작.
"""
import re

from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario3Action(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 3: 동작."""

    _DUP = "[AUTO]_sz_proc_dup"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ── sc3a: 타입별 생성 4종 전수 ──────────────────────────────────
    def test_scenario3a_create_by_type(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3a: 타입별 생성 4종 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            name = f"[AUTO]_sz_proc_3a_{ttype.split('_')[0].lower()}"
            if name in page.get_template_names():
                page.delete_template(name)
                page.navigate_to()
            page.create_template(name, ttype)
            page.navigate_to()
            created = name in page.get_template_names()
            row_type = page.row_type_text(name)
            self._add("pass" if (created and ko in row_type) else "fail",
                      f"sc3a — {ko} 생성 → 리스트 등장 + 타입 컬럼",
                      f"입력: 이름+{ko} 저장 / 결과: 생성={created}, 타입 표시={row_type!r}", sc=3,
                      highlight=(page._row_locator(name) if created else None),
                      repro=f"1. 템플릿 추가\n2. 이름+{ko} 선택\n3. 확인\n4. 리스트 타입 컬럼 확인")

    # ── sc3b: 동명 중복 스코프 (같은 타입 차단 / 다른 타입 공존) ─────
    def test_scenario3b_duplicate_scope(self, logged_in_page, settings):
        """★핵심 = 같은 타입 내 동명 차단(부여가 타입별). 부수 = 다른 타입 동명 공존(경고 가치)."""
        print("\n━━ [프로세스] sc3b: 동명 중복 스코프 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        while self._DUP in page.get_template_names():
            page.delete_template(self._DUP)
            page.navigate_to()
        page.create_template(self._DUP, "ALLOW_PROCESS")
        page.navigate_to()
        NAME = f"{page.SEL_MODAL} {page.SEL_NAME}"

        # ① 같은 타입 동명 재생성 → 차단 기대
        page.open_add_modal()
        page.fill(NAME, self._DUP)
        msg_same = page.submit_and_message()
        page._close_modal_if_open()
        blocked_same = "이미 등록" in msg_same
        self._add("pass" if blocked_same else "warn",
                  "sc3b — ★같은 타입 동일 이름 차단 (핵심 검증)",
                  f"입력: 허용 타입 동명 재생성 / 결과: 경고={msg_same!r} "
                  + ("(차단 정상)" if blocked_same
                     else "[차단 안 됨 — 같은 타입 내 동명 허용, 부여 시 구분 불가]"), sc=3,
                  highlight=page.page.locator(NAME),
                  merge_key=(None if blocked_same else "szproc_dup::same_type::warn::no_dup_check"),
                  repro="1. 허용 타입 템플릿 생성\n2. 같은 이름+같은 타입 재생성\n"
                        "3. '이미 등록된 이름' 차단되어야 — 부여 UI 가 타입별이라 동명이면 혼란")

        # ② 다른 타입 동명 생성 → 공존 여부
        page.navigate_to()
        page.open_add_modal()
        page.fill(NAME, self._DUP)
        page.select_type("DENY_PROCESS")
        msg_diff = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        page.search(self._DUP)
        count = page.get_template_names().count(self._DUP)
        coexist = count >= 2
        self._add("warn" if coexist else "pass",
                  "sc3b — 다른 타입 동일 이름 공존 (정상 범주 · 경고 가치)",
                  f"입력: 거부 타입 동명 생성 / 결과: 경고={msg_diff!r}, 동명 {count}개 "
                  + ("[타입 다르면 공존 허용 — 중복 검사가 타입 스코프. 부여 목록에 동명 노출 가능(경고 가치)]"
                     if coexist else "(전역 차단 — 공존 안 됨)"), sc=3,
                  highlight=page.page.locator("table tbody"),
                  merge_key=("szproc_dup::cross_type::warn::type_scoped_name_check" if coexist else None),
                  repro="1. 허용 타입으로 만든 이름 그대로\n2. 거부 타입 선택 후 저장\n3. 동명 2개 공존 확인")
        page.search("")
        while self._DUP in page.get_template_names():
            page.delete_template(self._DUP)
            page.navigate_to()

    # ── sc3c: 개별 프로세스 등록 — 단일 + 다중 (checkbox picker) ─────
    def test_scenario3c_register_single_multi(self, logged_in_page, settings):
        """picker=checkbox → 다중 선택 한 번에 N개 등록(실측). 단일 1건 + 다중 3건 → L2 반영."""
        print("\n━━ [프로세스] sc3c: 개별 프로세스 등록(단일+다중) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3c"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        L2_BODY = f"{page.SEL_L2_MODAL} tbody"

        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        picked1 = page.l3_register("ALLOW_PROCESS", count=1)
        msg1 = page.l3_add_message("ALLOW_PROCESS")
        cnt1 = page.l2_item_count()
        self._add("pass" if (len(picked1) == 1 and msg1 == "" and cnt1 == 1) else "fail",
                  "sc3c — 단일 프로세스 등록 → L2 1건",
                  f"입력: {picked1} 선택+추가 / 결과: 경고={msg1!r}, L2={cnt1}건", sc=3,
                  highlight=page.page.locator(L2_BODY),
                  repro="1. L2 + → picker 1개 체크\n2. 확인 → 추가\n3. L2 1행")

        page.open_l3_add("ALLOW_PROCESS")
        picked3 = page.l3_register("ALLOW_PROCESS", count=3)
        shown = page.l3_selected_name("ALLOW_PROCESS")
        msg3 = page.l3_add_message("ALLOW_PROCESS")
        cnt_after = page.l2_item_count()
        skip_dup = ("생략" in msg3) or ("이미 등록" in msg3)
        multi_ok = (len(picked3) == 3) and ("외" in shown) and (cnt_after >= 2)
        self._add("pass" if multi_ok else "fail",
                  "sc3c — 다중 프로세스 등록(한 번에 N개) → L2 반영",
                  f"입력: {len(picked3)}개 선택({shown!r}) + 추가 / 결과: L2 총 {cnt_after}건"
                  + (f" (중복 생략 안내='{msg3}' — 정상)" if skip_dup else ""), sc=3,
                  highlight=page.page.locator(L2_BODY),
                  repro="1. L2 + → picker 여러 개 체크\n2. 확인 → 'N개 외' 표시\n3. 추가 → 다건 등록")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3d: 인라인 옵션 토글 (허용=재시작) ────────────────────────
    def test_scenario3d_inline_option_toggle(self, logged_in_page, settings):
        """등록 행 옵션 버튼(허용=재시작)을 L2 목록에서 인라인 토글 → 편집 재오픈으로 반영 확인."""
        print("\n━━ [프로세스] sc3d: 인라인 옵션 토글(허용 재시작) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3d"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=1)
        page.l3_add_message("ALLOW_PROCESS")
        before = page.l2_option_on(0)
        after = page.l2_toggle_option(0)
        opt_btn = page.l2_rows()[0].locator("td").nth(3).locator("button").first
        page.l2_open_item_edit(0)
        restart_loaded = page.l3_scope("ALLOW_PROCESS").locator("input#isProcessRestart").first.is_checked()
        page.close_l3_modal("ALLOW_PROCESS")
        ok = (before != after) and (restart_loaded == after)
        self._add("pass" if ok else "warn",
                  "sc3d — L2 인라인 옵션(재시작) 토글 → 편집 로드값 반영",
                  f"입력: 옵션 버튼 클릭 / 결과: 표시 {before}→{after}, 편집 로드 restart={restart_loaded}", sc=3,
                  highlight=opt_btn,
                  repro="1. 프로세스 등록\n2. L2 행 옵션 버튼 클릭(재시작 토글)\n3. 이름 링크 편집 → restart 반영")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3e: 태그 등록 (첫 태그) ───────────────────────────────────
    def test_scenario3e_tag_register(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3e: 태그 등록(기본) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3e"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.switch_l2_tab("태그")
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS", tag=True, count=1)
        shown = page.l3_selected_name("ALLOW_PROCESS")
        msg = page.l3_add_message("ALLOW_PROCESS")
        cnt = page.l2_item_count()
        ok = bool(picked) and (msg == "") and (cnt >= 1)
        self._add("pass" if ok else "fail",
                  "sc3e — 태그 등록 → L2 태그 탭 반영",
                  f"입력: 태그 {shown!r} 선택+추가 / 결과: 경고={msg!r}, 태그 탭 {cnt}건", sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. L2 태그 탭 → + → L3\n2. 태그 선택(체크)\n3. 추가 → 태그 탭 반영")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3f: 제거 — 개별 1건 + 헤더 전체선택 일괄 ──────────────────
    def test_scenario3f_remove_single_bulk(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3f: 제거(개별 + 일괄) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3f"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=3)
        page.l3_add_message("ALLOW_PROCESS")
        start = page.l2_item_count()
        msg1 = page.l2_remove_item(0)
        mid = page.l2_item_count()
        self._add("pass" if ("삭제 하시겠습니까" in msg1 and mid == start - 1) else "fail",
                  "sc3f — 개별 행 제거 → -1",
                  f"입력: 1행 체크+제거 / 결과: 확인={msg1!r}, {start}→{mid}건", sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 등록 3건\n2. 1행 체크 + - 버튼\n3. 삭제 확인 → 1건 감소")
        msg2 = page.l2_bulk_remove()
        end = page.l2_item_count()
        self._add("pass" if end == 0 else "fail",
                  "sc3f — 헤더 전체선택 → 일괄 제거 → 0건",
                  f"입력: 전체선택 + 제거 / 결과: 확인={msg2!r}, {mid}→{end}건", sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 헤더 체크(전체선택)\n2. - 버튼\n3. 전부 제거")
        page.close_l2_modal()

    # ── sc3g: 다중 등록 중복 처리 — 부분 / 전체 ─────────────────────
    def test_scenario3g_multi_dup_handling(self, logged_in_page, settings):
        """A 등록 후 A+B+C 선택 추가 → 겹치는 A만 생략, B·C 등록(전부 거부 아님). 전체 겹침=카운트 불변."""
        print("\n━━ [프로세스] sc3g: 다중 등록 중복 처리(부분/전체) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3g"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        L2_BODY = f"{page.SEL_L2_MODAL} tbody"
        page.open_l2_modal(tpl)

        page.open_l3_add("ALLOW_PROCESS")
        a = page.l3_register("ALLOW_PROCESS", count=1)
        page.l3_add_message("ALLOW_PROCESS")
        base = page.l2_item_count()

        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=3)
        msg = page.l3_add_message("ALLOW_PROCESS")
        page.close_l3_modal("ALLOW_PROCESS")
        partial = page.l2_item_count()
        skip_only_dup = (a and a[0].split()[0] in msg) and (partial == base + 2)
        self._add("pass" if skip_only_dup else "warn",
                  "sc3g — 부분 중복 다중 등록: 겹치는 것만 생략, 나머지 등록",
                  f"입력: 기존 {base}건 + 겹침 포함 3개 선택 / 결과: 안내={msg!r}, 최종 {partial}건 "
                  + ("(겹치는 1건만 생략, 2건 신규 — 정상)" if skip_only_dup else "[예상(base+2)과 다름]"), sc=3,
                  highlight=page.page.locator(L2_BODY),
                  repro="1. A 1건 등록\n2. A+B+C 다중 선택 후 추가\n3. A만 생략, B·C 등록(전부 거부 아님)")

        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=2)
        msg2 = page.l3_add_message("ALLOW_PROCESS")
        page.close_l3_modal("ALLOW_PROCESS")
        alldup = page.l2_item_count()
        self._add("pass" if (("생략" in msg2 or "이미 등록" in msg2) and alldup == partial) else "warn",
                  "sc3g — 전체 중복 다중 등록: 전부 생략, 카운트 불변",
                  f"입력: 이미 등록된 2건 재선택 / 결과: 안내={msg2!r}, {partial}→{alldup}건", sc=3,
                  highlight=page.page.locator(L2_BODY),
                  repro="1. 등록된 것만 재선택 후 추가\n2. 전부 생략, 카운트 변동 없음")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3h: templateName 직접입력 — clamp / 특수문자 ──────────────
    def test_scenario3h_templatename_input(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3h: templateName clamp/특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "a" * 60)
        self._add("pass" if accepted == 30 else "warn",
                  "sc3h — 이름 실타이핑 60자 → clamp 30",
                  f"입력: 60자 타이핑 / 결과: 수용={accepted}자 (maxlength=30 클라 가드)", sc=3,
                  highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 이름 60자 타이핑\n2. 수용 길이 30 확인")
        page._close_modal_if_open()
        sp = "[AUTO]_sz_proc_sp<>!@#"
        if sp in page.get_template_names():
            page.delete_template(sp); page.navigate_to()
        msg = page.create_template(sp)
        page.navigate_to()
        created = sp in page.get_template_names()
        self._add("pass" if created else "warn",
                  "sc3h — 이름 특수문자 생성(허용 여부)",
                  f"입력: '{sp}' / 결과: 경고={msg!r}, 생성={created} (실측: 형식 검사 없음, 허용)", sc=3,
                  highlight=(page._row_locator(sp) if created else None),
                  repro="1. 이름에 특수문자(<>!@#)\n2. 확인\n3. 허용/차단")

    # ── sc3i: L3 설명 직접입력 — 특수문자 / 장문 수용 ───────────────
    def test_scenario3i_description_input(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3i: L3 설명 특수문자/장문 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3i"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        scope = page.l3_scope("ALLOW_PROCESS")
        desc_sel = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        ml = scope.locator(page.SEL_L3_DESC).first.get_attribute("maxlength")
        sp = "설명<>&!@# 특수"
        page.fill(desc_sel, sp)
        sp_back = scope.locator(page.SEL_L3_DESC).first.input_value()
        self._add("pass" if sp_back == sp else "warn",
                  "sc3i — L3 설명 특수문자 수용(재읽기)",
                  f"입력: {sp!r} / 재읽기: {sp_back!r}, maxlength={ml!r}(서버측)", sc=3,
                  highlight=scope.locator(page.SEL_L3_DESC))
        page.fill(desc_sel, "가" * 500)
        long_back = len(scope.locator(page.SEL_L3_DESC).first.input_value())
        self._add("pass" if long_back == 500 else "warn",
                  "sc3i — L3 설명 장문 500자 수용(클라 제한 없음)",
                  f"입력: 500자 / 재읽기: {long_back}자 (maxlength=None — 서버 측 처리)", sc=3,
                  highlight=scope.locator(page.SEL_L3_DESC),
                  repro="1. L3 설명 500자\n2. 재읽기 500(클라 제한 없음)")
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()

    # ── sc3j: ★필수(미선택) 경고 — 4타입 전수 ───────────────────────
    def test_scenario3j_required_sweep_by_type(self, logged_in_page, settings):
        """L3 모달은 타입마다 별개 → 미선택 추가 시 필수 경고 4타입 전수(사용자 통찰).
        실측(2026-07-08): 허용/예외/차단='프로세스를 선택해 주세요' / 거부=경고 없음 → 거부 필수 검증 누락."""
        print("\n━━ [프로세스] sc3j: 필수(미선택) 경고 4타입 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = f"[AUTO]_sz_proc_3j_{ttype.split('_')[0].lower()}"
            # 행위 저널(§5.1) — warn(거부 무반응) 검출 시 블록 자동 재생·캡션
            self._ckpt()
            self._act(f"{ko} 템플릿 → + → L3",
                      lambda tpl=tpl, ttype=ttype: (
                          page.navigate_to_clean(), page.ensure_template(tpl, ttype),
                          page.open_l2_modal(tpl), page.open_l3_add(ttype)))
            self._act("프로세스 미선택 상태로 추가 → 필수 경고 기대",
                      lambda ttype=ttype: page.l3_click_add_wait(ttype))
            msg = page.get_modal_message() if page.is_confirm_modal_visible() else ""
            warned = ("선택" in msg) or ("프로세스를" in msg)
            self._add("pass" if warned else "warn",
                      f"sc3j — {ko}: 미선택 추가 → 필수 경고",
                      f"입력: 프로세스 미선택 + 추가 / 결과: 경고={msg!r} "
                      + ("(정상 — 필수 경고)" if warned
                         else "[★필수 경고 누락 — 다른 타입은 경고 뜨는데 이 타입만 무반응]"), sc=3,
                      merge_key=(None if warned
                                 else f"szproc_required_missing::{ttype}::warn::no_required_alert"),
                      repro=f"1. {ko} 템플릿 L2 → + → L3\n2. 프로세스 미선택 상태로 추가\n"
                            "3. '프로세스를 선택해 주세요' 경고 떠야 정상(타입별 상이 주의)")
            page.dismiss_alert()
            page.close_l3_modal(ttype)
            page.close_l2_modal()

    # ── sc3k: ★타입별 등록 + 옵션 표시 전수 ─────────────────────────
    def test_scenario3k_register_option_by_type(self, logged_in_page, settings):
        """4타입 각각 등록 → L2 옵션 셀이 타입별로 다른지 전수.
        실측: 허용=재시작 / 예외=시큐어드라이브+반출드라이브+재시작 / 거부·차단=옵션 없음."""
        print("\n━━ [프로세스] sc3k: 타입별 등록+옵션 표시 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = f"[AUTO]_sz_proc_3k_{ttype.split('_')[0].lower()}"
            expect = page.L2_OPTION_BTNS[ttype]
            page.navigate_to_clean()
            page.ensure_template(tpl, ttype)
            page.open_l2_modal(tpl)
            page.open_l3_add(ttype)
            picked = page.l3_register(ttype, count=1)
            msg = page.l3_add_message(ttype)
            cnt = page.l2_item_count()
            opts = page.l2_option_buttons(0) if cnt >= 1 else []
            reg_ok = bool(picked) and (msg == "") and (cnt == 1)
            opt_ok = set(opts) == set(expect)
            self._add("pass" if (reg_ok and opt_ok) else "fail",
                      f"sc3k — {ko}: 등록 + 옵션 표시(타입 전용)",
                      f"입력: {ko} 템플릿에 프로세스 1건 등록 / 결과: 등록={cnt}건, "
                      f"옵션 버튼={opts} (기대 {expect}) 일치={opt_ok}", sc=3,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      repro=f"1. {ko} 템플릿 L2 → + → 프로세스 선택 → 추가\n"
                            f"2. L2 행 옵션 셀 = {expect or '없음'}(타입 전용) 확인")
            page.l2_bulk_remove()
            page.close_l2_modal()

    # ── sc3l: 설명 3000자 오버플로 — 4타입 전수(수집) ───────────────
    def test_scenario3l_description_overflow_by_type(self, logged_in_page, settings):
        """설명 3000자 저장 시 서버 처리를 4타입 전수 수집(L3 별개). maxlength=None(서버측).
        raw 서버오류면 warn(클라 길이 가드 부재). 오버플로 시 특수폴더 sc3s 처럼 2컷 재현 캡처."""
        print("\n━━ [프로세스] sc3l: 설명 3000자 오버플로 4타입 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = f"[AUTO]_sz_proc_3l_{ttype.split('_')[0].lower()}"
            desc_sel = f"div#{page.L3_MAP[ttype]}.in {page.SEL_L3_DESC}"
            # 행위 저널(§5.1) — raw 서버오류(warn) 시 [진입·선택 → 설명 3000자 → 추가·오류] 자동 재생
            self._ckpt()
            self._act(f"{ko} → + → L3 → 프로세스 선택",
                      lambda tpl=tpl, ttype=ttype: (
                          page.navigate_to_clean(), page.ensure_template(tpl, ttype),
                          page.open_l2_modal(tpl), page.open_l3_add(ttype),
                          page.l3_register(ttype, count=1)))
            self._act("설명 3000자 입력",
                      lambda desc_sel=desc_sel: page.fill(desc_sel, "가" * 3000),
                      shot_target=page.l3_scope(ttype).locator(page.SEL_L3_DESC))
            before = page.l2_item_count()
            self._act("추가 → 서버 처리(알림/커밋)",
                      lambda ttype=ttype: page.l3_click_add_wait(ttype))
            msg = page.get_modal_message() if page.is_confirm_modal_visible() else ""
            after = page.l2_item_count()
            committed = after == before + 1
            raw_err = ("서버" in msg and "오류" in msg)
            guard = ("자" in msg or "길이" in msg or "초과" in msg) and not raw_err
            st = "warn" if raw_err else "pass"
            self._add(st,
                      f"sc3l — {ko}: 설명 3000자 → 저장 처리"   # 라벨 본문 = sc4i 와 동일(미러 dedup),
                      f"입력: 설명 3000자 + 추가 / 결과: 경고={msg!r}, 커밋={committed} "
                      + ("[raw 서버 오류 — 클라 길이 가드 부재]" if raw_err
                         else "(길이 가드 안내)" if guard else "(제한 없이 커밋)"), sc=3,
                      merge_key=(f"szproc_desc_ovf::{ttype}" if raw_err else None),   # 요소(타입)별 카드 — sc4i(수정)와 세로 병합
                      repro=f"1. {ko} L3 프로세스 선택 + 설명 3000자\n2. 추가\n3. 서버 처리 결과 확인")
            page.dismiss_alert()
            # ★서버 오류 후 정상값 재시도(복구) — 실측(14:29 run 진단 DUMP): 오류 확인을
            #   닫으면 앱이 L3+L2 모달 스택 **전체를 닫음**(open_modals=[]) → 같은 세션
            #   재시도 불가, 재진입으로 재시도. (첫 구현이 L3 유지 가정으로 timeout — 교정)
            if raw_err:
                page.navigate_to_clean()
                page.open_l2_modal(tpl)
                before2 = page.l2_item_count()
                page.open_l3_add(ttype)
                page.l3_register(ttype, count=1)
                page.fill(desc_sel, "ovf_recover")
                msg2 = page.l3_add_message(ttype)
                cnt2 = page.l2_item_count()
                recovered = cnt2 == before2 + 1
                self._add("pass" if recovered else "warn",
                          f"sc3l — {ko}: 서버 오류 후 재진입 정상값 재시도 → 등록 복구",
                          f"입력: 재진입 후 설명 'ovf_recover' 등록({msg2!r}) / "
                          f"결과: {before2}→{cnt2}건, 복구={recovered}"
                          + ("" if recovered else " [오류 후 정상 등록 불가 — 시스템 상태 오염]")
                          + " (관찰: 서버 오류 확인 시 앱이 모달 스택 전체를 닫음)",
                          sc=3, highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                          repro=f"1. {ko} 설명 3000자 → 서버 오류 → 확인(모달 전체 닫힘)\n"
                                "2. 재진입 후 정상 설명으로 등록\n3. 정상 등록되는지")
            page.close_l3_modal(ttype)
            page.l2_bulk_remove()
            page.close_l2_modal()

    # ── sc3m: ★저장값 roundtrip — 예외처리 옵션·설명 (설정→저장→재오픈 일치) ──
    def test_scenario3m_saved_value_roundtrip(self, logged_in_page, settings):
        """사용자 질문: 설정한 옵션이 일치하게 오는지. 특수폴더 sc3k(저장값 roundtrip) 미러.
        예외처리(옵션 최다)로 비기본값 설정(시큐어=차단/반출=허용/재시작 ON/설명) → 추가 →
        이름 링크 재오픈 → 로드값 일치 검증. 불일치=저장/로드 손실 결함."""
        print("\n━━ [프로세스] sc3m: 저장값 roundtrip(예외처리 옵션·설명) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3m"
        page.navigate_to_clean()
        page.ensure_template(tpl, "EXCEPT_PROCESS")
        page.open_l2_modal(tpl)
        page.open_l3_add("EXCEPT_PROCESS")
        page.l3_register("EXCEPT_PROCESS", count=1)
        scope = page.l3_scope("EXCEPT_PROCESS")
        # 비기본값 설정 (변경 적용 검증) — 시큐어=차단 / 반출=허용 / 재시작 ON / 설명
        scope.locator("input[name='isSecureDriveWrite']#BLOCK").first.evaluate("el => el.click()")
        scope.locator("input[name='isTakeoutDriveWrite']#ALLOW").first.evaluate("el => el.click()")
        rst = scope.locator("input#isProcessRestart").first
        if not rst.is_checked():
            rst.evaluate("el => el.click()")
        page.fill(f"div#{page.L3_MAP['EXCEPT_PROCESS']}.in {page.SEL_L3_DESC}", "rt_except_desc")
        page.page.wait_for_timeout(200)
        page.l3_add_message("EXCEPT_PROCESS")   # 저장(커밋)

        # 이름 링크 재오픈 → 로드값 대조
        page.l2_open_item_edit(0)
        sc2 = page.l3_scope("EXCEPT_PROCESS")
        loaded = {
            "시큐어드라이브=차단": sc2.locator("input[name='isSecureDriveWrite']#BLOCK").first.is_checked(),
            "반출드라이브=허용":   sc2.locator("input[name='isTakeoutDriveWrite']#ALLOW").first.is_checked(),
            "재시작 ON":           sc2.locator("input#isProcessRestart").first.is_checked(),
            "설명":               sc2.locator(page.SEL_L3_DESC).first.input_value() == "rt_except_desc",
        }
        page.close_l3_modal("EXCEPT_PROCESS")
        ok = all(loaded.values())
        self._add("pass" if ok else "warn",
                  "sc3m — 예외처리 저장값 roundtrip(옵션·설명 설정→재오픈 일치)",
                  f"입력: 시큐어=차단/반출=허용/재시작 ON/설명 저장 후 재오픈 / 결과: {loaded} 전부일치={ok}"
                  + ("" if ok else " [★설정값이 재오픈 시 손실/불일치 — 저장 또는 로드 결함]"), sc=3,
                  highlight=page.l2_rows()[0] if page.l2_rows() else None,
                  merge_key=(None if ok else "szproc_roundtrip::except_options::warn::value_lost"),
                  repro="1. 예외처리 L3 — 드라이브 권한 비기본값+재시작+설명 설정\n2. 추가(저장)\n"
                        "3. 이름 링크로 재오픈 → 설정값 그대로 로드되는지")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3n: ★여러 프로세스 등록해서 활용 (카운트 아닌 개별 검증) ──────
    def test_scenario3n_multi_register_operate(self, logged_in_page, settings):
        """사용자 지시(2026-07-09): '여러 프로세스 등록해서 무언가 하는' 시나리오.
        카운트만이 아니라 — 서로 다른 3개 등록 → 각 이름 그대로 반영 → 행별 다른 옵션
        (L2 인라인 재시작 0행만 ON) 개별 적용 → 1개만 부분 제거 → 나머지 유지 확인."""
        print("\n━━ [프로세스] sc3n: 여러 프로세스 등록·활용 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3n"
        page.navigate_to_clean()
        page.ensure_template(tpl)   # ALLOW (재시작 옵션 보유 타입)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS", count=3)   # 서로 다른 3개(picker 앞 3행)
        page.l3_add_message("ALLOW_PROCESS")

        # ① 등록 개수 + 각 이름 그대로 반영 (카운트만 아님)
        names = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        each_ok = len(picked) == 3 and all(
            any(p in n or n in p for n in names) for p in picked)
        cnt = page.l2_item_count()
        self._add("pass" if (cnt == 3 and each_ok) else "fail",
                  "sc3n — 서로 다른 프로세스 3개 등록 → 각 이름 그대로 반영",
                  f"입력: {picked} 등록 / 결과: L2 {cnt}행, 이름={names}, 전수일치={each_ok}", sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. L2 + → picker 서로 다른 3개 체크\n2. 추가\n"
                        "3. L2 3행 각 이름이 선택한 프로세스와 일치")

        # ② 행별 다른 옵션 개별 적용 — 0행 재시작 ON, 1행 미변경(OFF) 유지
        on0 = page.l2_toggle_option(0)     # 0행 토글 → ON 기대
        off1 = page.l2_option_on(1)        # 1행 미변경 → OFF 기대
        per_row_ok = on0 and not off1
        self._add("pass" if per_row_ok else "warn",
                  "sc3n — 등록된 여러 행에 서로 다른 옵션 개별 적용(0행만 재시작 ON)",
                  f"결과: 0행 재시작={on0}(ON 기대), 1행 재시작={off1}(OFF 기대), 독립={per_row_ok}"
                  + ("" if per_row_ok else " [행별 옵션이 독립 적용 안 됨 — 한 토글이 타 행에 전파/미반영]"),
                  sc=3, highlight=page.l2_rows()[0].locator("td").nth(3),
                  merge_key=(None if per_row_ok else "szproc_multi::per_row_option::warn::not_independent"),
                  repro="1. 3행 등록 상태\n2. 0행 옵션(재시작) 클릭\n3. 0행만 ON, 1행 OFF 유지")

        # ③ 여러 등록 중 1개만 부분 제거 → 나머지 유지 (지운 것만 사라짐)
        target = page.l2_rows()[1].locator("td").nth(1).inner_text().strip()
        page.l2_remove_item(1)
        remain = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        removed_ok = page.l2_item_count() == 2 and not any(
            (target in r or r in target) for r in remain)
        self._add("pass" if removed_ok else "fail",
                  "sc3n — 여러 등록 중 1개만 부분 제거 → 나머지 유지",
                  f"제거 대상={target!r} / 결과: 남은 {page.l2_item_count()}행={remain}, 대상제거={removed_ok}",
                  sc=3, highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 3행 중 1행 체크(-) 제거\n2. 2행 남고 지운 프로세스만 사라졌는지")

        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3o: ★검색 등록 — picker 검색 필터 동작 검증 ('[AUTO' seed / notepad) ──
    def test_scenario3o_register_by_search(self, logged_in_page, settings):
        """검색이 실제로 필터하고, 검색 결과에서 선택·등록되는지 (검색 기능 검증 = 생성 영역).
        순서(사용자 지시 2026-07-09): ① '[AUTO' 검색 — 상위 seed 있으면 검색 동작 확인(있을 때만).
        ② 'notepad' 검색 — 무조건 존재하는 프로세스라 검색 필터·등록 안정 확정.
        picker 1253건이라 검색이 안 되면 대상이 1페이지(20행)에 없어 못 찾음 → fail 로 드러남."""
        print("\n━━ [프로세스] sc3o: 검색 등록(필터 동작) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3o"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)

        # ① '[AUTO' 검색 — seed 있으면 검색 동작 확인
        page.open_l3_add("ALLOW_PROCESS")
        auto = page.l3_register("ALLOW_PROCESS", search_term="[AUTO",
                                name_pattern=re.compile(r"\[AUTO"))
        if auto:
            page.l3_add_message("ALLOW_PROCESS")
            self._add("pass", "sc3o — '[AUTO' 검색 등록 (대량 목록에서 검색으로 정확 선택)",
                      f"검색 '[AUTO' → {auto} 등록 (검색 필터 동작 확인)", sc=3,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      repro="1. picker '[AUTO' 검색\n2. 검색 결과에서 선택·추가\n3. 등록 확인")
        else:
            page.close_l3_modal("ALLOW_PROCESS")
            self._add("skip", "sc3o — '[AUTO' 검색 (일치 항목 없음)",
                      "상위 [AUTO_<date>]_cm_* seed 미존재 run → notepad 로 검색 검증 계속.", sc=3)

        # ② 'notepad' 검색 — 무조건 존재(안정 검증)
        page.open_l3_add("ALLOW_PROCESS")
        npd = page.l3_register("ALLOW_PROCESS", search_term="notepad",
                               name_pattern=re.compile(r"notepad", re.I))
        if npd:
            page.l3_add_message("ALLOW_PROCESS")
        else:
            page.close_l3_modal("ALLOW_PROCESS")
        names = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        found = bool(npd) and any("notepad" in n.lower() for n in names)
        self._add("pass" if found else "fail",
                  "sc3o — 'notepad' 검색 등록 (검색 필터 확정)",
                  f"검색 'notepad' → {npd} 등록 / L2 이름={names}, 검색등록={found}"
                  + ("" if found else " [검색이 필터 못 함 — 대량 목록에서 notepad 미발견]"), sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. picker 'notepad' 검색\n2. 검색 결과(notepad.exe) 선택·추가\n3. L2 등록 확인")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3p: 리스트 필터 (타입 4종 변별 + 상태) — sync sc3p 가 이 탭에 위임 ──
    def test_scenario3p_list_filters(self, logged_in_page, settings):
        """타입 필터 변별 — 타입 컬럼 있는 유일한 탭(sc1b 예고). 각 타입 선택 → 결과 전부
        그 타입인지(uniq). 상태 필터(활성)도 반영 확인. 실측: filter_by(JS change+검색) 동작."""
        print("\n━━ [프로세스] sc3p: 리스트 필터(타입/상태) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        # 4타입 존재 보장
        for ttype in page.TYPES:
            page.ensure_template(f"[AUTO]_sz_proc_3p_{ttype.split('_')[0].lower()}", ttype)

        bad = {}
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            page.filter_by(template_type=ko)
            uniq = sorted(set(page.list_type_values()))
            if uniq != [ko]:
                bad[ko] = uniq
        page.filter_by(template_type="전체")
        self._add("pass" if not bad else "fail",
                  "sc3p — 타입 필터 4종 변별 (결과 전부 해당 타입)",
                  f"입력: 타입 필터 4종 각각 선택+검색 / 결과: "
                  + ("4종 모두 해당 타입만 표시" if not bad else f"불일치={bad}"), sc=3,
                  highlight=page.page.locator("table tbody"),
                  repro="1. 타입 드롭다운 선택\n2. 검색\n3. 타입 컬럼 전부 해당 타입인지 (4종 반복)")

        page.filter_by(status="활성")
        status_vals = page.page.locator("table tbody").first.evaluate(
            "tb => [...tb.querySelectorAll('tr')]"
            ".map(r => (r.cells && r.cells.length > 4) ? r.cells[4].innerText.trim() : '')"
            ".filter(t => t)")
        status_ok = bool(status_vals) and all(v == "활성" for v in status_vals)
        page.filter_by(status="상태")   # 리셋
        self._add("pass" if status_ok else "fail",
                  "sc3p — 상태 필터(활성) → 결과 반영",
                  f"입력: 상태=활성 + 검색 / 결과: {len(status_vals)}행, 전부 활성={status_ok}", sc=3,
                  highlight=page.page.locator("table tbody"),
                  repro="1. 상태 드롭다운=활성\n2. 검색\n3. 상태 컬럼 전부 활성")

    # ── sc3q: 템플릿 복사 — _copy 생성 + ★L2 내용(카운트) 복제 + 충돌 ──
    def test_scenario3q_copy(self, logged_in_page, settings):
        """실측(2026-07-09): 복사 → '<이름>_copy', 프로세스/태그 카운트까지 딥카피(1/1→1/1).
        analog: sync sc3f/sc3m. 충돌(재복사 시 동명 _copy 중복)도 동일 클래스 확인."""
        print("\n━━ [프로세스] sc3q: 템플릿 복사(+카운트 복제/충돌) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3q"
        copy_name = tpl + "_copy"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        # 내용 1건 등록(카운트 복제 검증용)
        page.open_l2_modal(tpl)
        if page.l2_item_count() == 0:
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_register("ALLOW_PROCESS", count=1)
            page.l3_add_message("ALLOW_PROCESS")
        page.close_l2_modal()
        while copy_name in page.get_template_names():
            page.delete_template(copy_name)
            page.navigate_to()

        page.copy_template(tpl)
        page.navigate_to()
        copied = copy_name in page.get_template_names()
        n_copy = -1
        if copied:
            page.open_l2_modal(copy_name)
            n_copy = page.l2_item_count()
            page.close_l2_modal()
        deep_ok = copied and n_copy >= 1
        self._add("pass" if deep_ok else "fail",
                  "sc3q — 복사 → '_copy' 생성 + ★등록 프로세스까지 복제",
                  f"입력: 내용 1건 템플릿 복사 / 결과: {copy_name!r} 존재={copied}, "
                  f"복사본 등록={n_copy}건 (원본 딥카피={deep_ok})", sc=3,
                  highlight=(page._row_locator(copy_name) if copied else None),
                  repro="1. 프로세스 1건 등록된 템플릿 체크\n2. 복사 → 확인\n"
                        "3. _copy 등장 + 카운트 동일(내용 복제)")

        # 충돌: _copy 존재 상태 재복사 → 동명 중복?
        page.copy_template(tpl)
        page.navigate_to()
        page.search(copy_name)
        dup_cnt = page.get_template_names().count(copy_name)
        page.search("")
        dup = dup_cnt > 1
        self._add("warn" if dup else "pass",
                  "sc3q — 복사 충돌(_copy 존재 시 재복사)",
                  f"입력: '{copy_name}' 존재 상태 재복사 / 결과: 동명 {dup_cnt}개 "
                  + ("(중복 생성 — 복사는 중복 검사 안 함, 타 탭 동일 결함 클래스)" if dup
                     else "(중복 차단됨)"), sc=3,
                  highlight=page.page.locator("table tbody"),
                  merge_key=("szproc_copy_dup::copy::warn::no_dup_check" if dup else None),
                  repro="1. _copy 존재 상태\n2. 원본 재복사\n3. 같은 이름 중복 생기는지")
        page.navigate_to()
        while copy_name in page.get_template_names():
            page.delete_template(copy_name)
            page.navigate_to()

    # ── sc3r: ★L2 등록항목 검색 — 실측 결함 2종(일치 미검색 + 리셋 불가) ──
    def test_scenario3r_l2_item_search(self, logged_in_page, settings):
        """L2 '프로세스명' 검색 — 정확 일치·부분어·빈 검색 복귀. 실측 정정(2026-07-09):
        fill(모델 동기)+실클릭이면 정확 검색·복귀 정상(앞선 결함 관찰은 JS setter 프로브 오류).
        부분어는 실타이핑 관찰상 0건 의심 → 타 검색(부분 일치)과의 일관성으로 수집."""
        print("\n━━ [프로세스] sc3r: L2 등록항목 검색(결함 실측 카드) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3r"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS", count=1)
        page.l3_add_message("ALLOW_PROCESS")
        target = picked[0] if picked else ""
        total = page.l2_item_count()

        # ① 등록된 이름 정확 검색 → 1건이어야 정상
        page.l2_search(target)
        hit = page.l2_item_count()
        self._add("pass" if hit >= 1 else "warn",
                  "sc3r — L2 검색: 등록된 프로세스명 정확 검색 → 검색됨",
                  f"입력: 등록 {total}건 중 {target!r} 정확 검색 / 결과: {hit}건 "
                  + ("" if hit >= 1 else "[★등록된 항목을 전체 이름 일치로도 못 찾음 — 검색 미매칭 결함]"),
                  sc=3, highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  merge_key=(None if hit >= 1 else "szproc_l2_search::match::warn::no_hit"),
                  repro=f"1. 프로세스 등록\n2. L2 검색창에 등록된 이름({target}) 입력\n"
                        "3. 검색 → 해당 행 1건 표시되어야")

        # ①-b 부분 검색 — 타 검색(리스트/picker)은 전부 부분 일치 → 일관성 확인
        page.l2_search(target[:6])
        part = page.l2_item_count()
        self._add("pass" if part >= 1 else "warn",
                  "sc3r — L2 검색: 부분어 검색 (타 검색과 일관성)",
                  f"입력: {target!r} 의 앞 6자 {target[:6]!r} 검색 / 결과: {part}건 "
                  + ("" if part >= 1 else "[부분 일치 미지원(정확 일치만) — 리스트/picker 검색은 "
                     "부분 일치라 불일치. 사용자는 파일명 일부로 검색 기대]"), sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  merge_key=(None if part >= 1 else "szproc_l2_search::partial::warn::exact_only"),
                  repro=f"1. {target} 등록 상태\n2. L2 검색창에 이름 일부({target[:6]}) 입력\n"
                        "3. 검색 → 부분 일치로 검색되어야(타 검색과 동일 UX)")

        # ② 빈 검색 → 전체 복귀되어야 정상
        page.l2_search("")
        back = page.l2_item_count()
        self._add("pass" if back == total else "warn",
                  "sc3r — L2 검색: 빈 검색 → 전체 목록 복귀",
                  f"입력: 검색 후 빈 검색 재실행 / 결과: {back}건(기대 {total}건) "
                  + ("" if back == total else "[★검색 후 목록이 복구 안 됨 — 모달 재오픈 전까지 빈 상태 고착, "
                     "헤더 카운트와 불일치]"), sc=3,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  merge_key=(None if back == total else "szproc_l2_search::reset::warn::stuck_empty"),
                  repro="1. L2 검색 실행(임의어)\n2. 검색어 지우고 재검색\n3. 전체 목록 복귀되어야")
        page.close_l2_modal()
        # 재오픈(복구 경로) 후 정리
        page.open_l2_modal(tpl)
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3s: 검증 메시지 i18n 키 노출 전수 (카테고리 sweep) ────────────
    def test_scenario3s_i18n_sweep(self, logged_in_page, settings):
        """생성 검증 메시지 전수 — raw i18n 키(COLUMN.NAME 류) 노출 없는지 sweep (analog sync sc3o)."""
        print("\n━━ [프로세스] sc3s: 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        _KEY = re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")
        msgs = {}
        page.open_add_modal()
        msgs["1단계 이름 빈값"] = page.submit_and_message()
        page._close_modal_if_open()
        tpl = "[AUTO]_sz_proc_3s"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        msgs["L3 프로세스 미선택"] = page.l3_add_message("ALLOW_PROCESS")
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc3s — 검증 메시지 i18n 키 노출 전수",
                  f"입력: 생성 검증 메시지 수집 / 결과: {msgs} / 키 누출={leaks or '없음'}", sc=3,
                  merge_key=("szproc_i18n::messages::warn::key_leak" if leaks else None),
                  repro="1. 생성 검증 경고 유발(이름 빈값/프로세스 미선택)\n2. raw i18n 키 노출 없는지")
