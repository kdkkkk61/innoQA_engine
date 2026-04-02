"""
core/html_reporter.py — QA 보고서 HTML 자동 생성

실행 후 reports/QA_{product}_{날짜}.html 생성.
수신자: UI담당자 / 에이전트 개발담당자
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.models import PageScanReport, ScanResult

# ── 페이지 ID → 표시 이름 ──────────────────────────────────────────
_PAGE_LABELS: dict[str, str] = {
    "ransom_detect_policy": "탐지정책",
    "rdp_policy":           "RDP 정책",
    "common_process":       "공통 프로세스",
}

# ── 시나리오 경계 (list_page 기준) ─────────────────────────────────
_LIST_SCENARIO_THRESHOLDS = [
    (0,   "시나리오 1: UI 구조"),
    (45,  "시나리오 2: 입력 동작"),
    (100, "시나리오 3: CRUD"),
]

# list_page 전용 패턴 — 이 중 하나라도 있으면 list_page 모드로 판단
_LIST_PAGE_PATTERNS = {
    "list_tab", "list_button", "list_table", "list_search",
    "list_modal", "list_modal_required", "list_modal_overflow",
    "list_crud", "list_modify", "list_modify_save",
    "list_modify_verify", "list_modify_bug",
}

_STATUS_BADGE = {
    "pass":      ('<span class="badge pass">✅ PASS</span>', "pass"),
    "fail":      ('<span class="badge fail">❌ FAIL</span>', "fail"),
    "known_bug": ('<span class="badge bug">⚠️ BUG</span>',  "bug"),
    "error":     ('<span class="badge error">💥 ERROR</span>', "error"),
    "skip":      ('<span class="badge skip">⏭ SKIP</span>',  "skip"),
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
    """기댓값 / 실제값 추출."""
    if r.status == "pass":
        return "정상 동작", r.detail
    if "기댓값" in r.detail and "실제" in r.detail:
        parts = r.detail.split(",")
        exp = parts[0].replace("기댓값 ", "").strip().strip("'")
        act = parts[1].replace("실제 ", "").strip().strip("'") if len(parts) > 1 else ""
        return exp, act
    if r.status == "known_bug":
        return "클라이언트 입력 검증 또는 정상 저장", r.detail
    return "정상 동작", r.detail


# ── 시나리오 레이블 결정 ───────────────────────────────────────────

def _scenario_label(r: ScanResult, is_list_page: bool) -> str:
    if is_list_page:
        order = r.order or 9999
        idx = sum(1 for t, _ in _LIST_SCENARIO_THRESHOLDS if order >= t) - 1
        idx = max(0, min(idx, len(_LIST_SCENARIO_THRESHOLDS) - 1))
        return _LIST_SCENARIO_THRESHOLDS[idx][1]
    phase_map = {
        1: "시나리오 1: 구조 확인",
        2: "시나리오 2: 동작 검증",
        3: "시나리오 3: 수정 시나리오",
        4: "시나리오 4: 케이스 검증",
    }
    return phase_map.get(r.phase, f"시나리오 {r.phase}")


# ── HTML 조각 생성 ─────────────────────────────────────────────────

def _render_summary_card(page_id: str, report: PageScanReport) -> str:
    label  = _PAGE_LABELS.get(page_id, page_id)
    p, f   = len(report.passed), len(report.failed)
    k, e   = len(report.known_bugs), len(report.errors)
    total  = p + f + k + e
    status = "🔴 결함 있음" if (f + e) > 0 else ("🟡 버그 추적 중" if k > 0 else "🟢 정상")
    return f"""
    <div class="summary-card {'has-fail' if f+e > 0 else ('has-bug' if k > 0 else 'all-pass')}">
      <div class="card-title">{html.escape(label)}</div>
      <div class="card-status">{status}</div>
      <div class="card-counts">
        <span class="cnt pass">✅ {p}</span>
        <span class="cnt fail">❌ {f}</span>
        <span class="cnt bug">⚠️ {k}</span>
        <span class="cnt error">💥 {e}</span>
      </div>
      <div class="card-total">총 {total}건 검증</div>
    </div>"""


def _render_results_table(report: PageScanReport, is_list_page: bool) -> str:
    rows = []
    prev_scenario = None
    for r in sorted(report.results, key=lambda x: (x.order or 9999, x.phase or 0)):
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
          <th class="col-status">결과</th>
          <th class="col-expected">기댓값</th>
          <th class="col-actual">실제값</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def _render_defect_section(all_reports: list[tuple[str, PageScanReport]]) -> str:
    """전체 페이지에서 known_bug + fail 항목 모아서 결함 목록 생성."""
    defects = []
    for page_id, report in all_reports:
        label      = _PAGE_LABELS.get(page_id, page_id)
        is_list    = any(r.pattern in _LIST_PAGE_PATTERNS for r in report.results)
        bug_items  = [r for r in report.results if r.status in ("known_bug", "fail", "error")]
        for r in bug_items:
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
                if ss_abs.exists():
                    ss_uri = ss_abs.as_posix()
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
        <div class="defect-card defect-{css}">
          <div class="defect-header">
            {badge}
            <span class="defect-page">{html.escape(label)}</span>
            <span class="defect-scenario">{html.escape(scenario)}</span>
            <span class="defect-severity severity-{severity}">심각도: {severity}</span>
          </div>
          <div class="defect-title">{html.escape(r.label)}</div>
          <table class="defect-detail">
            <tr><th>재현 방법</th><td>{steps}</td></tr>
            <tr><th>기댓값</th><td>{html.escape(expected)}</td></tr>
            <tr><th>실제 결과</th><td>{html.escape(actual)}</td></tr>
            {ss_html}
          </table>
        </div>""")

    if not defects:
        return '<p class="no-defect">🎉 발견된 결함 없음</p>'
    return ''.join(defects)


# ── CSS ──────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #f5f7fa; color: #333; font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }

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
.cnt.pass  { color: #27ae60; }
.cnt.fail  { color: #e74c3c; }
.cnt.bug   { color: #f39c12; }
.cnt.error { color: #c0392b; }
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
.row-fail td  { background: #fff8f8; }
.row-bug td   { background: #fffdf0; }
.row-error td { background: #fff5f5; }
/* 시나리오 구분 헤더 */
.scenario-header td { background: #e8f0f8; color: #1e3a5f; font-weight: 700;
  font-size: 13px; padding: 8px 14px; border-top: 2px solid #b8cfe8;
  border-bottom: 1px solid #b8cfe8; letter-spacing: 0.3px; }

/* 배지 */
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.badge.pass  { background: #e8f8ef; color: #27ae60; }
.badge.fail  { background: #fde8e8; color: #e74c3c; }
.badge.bug   { background: #fef9e7; color: #f39c12; }
.badge.error { background: #fde8e8; color: #c0392b; }
.badge.skip  { background: #f0f0f0; color: #888; }

/* 결함 목록 */
.defect-card { background: white; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
.defect-fail  { border-left: 4px solid #e74c3c; }
.defect-bug   { border-left: 4px solid #f39c12; }
.defect-error { border-left: 4px solid #c0392b; }
.defect-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
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

    # ── 페이지별 결과 테이블 ──────────────────────────────────────
    page_sections = []
    for page_id, report in reports:
        label      = _PAGE_LABELS.get(page_id, page_id)
        is_list    = any(r.pattern in _LIST_PAGE_PATTERNS for r in report.results)
        table_html = _render_results_table(report, is_list)
        p, f, k, e = (len(report.passed), len(report.failed),
                      len(report.known_bugs), len(report.errors))
        page_sections.append(f"""
        <div class="page-label">{html.escape(label)}
          <span style="font-weight:400;font-size:13px;color:#666;margin-left:10px;">
            ✅ {p}  ❌ {f}  ⚠️ {k}  💥 {e}
          </span>
        </div>
        {table_html}""")

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
                f'<div class="screenshot"><img src="{s.resolve().as_posix()}" alt="{html.escape(s.name)}"></div></div>'
                for s in screenshots
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
      전체 결과: ✅ {total_p}  ❌ {total_f}  ⚠️ {total_k}  💥 {total_e} &nbsp;|&nbsp;
      {overall}
    </div>
  </div>

  <div class="section">
    <div class="section-title">📊 페이지별 요약</div>
    <div class="summary-grid">{summary_cards}</div>
  </div>

  <div class="section">
    <div class="section-title">📋 검증 결과 상세</div>
    {''.join(page_sections)}
  </div>

  <div class="section">
    <div class="section-title">🐛 발견된 결함 ({total_f + total_k + total_e}건)</div>
    {defect_html}
  </div>

  {screenshot_html}

</div>
</body>
</html>"""

    out_path.write_text(html_content, encoding="utf-8")
    print(f"\n[HTML 리포트] {out_path}")
    return out_path
