"""
validators/radio_group.py — 라디오 그룹 검증

검증 항목:
  ① 모든 옵션 DOM 존재 확인
  ② 기본값 확인 (YAML default 정의 시)
  ③ 전체 옵션 순환 클릭 테스트 → 원래 옵션으로 복원
"""
from __future__ import annotations

from core.models import PageScanReport, ScanResult
from core.scan_context import ScanContext


def scan_radio_groups(
    ctx: ScanContext, hints: dict, report: PageScanReport
) -> None:
    for group in hints.get("radio_groups", []):
        name          = group["name"]
        label         = group.get("label", name)
        options       = group.get("options", [])
        order         = group.get("order")
        default_value = group.get("default")

        ctx.log.debug(f"[radio_group] 스캔 시작: {label!r} (name={name})")
        try:
            # ① 모든 옵션 존재 확인
            missing = [
                opt["selector"]
                for opt in options
                if ctx.page.locator(opt["selector"]).count() == 0
            ]
            if missing:
                report.results.append(ScanResult(
                    pattern="radio_group", selector=f"[name={name}]", label=label,
                    status="fail", detail=f"라디오 옵션 누락: {missing}", order=order,
                ))
                continue

            failures: list[str] = []
            checks:   list[str] = [f"옵션 {len(options)}개 모두 존재"]

            # ② 기본값 확인
            if default_value is not None:
                default_opt = next(
                    (o for o in options if o.get("value") == default_value), None
                )
                if default_opt is None:
                    failures.append(f"YAML default '{default_value}' 에 해당하는 옵션 없음")
                elif not ctx.page.locator(default_opt["selector"]).is_checked():
                    failures.append(f"기본값 불일치 (기대: '{default_value}')")
                else:
                    checks.append(f"기본값 '{default_value}' 확인")

            # ③ 전체 옵션 순환 클릭 테스트
            initial_opt = next(
                (o for o in options if ctx.page.locator(o["selector"]).is_checked()),
                None,
            )
            ctx.log.debug(
                f"[radio_group] {label!r} → initial={initial_opt and initial_opt.get('value')!r}"
            )

            failed_opts: list[str] = []
            for opt in options:
                opt_val = opt.get("value", opt["selector"])
                opt_loc = ctx.page.locator(opt["selector"])
                ctx.log.debug(f"[radio_group] {label!r} → 클릭: {opt_val!r}")
                opt_loc.evaluate("el => el.click()")
                ctx.page.wait_for_timeout(300)
                if not opt_loc.is_checked():
                    failed_opts.append(opt_val)

            if failed_opts:
                failures.append(f"클릭 후 선택 실패 옵션: {', '.join(failed_opts)}")
            else:
                checks.append(f"전체 {len(options)}개 옵션 클릭 선택 확인")

            # 원래 옵션으로 복원
            if initial_opt:
                ctx.log.debug(
                    f"[radio_group] {label!r} → 복원: {initial_opt.get('value')!r}"
                )
                ctx.page.locator(initial_opt["selector"]).evaluate("el => el.click()")
                ctx.page.wait_for_timeout(200)

            status, detail = ctx.status_detail(failures, checks)
            ctx.log.debug(f"[radio_group] {label!r} → {status}: {detail}")
            report.results.append(ScanResult(
                pattern="radio_group", selector=f"[name={name}]", label=label,
                status=status, detail=detail, order=order,
            ))

        except Exception:
            ctx.append_error(report, "radio_group", f"[name={name}]", label, order)
