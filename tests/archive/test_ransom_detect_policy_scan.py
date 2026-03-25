"""
tests/test_ransom_detect_policy_scan.py — 탐지정책 시나리오 기반 QA 스캔

대상 페이지: RansomCruncher > 탐지정책 (managerRansomCruncherDetectPolicy)

[시나리오 기반 QA 3-Phase 구조]

  Phase 1 — 정책 생성 기본 검증 (ADD 모달 1회차)
    - 초기값 스냅샷: 모달 열리자마자 터치 전 상태 확인
      · 행위기반 탐지등급 라디오 초기값 없음 감지 (HE-01: 휴먼에러 / known_bug)
    - 필수입력 검증: 이름 없음 → 확장자 없음 → 전체 입력 → 등록
    - 저장: [AUTO]_detect_p1 정책 생성

  Phase 2 — UI 요소 동작 검증 (ADD 모달 2회차)
    - radio_group × 1: 행위기반 탐지등급 (4개 옵션 클릭)
    - toggle_checkbox × 6: 각 토글 ON/OFF + 종속 필드 활성/비활성
    - plain_checkbox  × 4: 적용 요일 등 독립 체크박스 클릭 동작
    - text_input      × 1: 정책 이름 (maxlength=20, required)
    - tag_input       × 1: 보호할 확장자 (ADD 모달 접근 가능)
    - tag_input × 3 (예외처리 탭): ADD 모달 탭 차단 → 스킵 (HE-05)
    - 저장: [AUTO]_detect_p2 정책 생성

  Phase 3 — 수정 시나리오 검증 (EDIT 모달)
    - [AUTO]_detect_p2 정책 수정 모달 열기
    - UI 요소 재검증 (EDIT 모달 동작 차이 확인)
    - 예외처리 탭: EDIT 모달에서는 접근 가능 → tag_input 동작 검증
    - 필수입력 수정 검증: 이름 비움 → 저장 시도
    - 정리: [AUTO] 정책 전체 삭제

실행:
  pytest tests/test_ransom_detect_policy_scan.py -v -s
  pytest tests/ -m ui_scan -v -s
"""

import pytest
from core.ui_scanner import UIScanner
from core.models import PageScanReport
from pages.ransom_detect_policy_page import RansomDetectPolicyPage

_PHASE_LABEL = {
    1: "Phase 1 (초기값+필수입력)",
    2: "Phase 2 (UI 동작)",
    3: "Phase 3 (수정)",
}

_STATUS_ICON = {
    "pass":      "✅",
    "fail":      "❌",
    "known_bug": "⚠️",
    "skip":      "⏭",
    "error":     "💥",
}

_PATTERN_FALLBACK = {
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


def _print_phase_report(report: PageScanReport, phase: int) -> None:
    if report is None:
        print(f"\n[{_PHASE_LABEL[phase]}] 결과 없음")
        return

    print(f"\n{'═' * 60}")
    print(f"  {_PHASE_LABEL[phase]}")
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
        """ScanResult에서 필드 id 추출 (required_submit missing_field 매칭용)."""
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

    # 현재 Phase에 실제 필드 결과가 있는지 확인 (text_input, tag_input)
    field_ids_in_report = set()
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
            mf    = r.extra.get("missing_field", "")
            mfl   = r.extra.get("missing_field_label", "")
            if mf and mfl and mf not in field_ids_in_report:
                req_icon = _STATUS_ICON.get(r.status, "?")
                print(f"  {req_icon} [{mfl}] 미입력 경고: {r.detail}")
                shown_req.add(id(r))
                continue

        icon = _STATUS_ICON.get(r.status, "?")
        print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")

        # toggle_checkbox 종속 필드 트리
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

        # 필수 입력 경고 — 해당 필드 바로 아래 (Phase 2/3: 필드 결과 있을 때)
        fid = _field_id(r)
        if fid and fid in req_map:
            for req_r in req_map[fid]:
                req_icon = _STATUS_ICON.get(req_r.status, "?")
                print(f"       └ {req_icon} [required] 미입력 경고: {req_r.detail}")
                shown_req.add(id(req_r))


@pytest.mark.ui_scan
class TestRansomDetectPolicyScan:

    def test_detect_scenario_qa(self, logged_in_page, settings, request):
        """
        탐지정책 시나리오 기반 QA — Phase 1, 2, 3 순서 실행.

        Phase 1: 초기값 스냅샷 + 필수입력 → 저장 ([AUTO]_detect_p1)
        Phase 2: UI 요소 동작 전체 → 저장 ([AUTO]_detect_p2)
        Phase 3: EDIT 모달 수정 시나리오 → 정리
        """
        page_obj = RansomDetectPolicyPage(logged_in_page, settings)
        page_obj.navigate_to()
        page_obj.delete_all_auto_policies()

        scanner = UIScanner(logged_in_page, config_dir="config")

        # ─────────────────────────────────────────────────────────────
        # Phase 1: 초기값 스냅샷 + 필수입력 검증
        # ─────────────────────────────────────────────────────────────
        p1_name = "[AUTO]_detect_p1"

        def close_phase1():
            """Phase 1 완료 후 정책 저장.
            required_submit step 3에서 이름+확장자 채워진 상태 → 이름만 덮어쓰고 등록.
            """
            page_obj.fill(page_obj.SEL_POLICY_NAME, p1_name)
            # 확장자 없으면 추가 (required_submit 이후 상태 보장용)
            if page_obj.page.locator("i.extentionDeleteBtn").count() == 0:
                page_obj.fill(page_obj.SEL_EXTENSION_INPUT, "txt")
                page_obj.click(page_obj.SEL_EXTENSION_ADD_BTN)
                page_obj.page.wait_for_timeout(300)
            page_obj.click(page_obj.SEL_REGISTER_BTN)
            page_obj.page.locator(page_obj.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=page_obj._TIMEOUT_MODAL
            )
            page_obj.click_attached(page_obj.SEL_CONFIRM_BTN)
            page_obj.wait_for_modal_closed()
            page_obj.wait_for(page_obj.SEL_ADD_BTN)

        report1 = scanner.scan(
            "ransom_detect_policy", phase=1,
            modal_open_fn=page_obj.open_add_modal,
            modal_close_fn=close_phase1,
        )
        _print_phase_report(report1, 1)

        # ─────────────────────────────────────────────────────────────
        # Phase 2: UI 요소 동작 검증
        # ─────────────────────────────────────────────────────────────
        p2_name = "[AUTO]_detect_p2"

        def close_phase2():
            """Phase 2 완료 후 정책 저장."""
            page_obj.fill(page_obj.SEL_POLICY_NAME, p2_name)
            if page_obj.page.locator("i.extentionDeleteBtn").count() == 0:
                page_obj.fill(page_obj.SEL_EXTENSION_INPUT, "txt")
                page_obj.click(page_obj.SEL_EXTENSION_ADD_BTN)
                page_obj.page.wait_for_timeout(300)
            page_obj.click(page_obj.SEL_REGISTER_BTN)
            page_obj.page.locator(page_obj.SEL_CONFIRM_MODAL_OPENED).wait_for(
                state="attached", timeout=page_obj._TIMEOUT_MODAL
            )
            page_obj.click_attached(page_obj.SEL_CONFIRM_BTN)
            page_obj.wait_for_modal_closed()
            page_obj.wait_for(page_obj.SEL_ADD_BTN)

        report2 = scanner.scan(
            "ransom_detect_policy", phase=2,
            modal_open_fn=page_obj.open_add_modal,
            modal_close_fn=close_phase2,
            context_extra={
                "existing_name": p1_name,   # 중복 이름 등록 시도용 (Step 0_dup)
            },
        )
        _print_phase_report(report2, 2)

        # ─────────────────────────────────────────────────────────────
        # Phase 3: 수정 시나리오 검증
        # ─────────────────────────────────────────────────────────────
        def close_phase3():
            """EDIT 모달 닫기 — 모달이 이미 닫혔을 수 있으므로 조건부 처리."""
            try:
                if page_obj.page.locator(page_obj.SEL_ADD_MODAL).count() > 0:
                    page_obj.close_modal()
                else:
                    page_obj.wait_for(page_obj.SEL_ADD_BTN)
            except Exception:
                pass

        report3: PageScanReport | None = None
        try:
            report3 = scanner.scan(
                "ransom_detect_policy", phase=3,
                modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
                modal_close_fn=close_phase3,
                context_extra={
                    # EDIT 모달 로드값 확인: Phase 2에서 저장한 값과 비교
                    "verify_values": {
                        "input#rcDetectPolicyName": p2_name,
                    },
                },
            )
            _print_phase_report(report3, 3)
        finally:
            try:
                page_obj.navigate_to()
                page_obj.delete_all_auto_policies()
            except Exception:
                pass

        # ─────────────────────────────────────────────────────────────
        # 결합 리포트 & 검증
        # ─────────────────────────────────────────────────────────────
        reports = [r for r in (report1, report2, report3) if r is not None]
        combined = PageScanReport.merge(*reports)

        request.node._scan_report = combined

        print(f"\n{'═' * 60}")
        print(f"  전체 결과: {combined.summary()}")
        print(f"{'═' * 60}")

        # ── known_bug 추적 섹션 (무시하지 않고 항상 출력) ────────────────
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

        assert not combined.failed, (
            f"UI 패턴 검사 실패 {len(combined.failed)}건:\n"
            + "\n".join(
                f"  [Phase {r.phase}][{r.pattern}] {r.label}: {r.detail}"
                for r in combined.failed
            )
        )
