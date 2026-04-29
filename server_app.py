"""
server_app.py — QA Dashboard 전용 웹 서버

로컬 app.py (pywebview 데스크톱)와 분리된 서버 전용 Flask 앱.
192.168.13.55:8080 에서 상시 운영, 대시보드만 제공.

실행:
    python server_app.py
    # 또는 서비스로 등록: sudo systemctl start qa-dashboard

접근:
    http://192.168.13.55:8080/              -> 대시보드로 리다이렉트
    http://192.168.13.55:8080/dashboard/    -> 대시보드 메인
    http://192.168.13.55:8080/dashboard/runs -> 실행 이력
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, redirect, url_for

from dashboard import dashboard_bp
from dashboard.db import init_db

# ─── 기본 설정 ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "data" / "qa.db"
PORT     = int(os.environ.get("QA_PORT", "8080"))
HOST     = os.environ.get("QA_HOST", "0.0.0.0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("qa_server")

# ─── Flask 앱 ────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.config["BASE_DIR"]    = BASE_DIR
app.config["SECRET_KEY"]  = os.environ.get("QA_SECRET", "qa-dashboard-key-2026")

# dashboard Blueprint 등록
app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

# DB 초기화
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
init_db(str(DB_PATH))
log.info(f"[OK] DB 초기화: {DB_PATH}")


# ─── 루트 리다이렉트 ─────────────────────────────────────────────────────────
@app.route("/")
def root():
    return redirect(url_for("dashboard.index"))


@app.route("/health")
def health():
    """헬스체크 엔드포인트 (systemd watchdog 용)."""
    from flask import jsonify
    return jsonify({"ok": True, "service": "qa-dashboard"})


# ─── 진입점 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info(f"QA Dashboard 서버 시작: http://{HOST}:{PORT}/dashboard/")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
