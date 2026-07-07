"""시큐어존 템플릿(폴더동기화) — 시나리오 5: lifecycle + 속성 모달 표시 (특수폴더 sc5 미러).

속성-확인 법칙: ①채워 저장 → ②재오픈 round-trip(손실=fail) → ③속성 모달 표시(불일치=warn — 표시 버그).
5a 케이스A(전체): 매핑 1건(설명+스케줄 매주·월) — 재오픈 요소별 + 속성 표시
5b 케이스B(필수만): 항목 0건 — 폴더모달 0 + 속성 '0 건' 표기
5c 되돌리기: 5a 항목 설명 비움 + 매핑 제거 → 재검증 (silent 무시 버그 클래스)
5d 마무리 cleanup: [AUTO](휘발성) 전부 삭제, 날짜본([AUTO_<MMDD>]) 보존
속성 모달 = div#detailSecureZoneTemplate (SD/특수폴더와 id 공유 — 행 가운데 셀 더블클릭).
"""
from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase

_FULL = "[AUTO]_sz_sync_l5"
_MIN  = "[AUTO]_sz_sync_l5min"
_ITEM = "sync_l5_item"
_DESC = "sync_l5_desc"


class TestSecureZoneTemplateSyncFolderScenario5Lifecycle(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — 시나리오 5: lifecycle."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ── 5a: 케이스A 전체 — 저장 → 재오픈 요소별 + 속성 표시 ─────────
    def test_scenario5a_full_case_lifecycle(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc5a: 케이스A(전체) lifecycle ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(_FULL)
        page.open_folder_modal(_FULL)
        if not page.folder_row_values(_ITEM):
            page.open_content_add()
            page.fill(page.SEL_C_NAME, _ITEM)
            page.pick_path("source", 0)
            page.pick_path("target", 1)
            page.set_schedule_type("WEEKS")
            page.page.locator("input#checkMon").first.evaluate(
                "el => { if (!el.checked) el.click(); }")
            page.fill(page.SEL_C_DESC, _DESC)
            page.content_add_message()
        # ① 재오픈 — 요소별 round-trip
        page.open_folder_item_edit(_ITEM)
        checks = {
            "설정명":   page.page.locator(page.SEL_C_NAME).first.input_value() == _ITEM,
            "설명":     page.page.locator(page.SEL_C_DESC).first.input_value() == _DESC,
            "스케줄(매주)": page.page.locator(page.SEL_C_SCHEDULE).first.evaluate("el => el.value") == "WEEKS",
            "요일(월)":  page.page.locator("input#checkMon").first.is_checked(),
            "원본위치":  "[/DESKTOP/]" in (page.page.locator(page.SEL_C_SOURCE).first.inner_text() or ""),
        }
        page.close_content_modal()
        page.close_folder_modal()
        for label, ok in checks.items():
            self._add("pass" if ok else "fail",
                      f"sc5a — 재오픈 round-trip: {label}",
                      f"결과: 유지={ok}", sc=5,
                      repro=f"1. 항목 저장(전체 필드)\n2. 재오픈\n3. {label} 유지 확인")
        # ② 속성 모달 표시 — 항목/카운트
        try:
            page.open_detail_modal(_FULL)
            dtext = page.detail_modal_text()
            shown_item = _ITEM in dtext
            self._add("pass" if shown_item else "warn",
                      "sc5a — 속성 모달 표시: 항목 설정명",
                      f"입력: 속성 열람 / 결과: {_ITEM!r} 표시={shown_item} "
                      "(재오픈은 유지 — 불일치면 표시 버그)", sc=5)
            page.close_detail_modal()
        except Exception as e:
            self._add("warn", "sc5a — 속성 모달 표시 검증", f"예외: {e!r}", sc=5)

    # ── 5b: 케이스B 필수만 — 항목 0건 표기 ──────────────────────────
    def test_scenario5b_minimal_case(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc5b: 케이스B(필수만) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        if _MIN in page.get_template_names():   # 재실행 잔존 가드(정상 흐름 미발동)
            page.delete_template(_MIN)
            page.navigate_to()
        page.create_template(_MIN)
        page.navigate_to()
        page.open_folder_modal(_MIN)
        cnt = page.folder_item_count()
        page.close_folder_modal()
        detail_zero = None
        try:
            page.open_detail_modal(_MIN)
            dtext = page.detail_modal_text()
            detail_zero = ("0" in dtext)
            page.close_detail_modal()
        except Exception:
            pass
        ok = cnt == 0
        self._add("pass" if ok else "fail",
                  "sc5b — 필수만 생성 → 항목 0건(폴더모달) + 속성 0 표기",
                  f"입력: 이름만 저장 / 결과: 폴더모달={cnt}건, 속성 0 표기={detail_zero}", sc=5,
                  repro="1. 이름만으로 생성\n2. 폴더 추가/제거 0건\n3. 속성 '0 건' 표기")

    # ── 5c: 되돌리기 — 설명 비움 + 매핑 제거 → 재검증 ───────────────
    def test_scenario5c_strip_then_verify(self, logged_in_page, settings):
        """5a 를 수정으로 되돌림: 설명 값→비움(silent 무시 버그 클래스) + 매핑 제거 → 재검증."""
        print("\n━━ [폴더동기화] sc5c: 되돌리기(설명 비움 + 매핑 제거) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(_FULL)
        page.open_folder_modal(_FULL)
        if not page.folder_row_values(_ITEM):
            page.open_content_add()
            page.fill(page.SEL_C_NAME, _ITEM)
            page.pick_path("source", 0)
            page.pick_path("target", 1)
            page.fill(page.SEL_C_DESC, _DESC)
            page.content_add_message()
        self._ckpt()

        def _strip_desc():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            page.open_folder_modal(_FULL)
            page.open_folder_item_edit(_ITEM)
            page.fill(page.SEL_C_DESC, "")
        self._act(f"항목 '{_ITEM}' 재오픈 — 설명 비움", _strip_desc,
                  shot_target=page.page.locator(page.SEL_C_DESC).first)
        self._act("수정 저장(경고 없어야 정상)",
                  lambda: page.content_save_message())
        self._act("재오픈 — 설명 잔존 여부 확인",
                  lambda: page.open_folder_item_edit(_ITEM),
                  shot_target=page.page.locator(page.SEL_C_DESC).first)
        desc_after = page.page.locator(page.SEL_C_DESC).first.input_value()
        page.close_content_modal()
        cleared = desc_after.strip() == ""
        self._add("pass" if cleared else "fail",
                  "sc5c — 설명 값→비움 수정 반영(silent 무시 버그 클래스)",
                  f"입력: 설명 비우고 수정 / 결과: 재오픈={desc_after!r} "
                  + ("(정상 반영)" if cleared else "— 빈값 수정이 조용히 무시됨"), sc=5,
                  repro="1. 항목 설명 전체 지움\n2. 수정(경고 없음)\n3. 재오픈 → 빈값이어야")
        # 매핑 제거 → 0건 확인
        msg = page.remove_folder_item(0)
        cnt = page.folder_item_count()
        page.close_folder_modal()
        self._add("pass" if cnt == 0 else "fail",
                  "sc5c — 매핑 제거 → 등록 0건",
                  f"입력: 항목 제거 / 결과: 확인메시지={msg!r}, 잔여={cnt}건", sc=5)

    # ── 5d: 마무리 cleanup — 휘발성 [AUTO] 만 삭제 ──────────────────
    def test_scenario5d_final_cleanup(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc5d: 마무리 cleanup(휘발성 [AUTO]) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.delete_all_auto()
        leftover = [n for n in page.get_template_names() if n.startswith("[AUTO]")]
        self._add("pass" if not leftover else "warn",
                  "sc5d — [AUTO] 휘발성 일괄 삭제(cleanup, 날짜본 보존)",
                  f"결과: 잔여 {len(leftover)}건" + (f" — {leftover}" if leftover else ""), sc=5,
                  repro="1. sc5 종료 시 [AUTO]_ 전부 삭제\n2. [AUTO_<날짜>] 보존")
