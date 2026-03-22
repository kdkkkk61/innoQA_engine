"""
core/ui_scanner.py

scan_hints yaml을 읽어 Playwright page 객체로 실제 DOM을 검사하는 스캐너.
휴리스틱 탐지 없이 yaml 정의만 사용 → 오탐 최소화.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, Locator


# ──────────────────────────────────────────────
# 결과 데이터 클래스
# ──────────────────────────────────────────────

@dataclass
class ScanResult:
    pattern: str          # "toggle_checkbox" | "tag_input" | "radio_group" | ...
    selector: str
    label: str
    status: str           # "pass" | "fail" | "skip" | "known_bug" | "error"
    detail: str = ""
    extra: dict = field(default_factory=dict)

    def is_real_failure(self) -> bool:
        """known_bug와 skip은 실패 카운트에서 제외"""
        return self.status == "fail"


@dataclass
class PageScanReport:
    page_id: str
    results: list[ScanResult] = field(default_factory=list)

    @property
    def passed(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "pass"]

    @property
    def failed(self) -> list[ScanResult]:
        return [r for r in self.results if r.is_real_failure()]

    @property
    def known_bugs(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "known_bug"]

    @property
    def errors(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "error"]

    def summary(self) -> str:
        return (
            f"[{self.page_id}] "
            f"pass={len(self.passed)} "
            f"fail={len(self.failed)} "
            f"known_bug={len(self.known_bugs)} "
            f"error={len(self.errors)}"
        )


# ──────────────────────────────────────────────
# 스캐너 본체
# ──────────────────────────────────────────────

class UIScanner:
    """
    scan_hints yaml + known_bugs yaml을 기반으로 페이지 UI를 검사.

    사용법:
        scanner = UIScanner(page, config_dir="config")
        report  = scanner.scan("ransom_detect_policy", modal_open_fn=open_modal)
    """

    def __init__(self, page: Page, config_dir: str = "config") -> None:
        self.page = page
        self._config_dir = Path(config_dir)
        self._known_bugs: list[dict] = self._load_yaml(
            self._config_dir / "known_bugs.yaml"
        ) or []

    # ── public ────────────────────────────────

    def scan(
        self,
        page_id: str,
        modal_open_fn: callable | None = None,
        modal_close_fn: callable | None = None,
    ) -> PageScanReport:
        """
        page_id에 해당하는 scan_hints를 로드하고 전체 패턴을 검사.

        modal_open_fn: 모달을 열어주는 callable (없으면 모달 스캔 건너뜀)
        modal_close_fn: 모달을 닫아주는 callable (없으면 ESC 시도)
        """
        hints_path = self._config_dir / "scan_hints" / f"{page_id}.yaml"
        hints = self._load_yaml(hints_path)
        if not hints:
            raise FileNotFoundError(f"scan_hints not found: {hints_path}")

        report = PageScanReport(page_id=page_id)

        # 모달 열기
        modal_opened = False
        if modal_open_fn:
            try:
                modal_open_fn()
                modal_opened = True
            except Exception as e:
                report.results.append(ScanResult(
                    pattern="modal_open",
                    selector=hints.get("modal_trigger", {}).get("add", ""),
                    label="모달 열기",
                    status="error",
                    detail=str(e),
                ))
                return report

        # 탭 순서대로 스캔
        tabs = hints.get("modal_tabs", [])
        if tabs and modal_opened:
            for tab in tabs:
                self._activate_tab(tab)
        elif not tabs:
            pass  # 탭 없는 페이지도 지원

        # 패턴별 스캔
        self._scan_toggle_checkboxes(hints, report)
        self._scan_plain_checkboxes(hints, report)
        self._scan_radio_groups(hints, report)
        self._scan_text_inputs(hints, report)
        self._scan_tag_inputs(hints, report)

        # 모달 닫기
        if modal_opened:
            try:
                if modal_close_fn:
                    modal_close_fn()
                else:
                    close_btn = hints.get("modal_actions", {}).get("close")
                    if close_btn:
                        self.page.locator(close_btn).click()
            except Exception:
                pass

        return report

    # ── 탭 전환 ───────────────────────────────

    def _activate_tab(self, tab: dict) -> None:
        data_tab = tab.get("data_tab", "")
        try:
            tab_link = self.page.locator(f'a[data-tab="{data_tab}"]')
            if tab_link.count() > 0:
                tab_link.click()
                self.page.wait_for_timeout(300)
        except Exception:
            pass

    # ── 토글 체크박스 스캔 ────────────────────

    def _scan_toggle_checkboxes(self, hints: dict, report: PageScanReport) -> None:
        for toggle in hints.get("toggle_checkboxes", []):
            selector = toggle["selector"]
            label    = toggle.get("label", selector)
            deps     = toggle.get("dependent_fields", [])

            # known_bug 체크
            if self._is_known_bug(selector, "toggle_dependent_fields"):
                report.results.append(ScanResult(
                    pattern="toggle_checkbox",
                    selector=selector,
                    label=label,
                    status="known_bug",
                    detail="알려진 버그 — OFF 상태에서도 종속 필드 활성화",
                    extra={"dependent_fields": deps},
                ))
                continue

            try:
                result = self._check_toggle_with_deps(selector, label, deps)
                report.results.append(result)
            except Exception as e:
                report.results.append(ScanResult(
                    pattern="toggle_checkbox",
                    selector=selector,
                    label=label,
                    status="error",
                    detail=str(e),
                ))

    def _check_toggle_with_deps(
        self, selector: str, label: str, dep_selectors: list[str]
    ) -> ScanResult:
        toggle_loc = self.page.locator(selector)

        if toggle_loc.count() == 0:
            return ScanResult(
                pattern="toggle_checkbox",
                selector=selector,
                label=label,
                status="skip",
                detail="요소를 찾을 수 없음",
            )

        # 종속 필드가 없는 단순 토글 — 존재 확인만
        if not dep_selectors:
            return ScanResult(
                pattern="toggle_checkbox",
                selector=selector,
                label=label,
                status="pass",
                detail="토글 존재 확인",
            )

        # 현재 상태 저장
        was_checked = toggle_loc.is_checked()

        failures: list[str] = []

        # ① OFF 상태 → 종속 필드 disabled 확인
        if was_checked:
            toggle_loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(400)

        for dep in dep_selectors:
            dep_loc = self.page.locator(dep)
            if dep_loc.count() == 0:
                failures.append(f"종속 필드 없음: {dep}")
                continue
            if dep_loc.is_enabled():
                failures.append(f"OFF 상태인데 활성화됨: {dep}")

        # ② ON 상태 → 종속 필드 enabled 확인
        toggle_loc.evaluate("el => el.click()")
        self.page.wait_for_timeout(400)

        for dep in dep_selectors:
            dep_loc = self.page.locator(dep)
            if dep_loc.count() == 0:
                continue
            if not dep_loc.is_enabled():
                failures.append(f"ON 상태인데 비활성화됨: {dep}")

        # 원래 상태로 복원
        current = toggle_loc.is_checked()
        if current != was_checked:
            toggle_loc.evaluate("el => el.click()")
            self.page.wait_for_timeout(200)

        if failures:
            return ScanResult(
                pattern="toggle_checkbox",
                selector=selector,
                label=label,
                status="fail",
                detail="; ".join(failures),
                extra={"dependent_fields": dep_selectors},
            )

        return ScanResult(
            pattern="toggle_checkbox",
            selector=selector,
            label=label,
            status="pass",
            detail=f"ON/OFF 종속 필드 {len(dep_selectors)}개 정상",
            extra={"dependent_fields": dep_selectors},
        )

    # ── 일반 체크박스 스캔 ────────────────────

    def _scan_plain_checkboxes(self, hints: dict, report: PageScanReport) -> None:
        for cb in hints.get("plain_checkboxes", []):
            selector = cb["selector"]
            label    = cb.get("label", selector)
            try:
                loc = self.page.locator(selector)
                if loc.count() == 0:
                    status, detail = "skip", "요소를 찾을 수 없음"
                else:
                    status, detail = "pass", "요소 존재 확인"
                report.results.append(ScanResult(
                    pattern="plain_checkbox",
                    selector=selector,
                    label=label,
                    status=status,
                    detail=detail,
                ))
            except Exception as e:
                report.results.append(ScanResult(
                    pattern="plain_checkbox",
                    selector=selector,
                    label=label,
                    status="error",
                    detail=str(e),
                ))

    # ── 라디오 그룹 스캔 ─────────────────────

    def _scan_radio_groups(self, hints: dict, report: PageScanReport) -> None:
        for group in hints.get("radio_groups", []):
            name    = group["name"]
            label   = group.get("label", name)
            options = group.get("options", [])

            missing = []
            for opt in options:
                loc = self.page.locator(opt["selector"])
                if loc.count() == 0:
                    missing.append(opt["selector"])

            if missing:
                report.results.append(ScanResult(
                    pattern="radio_group",
                    selector=f"[name={name}]",
                    label=label,
                    status="fail",
                    detail=f"라디오 옵션 누락: {missing}",
                ))
            else:
                report.results.append(ScanResult(
                    pattern="radio_group",
                    selector=f"[name={name}]",
                    label=label,
                    status="pass",
                    detail=f"옵션 {len(options)}개 모두 존재",
                ))

    # ── 텍스트 입력 스캔 ─────────────────────

    def _scan_text_inputs(self, hints: dict, report: PageScanReport) -> None:
        for inp in hints.get("text_inputs", []):
            selector   = inp["selector"]
            label      = inp.get("label", selector)
            maxlength  = inp.get("maxlength")
            required   = inp.get("required", False)

            try:
                loc = self.page.locator(selector)
                if loc.count() == 0:
                    report.results.append(ScanResult(
                        pattern="text_input",
                        selector=selector,
                        label=label,
                        status="skip",
                        detail="요소를 찾을 수 없음",
                    ))
                    continue

                failures = []

                # maxlength 확인
                if maxlength is not None:
                    actual_ml = loc.get_attribute("maxlength")
                    if actual_ml is None:
                        failures.append(f"maxlength 속성 없음 (기대: {maxlength})")
                    elif int(actual_ml) != maxlength:
                        failures.append(
                            f"maxlength 불일치 (기대: {maxlength}, 실제: {actual_ml})"
                        )

                # required 확인
                if required:
                    # HTML required 속성 또는 label의 * 마커로 확인
                    has_req_attr = loc.get_attribute("required") is not None
                    # label의 .star span 존재 여부로 보완 확인
                    label_sel = f'label[for="{selector.lstrip("input#")}"] .star'
                    has_star  = self.page.locator(label_sel).count() > 0
                    if not has_req_attr and not has_star:
                        failures.append("필수 필드 표시 없음")

                if failures:
                    report.results.append(ScanResult(
                        pattern="text_input",
                        selector=selector,
                        label=label,
                        status="fail",
                        detail="; ".join(failures),
                    ))
                else:
                    report.results.append(ScanResult(
                        pattern="text_input",
                        selector=selector,
                        label=label,
                        status="pass",
                        detail="필드 속성 정상",
                    ))

            except Exception as e:
                report.results.append(ScanResult(
                    pattern="text_input",
                    selector=selector,
                    label=label,
                    status="error",
                    detail=str(e),
                ))

    # ── 태그 입력 스캔 ───────────────────────

    def _scan_tag_inputs(self, hints: dict, report: PageScanReport) -> None:
        for tag in hints.get("tag_input", []):
            tag_id    = tag["id"]
            label     = tag.get("label", tag_id)
            inp_sel   = tag["input"]
            btn_sel   = tag["add_btn"]
            cont_sel  = tag["container"]
            tab       = tag.get("tab")

            # 탭 전환 후 확인
            if tab:
                self._activate_tab({"data_tab": tab})

            try:
                missing = []
                for sel in [inp_sel, btn_sel, cont_sel]:
                    if self.page.locator(sel).count() == 0:
                        missing.append(sel)

                if missing:
                    report.results.append(ScanResult(
                        pattern="tag_input",
                        selector=inp_sel,
                        label=label,
                        status="fail",
                        detail=f"요소 누락: {missing}",
                        extra={"tag_id": tag_id},
                    ))
                else:
                    report.results.append(ScanResult(
                        pattern="tag_input",
                        selector=inp_sel,
                        label=label,
                        status="pass",
                        detail="input + 추가버튼 + 컨테이너 모두 존재",
                        extra={"tag_id": tag_id},
                    ))

            except Exception as e:
                report.results.append(ScanResult(
                    pattern="tag_input",
                    selector=inp_sel,
                    label=label,
                    status="error",
                    detail=str(e),
                ))

    # ── 내부 유틸 ─────────────────────────────

    def _is_known_bug(self, selector: str, test_name: str) -> bool:
        return any(
            bug.get("selector") == selector and bug.get("test_name") == test_name
            for bug in self._known_bugs
        )

    @staticmethod
    def _load_yaml(path: Path) -> Any:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return None
