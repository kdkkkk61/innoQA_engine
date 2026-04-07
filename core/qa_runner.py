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

import json
import yaml
from datetime import datetime
from pathlib  import Path

from core.ui_scanner        import UIScanner
from core.models            import PageScanReport, ScanResult
from core.reporter          import print_phase_report, print_combined_report
from pages.registry         import PAGE_REGISTRY
from validators.overflow    import scan_overflow_tests
from validators.list_ui     import scan_list_ui


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3 두 케이스 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _apply_profile_actions(page, actions: list) -> None:
    """test_profiles YAML의 actions 목록을 순서대로 실행."""
    for action in actions:
        atype = action["type"]
        if atype == "checkbox_set":
            sel  = action["selector"]
            want = action["value"]
            el   = page.locator(sel).first
            if el.count() == 0:
                continue
            current = el.is_checked()
            if want != current:
                el.evaluate("el => el.click()")
                page.wait_for_timeout(200)
        elif atype == "radio_set":
            sel = action["selector"]
            page.locator(sel).first.evaluate("el => el.click()")
            page.wait_for_timeout(200)
        elif atype == "text_set":
            sel = action["selector"]
            val = str(action["value"])
            el  = page.locator(sel).first
            if el.count() == 0:
                continue
            el.evaluate(
                "(el, v) => { el.value = v;"
                " el.dispatchEvent(new Event('input',{bubbles:true}));"
                " el.dispatchEvent(new Event('blur',{bubbles:true})); }",
                val,
            )
            page.wait_for_timeout(200)
        elif atype == "tag_add":
            inp_sel = action["input"]
            btn_sel = action["btn"]
            val     = action["value"]
            page.locator(inp_sel).first.fill(val)
            page.wait_for_timeout(100)
            page.locator(btn_sel).first.evaluate("el => el.click()")
            page.wait_for_timeout(300)


def _verify_profile_case(
    page,
    verify_dict: dict,
    case_label: str,
    phase: int,
    order_base: int,
) -> list:
    """modify 모달 오픈 후 verify_dict 항목별로 값 검증. ScanResult 리스트 반환."""
    results = []
    for i, (selector, expected) in enumerate(verify_dict.items()):
        order = order_base + i
        try:
            el = page.locator(selector).first
            if el.count() == 0:
                results.append(ScanResult(
                    pattern="profile_verify", selector=selector,
                    label=f"[{case_label}] {selector}",
                    status="skip", detail="요소 없음",
                    order=order, phase=phase,
                ))
                continue
            if expected == "checked":
                ok     = el.is_checked()
                status = "pass" if ok else "fail"
                detail = "checked ✓" if ok else "unchecked (기댓값: checked)"
            elif expected == "unchecked":
                ok     = not el.is_checked()
                status = "pass" if ok else "fail"
                detail = "unchecked ✓" if ok else "checked (기댓값: unchecked)"
            else:
                actual = el.input_value()
                status = "pass" if actual == str(expected) else "fail"
                detail = (f"'{actual}' ✓" if status == "pass"
                          else f"기댓값 '{expected}', 실제 '{actual}'")
            results.append(ScanResult(
                pattern="profile_verify", selector=selector,
                label=f"[{case_label}] {selector}",
                status=status, detail=detail,
                order=order, phase=phase,
            ))
        except Exception as e:
            results.append(ScanResult(
                pattern="profile_verify", selector=selector,
                label=f"[{case_label}] {selector}",
                status="error", detail=str(e),
                order=order, phase=phase,
            ))
    return results


def _save_snapshot(page_id: str, case_name: str, verify_dict: dict) -> None:
    """검증 기댓값을 reports/policy_snapshots/에 JSON으로 저장 (에이전트 비교용)."""
    snap_dir = Path("reports") / "policy_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap = {
        "page_id":   page_id,
        "case":      case_name,
        "timestamp": ts,
        "values":    verify_dict,
    }
    path = snap_dir / f"{page_id}_{case_name}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    print(f"  💾 스냅샷 저장: {path}")


def run_phase3_cases(
    playwright_page,
    settings: dict,
    page_id: str,
    page_obj,
) -> PageScanReport | None:
    """
    config/test_profiles/{page_id}.yaml 을 읽어 단일 정책 전환 검증.

    흐름:
      1. create 액션으로 전체 ON 정책 생성
      2. verify_created: 수정 모달에서 전체 ON 확인 + 스냅샷
      3. modify_to_off 액션 적용 후 저장
      4. verify_modified: 수정 모달에서 전체 OFF 확인 + 스냅샷

    profile 파일 없으면 None 반환 (건너뜀).
    """
    config_dir   = settings.get("config_dir", "config")
    profile_path = Path(config_dir) / "test_profiles" / f"{page_id}.yaml"
    if not profile_path.exists():
        return None

    with open(profile_path, encoding="utf-8") as f:
        profile = yaml.safe_load(f) or {}

    report      = PageScanReport(page_id=page_id)
    create_cfg  = profile.get("create", {})
    policy_name = create_cfg.get("policy_name", f"[AUTO]_{page_id[:6]}_p4")

    # ── 1. 전체 ON 정책 생성 ──────────────────────────────────────
    try:
        page_obj.open_add_modal()
        _apply_profile_actions(playwright_page, create_cfg.get("actions", []))
        page_obj.save_policy(policy_name)
        report.results.append(ScanResult(
            pattern="profile_case", selector="",
            label="전체 ON 정책 생성",
            status="pass", detail=f"'{policy_name}' 생성 성공",
            order=1000, phase=4,
        ))
    except Exception as e:
        report.results.append(ScanResult(
            pattern="profile_case", selector="",
            label="전체 ON 정책 생성",
            status="error", detail=str(e),
            order=1000, phase=4,
        ))
        return report

    # ── 2. 생성 직후 검증: 전체 ON 확인 ──────────────────────────
    verify_created = profile.get("verify_created", {})
    if verify_created:
        try:
            page_obj.open_modify_modal(policy_name)
            playwright_page.wait_for_timeout(500)
            report.results.extend(_verify_profile_case(
                playwright_page, verify_created,
                "전체 ON", phase=4, order_base=1010,
            ))
            _save_snapshot(page_id, "created_all_on", verify_created)
        except Exception as e:
            report.results.append(ScanResult(
                pattern="profile_verify", selector="",
                label="전체 ON 검증 오류",
                status="error", detail=str(e),
                order=1010, phase=4,
            ))

    # ── 3. 수정: 전체 OFF로 전환 ──────────────────────────────────
    modify_cfg = profile.get("modify_to_off", {})
    if modify_cfg:
        try:
            # 모달이 이미 열려 있으면 그 상태에서 적용, 아니면 재오픈
            _apply_profile_actions(playwright_page, modify_cfg.get("actions", []))
            save_fn = getattr(page_obj, "save_edit_modal", page_obj.close_edit_modal)
            save_fn()
            playwright_page.wait_for_timeout(500)
            report.results.append(ScanResult(
                pattern="profile_case", selector="",
                label="전체 OFF로 수정 저장",
                status="pass", detail="전체 OFF 액션 적용 후 저장 성공",
                order=2000, phase=4,
            ))
        except Exception as e:
            report.results.append(ScanResult(
                pattern="profile_case", selector="",
                label="전체 OFF로 수정 저장",
                status="error", detail=str(e),
                order=2000, phase=4,
            ))
            try:
                page_obj.close_edit_modal()
            except Exception:
                pass

    # ── 4. 수정 후 검증: 전체 OFF 확인 ───────────────────────────
    verify_modified = profile.get("verify_modified", {})
    if verify_modified:
        try:
            page_obj.open_modify_modal(policy_name)
            playwright_page.wait_for_timeout(500)
            report.results.extend(_verify_profile_case(
                playwright_page, verify_modified,
                "전체 OFF", phase=4, order_base=2010,
            ))
            _save_snapshot(page_id, "modified_all_off", verify_modified)
            page_obj.close_edit_modal()
        except Exception as e:
            report.results.append(ScanResult(
                pattern="profile_verify", selector="",
                label="전체 OFF 검증 오류",
                status="error", detail=str(e),
                order=2010, phase=4,
            ))

    return report if report.results else None


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
    # 시나리오 1: UI 구조 (탭 · 테이블 헤더 · 검색창)
    # list_ui YAML 섹션이 있으면 실행, 없으면 스킵 출력
    # ─────────────────────────────────────────────────────────────
    hints_path = Path(config_dir) / "scan_hints" / f"{page_id}.yaml"
    try:
        with open(hints_path, encoding="utf-8") as _f:
            _hints = yaml.safe_load(_f) or {}
    except FileNotFoundError:
        _hints = {}

    report1: PageScanReport | None = None
    if _hints.get("list_ui"):
        try:
            report1 = PageScanReport(page_id=page_id)
            page_obj.navigate_to()
            scan_list_ui(playwright_page, _hints, report1)
            print_phase_report(report1, 1)
        except Exception as e:
            print(f"  💥 [{page_id}] 시나리오 1 실행 중 예외: {e}")
    else:
        print(f"\n  ⏭ 시나리오 1: UI 구조 — 해당 없음 (list_ui 섹션 없음)")

    # ─────────────────────────────────────────────────────────────
    # 시나리오 2: 입력 구조 (초기값 스냅샷 + 필수입력 검증)
    # ─────────────────────────────────────────────────────────────
    p1_saved = False

    def close_phase1():
        nonlocal p1_saved
        page_obj.save_policy(p1_name)
        p1_saved = True

    report2 = scanner.scan(
        page_id, phase=2,
        modal_open_fn=page_obj.open_add_modal,
        modal_close_fn=close_phase1,
    )
    _append_list_check(report2, page_obj, p1_name, phase=2, order=9990)
    print_phase_report(report2, 2)

    # ─────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 (UI 인터랙션 + 중복 처리)
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
        print(f"  ⏭ [{page_id}] 시나리오 3: existing_name 스킵 — 시나리오 2 저장 실패")

    report3 = scanner.scan(
        page_id, phase=3,
        modal_open_fn=page_obj.open_add_modal,
        modal_close_fn=close_phase2,
        context_extra=context2,
    )
    _append_list_check(report3, page_obj, p2_name, phase=3, order=9990)

    # 시나리오 3 연장: 오버플로 검증 (overflow_tests 섹션 있을 때)
    # 정상 추가(p2) 직후 → 오버플로 시도 → 시나리오 4(수정) 전 정리
    hints_path = Path(config_dir) / "scan_hints" / f"{page_id}.yaml"
    try:
        with open(hints_path, encoding="utf-8") as _f:
            _hints = yaml.safe_load(_f) or {}
    except FileNotFoundError:
        _hints = {}

    if _hints.get("overflow_tests"):
        try:
            page_obj.navigate_to()
            scan_overflow_tests(
                playwright_page, _hints, report3,
                open_modal_fn=page_obj.open_add_modal,
            )
        except Exception as e:
            print(f"  💥 [{page_id}] 시나리오 3 오버플로 실행 중 예외: {e}")

    print_phase_report(report3, 3)

    # ─────────────────────────────────────────────────────────────
    # 시나리오 4: 수정 시나리오 (저장값 로드 + 재확인)
    # ─────────────────────────────────────────────────────────────
    report4: PageScanReport | None = None

    if not p2_saved:
        print(f"  ⏭ 시나리오 4: 수정 시나리오 스킵 — 시나리오 3 저장 실패 (p2 정책 없음)")
    else:
        try:
            report4 = scanner.scan(
                page_id, phase=4,
                modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
                modal_close_fn=page_obj.close_edit_modal,
                context_extra={"verify_values": page_obj.get_verify_values(p2_name)},
            )
            _append_list_check(report4, page_obj, p2_name, phase=4, order=9990)
            print_phase_report(report4, 4)
        except Exception as e:
            print(f"  💥 [{page_id}] 시나리오 4 실행 중 예외: {e}")
        finally:
            try:
                page_obj.navigate_to()
                page_obj.delete_all_auto_policies()
            except Exception as e:
                print(
                    f"\n  ⚠️  [{page_id}] 정리 실패 — "
                    f"잔여 [AUTO] 정책이 남아있을 수 있습니다: {e}"
                )

    # ─────────────────────────────────────────────────────────────
    # 시나리오 5: 케이스 검증 (제품 설정 ON/OFF 프로파일)
    # ─────────────────────────────────────────────────────────────
    report5: PageScanReport | None = None
    try:
        report5 = run_phase3_cases(playwright_page, settings, page_id, page_obj)
        if report5:
            print_phase_report(report5, 5)
        else:
            print(f"\n  ⏭ 시나리오 5: 케이스 검증 — 해당 없음 (test_profiles/{page_id}.yaml 없음)")
    except Exception as e:
        print(f"  💥 [{page_id}] 시나리오 5 실행 중 예외: {e}")
    finally:
        try:
            page_obj.navigate_to()
            page_obj.delete_all_auto_policies()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────
    # 결합 리포트
    # ─────────────────────────────────────────────────────────────
    reports = [r for r in (report1, report2, report3, report4, report5) if r is not None]
    if not reports:
        raise RuntimeError(f"[{page_id}] 스캔 결과 없음 — 모든 시나리오 실패")

    combined = PageScanReport.merge(*reports)
    print_combined_report(combined)
    return combined
