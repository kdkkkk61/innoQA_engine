"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 1: UI 구조 (nPouch sc1 패턴).

요소 '없으면 fail 아니라 skip' — 빌드별 삭제(회귀)는 sc0 변경사항(삭제)이 보고, sc1은 구조 확인.
단순 존재 + behavior(서브모달 열닫 / default reset) 혼합. (Chrome MCP 직접조작 확인 2026-06-23)

sc1a — navigate + 툴바4(추가/수정/복사/삭제) + cleanup
sc1b — 리스트 컬럼 헤더(템플릿이름/시큐어드라이브정보/반출드라이브정보/등록일/수정일)
sc1c — ADD 모달 진입 + 메인 핵심필드(이름/반출4/ECM/예외/addSecureDriveBtn) + close
sc1d — ★서브모달(addSecureDrive) 진입/핵심필드/닫힘 — 이 탭 다단구조 핵심
sc1e — default reset (이름 채움→close→재오픈→빈값)
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario1Ui(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1a: navigate + 툴바 + cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)

        url_ok = ("managerSecureZoneTemplate" in page.page.url
                  and "selectedTab=SECURE_DRIVE" in page.page.url)
        self._add("pass" if url_ok else "fail",
                  "sc1a — navigate → 템플릿 관리 / 시큐어 드라이브 탭",
                  f"입력: navigate_to / 결과: url={page.page.url!r}", sc=1,
                  repro="1. 공통설정>SecureZone>템플릿 관리\n2. 시큐어 드라이브 탭")

        toolbar = {"템플릿추가": page.SEL_ADD_BTN, "수정": page.SEL_MODIFY_BTN,
                   "복사": page.SEL_COPY_BTN, "삭제": page.SEL_DELETE_BTN}
        for label, sel in toolbar.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1a — 툴바 '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)

    def test_scenario1b_list_columns(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1b: 리스트 컬럼 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = page.column_headers()
        has_name = any("이름" in h or "템플릿" in h for h in headers)
        self._add("pass" if (headers and has_name) else "warn",
                  "sc1b — 리스트 컬럼 헤더",
                  f"입력: 리스트 / 결과: 헤더={headers} (이름 컬럼 포함={has_name})", sc=1,
                  repro="1. 시큐어 드라이브 탭 리스트\n2. 컬럼 헤더 확인")

    def test_scenario1c_add_modal_fields(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1c: ADD 모달 핵심필드 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        modal_open = page.field_present(page.SEL_MODAL)
        self._add("pass" if modal_open else "fail",
                  "sc1c — ADD 모달 진입",
                  f"입력: 템플릿 추가 / 결과: modal_open={modal_open}", sc=1,
                  repro="1. 템플릿 추가 버튼\n2. 모달 열림 확인")

        fields = {
            "템플릿 이름":        f"{page.SEL_MODAL} {page.SEL_NAME}",
            "ECM드라이브 연동":    page.SEL_ECM,
            "예외 드라이브":       page.SEL_OLD_DRIVE,
            "반출 생성위치":       page.SEL_TAKEOUT_PATH,
            "반출 드라이브 문자":  page.SEL_TAKEOUT_LETTER,
            "반출 드라이브 라벨":  page.SEL_TAKEOUT_LABEL,
            "반출 드라이브 용량":  page.SEL_TAKEOUT_QUOTA,
            "시큐어드라이브 추가버튼": page.SEL_ADD_DRIVE_BTN,
        }
        for label, sel in fields.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1c — ADD 모달 '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)
        page._close_modal_if_open()

    def test_scenario1d_sub_modal(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1d: 서브모달(시큐어드라이브 항목) 진입/닫힘 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.open_sub_modal()
        sub_open = page.field_present(page.SEL_SUB)
        self._add("pass" if sub_open else "fail",
                  "sc1d — addSecureDriveBtn → 서브모달 진입",
                  f"입력: 시큐어드라이브 추가 / 결과: 서브모달 열림={sub_open}", sc=1,
                  repro="1. ADD 모달\n2. 시큐어드라이브 추가 버튼\n3. 서브모달 열림 확인")

        sub_fields = {
            "드라이브 라벨":  page.SEL_SUB_LABEL, "드라이브 문자": page.SEL_SUB_LETTER,
            "생성위치":       page.SEL_SUB_PATH,
            "용량방식 WRITE": page.SEL_SUB_QTYPE_WRITE, "용량방식 SYNC": page.SEL_SUB_QTYPE_SYNC,
        }
        for label, sel in sub_fields.items():
            present = page.field_present(sel)
            self._add("pass" if present else "skip",
                      f"sc1d — 서브모달 '{label}' 존재",
                      f"결과: present={present}"
                      + ("" if present else " (이 빌드 미존재 — sc0 변경사항 참조)"), sc=1)

        page.close_sub_modal()
        sub_closed = not page.field_present(page.SEL_SUB)
        main_still = page.field_present(page.SEL_MODAL)
        self._add("pass" if (sub_closed and main_still) else "fail",
                  "sc1d — 서브모달 '닫기' → 서브만 닫힘, 메인 유지",
                  f"입력: 서브 닫기 / 결과: 서브닫힘={sub_closed}, 메인유지={main_still}", sc=1,
                  repro="1. 서브모달 닫기\n2. 서브만 닫히고 메인 모달 유지 확인")
        page._close_modal_if_open()

    def test_scenario1e_default_reset(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1e: default reset ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        page.fill(f"{page.SEL_MODAL} {page.SEL_NAME}", "[AUTO]_probe_reset")
        page.close_modal()
        page.open_add_modal()
        name_after = page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}").first.input_value()
        reset_ok = name_after == ""
        self._add("pass" if reset_ok else "fail",
                  "sc1e — ADD 재오픈 시 이름 빈값 default reset",
                  f"입력: 이름 채움→닫기→재오픈 / 결과: 재오픈 이름={name_after!r} (기대 빈값)", sc=1,
                  highlight=page.page.locator(f"{page.SEL_MODAL} {page.SEL_NAME}"),
                  repro="1. 이름 입력\n2. 닫기\n3. 재오픈\n4. 이름 빈값 확인")
        page._close_modal_if_open()
