"""
core/reporter.py — 스캔 결과 출력 공통 함수

print_phase_report(), print_combined_report() 공통화.
test 파일마다 중복 정의되던 _print_phase_report() 코드를 한 곳으로 통합.

출력 규칙 (CLAUDE.md 필수 요건):
  - order 값 오름차순 정렬 (화면 위→아래 시각적 순서)
  - 탭 구간 헤더: report.tab_sections 기반
  - toggle_checkbox dep 트리: 부모 바로 아래 └ 형식
  - required_submit: 해당 필드 아래 역색인으로 표시
"""
from __future__ import annotations
from core.models import PageScanReport

_PHASE_LABEL: dict[int, str] = {
    1: "Phase 1 (초기값+필수입력)",
    2: "Phase 2 (UI 동작)",
    3: "Phase 3 (수정)",
}

_STATUS_ICON: dict[str, str] = {
    "pass":      "✅",
    "fail":      "❌",
    "known_bug": "⚠️",
    "skip":      "⏭",
    "error":     "💥",
}

_PATTERN_FALLBACK: dict[str, int] = {
    "initial_state":   0,
    "modal_open":      1,
    "text_input":      2,
    "radio_group":     3,
    "toggle_checkbox": 4,
    "plain_checkbox":  5,
    "tag_input":       6,
    "button_action":   7,
    "required_submit": 8,
    "auto_detect":     9,
}


def print_phase_report(report: PageScanReport | None, phase: int) -> None:
    """
    페이즈별 스캔 결과 출력.
    - order 기준 오름차순 정렬 (화면 위→아래 순서)
    - 탭 구간 헤더 출력 (tab_sections 있을 때만)
    - toggle_checkbox dep 트리 출력 (CLAUDE.md 필수)
    - required_submit → missing_field 역색인으로 해당 필드 아래 표시
    """
    if report is None:
        print(f"\n[{_PHASE_LABEL.get(phase, f'Phase {phase}')}] 결과 없음")
        return

    print(f"\n{'═' * 60}")
    print(f"  {_PHASE_LABEL.get(phase, f'Phase {phase}')}")
    print(f"{'═' * 60}")
    print(f"  {report.summary()}")

    def _sort_key(r):
        if r.order is not None:
            return r.order
        return 10_000 + _PATTERN_FALLBACK.get(r.pattern, 99) * 10

    def _tab_for_order(order):
        if order is None or not report.tab_sections:
            return None
        current = None
        for ts in report.tab_sections:
            if order >= ts["start_order"]:
                current = ts["label"]
        return current

    def _field_id(r) -> str:
        if r.pattern == "tag_input":
            return r.extra.get("tag_id", "")
        if "#" in r.selector:
            return r.selector.split("#")[-1]
        return ""

    # required_submit → missing_field 역색인
    req_map: dict[str, list] = {}
    shown_req: set[int] = set()
    for r in report.results:
        if r.pattern == "required_submit":
            mf = r.extra.get("missing_field", "")
            if mf:
                req_map.setdefault(mf, []).append(r)

    field_ids_in_report: set[str] = set()
    for r in report.results:
        fid = _field_id(r)
        if fid:
            field_ids_in_report.add(fid)

    sorted_results    = sorted(report.results, key=_sort_key)
    current_tab_label = None

    for r in sorted_results:
        if r.pattern != "required_submit":
            tab_label = _tab_for_order(r.order)
            if tab_label != current_tab_label:
                current_tab_label = tab_label
                if current_tab_label:
                    bar = "─" * 14
                    print(f"\n  {bar} [ {current_tab_label} ] {bar}")

        # 부모 필드에 이미 붙여 출력된 required_submit은 스킵
        if r.pattern == "required_submit" and id(r) in shown_req:
            continue

        # required_submit 중 missing_field가 있지만 해당 Phase에 부모 필드가 없는 경우
        # → missing_field_label로 가상 필드 행으로 표시 (Phase 1 케이스)
        if r.pattern == "required_submit":
            mf  = r.extra.get("missing_field", "")
            mfl = r.extra.get("missing_field_label", "")
            if mf and mfl and mf not in field_ids_in_report:
                req_icon = _STATUS_ICON.get(r.status, "?")
                print(f"  {req_icon} [{mfl}] 미입력 경고: {r.detail}")
                shown_req.add(id(r))
                continue

        icon = _STATUS_ICON.get(r.status, "?")
        print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")

        # toggle dep 트리 (CLAUDE.md 필수 요건)
        if r.pattern == "toggle_checkbox":
            dep_labels  = r.extra.get("dependent_labels",  [])
            dep_types   = r.extra.get("dependent_types",   [])
            dep_results = r.extra.get("dependent_results", [])
            for i, dep_label in enumerate(dep_labels):
                dep_type   = dep_types[i]   if i < len(dep_types)   else "field"
                dep_res    = dep_results[i]  if i < len(dep_results) else {}
                dep_status = dep_res.get("status", "skip")
                dep_icon   = _STATUS_ICON.get(dep_status, "?")
                dep_detail = dep_res.get("detail", "")
                detail_str = f" — {dep_detail}" if dep_detail else ""
                print(f"       └ {dep_icon} [{dep_type}] {dep_label}{detail_str}")

        # 필수 입력 경고 — 해당 필드 바로 아래
        fid = _field_id(r)
        if fid and fid in req_map:
            for req_r in req_map[fid]:
                req_icon = _STATUS_ICON.get(req_r.status, "?")
                print(f"       └ {req_icon} [required] 미입력 경고: {req_r.detail}")
                shown_req.add(id(req_r))


def print_combined_report(combined: PageScanReport) -> None:
    """전체 결과 요약 + known_bug 추적 섹션 출력."""
    print(f"\n{'═' * 60}")
    print(f"  전체 결과: {combined.summary()}")
    print(f"{'═' * 60}")

    if combined.known_bugs:
        print(f"\n{'─' * 60}")
        print(f"  ⚠️  추적 중인 결함 {len(combined.known_bugs)}건 — 수정 필요 (fail 카운트 제외)")
        print(f"{'─' * 60}")
        for r in combined.known_bugs:
            phase_tag = f"[Phase {r.phase}]" if r.phase else ""
            print(f"  ⚠️  {phase_tag}[{r.pattern}] {r.label}")
            print(f"       → {r.detail}")
        print(f"{'─' * 60}")
        print(f"  💡 known_bugs.yaml 에서 status: open → fixed 로 변경 시 회귀 감지 활성화")
        print(f"{'─' * 60}\n")
