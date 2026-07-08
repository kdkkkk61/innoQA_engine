"""시큐어존 템플릿(프로세스) — 시나리오 3: 동작 (원자 단위 재작성 — 2026-07-08).

★재작성 원칙(13:03 run 9 fail 교훈): 한 번에 다 짓지 않는다. 실행 확인된 흐름만 남기고
단계별로 확장 — 이번 단계는 **1단계 모달만 쓰는 검증**(L2/L3 미진입 = 검증된 안전 구간).
L2/L3 등록 흐름(3c~)은 크롬 실측(picker=checkbox·L3 자동닫힘·카운트 갱신) 반영 후 다음 단계.

sc3 = 순수 '동작' 검증 (표준 + 제어스위트 아날로그 대조). 등록은 picker 첫 행 선택 —
제어스위트 sc3 도 select_first_and_confirm(첫 행). ★seed 소비·연계는 sc3 아님 = sc6 책임
(운용 프로세스/태그 sc6 산출물 [AUTO_<date>]_cm_* 소비하여 chain 구성). sc3 에서 끌어오지 않는다.

sc3a — 타입별 생성 4종 전수 → 리스트 등장 + 타입 컬럼 표시 (radio 반영 검증 포함)
sc3b — 동명 중복 스코프. ★핵심 = 같은 타입 내 동명 차단 여부(부여가 타입별 → 같은 타입 동명 혼란).
       부수 = 다른 타입 동명 공존(타입 스코프 — 정상이나 경고 가치).
[L2/L3 등록 구간 — 크롬 실측(13:14/14:03) 반영: picker=checkbox plain click·L3 자동닫힘·카운트 갱신]
sc3c 등록(단일+다중) / sc3d 인라인 옵션 토글(재시작) / sc3e 태그 등록 / sc3f 제거(개별+일괄)
sc3g 다중 등록 중복 처리(부분=겹치는 것만 생략 / 전체=전부 생략)
[요소별(필드) — 표준상 clamp·특수문자·오버플로는 sc3(특수폴더 3i/3l/3s/3t 관례 대조)]
sc3h templateName 직접입력(clamp 60→30 / 특수문자 생성) / sc3i L3 설명(특수문자 / 장문 수용)
※ sc2=속성(maxlength 존재·초기값·별표), sc3=실제 입력 동작. 날짜본 seed 연계는 sc6.
  (요소 테스트를 sc2 에 잘못 뒀던 것 → sc3 로 정렬, 사용자 지적 2026-07-08)
"""
import time

from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario3Action(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 3: 동작 (1단계 구간)."""

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
            self._ckpt()

            def _create(name=name, ttype=ttype):
                page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
                if name in page.get_template_names():
                    page.delete_template(name)
                    page.navigate_to()
                page.create_template(name, ttype)
                page.navigate_to()
            self._act(f"'{name}' 생성(타입={ko})", _create)
            created = name in page.get_template_names()
            row_type = page.row_type_text(name)
            self._add("pass" if (created and ko in row_type) else "fail",
                      f"sc3a — {ko} 생성 → 리스트 등장 + 타입 컬럼",
                      f"입력: 이름+{ko} 저장 / 결과: 생성={created}, 타입 표시={row_type!r}", sc=3,
                      repro=f"1. 템플릿 추가\n2. 이름+{ko} 선택\n3. 확인\n4. 리스트 타입 컬럼 확인")

    # ── sc3b: 동명 중복 스코프 (같은 타입 vs 다른 타입) ─────────────
    def test_scenario3b_duplicate_scope(self, logged_in_page, settings):
        """★핵심=같은 타입 동명 차단(부여가 타입별). 판정 순간(차단 알림/공존 목록)을
        빨간 표시와 함께 캡처 — pass 여도 첨부(차단 증거를 눈으로 확인)."""
        print("\n━━ [프로세스] sc3b: 동명 중복 스코프 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.navigate_to_clean()
        while self._DUP in page.get_template_names():
            page.delete_template(self._DUP)
            page.navigate_to()
        page.create_template(self._DUP, "ALLOW_PROCESS")
        page.navigate_to()

        NAME = f"{page.SEL_MODAL} {page.SEL_NAME}"

        # ① 같은 타입 동명 재생성 → 차단 알림 순간 캡처(빨간 표시=이름 필드)
        page.open_add_modal()
        page.fill(NAME, self._DUP)
        f1 = self._shot("dup_same_input",
                        highlight=page.page.locator(NAME).first,
                        caption="1. 같은 타입(허용)에 동일 이름 입력")
        msg_same = page.submit_and_wait_alert()
        f2 = self._shot("dup_same_alert",
                        caption=f"2. 저장 시도 → 차단 알림: {msg_same!r}")
        page.dismiss_alert()
        page._close_modal_if_open()
        blocked_same = "이미 등록" in msg_same
        self._add("pass" if blocked_same else "warn",
                  "sc3b — ★같은 타입 동일 이름 차단 (핵심 검증)",
                  f"입력: 허용 타입 동명 재생성 / 결과: 경고={msg_same!r} "
                  + ("(차단 정상)" if blocked_same else
                     "[차단 안 됨 — 같은 타입 내 동명 허용, 템플릿 부여 시 구분 불가]"), sc=3,
                  screenshots=[f1, f2],
                  merge_key=(None if blocked_same
                             else "szproc_dup::same_type::warn::no_dup_check"),
                  repro="1. 허용 타입 템플릿 생성\n2. 같은 이름+같은 타입 재생성\n"
                        "3. '이미 등록된 이름' 차단되어야 — 부여 UI 가 타입별이라 동명이면 혼란")

        # ② 다른 타입 동명 생성 → 공존 여부 (13:03 실측: '저장 하였습니다' 공존)
        page.navigate_to()
        page.open_add_modal()
        page.fill(NAME, self._DUP)
        page.select_type("DENY_PROCESS")
        msg_diff = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        page.search(self._DUP)   # 공존 2행이 목록에 보이도록 필터
        count = page.get_template_names().count(self._DUP)
        coexist = count >= 2
        f3 = self._shot("dup_cross_list",
                        highlight=page.page.locator("table tbody").first,
                        caption=f"다른 타입 동명 생성 후 목록 — '{self._DUP}' {count}개 공존")
        self._add("warn" if coexist else "pass",
                  "sc3b — 다른 타입 동일 이름 공존 (정상 범주 · 경고 가치)",
                  f"입력: 거부 타입 동명 생성 / 결과: 경고={msg_diff!r}, 동명 {count}개 "
                  + ("[타입 다르면 공존 허용 — 이름 중복 검사가 타입 스코프. 동작상 정상이나 "
                     "부여 시 타입별 목록에 동명이 나올 수 있어 경고 가치]"
                     if coexist else "(전역 차단 — 공존 안 됨)"), sc=3,
                  screenshots=[f3],
                  merge_key=("szproc_dup::cross_type::warn::type_scoped_name_check"
                             if coexist else None),
                  repro="1. 허용 타입으로 만든 이름 그대로\n2. 거부 타입 선택 후 저장\n"
                        "3. 동명 2개 공존(타입 스코프 — 정상이나 경고 가치)")
        page.search("")   # 검색 리셋
        # 정리 — 동명 잔존은 후속 이름 매칭을 오염시키므로 즉시 제거(재실행 가드 성격)
        while self._DUP in page.get_template_names():
            page.delete_template(self._DUP)
            page.navigate_to()


    # ── sc3c: 개별 프로세스 등록 — 단일 + 다중 (checkbox picker) ─────
    def test_scenario3c_register_single_multi(self, logged_in_page, settings):
        """★등록 동작. picker 는 checkbox(라디오 아님) → 다중 선택 한 번에 N개 등록 가능(실측).
        단일 1건 + 다중 3건 → L2 반영 + '등록된 프로세스' 카운트."""
        print("\n━━ [프로세스] sc3c: 개별 프로세스 등록(단일+다중) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3c"
        page.navigate_to_clean()
        page.ensure_template(tpl)

        # 단일 등록
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        picked1 = page.l3_register("ALLOW_PROCESS", count=1)
        msg1 = page.l3_add_message("ALLOW_PROCESS")
        cnt1 = page.l2_item_count()
        self._add("pass" if (len(picked1) == 1 and msg1 == "" and cnt1 == 1) else "fail",
                  "sc3c — 단일 프로세스 등록 → L2 1건",
                  f"입력: {picked1} 선택+추가 / 결과: 경고={msg1!r}, L2={cnt1}건", sc=3,
                  repro="1. L2 + → picker 1개 체크\n2. 확인 → 추가\n3. L2 1행")

        # 다중 등록 (앞에서부터 3개 — 이미 등록된 것과 겹치면 제품이 스킵/중복처리하는지도 관찰)
        page.open_l3_add("ALLOW_PROCESS")
        picked3 = page.l3_register("ALLOW_PROCESS", count=3)
        shown = page.l3_selected_name("ALLOW_PROCESS")
        f1 = self._shot("multi_selected",
                        highlight=page.l3_scope("ALLOW_PROCESS").locator("span#szProcessName").first,
                        caption=f"1. picker 다중 선택 → L3 표시: {shown!r}")
        msg3 = page.l3_add_message("ALLOW_PROCESS")
        cnt_after = page.l2_item_count()
        f2 = self._shot("multi_l2",
                        highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody").first,
                        caption=f"2. 추가 → L2 총 {cnt_after}건 (안내={msg3!r})")
        # ★중복 생략 안내('이미 등록되어 생략')는 정상 — 이미 등록된 것 재선택 시 스킵. 카운트로만 판정.
        skip_dup = ("생략" in msg3) or ("이미 등록" in msg3)
        multi_ok = (len(picked3) == 3) and ("외" in shown) and (cnt_after >= 2)
        self._add("pass" if multi_ok else "fail",
                  "sc3c — 다중 프로세스 등록(한 번에 N개) → L2 반영",
                  f"입력: {len(picked3)}개 선택({shown!r}) + 추가 / 결과: L2 총 {cnt_after}건"
                  + (f" (중복 생략 안내='{msg3}' — 정상 동작)" if skip_dup else f" (안내={msg3!r})"), sc=3,
                  screenshots=[f1, f2],
                  repro="1. L2 + → picker 여러 개 체크\n2. 확인 → 'N개 외' 표시\n"
                        "3. 추가 → L2 다건 등록(이미 등록분 있으면 생략 안내=정상)")
        page.l2_bulk_remove()   # 정리(전체 제거)
        page.close_l2_modal()

    # ── sc3d: 인라인 옵션 토글 (허용=재시작) ────────────────────────
    def test_scenario3d_inline_option_toggle(self, logged_in_page, settings):
        """★등록 행의 옵션 버튼(허용=재시작)을 L2 목록에서 인라인 토글 → 즉시 반영(실측:
        편집 재오픈 시 restart 반영). 등록만 하고 옵션 안 건드리던 허술함 보강."""
        print("\n━━ [프로세스] sc3d: 인라인 옵션 토글(허용 재시작) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3d"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=1)
        page.l3_add_message("ALLOW_PROCESS")   # 등록(재시작 기본 off)

        before = page.l2_option_on(0)
        after = page.l2_toggle_option(0)
        f1 = self._shot("opt_toggled",
                        highlight=page.l2_rows()[0].locator("td").nth(3).locator("button").first,
                        caption=f"옵션(재시작) 토글: {before} → {after}")
        # 편집 재오픈으로 실제 반영 확인
        page.l2_open_item_edit(0)
        restart_loaded = page.l3_scope("ALLOW_PROCESS").locator("input#isProcessRestart").first.is_checked()
        page.close_l3_modal("ALLOW_PROCESS")
        ok = (before != after) and (restart_loaded == after)
        self._add("pass" if ok else "warn",
                  "sc3d — L2 인라인 옵션(재시작) 토글 → 편집 로드값 반영",
                  f"입력: 옵션 버튼 클릭 / 결과: 표시 {before}→{after}, 편집 로드 restart={restart_loaded}", sc=3,
                  screenshots=[f1],
                  repro="1. 프로세스 등록\n2. L2 행 옵션 버튼 클릭(재시작 토글)\n3. 이름 링크 편집 → restart 반영 확인")
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
                  repro="1. L2 태그 탭 → + → L3\n2. 태그 선택(체크)\n3. 추가 → 태그 탭 반영")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3f: 제거 — 개별 1건 + 헤더 전체선택 일괄 ──────────────────
    def test_scenario3f_remove_single_bulk(self, logged_in_page, settings):
        """등록 후 제거 2방식: 개별 행 체크 제거 / 헤더 전체선택 일괄 제거(실측 확인 '삭제 하시겠습니까')."""
        print("\n━━ [프로세스] sc3f: 제거(개별 + 일괄) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3f"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=3)   # 3건 등록
        page.l3_add_message("ALLOW_PROCESS")
        start = page.l2_item_count()

        # 개별 제거 1건
        msg1 = page.l2_remove_item(0)
        mid = page.l2_item_count()
        self._add("pass" if ("삭제 하시겠습니까" in msg1 and mid == start - 1) else "fail",
                  "sc3f — 개별 행 제거 → -1",
                  f"입력: 1행 체크+제거 / 결과: 확인={msg1!r}, {start}→{mid}건", sc=3,
                  repro="1. 등록 3건\n2. 1행 체크 + - 버튼\n3. 삭제 확인 → 1건 감소")

        # 헤더 전체선택 일괄 제거
        msg2 = page.l2_bulk_remove()
        end = page.l2_item_count()
        self._add("pass" if end == 0 else "fail",
                  "sc3f — 헤더 전체선택 → 일괄 제거 → 0건",
                  f"입력: 전체선택 + 제거 / 결과: 확인={msg2!r}, {mid}→{end}건", sc=3,
                  repro="1. 헤더 체크(전체선택)\n2. - 버튼\n3. 전부 제거")
        page.close_l2_modal()

    # ── sc3g: 다중 등록 중복 처리 — 부분 중복(겹치는 것만 생략) / 전체 중복 ──
    def test_scenario3g_multi_dup_handling(self, logged_in_page, settings):
        """★실측(2026-07-08): 이미 A 등록된 상태에서 A+B+C 다중 선택 추가 →
        '<A>은 이미 등록되어 있어 생략' + 최종 3건(A유지 + B,C 신규). = 겹치는 것만 빠지고 나머진 등록.
        전체 겹침(A,B 재선택)은 전부 생략 → 카운트 불변. 대량 등록 시 중복 처리 정확성 검증."""
        print("\n━━ [프로세스] sc3g: 다중 등록 중복 처리(부분/전체) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3g"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)

        # 기준: A(첫 행) 1건 등록
        page.open_l3_add("ALLOW_PROCESS")
        a = page.l3_register("ALLOW_PROCESS", count=1)
        page.l3_add_message("ALLOW_PROCESS")
        base = page.l2_item_count()

        # 부분 중복: A+B+C(첫 3행, A 포함) 선택 → 겹치는 A만 생략, B·C 등록
        page.open_l3_add("ALLOW_PROCESS")
        picked3 = page.l3_register("ALLOW_PROCESS", count=3)
        msg = page.l3_add_message("ALLOW_PROCESS")
        page.close_l3_modal("ALLOW_PROCESS")   # 커밋 성공 시 자동닫힘 — 방어적(L3만, L2 유지)
        partial = page.l2_item_count()
        f1 = self._shot("partial_dup",
                        highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody").first,
                        caption=f"부분 중복: A+2개 선택 → 최종 {partial}건 (안내={msg!r})")
        # A 하나만 생략(1건 유지)되고 나머지 2 신규 → base(1) → 3
        skip_only_dup = (a and a[0].split()[0] in msg) and (partial == base + 2)
        self._add("pass" if skip_only_dup else "warn",
                  "sc3g — 부분 중복 다중 등록: 겹치는 것만 생략, 나머지 등록",
                  f"입력: 기존 {base}건 + 겹침 포함 3개 선택 / 결과: 안내={msg!r}, 최종 {partial}건 "
                  + ("(겹치는 1건만 생략, 2건 신규 — 정상)" if skip_only_dup
                     else "[예상(base+2)과 다름 — 동작 확인 필요]"), sc=3,
                  screenshots=[f1],
                  repro="1. A 1건 등록\n2. A+B+C 다중 선택 후 추가\n3. A만 '생략' 안내, B·C 등록(전부 거부 아님)")

        # 전체 중복: 이미 등록된 첫 2건(A,B) 재선택 → 전부 생략, 카운트 불변
        page.open_l3_add("ALLOW_PROCESS")
        page.l3_register("ALLOW_PROCESS", count=2)
        msg2 = page.l3_add_message("ALLOW_PROCESS")
        page.close_l3_modal("ALLOW_PROCESS")   # 커밋 성공 시 자동닫힘 — 방어적(L3만, L2 유지)
        alldup = page.l2_item_count()
        self._add("pass" if (("생략" in msg2 or "이미 등록" in msg2) and alldup == partial) else "warn",
                  "sc3g — 전체 중복 다중 등록: 전부 생략, 카운트 불변",
                  f"입력: 이미 등록된 2건 재선택 / 결과: 안내={msg2!r}, {partial}→{alldup}건 "
                  + ("(전부 생략 — 정상)" if alldup == partial else "[카운트 변동 — 확인 필요]"), sc=3,
                  repro="1. 등록된 것만 재선택 후 추가\n2. 전부 '생략', 카운트 변동 없음")
        page.l2_bulk_remove()
        page.close_l2_modal()

    # ── sc3h: templateName 직접입력 — clamp(60→30) + 특수문자 생성 ──
    def test_scenario3h_templatename_input(self, logged_in_page, settings):
        """요소별(1단계 이름 자유입력): 실타이핑 60→30 clamp + 특수문자 생성 허용(실측).
        표준: clamp/특수문자는 sc3(실제 입력 동작). sc2 는 maxlength 속성만."""
        print("\n━━ [프로세스] sc3h: templateName clamp/특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        # clamp
        page.open_add_modal()
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "a" * 60)
        page._close_modal_if_open()
        self._add("pass" if accepted == 30 else "warn",
                  "sc3h — 이름 실타이핑 60자 → clamp 30",
                  f"입력: 60자 타이핑 / 결과: 수용={accepted}자 (maxlength=30 클라 가드)", sc=3,
                  repro="1. 이름 60자 타이핑\n2. 수용 길이 30 확인")
        # 특수문자 생성
        sp = "[AUTO]_sz_proc_sp<>!@#"
        if sp in page.get_template_names():
            page.delete_template(sp); page.navigate_to()
        msg = page.create_template(sp)
        page.navigate_to()
        created = sp in page.get_template_names()
        self._add("pass" if created else "warn",
                  "sc3h — 이름 특수문자 생성(허용 여부)",
                  f"입력: '{sp}' / 결과: 경고={msg!r}, 생성={created} (실측: 형식 검사 없음, 허용)", sc=3,
                  repro="1. 이름에 특수문자(<>!@#)\n2. 확인\n3. 허용/차단")

    # ── sc3i: L3 설명 직접입력 — 특수문자 + 장문 수용 ───────────────
    def test_scenario3i_description_input(self, logged_in_page, settings):
        """요소별(L3 설명 자유입력, maxlength=None 서버측): 특수문자 재읽기 + 장문 500자 수용.
        3000자 실저장은 렌더 부하로 회피 — 클라 제한 없음(서버 처리) 확인까지."""
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
                  f"입력: {sp!r} / 재읽기: {sp_back!r}, maxlength={ml!r}(서버측)", sc=3)
        page.fill(desc_sel, "가" * 500)
        long_back = len(scope.locator(page.SEL_L3_DESC).first.input_value())
        self._add("pass" if long_back == 500 else "warn",
                  "sc3i — L3 설명 장문 500자 수용(클라 제한 없음)",
                  f"입력: 500자 / 재읽기: {long_back}자 (maxlength=None — 서버 측 처리)", sc=3,
                  repro="1. L3 설명 500자\n2. 재읽기 500(클라 제한 없음)")
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()

    # ── sc3j: ★필수(미선택) 경고 — 4타입 전수 sweep ─────────────────
    def test_scenario3j_required_sweep_by_type(self, logged_in_page, settings):
        """★L3 모달은 타입마다 별개 → 미선택 추가 시 필수 경고를 4타입 전수 검증
        (사용자 통찰: 생김새 같아도 다른 모달이라 다른 결과). 실측(2026-07-08):
        허용/예외/차단='프로세스를 선택해 주세요' / 거부=경고 없음(silent) → 거부 필수 검증 누락 결함."""
        print("\n━━ [프로세스] sc3j: 필수(미선택) 경고 4타입 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        results = {}
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = f"[AUTO]_sz_proc_3j_{ttype.split('_')[0].lower()}"
            page.navigate_to_clean()
            page.ensure_template(tpl, ttype)
            page.open_l2_modal(tpl)
            page.open_l3_add(ttype)
            # 프로세스 미선택 상태로 '추가'
            msg = page.l3_add_message(ttype)   # 경고 있으면 dismiss 후 반환, 없으면 ''
            warned = ("선택" in msg) or ("프로세스를" in msg)
            results[ko] = {"msg": msg, "warned": warned}
            f = self._shot(f"req_{ttype.split('_')[0].lower()}",
                           caption=f"{ko}: 미선택 추가 → 경고={msg!r} (경고 유무={warned})")
            self._add("pass" if warned else "warn",
                      f"sc3j — {ko}: 미선택 추가 → 필수 경고",
                      f"입력: 프로세스 미선택 + 추가 / 결과: 경고={msg!r} "
                      + ("(정상 — 필수 경고)" if warned
                         else "[★필수 경고 누락 — 다른 타입은 경고 뜨는데 이 타입만 무반응]"), sc=3,
                      screenshots=[f],
                      merge_key=(None if warned
                                 else f"szproc_required_missing::{ttype}::warn::no_required_alert"),
                      repro=f"1. {ko} 템플릿 L2 → + → L3\n2. 프로세스 미선택 상태로 추가\n"
                            "3. '프로세스를 선택해 주세요' 경고 떠야 정상(타입별 상이 주의)")
            page.close_l3_modal(ttype)
            page.close_l2_modal()
        # (요약 카드 제거 — 타입별 4개 카드가 실제 판정. 요약은 중복 서술이라 미생성.)

    # ── sc3k: ★타입별 등록 + 옵션 표시 전수 (허용에만 넣던 것 → 4타입) ──
    def test_scenario3k_register_option_by_type(self, logged_in_page, settings):
        """★사용자 지적: 등록을 허용에만 해봄. 4타입 각각 등록 → L2 옵션 셀이 타입별로 다른지 전수.
        실측(2026-07-08): 허용=재시작 / 예외=시큐어드라이브+반출드라이브+재시작 / 거부·차단=옵션 없음."""
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
            picked = page.l3_register(ttype, count=1)   # 첫 행 등록
            msg = page.l3_add_message(ttype)
            cnt = page.l2_item_count()
            opts = page.l2_option_buttons(0) if cnt >= 1 else []
            f = self._shot(f"reg_opt_{ttype.split('_')[0].lower()}",
                           highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody").first,
                           caption=f"{ko}: 등록 {cnt}건 / 옵션 버튼={opts}")
            reg_ok = bool(picked) and (msg == "") and (cnt == 1)
            opt_ok = set(opts) == set(expect)
            self._add("pass" if (reg_ok and opt_ok) else "fail",
                      f"sc3k — {ko}: 등록 + 옵션 표시(타입 전용)",
                      f"입력: {ko} 템플릿에 프로세스 1건 등록 / 결과: 등록={cnt}건, "
                      f"옵션 버튼={opts} (기대 {expect}) 일치={opt_ok}", sc=3,
                      screenshots=[f],
                      repro=f"1. {ko} 템플릿 L2 → + → 프로세스 선택 → 추가\n"
                            f"2. L2 행 옵션 셀 = {expect or '없음'}(타입 전용) 확인")
            page.l2_bulk_remove()
            page.close_l2_modal()
