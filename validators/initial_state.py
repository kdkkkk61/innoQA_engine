"""
validators/initial_state.py — Phase 1 전용: 모달 초기 상태 검증

반드시 모달이 열리자마자 (어떤 필드도 건드리기 전) 실행해야 한다.
Phase 2 이후에 실행하면 클릭/입력으로 오염된 상태를 검사하게 되어 의미 없음.

검증 항목:
  ① 이진 라디오 그룹 초기값 없음 (require_default: true)
      → 선택 없이 저장 시 암묵적 동작 발생하는 UX 결함 감지
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext

_ORDER_INITIAL = -1   # 항상 가장 먼저 출력


def scan_initial_state(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    Phase 1 전용: 모달 열리자마자 터치 전 초기 상태 검증.
    현재 검사 항목: require_default (이진 라디오 초기값 없음)
    """
    _check_radio_require_default(ctx, hints, report)


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

            if ctx.is_known_bug(rd_sel, rd_test):
                status = "known_bug"
                detail = (
                    f"알려진 UX 결함: 이진 선택 그룹 초기값 없음 ({opt_labels})"
                )
            else:
                status = "fail"
                detail = (
                    f"이진 선택 그룹({opt_labels}) 초기값 없음 "
                    f"→ 선택 없이 저장 시 암묵적 동작 발생 (휴먼에러)"
                )

            ctx.log.debug(f"[initial_state] {label!r} → {status}")
            report.results.append(ScanResult(
                pattern="initial_state",
                selector=rd_sel,
                label=f"{label} 초기값",
                status=status,
                detail=detail,
                order=order,
                phase=1,
            ))
