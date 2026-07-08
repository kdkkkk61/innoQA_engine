"""시큐어존 템플릿(프로세스) — 시나리오 3: 동작 (원자 단위 재작성 — 2026-07-08).

★재작성 원칙(13:03 run 9 fail 교훈): 한 번에 다 짓지 않는다. 실행 확인된 흐름만 남기고
단계별로 확장 — 이번 단계는 **1단계 모달만 쓰는 검증**(L2/L3 미진입 = 검증된 안전 구간).
L2/L3 등록 흐름(3c~)은 크롬 실측(picker=checkbox·L3 자동닫힘·카운트 갱신) 반영 후 다음 단계.

sc3a — 타입별 생성 4종 전수 → 리스트 등장 + 타입 컬럼 표시 (radio 반영 검증 포함)
sc3b — 동명 중복 스코프. ★핵심 = 같은 타입 내 동명 차단 여부(템플릿 부여가 타입별로 나오므로
       같은 타입에 동명이면 구분 불가 = 중요). 부수 = 다른 타입 동명 공존(타입 스코프 — 동작상
       정상이나 부여 목록에 동명이 나올 수 있어 경고 가치). 복사 충돌 등은 후속 단계.
[L2/L3 등록 구간 — 크롬 실측(13:14) 반영: picker=checkbox(multi/tag_multi)·L3 자동닫힘·카운트 갱신]
sc3c — ★개별 프로세스 등록: 날짜본 seed([AUTO_<MMDD>]_cm_proc — 운용 프로세스 sc6 산출) 우선
       검색·선택(연계 소비) → 커밋 → L2 반영 + 리스트 카운트
sc3d — ★태그 등록: 날짜본 태그([AUTO_<MMDD>]_cm_tag — 태그 sc6 산출) 동일 패턴
※ seed 선택 규칙(사용자 2026-07-08): picker 에서 [AUTO_ 검색 → 정확 일치. 무조건 첫 행 금지.
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

    # ── sc3c: 개별 프로세스 등록 (기본 동작 — 첫 행) ────────────────
    def test_scenario3c_process_register(self, logged_in_page, settings):
        """★기본 등록이 되는가(핵심). 첫 행 프로세스 선택 → 추가 → L2 반영 + 리스트 카운트.
        seed 연계와 분리(엉킴이 13:03 오독 유발) — 여기선 '등록 자체' 만 검증."""
        print("\n━━ [프로세스] sc3c: 개별 프로세스 등록(기본) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3c"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS")   # 첫 행, plain click
        shown = page.l3_selected_name("ALLOW_PROCESS")
        f1 = self._shot("proc_reg_selected",
                        highlight=page.l3_scope("ALLOW_PROCESS").locator("span#szProcessName").first,
                        caption=f"1. 프로세스 선택 → 표시={shown!r}")
        msg = page.l3_add_message("ALLOW_PROCESS")
        cnt = page.l2_item_count()
        f2 = self._shot("proc_reg_l2",
                        highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody").first,
                        caption=f"2. 추가 → L2 목록 {cnt}건 (경고={msg!r})")
        ok = bool(picked) and (msg == "") and (cnt >= 1)
        self._add("pass" if ok else "fail",
                  "sc3c — 개별 프로세스 등록 → L2 반영",
                  f"입력: 첫 행 {shown!r} 선택 + 추가 / 결과: 경고={msg!r}, L2 등록 {cnt}건", sc=3,
                  screenshots=[f1, f2],
                  repro="1. L2 '+' → L3\n2. 프로세스 선택(체크)\n3. 추가 → 알림 없이 L2 목록 반영")
        page.close_l2_modal()
        list_cnt = ""
        try:
            list_cnt = page._row_locator(tpl).locator("td").nth(3).inner_text().strip()
        except Exception:
            pass
        self._add("pass" if list_cnt.startswith("1/") else "warn",
                  "sc3c — 리스트 '프로세스/태그 카운트' 갱신",
                  f"결과: {list_cnt!r} (기대 1/N — L2 닫으면 갱신)", sc=3)

    # ── sc3d: 태그 등록 (기본 동작 — 첫 태그) ───────────────────────
    def test_scenario3d_tag_register(self, logged_in_page, settings):
        """★기본 태그 등록. L2 태그 탭 → 첫 태그 선택 → 추가 → 태그 탭 반영 + 카운트."""
        print("\n━━ [프로세스] sc3d: 태그 등록(기본) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3d"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.switch_l2_tab("태그")
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS", tag=True)   # 첫 태그, plain click
        shown = page.l3_selected_name("ALLOW_PROCESS")
        f1 = self._shot("tag_reg_selected",
                        highlight=page.l3_scope("ALLOW_PROCESS").locator("span#szProcessName").first,
                        caption=f"1. 태그 선택 → 표시={shown!r}")
        msg = page.l3_add_message("ALLOW_PROCESS")
        cnt = page.l2_item_count()
        f2 = self._shot("tag_reg_l2",
                        highlight=page.page.locator(f"{page.SEL_L2_MODAL} tbody").first,
                        caption=f"2. 추가 → 태그 탭 {cnt}건 (경고={msg!r})")
        ok = bool(picked) and (msg == "") and (cnt >= 1)
        self._add("pass" if ok else "fail",
                  "sc3d — 태그 등록 → L2 태그 탭 반영",
                  f"입력: 첫 태그 {shown!r} 선택 + 추가 / 결과: 경고={msg!r}, 태그 탭 등록 {cnt}건", sc=3,
                  screenshots=[f1, f2],
                  repro="1. L2 태그 탭 → + → L3\n2. 태그 선택(체크)\n3. 추가 → 태그 탭 반영")
        page.close_l2_modal()

    # ── sc3e: ★sc6 연계 — 날짜본 프로세스 seed 소비 (운용 프로세스 sc6) ──
    def test_scenario3e_seed_link(self, logged_in_page, settings):
        """picker 에서 [AUTO_ 검색 → [AUTO_<date>]_cm_proc 날짜본 정확 매칭 선택 → 등록.
        ★seed 없으면 skip('운용 프로세스 sc6 선행 필요') — BUG 아님(연계 선행 조건)."""
        print("\n━━ [프로세스] sc3e: sc6 연계 프로세스 seed 소비 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_3e"
        page.navigate_to_clean()
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        picked = page.l3_register("ALLOW_PROCESS", name_pattern=page.SEED_PROC,
                                  search_term="[AUTO_")
        if not picked:
            self._add("skip",
                      "sc3e — 연계: 운용 프로세스 sc6 날짜본 seed 소비 [선행 필요]",
                      "결과: picker 에 [AUTO_<date>]_cm_proc 없음 — 운용 프로세스 sc6 미실행. "
                      "chain 검증 스킵(제품 이상 아님).", sc=3,
                      repro="1. 운용 프로세스 sc6 로 [AUTO_<날짜>]_cm_proc 생성\n"
                            "2. 프로세스 탭 L3 picker 에서 [AUTO_ 검색 → 그 seed 선택")
            page.close_l3_modal("ALLOW_PROCESS")
            page.close_l2_modal()
            return
        shown = page.l3_selected_name("ALLOW_PROCESS")
        f1 = self._shot("seed_selected",
                        highlight=page.l3_scope("ALLOW_PROCESS").locator("span#szProcessName").first,
                        caption=f"1. 연계 seed 선택 → {shown!r}")
        msg = page.l3_add_message("ALLOW_PROCESS")
        cnt = page.l2_item_count()
        ok = (msg == "") and (cnt >= 1)
        self._add("pass" if ok else "fail",
                  "sc3e — 연계: 운용 프로세스 sc6 날짜본 seed 등록",
                  f"입력: seed {shown!r}(운용 프로세스 sc6 산출) 선택 + 추가 / "
                  f"결과: 경고={msg!r}, L2 등록 {cnt}건", sc=3,
                  screenshots=[f1],
                  repro="1. L3 '프로세스 선택' → [AUTO_ 검색\n2. 날짜본 seed 정확 일치 선택\n3. 추가 → 등록")
        page.close_l2_modal()
