# 구현 명세서 — Universal Page Scanner

작성일: 2026-03-25
참조: `01_qa_analysis.md`, `02_dev_analysis.md`

이 문서는 QA + 개발자 분석을 통합한 최종 구현 명세다.
플랜 파일에서 이 문서를 참조해 실제 코드를 작성한다.

---

## 0. 전제 조건 (변경 없음)

- `core/ui_scanner.py` — 그대로 유지
- `validators/` — 그대로 유지
- `config/scan_hints/*.yaml` — 그대로 유지
- `conftest.py` — 그대로 유지

---

## 1. `pages/base_page.py` 수정 내용

기존 파일 **하단**에 3개 메서드 추가. 기존 코드 변경 없음.

```python
# pages/base_page.py 하단 추가 (──────────────── 섹션 뒤에 삽입)

# ------------------------------------------------------------------
# Universal Scanner 표준 인터페이스
# ------------------------------------------------------------------

def save_policy(self, name: str) -> None:
    """
    Phase 1/2 완료 후 정책 저장.
    서브클래스에서 반드시 override — 미구현 시 RuntimeError.
    """
    raise NotImplementedError(
        f"{self.__class__.__name__}.save_policy() 미구현. "
        "pages/base_page.py 상단 주석 참고."
    )

def close_edit_modal(self) -> None:
    """
    Phase 3 EDIT 모달 닫기.
    서브클래스에서 override. 기본: pass (모달 없으면 아무것도 안 함).
    """
    pass

def get_verify_values(self, saved_name: str) -> dict:
    """
    Phase 3 로드값 검증용 dict 반환.
    기본: 빈 dict (검증 생략).
    서브클래스에서 override하면 EDIT 모달 로드 후 필드값 일치 확인.
    반환 형식: {"selector": "기대값", ...}
    예: {"input#rcRdpPolicyName": saved_name}
    """
    return {}
```

---

## 2. `pages/ransom_detect_policy_page.py` 수정 내용

기존 `open_add_modal()` 메서드 **아래**에 추가. 기존 코드 변경 없음.

```python
# ------------------------------------------------------------------
# AUTO_NAME_PREFIX — maxlength=20 제약 대응 (QA 분석 2.4)
# ------------------------------------------------------------------
AUTO_NAME_PREFIX = "[AUTO]_det"   # 10자 — _p1/_p2 추가 시 최대 13자

# ------------------------------------------------------------------
# Universal Scanner 표준 인터페이스 구현
# ------------------------------------------------------------------

def save_policy(self, name: str) -> None:
    """Phase 1/2 완료 후 정책 저장 (이름 + 확장자 필수)."""
    self.fill(self.SEL_POLICY_NAME, name)
    if self.page.locator("i.extentionDeleteBtn").count() == 0:
        self.fill(self.SEL_EXTENSION_INPUT, "txt")
        self.click(self.SEL_EXTENSION_ADD_BTN)
        self.page.wait_for_timeout(300)
    self.click(self.SEL_REGISTER_BTN)
    self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
        state="attached", timeout=self._TIMEOUT_MODAL
    )
    self.click_attached(self.SEL_CONFIRM_BTN)
    self.wait_for_modal_closed()
    self.wait_for(self.SEL_ADD_BTN)

def close_edit_modal(self) -> None:
    """Phase 3 EDIT 모달 닫기 — known_bug로 이미 닫혔을 수 있으므로 조건부."""
    try:
        if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
            self.close_modal()
        else:
            self.wait_for(self.SEL_ADD_BTN)
    except Exception:
        pass

def get_verify_values(self, saved_name: str) -> dict:
    """Phase 3: EDIT 모달 로드 후 정책 이름 필드 값 확인."""
    return {"input#rcDetectPolicyName": saved_name}
```

---

## 3. `pages/rdp_policy_page.py` 수정 내용

기존 `open_add_modal()` 메서드 **아래**에 추가.

```python
# ------------------------------------------------------------------
# AUTO_NAME_PREFIX — 이름 길이 일관성 (QA 분석 2.4)
# ------------------------------------------------------------------
AUTO_NAME_PREFIX = "[AUTO]_rdp"   # 10자 — _p1/_p2 추가 시 최대 13자

# ------------------------------------------------------------------
# Universal Scanner 표준 인터페이스 구현
# ------------------------------------------------------------------

def save_policy(self, name: str) -> None:
    """Phase 1/2 완료 후 정책 저장 (이름만 필수)."""
    self.fill(self.SEL_POLICY_NAME, name)
    self.click_attached(self.SEL_REGISTER_BTN)
    self.page.locator(self.SEL_CONFIRM_MODAL_OPENED).wait_for(
        state="attached", timeout=self._TIMEOUT_MODAL
    )
    self.click_attached(self.SEL_CONFIRM_BTN)
    self.wait_for_modal_closed()
    self.wait_for(self.SEL_ADD_BTN)

def close_edit_modal(self) -> None:
    """Phase 3 EDIT 모달 닫기 — 조건부."""
    try:
        if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
            self.close_modal()
        else:
            self.wait_for(self.SEL_ADD_BTN)
    except Exception:
        pass

def get_verify_values(self, saved_name: str) -> dict:
    """Phase 3: EDIT 모달 로드 후 정책 이름 필드 값 확인."""
    return {"input#rcRdpPolicyName": saved_name}
```

---

## 4. `pages/registry.py` 신규 생성

```python
"""
pages/registry.py — page_id → PageClass 매핑

새 페이지 추가 시 이 파일에 1줄만 추가:
    "new_page_id": NewPageClass,
"""
from pages.ransom_detect_policy_page import RansomDetectPolicyPage
from pages.rdp_policy_page            import RdpPolicyPage

PAGE_REGISTRY: dict[str, type] = {
    "ransom_detect_policy": RansomDetectPolicyPage,
    "rdp_policy":           RdpPolicyPage,
}
```

---

## 5. `core/reporter.py` 신규 생성

두 기존 테스트 파일의 `_print_phase_report()` 코드가 완전히 동일하므로 단순 추출.

```python
"""
core/reporter.py — 스캔 결과 출력 공통 함수

_print_phase_report(), print_combined_report() 공통화.
test 파일마다 중복 정의되던 코드를 한 곳으로 통합.
"""
from __future__ import annotations
from core.models import PageScanReport, ScanResult

_PHASE_LABEL = {
    1: "Phase 1 (초기값+필수입력)",
    2: "Phase 2 (UI 동작)",
    3: "Phase 3 (수정)",
}

_STATUS_ICON = {
    "pass":      "✅",
    "fail":      "❌",
    "known_bug": "⚠️",
    "skip":      "⏭",
    "error":     "💥",
}

_PATTERN_FALLBACK = {
    "initial_state":   0,
    "modal_open":      1,
    "text_input":      2,
    "radio_group":     3,
    "toggle_checkbox": 4,
    "plain_checkbox":  5,
    "tag_input":       6,
    "button_action":   7,
    "required_submit": 8,
    "auto_detect":     9,
}


def print_phase_report(report: PageScanReport | None, phase: int) -> None:
    """페이즈별 스캔 결과 출력 — order 정렬 + 탭 헤더 + toggle dep 트리 + required 역색인."""
    if report is None:
        print(f"\n[{_PHASE_LABEL.get(phase, f'Phase {phase}')}] 결과 없음")
        return

    print(f"\n{'═' * 60}")
    print(f"  {_PHASE_LABEL.get(phase, f'Phase {phase}')}")
    print(f"{'═' * 60}")
    print(f"  {report.summary()}")

    def _sort_key(r):
        if r.order is not None:
            return r.order
        return 10_000 + _PATTERN_FALLBACK.get(r.pattern, 99) * 10

    def _tab_for_order(order):
        if order is None or not report.tab_sections:
            return None
        current = None
        for ts in report.tab_sections:
            if order >= ts["start_order"]:
                current = ts["label"]
        return current

    def _field_id(r) -> str:
        if r.pattern == "tag_input":
            return r.extra.get("tag_id", "")
        if "#" in r.selector:
            return r.selector.split("#")[-1]
        return ""

    # required_submit → missing_field 역색인
    req_map: dict[str, list] = {}
    shown_req: set[int] = set()
    for r in report.results:
        if r.pattern == "required_submit":
            mf = r.extra.get("missing_field", "")
            if mf:
                req_map.setdefault(mf, []).append(r)

    field_ids_in_report: set[str] = set()
    for r in report.results:
        fid = _field_id(r)
        if fid:
            field_ids_in_report.add(fid)

    sorted_results    = sorted(report.results, key=_sort_key)
    current_tab_label = None

    for r in sorted_results:
        if r.pattern != "required_submit":
            tab_label = _tab_for_order(r.order)
            if tab_label != current_tab_label:
                current_tab_label = tab_label
                if current_tab_label:
                    bar = "─" * 14
                    print(f"\n  {bar} [ {current_tab_label} ] {bar}")

        if r.pattern == "required_submit" and id(r) in shown_req:
            continue

        if r.pattern == "required_submit":
            mf  = r.extra.get("missing_field", "")
            mfl = r.extra.get("missing_field_label", "")
            if mf and mfl and mf not in field_ids_in_report:
                req_icon = _STATUS_ICON.get(r.status, "?")
                print(f"  {req_icon} [{mfl}] 미입력 경고: {r.detail}")
                shown_req.add(id(r))
                continue

        icon = _STATUS_ICON.get(r.status, "?")
        print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")

        # toggle dep 트리 (CLAUDE.md 필수 요건)
        if r.pattern == "toggle_checkbox":
            dep_labels  = r.extra.get("dependent_labels",  [])
            dep_types   = r.extra.get("dependent_types",   [])
            dep_results = r.extra.get("dependent_results", [])
            for i, dep_label in enumerate(dep_labels):
                dep_type   = dep_types[i]   if i < len(dep_types)   else "field"
                dep_res    = dep_results[i]  if i < len(dep_results) else {}
                dep_status = dep_res.get("status", "skip")
                dep_icon   = _STATUS_ICON.get(dep_status, "?")
                dep_detail = dep_res.get("detail", "")
                detail_str = f" — {dep_detail}" if dep_detail else ""
                print(f"       └ {dep_icon} [{dep_type}] {dep_label}{detail_str}")

        fid = _field_id(r)
        if fid and fid in req_map:
            for req_r in req_map[fid]:
                req_icon = _STATUS_ICON.get(req_r.status, "?")
                print(f"       └ {req_icon} [required] 미입력 경고: {req_r.detail}")
                shown_req.add(id(req_r))


def print_combined_report(combined: PageScanReport) -> None:
    """전체 결과 요약 + known_bug 추적 섹션 출력."""
    print(f"\n{'═' * 60}")
    print(f"  전체 결과: {combined.summary()}")
    print(f"{'═' * 60}")

    if combined.known_bugs:
        print(f"\n{'─' * 60}")
        print(f"  ⚠️  추적 중인 결함 {len(combined.known_bugs)}건 — 수정 필요 (fail 카운트 제외)")
        print(f"{'─' * 60}")
        for r in combined.known_bugs:
            phase_tag = f"[Phase {r.phase}]" if r.phase else ""
            print(f"  ⚠️  {phase_tag}[{r.pattern}] {r.label}")
            print(f"       → {r.detail}")
        print(f"{'─' * 60}")
        print(f"  💡 known_bugs.yaml 에서 status: open → fixed 로 변경 시 회귀 감지 활성화")
        print(f"{'─' * 60}\n")
```

---

## 6. `core/qa_runner.py` 신규 생성

QA 분석 이슈를 반영한 최종 구현:

```python
"""
core/qa_runner.py — 3-Phase 범용 QA 스캔 오케스트레이터

page_id → PageClass(registry) → 3-Phase scan → PageScanReport 반환.
테스트 파일에서 직접 Phase 코드를 작성할 필요 없음.

새 페이지 추가 시:
  1. config/scan_hints/new_page.yaml
  2. pages/new_page.py (save_policy, close_edit_modal, get_verify_values 구현)
  3. pages/registry.py에 1줄 추가
  → tests/test_scan_pages.py 자동 실행
"""
from __future__ import annotations
from core.ui_scanner import UIScanner
from core.models     import PageScanReport
from core.reporter   import print_phase_report, print_combined_report
from pages.registry  import PAGE_REGISTRY


def run_3phase_scan(
    playwright_page,
    settings: dict,
    page_id: str,
) -> PageScanReport:
    """
    page_id에 해당하는 페이지를 3-Phase로 스캔하고 결과를 출력.

    반환: 전체 PageScanReport (테스트 파일에서 assert에 사용)
    """
    if page_id not in PAGE_REGISTRY:
        raise ValueError(f"PAGE_REGISTRY에 등록되지 않은 page_id: {page_id!r}")

    PageClass = PAGE_REGISTRY[page_id]
    page_obj  = PageClass(playwright_page, settings)
    page_obj.navigate_to()
    page_obj.delete_all_auto_policies()

    config_dir = settings.get("config_dir", "config")
    scanner    = UIScanner(playwright_page, config_dir=config_dir)

    # ── 이름 생성 — AUTO_NAME_PREFIX 우선, 없으면 page_id 6자 약어 (QA 2.4)
    prefix  = getattr(page_obj, "AUTO_NAME_PREFIX", f"[AUTO]_{page_id[:6]}")
    p1_name = f"{prefix}_p1"
    p2_name = f"{prefix}_p2"

    # ─────────────────────────────────────────────────────────────
    # Phase 1: 초기값 스냅샷 + 필수입력 검증
    # ─────────────────────────────────────────────────────────────
    p1_saved = False
    def close_phase1():
        nonlocal p1_saved
        page_obj.save_policy(p1_name)
        p1_saved = True

    report1 = scanner.scan(
        page_id, phase=1,
        modal_open_fn=page_obj.open_add_modal,
        modal_close_fn=close_phase1,
    )
    print_phase_report(report1, 1)

    # ─────────────────────────────────────────────────────────────
    # Phase 2: UI 요소 동작 검증
    # ─────────────────────────────────────────────────────────────
    p2_saved = False
    def close_phase2():
        nonlocal p2_saved
        page_obj.save_policy(p2_name)
        p2_saved = True

    context2: dict = {}
    if p1_saved:
        context2["existing_name"] = p1_name
    else:
        print(f"  ⏭ [Phase 2] existing_name 스킵 — Phase 1 저장 실패")

    report2 = scanner.scan(
        page_id, phase=2,
        modal_open_fn=page_obj.open_add_modal,
        modal_close_fn=close_phase2,
        context_extra=context2,
    )
    print_phase_report(report2, 2)

    # ─────────────────────────────────────────────────────────────
    # Phase 3: 수정 시나리오 검증
    # ─────────────────────────────────────────────────────────────
    report3: PageScanReport | None = None

    if not p2_saved:
        print(f"  ⏭ [Phase 3] 스킵 — Phase 2 저장 실패 (p2 정책 없음)")
    else:
        try:
            report3 = scanner.scan(
                page_id, phase=3,
                modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
                modal_close_fn=page_obj.close_edit_modal,
                context_extra={"verify_values": page_obj.get_verify_values(p2_name)},
            )
            print_phase_report(report3, 3)
        except Exception as e:
            print(f"  💥 [Phase 3] 실행 중 예외: {e}")
        finally:
            try:
                page_obj.navigate_to()
                page_obj.delete_all_auto_policies()
            except Exception as e:
                print(f"\n  ⚠️  [{page_id}] 정리 실패 — 잔여 [AUTO] 정책이 남아있을 수 있습니다: {e}")

    if report3 is None and p2_saved:
        print(f"  ⏭ [Phase 3] 실행되지 않음")

    # ─────────────────────────────────────────────────────────────
    # 결합 리포트
    # ─────────────────────────────────────────────────────────────
    reports = [r for r in (report1, report2, report3) if r is not None]
    if not reports:
        raise RuntimeError(f"[{page_id}] 스캔 결과 없음 — 모든 Phase 실패")

    combined = PageScanReport.merge(*reports)
    print_combined_report(combined)
    return combined
```

---

## 7. `tests/test_scan_pages.py` 신규 생성

```python
"""
tests/test_scan_pages.py — 범용 페이지 스캔 테스트

새 페이지 추가 시:
  1. config/scan_hints/new_page.yaml 작성
  2. pages/new_page.py 작성 (save_policy, close_edit_modal, get_verify_values, AUTO_NAME_PREFIX)
  3. pages/registry.py 에 page_id → PageClass 한 줄 추가
  이것으로 끝. 이 파일은 수정 불필요.

실행:
  pytest tests/test_scan_pages.py -v -s                 # 전체 등록 페이지
  pytest tests/test_scan_pages.py -v -s -k ransom       # 특정 페이지
  pytest tests/test_scan_pages.py -v -s -k rdp_policy
"""
import pytest
from core.qa_runner  import run_3phase_scan
from pages.registry  import PAGE_REGISTRY


@pytest.mark.ui_scan
@pytest.mark.parametrize("page_id", list(PAGE_REGISTRY.keys()))
def test_page_scan(logged_in_page, settings, request, page_id):
    """범용 3-Phase 스캔 테스트. page_id별로 parametrize 실행."""
    combined = run_3phase_scan(logged_in_page, settings, page_id)
    request.node._scan_report = combined

    assert not combined.failed, (
        f"[{page_id}] UI 패턴 검사 실패 {len(combined.failed)}건:\n"
        + "\n".join(
            f"  [Phase {r.phase}][{r.pattern}] {r.label}: {r.detail}"
            for r in combined.failed
        )
    )
```

---

## 8. 기존 테스트 파일 처리

**권고:** `tests/archive/` 폴더 이동 (pytest가 자동 수집하지 않는 위치).

```
tests/
  archive/
    test_ransom_detect_policy_scan.py   ← 이동
    test_rdp_policy_scan.py             ← 이동
  test_scan_pages.py                    ← 신규
  conftest.py                           ← 그대로
```

**이동 이유:**
- `pytest tests/` 실행 시 동일 페이지가 두 번 테스트됨 (중복 + 충돌)
- archive로 이동하면 필요 시 수동 실행 가능 (참조용 보존)

---

## 9. 검증 방법

### 9.1 기능 동일성 확인

```bash
# 신규 범용 테스트
pytest tests/test_scan_pages.py -v -s -k ransom
# 기대: pass=50, known_bug=3, fail=0 (기존과 동일)

pytest tests/test_scan_pages.py -v -s -k rdp_policy
# 기대: pass=61, known_bug=3, fail=0 (기존과 동일)
```

### 9.2 전체 실행

```bash
pytest tests/test_scan_pages.py -v -s
# 두 페이지 순서대로 실행 확인
# [ransom_detect_policy] → [rdp_policy] 순
```

### 9.3 Phase 1 저장 실패 시뮬레이션

`save_policy()`에서 일시적으로 Exception 발생 → Phase 2 `existing_name` 스킵 메시지 출력 확인.

### 9.4 새 페이지 추가 E2E

```
1. config/scan_hints/test_dummy.yaml 최소 작성
2. pages/test_dummy_page.py 작성 (AUTO_NAME_PREFIX, save_policy 등)
3. pages/registry.py에 "test_dummy": TestDummyPage 추가
4. pytest tests/test_scan_pages.py -v -s -k test_dummy
```

---

## 10. 구현 순서 (권고)

1. `pages/base_page.py` — 3개 메서드 서명 추가
2. `pages/ransom_detect_policy_page.py` — 구현 추가
3. `pages/rdp_policy_page.py` — 구현 추가
4. `pages/registry.py` — 신규 생성
5. `core/reporter.py` — 신규 생성
6. `core/qa_runner.py` — 신규 생성
7. `tests/test_scan_pages.py` — 신규 생성
8. 기존 테스트 파일 `tests/archive/` 이동
9. 검증 (9.1 → 9.2 순서)
