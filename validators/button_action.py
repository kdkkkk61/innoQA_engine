"""
validators/button_action.py — 버튼 동작 검증

검증 항목:
  ① 버튼 DOM 존재 확인
  ② 버튼 클릭 후 기대 결과 확인
     - type: "all_checked"  → targets 전체가 checked 상태인지 확인
  ③ 검증 후 원래 상태로 복원 (restore: true 기본값)

YAML 구조:
  button_actions:
    - selector: "button#allCheck"
      label:    "전체 선택"
      order:    47
      verify:
        type:    "all_checked"
        targets:
          - "input#sunday"
          - "input#monday"
          ...
      restore: true   # 클릭 전 상태로 복원 (기본값 true)
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext


def scan_button_actions(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    for action in hints.get("button_actions", []):
        selector = action["selector"]
        label    = action.get("label", selector)
        order    = action.get("order")
        verify   = action.get("verify", {})
        restore  = action.get("restore", True)

        ctx.log.debug(f"[button_action] 스캔 시작: {label!r} ({selector})")
        try:
            loc = ctx.page.locator(selector)
            if loc.count() == 0:
                report.results.append(ScanResult(
                    pattern="button_action", selector=selector, label=label,
                    status="skip", detail="버튼을 찾을 수 없음", order=order,
                ))
                continue

            targets   = verify.get("targets", [])
            vtype     = verify.get("type")
            failures: list[str] = []
            checks:   list[str] = ["버튼 존재 확인"]

            # ① 클릭 전 상태 저장
            before: dict[str, bool | None] = {}
            for t in targets:
                try:
                    before[t] = ctx.page.locator(t).is_checked()
                except Exception:
                    before[t] = None

            # ② 버튼 클릭
            ctx.log.debug(f"[button_action] {label!r} → 클릭")
            loc.evaluate("el => el.click()")
            ctx.page.wait_for_timeout(300)

            # ③ 결과 검증
            if vtype == "all_checked":
                not_checked = [
                    t for t in targets
                    if not ctx.page.locator(t).is_checked()
                ]
                if not_checked:
                    failures.append(
                        f"전체 선택 후 미체크 항목 {len(not_checked)}개: "
                        + ", ".join(not_checked)
                    )
                else:
                    checks.append(
                        f"전체 선택 동작 확인 ({len(targets)}개 모두 체크됨)"
                    )

            # ④ 복원
            if restore and targets:
                ctx.log.debug(f"[button_action] {label!r} → 원래 상태 복원")
                for t, was in before.items():
                    if was is None:
                        continue
                    try:
                        now = ctx.page.locator(t).is_checked()
                        if now != was:
                            ctx.page.locator(t).evaluate("el => el.click()")
                            ctx.page.wait_for_timeout(100)
                    except Exception:
                        pass

            status, detail = ctx.status_detail(failures, checks)
            ctx.log.debug(f"[button_action] {label!r} → {status}: {detail}")
            report.results.append(ScanResult(
                pattern="button_action", selector=selector, label=label,
                status=status, detail=detail, order=order,
            ))

        except Exception:
            ctx.append_error(report, "button_action", selector, label, order)
