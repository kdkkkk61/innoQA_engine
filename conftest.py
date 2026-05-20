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
import io
import os
import shutil
import sys
import pytest

# Windows CP949 환경에서 UnicodeEncodeError 방지
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer") and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


class _TeeOutput:
    """stdout/stderr 를 터미널 + 파일에 동시 출력."""
    def __init__(self, original, file_obj):
        self._orig = original
        self._file = file_obj

    def write(self, data):
        self._orig.write(data)
        self._orig.flush()          # 파이프 버퍼 즉시 flush → 실시간 출력 보장
        try:
            self._file.write(data)
            self._file.flush()
        except Exception:
            pass

    def flush(self):
        self._orig.flush()
        try:
            self._file.flush()
        except Exception:
            pass

    def fileno(self):
        return self._orig.fileno()

    def isatty(self):
        return getattr(self._orig, "isatty", lambda: False)()

    @property
    def encoding(self):
        return "utf-8"

    @property
    def errors(self):
        return "replace"

    @property
    def closed(self):
        return False
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

# HTML 리포트용 — (page_id, PageScanReport) 수집 버퍼
_scan_reports: list = []

def _extract_fail_msg(report) -> str:
    """pytest report에서 AssertionError 메시지만 추출 (최대 200자)."""
    try:
        text = str(report.longrepr)
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            # "E   AssertionError: ..." 형태
            if "AssertionError:" in line:
                return line.split("AssertionError:", 1)[-1].strip()[:200]
            # "E   playwright..." 등 마지막 의미있는 줄
            if line.startswith("E "):
                return line[2:].strip()[:200]
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return lines[-1][:200] if lines else "실패"
    except Exception:
        return "실패"

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

    # ── 로그 파일 자동 저장 설정 ──────────────────────────────────────
    from pathlib import Path
    from datetime import datetime as _dt

    runs_dir = Path("reports/runs")
    runs_dir.mkdir(parents=True, exist_ok=True)

    # -k 필터값을 파일명에 포함 (없으면 "all")
    try:
        k_filter = (config.getoption("-k", skip=True) or "all").strip()
    except Exception:
        k_filter = "all"
    k_filter = "".join(c if c.isalnum() or c in "_-" else "_" for c in k_filter)[:40] or "all"

    ts       = _dt.now().strftime("%Y%m%d_%H%M%S")
    log_path = runs_dir / f"{ts}_{k_filter}.log"
    log_file = open(log_path, "w", encoding="utf-8")

    config._qa_log_file     = log_file
    config._qa_log_path     = log_path
    config._qa_orig_stdout  = sys.stdout
    config._qa_orig_stderr  = sys.stderr

    sys.stdout = _TeeOutput(sys.stdout, log_file)
    sys.stderr = _TeeOutput(sys.stderr, log_file)


def pytest_unconfigure(config):
    """테스트 종료 시 HTML 리포트 생성 → 로그 파일 닫고 last_run.log에 복사."""
    from pathlib import Path

    # ── HTML 리포트 생성 (scan_reports 있을 때만) ────────────────────────
    if _scan_reports:
        try:
            import yaml as _yaml
            from core.models import PageScanReport as _PSR
            from core.html_reporter import generate_html_report

            # 같은 page_id 리포트 머지 (nPouch: 시나리오별 5개 → 1개로 합산)
            _merged: dict[str, list] = {}
            for _pid, _rpt in _scan_reports:
                _merged.setdefault(_pid, []).append(_rpt)
            _merged_list = [
                (_pid, _PSR.merge(*_rpts))
                for _pid, _rpts in _merged.items()
            ]

            # 제품명 자동 감지 (page_id 접두사 기준)
            _all_ids = list(_merged.keys())
            if any(_pid.startswith("npouch_") for _pid in _all_ids):
                product_name = "nPouch"
            else:
                with open(CONFIG_PATH, encoding="utf-8") as _f:
                    _cfg = _yaml.safe_load(_f) or {}
                product_name = _cfg.get("product_name", "RansomCruncher")

            html_path = generate_html_report(
                _merged_list,
                product_name=product_name,
                output_dir=f"reports/{product_name}",
                screenshot_dir=None,
            )
            sys.stdout.write(f"\n[HTML 리포트] {html_path}\n")
            sys.stdout.flush()
        except Exception as _e:
            sys.stdout.write(f"\n[HTML 리포트 생성 실패] {_e}\n")
            sys.stdout.flush()

    log_file = getattr(config, "_qa_log_file", None)
    log_path = getattr(config, "_qa_log_path", None)

    # stdout/stderr 원본 복원
    orig_out = getattr(config, "_qa_orig_stdout", None)
    orig_err = getattr(config, "_qa_orig_stderr", None)
    if orig_out:
        sys.stdout = orig_out
    if orig_err:
        sys.stderr = orig_err

    if log_file:
        try:
            log_file.flush()
            log_file.close()
        except Exception:
            pass

    if log_path and Path(log_path).exists():
        shutil.copy2(log_path, Path("reports/last_run.log"))


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
    # TEST_HEADLESS 환경변수가 명시적으로 설정된 경우 우선 적용
    # (app.py 에서 화면 ON/OFF 토글 결과를 전달함)
    env_headless = os.environ.get("TEST_HEADLESS", "").strip()
    if env_headless == "1":
        headless = True
    elif env_headless == "0":
        headless = False
    else:
        headless = browser_cfg.get("headless", False)
    slow_mo  = browser_cfg.get("slow_mo", 0)

    # VM / GPU 없는 환경에서 Chromium libuv 타이머 assertion 방지용 플래그
    # - --no-sandbox                            : VM/컨테이너 sandbox 비활성화 (필수)
    # - --disable-gpu                           : GPU 가속 비활성화 (VM 렌더링 오류 방지)
    # - --disable-dev-shm-usage                 : /dev/shm 부족 방지 (Linux VM)
    # - --disable-software-rasterizer           : SW 래스터라이저 충돌 방지
    # - --disable-background-timer-throttling   : 백그라운드 타이머 지연 비활성화
    # - --disable-renderer-backgrounding        : 렌더러 백그라운드 전환 비활성화
    # - --disable-backgrounding-occluded-windows: 가려진 창 백그라운드 전환 비활성화
    # - --disable-ipc-flooding-protection       : IPC 과부하 보호 비활성화 (VM 타이머 오류 감소)
    # - --no-first-run                          : 첫 실행 초기화 생략
    # - --metrics-recording-only                : 메트릭 외부 전송 없음
    _chromium_args = [
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-software-rasterizer",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-ipc-flooding-protection",
        "--no-first-run",
        "--metrics-recording-only",
    ]

    br = playwright_instance.chromium.launch(
        headless=headless,
        slow_mo=slow_mo,
        args=_chromium_args,
    )
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

    # console error/warning listener — JS error 자동화 로그 기록 (UX 결함 후 JS state 진단용)
    def _log_console(msg):
        if msg.type in ("error", "warning"):
            try:
                print(f"[JS {msg.type.upper()}] {msg.text[:200]}")
            except Exception:
                pass
    page.on("console", _log_console)
    page.on("pageerror", lambda exc: print(f"[JS PAGE ERROR] {str(exc)[:200]}"))

    # 네트워크 요청/응답 ring buffer — cascade fail 진단용 (최근 20건만 유지)
    # 5xx / 4xx 는 별도 로그. ring buffer 는 fail 시 dump.
    page._qa_recent_net = []
    def _on_response(resp):
        try:
            entry = {
                "method": resp.request.method,
                "url": resp.url[:120],
                "status": resp.status,
            }
            page._qa_recent_net.append(entry)
            if len(page._qa_recent_net) > 20:
                page._qa_recent_net.pop(0)
            if resp.status >= 500:
                print(f"[NET 5xx] {entry['method']} {entry['status']} {entry['url']}")
            elif resp.status >= 400 and resp.request.method != "GET":
                print(f"[NET 4xx] {entry['method']} {entry['status']} {entry['url']}")
        except Exception:
            pass
    page.on("response", _on_response)

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
            # 환경변수 모드: 비밀번호 재입력 불가 → 즉시 종료
            if os.environ.get("TEST_PW", "").strip():
                sys.stderr.write("환경변수 TEST_PW가 틀렸습니다. 올바른 비밀번호로 다시 실행하세요.\n\n")
                sys.stderr.flush()
                pytest.exit(f"[환경변수 로그인 실패] {msg}", returncode=1)
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

    # HTML 리포트용 스캔 결과 수집 (test_page_scan + test_npouch 공통)
    if report.when == "call":
        scan_report = getattr(item, "_scan_report", None)
        if scan_report is not None:
            try:
                page_id = item.callspec.params.get("page_id")
            except AttributeError:
                # nPouch: 클래스 메서드 방식 — callspec 없음
                page_id = getattr(item, "_npouch_page_id", None)
            if page_id:
                _scan_reports.append((page_id, scan_report))

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

        # ── cascade fail 진단 dump (로그로만, 별도 파일 X) ─────────────
        print(f"\n[진단 DUMP] === {item.name} fail 시점 상태 ===")
        # 1) DOM snapshot — modal/backdrop/body class
        try:
            dom_state = page.evaluate("""
                () => {
                    const open_modals = Array.from(document.querySelectorAll('.modal.in'))
                        .map(m => m.id || m.className);
                    const backdrops = document.querySelectorAll('.modal-backdrop').length;
                    const body_cls = document.body.className;
                    const body_style = document.body.getAttribute('style') || '';
                    return {open_modals, backdrops, body_cls, body_style};
                }
            """)
            print(f"[진단 DOM] open_modals={dom_state['open_modals']} backdrops={dom_state['backdrops']} body_cls='{dom_state['body_cls']}' body_style='{dom_state['body_style']}'")
        except Exception as e:
            print(f"[진단 DOM] 실패: {e}")

        # 2) AngularJS $rootScope 상태
        try:
            ng_state = page.evaluate("""
                () => {
                    if (!window.angular) return {error: 'angular not loaded'};
                    const body = angular.element(document.body);
                    const rs = body.scope() ? body.scope().$root : null;
                    if (!rs) return {error: 'rootScope not found'};
                    return {
                        phase: rs.$$phase || null,
                        watchers: (rs.$$watchersCount !== undefined ? rs.$$watchersCount : 'n/a'),
                        children: rs.$$childHead ? 'has_children' : 'no_children',
                        digest_pending: !!rs.$$asyncQueue && rs.$$asyncQueue.length > 0,
                        async_q_len: rs.$$asyncQueue ? rs.$$asyncQueue.length : 0,
                    };
                }
            """)
            print(f"[진단 NG] {ng_state}")
        except Exception as e:
            print(f"[진단 NG] 실패: {e}")

        # 3) 최근 네트워크 요청 (ring buffer)
        try:
            recent = getattr(page, "_qa_recent_net", [])
            print(f"[진단 NET] 최근 {len(recent)}건:")
            for entry in recent[-10:]:
                print(f"  {entry['method']:6s} {entry['status']} {entry['url']}")
        except Exception as e:
            print(f"[진단 NET] 실패: {e}")
        print(f"[진단 DUMP] === end ===\n")
