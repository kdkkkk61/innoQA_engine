"""시큐어존 정책 — 시나리오 4: EDIT(수정) 동작 검증 (sc3 ADD 전 영역 미러).

EDIT 모달은 ADD 와 같은 컨테이너(#addItemModal) 재사용 → 필드 gating/토글/picker/입력 동작은
ADD(sc3)와 동일하지만, **수정 컨텍스트에서도 동일하게 성립하는지 + 변경이 '수정' 저장으로 반영되는지**를
sc3 의 전 영역에 대해 검증 (사용자 지정 2026-06-18: 생성 시나리오에서 한 테스트는 수정에서도 다).

직접조작 확정 (Chrome MCP 2026-06-18, 콘솔 192.168.13.141):
  - 저장 버튼: btn-primary 2개 공존(ng-show) — EDIT 에선 "수정"(보임)/"등록"(숨김). submit_and_message 가 _first_visible 로 보이는 버튼 클릭.
  - EDIT 저장은 정상 in-place UPDATE (같은 이름/rename 모두 레코드 불변). 신규생성 아님.
  - 빈값 이름 수정 → "저장 하였습니다"(거짓 성공) + 이름 silent revert. ADD(필수 차단)와 불일치.
  - 기존 이름으로 rename → "이미 등록된 이름" 차단(정상).

cleanup 안 함 — [AUTO] 데이터 남김(sc1 세션시작/sc5 추후 신설에서만 정리, mid-stream 삭제 금지).
편집 대상: [AUTO]_szp_sc4(없으면 생성). gating/토글 카드는 변경 후 저장 안 하고 취소(base 보존).
4c=중복대상 [AUTO]_szp_sc4t 생성, 4w=rename [AUTO]_szp_sc4ren(마지막, base 소진).
"""
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase


class TestSecureZonePolicyScenario4Modify(SecureZonePolicyBase):
    """시큐어존 정책 — 시나리오 4: EDIT(수정), sc3 전 영역 미러."""

    _BASE = "[AUTO]_szp_sc4"
    _CUST_SEL = "div#addItemModal.in input#customOptionText"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAgentPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _ensure_policy(self, page, name) -> bool:
        page.navigate_to()
        if name in page.get_policy_names():
            return True
        page.open_add_modal()
        page.create_basic_policy(name)
        page.navigate_to()
        return name in page.get_policy_names()

    def _open_edit(self, page) -> bool:
        """base 보장 + 수정모달 진입. 실패 시 False."""
        if not self._ensure_policy(page, self._BASE):
            return False
        page.open_modify_modal(self._BASE)
        return True

    # ══ 4a: EDIT 진입 + 저장값 LOAD ════════════════════════════════
    def test_scenario4a_edit_enter_and_load(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4a: EDIT 진입 + 저장값 LOAD ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        if not self._open_edit(page):
            self._add("skip", "sc4a — 편집 대상 생성 실패", f"입력: - / 결과: {self._BASE} 미생성", sc=4)
            return
        name_val = page.page.locator(page.SEL_NAME).first.input_value()
        drive = page.drive_row_text()
        title = page.page.locator("div#addItemModal.in .modal-title").first.inner_text().strip()
        save_btn = page._first_visible(page.page.locator(page.SEL_SAVE_BTN))
        save_text = save_btn.inner_text().strip() if save_btn else "?"
        loaded = (name_val == self._BASE) and ("없음" not in drive)
        self._add("pass" if loaded else "fail",
                  "sc4a — 수정모달 진입 시 저장값 LOAD",
                  f"입력: '{self._BASE}' 수정 / 결과: 제목={title!r}, 이름='{name_val}', 드라이브행={drive!r}, "
                  f"보이는 저장버튼='{save_text}' (기대: 저장값 표시 + 버튼 '수정')",
                  sc=4, highlight=page.page.locator(page.SEL_NAME),
                  repro=(f"1. '{self._BASE}' 선택 → 수정\n2. 이름/드라이브/제어스위트가 저장값으로 뜨는지 확인"))
        page.close_edit_modal()

    # ══ 4b: 같은 이름 in-place 업데이트 + 재오픈 round-trip ═════════
    def test_scenario4b_edit_update_inplace(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4b: 같은 이름 in-place 업데이트 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc4b — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        before = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        page.open_modify_modal(self._BASE)
        page.fill(self._CUST_SEL, "sc4b_upd")
        msg = page.submit_and_message()
        page.navigate_to()
        after = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        updated = ("저장" in msg) and (len(after) == len(before)) and (self._BASE in after)
        self._add("pass" if updated else "fail",
                  "sc4b — 같은 이름 수정 저장 = in-place 업데이트(신규생성 아님)",
                  f"입력: 커스텀옵션 변경 후 (이름 유지) 수정 저장 / 결과: {msg!r}, [AUTO] {len(before)}→{len(after)}건 "
                  + ("(레코드 불변 = 정상)" if updated else "[결함: 저장 실패 또는 레코드 변동]"),
                  sc=4, repro="1. 수정\n2. 커스텀 옵션값 변경(이름 유지)\n3. '수정'\n4. 저장+개수 불변 확인")
        if self._BASE in after:
            page.open_modify_modal(self._BASE)
            cust_val = page.page.locator(self._CUST_SEL).first.input_value()
            # _add 를 모달 열린 채 호출(실패 시 스크린샷이 빈 필드를 잡도록), 그 뒤 close
            self._add("pass" if cust_val == "sc4b_upd" else "fail",
                      "sc4b — 수정 후 재오픈 시 변경값 유지(round-trip)",
                      f"입력: 커스텀='sc4b_upd' 저장 후 재오픈 / 결과: 재오픈 값={cust_val!r}", sc=4,
                      highlight=page.page.locator(self._CUST_SEL), repro="1. 재수정\n2. 커스텀값 유지 확인")
            page.close_edit_modal()

    # ══ 4c: 기존 이름으로 rename → 중복 차단 ═══════════════════════
    def test_scenario4c_edit_rename_duplicate_blocked(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4c: 기존 이름 rename 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        target = "[AUTO]_szp_sc4t"
        if not self._ensure_policy(page, self._BASE) or not self._ensure_policy(page, target):
            self._add("skip", "sc4c — 편집/중복 대상 생성 실패", f"입력: - / 결과: 미생성", sc=4); return
        page.open_modify_modal(self._BASE)
        page.fill(page.SEL_NAME, target)
        msg = page.submit_and_message()
        blocked = ("이미" in msg) or ("중복" in msg)
        self._add("pass" if blocked else "fail",
                  "sc4c — 기존 이름으로 rename 시 중복 차단",
                  f"입력: '{self._BASE}'→기존명 '{target}' 수정 / 결과: {msg!r} "
                  + ("(차단 정상)" if blocked else "[결함: 중복 rename 허용 = ADD(sc3c)와 불일치]"),
                  sc=4, highlight=page.page.locator(page.SEL_NAME),
                  repro=f"1. 수정\n2. 이름을 기존 '{target}'으로\n3. '수정' → '이미 등록된 이름' 확인")
        page._close_modal_if_open()

    # ══ 4d: 빈값 이름 수정 → 거짓 성공 + silent revert ══════════
    def test_scenario4d_edit_empty_name_silent_revert(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4d: 빈값 이름 수정 (ADD↔EDIT 불일치) ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc4d — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        page.open_modify_modal(self._BASE)
        page.fill(page.SEL_NAME, "")
        msg = page.submit_and_message()
        page.navigate_to()
        reverted = self._BASE in [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        saved_ok = "저장" in msg
        status = "warn" if (saved_ok and reverted) else ("pass" if not saved_ok else "fail")
        self._add(status, "sc4d — 빈값 이름 수정 처리(ADD↔EDIT 일치 여부)",
                  f"입력: 이름 빈값 수정 / 결과: {msg!r}, 원본명유지={reverted} "
                  + ("[ADD 는 '필수 입력값' 차단인데 EDIT 는 '저장 하였습니다'(거짓 성공)+이름 silent revert = 불일치]"
                     if (saved_ok and reverted) else ("[빈 이름 실제 저장=데이터 결함]" if saved_ok else "[차단=ADD 일치, 정상]")),
                  sc=4, highlight=page.page.locator(page.SEL_NAME),
                  repro="1. 수정\n2. 이름 전체 삭제\n3. '수정'\n4. 메시지/이름 변경 여부(ADD 차단과 비교)")
        page._close_modal_if_open()

    # ══ 4e: 타입(일반/반출) 전환 + 기본반출정책 singleton (sc3a) ════
    def test_scenario4e_edit_type_takeout(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4e: 타입/기본반출정책 (EDIT) ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4e — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        td = page.field_state("szAgentPolicyTypeDefault")
        self._add("pass" if td.get("checked") else "warn",
                  "sc4e — 수정 진입 시 타입 로드(일반)",
                  f"입력: '{self._BASE}'(일반) 수정 / 결과: 일반 radio checked={td.get('checked')}", sc=4,
                  repro="1. 일반 정책 수정\n2. 타입 '일반' 로드 확인")
        page.set_toggle("szAgentPolicyTypeTakeout", True)
        tt = page.field_state("szAgentPolicyTypeTakeout")
        self._add("pass" if tt.get("checked") else "fail",
                  "sc4e — EDIT 에서 타입 '반출' 전환",
                  f"입력: 반출 radio 클릭 / 결과: 반출 checked={tt.get('checked')}", sc=4,
                  repro="1. 수정\n2. 타입 '반출' 클릭\n3. 전환 확인")
        page.set_toggle("isSzAgentPolicyTypeTakeoutDefault", True)
        msg = page.cancel_confirm_modal()
        warned = "기본반출정책" in msg or "변경" in msg
        self._add("pass" if warned else "warn",
                  "sc4e — 기본반출정책 체크 시 singleton 경고(취소)",
                  f"입력: 기본반출정책 체크 / 결과: 다이얼로그={msg!r} → '취소'(데이터안전, 절대 확인 X)", sc=4,
                  repro="1. 반출\n2. 기본반출정책 체크\n3. 경고 다이얼로그\n4. **취소**")
        page.close_edit_modal()   # 저장 안 함 — base 타입 보존

    # ══ 4f: 특수문자 rename (sc3d) ═════════════════════════════════
    def test_scenario4f_edit_special_char_rename(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4f: 특수문자 이름 rename ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc4f — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        sc_name = page.AUTO_NAME_PREFIX + "_e4f';!@#$%"
        page.open_modify_modal(self._BASE)
        page.fill(page.SEL_NAME, sc_name)
        msg = page.submit_and_message()
        page.navigate_to()
        saved = "저장" in msg and "오류" not in msg
        # 저장됐으면 base→sc_name 으로 rename 된 것 (in-place). base 복구 위해 다시 rename 백
        if saved and sc_name in page.get_policy_names():
            try:
                page.open_modify_modal(sc_name)
                page.fill(page.SEL_NAME, self._BASE)
                page.submit_and_message()
            except Exception:
                pass
        self._add("warn" if saved else "pass",
                  "sc4f — 특수문자 이름으로 rename 차단 여부",
                  f"입력: 이름=\"{sc_name}\"로 수정 / 결과: {msg!r} "
                  + ("[차단 없이 저장 — known issue 가능(ADD sc3d 와 동일)]" if saved else "[차단됨]"),
                  sc=4, highlight=page.page.locator(page.SEL_NAME),
                  repro=f"1. 수정\n2. 이름=\"{sc_name}\"\n3. '수정' → 저장/차단 확인")
        page._close_modal_if_open()

    # ══ 4g: 드라이브 템플릿 변경 (sc3e) ════════════════════════════
    def test_scenario4g_edit_drive_template_change(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4g: 드라이브 템플릿 변경 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4g — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        name2 = page.reselect_template(0, 1)   # 드라이브 2번째 행으로 변경
        row = page.drive_row_text()
        changed = bool(name2) and name2.split()[0] in row
        self._add("pass" if changed else "warn",
                  "sc4g — EDIT 드라이브 템플릿 재설정",
                  f"입력: 드라이브 '템플릿 선택' → 2번째('{name2}') / 결과: 드라이브 행={row!r}, 변경됨={changed} "
                  "(템플릿 1개뿐이면 변경 불가→warn)",
                  sc=4, highlight=page.page.locator(page.SEL_TEMPLATE_BTN).first,
                  repro="1. 수정\n2. 드라이브 '템플릿 선택' → 다른 행 → 확인\n3. 드라이브 행 갱신 확인")
        page.close_edit_modal()

    # ══ 4h: 제어스위트 picker + 검색 (sc3f) ════════════════════════
    def test_scenario4h_edit_suite_picker_search(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4h: 제어스위트 변경 + picker 검색 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4h — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        name2 = page.reselect_template(1, 1)   # 제어스위트 2번째 행
        txt = page.page.locator("div#addItemModal.in").inner_text()
        changed = bool(name2) and name2.split()[0] in txt
        self._add("pass" if changed else "warn",
                  "sc4h — EDIT 제어스위트 템플릿 재설정",
                  f"입력: 제어스위트 재선택('{name2}') / 결과: 변경됨={changed}", sc=4,
                  highlight=page.page.locator(page.SEL_TEMPLATE_BTN).nth(1),
                  repro="1. 수정\n2. 제어스위트 재선택\n3. 갱신 확인")
        # picker 검색 미동작 — ADD(sc3f)가 8진입점 통합 검출, EDIT 는 여기서 1회 대표 확인('수정에 한번').
        #   같은 공유 컴포넌트(selectCommonPolicyItemModal)라 EDIT 진입점도 동일 미동작 = '수정 컨텍스트' 확정용.
        res = page.picker_search_filters(1, "전사", tab="기본정책")
        if res["before"] == 0:
            self._add("skip", "sc4h — EDIT picker 검색 (빈 목록)", "입력: - / 결과: 0건", sc=4)
        else:
            self._add("warn" if not res["filtered"] else "pass",
                      "sc4h — EDIT picker 검색 미동작 (수정 컨텍스트 1회 확인, ADD sc3f 통합본과 동일 컴포넌트)",
                      f"입력: EDIT 제어스위트 picker '전사' 검색 / 결과: {res['before']}→{res['after']}건 "
                      + ("[결함: 미동작 — ADD sc3f(8진입점)와 동일 공유 컴포넌트, EDIT 에서도 재현]" if not res["filtered"] else "[필터 동작]"),
                      sc=4, highlight=page.page.locator(page.SEL_PICKER_SEARCH),
                      repro="1. 수정\n2. 제어스위트 picker 검색 '전사'\n3. 건수 변화 확인")
        page.close_picker()
        page.close_edit_modal()

    # ══ 4i: 프로세스 통제 gating + 허용/거부 (sc3g) ════════════════
    def test_scenario4i_edit_process_control(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4i: 프로세스 통제 gating + 허용/거부 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4i — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        off = page.field_state("isAllowProcessForceStop")
        self._add("pass" if off.get("disabled") else "warn",
                  "sc4i — EDIT 프로세스통제 OFF 시 '강제종료' 비활성",
                  f"입력: 프로세스통제 OFF(로드) / 결과: isAllowProcessForceStop disabled={off.get('disabled')}", sc=4,
                  repro="1. 수정\n2. '강제종료' disabled 확인")
        allow_nm = page.assign_process_template("허용")
        area = page.process_template_area_text()
        shown = ("허용 프로세스" in area) and ("할당해제" in area)
        self._add("pass" if shown else "fail",
                  "sc4i — EDIT 허용 프로세스 템플릿 등록 표시",
                  f"입력: 허용 템플릿('{allow_nm}') 할당 / 결과: 행={area!r}", sc=4,
                  repro="1. 수정\n2. 템플릿설정 → 허용/거부 [설정] → 허용\n3. '허용 프로세스 [할당해제]' 표시 확인")
        page.goto_modal_tab("기본정책")
        # 검증A: 프로세스통제 OFF(로드)인데 허용 템플릿 할당됨 = UX 결함 가능 (sc3g 미러)
        master_off = page.field_state("isAllowDenyProcessUse")
        assigned = bool(allow_nm)
        self._add("warn" if (assigned and master_off.get("checked") is False) else "pass",
                  "sc4i — 검증A: 프로세스통제 OFF인데 템플릿 할당 가능(EDIT)",
                  f"입력: 통제 OFF에서 허용 템플릿('{allow_nm}') 할당 / 결과: 할당됨={assigned}, master={master_off.get('checked')} "
                  + ("[미사용(OFF)인데 할당됨 — UX 결함 가능(낮음), ADD sc3g 동일]" if (assigned and master_off.get('checked') is False) else ""),
                  sc=4, repro="1. 통제 OFF\n2. 허용 할당\n3. OFF인데 할당되는지 확인")
        page.set_toggle("isAllowDenyProcessUse", True)
        f_allow = page.field_state("isAllowProcessForceStop")
        self._add("pass" if f_allow.get("disabled") is False else "warn",
                  "sc4i — 허용 템플릿 + master ON → '강제종료' 활성",
                  f"입력: 허용 할당 + 통제 ON / 결과: 강제종료 disabled={f_allow.get('disabled')} (기대 False)", sc=4,
                  repro="1. 허용 할당\n2. 프로세스통제 ON\n3. 강제종료 활성 확인")
        page.close_edit_modal()   # 저장 안 함

    # ══ 4j: 기타 토글 (실행차단/특수폴더/폴더동기화) (sc3h) ════════
    def test_scenario4j_edit_other_toggles(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4j: 기타 토글 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4j — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        for cid, label in [("isBlockExecuteProcess", "실행차단 프로세스"),
                           ("isManageFolder", "특수폴더"), ("isSyncFolder", "폴더 동기화")]:
            s0 = page.field_state(cid)
            page.set_toggle(cid, True)
            s1 = page.field_state(cid)
            self._add("pass" if (s1.get("checked") is True) else "fail",
                      f"sc4j — EDIT '{label} 사용' 토글 반응",
                      f"입력: '{label}' 클릭 / 결과: {s0.get('checked')}→{s1.get('checked')}", sc=4,
                      repro=f"1. 수정\n2. '{label} 사용' 클릭\n3. ON 확인")
            page.set_toggle(cid, False)
        # 검증A: 각 토글 OFF인데 템플릿설정 탭에서 해당 템플릿 할당 가능 (sc3h 미러)
        for cid, btn_idx, feat in [("isBlockExecuteProcess", 2, "실행차단 프로세스"),
                                   ("isManageFolder", 3, "특수폴더(바로가기)"),
                                   ("isSyncFolder", 5, "폴더동기화")]:
            nm = page.assign_template_setting(btn_idx)
            page.goto_modal_tab("기본정책")
            tog = page.field_state(cid)
            if not nm:
                self._add("skip", f"sc4j — 검증A: '{feat}' (할당 가능 템플릿 없음)",
                          "입력: - / 결과: picker 비어있음/실패", sc=4)
                continue
            self._add("warn" if tog.get("checked") is False else "pass",
                      f"sc4j — 검증A: '{feat}' OFF인데 템플릿 할당 가능(EDIT)",
                      f"입력: '{feat}' OFF에서 템플릿('{nm}') 할당 / 결과: 할당됨=True, 토글={tog.get('checked')} "
                      + ("[미사용(OFF)인데 할당됨 — ADD sc3h 동일]" if tog.get('checked') is False else ""),
                      sc=4, repro=f"1. '{feat}' OFF\n2. {feat} [설정] 할당\n3. OFF인데 할당되는지 확인")
        page.close_edit_modal()

    # ══ 4k: 파일감시 master gating (sc3i) ══════════════════════════
    def test_scenario4k_edit_filewatch_gating(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4k: 파일감시 master gating ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4k — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        subs = page.filewatch_sub_disabled()
        enabled_left = [k for k, v in subs.items() if v is not True]
        all_off = len(enabled_left) == 0
        self._add("pass" if all_off else "warn",
                  "sc4k — EDIT 파일감시 OFF 시 하위 전체 비활성",
                  "입력: 파일감시 OFF(로드) / 결과: " + ", ".join(f"{k}={v}" for k, v in subs.items())
                  + (" [전체 disabled 정상]" if all_off else f" [활성 잔존 {enabled_left}]"),
                  sc=4, repro="1. 수정\n2. 보관소/확장자/예외폴더/헤더 disabled 확인")
        # 파일감시 OFF 에서 확장자 [추가] 클릭 → 무반응 (sc3i 미러)
        before_ext = len(page.watch_extension_items())
        try:
            page.page.locator(page.SEL_WATCH_EXT_ADD).evaluate("el => el.click()")
            page.page.wait_for_timeout(150)
        except Exception:
            pass
        after_ext = len(page.watch_extension_items())
        self._add("pass" if after_ext == before_ext else "warn",
                  "sc4k — EDIT 파일감시 OFF 시 확장자 [추가] 클릭 무반응",
                  f"입력: 파일감시 OFF에서 확장자 [추가] / 결과: 리스트 {before_ext}→{after_ext} "
                  + ("(불변 정상)" if after_ext == before_ext else "[결함: OFF인데 추가됨]"),
                  sc=4, repro="1. 파일감시 OFF\n2. 확장자 [추가]\n3. 리스트 불변 확인")
        page.set_toggle("isWatchFile", True)
        sp_on = page.field_state("watchFileStorePath")
        self._add("pass" if sp_on.get("disabled") is False else "fail",
                  "sc4k — 파일감시 ON 시 '보관소 지정' 활성",
                  f"입력: 파일감시 ON / 결과: 보관소 disabled={sp_on.get('disabled')}", sc=4,
                  repro="1. 파일감시 ON\n2. 보관소 활성 확인")
        page.close_edit_modal()

    # ══ 4l: 보관소 데이터 손실 — EDIT 저장 시에도 재현되는지 (sc3j) ══
    def test_scenario4l_edit_watchpath_data_loss(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4l: 보관소 값 손실 (EDIT 저장) ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc4l — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        sel = "div#addItemModal.in input#watchFileStorePath"
        page.open_modify_modal(self._BASE)
        page.set_toggle("isWatchFile", True)
        page.fill(sel, "b" * 400)
        msg = page.submit_and_message()
        page._close_modal_if_open()   # ⚠️ 서버오류 시 EDIT 모달 잔류 → 닫아야 다음 open_modify 의 수정버튼이 안 가려짐(타임아웃 방지)
        saved_ok = "저장" in msg
        if saved_ok:
            # 저장 성공 경로 → 재오픈 값 손실 확인 (ADD sc3j 패턴)
            if self._BASE in page.get_policy_names():
                page.open_modify_modal(self._BASE)
                st = page.field_state("watchFileStorePath")
                saved_len = len(st.get("value") or "")
                empty = saved_len == 0
                self._add("fail" if empty else "pass",
                          ("sc4l — EDIT 저장 후 재오픈 시 보관소 값 유지" if empty
                           else "sc4l — EDIT 저장 후 재오픈 시 보관소 값 유지"),
                          f"입력: 400자 EDIT 저장 후 재오픈 / 결과: 저장된 길이={saved_len}자 (기대 400) "
                          + ("[결함: 저장 성공인데 값 비워짐 = 데이터 손실 (ADD sc3j 와 동일)]" if empty else ""),
                          sc=4, highlight=page.page.locator(sel),
                          repro="1. 재수정\n2. 보관소 값/길이 확인")
                page.close_edit_modal()
        else:
            # 서버오류 경로 — ADD(sc3j: '저장 하였습니다'+silent 손실)와 다른 EDIT 거동
            self._add("warn",
                      "sc4l — EDIT 보관소 400자 저장 시 거동 (ADD↔EDIT 차이)",
                      f"입력: 보관소 'b'×400자 EDIT 수정 저장 / 결과: {msg!r} "
                      "[ADD(sc3j)는 '저장 하였습니다'+값 silent 손실인데, EDIT 는 '서버에서 오류' — "
                      "동일 길이값을 ADD/EDIT 가 다르게 처리(둘 다 보관소 길이 처리 결함). 전 필드 누락 전수는 sc5 lifecycle 에서.]",
                      sc=4, highlight=page.page.locator(sel),
                      repro="1. 수정\n2. 파일감시 ON\n3. 보관소 b×400\n4. '수정' → '서버에서 오류' 확인")

    # ══ 4m: 확장자 입력 케이스 (sc3k 핵심) ═════════════════════════
    def test_scenario4m_edit_extension_cases(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4m: 확장자 입력 케이스 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4m — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        page.set_toggle("isWatchFile", True)
        it, _ = page.add_extension_msg("exe")
        self._add("pass" if "exe" in it else "fail", "sc4m — ① 확장자 단일 추가('exe')",
                  f"입력: 'exe'+[추가] / 결과: {it}", sc=4, repro="1. 파일감시 ON\n2. 'exe'+[추가]")
        it, _ = page.add_extension_msg("dll;txt")
        self._add("pass" if ("dll" in it and "txt" in it) else "fail", "sc4m — ② ';' 다중",
                  f"입력: 'dll;txt' / 결과: {it}", sc=4, repro="1. 'dll;txt'+[추가]\n2. 분리 확인")
        it, msg = page.add_extension_msg("exe")
        self._add("pass" if ("이미" in msg or "동일" in msg) else "fail", "sc4m — ③ 중복 차단",
                  f"입력: 'exe' 재추가 / 결과: {msg!r}", sc=4, repro="1. 'exe' 재추가\n2. 중복 경고")
        before = len(page.watch_extension_items())
        page.delete_first_watch_extension()
        after = len(page.watch_extension_items())
        self._add("pass" if after == before - 1 else "fail", "sc4m — ④ 확장자 삭제(x)",
                  f"입력: 첫 항목 x / 결과: {before}→{after}", sc=4, repro="1. 첫 항목 x\n2. 1 감소")
        page.close_edit_modal()

    # ══ 4n: 하위 체크박스 OFF gating (sc3l) ════════════════════════
    def test_scenario4n_edit_subtoggle_gating(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4n: 하위 체크박스 OFF gating ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4n — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        page.set_toggle("isWatchFile", True)
        page.set_toggle("isWatchFileExtention", False)
        cb = page.field_state("isWatchFileExtention")
        page.add_watch_extension("exe")
        items = page.watch_extension_items()
        added = "exe" in items
        self._add("warn" if added else "pass",
                  "sc4n — '감시할 확장자' OFF 시 입력 차단 여부",
                  f"입력: 확장자 체크박스 OFF(checked={cb.get('checked')})에서 'exe' 추가 / 결과: {items} "
                  + ("[결함: OFF인데 추가됨 — gating 부재(ADD sc3l 와 동일)]" if added else "[정상 차단]"),
                  sc=4, highlight=page.page.locator(page.SEL_WATCH_EXT_LIST),
                  repro="1. 파일감시 ON\n2. '감시할 확장자' OFF\n3. 'exe'+[추가]\n4. 차단 여부")
        # ② 감시 예외 폴더 체크박스 OFF → [특수폴더]/[추가] 버튼 비활성 여부 (sc3l ② 미러)
        page.set_toggle("isWatchFolder", False)
        wfo = page.field_state("isWatchFolder")
        sp = page.page.locator(page.SEL_WATCH_FOLDER_SPECIAL).first
        ad = page.page.locator(page.SEL_WATCH_FOLDER_ADD).first
        sp_dis = sp.is_disabled() if sp.count() else None
        ad_dis = ad.is_disabled() if ad.count() else None
        blocked = bool(sp_dis) and bool(ad_dis)
        self._add("pass" if blocked else "warn",
                  "sc4n — ② '감시 예외 폴더' OFF 시 버튼 비활성 여부",
                  f"입력: 예외폴더 체크박스 OFF(checked={wfo.get('checked')}) / 결과: [특수폴더] disabled={sp_dis}, [추가] disabled={ad_dis} "
                  + ("[정상 차단]" if blocked else "[결함: OFF인데 버튼 활성 — gating 부재(ADD sc3l ② 동일)]"),
                  sc=4, highlight=page.page.locator(page.SEL_WATCH_FOLDER_SPECIAL),
                  repro="1. 파일감시 ON\n2. '감시 예외 폴더' OFF\n3. [특수폴더]/[추가] 비활성 여부 확인")
        page.close_edit_modal()

    # ══ 4o: 헤더 체크 토글 (sc3m) ══════════════════════════════════
    def test_scenario4o_edit_header_check(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4o: 헤더 체크 토글 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4o — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        page.set_toggle("isWatchFile", True)
        s0 = page.field_state("isWatchFileHeader")
        page.set_toggle("isWatchFileHeader", True)
        s1 = page.field_state("isWatchFileHeader")
        self._add("pass" if s1.get("checked") is True else "fail",
                  "sc4o — EDIT 헤더 체크 토글 반응",
                  f"입력: 파일감시 ON 후 헤더 체크 클릭 / 결과: {s0.get('checked')}→{s1.get('checked')}", sc=4,
                  repro="1. 파일감시 ON\n2. '헤더 체크 기능 사용' 클릭\n3. ON 확인")
        page.close_edit_modal()

    # ══ 4p: 감시 예외 폴더 (sc3n) ══════════════════════════════════
    def test_scenario4p_edit_watch_folder(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4p: 감시 예외 폴더 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4p — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        # 파일감시 OFF(로드) 시 예외폴더 체크박스 비활성 (sc3n 미러)
        off = page.field_state("isWatchFolder")
        self._add("pass" if off.get("disabled") else "warn",
                  "sc4p — EDIT 파일감시 OFF 시 '감시 예외 폴더' 비활성",
                  f"입력: 파일감시 OFF(로드) / 결과: isWatchFolder disabled={off.get('disabled')} (기대 True)", sc=4,
                  repro="1. 수정\n2. 예외폴더 체크박스 disabled 확인")
        page.set_toggle("isWatchFile", True)
        page.set_toggle("isWatchFolder", True)
        items, _ = page.add_watch_folder_reserved("DESKTOP")
        added = any("DESKTOP" in it for it in items)
        self._add("pass" if added else "fail",
                  "sc4p — EDIT 예외폴더 예약어([/DESKTOP/]) 추가",
                  f"입력: [특수폴더]→'[/DESKTOP/]'→확인→[추가] / 결과: {items}", sc=4,
                  highlight=page.page.locator(page.SEL_WATCH_FOLDER_LIST),
                  repro="1. 파일감시+예외폴더 ON\n2. [특수폴더]→DESKTOP→확인→[추가]\n3. 리스트 반영")
        page.close_edit_modal()

    # ══ 4q: 프린트 설정 (sc3o) ═════════════════════════════════════
    def test_scenario4q_edit_print_settings(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4q: 프린트 설정 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4q — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        # 프린트 OFF(로드) 시 라디오 클릭 무반응 (sc3o 미러)
        before_v = page.print_radio_value()
        try:
            page.page.locator("div#addItemModal.in input[name='isPrint'][value='0']").evaluate("el => el.click()")
            page.page.wait_for_timeout(120)
        except Exception:
            pass
        after_v = page.print_radio_value()
        self._add("pass" if before_v == after_v else "warn",
                  "sc4q — EDIT 프린트 OFF 시 라디오 클릭 무반응",
                  f"입력: 프린트 OFF에서 '차단'(0) 클릭 / 결과: 선택 {before_v!r}→{after_v!r} "
                  + ("(불변 정상)" if before_v == after_v else "[결함: OFF인데 변경됨]"),
                  sc=4, repro="1. 프린트 OFF\n2. '차단' 라디오 클릭\n3. 불변 확인")
        page.set_toggle("isPrintUse", True)
        dv = page.print_radio_value()
        self._add("pass" if dv == "1" else "warn", "sc4q — 프린트 ON default '허용'(1)",
                  f"입력: 프린트 ON / 결과: value={dv!r}", sc=4, repro="1. 프린트 ON\n2. 기본 '허용' 확인")
        page.set_print_radio("0")
        self._add("pass" if page.print_radio_value() == "0" else "fail", "sc4q — 라디오 '차단'(0) 전환",
                  f"입력: '차단' 클릭 / 결과: {page.print_radio_value()!r}", sc=4, repro="1. '차단' 클릭\n2. 선택 확인")
        page.close_edit_modal()

    # ══ 4r: 메뉴 토글 (sc3p) ═══════════════════════════════════════
    def test_scenario4r_edit_menu_toggles(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4r: 메뉴 토글 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4r — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        for cid, label in [("isShowAgentShutdownMenu", "에이전트 종료 메뉴"),
                           ("isShowEmergencyCodeMenu", "긴급 허용 코드 메뉴")]:
            page.set_toggle(cid, True)
            s1 = page.field_state(cid)
            self._add("pass" if s1.get("checked") is True else "fail",
                      f"sc4r — EDIT '{label} 표시' 토글 반응",
                      f"입력: '{label}' 클릭 / 결과: checked={s1.get('checked')}", sc=4,
                      repro=f"1. '{label} 표시' 클릭\n2. ON 확인")
            page.set_toggle(cid, False)
        page.close_edit_modal()

    # ══ 4s: 오프라인 차단 대기시간 (sc3q) ══════════════════════════
    def test_scenario4s_edit_offline_blocktime(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4s: 오프라인 차단 대기시간 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4s — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        page.set_toggle("isOfflineUse", True)
        v1, _ = page.type_block_time("1.5")
        self._add("pass" if v1 == "1.5" else "warn", "sc4s — 소수점 입력 허용",
                  f"입력: '1.5' / 결과: {v1!r}", sc=4, repro="1. 오프라인 ON\n2. '1.5'\n3. 값 유지")
        v2, _ = page.type_block_time("abc")
        self._add("pass" if v2 in ("0", "") else "warn", "sc4s — 문자 입력 거부",
                  f"입력: 'abc' / 결과: {v2!r}", sc=4, repro="1. 'abc'\n2. 0/빈값 거부")
        page.close_edit_modal()

    # ══ 4t: 커스텀 옵션값 (sc3r) ═══════════════════════════════════
    def test_scenario4t_edit_custom_option(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4t: 커스텀 옵션값 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4t — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        page.fill(self._CUST_SEL, "edit_custom_456")
        val = page.page.locator(self._CUST_SEL).first.input_value()
        self._add("pass" if val == "edit_custom_456" else "fail",
                  "sc4t — EDIT 커스텀 옵션값 입력",
                  f"입력: 커스텀='edit_custom_456' / 결과: {val!r}", sc=4,
                  repro="1. 수정\n2. 커스텀 옵션값 입력\n3. 값 유지 확인")
        page.close_edit_modal()

    # ══ 4u: 템플릿 할당해제 (sc3u) ═════════════════════════════════
    def test_scenario4u_edit_template_unassign(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4u: 템플릿 할당해제 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4u — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        nm = page.assign_process_template("허용")
        area1 = page.process_template_area_text()
        if not (bool(nm) and "할당해제" in area1):
            self._add("skip", "sc4u — 할당해제 (허용 템플릿 할당 실패)", f"입력: - / 결과: {nm!r}", sc=4)
            page.close_edit_modal(); return
        released = page.unassign_template_setting()
        area2 = page.process_template_area_text()
        gone = released and ("할당해제" not in area2)
        self._add("pass" if gone else "fail",
                  "sc4u — EDIT 허용 프로세스 [할당해제] → '없음' 복귀",
                  f"입력: 허용('{nm}') 할당 후 [할당해제] / 결과: 해제전={area1!r} → 해제후={area2!r}", sc=4,
                  repro="1. 수정\n2. 허용 할당 → [할당해제]\n3. '없음' 복귀 확인")
        page.close_edit_modal()

    # ══ 4v: 비-허용거부 템플릿 할당+할당해제 (sc3v) ════════════════
    def test_scenario4v_edit_other_templates(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4v: 비-허용거부 템플릿 할당+할당해제 ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._open_edit(page):
            self._add("skip", "sc4v — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        for btn_idx, feat in [(1, "예외처리 프로세스"), (2, "실행차단 프로세스"),
                              (4, "레지스트리 변경"), (5, "폴더동기화")]:
            nm = page.assign_template_setting(btn_idx)
            if not nm:
                self._add("skip", f"sc4v — '{feat}' (할당 가능 템플릿 없음)",
                          f"입력: {feat} [설정] / 결과: picker 비어있음/실패", sc=4)
                continue
            txt = page.template_tab_text()
            shown = nm.split()[0] in txt
            released = page.unassign_template_setting()
            txt2 = page.template_tab_text()
            gone = released and (nm.split()[0] not in txt2)
            self._add("pass" if (shown and gone) else "fail",
                      f"sc4v — EDIT '{feat}' 할당+할당해제",
                      f"입력: {feat} 할당('{nm}')→할당해제 / 결과: 할당표시={shown}, 해제={gone}", sc=4,
                      repro=f"1. 수정\n2. {feat} [설정]→할당\n3. [할당해제]\n4. 표시+제거 확인")
        page.close_edit_modal()

    # ══ 4w: 이름 변경 = in-place rename (마지막 — base 소진) ════════
    def test_scenario4w_edit_rename_update(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 4w: 이름 변경 = in-place rename ━━━")
        page = self._new_page(logged_in_page, settings)
        if not self._ensure_policy(page, self._BASE):
            self._add("skip", "sc4w — 편집 대상 없음", "입력: - / 결과: base 미존재", sc=4); return
        ren = "[AUTO]_szp_sc4ren"
        before = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        if ren in before:
            self._add("skip", "sc4w — rename 대상명 이미 존재",
                      f"입력: - / 결과: '{ren}' 잔여 — 충돌 회피(sc1 정리 후 재실행)", sc=4)
            return
        page.open_modify_modal(self._BASE)
        page.fill(page.SEL_NAME, ren)
        msg = page.submit_and_message()
        page.navigate_to()
        after = [n for n in page.get_policy_names() if n.startswith("[AUTO]")]
        in_place = ("저장" in msg) and (self._BASE not in after) and (ren in after) and (len(after) == len(before))
        self._add("pass" if in_place else "fail",
                  "sc4w — 이름 변경 수정 = in-place rename(신규생성 아님)",
                  f"입력: '{self._BASE}'→'{ren}' 수정 저장({msg!r}) / "
                  f"결과: 원본사라짐={self._BASE not in after}, 새이름존재={ren in after}, [AUTO] {len(before)}→{len(after)}건 "
                  + ("(원본 갱신 + 개수 불변 = 정상 rename)" if in_place else "[결함: 신규 레코드 또는 원본 잔존]"),
                  sc=4, repro=f"1. 수정\n2. 이름 '{ren}'으로\n3. '수정'\n4. 원본 사라지고 새 이름만 + 개수 불변")

    # ══ 4x: 입력 필드 overflow(3000자) EDIT 거동 분류 (sc3x EDIT 미러) ══
    def test_scenario4x_field_overflow(self, logged_in_page, settings):
        """EDIT 에서 텍스트 필드 3000자 → 서버오류/silent손실/정상유지 전수 분류 (sc3x 의 EDIT 판).

        ADD(sc3x)와 EDIT 거동이 다를 수 있어(예: watchpath ADD=손실 / EDIT=서버오류, sc4l) 동일 sweep 을 EDIT 에서도.
        필드별 전용 [AUTO] 정책을 만들어 수정모달에서 3000자 입력 후 저장→분류. cleanup 안 함."""
        print("\n━━ [시큐어존 정책] 시나리오 4x: 입력 필드 overflow(3000자) EDIT 분류 ━━━")
        page = self._new_page(logged_in_page, settings)
        BIG = "X" * 3000
        fields = [
            ("감시파일 보관소", "div#addItemModal.in input#watchFileStorePath", "isWatchFile", "watchFileStorePath"),
            ("프린트 허용 브랜드", "div#addItemModal.in textarea#allowPrintModel", "isPrintUse", "allowPrintModel"),
            ("프린트 제외 포트", "div#addItemModal.in textarea#exceptPrintPort", "isPrintUse", "exceptPrintPort"),
            ("커스텀 옵션값", "div#addItemModal.in input#customOptionText", None, "customOptionText"),
        ]
        for label, sel, toggle, fid in fields:
            name = f"{page.AUTO_NAME_PREFIX}_ovfe_{fid[:6]}"
            if not self._ensure_policy(page, name):
                self._add("skip", f"sc4x — '{label}' (대상 정책 생성 실패)", "입력: - / 결과: 생성 안 됨", sc=4)
                continue
            page.open_modify_modal(name)
            if toggle:
                page.set_toggle(toggle, True)
            raw_len = page.set_value_raw(sel, BIG)
            msg = page.submit_and_message()
            if ("서버" in msg) or ("오류" in msg):
                self._add("warn", f"sc4x — EDIT '{label}' 3000자 → 서버오류(저장 거부)",
                          f"입력: {label} {raw_len}자 EDIT 저장 / 결과: {msg!r} [클라 길이 가드 없이 서버 거부 — ungraceful]",
                          sc=4, highlight=page.page.locator(sel),
                          repro=f"1. 수정\n2. {label} 3000자\n3. '수정' → '서버에서 오류' 확인")
                page._close_modal_if_open(); continue
            if "저장" not in msg:
                self._add("warn", f"sc4x — EDIT '{label}' 3000자 → 기타 메시지",
                          f"입력: {label} {raw_len}자 / 결과: {msg!r}", sc=4)
                page._close_modal_if_open(); continue
            # ⚠️ _add 는 모달 '열린 채' 호출(스크린샷이 빈/유지 필드를 잡도록), 그 뒤 close.
            if name not in page.get_policy_names():
                self._add("warn", f"sc4x — EDIT '{label}' 3000자 저장 후 정책 미존재", f"입력: {label} {raw_len}자 / 결과: {msg!r}", sc=4)
                continue
            page.open_modify_modal(name)
            persisted = len(page.field_state(fid).get("value") or "")
            if persisted == 0:
                self._add("fail", f"sc4x — EDIT '{label}' 3000자 저장 성공인데 값 손실",
                          f"입력: {label} {raw_len}자 EDIT 저장→재오픈 / 결과: {msg!r} + 저장값 0자 [결함: silent 데이터 손실]",
                          sc=4, highlight=page.page.locator(sel),
                          repro=f"1. {label} 3000자 EDIT 저장\n2. 재오픈 → 값 0자 확인")
            else:
                self._add("pass", f"sc4x — EDIT '{label}' 3000자 저장+유지(정상)",
                          f"입력: {label} {raw_len}자 EDIT 저장→재오픈 / 결과: 저장값 {persisted}자 유지",
                          sc=4, highlight=page.page.locator(sel),
                          repro=f"1. {label} 3000자 EDIT 저장\n2. 재오픈 → 값 유지 확인")
            page.close_edit_modal()
