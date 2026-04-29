"""
core/innorelease_client.py — innoRelease API 연동 클라이언트

requests.Session()으로 로그인 후 쿠키 기반 인증을 유지하여 API 호출.
"""
from __future__ import annotations

import json
import logging
from datetime import date

import requests

log = logging.getLogger("qa_app.innorelease_client")

# ── 제품 코드 매핑 ────────────────────────────────────────────────────────────
INNO_PRODUCT_MAP = {
    1: "INNO_ECM",
    2: "LIZARD_BACKUP",
    3: "RANSOM_CRUNCHER",
    4: "NPOUCH",
    5: "SECURE_ZONE",
    6: "INNO_MARK",
    7: "INNO_LOG",
}

INNO_PRODUCT_KO = {
    1: "innoECM",
    2: "리자드백업",
    3: "랜섬크런처",
    4: "엔파우치",
    5: "시큐어존",
    6: "이노마크",
    7: "이노로그",
}

PIPELINE_STATUS_KO = {
    "PENDING_QA": "QA 대기",
    "TESTING":    "테스트 중",
    "APPROVED":   "승인",
    "REJECTED":   "반려",
    "DEPLOYED":   "배포 완료",
    "MERGED":     "병합됨",
    "EXCLUDED":   "제외",
}

PIPELINE_STATUS_COLOR = {
    "PENDING_QA": "#f39c12",
    "TESTING":    "#3498db",
    "APPROVED":   "#27ae60",
    "REJECTED":   "#e74c3c",
    "DEPLOYED":   "#6c5ce7",
    "MERGED":     "#1abc9c",
    "EXCLUDED":   "#95a5a6",
}


class InnoReleaseClient:
    """innoRelease 서버와 통신하는 HTTP 클라이언트."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url  = base_url.rstrip("/")
        self.username  = username
        self.password  = password
        self._session  = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        self._logged_in = False

    # ── 인증 ─────────────────────────────────────────────────────────────────

    def login(self) -> bool:
        """POST /api/auth/login — access_token 쿠키 획득."""
        try:
            resp = self._session.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=10,
            )
            if resp.status_code == 200:
                self._logged_in = True
                log.info("[OK] innoRelease 로그인 성공 (%s)", self.username)
                return True
            log.warning("[WARN] innoRelease 로그인 실패: %s %s", resp.status_code, resp.text[:100])
            return False
        except Exception as exc:
            log.error("[ERR] innoRelease 로그인 오류: %s", exc)
            return False

    def _ensure_login(self) -> bool:
        if not self._logged_in:
            return self.login()
        return True

    # ── 파이프라인 API ────────────────────────────────────────────────────────

    def get_pipelines(self, status: str | None = None) -> list[dict]:
        """GET /innorelease/api/pipelines — 파이프라인 목록."""
        if not self._ensure_login():
            return []
        params: dict = {}
        if status:
            params["status"] = status
        try:
            resp = self._session.get(
                f"{self.base_url}/innorelease/api/pipelines",
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                body = resp.json()
                raw = body.get("data", []) if isinstance(body, dict) else body
                return self._enrich_pipelines(raw if isinstance(raw, list) else [])
            log.warning("[WARN] get_pipelines %s: %s", resp.status_code, resp.text[:100])
            return []
        except Exception as exc:
            log.error("[ERR] get_pipelines: %s", exc)
            return []

    def _enrich_pipelines(self, rows: list[dict]) -> list[dict]:
        """파이프라인에 한국어 상태/제품명 보조 필드 추가."""
        for row in rows:
            st = row.get("status", "")
            row["statusKo"]    = PIPELINE_STATUS_KO.get(st, st)
            row["statusColor"] = PIPELINE_STATUS_COLOR.get(st, "#888")
        return rows

    def get_pipeline_detail(self, pipeline_id: int) -> dict | None:
        """GET /innorelease/api/pipelines/{id} — 파이프라인 상세."""
        if not self._ensure_login():
            return None
        try:
            resp = self._session.get(
                f"{self.base_url}/innorelease/api/pipelines/{pipeline_id}",
                timeout=10,
            )
            if resp.status_code == 200:
                body = resp.json()
                return body.get("data") if isinstance(body, dict) else body
            return None
        except Exception as exc:
            log.error("[ERR] get_pipeline_detail(%s): %s", pipeline_id, exc)
            return None

    def approve_pipeline(self, pipeline_id: int, comment: str = "", test_env_info: str = "") -> bool:
        """POST /innorelease/api/pipelines/{id}/approve — QA 승인."""
        if not self._ensure_login():
            return False
        payload: dict = {"comment": comment}
        if test_env_info:
            payload["testEnvInfo"] = test_env_info
        try:
            resp = self._session.post(
                f"{self.base_url}/innorelease/api/pipelines/{pipeline_id}/approve",
                json=payload,
                timeout=10,
            )
            ok = resp.status_code == 200
            if ok:
                log.info("[OK] 파이프라인 %s 승인 완료", pipeline_id)
            else:
                log.warning("[WARN] approve %s: %s %s", pipeline_id, resp.status_code, resp.text[:100])
            return ok
        except Exception as exc:
            log.error("[ERR] approve_pipeline(%s): %s", pipeline_id, exc)
            return False

    def reject_pipeline(self, pipeline_id: int, reason: str = "") -> bool:
        """POST /innorelease/api/pipelines/{id}/reject — QA 반려."""
        if not self._ensure_login():
            return False
        try:
            resp = self._session.post(
                f"{self.base_url}/innorelease/api/pipelines/{pipeline_id}/reject",
                json={"reason": reason},
                timeout=10,
            )
            ok = resp.status_code == 200
            if ok:
                log.info("[OK] 파이프라인 %s 반려 완료", pipeline_id)
            else:
                log.warning("[WARN] reject %s: %s %s", pipeline_id, resp.status_code, resp.text[:100])
            return ok
        except Exception as exc:
            log.error("[ERR] reject_pipeline(%s): %s", pipeline_id, exc)
            return False

    # ── QA 레코드 API ─────────────────────────────────────────────────────────

    def get_qa_records(self, inno_product: int, page: int = 0, size: int = 20) -> list[dict]:
        """GET /innorelease/api/qa?innoProduct=N — QA 레코드 목록."""
        if not self._ensure_login():
            return []
        try:
            resp = self._session.get(
                f"{self.base_url}/innorelease/api/qa",
                params={"innoProduct": inno_product, "page": page, "size": size},
                timeout=10,
            )
            if resp.status_code == 200:
                body = resp.json()
                data = body.get("data", {}) if isinstance(body, dict) else {}
                if isinstance(data, dict):
                    return data.get("content", [])
                return []
            log.warning("[WARN] get_qa_records(%s): %s", inno_product, resp.status_code)
            return []
        except Exception as exc:
            log.error("[ERR] get_qa_records(%s): %s", inno_product, exc)
            return []

    def get_all_qa_records(self, size: int = 20) -> list[dict]:
        """모든 제품(1~7)의 QA 레코드를 합쳐서 반환."""
        result = []
        for product_code in INNO_PRODUCT_MAP:
            records = self.get_qa_records(inno_product=product_code, size=size)
            for r in records:
                r["productKo"] = INNO_PRODUCT_KO.get(product_code, str(product_code))
            result.extend(records)
        return result

    def post_qa_result(
        self,
        repo_id: int,
        inno_product: int,
        platform: str,
        record_date: str,         # "YYYY-MM-DD"
        new_features: str = "",
        updates: str = "",
        errors_bugs: str = "",
        pipeline_id: int | None = None,
        html_file_path: str | None = None,
    ) -> bool:
        """
        POST /innorelease/api/qa — QA 결과 innoRelease에 등록.
        html_file_path 가 있으면 HTML 리포트를 첨부파일로 전송.
        """
        if not self._ensure_login():
            return False

        payload = {
            "repoId":      repo_id,
            "innoProduct": inno_product,
            "platform":    platform,
            "recordDate":  record_date,
            "newFeatures": new_features,
            "updates":     updates,
            "errorsBugs":  errors_bugs,
        }
        if pipeline_id is not None:
            payload["pipelineId"] = pipeline_id

        try:
            files: dict = {
                "data": (None, json.dumps(payload, ensure_ascii=False), "application/json"),
            }
            if html_file_path:
                fname = html_file_path.replace("\\", "/").split("/")[-1]
                with open(html_file_path, "rb") as fh:
                    files["file"] = (fname, fh.read(), "text/html")

            resp = self._session.post(
                f"{self.base_url}/innorelease/api/qa",
                files=files,
                timeout=30,
            )
            if resp.status_code == 200:
                log.info("[OK] innoRelease QA 등록 성공 (product=%s)", INNO_PRODUCT_KO.get(inno_product))
                return True
            log.warning("[WARN] post_qa_result %s: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as exc:
            log.error("[ERR] post_qa_result: %s", exc)
            return False


# ── 전역 싱글턴 (설정 로드 후 초기화) ────────────────────────────────────────
_client: InnoReleaseClient | None = None


def init_client(base_url: str, username: str, password: str) -> InnoReleaseClient:
    """Flask app 기동 시 한 번 호출해 전역 클라이언트 초기화."""
    global _client
    _client = InnoReleaseClient(base_url, username, password)
    return _client


def get_client() -> InnoReleaseClient | None:
    return _client
