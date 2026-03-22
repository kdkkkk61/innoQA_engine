"""
로그인 관련 테스트 케이스
- 하나의 테스트 함수 = 하나의 시나리오
- Page 객체만 사용, Playwright page를 직접 조작하지 않는다
- 로그인 기능 자체를 테스트하므로 fresh_page fixture 사용
"""
from pages.login_page import LoginPage


class TestLogin:
    def test_login_success(self, fresh_page, settings, credentials):
        """정상 계정으로 로그인 후 /login 경로에서 벗어나는지 확인"""
        login_page = LoginPage(fresh_page, settings)
        login_page.open()

        login_page.login(
            credentials["admin"]["username"],
            credentials["admin"]["password"],
        )

        assert "/login" not in fresh_page.url, (
            f"로그인 성공 후에도 URL에 /login이 포함되어 있음: {fresh_page.url}"
        )

    def test_login_failure(self, fresh_page, settings, credentials):
        """잘못된 계정으로 로그인 시 에러 모달이 표시되고 닫히는지 확인"""
        login_page = LoginPage(fresh_page, settings)
        login_page.open()

        login_page.login(
            credentials["invalid"]["username"],
            credentials["invalid"]["password"],
        )

        assert login_page.is_error_visible(), "로그인 실패 시 에러 모달이 표시되지 않음"

        login_page.close_error_modal()

        assert not login_page.is_error_visible(), "확인 버튼 클릭 후 에러 모달이 닫히지 않음"

    def test_logout(self, fresh_page, settings, credentials):
        """정상 로그인 후 로그아웃 시 로그인 폼이 다시 표시되는지 확인"""
        login_page = LoginPage(fresh_page, settings)
        login_page.open()

        login_page.login(
            credentials["admin"]["username"],
            credentials["admin"]["password"],
        )

        timeout = settings.get("browser", {}).get("timeout", 30000)
        fresh_page.wait_for_url(lambda url: "/login" not in url, timeout=timeout)

        login_page.logout()

        assert login_page.is_login_form_visible(), "로그아웃 후 로그인 폼이 표시되지 않음"
