"""
validators/text_input.py — 텍스트 입력 검증

검증 항목:
  ① maxlength 속성 값 일치 확인
  ② maxlength 실제 동작 (초과 입력 차단)
  ③ 입력/삭제 자유도
  ④ required 마커 확인
  검증 후 필드 값 복원.
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext


def scan_text_inputs(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    for inp in hints.get("text_inputs", []):
        selector  = inp["selector"]
        label     = inp.get("label", selector)
        maxlength = inp.get("maxlength")
        required  = inp.get("required", False)
        order     = inp.get("order")

        ctx.log.debug(f"[text_input] 스캔 시작: {label!r} ({selector})")

        tab = inp.get("tab")
        if tab:
            ctx.activate_tab({"data_tab": tab})

        try:
            loc = ctx.page.locator(selector)
            if loc.count() == 0:
                report.results.append(ScanResult(
                    pattern="text_input", selector=selector, label=label,
                    status="skip", detail="요소를 찾을 수 없음", order=order,
                ))
                continue

            original_value = loc.input_value()
            failures: list[str] = []
            checks:   list[str] = ["존재 확인"]

            # ① maxlength 속성 확인
            if maxlength is not None:
                actual_ml = loc.get_attribute("maxlength")
                if actual_ml is None:
                    failures.append(f"maxlength 속성 없음 (기대: {maxlength})")
                elif int(actual_ml) != maxlength:
                    failures.append(
                        f"maxlength 불일치 (기대: {maxlength}, 실제: {actual_ml})"
                    )
                else:
                    # ② maxlength 실제 동작 테스트
                    test_str = "x" * (maxlength + 5)
                    ctx.log.debug(f"[text_input] {label!r} → fill({len(test_str)}자)")
                    loc.fill(test_str)
                    actual_len = len(loc.input_value())
                    if actual_len > maxlength:
                        failures.append(
                            f"maxlength {maxlength}자 실제 미적용 ({actual_len}자 입력됨)"
                        )
                    else:
                        checks.append(f"maxlength {maxlength}자 실제 동작 확인")
                    # ③ 삭제 자유도
                    loc.fill("")
                    if loc.input_value() != "":
                        failures.append("입력 후 삭제 불가")
                    else:
                        checks.append("입력/삭제 자유도 확인")
            else:
                loc.fill("scan_test")
                loc.fill("")
                if loc.input_value() != "":
                    failures.append("입력 후 삭제 불가")
                else:
                    checks.append("입력/삭제 자유도 확인")

            # 원래 값 복원
            if loc.input_value() != original_value:
                loc.fill(original_value)

            # ④ required 마커 확인
            if required:
                has_req_attr = loc.get_attribute("required") is not None
                inp_id       = selector.replace("input#", "", 1)
                label_sel    = f'label[for="{inp_id}"] .star'
                has_star     = ctx.page.locator(label_sel).count() > 0
                if not has_req_attr and not has_star:
                    failures.append(
                        "필수 필드 표시 없음 (required 속성 & .star 마커 모두 미확인)"
                    )
                else:
                    checks.append("required 마커 확인")

            status, detail = ctx.status_detail(failures, checks)
            ctx.log.debug(f"[text_input] {label!r} → {status}: {detail}")
            report.results.append(ScanResult(
                pattern="text_input", selector=selector, label=label,
                status=status, detail=detail, order=order,
            ))

        except Exception:
            ctx.append_error(report, "text_input", selector, label, order)
