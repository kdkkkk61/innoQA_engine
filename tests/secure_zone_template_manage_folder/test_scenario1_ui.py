"""시큐어존 템플릿(특수폴더) — 시나리오 1: UI 구조 (nPouch sc1 패턴).

요소 '없으면 fail 아니라 skip' — 빌드별 삭제(회귀)는 sc0 변경사항이 보고, sc1은 구조 확인.
2단계 구조(행 선택 → 폴더 추가/제거 → 용도별 내용 모달)가 이 탭 핵심. (Chrome MCP 직접조작 2026-06-30)

sc1a — navigate + 툴바(추가/수정/폴더추가제거/복사/삭제) + cleanup
sc1b — 리스트 컬럼 헤더(템플릿이름/용도/등록된경로/상태/등록일/수정일)
sc1c — 1단계 ADD 모달 진입 + 핵심필드(이름/용도 SHORTCUT·REGIST/상태 CREATE·DELETE) + close
sc1d — ★2단계: 폴더 추가/제거 모달 → + → 바로가기(SHORTCUT) 내용 모달 핵심필드/닫힘 — 이 탭 핵심
sc1e — ★레지스트리(MODIFY_REGIST) 내용 모달 — 바로가기와 '따로': 다른 모달 id + 전용 숨김필드(인증) 존재(구조 차이)
sc1f — default reset (1단계 이름 채움→close→재오픈→빈값)
※ 바로가기/레지스트리는 보이는 필드는 같아도 동일 아님 — 레지스트리 전용 동작(관리자 예약어 게이팅·암호화)은 sc3.
"""
from pages.secure_zone_template_manage_folder_page import SecureZoneTemplateManageFolderPage
from tests.secure_zone_template_manage_folder._base import SecureZoneTemplateManageFolderBase


class TestSecureZoneTemplateManageFolderScenario1Ui(SecureZoneTemplateManageFolderBase):
    """시큐어존 템플릿(특수폴더) — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateManageFolderPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/특수폴더] 시나리오 1a: navigate + 툴바 + cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)

        url_ok = ("managerSecureZoneTemplate" in page.page.url
                  and "selectedTab=MANAGE_FOLDER" in page.page.url)
        self._add("pass" if url_ok else "fail",
                  "sc1a — navigate → 템플릿 관리 / 특수폴더 탭",
                  f"입력: navigate_to / 결과: url={page.page.url!r}", sc=1,
                  repro="1. 공통설정>SecureZone>템플릿 관리\n2. 특수폴더 탭")

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
        print("\n━━ [시큐어존 템플릿/특수폴더] 시나리오 1b: 리스트 컬럼 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = page.column_headers()
        has_name = any("이름" in h or "템플릿" in h for h in headers)
        self._add("pass" if (headers and has_name) else "warn",
                  "sc1b — 리스트 컬럼 헤더",
                  f"입력: 리스트 / 결과: 헤더={headers} (이름 컬럼 포함={has_name})", sc=1,
                  repro="1. 특수폴더 탭 리스트\n2. 컬럼 헤더 확인")

    def test_scenario1c_add_modal_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/특수폴더] 시나리오 1c: 1단계 ADD 모달 핵심필드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        modal_open = page.field_present(page.SEL_MODAL)
        self._add("pass" if modal_open else "fail",
                  "sc1c — 1단계 ADD 모달 진입",
                  f"입력: 템플릿 추가 / 결과: modal_open={modal_open}", sc=1,
                  repro="1. 템플릿 추가 버튼\n2. 모달 열림 확인")

        fields = {
            "템플릿 이름":        f"{page.SEL_MODAL} {page.SEL_NAME}",
            "용도 바로가기(SHORTCUT)": page.SEL_TYPE_SHORTCUT,
            "용도 레지스트리(MODIFY_REGIST)": page.SEL_TYPE_REGIST,
            "상태 활성(CREATE)":   page.SEL_STATUS_CREATE,
            "상태 비활성(DELETE)": page.SEL_STATUS_DELETE,
        }
        for label, sel in fields.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1c — 1단계 모달 '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)
        page._close_modal_if_open()

    def test_scenario1d_folder_content_modal(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/특수폴더] 시나리오 1d: 2단계 폴더/내용 모달 진입·필드·닫힘 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = "[AUTO]_sz_mf_uichk"
        page.ensure_template(name, "SHORTCUT")   # 2단계는 템플릿 존재 전제

        page.open_folder_modal(name)
        folder_open = page.field_present(page.SEL_FOLDER_MODAL)
        self._add("pass" if folder_open else "fail",
                  "sc1d — 행 선택 → 폴더 추가/제거 모달 진입",
                  f"입력: 행 선택+폴더 추가/제거 / 결과: 폴더모달 열림={folder_open}", sc=1,
                  repro="1. 템플릿 행 선택\n2. 폴더 추가/제거 버튼\n3. 폴더모달 열림 확인")

        # 폴더모달 툴바(+/-)
        for label, sel in {"항목추가(+)": page.SEL_FOLDER_ADD_ITEM,
                           "항목제거(-)": page.SEL_FOLDER_DEL_ITEM}.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1d — 폴더모달 '{label}' 존재",
                      f"결과: present={present}", sc=1)

        # + → 용도별 내용 모달(SHORTCUT)
        page.open_content_add()
        ctype = page.content_modal_id()
        self._add("pass" if ctype == "SHORTCUT" else "warn",
                  "sc1d — '+' → 용도별 내용 모달(바로가기=SHORTCUT) 진입",
                  f"입력: 폴더모달 + / 결과: 내용모달 종류={ctype!r} (기대 SHORTCUT)", sc=1,
                  repro="1. 폴더모달 +\n2. 바로가기 템플릿이면 시큐어존 바로가기 추가 모달")

        content_fields = {
            "설정명":   page.SEL_C_NAME,
            "원본위치": page.SEL_C_SOURCE,
            "대상위치": page.SEL_C_TARGET,
            "설명":     page.SEL_C_DESC,
        }
        for label, sel in content_fields.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1d — 내용모달 '{label}' 존재",
                      f"결과: present={present}", sc=1)

        page.close_content_modal()
        content_closed = not page.field_present(page.SEL_CONTENT_ANY)
        folder_still = page.field_present(page.SEL_FOLDER_MODAL)
        self._add("pass" if (content_closed and folder_still) else "warn",
                  "sc1d — 내용모달 '닫기' → 내용만 닫힘, 폴더모달 유지",
                  f"입력: 내용 닫기 / 결과: 내용닫힘={content_closed}, 폴더모달유지={folder_still}", sc=1,
                  repro="1. 내용모달 닫기\n2. 내용만 닫히고 폴더모달 유지 확인")
        page.close_folder_modal()

    def test_scenario1e_regist_content_modal(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/특수폴더] 시나리오 1e: 레지스트리 내용 모달(바로가기와 따로) ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        name = "[AUTO]_sz_mf_reg_uichk"
        page.ensure_template(name, "MODIFY_REGIST")   # 레지스트리 용도 템플릿
        page.open_folder_modal(name)
        page.open_content_add()
        ctype = page.content_modal_id()
        self._add("pass" if ctype == "MODIFY_REGIST" else "fail",
                  "sc1e — 레지스트리 용도 → 레지스트리 내용 모달(addModifySecureZoneModifyRegist) 진입",
                  f"입력: 레지스트리 템플릿 +폴더 / 결과: 내용모달 종류={ctype!r} (기대 MODIFY_REGIST, 바로가기와 다른 모달)", sc=1,
                  repro="1. 레지스트리 템플릿 행 선택\n2. 폴더 추가/제거 +\n3. '레지스트리 변경 등록' 모달(바로가기와 다른 id) 확인")
        # 공통 필드 (바로가기와 동일)
        for label, sel in {"설정명": page.SEL_C_NAME, "원본위치": page.SEL_C_SOURCE,
                           "대상위치": page.SEL_C_TARGET, "설명": page.SEL_C_DESC}.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1e — 레지스트리 내용 '{label}'(공통) 존재", f"결과: present={present}", sc=1)
        # ★레지스트리 전용 필드 (바로가기엔 없음) — 기본 숨김이나 DOM 존재로 '동일 아님' 구조 확인
        for label, sel in {"실행설명(descriptionRun)": page.SEL_C_DESC_RUN,
                           "실행비밀번호(runPassword)": page.SEL_C_RUN_PW,
                           "라이센스/관리자비번(licensePwd)": page.SEL_C_LICENSE_PW}.items():
            present = page.field_present(sel)
            self._add("pass" if present else "warn",
                      f"sc1e — ★레지스트리 전용 '{label}' 존재(바로가기엔 없음)",
                      f"결과: present={present} (구조상 바로가기≠레지스트리 — 전용 인증/암호화 필드)", sc=1,
                      repro="1. 레지스트리 내용 모달\n2. 바로가기엔 없는 전용 인증 필드 존재 확인")
        page.close_content_modal()
        page.close_folder_modal()

    def test_scenario1f_default_reset(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/특수폴더] 시나리오 1f: default reset ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "[AUTO]_probe_reset")
        page.close_modal()
        page.open_add_modal()
        name_after = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        reset_ok = name_after == ""
        self._add("pass" if reset_ok else "fail",
                  "sc1e — 1단계 ADD 재오픈 시 이름 빈값 default reset",
                  f"입력: 이름 채움→닫기→재오픈 / 결과: 재오픈 이름={name_after!r} (기대 빈값)", sc=1,
                  highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 이름 입력\n2. 닫기\n3. 재오픈\n4. 이름 빈값 확인")
        page._close_modal_if_open()
