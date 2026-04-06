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

# ── 경로 설정 ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── 로그 설정 ─────────────────────────────────────────────────────────
_LOG_DIR = BASE_DIR / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),          # CMD 창에도 동시 출력
    ],
)
log = logging.getLogger("qa_app")
log.info(f"=== QA Tool 시작 === 로그 파일: {_LOG_FILE}")

app = Flask(__name__, template_folder=str(BASE_DIR / "templates" / "app"))

# ── 실행 상태 (세션 단위) ─────────────────────────────────────────────
_state: dict = {
    "product":         None,   # 선택된 제품 ID
    "pages":           [],     # 선택된 page_id 목록
    "status":          "idle", # idle / running / done / error
    "page_status":     {},     # {page_id: "waiting"|"running"|"done"|"error"}
    "scenario_status": {},     # {page_id: [{"label":..., "status":"pending"|"running"|"done"}]}
    "error_log":       "",
    "report_path":     None,
}
_proc: subprocess.Popen | None = None


# ── 시나리오 사전 정의 ──────────────────────────────────────────────

_MODAL_SCENARIOS = [
    {"num": 1, "label": "시나리오 1: 구조 확인  (초기값 + 필수입력 검증)", "status": "pending"},
    {"num": 2, "label": "시나리오 2: 동작 검증  (UI 인터랙션 + 중복 처리)", "status": "pending"},
    {"num": 3, "label": "시나리오 3: 수정 시나리오  (저장값 로드 + 재확인)", "status": "pending"},
    {"num": 4, "label": "시나리오 4: 케이스 검증  (Case A 전체 ON / Case B 전체 OFF)", "status": "pending"},
]
_LIST_SCENARIOS = [
    {"num": 1, "label": "시나리오 1: UI 구조  (탭 · 버튼 · 테이블)", "status": "pending"},
    {"num": 2, "label": "시나리오 2: 입력 동작  (모달 필드 · 필수입력 검증)", "status": "pending"},
    {"num": 3, "label": "시나리오 3: CRUD  (추가 · 수정 · 검색 · 삭제)", "status": "pending"},
]


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
        label_map = {"ransom_cruncher": "랜섬크런처"}
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
            "ransom_detect_policy": "탐지정책",
            "rdp_policy":           "RDP 정책",
            "common_process":       "공통 프로세스",
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
    # 선택된 페이지의 라벨 포함해서 전달
    all_pages  = _get_pages(product_id)
    selected   = [p for p in all_pages if p["id"] in page_ids]
    # 선택 안 된 페이지도 흐리게 보여주기 위해 전체 포함
    pages_info = [
        {**p, "selected": p["id"] in page_ids}
        for p in all_pages
    ]
    product_label_map = {"ransom_cruncher": "RansomCruncher"}
    log.info(f"화면: 실행 설정 | 선택된 페이지={page_ids}")
    return render_template(
        "run_setup.html",
        pages=page_ids,
        pages_info=pages_info,
        product_id=product_id,
        product_label=product_label_map.get(product_id, product_id),
    )


@app.route("/start", methods=["POST"])
def start():
    """테스트 subprocess 실행."""
    global _proc
    data      = request.get_json()
    test_id   = data.get("test_id", "")
    test_pw   = data.get("test_pw", "")
    headless  = bool(data.get("headless", False))
    page_ids  = _state.get("pages", [])

    if not page_ids or not test_id or not test_pw:
        log.warning(f"시작 실패 — 필수 입력 누락 | id={test_id!r} pages={page_ids}")
        return jsonify({"ok": False, "error": "필수 입력 누락"}), 400

    if _state["status"] == "running":
        log.warning("시작 실패 — 이미 실행 중")
        return jsonify({"ok": False, "error": "이미 실행 중"}), 400

    log.info(f"테스트 시작 | ID={test_id} | 대상={page_ids} | headless={headless}")

    # 상태 초기화 — 첫 번째 페이지는 즉시 running으로 (pytest 로딩 중 대기 없이 표시)
    _state["status"]          = "running"
    _state["error_log"]       = ""
    _state["report_path"]     = None
    _state["page_status"]     = {
        pid: ("running" if i == 0 else "waiting")
        for i, pid in enumerate(page_ids)
    }
    _state["scenario_status"] = {pid: _get_default_scenarios(pid) for pid in page_ids}

    # pytest -k 필터 조합
    k_filter = " or ".join(page_ids)

    env = os.environ.copy()
    env["TEST_ID"] = test_id
    env["TEST_PW"] = test_pw
    env["TEST_HEADLESS"] = "1" if headless else "0"

    cmd = [
        sys.executable, "-u", "-m", "pytest",
        "tests/test_scan_pages.py",
        "-v", "-s", "-k", k_filter,
    ]
    env["PYTHONUNBUFFERED"] = "1"

    def _run():
        import re as _re
        _SC_RE = _re.compile(r'시나리오\s+(\d+)\s*[:\uff1a]\s*(.+)')

        global _proc
        try:
            log.info(f"pytest 실행: {' '.join(cmd)}")
            _proc = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            log.info(f"pytest PID={_proc.pid}")

            current_page = None
            error_lines: list[str] = []

            for line in _proc.stdout:
                line = line.rstrip()
                if not line:
                    continue

                # pytest 출력 전체를 로그에 기록 (DEBUG 레벨)
                log.debug(f"[pytest] {line}")

                # 현재 스캔 중인 페이지 감지
                for pid in page_ids:
                    if f"test_page_scan[{pid}]" in line:
                        if current_page and current_page != pid:
                            for sc in _state["scenario_status"].get(current_page, []):
                                if sc["status"] != "done":
                                    sc["status"] = "done"
                        if current_page != pid:
                            log.info(f"페이지 전환: {current_page} → {pid}")
                        current_page = pid
                        _state["page_status"][pid] = "running"

                # 시나리오 헤더 감지
                if current_page:
                    m = _SC_RE.search(line)
                    if m:
                        sc_num   = int(m.group(1))
                        sc_label = m.group(2).strip().strip("─═ \t")
                        sc_list  = _state["scenario_status"][current_page]
                        for sc in sc_list:
                            if sc["status"] == "running":
                                sc["status"] = "done"
                        existing = next((s for s in sc_list if s["num"] == sc_num), None)
                        if existing:
                            existing["status"] = "running"
                        else:
                            sc_list.append({
                                "num":    sc_num,
                                "label":  f"시나리오 {sc_num}: {sc_label}",
                                "status": "running",
                            })
                        log.info(f"  [{current_page}] 시나리오 {sc_num} 시작: {sc_label}")

                # pytest 결과 줄 감지
                if current_page and "test_page_scan" in line:
                    if line.lstrip().startswith("PASSED"):
                        for sc in _state["scenario_status"].get(current_page, []):
                            sc["status"] = "done"
                        _state["page_status"][current_page] = "done"
                        log.info(f"  [{current_page}] PASSED ✅")
                    elif line.lstrip().startswith("FAILED"):
                        for sc in _state["scenario_status"].get(current_page, []):
                            if sc["status"] in ("running", "pending"):
                                sc["status"] = "done"
                        _state["page_status"][current_page] = "error"
                        log.warning(f"  [{current_page}] FAILED ❌")

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
                # 최신 HTML 리포트 경로 찾기
                reports = sorted(
                    BASE_DIR.glob("reports/QA_*.html"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if reports:
                    _state["report_path"] = str(reports[0])
                    log.info(f"HTML 리포트: {reports[0]}")
                # 미완료 페이지 + 시나리오 전부 done 처리 (returncode=0 보장)
                for pid in page_ids:
                    for sc in _state["scenario_status"].get(pid, []):
                        sc["status"] = "done"
                    if _state["page_status"][pid] != "error":
                        _state["page_status"][pid] = "done"
            else:
                _state["status"] = "error"

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


@app.route("/report")
def report():
    """⑤ 1차 리포트 편집 화면."""
    return render_template("report.html")


@app.route("/report-data")
def report_data():
    """리포트 데이터 API — 전체 결과 + 결함 목록."""
    json_path = BASE_DIR / "reports" / "last_report.json"
    if not json_path.exists():
        return jsonify({"pages": [], "html_path": None})
    try:
        import json as _json
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
        "pass": ('<span class="badge pass">✅ PASS</span>', "pass"),
        "bug":  ('<span class="badge bug">⚠️ BUG</span>',  "bug"),
        "fail": ('<span class="badge fail">❌ FAIL</span>', "fail"),
    }

    # 결함 카드 HTML — html_reporter의 defect-card 스타일과 동일
    cards_html = ""
    for it in items:
        st          = it.get("status", "fail")
        badge_html, css = STATUS_BADGE.get(st, STATUS_BADGE["fail"])
        page_label   = _html.escape(it.get("page", ""))
        pattern      = _html.escape(it.get("pattern", ""))
        label        = _html.escape(it.get("label", ""))
        detail       = _html.escape(it.get("detail", ""))
        user_opinion = _html.escape(it.get("user_opinion", ""))
        severity     = "높음" if st in ("fail", "error") else "낮음"
        manual_tag   = '<span class="manual-badge">✏️ 직접 등록</span>' if it.get("manual") else ""

        ss_html = ""
        ss_raw  = it.get("screenshot", "")
        if ss_raw:
            ss_path_str = ss_raw.replace("/screenshot?path=", "").strip()
            ss_p = Path(ss_path_str)
            if ss_p.exists():
                ss_uri = ss_p.resolve().as_posix()
                ss_html = f"""
            <tr>
              <th>스크린샷</th>
              <td>
                <details>
                  <summary class="ss-toggle">📷 스크린샷 보기</summary>
                  <img src="{ss_uri}" class="ss-img" alt="{label}">
                </details>
              </td>
            </tr>"""

        cards_html += f"""
        <div class="defect-card defect-{css}" data-page-key="{page_label}">
          <div class="defect-header">
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
    no_defect_el = '<p class="tab-no-defect" id="tab-no-defect">✅ 해당 페이지에 결함이 없습니다</p>'
    new_section  = f"""<!-- DEFECT_SECTION_START -->
  <div class="section">
    <div class="section-title">🐛 확정된 결함 ({len(items)}건) <span style="font-size:12px;font-weight:400;color:#888;">— QA 검토 완료</span></div>
    {cards_html}
    {no_defect_el}
  </div>
  <!-- DEFECT_SECTION_END -->"""

    patched = _re.sub(
        r'<!-- DEFECT_SECTION_START -->.*?<!-- DEFECT_SECTION_END -->',
        new_section,
        original,
        flags=_re.DOTALL,
    )
    if patched == original:
        # 마커 없는 구버전 파일 fallback
        patched = _re.sub(
            r'<div class="section">\s*<div class="section-title">🐛 발견된 결함.*?</div>\s*</div>',
            new_section,
            original,
            flags=_re.DOTALL,
        )
    if patched == original:
        patched = original.replace("</body>", new_section + "\n</body>")

    Path(html_path).write_text(patched, encoding="utf-8")
    log.info(f"확정 완료 → {html_path}")
    return jsonify({"ok": True, "path": html_path})


# ── 진입점 ────────────────────────────────────────────────────────────

def _run_flask():
    app.run(port=5321, debug=False, use_reloader=False)


if __name__ == "__main__":
    import webview

    # Flask를 백그라운드 스레드로 실행
    t = threading.Thread(target=_run_flask, daemon=True)
    t.start()

    # PyWebView 앱 창 오픈
    webview.create_window(
        title="QA Tool",
        url="http://127.0.0.1:5321",
        width=1100,
        height=750,
        min_size=(900, 600),
        resizable=True,
    )
    webview.start()
