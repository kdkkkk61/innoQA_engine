"""시큐어존 템플릿(폴더동기화) — 시나리오 1: UI 구조 (특수폴더 sc1 미러).

요소 없으면 fail 아니라 skip — 빌드별 회귀는 sc0 변경사항이 보고, sc1은 구조 확인.
2단계 구조(행 선택 → 폴더 추가/제거 → 내용 모달) + 스케줄 조건부 노출이 이 탭 핵심.
(Chrome 직접조작 실측 2026-07-07)

sc1a — navigate + 툴바(추가/수정/폴더추가제거/복사/삭제) + cleanup
sc1b — 리스트 컬럼 헤더
sc1c — 1단계 ADD 모달 진입 + 핵심필드(이름/상태 CREATE·INACTIVE, 용도 분기 없음) + close
sc1d — ★2단계: 폴더 추가/제거 모달 → + → 내용 모달 핵심필드/닫힘 (최다 필드)
sc1e — ★스케줄 조건부 노출: 없음/매분/매일/매주 선택 시 실행시각·주기·요일 필드 노출 전환 (실측 매핑 대조)
sc1f — default reset (1단계 이름 채움→close→재오픈→빈값)
"""
from pages.secure_zone_template_sync_folder_page import SecureZoneTemplateSyncFolderPage
from tests.secure_zone_template_sync_folder._base import SecureZoneTemplateSyncFolderBase


class TestSecureZoneTemplateSyncFolderScenario1Ui(SecureZoneTemplateSyncFolderBase):
    """시큐어존 템플릿(폴더동기화) — 시나리오 1: UI 구조."""

    _AUTO = "[AUTO]_sz_sync_sc1"

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSyncFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/폴더동기화] 시나리오 1a: navigate + 툴바 + cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)

        url_ok = ("managerSecureZoneTemplate" in page.page.url
                  and "selectedTab=SYNC_FOLDER" in page.page.url)
        self._add("pass" if url_ok else "fail",
                  "sc1a — navigate → 템플릿 관리 / 폴더동기화 탭",
                  f"입력: navigate_to / 결과: url={page.page.url!r}", sc=1,
                  repro="1. 공통설정>SecureZone>템플릿 관리\n2. 폴더동기화 탭")

        toolbar = {"템플릿추가": page.SEL_ADD_BTN, "수정": page.SEL_MODIFY_BTN,
                   "폴더 추가/제거": page.SEL_FOLDER_ADD_DEL_BTN,
                   "복사": page.SEL_COPY_BTN, "삭제": page.SEL_DELETE_BTN}
        for label, sel in toolbar.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1a — 툴바 '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)

    def test_scenario1b_list_columns(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/폴더동기화] 시나리오 1b: 리스트 컬럼 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = page.column_headers()
        has_name = any("이름" in h or "템플릿" in h for h in headers)
        self._add("pass" if (headers and has_name) else "warn",
                  "sc1b — 리스트 컬럼 헤더",
                  f"입력: 리스트 / 결과: 헤더={headers} (이름 컬럼 포함={has_name})", sc=1,
                  repro="1. 폴더동기화 탭 리스트\n2. 컬럼 헤더 확인")

    def test_scenario1c_add_modal_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/폴더동기화] 시나리오 1c: 1단계 ADD 모달 핵심필드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        fields = {"이름(templateName)": page.SEL_NAME,
                  "상태 CREATE(활성)": page.SEL_STATUS_CREATE,
                  "상태 INACTIVE(비활성)": page.SEL_STATUS_INACTIVE}
        for label, sel in fields.items():
            present = page.field_present(sel)
            self._add("pass" if present else "fail",
                      f"sc1c — ADD 모달 필드 '{label}'",
                      f"결과: present={present}", sc=1,
                      highlight=(None if present else None))
        page.close_modal()
        closed = page.field_present(page.SEL_MODAL) is False
        self._add("pass" if closed else "warn", "sc1c — ADD 모달 닫힘",
                  f"결과: 닫힘={closed}", sc=1)

    def test_scenario1d_content_modal_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/폴더동기화] 시나리오 1d: 2단계 → 내용 모달 핵심필드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        # [AUTO] 템플릿 1개 확보 후 2단계 진입
        page.ensure_template(self._AUTO)
        page.navigate_to()
        if self._AUTO not in page.get_template_names():
            self._add("warn", "sc1d — 템플릿 생성 실패로 2단계 진입 불가", f"'{self._AUTO}' 없음", sc=1)
            return
        page.open_folder_modal(self._AUTO)
        folder_ok = page.field_present(page.SEL_FOLDER_MODAL)
        self._add("pass" if folder_ok else "fail", "sc1d — 2단계 폴더 추가/제거 모달 진입",
                  f"입력: 행 선택 → 폴더 추가/제거 / 결과: 모달={folder_ok}", sc=1,
                  repro="1. 행 선택(tActive)\n2. 폴더 추가/제거 버튼")
        if not folder_ok:
            return
        page.open_content_add()
        core = {"설정명(syncFolderName)": page.SEL_C_NAME,
                "원본위치(sourcePath)": page.SEL_C_SOURCE,
                "대상위치(destinationPath)": page.SEL_C_TARGET,
                "스케줄타입(syncFolderScheduleType)": page.SEL_C_SCHEDULE,
                "확장자목록(extensionIncludes)": page.SEL_C_EXT_LIST,
                "실시간동기화(isRealTime)": page.SEL_C_REALTIME,
                "파일용량(fileLimitSize)": page.SEL_C_FILE_LIMIT,
                "상태 활성(CREATE)": page.SEL_C_STATUS_CREATE,
                "상태 비활성(DELETE)": page.SEL_C_STATUS_DELETE}
        for label, sel in core.items():
            present = page.field_present(sel)
            self._add("pass" if present else "fail",
                      f"sc1d — 내용 모달 필드 '{label}'", f"결과: present={present}", sc=1)
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario1e_schedule_conditional(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/폴더동기화] 시나리오 1e: 스케줄 조건부 노출 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.ensure_template(self._AUTO)
        page.navigate_to()
        if self._AUTO not in page.get_template_names():
            self._add("warn", "sc1e — 템플릿 없음으로 스케줄 검증 불가", f"'{self._AUTO}' 없음", sc=1)
            return
        page.open_folder_modal(self._AUTO)
        page.open_content_add()
        # 실측 매핑(SCHEDULE_VISIBLE)대로 타입별 노출 필드 대조
        for stype, visible_fields in page.SCHEDULE_VISIBLE.items():
            page.set_schedule_type(stype)
            hidden_expected = [s for s in page.SCHEDULE_HIDDEN_ALL if s not in visible_fields]
            vis_ok = all(page.field_visible(s) for s in visible_fields)
            hid_ok = all(not page.field_visible(s) for s in hidden_expected)
            ok = vis_ok and hid_ok
            ko = page.sched_ko(stype)
            vis_ko = page.fields_ko(visible_fields)
            self._add("pass" if ok else "fail",
                      f"sc1e — 스케줄 '{ko}' 조건부 노출",
                      f"입력: 스케줄 동작 '{ko}' 선택 / "
                      f"결과: 노출기대={vis_ko or '없음'}, 노출OK={vis_ok}, 숨김OK={hid_ok}", sc=1,
                      repro=f"1. 내용 모달 → 스케줄 동작 '{ko}' 선택\n"
                            f"2. 노출돼야 할 필드: {vis_ko or '없음'}")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario1f_default_reset(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/폴더동기화] 시나리오 1f: default reset ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", self._AUTO + "_reset")
        page.close_modal()
        page.open_add_modal()
        val = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        self._add("pass" if val == "" else "fail",
                  "sc1f — ADD 모달 재오픈 시 이름 빈값(default reset)",
                  f"입력: 이름 채움→닫기→재오픈 / 결과: 이름={val!r}", sc=1,
                  repro="1. 추가 모달 이름 입력\n2. 닫기\n3. 재오픈 → 빈값이어야")
        page.close_modal()
