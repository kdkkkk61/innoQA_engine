import os
from datetime import datetime
from urllib.parse import urlparse
from playwright.sync_api import Page

from pages.shared._overlay import overlay_off


class BasePage:
    def __init__(self, page: Page, settings: dict):
        self.page = page
        self.base_url = settings.get("base_url", "")
        self.timeout = settings.get("browser", {}).get("timeout", 30000)

    @property
    def host_origin(self) -> str:
        """
        base_url에서 scheme + host + port만 추출.
        예) "http://192.168.13.141/#!/"       → "http://192.168.13.141"
            "http://innotium.iptime.org:14180/" → "http://innotium.iptime.org:14180"
        split("/#!/") 하드코딩 방식 대신 urlparse로 안전하게 추출.
        """
        parsed = urlparse(self.base_url)
        return f"{parsed.scheme}://{parsed.netloc}"

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
        """
        설계: overlay 잠깐 OFF → native click → overlay ON.
        AngularJS mousedown/click 핸들러 모두 정상 동작.
        """
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible", timeout=self.timeout)
            with overlay_off(self.page):
                locator.click()
        except Exception as e:
            self._on_error(f"click:{selector}", e)
            raise

    def click_attached(self, selector: str) -> None:
        """
        Bootstrap 3 모달 내부 버튼처럼 visible 판정 안 나는 요소 클릭.
        attached 확인 후 overlay OFF + force=True 좌표 클릭.
        """
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state="attached", timeout=self.timeout)
            with overlay_off(self.page):
                locator.click(force=True)
        except Exception as e:
            self._on_error(f"click_attached:{selector}", e)
            raise

    def _click(self, locator) -> None:
        """이미 만든 locator 를 overlay OFF 컨텍스트로 클릭."""
        with overlay_off(self.page):
            locator.click()

    def _click_hidden(self, locator) -> None:
        """
        화면에 안 보이는 input (Bootstrap toggle 의 hidden checkbox 등) 클릭.
        좌표 hit-testing 불가능 → JS evaluate 직접 호출.
        AngularJS ng-click/ng-change 정상 트리거.
        """
        locator.evaluate("el => el.click()")

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

    # ------------------------------------------------------------------
    # Universal Scanner 표준 인터페이스
    # 서브클래스에서 구현 — qa_runner.py가 호출
    # ------------------------------------------------------------------

    def save_policy(self, name: str) -> None:
        """
        Phase 1/2 완료 후 정책 저장.
        서브클래스에서 반드시 override — 미구현 시 NotImplementedError.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.save_policy() 미구현. "
            "pages/base_page.py Universal Scanner 표준 인터페이스 주석 참고."
        )

    def close_edit_modal(self) -> None:
        """
        Phase 3 EDIT 모달 닫기.
        서브클래스에서 override. 기본: pass (아무것도 하지 않음).
        SEL_ADD_MODAL, SEL_ADD_BTN 등은 서브클래스에만 있으므로 BasePage에서 구현 불가.
        """
        pass

    def get_verify_values(self, saved_name: str) -> dict:
        """
        Phase 3 로드값 검증용 dict 반환.
        기본: 빈 dict (검증 생략).
        서브클래스에서 override 시 EDIT 모달 로드 후 필드값 일치 확인.
        반환 형식: {"selector": "기대값", ...}
        예: {"input#rcRdpPolicyName": saved_name}
        """
        return {}
