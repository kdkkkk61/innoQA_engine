"""시큐어존 템플릿(프로세스) — 시나리오 4: 수정 (L1 템플릿 구간 — 원자적 1차분).

analog: sync/manage_folder sc4 (template_load/status_update/required/rename_dup/clamp).
L1(1단계 수정 모달) 구간 먼저 — run 통과 후 L2/L3(항목 수정) 구간 확장(13:03 교훈).
계약(사용자 확인 2026-07-09): L2 리스트 옵션=클릭 즉시 / L3 편집=바꾸고 '수정'까지.

sc4a 수정 모달 로드값(이름/타입/상태) + 타입 radio 편집가능 여부 수집
sc4b 상태 활성→비활성 3점 대조(저장→리스트 상태열→재오픈) + 원복
sc4c 수정에서 이름 비움 → 필수 경고 + 원래 이름 유지
sc4d 같은 타입 기존 이름으로 rename → 중복 차단
sc4e 수정에서 이름 60자 실타이핑 → clamp 30 (생성 sc3h 와 같은 가드가 수정에도)

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
