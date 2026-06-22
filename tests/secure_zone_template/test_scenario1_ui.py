"""시큐어존 템플릿(시큐어 드라이브) — 시나리오 1: UI 구조 + session cleanup.

sc1a — session 시작 cleanup ([AUTO] clean slate) + 리스트 툴바 버튼 존재
sc1b — 리스트 컬럼 헤더 존재
sc1c — 템플릿 추가 모달 열림/닫힘 + 시큐어드라이브 서브모달 열림/닫힘 (이 탭 핵심 구조)
"""
from pages.secure_zone_template_page import SecureZoneTemplateSecureDrivePage
from pages.shared._overlay import overlay_off
from tests.secure_zone_template._base import SecureZoneTemplateBase


class TestSecureZoneTemplateScenario1UI(SecureZoneTemplateBase):
    """시큐어존 템플릿(시큐어 드라이브) — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneTemplateSecureDrivePage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1a: 툴바 버튼 + cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)
        btns = {
            "템플릿추가": page.SEL_ADD_BTN, "수정": page.SEL_MODIFY_BTN,
            "복사": page.SEL_COPY_BTN, "삭제": page.SEL_DELETE_BTN,
        }
        missing = [k for k, sel in btns.items() if not page.is_visible(sel)]
        self._add("pass" if not missing else "fail",
                  "sc1a — 리스트 툴바 버튼 존재",
                  f"입력: 시큐어 드라이브 탭 / 결과: "
                  + ("추가/수정/복사/삭제 전부 존재" if not missing else f"누락 {missing}"),
                  sc=1, repro="1. 템플릿 관리 > 시큐어 드라이브 탭\n2. 툴바 4버튼 존재 확인")

    def test_scenario1b_list_columns(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1b: 리스트 컬럼 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        headers = [h.inner_text().strip()
                   for h in page.page.locator("table thead th").all()
                   if h.inner_text().strip()]
        has_name = any("이름" in h or "템플릿" in h for h in headers)
        self._add("pass" if (headers and has_name) else "warn",
                  "sc1b — 리스트 컬럼 헤더 존재",
                  f"입력: 리스트 / 결과: 헤더={headers} (이름 컬럼 포함={has_name})",
                  sc=1, repro="1. 시큐어 드라이브 탭 리스트\n2. 컬럼 헤더(이름 등) 존재 확인")

    def test_scenario1c_modal_open_close(self, logged_in_page, settings):
        print("\n━━ [시큐어존 템플릿/SD] 시나리오 1c: 모달/서브모달 열림닫힘 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        page.open_add_modal()
        main_open = page.page.locator(page.SEL_MODAL).count() > 0
        # 서브모달 열기
        with overlay_off(page.page):
            page.page.locator(page.SEL_ADD_DRIVE_BTN).first.click(force=True)
        try:
            page.page.locator(page.SEL_SUB).wait_for(state="attached", timeout=3000)
        except Exception:
            pass
        sub_open = page.page.locator(page.SEL_SUB).count() > 0
        page._close_sub_if_open()
        page.page.wait_for_timeout(400)
        page._close_modal_if_open()
        main_closed = page.page.locator(page.SEL_MODAL).count() == 0
        ok = main_open and sub_open and main_closed
        self._add("pass" if ok else "fail",
                  "sc1c — 추가 모달 + 시큐어드라이브 서브모달 열림/닫힘",
                  f"입력: 추가→서브 열기→닫기 / 결과: 메인열림={main_open}, 서브열림={sub_open}, 메인닫힘={main_closed}",
                  sc=1, repro="1. 템플릿 추가(메인 열림)\n2. 시큐어드라이브 추가(서브 열림)\n3. 닫기(메인 닫힘)")
