# UI 자동 스캔 + 패턴 검증 아키텍처 — 구현 요구사항

> **이 문서의 목적**: Claude Code에게 전달하는 작업 지시서.
> 이 파일을 읽고, 현재 프로젝트 코드를 확인한 뒤, Phase별로 순서대로 구현한다.
>
> **기존 문서와의 관계**:
> - `CLAUDE.md`: 기존 설계 원칙 → 이 문서의 규칙은 CLAUDE.md를 확장한다 (충돌 시 이 문서 우선)
> - `design.md` Section 6~9: 초안이었던 방향성 → 이 문서가 확정판이다

---

## 0. 사전 작업 — 반드시 먼저 수행

Claude Code는 코드 작성 전 아래를 수행한다:

1. `CLAUDE.md` 를 읽고 기존 설계 원칙을 숙지
2. `design.md` 를 읽고 현재 프로젝트 상태를 파악 (특히 Section 4: 구현 완료 기능)
3. 프로젝트 디렉토리 구조를 확인 (`tree` 또는 `ls -R`)
4. `pages/base_page.py` 의 메서드 목록 확인 (click, click_attached, fill, wait_for 등)
5. `pages/ransom_detect_policy_page.py` 의 selector 상수와 메서드 확인
6. `conftest.py` 의 fixture 구조 확인 (fresh_page, logged_in_page, credentials, settings)
7. `config/settings.yaml` 구조 확인

**기존 코드(pages/, tests/, conftest.py)는 삭제하거나 변경하지 않는다.**
새 아키텍처는 별도 디렉토리(`core/`, `validators/`)로 추가한다.

---

## 1. design.md 미결 사항 확정

design.md Section 9의 미결 사항을 아래와 같이 확정한다:

| # | 항목 | 확정 결론 | 이유 |
|---|------|-----------|------|
| 1 | HTML 스캔 방식 | **Playwright로 라이브 페이지 스캔** | SPA(AngularJS)라서 정적 HTML 분석으론 ng-model 등 동적 바인딩을 볼 수 없음 |
| 2 | 패턴 매핑 초안 | **HTML 스캔 자동 생성 → 사람이 검토/보정** | 완전 수동은 비효율, 완전 자동은 오탐 위험 |
| 3 | xlsx 시트 구조 | **심각도별 시트 분리** (요약 + Critical + Major + Minor + 전체) | 정책별 시트는 정책 수 증가 시 시트가 과다해짐 |
| 4 | 스캔 범위 | **모든 정책 모달에 동일 방식 확장** | 패턴 기반이므로 정책별 차이는 config로 흡수 |
| 5 | 패턴 라이브러리 위치 | **`core/` + `validators/`** (pages/patterns/ 아님) | pages/는 "페이지 조작만" 원칙 유지, 검증 로직은 별도 레이어 |

---

## 2. 최종 목표

```
UI 요소 자동 스캔 → 패턴별 검증 실행 + 스크린샷 캡처 → 리포트(pytest-html + xlsx)
```

---

## 3. 추가할 디렉토리 구조

기존 구조는 그대로 두고 아래를 **추가**한다:

```
inno_test_tool/
├── (기존 유지 — 절대 수정 금지)
│   ├── CLAUDE.md
│   ├── design.md
│   ├── conftest.py
│   ├── config/settings.yaml
│   ├── pages/base_page.py
│   ├── pages/login_page.py
│   ├── pages/ransom_detect_policy_page.py
│   ├── tests/test_login.py
│   └── tests/test_ransom_detect_policy.py
│
├── config/
│   ├── ui_patterns.yaml           ← [신규] 요소 유형별 식별 규칙 + 검증 항목
│   ├── common_validations.yaml    ← [신규] 공통 검증 규칙
│   └── test_data.yaml             ← [신규] 테스트 입력 데이터
│
├── core/                          ← [신규] 자동 스캔 엔진
│   ├── __init__.py
│   ├── registry.py                ← validator 자동 등록 (데코레이터)
│   ├── base_validator.py          ← validator 공통 인터페이스
│   ├── scanner.py                 ← 페이지 스캔 → 요소 유형 탐지
│   ├── wait_strategy.py           ← 요소별 대기 전략
│   ├── screenshot_manager.py      ← 캡처 + 하이라이팅
│   └── performance.py             ← 액션별 응답 시간 측정
│
├── validators/                    ← [신규] 요소 유형별 검증 로직
│   ├── __init__.py                ← 동적 import로 자동 등록
│   ├── tag_input.py
│   ├── checkbox.py
│   ├── text_input.py
│   ├── number_input.py
│   ├── modal_trigger.py
│   ├── dropdown.py
│   ├── table_grid.py
│   └── (추후 확장)
│
├── tests/
│   └── test_ui_scan.py            ← [신규] 스캔 기반 자동 검증
│
└── reports/
    └── generators/                ← [신규]
        ├── __init__.py
        ├── xlsx_report.py         ← 심각도별 시트
        └── json_export.py         ← CI/CD용
```

---

## 4. config/ YAML 설계

### 4-1. ui_patterns.yaml

design.md Section 7의 초안을 확장한다.
**변경점**: `pages/patterns/` 대신 `validators/`를 참조하고, 식별 규칙(identify)을 추가한다.

```yaml
# ==========================================
# UI 요소 패턴 정의
# ==========================================
# 각 패턴: identify(식별) + tests(검증) + capture_on(캡처 조건)
# 식별 우선순위: by_attribute > by_aria > by_heuristic

tag_input:
  identify:
    priority: 1
    by_attribute: '[data-component="tag-input"]'
    by_aria: '[role="combobox"][aria-haspopup="listbox"]'
    by_heuristic:
      # 이 프로젝트의 실제 구조: input.tag-input + ul.tag-list
      container_selector: '.tag-list, .tags-wrapper, ul.tag-list'
      has_child_input: true
      has_removable_items: '.tag-remove, .close, .fa-times, [data-dismiss]'
  tests:
    - name: duplicate_entry
      description: "중복 입력 시 거부 확인"
      severity: major
    - name: format_restriction
      description: "형식 외 입력 거부 (regex 기반)"
      severity: major
    - name: char_limit
      description: "글자 수 제한 확인"
      severity: minor
    - name: add_button
      description: "추가 버튼 동작"
      severity: critical
    - name: delete_button
      description: "태그 삭제 버튼 동작"
      severity: critical
  capture_on: [fail, modal]

checkbox:
  identify:
    priority: 2
    by_attribute: 'input[type="checkbox"]'
    by_aria: '[role="checkbox"], [role="switch"]'
    by_heuristic:
      # AngularJS 토글: ng-model 바인딩된 체크박스
      has_state_attribute: 'ng-model, ng-checked, ng-change'
  tests:
    - name: toggle_on_off
      description: "체크 ON → OFF → ON 상태 전환"
      severity: critical
    - name: dependent_fields
      description: "ON 시 종속 필드 활성화, OFF 시 비활성화"
      severity: major
    - name: initial_state
      description: "초기 상태(체크/미체크) 확인"
      severity: minor
  capture_on: [each_state]

text_input:
  identify:
    priority: 3
    by_attribute: 'input[type="text"], input:not([type]), textarea'
    by_aria: '[role="textbox"]'
    by_heuristic:
      exclude: 'input[type="checkbox"], input[type="radio"], input[type="button"], input[type="submit"], input[type="hidden"], input.tag-input'
  tests:
    - name: maxlength_check
      description: "maxlength 속성 초과 입력 차단"
      severity: minor
    - name: required_field
      description: "필수값 미입력 시 에러 확인"
      severity: major
    - name: special_char_input
      description: "특수문자 입력 처리"
      severity: major
    - name: xss_injection
      description: "XSS 스크립트 입력 차단"
      severity: critical
    - name: sql_injection
      description: "SQL 인젝션 입력 차단"
      severity: critical
  capture_on: [fail]

number_input:
  identify:
    priority: 4
    by_attribute: 'input[type="number"]'
    by_aria: '[role="spinbutton"]'
    by_heuristic:
      # 숫자 전용: min/max 속성이 있거나, ng-pattern에 숫자 regex
      has_numeric_attribute: 'min, max, step, ng-pattern'
  tests:
    - name: min_max_range
      description: "min/max 범위 제한 확인"
      severity: major
    - name: non_numeric_reject
      description: "숫자 외 입력 차단"
      severity: major
    - name: boundary_values
      description: "경계값 (min, max, min-1, max+1) 검증"
      severity: minor
  capture_on: [fail]

modal_trigger:
  identify:
    priority: 5
    by_attribute: '[data-toggle="modal"], [data-bs-toggle="modal"]'
    by_aria: '[aria-haspopup="dialog"]'
    by_heuristic:
      # Bootstrap 3 모달: .modal 클래스 + .in 상태 감지
      target_selector: '.modal, [role="dialog"]'
      opened_indicator: '.in'  # Bootstrap 3 특수: .modal.in = 열린 상태
  tests:
    - name: open_close
      description: "모달 열기/닫기 동작"
      severity: critical
    - name: escape_close
      description: "ESC 키로 닫기"
      severity: minor
    - name: content_render
      description: "모달 내부 컨텐츠 정상 렌더링"
      severity: major
  capture_on: [open, close]

dropdown:
  identify:
    priority: 6
    by_attribute: 'select'
    by_aria: '[role="listbox"]'
    by_heuristic:
      container_selector: '.dropdown, .select2, [class*="dropdown"]'
  tests:
    - name: option_load
      description: "옵션 목록 정상 로딩"
      severity: critical
    - name: selection_change
      description: "선택 변경 후 값 반영"
      severity: critical
    - name: keyboard_navigation
      description: "Arrow Up/Down + Enter 키보드 탐색"
      severity: minor
  capture_on: [fail]

table_grid:
  identify:
    priority: 7
    by_attribute: 'table, [role="grid"]'
    by_aria: '[role="grid"], [role="table"]'
    by_heuristic:
      # AngularJS: ng-repeat로 생성된 tr 확인
      has_rows: 'tr.ng-scope'
  tests:
    - name: row_selection
      description: "행 선택 동작 (클릭 → 하이라이트)"
      severity: critical
    - name: checkbox_selection
      description: "체크박스 다중 선택"
      severity: major
    - name: pagination
      description: "페이지네이션 동작"
      severity: major
    - name: sort_column
      description: "컬럼 정렬 동작"
      severity: minor
  capture_on: [fail]
```

### 4-2. common_validations.yaml

모든 UI 요소에 공통 적용되는 검증 규칙.

```yaml
# ==========================================
# 공통 검증 (모든 요소에 자동 적용)
# ==========================================

accessibility:
  - name: keyboard_navigable
    description: "Tab/Shift+Tab으로 접근 가능"
    severity: major
  - name: focus_visible
    description: "포커스 시 시각적 표시 존재"
    severity: major
  - name: aria_labels_present
    description: "스크린리더용 라벨 존재"
    severity: minor

error_handling:
  - name: required_field_message
    description: "필수값 미입력 시 에러 메시지 표시"
    severity: major
  - name: error_clear_on_fix
    description: "올바른 입력 시 에러 해제"
    severity: major

state_persistence:
  - name: value_after_interaction
    description: "값 입력 후 다른 필드 클릭 시 값 유지"
    severity: critical
```

### 4-3. test_data.yaml

검증에 사용할 테스트 입력 데이터. **코드 안에 하드코딩하지 않는다.**

```yaml
# ==========================================
# 패턴별 테스트 입력 데이터
# ==========================================

text_input:
  valid_samples:
    - "정상 텍스트"
    - "Normal Text 123"
  xss_payloads:
    - '<script>alert("xss")</script>'
    - '"><img src=x onerror=alert(1)>'
  sql_payloads:
    - "' OR 1=1 --"
    - "'; DROP TABLE users; --"
  special_chars:
    - "!@#$%^&*()"
    - "<>&'\""
  boundary:
    empty: ""
    single_char: "a"
    max_length_filler: "A"  # maxlength 값만큼 반복 생성

tag_input:
  valid_tags: ["exe", "doc", "pdf"]
  duplicate_tag: "exe"
  invalid_format:
    - "exe exe"   # 공백 포함
    - ".exe"      # 점 포함
    - ""          # 빈값
  long_tag: "a_very_long_extension_name_that_exceeds_limit"

number_input:
  valid: [1, 50, 100]
  non_numeric: ["abc", "!@#", "1.2.3"]
  # min/max는 요소의 HTML 속성에서 자동 읽음
```

---

## 5. core/ 엔진 설계

### 5-1. registry.py — Validator 자동 등록

```
구현 요구사항:

1. _VALIDATORS: Dict[str, Type[BaseValidator]] 글로벌 레지스트리
2. @register_validator(pattern_name) 데코레이터
   - 클래스를 레지스트리에 등록
   - 중복 등록 시 경고 로그 출력
3. get_validator(pattern_name) -> Optional[Type[BaseValidator]]
4. get_all_validators() -> Dict[str, Type[BaseValidator]]
5. validators/__init__.py 에서 동적 import:
   validators/ 디렉토리의 모든 .py 파일을 import하면
   각 파일의 @register_validator가 실행되어 자동 등록됨
```

### 5-2. base_validator.py — 공통 인터페이스

```
구현 요구사항:

1. BaseValidator(ABC) 추상 클래스
   __init__(self, page, element_locator, config, test_data)
   - page: Playwright Page 객체 (기존 logged_in_page와 동일)
   - element_locator: 탐지된 요소의 Locator
   - config: ui_patterns.yaml 에서 해당 패턴 설정
   - test_data: test_data.yaml 에서 해당 패턴 데이터

2. 추상 메서드:
   validate(self) -> list[ValidationResult]

3. 공통 메서드 (기존 코드에서 검증된 패턴 반영):

   angular_fill(self, locator, value)
     AngularJS 호환 입력:
       locator.evaluate("el => { el.value = ''; }")
       locator.fill(value)
       locator.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
       locator.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
     → 기존 ransom_detect_policy_page.py에서 검증된 패턴

   js_click(self, locator)
     오버레이 우회 클릭:
       locator.evaluate("el => el.click()")
     → 기존 base_page.py의 click() 방식과 동일
     → force=True는 사용 불가 (design.md Section 10 참조)

   check_bootstrap3_modal(self, modal_selector) -> bool
     Bootstrap 3 모달 열림 감지:
       page.locator(f"{modal_selector}.in").wait_for(state="attached")
     → 기존 코드의 .in 클래스 패턴 (visible 체크 불가)

   run_common_validations(self) -> list[ValidationResult]
     common_validations.yaml 기반 공통 검증

   take_screenshot(self, name, highlight=True) -> str
   measure_action_time(self, action_callable) -> float

4. ValidationResult 데이터 클래스:
   pattern: str         # "tag_input" 등
   test_name: str       # "duplicate_entry" 등
   status: str          # "pass", "fail", "skip", "error"
   severity: str        # "critical", "major", "minor"
   message: str         # 결과 설명
   screenshot_path: str # 스크린샷 경로
   duration_ms: float   # 실행 시간
   element_info: dict   # selector, text, attributes 등
```

### 5-3. scanner.py — 3단계 식별 엔진

```
구현 요구사항:

1. UIScanner 클래스
   __init__(self, page, patterns_config)

2. scan(self) -> list[ScannedElement]
   페이지 전체 스캔 → 탐지된 요소 목록 반환
   
   식별 3단계:
     Step 1: by_attribute — CSS selector로 직접 매칭 (가장 정확)
     Step 2: by_aria — ARIA role/속성으로 시멘틱 매칭
     Step 3: by_heuristic — DOM 구조 + AngularJS 디렉티브로 추론
   
   AngularJS 특수 처리:
     - ng-model 속성으로 유형 추론
     - ng-repeat가 있는 tr → table_grid 강한 시그널

3. ScannedElement 데이터 클래스:
   pattern_name: str    # "tag_input" 등
   locator: Locator
   match_method: str    # "attribute", "aria", "heuristic"
   confidence: float    # 0.0 ~ 1.0
   element_info: dict   # tag, id, class, ng-model 등

4. 규칙:
   - 여러 패턴에 매칭 → priority 숫자 작은 패턴 우선
   - heuristic confidence < 0.5 → "unknown" (검증 건너뜀)
   - display:none / visibility:hidden → 스캔 제외
   - 오버레이(#qa-block-overlay, #qa-test-banner) → 스캔 제외
```

### 5-4. wait_strategy.py

```
구현 요구사항:

time.sleep() 대신 사용. base_page.py 수정하지 않고 독립 구현.

전략:
  VISIBLE         → locator.wait_for(state="visible")
  CLICKABLE       → visible + enabled
  ANIMATION_DONE  → CSS transition 종료 감지
  NETWORK_IDLE    → page.wait_for_load_state("networkidle")
  ANGULAR_DIGEST  → AngularJS $digest 사이클 완료
  MODAL_OPENED    → Bootstrap 3 전용: .in 클래스 부착 대기

기본 타임아웃: 10000ms (설정 가능)
```

### 5-5. screenshot_manager.py

```
구현 요구사항:

기존 reports/screenshots/ 구조와 호환.

capture_element(locator, name, highlight=True) → 요소 캡처
capture_page(page, name) → 전체 페이지 캡처
capture_before_after(page, locator, action, name) → 전/후 비교

하이라이팅: page.evaluate()로 임시 border → 캡처 → 제거
오버레이(z-index 99998)와 충돌 주의

저장: reports/screenshots/scan/{패턴명}/{테스트명}_{timestamp}.png
```

### 5-6. performance.py

```
구현 요구사항:

임계값:
  200ms 이하 → 정상
  200ms ~ 1000ms → 주의
  1000ms 초과 → 경고 (리포트에 표시)
```

---

## 6. validators/ 작성 규칙

### 6-1. 공통 구조

```python
from core.registry import register_validator
from core.base_validator import BaseValidator, ValidationResult

@register_validator("패턴이름")
class PatternNameValidator(BaseValidator):
    
    def validate(self) -> list[ValidationResult]:
        results = []
        results.extend(self.run_common_validations())
        for test_config in self.config.get("tests", []):
            method_name = f"validate_{test_config['name']}"
            if hasattr(self, method_name):
                result = getattr(self, method_name)()
                results.append(result)
            else:
                results.append(ValidationResult(
                    pattern=self.pattern_name,
                    test_name=test_config["name"],
                    status="skip",
                    severity=test_config.get("severity", "minor"),
                    message=f"미구현: {method_name}",
                    screenshot_path="",
                    duration_ms=0,
                    element_info={}
                ))
        return results
    
    def validate_테스트항목(self) -> ValidationResult:
        ...
```

### 6-2. 1단계 우선 구현 (기존 경험 활용)

| validator | 기존 코드 참고 | 핵심 검증 |
|-----------|---------------|-----------|
| tag_input.py | test_extension_validation | 중복/형식/추가/삭제 |
| checkbox.py | test_toggle_activation | ON/OFF + 종속필드 |
| text_input.py | test_policy_name_validation | maxlength/필수값/XSS/SQLi |
| number_input.py | 롤백 크기, 갱신 주기 필드 | min/max/비숫자 |
| modal_trigger.py | 정책추가/수정 모달 | 열기/닫기/ESC |

### 6-3. AngularJS 호환 필수

모든 validator에서 반드시 지킬 것:
- 텍스트 입력 → angular_fill() 사용
- 클릭 → js_click() 사용
- 모달 감지 → .in 클래스 확인
- SPA 이동 → hash 변경 (page.goto 금지)
- pageSize 리셋 주의

---

## 7. tests/test_ui_scan.py

```
구현 요구사항:

1. logged_in_page fixture 사용 (기존과 동일)
2. 스캔 대상 URL은 config에서 읽음
3. 실행 흐름:
   - 대상 페이지로 이동 (hash 변경)
   - UIScanner로 스캔
   - 레지스트리에서 validator 조회
   - validator.validate() 실행
   - ValidationResult 수집
4. pytest 마커로 분리 실행:
   @pytest.mark.scan → 스캔 테스트만
   마커 없음 → 전체 (기존 + 스캔)
```

---

## 8. reports/ 리포트

### 8-1. pytest-html (기존 확장)
스크린샷 임베딩 + severity 컬럼 + 패턴별 그룹핑

### 8-2. xlsx (신규 — openpyxl 사용)
```
시트 구조:
  Sheet 1: "요약" — pass/fail, severity별 집계
  Sheet 2: "Critical"
  Sheet 3: "Major"
  Sheet 4: "Minor"
  Sheet 5: "전체 결과" (필터 가능)

각 행: 페이지명 | 요소명 | 패턴 | 검증항목 | 결과 | 심각도 | 설명 | 소요시간 | 스크린샷
```

### 8-3. JSON (CI/CD용)
실행 ID, 요약 집계, 전체 결과 배열

---

## 9. CLAUDE.md 추가 규칙

기존 CLAUDE.md 하단에 아래 섹션을 **추가**한다 (기존 내용 유지):

```markdown
---

## UI 자동 스캔 아키텍처 규칙

### 레이어 구조 (기존 확장)
core/          → 스캔/검증 엔진만 (특정 페이지 로직 금지)
validators/    → 패턴별 검증만 (다른 validator 참조 금지)

### 새 UI 패턴 추가 시 체크리스트
1. config/ui_patterns.yaml 에 패턴 정의 추가
2. config/test_data.yaml 에 테스트 데이터 추가
3. validators/ 에 새 파일 생성 (@register_validator 필수)
4. 다른 파일은 수정하지 않는다 (자동 등록됨)

### validator 작성 규칙
- 하나의 파일 = 하나의 UI 패턴
- BaseValidator 상속 필수
- 데이터는 test_data.yaml에서 (하드코딩 금지)
- severity는 ui_patterns.yaml에서 (하드코딩 금지)
- sleep() 금지, fill() 대신 angular_fill(), click() 대신 js_click()
```

---

## 10. 구현 순서 (Phase별)

**각 Phase 완료 후 결과를 보고하고, 다음 Phase 진행 허가를 기다린다.**

### Phase 1: 기반 구조
1. config/ YAML 3개 파일 생성
2. core/__init__.py
3. core/registry.py (데코레이터 + 레지스트리)
4. core/base_validator.py (추상 클래스 + 공통 메서드 + ValidationResult)
5. core/wait_strategy.py
6. validators/__init__.py (동적 import)
7. 빈 validator 1개(text_input.py) 생성하여 등록 동작 확인
8. **확인**: python -c로 registry 등록 동작 테스트

### Phase 2: 1차 validator
9. validators/text_input.py
10. validators/checkbox.py
11. validators/tag_input.py
12. validators/number_input.py
13. validators/modal_trigger.py
14. **확인**: 각 validator import + validate() 호출 가능 확인

### Phase 3: 스캔 엔진 + 연동
15. core/scanner.py (3단계 식별)
16. core/screenshot_manager.py
17. core/performance.py
18. tests/test_ui_scan.py
19. **확인**: RansomCruncher 탐지정책 대상 스캔 → 탐지 → 검증
20. **확인**: 기존 테스트와 공존 (pytest 전체 실행 시 충돌 없음)

### Phase 4: 리포트
21. reports/generators/xlsx_report.py
22. reports/generators/json_export.py
23. pytest-html 확장 (conftest.py 훅 추가 — 기존 유지)
24. CLAUDE.md 업데이트
25. design.md 업데이트

### Phase 5: 2차 validator (필요 시)
26. validators/dropdown.py
27. validators/table_grid.py
28. 추가 패턴

---

## 11. 기술적 제약 요약

| 제약 | 이유 | 해결 방식 |
|------|------|-----------|
| page.goto() 금지 | SPA 세션 끊김 | hash 변경으로 이동 |
| visible 체크 불가 (모달) | Bootstrap 3 구조 | .in 클래스 attached 확인 |
| 일반 fill() 불가 | AngularJS 바인딩 미감지 | angular_fill() |
| 일반 click() 불가 | 오버레이 차단 | js_click() (el.click()) |
| force=True 불가 | 좌표 클릭도 오버레이에 막힘 | JS el.click()만 사용 |
| sleep() 금지 | 불안정 + 느림 | wait_strategy |
| [AUTO] 접두사 필수 | 운영 데이터 보호 | 생성/복사/삭제 시 검사 |
| pageSize 리셋 | CRUD 후 10으로 돌아감 | _restore_page_size() |
