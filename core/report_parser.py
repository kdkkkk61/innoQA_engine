"""
core/report_parser.py — QA HTML 보고서 파싱 모듈

기존 QA HTML 보고서를 BeautifulSoup으로 파싱해서 dict 반환.
"""
from __future__ import annotations

import re
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger("qa_app.report_parser")


def parse_report(html_path: str) -> dict | None:
    """
    QA HTML 보고서 파일을 파싱해서 dict 반환.
    파싱 실패 시 None 반환.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("[ERR] beautifulsoup4 미설치 — pip install beautifulsoup4")
        return None

    p = Path(html_path)
    if not p.exists():
        log.warning(f"[WARN] 리포트 파일 없음: {html_path}")
        return None

    try:
        html_text = p.read_text(encoding="utf-8")
    except Exception as e:
        log.error(f"[ERR] 파일 읽기 실패: {e}")
        return None

    soup = BeautifulSoup(html_text, "html.parser")

    # ── 제품명 추출 (title 태그) ─────────────────────────────────────────
    product = _extract_product(soup)

    # ── 날짜/시간 추출 (meta div) ────────────────────────────────────────
    timestamp = _extract_timestamp(soup)

    # ── pass/fail/bug/error 수 추출 ──────────────────────────────────────
    counts = _extract_counts(soup)

    # ── pages 요약 추출 ──────────────────────────────────────────────────
    pages = _extract_pages(soup)

    # ── results 상세 추출 ────────────────────────────────────────────────
    results = _extract_results(soup)

    parsed = {
        "product":   product,
        "timestamp": timestamp,
        "html_path": str(p.resolve()),
        "total":     counts["total"],
        "pass":      counts["pass"],
        "fail":      counts["fail"],
        "bug":       counts["bug"],
        "error":     counts["error"],
        "skip":      0,
        "pages":     pages,
        "results":   results,
    }
    log.info(f"[OK] 파싱 완료: {p.name} | pass={counts['pass']} fail={counts['fail']} bug={counts['bug']}")
    return parsed


# ── 내부 헬퍼 함수 ────────────────────────────────────────────────────────

def _extract_product(soup) -> str:
    """title 태그에서 제품명 추출. 'QA 보고서 — {제품명} {날짜}' 패턴."""
    title_tag = soup.find("title")
    if not title_tag:
        return "Unknown"
    title_text = title_tag.get_text(strip=True)
    # 패턴: "QA 보고서 — RansomCruncher 2026-04-02"
    m = re.search(r'QA\s+보고서\s*[—\-]+\s*(.+?)\s+\d{4}-\d{2}-\d{2}', title_text)
    if m:
        return m.group(1).strip()
    # fallback: 대시 이후 첫 단어
    m2 = re.search(r'[—\-]+\s*(\S+)', title_text)
    if m2:
        return m2.group(1).strip()
    return "Unknown"


def _extract_timestamp(soup) -> str:
    """meta div 텍스트에서 날짜/시간 추출. ISO 포맷 문자열 반환."""
    # 전체 텍스트에서 생성일시 패턴 탐색
    meta_div = soup.find("div", class_="meta")
    if not meta_div:
        # fallback: 전체 텍스트에서 탐색
        full_text = soup.get_text()
    else:
        full_text = meta_div.get_text()

    m = re.search(r'생성일시\s*:\s*(\d{4})년\s*(\d{2})월\s*(\d{2})일\s+(\d{2}):(\d{2})', full_text)
    if m:
        year, month, day, hour, minute = m.groups()
        dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
        return dt.isoformat()

    # fallback: 파일명에서 날짜 추출 불가능 → 현재 시각
    log.warning("[WARN] 생성일시 파싱 실패 — 현재 시각 사용")
    return datetime.now().isoformat()


def _extract_counts(soup) -> dict:
    """meta div에서 pass/fail/bug/error 카운트 추출."""
    meta_div = soup.find("div", class_="meta")
    text = meta_div.get_text() if meta_div else soup.get_text()

    # 패턴: "✅ 84  ❌ 0  ⚠️ 3  💥 0"
    pass_m  = re.search(r'✅\s*(\d+)', text)
    fail_m  = re.search(r'❌\s*(\d+)', text)
    bug_m   = re.search(r'⚠️?\s*(\d+)', text)
    error_m = re.search(r'💥\s*(\d+)', text)

    pass_cnt  = int(pass_m.group(1))  if pass_m  else 0
    fail_cnt  = int(fail_m.group(1))  if fail_m  else 0
    bug_cnt   = int(bug_m.group(1))   if bug_m   else 0
    error_cnt = int(error_m.group(1)) if error_m else 0
    total     = pass_cnt + fail_cnt + bug_cnt + error_cnt

    return {
        "pass":  pass_cnt,
        "fail":  fail_cnt,
        "bug":   bug_cnt,
        "error": error_cnt,
        "total": total,
    }


def _extract_pages(soup) -> list[dict]:
    """
    .page-label div에서 페이지 레이블과 카운트 추출.
    결과 테이블과 page-label을 매핑해서 페이지별 집계.
    """
    pages = []
    page_labels_seen = []

    page_label_divs = soup.find_all("div", class_="page-label")
    for div in page_label_divs:
        # span 제거 후 텍스트 추출 (앞부분이 page_label)
        for span in div.find_all("span"):
            span.decompose()
        label = div.get_text(strip=True)
        if label and label not in page_labels_seen:
            page_labels_seen.append(label)

    # 페이지별 결과 집계
    result_rows = soup.find_all("tr", class_=re.compile(r'row-(pass|fail|bug|error|skip)'))
    page_counts: dict[str, dict] = {}

    for row in result_rows:
        # 해당 row의 page_label 찾기 (이전 page-label div)
        prev_label = _find_preceding_page_label(row)
        if not prev_label:
            prev_label = page_labels_seen[0] if page_labels_seen else "Unknown"

        if prev_label not in page_counts:
            page_counts[prev_label] = {"pass": 0, "fail": 0, "bug": 0, "error": 0, "skip": 0, "total": 0}

        classes = row.get("class", [])
        status = _row_class_to_status(classes)
        page_counts[prev_label][status] += 1
        page_counts[prev_label]["total"] += 1

    for label in page_labels_seen:
        cnt = page_counts.get(label, {"pass": 0, "fail": 0, "bug": 0, "error": 0, "total": 0})
        pages.append({
            "page_id":    label,  # page_id는 label로 대체
            "page_label": label,
            "total":      cnt["total"],
            "pass":       cnt["pass"],
            "fail":       cnt["fail"],
            "bug":        cnt["bug"],
            "error":      cnt["error"],
        })

    return pages


def _find_preceding_page_label(row) -> str | None:
    """
    결과 tr 이전에 있는 가장 가까운 .page-label div의 텍스트 반환.
    DOM 트리 탐색: row → tbody → table → 부모 section → page-label
    """
    # row 이전 형제/사촌 탐색은 복잡하므로 부모를 거슬러 올라가는 방식 사용
    # result-table > tbody > tr 구조에서
    # section > page-label > table 순서이므로 section에서 page-label 찾기
    for parent in row.parents:
        cls = parent.get("class", [])
        if "section" in cls:
            # section 안에서 이 row보다 앞에 있는 page-label 찾기
            labels_in_section = parent.find_all("div", class_="page-label")
            if labels_in_section:
                # 여러 page-label이 있을 경우 row보다 앞의 것 중 마지막 선택
                for div in reversed(labels_in_section):
                    # div가 row보다 문서상 앞에 있는지 확인
                    for span in div.find_all("span"):
                        span.decompose()
                    text = div.get_text(strip=True)
                    if text:
                        return text
            break
    return None


def _row_class_to_status(classes: list) -> str:
    """tr class 목록에서 status 문자열 반환."""
    class_str = " ".join(classes)
    if "row-pass" in class_str:
        return "pass"
    if "row-fail" in class_str:
        return "fail"
    if "row-bug" in class_str:
        return "bug"
    if "row-error" in class_str:
        return "error"
    if "row-skip" in class_str:
        return "skip"
    return "pass"


def _extract_results(soup) -> list[dict]:
    """
    .result-table tbody tr 에서 결과 행 상세 추출.
    page_label은 이전 .page-label div에서 추론.

    두 가지 HTML 포맷을 모두 지원:
    - 구버전: 5개 셀 [scenario, label, status_badge, expected, actual]
    - 신버전: scenario-header 행(1셀) + 데이터 행 4개 셀 [label, status_badge, expected, actual]
    """
    results = []

    # section 단위로 순회 (page-label과 table 쌍으로 처리)
    sections = soup.find_all("div", class_="section")
    for section in sections:
        # section 내 page-label과 result-table을 순서대로 추출
        page_label_divs = section.find_all("div", class_="page-label")
        result_tables   = section.find_all("table", class_="result-table")

        if not result_tables:
            continue

        for i, table in enumerate(result_tables):
            # 해당 table 이전의 page-label 찾기 (section 내 순서 기준)
            label = _get_page_label_for_table(section, table, page_label_divs)

            tbody = table.find("tbody")
            if not tbody:
                continue

            rows = tbody.find_all("tr")
            current_scenario = ""

            for row in rows:
                classes = row.get("class", [])
                cells   = row.find_all("td")

                # 신버전: scenario-header 행 (colspan=1, class=scenario-header)
                if "scenario-header" in classes:
                    current_scenario = cells[0].get_text(strip=True) if cells else ""
                    continue

                # 구버전: 5개 셀 [scenario, label, status_badge, expected, actual]
                if len(cells) == 5:
                    status   = _row_class_to_status(classes)
                    scenario = cells[0].get_text(strip=True)
                    lbl      = cells[1].get_text(strip=True)
                    expected = cells[3].get_text(strip=True)
                    actual   = cells[4].get_text(strip=True)
                    results.append({
                        "page_label": label,
                        "scenario":   scenario,
                        "label":      lbl,
                        "status":     status,
                        "expected":   expected,
                        "actual":     actual,
                    })
                    continue

                # 신버전: 4개 셀 [label, status_badge, expected, actual]
                if len(cells) == 4:
                    status   = _row_class_to_status(classes)
                    lbl      = cells[0].get_text(strip=True)
                    expected = cells[2].get_text(strip=True)
                    actual   = cells[3].get_text(strip=True)
                    results.append({
                        "page_label": label,
                        "scenario":   current_scenario,
                        "label":      lbl,
                        "status":     status,
                        "expected":   expected,
                        "actual":     actual,
                    })
                    continue

                # 그 외 (헤더 행 등): 무시

    return results


def _get_page_label_for_table(section, table, page_label_divs: list) -> str:
    """section 내에서 table 이전에 위치한 가장 가까운 page-label 텍스트 반환."""
    # section의 모든 자식을 순서대로 순회하면서 table 앞에 나온 마지막 page-label 기록
    last_label = None
    for child in section.descendants:
        if child in page_label_divs:
            # span 제거하고 텍스트 추출
            import copy
            div_copy = copy.copy(child)
            for span in child.find_all("span"):
                pass  # 이미 decompose됐을 수 있음
            # 직접 NavigableString 합산
            texts = [t.strip() for t in child.strings if t.strip()]
            if texts:
                last_label = texts[0]
        if child is table:
            break
    return last_label or "Unknown"
