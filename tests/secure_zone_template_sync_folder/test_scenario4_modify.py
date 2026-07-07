"""시큐어존 템플릿(폴더동기화) — 시나리오 4: 수정 흐름 (특수폴더 sc4 미러 + 스케줄 수정).

표준(scenario_4_modify.md): 4-1 로드 / 4-2 수정 후 재확인 / 4-3 위반 저장값.
sc3 검증을 '수정 컨텍스트'로 미러 — 상태 의존 버그(생성 땐 되는데 수정 뒤 안 되는) 포착.
※ 삭제(리스트 단위)=sc1/sc5. 저널(_ckpt/_act) 기반 — 결함 가능 블록은 F5 리셋 첫 행위.

4a 템플릿 로드(4-1: 이름/상태) / 4b 상태 수정(활성→비활성) 3점 대조(입력↔리스트↔재오픈)
4c 이름 비움 위반 저장값(4-3) / 4d rename 중복 차단
4f 항목 로드+설명 update / 4g ★항목 스케줄 수정(매주→매일) roundtrip — 이 탭 고유
4h 항목 설명 3000자(수정 컨텍스트 — sc3i 미러) / 4i 내용 필수 비움(4-3)
4j 원본 3000자(수정 — sc3k EDIT 미러, merge) / 4k 항목 설정명 rename 중복
4l i18n sweep(수정) / 4m 항목 상태 수정(활성→비활성) 재오픈 대조
※ 복사/검색/필터(3f/3g/3p)는 리스트 액션 — sc3 책임 유지(미러 안 함).
"""
from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase


class TestSecureZoneTemplateSyncFolderScenario4Modify(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — 시나리오 4: 수정."""

    _TPL = "[AUTO]_sz_sync_m"      # sc4 전용 템플릿
    _ITEM = "sync_m1"              # sc4 전용 항목

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    @staticmethod
    def _content_save_wait_alert(page):
        """'수정'(없으면 '추가') 클릭 후 알림을 열린 채로 둠 — 경고 화면 = 재생 마지막 프레임."""
        loc = page.page.locator(page.SEL_CONTENT)
        btn = loc.locator("button", has_text="수정")
        if btn.count() == 0:
            btn = loc.locator("button", has_text="추가")
        btn.first.evaluate("el => el.click()")
        page.page.wait_for_timeout(500)
        try:
            page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).first.wait_for(
                state="attached", timeout=2000)
        except Exception:
            pass

    @staticmethod
    def _dismiss_alert_if_open(page):
        if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            page.click_attached(page.SEL_CONFIRM_BTN)
            page.wait_for_modal_closed()

    def _ensure_item(self, page):
        """sc4 공용 항목 확보 — self._TPL 에 self._ITEM 1건(스케줄 매주+월)."""
        page.ensure_template(self._TPL)
        page.open_folder_modal(self._TPL)
        if not page.folder_row_values(self._ITEM):
            page.open_content_add()
            page.fill(page.SEL_C_NAME, self._ITEM)
            page.pick_path("source", 0)
            page.pick_path("target", 1)
            page.set_schedule_type("WEEKS")
            page.page.locator("input#checkMon").first.evaluate(
                "el => { if (!el.checked) el.click(); }")
            page.content_add_message()

    def _row_status_text(self, page, name):
        """리스트 행에서 상태 셀 텍스트('활성'/'비활성') — 컬럼 offset 무관 td 스캔."""
        row = page._row_locator(name)
        for td in row.locator("td").all():
            t = td.inner_text().strip()
            if t in ("활성", "비활성"):
                return t
        return ""

    # ── 4a: 템플릿 로드 (4-1) ───────────────────────────────────────
    def test_scenario4a_template_load(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4a: 템플릿 수정 모달 로드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        page.ensure_template(self._TPL)
        page.open_modify_modal(self._TPL)
        name_loaded = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        create_on = page.page.locator(page.SEL_STATUS_CREATE).first.is_checked()
        ok = name_loaded == self._TPL
        self._add("pass" if ok else "fail",
                  "sc4a — 수정 모달 로드(이름/상태)",
                  f"입력: 행 선택+수정 / 결과: 이름={name_loaded!r}(일치={ok}), 활성={create_on}", sc=4,
                  repro="1. 행 선택\n2. 수정\n3. 저장값 로드 확인")
        page.close_modal()

    # ── 4b: 상태 수정 3점 대조 (4-2) ────────────────────────────────
    def test_scenario4b_status_update(self, logged_in_page, settings):
        """활성→비활성 수정 — 입력값 ↔ 리스트 상태열 ↔ 재오픈 로드 3점 대조(표시/저장 계층 분리 버그 구분)."""
        print("\n━━ [폴더동기화] sc4b: 상태 수정(활성→비활성) 3점 대조 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()

        def _to_inactive():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            page.open_modify_modal(self._TPL)
            page.page.locator(page.SEL_STATUS_INACTIVE).first.evaluate("el => el.click()")
            page.submit_and_message()
        self._act(f"'{self._TPL}' 수정 모달 — 상태 비활성 선택 + 수정 저장", _to_inactive)
        list_status = self._row_status_text(page, self._TPL)
        self._act("재오픈 — 상태 로드값 확인",
                  lambda: page.open_modify_modal(self._TPL))
        inactive_on = page.page.locator(page.SEL_STATUS_INACTIVE).first.is_checked()
        page.close_modal()
        ok = (list_status == "비활성") and inactive_on
        self._add("pass" if ok else "fail",
                  "sc4b — 상태 수정(활성→비활성) 3점 대조(입력↔리스트↔재오픈)",
                  f"입력: 비활성 저장 / 결과: 리스트={list_status!r}, 재오픈 비활성={inactive_on}", sc=4,
                  repro="1. 수정 모달 상태=비활성\n2. 수정\n3. 리스트 상태열 + 재오픈 radio 대조")
        # 원복(활성) — 후속 테스트 상태 독립성
        page.open_modify_modal(self._TPL)
        page.page.locator(page.SEL_STATUS_CREATE).first.evaluate("el => el.click()")
        page.submit_and_message()

    # ── 4c: 이름 비움 위반 저장값 (4-3) ─────────────────────────────
    def test_scenario4c_required_empty_violation(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4c: 이름 비움 위반 저장값 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        self._act(f"'{self._TPL}' 수정 모달 — 이름 비움 + 수정 시도",
                  lambda: (page.navigate_to_clean(), page.open_modify_modal(self._TPL),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "")),
                  shot_target=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first)
        msg = page.submit_and_message()
        page._close_modal_if_open()
        page.navigate_to()
        kept = self._TPL in page.get_template_names()
        ok = ("이름" in msg) and kept
        self._add("pass" if ok else "fail",
                  "sc4c — 이름 비움 + 수정 → 경고 + 원값 유지(4-3 위반 저장값)",
                  f"입력: 이름 '' + 수정 / 결과: 경고={msg!r}, 원 이름 유지={kept}", sc=4,
                  repro="1. 수정 모달 이름 전체 삭제\n2. 수정\n3. 경고 + 리스트 원 이름 유지")

    # ── 4d: rename 중복 차단 ────────────────────────────────────────
    def test_scenario4d_rename_duplicate(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4d: rename 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        other = "[AUTO]_sz_sync_m2"
        page.ensure_template(other)
        self._ckpt()
        self._act(f"'{other}' 수정 모달 — 기존 이름 '{self._TPL}' 으로 rename 시도",
                  lambda: (page.navigate_to_clean(), page.open_modify_modal(other),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._TPL)))
        msg = page.submit_and_message()
        page._close_modal_if_open()
        self._add("pass" if "이미 등록된 이름" in msg else "fail",
                  "sc4d — rename 을 기존 이름으로 → 중복 차단",
                  f"입력: '{other}'→'{self._TPL}' / 결과: 경고={msg!r}", sc=4,
                  repro="1. 수정 모달에서 기존 다른 템플릿 이름으로 변경\n2. 수정\n3. 중복 경고")

    # ── 4f: 항목 로드 + 설명 update ─────────────────────────────────
    def test_scenario4f_folder_item_load_update(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4f: 항목 로드 + 설명 수정 → 재확인 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        page.open_folder_item_edit(self._ITEM)
        name_loaded = page.page.locator(page.SEL_C_NAME).first.input_value()
        page.fill(page.SEL_C_DESC, "sync_m_desc_v2")
        page.content_save_message()
        page.open_folder_item_edit(self._ITEM)
        desc_after = page.page.locator(page.SEL_C_DESC).first.input_value()
        page.close_content_modal()
        page.close_folder_modal()
        ok = (name_loaded == self._ITEM) and (desc_after == "sync_m_desc_v2")
        self._add("pass" if ok else "fail",
                  "sc4f — 항목 로드(설정명) + 설명 수정 → 재오픈 반영",
                  f"입력: 설명='sync_m_desc_v2' 수정 / 결과: 로드 이름={name_loaded!r}, 재오픈 설명={desc_after!r}", sc=4,
                  repro="1. 항목 설정명 링크\n2. 설명 수정+저장\n3. 재오픈 값 확인")

    # ── 4g: ★항목 스케줄 수정(매주→매일) roundtrip — 이 탭 고유 ─────
    def test_scenario4g_item_schedule_update(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4g: 항목 스케줄 수정(매주→매일) roundtrip ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        self._ckpt()

        def _to_days():
            page.navigate_to_clean()   # 상태 리셋(F5)
            page.open_folder_modal(self._TPL)
            page.open_folder_item_edit(self._ITEM)
            page.set_schedule_type("DAYS")
            page.fill(page.SEL_C_DAYS, "2")
        self._act(f"항목 '{self._ITEM}' 재오픈 — 스케줄 매주→매일(일 주기=2) 변경", _to_days,
                  shot_target=page.page.locator(page.SEL_C_SCHEDULE).first)
        self._act("수정 저장", lambda: self._content_save_wait_alert(page))
        self._dismiss_alert_if_open(page)
        page.open_folder_item_edit(self._ITEM)
        sched_after = page.page.locator(page.SEL_C_SCHEDULE).first.evaluate("el => el.value")
        days_after = page.page.locator(page.SEL_C_DAYS).first.input_value()
        page.close_content_modal()
        page.close_folder_modal()
        ok = sched_after == "DAYS" and days_after == "2"
        self._add("pass" if ok else "fail",
                  "sc4g — 항목 스케줄 수정(매주→매일) → 재오픈 반영",
                  f"입력: 매일+일주기 2 저장 / 결과: 재오픈 스케줄={page.sched_ko(sched_after)!r}, 일주기={days_after!r}", sc=4,
                  repro="1. 항목 재오픈\n2. 스케줄 매일+일주기 2\n3. 수정\n4. 재오픈 값 대조")

    # ── 4h: 항목 설명 3000자 (수정 컨텍스트 — sc3i 미러) ────────────
    def test_scenario4h_item_desc_overflow_in_modify(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4h: 항목 설명 3000자(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        self._ckpt()
        self._act(f"항목 '{self._ITEM}' 재오픈 — 설명 3000자 입력",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_folder_item_edit(self._ITEM),
                           page.fill(page.SEL_C_DESC, "가" * 3000)),
                  shot_target=page.page.locator(page.SEL_C_DESC).first)
        self._act("수정 저장 → 처리 결과(경고 알림/커밋)",
                  lambda: self._content_save_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        raw_err = ("서버" in msg and "오류" in msg)
        st = "warn" if raw_err else "pass"
        self._add(st,
                  "sc4h — 항목 설명 3000자 + 수정 → 서버 처리(수집, sc3i 수정 미러)",
                  f"입력: 설명 3000자 수정 / 결과: 경고={msg!r}"
                  + (" [raw 서버 오류]" if raw_err else ""), sc=4,
                  merge_key=("szsync_ovf::설명::warn::raw_server_error" if raw_err else None),
                  repro="1. 항목 재오픈 설명 3000자\n2. 수정\n3. 처리 확인")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()

    # ── 4i: 내용 필수 비움 (4-3) ────────────────────────────────────
    def test_scenario4i_content_required_violation(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4i: 항목 설정명 비움 위반 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        self._ckpt()
        self._act(f"항목 '{self._ITEM}' 재오픈 — 설정명 비움 + 수정 시도",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_folder_item_edit(self._ITEM),
                           page.fill(page.SEL_C_NAME, "")),
                  shot_target=page.page.locator(page.SEL_C_NAME).first)
        self._act("수정 저장 → 경고 대기", lambda: self._content_save_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        kept = bool(page.folder_row_values(self._ITEM))
        page.close_folder_modal()
        ok = ("설정명" in msg) and kept
        self._add("pass" if ok else "fail",
                  "sc4i — 항목 설정명 비움 + 수정 → 경고 + 원값 유지",
                  f"입력: 설정명 '' + 수정 / 결과: 경고={msg!r}, 원 항목 유지={kept}", sc=4,
                  repro="1. 항목 설정명 비움\n2. 수정\n3. 경고 + 행 유지")

    # ── 4j: 원본 3000자 (수정 — sc3k EDIT 미러, merge) ──────────────
    def test_scenario4j_path_overflow_in_modify(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4j: 원본 3000자(수정) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        self._ckpt()
        self._act(f"항목 '{self._ITEM}' 재오픈 — 원본 3000자 직접입력",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_folder_item_edit(self._ITEM),
                           page.set_content_path(page.SEL_C_SOURCE, "a" * 3000)),
                  shot_target=page.page.locator(page.SEL_C_SOURCE).first)
        self._act("수정 저장 → 처리 결과(경고 알림/커밋)",
                  lambda: self._content_save_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        raw_err = ("서버" in msg and "오류" in msg)
        st = "warn" if raw_err else "pass"
        self._add(st,
                  "sc4j — 원본위치 3000자 + 수정 → 서버 처리(수집, sc3k EDIT 미러)",
                  f"입력: 원본 3000자 수정 / 결과: 경고={msg!r}"
                  + (" [raw 서버 오류 — 클라 길이 가드 부재]" if raw_err else ""), sc=4,
                  merge_key=("szsync_ovf::원본위치::warn::raw_server_error" if raw_err else None),
                  repro="1. 항목 재오픈 원본에 3000자\n2. 수정\n3. 처리 확인")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()

    # ── 4k: 항목 설정명 rename 중복 ─────────────────────────────────
    def test_scenario4k_item_rename_duplicate(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4k: 항목 설정명 rename 중복 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        # 두 번째 항목 확보
        if not page.folder_row_values("sync_m2i"):
            page.open_content_add()
            page.add_folder_mapping("sync_m2i", use_picker=True, src_index=2, tgt_index=3)
        self._ckpt()
        self._act(f"항목 'sync_m2i' 재오픈 — 설정명을 기존 '{self._ITEM}' 으로 rename",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_folder_item_edit("sync_m2i"),
                           page.fill(page.SEL_C_NAME, self._ITEM)),
                  shot_target=page.page.locator(page.SEL_C_NAME).first)
        self._act("수정 저장 → 경고 대기", lambda: self._content_save_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        blocked = "이미 등록" in msg
        self._add("pass" if blocked else "warn",
                  "sc4k — 항목 설정명 rename 중복 → 차단(수집)",
                  f"입력: 'sync_m2i'→'{self._ITEM}' / 결과: 경고={msg!r}", sc=4,
                  repro="1. 항목 재오픈\n2. 설정명을 기존 항목명으로\n3. 수정 → 차단 여부")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()

    # ── 4l: i18n sweep (수정 컨텍스트) ──────────────────────────────
    def test_scenario4l_i18n_sweep_in_modify(self, logged_in_page, settings):
        import re as _re
        print("\n━━ [폴더동기화] sc4l: 수정 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        _KEY = _re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")
        msgs = {}
        page.open_modify_modal(self._TPL)
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "")
        msgs["수정 이름 빈값"] = page.submit_and_message()
        page._close_modal_if_open()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc4l — 수정 검증 메시지 i18n 키 노출 전수",
                  f"결과: {msgs} / 키 누출={leaks or '없음'}", sc=4,
                  repro="1. 수정 검증 경고 유발\n2. raw i18n 키 없는지")

    # ── 4m: 항목 상태 수정(활성→비활성) 재오픈 대조 ─────────────────
    def test_scenario4m_item_status_update(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc4m: 항목 상태 수정(활성→비활성) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_item(page)
        page.open_folder_item_edit(self._ITEM)
        page.page.locator(page.SEL_C_STATUS_DELETE).first.evaluate("el => el.click()")
        page.content_save_message()
        page.open_folder_item_edit(self._ITEM)
        delete_on = page.page.locator(page.SEL_C_STATUS_DELETE).first.is_checked()
        # 원복(활성)
        page.page.locator(page.SEL_C_STATUS_CREATE).first.evaluate("el => el.click()")
        page.content_save_message()
        page.close_folder_modal()
        self._add("pass" if delete_on else "fail",
                  "sc4m — 항목 상태 수정(활성→비활성) → 재오픈 반영",
                  f"입력: 비활성 저장 / 결과: 재오픈 비활성={delete_on}", sc=4,
                  repro="1. 항목 재오픈 상태=비활성\n2. 수정\n3. 재오픈 radio 대조")
