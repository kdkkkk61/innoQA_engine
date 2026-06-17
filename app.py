"""
app.py — QA Tool 앱 진입점

실행: python app.py
     → PyWebView 앱 창 오픈 (네이티브 윈도우)
     → Flask 백엔드 백그라운드 실행

화면 흐름:
  ① 제품 선택 → ② 테스트 선택 → ③ 실행 설정
  → ④ 진행 화면 → ⑤ 1차 리포트(편집) → ⑥ 최종 리포트 다운로드
"""
from __future__ import annotations

import logging
import subprocess
import sys
import threading
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file
try:
    from dashboard import dashboard_bp as dashboard_bp
    _dashboard_available = True
except ImportError:
    dashboard_bp = None
    _dashboard_available = False

# ── 경로 설정 ────────────────────────────────────────────────────────
# PyInstaller --onedir EXE 로 실행 시: sys._MEIPASS 가 존재하며
#   sys.executable = dist/inno_test_tool/inno_test_tool.exe
#   BASE_DIR       = dist/inno_test_tool/          (EXE 옆 폴더)
# 일반 python app.py 실행 시: Path(__file__).parent 그대로 사용
if getattr(sys, "frozen", False):
    # PyInstaller 번들 실행
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def _get_python() -> str:
    """
    pytest 서브프로세스에 전달할 Python 인터프리터 경로를 반환한다.

    우선순위:
    1. 설치 폴더 python/python.exe  (qatool_setup.exe 로 설치한 경우)
    2. 현재 venv Scripts/python.exe (setup.bat 으로 구성한 경우)
    3. sys.executable 의 pythonw -> python 전환 (pythonw 는 subprocess 에 부적합)
    4. sys.executable 그대로 (일반 개발 실행)
    """
    # 인스톨러 배포: EXE 옆 python\ 폴더
    bundled = BASE_DIR / "python" / "python.exe"
    if bundled.exists():
        return str(bundled)

    # setup.bat 배포: venv
    venv_py = BASE_DIR / "venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)

    # 일반 실행: pythonw.exe 인 경우 python.exe 로 교체
    exe = Path(sys.executable)
    if exe.stem.lower() == "pythonw":
        sibling = exe.parent / "python.exe"
        if sibling.exists():
            return str(sibling)

    return sys.executable


def _get_browsers_env(base: dict) -> dict:
    """
    PLAYWRIGHT_BROWSERS_PATH 를 설치 폴더 기준으로 설정한다.
    인스톨러 배포 시 browsers/ 폴더를 사용하고,
    개발 환경에서는 기존 환경변수를 그대로 유지한다.
    """
    browsers_dir = BASE_DIR / "browsers"
    if browsers_dir.exists():
        base["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_dir)
        log.info(f"[browsers] PLAYWRIGHT_BROWSERS_PATH = {browsers_dir}")
    else:
        log.info(f"[browsers] browsers/ 폴더 없음 — 시스템 기본 Chromium 사용 ({browsers_dir})")
    return base

# ── 로그 설정 ─────────────────────────────────────────────────────────
_LOG_DIR = BASE_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

import io as _io
_safe_stdout = _io.TextIOWrapper(
    sys.stdout.buffer if hasattr(sys.stdout, "buffer") else open(os.devnull, "wb"),
    encoding="utf-8", errors="replace", line_buffering=True,
)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(_safe_stdout),        # UTF-8 강제 — CP949 이모지 오류 방지
    ],
)
log = logging.getLogger("qa_app")
log.info(f"=== QA Tool 시작 === 로그 파일: {_LOG_FILE}")

# PyInstaller --onedir: 코드/템플릿은 _MEIPASS 안에 번들되지만
# BASE_DIR (EXE 옆) 에도 templates 폴더를 배치하는 방식으로 통일
_TEMPLATE_DIR = BASE_DIR / "templates" / "app"
_STATIC_DIR   = BASE_DIR / "static"
app = Flask(
    __name__,
    template_folder=str(_TEMPLATE_DIR),
    static_folder=str(_STATIC_DIR),
)
app.config['BASE_DIR'] = BASE_DIR
if _dashboard_available and dashboard_bp is not None:
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

# dashboard DB 초기화
_DB_PATH = BASE_DIR / "data" / "qa.db"
_DB_PATH.parent.mkdir(exist_ok=True)
if _dashboard_available:
    try:
        from dashboard.db import init_db as _init_db
        _init_db(str(_DB_PATH))
    except Exception as _e:
        log.warning(f"dashboard DB 초기화 실패 (무시): {_e}")

# innoRelease 클라이언트 초기화 (settings.yaml 로드)
try:
    import yaml as _yaml
    _settings_path = BASE_DIR / "config" / "settings.yaml"
    if _settings_path.exists():
        _settings_data = _yaml.safe_load(_settings_path.read_text(encoding="utf-8")) or {}
        _irel_cfg = _settings_data.get("innorelease", {})
        _irel_url = _irel_cfg.get("url", "")
        _irel_user = _irel_cfg.get("username", "")
        _irel_pass = _irel_cfg.get("password", "")
        if _irel_url and _irel_user:
            from core.innorelease_client import init_client as _init_irel
            _irel_client = _init_irel(_irel_url, _irel_user, _irel_pass)
            app.config["INNORELEASE_URL"] = _irel_url
            log.info(f"[OK] innoRelease 클라이언트 초기화: {_irel_url} ({_irel_user})")
        # QA 서버 URL (승인 시 testEnvInfo에 포함)
        _qa_server_url = _settings_data.get("qa_server_url", "").strip()
        if _qa_server_url:
            app.config["QA_SERVER_URL"] = _qa_server_url
        else:
            log.info("[INFO] innoRelease 미설정 (settings.yaml innorelease.url/username 확인)")
except Exception as _exc:
    log.warning(f"[WARN] innoRelease 클라이언트 초기화 실패: {_exc}")

# ── 실행 상태 (세션 단위) ─────────────────────────────────────────────
_state: dict = {
    "product":         None,   # 선택된 제품 ID
    "pages":           [],     # 선택된 page_id 목록
    "status":          "idle", # idle / running / done / error
    "page_status":     {},     # {page_id: "waiting"|"running"|"done"|"error"}
    "scenario_status": {},     # {page_id: [{"label":..., "status":"pending"|"running"|"done"}]}
    "error_log":       "",
    "report_path":     None,
    "live_log":        [],     # 최근 pytest 출력 (최대 200줄) — progress 화면 실시간 표시용
    "log_file":        "",     # 현재 세션 로그 파일 경로
    # innoRelease 파이프라인 연동 (qa_queue에서 테스트 실행 시 설정)
    "pipeline_id":     None,   # innoRelease pipeline_id (TESTING 상태)
    "pipeline_repo_id":None,   # innoRelease repoId
    "pipeline_product":None,   # innoProduct 코드 (1~7)
    "pipeline_run_id": None,   # 테스트 완료 후 저장된 run_id (local DB)
}
_proc: subprocess.Popen | None = None
_wv: dict = {"window": None}   # pywebview 창 참조 — /open-window 엔드포인트에서 사용


# ── 시나리오 사전 정의 ──────────────────────────────────────────────

# CLAUDE.md 시나리오 번호 표준: 1~5 고정 (없는 항목은 [SKIP] skip 출력)
# modal_form / list_page 모두 동일 번호 사용
_MODAL_SCENARIOS = [
    {"num": 1, "label": "시나리오 1: UI 구조  (탭 · 테이블 · 검색)", "status": "pending"},
    {"num": 2, "label": "시나리오 2: 입력 구조  (모달 필드 · 초기값 · 필수입력)", "status": "pending"},
    {"num": 3, "label": "시나리오 3: 동작 검증  (CRUD · 오버플로 · 중복 처리)", "status": "pending"},
    {"num": 4, "label": "시나리오 4: 수정 시나리오  (저장값 로드 · 재확인)", "status": "pending"},
    {"num": 5, "label": "시나리오 5: 케이스 검증  (제품 설정 ON/OFF 프로파일)", "status": "pending"},
]
_LIST_SCENARIOS = [
    {"num": 1, "label": "시나리오 1: UI 구조  (탭 · 테이블 · 검색)", "status": "pending"},
    {"num": 2, "label": "시나리오 2: 입력 구조  (모달 필드 · 필수입력 검증)", "status": "pending"},
    {"num": 3, "label": "시나리오 3: 동작 검증  (CRUD · 추가 · 수정 · 삭제)", "status": "pending"},
    {"num": 4, "label": "시나리오 4: 수정 시나리오  (저장값 로드 · 재확인)", "status": "pending"},
    {"num": 5, "label": "시나리오 5: 케이스 검증  (전체 채우기 / 필수만 저장 확인)", "status": "pending"},
    {"num": 6, "label": "시나리오 6: 연계 데이터 준비  (다음 테스트용 항목 생성)", "status": "pending"},
]

# nPouch 전용: page_id ↔ 테스트 클래스명 매핑
_NPOUCH_PAGE_TO_CLASS: dict[str, str] = {
    "common_operation_process": "TestNpouchOperationProcess",
    "common_tag":               "TestNpouchTag",
    "common_control_suite":     "TestNpouchControlSuite",
    "npouch_origin_protect":    "TestNpouchOriginProtect",
    "npouch_policy":            "TestNpouchPolicy",
}
_NPOUCH_CLASS_TO_PAGE: dict[str, str] = {v: k for k, v in _NPOUCH_PAGE_TO_CLASS.items()}
_NPOUCH_PAGE_TO_FILE: dict[str, str] = {
    # 공통 페이지(운용/태그/제어스위트)는 tests/common/ 에 있고 page_id 도 common_ 으로 통일
    "common_operation_process": "common/test_operation_process.py",
    "common_tag":               "common/test_tag.py",
    # 디렉토리 매핑 — tests/<디렉토리>/ 안의 모든 test_scenario*.py 실행
    "common_control_suite":     "common/control_suite",
    "npouch_origin_protect":    "origin_protect",
    "npouch_policy":            "npouch_policy",   # 디렉토리 매핑 (sc0~6 구조)
}


def _get_default_scenarios(page_id: str) -> list[dict]:
    """scan_hints yaml에서 scan_mode 읽어 시나리오 목록을 '예정' 상태로 반환."""
    hints_path = BASE_DIR / "config" / "scan_hints" / f"{page_id}.yaml"
    try:
        import yaml as _yaml
        hints     = _yaml.safe_load(hints_path.read_text(encoding="utf-8")) or {}
        scan_mode = hints.get("scan_mode", "modal_form")
    except Exception:
        scan_mode = "modal_form"

    base = _LIST_SCENARIOS if scan_mode == "list_page" else _MODAL_SCENARIOS
    # 매번 새 dict 복사 (상태 공유 방지)
    return [dict(sc) for sc in base]


# ── 제품/페이지 목록 ──────────────────────────────────────────────────

def _get_products() -> list[dict]:
    """registry.py의 MODULE_GROUPS 기반으로 제품 목록 반환."""
    try:
        from pages.registry import MODULE_GROUPS
        label_map = {
            "ransom_cruncher": "랜섬크런처",
            "npouch":          "엔파우치",
        }
        return [
            {
                "id":     mid,
                "label":  label_map.get(mid, mid),
                "active": mid in label_map,
            }
            for mid in MODULE_GROUPS
        ]
    except Exception:
        return []


def _get_pages(product_id: str) -> list[dict]:
    """선택된 제품의 page_id 목록 반환."""
    try:
        from pages.registry import MODULE_GROUPS, PAGE_REGISTRY
        page_label = {
            "ransom_detect_policy":     "탐지정책",
            "rdp_policy":               "RDP 정책",
            "common_process":           "공통 프로세스",
            "common_operation_process": "운용 프로세스",
            "common_tag":               "태그 관리",
            "common_control_suite":     "제어 스위트",
            "npouch_origin_protect":    "원본 보호 정책",
            "npouch_policy":            "nPouch 정책",
        }
        return [
            {"id": pid, "label": page_label.get(pid, pid)}
            for pid in MODULE_GROUPS.get(product_id, [])
            if pid in PAGE_REGISTRY
        ]
    except Exception:
        return []


# ── 라우트 ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """① 제품 선택 화면."""
    products = _get_products()
    log.info("화면: 제품 선택")
    return render_template("index.html", products=products)


@app.route("/test-type")
def test_type():
    """② 테스트 선택 화면."""
    product_id = request.args.get("product", "")
    _state["product"] = product_id
    pages = _get_pages(product_id)
    log.info(f"화면: 테스트 선택 | 제품={product_id} | 페이지 목록={[p['id'] for p in pages]}")
    return render_template("test_type.html", product_id=product_id, pages=pages)


@app.route("/run-setup")
def run_setup():
    """③ 실행 설정 화면 (ID/PW 입력)."""
    page_ids = request.args.getlist("pages")
    _state["pages"] = page_ids
    product_id = _state.get("product", "")
    all_pages  = _get_pages(product_id)
    pages_info = [
        {**p, "selected": p["id"] in page_ids}
        for p in all_pages
    ]
    product_label_map = {"ransom_cruncher": "RansomCruncher"}

    # 현재 설정된 base_url 읽어서 UI에 표시 (설치 PC에서 수정 가능)
    import yaml as _yaml
    try:
        _cfg = _yaml.safe_load((BASE_DIR / "config" / "settings.yaml").read_text(encoding="utf-8")) or {}
        current_url = _cfg.get("base_url", "")
    except Exception:
        current_url = ""

    log.info(f"화면: 실행 설정 | 선택된 페이지={page_ids} | URL={current_url}")
    return render_template(
        "run_setup.html",
        pages=page_ids,
        pages_info=pages_info,
        product_id=product_id,
        product_label=product_label_map.get(product_id, product_id),
        current_url=current_url,
    )


@app.route("/start", methods=["POST"])
def start():
    """테스트 subprocess 실행."""
    global _proc
    data      = request.get_json()
    test_id   = data.get("test_id", "")
    test_pw   = data.get("test_pw", "")
    headless  = bool(data.get("headless", False))
    target_url = data.get("target_url", "").strip()
    page_ids  = _state.get("pages", [])

    # target_url이 전달된 경우 settings.yaml에 즉시 반영 (설치 PC에서 IP 변경 지원)
    if target_url:
        import yaml as _yaml
        _cfg_path = BASE_DIR / "config" / "settings.yaml"
        try:
            _cfg = _yaml.safe_load(_cfg_path.read_text(encoding="utf-8")) or {}
            if _cfg.get("base_url") != target_url:
                _cfg["base_url"] = target_url
                _cfg_path.write_text(
                    _yaml.dump(_cfg, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )
                log.info(f"base_url 업데이트: {target_url}")
        except Exception as e:
            log.warning(f"settings.yaml 업데이트 실패: {e}")

    if not page_ids or not test_id or not test_pw:
        log.warning(f"시작 실패 — 필수 입력 누락 | id={test_id!r} pages={page_ids}")
        return jsonify({"ok": False, "error": "필수 입력 누락"}), 400

    # 이전 프로세스가 크래시/timeout으로 죽었는데 status가 running에 고착된 경우 자동 복구
    if _state["status"] == "running" and _proc is not None:
        if _proc.poll() is not None:
            log.info(f"이전 프로세스 종료 감지 (returncode={_proc.returncode}) — 상태 자동 복구")
            _state["status"] = "done"

    if _state["status"] == "running":
        log.warning("시작 실패 — 이미 실행 중")
        return jsonify({"ok": False, "error": "이미 실행 중"}), 400

    # innoRelease 파이프라인 컨텍스트 (qa_queue에서 전달 — 없으면 None)
    pipeline_id      = data.get("pipeline_id")
    pipeline_repo_id = data.get("pipeline_repo_id")
    pipeline_product = data.get("pipeline_product")

    log.info(f"테스트 시작 | ID={test_id} | 대상={page_ids} | headless={headless}"
             + (f" | pipeline={pipeline_id}" if pipeline_id else ""))

    # 상태 초기화 — 첫 번째 페이지는 즉시 running으로 (pytest 로딩 중 대기 없이 표시)
    _state["status"]           = "running"
    _state["error_log"]        = ""
    _state["report_path"]      = None
    _state["live_log"]         = []
    _state["log_file"]         = str(_LOG_FILE)
    _state["pipeline_id"]      = int(pipeline_id) if pipeline_id else None
    _state["pipeline_repo_id"] = int(pipeline_repo_id) if pipeline_repo_id else None
    _state["pipeline_product"] = int(pipeline_product) if pipeline_product else None
    _state["pipeline_run_id"]  = None
    _state["page_status"]      = {
        pid: ("running" if i == 0 else "waiting")
        for i, pid in enumerate(page_ids)
    }
    _state["scenario_status"] = {pid: _get_default_scenarios(pid) for pid in page_ids}

    # pytest 실행 파일 + 필터 결정
    product_id = _state.get("product", "")
    if product_id == "npouch":
        # nPouch: page_id별 test 파일 수집 (중복 제거) — -k 필터로 클래스 선택
        test_files = list(dict.fromkeys(
            str(BASE_DIR / "tests" / _NPOUCH_PAGE_TO_FILE.get(pid, "common/test_operation_process.py"))
            for pid in page_ids
        ))
        # 디렉토리 매핑된 page (control_suite/origin_protect/npouch_policy) 가 하나라도 있으면
        # -k 필터 skip — 디렉토리 패턴의 클래스명 (TestScenario*, TestOriginProtect*) 가
        # 매핑값 (TestNpouchControlSuite, TestNpouchOriginProtect) 과 불일치 → match 0건 → deselect
        # 사용자 보고 2026-06-03: 5 페이지 체크해도 control_suite/origin_protect 누락.
        # 해결: 디렉토리 페이지 포함 시 -k 필터 자체 skip → test_files path 가 page 분리.
        _dir_pages = {"common_control_suite", "npouch_origin_protect", "npouch_policy"}
        has_dir = any(pid in _dir_pages for pid in page_ids)
        if has_dir:
            k_filter = ""
        else:
            class_names = [_NPOUCH_PAGE_TO_CLASS.get(pid, pid) for pid in page_ids]
            k_filter = " or ".join(class_names)
    else:
        # 그 외: 범용 test_scan_pages.py — page_id 그대로 -k 필터
        test_files = [str(BASE_DIR / "tests" / "test_scan_pages.py")]
        k_filter = " or ".join(page_ids)

    env = os.environ.copy()
    env["TEST_ID"] = test_id
    env["TEST_PW"] = test_pw
    env["TEST_HEADLESS"] = "1" if headless else "0"
    env = _get_browsers_env(env)   # 설치 폴더 browsers\ 있으면 PLAYWRIGHT_BROWSERS_PATH 설정
    env["UV_USE_IO_RINGS"] = "0"   # libuv Windows 타이머 역방향 assertion 방지 (Chromium 크래시 방지)

    cmd = [
        _get_python(), "-u", "-m", "pytest",
        *test_files,        # 제품별 테스트 파일 선택 (복수 지원)
        "-v", "-s",
        "--timeout=300",    # 테스트 1개당 최대 5분 — Chromium hang 시 강제 종료
    ]
    if k_filter:
        cmd.extend(["-k", k_filter])
    env["PYTHONUNBUFFERED"] = "1"

    def _run():
        import re as _re
        # 시나리오 N: ... 헤더 감지 (일반 실행)
        _SC_RE   = _re.compile(r'시나리오\s+(\d+)[a-z]?\s*[:\uff1a]\s*(.+)')
        # [SKIP] 시나리오 N: ... — 해당 없음 (skip 출력)
        _SKIP_RE = _re.compile(r'[[SKIP]]\s*시나리오\s+(\d+)')

        global _proc
        try:
            log.info(f"pytest 실행: {' '.join(cmd)}")
            _startupinfo = None
            if os.name == "nt":
                _startupinfo = subprocess.STARTUPINFO()
                _startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                _startupinfo.wShowWindow = subprocess.SW_HIDE

            _proc = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,   # 콘솔 없는 환경에서 stdin block 방지
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=_startupinfo,
                # CREATE_NO_WINDOW 제거 — headless Playwright 자식 프로세스 통신 보장
            )
            log.info(f"pytest PID={_proc.pid}")

            current_page = None
            error_lines: list[str] = []
            _MAX_LIVE_LOG = 200  # 최대 보관 줄 수

            for line in _proc.stdout:
                line = line.rstrip()
                if not line:
                    continue

                # pytest 출력 전체를 로그에 기록 (DEBUG 레벨)
                log.debug(f"[pytest] {line}")

                # live_log 버퍼에 추가 (progress 화면 실시간 표시용)
                _state["live_log"].append(line)
                if len(_state["live_log"]) > _MAX_LIVE_LOG:
                    _state["live_log"] = _state["live_log"][-_MAX_LIVE_LOG:]

                # ── 현재 스캔 중인 페이지 감지 ──────────────────────────────
                # test_scan_pages.py: "test_page_scan[page_id]"
                # 공통 단일 파일:    "test_operation_process.py::" / "test_tag.py::" (basename)
                # 디렉토리 패턴:     "tests/control_suite/" / "tests\control_suite\"
                #                    (단일 클래스명 매핑 불가 — 디렉토리 안 다중 클래스)
                for pid in page_ids:
                    detected = False
                    if product_id == "npouch":
                        file_or_dir = _NPOUCH_PAGE_TO_FILE.get(pid, "")
                        if file_or_dir.endswith(".py"):
                            # 단일 파일: basename 으로 매칭 (경로 구분자 무관 — common/ 접두 대응)
                            _base = file_or_dir.rsplit("/", 1)[-1]
                            if f"{_base}::" in line or f"{_base} " in line:
                                detected = True
                        elif file_or_dir:
                            # 디렉토리: "tests/<dir>/" 또는 "tests\<dir>\"
                            if f"/{file_or_dir}/" in line or f"\\{file_or_dir}\\" in line:
                                detected = True
                    else:
                        if f"test_page_scan[{pid}]" in line:
                            detected = True
                    if detected:
                        if current_page and current_page != pid:
                            for sc in _state["scenario_status"].get(current_page, []):
                                if sc["status"] == "pending":
                                    sc["status"] = "stopped"
                        if current_page != pid:
                            log.info(f"페이지 전환: {current_page} → {pid}")
                        current_page = pid
                        _state["page_status"][pid] = "running"

                # ── 시나리오 헤더 감지 ──────────────────────────────────────
                if current_page:
                    sc_list = _state["scenario_status"][current_page]

                    # [SKIP] skip 감지 — 해당 시나리오를 stopped로 표시
                    ms = _SKIP_RE.search(line)
                    if ms:
                        sc_num = int(ms.group(1))
                        existing = next((s for s in sc_list if s["num"] == sc_num), None)
                        if existing and existing["status"] == "pending":
                            existing["status"] = "stopped"
                        log.info(f"  [{current_page}] 시나리오 {sc_num} 스킵")

                    # 일반 시나리오 헤더 감지 ([SKIP]가 없는 줄만)
                    elif "[SKIP]" not in line:
                        m = _SC_RE.search(line)
                        if m:
                            sc_num   = int(m.group(1))
                            sc_label = m.group(2).strip().strip("─═ \t")
                            for sc in sc_list:
                                if sc["status"] == "running":
                                    sc["status"] = "done"
                            existing = next((s for s in sc_list if s["num"] == sc_num), None)
                            if existing:
                                existing["status"] = "running"
                            else:
                                # sc_num 오름차순 정렬 insert (sc0 가 sc1 앞으로 가도록)
                                new_sc = {
                                    "num":    sc_num,
                                    "label":  f"시나리오 {sc_num}: {sc_label}",
                                    "status": "running",
                                }
                                insert_at = next(
                                    (i for i, s in enumerate(sc_list) if s["num"] > sc_num),
                                    len(sc_list)
                                )
                                sc_list.insert(insert_at, new_sc)
                            log.info(f"  [{current_page}] 시나리오 {sc_num} 시작: {sc_label}")

                # ── pytest 결과 줄 감지 ─────────────────────────────────────
                # test_scan_pages.py: 페이지 1개 = 테스트 함수 1개 → PASSED면 페이지 완료
                # 공통 운용/태그:    페이지 1개 = 시나리오 5개 → 모든 시나리오 done 시 페이지 완료
                if current_page:
                    bare        = line.strip()
                    in_summary  = (
                        ("test_page_scan" in line)
                        or ("test_operation_process" in line) or ("test_tag" in line) or
                        ("/control_suite/" in line) or ("\\control_suite\\" in line) or
                        ("/origin_protect/" in line) or ("\\origin_protect\\" in line) or
                        ("/npouch_policy/" in line) or ("\\npouch_policy\\" in line)
                    )
                    is_passed   = bare == "PASSED"
                    is_failed   = bare == "FAILED" or (in_summary and line.lstrip().startswith("FAILED"))

                    if is_passed:
                        if product_id == "npouch":
                            # 시나리오 단위: 실행 중인 시나리오만 done 처리
                            for sc in _state["scenario_status"].get(current_page, []):
                                if sc["status"] == "running":
                                    sc["status"] = "done"
                            # 모든 시나리오 완료 시 페이지 done
                            all_done = all(
                                sc["status"] in ("done", "stopped")
                                for sc in _state["scenario_status"].get(current_page, [])
                            )
                            if all_done:
                                _state["page_status"][current_page] = "done"
                                log.info(f"  [{current_page}] 전체 시나리오 완료 [OK]")
                        else:
                            # 페이지 단위: PASSED = 페이지 전체 완료
                            for sc in _state["scenario_status"].get(current_page, []):
                                sc["status"] = "done"
                            _state["page_status"][current_page] = "done"
                            log.info(f"  [{current_page}] PASSED [OK]")
                    elif is_failed:
                        for sc in _state["scenario_status"].get(current_page, []):
                            if sc["status"] == "running":
                                sc["status"] = "error"    # 실행 중 실패한 시나리오
                            elif sc["status"] == "pending":
                                sc["status"] = "stopped"  # 미실행 시나리오 → 중지
                        _state["page_status"][current_page] = "error"
                        log.warning(f"  [{current_page}] FAILED [FAIL]")

                # HTML 리포트 경로 감지 (conftest pytest_unconfigure가 출력)
                if "[HTML 리포트]" in line:
                    html_path = line.split("[HTML 리포트]", 1)[1].strip()
                    p = Path(html_path)
                    if not p.is_absolute():
                        p = BASE_DIR / p
                    if p.exists():
                        _state["report_path"] = str(p)
                        log.info(f"HTML 리포트 경로 설정: {p}")

                # 오류/예외 줄 수집 + 로그 기록
                if any(kw in line for kw in ("ERROR", "Error:", "Traceback", "Exception", "AssertionError")):
                    log.error(f"[오류줄] {line}")
                    error_lines.append(line)
                    if len(error_lines) > 40:
                        error_lines.pop(0)

            _state["error_log"] = "\n".join(error_lines) if error_lines else ""

            _proc.wait()
            log.info(f"pytest 종료 | returncode={_proc.returncode}")

            if _proc.returncode == 0:
                _state["status"] = "done"
                # 미완료 페이지 + 시나리오 전부 done 처리 (returncode=0 보장)
                for pid in page_ids:
                    for sc in _state["scenario_status"].get(pid, []):
                        sc["status"] = "done"
                    if _state["page_status"][pid] != "error":
                        _state["page_status"][pid] = "done"
            else:
                _state["status"] = "error"

            # ── HTML 리포트 경로 폴백 (conftest [HTML 리포트] 감지 못한 경우) ─
            # 제품별 폴더만 탐색 — 다른 제품 리포트 혼입 방지
            if not _state.get("report_path"):
                _product_label = {
                    "ransom_cruncher": "RansomCruncher",
                    "npouch":          "nPouch",
                }.get(product_id, product_id)
                _report_dir = BASE_DIR / "reports" / _product_label
                if _report_dir.exists():
                    _reports = sorted(
                        _report_dir.glob("QA_*.html"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                    if _reports:
                        _state["report_path"] = str(_reports[0])
                        log.info(f"HTML 리포트 (폴백): {_reports[0]}")

            # 리포트 자동 import (로컬 DB + 원격 서버)
            if _state.get("report_path"):
                _rp = _state["report_path"]

                # ① 로컬 DB import
                _local_run_id: int | None = None
                try:
                    from core.report_parser import parse_report
                    from dashboard.db import import_report as _local_import
                    _parsed = parse_report(_rp)
                    if _parsed:
                        _local_run_id = _local_import(str(_DB_PATH), _parsed)
                        _state["pipeline_run_id"] = _local_run_id
                        log.info(f"[OK] 로컬 DB import 완료 (run_id={_local_run_id})")
                except Exception as _e:
                    log.warning(f"로컬 import 실패: {_e}")

                # ② innoRelease QA 레코드 자동 등록 (pipeline_id가 설정된 경우)
                _pip_id   = _state.get("pipeline_id")
                _repo_id  = _state.get("pipeline_repo_id")
                _prod_id  = _state.get("pipeline_product")
                if _pip_id and _repo_id and _prod_id:
                    try:
                        from core.innorelease_client import get_client as _get_irel_client
                        from dashboard.db import get_run as _get_run, update_qa_request as _upd_qa
                        from datetime import date as _date2
                        _irel = _get_irel_client()
                        if _irel and _local_run_id:
                            _run_row = _get_run(str(_DB_PATH), _local_run_id)
                            if _run_row:
                                _total    = _run_row["total"]    or 0
                                _pass_cnt = _run_row["pass_cnt"] or 0
                                _fail_cnt = _run_row["fail_cnt"] or 0
                                _bug_cnt  = _run_row["bug_cnt"]  or 0
                                _err_cnt  = _run_row["error_cnt"]or 0
                                _rate     = round(_pass_cnt / _total * 100, 1) if _total else 0
                                _errtxt   = ""
                                if _fail_cnt or _bug_cnt or _err_cnt:
                                    _errtxt = (
                                        f"FAIL: {_fail_cnt}건, BUG: {_bug_cnt}건, ERROR: {_err_cnt}건\n"
                                        f"PASS율: {_rate}%"
                                    )
                                _html_p = _rp if Path(_rp).exists() else None
                                _qa_ok = _irel.post_qa_result(
                                    repo_id=_repo_id,
                                    inno_product=_prod_id,
                                    platform="MANAGER",
                                    record_date=_date2.today().isoformat(),
                                    updates=f"전체: {_total}건, PASS: {_pass_cnt}건",
                                    errors_bugs=_errtxt,
                                    pipeline_id=_pip_id,
                                    html_file_path=_html_p,
                                )
                                # 로컬 qa_requests 상태 갱신 (run_id 연결, 결과 대기 상태)
                                _upd_qa(str(_DB_PATH), _pip_id, run_id=_local_run_id)
                                log.info(f"[OK] innoRelease QA 레코드 자동 등록: pipeline={_pip_id} qa_ok={_qa_ok}")
                    except Exception as _e:
                        log.warning(f"[WARN] innoRelease QA 자동 등록 실패: {_e}")

                # ② 원격 서버 업로드 (QA_SERVER_URL 환경변수 또는 settings.yaml)
                _server_url = os.environ.get("QA_SERVER_URL", "").strip()
                if not _server_url:
                    try:
                        import yaml as _yaml2
                        _scfg = _yaml2.safe_load(
                            (BASE_DIR / "config" / "settings.yaml").read_text(encoding="utf-8")
                        ) or {}
                        _server_url = _scfg.get("qa_server_url", "").strip()
                    except Exception:
                        pass
                if _server_url:
                    try:
                        import requests as _req
                        _rp_path = Path(_rp)
                        with open(_rp_path, "rb") as _rf:
                            _resp = _req.post(
                                f"{_server_url.rstrip('/')}/dashboard/import-file",
                                files={"report": (_rp_path.name, _rf, "text/html")},
                                timeout=30,
                            )
                        _rd = _resp.json()
                        log.info(f"[OK] 서버 업로드: {_rd.get('message')} (run_id={_rd.get('run_id')})")
                    except Exception as _e:
                        log.warning(f"서버 업로드 실패: {_e}")

        except Exception as e:
            log.exception(f"_run() 예외 발생: {e}")
            _state["status"]    = "error"
            _state["error_log"] = str(e)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/progress")
def progress():
    """④ 진행 화면."""
    return render_template("progress.html", pages=_state["pages"])


@app.route("/status")
def status():
    """진행 상태 폴링 API."""
    return jsonify({
        "status":          _state["status"],
        "page_status":     _state["page_status"],
        "scenario_status": _state["scenario_status"],
        "error_log":       _state["error_log"],
        "report_path":     _state["report_path"],
        "live_log":        _state.get("live_log", [])[-80:],   # 최신 80줄만 전송
        "log_file":        _state.get("log_file", ""),
        "pipeline_id":     _state.get("pipeline_id"),
        "pipeline_run_id": _state.get("pipeline_run_id"),
    })


@app.route("/set-pipeline", methods=["POST"])
def set_pipeline():
    """
    qa_queue 페이지에서 테스트 시작 전 pipeline 컨텍스트를 서버에 사전 등록.
    테스트 완료 후 _run()이 이 정보를 참조해 innoRelease에 자동 등록한다.
    Body: { pipeline_id, pipeline_repo_id, pipeline_product }
    """
    data = request.get_json(silent=True) or {}
    _state["pipeline_id"]      = int(data["pipeline_id"])      if data.get("pipeline_id")      else None
    _state["pipeline_repo_id"] = int(data["pipeline_repo_id"]) if data.get("pipeline_repo_id") else None
    _state["pipeline_product"] = int(data["pipeline_product"]) if data.get("pipeline_product") else None
    _state["pipeline_run_id"]  = None
    log.info(f"[pipeline] 컨텍스트 설정: pipeline_id={_state['pipeline_id']} "
             f"repo_id={_state['pipeline_repo_id']} product={_state['pipeline_product']}")
    return jsonify({"ok": True})


@app.route("/pipeline-status")
def pipeline_status():
    """
    qa_queue 페이지에서 테스트 완료 여부 + run_id를 폴링하기 위한 API.
    테스트 완료 후 pipeline_run_id가 설정되면 해당 값을 반환.
    """
    return jsonify({
        "status":       _state["status"],
        "pipeline_id":  _state.get("pipeline_id"),
        "run_id":       _state.get("pipeline_run_id"),
    })


@app.route("/stop", methods=["POST"])
def stop():
    """테스트 중단."""
    global _proc
    if _proc and _proc.poll() is None:
        log.warning("테스트 강제 중단 (사용자 요청)")
        _proc.terminate()
    _state["status"] = "idle"
    return jsonify({"ok": True})


@app.route("/open-window", methods=["POST"])
def open_window():
    """pywebview 앱 창 열기 — 브라우저에서 '앱으로 열기' 버튼 클릭 시 호출."""
    win = _wv.get("window")
    if win is not None:
        try:
            win.show()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})
    return jsonify({"ok": False, "error": "not_available"})


@app.route("/report")
def report():
    """⑤ 1차 리포트 편집 화면."""
    return render_template("report.html")


@app.route("/report-data")
def report_data():
    """리포트 데이터 API — 전체 결과 + 결함 목록.
    _state["report_path"] 옆의 last_report.json 우선 사용 (제품별 폴더 지원).
    없으면 reports/ 루트 폴백.
    """
    import json as _json
    # 현재 세션 리포트 경로 기준으로 JSON 파일 탐색
    rp = _state.get("report_path")
    candidates = []
    if rp:
        candidates.append(Path(rp).parent / "last_report.json")
    candidates.append(BASE_DIR / "reports" / "last_report.json")

    json_path = next((p for p in candidates if p.exists()), None)
    if not json_path:
        return jsonify({"pages": [], "html_path": None})
    try:
        data = _json.loads(json_path.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"pages": [], "error": str(e)})


@app.route("/open-report")
def open_report():
    """최종 HTML 리포트를 시스템 기본 브라우저로 열기."""
    path = _state.get("report_path")
    if not path or not Path(path).exists():
        # last_report.json에서 경로 찾기
        try:
            import json as _json
            j = _json.loads((BASE_DIR / "reports" / "last_report.json").read_text(encoding="utf-8"))
            path = j.get("html_path", "")
        except Exception:
            pass
    if path and Path(path).exists():
        import subprocess as _sp
        _sp.Popen(["explorer", str(Path(path))], shell=False)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "리포트 파일 없음"})


@app.route("/screenshot")
def screenshot():
    """스크린샷 이미지 서빙."""
    path = request.args.get("path", "")
    p = Path(path)
    if not p.exists() or not p.is_file():
        return "Not found", 404
    return send_file(str(p), mimetype="image/png")


@app.route("/upload-screenshot", methods=["POST"])
def upload_screenshot():
    """편집 테이블에서 스크린샷 첨부 업로드."""
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "파일 없음"}), 400
    import uuid
    dest = BASE_DIR / "reports" / "screenshots" / f"manual_{uuid.uuid4().hex[:8]}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(dest))
    return jsonify({"ok": True, "url": f"/screenshot?path={dest}"})


@app.route("/download-report")
def download_report():
    """최종 HTML 리포트 다운로드."""
    path = _state.get("report_path")
    if not path or not Path(path).exists():
        return "리포트 없음", 404
    return send_file(str(path), as_attachment=True, download_name=Path(path).name)


@app.route("/finalize", methods=["POST"])
def finalize():
    """⑥ 편집 내용 확정 → 결함 항목 반영한 최종 HTML 덮어쓰기."""
    import json as _json

    data  = request.get_json() or {}
    items = data.get("items", [])
    log.info(f"확정 요청 | 결함 항목 {len(items)}건")

    html_path = _state.get("report_path")
    if not html_path:
        try:
            j = _json.loads((BASE_DIR / "reports" / "last_report.json").read_text(encoding="utf-8"))
            html_path = j.get("html_path", "")
        except Exception:
            pass

    if not html_path or not Path(html_path).exists():
        return jsonify({"ok": False, "error": "리포트 파일 없음"})

    import html as _html
    import re as _re

    STATUS_BADGE = {
        "pass":     ('<span class="badge pass">&#x2705; PASS</span>',          "pass"),
        "bug_low":  ('<span class="badge bug-low">&#x26A0;&#xFE0F; BUG &#xB0AE;&#xC74C;</span>', "bug-low"),
        "bug_high": ('<span class="badge bug-high">&#x1F534; BUG &#xB192;&#xC74C;</span>', "bug-high"),
        # 구버전 호환 (finalize JSON에 'bug'/'fail' 있을 수 있음)
        "bug":  ('<span class="badge bug-low">&#x26A0;&#xFE0F; BUG &#xB0AE;&#xC74C;</span>', "bug-low"),
        "fail": ('<span class="badge bug-high">&#x1F534; BUG &#xB192;&#xC74C;</span>', "bug-high"),
    }

    # 결함 카드 HTML — html_reporter의 defect-card 스타일과 동일
    cards_html = ""
    for issue_idx, it in enumerate(items, 1):
        st          = it.get("status", "fail")
        badge_html, css = STATUS_BADGE.get(st, STATUS_BADGE["fail"])
        page_label   = _html.escape(it.get("page", ""))
        pattern      = _html.escape(it.get("pattern", ""))
        label        = _html.escape(it.get("label", ""))
        detail       = _html.escape(it.get("detail", ""))
        user_opinion = _html.escape(it.get("user_opinion", ""))
        severity     = "높음" if st in ("bug_high", "fail", "error") else "낮음"
        manual_tag   = '<span class="manual-badge">&#x270F;&#xFE0F; 직접 등록</span>' if it.get("manual") else ""

        ss_html = ""
        ss_raw  = it.get("screenshot", "")
        if ss_raw:
            ss_path_str = ss_raw.replace("/screenshot?path=", "").strip()
            ss_p = Path(ss_path_str)
            if ss_p.exists():
                try:
                    import base64 as _b64
                    _ss_data = _b64.b64encode(ss_p.read_bytes()).decode("ascii")
                    _ss_mime = "image/png" if ss_p.suffix.lower() == ".png" else "image/jpeg"
                    ss_data_uri = f"data:{_ss_mime};base64,{_ss_data}"
                    ss_html = f"""
            <tr>
              <th>스크린샷</th>
              <td>
                <details>
                  <summary class="ss-toggle">&#x1F4F7; 스크린샷 보기</summary>
                  <img src="{ss_data_uri}" class="ss-img" alt="{label}">
                </details>
              </td>
            </tr>"""
                except Exception:
                    pass

        cards_html += f"""
        <div class="defect-card defect-{css}" data-page-key="{page_label}">
          <div class="defect-header">
            <span class="issue-num">#{issue_idx}</span>
            {badge_html}
            <span class="defect-page">{page_label}</span>
            <span class="defect-scenario">{pattern}</span>
            {manual_tag}
            <span class="defect-severity severity-{severity}">심각도: {severity}</span>
          </div>
          <div class="defect-title">{label}</div>
          <table class="defect-detail">
            <tr><th>QA Tool 결과</th><td>{detail}</td></tr>
            <tr><th>담당자 의견</th><td>{user_opinion if user_opinion else '<span style="color:#bbb;">—</span>'}</td></tr>
            {ss_html}
          </table>
        </div>"""

    cards_html = cards_html or '<p class="no-defect">🎉 확정된 결함 없음</p>'

    # 기존 HTML에서 결함 섹션 교체 (마커 기반)
    original     = Path(html_path).read_text(encoding="utf-8")
    no_defect_el = '<p class="tab-no-defect" id="tab-no-defect">[OK]  해당 페이지에 결함이 없습니다</p>'
    new_section  = f"""<!-- DEFECT_SECTION_START -->
  <div class="section">
    <div class="section-title">🐛 확정된 결함 ({len(items)}건) <span style="font-size:12px;font-weight:400;color:#888;">— QA 검토 완료</span></div>
    {cards_html}
    {no_defect_el}
  </div>
  <!-- DEFECT_SECTION_END -->"""

    # 치환문자열을 함수로 전달 — new_section 의 Windows 경로(\screenshots 등)가
    # re.sub 치환에서 이스케이프로 해석돼 'bad escape \s' 나는 것 방지 (2026-06-15).
    patched = _re.sub(
        r'<!-- DEFECT_SECTION_START -->.*?<!-- DEFECT_SECTION_END -->',
        lambda _m: new_section,
        original,
        flags=_re.DOTALL,
    )
    if patched == original:
        # 마커 없는 구버전 파일 fallback
        patched = _re.sub(
            r'<div class="section">\s*<div class="section-title">🐛 발견된 결함.*?</div>\s*</div>',
            lambda _m: new_section,
            original,
            flags=_re.DOTALL,
        )
    if patched == original:
        patched = original.replace("</body>", new_section + "\n</body>")

    # ── 수동 이슈 → 요약 카드 패치 ───────────────────────────────────
    # data-page-id 카드를 찾아서 fail/bug/total 카운트에 수동 항목 합산
    manual_by_page: dict[str, dict] = {}
    page_label_rev = {v: k for k, v in {
        "ransom_detect_policy":     "탐지정책",
        "rdp_policy":               "RDP 정책",
        "common_process":           "공통 프로세스",
        "common_operation_process": "운용 프로세스",
        "common_tag":               "태그 관리",
        "common_control_suite":     "제어 스위트",
        "npouch_origin_protect":    "원본 보호 정책",
        "npouch_policy":            "nPouch 정책",
    }.items()}
    for it in items:
        if not it.get("manual"):
            continue
        pg_label = it.get("page", "")
        pid = page_label_rev.get(pg_label, pg_label)
        st  = it.get("status", "fail")
        if pid not in manual_by_page:
            manual_by_page[pid] = {"fail": 0, "bug": 0}
        if st == "fail":
            manual_by_page[pid]["fail"] += 1
        elif st == "bug":
            manual_by_page[pid]["bug"] += 1

    if manual_by_page:
        import re as _re2

        def _extract_card_range(html_str: str, pid: str):
            """pid에 해당하는 summary-card div의 (start, end) 인덱스 반환. 없으면 (-1, -1)."""
            marker = f'data-page-id="{pid}"'
            marker_pos = html_str.find(marker)
            if marker_pos == -1:
                return -1, -1
            # marker 앞에서 가장 가까운 <div 찾기 (= 카드 루트 태그)
            start = html_str.rfind('<div', 0, marker_pos)
            if start == -1:
                return -1, -1
            # 중첩 깊이 카운팅으로 매칭 </div> 찾기
            depth = 0
            i = start
            while i < len(html_str):
                if html_str[i:i+4] == '<div':
                    depth += 1
                    i += 4
                elif html_str[i:i+6] == '</div>':
                    depth -= 1
                    i += 6
                    if depth == 0:
                        return start, i
                else:
                    i += 1
            return -1, -1

        for pid, mc in manual_by_page.items():
            start, end = _extract_card_range(patched, pid)
            if start == -1:
                continue
            card = patched[start:end]

            # auto 카운트 추출 (opening div 태그에 있음)
            auto_fail_m = _re2.search(r'data-auto-fail="(\d+)"', card)
            auto_bug_m  = _re2.search(r'data-auto-bug="(\d+)"',  card)
            auto_tot_m  = _re2.search(r'data-auto-total="(\d+)"', card)
            auto_fail = int(auto_fail_m.group(1)) if auto_fail_m else 0
            auto_bug  = int(auto_bug_m.group(1))  if auto_bug_m  else 0
            auto_tot  = int(auto_tot_m.group(1))  if auto_tot_m  else 0

            new_fail = auto_fail + mc["fail"]
            new_bug  = auto_bug  + mc["bug"]
            m_cnt    = mc["fail"] + mc["bug"]

            # fail/bug 카운트 업데이트 (HTML entity 이모지 버전에 맞춤)
            card = _re2.sub(r'(<span class="cnt fail"[^>]*>)&#x274C; \d+', f'\\g<1>&#x274C; {new_fail}', card)
            card = _re2.sub(r'(<span class="cnt bug"[^>]*>)&#x26A0;&#xFE0F; \d+', f'\\g<1>&#x26A0;&#xFE0F; {new_bug}', card)
            # card-total: 자동 N건 검증 → 자동 N건 수동 M건 검증
            card = _re2.sub(r'자동 \d+건 검증', f'자동 {auto_tot}건 수동 {m_cnt}건 검증', card)
            # has-fail 클래스 + 상태 텍스트 업데이트
            if new_fail > 0 and 'has-fail' not in card:
                card = _re2.sub(
                    r'class="summary-card (has-bug|all-pass)"',
                    'class="summary-card has-fail"',
                    card,
                )
                card = card.replace('🟡 버그 추적 중', '🔴 결함 있음').replace('🟢 정상', '🔴 결함 있음')

            patched = patched[:start] + card + patched[end:]

    Path(html_path).write_text(patched, encoding="utf-8")
    log.info(f"확정 완료 → {html_path}")
    return jsonify({"ok": True, "path": html_path})


# ── 진입점 ────────────────────────────────────────────────────────────

def _run_flask():
    app.run(port=5321, debug=False, use_reloader=False)


if __name__ == "__main__":
    import webbrowser
    import time as _time

    # Flask를 백그라운드 스레드로 실행
    t = threading.Thread(target=_run_flask, daemon=True)
    t.start()

    _FLASK_URL = "http://127.0.0.1:5321"

    # Flask 준비 대기 후 기본 브라우저로 열기
    _time.sleep(1)
    log.info(f"브라우저로 열기: {_FLASK_URL}")
    webbrowser.open(_FLASK_URL)

    # PyWebView — 브라우저와 함께 앱 창도 바로 오픈
    _webview_ok = False
    try:
        import webview
        _wv["window"] = webview.create_window(
            title="QA Tool",
            url=_FLASK_URL,
            width=1100,
            height=750,
            min_size=(900, 600),
            resizable=True,
        )
        _webview_ok = True
        webview.start()   # 블로킹
    except Exception as e:
        log.warning(f"pywebview 사용 불가 ({e}) — 브라우저로만 운영")

    if not _webview_ok:
        # pywebview 없으면 메인 스레드 유지 (Flask daemon 스레드 살려두기)
        try:
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            pass
