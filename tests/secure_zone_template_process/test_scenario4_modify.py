"""시큐어존 템플릿(프로세스) — 시나리오 4: 수정.

analog: sync/manage_folder sc4. L1 구간(4a~4e, run 통과 확인) → L2/L3 구간(4f~4k) 확장.
계약(사용자 확인 2026-07-09): L2 리스트 옵션=클릭 즉시 / L3 편집=바꾸고 '수정'까지 커밋.

[L1 — 템플릿 수정 모달]
sc4a 로드값(이름/타입/상태) + 타입 radio 잠금 수집(실측 disabled=안전)
sc4b 상태 활성↔비활성 3점 대조(저장→리스트 상태열→재오픈)+원복
sc4c 이름 비움 필수 경고+원본 유지 / sc4d rename 중복 차단 / sc4e 이름 clamp 30
[L2/L3 — 항목 수정 (이름 링크 → L3 편집 → '수정' 버튼)]
sc4f 로드값+설명 수정 재오픈 반영 / sc4g 항목 상태 활성↔비활성(L2 표시+재오픈, 원복)
sc4h 옵션 수정 roundtrip(허용 재시작 L3→인라인 방향 + ★예외처리 드라이브 수정 경로)
sc4i 설명 3000자 in modify ★4타입 전수 — 재오픈 실저장값 대조 + 복구 재수정(sc3l 대응)
sc4j i18n sweep / sc4k 수정 세션 제거
[sc3↔sc4 대응 — 생성에서 검증한 동작을 수정 경로에서 재검증 (사용자 지시 2026-07-09)]
sc4l ★등록 프로세스 재선택 변경(sc3c 대응) / sc4m 재선택 중복 충돌(sc3g 대응)
sc4n ★태그 항목 편집(sc3e 대응 — 이름 링크 td[2] 순위 시프트) / sc4o 설명 특수문자·500자(sc3i 대응)
sc4p 다중 등록 중 1건만 수정 → 편집 격리(sc3n 대응)

캡처: _add(highlight=) 기본(issue-screenshot-rules §2). pass=캡처 없음.
"""
from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario4Modify(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 4: 수정 (L1 구간)."""

    _TPL = "[AUTO]_sz_proc_4"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _row_status(self, page, name: str) -> str:
        """리스트 행 상태열(td[4]) 텍스트 — sc1b 헤더 실측(용도/이름/타입/카운트/상태/...)."""
        try:
            return page._row_locator(name).locator("td").nth(4).inner_text().strip()
        except Exception:
            return ""

    # ── sc4a: 수정 모달 로드값 + 타입 radio 편집 가능 여부(수집) ──────
    def test_scenario4a_template_load(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc4a: 수정 모달 로드값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_modify_modal(self._TPL)
        NAME = f"{page.SEL_MODAL} {page.SEL_NAME}"
        name_loaded = page.page.locator(NAME).first.input_value()
        type_allow = page.page.locator(f"{page.SEL_MODAL} input#ALLOW_PROCESS").first.is_checked()
        status_active = page.page.locator(f"{page.SEL_MODAL} input#CREATE").first.is_checked()
        ok = (name_loaded == self._TPL) and type_allow and status_active
        self._add("pass" if ok else "fail",
                  "sc4a — 수정 모달 로드값(이름/타입/상태) 일치",
                  f"결과: 이름={name_loaded!r}(기대 {self._TPL!r}), 허용 checked={type_allow}, "
                  f"활성 checked={status_active}", sc=4,
                  highlight=page.page.locator(NAME),
                  repro="1. 행 선택 → 수정\n2. 이름/타입/상태가 저장값 그대로 로드되는지")

        # 타입 radio 편집 가능 여부 — 수집형(등록 내용과 타입 불일치 위험 관찰 지점)
        type_disabled = page.page.locator(
            f"{page.SEL_MODAL} input#DENY_PROCESS").first.is_disabled()
        self._add("pass" if type_disabled else "warn",
                  "sc4a — 수정 모달 타입 radio 잠금 여부(수집)",
                  f"결과: 타입 radio disabled={type_disabled} "
                  + ("(수정에서 타입 변경 차단 — 안전)" if type_disabled
                     else "[수정에서 타입 변경 가능 — L2 에 등록된 프로세스(타입 종속 옵션)와 "
                          "불일치 위험. 변경 시 등록 내용 처리 방식 확인 필요]"), sc=4,
                  highlight=page.page.locator(f"{page.SEL_MODAL} input#DENY_PROCESS"),
                  merge_key=(None if type_disabled
                             else "szproc_modify::type_radio::warn::editable_in_modify"),
                  repro="1. 수정 모달\n2. 타입 radio 가 disabled 인지(등록 내용 보호)")
        page._close_modal_if_open()

    # ── sc4b: 상태 활성→비활성 — 3점 대조(저장/리스트/재오픈) + 원복 ──
    def test_scenario4b_status_update(self, logged_in_page, settings):
        """입력값 ↔ 리스트 상태열 ↔ 재오픈 로드 3점 대조(표시/저장 계층 분리 버그 구분)."""
        print("\n━━ [프로세스] sc4b: 상태 활성→비활성 3점 대조 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_modify_modal(self._TPL)
        page.page.locator(f"{page.SEL_MODAL} input#DELETE").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        list_status = self._row_status(page, self._TPL)
        page.open_modify_modal(self._TPL)
        reload_inactive = page.page.locator(f"{page.SEL_MODAL} input#DELETE").first.is_checked()
        # 원복(활성) — 같은 세션에서 바로
        page.page.locator(f"{page.SEL_MODAL} input#CREATE").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        restored = self._row_status(page, self._TPL)
        ok = (list_status == "비활성") and reload_inactive and (restored == "활성")
        self._add("pass" if ok else "fail",
                  "sc4b — 상태 활성→비활성 수정: 저장·리스트·재오픈 3점 일치(+원복)",
                  f"입력: 비활성 저장({msg!r}) / 결과: 리스트={list_status!r}(기대 비활성), "
                  f"재오픈 비활성 checked={reload_inactive}, 원복 후 리스트={restored!r}(기대 활성)",
                  sc=4, highlight=(page._row_locator(self._TPL)
                                   if self._TPL in page.get_template_names() else None),
                  repro="1. 수정 → 상태 비활성 → 저장\n2. 리스트 상태열 '비활성'\n"
                        "3. 재오픈 → 비활성 checked\n4. 활성 원복")

    # ── sc4c: 수정에서 이름 비움 → 필수 경고 + 원래 이름 유지 ─────────
    def test_scenario4c_required_empty_violation(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc4c: 수정 이름 비움 필수 위반 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_modify_modal(self._TPL)
        NAME = f"{page.SEL_MODAL} {page.SEL_NAME}"
        page.page.locator(NAME).first.fill("")
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        kept = self._TPL in page.get_template_names()
        warned = "입력" in (msg or "")
        self._add("pass" if (warned and kept) else "fail",
                  "sc4c — 수정에서 이름 비움 → 필수 경고 + 원래 이름 유지",
                  f"입력: 이름 비우고 저장 / 결과: 경고={msg!r}(기대 '입력해 주세요'), "
                  f"원본 유지={kept}", sc=4,
                  highlight=page.page.locator("table tbody"),
                  repro="1. 수정 → 이름 전체 삭제\n2. 저장 → 경고\n3. 원래 이름 그대로인지")

    # ── sc4d: 같은 타입 기존 이름으로 rename → 중복 차단 ──────────────
    def test_scenario4d_rename_duplicate(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc4d: rename 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        other = "[AUTO]_sz_proc_4d_other"
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.ensure_template(other, "ALLOW_PROCESS")
        page.open_modify_modal(other)
        NAME = f"{page.SEL_MODAL} {page.SEL_NAME}"
        page.page.locator(NAME).first.fill(self._TPL)
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        page.search(self._TPL)
        dup_cnt = page.get_template_names().count(self._TPL)
        page.search("")
        blocked = ("이미 등록" in (msg or "")) and dup_cnt == 1
        self._add("pass" if blocked else "warn",
                  "sc4d — 같은 타입 기존 이름으로 rename → 중복 차단",
                  f"입력: {other!r} 를 {self._TPL!r} 로 rename / 결과: 경고={msg!r}, "
                  f"동명 {dup_cnt}개 " + ("(차단 정상)" if blocked
                     else "[rename 경로 중복 검사 누락 — 생성은 차단(sc3b)하는데 수정은 통과]"),
                  sc=4, highlight=page.page.locator("table tbody"),
                  merge_key=(None if blocked else "szproc_dup::rename::warn::no_dup_check"),
                  repro=f"1. {other} 수정\n2. 이름을 기존 {self._TPL} 로 변경\n3. 저장 → 차단되어야")
        page.navigate_to()
        if other in page.get_template_names():
            page.delete_template(other)
            page.navigate_to()

    # ── sc4e: 수정에서 이름 60자 실타이핑 → clamp 30 ──────────────────
    def test_scenario4e_name_clamp_in_modify(self, logged_in_page, settings):
        """생성(sc3h)의 maxlength 가드가 수정 컨텍스트에도 동일한지 — 실타이핑(fill 금지 규칙)."""
        print("\n━━ [프로세스] sc4e: 수정 이름 clamp ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_modify_modal(self._TPL)
        NAME = f"{page.SEL_MODAL} {page.SEL_NAME}"
        accepted = page.type_real(NAME, "a" * 60)
        page._close_modal_if_open()   # 저장 안 함 — 가드 확인만
        self._add("pass" if accepted == 30 else "warn",
                  "sc4e — 수정에서 이름 60자 실타이핑 → clamp 30",
                  f"입력: 60자 타이핑 / 결과: 수용={accepted}자 "
                  + ("(생성과 동일 maxlength 가드)" if accepted == 30
                     else "[생성(30)과 다른 수용 길이 — 수정 경로 가드 불일치]"), sc=4,
                  highlight=page.page.locator(NAME),
                  merge_key=(None if accepted == 30 else "szproc_clamp::modify_name::warn::guard_mismatch"),
                  repro="1. 수정 모달 이름에 60자 타이핑\n2. 수용 길이 30 확인(저장 안 함)")

    # ══ L2/L3 구간 (2차분) — 항목 수정. L3 편집 커밋 = '수정' 버튼(실측 2026-07-08) ══

    def _ensure_item(self, page, tpl: str, ttype: str = "ALLOW_PROCESS") -> None:
        """sc4 공용 — tpl(해당 타입)에 프로세스 1건 확보 후 L2 열린 상태로 반환."""
        page.navigate_to_clean()
        page.ensure_template(tpl, ttype)
        page.open_l2_modal(tpl)
        if page.l2_item_count() == 0:
            page.open_l3_add(ttype)
            page.l3_register(ttype, count=1)
            page.l3_add_message(ttype)

    def _row_item_status_on(self, page, idx: int = 0) -> bool:
        """L2 행 상태 셀(td[4]) ON 여부 — ★Chrome 실측(2026-07-09): 시각 상태는
        label.switch 의 'on' 클래스. 내부 input#status 는 checked 가 모델과 미바인딩
        (활성인데 checked=false)이라 신뢰 불가 — sc4g 첫 FAIL 원인."""
        cls = page.l2_rows()[idx].locator("td").nth(4).locator(
            "label.switch").first.get_attribute("class") or ""
        return " on" in f" {cls} "

    def _wait_row_status(self, page, want_on: bool, timeout_ms: int = 4000) -> bool:
        """L2 행 상태 표시가 기대값이 될 때까지 폴링 — '수정' 커밋 후 목록 재렌더가
        비동기(15:33 run sc4g 재실패: 커밋 직후 즉시 읽어 stale). 미도달 시 관측값 반환."""
        import time as _t
        deadline = _t.monotonic() + timeout_ms / 1000
        cur = self._row_item_status_on(page)
        while cur != want_on and _t.monotonic() < deadline:
            page.page.wait_for_timeout(250)
            cur = self._row_item_status_on(page)
        return cur

    # ── sc4f: 항목 편집 로드값 → 설명 수정 → '수정' 커밋 → 재오픈 반영 ──
    def test_scenario4f_item_load_update(self, logged_in_page, settings):
        """L3 편집 계약(사용자 확인 2026-07-09): 바꾼 뒤 '수정'까지 눌러야 커밋."""
        print("\n━━ [프로세스] sc4f: 항목 편집 로드→설명 수정→재오픈 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = self._TPL   # 공용 재사용 — 각 테스트가 끝에 항목 비움
        self._ensure_item(page, tpl)
        reg_name = page.l2_rows()[0].locator("td").nth(1).inner_text().strip()

        page.l2_open_item_edit(0)
        loaded_name = page.l3_selected_name("ALLOW_PROCESS")
        active = page.l3_scope("ALLOW_PROCESS").locator("input#CREATE").first.is_checked()
        load_ok = (loaded_name == reg_name) and active
        page.fill(f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}", "sc4f_desc")
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")

        page.l2_open_item_edit(0)
        desc_after = page.l3_scope("ALLOW_PROCESS").locator(
            page.SEL_L3_DESC).first.input_value()
        page.close_l3_modal("ALLOW_PROCESS")
        ok = load_ok and (msg == "" or "저장" in msg) and desc_after == "sc4f_desc"
        self._add("pass" if ok else "fail",
                  "sc4f — 항목 편집: 로드값 일치 + 설명 수정 '수정' 커밋 → 재오픈 반영",
                  f"결과: 로드 이름={loaded_name!r}(기대 {reg_name!r}), 활성={active}, "
                  f"커밋={msg!r}, 재오픈 설명={desc_after!r}(기대 'sc4f_desc')", sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 프로세스명 링크 → L3 편집(로드값 확인)\n2. 설명 변경 → '수정'\n"
                        "3. 재오픈 → 변경 반영 확인")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4g: 항목 상태 활성→비활성 (L3 경로 — L2 상태 셀은 표시 전용) ──
    def test_scenario4g_item_status_update(self, logged_in_page, settings):
        """실측(2026-07-08): L2 행 상태 = input#status[disabled] 표시 전용,
        변경은 이름 링크 → L3 편집 → CREATE/DELETE → '수정' 이 유일 경로."""
        print("\n━━ [프로세스] sc4g: 항목 상태 활성→비활성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = self._TPL   # 공용 재사용 — 각 테스트가 끝에 항목 비움
        self._ensure_item(page, tpl)
        before_on = self._row_item_status_on(page)

        page.l2_open_item_edit(0)
        page.l3_scope("ALLOW_PROCESS").locator("input#DELETE").first.evaluate(
            "el => el.click()")
        page.page.wait_for_timeout(150)
        page.l3_add_message("ALLOW_PROCESS", button="수정")
        after_on = self._wait_row_status(page, False)   # 재렌더 폴링(stale 방지)
        page.l2_open_item_edit(0)
        reload_inactive = page.l3_scope("ALLOW_PROCESS").locator(
            "input#DELETE").first.is_checked()
        # 원복(활성)
        page.l3_scope("ALLOW_PROCESS").locator("input#CREATE").first.evaluate(
            "el => el.click()")
        page.page.wait_for_timeout(150)
        page.l3_add_message("ALLOW_PROCESS", button="수정")
        restored_on = self._wait_row_status(page, True)   # 재렌더 폴링
        ok = before_on and (not after_on) and reload_inactive and restored_on
        # 3점 대조 분류(issue-card-rules §6): 저장(재오픈)은 정상인데 표시만 어긋나면
        # '리스트 갱신 버그'(제품 표시 결함 warn) — 저장 자체가 틀리면 fail.
        display_only = reload_inactive and before_on and after_on
        st = "pass" if ok else ("warn" if display_only else "fail")
        self._add(st,
                  "sc4g — 항목 상태 활성→비활성 '수정': L2 표시·재오픈 일치(+원복)",
                  f"결과: 이전 ON={before_on} → 비활성 후 ON={after_on}(기대 False), "
                  f"재오픈 비활성 checked={reload_inactive}, 원복 후 ON={restored_on}"
                  + (" [★저장은 정상(재오픈 비활성)인데 L2 행 상태 표시가 갱신 안 됨(4s 폴링) — "
                     "리스트 갱신 버그. 옵션 셀은 즉시 갱신되는 것과 대조적]" if (not ok and display_only)
                     else ""), sc=4,
                  highlight=page.l2_rows()[0].locator("td").nth(4) if page.l2_rows() else None,
                  merge_key=("szproc_item_status::display::warn::list_not_refreshed"
                             if (not ok and display_only) else None),
                  repro="1. 이름 링크 → L3 상태 비활성 → '수정'\n2. L2 행 상태 OFF 표시\n"
                        "3. 재오픈 비활성 checked\n4. 활성 원복")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4h: 옵션 수정 roundtrip — 허용 재시작(L3 경로) + 예외처리 드라이브 ──
    def test_scenario4h_option_update_roundtrip(self, logged_in_page, settings):
        """sc3d(인라인→편집 로드)와 반대 방향: L3 편집에서 바꿔 '수정' → L2 인라인 표시 반영.
        + 예외처리 드라이브 권한을 수정 경로로 변경(sc3m 은 생성 시 설정 — 경로 대칭)."""
        print("\n━━ [프로세스] sc4h: 옵션 수정 roundtrip ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        # (a) 허용 — L3 편집에서 재시작 ON → '수정' → L2 인라인 표시 + 재오픈
        tpl = self._TPL   # 공용 재사용 — 각 테스트가 끝에 항목 비움
        self._ensure_item(page, tpl)
        page.l2_open_item_edit(0)
        rst = page.l3_scope("ALLOW_PROCESS").locator("input#isProcessRestart").first
        if not rst.is_checked():
            rst.evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        page.l3_add_message("ALLOW_PROCESS", button="수정")
        inline_on = page.l2_option_on(0)
        page.l2_open_item_edit(0)
        reload_on = page.l3_scope("ALLOW_PROCESS").locator(
            "input#isProcessRestart").first.is_checked()
        page.close_l3_modal("ALLOW_PROCESS")
        a_ok = inline_on and reload_on
        self._add("pass" if a_ok else "fail",
                  "sc4h — 허용: L3 편집 재시작 ON '수정' → L2 인라인 표시+재오픈 반영",
                  f"결과: L2 옵션 버튼 on={inline_on}, 재오픈 checked={reload_on}", sc=4,
                  highlight=page.l2_rows()[0].locator("td").nth(3) if page.l2_rows() else None,
                  repro="1. 이름 링크 → L3 재시작 ON → '수정'\n2. L2 옵션 버튼 on 표시\n3. 재오픈 checked")
        page.l2_bulk_remove()
        page.close_l2_modal()

        # (b) 예외처리 — 수정 경로로 드라이브 권한 변경(시큐어=차단/반출=허용) → 재오픈 대조
        tpl_ex = "[AUTO]_sz_proc_4_ex"   # 타입 radio 잠금 → 예외처리만 별도
        self._ensure_item(page, tpl_ex, "EXCEPT_PROCESS")
        page.l2_open_item_edit(0)
        sc = page.l3_scope("EXCEPT_PROCESS")
        sc.locator("input[name='isSecureDriveWrite']#BLOCK").first.evaluate("el => el.click()")
        sc.locator("input[name='isTakeoutDriveWrite']#ALLOW").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        page.l3_add_message("EXCEPT_PROCESS", button="수정")
        page.l2_open_item_edit(0)
        sc2 = page.l3_scope("EXCEPT_PROCESS")
        loaded = {
            "시큐어=차단": sc2.locator("input[name='isSecureDriveWrite']#BLOCK").first.is_checked(),
            "반출=허용": sc2.locator("input[name='isTakeoutDriveWrite']#ALLOW").first.is_checked(),
        }
        page.close_l3_modal("EXCEPT_PROCESS")
        b_ok = all(loaded.values())
        self._add("pass" if b_ok else "warn",
                  "sc4h — 예외처리: 드라이브 권한 수정 '수정' → 재오픈 일치",
                  f"입력: 시큐어=차단/반출=허용 수정 / 결과: {loaded} 전부일치={b_ok}"
                  + ("" if b_ok else " [수정 경로 저장/로드 손실 — 생성 경로(sc3m)는 정상]"), sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  merge_key=(None if b_ok else "szproc_roundtrip::except_modify::warn::value_lost"),
                  repro="1. 예외처리 항목 이름 링크 → 드라이브 권한 변경 → '수정'\n2. 재오픈 → 값 유지 확인")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4i: 설명 3000자 오버플로 in modify — ★4타입 전수 (sc3l 대응) ──
    def test_scenario4i_desc_overflow_in_modify(self, logged_in_page, settings):
        """수정 경로 3000자 — L3 편집 모달이 타입별 별개(sc3j 교훈)라 4타입 전수.
        메시지만 믿지 않고 재오픈으로 실제 저장값 대조 + 이후 정상값 재수정(복구)."""
        print("\n━━ [프로세스] sc4i: 설명 3000자(수정 경로) 4타입 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = self._tpl_for(ttype)
            DESC = f"div#{page.L3_MAP[ttype]}.in {page.SEL_L3_DESC}"
            self._ensure_item(page, tpl, ttype)
            page.l2_open_item_edit(0)
            page.fill(DESC, "가" * 3000)
            msg = page.l3_add_message(ttype, button="수정")
            raw_err = "서버에서 오류" in (msg or "")
            page.dismiss_alert()
            if page.page.locator(f"div#{page.L3_MAP[ttype]}.in").count() > 0:
                page.close_l3_modal(ttype)

            # 재오픈 — 실제 저장값 대조 (커밋 메시지만 믿는 은폐 금지)
            page.l2_open_item_edit(0)
            stored = page.l3_scope(ttype).locator(page.SEL_L3_DESC).first.input_value()
            n = len(stored)
            # merge_key = 요소(타입)별 — sc3l(생성)과 같은 키로 세로 병합(3↔4 한 카드,
            #   결과가 다르면 리포터가 시나리오별 줄로 분리 표기)
            mk = f"szproc_desc_ovf::{ttype}"
            if raw_err:
                verdict, note = "warn", "[raw 서버 오류 — 생성(sc3l)과 동일, 수정 경로도 가드 부재]"
            elif n == 3000:
                verdict, note = ("warn",
                    "[★경로 불일치 — 생성은 3000자를 서버 오류로 차단하는데 수정 경로는 "
                    "그대로 DB 저장. 수정이 생성 검증을 우회]")
            elif 0 < n < 3000:
                verdict, note = "warn", f"[조용한 절단 — 안내 없이 {n}자로 잘려 저장]"
            else:
                verdict, note = "warn", "[조용한 미저장 — 경고 없이 설명 유실]"
            self._add(verdict,
                      f"sc4i — {ko}: 설명 3000자 → 저장 처리",   # 라벨 본문 = sc3l 과 동일(미러 dedup)
                      f"입력: 3000자 + '수정' / 결과: 경고={msg!r}, 재오픈 저장={n}자 {note}",
                      sc=4,
                      highlight=page.l3_scope(ttype).locator(page.SEL_L3_DESC),
                      merge_key=mk,
                      repro=f"1. {ko} 등록 항목 편집 → 설명 3000자 → '수정'\n"
                            "2. 재오픈 → 실제 저장 길이 확인\n3. 생성 경로(서버 오류)와 비교")

            # 경계 입력 이후 같은 항목 정상 재수정 — 오염/복구(사용자 지적 2026-07-09)
            page.fill(DESC, "sc4i_recover")
            msg2 = page.l3_add_message(ttype, button="수정")
            page.dismiss_alert()
            if page.page.locator(f"div#{page.L3_MAP[ttype]}.in").count() > 0:
                page.close_l3_modal(ttype)
            page.l2_open_item_edit(0)
            after = page.l3_scope(ttype).locator(page.SEL_L3_DESC).first.input_value()
            page.close_l3_modal(ttype)
            recovered = after == "sc4i_recover"
            self._add("pass" if recovered else "fail",
                      f"sc4i — {ko}: 3000자 시도 후 정상값 재수정 → 복구",
                      f"입력: 'sc4i_recover' 재수정({msg2!r}) / 재오픈={after[:30]!r}, 복구={recovered}"
                      + ("" if recovered else " [경계 입력 후 항목 정상 수정 불가 — 상태 오염]"),
                      sc=4, highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      repro=f"1. {ko} 3000자 시도 직후 같은 항목 재편집\n2. 정상 설명 '수정'\n3. 반영 확인")
            page.l2_bulk_remove()
            page.close_l2_modal()

    # ── sc4j: 검증 메시지 i18n sweep (수정 컨텍스트) ──────────────────
    def test_scenario4j_i18n_sweep_in_modify(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc4j: i18n sweep(수정 컨텍스트) ━━━")
        import re as _re
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        _KEY = _re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")
        msgs = {}
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_modify_modal(self._TPL)
        page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.fill("")
        msgs["수정 이름 빈값"] = page.submit_and_message()
        page._close_modal_if_open()
        page.open_modify_modal(self._TPL)
        msgs["수정 무변경 저장"] = page.submit_and_message()
        page._close_modal_if_open()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc4j — 수정 검증 메시지 i18n 키 노출 전수",
                  f"결과: {msgs} / 키 누출={leaks or '없음'}", sc=4,
                  merge_key=("szproc_i18n::modify::warn::key_leak" if leaks else None),
                  repro="1. 수정 검증 경고 유발(이름 빈값/무변경 저장)\n2. raw i18n 키 노출 없는지")

    # ── sc4k: 수정 세션에서 항목 제거 (편집 커밋 직후 컨텍스트) ────────
    def test_scenario4k_item_remove_in_modify(self, logged_in_page, settings):
        """생성 직후 제거(sc3f)와 다른 컨텍스트 — 편집('수정' 커밋) 직후 같은 세션에서 제거."""
        print("\n━━ [프로세스] sc4k: 수정 세션 항목 제거 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = self._TPL   # 공용 재사용 — 각 테스트가 끝에 항목 비움
        self._ensure_item(page, tpl)
        page.l2_open_item_edit(0)
        page.fill(f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}", "sc4k")
        page.l3_add_message("ALLOW_PROCESS", button="수정")
        before = page.l2_item_count()
        msg = page.l2_remove_item(0)
        after = page.l2_item_count()
        ok = (before == 1) and (after == 0) and ("삭제" in (msg or ""))
        self._add("pass" if ok else "fail",
                  "sc4k — 편집 커밋 직후 같은 세션에서 항목 제거",
                  f"결과: 편집 후 {before}건 → 제거 확인={msg!r} → {after}건", sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 항목 편집 → '수정' 커밋\n2. 같은 세션에서 행 체크 → 제거\n3. 0건")
        page.close_l2_modal()

    # ══ sc3↔sc4 대응 구간 — 생성에서 검증한 동작을 수정 경로에서 재검증 ══

    def _tpl_for(self, ttype: str) -> str:
        """타입별 sc4 공용 템플릿(타입 radio 잠금 — 타입별 1개)."""
        return {"ALLOW_PROCESS": self._TPL,
                "DENY_PROCESS": "[AUTO]_sz_proc_4_deny",
                "EXCEPT_PROCESS": "[AUTO]_sz_proc_4_ex",
                "BLOCK_PROCESS": "[AUTO]_sz_proc_4_block"}[ttype]

    # ── sc4l: ★등록된 프로세스 자체 변경 (재선택 → '수정') — sc3c 대응 ──
    def test_scenario4l_item_process_reselect(self, logged_in_page, settings):
        """편집 모달의 '프로세스 선택'으로 다른 프로세스로 교체 → L2 행 이름 변경 +
        카운트 불변(교체이지 추가 아님). 사용자 지적(2026-07-09): 기존 등록 프로세스 변경."""
        import re as _re
        print("\n━━ [프로세스] sc4l: 등록 프로세스 재선택 변경 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page, self._TPL)
        cur = page.l2_rows()[0].locator("td").nth(1).inner_text().strip()

        page.l2_open_item_edit(0)
        # 현재 프로세스가 아닌 아무 프로세스로 재선택
        picked = page.l3_register("ALLOW_PROCESS", count=1,
                                  name_pattern=_re.compile(rf"^(?!{_re.escape(cur)}$).+"))
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.dismiss_alert()
        cnt = page.l2_item_count()
        new_name = page.l2_rows()[0].locator("td").nth(1).inner_text().strip() if cnt else ""
        changed = bool(picked) and cnt == 1 and new_name == picked[0] and new_name != cur
        self._add("pass" if changed else "fail",
                  "sc4l — 등록 프로세스 재선택 변경: 행 이름 교체 + 카운트 불변",
                  f"입력: {cur!r} 편집 → {picked} 재선택 + '수정'({msg!r}) / "
                  f"결과: L2 {cnt}건(기대 1), 행 이름={new_name!r}", sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 등록 항목 이름 링크 → '프로세스 선택'\n2. 다른 프로세스 선택 → '수정'\n"
                        "3. 행 이름이 새 프로세스로 교체 + 1건 유지")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4m: 변경으로 중복 유발 (B → 이미 등록된 A 로 재선택) — sc3g 대응 ──
    def test_scenario4m_item_reselect_duplicate(self, logged_in_page, settings):
        """등록 중복 처리(sc3g: 생략 안내)가 '변경' 경로에도 있는지 — B 를 A 로 재선택."""
        import re as _re
        print("\n━━ [프로세스] sc4m: 재선택 중복 충돌 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_l2_modal(self._TPL)
        if page.l2_item_count() != 2:
            page.l2_bulk_remove()
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_register("ALLOW_PROCESS", count=2)
            page.l3_add_message("ALLOW_PROCESS")
        names = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        a, b = names[0], names[1]

        page.l2_open_item_edit(1)   # B 편집
        picked = page.l3_register("ALLOW_PROCESS", count=1,
                                  name_pattern=_re.compile(rf"^{_re.escape(a)}$"), search_term=a)
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.dismiss_alert()
        if page.page.locator(f"div#{page.L3_MAP['ALLOW_PROCESS']}.in").count() > 0:
            page.close_l3_modal("ALLOW_PROCESS")
        after = [r.locator("td").nth(1).inner_text().strip() for r in page.l2_rows()]
        if not picked:
            # 재선택 자체가 실패하면 '차단' 으로 오판하지 않는다(가짜 pass 방지 — 14:29 run 교훈)
            self._add("warn",
                      "sc4m — 재선택 중복 충돌 [검증 불가 — 편집 picker 재선택 실패]",
                      f"입력: {b!r} 편집 → {a!r} 재선택 시도 / 결과: picker 선택 0건({msg!r}), "
                      f"{after} — sc4l 과 동일 원인(편집 모달 picker), 메커니즘 실측 후 재검증",
                      sc=4, highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      merge_key="szproc_reselect::picker::warn::not_working",
                      repro=f"1. {b} 편집 → '프로세스 선택'\n2. picker 에서 {a} 선택 시도\n3. 선택 반영 여부")
        else:
            dup = after.count(a) > 1
            blocked = (not dup) and (a in after) and (b in after)   # 차단되어 원상 유지
            self._add("warn" if dup else "pass",
                      "sc4m — 재선택으로 중복 유발(B→A): 중복 차단/생략 여부",
                      f"입력: {b!r} 편집 → 이미 등록된 {a!r} 로 재선택 '수정'({msg!r}) / "
                      f"결과: {after} "
                      + ("[★동일 프로세스 중복 행 생성 — 등록 경로(생략 안내)와 달리 변경 경로는 "
                         "중복 검사 누락]" if dup else "(차단/생략 — 원상 유지)" if blocked
                         else "(처리됨)"), sc=4,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      merge_key=("szproc_dup::reselect::warn::no_dup_check" if dup else None),
                      repro=f"1. {a}, {b} 2건 등록\n2. {b} 편집 → {a} 로 재선택 → '수정'\n"
                            "3. 중복 처리(차단/생략) 확인")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4n: ★태그 항목 편집 (태그 수정 전무였음) — sc3e 대응 ──────────
    def test_scenario4n_tag_item_edit(self, logged_in_page, settings):
        """태그 탭 항목 편집 — 이름 링크는 td[2](순위 컬럼 시프트). 로드값 + 설명 수정 반영."""
        print("\n━━ [프로세스] sc4n: 태그 항목 편집 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_l2_modal(self._TPL)
        page.switch_l2_tab("태그")
        if page.l2_item_count() == 0:
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_register("ALLOW_PROCESS", tag=True, count=1)
            page.l3_add_message("ALLOW_PROCESS")
        tag_name = page.l2_rows()[0].locator("td").nth(2).inner_text().strip()

        # 태그 탭 이름 링크 = td[2] (순위 시프트 — 2026-07-09 실측)
        page.l2_rows()[0].locator("td").nth(2).locator("a").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(700)
        loaded = page.l3_selected_name("ALLOW_PROCESS")
        DESC = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        page.fill(DESC, "sc4n_tag_desc")
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.dismiss_alert()

        page.l2_rows()[0].locator("td").nth(2).locator("a").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(700)
        desc_after = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        page.close_l3_modal("ALLOW_PROCESS")
        ok = (loaded == tag_name) and desc_after == "sc4n_tag_desc"
        self._add("pass" if ok else "fail",
                  "sc4n — 태그 항목 편집: 로드값 일치 + 설명 수정 재오픈 반영",
                  f"결과: 로드 태그={loaded!r}(기대 {tag_name!r}), 커밋={msg!r}, "
                  f"재오픈 설명={desc_after!r}(기대 'sc4n_tag_desc')", sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 태그 탭 이름 링크 → L3 편집\n2. 설명 변경 → '수정'\n3. 재오픈 반영")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4o: 설명 특수문자 + 500자 (수정 경로 재읽기) — sc3i 대응 ──────
    def test_scenario4o_desc_special_long_in_modify(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc4o: 설명 특수문자/500자(수정 경로) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page, self._TPL)
        DESC = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        results = {}
        for label, val in [("특수문자", "수정<>&!@# 특수"), ("500자", "나" * 500)]:
            page.l2_open_item_edit(0)
            page.fill(DESC, val)
            page.l3_add_message("ALLOW_PROCESS", button="수정")
            page.dismiss_alert()
            page.l2_open_item_edit(0)
            back = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
            page.close_l3_modal("ALLOW_PROCESS")
            results[label] = (back == val, len(back))
        ok = all(v[0] for v in results.values())
        self._add("pass" if ok else "warn",
                  "sc4o — 수정 경로 설명 특수문자/500자 저장 재읽기 (생성 sc3i 대응)",
                  f"결과: 특수문자 일치={results['특수문자'][0]}, "
                  f"500자 일치={results['500자'][0]}(저장 {results['500자'][1]}자)"
                  + ("" if ok else " [생성 경로(sc3i 수용)와 불일치 — 수정 경로 손실/변형]"), sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  merge_key=(None if ok else "szproc_desc::modify_special::warn::path_mismatch"),
                  repro="1. 항목 편집 → 설명 특수문자/500자 → '수정'\n2. 재오픈 → 그대로 저장됐는지")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4p: 다중 등록 상태에서 1개만 편집 → 나머지 불변 — sc3n 대응 ────
    def test_scenario4p_edit_isolation_multi(self, logged_in_page, settings):
        """3건 등록 상태에서 가운데 1건만 설명 수정 → 나머지 2건 이름·설명·옵션 불변(편집 격리)."""
        print("\n━━ [프로세스] sc4p: 다중 상태 편집 격리 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_l2_modal(self._TPL)
        page.l2_bulk_remove()
        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=3)
        page.l3_add_message("ALLOW_PROCESS")

        def _snapshot():
            return [(r.locator("td").nth(1).inner_text().strip(),
                     r.locator("td").nth(2).inner_text().strip()) for r in page.l2_rows()]
        before = _snapshot()

        page.l2_open_item_edit(1)   # 가운데 항목만
        DESC = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        page.fill(DESC, "sc4p_mid")
        page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.dismiss_alert()
        after = _snapshot()
        others_ok = (len(after) == 3 and after[0] == before[0] and after[2] == before[2])
        target_ok = len(after) == 3 and after[1][1] == "sc4p_mid"
        ok = others_ok and target_ok
        self._add("pass" if ok else "fail",
                  "sc4p — 다중 등록 중 1건만 수정 → 대상만 변경·나머지 불변(편집 격리)",
                  f"입력: 3건 중 2번째만 설명 'sc4p_mid' / 결과: 대상 반영={target_ok}, "
                  f"나머지 불변={others_ok} (전={before} 후={after})", sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                  repro="1. 3건 등록\n2. 2번째만 편집 → 설명 변경 → '수정'\n"
                        "3. 2번째만 바뀌고 1·3번째 그대로인지")
        page.l2_bulk_remove()
        page.close_l2_modal()
