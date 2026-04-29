"""
validators/list_ui.py — 시나리오 1: UI 구조 공통 스캔

modal_form / list_page 구분 없이 동일하게 동작.
YAML list_ui 섹션을 읽어 탭 / 검색 / 테이블 헤더를 검증한다.

YAML 구조 (config/scan_hints/{page_id}.yaml):

  list_ui:
    tabs:                         # 없거나 [] 이면 [SKIP] skip
      - label: "예외 프로세스"
        param_key: "processType"
        param_value: "EXCEPT_PROCESS"

    search:
      input:     "input#searchText"
      button:    "button#searchBtn"   # 있으면 버튼 클릭, 없으면 Enter
      maxlength: 20                   # null 이면 미확인
      filters:                        # 드롭다운 등 추가 필터 (선택)
        - { selector: "select#typeFilter", label: "유형 필터" }

    table:
      headers:
        - "정책 이름"
        - "등록일"
        - "수정일"
"""
from __future__ import annotations

import urllib.parse

from core.models import PageScanReport, ScanResult

_PHASE = 1  # 시나리오 1 고정


def scan_list_ui(
    page,
    hints: dict,
    report: PageScanReport,
) -> None:
    """list_ui 섹션 전체를 순서대로 스캔해 결과를 report에 추가."""
    cfg = hints.get("list_ui")
    if not cfg:
        return

    _scan_tabs(page, cfg, report)
    _scan_search(page, cfg, report)
    _scan_buttons(page, cfg, report)
    _scan_table(page, cfg, report)


# ──────────────────────────────────────────────────────────────────────────────
# 탭 전환
# ──────────────────────────────────────────────────────────────────────────────

def _scan_tabs(page, cfg: dict, report: PageScanReport) -> None:
    tabs = cfg.get("tabs", [])

    if not tabs:
        report.results.append(ScanResult(
            pattern="list_tab", selector="",
            label="탭 전환",
            status="skip", detail="탭 없음 (단일 뷰 페이지)",
            order=10, phase=_PHASE,
        ))
        return

    for tab in tabs:
        label     = tab["label"]
        param_key = tab.get("param_key", "")
        param_val = tab.get("param_value", "")
        sel       = f"a:has-text('{label}')"
        try:
            page.locator(sel).first.evaluate("el => el.click()")
            page.wait_for_timeout(500)
            url = page.url
            if param_val and param_val in url:
                report.results.append(ScanResult(
                    pattern="list_tab", selector=sel,
                    label=f"탭 전환 — {label}",
                    status="pass",
                    detail=f"클릭 후 URL 파라미터 확인: {param_key}={param_val}",
                    order=10, phase=_PHASE,
                ))
            elif not param_val:
                report.results.append(ScanResult(
                    pattern="list_tab", selector=sel,
                    label=f"탭 전환 — {label}",
                    status="pass", detail="탭 클릭 완료 (param_value 미지정)",
                    order=10, phase=_PHASE,
                ))
            else:
                report.results.append(ScanResult(
                    pattern="list_tab", selector=sel,
                    label=f"탭 전환 — {label}",
                    status="fail",
                    detail=f"URL에 {param_key}={param_val} 없음",
                    order=10, phase=_PHASE,
                ))
        except Exception as e:
            report.results.append(ScanResult(
                pattern="list_tab", selector=sel,
                label=f"탭 전환 — {label}",
                status="error", detail=str(e),
                order=10, phase=_PHASE,
            ))

    # 첫 번째 탭으로 복원
    if tabs:
        try:
            first_sel = f"a:has-text('{tabs[0]['label']}')"
            page.locator(first_sel).first.evaluate("el => el.click()")
            page.wait_for_timeout(400)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# 검색창
# ──────────────────────────────────────────────────────────────────────────────

def _scan_search(page, cfg: dict, report: PageScanReport) -> None:
    search = cfg.get("search")
    if not search:
        report.results.append(ScanResult(
            pattern="list_search", selector="",
            label="검색창",
            status="skip", detail="search 섹션 없음",
            order=20, phase=_PHASE,
        ))
        return

    inp_sel = search.get("input", "")
    btn_sel = search.get("button", "")
    maxlen  = search.get("maxlength")
    label   = search.get("label", "검색창")

    try:
        loc = page.locator(inp_sel).first
        if loc.count() == 0:
            report.results.append(ScanResult(
                pattern="list_search", selector=inp_sel,
                label=label, status="fail",
                detail=f"검색 입력창 없음: {inp_sel}",
                order=20, phase=_PHASE,
            ))
            return

        # ① 존재 확인 + maxlength 속성
        checks = ["검색 입력창 존재"]
        failures = []

        if maxlen is not None:
            actual_ml = loc.get_attribute("maxlength")
            if actual_ml is None:
                failures.append(f"maxlength 속성 없음 (기대: {maxlen})")
            elif int(actual_ml) != maxlen:
                failures.append(f"maxlength 불일치 (기대: {maxlen}, 실제: {actual_ml})")
            else:
                checks.append(f"maxlength={maxlen} 확인")

        # ② 검색 버튼 존재
        if btn_sel:
            btn_exists = page.locator(btn_sel).count() > 0
            if btn_exists:
                checks.append("검색 버튼 존재")
            else:
                failures.append(f"검색 버튼 없음: {btn_sel}")

        # ③ 추가 필터 존재 확인
        for f in search.get("filters", []):
            f_sel   = f.get("selector", "")
            f_label = f.get("label", f_sel)
            if page.locator(f_sel).count() > 0:
                checks.append(f"필터 존재 — {f_label}")
            else:
                failures.append(f"필터 없음 — {f_label} ({f_sel})")

        status = "fail" if failures else "pass"
        detail = " / ".join(checks + [f"[FAIL] {f}" for f in failures])
        report.results.append(ScanResult(
            pattern="list_search", selector=inp_sel,
            label=label, status=status, detail=detail,
            order=20, phase=_PHASE,
        ))

        if failures:
            return  # 구조 자체 문제면 동작 테스트 건너뜀

        # ④ 검색 실행 동작 확인
        keyword = "ui_scan_kw"
        loc.fill(keyword)
        page.wait_for_timeout(200)

        if btn_sel and page.locator(btn_sel).count() > 0:
            page.locator(btn_sel).first.evaluate("el => el.click()")
        else:
            loc.dispatch_event("keydown", {"keyCode": 13, "which": 13})
            loc.dispatch_event("keyup",   {"keyCode": 13, "which": 13})
        page.wait_for_timeout(600)

        url = page.url
        decoded = urllib.parse.unquote(url)
        if keyword in decoded:
            report.results.append(ScanResult(
                pattern="list_search", selector=inp_sel,
                label=f"{label} — 검색 실행",
                status="pass",
                detail="검색어 입력 후 URL 파라미터 반영 확인",
                order=21, phase=_PHASE,
            ))
        else:
            report.results.append(ScanResult(
                pattern="list_search", selector=inp_sel,
                label=f"{label} — 검색 실행",
                status="fail",
                detail=f"검색 후 URL에 키워드 미반영 (url={url!r})",
                order=21, phase=_PHASE,
            ))

        # ⑤ 검색 초기화
        loc.fill("")
        if btn_sel and page.locator(btn_sel).count() > 0:
            page.locator(btn_sel).first.evaluate("el => el.click()")
        else:
            loc.dispatch_event("keydown", {"keyCode": 13, "which": 13})
            loc.dispatch_event("keyup",   {"keyCode": 13, "which": 13})
        page.wait_for_timeout(400)

    except Exception as e:
        report.results.append(ScanResult(
            pattern="list_search", selector=inp_sel,
            label=label, status="error", detail=str(e),
            order=20, phase=_PHASE,
        ))


# ──────────────────────────────────────────────────────────────────────────────
# 버튼 존재 확인
# YAML: list_ui.buttons: [{selector, label}, ...]
# ──────────────────────────────────────────────────────────────────────────────

def _scan_buttons(page, cfg: dict, report: PageScanReport) -> None:
    buttons = cfg.get("buttons", [])
    if not buttons:
        return

    for i, btn in enumerate(buttons):
        sel   = btn.get("selector", "")
        label = btn.get("label", sel)
        order = 25 + i  # 검색(20~21) 다음, 테이블(30) 이전
        try:
            exists = page.locator(sel).count() > 0
            if exists:
                report.results.append(ScanResult(
                    pattern="list_button", selector=sel,
                    label=f"버튼 존재 — {label}",
                    status="pass",
                    detail=f"{sel} 존재 확인",
                    order=order, phase=_PHASE,
                ))
            else:
                report.results.append(ScanResult(
                    pattern="list_button", selector=sel,
                    label=f"버튼 존재 — {label}",
                    status="fail",
                    detail=f"버튼 없음: {sel}",
                    order=order, phase=_PHASE,
                ))
        except Exception as e:
            report.results.append(ScanResult(
                pattern="list_button", selector=sel,
                label=f"버튼 존재 — {label}",
                status="error", detail=str(e),
                order=order, phase=_PHASE,
            ))


# ──────────────────────────────────────────────────────────────────────────────
# 테이블 헤더
# ──────────────────────────────────────────────────────────────────────────────

def _scan_table(page, cfg: dict, report: PageScanReport) -> None:
    tbl = cfg.get("table")
    if not tbl:
        report.results.append(ScanResult(
            pattern="list_table", selector="",
            label="테이블 컬럼 구조",
            status="skip", detail="table 섹션 없음",
            order=30, phase=_PHASE,
        ))
        return

    expected = tbl.get("headers", [])
    if not expected:
        return

    try:
        actual = [
            h.inner_text().strip()
            for h in page.locator("table th").all()
            if h.inner_text().strip()
        ]
        missing = [h for h in expected if h not in actual]
        if not missing:
            report.results.append(ScanResult(
                pattern="list_table", selector="table th",
                label="테이블 컬럼 구조",
                status="pass",
                detail=f"컬럼 {len(expected)}개 확인: {', '.join(expected)}",
                order=30, phase=_PHASE,
            ))
        else:
            report.results.append(ScanResult(
                pattern="list_table", selector="table th",
                label="테이블 컬럼 구조",
                status="fail",
                detail=f"누락 컬럼: {', '.join(missing)} (실제: {actual})",
                order=30, phase=_PHASE,
            ))
    except Exception as e:
        report.results.append(ScanResult(
            pattern="list_table", selector="table th",
            label="테이블 컬럼 구조",
            status="error", detail=str(e),
            order=30, phase=_PHASE,
        ))
