"""시큐어존 템플릿(특수폴더) — 시나리오 2: 입력 구조 (가볍게, 그러나 필수검증/순서/marker 보강).

sc0/1/2 가벼운 baseline. 생성 흐름·용도별 이슈(폴더 매핑·관리자 게이팅·중복·암호화)는 sc3/4(빡빡).
sc2 책임 = "생성 시 무엇을 입력하고, 안 넣으면 **어떤 순서로** 막히나" + 구조 속성(초기값/maxlength/별표/종속).
필드 단순 '존재'는 sc1 몫(중복 안 함). 용도 '구조' 차이(레지 전용 인증 필드)=sc1e, '동작' 차이(관리자 게이팅·암호화)=sc3.
공통 입력(설정명/원본/대상/설명)은 바로가기·레지변경이 같은 id·컴포넌트 → 입력 속성 1회 검증(정당한 dedup).

직접조작 수집(2026-06-30, 192.168.13.141):
- 1단계 필수=이름 1개(별표1), maxlength 30, 빈값→"템플릿 이름을 입력해 주세요."
- 내용 필수=설정명/원본/대상(별표3), 설정명 maxlength 30 / 설명 null(서버) / 원본·대상 contenteditable.
- 내용 필수 순서: 설정명 → 원본위치 → 대상위치 (메시지 깔끔, i18n 키 누출 없음).
- 내용 모달 종속/gating 없음(status radio 외 조건부 필드 없음 — secure_drive 용량방식 같은 게 없음).

sc2a — 1단계: 입력 면 + 초기값 + 별표 + 이름 maxlength + 이름 빈값→경고(순서 1단계)
sc2b — 내용: 입력 면 + 별표 + 설정명/설명 maxlength + 원본·대상=contenteditable(picker 전용)
sc2c — 내용 필수 '순서'(설정명→원본위치→대상위치) — 단계별 경고 == 비교
sc2d — 내용 종속/gating 여부 ([SKIP] 없음 확인)
"""
from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario2Input(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — 시나리오 2: 입력 구조(보강)."""

    _S2_TEMPLATE = "[AUTO]_sz_mf_s2"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _open_content(self, page):
        """바로가기 내용 모달 진입 — 입력 면 검사용([AUTO] 템플릿 ensure)."""
        page.ensure_template(self._S2_TEMPLATE, "SHORTCUT")
        page.open_folder_modal(self._S2_TEMPLATE)
        page.open_content_add()

    # ══ sc2a: 1단계 입력 면 + 초기값 + 별표 + maxlength + 이름 필수 ══════
    def test_scenario2a_stage1_input(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc2a: 1단계 입력 면/초기값/별표/maxlength/이름 필수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        M = page.SEL_MODAL

        # 입력 면(이름/용도2종/상태) + 초기값(default 바로가기·활성·이름빈값)
        both_types = page.field_present(page.SEL_TYPE_SHORTCUT) and page.field_present(page.SEL_TYPE_REGIST)
        sc_def = page.page.locator(page.SEL_TYPE_SHORTCUT).first
        cr_def = page.page.locator(page.SEL_STATUS_CREATE).first
        name_init = page.page.locator(f"{M} {page.SEL_NAME}").first.input_value()
        self._add("pass" if both_types else "warn",
                  "sc2a — 1단계 입력 면(이름 / 용도 바로가기·레지변경 / 상태)",
                  f"결과: 용도2종={both_types}", sc=2,
                  repro="1. 템플릿 추가\n2. 이름·용도2종·상태 입력 면")
        self._add("pass" if (sc_def.is_checked() and cr_def.is_checked() and name_init == "") else "warn",
                  "sc2a — 초기값(용도=바로가기 / 상태=활성 / 이름 빈값)",
                  f"결과: 바로가기={sc_def.is_checked()}, 활성={cr_def.is_checked()}, 이름={name_init!r}", sc=2)

        # 별표(필수=이름 1개) + 이름 maxlength
        star = page.page.locator(f"{M} span.star").count()
        ml = page.page.locator(f"{M} {page.SEL_NAME}").first.get_attribute("maxlength")
        self._add("pass" if star >= 1 else "warn",
                  "sc2a — 1단계 필수 marker(별표)", f"결과: 별표 {star}개 (이름)", sc=2)
        self._add("pass", "sc2a — 이름 maxlength",
                  f"결과: maxlength={ml!r} " + ("(클라 가드)" if ml is not None else "(null — 서버 측)"), sc=2)

        # 이름 빈값 → 경고(순서상 1단계 첫 관문)
        msg = page.submit_and_message()
        self._add("pass" if "템플릿 이름을 입력해 주세요." in msg else "fail",
                  "sc2a — 이름 안 넣고 저장 → 경고(생성 막힘)",
                  f"입력: 빈 이름 확인 / 결과: 경고={msg!r} (기대 '템플릿 이름을 입력해 주세요.')", sc=2,
                  repro="1. 1단계 빈값\n2. 확인\n3. 이름 필수 경고")
        page._close_modal_if_open()

    # ══ sc2b: 내용 입력 면 + 별표 + maxlength + 원본대상 속성 ════════════
    def test_scenario2b_content_input(self, logged_in_page, settings):
        print("\n━━ [특수폴더] sc2b: 내용(폴더 매핑) 입력 면/별표/maxlength/원본대상 속성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._open_content(page)
        scope = page.SEL_CONTENT_ANY

        star = page.page.locator(f"{scope} >> span.star").count()
        self._add("pass" if star >= 3 else "warn",
                  "sc2b — 내용 필수 marker(별표)",
                  f"결과: 별표 {star}개 (설정명/원본/대상)", sc=2)

        name_ml = page.page.locator(page.SEL_C_NAME).first.get_attribute("maxlength")
        desc_ml = page.page.locator(page.SEL_C_DESC).first.get_attribute("maxlength")
        self._add("pass", "sc2b — 설정명 maxlength",
                  f"결과: maxlength={name_ml!r} " + ("(클라 가드)" if name_ml is not None else "(null — 서버 측)"), sc=2)
        self._add("pass", "sc2b — 설명 maxlength",
                  f"결과: maxlength={desc_ml!r} " + ("(클라 가드)" if desc_ml is not None else "(null — 서버 측)"), sc=2)

        src_ce = page.page.locator(page.SEL_C_SOURCE).first.get_attribute("contenteditable")
        tgt_ce = page.page.locator(page.SEL_C_TARGET).first.get_attribute("contenteditable")
        self._add("pass" if (src_ce == "true" and tgt_ce == "true") else "warn",
                  "sc2b — 원본/대상위치 = input 아닌 contenteditable(예약어 picker 전용)",
                  f"결과: 원본 ce={src_ce!r}, 대상 ce={tgt_ce!r} (특수폴더 버튼/예약어로 채움 — picker 동작은 sc3)", sc=2,
                  repro="1. 내용 모달\n2. 원본/대상은 텍스트 input 아님(picker 전용)")
        page.close_content_modal()
        page.close_folder_modal()

    # ══ sc2c: 내용 필수 '순서' (설정명→원본위치→대상위치) ════════════════
    def test_scenario2c_content_required_order(self, logged_in_page, settings):
        """필수 미입력 시 '어느 필드를 어떤 순서로' 짚는지 — 단계별 경고 == 비교(직접조작 수집).
        순서: 빈값→설정명 / +설정명→원본위치 / +원본→대상위치 (대상까지 채우면 커밋되므로 그 앞까지)."""
        print("\n━━ [특수폴더] sc2c: 내용 필수 순서(설정명→원본→대상) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._open_content(page)

        # (직전에 채울 (종류, 셀렉터, 값) | 기대 경고 부분문자열 | 설명)
        steps = [
            (None,                                          "설정명을 입력해 주세요.",   "전부 빈값"),
            (("input", page.SEL_C_NAME, "[AUTO]_seq"),      "원본위치를 입력해 주세요.", "+설정명"),
            (("ce",    page.SEL_C_SOURCE, "[/DESKTOP/]"),   "대상위치를 입력해 주세요.", "+원본위치"),
        ]
        for fill, expect, desc in steps:
            if fill:
                kind, sel, val = fill
                if kind == "input":
                    page.fill(sel, val)
                else:
                    page.set_content_path(sel, val)
            msg = page.content_add_message()
            self._add("pass" if expect in msg else "fail",
                      f"sc2c — 내용 필수 순서: {desc} → 경고",
                      f"입력: {desc} 후 추가 / 결과: 경고={msg!r} (기대 포함 {expect!r})", sc=2,
                      repro=f"1. {desc} 상태로 추가\n2. 해당 필수 필드 짚는 경고 확인")
        page.close_content_modal()
        page.close_folder_modal()

    # ══ sc2d: 내용 종속/gating 여부 ═════════════════════════════════════
    def test_scenario2d_content_gating(self, logged_in_page, settings):
        """secure_drive 의 용량방식→용량 같은 '종속/gating' 이 내용 모달에 있는지.
        직접조작(2026-06-30): 내용 모달에 select·조건부 토글 없음(status radio 만) → 종속 없음."""
        print("\n━━ [특수폴더] sc2d: 내용 종속/gating 여부 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._open_content(page)
        scope = page.SEL_CONTENT_ANY
        selects = page.page.locator(f"{scope} >> select").count()
        # status 외 조건부 토글(체크박스) 유무
        checks = page.page.locator(f"{scope} >> input[type='checkbox']").count()
        self._add("skip" if (selects == 0 and checks == 0) else "warn",
                  "sc2d — 내용 모달 종속/gating",
                  f"결과: select={selects}, 조건부 체크박스={checks} "
                  + ("([SKIP] 종속 없음 — secure_drive 용량방식 같은 조건부 필드 없음)"
                     if (selects == 0 and checks == 0) else "(조건부 필드 발견 — 종속 검증 필요)"), sc=2,
                  repro="1. 내용 모달\n2. 조건부로 나타나는 필드 없는지 확인")
        page.close_content_modal()
        page.close_folder_modal()
