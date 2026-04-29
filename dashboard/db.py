"""
dashboard/db.py — SQLite DB 관리 모듈

data/qa.db 에 QA 실행 이력과 결과를 저장.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger("qa_app.dashboard.db")

# 제품 메타 (색상 매핑)
PRODUCT_META = {
    "RansomCruncher": {"label": "랜섬크런처", "color": "#e74c3c"},
    "SecureZone":     {"label": "시큐어존",   "color": "#27ae60"},
    "nPouch":         {"label": "엔파우치",   "color": "#9b59b6"},
    "innoECM":        {"label": "innoECM",   "color": "#e67e22"},
    "LizardBackup":   {"label": "리자드백업", "color": "#1abc9c"},
    "CommonPolicy":   {"label": "공통정책",   "color": "#34495e"},
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product     TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    html_path   TEXT    UNIQUE,
    total       INTEGER DEFAULT 0,
    pass_cnt    INTEGER DEFAULT 0,
    fail_cnt    INTEGER DEFAULT 0,
    bug_cnt     INTEGER DEFAULT 0,
    error_cnt   INTEGER DEFAULT 0,
    skip_cnt    INTEGER DEFAULT 0,
    pipeline_id INTEGER,
    version     TEXT,
    target      TEXT,
    imported_at TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES runs(id),
    page_label  TEXT,
    scenario    TEXT,
    label       TEXT,
    status      TEXT,
    expected    TEXT,
    actual      TEXT
);

CREATE TABLE IF NOT EXISTS qa_requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id    INTEGER NOT NULL UNIQUE,
    repo_id        INTEGER,
    repo_name      TEXT,
    branch         TEXT,
    version_hint   TEXT,
    release_target TEXT,
    inno_product   INTEGER,
    test_url       TEXT,                   -- 테스트 대상 서버 URL (테스터가 직접 입력)
    status         TEXT DEFAULT 'TESTING',
    run_id         INTEGER,
    result         TEXT,
    received_at    TEXT DEFAULT (datetime('now','localtime')),
    updated_at     TEXT DEFAULT (datetime('now','localtime'))
);
"""


def get_db(db_path: str) -> sqlite3.Connection:
    """sqlite3 connection 반환 (row_factory=sqlite3.Row)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """테이블 생성 (없는 경우에만) + 컬럼 마이그레이션."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_db(db_path) as conn:
        conn.executescript(_SCHEMA)
        # runs 테이블 신규 컬럼 마이그레이션 (기존 DB 호환)
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()
        }
        for col, ddl in [
            ("pipeline_id", "INTEGER"),
            ("version",     "TEXT"),
            ("target",      "TEXT"),
        ]:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {ddl}")
                log.info(f"[DB 마이그레이션] runs.{col} 컬럼 추가")

        # qa_requests 테이블 신규 컬럼 마이그레이션
        qa_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(qa_requests)").fetchall()
        }
        for col, ddl in [
            ("test_url", "TEXT"),
        ]:
            if col not in qa_cols:
                conn.execute(f"ALTER TABLE qa_requests ADD COLUMN {col} {ddl}")
                log.info(f"[DB 마이그레이션] qa_requests.{col} 컬럼 추가")
        conn.commit()
    log.info(f"[OK] DB 초기화 완료: {db_path}")


def import_report(db_path: str, parsed: dict) -> int | None:
    """
    parsed_dict를 runs + results 테이블에 삽입.
    html_path가 이미 존재하면 skip (중복 import 방지).
    run_id 반환. skip 시 None 반환.
    """
    html_path = parsed.get("html_path", "")
    timestamp = parsed.get("timestamp", "")
    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()

    with get_db(db_path) as conn:
        # 중복 체크
        existing = conn.execute(
            "SELECT id FROM runs WHERE html_path = ?", (html_path,)
        ).fetchone()
        if existing:
            log.info(f"[SKIP] 이미 import된 리포트: {html_path}")
            return None

        # runs 삽입
        cur = conn.execute(
            """
            INSERT INTO runs (product, timestamp, html_path, total, pass_cnt, fail_cnt, bug_cnt, error_cnt, skip_cnt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parsed.get("product", "Unknown"),
                timestamp,
                html_path,
                parsed.get("total", 0),
                parsed.get("pass", 0),
                parsed.get("fail", 0),
                parsed.get("bug", 0),
                parsed.get("error", 0),
                parsed.get("skip", 0),
            ),
        )
        run_id = cur.lastrowid

        # results 삽입
        results = parsed.get("results", [])
        conn.executemany(
            """
            INSERT INTO results (run_id, page_label, scenario, label, status, expected, actual)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    r.get("page_label", ""),
                    r.get("scenario", ""),
                    r.get("label", ""),
                    r.get("status", ""),
                    r.get("expected", ""),
                    r.get("actual", ""),
                )
                for r in results
            ],
        )
        conn.commit()

    log.info(f"[OK] import 완료: run_id={run_id} | results={len(results)}건")
    return run_id


def _build_in_clause(products: list[str] | None) -> tuple[str, list]:
    """products 리스트로 WHERE IN 절 및 파라미터 생성."""
    if not products:
        return "", []
    placeholders = ",".join("?" * len(products))
    return f"AND product IN ({placeholders})", list(products)


def get_runs(db_path: str, limit: int = 50, products: list[str] | None = None) -> list[sqlite3.Row]:
    """최근 실행 목록 반환 (최신순). products 지정 시 해당 제품들만 필터."""
    in_clause, in_params = _build_in_clause(products)
    with get_db(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM runs WHERE 1=1 {in_clause} ORDER BY id DESC LIMIT ?",
            in_params + [limit],
        ).fetchall()
    return rows


def get_run(db_path: str, run_id: int) -> sqlite3.Row | None:
    """단일 run 정보 반환."""
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
    return row


def get_results(db_path: str, run_id: int) -> list[sqlite3.Row]:
    """해당 run의 results 목록 반환."""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM results WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
    return rows


def upsert_qa_request(db_path: str, pipeline: dict) -> None:
    """innoRelease TESTING 파이프라인을 qa_requests에 저장 (중복 시 무시)."""
    with get_db(db_path) as conn:
        conn.execute("""
            INSERT INTO qa_requests (pipeline_id, repo_id, repo_name, branch, version_hint, release_target, status)
            VALUES (?, ?, ?, ?, ?, ?, 'TESTING')
            ON CONFLICT(pipeline_id) DO NOTHING
        """, (
            pipeline.get("id"),
            pipeline.get("repoId"),
            pipeline.get("repoName"),
            pipeline.get("branch"),
            pipeline.get("versionHint"),
            pipeline.get("releaseTargetName"),
        ))
        conn.commit()


def get_qa_requests(db_path: str) -> list[sqlite3.Row]:
    """qa_requests 전체 목록 (최신순)."""
    with get_db(db_path) as conn:
        return conn.execute(
            "SELECT * FROM qa_requests ORDER BY id DESC"
        ).fetchall()


def update_qa_request(db_path: str, pipeline_id: int, **kwargs) -> None:
    """qa_requests 특정 필드 업데이트."""
    sets   = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [pipeline_id]
    with get_db(db_path) as conn:
        conn.execute(
            f"UPDATE qa_requests SET {sets}, updated_at = datetime('now','localtime') WHERE pipeline_id = ?",
            values,
        )
        conn.commit()


def get_products(db_path: str) -> list[str]:
    """DB에 존재하는 제품명 목록 반환 (알파벳 순)."""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT product FROM runs ORDER BY product"
        ).fetchall()
    return [row["product"] for row in rows]


def get_product_stats(db_path: str) -> list[dict]:
    """
    DB에 있는 제품별 통계 반환.
    반환 형식:
    [
        {
            "product": "RansomCruncher",
            "label": "랜섬크런처",
            "color": "#e74c3c",
            "total": 45,
            "pass": 420,
            "fail": 12,
            "bug": 5,
            "pass_rate": 95.3,
        },
        ...
    ]
    """
    with get_db(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                product,
                COUNT(*) as total,
                COALESCE(SUM(pass_cnt),  0) as pass_sum,
                COALESCE(SUM(fail_cnt),  0) as fail_sum,
                COALESCE(SUM(bug_cnt),   0) as bug_sum
            FROM runs
            GROUP BY product
            ORDER BY product
            """
        ).fetchall()

    result = []
    for row in rows:
        product = row["product"]
        meta = PRODUCT_META.get(product, {"label": product, "color": "#888888"})
        total_items = row["pass_sum"] + row["fail_sum"] + row["bug_sum"]
        if total_items > 0:
            pass_rate = round(row["pass_sum"] / total_items * 100, 1)
        else:
            pass_rate = 0.0
        result.append({
            "product":   product,
            "label":     meta["label"],
            "color":     meta["color"],
            "total":     row["total"],
            "pass":      row["pass_sum"],
            "fail":      row["fail_sum"],
            "bug":       row["bug_sum"],
            "pass_rate": pass_rate,
        })
    return result


def get_run_comparison(db_path: str, run_id: int) -> dict[str, str]:
    """
    같은 product의 직전 run과 비교하여 수정됨/회귀 항목 반환.
    반환: {page_label + '|' + label: "fixed" or "regressed"}
    비교 불가(이전 run 없음)이면 {} 반환.
    """
    with get_db(db_path) as conn:
        # 현재 run 정보
        current_run = conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if current_run is None:
            return {}

        product = current_run["product"]

        # 같은 product의 직전 run (id < run_id 중 최대)
        prev_run = conn.execute(
            "SELECT * FROM runs WHERE product = ? AND id < ? ORDER BY id DESC LIMIT 1",
            (product, run_id),
        ).fetchone()
        if prev_run is None:
            return {}

        prev_run_id = prev_run["id"]

        # 현재 run 결과
        current_results = conn.execute(
            "SELECT page_label, label, status FROM results WHERE run_id = ?",
            (run_id,),
        ).fetchall()

        # 이전 run 결과 (dict로 변환)
        prev_results_rows = conn.execute(
            "SELECT page_label, label, status FROM results WHERE run_id = ?",
            (prev_run_id,),
        ).fetchall()
        prev_map: dict[str, str] = {
            (row["page_label"] + "|" + row["label"]): row["status"]
            for row in prev_results_rows
        }

    fail_statuses = {"fail", "bug", "error"}
    diff: dict[str, str] = {}

    for r in current_results:
        key = (r["page_label"] or "") + "|" + (r["label"] or "")
        curr_status = r["status"] or ""
        prev_status = prev_map.get(key, "")

        if not prev_status:
            continue

        prev_is_fail = prev_status in fail_statuses
        curr_is_fail = curr_status in fail_statuses

        if prev_is_fail and not curr_is_fail and curr_status == "pass":
            diff[key] = "fixed"
        elif not prev_is_fail and curr_is_fail and prev_status == "pass":
            diff[key] = "regressed"

    return diff


def get_dashboard_stats(db_path: str, products: list[str] | None = None) -> dict:
    """
    대시보드 KPI 통계 반환.
    products 지정 시 해당 제품 데이터만 집계.
    {
        total_runs, total_issues, critical_bugs, avg_pass_rate,
        trend: [{date, pass, fail, bug}, ...]  # 최근 14일
    }
    """
    in_clause, in_params = _build_in_clause(products)
    where = f"WHERE 1=1 {in_clause}" if in_clause else ""

    with get_db(db_path) as conn:
        # 전체 실행 횟수
        total_runs_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM runs {where}", in_params
        ).fetchone()
        total_runs = total_runs_row["cnt"] if total_runs_row else 0

        # 총 이슈 수 (fail+bug+error 합계)
        issues_row = conn.execute(
            f"SELECT COALESCE(SUM(fail_cnt + bug_cnt + error_cnt), 0) as cnt FROM runs {where}",
            in_params,
        ).fetchone()
        total_issues = issues_row["cnt"] if issues_row else 0

        # 치명적 오류 (status='error'인 results 수)
        if products:
            placeholders = ",".join("?" * len(products))
            critical_row = conn.execute(
                f"""
                SELECT COUNT(*) as cnt FROM results r
                JOIN runs ON r.run_id = runs.id
                WHERE r.status = 'error' AND runs.product IN ({placeholders})
                """,
                list(products),
            ).fetchone()
        else:
            critical_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM results WHERE status = 'error'"
            ).fetchone()
        critical_bugs = critical_row["cnt"] if critical_row else 0

        # 평균 PASS율
        if total_runs > 0:
            rate_row = conn.execute(
                f"""
                SELECT AVG(CASE WHEN total > 0 THEN CAST(pass_cnt AS REAL) / total * 100 ELSE 0 END) as rate
                FROM runs {where}
                """,
                in_params,
            ).fetchone()
            avg_pass_rate = round(rate_row["rate"], 1) if rate_row and rate_row["rate"] is not None else 0.0
        else:
            avg_pass_rate = 0.0

        # 트렌드: 최근 14일 날짜별 runs 합산
        trend = _build_trend(conn, products=products)

        # 제품별 실행 횟수 (탭 배지용)
        product_counts_rows = conn.execute(
            "SELECT product, COUNT(*) as cnt FROM runs GROUP BY product"
        ).fetchall()
        product_counts = {row["product"]: row["cnt"] for row in product_counts_rows}

    return {
        "total_runs":     total_runs,
        "total_issues":   total_issues,
        "critical_bugs":  critical_bugs,
        "avg_pass_rate":  avg_pass_rate,
        "trend":          trend,
        "product_counts": product_counts,
    }


def _build_trend(conn: sqlite3.Connection, products: list[str] | None = None) -> list[dict]:
    """최근 14일간의 날짜별 pass/fail/bug 합산 리스트 반환."""
    today     = datetime.now().date()
    date_list = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]

    if products:
        placeholders = ",".join("?" * len(products))
        in_clause = f"AND product IN ({placeholders})"
        params = [date_list[0]] + list(products)
    else:
        in_clause = ""
        params = [date_list[0]]

    rows = conn.execute(
        f"""
        SELECT
            substr(timestamp, 1, 10) as date,
            SUM(pass_cnt)  as pass_sum,
            SUM(fail_cnt)  as fail_sum,
            SUM(bug_cnt)   as bug_sum
        FROM runs
        WHERE substr(timestamp, 1, 10) >= ? {in_clause}
        GROUP BY date
        ORDER BY date
        """,
        params,
    ).fetchall()

    db_map: dict[str, dict] = {
        row["date"]: {
            "pass": row["pass_sum"] or 0,
            "fail": row["fail_sum"] or 0,
            "bug":  row["bug_sum"]  or 0,
        }
        for row in rows
    }

    trend = [
        {
            "date": d,
            "pass": db_map.get(d, {}).get("pass", 0),
            "fail": db_map.get(d, {}).get("fail", 0),
            "bug":  db_map.get(d, {}).get("bug",  0),
        }
        for d in date_list
    ]
    return trend
