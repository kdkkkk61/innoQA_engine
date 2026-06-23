"""
core/html_reporter.py — QA 보고서 HTML 자동 생성

실행 후 reports/QA_{product}_{날짜}.html 생성.
수신자: UI담당자 / 에이전트 개발담당자
"""
from __future__ import annotations

import base64
import html
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.models import PageScanReport, ScanResult


def _to_data_uri(path: Path) -> str | None:
    """이미지 파일을 Base64 data URI로 변환. 파일 없으면 None 반환."""
    try:
        if not path.exists():
            return None
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        suffix = path.suffix.lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(suffix, "png")
        return f"data:image/{mime};base64,{data}"
    except Exception:
        return None

# ── 페이지 ID → 표시 이름 ──────────────────────────────────────────
_PAGE_LABELS: dict[str, str] = {
    # RansomCruncher
    "ransom_detect_policy": "탐지정책",
    "rdp_policy":           "RDP 정책",
    "common_process":       "공통 프로세스",
    # 공통 (nPouch·SecureZone)
    "common_operation_process": "운용 프로세스",
    "common_tag":               "태그 관리",
    "common_control_suite":     "제어 스위트",
    # nPouch
    "npouch_origin_protect":    "원본 보호 정책",
    "npouch_policy":            "nPouch 정책",
    # SecureZone
    "secure_zone_access_control": "접근제어 정책",
    "secure_zone_agent_policy":   "시큐어존 정책",
    "secure_zone_template_secure_drive": "템플릿(시큐어드라이브)",
}

# ── 시나리오 번호 → 표시 라벨 (extra["scenario"] 태깅 기준) ────────
# 공통 fallback — page_id 별 dict 에 없을 때 사용.
_SCENARIO_LABELS: dict[int, str] = {
    1: "시나리오 1: UI 구조",
    2: "시나리오 2: 입력 구조",
    3: "시나리오 3: 동작 검증",
    4: "시나리오 4: 수정 시나리오",
    5: "시나리오 5: 케이스 검증",
    6: "시나리오 6: 연계 데이터 핸드오프 + 최종 cleanup ([AUTO_KEEP] 확인·AUTO 정리)",
}

# ── page_id 별 sub-numbering 라벨 (sn*100 + sub_idx) ────────────────
# 같은 sub-num 키(예: 301) 가 page 마다 다른 의미(origin sc3a vs csu sc3 ?)일 수 있어 분리.
_SCENARIO_LABELS_BY_PAGE: dict[str, dict[int, str]] = {
    "npouch_origin_protect": {
        # 단일 parent (공통 dict 로도 fallback 가능)
        0: "시나리오 0: UIScanner 자동 스캔 (신규 기능 감지 + UI 패턴 검증)",
        1: "시나리오 1: UI 구조",
        2: "시나리오 2: 입력 구조",
        3: "시나리오 3: ADD 동작 검증",
        # sc1 sub
        101: "시나리오 1a: navigate + 목록 UI (4 버튼 + 검색)",
        102: "시나리오 1b: ADD 모달 진입 + 26 필드·CSU·탭",
        103: "시나리오 1c: ADD 비기본 탭 접근 차단 (3 탭)",
        104: "시나리오 1d: ADD close → re-open default reset",
        # sc2 sub
        201: "시나리오 2a: ADD 모달 필드 인벤토리 (26 항목)",
        202: "시나리오 2b: 필수 marker — span.star 정확 3개",
        203: "시나리오 2c: default 값 (4 switch ON / 9 checkbox OFF / 13 text 빈값)",
        204: "시나리오 2d: maxlength = 전부 null (서버 측 검증)",
        # sc3 sub (작성 예정 — yaml 사실 13건 기반)
        301: "시나리오 3a: 필수 빈값 메시지 5건 (α/β1/β2/β3/γ) + 발화순서",
        302: "시나리오 3b: 정책 이름 중복 차단 메시지",
        303: "시나리오 3c: driveLetter 형식 — alert + value reset",
        304: "시나리오 3d: 확장자 list (중복/형식/빈값/다중구분자)",
        305: "시나리오 3e: 예외폴더 list (중복/형식 없음/빈값 typo 결함)",
        306: "시나리오 3f: 워터마크 토큰 동작 ([/PCINFO/]·[/TIME/])",
        307: "시나리오 3g: 정상 저장 + CSU picker (KEEP 활용)",
        308: "시나리오 3h: Quota 마스킹 (숫자만/음수·소수점 제거/13자리 OK)",
        309: "시나리오 3i: 워터마크 투명도(0~100 cap)/각도(0~360 cap)",
        310: "시나리오 3j: free text inputs (driveLabel·종료알림 textarea)",
        311: "시나리오 3k: 워터마크 저장+재오픈 sync 복구 (text 우선)",
        312: "시나리오 3l: driveLetter 같은 값 정책 2건 공존 (도메인 의도)",
        313: "시나리오 3m: 출력 워터마크 토큰 동작 (화면 동일 패턴)",
        314: "시나리오 3n: 텍스트 길이 클라 가드 부재 — 5 필드 server reject",
        315: "시나리오 3o: 토글 종속 disabled (4 토글 × 16 종속)",
        # sc4 sub (a~i)
        4: "시나리오 4: EDIT 모달 수정 동작 검증",
        401: "시나리오 4a: EDIT 진입 + 저장값 정확 load",
        402: "시나리오 4b: 이름 빈값 차단 (ADD sc3a 와 동일)",
        403: "시나리오 4c: 이름 중복 검증 부재 결함 🔴",
        404: "시나리오 4d: driveLetter/Label 빈값 silent revert 🟡",
        405: "시나리오 4e: Quota 빈값 → 0 silent 변환 결함 🔴",
        406: "시나리오 4f: 입력 마스킹 sanity (ADD 동일)",
        407: "시나리오 4g: 워터마크 토큰 sanity (화면+출력)",
        408: "시나리오 4h: 텍스트 길이 server reject + 4-3 패턴",
        409: "시나리오 4i: EDIT 모달 title 결함 ⚠",
        410: "시나리오 4j: 확장자/예외폴더 list EDIT 동작 (sc3d/e 대응)",
        411: "시나리오 4k: 워터마크 단방향 sync state2/3 결함 EDIT (sc3f/m 대응)",
        412: "시나리오 4l: 투명도/각도 cap EDIT (sc3i 대응 화면+출력)",
        413: "시나리오 4m: free text 한글/특수 EDIT (sc3j 대응)",
        414: "시나리오 4n: 토글 종속 disabled EDIT (sc3o 대응 4 토글)",
        415: "시나리오 4o: 텍스트 길이 server reject EDIT 4 필드 (sc3n 대응)",
        416: "시나리오 4p: driveLetter 공존 EDIT 도메인 의도 (sc3l 대응)",
        417: "시나리오 4q: EDIT 3 탭 진입 sanity (sc1c 차단과 대비)",
        418: "시나리오 4r: 허용 프로세스 sub-modal 구조 + picker 진입",
        419: "시나리오 4s: 같은 프로세스 다중 탭 등록 결함 🔴 (도메인 배타성)",
        420: "시나리오 4t: 태그 sub-tab 진입 EDIT",
        421: "시나리오 4u: 사용 체크박스 OFF + 탭 진입 가능 ⚠ (UX)",
        422: "시나리오 4v: 개별 프로세스 add 3 탭 (AUTO 검색 → 첫행 fallback)",
        423: "시나리오 4w: 개별 프로세스 remove (- 버튼)",
        424: "시나리오 4x: 태그 sub-tab add",
        425: "시나리오 4y: 태그 sub-tab remove",
        426: "시나리오 4z: 프로세스 설명 textarea free text (한글/특수/3000자)",
        # sc5 lifecycle (a/b/c)
        5: "시나리오 5: 한 정책 lifecycle (ADD → modify → verify+cleanup)",
        501: "시나리오 5a: lifecycle ADD (전체 필드 + 재오픈 일치)",
        502: "시나리오 5b: lifecycle modify (필드 변경 + 재오픈 일치)",
        503: "시나리오 5c: lifecycle verify + cleanup (AUTO 정리 / KEEP 보존)",
        # sc6 KEEP 확인 (단일 페이지 마무리)
        6: "시나리오 6: KEEP 정책 보존 확인 (lifecycle 완결, 단일 페이지)",
    },
    "common_control_suite": {
        0: "시나리오 0: UIScanner 자동 스캔 (신규 기능 감지 + UI 패턴 검증)",
        1: "시나리오 1: UI 구조",
        2: "시나리오 2: 입력 구조",
        3: "시나리오 3: 동작 검증",
        4: "시나리오 4: 수정 시나리오",
        5: "시나리오 5: 케이스 검증",
        6: "시나리오 6: 연계 데이터 핸드오프 + 최종 cleanup ([AUTO_KEEP] 확인·AUTO 정리)",
        # sc1 sub (a/b/c)
        101: "시나리오 1a: navigate + 메인 모달",
        102: "시나리오 1b: process_modal sub-tab (개별/태그)",
        103: "시나리오 1c: web_restrict 모달",
        # sc2 sub (a~h)
        201: "시나리오 2a: 메인 모달 필드",
        202: "시나리오 2b: process_modal 필드",
        203: "시나리오 2c: cache_folder picker (특수폴더)",
        204: "시나리오 2d: web_restrict 프로세스 picker (multi)",
        205: "시나리오 2e: web_restrict 모달 필드",
        206: "시나리오 2f: process picker (single)",
        207: "시나리오 2g: 초기값 점검",
        208: "시나리오 2h: 태그 모달 필드",
        # sc3 sub (a~k)
        302: "시나리오 3b: minimal 저장",
        303: "시나리오 3c: ADD 종합 풍부 (전체 영역)",
        304: "시나리오 3d: 웹제한 ADD 동작",
        305: "시나리오 3e: 검증 메시지 (메인 모달)",
        306: "시나리오 3f: validation 확장 (web/csu)",
        307: "시나리오 3g: format / overflow",
        308: "시나리오 3h: length boundary (메인)",
        309: "시나리오 3i: picker duplicate",
        310: "시나리오 3j: save cycle errors (서버 오류)",
        311: "시나리오 3k: yaml audit (process_modal 갭)",
        # sc4 sub (b~r)
        402: "시나리오 4b: minimal 수정",
        403: "시나리오 4c: 메인 필드 CRUD (EDIT)",
        404: "시나리오 4d: process_modal full (EDIT)",
        405: "시나리오 4e: tag full (EDIT)",
        406: "시나리오 4f: web_restrict full (EDIT)",
        407: "시나리오 4g: validation 메시지 (EDIT)",
        408: "시나리오 4h: sub-modal 재진입 변경 없음",
        409: "시나리오 4i: 이름 중복 (EDIT)",
        410: "시나리오 4j: ux defect 재현 (EDIT)",
        411: "시나리오 4k: 메인 모달 중복 (EDIT)",
        412: "시나리오 4l: 웹제한 validation (EDIT)",
        413: "시나리오 4m: process_modal validation (EDIT)",
        414: "시나리오 4n: picker duplicate (EDIT)",
        415: "시나리오 4o: format/overflow (EDIT)",
        416: "시나리오 4p: length boundary (EDIT)",
        417: "시나리오 4q: normal boundary 회귀",
        418: "시나리오 4r: yaml audit EDIT (process_modal 갭)",
        # sc5 lifecycle (a/b/c)
        501: "시나리오 5a: lifecycle 생성 + 재오픈 일치",
        502: "시나리오 5b: 요소(내용) 제거 + 재오픈 비움",
        503: "시나리오 5c: 토글 전부 OFF + 빈 정책 확인",
    },
}


def _scenario_num_of(r) -> int:
    """extra['scenario'] 우선, 없으면 phase, 없으면 0.

    sub-numbering 은 base._add() 가 메서드 이름에서 자동 매핑 (sn*100 + sub_idx).
    여기서는 그 값을 그대로 사용 — 추가 분기 없음.
    """
    return (r.extra or {}).get("scenario") or r.phase or 0

# ── list_page order 임계값 (extra["scenario"] 없을 때 폴백용) ────────
_LIST_SCENARIO_THRESHOLDS = [
    (0,   "시나리오 1: UI 구조"),
    (45,  "시나리오 2: 입력 구조"),
    (100, "시나리오 3: 동작 검증"),
]

# list_page 전용 패턴 — 이 중 하나라도 있으면 list_page 모드로 판단
_LIST_PAGE_PATTERNS = {
    "list_tab", "list_button", "list_table", "list_search",
    "list_modal", "list_modal_required", "list_modal_overflow",
    "list_crud", "list_modify", "list_modify_save",
    "list_modify_verify", "list_modify_bug",
}

_STATUS_BADGE = {
    "pass":      ('<span class="badge pass">&#x2705; PASS</span>',     "pass"),
    "fail":      ('<span class="badge bug-high">&#x1F534; BUG</span>', "bug-high"),
    "warn":      ('<span class="badge bug-low">&#x26A0;&#xFE0F; BUG</span>', "bug-low"),
    "known_bug": ('<span class="badge bug-low">&#x26A0;&#xFE0F; BUG</span>', "bug-low"),  # 하위 호환
    "error":     ('<span class="badge error">&#x26D4; ERROR</span>',   "error"),
    "skip":      ('<span class="badge skip">&#x23ED; SKIP</span>',     "skip"),
}

# ── 재현 단계 자동 생성 ────────────────────────────────────────────

def _reproduce_steps(r: ScanResult) -> str:
    """ScanResult에서 재현 단계 텍스트 자동 생성.

    extra['repro'] 가 있으면 그걸 우선 사용 (시나리오 테스트가 직접 지정한 상세 단계).
    줄바꿈은 <br> 로 변환. (다른 페이지는 미지정 → 기존 pattern 기반 동작 유지)
    """
    if r.extra and r.extra.get("repro"):
        return html.escape(str(r.extra["repro"])).replace("\n", "<br>")
    p = r.pattern
    if p == "list_modal_overflow":
        field = r.label.split("—")[-1].strip().split("(")[0].strip()
        size  = r.label.split("(")[-1].replace("자)", "").strip() if "자)" in r.label else "500"
        return (
            f"1. 추가 모달 열기<br>"
            f"2. [{field}] 필드에 {size}자 문자열 입력<br>"
            f"3. 저장 버튼 클릭"
        )
    if p == "list_modify_bug":
        tab = ""
        if "[" in r.label:
            tab = r.label.split("[")[-1].replace("]", "")
        return (
            f"1. {'[' + tab + '] 탭 선택<br>2. ' if tab else ''}"
            f"항목 행 클릭 → 수정 버튼 클릭<br>"
            f"{'3' if tab else '2'}. 전자서명 필드 값 변경<br>"
            f"{'4' if tab else '3'}. 수정 버튼 클릭"
        )
    if p in ("toggle_checkbox", "plain_checkbox", "radio_group"):
        return f"1. 해당 필드 조작<br>2. 결과 확인"
    if p == "required_submit":
        return f"1. 추가/수정 모달 열기<br>2. [{r.label}] 필드 비움<br>3. 저장 버튼 클릭"
    return "해당 항목 조작 후 결과 확인"


def _expected_vs_actual(r: ScanResult) -> tuple[str, str]:
    """입력/조건 / 결과 추출.

    지원 형식:
      ① "입력: X / 결과: Y"      — nPouch _r() 헬퍼 신규 표준 포맷
      ② "기댓값: X / 실제값: Y"  — nPouch _r() 헬퍼 구버전 포맷
      ③ "기댓값 X, 실제 Y"       — scan_pages 구버전 포맷 (콤마 구분)
      ④ 그 외                   — detail 전체를 결과로 표시
    """
    det = r.detail or ""

    # ① 신규 표준 포맷: "입력: X / 결과: Y"
    if "입력:" in det and "결과:" in det:
        try:
            inp_raw, res_raw = det.split("결과:", 1)
            inp = inp_raw.replace("입력:", "").strip().rstrip("/ ").strip()
            res = res_raw.strip()
            return inp, res
        except Exception:
            pass

    # ② 구버전 포맷: "기댓값: X / 실제값: Y"
    if "기댓값:" in det and "실제값:" in det:
        try:
            exp_raw, act_raw = det.split("실제값:", 1)
            exp = exp_raw.replace("기댓값:", "").strip().rstrip("/ ").strip()
            act = act_raw.strip()
            return exp, act
        except Exception:
            pass

    # ③ 구버전 포맷: "기댓값 X, 실제 Y"
    if "기댓값" in det and "실제" in det:
        parts = det.split(",")
        exp = parts[0].replace("기댓값 ", "").strip().strip("'")
        act = parts[1].replace("실제 ", "").strip().strip("'") if len(parts) > 1 else ""
        if exp or act:
            return exp, act

    # ④ 포맷 없음 — 상태별 기본값
    if r.status in ("warn", "known_bug"):
        # 라벨 🔴 면 "버그 (높음)" 으로 격상 (사용자 보고 2026-06-01 모순 fix)
        severity_label = "버그 (높음)" if "🔴" in (r.label or "") else "버그 (낮음)"
        return severity_label, det
    if r.status == "skip":
        return "해당 없음", det
    return "정상 동작", det


# ── 시나리오 레이블 결정 ───────────────────────────────────────────

def _strip_scenario_prefix(label: str) -> str:
    """라벨에서 시나리오 prefix 제거 — 헤더가 이미 시나리오 표시하므로 중복/장황 방지.
    두 패턴: '시나리오 Nx — ' (한글) / 'scNx — ' (영어, 사용자 지적 2026-05-29).
    """
    s = re.sub(r"^시나리오\s*\d+[a-z]?\s*[—–\-]\s*", "", label)
    s = re.sub(r"^sc\d+[a-z]?\s*[—–\-]\s*", "", s, flags=re.IGNORECASE)
    return s


def _format_num_pretty(n: int) -> str:
    """sub-numbering num 을 사용자 친화 표기로 변환 — '313' → '3.13', '101' → '1.01'.

    사용자 요구 (2026-05-29): "313 이런 식으로 되는 게 불편 — 3.01 / 3.13 식으로".
    dict 미등록 sub-num 의 fallback 표기에 사용. dict 등록된 항목은 영향 없음.
    """
    if n >= 100:
        parent, sub = n // 100, n % 100
        return f"{parent}.{sub:02d}"
    return str(n)


def _scenario_label(r: ScanResult, is_list_page: bool, page_id: str = "") -> str:
    # ① extra["scenario"] 명시 태깅 우선 — qa_runner / list_page_runner가 부여
    scenario_num = (r.extra or {}).get("scenario")
    if scenario_num is not None:
        # sub-numbering(sn*100+sub) + base — page_id 별 dict 우선 → 공통 fallback
        num = _scenario_num_of(r)
        page_dict = _SCENARIO_LABELS_BY_PAGE.get(page_id, {})
        return (page_dict.get(num)
                or page_dict.get(scenario_num)
                or _SCENARIO_LABELS.get(num)
                or _SCENARIO_LABELS.get(scenario_num, f"시나리오 {_format_num_pretty(scenario_num)}"))

    # ② 폴백: order 임계값 (구버전 호환 / 태깅 없는 결과)
    if is_list_page:
        order = r.order or 9999
        idx = sum(1 for t, _ in _LIST_SCENARIO_THRESHOLDS if order >= t) - 1
        idx = max(0, min(idx, len(_LIST_SCENARIO_THRESHOLDS) - 1))
        return _LIST_SCENARIO_THRESHOLDS[idx][1]

    # ③ 폴백: phase 번호 (modal_form 구버전)
    return _SCENARIO_LABELS.get(r.phase, f"시나리오 {r.phase}")


# ── HTML 조각 생성 ─────────────────────────────────────────────────

def _count_label_high(items) -> int:
    """라벨에 🔴 있는 항목 갯수 — status=warn 이지만 라벨 의도 HIGH 로 표시된 결함.
    (사용자 보고 2026-06-01: 항목별 심각도 = "높음" 인데 카운트는 warn — 모순 fix)
    """
    return sum(1 for r in items if "🔴" in (r.label or ""))


def _render_summary_card(page_id: str, report: PageScanReport) -> str:
    label  = _PAGE_LABELS.get(page_id, page_id)
    # 라벨 🔴 인 warn 항목 → fail 카운트로 격상 (심각도 일관성)
    warn_high = _count_label_high(report.known_bugs)
    p      = len(report.passed)
    f      = len(report.failed) + warn_high
    k      = len(report.known_bugs) - warn_high
    e      = len(report.errors)
    total  = p + f + k + e
    status = "🔴 BUG 높음 있음" if f > 0 else ("🟡 BUG 낮음 있음" if k > 0 else ("⛔ 실행 오류" if e > 0 else "🟢 정상"))
    # data-page-id: finalize 후 JS가 수동 이슈 카운트를 업데이트할 때 사용
    return f"""
    <div class="summary-card {'has-fail' if f > 0 else ('has-bug' if k+e > 0 else 'all-pass')}"
         data-page-id="{html.escape(page_id)}"
         data-auto-total="{total}" data-auto-fail="{f}" data-auto-bug="{k}">
      <div class="card-title">{html.escape(label)}</div>
      <div class="card-status" data-status-el="1">{status}</div>
      <div class="card-counts">
        <span class="cnt pass">&#x2705; {p}</span>
        <span class="cnt bug-high" data-fail-cnt="1">&#x1F534; {f}</span>
        <span class="cnt bug-low" data-bug-cnt="1">&#x26A0;&#xFE0F; {k}</span>
        <span class="cnt error">&#x26D4; {e}</span>
      </div>
      <div class="card-total" data-total-el="1">자동 {total}건 검증</div>
    </div>"""


def _label_area_priority(r: ScanResult) -> tuple:
    """라벨에서 (영역 우선순위, 그룹명) 튜플 추출 — 영역별 sort 용.

    사용자 의도 (2026-05-21):
      1차 모달 (메인 스위트 모달 내 직접 input) — 스위트 이름, 클립보드, 전자서명 등
      2차 모달 - 프로세스별 제어 (개별 프로세스)
      3차 - 프로세스별 제어 (태그)
      4차 - 웹제한 기능

    page_id 조건부 sort 에서 사용. whitelist 외 페이지는 미사용.
    """
    lbl = r.label or ""
    # 선두 [tag] 제거
    if lbl.startswith("[") and "]" in lbl:
        lbl = lbl.split("]", 1)[1].strip()

    # 0: sc5 lifecycle 액션 (저장/제거) — 재오픈 검증보다 먼저 표시 (생성→재오픈 흐름)
    #    '재오픈' 미포함 + ('저장' or '제거') → 단계 액션으로 최상위 배치
    if "시나리오 5" in lbl and "재오픈" not in lbl and ("저장" in lbl or "제거" in lbl):
        return (0, "0차 (lifecycle 액션)")

    # 1: 1차 (메인 스위트 모달) — 추가/수정 양쪽 + 메인 영역 직접 input
    #    sc5 라벨 추가: '메인 필드'(5a) / '빈 정책'(5c) / '차단할 확장자'·'제어할 확장자'(메인 확장자)
    #    / '전자서명'(예외 토글·list). 프로세스의 '제어 확장자'/'확장자 제어' 와 구분됨.
    main_kw = ["스위트 추가 모달", "스위트 수정 모달", "스위트 이름", "메인 모달",
               "메인 필드", "빈 정책",
               "클립보드", "네트워크 허용", "헤더 체크",
               "전자서명", "커스텀 옵션",
               "메인 확장자", "차단할 확장자", "제어할 확장자",
               "정책 list"]  # sc4 정책 list 검증도 1차 영역
    if any(kw in lbl for kw in main_kw):
        return (1, "1차 (메인 모달)")

    # 3: 프로세스별 제어 (태그) — 프로세스보다 먼저 체크 (itemTagList ⊃ itemList 혼동 방지)
    #    sc5 라벨 추가: '태그 등록 모달' / 'itemTagList'
    if ("(태그)" in lbl or "태그 등록 모달" in lbl or "itemTagList" in lbl
            or "태그 picker" in lbl or "tag picker" in lbl.lower()):
        return (3, "2차 (프로세스별 제어 (태그))")

    # 2: 프로세스별 제어 (개별 프로세스) — sc5 라벨 추가: '개별 프로세스' / 'itemList'
    if ("(개별 프로세스)" in lbl or "프로세스 등록 모달" in lbl
            or "개별 프로세스" in lbl or "itemList" in lbl):
        return (2, "2차 (프로세스별 제어 (개별 프로세스))")

    # 4: 웹제한 기능 — 명시 prefix 또는 '웹제한 모달'/'web_restrict'
    if "웹제한" in lbl or "web_restrict" in lbl.lower():
        return (4, "2차 (웹제한 기능)")

    # 5: 기타 (picker 일반, IP/Port 무영역, KEEP 보존 등)
    return (5, "기타")


# 영역별 sort 적용 page_id 목록 — 추후 다른 페이지 추가 시 여기에 추가
_PAGE_IDS_USE_LABEL_GROUP_SORT = {"common_control_suite"}


def _render_results_table(report: PageScanReport, is_list_page: bool,
                           page_id: str = "") -> str:
    rows = []
    prev_scenario = None
    prev_parent_num = None   # 큰 시나리오(1·2·3·...) 전환 추적 — sub-header 와 디자인 차등
    _scenario_num = _scenario_num_of  # sc5 lifecycle 세분 포함 모듈 헬퍼

    # page_id 조건부 sort — 영역 우선순위 (1차 → 2차 프로세스 → 태그 → 웹제한) 적용
    # parent 별 묶음 정렬 — 1 < 1a < 1b < ... < 2 < 2a < ... < 6 < 7 자연순
    # sub-num (sn>=100) 는 parent = sn // 100, sub = sn % 100 로 분해해서
    # base(sub=0) → sub_a → sub_b ... 순서 유지.
    if page_id in _PAGE_IDS_USE_LABEL_GROUP_SORT:
        def sort_key(x):
            sn = _scenario_num(x)
            if sn >= 100:
                # sub-num: parent=sn//100, sub=sn%100 → (parent, sub, area=0) 시간순
                return (sn // 100, sn % 100, (0, ""), 0)
            # base (sub 없음): parent=sn, sub=0 → 같은 parent 의 sub-num 보다 먼저
            return (sn, 0, _label_area_priority(x), x.order or 9999)
    else:
        # 기존 동작 + parent 별 묶음 — RansomCruncher 등도 일관 적용
        def sort_key(x):
            sn = _scenario_num(x)
            if sn >= 100:
                return (sn // 100, sn % 100, x.order or 9999)
            return (sn, 0, x.order or 9999)

    for r in sorted(report.results, key=sort_key):
        badge, css = _STATUS_BADGE.get(r.status, ('?', ''))
        scenario   = _scenario_label(r, is_list_page, page_id)
        expected, actual = _expected_vs_actual(r)
        # 항목 라벨에서 시나리오 prefix 제거 — helper 일관 사용
        disp_label = _strip_scenario_prefix(r.label or "")

        # 시나리오 구분 헤더 — 2단 계층:
        #   parent (sn < 100 단독, 또는 sub-num 의 base): 큰 헤더 (시나리오 1 / 2 / ...)
        #   sub (sn >= 100, sn % 100 ≠ 0): 작은 헤더 (시나리오 1a / 1b / 3j / 4r ...)
        sn = _scenario_num(r)
        is_sub = sn >= 100 and (sn % 100) != 0   # 101/102/.../301/.../418/501/502/503
        parent_num = sn // 100 if is_sub else sn

        # parent 전환 시 — 큰 헤더 출력
        if parent_num != prev_parent_num:
            page_dict = _SCENARIO_LABELS_BY_PAGE.get(page_id, {})
            parent_label = (page_dict.get(parent_num)
                            or _SCENARIO_LABELS.get(parent_num, f"시나리오 {parent_num}"))
            rows.append(f"""
        <tr class="scenario-header">
          <td colspan="4">{html.escape(parent_label)}</td>
        </tr>""")
            prev_parent_num = parent_num
            prev_scenario = None   # parent 갱신 후 sub-header 도 새로 그리도록 reset

        # sub 진입 (sn >= 10) — 작은 헤더 출력 (parent 헤더와 분리)
        if is_sub and scenario != prev_scenario:
            rows.append(f"""
        <tr class="scenario-subheader">
          <td colspan="4">{html.escape(scenario)}</td>
        </tr>""")
            prev_scenario = scenario
        elif not is_sub:
            # sub 가 아닌 경우 parent 만 있으면 충분 — 별도 sub-header 없음
            prev_scenario = scenario

        rows.append(f"""
        <tr class="row-{css}">
          <td class="col-label">{html.escape(disp_label)}</td>
          <td class="col-status">{badge}</td>
          <td class="col-expected">{html.escape(expected)}</td>
          <td class="col-actual">{html.escape(actual)}</td>
        </tr>""")
    return f"""
    <table class="result-table">
      <thead>
        <tr>
          <th class="col-label">검증 항목</th>
          <th class="col-status">판정</th>
          <th class="col-expected">입력 / 조건</th>
          <th class="col-actual">결과</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def _render_defect_section(all_reports: list[tuple[str, PageScanReport]]) -> str:
    """전체 페이지에서 fail + warn + error 항목 모아서 결함 목록 생성."""
    defects = []
    issue_num = 0
    for page_id, report in all_reports:
        label      = _PAGE_LABELS.get(page_id, page_id)
        is_list    = any(r.pattern in _LIST_PAGE_PATTERNS for r in report.results)
        bug_items  = [r for r in report.results if r.status in ("fail", "warn", "known_bug", "error")]
        # page_id 조건부 sort — parent 별 묶음 (1 < 1a < 1b < ... < 2 < ... < 6 < 7)
        if page_id in _PAGE_IDS_USE_LABEL_GROUP_SORT:
            def _bug_sort_key(r):
                sn = _scenario_num_of(r)
                if sn >= 100:
                    return (sn // 100, sn % 100, (0, ""), 0)
                return (sn, 0, _label_area_priority(r), r.order or 9999)
            bug_items.sort(key=_bug_sort_key)
        for r in bug_items:
            issue_num += 1
            badge, css = _STATUS_BADGE.get(r.status, ('?', ''))
            scenario   = _scenario_label(r, is_list, page_id)
            steps      = _reproduce_steps(r)
            expected, actual = _expected_vs_actual(r)
            # 심각도 + 아이콘 결정 — status + 라벨/시나리오의 🔴/🟡 의도 반영 (사용자 보고 2026-06-01)
            # 이전: status 만 — fail/error→높음/빨강 else 낮음/노랑
            # → sc4c 처럼 known_bug 로 warn 처리됐는데 라벨 🔴 (높음 의도) 인 경우 모순
            # 수정: 라벨에 🔴 있으면 status 무관하게 "높음" + 빨강 아이콘 (라벨/아이콘/심각도 일관성)
            _label_text = (r.label or "") + " " + (scenario or "")
            if "🔴" in _label_text:
                severity = "높음"
                # warn/known_bug 인데 라벨 🔴 면 빨강 아이콘으로 격상
                if r.status in ("warn", "known_bug"):
                    badge = '<span class="badge bug-high">&#x1F534; BUG</span>'
                    css = "bug-high"
            elif r.status in ("fail", "error"):
                severity = "높음"
            else:
                severity = "낮음"
            ss_path    = r.extra.get("screenshot") if r.extra else None
            ss_html    = ""
            if ss_path:
                from pathlib import Path as _Path
                ss_abs = _Path(ss_path).resolve()
                ss_uri = _to_data_uri(ss_abs)
                if ss_uri:
                    ss_html = f"""
            <tr>
              <th>스크린샷</th>
              <td>
                <details>
                  <summary class="ss-toggle">📷 스크린샷 보기</summary>
                  <img src="{ss_uri}" class="ss-img" alt="{html.escape(r.label)}">
                </details>
              </td>
            </tr>"""
            defects.append(f"""
        <div class="defect-card defect-{css}" data-page-key="{html.escape(label)}">
          <div class="defect-header">
            <span class="issue-num">#{issue_num}</span>
            {badge}
            <span class="defect-page">{html.escape(label)}</span>
            <span class="defect-scenario">{html.escape(scenario)}</span>
            <span class="defect-severity severity-{severity}">심각도: {severity}</span>
          </div>
          <div class="defect-title">{html.escape(_strip_scenario_prefix(r.label or ''))}</div>
          <table class="defect-detail">
            <tr><th>재현 방법</th><td>{steps}</td></tr>
            <tr><th>입력 / 조건</th><td>{html.escape(expected)}</td></tr>
            <tr><th>결과</th><td>{html.escape(actual)}</td></tr>
            {ss_html}
          </table>
        </div>""")

    if not defects:
        return '<p class="no-defect">🎉 발견된 결함 없음</p>'
    # tab-no-defect: 탭 필터로 결함 없을 때 JS가 show
    return ''.join(defects) + '\n<p class="tab-no-defect" id="tab-no-defect">[OK]  해당 페이지에 결함이 없습니다</p>'


# ── CSS ──────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #f5f7fa; color: #333; font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }

/* 페이지 탭 바 */
.tab-bar { display: flex; gap: 6px; background: white; border-radius: 8px;
           padding: 12px 16px; box-shadow: 0 1px 4px rgba(0,0,0,.1);
           margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.tab-btn { padding: 6px 16px; border: 1px solid #dde4ee; border-radius: 20px;
           background: white; color: #666; font-size: 13px; font-weight: 500;
           cursor: pointer; transition: all .15s; }
.tab-btn:hover { border-color: #1e3a5f; color: #1e3a5f; }
.tab-btn.active { background: #1e3a5f; color: white; border-color: #1e3a5f; font-weight: 600; }

/* 직접 등록 배지 */
.manual-badge { display: inline-block; font-size: 11px; font-weight: 600;
                background: #eef6ff; color: #2980b9;
                border: 1px solid #bee3f8;
                border-radius: 10px; padding: 1px 8px; margin-left: 6px; }
/* 탭 필터 적용 시 결함 없음 메시지 */
.tab-no-defect { color: #27ae60; font-weight: 600; padding: 20px; text-align: center; display: none; }

/* 헤더 */
.report-header { background: #1e3a5f; color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 24px; }
.report-header h1 { font-size: 22px; font-weight: 600; }
.report-header .meta { margin-top: 6px; font-size: 13px; opacity: 0.8; }

/* 요약 카드 */
.summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }
.summary-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); border-left: 4px solid #ccc; }
.summary-card.all-pass  { border-left-color: #27ae60; }
.summary-card.has-bug   { border-left-color: #f39c12; }
.summary-card.has-fail  { border-left-color: #e74c3c; }
.card-title  { font-weight: 600; font-size: 15px; margin-bottom: 6px; }
.card-status { font-size: 13px; margin-bottom: 10px; }
.card-counts { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.cnt { font-size: 13px; font-weight: 600; }
.cnt.pass     { color: #27ae60; }
.cnt.bug-high { color: #e74c3c; }
.cnt.bug-low  { color: #f39c12; }
.cnt.error    { color: #c0392b; }
.card-total { font-size: 12px; color: #888; }

/* 섹션 */
.section { background: white; border-radius: 8px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.1); margin-bottom: 24px; }
.section-title { font-size: 17px; font-weight: 600; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #eee; }
.page-label { font-size: 15px; font-weight: 600; margin: 20px 0 10px; color: #1e3a5f; }

/* 결과 테이블 */
.result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.result-table th { background: #f0f4f8; padding: 10px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #ddd; }
.result-table td { padding: 9px 12px; border-bottom: 1px solid #eee; vertical-align: top; }
/* tr:hover 하얘지는 효과 제거 (사용자 요청 2026-05-29 — 가독성 향상) */
.col-label    { width: 40%; }
.col-status   { width: 10%; text-align: center; white-space: nowrap; }
.col-expected { width: 22%; font-size: 12px; color: #555; }
.col-actual   { width: 28%; font-size: 12px; color: #555; }
.row-bug-high td { background: #fff8f8; }
.row-bug-low td  { background: #fffdf0; }
.row-error td    { background: #fdf0ff; }
/* 시나리오 구분 헤더 — parent (큰 시나리오 1·2·3·...) */
.scenario-header td { background: #1e3a5f; color: #ffffff; font-weight: 700;
  font-size: 15px; padding: 12px 16px; border-top: 4px solid #0f1f3a;
  border-bottom: 1px solid #0f1f3a; letter-spacing: 0.5px; }
/* 시나리오 sub 헤더 (sub-numbering: sc1a / 1b / ... / 2a / 2b / ... ) */
.scenario-subheader td { background: #e8f0f8; color: #1e3a5f; font-weight: 600;
  font-size: 13px; padding: 7px 14px 7px 30px; border-top: 1px solid #b8cfe8;
  border-bottom: 1px solid #b8cfe8; letter-spacing: 0.3px; }
.scenario-subheader td::before { content: "└ "; color: #4a72a5; font-weight: 400; }

/* 배지 */
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.badge.pass     { background: #e8f8ef; color: #27ae60; }
.badge.bug-high { background: #fde8e8; color: #e74c3c; }
.badge.bug-low  { background: #fef9e7; color: #d68000; }
.badge.error    { background: #f3e8fd; color: #8e44ad; }
.badge.skip     { background: #f0f0f0; color: #888; }

/* 결함 목록 */
.defect-card { background: white; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.defect-fail  { border-left: 4px solid #e74c3c; }
.defect-bug   { border-left: 4px solid #f39c12; }
.defect-error { border-left: 4px solid #c0392b; }
.defect-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.issue-num { display: inline-block; min-width: 32px; text-align: center;
             font-size: 12px; font-weight: 700; color: #fff;
             background: #4a6fa5; border-radius: 4px; padding: 2px 6px;
             letter-spacing: 0.3px; flex-shrink: 0; }
.defect-page     { font-weight: 600; color: #1e3a5f; }
.defect-scenario { color: #666; font-size: 12px; }
.defect-severity { margin-left: auto; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; }
.severity-높음 { background: #fde8e8; color: #e74c3c; }
.severity-낮음 { background: #fef9e7; color: #f39c12; }
.defect-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.defect-detail { width: 100%; border-collapse: collapse; font-size: 13px; }
.defect-detail th { width: 120px; padding: 8px 12px; background: #f8f9fa; text-align: left; font-weight: 600; border: 1px solid #eee; color: #555; vertical-align: top; }
.defect-detail td { padding: 8px 12px; border: 1px solid #eee; line-height: 1.6; }
.no-defect { color: #27ae60; font-weight: 600; padding: 20px; text-align: center; }

/* 스크린샷 */
.screenshot { margin-top: 10px; }
.screenshot img { max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }
.ss-toggle { cursor: pointer; color: #1e3a5f; font-weight: 600; font-size: 13px;
  padding: 4px 0; display: inline-block; }
.ss-toggle:hover { text-decoration: underline; }
.ss-img { max-width: 100%; margin-top: 10px; border: 1px solid #ddd;
  border-radius: 4px; display: block; }
"""


# ── 메인 함수 ─────────────────────────────────────────────────────

def generate_html_report(
    reports: list[tuple[str, PageScanReport]],
    product_name: str = "RansomCruncher",
    output_dir: str = "reports",
    screenshot_dir: Optional[str] = None,
    duration_sec: Optional[float] = None,
) -> Path:
    """
    reports: [(page_id, PageScanReport), ...] 순서대로 전달
    duration_sec: 테스트 총 소요시간(초) — 헤더에 표시 (None 이면 생략)
    반환값: 생성된 HTML 파일 경로
    """
    now       = datetime.now()
    # 소요시간 표시 문자열 (예: "46분 28초")
    _dur_str = ""
    if duration_sec is not None:
        _m, _s = divmod(int(duration_sec), 60)
        _dur_str = (f"{_m}분 {_s}초" if _m else f"{_s}초")
    date_str  = now.strftime("%Y%m%d_%H%M")
    filename  = f"QA_{product_name}_{date_str}.html"
    out_path  = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 요약 카드 ─────────────────────────────────────────────────
    summary_cards = "".join(
        _render_summary_card(pid, rep) for pid, rep in reports
    )

    # ── 페이지 탭 바 ──────────────────────────────────────────────
    pages_for_tabs = [_PAGE_LABELS.get(pid, pid) for pid, _ in reports]
    tab_buttons = '\n    '.join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" '
        f'data-tab="{html.escape(lbl)}" '
        f'onclick="switchTab(this,\'{html.escape(lbl)}\')">'
        f'{html.escape(lbl)}</button>'
        for i, lbl in enumerate(['전체'] + pages_for_tabs)
    )
    tab_html = f"""<div class="tab-bar">
    {tab_buttons}
  </div>"""

    # ── 페이지별 결과 테이블 ──────────────────────────────────────
    page_sections = []
    for page_id, report in reports:
        label      = _PAGE_LABELS.get(page_id, page_id)
        is_list    = any(r.pattern in _LIST_PAGE_PATTERNS for r in report.results)
        table_html = _render_results_table(report, is_list, page_id)
        p, f, k, e = (len(report.passed), len(report.failed),
                      len(report.known_bugs), len(report.errors))
        page_sections.append(f"""
        <div class="page-result-section" data-page-key="{html.escape(label)}">
          <div class="page-label">{html.escape(label)}
            <span style="font-weight:400;font-size:13px;color:#666;margin-left:10px;">
              &#x2705; {p}  &#x1F534; {f}  &#x26A0;&#xFE0F; {k}  &#x26D4; {e}
            </span>
          </div>
          {table_html}
        </div>""")

    # ── 결함 목록 ─────────────────────────────────────────────────
    defect_html = _render_defect_section(reports)

    # ── 스크린샷 섹션 (실패 스크린샷 존재 시) ─────────────────────
    screenshot_html = ""
    if screenshot_dir:
        ss_path = Path(screenshot_dir)
        screenshots = sorted(ss_path.glob("FAIL_*.png"), reverse=True)[:20]
        if screenshots:
            items = "".join(
                f'<div style="margin-bottom:16px;"><div style="font-size:12px;color:#666;margin-bottom:4px;">{html.escape(s.name)}</div>'
                f'<div class="screenshot"><img src="{_to_data_uri(s)}" alt="{html.escape(s.name)}"></div></div>'
                for s in screenshots
                if _to_data_uri(s)
            )
            screenshot_html = f"""
    <div class="section">
      <div class="section-title">📷 실패 스크린샷</div>
      {items}
    </div>"""

    # ── 전체 카운트 ───────────────────────────────────────────────
    total_p = sum(len(r.passed)     for _, r in reports)
    # 라벨 🔴 인 warn 항목들은 fail 카운트로 격상 (심각도 일관성, 사용자 보고 2026-06-01)
    total_warn_high = sum(_count_label_high(r.known_bugs) for _, r in reports)
    total_f = sum(len(r.failed)     for _, r in reports) + total_warn_high
    total_k = sum(len(r.known_bugs) for _, r in reports) - total_warn_high
    total_e = sum(len(r.errors)     for _, r in reports)
    overall = "🔴 결함 있음" if (total_f + total_e) > 0 else ("🟡 버그 추적 중" if total_k > 0 else "🟢 전체 정상")

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QA 보고서 — {html.escape(product_name)} {now.strftime('%Y-%m-%d')}</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="container">

  <div class="report-header">
    <h1>🔍 QA 보고서 — {html.escape(product_name)}</h1>
    <div class="meta">
      생성일시: {now.strftime('%Y년 %m월 %d일 %H:%M')} &nbsp;|&nbsp;
      {f'소요시간: {_dur_str} &nbsp;|&nbsp;' if _dur_str else ''}
      전체 결과: &#x2705; {total_p}  &#x1F534; {total_f}  &#x26A0;&#xFE0F; {total_k}  &#x26D4; {total_e} &nbsp;|&nbsp;
      {overall}
    </div>
    <div class="meta" style="margin-top:6px;font-size:12px;opacity:0.85;">
      범례: &#x2705; 통과 &nbsp;·&nbsp; &#x1F534; BUG 높음 (fail) &nbsp;·&nbsp; &#x26A0;&#xFE0F; BUG 낮음 (warn) &nbsp;·&nbsp; &#x26D4; 실행 오류 (error)
    </div>
  </div>

  <div class="section">
    <div class="section-title">📊 페이지별 요약</div>
    <div class="summary-grid">{summary_cards}</div>
  </div>

  {tab_html}

  <!-- DEFECT_SECTION_START -->
  <div class="section">
    <div class="section-title">🐛 확정된 결함 (<span id="defect-count">{total_f + total_k + total_e}</span>건)</div>
    {defect_html}
  </div>
  <!-- DEFECT_SECTION_END -->

  <div class="section">
    <div class="section-title">📋 전체 테스트 결과</div>
    {''.join(page_sections)}
  </div>

  {screenshot_html}

</div>
<script>
function switchTab(btn, key) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  var defectCount = 0;
  document.querySelectorAll('[data-page-key]').forEach(function(el) {{
    var show = key === '전체' || el.dataset.pageKey === key;
    el.style.display = show ? '' : 'none';
    if (show && el.classList.contains('defect-card')) defectCount++;
  }});
  var noDefEl = document.getElementById('tab-no-defect');
  if (noDefEl) noDefEl.style.display = defectCount > 0 ? 'none' : '';
  var countEl = document.getElementById('defect-count');
  if (countEl) countEl.textContent = defectCount;
}}
</script>
</body>
</html>"""

    out_path.write_text(html_content, encoding="utf-8")
    print(f"\n[HTML 리포트] {out_path}")

    # ── JSON 요약 저장 (app.py 리포트 화면용) ─────────────────────
    import json as _json
    json_data = {
        "generated_at": now.isoformat(),
        "duration_sec": round(duration_sec, 1) if duration_sec is not None else None,
        "html_path":    str(out_path.resolve()),
        "pages": [
            {
                "page_id": pid,
                "label":   _PAGE_LABELS.get(pid, pid),
                # is_list: 결과에 list_page 전용 패턴(list_crud, list_modify 등)이 있을 때만 True
                # list_tab/list_search/list_table은 modal_form도 사용하므로 제외
                "is_list": any(r.pattern in {
                    "list_crud", "list_modify", "list_modify_save",
                    "list_modify_verify", "list_modify_bug", "list_button",
                } for r in rep.results),
                "results": [
                    {
                        "phase":    r.phase,
                        "order":    r.order or 9999,
                        "pattern":  r.pattern,
                        "label":    r.label,
                        "status":   r.status,
                        "detail":   r.detail,
                        "screenshot":  (r.extra or {}).get("screenshot"),
                        "scenario":    (r.extra or {}).get("scenario"),      # 새 태깅 필드
                        "scenario_tag": (r.extra or {}).get("scenario_tag"), # 구버전 호환
                    }
                    for r in rep.results
                ],
            }
            for pid, rep in reports
        ],
    }
    _json_str = _json.dumps(json_data, ensure_ascii=False, indent=2)
    # 제품 폴더에 저장 (히스토리용)
    last_json = Path(output_dir) / "last_report.json"
    last_json.write_text(_json_str, encoding="utf-8")
    # 루트 reports/ 에도 항상 덮어쓰기 — app.py /report-data 엔드포인트 폴백 경로
    root_json = Path("reports") / "last_report.json"
    root_json.parent.mkdir(parents=True, exist_ok=True)
    root_json.write_text(_json_str, encoding="utf-8")

    return out_path
