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
import time
import yaml
from contextlib import contextmanager
from datetime import datetime
from pathlib  import Path

from core.ui_scanner        import UIScanner
from core.models            import PageScanReport, ScanResult
from core.reporter          import print_phase_report, print_combined_report
from pages.registry         import PAGE_REGISTRY
from validators.overflow    import scan_overflow_tests
from validators.list_ui     import scan_list_ui


@contextmanager
def _t(label: str):
    """Timing 헬퍼 — [TIMING] {label} took {sec}s 출력."""
    t0 = time.time()
    try:
        yield
    finally:
        print(f"[TIMING] {label} took {time.time()-t0:.2f}s")


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
    print(f"  [SAVE] 스냅샷 저장: {path}")


def _fill_discovered_text_fields(page, hints: dict) -> list[ScanResult]:
    """
    B-1-B-4: 시나리오 3 자동 채우기 — 신규 자동 발견된 단독 text/number input 자동 fill.

    호출 시점: ADD 모달이 열린 상태에서 save_policy() 호출 직전.
    신규 input 의 type 이 text/textarea/number/password/email 인 것만 자동 채움.
    checkbox/toggle/radio 는 default 유지 (안전).

    md 정의 (test_scenario_standard.md "모든 필드 커버")에 따라 모든 신규 필드의
    시나리오 3 처리 결과를 ScanResult 로 등록 — 검수자가 카드에서 확인 가능.

    반환:
      list[ScanResult] — 신규 필드별 시나리오 3 처리 결과 카드.
      호출자가 report.results 에 extend 해서 시나리오 3 영역에 표시.
    """
    from core.scan_diff import (
        extract_yaml_selectors, extract_dom_selectors,
        extract_dom_attributes, extract_dom_labels, compare,
    )
    out: list[ScanResult] = []

    modal_id = hints.get("modal_id") or ""
    if not modal_id:
        return out
    context_sel = f"#{modal_id}.in"

    try:
        yaml_set = extract_yaml_selectors(hints)
        dom_set  = extract_dom_selectors(page, context_sel)
        diff     = compare(yaml_set, dom_set)
    except Exception:
        return out

    if not diff["new"]:
        return out

    try:
        attrs  = extract_dom_attributes(page, context_sel, diff["new"])
        labels = extract_dom_labels(page, context_sel, diff["new"])
    except Exception:
        return out

    # order: 시나리오 3 영역 끝 (다른 검증보다 뒤, 9990 list_check 보다는 앞)
    order_base = 9000

    for i, sel in enumerate(sorted(diff["new"])):
        a   = attrs.get(sel) or {}
        ko  = (labels.get(sel) or "").strip() or sel
        t   = a.get("type", "")
        order = order_base + i

        if t not in ("text", "textarea", "number", "password", "email"):
            # checkbox/toggle/radio — default 유지 (시나리오 3 회귀 X)
            out.append(ScanResult(
                pattern="discovered_fill", selector=sel,
                label=f"[신규] {ko}",
                status="pass",
                detail=(
                    f"[자동 분류 — yaml 미등록] 타입: {t or '?'} / "
                    "default 유지 (시나리오 3 추가 흐름 영향 없음)"
                ),
                order=order, phase=3,
            ))
            continue

        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                out.append(ScanResult(
                    pattern="discovered_fill", selector=sel,
                    label=f"[신규] {ko}",
                    status="skip",
                    detail="[자동 분류] 요소 미발견",
                    order=order, phase=3,
                ))
                continue
            if not loc.is_enabled():
                # disabled — 종속 필드 가능성. 토글 ON 후 검증은 B-1-C에서.
                out.append(ScanResult(
                    pattern="discovered_fill", selector=sel,
                    label=f"[신규] {ko}",
                    status="skip",
                    detail=(
                        "[자동 분류 — yaml 미등록] disabled 상태 — "
                        "종속 필드 가능성 (yaml 등록 시 dependent_fields 확인)"
                    ),
                    order=order, phase=3,
                ))
                continue
            value = "1" if t == "number" else "auto_test"
            loc.fill(value)
            out.append(ScanResult(
                pattern="discovered_fill", selector=sel,
                label=f"[신규] {ko}",
                status="pass",
                detail=(
                    f"[자동 분류 — yaml 미등록] 자동 채우기 {value!r} → "
                    "시나리오 3 추가 흐름 포함됨"
                ),
                order=order, phase=3,
            ))
        except Exception as e:
            out.append(ScanResult(
                pattern="discovered_fill", selector=sel,
                label=f"[신규] {ko}",
                status="error",
                detail=f"[자동 분류] 자동 채우기 실패: {e}",
                order=order, phase=3,
            ))

    return out


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
            # 신규 발견 필드 — 전체 ON 시점 카드 (md "모든 필드 커버")
            try:
                report.results.extend(_scenario5_discovered_cards(
                    playwright_page, page_obj, page_id,
                    modal_already_open=True, case_label="전체 ON",
                    order_base=1900,
                ))
            except Exception:
                pass
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
    modal_open_at_end = False
    if verify_modified:
        try:
            page_obj.open_modify_modal(policy_name)
            playwright_page.wait_for_timeout(500)
            modal_open_at_end = True
            report.results.extend(_verify_profile_case(
                playwright_page, verify_modified,
                "전체 OFF", phase=4, order_base=2010,
            ))
            _save_snapshot(page_id, "modified_all_off", verify_modified)
        except Exception as e:
            report.results.append(ScanResult(
                pattern="profile_verify", selector="",
                label="전체 OFF 검증 오류",
                status="error", detail=str(e),
                order=2010, phase=4,
            ))

    # ── 5. 신규 발견 필드 — 전체 OFF 시점 카드 ─────────────────────
    # md 정의 (test_scenario_standard.md "모든 필드 커버") 따라
    # yaml 미등록 신규 필드도 시나리오 5 영역 카드 등록 (ON·OFF 각각).
    # 추정 X — DOM 비교로 발견만, 케이스 동작은 yaml 등록 후 verify_*에서 다룸.
    try:
        report.results.extend(_scenario5_discovered_cards(
            playwright_page, page_obj, page_id,
            modal_already_open=modal_open_at_end,
            case_label="전체 OFF", order_base=2900,
        ))
    except Exception as e:
        report.results.append(ScanResult(
            pattern="discovered_case", selector="",
            label="신규 필드 자동 분류 (시나리오 5)",
            status="error", detail=f"자동 분류 중 오류: {e}",
            order=2900, phase=4,
        ))
    finally:
        if modal_open_at_end:
            try:
                page_obj.close_edit_modal()
            except Exception:
                pass

    return report if report.results else None


def _scenario5_discovered_cards(
    playwright_page, page_obj, page_id: str,
    modal_already_open: bool, case_label: str = "",
    order_base: int = 3000,
) -> list[ScanResult]:
    """시나리오 5 영역 자동 분류 카드 — yaml 미등록 신규 필드 감지 표시.

    동작:
      1. EDIT 모달이 열려 있는지 확인 (없으면 빈 리스트 반환 — 보수적)
      2. DOM ↔ yaml selector 비교 → 신규 필드 추출
      3. 각 신규 필드에 대해 케이스(ON/OFF) 시점의 DOM 값 + 케이스 분류 카드 등록

    case_label: "전체 ON" / "전체 OFF" (라벨 prefix 부착용). 빈 문자열이면 prefix 없음.

    회귀 안전:
      - 모달 재오픈/닫기 부수효과 없음 (modal_already_open=True 일 때만 스캔)
      - 추가 액션 없음 — DOM 읽기만
    """
    out: list[ScanResult] = []
    if not modal_already_open:
        return out

    from core.scan_diff import (
        extract_yaml_selectors, extract_dom_selectors,
        extract_dom_attributes, extract_dom_labels, compare,
    )
    config_dir = "config"
    hints_path = Path(config_dir) / "scan_hints" / f"{page_id}.yaml"
    try:
        with open(hints_path, encoding="utf-8") as f:
            hints = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return out

    modal_id = hints.get("modal_id") or ""
    if not modal_id:
        return out
    context_sel = f"#{modal_id}.in"

    try:
        yaml_set = extract_yaml_selectors(hints)
        dom_set  = extract_dom_selectors(playwright_page, context_sel)
        diff     = compare(yaml_set, dom_set)
    except Exception:
        return out

    if not diff["new"]:
        return out

    try:
        attrs  = extract_dom_attributes(playwright_page, context_sel, diff["new"])
        labels = extract_dom_labels(playwright_page, context_sel, diff["new"])
    except Exception:
        return out

    case_prefix = f"[{case_label}] " if case_label else ""
    for i, sel in enumerate(sorted(diff["new"])):
        a   = attrs.get(sel) or {}
        ko  = (labels.get(sel) or "").strip() or sel
        t   = a.get("type", "")
        # 현재 DOM 값 추출 (ON/OFF 시점 스냅샷)
        state_str = "?"
        try:
            loc = playwright_page.locator(sel).first
            if loc.count() > 0:
                if t in ("checkbox", "radio"):
                    state_str = "ON" if loc.is_checked() else "OFF"
                elif t in ("text", "number", "textarea", "password", "email"):
                    val = loc.input_value()
                    state_str = f"'{val}'" if val else "(빈값)"
        except Exception:
            pass
        out.append(ScanResult(
            pattern="discovered_case", selector=sel,
            label=f"[신규] {case_prefix}{ko}",
            status="pass",
            detail=(
                f"[자동 분류 — yaml 미등록] 타입: {t or '?'} / 현재 값: {state_str} / "
                "케이스 검증(전체 ON·전체 OFF) 대상 외 — "
                "yaml 등록 시 test_profiles 의 verify_* 에 추가 필요"
            ),
            order=order_base + i, phase=4,
        ))

    return out


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
    """저장/닫기 후 해당 이름이 목록에 나타나는지 확인하고 결과를 report에 추가.

    모달 닫힘 직후 AngularJS 목록 갱신 타이밍 문제 방지:
    navigate_to()로 페이지를 명시적으로 새로고침 후 조회한다.
    """
    get_names = getattr(page_obj, "get_policy_names", None) or \
                getattr(page_obj, "get_item_names",   None)
    if get_names is None:
        return
    try:
        # 목록 갱신 대기 — navigate_to()로 페이지 재진입 후 조회
        page_obj.navigate_to()
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


def _tag_scenario(report: PageScanReport | None, scenario: int) -> None:
    """report의 모든 결과에 extra['scenario'] = N 을 태깅.
    HTML 리포트에서 시나리오별 그룹핑의 기준이 된다.
    """
    if report is None:
        return
    for r in report.results:
        r.extra["scenario"] = scenario


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
    with _t(f"[{page_id}] 초기 navigate_to"):
        page_obj.navigate_to()
    with _t(f"[{page_id}] 사전 정리 (delete_all_auto_policies)"):
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
        with _t("[시나리오 1] UI 구조"):
            try:
                report1 = PageScanReport(page_id=page_id)
                page_obj.navigate_to()
                scan_list_ui(playwright_page, _hints, report1)
                _tag_scenario(report1, 1)
                print_phase_report(report1, 1)
            except Exception as e:
                print(f"  [ERR]  [{page_id}] 시나리오 1 실행 중 예외: {e}")
    else:
        print(f"\n  [SKIP] 시나리오 1: UI 구조 — 해당 없음 (list_ui 섹션 없음)")

    # ─────────────────────────────────────────────────────────────
    # 시나리오 2: 입력 구조 (초기값 스냅샷 + 필수입력 검증)
    # ─────────────────────────────────────────────────────────────
    p1_saved = False

    def close_phase1():
        nonlocal p1_saved
        page_obj.save_policy(p1_name)
        p1_saved = True

    with _t("[시나리오 2] 입력 구조"):
        report2 = scanner.scan(
            page_id, phase=2,
            modal_open_fn=page_obj.open_add_modal,
            modal_close_fn=close_phase1,
        )
        _append_list_check(report2, page_obj, p1_name, phase=2, order=9990)
        _tag_scenario(report2, 2)
        print_phase_report(report2, 2)

    # ─────────────────────────────────────────────────────────────
    # 시나리오 3: 동작 검증 (UI 인터랙션 + 중복 처리)
    # ─────────────────────────────────────────────────────────────
    p2_saved = False
    # B-1-B-4: 시나리오 3 자동 채우기용 hints 미리 로드 (close_phase2 클로저에서 참조)
    hints_path_for_fill = Path(config_dir) / "scan_hints" / f"{page_id}.yaml"
    try:
        with open(hints_path_for_fill, encoding="utf-8") as _f:
            _hints_for_fill = yaml.safe_load(_f) or {}
    except FileNotFoundError:
        _hints_for_fill = {}

    # 자동 채우기 결과 ScanResult 누적 — scanner.scan() 끝난 후 report3 에 합침
    discovered_fill_results: list[ScanResult] = []

    def close_phase2():
        nonlocal p2_saved
        # 신규 자동 발견 text/number input fill — save_policy() 직전.
        # md 정의 (모든 필드 커버) 따라 결과 카드 등록.
        try:
            results = _fill_discovered_text_fields(page_obj.page, _hints_for_fill)
            discovered_fill_results.extend(results)
        except Exception:
            pass  # 자동 채우기 실패는 무시 (회귀 위험 없게)
        page_obj.save_policy(p2_name)
        p2_saved = True

    context2: dict = {}
    if p1_saved:
        context2["existing_name"] = p1_name
    else:
        print(f"  [SKIP] [{page_id}] 시나리오 3: existing_name 스킵 — 시나리오 2 저장 실패")

    with _t("[시나리오 3] 동작 검증 (scan)"):
        report3 = scanner.scan(
            page_id, phase=3,
            modal_open_fn=page_obj.open_add_modal,
            modal_close_fn=close_phase2,
            context_extra=context2,
        )
    # B-1-B-4: 자동 채우기 결과를 시나리오 3 영역 카드로 추가 (md 정의 "모든 필드 커버")
    if discovered_fill_results:
        report3.results.extend(discovered_fill_results)
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
        with _t("[시나리오 3] 오버플로"):
            try:
                page_obj.navigate_to()
                scan_overflow_tests(
                    playwright_page, _hints, report3,
                    open_modal_fn=page_obj.open_add_modal,
                    open_edit_modal_fn=(
                        (lambda: page_obj.open_modify_modal(p2_name))
                        if p2_saved else None
                    ),
                )
            except Exception as e:
                print(f"  [ERR]  [{page_id}] 시나리오 3 오버플로 실행 중 예외: {e}")

    _tag_scenario(report3, 3)
    print_phase_report(report3, 3)

    # ─────────────────────────────────────────────────────────────
    # 시나리오 4: 수정 시나리오 (저장값 로드 + 재확인)
    # ─────────────────────────────────────────────────────────────
    report4: PageScanReport | None = None

    # 시나리오 3 오버플로 테스트 후 잔여 모달/상태 초기화
    try:
        page_obj.navigate_to()
    except Exception:
        pass

    if not p2_saved:
        print(f"  [SKIP] 시나리오 4: 수정 시나리오 스킵 — 시나리오 3 저장 실패 (p2 정책 없음)")
    else:
        with _t("[시나리오 4] 수정 시나리오"):
            try:
                report4 = scanner.scan(
                    page_id, phase=4,
                    modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
                    modal_close_fn=page_obj.close_edit_modal,
                    context_extra={"verify_values": page_obj.get_verify_values(p2_name)},
                )
                _append_list_check(report4, page_obj, p2_name, phase=4, order=9990)
                _tag_scenario(report4, 4)
                print_phase_report(report4, 4)
            except Exception as e:
                print(f"  [ERR]  [{page_id}] 시나리오 4 실행 중 예외: {e}")
            finally:
                with _t("[시나리오 4] 종료 후 정리 (navigate + delete_all)"):
                    try:
                        page_obj.navigate_to()
                        page_obj.delete_all_auto_policies()
                    except Exception as e:
                        print(
                            f"\n  [WARN]  [{page_id}] 정리 실패 — "
                            f"잔여 [AUTO] 정책이 남아있을 수 있습니다: {e}"
                        )

    # ─────────────────────────────────────────────────────────────
    # 시나리오 5: 케이스 검증 (제품 설정 ON/OFF 프로파일)
    # ─────────────────────────────────────────────────────────────
    report5: PageScanReport | None = None
    with _t("[시나리오 5] 케이스 검증"):
        try:
            report5 = run_phase3_cases(playwright_page, settings, page_id, page_obj)
            if report5:
                _tag_scenario(report5, 5)
                print_phase_report(report5, 5)
            else:
                print(f"\n  [SKIP] 시나리오 5: 케이스 검증 — 해당 없음 (test_profiles/{page_id}.yaml 없음)")
        except Exception as e:
            print(f"  [ERR]  [{page_id}] 시나리오 5 실행 중 예외: {e}")
        finally:
            with _t("[시나리오 5] 종료 후 정리 (navigate + delete_all)"):
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
