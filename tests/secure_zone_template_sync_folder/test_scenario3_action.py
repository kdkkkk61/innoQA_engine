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
[보강 — 특수폴더 sc3 미러 대조 2026-07-07]
sc3l 이름 특수문자 / sc3m 복사 충돌(_copy 재복사) / sc3n 멀티 매핑 / sc3o i18n 전수
sc3p 리스트 필터(타입/상태) / sc3q 항목 설정명 중복 / sc3r 관리자 예약어 게이팅(수집)
sc3s 템플릿 이름 clamp / sc3t 설정명 특수문자
※ N/A(이 탭 기능 부재): 용도별 흐름(레지변경), Example/Import(폴더 모달에 버튼 없음 — 실측 2026-07-07)

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

    # ── sc3k: 3000자 오버플로 — 클래스 전수(요소별 카드) ─────────────
    def test_scenario3k_path_overflow(self, logged_in_page, settings):
        """오버플로 클래스 전수(issue-card-rules — spot-check 금지): 서버측 자유입력 3요소.
        원본/대상위치(contenteditable) + 확장자 목록(textarea, maxlength=None — sc2f 실측).
        제외(클라 clamp 실측): 설정명(30)/파일용량(30)/분주기(3). 설명(300자 서버가드)=sc3i."""
        print("\n━━ [폴더동기화] sc3k: 3000자 오버플로 전수(원본/대상/확장자) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)

        # (요소라벨, 아이템명, 채우기모드) — 모드: src=원본3000+대상picker / tgt=원본picker+대상3000
        #                                        / ext=원본·대상 picker+확장자3000
        elems = [("원본위치", "sync_ovf_src", "src", page.SEL_C_SOURCE),
                 ("대상위치", "sync_ovf_tgt", "tgt", page.SEL_C_TARGET),
                 ("확장자 목록", "sync_ovf_ext", "ext", page.SEL_C_EXT_LIST)]
        for elem, iname, mode, sel in elems:
            self._ckpt()

            def _enter(iname=iname, mode=mode):
                page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
                page.open_folder_modal(self._TPL)
                page.open_content_add()
                page.fill(page.SEL_C_NAME, iname)
                if mode == "src":
                    page.set_content_path(page.SEL_C_SOURCE, "a" * 3000)
                    page.pick_path("target", 1)
                elif mode == "tgt":
                    page.pick_path("source", 0)
                    page.set_content_path(page.SEL_C_TARGET, "a" * 3000)
                else:
                    page.pick_path("source", 0)
                    page.pick_path("target", 1)
                    page.fill(page.SEL_C_EXT_LIST, "a" * 3000)
            self._act(f"내용 모달 진입 + {elem} 3000자 입력(나머지 필수는 정상값)", _enter,
                      shot_target=page.page.locator(sel).first)
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
                      f"sc3k — {elem} 3000자 + 추가 → 서버 처리(수집, 오버플로 전수)",
                      f"입력: {elem} 3000자 / 결과: 경고={msg!r}, 커밋={committed}"
                      + (" [raw 서버 오류 — 클라 길이 가드 부재]" if raw_err else ""), sc=3,
                      merge_key=(f"szsync_ovf::{elem}::warn::raw_server_error" if raw_err else None),
                      repro=f"1. 내용 모달 {elem} 에 3000자 입력(나머지 필수 정상)\n"
                            "2. 추가\n3. 처리 결과(경고/커밋) 확인")
            self._dismiss_alert_if_open(page)
            page.close_content_modal()
            page.close_folder_modal()

    # ══ 보강 (특수폴더 sc3 미러 대조 — 2026-07-07) ═══════════════════════

    # ── sc3l: 템플릿 이름 특수문자 ──────────────────────────────────
    def test_scenario3l_special_char_name(self, logged_in_page, settings):
        """이름 특수문자 처리 — 특수폴더 실측은 '경고 없이 허용(검사 없음)'. 동일 여부 수집."""
        print("\n━━ [폴더동기화] sc3l: 이름 특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        sp = "[AUTO]_sz_sync_sp<>!@#"
        if sp in page.get_template_names():
            page.delete_template(sp); page.navigate_to()
        msg = page.create_template(sp)
        page.navigate_to()
        created = sp in page.get_template_names()
        self._add("pass" if created else "warn",
                  "sc3l — 이름 특수문자 입력(생성 시)",
                  f"입력: 이름 '{sp}' / 결과: 경고={msg!r}, 생성={created} "
                  "(특수폴더 실측: 허용 — 이름 형식 검사 없음)", sc=3,
                  repro="1. 이름에 특수문자(<>!@#)\n2. 확인\n3. 허용/차단 여부")

    # ── sc3m: 복사 충돌(_copy 존재 시 재복사) ───────────────────────
    def test_scenario3m_copy_collision(self, logged_in_page, settings):
        """특수폴더 실측: 같은 '_copy' 이름 중복 생성(복사는 중복 검사 안 함). 동일 클래스 여부."""
        print("\n━━ [폴더동기화] sc3m: 복사 충돌(_copy 존재 시 재복사) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        copy_name = self._TPL + "_copy"
        self._ckpt()

        def _ensure_copy():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            if copy_name not in page.get_template_names():
                page.copy_template(self._TPL)
                page.navigate_to()
        self._act(f"복사본 '{copy_name}' 존재 확보", _ensure_copy)
        before = page.get_template_names().count(copy_name)
        self._act("_copy 존재 상태에서 원본 재복사",
                  lambda: (page.copy_template(self._TPL), page.navigate_to()))
        after = page.get_template_names().count(copy_name)
        dup = after > before
        if dup:
            page.search(copy_name)   # 캡처에 중복 행만 보이게
        self._add("warn" if dup else "pass",
                  "sc3m — 복사 충돌(_copy 존재 시 재복사)",
                  f"입력: '{copy_name}' 존재 상태 재복사 / 결과: {before}→{after}개 "
                  + ("(중복 생성 — 복사는 중복 검사 안 함, 특수폴더 동일 결함 클래스)" if dup
                     else "(중복 차단됨)"), sc=3,
                  merge_key=("szsync_copy_dup::copy::warn::no_dup_check" if dup else None),
                  repro="1. 복사본 존재 상태\n2. 원본 재복사\n3. 같은 _copy 이름 중복 생기는지")
        page.search("")

    # ── sc3n: 멀티 폴더 매핑 추가 ───────────────────────────────────
    def test_scenario3n_multi_folder(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3n: 멀티 폴더 매핑 추가 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_sync_multi"
        page.ensure_template(tpl)
        page.open_folder_modal(tpl)
        before = page.folder_item_count()
        page.open_content_add()
        page.add_folder_mapping("multi_1", use_picker=True, src_index=0, tgt_index=1)
        page.open_content_add()
        page.add_folder_mapping("multi_2", use_picker=True, src_index=2, tgt_index=3)
        after = page.folder_item_count()
        ok = after == before + 2
        self._add("pass" if ok else "fail",
                  "sc3n — 멀티 폴더 매핑 추가 → 등록 +2",
                  f"입력: 매핑 2건 추가 / 결과: 등록 {before}→{after} (기대 +2)", sc=3,
                  repro="1. 폴더 매핑 2개 추가\n2. 등록 카운트 2 증가")
        page.close_folder_modal()

    # ── sc3o: 검증 메시지 i18n 전수 ─────────────────────────────────
    def test_scenario3o_i18n_sweep(self, logged_in_page, settings):
        """생성 검증 메시지 전수 — raw i18n 키(COLUMN.NAME 류) 노출 없는지 sweep."""
        import re as _re
        print("\n━━ [폴더동기화] sc3o: 검증 메시지 i18n 전수 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        _KEY = _re.compile(r"[A-Z]{2,}[._][A-Z_.]{2,}")
        msgs = {}
        page.open_add_modal()
        msgs["1단계 이름 빈값"] = page.submit_and_message()
        page._close_modal_if_open()
        page.ensure_template(self._TPL)
        page.open_folder_modal(self._TPL)
        page.open_content_add()
        msgs["내용 필수 빈값"] = page.content_add_message()
        page.close_content_modal()
        page.close_folder_modal()
        leaks = {k: v for k, v in msgs.items() if _KEY.search(v or "")}
        self._add("warn" if leaks else "pass",
                  "sc3o — 검증 메시지 i18n 키 노출 전수",
                  f"입력: 생성 검증 메시지 수집 / 결과: {msgs} / 키 누출={leaks or '없음'}", sc=3,
                  repro="1. 생성 검증 경고 유발\n2. raw i18n 키 노출 없는지")

    # ── sc3p: 리스트 필터(타입/상태) ────────────────────────────────
    def test_scenario3p_list_filters(self, logged_in_page, settings):
        """타입(전체/폴더 동기화)·상태(활성/비활성) 필터 — 행 텍스트 스캔으로 반영 확인
        (컬럼 인덱스 미확정이라 행 단위 lenient 대조)."""
        print("\n━━ [폴더동기화] sc3p: 리스트 필터(타입/상태) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)

        def _row_texts():
            return [r.inner_text() for r in page.page.locator(page.SEL_TABLE_ROW).all()
                    if r.inner_text().strip() and "없습니다" not in r.inner_text()]

        # 타입 필터: 옵션이 '전체/폴더 동기화' 2개뿐(단일 타입 탭) + 리스트에 타입 컬럼도 없음
        # (헤더 실측: 이름/등록경로/상태/등록일/수정일 — sc1b) → 결과가 달라질 수 없어 변별 검증 불가.
        self._add("skip",
                  "sc3p — 타입 필터 [검증 불가 — 단일 타입 탭]",
                  "결과: 옵션=전체/폴더 동기화(동일 집합), 리스트 타입 컬럼 없음 — "
                  "필터 존재는 sc1 커버, 변별 동작은 타입이 여러 개인 탭(프로세스 등)에서 검증", sc=3)
        page.filter_by(status="활성")
        rows = _row_texts()
        status_ok = all("비활성" not in t for t in rows)
        self._add("pass" if status_ok else "fail",
                  "sc3p — 상태 필터(활성) → 결과 반영",
                  f"입력: 상태=활성 + 검색 / 결과: {len(rows)}행, 비활성 없음={status_ok}", sc=3,
                  repro="1. 상태 드롭다운=활성\n2. 검색(돋보기)\n3. 활성만 표시")
        page.filter_by(status="상태")

    # ── sc3q: 폴더 항목 중복(같은 설정명) ───────────────────────────
    def test_scenario3q_folder_item_duplicate(self, logged_in_page, settings):
        """같은 설정명 재추가 — 특수폴더 실측은 '이미 등록된 이름' 차단. 동일 여부 수집."""
        print("\n━━ [폴더동기화] sc3q: 폴더 항목 중복 차단 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        tpl = "[AUTO]_sz_sync_dup"
        page.ensure_template(tpl)
        self._ckpt()

        def _base_item():
            page.navigate_to_clean()   # 상태 리셋(F5) — 재생 가능 조건
            page.open_folder_modal(tpl)
            if not page.folder_row_values("dup1"):
                page.open_content_add()
                page.add_folder_mapping("dup1", use_picker=True, src_index=0, tgt_index=1)
        self._act("기준 항목 'dup1' 확보", _base_item)
        self._act("같은 설정명 'dup1' 재추가 입력(picker 원본/대상)",
                  lambda: (page.open_content_add(),
                           page.fill(page.SEL_C_NAME, "dup1"),
                           page.pick_path("source", 0), page.pick_path("target", 1)),
                  shot_target=page.page.locator(page.SEL_C_NAME).first)
        self._act("추가 클릭 → 처리 결과(중복 차단 기대)",
                  lambda: self._content_add_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        blocked = "이미 등록" in msg
        self._add("pass" if blocked else "warn",
                  "sc3q — 폴더 항목 중복(같은 설정명) → 차단",
                  f"입력: 'dup1' 재추가 / 결과: 경고={msg!r} "
                  + ("" if blocked else "(차단 안 됨 — 중복 허용 여부 수집)"), sc=3,
                  repro="1. 항목 dup1 추가\n2. 같은 설정명 재추가\n3. 중복 차단 여부")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()

    # ── sc3r: 관리자 예약어 게이팅 존재 여부(수집) ───────────────────
    def test_scenario3r_admin_reserved_word(self, logged_in_page, settings):
        """원본에 관리자 예약어([/RUN/]) 직접입력 → 추가 — 특수폴더(레지변경)는 비밀번호 인증
        게이팅. 폴더동기화 탭의 동작은 미실측 → 수집(차단/허용/오류). 비번 입력은 안 함(안전규칙)."""
        print("\n━━ [폴더동기화] sc3r: 관리자 예약어 게이팅(수집) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        self._ckpt()
        self._act(f"'{self._TPL}' 폴더 추가/제거 → + (내용 모달)",
                  lambda: (page.navigate_to_clean(), page.open_folder_modal(self._TPL),
                           page.open_content_add()))
        self._act("설정명 + 원본에 관리자 예약어 [/RUN/] 직접입력 + 대상 picker",
                  lambda: (page.fill(page.SEL_C_NAME, "sync_admin_rw"),
                           page.set_content_path(page.SEL_C_SOURCE, "[/RUN/]"),
                           page.pick_path("target", 1)),
                  shot_target=page.page.locator(page.SEL_C_SOURCE).first)
        before = page.folder_item_count()
        self._act("추가 클릭 → 처리 결과(게이팅/허용/오류)",
                  lambda: self._content_add_wait_alert(page))
        msg = (page.get_modal_message()
               if page.page.locator(page.SEL_CONFIRM_MODAL_OPENED).count() > 0 else "")
        after = page.folder_item_count()
        committed = after == before + 1
        gated = "관리자" in msg or "비밀번호" in msg or "인증" in msg
        raw_err = ("서버" in msg and "오류" in msg)
        st = "warn" if raw_err else "pass"
        self._add(st,
                  "sc3r — 관리자 예약어([/RUN/]) 입력 → 처리(수집)",
                  f"입력: 원본=[/RUN/] + 추가 / 결과: 경고={msg!r}, 커밋={committed}, "
                  f"인증 게이팅={gated} (인증/암호화는 user-driven — 테스트 제외)", sc=3,
                  repro="1. 원본위치에 [/RUN/] 직접입력\n2. 추가\n3. 게이팅/허용/오류 확인")
        self._dismiss_alert_if_open(page)
        page.close_content_modal()
        page.close_folder_modal()

    # ── sc3s: 템플릿 이름 글자수 clamp (실타이핑) ───────────────────
    def test_scenario3s_template_name_clamp(self, logged_in_page, settings):
        print("\n━━ [폴더동기화] sc3s: 템플릿 이름 clamp(실타이핑) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        accepted = page.type_real(f"{page.SEL_MODAL} {page.SEL_NAME}", "a" * 60)
        ml = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.get_attribute("maxlength")
        self._add("pass",
                  "sc3s — 템플릿 이름 실타이핑 60자 → 수용 길이(clamp 실측)",
                  f"입력: 60자 타이핑 / 결과: 수용={accepted}자, maxlength={ml!r}", sc=3,
                  repro="1. 1단계 이름에 60자 타이핑\n2. 실제 수용 길이 확인")
        page._close_modal_if_open()

    # ── sc3t: 설정명 특수문자 ───────────────────────────────────────
    def test_scenario3t_content_name_special_char(self, logged_in_page, settings):
        """설정명 특수문자 — 허용/차단 수집(특수폴더 미러 전수 대조)."""
        print("\n━━ [폴더동기화] sc3t: 설정명 특수문자 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._TPL)
        page.open_folder_modal(self._TPL)
        page.open_content_add()
        sp_name = "sync_sp<>!@#"
        msg = page.add_folder_mapping(sp_name, use_picker=True, src_index=0, tgt_index=1)
        created = bool(page.folder_row_values(sp_name))
        self._add("pass" if (created or msg) else "warn",
                  "sc3t — 설정명 특수문자 입력",
                  f"입력: 설정명 '{sp_name}' / 결과: 경고={msg!r}, 등록={created} "
                  "(허용/차단 실측 수집)", sc=3,
                  repro="1. 설정명에 특수문자\n2. 추가\n3. 허용/차단 여부")
        page.close_content_modal()
        page.close_folder_modal()
