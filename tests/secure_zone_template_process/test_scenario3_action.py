"""시큐어존 템플릿(프로세스) — 시나리오 3: 동작 (원자 단위 재작성 — 2026-07-08).

★재작성 원칙(13:03 run 9 fail 교훈): 한 번에 다 짓지 않는다. 실행 확인된 흐름만 남기고
단계별로 확장 — 이번 단계는 **1단계 모달만 쓰는 검증**(L2/L3 미진입 = 검증된 안전 구간).
L2/L3 등록 흐름(3c~)은 크롬 실측(picker=checkbox·L3 자동닫힘·카운트 갱신) 반영 후 다음 단계.

sc3a — 타입별 생성 4종 전수 → 리스트 등장 + 타입 컬럼 표시 (radio 반영 검증 포함)
sc3b — 동명 중복 스코프: 같은 타입 재생성(차단 기대) vs 다른 타입 동명(13:03 실측: 공존 허용
       — 이름 중복 검사가 타입 스코프. probe 관찰 재확인 대상)
"""
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
        """probe(2026-07-08) 관찰: 동명 템플릿 공존 — 중복 검사가 타입 스코프인지 분리 검증."""
        print("\n━━ [프로세스] sc3b: 동명 중복 스코프 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        # 기준 템플릿(허용) — 잔존 동명 정리 후 생성
        self._ckpt()

        def _base_tpl():
            page.navigate_to_clean()
            while self._DUP in page.get_template_names():
                page.delete_template(self._DUP)
                page.navigate_to()
            page.create_template(self._DUP, "ALLOW_PROCESS")
            page.navigate_to()
        self._act(f"기준 '{self._DUP}'(허용) 생성", _base_tpl)

        # ① 같은 타입 동명 재생성 → 차단 기대
        self._act("같은 타입(허용) 동명 재생성 시도",
                  lambda: (page.open_add_modal(),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._DUP)))
        msg_same = page.submit_and_message()
        page._close_modal_if_open()
        blocked_same = "이미 등록" in msg_same
        self._add("pass" if blocked_same else "warn",
                  "sc3b — 같은 타입 동명 재생성 → 차단",
                  f"입력: 허용+동명 / 결과: 경고={msg_same!r}"
                  + ("" if blocked_same else " [차단 안 됨 — 같은 타입도 동명 허용]"), sc=3,
                  merge_key=(None if blocked_same
                             else "szproc_dup::same_type::warn::no_dup_check"),
                  repro="1. 허용 타입 템플릿 생성\n2. 같은 이름+같은 타입 재생성\n3. 차단 여부")

        # ② 다른 타입 동명 생성 → 공존 여부 (13:03 실측: '저장 하였습니다' 공존)
        self._act("다른 타입(거부) 동명 생성 시도",
                  lambda: (page.navigate_to(), page.open_add_modal(),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._DUP),
                           page.select_type("DENY_PROCESS")))
        msg_diff = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        count = page.get_template_names().count(self._DUP)
        coexist = count >= 2
        self._add("warn" if coexist else "pass",
                  "sc3b — 다른 타입 동명 생성 → 공존 여부(스코프 실측)",
                  f"입력: 거부+동명 / 결과: 경고={msg_diff!r}, 동명 {count}개 "
                  + ("[동명 공존 — 이름 중복 검사가 타입 스코프(전역 아님), probe 관찰 재현]"
                     if coexist else "(전역 차단 — 공존 안 됨)"), sc=3,
                  merge_key=("szproc_dup::cross_type::warn::type_scoped_name_check"
                             if coexist else None),
                  repro="1. 허용 타입으로 생성한 이름 그대로\n2. 거부 타입 선택 후 저장\n"
                        "3. 동명 2개 공존하는지(리스트 확인)")
        # 정리 — 동명 잔존은 후속 이름 매칭을 오염시키므로 즉시 제거(재실행 가드 성격)
        while self._DUP in page.get_template_names():
            page.delete_template(self._DUP)
            page.navigate_to()
