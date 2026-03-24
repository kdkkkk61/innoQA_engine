"""
validators/plain_checkbox.py — 일반 체크박스 검증

검증 항목:
  ① 요소 DOM 존재 확인
  ② label[for="id"] 클릭 시 체크 상태 변화 확인
     - label[for] 없으면 조상 <label> 시도
     - label 자체 없으면 "label[for] 없음"으로 생략 처리
  검증 후 원래 체크 상태로 복원.
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext


def scan_plain_checkboxes(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    for cb in hints.get("plain_checkboxes", []):
        selector = cb["selector"]
        label    = cb.get("label", selector)
        order    = cb.get("order")
        ctx.log.debug(f"[plain_checkbox] 스캔 시작: {label!r} ({selector})")
        try:
            loc = ctx.page.locator(selector)
            if loc.count() == 0:
                report.results.append(ScanResult(
                    pattern="plain_checkbox", selector=selector, label=label,
                    status="skip", detail="요소를 찾을 수 없음", order=order,
                ))
                continue

            failures: list[str] = []
            checks:   list[str] = ["존재 확인"]

            cb_id     = selector.replace("input#", "", 1)
            label_loc = ctx.page.locator(f'label[for="{cb_id}"]')

            if label_loc.count() == 0:
                has_ancestor = loc.evaluate("el => !!el.closest('label')")
                if has_ancestor:
                    label_loc = ctx.page.locator(f"label:has({selector})")

            if label_loc.count() > 0:
                ctx.log.debug(f"[plain_checkbox] {label!r} → is_checked() 호출")
                before = loc.is_checked()
                ctx.log.debug(f"[plain_checkbox] {label!r} → 라벨 클릭 (before={before})")
                label_loc.first.evaluate("el => el.click()")
                ctx.page.wait_for_timeout(300)
                after = loc.is_checked()
                ctx.log.debug(f"[plain_checkbox] {label!r} → 클릭 후 after={after}")

                if after == before:
                    failures.append("라벨 클릭 무반응 (체크 상태 변화 없음)")
                else:
                    checks.append("라벨 클릭 동작 확인")
                    ctx.log.debug(f"[plain_checkbox] {label!r} → 상태 복원")
                    loc.evaluate("el => el.click()")
                    ctx.page.wait_for_timeout(200)
            else:
                checks.append("label[for] 없음 (라벨 클릭 테스트 생략)")

            status, detail = ctx.status_detail(failures, checks)
            ctx.log.debug(f"[plain_checkbox] {label!r} → {status}: {detail}")
            report.results.append(ScanResult(
                pattern="plain_checkbox", selector=selector, label=label,
                status=status, detail=detail, order=order,
            ))
        except Exception:
            ctx.append_error(report, "plain_checkbox", selector, label, order)
