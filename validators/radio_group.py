"""
validators/radio_group.py — 라디오 그룹 검증

검증 항목:
  ① 모든 옵션 DOM 존재 확인
  ② 기본값 확인 (YAML default 정의 시)
  ③ 전체 옵션 순환 클릭 테스트 → 원래 옵션으로 복원
  ④ dependent_fields 잠금/해제 검증 (YAML dependent_fields 정의 시)

NOTE: require_default (이진 라디오 초기값 없음) 감지는
      Phase 1 전용인 validators/initial_state.py 에서 처리한다.
      (클릭 루프 이전의 진짜 초기 상태를 확인해야 하기 때문)

dependent_fields YAML 구조:
  dependent_fields:
    - selector:      "input#someField"   # 검증 대상 셀렉터
      label:         "필드 이름"          # 표시용 레이블 (선택)
      active_option: "input#radioOpt"    # 이 옵션 선택 시 enabled, 나머지 선택 시 disabled
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext


def scan_radio_groups(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    for group in hints.get("radio_groups", []):
        name          = group["name"]
        label         = group.get("label", name)
        options       = group.get("options", [])
        order         = group.get("order")
        default_value = group.get("default")
        dep_fields    = group.get("dependent_fields", [])
        # require_default 체크는 validators/initial_state.py (Phase 1)에서 처리

        ctx.log.debug(f"[radio_group] 스캔 시작: {label!r} (name={name})")
        try:
            # ① 모든 옵션 존재 확인
            missing = [
                opt["selector"]
                for opt in options
                if ctx.page.locator(opt["selector"]).count() == 0
            ]
            if missing:
                report.results.append(ScanResult(
                    pattern="radio_group", selector=f"[name={name}]", label=label,
                    status="fail", detail=f"라디오 옵션 누락: {missing}", order=order,
                ))
                continue

            failures: list[str] = []
            checks:   list[str] = [f"옵션 {len(options)}개 모두 존재"]

            # ② 기본값 확인 (default 값이 명시된 경우만)
            if default_value is not None:
                default_opt = next(
                    (o for o in options if o.get("value") == default_value), None
                )
                if default_opt is None:
                    failures.append(f"YAML default '{default_value}' 에 해당하는 옵션 없음")
                elif not ctx.page.locator(default_opt["selector"]).is_checked():
                    failures.append(f"기본값 불일치 (기대: '{default_value}')")
                else:
                    checks.append(f"기본값 '{default_value}' 확인")

            # ③ 전체 옵션 순환 클릭 테스트 (+ ④ dep_fields 인라인 수집)
            initial_opt = next(
                (o for o in options if ctx.page.locator(o["selector"]).is_checked()),
                None,
            )
            ctx.log.debug(
                f"[radio_group] {label!r} → initial={initial_opt and initial_opt.get('value')!r}"
            )

            failed_opts:  list[str] = []
            dep_failures: list[str] = []
            dep_checks:   list[str] = []

            for opt in options:
                opt_val = opt.get("value", opt["selector"])
                opt_loc = ctx.page.locator(opt["selector"])
                ctx.log.debug(f"[radio_group] {label!r} → 클릭: {opt_val!r}")
                opt_loc.evaluate("el => el.click()")
                ctx.page.wait_for_timeout(300)
                if not opt_loc.is_checked():
                    failed_opts.append(opt_val)

                # ④ 이 옵션 선택 후 dependent_fields 잠금/해제 상태 확인
                if dep_fields:
                    _check_dep_fields_for_option(
                        ctx, opt, dep_fields, dep_failures, dep_checks
                    )

            if failed_opts:
                failures.append(f"클릭 후 선택 실패 옵션: {', '.join(failed_opts)}")
            else:
                checks.append(f"전체 {len(options)}개 옵션 클릭 선택 확인")

            # 원래 옵션으로 복원
            if initial_opt:
                ctx.log.debug(
                    f"[radio_group] {label!r} → 복원: {initial_opt.get('value')!r}"
                )
                ctx.page.locator(initial_opt["selector"]).evaluate("el => el.click()")
                ctx.page.wait_for_timeout(200)

            # ③ 결과
            status, detail = ctx.status_detail(failures, checks)
            ctx.log.debug(f"[radio_group] {label!r} → {status}: {detail}")
            report.results.append(ScanResult(
                pattern="radio_group", selector=f"[name={name}]", label=label,
                status=status, detail=detail, order=order,
            ))

            # ④ dependent_fields 결과 (별도 ScanResult)
            if dep_fields:
                dep_status, dep_detail = ctx.status_detail(dep_failures, dep_checks)
                ctx.log.debug(
                    f"[radio_group] {label!r} → dep_fields {dep_status}: {dep_detail}"
                )
                report.results.append(ScanResult(
                    pattern="radio_group",
                    selector=f"[name={name}]",
                    label=f"{label} → 종속필드",
                    status=dep_status, detail=dep_detail,
                    order=order,
                ))

        except Exception:
            ctx.append_error(report, "radio_group", f"[name={name}]", label, order)


def _check_dep_fields_for_option(
    ctx: ScanContext,
    opt: dict,
    dep_fields: list[dict],
    failures: list[str],
    checks: list[str],
) -> None:
    """
    현재 선택된 옵션(opt)에 대해 dep_fields 각 항목의 disabled 상태를 검증한다.

    active_option == opt["selector"]  →  expected: enabled  (disabled=false)
    active_option != opt["selector"]  →  expected: disabled (disabled=true)
    """
    opt_sel   = opt["selector"]
    opt_label = opt.get("label", opt_sel)

    for dep in dep_fields:
        dep_sel   = dep["selector"]
        dep_label = dep.get("label", dep_sel)
        active    = dep.get("active_option", "")

        expected_enabled = (active == opt_sel)

        loc = ctx.page.locator(dep_sel)
        if loc.count() == 0:
            failures.append(f"[{opt_label}] {dep_label}: 셀렉터 없음 ({dep_sel})")
            continue

        try:
            actual_disabled = loc.evaluate("el => el.disabled")
        except Exception:
            failures.append(f"[{opt_label}] {dep_label}: disabled 확인 실패")
            continue

        actual_enabled = not actual_disabled
        if actual_enabled != expected_enabled:
            exp_str = "활성" if expected_enabled else "비활성"
            act_str = "활성" if actual_enabled else "비활성"
            failures.append(
                f"[{opt_label}] {dep_label}: 기대={exp_str}, 실제={act_str}"
            )
        else:
            state = "활성" if expected_enabled else "비활성"
            checks.append(f"[{opt_label}] {dep_label} → {state} ✓")
