"""
core/models.py — 스캔 결과 데이터 클래스

ScanResult, PageScanReport를 여기서 정의한다.
core/ui_scanner.py 와 validators/ 모두 이 파일을 공유한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScanResult:
    """
    스캐너가 검사한 UI 요소 하나의 결과.

    Attributes:
        pattern  : "initial_state" | "toggle_checkbox" | "plain_checkbox" | "radio_group" |
                   "text_input" | "tag_input" | "required_submit" | "button_action" |
                   "auto_detect" | "modal_open"
        selector : CSS selector 문자열
        label    : 사람이 읽을 수 있는 설명
        status   : "pass" | "fail" | "warn" | "skip" | "error"
        detail   : 결과 상세 메시지
        extra    : 패턴별 추가 정보 (dependent_fields, tag_id 등)
        order    : scan_hints yaml의 order 값 — 출력 정렬 기준 (None이면 패턴 타입 순)
        phase    : 스캔 페이즈 (1=초기값+필수입력, 2=UI동작, 3=수정, 0=전체)
    """
    pattern:  str
    selector: str
    label:    str
    status:   str
    detail:   str           = ""
    extra:    dict          = field(default_factory=dict)
    order:    Optional[int] = None
    phase:    int           = 0

    def is_real_failure(self) -> bool:
        """fail 만 실패 카운트에 포함 (pytest FAIL 기준)."""
        return self.status == "fail"


@dataclass
class PageScanReport:
    """페이지 하나의 전체 스캔 결과."""
    page_id:      str
    results:      list[ScanResult] = field(default_factory=list)
    tab_sections: list[dict]       = field(default_factory=list)
    # tab_sections: [{"label": str, "start_order": int}, ...] — start_order 오름차순

    @property
    def passed(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "pass"]

    @property
    def failed(self) -> list[ScanResult]:
        return [r for r in self.results if r.is_real_failure()]

    @property
    def warnings(self) -> list[ScanResult]:
        """버그 (낮음) — warn 상태 항목."""
        return [r for r in self.results if r.status in ("warn", "known_bug")]

    @property
    def known_bugs(self) -> list[ScanResult]:
        """하위 호환용 alias → warnings 와 동일."""
        return self.warnings

    @property
    def errors(self) -> list[ScanResult]:
        return [r for r in self.results if r.status == "error"]

    def summary(self) -> str:
        return (
            f"[{self.page_id}] "
            f"pass={len(self.passed)} "
            f"fail={len(self.failed)} "
            f"warn={len(self.warnings)} "
            f"error={len(self.errors)}"
        )

    @classmethod
    def merge(cls, *reports: "PageScanReport") -> "PageScanReport":
        """여러 페이즈의 결과를 하나의 리포트로 합산한다."""
        if not reports:
            return cls(page_id="")
        merged = cls(page_id=reports[0].page_id)
        for r in reports:
            merged.results.extend(r.results)
            merged.tab_sections.extend(r.tab_sections)
        return merged
