"""시큐어존 접근제어 정책 — 시나리오 1: UI 구조 + session cleanup.

sc1a — session 시작 cleanup ([AUTO] clean slate) + 리스트 툴바 버튼 존재
sc1b — 리스트 컬럼 헤더 존재
sc1c — 정책추가 모달 열림/닫힘
"""
from pages.secure_zone_access_control_policy_page import SecureZoneAccessControlPolicyPage
from tests.secure_zone._base import SecureZoneACBase


class TestSecureZoneAccessControlScenario1UI(SecureZoneACBase):
    """접근제어 정책 — 시나리오 1: UI 구조."""

    def _new_page(self, logged_in_page, settings):
        page = SecureZoneAccessControlPolicyPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario1a_toolbar_buttons(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 1a: 툴바 버튼 + cleanup ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()
        self._ensure_session_cleanup(page)   # clean slate (1회)

        buttons = [
            ("정책추가",      "button#addItem"),
            ("정책 할당/회수", "button#addRemoveItemUserBtn"),
            ("수정",          "button#modifyItem"),
            ("삭제",          "button#removeItem"),
        ]
        for label, sel in buttons:
            present = page.page.locator(sel).count() > 0
            self._add("pass" if present else "fail",
                      f"sc1a — 툴바 '{label}' 존재",
                      f"selector='{sel}' / present={present}", sc=1)

    def test_scenario1b_list_columns(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 1b: 리스트 컬럼 헤더 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        expected = ["정책이름", "접근제어 사용", "명령프롬프트(CMD) 사용",
                    "Regedit 사용", "등록일", "수정일"]
        headers = [th.inner_text().strip()
                   for th in page.page.locator("table thead th").all()
                   if th.inner_text().strip()]
        for col in expected:
            self._add("pass" if col in headers else "fail",
                      f"sc1b — 컬럼 '{col}' 존재",
                      f"실제 헤더={headers}", sc=1)

    def test_scenario1c_modal_open_close(self, logged_in_page, settings):
        print("\n━━ [접근제어 정책] 시나리오 1c: 모달 열림/닫힘 ━━━")
        page = self._new_page(logged_in_page, settings)
        page.navigate_to()

        page.open_add_modal()
        opened = page.page.locator(page.SEL_MODAL).count() > 0
        self._add("pass" if opened else "fail",
                  "sc1c — 정책추가 모달 열림",
                  f"modal('{page.SEL_MODAL}') count={page.page.locator(page.SEL_MODAL).count()}",
                  sc=1)

        page._close_modal_if_open()
        closed = page.page.locator(page.SEL_MODAL).count() == 0
        self._add("pass" if closed else "fail",
                  "sc1c — 모달 닫힘",
                  f"닫은 후 modal count={page.page.locator(page.SEL_MODAL).count()}", sc=1)
