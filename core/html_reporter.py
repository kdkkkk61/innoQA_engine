"""
core/html_reporter.py — QA 보고서 HTML 자동 생성

실행 후 reports/QA_{product}_{날짜}.html 생성.
수신자: UI담당자 / 에이전트 개발담당자
"""
from __future__ import annotations

import base64
import html
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
    # nPouch
    "npouch_operation_process": "운용 프로세스",
    "npouch_tag":               "태그 관리",
    "npouch_control_suite":     "제어 스위트",
    "npouch_origin_protect":    "원본 보호 정책",
    "npouch_policy":            "nPouch 정책",
}

# ── 시나리오 번호 → 표시 라벨 (extra["scenario"] 태깅 기준) ────────
_SCENARIO_LABELS: dict[int, str] = {
    1: "시나리오 1: UI 구조",
    2: "시나리오 2: 입력 구조",
    3: "시나리오 3: 동작 검증",
    4: "시나리오 4: 수정 시나리오",
    5: "시나리오 5: 케이스 검증",
}

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
    """ScanResult에서 재현 단계 텍스트 자동 생성."""
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
        return "버그 (낮음)", det
    if r.status == "skip":
        return "해당 없음", det
    return "정상 동작", det


# ── 시나리오 레이블 결정 ───────────────────────────────────────────

def _scenario_label(r: ScanResult, is_list_page: bool) -> str:
    # ① extra["scenario"] 명시 태깅 우선 — qa_runner / list_page_runner가 부여
    scenario_num = (r.extra or {}).get("scenario")
    if scenario_num is not None:
        return _SCENARIO_LABELS.get(scenario_num, f"시나리오 {scenario_num}")

    # ② 폴백: order 임계값 (구버전 호환 / 태깅 없는 결과)
    if is_list_page:
        order = r.order or 9999
        idx = sum(1 for t, _ in _LIST_SCENARIO_THRESHOLDS if order >= t) - 1
        idx = max(0, min(idx, len(_LIST_SCENARIO_THRESHOLDS) - 1))
        return _LIST_SCENARIO_THRESHOLDS[idx][1]

    # ③ 폴백: phase 번호 (modal_form 구버전)
    return _SCENARIO_LABELS.get(r.phase, f"시나리오 {r.phase}")


# ── HTML 조각 생성 ─────────────────────────────────────────────────

def _render_summary_card(page_id: str, report: PageScanReport) -> str:
    label  = _PAGE_LABELS.get(page_id, page_id)
    p, f   = len(report.passed), len(report.failed)
    k, e   = len(report.known_bugs), len(report.errors)
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


def _label_group_prefix(r: ScanResult) -> str:
    """라벨 영역 그룹 prefix 추출.

    예: '[UX 결함] 프로세스별 제어 (개별 프로세스) - 접근 드라이브...'
        → '프로세스별 제어 (개별 프로세스)'

    page_id 조건부 sort 에서 사용. 같은 영역의 case 들이 보고서에서 연속 표시되도록.
    선두 [...] tag 제거 후 첫 ' - ' 까지가 그룹 식별자.
    """
    lbl = r.label or ""
    if lbl.startswith("[") and "]" in lbl:
        lbl = lbl.split("]", 1)[1].strip()
    return lbl.split(" - ", 1)[0].strip() if " - " in lbl else lbl


# 영역별 sort 적용 page_id 목록 — 추후 다른 페이지 추가 시 여기에 추가
_PAGE_IDS_USE_LABEL_GROUP_SORT = {"npouch_control_suite"}


def _render_results_table(report: PageScanReport, is_list_page: bool,
                           page_id: str = "") -> str:
    rows = []
    prev_scenario = None

    def _scenario_num(r: ScanResult) -> int:
        """extra["scenario"] 우선, 없으면 phase, 없으면 0."""
        return (r.extra or {}).get("scenario") or r.phase or 0

    # page_id 조건부 sort — 영역 그룹 sort 적용 페이지만 label_group 사용
    if page_id in _PAGE_IDS_USE_LABEL_GROUP_SORT:
        sort_key = lambda x: (_scenario_num(x), _label_group_prefix(x), x.order or 9999)
    else:
        # 기존 동작 (시나리오 → order) — RansomCruncher 등 영향 없음
        sort_key = lambda x: (_scenario_num(x), x.order or 9999)

    for r in sorted(report.results, key=sort_key):
        badge, css = _STATUS_BADGE.get(r.status, ('?', ''))
        scenario   = _scenario_label(r, is_list_page)
        expected, actual = _expected_vs_actual(r)

        # 시나리오 구분 헤더 행 (4컬럼 전체 span)
        if scenario != prev_scenario:
            rows.append(f"""
        <tr class="scenario-header">
          <td colspan="4">{html.escape(scenario)}</td>
        </tr>""")
            prev_scenario = scenario

        rows.append(f"""
        <tr class="row-{css}">
          <td class="col-label">{html.escape(r.label)}</td>
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
        # page_id 조건부 sort — 영역 그룹 sort 적용 페이지만 (RansomCruncher 등 무관)
        if page_id in _PAGE_IDS_USE_LABEL_GROUP_SORT:
            sc_num = lambda r: (r.extra or {}).get("scenario") or r.phase or 0
            bug_items.sort(key=lambda r: (sc_num(r), _label_group_prefix(r), r.order or 9999))
        for r in bug_items:
            issue_num += 1
            badge, css = _STATUS_BADGE.get(r.status, ('?', ''))
            scenario   = _scenario_label(r, is_list)
            steps      = _reproduce_steps(r)
            expected, actual = _expected_vs_actual(r)
            severity   = "높음" if r.status in ("fail", "error") else "낮음"
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
          <div class="defect-title">{html.escape(r.label)}</div>
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
.result-table tr:hover td { background: #fafbfc; }
.col-label    { width: 40%; }
.col-status   { width: 10%; text-align: center; white-space: nowrap; }
.col-expected { width: 22%; font-size: 12px; color: #555; }
.col-actual   { width: 28%; font-size: 12px; color: #555; }
.row-bug-high td { background: #fff8f8; }
.row-bug-low td  { background: #fffdf0; }
.row-error td    { background: #fdf0ff; }
/* 시나리오 구분 헤더 */
.scenario-header td { background: #e8f0f8; color: #1e3a5f; font-weight: 700;
  font-size: 13px; padding: 8px 14px; border-top: 2px solid #b8cfe8;
  border-bottom: 1px solid #b8cfe8; letter-spacing: 0.3px; }

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
) -> Path:
    """
    reports: [(page_id, PageScanReport), ...] 순서대로 전달
    반환값: 생성된 HTML 파일 경로
    """
    now       = datetime.now()
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
              &#x2705; {p}  &#x274C; {f}  &#x26A0;&#xFE0F; {k}  &#x1F534; {e}
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
    total_f = sum(len(r.failed)     for _, r in reports)
    total_k = sum(len(r.known_bugs) for _, r in reports)
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
      전체 결과: &#x2705; {total_p}  &#x274C; {total_f}  &#x26A0;&#xFE0F; {total_k}  &#x1F534; {total_e} &nbsp;|&nbsp;
      {overall}
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
