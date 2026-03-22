import os
from datetime import datetime
from playwright.sync_api import Page


class BasePage:
    def __init__(self, page: Page, settings: dict):
        self.page = page
        self.base_url = settings.get("base_url", "")
        self.timeout = settings.get("browser", {}).get("timeout", 30000)

    # ------------------------------------------------------------------
    # 네비게이션
    # ------------------------------------------------------------------
    def navigate(self, path: str = "") -> None:
        url = self.base_url.rstrip("/") + ("/" + path.lstrip("/") if path else "")
        try:
            self.page.goto(url, timeout=self.timeout)
        except Exception as e:
            self._on_error("navigate", e)
            raise

    # ------------------------------------------------------------------
    # 기본 액션
    # ------------------------------------------------------------------
    def click(self, selector: str) -> None:
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible", timeout=self.timeout)
            # locator.evaluate로 JS element.click() 직접 호출:
            # 좌표 기반 hit-testing을 거치지 않으므로 클릭 차단 오버레이에 영향받지 않는다.
            locator.evaluate("el => el.click()")
        except Exception as e:
            self._on_error(f"click:{selector}", e)
            raise

    def click_attached(self, selector: str) -> None:
        """
        Playwright visible 체크를 통과하지 못하지만 DOM에는 존재하는 요소를 클릭한다.
        Bootstrap 3 모달 내부 버튼처럼 hidden 판정이 나는 요소에 사용.
        attached 상태 확인 후 JS el.click() 직접 호출 → hit-testing 완전 우회.
        """
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state="attached", timeout=self.timeout)
            locator.evaluate("el => el.click()")
        except Exception as e:
            self._on_error(f"click_attached:{selector}", e)
            raise

    def fill(self, selector: str, text: str) -> None:
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible", timeout=self.timeout)
            locator.fill(text)
        except Exception as e:
            self._on_error(f"fill:{selector}", e)
            raise

    def wait_for(self, selector: str, state: str = "visible") -> None:
        try:
            self.page.locator(selector).first.wait_for(
                state=state, timeout=self.timeout
            )
        except Exception as e:
            self._on_error(f"wait_for:{selector}", e)
            raise

    def wait_for_enabled(self, selector: str) -> None:
        """요소가 활성화(enabled) 상태가 될 때까지 대기"""
        from playwright.sync_api import expect
        try:
            expect(self.page.locator(selector).first).to_be_enabled(timeout=self.timeout)
        except Exception as e:
            self._on_error(f"wait_for_enabled:{selector}", e)
            raise

    def is_visible(self, selector: str) -> bool:
        try:
            return self.page.locator(selector).first.is_visible()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 스크린샷
    # ------------------------------------------------------------------
    def take_screenshot(self, name: str) -> str:
        screenshots_dir = os.path.join("reports", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        path = os.path.join(screenshots_dir, filename)
        self.page.screenshot(path=path, full_page=True)
        return path

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _toggle_overlay(self, enabled: bool) -> None:
        """
        클릭 차단 오버레이의 pointer-events를 토글한다.
        enabled=False → 'none' (자동화 클릭 허용)
        enabled=True  → 'all'  (사람 클릭 차단 복원)
        """
        value = "all" if enabled else "none"
        self.page.evaluate(
            f"var el = document.getElementById('qa-block-overlay');"
            f"if (el) el.style.pointerEvents = '{value}';"
        )

    def _on_error(self, action: str, error: Exception) -> None:
        print(f"[BasePage] 오류 발생 — 액션: {action} | {type(error).__name__}: {error}")
        try:
            self.take_screenshot(f"error_{action.replace(':', '_')}")
        except Exception:
            pass
