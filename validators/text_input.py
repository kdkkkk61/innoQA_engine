"""
validators/text_input.py — 텍스트 입력 검증

YAML 선언 항목 (필드별 검증 명세):
  maxlength   : DOM maxlength 속성 확인 + 실제 동작 테스트
  max_value   : JS 클램핑 상한 확인 (초과 입력 → 자동 보정 여부)
  min_value   : JS 클램핑 하한 확인 (미만 입력 → 자동 보정 여부)
  allow_empty : False = 빈값 불가 필드 (숫자 필드 등), 삭제 테스트 생략
  required    : 필수 마커(.star 또는 required 속성) 확인
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
        maxlength   = inp.get("maxlength")
        max_value   = inp.get("max_value")   # JS 클램핑 상한 (None=미검증)
        min_value   = inp.get("min_value")   # JS 클램핑 하한 (None=미검증)
        required    = inp.get("required", False)
        allow_empty = inp.get("allow_empty", True)
        order       = inp.get("order")

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

            # disabled 상태면 스킵 (종속 필드 — 활성화 조건 미충족)
            if loc.evaluate("el => el.disabled"):
                report.results.append(ScanResult(
                    pattern="text_input", selector=selector, label=label,
                    status="skip", detail="비활성화 상태 (종속 필드)", order=order,
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
                    # ③ 삭제 자유도 (allow_empty=False인 숫자 필드는 생략)
                    if allow_empty:
                        loc.fill("")
                        if loc.input_value() != "":
                            failures.append("입력 후 삭제 불가")
                        else:
                            checks.append("입력/삭제 자유도 확인")
                    else:
                        checks.append("빈값 불가 필드 (숫자 최솟값 강제 — 삭제 테스트 생략)")
            else:
                if allow_empty:
                    loc.fill("scan_test")
                    loc.fill("")
                    if loc.input_value() != "":
                        failures.append("입력 후 삭제 불가")
                    else:
                        checks.append("입력/삭제 자유도 확인")
                else:
                    # 숫자 필드: 값 입력/읽기만 확인
                    loc.fill("1")
                    if loc.input_value() == "":
                        failures.append("값 입력 불가")
                    else:
                        checks.append("값 입력 확인 (빈값 불가 필드)")

            # ⑤ JS 클램핑 상한(max_value) 확인
            if max_value is not None:
                over_str = str(max_value + 1)
                loc.fill(over_str)
                ctx.page.wait_for_timeout(150)
                actual = loc.input_value()
                if actual == over_str:
                    failures.append(
                        f"max_value({max_value}) 초과 입력 차단 안 됨 ({over_str} 그대로 유지)"
                    )
                elif actual == str(max_value):
                    checks.append(f"max_value {max_value} 클램핑 확인")
                else:
                    checks.append(f"max_value {max_value} 초과 시 자동 보정 ({actual})")

            # ⑥ JS 클램핑 하한(min_value) 확인
            if min_value is not None:
                under_str = str(min_value - 1)
                loc.fill(under_str)
                ctx.page.wait_for_timeout(150)
                actual = loc.input_value()
                if actual == under_str:
                    failures.append(
                        f"min_value({min_value}) 미만 입력 차단 안 됨 ({under_str} 그대로 유지)"
                    )
                else:
                    checks.append(f"min_value {min_value} 클램핑 확인 (입력값: {under_str} → {actual})")

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
