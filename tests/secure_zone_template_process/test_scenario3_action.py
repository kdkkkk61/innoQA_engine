"""시큐어존 템플릿(프로세스) — 시나리오 3: 동작 (타입 전수 + 컨텍스트 분산).

타입 종속 검증(생성 4종·L3 등록·EXCEPT 옵션)은 전수, 공통 검증(중복·clamp·특수문자·
오버플로·복사·검색·i18n)은 타입을 분산 배정(허용/거부/예외/차단 — 차이 발견 시만 확장).
메시지는 sc2 실측값('템플릿 이름을 입력해 주세요.'/'프로세스를 선택해 주세요') == 비교.

sc3a — 타입별 생성 4종(루프): 생성 → 리스트 등장 + 타입 컬럼 표시
sc3b — ★이름 중복 스코프: 같은 타입 동명(차단?) / 다른 타입 동명(probe 관찰: 공존?) 분리 검증
sc3c — 프로세스 등록 커밋(허용): L3 picker → 추가 → L2 행 +1 + 리스트 카운트 반영
sc3d — 태그 등록 커밋: 태그 탭 → picker(tag) → 추가 → 카운트 반영
sc3e — ★타입 필터 변별(4종 전수 — 타입 컬럼 있어 가능, sync 에선 검증 불가였던 항목) + 상태 필터
sc3f — L3 항목 제거(-) (모달 내 제거 — 리스트 삭제는 sc1/sc5)
sc3g — 복사 → _copy (분산: 실행차단) / sc3h — 검색
sc3i — 이름 clamp 30 실타이핑 (분산: 거부) / sc3j — 이름 특수문자 (분산: 예외처리)
sc3k — L3 설명 3000자 오버플로 (maxlength=None 실측 — 서버측, 분산: 허용) [저널]
sc3l — ★EXCEPT 옵션 변경 저장(차단/차단/재시작 ON) → 재오픈 반영
sc3m — i18n sweep(생성 검증 메시지 전수)
"""
import re as _re

from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario3Action(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 3: 동작."""

    _TPL = "[AUTO]_sz_proc_a"    # 주 흐름(허용)

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ── sc3a: 타입별 생성 4종 ───────────────────────────────────────
    def test_scenario3a_create_by_type(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3a: 타입별 생성 4종 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            name = f"[AUTO]_sz_proc_3a_{ttype.split('_')[0].lower()}"
            if name in page.get_template_names():   # 재실행 잔존 가드
                page.delete_template(name)
                page.navigate_to()
            page.create_template(name, ttype)
            page.navigate_to()
            created = name in page.get_template_names()
            row_type = page.row_type_text(name)
            ok = created and (ko in row_type)
            self._add("pass" if ok else "fail",
                      f"sc3a — {ko} 생성 → 리스트 등장 + 타입 표시",
                      f"입력: 이름+{ko} 저장 / 결과: 생성={created}, 타입 컬럼={row_type!r}", sc=3,
                      repro=f"1. 템플릿 추가\n2. 이름+{ko}\n3. 확인\n4. 리스트·타입 컬럼 확인")

    # ── sc3b: ★이름 중복 스코프 (probe 관찰 이슈 정식 검증) ─────────
    def test_scenario3b_duplicate_name_scope(self, logged_in_page, settings):
        """같은 타입 동명 vs 다른 타입 동명 — 중복 검사 스코프 확정.
        probe 관찰(2026-07-08): 동명 템플릿 2개 공존 사례 — 타입 다르면 허용? 실측 확정."""
        print("\n━━ [프로세스] sc3b: 이름 중복 스코프(같은 타입/다른 타입) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)   # ALLOW
        self._ckpt()

        # (1) 같은 타입(허용) 동명 재생성 → 차단 기대
        self._act(f"같은 타입(허용)으로 기존 이름 '{self._TPL}' 재생성 시도",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._TPL)))
        msg_same = page.submit_and_message()
        page._close_modal_if_open()
        blocked_same = "이미 등록" in msg_same
        self._add("pass" if blocked_same else "warn",
                  "sc3b — 같은 타입 동명 재생성 → 중복 차단",
                  f"입력: 허용+기존 이름 / 결과: 경고={msg_same!r}"
                  + ("" if blocked_same else " (차단 안 됨 — 중복 검사 부재)"), sc=3,
                  merge_key=(None if blocked_same
                             else "szproc_dup::same_type::warn::no_dup_check"),
                  repro="1. 기존 이름으로 같은 타입 재생성\n2. 확인\n3. 중복 경고 여부")

        # (2) 다른 타입(거부) 동명 생성 → 공존 여부 실측
        self._act(f"다른 타입(거부)으로 동명 '{self._TPL}' 생성 시도",
                  lambda: (page.open_add_modal(),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._TPL),
                           page.select_type("DENY_PROCESS")))
        msg_cross = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        count = page.get_template_names().count(self._TPL)
        coexist = count > 1
        st = "warn" if coexist else "pass"
        self._add(st,
                  "sc3b — 다른 타입 동명 생성 → 공존 여부(스코프 실측)",
                  f"입력: 거부+동명 / 결과: 경고={msg_cross!r}, 동명 {count}개"
                  + (" [동명 공존 — 이름 중복 검사가 타입 스코프(전역 아님), probe 관찰 재현]"
                     if coexist else " (전역 차단)"), sc=3,
                  merge_key=("szproc_dup::cross_type::warn::type_scoped_name_check" if coexist else None),
                  repro="1. 허용 타입 A 존재\n2. 거부 타입으로 같은 이름 생성\n3. 공존하는지 확인")
        # 정리 — 동명 잔재 제거(거부판). 동명 2개면 delete 가 첫 행부터 제거.
        while page.get_template_names().count(self._TPL) > 1:
            page.delete_template(self._TPL)
            page.navigate_to()

    # ── sc3c: 프로세스 등록 커밋 (허용) ─────────────────────────────
    def test_scenario3c_process_register(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3c: 프로세스 등록 커밋(허용) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        page.open_l2_modal(self._TPL)
        before = page.l2_item_count()
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_pick_first("ALLOW_PROCESS", mode="single")
        msg = page.l3_add_message("ALLOW_PROCESS")
        after = page.l2_item_count()
        page.close_l2_modal()
        page.navigate_to()
        cnt_col = ""
        try:
            cnt_col = page._row_locator(self._TPL).locator("td").nth(3).inner_text().strip()
        except Exception:
            pass
        ok = (after == before + 1) and (msg.strip() == "")
        self._add("pass" if ok else "fail",
                  "sc3c — L3 프로세스 선택 + 추가 → L2 행 +1 + 리스트 카운트",
                  f"입력: picker '{picked}' + 추가 / 결과: 경고={msg!r}, L2 {before}→{after}, "
                  f"리스트 카운트={cnt_col!r}", sc=3,
                  repro="1. 행 선택 → 프로세스 추가/제거 → +\n2. 프로세스 선택 → 추가\n3. 등록 행·카운트 증가")

    # ── sc3d: 태그 등록 커밋 ────────────────────────────────────────
    def test_scenario3d_tag_register(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3d: 태그 등록 커밋 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        page.open_l2_modal(self._TPL)
        page.switch_l2_tab("태그")
        before = page.l2_item_count()
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_pick_first("ALLOW_PROCESS", mode="tag")
        msg = page.l3_add_message("ALLOW_PROCESS")
        after = page.l2_item_count()
        page.close_l2_modal()
        ok = (after == before + 1) and (msg.strip() == "")
        self._add("pass" if ok else "fail",
                  "sc3d — 태그 탭 + 태그 선택 + 추가 → 등록 +1",
                  f"입력: 태그 '{picked}' + 추가 / 결과: 경고={msg!r}, 등록 {before}→{after}", sc=3,
                  repro="1. L2 태그 탭\n2. + → 태그 선택 → 추가\n3. 등록 증가")

    # ── sc3e: ★타입 필터 변별 4종 + 상태 필터 ──────────────────────
    def test_scenario3e_type_filter(self, logged_in_page, settings):
        """타입 컬럼이 있어 필터 변별 검증 가능(폴더동기화에선 검증 불가로 SKIP 했던 항목).
        sc3a 가 만든 4타입 [AUTO] 템플릿이 각 필터 결과에 잡히는지 + 결과 전부 해당 타입인지."""
        print("\n━━ [프로세스] sc3e: 타입 필터 변별(4종 전수) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            page.ensure_template(f"[AUTO]_sz_proc_3a_{ttype.split('_')[0].lower()}", ttype)
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            page.filter_by(template_type=ko)
            vals = page.list_type_values()
            all_match = bool(vals) and all(v == ko for v in vals)
            self._add("pass" if all_match else "fail",
                      f"sc3e — 타입 필터 '{ko}' → 해당 타입만 표시",
                      f"입력: 타입={ko} + 검색 / 결과: {len(vals)}행, 전부 일치={all_match}", sc=3,
                      repro=f"1. 타입 드롭다운={ko}\n2. 검색(돋보기)\n3. 해당 타입 행만")
        page.filter_by(template_type="전체")
        page.filter_by(status="활성")
        rows = page.page.locator(page.SEL_TABLE_ROW).all()
        no_inactive = all("비활성" not in r.inner_text() for r in rows)
        self._add("pass" if no_inactive else "fail",
                  "sc3e — 상태 필터(활성) → 비활성 미표시",
                  f"결과: {len(rows)}행, 비활성 없음={no_inactive}", sc=3)
        page.filter_by(status="상태")

    # ── sc3f: L3 항목 제거(-) ───────────────────────────────────────
    def test_scenario3f_item_remove(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3f: L2 항목 제거(-) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_rm"
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        if page.l2_item_count() == 0:
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_pick_first("ALLOW_PROCESS", mode="single")
            page.l3_add_message("ALLOW_PROCESS")
        before = page.l2_item_count()
        msg = page.l2_remove_item(0)
        after = page.l2_item_count()
        page.close_l2_modal()
        ok = ("삭제 하시겠습니까" in msg) and (after == before - 1)
        self._add("pass" if ok else "fail",
                  "sc3f — L2 항목 체크 + 제거(-) → 확인 → 등록 -1",
                  f"입력: 항목 제거 / 결과: 확인메시지={msg!r}, 등록 {before}→{after}", sc=3,
                  repro="1. L2 항목 체크\n2. - 버튼\n3. 삭제 확인\n4. 등록 감소")

    # ── sc3g: 복사 (분산: 실행차단) ─────────────────────────────────
    def test_scenario3g_copy(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3g: 복사(실행차단 타입) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3a_block"
        page.ensure_template(tpl, "BLOCK_PROCESS")
        copy_name = tpl + "_copy"
        if copy_name in page.get_template_names():
            page.delete_template(copy_name)
            page.navigate_to()
        page.copy_template(tpl)
        page.navigate_to()
        copied = copy_name in page.get_template_names()
        copy_type = page.row_type_text(copy_name) if copied else ""
        self._add("pass" if (copied and "실행차단" in copy_type) else "fail",
                  "sc3g — 복사 → '<이름>_copy' 생성 + 타입 유지",
                  f"입력: 복사 확인 / 결과: {copy_name!r} 존재={copied}, 타입={copy_type!r}", sc=3,
                  repro="1. 행 체크\n2. 복사\n3. 확인\n4. _copy 등장 + 타입 동일")

    # ── sc3h: 검색 ──────────────────────────────────────────────────
    def test_scenario3h_search(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3h: 이름 검색 필터 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        page.search(self._TPL)
        names = page.get_template_names()
        hit = self._TPL in names and all(self._TPL in n for n in names)
        page.search("")
        self._add("pass" if hit else "fail",
                  "sc3h — 이름 검색 → 해당 템플릿만 필터",
                  f"입력: {self._TPL!r} 검색 / 결과: {len(names)}건, 전부 매칭={hit}", sc=3,
                  repro="1. 검색창 이름 입력 + Enter\n2. 매칭 행만 표시")

    # ── sc3i: 이름 clamp 실타이핑 (분산: 거부) ──────────────────────
    def test_scenario3i_name_clamp(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3i: 이름 clamp(실타이핑, 거부 타입 모달) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.select_type("DENY_PROCESS")
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "a" * 60)
        page._close_modal_if_open()
        self._add("pass" if accepted == 30 else "warn",
                  "sc3i — 이름 실타이핑 60자 → 수용 길이(clamp 실측)",
                  f"결과: 수용={accepted}자 (maxlength=30 — sc2a 속성과 일치 여부)", sc=3,
                  repro="1. 추가 모달 이름 60자 타이핑\n2. 수용 길이 확인")

    # ── sc3j: 이름 특수문자 (분산: 예외처리) ────────────────────────
    def test_scenario3j_special_char_name(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3j: 이름 특수문자(예외처리 타입) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        sp = "[AUTO]_sz_proc_sp<>!@#"
        if sp in page.get_template_names():
            page.delete_template(sp); page.navigate_to()
        msg = page.create_template(sp, "EXCEPT_PROCESS")
        page.navigate_to()
        created = sp in page.get_template_names()
        self._add("pass" if created else "warn",
                  "sc3j — 이름 특수문자 입력(생성 시)",
                  f"입력: 이름 '{sp}' / 결과: 경고={msg!r}, 생성={created} "
                  "(타 탭 실측: 허용 — 이름 형식 검사 없음)", sc=3,
                  repro="1. 이름에 특수문자(<>!@#)\n2. 확인\n3. 허용/차단 여부")

    # ── sc3k: L3 설명 3000자 오버플로 (서버측 — sc2b 실측 근거) ─────
    def test_scenario3k_desc_overflow(self, logged_in_page, settings):
        """L3 설명 maxlength=None(sc2b 실측) → 서버측 오버플로 검증. 분산: 허용 타입.
        (L3 자유입력은 설명 1필드뿐 — 프로세스명은 picker 전용이라 전수=이 1건)"""
        print("\n━━ [프로세스] sc3k: L3 설명 3000자 오버플로 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()

        def _enter():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            page.open_l2_modal(self._TPL)
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_pick_first("ALLOW_PROCESS", mode="single")
            page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.fill("가" * 3000)
        self._act("L3 진입 + 프로세스 선택 + 설명 3000자 입력", _enter,
                  shot_target=page.page.locator(page.SEL_L3_DESC).first)

        def _click_add_wait():
            scope = page.l3_scope("ALLOW_PROCESS")
            scope.locator("button", has_text="추가").first.evaluate("el => el.click()")
            page.page.wait_for_timeout(500)
            try:
                page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).first.wait_for(
                    state="attached", timeout=2000)
            except Exception:
                pass
        self._act("추가 클릭 → 처리 결과(경고 알림/커밋)", _click_add_wait)
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        raw_err = ("서버" in msg and "오류" in msg)
        st = "warn" if raw_err else "pass"
        self._add(st,
                  "sc3k — L3 설명 3000자 + 추가 → 서버 처리(수집)",
                  f"입력: 설명 3000자 / 결과: 경고={msg!r}"
                  + (" [raw 서버 오류 — 클라 길이 가드 부재]" if raw_err else ""), sc=3,
                  merge_key=("szproc_ovf::설명::warn::raw_server_error" if raw_err else None),
                  repro="1. L3 설명에 3000자\n2. 추가\n3. 처리 결과 확인")
        if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            page.click_attached(page.SEL_CONFIRM_BTN)
            page.wait_for_modal_closed()
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()

    # ── sc3l: ★EXCEPT 옵션 변경 저장 → 재오픈 반영 ──────────────────
    def test_scenario3l_except_options_save(self, logged_in_page, settings):
        """예외처리 전용 옵션: 기본(허용/허용/OFF — sc2c 실측)을 차단/차단/ON 으로 저장 →
        항목 재오픈 시 반영 확인. radio 는 name 조합 셀렉터(id 중복 함정)."""
        print("\n━━ [프로세스] sc3l: EXCEPT 옵션 변경 저장 → 재오픈 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3a_except"
        page.ensure_template(tpl, "EXCEPT_PROCESS")
        page.open_l2_modal(tpl)
        page.open_l3_add("EXCEPT_PROCESS")
        scope = page.l3_scope("EXCEPT_PROCESS")
        picked = page.l3_pick_first("EXCEPT_PROCESS", mode="single")
        for group in ("isSecureDriveWrite", "isTakeoutDriveWrite"):
            scope.locator(f"input[name='{group}']#BLOCK").first.evaluate("el => el.click()")
        scope.locator("input#isProcessRestart").first.evaluate(
            "el => { if (!el.checked) el.click(); }")
        msg = page.l3_add_message("EXCEPT_PROCESS")
        # 재오픈 — L2 등록 행의 프로세스명 링크/행 클릭 방식은 실측 전 → 행 더블클릭 대신
        # 편집 재진입 UI 를 수집형으로: 행 존재 + 다음 추가 모달 기본값 오염 없는지로 대체 검증
        after = page.l2_item_count()
        page.open_l3_add("EXCEPT_PROCESS")
        fresh_defaults = {
            g: scope.locator(f"input[name='{g}']#ALLOW").first.is_checked()
            for g in ("isSecureDriveWrite", "isTakeoutDriveWrite")}
        fresh_restart = scope.locator("input#isProcessRestart").first.is_checked()
        page.close_l3_modal("EXCEPT_PROCESS")
        page.close_l2_modal()
        committed = (msg.strip() == "") and after >= 1
        clean = all(fresh_defaults.values()) and not fresh_restart
        self._add("pass" if committed else "fail",
                  "sc3l — EXCEPT 옵션(차단/차단/재시작 ON) 저장 커밋",
                  f"입력: '{picked}' + 옵션 변경 + 추가 / 결과: 경고={msg!r}, 등록 {after}건", sc=3,
                  repro="1. 예외처리 L3 — 드라이브 권한 차단×2 + 재시작 ON\n2. 추가 → 커밋")
        self._add("pass" if clean else "warn",
                  "sc3l — 다음 추가 모달 기본값 오염 없음(허용/허용/OFF 복귀)",
                  f"결과: 기본 허용={fresh_defaults}, 재시작={fresh_restart} "
                  "(저장값의 항목별 반영 상세는 sc4/sc5 담당)", sc=3)

    # ── sc3m: i18n sweep ────────────────────────────────────────────
    def test_scenario3m_i18n_sweep(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc3m: 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        _KEY = _re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")
        msgs = {}
        page.open_add_modal()
        msgs["1단계 이름 빈값"] = page.submit_and_message()
        page._close_modal_if_open()
        page.ensure_template(self._TPL)
        page.open_l2_modal(self._TPL)
        page.open_l3_add("ALLOW_PROCESS")
        msgs["L3 프로세스 미선택"] = page.l3_add_message("ALLOW_PROCESS")
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc3m — 검증 메시지 i18n 키 노출 전수",
                  f"결과: {msgs} / 키 누출={leaks or '없음'}", sc=3,
                  repro="1. 생성 검증 경고 유발\n2. raw i18n 키 없는지")
