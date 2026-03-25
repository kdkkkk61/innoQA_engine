"""
pytest 전역 fixture
- settings.yaml 로드 (URL, 브라우저 설정, selector)
- 계정 정보: pytest 시작 시 터미널에서 직접 입력받음 (ID/PW)
- 브라우저/페이지 fixture 2종:
    fresh_page      → 로그인 안 된 상태 (test_login.py 전용)
    logged_in_page  → 로그인 된 상태 (나머지 기능 테스트 공용, 세션 1회)
- 테스트 실행 중 클릭 차단 오버레이 + 우측 하단 알림 배너 주입/제거
- 테스트 실패 시 자동 스크린샷 저장
"""
import getpass
import os
import sys
import pytest
import yaml
from datetime import datetime
from playwright.sync_api import sync_playwright

# ------------------------------------------------------------------
# 설정 로드
# ------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")

# pytest_configure 에서 수집한 계정 정보를 보관하는 모듈 변수
_credentials: dict = {}

# 의존성 추적: dependency(name=...) 로 명명된 테스트의 pass/fail 결과 보관
_dependency_results: dict = {}

# ------------------------------------------------------------------
# 테스트 진행 중 주입 요소 JS
# 1. 클릭 차단 오버레이 (qa-block-overlay): pointer-events:all 로 페이지 클릭 차단
# 2. 우측 하단 알림 배너 (qa-test-banner): 테스트 진행 중임을 사용자에게 알림
# ------------------------------------------------------------------
_OVERLAY_INJECT = """
(function() {
    if (!document.getElementById('qa-block-overlay')) {
        var block = document.createElement('div');
        block.id = 'qa-block-overlay';
        block.style.cssText = [
            'position: fixed',
            'top: 0',
            'left: 0',
            'width: 100%',
            'height: 100%',
            'background: rgba(0, 0, 0, 0.15)',
            'z-index: 99998',
            'pointer-events: all',
            'cursor: not-allowed'
        ].join(';');
        if (document.body) {
            document.body.appendChild(block);
        } else {
            document.addEventListener('DOMContentLoaded', function() {
                document.body.appendChild(block);
            });
        }
    }
    if (!document.getElementById('qa-test-banner')) {
        var banner = document.createElement('div');
        banner.id = 'qa-test-banner';
        banner.style.cssText = [
            'position: fixed',
            'bottom: 20px',
            'right: 20px',
            'z-index: 99999',
            'background: rgba(0, 0, 0, 0.75)',
            'color: #ffffff',
            'border-radius: 8px',
            'padding: 10px 16px',
            'font-size: 14px',
            'font-weight: bold',
            'pointer-events: none'
        ].join(';');
        banner.textContent = '\uD83D\uDD12 자동 테스트 진행 중';
        if (document.body) {
            document.body.appendChild(banner);
        } else {
            document.addEventListener('DOMContentLoaded', function() {
                document.body.appendChild(banner);
            });
        }
    }
})();
"""

_OVERLAY_REMOVE = """
(function() {
    ['qa-block-overlay', 'qa-test-banner'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.parentNode.removeChild(el);
    });
})();
"""


def _inject_overlay(page) -> None:
    try:
        page.evaluate(_OVERLAY_INJECT)
    except Exception:
        pass


def _remove_overlay(page) -> None:
    try:
        page.evaluate(_OVERLAY_REMOVE)
    except Exception:
        pass


# ------------------------------------------------------------------
# 계정 입력
# ------------------------------------------------------------------
def pytest_configure(config):
    """
    pytest 시작 직후(캡처 설정 이전) 계정 정보를 터미널에서 입력받는다.
    --collect-only / --help 등 실제 실행이 아닐 때는 스킵한다.
    커스텀 마커 dependency를 등록해 경고를 억제한다.
    """
    config.addinivalue_line(
        "markers",
        "dependency(name=None, depends=[]): 테스트 의존성 선언 — depends 목록 중 하나라도 실패하면 SKIP",
    )
    try:
        if config.option.collectonly or config.option.help:
            return
    except AttributeError:
        pass

    # 환경변수 폴백: TEST_ID / TEST_PW 설정 시 프롬프트 스킵
    # 예) set TEST_ID=admin && set TEST_PW=yourpassword
    # EXE 전환 시: 이 블록을 GUI 로그인 팝업으로 교체하면 됨
    env_id = os.environ.get("TEST_ID", "").strip()
    env_pw = os.environ.get("TEST_PW", "").strip()

    if env_id and env_pw:
        username = env_id or "admin"
        password = env_pw
        sys.stderr.write("\n" + "=" * 50 + "\n")
        sys.stderr.write(f"  환경변수 계정 사용: {username}\n")
        sys.stderr.write("=" * 50 + "\n\n")
        sys.stderr.flush()
    else:
        sys.stderr.write("\n" + "=" * 50 + "\n")
        sys.stderr.write("  매니저 로그인 계정을 입력하세요\n")
        sys.stderr.write("=" * 50 + "\n")
        sys.stderr.flush()

        # getpass는 콘솔 TTY를 직접 읽으므로 pytest의 stdin 캡처에 영향받지 않는다.
        username = getpass.getpass("ID [admin]: ", stream=sys.stderr) or "admin"
        sys.stderr.write(f"  → {username}\n")
        sys.stderr.flush()

        password = getpass.getpass("Password: ", stream=sys.stderr)

        sys.stderr.write("=" * 50 + "\n\n")

    _credentials["admin"]   = {"username": username, "password": password}
    _credentials["invalid"] = {"username": "wrong_user", "password": "wrong_pass"}


@pytest.fixture(scope="session")
def settings() -> dict:
    """settings.yaml을 딕셔너리로 반환한다. 세션 전체에서 공유."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def credentials() -> dict:
    """
    pytest_configure 에서 터미널 입력으로 수집한 계정 정보를 반환한다.
    반환 형태:
        {
            "admin":   {"username": ..., "password": ...},  ← 터미널 입력
            "invalid": {"username": ..., "password": ...},  ← 고정 오류 계정
        }
    """
    return _credentials


# ------------------------------------------------------------------
# 브라우저 fixture (session scope)
# ------------------------------------------------------------------
@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance, settings):
    browser_cfg = settings.get("browser", {})
    headless = browser_cfg.get("headless", False)
    slow_mo  = browser_cfg.get("slow_mo", 0)

    br = playwright_instance.chromium.launch(headless=headless, slow_mo=slow_mo)
    yield br
    br.close()


# ------------------------------------------------------------------
# 페이지 fixture 2종
# ------------------------------------------------------------------
@pytest.fixture(scope="function")
def fresh_page(browser, settings):
    """
    로그인 안 된 상태의 새 페이지. test_login.py 전용.
    매 테스트마다 새 컨텍스트로 격리된다.

    [세션 분리 보장]
    - test_login.py 는 이 fixture 만 사용하며 logged_in_page 를 사용하지 않는다.
    - fresh_page 는 function-scope 로 독립된 브라우저 컨텍스트(쿠키/세션 완전 분리).
    - test_logout 이 admin 로그아웃을 수행해도 logged_in_page 의 세션에 영향 없음:
      pytest 실행 순서상 test_login.py → test_ransom_detect_policy.py 순이므로
      logged_in_page(session-scope) 는 test_logout 완료 후에 생성된다.
    - 서버 단일세션 정책 대응: 이 순서가 보장되는 한 세션 충돌 없음.
    """
    timeout = settings.get("browser", {}).get("timeout", 30000)
    context = browser.new_context()
    context.set_default_timeout(timeout)
    context.add_init_script(_OVERLAY_INJECT)   # 모든 페이지 로드 시 자동 주입
    page = context.new_page()
    yield page
    _remove_overlay(page)
    context.close()


@pytest.fixture(scope="session")
def logged_in_page(browser, settings, credentials):
    """
    로그인 완료 상태의 페이지.
    로그인 이후 기능(방화벽, DLP 등)을 테스트할 때 사용한다.
    세션 전체에서 1번만 로그인하고 페이지를 공유한다.
    클릭 차단 오버레이 + 알림 배너는 로그인 완료 후 현재 페이지에 즉시 주입된다.

    비밀번호 오류 모달이 뜨면 터미널에서 비밀번호를 다시 입력받아 재시도한다.
    """
    from pages.login_page import LoginPage, LoginError

    timeout = settings.get("browser", {}).get("timeout", 30000)
    context = browser.new_context()
    context.set_default_timeout(timeout)
    context.add_init_script(_OVERLAY_INJECT)   # 모든 페이지 로드 시 자동 주입
    page = context.new_page()

    login = LoginPage(page, settings)
    login.open()

    while True:
        try:
            login.login(credentials["admin"]["username"], credentials["admin"]["password"],
                        raise_on_error=True)
            break   # 로그인 성공
        except LoginError as e:
            msg = str(e)
            sys.stderr.write(f"\n[로그인 실패] {msg}\n")
            sys.stderr.flush()
            # 계정 잠금 메시지("이후에 가능", "불가능") → 재시도 불가, 즉시 종료
            if "이후에" in msg or "불가능" in msg:
                sys.stderr.write("계정이 잠겼습니다. 잠금 해제 후 pytest를 다시 실행하세요.\n\n")
                sys.stderr.flush()
                pytest.exit(f"[계정 잠금] {msg}", returncode=1)
            # 일반 비밀번호 오류 → 재입력
            new_pw = getpass.getpass("Password (다시 입력): ", stream=sys.stderr)
            credentials["admin"]["password"] = new_pw
            _credentials["admin"]["password"] = new_pw
            login.wait_for(login.SEL_PASSWORD)  # 로그인 폼 복귀 대기

    page.wait_for_url(lambda url: "/login" not in url, timeout=timeout)
    _inject_overlay(page)   # 로그인 후 이미 로드된 페이지에 즉시 주입

    yield page

    # Teardown: 오버레이 제거 → 로그아웃 → 컨텍스트 종료
    # 로그아웃을 해야 서버 세션이 정리되며, 다음 실행에서 세션 충돌로 인한
    # "로그인 정보가 만료되었거나 접근권한이 없습니다" 모달이 발생하지 않는다.
    _remove_overlay(page)
    try:
        login.logout()
    except Exception as e:
        print(f"\n[logged_in_page 정리] 로그아웃 실패 (무시됨): {e}")
    finally:
        context.close()


# ------------------------------------------------------------------
# 의존성 체크: depends 목록 중 실패한 항목이 있으면 SKIP
# ------------------------------------------------------------------
def pytest_runtest_setup(item):
    marker = item.get_closest_marker("dependency")
    if not marker:
        return
    for dep_name in marker.kwargs.get("depends", []):
        if dep_name in _dependency_results and not _dependency_results[dep_name]:
            pytest.skip(f"의존 테스트 실패로 스킵: {dep_name}")


# ------------------------------------------------------------------
# 실패 시 자동 스크린샷 + 의존성 결과 기록
# ------------------------------------------------------------------
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    # 의존성 결과 기록: dependency(name=...) 마커가 있을 때만
    if report.when == "call":
        marker = item.get_closest_marker("dependency")
        if marker and marker.kwargs.get("name"):
            _dependency_results[marker.kwargs["name"]] = report.passed

    if report.when == "call" and report.failed:
        page = item.funcargs.get("fresh_page") or item.funcargs.get("logged_in_page")
        if page is None:
            return
        screenshots_dir = os.path.join("reports", "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_name = item.name.replace(" ", "_")
        path = os.path.join(screenshots_dir, f"FAIL_{test_name}_{timestamp}.png")
        try:
            page.screenshot(path=path, full_page=True)
            print(f"\n[스크린샷 저장] {path}")
        except Exception as e:
            print(f"\n[스크린샷 저장 실패] {e}")
