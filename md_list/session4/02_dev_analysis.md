# 개발자 관점 분석 — Universal Page Scanner

작성일: 2026-03-25
대상 플랜: `C:\Users\D.K.Kim\.claude\plans\generic-drifting-cook.md`

---

## 1. 아키텍처 문제

### 1.1 `BasePage`에 `close_edit_modal()` 기본 구현 불가

**계획 내용:**
```python
# pages/base_page.py
def close_edit_modal(self) -> None:
    try:
        if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
            self.close_modal()
        else:
            self.wait_for(self.SEL_ADD_BTN)
    except Exception:
        pass
```

**문제:**
- `BasePage`에는 `SEL_ADD_MODAL`, `SEL_ADD_BTN`, `close_modal()` 없음
- 이 상수들은 각 서브클래스(RdpPolicyPage, RansomDetectPolicyPage)에만 정의됨
- `BasePage`에 구현하면 AttributeError 발생

**현재 `BasePage` 메서드 목록:**
- `navigate()`, `click()`, `click_attached()`, `fill()`, `wait_for()`, `wait_for_enabled()`
- `is_visible()`, `take_screenshot()`
- `_toggle_overlay()`, `_on_error()`

**권고:**
`BasePage`에는 추상 메서드(NotImplementedError) 또는 아무것도 없이 두고,
각 Page 클래스에서 `_close_modal_if_open()` 등 이미 있는 메서드를 활용해 직접 구현:

```python
# pages/base_page.py — 서명만 정의
def save_policy(self, name: str) -> None:
    raise NotImplementedError(f"{self.__class__.__name__}.save_policy() 미구현")

def close_edit_modal(self) -> None:
    raise NotImplementedError(f"{self.__class__.__name__}.close_edit_modal() 미구현")

def get_verify_values(self, saved_name: str) -> dict:
    return {}   # 기본값 빈 dict — 검증 생략
```

```python
# pages/rdp_policy_page.py — 실제 구현
def close_edit_modal(self) -> None:
    try:
        if self.page.locator(self.SEL_ADD_MODAL).count() > 0:
            self.close_modal()
        else:
            self.wait_for(self.SEL_ADD_BTN)
    except Exception:
        pass
```

---

### 1.2 `request` pytest fixture를 `qa_runner.py`가 받을 수 없음

**계획 내용:**
```python
# tests/test_scan_pages.py
def test_page_scan(logged_in_page, settings, request, page_id):
    combined = run_3phase_scan(logged_in_page, settings, page_id)
    request.node._scan_report = combined   # ← pytest request 필요
```

**현재 qa_runner.py 계획:**
```python
def run_3phase_scan(playwright_page, settings, page_id) -> PageScanReport:
    ...
    # request.node._scan_report 설정 불가
```

**분석:** `request`는 pytest fixture — 일반 함수에 주입 불가. test 파일에서만 접근 가능.

**권고:** `run_3phase_scan()`은 `PageScanReport`만 반환. `request.node._scan_report` 설정은 테스트 함수에서 직접:

```python
# tests/test_scan_pages.py
def test_page_scan(logged_in_page, settings, request, page_id):
    combined = run_3phase_scan(logged_in_page, settings, page_id)
    request.node._scan_report = combined   # ← 여기서만 처리
    assert not combined.failed, ...
```

이 구조는 현재 계획과 동일. 문제없음. 단, `run_3phase_scan()` 내부에서 `request`가 필요한 로직이 있어선 안 됨.

---

### 1.3 `config_dir` 하드코딩

**계획 내용:**
```python
# core/qa_runner.py
scanner = UIScanner(playwright_page, config_dir="config")
```

**문제:**
- `pytest`를 어느 디렉토리에서 실행하느냐에 따라 `config` 경로가 달라짐
- 현재 `conftest.py`나 `settings.yaml`에서 경로 관리 방식 확인 필요

**현재 `UIScanner` 생성 방식 (기존 테스트 파일):**
```python
scanner = UIScanner(logged_in_page, config_dir="config")
```
기존 테스트도 동일하게 하드코딩 → qa_runner도 동일하게 맞추면 됨.

**권고:** `settings` dict에 `config_dir` 키 추가 또는 파라미터화:
```python
def run_3phase_scan(playwright_page, settings, page_id):
    config_dir = settings.get("config_dir", "config")
    scanner = UIScanner(playwright_page, config_dir=config_dir)
```

---

### 1.4 기존 테스트 파일과 `test_scan_pages.py` 중복 실행 문제

**현재 상황:**
- `tests/test_ransom_detect_policy_scan.py` — 기존 파일 (유지 예정)
- `tests/test_rdp_policy_scan.py` — 기존 파일 (유지 예정)
- `tests/test_scan_pages.py` — 신규 (ransom_detect_policy + rdp_policy parametrize)

**문제:**
```
pytest tests/ -m ui_scan
```
실행 시 두 파일 모두 실행 → **같은 정책을 두 번 생성/삭제** → 충돌 가능성.

**구체적 시나리오:**
1. `test_scan_pages.py::test_page_scan[ransom_detect_policy]` 실행 중
2. `[AUTO]_ransom_detect_policy_p1` 생성
3. 동시에(또는 직후) `test_ransom_detect_policy_scan.py::test_detect_scenario_qa` 실행
4. 같은 이름 정책 충돌 or 정리 타이밍 충돌

**권고 옵션:**

**옵션 A (권고):** 기존 테스트 파일을 `tests/archive/` 이동:
```
tests/
  archive/
    test_ransom_detect_policy_scan.py   ← 이동 (pytest 자동 수집 제외)
    test_rdp_policy_scan.py
  test_scan_pages.py                    ← 신규 범용 테스트
```

**옵션 B:** 기존 파일에 `@pytest.mark.skip` 추가:
```python
@pytest.mark.skip(reason="test_scan_pages.py로 대체됨")
class TestRansomDetectPolicyScan:
    ...
```

**옵션 C:** `conftest.py`에서 marker로 분리:
```
pytest tests/ -m "ui_scan and not legacy"  # 신규만
pytest tests/ -m "legacy"                  # 구버전만
```

---

### 1.5 `save_policy()` 호출 시 확장자 필드 의존성 (ransom_detect_policy)

**현재 기존 코드 (close_phase1/2):**
```python
def close_phase1():
    page_obj.fill(page_obj.SEL_POLICY_NAME, p1_name)
    if page_obj.page.locator("i.extentionDeleteBtn").count() == 0:
        page_obj.fill(page_obj.SEL_EXTENSION_INPUT, "txt")
        page_obj.click(page_obj.SEL_EXTENSION_ADD_BTN)
        page_obj.page.wait_for_timeout(300)
    page_obj.click(page_obj.SEL_REGISTER_BTN)
    ...
```

**계획의 `save_policy(name)` 구현:**
```python
def save_policy(self, name: str) -> None:
    self.fill(self.SEL_POLICY_NAME, name)
    if self.page.locator("i.extentionDeleteBtn").count() == 0:
        self.fill(self.SEL_EXTENSION_INPUT, "txt")
        ...
```

**문제:** `"i.extentionDeleteBtn"` 하드코딩. 기존 코드와 동일하게 가져오면 됨.
→ **이 부분은 문제없음**, 그대로 이전하면 됨.

**단, 주의사항:** `save_policy()`가 Page 클래스 내부에서 완결되므로,
기존 `close_phase1()` 내 `page_obj.wait_for(page_obj.SEL_ADD_BTN)` 호출 누락 여부 확인.

---

### 1.6 `open_modify_modal()` 내부에서 `_fail_if_modal()` 호출

**현재 `RdpPolicyPage.open_modify_modal()`:**
```python
def open_modify_modal(self, policy_name: str) -> None:
    self.click_policy_row(policy_name)
    self.click(self.SEL_MODIFY_BTN)
    self._fail_if_modal(self._TIMEOUT_MODAL)   # ← 예상치 못한 모달 발생 시 Exception
    try:
        self.wait_for(self.SEL_ADD_MODAL, state="attached")
    except Exception as e:
        raise Exception(f"정책 수정 모달이 열리지 않음: {e}") from e
```

**qa_runner.py에서:**
```python
modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
```

Phase 2 저장 실패로 p2_name 정책이 없으면 → `click_policy_row(p2_name)` → 행 없음 → Exception.

→ **2.3 (QA 분석)과 동일 이슈** — Phase 2 성공 여부 추적 필요.

---

### 1.7 `PageScanReport.merge()` 빈 인자 처리

**현재 계획:**
```python
reports = [r for r in (report1, report2, report3) if r is not None]
combined = PageScanReport.merge(*reports)
```

`report1`도 None일 수 있는가? (Phase 1 전체 예외 시)

**`PageScanReport.merge()`가 0개 인자를 받으면?** → `models.py` 확인 필요.

**권고:** 최소 1개 보장:
```python
if not reports:
    raise RuntimeError(f"[{page_id}] 스캔 결과 없음 — 모든 Phase 실패")
```

---

### 1.8 `core/reporter.py` — `_print_phase_report()` 이전 시 toggle dep 트리 유지

**현재 `test_rdp_policy_scan.py`의 `_print_phase_report()`:**
- toggle_checkbox dep 트리 출력 코드 포함 (CLAUDE.md 필수 요건)
- tab 구간 헤더 출력 코드 포함

`core/reporter.py`로 이전 시 이 두 가지 코드가 반드시 포함되어야 함.
현재 두 테스트 파일의 `_print_phase_report()`가 동일 코드 → 단순 이전으로 충분.

**확인사항:** 두 파일 간 출력 로직 차이 없음 — 동일하게 복사하면 됨.

---

## 2. 불필요 항목 (제외 권고)

### 2.1 `core/scanner.py` 수정 불필요

`core/scanner.py`는 현재 미사용(또는 구버전) 파일로 보임.
`core/ui_scanner.py`가 실제 오케스트레이터 → scanner.py는 건드리지 않음.

### 2.2 `conftest.py` 수정 불필요

`logged_in_page`, `settings` fixture는 현재 구조 유지.
`qa_runner.py`는 이 값들을 파라미터로 받으므로 fixture 구조 변경 없음.

---

## 3. 추가 권고 사항

### 3.1 `pages/registry.py` — 순환 임포트 위험 없음

```python
# pages/registry.py
from pages.ransom_detect_policy_page import RansomDetectPolicyPage
from pages.rdp_policy_page import RdpPolicyPage

PAGE_REGISTRY = {...}
```

`core/qa_runner.py` → `pages/registry.py` → `pages/*.py` → `pages/base_page.py`

단방향 의존성. 순환 없음.

### 3.2 `test_scan_pages.py`의 parametrize ID 형식

```python
@pytest.mark.parametrize("page_id", list(PAGE_REGISTRY.keys()))
```

pytest 출력:
```
test_page_scan[ransom_detect_policy]
test_page_scan[rdp_policy]
```
명확하고 좋음. 변경 불필요.

### 3.3 `AUTO_NAME_PREFIX` vs `page_id` 기반 이름 생성

QA 분석 2.4 해결책으로:
- `Page 클래스에 AUTO_NAME_PREFIX 상수` 추가가 가장 깔끔
- 또는 `YAML의 page_id`를 4~6자로 줄인 약어 사용

```python
# 방법 1: Page 클래스 상수
class RansomDetectPolicyPage(BasePage):
    AUTO_NAME_PREFIX = "[AUTO]_det"   # maxlength=20 내 (10자)

class RdpPolicyPage(BasePage):
    AUTO_NAME_PREFIX = "[AUTO]_rdp"   # (10자, 이후 _p1/_p2 추가 = 13자)

# qa_runner.py
prefix = getattr(page_obj, "AUTO_NAME_PREFIX", f"[AUTO]_{page_id[:6]}")
p1_name = f"{prefix}_p1"
p2_name = f"{prefix}_p2"
```

---

## 4. 변경 파일 최종 목록

| 파일 | 변경 유형 | 주요 내용 |
|------|----------|----------|
| `core/reporter.py` | **신규** | `_print_phase_report()` + `print_combined_report()` 공통화 |
| `core/qa_runner.py` | **신규** | `run_3phase_scan()` 오케스트레이터 |
| `pages/registry.py` | **신규** | PAGE_REGISTRY 매핑 |
| `pages/base_page.py` | **수정** | `save_policy()`, `close_edit_modal()`, `get_verify_values()` 서명 추가 |
| `pages/ransom_detect_policy_page.py` | **수정** | 위 3개 메서드 + `AUTO_NAME_PREFIX` 구현 |
| `pages/rdp_policy_page.py` | **수정** | 위 3개 메서드 + `AUTO_NAME_PREFIX` 구현 |
| `tests/test_scan_pages.py` | **신규** | parametrize 범용 테스트 |
| `tests/test_ransom_detect_policy_scan.py` | **이동/skip** | `tests/archive/` 이동 권고 |
| `tests/test_rdp_policy_scan.py` | **이동/skip** | `tests/archive/` 이동 권고 |
