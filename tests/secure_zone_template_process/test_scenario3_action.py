"""시큐어존 템플릿(프로세스) — 시나리오 3: 동작.

캡처 컨벤션 = docs/issue-screenshot-rules.md (특수폴더 sc3 레퍼런스와 동일):
  _add(status, ..., highlight=<이슈 요소 locator>) → base 가 fail/warn 에서만 빨간 crop 자동 캡처,
  pass/skip 은 캡처 없음. 저널(_ckpt/_act)·수동 _shot·screenshots= 미사용(임의 시스템 배제).

sc3a 타입별 생성 4종 / sc3b 동명 중복 스코프(같은 타입 차단·다른 타입 공존)
sc3c 등록(단일+다중, checkbox) / sc3d 인라인 옵션 토글(재시작) / sc3e 태그 등록 / sc3f 제거(개별+일괄)
sc3g 다중 중복 처리(부분/전체) / sc3h 이름(clamp·특수문자) / sc3i 설명(특수문자·장문)
sc3j ★미선택 필수 경고 4타입 전수 / sc3k ★등록+옵션 4타입 전수 / sc3l 설명 3000자 오버플로 4타입
※ 등록 picker=checkbox plain click(실측). L3 타입별 모달 별개 → 타입 종속 검증은 4타입 전수.
※ seed 연계는 sc6. sc2=속성(maxlength 존재·초기값), sc3=실제 동작.
"""
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
                      f"sc3l — {ko}: 설명 3000자 저장 → 서버 처리(수집)",
                      f"입력: 설명 3000자 + 추가 / 결과: 경고={msg!r}, 커밋={committed} "
                      + ("[raw 서버 오류 — 클라 길이 가드 부재]" if raw_err
                         else "(길이 가드 안내)" if guard else "(제한 없이 커밋)"), sc=3,
                      merge_key=(f"szproc_desc_ovf::{ttype}::warn::raw_server_error" if raw_err else None),
                      repro=f"1. {ko} L3 프로세스 선택 + 설명 3000자\n2. 추가\n3. 서버 처리 결과 확인")
            page.dismiss_alert()
            page.close_l3_modal(ttype)
            page.l2_bulk_remove()
            page.close_l2_modal()
