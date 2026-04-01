"""
core/qa_runner.py — 3-Phase 범용 QA 스캔 오케스트레이터

page_id → PAGE_REGISTRY[page_id] → 3-Phase scan → PageScanReport 반환.
테스트 파일에서 직접 Phase 코드를 작성할 필요 없음.

새 페이지 추가 시:
  1. config/scan_hints/{page_id}.yaml
  2. pages/{page_id}_page.py (save_policy, close_edit_modal, get_verify_values 구현)
  3. pages/registry.py 에 1줄 추가
  → tests/test_scan_pages.py 에서 자동 실행

Phase 이름 생성 규칙:
  Page 클래스에 AUTO_NAME_PREFIX 상수가 있으면 사용.
  없으면 "[AUTO]_" + page_id 앞 6자 폴백.
  (maxlength 제약이 있는 페이지는 Page 클래스에서 반드시 AUTO_NAME_PREFIX 정의)
"""
from __future__ import annotations

import yaml
from pathlib import Path

from core.ui_scanner import UIScanner
from core.models     import PageScanReport, ScanResult
from core.reporter   import print_phase_report, print_combined_report
from pages.registry  import PAGE_REGISTRY


def run_scan(
    playwright_page,
    settings: dict,
    page_id: str,
) -> PageScanReport:
    """
    scan_mode에 따라 적절한 스캐너를 실행한다.

      scan_mode: modal_form (기본값) → run_3phase_scan()
      scan_mode: list_page           → run_list_page_scan()

    새 scan_mode 추가 시 이 함수에만 분기를 추가하면 된다.
    """
    config_dir = settings.get("config_dir", "config")
    hints_path = Path(config_dir) / "scan_hints" / f"{page_id}.yaml"
    try:
        with open(hints_path, encoding="utf-8") as f:
            hints = yaml.safe_load(f) or {}
    except FileNotFoundError:
        hints = {}

    scan_mode = hints.get("scan_mode", "modal_form")

    if scan_mode == "list_page":
        return run_list_page_scan(playwright_page, settings, page_id, hints)
    return run_3phase_scan(playwright_page, settings, page_id)


def _append_list_check(
    report: PageScanReport,
    page_obj,
    name: str,
    phase: int,
    order: int,
) -> None:
    """저장/닫기 후 해당 이름이 목록에 나타나는지 확인하고 결과를 report에 추가."""
    get_names = getattr(page_obj, "get_policy_names", None) or \
                getattr(page_obj, "get_item_names",   None)
    if get_names is None:
        return
    try:
        names = get_names()
        if name in names:
            report.results.append(ScanResult(
                pattern="list_confirm", selector="table tbody tr",
                label=f"목록 확인 — '{name}'",
                status="pass",
                detail=f"저장 후 목록에서 '{name}' 확인 ({len(names)}건 중)",
                order=order, phase=phase,
            ))
        else:
            report.results.append(ScanResult(
                pattern="list_confirm", selector="table tbody tr",
                label=f"목록 확인 — '{name}'",
                status="fail",
                detail=f"저장 후 목록에 '{name}' 없음 (목록: {names[:3]}...)",
                order=order, phase=phase,
            ))
    except Exception as e:
        report.results.append(ScanResult(
            pattern="list_confirm", selector="table tbody tr",
            label=f"목록 확인 — '{name}'",
            status="error", detail=str(e),
            order=order, phase=phase,
        ))


def run_list_page_scan(
    playwright_page,
    settings: dict,
    page_id: str,
    hints: dict | None = None,
) -> PageScanReport:
    """
    list_page 모드: 탭전환 / 검색 / 버튼 / 테이블 / 모달 / CRUD 순서로 스캔.
    실제 스캔 로직은 core/list_page_runner.py의 ListPageRunner에 위임.
    """
    from core.list_page_runner import ListPageRunner

    if hints is None:
        config_dir = settings.get("config_dir", "config")
        hints_path = Path(config_dir) / "scan_hints" / f"{page_id}.yaml"
        with open(hints_path, encoding="utf-8") as f:
            hints = yaml.safe_load(f) or {}

    if page_id not in PAGE_REGISTRY:
        raise ValueError(f"PAGE_REGISTRY에 등록되지 않은 page_id: {page_id!r}")

    PageClass = PAGE_REGISTRY[page_id]
    page_obj  = PageClass(playwright_page, settings)
    page_obj.navigate_to()
    page_obj.delete_all_auto_items()

    runner = ListPageRunner(playwright_page, page_obj, hints)
    report = runner.run()

    # 최종 정리
    try:
        page_obj.delete_all_auto_items()
    except Exception:
        pass

    return report


def run_3phase_scan(
    playwright_page,
    settings: dict,
    page_id: str,
) -> PageScanReport:
    """
    page_id에 해당하는 페이지를 3-Phase로 스캔하고 결과를 출력.

    반환: 전체 PageScanReport
    테스트 파일에서 assert not combined.failed 에 사용.
    """
    if page_id not in PAGE_REGISTRY:
        raise ValueError(f"PAGE_REGISTRY에 등록되지 않은 page_id: {page_id!r}")

    PageClass = PAGE_REGISTRY[page_id]
    page_obj  = PageClass(playwright_page, settings)
    page_obj.navigate_to()
    page_obj.delete_all_auto_policies()

    config_dir = settings.get("config_dir", "config")
    scanner    = UIScanner(playwright_page, config_dir=config_dir)

    # 이름 생성 — AUTO_NAME_PREFIX 우선, 없으면 page_id 6자 약어 폴백
    prefix  = getattr(page_obj, "AUTO_NAME_PREFIX", f"[AUTO]_{page_id[:6]}")
    p1_name = f"{prefix}_p1"
    p2_name = f"{prefix}_p2"

    # ─────────────────────────────────────────────────────────────
    # Phase 1: 초기값 스냅샷 + 필수입력 검증
    # ─────────────────────────────────────────────────────────────
    p1_saved = False

    def close_phase1():
        nonlocal p1_saved
        page_obj.save_policy(p1_name)
        p1_saved = True

    report1 = scanner.scan(
        page_id, phase=1,
        modal_open_fn=page_obj.open_add_modal,
        modal_close_fn=close_phase1,
    )
    # 목록 확인: 시나리오 1 저장 후 정책이 목록에 나타나는지
    _append_list_check(report1, page_obj, p1_name, phase=1, order=9990)
    print_phase_report(report1, 1)

    # ─────────────────────────────────────────────────────────────
    # Phase 2: UI 요소 동작 검증
    # ─────────────────────────────────────────────────────────────
    p2_saved = False

    def close_phase2():
        nonlocal p2_saved
        page_obj.save_policy(p2_name)
        p2_saved = True

    context2: dict = {}
    if p1_saved:
        context2["existing_name"] = p1_name
    else:
        print(f"  ⏭ [{page_id}] Phase 2: existing_name 스킵 — Phase 1 저장 실패")

    report2 = scanner.scan(
        page_id, phase=2,
        modal_open_fn=page_obj.open_add_modal,
        modal_close_fn=close_phase2,
        context_extra=context2,
    )
    # 목록 확인: 시나리오 2 저장 후 정책이 목록에 나타나는지
    _append_list_check(report2, page_obj, p2_name, phase=2, order=9990)
    print_phase_report(report2, 2)

    # ─────────────────────────────────────────────────────────────
    # Phase 3: 수정 시나리오 검증
    # ─────────────────────────────────────────────────────────────
    report3: PageScanReport | None = None

    if not p2_saved:
        print(f"  ⏭ [{page_id}] Phase 3 스킵 — Phase 2 저장 실패 (p2 정책 없음)")
    else:
        try:
            report3 = scanner.scan(
                page_id, phase=3,
                modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
                modal_close_fn=page_obj.close_edit_modal,
                context_extra={"verify_values": page_obj.get_verify_values(p2_name)},
            )
            # 목록 확인: 시나리오 3 닫기 후 정책이 목록에 남아있는지
            _append_list_check(report3, page_obj, p2_name, phase=3, order=9990)
            print_phase_report(report3, 3)
        except Exception as e:
            print(f"  💥 [{page_id}] Phase 3 실행 중 예외: {e}")
        finally:
            try:
                page_obj.navigate_to()
                page_obj.delete_all_auto_policies()
            except Exception as e:
                print(
                    f"\n  ⚠️  [{page_id}] 정리 실패 — "
                    f"잔여 [AUTO] 정책이 남아있을 수 있습니다: {e}"
                )

    if report3 is None and p2_saved:
        print(f"  ⏭ [{page_id}] Phase 3 실행되지 않음")

    # ─────────────────────────────────────────────────────────────
    # 결합 리포트
    # ─────────────────────────────────────────────────────────────
    reports = [r for r in (report1, report2, report3) if r is not None]
    if not reports:
        raise RuntimeError(f"[{page_id}] 스캔 결과 없음 — 모든 Phase 실패")

    combined = PageScanReport.merge(*reports)
    print_combined_report(combined)
    return combined
