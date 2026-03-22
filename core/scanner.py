"""
UIScanner — UI 요소 자동 탐지 엔진

동작 순서:
  1. scan_hints (config/scan_hints/*.yaml)  → confidence 1.0  정확, 오탐 없음
  2. HTML 속성 기반                          → confidence 0.9  toggle="" / disabled=""
  3. 탭 전환 (ul#modalTabLayer)              → 각 탭에서 1·2 반복
  4. 중복 제거                               → 같은 selector는 confidence 높은 쪽으로

설계 원칙:
  - ScannedElement는 CSS selector 문자열 보관 (Playwright Locator 미보관)
    → 직렬화 가능, 리포트에 그대로 기록 가능
  - 스캐너는 페이지 상태를 변경하지 않는다 (readonly 원칙)
    단, 탭 전환은 예외 (스캔 완료 후 원래 탭 복원)
  - confidence < 0.5 요소는 결과에서 제외 (노이즈 방지)
"""
from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional

from playwright.sync_api import Page


# ──────────────────────────────────────────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ScannedElement:
    """
    스캐너가 탐지한 UI 요소 하나.

    Attributes:
        pattern_name    : "tag_input" | "checkbox" | "text_input" | "number_input" | ...
        selector        : CSS selector 문자열 (Playwright locator 아님)
        match_method    : "hint" | "attribute" | "heuristic"
        confidence      : 0.0 ~ 1.0 (hint=1.0, attribute=0.9, heuristic<0.8)
        tab_label       : 속한 탭 이름. 탭 없는 요소는 None
        element_info    : 패턴별 추가 정보 (dependent_fields, maxlength 등)
    """
    pattern_name : str
    selector     : str
    match_method : str
    confidence   : float
    tab_label    : Optional[str]
    element_info : dict = field(default_factory=dict)

    def __repr__(self) -> str:
        tab = f" tab={self.tab_label!r}" if self.tab_label else ""
        return (
            f"<{self.pattern_name} [{self.match_method}:{self.confidence:.1f}]"
            f"{tab} {self.selector!r}>"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 스캐너
# ──────────────────────────────────────────────────────────────────────────────

class UIScanner:
    """
    Usage:
        scanner = UIScanner(page, hints_path="config/scan_hints/ransom_detect_policy.yaml")
        elements = scanner.scan(context_selector="div#addItemModal")
        for el in elements:
            print(el)
    """

    # 탭 구조 selector (Bootstrap 3 탭 패턴)
    _SEL_TAB_LINKS = "ul#modalTabLayer li a"

    # HTML 속성 기반 패턴 식별 selector
    _ATTR_TOGGLE      = 'input[type="checkbox"][toggle]'
    _ATTR_TEXT_INPUT  = (
        'input[type="text"]:not([toggle]), '
        'input:not([type]):not([toggle]):not([hidden])'
    )
    _ATTR_NUMBER      = 'input[type="number"]'

    # 탭 전환 후 컨텐츠 안정 대기 (ms)
    _TAB_SETTLE_MS = 300

    # confidence 최저 기준 — 미만은 결과에서 제외
    _MIN_CONFIDENCE = 0.5

    def __init__(self, page: Page, hints_path: Optional[str] = None):
        self.page = page
        self._hints: dict = {}

        if hints_path:
            abs_path = os.path.abspath(hints_path)
            if os.path.exists(abs_path):
                with open(abs_path, encoding="utf-8") as f:
                    self._hints = yaml.safe_load(f) or {}
            else:
                print(f"[UIScanner] hints 파일 없음 (무시): {abs_path}")

    # ── 공개 API ──────────────────────────────────────────────────────────────

    def scan(self, context_selector: str = "body") -> list[ScannedElement]:
        """
        페이지(또는 모달)를 스캔해 탐지된 UI 요소 목록을 반환한다.

        Args:
            context_selector: 스캔 범위를 제한할 CSS selector.
                              전체 페이지면 "body", 특정 모달이면 "div#addItemModal".

        Returns:
            confidence >= _MIN_CONFIDENCE 인 ScannedElement 목록 (중복 제거됨).
        """
        results: list[ScannedElement] = []

        tabs = self._get_tabs()
        if tabs:
            original_tab = tabs[0]  # 스캔 후 첫 번째 탭으로 복원
            for tab_label, tab_selector in tabs:
                self._switch_tab(tab_selector)
                results.extend(self._scan_context(context_selector, tab_label))
            # 원래 탭 복원 (페이지 상태 readonly 원칙)
            self._switch_tab(original_tab[1])
        else:
            results.extend(self._scan_context(context_selector, tab_label=None))

        return self._dedup(results)

    # ── 탭 처리 ───────────────────────────────────────────────────────────────

    def _get_tabs(self) -> list[tuple[str, str]]:
        """
        Bootstrap 3 탭 목록을 반환한다.
        (탭 이름, 탭 링크 CSS selector) 쌍의 리스트.
        탭이 없으면 빈 리스트.
        """
        tabs = []
        try:
            tab_links = self.page.locator(self._SEL_TAB_LINKS).all()
            for i, tab in enumerate(tab_links):
                label = tab.inner_text().strip() or f"탭{i + 1}"
                href  = tab.get_attribute("href") or f"#tab{i}"
                # href 가 "#tabId" 형태 → a[href="#tabId"] 로 재클릭
                selector = f'{self._SEL_TAB_LINKS.rsplit(" a", 1)[0]} a[href="{href}"]'
                tabs.append((label, selector))
        except Exception:
            pass
        return tabs

    def _switch_tab(self, tab_selector: str) -> None:
        try:
            self.page.locator(tab_selector).first.evaluate("el => el.click()")
            self.page.wait_for_timeout(self._TAB_SETTLE_MS)
        except Exception:
            pass

    # ── 컨텍스트 스캔 ─────────────────────────────────────────────────────────

    def _scan_context(
        self,
        context_selector: str,
        tab_label: Optional[str],
    ) -> list[ScannedElement]:
        results: list[ScannedElement] = []
        results.extend(self._scan_hints(tab_label))
        results.extend(self._scan_attributes(context_selector, tab_label))
        return [el for el in results if el.confidence >= self._MIN_CONFIDENCE]

    # ── 1단계: scan_hints 기반 (confidence 1.0) ───────────────────────────────

    def _scan_hints(self, tab_label: Optional[str]) -> list[ScannedElement]:
        """
        config/scan_hints/*.yaml 에서 읽은 힌트로 요소를 탐지한다.
        힌트에 정의된 primary selector 가 페이지에 존재하면 신뢰도 1.0.
        """
        results = []
        for pattern_name, hint in self._hints.items():
            if not isinstance(hint, dict):
                continue

            # 우선순위: container > input > selector 순으로 primary selector 결정
            primary = (
                hint.get("container")
                or hint.get("input")
                or hint.get("selector")
            )
            if not primary:
                continue

            try:
                exists = self.page.locator(primary).count() > 0
            except Exception:
                exists = False

            if not exists:
                continue

            results.append(ScannedElement(
                pattern_name=pattern_name,
                selector=primary,
                match_method="hint",
                confidence=1.0,
                tab_label=tab_label,
                element_info=dict(hint),   # hint 전체 보존 (add_btn 등 validator가 사용)
            ))

        return results

    # ── 2단계: HTML 속성 기반 (confidence 0.8~0.9) ────────────────────────────

    def _scan_attributes(
        self,
        context_selector: str,
        tab_label: Optional[str],
    ) -> list[ScannedElement]:
        results: list[ScannedElement] = []
        results.extend(self._detect_toggles(context_selector, tab_label))
        results.extend(self._detect_text_inputs(context_selector, tab_label))
        results.extend(self._detect_number_inputs(context_selector, tab_label))
        return results

    # ── toggle="" 속성으로 토글 체크박스 탐지 ────────────────────────────────

    def _detect_toggles(
        self,
        context: str,
        tab_label: Optional[str],
    ) -> list[ScannedElement]:
        """
        toggle="" 속성이 있는 checkbox → "checkbox" 패턴.
        DOM 트리 탐색으로 disabled 종속 필드를 자동 매핑.
        """
        results = []
        try:
            toggles = self.page.locator(
                f"{context} {self._ATTR_TOGGLE}"
            ).all()
        except Exception:
            return results

        for cb in toggles:
            try:
                cb_id    = cb.get_attribute("id") or ""
                selector = f"input#{cb_id}" if cb_id else self._ATTR_TOGGLE
                dependent = self._find_dependent_fields(cb)

                results.append(ScannedElement(
                    pattern_name="checkbox",
                    selector=selector,
                    match_method="attribute",
                    confidence=0.9,
                    tab_label=tab_label,
                    element_info={
                        "id"              : cb_id,
                        "is_checked"      : cb.is_checked(),
                        "has_toggle_attr" : True,
                        "dependent_fields": dependent,
                    },
                ))
            except Exception:
                continue

        return results

    def _find_dependent_fields(self, toggle_locator) -> list[str]:
        """
        toggle과 같은 컨테이너(tr / section / .form-group)에서
        disabled 또는 ng-disabled 속성을 가진 input의 id 목록을 반환.

        HTML 분석으로 확인된 패턴:
          - 종속 필드는 toggle과 같은 tr/section 블록 내에 위치
          - 비활성 상태일 때 disabled="" 속성이 명시됨
        """
        try:
            result = toggle_locator.evaluate("""el => {
                // 공통 조상 탐색: tr → section → .form-group → 부모 2단계
                const ancestors = ['tr', 'section', '.form-group', '.option-wrap', '.control-group'];
                let ancestor = null;
                for (const sel of ancestors) {
                    ancestor = el.closest(sel);
                    if (ancestor) break;
                }
                if (!ancestor) {
                    ancestor = el.parentElement && el.parentElement.parentElement;
                }
                if (!ancestor) return [];

                // ancestor 내에서 disabled 또는 ng-disabled 속성을 가진 input 수집
                // toggle 자신은 제외
                return Array.from(
                    ancestor.querySelectorAll(
                        'input[disabled], input[ng-disabled], textarea[disabled]'
                    )
                )
                .filter(inp => inp !== el)
                .map(inp => inp.id || inp.getAttribute('ng-model') || inp.name || '');
            }""")
            return [r for r in (result or []) if r]
        except Exception:
            return []

    # ── text_input 탐지 ───────────────────────────────────────────────────────

    def _detect_text_inputs(
        self,
        context: str,
        tab_label: Optional[str],
    ) -> list[ScannedElement]:
        results = []
        try:
            inputs = self.page.locator(
                f"{context} {self._ATTR_TEXT_INPUT}"
            ).all()
        except Exception:
            return results

        for inp in inputs:
            try:
                inp_id   = inp.get_attribute("id") or ""
                selector = f"input#{inp_id}" if inp_id else 'input[type="text"]'
                maxlen   = inp.get_attribute("maxlength")

                results.append(ScannedElement(
                    pattern_name="text_input",
                    selector=selector,
                    match_method="attribute",
                    confidence=0.8,
                    tab_label=tab_label,
                    element_info={
                        "id"       : inp_id,
                        "maxlength": int(maxlen) if maxlen else None,
                        "required" : inp.get_attribute("required") is not None,
                        "ng_model" : inp.get_attribute("ng-model") or "",
                    },
                ))
            except Exception:
                continue

        return results

    # ── number_input 탐지 ─────────────────────────────────────────────────────

    def _detect_number_inputs(
        self,
        context: str,
        tab_label: Optional[str],
    ) -> list[ScannedElement]:
        results = []
        try:
            inputs = self.page.locator(
                f"{context} {self._ATTR_NUMBER}"
            ).all()
        except Exception:
            return results

        for inp in inputs:
            try:
                inp_id   = inp.get_attribute("id") or ""
                selector = f"input#{inp_id}" if inp_id else 'input[type="number"]'

                results.append(ScannedElement(
                    pattern_name="number_input",
                    selector=selector,
                    match_method="attribute",
                    confidence=0.9,
                    tab_label=tab_label,
                    element_info={
                        "id"  : inp_id,
                        "min" : inp.get_attribute("min"),
                        "max" : inp.get_attribute("max"),
                        "step": inp.get_attribute("step"),
                    },
                ))
            except Exception:
                continue

        return results

    # ── 중복 제거 ─────────────────────────────────────────────────────────────

    def _dedup(self, elements: list[ScannedElement]) -> list[ScannedElement]:
        """
        같은 selector가 여러 방법으로 탐지된 경우 confidence 높은 것만 유지.
        힌트(1.0) > 속성(0.9) > 휴리스틱(< 0.8)
        """
        seen: dict[str, ScannedElement] = {}
        for el in elements:
            key = el.selector
            if key not in seen or el.confidence > seen[key].confidence:
                seen[key] = el
        return list(seen.values())

    # ── 결과 출력 헬퍼 ────────────────────────────────────────────────────────

    def print_summary(self, elements: list[ScannedElement]) -> None:
        """스캔 결과 요약을 터미널에 출력한다."""
        print(f"\n{'─' * 60}")
        print(f"  UIScanner 결과 — 총 {len(elements)}개 요소 탐지")
        print(f"{'─' * 60}")

        by_pattern: dict[str, list[ScannedElement]] = {}
        for el in elements:
            by_pattern.setdefault(el.pattern_name, []).append(el)

        for pattern, els in sorted(by_pattern.items()):
            print(f"\n  [{pattern}] {len(els)}개")
            for el in els:
                tab_info = f"(탭: {el.tab_label})" if el.tab_label else ""
                dep = el.element_info.get("dependent_fields", [])
                dep_info = f" → 종속필드: {dep}" if dep else ""
                print(f"    {el.selector:<45} [{el.match_method}:{el.confidence:.1f}] {tab_info}{dep_info}")

        print(f"\n{'─' * 60}\n")
