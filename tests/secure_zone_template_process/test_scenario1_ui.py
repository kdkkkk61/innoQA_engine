"""시큐어존 템플릿(프로세스) — 시나리오 1: UI 구조 (폴더동기화 sc1 미러 + 타입 하드매핑).

sc1a — navigate + 툴바(추가/수정/프로세스 추가·제거/복사/삭제) + cleanup
sc1b — 리스트 컬럼 헤더(용도/이름/타입/카운트/상태/등록일/수정일 — ★타입 컬럼 존재)
sc1c — 1단계 ADD 모달 필드(이름/타입 radio 4종/상태) + 기본값(허용·활성) + close
sc1d — 2단계 L2 진입 + 내부 탭(개별 프로세스/태그) + +/- 버튼
sc1e — ★타입별 L3 하드매핑 대조(4종: 모달 id·타이틀·타입 전용 옵션 노출) — 이 탭 핵심
sc1f — default reset
"""
from pages.secure_zone_template_process_page import SecureZoneTemplateProcessPage
from tests.secure_zone_template_process._base import SecureZoneTemplateProcessBase


class TestSecureZoneTemplateProcessScenario1Ui(SecureZoneTemplateProcessBase):
    """시큐어존 템플릿(프로세스) — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/프로세스] 시나리오 1a: navigate + 툴바 + cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        url_ok = ("managerSecureZoneTemplate" in page.page.url
                  and "selectedTab=PROCESS" in page.page.url)
        self._add("pass" if url_ok else "fail",
                  "sc1a — navigate → 템플릿 관리 / 프로세스 탭",
                  f"입력: navigate_to / 결과: url={page.page.url!r}", sc=1,
                  repro="1. 공통설정>SecureZone>템플릿 관리\n2. 프로세스 탭")
        toolbar = {"템플릿추가": page.SEL_ADD_BTN, "수정": page.SEL_MODIFY_BTN,
                   "프로세스 추가/제거": page.SEL_PROC_ADD_DEL_BTN,
                   "복사": page.SEL_COPY_BTN, "삭제": page.SEL_DELETE_BTN}
        for label, sel in toolbar.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1a — 툴바 '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)

    def test_scenario1b_list_columns(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/프로세스] 시나리오 1b: 리스트 컬럼 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = page.column_headers()
        has_type = any("타입" in h for h in headers)
        has_name = any("이름" in h or "템플릿" in h for h in headers)
        self._add("pass" if (headers and has_name and has_type) else "warn",
                  "sc1b — 리스트 컬럼 헤더 (★타입 컬럼 존재 — 필터 변별 검증 가능)",
                  f"입력: 리스트 / 결과: 헤더={headers} (이름={has_name}, 타입={has_type})", sc=1,
                  repro="1. 프로세스 탭 리스트\n2. 컬럼 헤더 확인")

    def test_scenario1c_add_modal_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/프로세스] 시나리오 1c: 1단계 ADD 모달 핵심필드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        fields = {"이름(templateName)": f"{page.SEL_MODAL} {page.SEL_NAME}",
                  "상태 활성(CREATE)": page.SEL_STATUS_CREATE,
                  "상태 비활성(DELETE)": page.SEL_STATUS_DELETE}
        for t in page.TYPES:
            fields[f"타입 {page.TYPE_KO[t]}"] = f"{page.SEL_MODAL} input#{t}"
        for label, sel in fields.items():
            present = page.field_present(sel)
            self._add("pass" if present else "fail",
                      f"sc1c — ADD 모달 필드 '{label}'", f"결과: present={present}", sc=1)
        # 기본값: 타입=허용 / 상태=활성
        allow_def = page.page.locator(f"{page.SEL_MODAL} input#ALLOW_PROCESS").first.is_checked()
        create_def = page.page.locator(page.SEL_STATUS_CREATE).first.is_checked()
        self._add("pass" if (allow_def and create_def) else "warn",
                  "sc1c — 기본값(타입=허용 프로세스 / 상태=활성)",
                  f"결과: 허용={allow_def}, 활성={create_def}", sc=1)
        page.close_modal()

    def test_scenario1d_l2_modal(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/프로세스] 시나리오 1d: 2단계 L2 모달 + 내부 탭 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_proc_sc1"
        page.ensure_template(tpl)
        page.navigate_to()
        if tpl not in page.get_template_names():
            self._add("warn", "sc1d — 템플릿 생성 실패로 2단계 진입 불가", f"'{tpl}' 없음", sc=1)
            return
        page.open_l2_modal(tpl)
        l2_ok = page.field_present(page.SEL_L2_MODAL)
        self._add("pass" if l2_ok else "fail",
                  "sc1d — 2단계 '프로세스 추가/제거'(L2) 진입",
                  f"입력: 행 선택 → 프로세스 추가/제거 / 결과: 모달={l2_ok}", sc=1,
                  repro="1. 행 선택(tActive)\n2. 프로세스 추가/제거 버튼")
        if not l2_ok:
            return
        l2 = page.page.locator(page.SEL_L2_MODAL).last
        for tab in ("개별 프로세스", "태그"):
            present = l2.locator("li a", has_text=tab).count() > 0
            self._add("pass" if present else "fail",
                      f"sc1d — L2 내부 탭 '{tab}' 존재", f"결과: present={present}", sc=1)
        for label, sel in (("+(addItemBtn)", page.SEL_L2_ADD_ITEM),
                           ("-(removeItemBtn)", page.SEL_L2_DEL_ITEM)):
            present = page.field_present(sel)
            self._add("pass" if present else "fail",
                      f"sc1d — L2 버튼 '{label}' 존재", f"결과: present={present}", sc=1)
        page.close_l2_modal()

    def test_scenario1e_l3_type_mapping(self, logged_in_page, settings):
        """★타입별 L3 하드매핑 대조 — 실측(2026-07-08) id·옵션과 일치 여부. 이 탭 핵심."""
        print("\n━━ [시큐어존 템플릿/프로세스] 시나리오 1e: 타입별 L3 하드매핑 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        for ttype in page.TYPES:
            ko = page.TYPE_KO[ttype]
            tpl = f"[AUTO]_sz_proc_sc1_{ttype.split('_')[0].lower()}"
            page.ensure_template(tpl, ttype)
            page.navigate_to()
            # 타입 컬럼 표시도 함께 대조 (radio 반영 검증 — probe 미반영 사례 교훈)
            row_type = page.row_type_text(tpl)
            page.open_l2_modal(tpl)
            page.open_l3_add(ttype)
            scope = page.l3_scope(ttype)
            title = scope.locator(".modal-title").first.inner_text().strip()
            opts_ok = {}
            for opt_label, opt_sel in page.L3_OPTIONS[ttype].items():
                opts_ok[opt_label] = scope.locator(opt_sel).count() > 0
            common_ok = (scope.locator(page.SEL_L3_PICK).count() > 0
                         and scope.locator(page.SEL_L3_DESC).count() > 0)
            page.close_l3_modal(ttype)
            page.close_l2_modal()
            ok = (ko in title) and (ko in row_type) and common_ok and all(opts_ok.values())
            self._add("pass" if ok else "fail",
                      f"sc1e — L3 하드매핑: {ko} → {page.L3_MAP[ttype]}",
                      f"결과: 행 타입={row_type!r}, 타이틀={title!r}, 공통(선택버튼/설명)={common_ok}, "
                      f"전용 옵션={opts_ok or '없음(정상)'}", sc=1,
                      repro=f"1. {ko} 템플릿 행 선택\n2. 프로세스 추가/제거 → +\n"
                            f"3. L3 = {page.L3_MAP[ttype]} · 옵션 노출 대조")

    def test_scenario1f_default_reset(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/프로세스] 시나리오 1f: default reset ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "[AUTO]_sz_proc_reset")
        page.select_type("DENY_PROCESS")
        page.close_modal()
        page.open_add_modal()
        val = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        allow_def = page.page.locator(f"{page.SEL_MODAL} input#ALLOW_PROCESS").first.is_checked()
        ok = (val == "") and allow_def
        self._add("pass" if ok else "fail",
                  "sc1f — ADD 모달 재오픈 시 초기화(이름 빈값 + 타입 허용 복귀)",
                  f"입력: 이름+거부 선택→닫기→재오픈 / 결과: 이름={val!r}, 허용 기본={allow_def}", sc=1,
                  repro="1. 추가 모달 이름·타입 변경\n2. 닫기\n3. 재오픈 → 초기값이어야")
        page.close_modal()
