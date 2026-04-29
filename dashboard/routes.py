"""
dashboard/routes.py — QA Dashboard Flask Blueprint

prefix: /dashboard
"""
from __future__ import annotations

import logging
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)

from .db import (
    PRODUCT_META,
    get_dashboard_stats,
    get_product_stats,
    get_products,
    get_results,
    get_run,
    get_run_comparison,
    get_runs,
    import_report,
    init_db,
    upsert_qa_request,
    get_qa_requests,
    update_qa_request,
)
from core.innorelease_client import (
    get_client,
    INNO_PRODUCT_KO,
    INNO_PRODUCT_MAP,
    PIPELINE_STATUS_KO,
    PIPELINE_STATUS_COLOR,
)

log = logging.getLogger("qa_app.dashboard")

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="../templates",   # templates/ 루트 → dashboard/*.html 경로 해결
)


def _db_path() -> str:
    base_dir: Path = current_app.config["BASE_DIR"]
    db_path = base_dir / "data" / "qa.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def _toggle_url(product_id: str, selected_list: list[str]) -> str:
    """탭 클릭 시 이동할 URL 반환. 클릭된 제품을 선택/해제 토글."""
    if product_id == "all":
        return "?"  # 전체 선택 (all)
    new_list = [p for p in selected_list if p != product_id]
    if product_id not in selected_list:
        new_list = selected_list + [product_id]
    if not new_list:
        return "?"
    return "?" + "&".join(f"p={p}" for p in new_list)


def _product_tabs(db: str, selected_list: list[str]) -> list[dict]:
    """탭 목록 생성 (DB에 있는 제품만 표시, 실행 횟수 포함)."""
    # DB에 있는 제품별 통계
    prod_stats = get_product_stats(db)
    # 전체 실행 수
    all_stats = get_dashboard_stats(db)
    total_runs = all_stats["total_runs"]

    is_all = not selected_list

    tabs = [{
        "id":     "all",
        "label":  "전체",
        "color":  "#6c757d",
        "count":  total_runs,
        "active": is_all,
        "href":   _toggle_url("all", selected_list),
    }]

    for ps in prod_stats:
        pid = ps["product"]
        active = pid in selected_list
        tabs.append({
            "id":     pid,
            "label":  ps["label"],
            "color":  ps["color"],
            "count":  ps["total"],
            "active": active,
            "href":   _toggle_url(pid, selected_list),
        })

    return tabs


# ─── 라우트 ──────────────────────────────────────────────────────────────────

@dashboard_bp.route("/")
def index():
    """대시보드 메인 화면."""
    db     = _db_path()
    p_list = request.args.getlist("p")
    products = p_list if p_list else None

    stats         = get_dashboard_stats(db, products=products)
    recent_runs   = get_runs(db, limit=10, products=products)
    tabs          = _product_tabs(db, p_list)
    product_stats = get_product_stats(db)

    return render_template(
        "dashboard/index.html",
        stats=stats,
        recent_runs=recent_runs,
        tabs=tabs,
        product_stats=product_stats,
        selected_products=p_list,
    )


@dashboard_bp.route("/runs")
def runs():
    """실행 이력 목록 화면."""
    db     = _db_path()
    p_list = request.args.getlist("p")
    products = p_list if p_list else None

    all_runs = get_runs(db, limit=200, products=products)
    tabs     = _product_tabs(db, p_list)

    return render_template(
        "dashboard/runs.html",
        runs=all_runs,
        tabs=tabs,
        selected_products=p_list,
    )


@dashboard_bp.route("/runs/<int:run_id>")
def run_detail(run_id: int):
    """단일 실행 상세 화면."""
    db      = _db_path()
    run     = get_run(db, run_id)
    if run is None:
        return "실행 이력을 찾을 수 없습니다.", 404
    results  = get_results(db, run_id)
    run_diff = get_run_comparison(db, run_id)
    return render_template(
        "dashboard/run_detail.html",
        run=run,
        results=results,
        run_diff=run_diff,
    )


@dashboard_bp.route("/report/<int:run_id>")
def serve_report(run_id: int):
    """원본 HTML 리포트 파일 서빙."""
    db  = _db_path()
    run = get_run(db, run_id)
    if run is None or not run["html_path"]:
        return "리포트 파일 없음", 404
    p = Path(run["html_path"])
    if not p.exists():
        return "리포트 파일 없음 (파일 삭제됨)", 404
    return send_file(str(p), mimetype="text/html")


@dashboard_bp.route("/import", methods=["POST"])
def import_reports():
    """
    reports/ 디렉토리의 QA HTML 파일 전체를 일괄 import.
    JSON 응답 반환.
    """
    base_dir: Path = current_app.config["BASE_DIR"]
    db = _db_path()

    html_files = sorted(base_dir.glob("reports/**/QA_*.html"))
    if not html_files:
        html_files = sorted(base_dir.glob("reports/QA_*.html"))

    imported = 0
    skipped  = 0
    errors   = 0

    try:
        from core.report_parser import parse_report
    except ImportError as e:
        log.error(f"[ERR] report_parser import 실패: {e}")
        return jsonify({"ok": False, "message": f"report_parser 로드 실패: {e}"}), 500

    for html_file in html_files:
        try:
            parsed = parse_report(str(html_file))
            if parsed is None:
                errors += 1
                continue
            run_id = import_report(db, parsed)
            if run_id is None:
                skipped += 1
            else:
                imported += 1
        except Exception as e:
            log.warning(f"[WARN] import 실패: {html_file.name} — {e}")
            errors += 1

    msg = f"import {imported}건 완료"
    if skipped:
        msg += f" / {skipped}건 중복 skip"
    if errors:
        msg += f" / {errors}건 오류"

    log.info(f"[OK] 일괄 import: {msg} (파일 {len(html_files)}건 처리)")
    return jsonify({
        "ok":       True,
        "message":  msg,
        "imported": imported,
        "skipped":  skipped,
        "errors":   errors,
    })


@dashboard_bp.route("/import-file", methods=["POST"])
def import_file():
    """
    로컬 QA 앱에서 HTML 리포트를 multipart/form-data로 전송받아 DB에 import.

    요청 형식:
        POST /dashboard/import-file
        Content-Type: multipart/form-data
        Body: report=<HTML 파일>
    """
    from werkzeug.utils import secure_filename

    f = request.files.get("report")
    if not f:
        return jsonify({"ok": False, "message": "report 파일 없음"}), 400

    base_dir: Path = current_app.config["BASE_DIR"]
    save_dir = base_dir / "reports" / "remote"
    save_dir.mkdir(parents=True, exist_ok=True)

    filename  = secure_filename(f.filename or "report.html")
    save_path = save_dir / filename
    f.save(str(save_path))
    log.info(f"[OK] 수신 파일 저장: {save_path}")

    try:
        from core.report_parser import parse_report
        parsed = parse_report(str(save_path))
        if not parsed:
            return jsonify({"ok": False, "message": "HTML 파싱 실패"}), 400

        db     = _db_path()
        run_id = import_report(db, parsed)
        if run_id:
            log.info(f"[OK] 원격 import 완료: run_id={run_id} ({parsed['product']})")
            return jsonify({"ok": True, "run_id": run_id, "message": "import 완료"})
        else:
            log.info(f"[SKIP] 중복 리포트: {filename}")
            return jsonify({"ok": True, "run_id": None, "message": "중복 skip"})

    except Exception as e:
        log.error(f"[ERR] import-file 처리 오류: {e}")
        return jsonify({"ok": False, "message": str(e)}), 500


@dashboard_bp.route("/api/stats")
def api_stats():
    """Chart.js용 통계 JSON API (product 필터 지원)."""
    db     = _db_path()
    p_list = request.args.getlist("p")
    products = p_list if p_list else None
    stats  = get_dashboard_stats(db, products=products)
    return jsonify(stats)


@dashboard_bp.route("/api/runs")
def api_runs():
    """
    React 대시보드용 실행 이력 JSON API.
    ?p=제품명 필터 지원, ?limit=N (기본 200)
    """
    db       = _db_path()
    p_list   = request.args.getlist("p")
    limit    = request.args.get("limit", 200, type=int)
    products = p_list if p_list else None
    rows     = get_runs(db, limit=limit, products=products)
    return jsonify([dict(r) for r in rows])


@dashboard_bp.route("/api/runs/<int:run_id>")
def api_run_detail(run_id: int):
    """
    React 대시보드용 단일 실행 상세 JSON API.
    run 정보 + results 목록 + 이전 run과 비교(diff) 포함.
    """
    db      = _db_path()
    run     = get_run(db, run_id)
    if run is None:
        return jsonify({"error": "not found"}), 404
    results  = get_results(db, run_id)
    run_diff = get_run_comparison(db, run_id)
    return jsonify({
        "run":      dict(run),
        "results":  [dict(r) for r in results],
        "diff":     run_diff,
        "report_url": f"/dashboard/report/{run_id}" if run["html_path"] else None,
    })


@dashboard_bp.route("/api/qa-requests")
def api_qa_requests():
    """
    React 대시보드용 QA 요청 큐 JSON API.
    ?status=TESTING 필터 지원.
    """
    db         = _db_path()
    status_f   = request.args.get("status")   # 없으면 전체
    rows       = get_qa_requests(db)
    data = [dict(r) for r in rows]
    if status_f:
        data = [r for r in data if r.get("status") == status_f]
    return jsonify(data)


# ─── innoRelease 연동 라우트 ─────────────────────────────────────────────────

@dashboard_bp.route("/innorelease")
def innorelease():
    """innoRelease 연동 페이지 — 파이프라인 + QA 레코드 현황."""
    client = get_client()
    connected = client is not None

    # 설정에서 URL 확인
    irel_url = current_app.config.get("INNORELEASE_URL", "")

    return render_template(
        "dashboard/innorelease.html",
        connected=connected,
        irel_url=irel_url,
        product_map=INNO_PRODUCT_KO,
        status_ko=PIPELINE_STATUS_KO,
        status_color=PIPELINE_STATUS_COLOR,
    )


@dashboard_bp.route("/innorelease/api/pipelines")
def irel_pipelines():
    """JSON — innoRelease 파이프라인 목록 (실시간 조회)."""
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    status_filter = request.args.get("status")  # 없으면 전체
    pipelines = client.get_pipelines(status=status_filter)
    return jsonify({"ok": True, "data": pipelines, "total": len(pipelines)})


@dashboard_bp.route("/innorelease/api/qa")
def irel_qa():
    """JSON — innoRelease QA 레코드 목록 (제품별 또는 전체)."""
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    product_code = request.args.get("product", type=int)  # None이면 전체
    page = request.args.get("page", 0, type=int)
    size = request.args.get("size", 20, type=int)

    if product_code:
        records = client.get_qa_records(inno_product=product_code, page=page, size=size)
        for r in records:
            r["productKo"] = INNO_PRODUCT_KO.get(product_code, str(product_code))
    else:
        records = client.get_all_qa_records(size=size)

    return jsonify({"ok": True, "data": records, "total": len(records)})


@dashboard_bp.route("/innorelease/api/pipelines/<int:pipeline_id>/approve", methods=["POST"])
def irel_approve(pipeline_id: int):
    """POST — 파이프라인 QA 승인."""
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    body    = request.get_json(silent=True) or {}
    comment = body.get("comment", "")
    ok      = client.approve_pipeline(pipeline_id, comment=comment)
    return jsonify({"ok": ok, "message": "승인 완료" if ok else "승인 실패"})


@dashboard_bp.route("/innorelease/api/pipelines/<int:pipeline_id>/reject", methods=["POST"])
def irel_reject(pipeline_id: int):
    """POST — 파이프라인 QA 반려."""
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    body   = request.get_json(silent=True) or {}
    reason = body.get("reason", "")
    ok     = client.reject_pipeline(pipeline_id, reason=reason)
    return jsonify({"ok": ok, "message": "반려 완료" if ok else "반려 실패"})


@dashboard_bp.route("/innorelease/api/post-result", methods=["POST"])
def irel_post_result():
    """
    POST — 우리 QA 결과를 innoRelease에 등록.
    Body JSON:
        {repo_id, inno_product, platform, record_date,
         new_features, updates, errors_bugs, pipeline_id?, run_id?}
    run_id가 있으면 해당 HTML 리포트를 첨부파일로 전송.
    """
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    body = request.get_json(silent=True) or {}
    repo_id      = body.get("repo_id")
    inno_product = body.get("inno_product")
    platform     = body.get("platform", "Windows")
    record_date  = body.get("record_date")
    new_features = body.get("new_features", "")
    updates      = body.get("updates", "")
    errors_bugs  = body.get("errors_bugs", "")
    pipeline_id  = body.get("pipeline_id")
    run_id       = body.get("run_id")

    if not repo_id or not inno_product or not record_date:
        return jsonify({"ok": False, "error": "repo_id, inno_product, record_date 필수"}), 400

    # run_id가 있으면 HTML 리포트 경로 조회
    html_path: str | None = None
    if run_id:
        db  = _db_path()
        run = get_run(db, int(run_id))
        if run and run["html_path"]:
            p = Path(run["html_path"])
            if p.exists():
                html_path = str(p)

    ok = client.post_qa_result(
        repo_id=int(repo_id),
        inno_product=int(inno_product),
        platform=platform,
        record_date=record_date,
        new_features=new_features,
        updates=updates,
        errors_bugs=errors_bugs,
        pipeline_id=int(pipeline_id) if pipeline_id else None,
        html_file_path=html_path,
    )
    return jsonify({"ok": ok, "message": "innoRelease 등록 완료" if ok else "등록 실패"})


# ─── QA Queue (사이클 통합) ─────────────────────────────────────────────────

@dashboard_bp.route("/qa-queue")
def qa_queue():
    """QA 요청 큐 페이지 — TESTING 파이프라인 수신 및 결과 전송."""
    db       = _db_path()
    requests = get_qa_requests(db)
    irel_url = current_app.config.get("INNORELEASE_URL", "")
    client   = get_client()
    return render_template(
        "dashboard/qa_queue.html",
        qa_requests=requests,
        irel_url=irel_url,
        connected=client is not None,
        product_map=INNO_PRODUCT_KO,
    )


@dashboard_bp.route("/qa-queue/sync", methods=["POST"])
def qa_queue_sync():
    """
    innoRelease에서 TESTING 파이프라인을 가져와 qa_requests에 저장.
    새로 발견된 파이프라인 수를 반환.
    """
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    db       = _db_path()
    pipelines = client.get_pipelines(status="TESTING")
    new_count = 0

    for p in pipelines:
        existing = [r for r in get_qa_requests(db) if r["pipeline_id"] == p["id"]]
        if not existing:
            upsert_qa_request(db, p)
            new_count += 1
        else:
            # 상태가 바뀐 경우 동기화
            if existing[0]["status"] == "TESTING" and p.get("status") != "TESTING":
                update_qa_request(db, p["id"], status=p["status"])

    return jsonify({"ok": True, "total": len(pipelines), "new": new_count})


@dashboard_bp.route("/qa-queue/<int:pipeline_id>/set-test-url", methods=["POST"])
def qa_queue_set_test_url(pipeline_id: int):
    """테스트 대상 URL 저장 (테스터가 직접 입력한 VM/서버 주소)."""
    db       = _db_path()
    body     = request.get_json(silent=True) or {}
    test_url = body.get("test_url", "").strip()
    if not test_url:
        return jsonify({"ok": False, "error": "test_url 필수"}), 400
    update_qa_request(db, pipeline_id, test_url=test_url)
    return jsonify({"ok": True})


@dashboard_bp.route("/qa-queue/<int:pipeline_id>/refresh-env", methods=["POST"])
def qa_queue_refresh_env(pipeline_id: int):
    """
    innoRelease '테스트 환경 갱신' 프록시.
    Body: { agent_id: number }
    → POST /innorelease/api/pipelines/{id}/refresh { agentId }
    """
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    body     = request.get_json(silent=True) or {}
    agent_id = body.get("agent_id")
    if not agent_id:
        return jsonify({"ok": False, "error": "agent_id 필수"}), 400

    try:
        if not client._ensure_login():
            return jsonify({"ok": False, "error": "innoRelease 로그인 실패"}), 503
        resp = client._session.post(
            f"{client.base_url}/innorelease/api/pipelines/{pipeline_id}/refresh",
            json={"agentId": int(agent_id)},
            timeout=15,
        )
        ok = resp.status_code == 200
        log.info(f"[refresh-env] pipeline={pipeline_id} agent={agent_id} status={resp.status_code}")
        return jsonify({"ok": ok, "message": "환경 갱신 요청 완료" if ok else f"실패({resp.status_code})"})
    except Exception as e:
        log.error(f"[ERR] refresh-env: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@dashboard_bp.route("/qa-queue/<int:pipeline_id>/set-product", methods=["POST"])
def qa_queue_set_product(pipeline_id: int):
    """파이프라인에 innoProduct 코드 매핑 저장."""
    db           = _db_path()
    body         = request.get_json(silent=True) or {}
    inno_product = body.get("inno_product")
    if not inno_product:
        return jsonify({"ok": False, "error": "inno_product 필수"}), 400
    update_qa_request(db, pipeline_id, inno_product=int(inno_product))
    return jsonify({"ok": True})


@dashboard_bp.route("/qa-queue/<int:pipeline_id>/complete", methods=["POST"])
def qa_queue_complete(pipeline_id: int):
    """
    테스트 완료 후 innoRelease에 결과 전송 + 승인/반려 처리.
    Body: { action: "approve"|"reject", comment: "", run_id: N, inno_product: N }
    """
    client = get_client()
    if client is None:
        return jsonify({"ok": False, "error": "innoRelease 미설정"}), 503

    db           = _db_path()
    body         = request.get_json(silent=True) or {}
    action       = body.get("action")        # "approve" or "reject"
    comment      = body.get("comment", "")
    run_id       = body.get("run_id")
    inno_product = body.get("inno_product")
    repo_id      = body.get("repo_id")
    platform     = body.get("platform", "MANAGER")

    # ① innoRelease QA 레코드 등록
    qa_ok = False
    if run_id and inno_product and repo_id:
        run = get_run(db, int(run_id))
        if run:
            from datetime import date as _date
            html_path = run["html_path"] if run["html_path"] and Path(run["html_path"]).exists() else None

            # 테스트 결과 요약 텍스트 생성
            total    = run["total"] or 0
            pass_cnt = run["pass_cnt"] or 0
            fail_cnt = run["fail_cnt"] or 0
            bug_cnt  = run["bug_cnt"]  or 0
            err_cnt  = run["error_cnt"] or 0
            pass_rate = round(pass_cnt / total * 100, 1) if total > 0 else 0

            errors_bugs_text = ""
            if fail_cnt or bug_cnt or err_cnt:
                errors_bugs_text = (
                    f"FAIL: {fail_cnt}건, BUG: {bug_cnt}건, ERROR: {err_cnt}건\n"
                    f"PASS율: {pass_rate}%"
                )

            qa_ok = client.post_qa_result(
                repo_id=int(repo_id),
                inno_product=int(inno_product),
                platform=platform,
                record_date=_date.today().isoformat(),
                updates=f"전체: {total}건, PASS: {pass_cnt}건",
                errors_bugs=errors_bugs_text,
                pipeline_id=pipeline_id,
                html_file_path=html_path,
            )
            log.info(f"[QA등록] pipeline={pipeline_id} qa_ok={qa_ok}")

    # ② 파이프라인 승인 / 반려
    # 승인 시 testEnvInfo에 우리 대시보드 결과 URL 포함
    action_ok = False
    if action == "approve":
        test_env_info = comment
        if run_id:
            irel_url = current_app.config.get("INNORELEASE_URL", "")
            # 결과 리포트 URL을 testEnvInfo에 포함 (innoRelease 승인 이력에 기록됨)
            qa_server = current_app.config.get("QA_SERVER_URL", "")
            if qa_server and run_id:
                test_env_info = f"{comment}\nQA 결과: {qa_server.rstrip('/')}/dashboard/runs/{run_id}".strip()
        action_ok = client.approve_pipeline(pipeline_id, comment=comment, test_env_info=test_env_info)
    elif action == "reject":
        action_ok = client.reject_pipeline(pipeline_id, reason=comment)

    # ③ 로컬 DB 상태 갱신
    result_str = "APPROVED" if action == "approve" else "REJECTED"
    update_qa_request(db, pipeline_id,
                      status=result_str,
                      result=result_str,
                      run_id=run_id)

    return jsonify({
        "ok":        action_ok,
        "qa_ok":     qa_ok,
        "action_ok": action_ok,
        "message":   f"{'승인' if action == 'approve' else '반려'} 완료" if action_ok else "처리 실패",
    })
