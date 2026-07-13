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
        """sc4 공용 — tpl(해당 타입)에 프로세스 1건 확보 후 L2 열린 상태로 반환.
        등록 직후 리스트 재렌더는 비동기 — 행 attach 까지 기다려서 반환 직후 판독을 보장
        (같은 stale 판독 함정 3회째: sc4g 재오픈 프로브 → sc4q _ensure_tags → sc4i 16:29 run)."""
        page.navigate_to_clean()
        page.ensure_template(tpl, ttype)
        page.open_l2_modal(tpl)
        if page.l2_item_count() == 0:
            page.open_l3_add(ttype)
            page.l3_register(ttype, count=1)
            page.l3_add_message(ttype)
            page.dismiss_alert()
        # ★행 attach 대기는 무조건(등록 분기 밖) — 기존 항목 경로도 모달 오픈 직후
        #   재렌더로 순간 detach 가능(stale 함정 4회째, 12:27 run sc4k IndexError)
        try:
            page.page.locator(
                f"{page.SEL_L2_MODAL} tbody tr:visible input[type='checkbox']"
            ).first.wait_for(state="attached", timeout=page._TIMEOUT_TABLE)
        except Exception:
            pass

    def _row_item_status_on(self, page, idx: int = 0) -> bool:
        """L2 행 상태 셀 ON 여부 — ★재정정(Chrome 프로브 2026-07-13): 'on' 클래스는
        항상 붙음(무의미)·checked 는 저장값 반전·비주얼은 XOR CSS 로 저장값을 정확히
        표시. 클래스 판독(2026-07-09 정정 포함)이 '항상 ON' 오탐 원인 — 비주얼 판독으로
        교체(page.l2_status_display_on 참조)."""
        return bool(page.l2_status_display_on(idx))

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
        # ①결함 장면 사전 컷 — 편집을 열면 상태 셀이 갱신돼 버려 판정 후 캡처는 모순 증거가 됨
        #   (사용자 지적 2026-07-10: 카드 스크린샷이 OFF 로 찍혀 '먼소리야')
        shots = []
        if after_on:
            shots.append(self._shot(
                "sc4g_목록ON",
                highlight=(page.l2_rows()[0].locator("td").nth(4) if page.l2_rows() else None),
                caption="비활성 '수정' 후 — 목록 상태는 계속 ON (결함 장면)"))
        page.l2_open_item_edit(0)
        reload_inactive = page.l3_scope("ALLOW_PROCESS").locator(
            "input#DELETE").first.is_checked()
        # 표시만 어긋나면 L2 재오픈(신규 fetch)으로 고쳐지는지 — 갱신 지연 vs 항상 ON 렌더 판별
        # (Chrome 실측 2026-07-10: 서버는 status=DELETE 를 내려주는데 재오픈 후에도 ON)
        fresh_on = None
        if after_on and reload_inactive:
            page.close_l3_modal("ALLOW_PROCESS")
            page.close_l2_modal()
            page.open_l2_modal(tpl)
            # open_l2_modal 은 모달 attach 까지만 대기 — 행 렌더를 기다린다
            # (09:15 run: 재오픈 직후 l2_rows()=[] → IndexError 크래시)
            try:
                page.page.locator(
                    f"{page.SEL_L2_MODAL} tbody tr:visible input[type='checkbox']"
                ).first.wait_for(state="attached", timeout=page._TIMEOUT_TABLE)
            except Exception:
                pass
            fresh_on = self._row_item_status_on(page) if page.l2_rows() else None
            if fresh_on:
                shots.append(self._shot(
                    "sc4g_재조회ON",
                    highlight=(page.l2_rows()[0].locator("td").nth(4)
                               if page.l2_rows() else None),
                    caption="L2 를 닫고 다시 열어도(신규 조회) 여전히 ON — 저장은 비활성"))
            page.l2_open_item_edit(0)
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
                  ("sc4g — 상태 '비활성' 저장은 되는데 목록 상태 표시는 계속 ON — 표시 결함"
                   if (not ok and display_only) else
                   "sc4g — 항목 상태 활성→비활성 '수정': L2 표시·재오픈 일치(+원복)"),
                  f"결과: 이전 ON={before_on} → 비활성 후 ON={after_on}(기대 False), "
                  f"재오픈 비활성 checked={reload_inactive}, 원복 후 ON={restored_on}"
                  + ((" [★저장은 정상(재오픈 비활성)인데 L2 상태 표시는 모달 재오픈(신규 조회) "
                      "후에도 ON — 갱신 지연이 아니라 상태 셀이 저장값 미반영(항상 ON 렌더). "
                      "옵션 셀은 즉시 갱신되는 것과 대조적]" if fresh_on
                      else " [★저장은 정상(재오픈 비활성)인데 L2 행 상태 표시가 갱신 안 됨(4s 폴링) — "
                           "리스트 갱신 버그. 옵션 셀은 즉시 갱신되는 것과 대조적]")
                     if (not ok and display_only) else ""), sc=4,
                  highlight=page.l2_rows()[0].locator("td").nth(4) if page.l2_rows() else None,
                  screenshots=([s for s in shots if s] or None),
                  # 결과 동일한 타입·요소는 가로 병합(사용자 지시 2026-07-10)
                  merge_key=("szproc_item_status_display"
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
        # 앱 JS 예외 수집 — '수정' 클릭이 서버 도달 전에 죽는 결함 분류용
        # (Chrome 실측 2026-07-10: 거부 타입은 정상값 수정도 'isProcessRestart is not defined' 로 불발)
        js_errors = []
        _collect = lambda exc: js_errors.append(str(exc).splitlines()[0][:120])
        page.page.on("pageerror", _collect)
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = self._tpl_for(ttype)
            DESC = f"div#{page.L3_MAP[ttype]}.in {page.SEL_L3_DESC}"
            self._ensure_item(page, tpl, ttype)
            rows0 = page.l2_rows()
            if not rows0:
                page.close_l2_modal()
                self._add("warn", f"sc4i — {ko}: 설명 3000자 [검증 불가 — 항목 확보 실패]",
                          f"대상: {tpl!r} / 등록 후에도 행 0건 — 재실측 필요", sc=4)
                continue
            item = rows0[0].locator("td").nth(1).inner_text().strip()
            ctx = f"{tpl!r} 의 {item!r}"   # 카드에 대상 컨텍스트 명시(사용자 지적 2026-07-10)
            page.l2_open_item_edit(0)
            page.fill(DESC, "가" * 3000)
            # 시간 서사 카드 — 대비 컷(입력→클릭 직후→재오픈) 수집(사용자 지적 2026-07-10)
            shots = [self._shot(f"sc4i_{ttype}_3000자_입력",
                                highlight=page.l3_scope(ttype).locator(page.SEL_L3_DESC),
                                caption="설명 3000자 입력 — '수정' 클릭 직전")]
            e0 = len(js_errors)
            msg = page.l3_add_message(ttype, button="수정")
            ovf_errs = js_errors[e0:]
            raw_err = "서버에서 오류" in (msg or "")
            shots.append(self._shot(f"sc4i_{ttype}_클릭직후",
                                    caption=f"'수정' 클릭 직후 — 경고={msg!r}"))
            page.dismiss_alert()
            if page.page.locator(f"div#{page.L3_MAP[ttype]}.in").count() > 0:
                page.close_l3_modal(ttype)

            # 재오픈 — 실제 저장값 대조 (커밋 메시지만 믿는 은폐 금지)
            page.l2_open_item_edit(0)
            stored = page.l3_scope(ttype).locator(page.SEL_L3_DESC).first.input_value()
            n = len(stored)
            shots.append(self._shot(f"sc4i_{ttype}_재오픈",
                                    highlight=page.l3_scope(ttype).locator(page.SEL_L3_DESC),
                                    caption=f"재오픈 — 설명 {n}자(3000자 저장 안 됨)"))
            # merge_key = 요소(타입)별 — sc3l(생성)과 같은 키로 세로 병합(3↔4 한 카드,
            #   결과가 다르면 리포터가 시나리오별 줄로 분리 표기)
            if ovf_errs and n == 0 and not raw_err:
                # ★JS 오류 불발 = '3000자 저장 처리' 결함이 아니라 편집 불능 결함의 한 사례
                #   — 별도 카드 대신 편집 불능 카드로 귀속(사용자 지적 2026-07-10: 중복 카드)
                self._add("warn",
                          f"sc4i — {ko}: 편집 '수정'이 적용 안 됨 — 설명·상태 변경 불가(앱 JS 오류)",
                          f"대상: {ctx} / 입력: 설명 3000자 + '수정' / 결과: 무반응(경고 없음), "
                          f"재오픈 {n}자 [편집 '수정' 자체가 JS 오류로 불발 — 3000자 무관, "
                          f"아래 정상값 재수정과 동일 결함: {ovf_errs[0]}]",
                          sc=4,
                          screenshots=shots,
                          merge_key=f"szproc_item_edit_broken::{ttype}",
                          repro=f"1. {ko} 템플릿 {tpl} 의 항목 {item} 편집 → '수정'\n"
                                "2. 무반응(콘솔 ReferenceError) — 입력값 무관")
            else:
                # ★증상별 카드 분리(사용자 지시 2026-07-14): 생성 경로(raw 서버 오류)와
                #   수정 경로(조용한 미저장)는 다른 증상 — 제목·병합 키를 증상 기준으로.
                if raw_err:
                    verdict, note = "warn", "[raw 서버 오류 — 생성(sc3l)과 동일, 수정 경로도 가드 부재]"
                    label_i = "sc4i — 설명 3000자 → raw 서버 오류(클라 길이 가드 부재)"
                    mk_i = "szproc_desc_ovf::PROCESS::raw"
                elif n == 3000:
                    verdict, note = ("warn",
                        "[★경로 불일치 — 생성은 3000자를 서버 오류로 차단하는데 수정 경로는 "
                        "그대로 DB 저장. 수정이 생성 검증을 우회]")
                    label_i = "sc4i — 설명 3000자 수정 → 생성 검증 우회 저장"
                    mk_i = "szproc_desc_ovf::PROCESS::bypass"
                elif 0 < n < 3000:
                    verdict, note = "warn", f"[조용한 절단 — 안내 없이 {n}자로 잘려 저장]"
                    label_i = "sc4i — 설명 3000자 수정 → 조용한 절단 저장"
                    mk_i = "szproc_desc_ovf::PROCESS::clip"
                else:
                    verdict, note = "warn", "[조용한 미저장 — 경고 없이 설명 유실]"
                    label_i = "sc4i — 설명 3000자 수정 → 조용한 미저장(경고 없음)"
                    mk_i = "szproc_desc_ovf::PROCESS::silent"
                self._add(verdict,
                          label_i,
                          f"대상: {ko} — {ctx} / 입력: 3000자 + '수정' / 결과: 경고={msg!r}, "
                          f"재오픈 저장={n}자 {note}",
                          sc=4,
                          screenshots=shots,
                          # 같은 증상끼리만 타입 가로 병합(2026-07-10 정책 + 2026-07-14 증상 분리)
                          merge_key=mk_i,
                          repro=f"1. {ko} 템플릿 {tpl} 의 항목 {item} 편집 → 설명 3000자 → '수정'\n"
                                "2. 재오픈 → 실제 저장 길이 확인\n3. 생성 경로(서버 오류)와 비교")

            # 경계 입력 이후 같은 항목 정상 재수정 — 오염/복구(사용자 지적 2026-07-09)
            page.fill(DESC, "sc4i_recover")
            # 대비 컷 — fail(복구 실패) 카드에 스토리가 없으면 _R 이 6분 테스트를 통째로
            # 재생(teardown +343s, 12:27 run) → 예상된 결함 카드는 직접 첨부(sc4n 동일 원칙)
            rec_shots = [self._shot(f"sc4i_{ttype}_복구입력",
                                    highlight=page.l3_scope(ttype).locator(page.SEL_L3_DESC),
                                    caption="정상값 'sc4i_recover' 입력 — '수정' 클릭 직전")]
            e1 = len(js_errors)
            msg2 = page.l3_add_message(ttype, button="수정")
            rec_errs = js_errors[e1:]
            rec_shots.append(self._shot(f"sc4i_{ttype}_복구클릭직후",
                                        caption=f"'수정' 클릭 직후 — 경고={msg2!r}"))
            page.dismiss_alert()
            if page.page.locator(f"div#{page.L3_MAP[ttype]}.in").count() > 0:
                page.close_l3_modal(ttype)
            page.l2_open_item_edit(0)
            after = page.l3_scope(ttype).locator(page.SEL_L3_DESC).first.input_value()
            rec_shots.append(self._shot(f"sc4i_{ttype}_복구재오픈",
                                        highlight=page.l3_scope(ttype).locator(page.SEL_L3_DESC),
                                        caption=f"재오픈 — 설명 {after[:20]!r}"))
            page.close_l3_modal(ttype)
            recovered = after == "sc4i_recover"
            # 제목은 결함 중심으로 — '3000자'는 발견 경위일 뿐, JS 오류 분기의 실체는
            # 편집 불능(사용자 지적 2026-07-10: 경위를 제목에 쓰면 3000자가 이슈로 읽힘)
            broken = (not recovered) and bool(rec_errs)
            self._add("pass" if recovered else "fail",
                      (f"sc4i — {ko}: 편집 '수정'이 적용 안 됨 — 설명·상태 변경 불가(앱 JS 오류)"
                       if broken else
                       f"sc4i — {ko}: 3000자 시도 후 정상값 재수정 → 복구"),
                      f"대상: {ctx} / 입력: 'sc4i_recover' 재수정({msg2!r}) / "
                      f"재오픈={after[:30]!r}, 복구={recovered}"
                      + ("" if recovered else
                         (f" [★편집 '수정'이 앱 JS 오류로 불능 — 3000자와 무관"
                          f"(정상값도 동일 실패), 무반응·서버 미도달: {rec_errs[0]}]" if broken
                          else " [경계 입력 후 항목 정상 수정 불가 — 상태 오염]")),
                      sc=4,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody tr:visible"),
                      screenshots=(([s for s in rec_shots if s] or None)
                                   if not recovered else None),
                      merge_key=(f"szproc_item_edit_broken::{ttype}" if broken else None),
                      repro=(f"1. {ko} 템플릿 {tpl} 의 항목 {item} 이름 링크 → 설명만 변경 → '수정'\n"
                             "2. 무반응(모달 유지·경고 없음, 콘솔 ReferenceError)\n"
                             "3. 재오픈 → 반영 안 됨 (3000자 무관)" if broken else
                             f"1. {ko} 3000자 시도 직후 같은 항목 재편집\n2. 정상 설명 '수정'\n3. 반영 확인"))
            page.l2_bulk_remove()
            page.close_l2_modal()
        page.page.remove_listener("pageerror", _collect)

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
        if not picked:
            # 재선택 실패 = 자동화 문제 — 제품 FAIL 로 오판 금지(sc4m 과 동일 가드, 08:06 run 오탐 교훈)
            self._add("warn",
                      "sc4l — 등록 프로세스 재선택 변경 [검증 불가 — 편집 picker 재선택 실패]",
                      f"입력: {cur!r} 편집 → 재선택 0건({msg!r}) / 결과: L2 {cnt}건, "
                      f"행 이름={new_name!r} — 메커니즘 재실측 필요", sc=4,
                      highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody"),
                      merge_key="szproc_reselect::picker::warn::not_working",
                      repro="1. 등록 항목 이름 링크 → '프로세스 선택'\n2. picker 선택 반영 여부")
        else:
            changed = cnt == 1 and new_name == picked[0] and new_name != cur
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
                      f"대상: {self._TPL!r} 개별 프로세스 탭 / 입력: {b!r} 편집 → 이미 등록된 "
                      f"{a!r} 로 재선택 '수정'({msg!r}) / 결과: {after} "
                      + ("[★동일 프로세스 중복 행 생성 — 등록 경로(생략 안내)와 달리 변경 경로는 "
                         "중복 검사 누락. 대조: 미등록 항목으로의 재선택 변경은 정상 반영(sc4l 통과) "
                         "— 변경 자체는 정상, 중복 검사만 빠짐]" if dup
                         else "(차단/생략 — 원상 유지)" if blocked
                         else "(처리됨)"), sc=4,
                      highlight=page.page.locator(
                          f"{page.SEL_L2_MODAL} tbody tr:visible", has_text=a),
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
        page.l2_open_item_edit(0, tag=True)
        loaded = page.l3_selected_name("ALLOW_PROCESS")
        DESC = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        page.fill(DESC, "sc4n_tag_desc")
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.dismiss_alert()

        page.l2_open_item_edit(0, tag=True)
        desc_after = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        page.close_l3_modal("ALLOW_PROCESS")
        ok = (loaded == tag_name) and desc_after == "sc4n_tag_desc"
        self._add("pass" if ok else "fail",
                  "sc4n — 태그 항목 편집: 로드값 일치 + 설명 수정 재오픈 반영",
                  f"결과: 로드 태그={loaded!r}(기대 {tag_name!r}), 커밋={msg!r}, "
                  f"재오픈 설명={desc_after!r}(기대 'sc4n_tag_desc')", sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody tr:visible"),
                  repro="1. 태그 탭 이름 링크 → L3 편집\n2. 설명 변경 → '수정'\n3. 재오픈 반영")
        page.l2_bulk_remove()
        page.close_l2_modal()

        # ── 거부 타입 태그 편집 — 실측(2026-07-10): 프로세스와 같은 수정 핸들러라
        #    'isProcessRestart is not defined' JS 오류로 저장 불능 → 결함 카드(sc4i 와 병합)
        js_errors = []
        _collect = lambda exc: js_errors.append(str(exc).splitlines()[0][:120])
        page.page.on("pageerror", _collect)
        tpl_d = self._tpl_for("DENY_PROCESS")
        page.navigate_to_clean()
        page.ensure_template(tpl_d, "DENY_PROCESS")
        page.open_l2_modal(tpl_d)
        page.switch_l2_tab("태그")
        if page.l2_item_count() == 0:
            page.open_l3_add("DENY_PROCESS")
            page.l3_register("DENY_PROCESS", tag=True, count=1)
            page.l3_add_message("DENY_PROCESS")
            page.dismiss_alert()
        if page.l2_item_count() == 0:
            page.close_l2_modal()
            page.page.remove_listener("pageerror", _collect)
            self._add("warn", "sc4n — 거부 프로세스: 태그 편집 [검증 불가 — 태그 등록 실패]",
                      "거부 템플릿 태그 등록 0건 — 재실측 필요", sc=4)
            return
        tag_d = page.l2_rows()[0].locator("td").nth(2).inner_text().strip()
        page.l2_open_item_edit(0, tag=True)
        DESC_D = f"div#{page.L3_MAP['DENY_PROCESS']}.in {page.SEL_L3_DESC}"
        page.fill(DESC_D, "sc4n_deny_tag")
        # 대비 컷(입력→클릭 직후→재오픈) — sc4i 미러. 예상된 결함 카드에 스토리를 직접
        # 첨부해야 _R 리턴 재생(예기치 못한 fail 전용)이 발동하지 않음 (16:29 run 55s 낭비)
        shots_d = [self._shot("sc4n_deny_설명입력",
                              highlight=page.l3_scope("DENY_PROCESS").locator(page.SEL_L3_DESC),
                              caption="설명 'sc4n_deny_tag' 입력 — '수정' 클릭 직전")]
        e0 = len(js_errors)
        msg_d = page.l3_add_message("DENY_PROCESS", button="수정")
        errs = js_errors[e0:]
        shots_d.append(self._shot("sc4n_deny_클릭직후",
                                  caption=f"'수정' 클릭 직후 — 무반응(경고={msg_d!r})"))
        page.dismiss_alert()
        if page.page.locator(f"div#{page.L3_MAP['DENY_PROCESS']}.in").count() > 0:
            page.close_l3_modal("DENY_PROCESS")
        page.l2_open_item_edit(0, tag=True)
        after_d = page.l3_scope("DENY_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        shots_d.append(self._shot("sc4n_deny_재오픈",
                                  highlight=page.l3_scope("DENY_PROCESS").locator(page.SEL_L3_DESC),
                                  caption=f"재오픈 — 설명 {after_d!r}(수정 미반영)"))
        page.close_l3_modal("DENY_PROCESS")
        page.page.remove_listener("pageerror", _collect)
        applied = after_d == "sc4n_deny_tag"
        broken = (not applied) and bool(errs)
        self._add("pass" if applied else "fail",
                  ("sc4n — 거부 프로세스: 편집 '수정'이 적용 안 됨 — 설명·상태 변경 불가(앱 JS 오류)"
                   if broken else
                   "sc4n — 거부 프로세스: 태그 항목 편집 반영"),
                  f"대상: {tpl_d!r} 태그 탭의 {tag_d!r} / 입력: 설명 'sc4n_deny_tag' "
                  f"'수정'({msg_d!r}) / 재오픈={after_d!r}, 반영={applied}"
                  + (f" [★태그 탭도 동일 — 편집 '수정'이 앱 JS 오류로 불능(개별 프로세스와 같은 "
                     f"수정 핸들러), 무반응·서버 미도달: {errs[0]}]" if broken else ""), sc=4,
                  highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody tr:visible"),
                  screenshots=(([s for s in shots_d if s] or None) if not applied else None),
                  merge_key=("szproc_item_edit_broken::DENY_PROCESS" if broken else None),
                  repro=f"1. 거부 템플릿 {tpl_d} 태그 탭 → {tag_d} 이름 링크 → 설명만 변경 → '수정'\n"
                        "2. 무반응(모달 유지·경고 없음, 콘솔 ReferenceError)\n3. 재오픈 → 반영 안 됨")
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

    # ══ 태그 탭 수정 클래스 대칭 (Chrome 실측 2026-07-10) — sc4l/4m/4i/4g 의 태그판 ══

    def _ensure_tags(self, page, tpl: str, n: int = 1) -> list[str]:
        """태그 탭에 태그 n건 확보 — L2 태그 탭 열린 상태로 이름 리스트 반환(td[2])."""
        page.navigate_to_clean()
        page.ensure_template(tpl, "ALLOW_PROCESS")
        page.open_l2_modal(tpl)
        page.switch_l2_tab("태그")
        if page.l2_item_count() != n:
            page.l2_bulk_remove()
            page.open_l3_add("ALLOW_PROCESS")
            page.l3_register("ALLOW_PROCESS", tag=True, count=n)
            page.l3_add_message("ALLOW_PROCESS")
            page.dismiss_alert()
            # 등록 직후 리스트 재렌더는 비동기 — 행 attach 대기 없이 읽으면 []
            # (14:14 run sc4q '검증 불가 — 2건 확보 실패' 원인)
            try:
                page.page.locator(
                    f"{page.SEL_L2_MODAL} tbody tr:visible input[type='checkbox']"
                ).first.wait_for(state="attached", timeout=page._TIMEOUT_TABLE)
            except Exception:
                pass
        return [r.locator("td").nth(2).inner_text().strip() for r in page.l2_rows()]

    # ── sc4q: 태그 재선택 중복 (sc4m 태그판 — 편집 picker=radio 실측 2026-07-10) ──
    def test_scenario4q_tag_reselect_duplicate(self, logged_in_page, settings):
        """태그 B 편집 → 이미 등록된 A 로 radio 재선택 '수정' → 중복 차단/생략 여부.
        실측(2026-07-10): 경고 없이 동일 태그 중복 행 생성 — 변경 경로 중복 검사 누락."""
        import re as _re
        print("\n━━ [프로세스] sc4q: 태그 재선택 중복 충돌 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        names = self._ensure_tags(page, "[AUTO]_sz_proc_4q", n=2)
        if len(names) < 2:
            page.close_l2_modal()
            self._add("warn", "sc4q — 태그 재선택 중복 [검증 불가 — 2건 확보 실패]",
                      f"결과: {names}", sc=4)
            return
        a, b = names[0], names[1]
        page.l2_open_item_edit(1, tag=True)
        picked = page.l3_register("ALLOW_PROCESS", tag=True, count=1,
                                  name_pattern=_re.compile(rf"^{_re.escape(a)}$"))
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.dismiss_alert()
        if page.page.locator(f"div#{page.L3_MAP['ALLOW_PROCESS']}.in").count() > 0:
            page.close_l3_modal("ALLOW_PROCESS")
        after = [r.locator("td").nth(2).inner_text().strip() for r in page.l2_rows()]
        if not picked:
            self._add("warn",
                      "sc4q — 태그 재선택 중복 [검증 불가 — 편집 picker 재선택 실패]",
                      f"입력: {b!r} 편집 → {a!r} 재선택 시도 / 결과: 선택 0건({msg!r}), {after}",
                      sc=4, merge_key="szproc_reselect::tag_picker::warn::not_working")
        else:
            dup = after.count(a) > 1
            self._add("warn" if dup else "pass",
                      "sc4q — 재선택으로 중복 유발(B→A): 중복 차단/생략 여부",
                      f"대상: '[AUTO]_sz_proc_4q' 태그 탭 / 입력: {b!r} 편집 → 이미 등록된 "
                      f"{a!r} 로 재선택 '수정'({msg!r}) / 결과: {after} "
                      + ("[★동일 태그 중복 행 생성 — 등록 경로(생략 안내)와 달리 변경 경로는 "
                         "중복 검사 누락(개별 프로세스와 동일 결함)]" if dup
                         else "(차단/생략 — 원상 유지)"), sc=4,
                      highlight=page.page.locator(
                          f"{page.SEL_L2_MODAL} tbody tr:visible", has_text=a),
                      # 결과 동일(중복 생성) → 프로세스(sc4m)와 가로 병합(사용자 지시 2026-07-10)
                      merge_key=("szproc_dup::reselect::warn::no_dup_check" if dup else None),
                      repro=f"1. 태그 {a}, {b} 2건 등록\n2. {b} 편집 → {a} 재선택 → '수정'\n"
                            "3. 중복 처리(차단/생략) 확인")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4r: 태그 설명 3000자 (sc4i 태그판 — 서버 응답을 실측해 모드 분류) ─────
    def test_scenario4r_tag_desc_overflow_in_modify(self, logged_in_page, settings):
        """태그 편집 설명 3000자 → '수정'. ★정정(run 실측 2026-07-13): '요청 미발송
        무반응'(2026-07-10 수동 프로브)은 JS setter 미동기 오관찰 — 실제로는 PUT
        /processTag/szTag 가 발송되고 서버 500, UI 가 경고 없이 삼킴(프로세스 설명
        오버플로와 동일 계열). 네트워크 응답을 수집해 문구를 실측으로 분기."""
        print("\n━━ [프로세스] sc4r: 태그 설명 3000자(수정 경로) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        names = self._ensure_tags(page, "[AUTO]_sz_proc_4r", n=1)
        tag = names[0] if names else "?"
        DESC = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        page.l2_open_item_edit(0, tag=True)
        base_desc = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        page.fill(DESC, "가" * 3000)
        # 시간 서사 카드 — 대비 컷 수집(사용자 지적 2026-07-10: 마지막 장면 1장으론 증거 안 됨)
        shots = [self._shot("sc4r_3000자_입력",
                            highlight=page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC),
                            caption="설명 3000자 입력 — '수정' 클릭 직전")]
        # '수정' 커밋의 서버 응답 실측 — "무반응"이 미발송인지 raw 오류 은폐인지 판별
        put_statuses: list[int] = []
        def _collect_put(resp):
            try:
                if "/processTag/" in resp.url and resp.request.method == "PUT":
                    put_statuses.append(resp.status)
            except Exception:
                pass
        page.page.on("response", _collect_put)
        msg = page.l3_add_message("ALLOW_PROCESS", button="수정")
        page.page.wait_for_timeout(400)
        page.page.remove_listener("response", _collect_put)
        page.dismiss_alert()
        if page.page.locator(f"div#{page.L3_MAP['ALLOW_PROCESS']}.in").count() > 0:
            shots.append(self._shot("sc4r_클릭직후",
                                    caption="'수정' 클릭 직후 — 무반응(모달 유지·경고 없음)"))
            page.close_l3_modal("ALLOW_PROCESS")
        page.l2_open_item_edit(0, tag=True)
        stored = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        shots.append(self._shot("sc4r_재오픈",
                                highlight=page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC),
                                caption=f"재오픈 — 설명 {len(stored)}자(3000자 저장 안 됨)"))
        page.close_l3_modal("ALLOW_PROCESS")
        n = len(stored)
        srv = (f"서버 응답 {put_statuses}" if put_statuses else "저장 요청 미발송")
        # ★증상별 카드 분리(사용자 지시 2026-07-14) — 등록 경로(raw 알림)와 병합은
        #   같은 증상일 때만.
        if n == 3000:
            verdict, note = "warn", "[★3000자 그대로 저장 — 생성/프로세스 경로와 불일치]"
            label_r = "sc4r — 태그: 설명 3000자 수정 → 검증 우회 저장"
            mk_r = "szproc_desc_ovf::TAG::bypass"
        elif stored == base_desc:
            if any(s >= 500 for s in put_statuses):
                note = (f"[raw 서버 오류 은폐 — PUT {put_statuses} 인데 UI 는 경고 없이 "
                        "무반응·미저장(프로세스 설명 오버플로와 동일 계열, 측정=허용 템플릿. "
                        "거부는 편집 불능으로 검증 불가)]")
            else:
                note = f"[조용한 미저장 — 경고 없이 무반응({srv})]"
            verdict = "warn"
            label_r = "sc4r — 태그: 설명 3000자 → 조용한 미저장(경고 없음)"
            mk_r = "szproc_desc_ovf::TAG::silent"
        else:
            verdict, note = "warn", f"[조용한 절단/변형 — {n}자로 저장]"
            label_r = "sc4r — 태그: 설명 3000자 수정 → 조용한 절단 저장"
            mk_r = "szproc_desc_ovf::TAG::clip"
        self._add(verdict,
                  label_r,
                  f"대상: '[AUTO]_sz_proc_4r' 태그 탭의 {tag!r} / 입력: 설명 3000자 + "
                  f"'수정'({msg!r}) / 재오픈 저장={n}자, {srv} {note}", sc=4,
                  screenshots=shots,
                  merge_key=mk_r,
                  repro=f"1. 태그 {tag} 편집 → 설명 3000자 → '수정'\n"
                        "2. 무반응 관찰\n3. 재오픈 → 실제 저장 길이")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4s: 태그 상태 비활성 → 행 표시 (sc4g 태그판 — 실측: 표시 ON 고정) ──
    def test_scenario4s_tag_status_display(self, logged_in_page, settings):
        """태그 상태 활성→비활성 '수정' → 행 상태 셀 표시 + 재오픈 저장값 대조.
        실측(2026-07-10): 저장 정상(재오픈 DELETE)인데 행 표시는 ON — 프로세스 행과 동일."""
        print("\n━━ [프로세스] sc4s: 태그 상태 비활성 → 행 표시 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_tags(page, "[AUTO]_sz_proc_4s", n=1)
        page.l2_open_item_edit(0, tag=True)
        page.l3_scope("ALLOW_PROCESS").locator("input#DELETE").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(150)
        page.l3_add_message("ALLOW_PROCESS", button="수정")
        # ★판독 정정(Chrome 2026-07-13): 클래스 아닌 비주얼(computed 색) 판독
        import time as _t
        deadline = _t.monotonic() + 4
        def _tag_row_on():
            return bool(page.l2_status_display_on(0))
        after_on = _tag_row_on()
        while after_on and _t.monotonic() < deadline:
            page.page.wait_for_timeout(250)
            after_on = _tag_row_on()
        # ①결함 장면 사전 컷 — 편집을 열면 상태 셀이 갱신돼 버림(사용자 지적 2026-07-10)
        shots = []
        if after_on:
            shots.append(self._shot(
                "sc4s_목록ON",
                highlight=(page.l2_rows()[0].locator("td").nth(5) if page.l2_rows() else None),
                caption="비활성 '수정' 후 — 목록 상태는 계속 ON (결함 장면)"))
        page.l2_open_item_edit(0, tag=True)
        saved_inactive = page.l3_scope("ALLOW_PROCESS").locator("input#DELETE").first.is_checked()
        page.close_l3_modal("ALLOW_PROCESS")
        # ②편집 열닫 후 재판독 — 갱신 트리거 실측
        page.page.wait_for_timeout(400)
        after_edit_on = _tag_row_on()
        if after_on and not after_edit_on:
            shots.append(self._shot(
                "sc4s_편집후OFF",
                highlight=(page.l2_rows()[0].locator("td").nth(5) if page.l2_rows() else None),
                caption="같은 태그 편집을 열었다 닫자 OFF 로 갱신 — 저장은 처음부터 비활성"))
        ok = saved_inactive and not after_on
        display_bug = saved_inactive and after_on
        self._add("pass" if ok else ("warn" if display_bug else "fail"),
                  ("sc4s — 상태 '비활성' 저장은 되는데 목록 상태 표시는 계속 ON — 표시 결함"
                   if display_bug else
                   "sc4s — 태그: 상태 활성→비활성 '수정' → 행 표시·재오픈 일치"),
                  f"대상: '[AUTO]_sz_proc_4s' 태그 탭 / 입력: 태그 비활성 '수정' / "
                  f"결과: 행 표시 ON={after_on}(기대 False), "
                  f"재오픈 비활성 checked={saved_inactive}, 편집 열닫 후 ON={after_edit_on}"
                  + (" [★목록 조회로는 저장값 미반영 — 해당 항목 편집 모달을 열었다 닫아야 "
                     "상태 셀 갱신. 개별 프로세스와 동일 결함]"
                     if display_bug else ""), sc=4,
                  highlight=(page.l2_rows()[0].locator("td").nth(5) if page.l2_rows() else None),
                  screenshots=([s for s in shots if s] or None),
                  # 결과 동일한 타입·요소는 가로 병합(사용자 지시 2026-07-10)
                  merge_key=("szproc_item_status_display" if display_bug else None),
                  repro="1. 태그 편집 → 상태 비활성 → '수정'\n"
                        "2. 행 상태 ON 으로 잘못 표시\n"
                        "3. 편집 열었다 닫으면 OFF 갱신(저장은 비활성이었음)")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc4t: 수정 모달 이름 특수문자 rename (sc3h 생성 특수문자와 경로 대칭) ──
    def test_scenario4t_name_special_char_rename(self, logged_in_page, settings):
        """생성(sc3h)이 특수문자 이름을 허용하므로 수정 경로도 동일한지 — rename 후 목록 대조."""
        print("\n━━ [프로세스] sc4t: 이름 특수문자 rename ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        sp = "[AUTO]_sz_proc_4t<>!@#"
        while sp in page.get_template_names():
            page.delete_template(sp)
            page.navigate_to()
        page.open_modify_modal(self._TPL)
        page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.fill(sp)
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        renamed = sp in page.get_template_names()
        # 생성 경로(sc3h: 특수문자 허용)와의 대칭 — rename 도 허용이면 pass, 다르면 warn
        self._add("pass" if renamed else "warn",
                  "sc4t — 수정 경로 이름 특수문자 rename (생성 sc3h 대응)",
                  f"입력: {self._TPL!r} → {sp!r} rename({msg!r}) / 결과: 목록 존재={renamed}"
                  + ("" if renamed else " [생성 경로(허용)와 불일치 — 수정 경로만 차단/실패]"), sc=4,
                  highlight=(page._row_locator(sp) if renamed else None),
                  merge_key=(None if renamed else "szproc_special_name::rename::warn::path_mismatch"),
                  repro=f"1. 수정 모달 이름에 특수문자({sp})\n2. 확인\n3. 목록 반영 대조")
        # 원상복귀(이름 되돌림) — 후속 테스트가 _TPL 을 쓰므로
        if renamed:
            page.open_modify_modal(sp)
            page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.fill(self._TPL)
            page.submit_and_message()
            page._close_modal_if_open()
            page.navigate_to()

    # ── sc4u: 수정 취소(닫기) — 변경 미커밋 (L1+L3, 매트릭스 감사 갭 2026-07-13) ──
    def test_scenario4u_modify_cancel_no_commit(self, logged_in_page, settings):
        """'수정' 없이 닫기로 나가면 변경이 저장되지 않아야 한다 — L1(이름)·L3(설명) 두
        컨텍스트. 닫기가 저장/잔존시키면 결함(암묵 커밋·모달 상태 누적). 취소 경로가
        스위트 전체에 전무하던 갭."""
        print("\n━━ [프로세스] sc4u: 수정 취소(닫기) 미커밋 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        # ── L1: 이름 변경 후 닫기 ──
        page.navigate_to_clean()
        page.ensure_template(self._TPL, "ALLOW_PROCESS")
        page.open_modify_modal(self._TPL)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._TPL + "_cancel")
        page._close_modal_if_open()          # '닫기' — 커밋 아님
        page.navigate_to()
        names = page.get_template_names()
        l1_kept = self._TPL in names and (self._TPL + "_cancel") not in names
        page.open_modify_modal(self._TPL)
        loaded = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        page._close_modal_if_open()
        l1_ok = l1_kept and loaded == self._TPL
        self._add("pass" if l1_ok else "warn",
                  "sc4u — L1 수정 취소(닫기): 이름 변경 미커밋",
                  f"입력: 이름 '{self._TPL}_cancel' 변경 후 '닫기' / 결과: 원명 유지={l1_kept}, "
                  f"재오픈 로드={loaded!r}"
                  + ("" if l1_ok else " [닫기가 변경을 저장/잔존 — 취소 semantics 결함]"), sc=4,
                  merge_key=(None if l1_ok else "szproc_cancel::warn::implicit_commit"),
                  repro="1. 수정 모달에서 이름 변경\n2. '수정' 없이 닫기\n3. 목록·재오픈 원값 유지")
        # ── L3: 설명 변경 후 닫기 ──
        self._ensure_item(page, self._TPL)
        page.l2_open_item_edit(0)
        DESC = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        before = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        page.fill(DESC, "sc4u_cancel")
        page.close_l3_modal("ALLOW_PROCESS")   # '닫기' — 커밋 아님
        page.l2_open_item_edit(0)
        after = page.l3_scope("ALLOW_PROCESS").locator(page.SEL_L3_DESC).first.input_value()
        page.close_l3_modal("ALLOW_PROCESS")
        l3_ok = after == before and after != "sc4u_cancel"
        self._add("pass" if l3_ok else "warn",
                  "sc4u — L3 편집 취소(닫기): 설명 변경 미커밋",
                  f"입력: 설명 'sc4u_cancel' 변경 후 닫기 / 결과: 재오픈 {after!r}(변경 전 {before!r})"
                  + ("" if l3_ok else " [닫기 후에도 변경 잔존 — 취소 semantics 결함 또는 모달 상태 누적]"),
                  sc=4,
                  merge_key=(None if l3_ok else "szproc_cancel::warn::implicit_commit"),
                  repro="1. 항목 편집에서 설명만 변경\n2. '수정' 없이 닫기\n3. 재오픈 → 변경 전 값")
        page.l2_bulk_remove()
        page.close_l2_modal()
