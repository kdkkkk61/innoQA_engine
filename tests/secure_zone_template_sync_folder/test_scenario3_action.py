"""시큐어존 템플릿(폴더동기화) — 시나리오 3: 동작 (특수폴더 sc3 미러 + 스케줄 타입별 저장).

★첫 저널(_ckpt/_act) 기반 신규 작성 — 각 흐름을 행위 라벨로 기술, warn/fail 검출 시
  자동 재생·단계별 캡처(tests/shared_journal). 손코딩 캡처 없음.

[생성 흐름]
sc3a — 템플릿 생성(정상) → 리스트 등장 + 타입=폴더 동기화
sc3b — 같은 이름 재생성 → '이미 등록된 이름' 차단
sc3c — 폴더 매핑 추가(예약어 picker 원본/대상, 스케줄 없음) → 커밋 + 등록 +1
sc3d — 폴더 항목 제거(-) → 확인 → 등록 -1
[★스케줄 — 이 탭 고유]
sc3e — 스케줄 타입별 저장(매분/매일/매주 — 하위필드 채워 커밋, 타입별 저널 블록)
[list-level]
sc3f — 복사 → '<이름>_copy' 생성 / sc3g — 검색 필터
[직접 입력 검증]
sc3h — 설정명 글자수 clamp(type_real 실측) / sc3i — 설명 3000자 오버플로(서버 처리 수집)
sc3j — 저장값 재오픈 대조(roundtrip: 행 표시 + 항목 편집 로드값 — 스케줄 포함)
sc3k — 경로(원본) 3000자 오버플로(특수폴더 sc3s 미러 — raw 서버 오류 클래스)

※ 삭제(리스트 단위)=sc1/sc5, 수정=sc4/sc5 (sc3=생성 기반). 메시지 미실측 항목은 수집형(추정 금지).
"""
from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase


class TestSecureZoneTemplateSyncFolderScenario3Action(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — 시나리오 3: 동작."""

    _TPL = "[AUTO]_sz_sync_a"    # 주 생성 흐름
    _RM  = "[AUTO]_sz_sync_rm"   # 제거 검증 전용

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    # ── 공용 헬퍼: '추가' 클릭 후 알림을 열린 채로 둠 — 경고 화면이 저널 재생의
    #    마지막 프레임이 되도록(내용↔사진 일치). dismiss 는 _add 뒤 별도 호출.
    @staticmethod
    def _content_add_wait_alert(page):
        btn = page.page.locator(page.SEL_CONTENT).locator("button", has_text="추가").first
        btn.evaluate("el => el.click()")
        page.page.wait_for_timeout(500)
        try:
            page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).first.wait_for(
                state="attached", timeout=2000)
        except Exception:
            pass   # 커밋 성공이면 알림 없음 — 정상

    @staticmethod
    def _dismiss_alert_if_open(page):
        if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0:
            page.click_attached(page.SEL_CONFIRM_BTN)
            page.wait_for_modal_closed()

    # ── sc3a: 템플릿 생성(정상) ─────────────────────────────────────
    def test_scenario3a_create(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3a: 템플릿 생성(정상) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        self._ckpt()

        def _fresh_create():
            page.navigate_to_clean()   # 상태 리셋(F5 — AngularJS 모달 상태 누적 정리) — 재생 가능 조건
            if self._TPL in page.get_template_names():
                page.delete_template(self._TPL)
                page.navigate_to()
            page.create_template(self._TPL)
            page.navigate_to()
        self._act(f"템플릿 '{self._TPL}' 생성(이름 입력 → 확인)", _fresh_create)
        created = self._TPL in page.get_template_names()
        self._add("pass" if created else "fail",
                  "sc3a — 폴더동기화 템플릿 생성 → 리스트 등장",
                  f"입력: 이름 저장(타입 SYNC_FOLDER 단일) / 결과: 생성={created}", sc=3,
                  repro="1. 템플릿 추가\n2. 이름 입력\n3. 확인\n4. 리스트 등장")

    # ── sc3b: 이름 중복 차단 ────────────────────────────────────────
    def test_scenario3b_duplicate_name(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3b: 이름 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        self._act(f"기존 이름 '{self._TPL}' 으로 재생성 시도",
                  lambda: (page.navigate_to_clean(), page.open_add_modal(),
                           page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._TPL)))
        msg = page.submit_and_message()
        self._add("pass" if "이미 등록된 이름" in msg else "fail",
                  "sc3b — 같은 이름 또 생성 → 중복 차단",
                  f"입력: 기존 이름 재생성 / 결과: 경고={msg!r} (기대 '이미 등록된 이름')", sc=3,
                  repro="1. 기존 이름으로 추가\n2. 확인\n3. 중복 경고")
        page._close_modal_if_open()

    # ── sc3c: 폴더 매핑 추가(picker) → 커밋 ─────────────────────────
    def test_scenario3c_folder_add_via_picker(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3c: 폴더 매핑 추가(예약어 picker) → 등록 반영 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        self._act(f"'{self._TPL}' 행 선택 → 폴더 추가/제거 모달 진입",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL)))
        before = page.folder_item_count()
        self._act("+ → 내용 모달 → 설정명 입력 + picker 원본([/DESKTOP/])·대상([/MYDOC/]) 선택",
                  lambda: (page.open_content_add(),
                           page.fill(page.SEL_C_NAME, "sync_pick"),
                           page.pick_path("source", 0), page.pick_path("target", 1)),
                  shot_target=page.page.locator(page.SEL_C_SOURCE).first)
        msg = page.content_add_message()
        after = page.folder_item_count()
        ok = (msg.strip() == "") and (after == before + 1)
        self._add("pass" if ok else "fail",
                  "sc3c — 폴더 매핑 추가(picker 원본/대상) → 등록 +1",
                  f"입력: picker 원본·대상 + 추가 / 결과: 경고={msg!r}, 등록 {before}→{after}", sc=3,
                  repro="1. 폴더 추가/제거 +\n2. 설정명 + 특수폴더 picker 원본·대상\n3. 추가\n4. 등록 증가")
        page.close_folder_modal()

    # ── sc3d: 폴더 항목 제거(-) ─────────────────────────────────────
    def test_scenario3d_folder_remove(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3d: 폴더 항목 제거(-) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._RM)
        self._ckpt()

        def _prepare_item():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            page.open_folder_modal(self._RM)
            page.open_content_add()
            page.fill(page.SEL_C_NAME, "sync_rm")
            page.pick_path("source", 0)
            page.pick_path("target", 1)
            page.content_add_message()
        self._act(f"'{self._RM}' 에 제거용 항목 1건 등록", _prepare_item)
        before = page.folder_item_count()
        msg = page.remove_folder_item(0)
        after = page.folder_item_count()
        ok = ("삭제 하시겠습니까" in msg) and (after == before - 1)
        self._add("pass" if ok else "fail",
                  "sc3d — 폴더 항목 제거(-) → 확인 → 등록 -1",
                  f"입력: 항목 체크 + 제거 / 결과: 확인메시지={msg!r}, 등록 {before}→{after}", sc=3,
                  repro="1. 폴더 항목 체크\n2. - 버튼\n3. 삭제 확인\n4. 등록 감소")
        page.close_folder_modal()

    # ── sc3e: ★스케줄 타입별 저장 (이 탭 고유) ──────────────────────
    def test_scenario3e_schedule_type_save(self, logged_in_page, settings):
        """매분/매일/매주 각각 — 하위필드를 채워 저장 커밋 확인 (타입별 저널 블록).
        하위필드 required 메시지는 미실측 → 커밋 실패 시 메시지 수집(추정 금지)."""
        print("\n━━ [폴더동기화] sc3e: 스케줄 타입별 저장 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)

        cases = [
            ("MINUTES", "sync_min",  lambda: page.fill(page.SEL_C_MINUTES, "10"),
             "분 주기=10"),
            ("DAYS",    "sync_day",  lambda: page.fill(page.SEL_C_DAYS, "1"),
             "일 주기=1 (실행 시각 기본값)"),
            ("WEEKS",   "sync_week", lambda: page.page.locator("input#checkMon").first.evaluate(
                "el => { if (!el.checked) el.click(); }"),
             "요일=월 (실행 시각 기본값)"),
        ]
        for stype, item_name, fill_sub, sub_desc in cases:
            ko = page.sched_ko(stype)
            self._ckpt()
            self._act(f"'{self._TPL}' 폴더 추가/제거 → + (내용 모달)",
                      lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                               page.open_content_add()))
            self._act(f"설정명 '{item_name}' + picker 원본/대상",
                      lambda: (page.fill(page.SEL_C_NAME, item_name),
                               page.pick_path("source", 0), page.pick_path("target", 1)))
            self._act(f"스케줄 동작 '{ko}' 선택 + 하위필드 입력({sub_desc})",
                      lambda: (page.set_schedule_type(stype), fill_sub()),
                      shot_target=page.page.locator(page.SEL_C_SCHEDULE).first)
            before = page.folder_item_count()
            self._act("추가 클릭 → 처리 결과(경고 알림/커밋)",
                      lambda: self._content_add_wait_alert(page))
            msg = (page.get_modal_message()
                   if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
            after = page.folder_item_count()
            ok = (msg.strip() == "") and (after == before + 1)
            self._add("pass" if ok else "warn",
                      f"sc3e — 스케줄 '{ko}' 저장 → 커밋",
                      f"입력: {sub_desc} + 추가 / 결과: 경고={msg!r}, 등록 {before}→{after}"
                      + ("" if ok else " (커밋 실패 — 메시지 수집)"), sc=3,
                      repro=f"1. 내용 모달 스케줄 '{ko}'\n2. {sub_desc}\n3. 추가 → 커밋")
            self._dismiss_alert_if_open(page)
            page.close_content_modal()
            page.close_folder_modal()

    # ── sc3f: 복사 ──────────────────────────────────────────────────
    def test_scenario3f_copy(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3f: 템플릿 복사 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        copy_name = f"{self._TPL}_copy"

        def _fresh_copy():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            if copy_name in page.get_template_names():
                page.delete_template(copy_name)
                page.navigate_to()
            page.copy_template(self._TPL)
            page.navigate_to()
        self._act(f"'{self._TPL}' 체크 → 복사 → 확인", _fresh_copy)
        copied = copy_name in page.get_template_names()
        self._add("pass" if copied else "fail",
                  "sc3f — 복사 → '<이름>_copy' 생성",
                  f"입력: 복사 확인 / 결과: {copy_name!r} 존재={copied}", sc=3,
                  repro="1. 행 체크\n2. 복사\n3. 확인\n4. _copy 리스트 등장")

    # ── sc3g: 검색 ──────────────────────────────────────────────────
    def test_scenario3g_search(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3g: 이름 검색 필터 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        page.search(self._TPL)
        names = page.get_template_names()
        hit = self._TPL in names and all(self._TPL in n for n in names)
        page.search("")
        self._add("pass" if hit else "fail",
                  "sc3g — 이름 검색 → 해당 템플릿만 필터",
                  f"입력: {self._TPL!r} 검색 / 결과: {len(names)}건, 전부 매칭={hit}", sc=3,
                  repro="1. 검색창 이름 입력 + Enter\n2. 매칭 행만 표시")

    # ── sc3h: 설정명 글자수 clamp (실타이핑) ────────────────────────
    def test_scenario3h_content_name_clamp(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3h: 설정명 글자수 clamp(실타이핑) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        page.open_folder_modal(self._TPL)
        page.open_content_add()
        accepted = page.type_real(page.SEL_C_NAME, "a" * 60)
        ml = page.page.locator(page.SEL_C_NAME).first.get_attribute("maxlength")
        self._add("pass",
                  "sc3h — 설정명 실타이핑 60자 → 수용 길이(clamp 실측)",
                  f"입력: 60자 타이핑 / 결과: 수용={accepted}자, maxlength={ml!r}", sc=3,
                  repro="1. 내용 모달 설정명에 60자 타이핑\n2. 실제 수용 길이 확인")
        page.close_content_modal()
        page.close_folder_modal()

    # ── sc3i: 설명 3000자 오버플로 (서버 처리 수집) ─────────────────
    def test_scenario3i_description_overflow(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3i: 설명 3000자 오버플로 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        self._act(f"'{self._TPL}' 폴더 추가/제거 → + (내용 모달)",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_content_add()))
        self._act("설정명 + picker 원본/대상 + 설명 3000자 입력",
                  lambda: (page.fill(page.SEL_C_NAME, "sync_desc_ovf"),
                           page.pick_path("source", 0), page.pick_path("target", 1),
                           page.fill(page.SEL_C_DESC, "가" * 3000)),
                  shot_target=page.page.locator(page.SEL_C_DESC).first)
        before = page.folder_item_count()
        self._act("추가 클릭 → 처리 결과(경고 알림/커밋)",
                  lambda: self._content_add_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        after = page.folder_item_count()
        committed = after == before + 1
        raw_err = ("서버" in msg and "오류" in msg)
        st = "warn" if raw_err else "pass"
        self._add(st,
                  "sc3i — 설명 3000자 + 추가 → 서버 처리(수집)",
                  f"입력: 설명 3000자 / 결과: 경고={msg!r}, 커밋={committed}"
                  + (" [raw 서버 오류 — 클라 길이 가드 부재]" if raw_err else ""), sc=3,
                  merge_key=("szsync_ovf::설명::warn::raw_server_error" if raw_err else None),
                  repro="1. 내용 모달 설명에 3000자\n2. 추가\n3. 처리 결과 확인")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()

    # ── sc3j: 저장값 재오픈 대조 (roundtrip — 스케줄 포함) ──────────
    def test_scenario3j_saved_value_roundtrip(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3j: 저장값 재오픈 대조(스케줄 포함) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        item = "sync_rt"
        self._ckpt()

        def _create_item():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            page.open_folder_modal(self._TPL)
            page.open_content_add()
            page.fill(page.SEL_C_NAME, item)
            page.pick_path("source", 0)
            page.pick_path("target", 1)
            page.set_schedule_type("WEEKS")
            page.page.locator("input#checkMon").first.evaluate(
                "el => { if (!el.checked) el.click(); }")
            page.content_add_message()
        self._act(f"항목 '{item}' 생성(매주+월요일)", _create_item)
        row = page.folder_row_values(item)
        self._act(f"항목 '{item}' 설정명 링크 → 재오픈(로드값)",
                  lambda: page.open_folder_item_edit(item))
        loaded_name = page.page.locator(page.SEL_C_NAME).first.input_value()
        loaded_sched = page.page.locator(page.SEL_C_SCHEDULE).first.evaluate("el => el.value")
        mon_checked = page.page.locator("input#checkMon").first.is_checked()
        ok = (loaded_name == item and loaded_sched == "WEEKS" and mon_checked and bool(row))
        self._add("pass" if ok else "fail",
                  "sc3j — 저장값 재오픈 대조(설정명/스케줄 매주/요일 월/행 표시)",
                  f"입력: {item!r}(매주+월) 저장 후 재오픈 / 결과: 이름={loaded_name!r}, "
                  f"스케줄={page.sched_ko(loaded_sched)!r}, 월체크={mon_checked}, 행={bool(row)}", sc=3,
                  repro="1. 항목 저장(매주+월)\n2. 설정명 링크 재오픈\n3. 로드값 대조")
        page.close_content_modal()
        page.close_folder_modal()

    # ── sc3k: 경로 3000자 오버플로 (특수폴더 sc3s 미러) ─────────────
    def test_scenario3k_path_overflow(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3k: 원본 경로 3000자 오버플로 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        self._act(f"'{self._TPL}' 폴더 추가/제거 → + (내용 모달)",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_content_add()))
        self._act("설정명 + 원본 3000자 직접입력 + 대상 picker",
                  lambda: (page.fill(page.SEL_C_NAME, "sync_path_ovf"),
                           page.set_content_path(page.SEL_C_SOURCE, "a" * 3000),
                           page.pick_path("target", 1)),
                  shot_target=page.page.locator(page.SEL_C_SOURCE).first)
        before = page.folder_item_count()
        self._act("추가 클릭 → 처리 결과(경고 알림/커밋)",
                  lambda: self._content_add_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        after = page.folder_item_count()
        committed = after == before + 1
        raw_err = ("서버" in msg and "오류" in msg)
        st = "warn" if raw_err else "pass"
        self._add(st,
                  "sc3k — 원본위치 3000자 + 추가 → 서버 처리(수집, 특수폴더 sc3s 동일 클래스)",
                  f"입력: 원본 3000자 / 결과: 경고={msg!r}, 커밋={committed}"
                  + (" [raw 서버 오류 — 클라 길이 가드 부재]" if raw_err else ""), sc=3,
                  merge_key=("szsync_ovf::원본위치::warn::raw_server_error" if raw_err else None),
                  repro="1. 내용 모달 원본위치에 3000자 직접입력\n2. 대상 picker\n3. 추가 → 처리 확인")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()
