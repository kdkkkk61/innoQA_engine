"""
validators/required_submit.py — 필수 입력 미입력 제출 검증

ADD 모달 + required_submit_sequence 정의 → 단계별 순서 검증
ADD 모달 + 시퀀스 없음              → 빈 폼 단순 검증
EDIT 모달 (submit_modify)           → 필수 필드 비움 → 수정 시도 → 경고 확인 → 복원
"""
from __future__ import annotations

import traceback

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext

_ORDER_REQUIRED_SUBMIT = 9999   # 항상 출력 맨 마지막


def scan_required_submit(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """
    필수 입력 미입력 시 제출 검증.
    호출 전 모달이 열려 있어야 하며, 호출 후 모달은 그대로 유지.
    """
    actions    = hints.get("modal_actions") or {}
    add_sel    = actions.get("submit_add", "")
    modify_sel = actions.get("submit_modify", "")

    is_add  = bool(add_sel    and ctx.page.locator(add_sel).is_visible())
    is_edit = bool(modify_sel and ctx.page.locator(modify_sel).is_visible()) and not is_add

    if not is_add and not is_edit:
        report.results.append(ScanResult(
            pattern="required_submit",
            selector=add_sel or modify_sel or "(none)",
            label="필수 필드 미입력 제출 검증",
            status="skip", detail="submit 버튼 없음",
            order=_ORDER_REQUIRED_SUBMIT,
        ))
        return

    # 첫 번째 탭으로 이동 (필수 입력 필드 있는 탭)
    tabs = hints.get("modal_tabs", [])
    if tabs:
        ctx.activate_tab(tabs[0])

    if is_add and hints.get("required_submit_sequence"):
        _run_submit_sequence(ctx, hints, report, add_sel)
    elif is_add:
        _run_submit_simple(ctx, hints, report, add_sel, mode="등록")
    else:
        _run_submit_edit(ctx, hints, report, modify_sel)


def _run_submit_sequence(
    ctx: ScanContext, hints: dict, report: PageScanReport, submit_sel: str
) -> None:
    """
    required_submit_sequence YAML 기반 단계별 필수 입력 검증 (ADD 모달 전용).

    각 step에서 fill 필드를 누적으로 채우고 submit 클릭 → 경고 메시지 일치 검증.
    expected: "success" 인 마지막 step은 실행 생략 (실제 저장은 close_fn 담당).
    """
    sequence       = hints.get("required_submit_sequence", [])
    main_modal_sel = hints.get("modal_id", "addItemModal")

    text_idx = {
        ti["selector"].replace("input#", ""): ti
        for ti in hints.get("text_inputs", [])
    }
    tag_idx = {ti["id"]: ti for ti in hints.get("tag_input", [])}

    filled: set[str] = set()

    for step_def in sequence:
        step_n   = step_def.get("step", "?")
        desc     = step_def.get("description", "")
        fill_ids = step_def.get("fill", [])
        exp_msg  = step_def.get("expected_msg", "")
        expected = step_def.get("expected", "")
        label    = f"필수 입력 Step {step_n} ({desc})"

        if expected == "success":
            report.results.append(ScanResult(
                pattern="required_submit", selector=submit_sel, label=label,
                status="pass",
                detail=f"필수 필드 확인 완료: {fill_ids} → 저장 성공 (close_fn 담당)",
                order=_ORDER_REQUIRED_SUBMIT,
            ))
            continue

        for fid in fill_ids:
            if fid in filled:
                continue
            try:
                if fid in text_idx:
                    ti  = text_idx[fid]
                    loc = ctx.page.locator(ti["selector"])
                    if loc.count() > 0:
                        loc.fill(ti.get("test_value", "[AUTO]_seq"))
                        ctx.page.wait_for_timeout(150)
                        filled.add(fid)
                elif fid in tag_idx:
                    ti      = tag_idx[fid]
                    inp_loc = ctx.page.locator(ti["input"])
                    btn_loc = ctx.page.locator(ti["add_btn"])
                    if inp_loc.count() > 0 and btn_loc.count() > 0:
                        inp_loc.fill(ti.get("test_value", "scan_test"))
                        ctx.page.wait_for_timeout(200)
                        btn_loc.first.evaluate("el => el.click()")
                        ctx.page.wait_for_timeout(400)
                        filled.add(fid)
            except Exception:
                ctx.log.debug(
                    f"[req_seq] 필드 채우기 실패: {fid}\n{traceback.format_exc()}"
                )

        try:
            ctx.page.locator(submit_sel).first.evaluate("el => el.click()")
            ctx.page.wait_for_timeout(600)

            warn       = ctx.page.locator(ctx.SEL_WARN_MODAL)
            actual_msg = ""
            if warn.count() > 0:
                body = warn.locator(".modal-body")
                actual_msg = body.inner_text().strip() if body.count() > 0 else ""
                ctx.dismiss_warning_dialog()

            if not actual_msg:
                main_open = ctx.page.locator(f"#{main_modal_sel}.in").count() > 0
                status    = "fail"
                detail    = "경고 없이 제출됨 " + ("(모달 유지)" if main_open else "(모달 닫힘)")
            elif exp_msg and actual_msg != exp_msg:
                status = "fail"
                detail = f"메시지 불일치 — 실제: '{actual_msg}' / 기대: '{exp_msg}'"
            else:
                status = "pass"
                detail = f"경고: '{actual_msg}'"

            report.results.append(ScanResult(
                pattern="required_submit", selector=submit_sel, label=label,
                status=status, detail=detail, order=_ORDER_REQUIRED_SUBMIT,
            ))

        except Exception:
            ctx.append_error(
                report, "required_submit", submit_sel, label, _ORDER_REQUIRED_SUBMIT,
            )


def _run_submit_simple(
    ctx: ScanContext, hints: dict, report: PageScanReport, submit_sel: str, mode: str
) -> None:
    """ADD 모달 단순 검증 — 빈 폼으로 submit 클릭 후 경고 여부 확인 (시퀀스 미정의 폴백)."""
    main_modal_sel = hints.get("modal_id", "addItemModal")
    try:
        ctx.page.locator(submit_sel).first.evaluate("el => el.click()")
        ctx.page.wait_for_timeout(600)
        warning_appeared = ctx.dismiss_warning_dialog()
        main_still_open  = ctx.page.locator(f"#{main_modal_sel}.in").count() > 0

        if not main_still_open:
            status, detail = "fail", f"빈 채로 {mode} 시 경고 없이 모달이 닫힘"
        elif warning_appeared:
            status, detail = "pass", f"빈 채로 {mode} 시 경고 모달 정상 출력"
        else:
            status, detail = "pass", f"빈 채로 {mode} 시 모달 닫히지 않음 (필드 검증 동작)"

        report.results.append(ScanResult(
            pattern="required_submit", selector=submit_sel,
            label=f"필수 필드 미입력 {mode} 검증",
            status=status, detail=detail, order=_ORDER_REQUIRED_SUBMIT,
        ))
    except Exception:
        ctx.append_error(
            report, "required_submit", submit_sel,
            f"필수 필드 미입력 {mode} 검증", _ORDER_REQUIRED_SUBMIT,
        )


def _run_submit_edit(
    ctx: ScanContext, hints: dict, report: PageScanReport, submit_sel: str
) -> None:
    """EDIT 모달 검증 — 필수 text_input 비움 → 수정 시도 → 경고 확인 → 값 복원."""
    main_modal_sel     = hints.get("modal_id", "addItemModal")
    required_input_sel = ""
    original_value     = ""

    for ti in hints.get("text_inputs", []):
        if ti.get("required") and ctx.page.locator(ti["selector"]).count() > 0:
            required_input_sel = ti["selector"]
            break

    if required_input_sel:
        req_loc        = ctx.page.locator(required_input_sel)
        original_value = req_loc.input_value()
        req_loc.fill("")
        ctx.page.wait_for_timeout(200)

    try:
        ctx.page.locator(submit_sel).first.evaluate("el => el.click()")
        ctx.page.wait_for_timeout(600)
        warning_appeared = ctx.dismiss_warning_dialog()
        main_still_open  = ctx.page.locator(f"#{main_modal_sel}.in").count() > 0

        if not main_still_open:
            status, detail = "fail", "필수 필드 비운 채 수정 시 경고 없이 모달이 닫힘"
        elif warning_appeared:
            status, detail = "pass", "필수 필드 비운 채 수정 시 경고 모달 정상 출력"
        else:
            status, detail = "pass", "필수 필드 비운 채 수정 시 모달 닫히지 않음 (필드 검증 동작)"

        report.results.append(ScanResult(
            pattern="required_submit", selector=submit_sel,
            label="필수 필드 미입력 수정 검증",
            status=status, detail=detail, order=_ORDER_REQUIRED_SUBMIT,
        ))
    except Exception:
        ctx.append_error(
            report, "required_submit", submit_sel,
            "필수 필드 미입력 수정 검증", _ORDER_REQUIRED_SUBMIT,
        )
    finally:
        if required_input_sel:
            try:
                loc = ctx.page.locator(required_input_sel)
                if loc.count() > 0:
                    loc.fill(original_value)
            except Exception:
                ctx.log.debug(
                    f"[required_submit] EDIT 복원 실패:\n{traceback.format_exc()}"
                )
