"""
validators/tag_input.py — 태그 입력 검증

검증 항목:
  ① input + add_btn + container 세 요소 DOM 존재 확인
  ② required 마커 (required: true 시)
  ③ 태그 추가 동작 — test_value 입력 → add_btn 클릭 → container 항목 증가 확인
  ④ 태그 삭제 동작 — remove_btn 클릭 → container 항목 감소 확인

required_toggle: 탭 접근 prerequisite 토글 (탭 차단 시 ON 후 재시도)
"""
from __future__ import annotations

import traceback

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext

# 태그 삭제 버튼 자동 탐지 시 시도 패턴 (컨테이너 내부 상대 selector)
_REMOVE_BTN_PATTERNS = [
    ".delBtn", ".del", ".removeBtn", ".remove-btn",
    ".close", ".btn-delete", ".tag-delete",
    "[ng-click*='remove']", "[ng-click*='delete']", "[ng-click*='del']",
]


def scan_tag_inputs(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    """tag_input 항목을 검증한다."""
    _toggle_restore: dict[str, bool] = {}

    for tag in hints.get("tag_input", []):
        tag_id            = tag["id"]
        label             = tag.get("label", tag_id)
        inp_sel           = tag["input"]
        btn_sel           = tag["add_btn"]
        cont_sel          = tag["container"]
        required          = tag.get("required", False)
        order             = tag.get("order")
        test_value        = tag.get("test_value", "scan_test")
        unique_test_value = tag.get("unique_test_value")
        remove_btn_sel    = tag.get("remove_btn")
        required_toggle   = tag.get("required_toggle")

        ctx.log.debug(f"[tag_input] 스캔 시작: {label!r} (id={tag_id})")

        tab_activated = True
        tab_id = tag.get("tab")
        if tab_id:
            tab_activated = ctx.activate_tab({"data_tab": tab_id})
            if not tab_activated and required_toggle:
                req_loc = ctx.page.locator(required_toggle)
                if req_loc.count() > 0:
                    prev_checked = req_loc.is_checked()
                    if required_toggle not in _toggle_restore:
                        _toggle_restore[required_toggle] = prev_checked
                    if not prev_checked:
                        ctx.log.debug(
                            f"[tag_input] {label!r} → required_toggle ON: {required_toggle}"
                        )
                        req_loc.evaluate("el => el.click()")
                        ctx.page.wait_for_timeout(300)
                    tab_activated = ctx.activate_tab({"data_tab": tab_id})
        ctx.log.debug(f"[tag_input] {label!r} → tab_activated={tab_activated}")

        try:
            # ① 세 요소 존재 확인
            missing = [
                sel
                for sel in [inp_sel, btn_sel, cont_sel]
                if ctx.page.locator(sel).count() == 0
            ]
            if missing:
                report.results.append(ScanResult(
                    pattern="tag_input", selector=inp_sel, label=label,
                    status="fail", detail=f"요소 누락: {missing}",
                    extra={"tag_id": tag_id}, order=order,
                ))
                continue

            failures: list[str] = []
            checks:   list[str] = ["input + 추가버튼 + 컨테이너 존재"]

            # ② required 마커 검증
            if required:
                inp_id       = inp_sel.replace("input#", "", 1)
                has_star_cls = ctx.page.locator(
                    f'label[for="{inp_id}"] .star, dt .star'
                ).count() > 0
                has_req_attr = ctx.page.locator(inp_sel).get_attribute("required") is not None
                if not has_star_cls and not has_req_attr:
                    try:
                        dt_text = ctx.page.locator(inp_sel).evaluate(
                            "el => el.closest('dl')?.querySelector('dt')?.textContent || ''"
                        )
                        if "*" not in dt_text and "＊" not in dt_text:
                            failures.append("필수 필드 표시 없음 (dt에 * 마커 미확인)")
                        else:
                            checks.append("required 마커 확인")
                    except Exception:
                        failures.append("필수 필드 마커 확인 중 오류")
                else:
                    checks.append("required 마커 확인")

            # ③④ 동작 테스트 — 탭이 경고 다이얼로그로 차단된 경우 스킵
            if not tab_activated:
                checks.append(
                    "생성 시 작성 불가 (탭 클릭 시 앱이 경고로 차단 — 수정 모달에서 검증)"
                )
            else:
                cont_loc = ctx.page.locator(cont_sel)
                inp_loc  = ctx.page.locator(inp_sel)
                btn_loc  = ctx.page.locator(btn_sel)

                ctx.log.debug(f"[tag_input] {label!r} → 초기 항목 수 카운트 ({cont_sel})")
                initial_count = cont_loc.evaluate(
                    "el => el.querySelectorAll(':scope > *').length"
                )
                ctx.log.debug(f"[tag_input] {label!r} → initial_count={initial_count}")

                # ③-1차: test_value 추가 시도
                ctx.log.debug(f"[tag_input] {label!r} → fill({test_value!r}) → {inp_sel}")
                inp_loc.fill(test_value)
                ctx.page.wait_for_timeout(200)
                ctx.log.debug(f"[tag_input] {label!r} → add_btn 클릭 ({btn_sel})")
                btn_loc.first.evaluate("el => el.click()")
                ctx.page.wait_for_timeout(400)

                after_first = cont_loc.evaluate(
                    "el => el.querySelectorAll(':scope > *').length"
                )
                ctx.log.debug(f"[tag_input] {label!r} → after_first={after_first}")

                tag_was_added = False

                if after_first > initial_count:
                    checks.append("태그 추가 동작 확인")
                    tag_was_added = True

                elif unique_test_value:
                    checks.append(f"중복 입력 거부 확인 ({test_value!r})")
                    ctx.log.debug(
                        f"[tag_input] {label!r} → 2차 시도: "
                        f"unique_test_value={unique_test_value!r}"
                    )
                    inp_loc.fill(unique_test_value)
                    ctx.page.wait_for_timeout(200)
                    btn_loc.first.evaluate("el => el.click()")
                    ctx.page.wait_for_timeout(400)

                    after_second = cont_loc.evaluate(
                        "el => el.querySelectorAll(':scope > *').length"
                    )
                    ctx.log.debug(
                        f"[tag_input] {label!r} → after_second={after_second}"
                    )
                    if after_second > after_first:
                        checks.append("태그 추가 동작 확인")
                        tag_was_added = True
                    else:
                        failures.append(
                            f"태그 추가 동작 실패 (추가 전: {after_first},"
                            f" 추가 후: {after_second})"
                        )

                else:
                    failures.append(
                        f"태그 추가 동작 실패 (추가 전: {initial_count},"
                        f" 추가 후: {after_first})"
                    )

                # ④ 태그 삭제 동작 테스트
                if tag_was_added:
                    _remove = remove_btn_sel
                    if not _remove:
                        for pat in _REMOVE_BTN_PATTERNS:
                            if cont_loc.locator(pat).count() > 0:
                                _remove = pat
                                ctx.log.debug(
                                    f"[tag_input] {label!r} → 삭제버튼 자동탐지: {pat}"
                                )
                                break

                    if _remove:
                        remove_loc = cont_loc.locator(_remove)
                        if remove_loc.count() > 0:
                            before_remove = cont_loc.evaluate(
                                "el => el.querySelectorAll(':scope > *').length"
                            )
                            ctx.log.debug(
                                f"[tag_input] {label!r} → 삭제버튼 클릭 ({_remove})"
                            )
                            remove_loc.first.evaluate("el => el.click()")
                            ctx.page.wait_for_timeout(400)
                            after_remove = cont_loc.evaluate(
                                "el => el.querySelectorAll(':scope > *').length"
                            )
                            if after_remove >= before_remove:
                                failures.append("태그 삭제 동작 실패")
                            else:
                                checks.append("태그 삭제 동작 확인")
                        else:
                            checks.append("삭제 버튼 없음 (삭제 테스트 생략)")
                    else:
                        checks.append("삭제 버튼 미탐지 (삭제 테스트 생략)")

            status, detail = ctx.status_detail(failures, checks)
            ctx.log.debug(f"[tag_input] {label!r} → {status}: {detail}")
            report.results.append(ScanResult(
                pattern="tag_input", selector=inp_sel, label=label,
                status=status, detail=detail,
                extra={"tag_id": tag_id}, order=order,
            ))

        except Exception:
            ctx.append_error(report, "tag_input", inp_sel, label, order)

    # required_toggle 원래 상태로 복원
    for req_sel, was_checked in _toggle_restore.items():
        try:
            req_loc = ctx.page.locator(req_sel)
            if req_loc.count() > 0 and req_loc.is_checked() != was_checked:
                ctx.log.debug(
                    f"[tag_input] required_toggle 복원: "
                    f"{req_sel} → {'ON' if was_checked else 'OFF'}"
                )
                req_loc.evaluate("el => el.click()")
                ctx.page.wait_for_timeout(200)
        except Exception:
            ctx.log.debug(
                f"[tag_input] required_toggle 복원 실패 ({req_sel}):\n"
                f"{traceback.format_exc()}"
            )
