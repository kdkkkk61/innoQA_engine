"""시큐어존 템플릿(프로세스) — 시나리오 2: 입력 구조 (기본 검증 매트릭스 적용).

sc2 책임 = 초기값/별표/maxlength/필수 1차 + 타입 전용 옵션 기본값.
필드 구성이 단순(1단계=이름+radio 8개 / L3=선택버튼+옵션+설명+상태)해 4테스트로 커버.
L3 공통 검증은 컨텍스트 분산(허용 타입에서 1회 — 4타입 L3 는 sc1e 가 구조 대조 완료).

sc2a — 1단계: 초기값(허용·활성·이름 빈값) + 별표 + 이름 maxlength + 이름 빈값→경고
sc2b — L3(허용): 별표/프로세스명 required 1차(미선택 추가→경고 수집) + 설명 maxlength
sc2c — ★L3(예외처리): 전용 옵션 기본값(드라이브 권한 radio 2그룹 + 재시작 토글)
sc2d — 1단계 타입 radio 전환 — 조건부 필드 gating 없음 확인(4타입 모두 동일 3필드)
"""
from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario2Input(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 2: 입력 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ══ sc2a: 1단계 초기값/별표/maxlength/이름 필수 ══════════════════
    def test_scenario2a_stage1_input(self, logged_in_page, settings):
        print("\n━━ [프로세스] sc2a: 1단계 초기값/별표/maxlength/이름 필수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        M = page.SEL_MODAL

        name_init = page.page.locator(f"{M} {page.SEL_NAME}").first.input_value()
        allow_def = page.page.locator(f"{M} input#ALLOW_PROCESS").first.is_checked()
        create_def = page.page.locator(page.SEL_STATUS_CREATE).first.is_checked()
        self._add("pass" if (name_init == "" and allow_def and create_def) else "warn",
                  "sc2a — 1단계 초기값(이름 빈값 / 타입=허용 / 상태=활성)",
                  f"결과: 이름={name_init!r}, 허용={allow_def}, 활성={create_def}", sc=2)

        star = page.page.locator(f"{M} span.star").count()
        ml = page.page.locator(f"{M} {page.SEL_NAME}").first.get_attribute("maxlength")
        self._add("pass" if star >= 1 else "warn",
                  "sc2a — 1단계 필수 marker(별표)", f"결과: 별표 {star}개 (이름)", sc=2)
        self._add("pass", "sc2a — 이름 maxlength",
                  f"결과: maxlength={ml!r} " + ("(클라 가드)" if ml is not None else "(null — 서버 측)"), sc=2)

        msg = page.submit_and_message()
        self._add("pass" if "이름을 입력해" in msg else "fail",
                  "sc2a — 이름 안 넣고 저장 → 경고(생성 막힘)",
                  f"입력: 빈 이름 확인 / 결과: 경고={msg!r} (기대 '이름을 입력해...')", sc=2,
                  repro="1. 1단계 빈값\n2. 확인\n3. 이름 필수 경고")
        page._close_modal_if_open()

    # ══ sc2b: L3(허용) 별표/필수 1차/설명 maxlength ══════════════════
    def test_scenario2b_l3_input(self, logged_in_page, settings):
        """L3 공통 입력 구조 — 컨텍스트 분산으로 허용 타입에서 1회.
        프로세스명 required 는 미선택 상태 추가 시 경고 수집(메시지 미실측 — 추정 금지)."""
        print("\n━━ [프로세스] sc2b: L3(허용) 입력 구조 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_sc2"
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        scope = page.l3_scope("ALLOW_PROCESS")

        star = scope.locator("span.star").count()
        self._add("pass" if star >= 1 else "warn",
                  "sc2b — L3 필수 marker(별표)", f"결과: 별표 {star}개 (프로세스명)", sc=2)

        desc_ml = scope.locator(page.SEL_L3_DESC).first.get_attribute("maxlength")
        self._add("pass", "sc2b — L3 설명 maxlength",
                  f"결과: maxlength={desc_ml!r} " + ("(클라 가드)" if desc_ml is not None else "(null — 서버 측)"), sc=2)

        create_def = scope.locator("input#CREATE").first.is_checked()
        restart_def = scope.locator("input#isProcessRestart").first.is_checked()
        self._add("pass" if (create_def and not restart_def) else "warn",
                  "sc2b — L3 초기값(상태=활성 / 재시작 토글 OFF)",
                  f"결과: 활성={create_def}, 재시작={restart_def}", sc=2)

        # 프로세스 미선택 상태로 '추가' → 필수 경고 수집
        msg = page.l3_add_message("ALLOW_PROCESS")
        self._add("pass" if msg else "warn",
                  "sc2b — 프로세스 미선택 + 추가 → 필수 경고(수집)",
                  f"입력: 프로세스 미선택 추가 / 결과: 경고={msg!r}"
                  + ("" if msg else " (경고 없음 — 커밋 여부 sc3 대조 필요)"), sc=2,
                  repro="1. L3 추가 모달\n2. 프로세스 선택 없이 추가\n3. 필수 경고")
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()

    # ══ sc2c: ★L3(예외처리) 전용 옵션 기본값 ═════════════════════════
    def test_scenario2c_except_option_defaults(self, logged_in_page, settings):
        """예외처리 전용: 드라이브 권한 radio 2그룹 기본 선택값 + 재시작 토글 초기 OFF.
        radio id 중복(#ALLOW/#BLOCK) — name 조합 셀렉터로 그룹별 판독."""
        print("\n━━ [프로세스] sc2c: L3(예외처리) 전용 옵션 기본값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_sc2_ex"
        page.ensure_template(tpl, "EXCEPT_PROCESS")
        page.open_l2_modal(tpl)
        page.open_l3_add("EXCEPT_PROCESS")
        scope = page.l3_scope("EXCEPT_PROCESS")

        defaults = {}
        for group, ko in (("isSecureDriveWrite", "시큐어드라이브 접근"),
                          ("isTakeoutDriveWrite", "반출드라이브 쓰기")):
            allow_on = scope.locator(f"input[name='{group}']#ALLOW").first.is_checked()
            block_on = scope.locator(f"input[name='{group}']#BLOCK").first.is_checked()
            defaults[ko] = "허용" if allow_on else ("차단" if block_on else "미선택")
        restart = scope.locator("input#isProcessRestart").first.is_checked()
        page.close_l3_modal("EXCEPT_PROCESS")
        page.close_l2_modal()
        self._add("pass",
                  "sc2c — 예외처리 전용 옵션 기본값(수집)",
                  f"결과: {defaults}, 재시작={restart} (기본 선택값 실측 기록)", sc=2,
                  repro="1. 예외처리 템플릿 L3 추가 모달\n2. 드라이브 권한 radio 기본 선택 확인")

    # ══ sc2d: 1단계 타입 전환 — gating 없음 확인 ═════════════════════
    def test_scenario2d_stage1_no_gating(self, logged_in_page, settings):
        """1단계는 타입 radio 를 바꿔도 필드 구성 불변(이름/타입/상태 3필드) — 조건부 gating 없음.
        타입 종속은 L3 에서 발생(sc1e 대조 완료)."""
        print("\n━━ [프로세스] sc2d: 1단계 타입 전환 gating 없음 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        M = page.SEL_MODAL

        def _visible_input_count():
            return page.page.locator(f"{M} input:visible, {M} select:visible, {M} textarea:visible").count()

        counts = {}
        for t in page.TYPES:
            page.select_type(t)
            counts[page.TYPE_KO[t]] = _visible_input_count()
        page._close_modal_if_open()
        same = len(set(counts.values())) == 1
        self._add("pass" if same else "warn",
                  "sc2d — 1단계 타입 전환 시 필드 구성 불변(gating 없음)",
                  f"결과: 타입별 노출 입력 수={counts} (전부 동일={same} — 타입 종속은 L3)", sc=2,
                  repro="1. 1단계 모달 타입 radio 4종 전환\n2. 필드 구성 변화 없는지")

    # ══ sc2e: 자유입력 요소 — templateName 특수문자 + clamp(실타이핑) ══
    def test_scenario2e_templatename_freetext(self, logged_in_page, settings):
        """1단계 이름(자유입력) 요소별: 특수문자 허용 + maxlength 30 clamp(실타이핑 60→30 실측)."""
        print("\n━━ [프로세스] sc2e: templateName 특수문자/clamp ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        # 특수문자 이름 생성 허용 여부
        sp = "[AUTO]_sz_proc_sp<>!@#"
        if sp in page.get_template_names():
            page.delete_template(sp); page.navigate_to()
        msg = page.create_template(sp)
        page.navigate_to()
        created = sp in page.get_template_names()
        self._add("pass" if created else "warn",
                  "sc2e — 이름 특수문자 입력(생성 허용 여부)",
                  f"입력: '{sp}' / 결과: 경고={msg!r}, 생성={created} (실측: 특수문자 허용, 형식 검사 없음)", sc=2,
                  repro="1. 이름에 특수문자(<>!@#)\n2. 확인\n3. 허용/차단")
        # clamp: 실타이핑 60자 → 수용 길이
        page.open_add_modal()
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "a" * 60)
        page._close_modal_if_open()
        self._add("pass" if accepted == 30 else "warn",
                  "sc2e — 이름 실타이핑 60자 → clamp 30",
                  f"입력: 60자 타이핑 / 결과: 수용={accepted}자 (maxlength=30 클라 가드)", sc=2,
                  repro="1. 이름에 60자 타이핑\n2. 실제 수용 길이 확인")

    # ══ sc2f: 자유입력 요소 — L3 설명 특수문자 + 장문 수용(재읽기) ══
    def test_scenario2f_l3_description_freetext(self, logged_in_page, settings):
        """L3 설명(자유입력, maxlength=None 서버측) 요소별: 특수문자 + 장문(500자) 수용 재읽기.
        저장 시 서버 처리(길이 초과 등)는 sc3/sc4 수집 — 여기선 입력 수용만."""
        print("\n━━ [프로세스] sc2f: L3 설명 특수문자/장문 수용 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_sc2f"
        page.ensure_template(tpl)
        page.open_l2_modal(tpl)
        page.open_l3_add("ALLOW_PROCESS")
        scope = page.l3_scope("ALLOW_PROCESS")
        desc_sel = f"div#{page.L3_MAP['ALLOW_PROCESS']}.in {page.SEL_L3_DESC}"
        ml = scope.locator(page.SEL_L3_DESC).first.get_attribute("maxlength")
        # 특수문자 재읽기
        sp = "설명<>&!@# 특수"
        page.fill(desc_sel, sp)
        sp_back = scope.locator(page.SEL_L3_DESC).first.input_value()
        self._add("pass" if sp_back == sp else "warn",
                  "sc2f — L3 설명 특수문자 수용(재읽기)",
                  f"입력: {sp!r} / 재읽기: {sp_back!r}, maxlength={ml!r}(서버측)", sc=2)
        # 장문 500자 수용 (안전 크기 — 3000 은 렌더 부하로 sc3 수집)
        page.fill(desc_sel, "가" * 500)
        long_back = len(scope.locator(page.SEL_L3_DESC).first.input_value())
        self._add("pass" if long_back == 500 else "warn",
                  "sc2f — L3 설명 장문 500자 수용(클라 제한 없음)",
                  f"입력: 500자 / 재읽기: {long_back}자 (maxlength=None — 서버 측 처리)", sc=2,
                  repro="1. L3 설명에 500자\n2. 재읽기 길이 = 500(클라 제한 없음)")
        page.close_l3_modal("ALLOW_PROCESS")
        page.close_l2_modal()
