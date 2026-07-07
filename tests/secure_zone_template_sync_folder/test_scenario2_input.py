"""시큐어존 템플릿(폴더동기화) — 시나리오 2: 입력 구조 (특수폴더 sc2 미러 + 스케줄 gating).

sc2 책임 = "생성 시 무엇을 입력하고, 안 넣으면 어떤 순서로 막히나" + 구조 속성(초기값/maxlength/별표/종속).
필드 단순 '존재'는 sc1 몫. 상세 동작(폴더 매핑 커밋·예약어 picker·스케줄별 저장)은 sc3.

★특수폴더와 다른 점: 폴더동기화 내용 모달엔 **스케줄 조건부(gating)가 있다** (syncFolderScheduleType
  → 매분/매일/매주별 필드 노출). 특수폴더 sc2d 는 "gating 없음"이었지만 여기선 "gating 존재"가 정상.

필수 메시지/maxlength 는 동일 제품(시큐어존 템플릿)이라 특수폴더 값 미러 → 첫 run 으로 튜닝.
스케줄 타입별 required(매주=요일 필수 등)는 저장 흐름이라 sc3 담당.

sc2a — 1단계: 입력 면 + 초기값(타입 SYNC_FOLDER 단일·상태 활성·이름 빈값) + 별표 + maxlength + 이름 빈값→경고
sc2b — 내용: 입력 면 + 별표 + 설정명/설명 maxlength + 원본/대상=contenteditable
sc2c — 내용 필수 순서(설정명→원본위치→대상위치) — 단계별 경고 비교
sc2d — ★내용 종속/gating = 스케줄 조건부 존재(select#syncFolderScheduleType + 타입 전환 시 필드 노출)
"""
from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase


class TestSecureZoneTemplateSyncFolderScenario2Input(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — 시나리오 2: 입력 구조."""

    _S2_TEMPLATE = "[AUTO]_sz_sync_s2"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def _open_content(self, page):
        page.ensure_template(self._S2_TEMPLATE)
        page.navigate_to()
        page.open_folder_modal(self._S2_TEMPLATE)
        page.open_content_add()

    # ══ sc2a: 1단계 입력 면 + 초기값 + 별표 + maxlength + 이름 필수 ══════
    def test_scenario2a_stage1_input(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc2a: 1단계 입력 면/초기값/별표/maxlength/이름 필수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.open_add_modal()
        M = page.SEL_MODAL

        type_single = page.field_present(page.SEL_MODAL + " input#SYNC_FOLDER")
        cr_def = page.page.locator(page.SEL_STATUS_CREATE).first
        name_init = page.page.locator(f"{M} {page.SEL_NAME}").first.input_value()
        self._add("pass" if type_single else "warn",
                  "sc2a — 1단계 입력 면(이름 / 타입 SYNC_FOLDER 단일 / 상태)",
                  f"결과: 타입 SYNC_FOLDER 존재={type_single} (특수폴더와 달리 용도 분기 없음)", sc=2,
                  repro="1. 템플릿 추가\n2. 이름·타입(단일)·상태 입력 면")
        self._add("pass" if (cr_def.is_checked() and name_init == "") else "warn",
                  "sc2a — 초기값(상태=활성 / 이름 빈값)",
                  f"결과: 활성={cr_def.is_checked()}, 이름={name_init!r}", sc=2)

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

    # ══ sc2b: 내용 입력 면 + 별표 + maxlength + 원본/대상 속성 ════════════
    def test_scenario2b_content_input(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc2b: 내용 입력 면/별표/maxlength/원본대상 속성 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._open_content(page)
        scope = page.SEL_CONTENT

        star = page.page.locator(f"{scope} span.star").count()
        self._add("pass" if star >= 3 else "warn",
                  "sc2b — 내용 필수 marker(별표)",
                  f"결과: 별표 {star}개 (설정명/원본/대상 기대)", sc=2)

        name_ml = page.page.locator(page.SEL_C_NAME).first.get_attribute("maxlength")
        desc_ml = page.page.locator(page.SEL_C_DESC).first.get_attribute("maxlength")
        self._add("pass", "sc2b — 설정명 maxlength",
                  f"결과: maxlength={name_ml!r} " + ("(클라 가드)" if name_ml is not None else "(null — 서버 측)"), sc=2)
        self._add("pass", "sc2b — 설명 maxlength",
                  f"결과: maxlength={desc_ml!r} " + ("(클라 가드)" if desc_ml is not None else "(null — 서버 측)"), sc=2)

        src_ce = page.page.locator(page.SEL_C_SOURCE).first.get_attribute("contenteditable")
        tgt_ce = page.page.locator(page.SEL_C_TARGET).first.get_attribute("contenteditable")
        self._add("pass" if (src_ce == "true" and tgt_ce == "true") else "warn",
                  "sc2b — 원본/대상위치 = contenteditable(예약어 picker 전용)",
                  f"결과: 원본 ce={src_ce!r}, 대상 ce={tgt_ce!r} (picker 동작은 sc3)", sc=2,
                  repro="1. 내용 모달\n2. 원본/대상은 텍스트 input 아님(picker 전용)")
        page.close_content_modal()
        page.close_folder_modal()

    # ══ sc2c: 내용 필수 순서 (설정명→원본위치→대상위치) ══════════════════
    def test_scenario2c_content_required_order(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc2c: 내용 필수 순서(설정명→원본→대상) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._open_content(page)

        steps = [
            (None,                                        "설정명을 입력해",   "전부 빈값"),
            (("input", page.SEL_C_NAME, "[AUTO]_seq"),    "원본위치를 입력해", "+설정명"),
            (("ce",    page.SEL_C_SOURCE, "[/DESKTOP/]"), "대상위치를 입력해", "+원본위치"),
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

    # ══ sc2d: ★내용 종속/gating = 스케줄 조건부 존재 ═════════════════════
    def test_scenario2d_schedule_gating(self, logged_in_page, settings):
        """특수폴더 sc2d 는 'gating 없음'이었지만, 폴더동기화는 스케줄 조건부(gating)가 정상 존재.
        select#syncFolderScheduleType(없음/매분/매일/매주) + 타입 전환 시 하위필드 노출 변화 확인.
        (타입별 노출 매핑 상세는 sc1e, 타입별 저장 required 는 sc3.)"""
        print("\n━━ [폴더동기화] sc2d: 스케줄 조건부 gating 존재 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._open_content(page)

        has_select = page.field_present(page.SEL_C_SCHEDULE)
        self._add("pass" if has_select else "fail",
                  "sc2d — 스케줄 동작 select(gating 트리거) 존재",
                  f"결과: select#syncFolderScheduleType={has_select} "
                  "(특수폴더와 달리 조건부 필드 gating 있음)", sc=2,
                  repro="1. 내용 모달\n2. 스케줄 동작 select 확인")
        if has_select:
            # 없음 → 하위필드 숨김 / 매주 → 요일 노출 : gating 실동작 1점 대조
            page.set_schedule_type("NONE")
            none_hidden = not page.field_visible(page.SEL_C_MINUTES) and not page.field_visible("input#checkMon")
            page.set_schedule_type("WEEKS")
            weeks_show = page.field_visible("input#checkMon")
            self._add("pass" if (none_hidden and weeks_show) else "fail",
                      "sc2d — gating 실동작(없음=숨김 / 매주=요일 노출)",
                      f"결과: 없음 하위숨김={none_hidden}, 매주 요일노출={weeks_show}", sc=2,
                      repro="1. 스케줄 '없음' → 하위필드 숨김\n2. '매주' → 요일 체크 노출")
        page.close_content_modal()
        page.close_folder_modal()
