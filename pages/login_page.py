from pages.base_page import BasePage


class LoginError(Exception):
    """로그인 실패 시 발생 (잘못된 비밀번호, 계정 잠금 등)"""


class LoginPage(BasePage):
    # ------------------------------------------------------------------
    # Selectors — settings.yaml의 selectors.login 섹션에서 읽어온다.
    # ------------------------------------------------------------------

    # 고정 selector (제품 전용, settings.yaml 오버라이드 대상 아님)
    SEL_ERROR_MODAL_OPENED = "div#__globalMessageModal.in"   # Bootstrap 3: .in 클래스가 붙을 때 모달이 열린 상태
    SEL_MODAL_CONFIRM      = "button[data-dismiss='modal']"
    SEL_USER_DROPDOWN = "div.dropdown-toggle[data-toggle='dropdown']"
    SEL_LOGOUT        = "a#__layoutMainUserInfoLogoutBtn"

    def __init__(self, page, settings: dict):
        super().__init__(page, settings)
        yaml_selectors = settings.get("selectors", {}).get("login", {})
        self.SEL_USERNAME = yaml_selectors.get("username_input", "")
        self.SEL_PASSWORD = yaml_selectors.get("password_input", "")
        self.SEL_SUBMIT   = yaml_selectors.get("submit_button",  "")

    # ------------------------------------------------------------------
    # 페이지 조작 메서드
    # ------------------------------------------------------------------
    def open(self) -> None:
        """로그인 페이지로 이동"""
        self.navigate()

    def login(self, username: str, password: str, raise_on_error: bool = False) -> None:
        """
        username / password 로 로그인 시도.

        raise_on_error=False (기본값):
            에러 모달이 떠도 예외를 발생시키지 않는다.
            test_login.py 처럼 의도적으로 실패를 확인하는 테스트에서 사용.
            → 호출자가 is_error_visible() / close_error_modal() 로 직접 처리.

        raise_on_error=True:
            에러 모달이 뜨면 모달을 닫고 LoginError 예외를 발생시킨다.
            logged_in_page fixture에서 비밀번호 재입력 루프에 사용.
        """
        # 이전 비정상 종료로 남은 stale modal (세션 만료/충돌) 정리.
        # modal-backdrop 가 loginBtn 클릭을 가로채는 케이스 방어.
        self._dismiss_stale_modal()

        self.fill(self.SEL_USERNAME, username)
        self.fill(self.SEL_PASSWORD, password)
        self.click(self.SEL_SUBMIT)
        if raise_on_error and self.is_error_visible():
            msg = self._get_modal_message()
            self.close_error_modal()
            raise LoginError(msg)

    def _dismiss_stale_modal(self) -> None:
        """페이지 진입 직후 떠 있는 stale modal (세션 만료 등) 정리.
        modal-backdrop.in 가 loginBtn 클릭 가로채는 케이스 대응."""
        try:
            # __globalMessageModal.in (Bootstrap 3 에러 modal)
            if self.page.locator(self.SEL_ERROR_MODAL_OPENED).count() > 0:
                try:
                    self.click_attached(self.SEL_MODAL_CONFIRM)
                except Exception:
                    self.page.keyboard.press("Escape")
                # backdrop 사라질 때까지 대기
                try:
                    self.page.locator("div.modal-backdrop.in").wait_for(
                        state="detached", timeout=3000
                    )
                except Exception:
                    pass
            # backdrop 만 남고 modal 닫혀있는 경우 (orphan)
            elif self.page.locator("div.modal-backdrop.in").count() > 0:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(300)
        except Exception:
            pass

    def _get_modal_message(self) -> str:
        """에러 모달의 본문 텍스트를 반환한다."""
        try:
            return self.page.locator(
                "div#__globalMessageModal .modal-body"
            ).inner_text().strip()
        except Exception:
            return ""

    def is_error_visible(self) -> bool:
        """
        로그인 실패 모달 노출 여부 반환 (최대 5초 대기)
        Bootstrap 3은 모달 표시 시 .in 클래스를 추가한다.
        position:relative 로 인해 Playwright의 visible 체크가 실패하므로
        .in 클래스 부착(attached) 여부로 판단한다.
        """
        try:
            modal = self.page.locator(self.SEL_ERROR_MODAL_OPENED)
            modal.wait_for(state="attached", timeout=5000)
            return True
        except Exception:
            return False

    def close_error_modal(self) -> None:
        """로그인 실패 모달의 확인 버튼을 클릭해 모달을 닫는다"""
        self.click(self.SEL_MODAL_CONFIRM)

    def is_login_form_visible(self) -> bool:
        """로그인 폼(아이디 입력란) 노출 여부 반환"""
        return self.is_visible(self.SEL_USERNAME)

    def logout(self) -> None:
        """
        로그아웃 3단계:
        1. 우상단 사용자 드롭다운 열기
        2. 로그아웃 메뉴 클릭
        3. 로그인 폼이 복귀할 때까지 대기
        """
        self.click(self.SEL_USER_DROPDOWN)
        self.click(self.SEL_LOGOUT)
        self.wait_for(self.SEL_USERNAME)
