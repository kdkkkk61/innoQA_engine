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

_ORDER_REQUIRED_SUBMIT = 9999   # 항상 출력 맨 마지막 (시나리오 2 끝)
_ORDER_MODIFY_REQUIRED = 9000   # 시나리오 4-3 — 시나리오 4 영역 마지막


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
        exp_type = step_def.get("expected_type", "")  # "any_warning" 등 타입 기반 판정
        label    = f"필수 입력 Step {step_n} ({desc})"

        # ── phases_only 필터: 특정 phase에서만 실행 ──────────────────────────
        phases_only = step_def.get("phases_only", [])
        if phases_only and ctx.phase not in phases_only:
            continue

        if expected == "success":
            report.results.append(ScanResult(
                pattern="required_submit", selector=submit_sel, label=label,
                status="pass",
                detail=f"필수 필드 확인 완료: {fill_ids} → 저장 성공 (close_fn 담당)",
                order=_ORDER_REQUIRED_SUBMIT,
                extra={"missing_field": ""},
            ))
            continue

        # ── fill_from_context: context_extra에서 값을 읽어 특정 필드 채우기 ──
        if "fill_from_context" in step_def:
            ctx_key     = step_def["fill_from_context"]
            fill_target = step_def.get("fill_target", "")
            ctx_val     = ctx.extra.get(ctx_key, "")

            if not ctx_val:
                report.results.append(ScanResult(
                    pattern="required_submit", selector=submit_sel, label=label,
                    status="skip",
                    detail=f"context_extra['{ctx_key}'] 미설정 — 스킵",
                    order=_ORDER_REQUIRED_SUBMIT,
                    extra={
                        "missing_field":       step_def.get("missing_field", ""),
                        "missing_field_label": step_def.get("missing_field_label", ""),
                    },
                ))
                continue

            if fill_target in text_idx:
                ti  = text_idx[fill_target]
                loc = ctx.page.locator(ti["selector"])
                if loc.count() > 0:
                    loc.fill(ctx_val)
                    ctx.page.wait_for_timeout(200)

            # ── fill_tag_before: 제출 전 tag_input 미리 채우기 (중복 검증용) ──
            for tag_id in step_def.get("fill_tag_before", []):
                if tag_id in tag_idx:
                    ti      = tag_idx[tag_id]
                    inp_loc = ctx.page.locator(ti["input"])
                    btn_loc = ctx.page.locator(ti["add_btn"])
                    if inp_loc.count() > 0 and btn_loc.count() > 0:
                        inp_loc.fill(ti.get("test_value", "scan_test"))
                        ctx.page.wait_for_timeout(200)
                        btn_loc.first.evaluate("el => el.click()")
                        ctx.page.wait_for_timeout(400)
        else:
            # ── 일반 fill 로직 ───────────────────────────────────────────────
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

            # ── 결과 판정 ────────────────────────────────────────────────────
            if exp_type == "any_warning":
                # 어떤 경고든 출현하면 pass (메시지 내용 무관 — 중복 이름 등)
                if actual_msg:
                    status = "pass"
                    detail = f"경고 확인: '{actual_msg}'"
                else:
                    main_open = ctx.page.locator(f"#{main_modal_sel}.in").count() > 0
                    status    = "fail"
                    detail    = "경고 없이 제출됨 " + ("(모달 유지)" if main_open else "(모달 닫힘)")
            elif not actual_msg:
                main_open = ctx.page.locator(f"#{main_modal_sel}.in").count() > 0
                status    = "fail"
                detail    = "경고 없이 제출됨 " + ("(모달 유지)" if main_open else "(모달 닫힘)")
            elif exp_msg and actual_msg != exp_msg:
                status = "fail"
                detail = f"메시지 불일치 — 실제: '{actual_msg}' / 기대: '{exp_msg}'"
            else:
                status = "pass"
                detail = f"경고: '{actual_msg}'"

            # fail/warn 시 dismiss 직전 캡처된 스크린샷 첨부 (모달 + cause 한 프레임)
            result_extra = {
                "missing_field":       step_def.get("missing_field", ""),
                "missing_field_label": step_def.get("missing_field_label", ""),
            }
            if status in ("fail", "warn") and ctx.last_warning_screenshot:
                result_extra["screenshot"] = ctx.last_warning_screenshot

            report.results.append(ScanResult(
                pattern="required_submit", selector=submit_sel, label=label,
                status=status, detail=detail, order=_ORDER_REQUIRED_SUBMIT,
                extra=result_extra,
            ))

            # ── reset_after: 지정 텍스트 필드 초기화 (중복 테스트 후 폼 리셋) ──
            for rf_id in step_def.get("reset_after", []):
                if rf_id in text_idx:
                    loc_r = ctx.page.locator(text_idx[rf_id]["selector"])
                    if loc_r.count() > 0:
                        loc_r.fill("")
                        ctx.page.wait_for_timeout(100)
                filled.discard(rf_id)

            # ── reset_tag_after: fill_tag_before로 추가한 태그 전부 제거 ───────
            for tag_id in step_def.get("reset_tag_after", []):
                if tag_id in tag_idx:
                    ti         = tag_idx[tag_id]
                    cont_loc   = ctx.page.locator(ti["container"])
                    remove_sel = ti.get("remove_btn", "button.deleteBtn")
                    try:
                        for _ in range(20):   # 최대 20개 태그 제거
                            del_btns = cont_loc.locator(remove_sel)
                            if del_btns.count() == 0:
                                break
                            del_btns.first.evaluate("el => el.click()")
                            ctx.page.wait_for_timeout(300)
                    except Exception:
                        ctx.log.debug(
                            f"[req_seq] reset_tag_after 실패: {tag_id}\n"
                            f"{traceback.format_exc()}"
                        )

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

        # fail 시 캡처: dismiss 직전 캡처본이 있으면 우선, 없으면 현재 화면 폴백
        result_extra = {}
        if status == "fail":
            ss = (
                ctx.last_warning_screenshot
                or ctx.take_screenshot(f"required_submit_simple_{mode}")
            )
            if ss:
                result_extra["screenshot"] = ss

        report.results.append(ScanResult(
            pattern="required_submit", selector=submit_sel,
            label=f"필수 필드 미입력 {mode} 검증",
            status=status, detail=detail, order=_ORDER_REQUIRED_SUBMIT,
            extra=result_extra,
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

        # 시나리오 2의 책임 = 1차 검증 (경고 떴는가). 추정 금지 원칙(scenario_2_input.md)
        # 에 따라 "저장됐다" 같은 표현 사용 금지. 실제 저장값은 시나리오 4-3에서 확인.
        if not main_still_open:
            if ctx.is_known_bug(submit_sel, "edit_required_submit"):
                status = "fail"
                detail = (
                    "필수 필드 비운 채 수정 시도 — 경고 없이 모달 닫힘 "
                    "(클라이언트 검증 누락) [알려진 버그] "
                    "→ 실제 저장값은 시나리오 4-3 참조"
                )
            else:
                status = "fail"
                detail = (
                    "필수 필드 비운 채 수정 시도 — 경고 없이 모달 닫힘 "
                    "(클라이언트 검증 누락) → 실제 저장값은 시나리오 4-3 참조"
                )
        elif warning_appeared:
            status, detail = "pass", "필수 필드 비운 채 수정 시 경고 모달 정상 출력"
        else:
            status, detail = "pass", "필수 필드 비운 채 수정 시 모달 닫히지 않음 (필드 검증 동작)"

        # fail 시 캡처: dismiss 직전 캡처본 우선 (경고 모달 + 입력 폼 한 프레임).
        # 경고 없이 닫힌 케이스(main_still_open=False)는 last_warning_screenshot=None →
        # 현재 화면(목록) 폴백 캡처. 의미는 떨어지지만 기록은 남음.
        ss = None
        if status == "fail":
            ss = (
                ctx.last_warning_screenshot
                or ctx.take_screenshot("edit_required_submit_fallback")
            )
        report.results.append(ScanResult(
            pattern="required_submit", selector=submit_sel,
            label="필수 필드 미입력 수정 검증",
            status=status, detail=detail, order=_ORDER_REQUIRED_SUBMIT,
            extra={"screenshot": ss} if ss else {},
        ))

        # ── 시나리오 4-3: 위반 결과 확인 (modal_form) ────────────────────
        # 1차에서 "fail (경고 없이 모달 닫힘)" 인 경우만 진행 — 실제 저장값을
        # 직접 재오픈해서 확인 (추정 금지 원칙, scenario_4_modify.md 4-3).
        # 호출 조건: ctx.phase == 4 + reopen_edit_fn 콜백 + 1차 fail + 모달 닫힘
        reopen_fn = ctx.extra.get("reopen_edit_fn")
        if (
            status == "fail"
            and not main_still_open
            and required_input_sel
            and reopen_fn
        ):
            _run_modify_required_check(
                ctx, report, required_input_sel, original_value, reopen_fn
            )
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


def _run_modify_required_check(
    ctx:           ScanContext,
    report:        PageScanReport,
    required_sel:  str,
    original_val:  str,
    reopen_fn:     callable,
) -> None:
    """
    시나리오 4-3: 필수 필드 비움 시도 후 실제 저장값 확인 (modal_form).

    1차 검증(_run_submit_edit)에서 "경고 없이 모달 닫힘"으로 끝난 케이스의 후속.
    재오픈 → 실제 값 확인 → 분기 판정 (scenario_4_modify.md 4-3).

    분기:
        "" (빈값)   → fail   (데이터 손상)
        original    → warn   (서버 거부, UX 혼란)
        그 외 다른값 → fail   (제품의 예상 못한 동작)

    호출 후 모달은 재오픈된 상태 — 호출자(_run_submit_edit)의 finally에서
    원본 복원 처리. 정리 책임은 호출자에 있다.
    """
    label = "필수 필드 — 빈값 저장 시도 후 결과"
    try:
        # 모달 재오픈 (콜백)
        reopen_fn()
        ctx.page.wait_for_timeout(300)

        # 실제 저장값 읽기
        loc = ctx.page.locator(required_sel)
        if loc.count() == 0:
            ctx.append_error(
                report, "modify_required", required_sel,
                label + " (재오픈 후 필드 미발견)", _ORDER_MODIFY_REQUIRED, phase=4,
            )
            return
        actual = loc.input_value()

        # 분기 판정
        if actual == "":
            status = "fail"
            detail = (
                f"빈값 그대로 저장됨 — 데이터 손상 "
                f"(입력: 비움 / 결과: '')"
            )
        elif actual == original_val:
            status = "warn"
            detail = (
                f"서버가 빈값 거부 → 이전값 유지 "
                f"(입력: 비움 / 결과: {actual!r}) — UX 혼란 유발"
            )
        else:
            status = "fail"
            detail = (
                f"제품의 예상 못한 동작 "
                f"(입력: 비움 / 원본: {original_val!r} / 결과: {actual!r})"
            )

        # 캡처: 재오픈된 모달 화면 (실제 저장값 보임 — Type 3 결과 검증형)
        ss = ctx.take_screenshot("modify_required_actual") if status in ("fail", "warn") else None

        report.results.append(ScanResult(
            pattern="modify_required", selector=required_sel, label=label,
            status=status, detail=detail,
            order=_ORDER_MODIFY_REQUIRED, phase=4,
            extra={"screenshot": ss} if ss else {},
        ))
    except Exception:
        ctx.append_error(
            report, "modify_required", required_sel, label,
            _ORDER_MODIFY_REQUIRED, phase=4,
        )
