"""
validators/initial_state.py — Phase 1/3 초기 상태 검증

Phase 1 전용 (ADD 모달 터치 전):
  ① 이진 라디오 그룹 초기값 없음 (require_default: true)
      → 선택 없이 저장 시 암묵적 동작 발생하는 UX 결함 감지
  ② toggle_checkboxes 초기값 확인 (YAML default vs 실제 DOM)
  ③ plain_checkboxes 초기값 확인
  ④ text_inputs 초기값 확인 (빈값 여부)

Phase 3 전용 (EDIT 모달 — scan_loaded_values):
  ⑤ context_extra["verify_values"] dict → 각 selector의 실제 DOM 값 비교
      키: CSS selector, 값: Phase 2에서 저장한 기대값
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext

_ORDER_INITIAL = -1   # 항상 가장 먼저 출력


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 진입점
# ─────────────────────────────────────────────────────────────────────────────

def scan_initial_state(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    Phase 1 전용: 모달 열리자마자 터치 전 초기 상태 검증.
    """
    _check_radio_require_default(ctx, hints, report)
    _check_toggle_defaults(ctx, hints, report)
    _check_checkbox_defaults(ctx, hints, report)
    _check_text_defaults(ctx, hints, report)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 진입점 — EDIT 모달 저장값 로드 확인
# ─────────────────────────────────────────────────────────────────────────────

def scan_loaded_values(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    Phase 3 전용: EDIT 모달에서 Phase 2에서 저장한 값이 올바르게 로드되었는지 검증.

    context_extra["verify_values"] = {selector: expected_value, ...}
    context_extra["verify_toggles"] = {selector: expected_bool, ...}  (optional)
    """
    verify_values  = ctx.extra.get("verify_values", {})
    verify_toggles = ctx.extra.get("verify_toggles", {})

    if not verify_values and not verify_toggles:
        return

    # ── 텍스트 필드 값 확인 ───────────────────────────────────────────────────
    # hints에서 label 역색인
    label_map: dict[str, str] = {}
    for inp in hints.get("text_inputs", []):
        label_map[inp["selector"]] = inp.get("label", inp["selector"])

    for sel, expected_val in verify_values.items():
        label = label_map.get(sel, sel)
        loc   = ctx.page.locator(sel)
        try:
            if loc.count() == 0:
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 로드값 확인",
                    status="skip", detail="요소 없음",
                    order=_ORDER_INITIAL, phase=3,
                ))
                continue
            actual = loc.input_value()
            if actual == expected_val:
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 로드값 확인",
                    status="pass", detail=f"저장값 정상 로드: '{actual}'",
                    order=_ORDER_INITIAL, phase=3,
                ))
            else:
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 로드값 확인",
                    status="fail",
                    detail=f"로드값 불일치 — 기대: '{expected_val}', 실제: '{actual}'",
                    order=_ORDER_INITIAL, phase=3,
                ))
        except Exception:
            ctx.append_error(report, "initial_state", sel, f"{label} 로드값 확인", _ORDER_INITIAL)

    # ── 토글 상태 확인 ────────────────────────────────────────────────────────
    for sel, expected_checked in verify_toggles.items():
        # hints에서 label 찾기
        label = sel
        for tgl in hints.get("toggle_checkboxes", []):
            if tgl["selector"] == sel:
                label = tgl.get("label", sel)
                break
        loc = ctx.page.locator(sel)
        try:
            if loc.count() == 0:
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 로드값 확인",
                    status="skip", detail="요소 없음",
                    order=_ORDER_INITIAL, phase=3,
                ))
                continue
            actual = loc.is_checked()
            if actual == bool(expected_checked):
                state = "ON" if actual else "OFF"
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 로드값 확인",
                    status="pass", detail=f"저장값 정상 로드: {state}",
                    order=_ORDER_INITIAL, phase=3,
                ))
            else:
                exp_s = "ON" if expected_checked else "OFF"
                act_s = "ON" if actual else "OFF"
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 로드값 확인",
                    status="fail",
                    detail=f"로드값 불일치 — 기대: {exp_s}, 실제: {act_s}",
                    order=_ORDER_INITIAL, phase=3,
                ))
        except Exception:
            ctx.append_error(report, "initial_state", sel, f"{label} 로드값 확인", _ORDER_INITIAL)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 내부 검증 함수들
# ─────────────────────────────────────────────────────────────────────────────

def _check_radio_require_default(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    require_default: true 로 설정된 라디오 그룹에서
    실제로 아무 옵션도 선택되지 않은 경우 UX 결함으로 리포트한다.
    """
    for group in hints.get("radio_groups", []):
        if not group.get("require_default"):
            continue
        if group.get("default") is not None:
            continue  # 기본값이 정의돼 있으면 radio_group validator가 처리

        name    = group["name"]
        label   = group.get("label", name)
        options = group.get("options", [])
        order   = group.get("order", _ORDER_INITIAL)

        ctx.log.debug(f"[initial_state] require_default 확인: {label!r}")

        try:
            any_checked = any(
                ctx.page.locator(o["selector"]).is_checked() for o in options
            )
        except Exception:
            ctx.append_error(
                report, "initial_state", f"[name={name}]", f"{label} 초기값", order
            )
            continue

        if any_checked:
            report.results.append(ScanResult(
                pattern="initial_state",
                selector=f"[name={name}]",
                label=f"{label} 초기값",
                status="pass",
                detail="초기값 선택됨 (DOM 확인)",
                order=order,
                phase=1,
            ))
        else:
            opt_labels = " / ".join(o.get("label", o["selector"]) for o in options)
            rd_sel  = f"[name={name}]"
            rd_test = "radio_require_default"

            known = ctx.is_known_bug(rd_sel, rd_test)
            status = "warn"
            detail = (
                f"이진 선택 그룹({opt_labels}) 초기값 없음 "
                f"→ 선택 없이 저장 시 암묵적 동작 발생 (휴먼에러)"
                + (" — 알려진 버그" if known else "")
            )

            ctx.log.debug(f"[initial_state] {label!r} → {status}")
            ss = None  # warn은 스크린샷 불필요
            report.results.append(ScanResult(
                pattern="initial_state",
                selector=rd_sel,
                label=f"{label} 초기값",
                status=status,
                detail=detail,
                order=order,
                phase=1,
                extra={"screenshot": ss} if ss else {},
            ))


def _check_toggle_defaults(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    toggle_checkboxes의 YAML default 값과 ADD 모달 최초 상태를 비교한다.
    default: null 인 토글은 스킵 (기대값 없음).
    """
    for toggle in hints.get("toggle_checkboxes", []):
        sel     = toggle["selector"]
        label   = toggle.get("label", sel)
        default = toggle.get("default")
        order   = toggle.get("order", _ORDER_INITIAL)

        if default is None:
            continue

        ctx.log.debug(f"[initial_state] toggle 초기값 확인: {label!r}")
        loc = ctx.page.locator(sel)
        if loc.count() == 0:
            continue

        try:
            actual   = loc.is_checked()
            expected = bool(default)
            exp_s    = "ON" if expected else "OFF"
            act_s    = "ON" if actual   else "OFF"

            if actual == expected:
                status = "pass"
                detail = f"초기값 {exp_s} 확인"
            else:
                status = "fail"
                detail = f"초기값 불일치 — 기대: {exp_s}, 실제: {act_s}"

            report.results.append(ScanResult(
                pattern="initial_state", selector=sel,
                label=f"{label} 초기값",
                status=status, detail=detail,
                order=order, phase=1,
            ))
        except Exception:
            ctx.append_error(report, "initial_state", sel, f"{label} 초기값", order)


def _check_checkbox_defaults(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    plain_checkboxes의 YAML default 값과 ADD 모달 최초 상태를 비교한다.
    """
    for cb in hints.get("plain_checkboxes", []):
        sel     = cb["selector"]
        label   = cb.get("label", sel)
        default = cb.get("default")
        order   = cb.get("order", _ORDER_INITIAL)

        if default is None:
            continue

        ctx.log.debug(f"[initial_state] checkbox 초기값 확인: {label!r}")
        loc = ctx.page.locator(sel)
        if loc.count() == 0:
            continue

        try:
            actual   = loc.is_checked()
            expected = bool(default)
            exp_s    = "ON" if expected else "OFF"
            act_s    = "ON" if actual   else "OFF"

            if actual == expected:
                status = "pass"
                detail = f"초기값 {exp_s} 확인"
            else:
                status = "fail"
                detail = f"초기값 불일치 — 기대: {exp_s}, 실제: {act_s}"

            report.results.append(ScanResult(
                pattern="initial_state", selector=sel,
                label=f"{label} 초기값",
                status=status, detail=detail,
                order=order, phase=1,
            ))
        except Exception:
            ctx.append_error(report, "initial_state", sel, f"{label} 초기값", order)


def _check_text_defaults(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    text_inputs의 ADD 모달 최초 진입 시 값이 빈값인지 확인한다.
    (기본값으로 채워진 필드가 있으면 fail — 잔류값 버그 감지)
    disabled 상태 필드는 스킵.
    """
    for inp in hints.get("text_inputs", []):
        sel   = inp["selector"]
        label = inp.get("label", sel)
        order = inp.get("order", _ORDER_INITIAL)

        ctx.log.debug(f"[initial_state] text 초기값 확인: {label!r}")
        loc = ctx.page.locator(sel)
        if loc.count() == 0:
            continue

        try:
            if loc.evaluate("el => el.disabled"):
                continue  # 비활성 종속 필드 — 초기값 체크 생략

            actual = loc.input_value()
            if actual == "":
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 초기값",
                    status="pass", detail="초기값 빈값 확인",
                    order=order, phase=1,
                ))
            else:
                report.results.append(ScanResult(
                    pattern="initial_state", selector=sel,
                    label=f"{label} 초기값",
                    status="fail",
                    detail=f"초기값이 빈값이 아님 — 실제: '{actual}'",
                    order=order, phase=1,
                ))
        except Exception:
            ctx.append_error(report, "initial_state", sel, f"{label} 초기값", order)
