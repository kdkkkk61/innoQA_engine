"""
validators/toggle_checkbox.py — 토글 체크박스 검증

toggle_checkboxes 항목:
  ① 기본값 확인 (default_checked 전달 시)
  ② OFF 상태 → 종속 필드 disabled 확인
  ③ ON  상태 → enabled + 실제 입력 테스트
  ④ OFF 재확인 → ON→OFF 후 disabled 유지 여부
  ⑤ 원래 상태 복원
"""
from __future__ import annotations

import traceback
from typing import Optional

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext


def scan_toggle_checkboxes(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    toggle_checkboxes 항목을 검증한다.

    known_bug 항목도 실제로 검사한다 — 어떤 필드가 비정상인지 개별 확인이 목적.
    is_known_bug=True 이면 실패 종속 필드를 "fail" 대신 "known_bug" 로 마킹한다.

    dependent_fields 포맷 두 가지 모두 지원:
      구형(str 리스트): ["input#foo", "input#bar"]  ← 하위 호환
      신형(dict 리스트): [{selector, label, type, maxlength?, onpaste_blocked?}, ...]
    """
    for toggle in hints.get("toggle_checkboxes", []):
        selector        = toggle["selector"]
        label           = toggle.get("label", selector)
        raw_deps        = toggle.get("dependent_fields", [])
        is_kb           = ctx.is_known_bug(selector, "toggle_dependent_fields")
        default_checked = toggle.get("default")

        dep_fields: list[dict] = []
        for d in raw_deps:
            if isinstance(d, str):
                dep_fields.append({"selector": d, "label": d, "type": "field"})
            else:
                dep_fields.append(d)

        dep_labels = [d.get("label", d["selector"]) for d in dep_fields]
        dep_types  = [d.get("type", "field")         for d in dep_fields]

        try:
            result = _check_toggle_with_deps(
                ctx, selector, label, dep_fields,
                is_known_bug=is_kb,
                default_checked=default_checked,
            )
            result.order = toggle.get("order")
            result.extra.update({
                "dependent_labels": dep_labels,
                "dependent_types":  dep_types,
            })
            report.results.append(result)
        except Exception:
            ctx.append_error(report, "toggle_checkbox", selector, label, toggle.get("order"))


def _check_toggle_with_deps(
    ctx:             ScanContext,
    selector:        str,
    label:           str,
    dep_fields:      list[dict],
    is_known_bug:    bool = False,
    default_checked: Optional[bool] = None,
) -> ScanResult:
    """
    토글 + 종속 필드 동작 검증 (OFF→ON+입력→OFF재확인→복원).

    dep_fields 항목 구조:
        {selector, label, type, maxlength?(number/text), onpaste_blocked?(text)}
    """
    dep_selectors = [d["selector"] for d in dep_fields]
    toggle_loc    = ctx.page.locator(selector)

    if toggle_loc.count() == 0:
        return ScanResult(
            pattern="toggle_checkbox", selector=selector, label=label,
            status="skip", detail="요소를 찾을 수 없음",
            extra={"dependent_fields": dep_fields, "dependent_results": []},
        )

    if not dep_fields:
        return ScanResult(
            pattern="toggle_checkbox", selector=selector, label=label,
            status="pass", detail="토글 존재 확인 (종속 필드 없음)",
            extra={"dependent_fields": [], "dependent_results": []},
        )

    was_checked = toggle_loc.is_checked()

    # ① 기본값 확인
    default_fail: Optional[str] = None
    if default_checked is not None and was_checked != default_checked:
        expected     = "ON" if default_checked else "OFF"
        actual       = "ON" if was_checked    else "OFF"
        default_fail = f"기본값 불일치 (기대: {expected}, 실제: {actual})"

    # ② OFF 상태 → 종속 필드 disabled 확인
    off1_ok: dict[str, bool | None] = {}
    if was_checked:
        toggle_loc.evaluate("el => el.click()")
        ctx.page.wait_for_timeout(400)

    for sel in dep_selectors:
        loc = ctx.page.locator(sel)
        off1_ok[sel] = None if loc.count() == 0 else not loc.is_enabled()

    # ③ ON 상태 → enabled 확인 + 실제 입력 테스트
    on_ok:     dict[str, bool | None] = {}
    input_res: dict[str, dict]        = {}
    toggle_loc.evaluate("el => el.click()")
    ctx.page.wait_for_timeout(400)

    for dep in dep_fields:
        sel = dep["selector"]
        loc = ctx.page.locator(sel)
        if loc.count() == 0:
            on_ok[sel] = None
        else:
            on_ok[sel] = loc.is_enabled()
            if on_ok[sel]:
                input_res[sel] = _test_dep_input(ctx, dep)

    # ④ OFF 재확인
    off2_ok: dict[str, bool | None] = {}
    toggle_loc.evaluate("el => el.click()")
    ctx.page.wait_for_timeout(400)

    for sel in dep_selectors:
        loc = ctx.page.locator(sel)
        off2_ok[sel] = None if loc.count() == 0 else not loc.is_enabled()

    # ⑤ 원래 상태로 복원
    current = toggle_loc.is_checked()
    if current != was_checked:
        toggle_loc.evaluate("el => el.click()")
        ctx.page.wait_for_timeout(200)

    # ── 필드별 독립 결과 조립 ─────────────────────────────────────────────────
    dep_results: list[dict] = []
    real_fail_count  = 0
    known_bug_count  = 0

    for dep in dep_fields:
        sel = dep["selector"]
        o1  = off1_ok.get(sel)
        n   = on_ok.get(sel)
        o2  = off2_ok.get(sel)
        i_r = input_res.get(sel, {})

        if o1 is None and n is None and o2 is None:
            dep_results.append({"selector": sel, "status": "skip", "detail": "요소 없음"})
            continue

        issues: list[str] = []
        checks: list[str] = []

        if o1 is False:
            issues.append("OFF 시 활성화됨 (비정상)")
        elif o1 is True:
            checks.append("OFF→disabled")

        if n is False:
            issues.append("ON 시 비활성화됨 (비정상)")
        elif n is True:
            checks.append("ON→enabled")

        if o2 is False:
            issues.append("ON→OFF 전환 후 활성화 유지됨 (비정상)")
        elif o2 is True:
            checks.append("OFF재확인→disabled")

        if i_r:
            if i_r.get("status") == "fail":
                issues.append(f"입력 테스트 실패: {i_r.get('detail', '')}")
            elif i_r.get("status") == "pass":
                checks.append(i_r.get("detail", "입력 테스트 pass"))

        if issues:
            if is_known_bug:
                dep_status = "known_bug"
                known_bug_count += 1
            else:
                dep_status = "fail"
                real_fail_count += 1
            dep_results.append({
                "selector": sel,
                "status":   dep_status,
                "detail":   ", ".join(issues),
            })
        else:
            detail_str = " + ".join(checks) if checks else "ON/OFF 정상"
            dep_results.append({"selector": sel, "status": "pass", "detail": detail_str})

    # ── 부모 토글 요약 상태 결정 ──────────────────────────────────────────────
    if real_fail_count > 0 or default_fail:
        parent_status = "fail"
        msgs: list[str] = []
        if default_fail:
            msgs.append(default_fail)
        if real_fail_count > 0:
            msgs.append(f"종속 필드 {real_fail_count}개 검증 실패")
        parent_detail = "; ".join(msgs)
    elif known_bug_count > 0:
        parent_status = "known_bug"
        parent_detail = (
            f"알려진 버그 — 종속 필드 {known_bug_count}개 비정상"
            f" ({len(dep_fields) - known_bug_count}개 정상)"
        )
    else:
        parent_status = "pass"
        parts: list[str] = []
        if default_checked is not None:
            parts.append(f"기본값 {'ON' if default_checked else 'OFF'} 확인")
        if dep_fields:
            parts.append(f"종속 필드 {len(dep_fields)}개 ON/OFF+입력 정상")
        parent_detail = " + ".join(parts) if parts else "토글 존재 확인"

    return ScanResult(
        pattern="toggle_checkbox", selector=selector, label=label,
        status=parent_status, detail=parent_detail,
        extra={"dependent_fields": dep_fields, "dependent_results": dep_results},
    )


def _test_dep_input(ctx: ScanContext, dep_field: dict) -> dict:
    """
    ON 상태에서 종속 필드 타입별 실제 입력 테스트를 수행한다.

    dep_field 키: selector, type, maxlength?, onpaste_blocked?
    반환: {"status": "pass"|"fail"|"skip", "detail": str}
    """
    ftype   = dep_field.get("type", "field")
    sel     = dep_field["selector"]
    maxlen  = dep_field.get("maxlength")
    onpaste = dep_field.get("onpaste_blocked", False)

    if ftype == "plain_checkbox":
        return _test_plain_checkbox_dep(ctx, sel)
    elif ftype in ("number_input", "text_input"):
        return _test_text_like_dep(ctx, sel, maxlen, onpaste, ftype)
    else:
        return {"status": "skip", "detail": f"입력 테스트 미지원 타입: {ftype}"}


def _test_text_like_dep(
    ctx:             ScanContext,
    selector:        str,
    maxlength:       Optional[int],
    onpaste_blocked: bool,
    ftype:           str = "text_input",
) -> dict:
    """
    number_input / text_input 종속 필드 입력 테스트.

    maxlength 지정 시: 속성 확인 + truncation 동작
    maxlength 미지정 시: 10자 입력으로 제한 자동 감지
    onpaste_blocked=True 시: onpaste="return false" 속성 확인
    공통: 입력/삭제 자유도 확인
    """
    loc = ctx.page.locator(selector)
    if loc.count() == 0:
        return {"status": "skip", "detail": "요소 없음"}

    checks:   list[str] = []
    failures: list[str] = []

    if maxlength is not None:
        actual_attr = loc.get_attribute("maxlength")
        if actual_attr is None:
            failures.append(f"maxlength 속성 없음 (기대: {maxlength})")
        elif int(actual_attr) != maxlength:
            failures.append(
                f"maxlength 불일치 (기대: {maxlength}, 실제: {actual_attr})"
            )
        else:
            loc.fill("1" * (maxlength + 5))
            actual_len = len(loc.input_value())
            if actual_len > maxlength:
                failures.append(
                    f"maxlength {maxlength}자 미적용 ({actual_len}자 입력됨)"
                )
            else:
                checks.append(f"maxlength {maxlength}자 동작 확인")
    else:
        loc.fill("1234567890")
        actual_len = len(loc.input_value())
        if actual_len < 10:
            checks.append(f"maxlength {actual_len}자 감지 (YAML 미명시)")
        else:
            checks.append("maxlength 없음 (10자 이상 가능)")

    if onpaste_blocked:
        attr = loc.get_attribute("onpaste") or ""
        if "false" in attr:
            checks.append("붙여넣기 차단 확인 (onpaste)")
        else:
            failures.append("onpaste 차단 속성 없음")

    loc.fill("")
    if loc.input_value() != "":
        if ftype == "number_input":
            checks.append("비움 불가 (앱 유효성 검사 추정)")
        else:
            failures.append("입력 후 삭제 불가")
    else:
        checks.append("입력/삭제 자유도 확인")

    status, detail = ctx.status_detail(failures, checks)
    return {"status": status, "detail": detail}


def _test_plain_checkbox_dep(ctx: ScanContext, selector: str) -> dict:
    """
    plain_checkbox 종속 필드 클릭 동작 테스트.
    ON 상태일 때 호출된다 — 클릭 후 상태 변경 확인 후 원래 상태로 복원.
    """
    loc = ctx.page.locator(selector)
    if loc.count() == 0:
        return {"status": "skip", "detail": "요소 없음"}

    was   = loc.is_checked()
    loc.evaluate("el => el.click()")
    ctx.page.wait_for_timeout(200)
    after = loc.is_checked()

    if after != was:
        loc.evaluate("el => el.click()")
        ctx.page.wait_for_timeout(200)

    if after != was:
        return {"status": "pass", "detail": "클릭 동작 확인"}
    else:
        return {"status": "fail", "detail": "클릭 후 상태 미변경"}
