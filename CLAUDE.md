# 프로젝트 설계 원칙 (Claude Code 필독)

이 파일은 코드 작성 전 반드시 읽어야 할 설계 규칙이다.
새 기능 추가 시 이 규칙을 벗어나는 구조는 만들지 않는다.

---

## 아키텍처 원칙

### 레이어 구조
```
config/         → 환경 설정만 (코드 없음)
pages/          → 페이지 조작만 (검증 로직 없음)
tests/          → 검증만 (페이지 조작 직접 하지 않음)
utils/          → 순수 유틸리티만 (페이지/테스트 의존 없음)
```

각 레이어는 자신의 역할만 수행한다. 역할이 애매하면 utils/에 넣기 전에 먼저 물어볼 것.

---

## 파일 분리 기준

### pages/ 규칙
- 파일 하나 = 페이지(또는 기능 영역) 하나
- 하나의 파일이 200줄을 넘으면 분리를 검토한다
- 모든 Page 클래스는 BasePage를 상속한다
- selector는 클래스 상단에 상수로 모아둔다 (메서드 안에 하드코딩 금지)

```python
# 좋은 예
class FirewallPolicyPage(BasePage):
    SELECTOR_NAME_INPUT = "#policy-name"
    SELECTOR_SAVE_BTN   = "button[type='submit']"

    def create(self, name): ...

# 나쁜 예
class FirewallPolicyPage(BasePage):
    def create(self, name):
        self.fill("#policy-name", name)      # selector 하드코딩
        self.click("button[type='submit']")  # selector 하드코딩
```

### tests/ 규칙
- 파일 하나 = 기능 영역 하나 (test_login.py, test_firewall_policy.py ...)
- 테스트 함수 하나는 하나의 시나리오만 검증한다
- Page 객체를 직접 import해서 사용하고, Playwright page 객체를 직접 조작하지 않는다

### utils/ 규칙
- 특정 페이지나 테스트에 종속되지 않는 순수 함수만
- 예: 로그 파싱, 날짜 포맷, yaml 로드, 스크린샷 네이밍

---

## 새 페이지/기능 추가 시 체크리스트

새로운 페이지 테스트를 추가할 때 반드시 이 순서를 따른다.

1. `pages/` 에 새 Page 클래스 파일 생성 (BasePage 상속)
2. selector를 클래스 상단 상수로 정의
3. 메서드 단위로 페이지 조작 구현
4. `tests/` 에 대응하는 테스트 파일 생성
5. 기존 파일에 관련 없는 코드를 추가하지 않는다

---

## 절대 하지 말아야 할 것

- `base_page.py`에 특정 페이지 전용 로직 추가
- `conftest.py`에 테스트 케이스 로직 추가
- 하나의 테스트 함수에서 여러 시나리오를 한꺼번에 검증
- 하드코딩된 sleep() 사용 (wait_for_selector 또는 expect 사용)
- 기존 파일에 계속 추가하는 방식으로 기능 확장

---

## 확장 예시

로그인 → 방화벽 정책 → DLP 정책 순서로 확장할 때:

```
pages/
├── base_page.py
├── login_page.py          ← 기존
├── firewall_policy_page.py  ← 신규 추가
└── dlp_policy_page.py       ← 신규 추가

tests/
├── test_login.py          ← 기존
├── test_firewall_policy.py  ← 신규 추가
└── test_dlp_policy.py       ← 신규 추가
```

기존 파일은 건드리지 않는다.

---

## scan_hints YAML 작성 규칙 (Chrome MCP 필드 확인 절차)

새 페이지의 scan_hints yaml을 작성하거나 필드를 추가할 때,
**브라우저에 보이는 것만 확인하면 안 된다.** 반드시 아래 절차를 따른다.

### 필드 확인 필수 항목

```javascript
// Chrome MCP에서 반드시 실행할 JS — 모든 속성 한 번에 추출
const el = document.getElementById('fieldId');
const attrs = {};
for (const attr of el.attributes) attrs[attr.name] = attr.value;
JSON.stringify({ attrs, type: el.type, disabled: el.disabled, value: el.value })
```

| 확인 항목 | 이유 |
|---|---|
| `type` | text / number / checkbox / radio 구분 |
| `maxlength` | DOM 제한 vs JS 클램핑 구분 |
| `min` / `max` | number type 범위 제한 |
| `disabled` | 종속 필드 여부 |
| `ng-model` | AngularJS 바인딩 키 |
| `ng-change` / `ng-blur` | JS 클램핑 트리거 이벤트 |
| `ng-min` / `ng-max` | AngularJS 범위 validator |
| 실제 경계값 입력 테스트 | "65536 입력 → 65535로 바뀌는가" 직접 확인 |

### 잘못된 접근 (금지)

```
❌ 화면에 숫자 입력 박스가 보이니까 text_input으로 추가
❌ maxlength 속성 없으니까 maxlength: null로 처리하고 끝
❌ 값이 0으로 보이니까 기본값 0으로 기록
```

### 올바른 접근

```
✅ JS로 outerHTML + 모든 attribute 추출 후 확인
✅ maxlength 없어도 → JS 클램핑 있는지 경계값 직접 테스트
✅ disabled=false여도 → 어떤 조건에서 disabled되는지 dep_fields 추적
✅ 시간 필드 max=24 → 0~23이 맞는지 0~24가 의도인지 제품팀 확인 필요로 기록
```

### YAML 주석 기록 기준

```yaml
- selector: "input#connectPort"
  maxlength: null   # DOM maxlength 없음, JS 클램핑 max=65535 (Chrome MCP 확인)
  # 확인일: 2026-03-25 / 확인방법: Chrome MCP javascript_tool outerHTML 추출
```

---

## 스캔 결과 출력 규칙 (절대 준수)

### 핵심 원칙: 화면 순서 = 출력 순서

스캔 결과는 **UI 화면 위→아래 시각적 순서**로 출력한다.
패턴 타입별(라디오/토글/텍스트...)로 묶어서 출력하는 것은 금지.

```
❌ 나쁜 예 — 타입별 묶음
  ✅ [radio_group] 행위기반 탐지등급
  ✅ [toggle_checkbox] 탐지 제외사항
  ✅ [toggle_checkbox] 롤백 기능 사용
  ✅ [text_input] 정책 이름
  ✅ [plain_checkbox] 소프트웨어 인증 사용

✅ 좋은 예 — 화면 순서 (order 기준 정렬)
  ✅ [text_input] 정책 이름          ← order=10
  ✅ [plain_checkbox] 소프트웨어 인증 사용  ← order=30
  ✅ [radio_group] 행위기반 탐지등급  ← order=40
  ✅ [toggle_checkbox] 롤백 기능 사용 ← order=80
       └ ✅ [number_input] 복구 대상파일 최대용량
       └ ✅ [number_input] 차단 후 롤백 대기시간
  ✅ [toggle_checkbox] 프로세스 격리기능 ← order=90
       └ ✅ [plain_checkbox] 격리 프로세스 삭제
```

### 출력 구현 필수 요건

1. **정렬**: `order` 값 오름차순. `order` 없는 항목은 맨 뒤.
2. **탭 구간 헤더**: `report.tab_sections`를 이용해 탭 경계마다 구분선 출력.
   - `required_submit` 패턴은 탭 구분 제외 (항상 마지막).
   - 탭 없는 페이지(RDP 등)도 동일 코드 사용 (단순히 헤더 출력 안 됨).
3. **종속 필드**: `toggle_checkbox`의 `dep_fields`는 부모 바로 아래 `└` 트리로 출력.
   - `r.extra.get("dependent_labels")` / `dependent_types` / `dependent_results` 활용
4. **새 테스트 파일 추가 시**: `_print_phase_report`에 탭 헤더 + toggle dep 필드 출력 코드 반드시 포함.

```python
# 필수 — toggle dep 필드 출력 패턴 (모든 테스트 파일에 동일하게 적용)
for r in sorted(report.results, key=_sort_key):
    icon = _STATUS_ICON.get(r.status, "?")
    print(f"  {icon} [{r.pattern}] {r.label}: {r.detail}")
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
```

### YAML order 값 작성 규칙

- 화면 상단 요소 = 낮은 order 값
- 하단 요소 = 높은 order 값
- 10단위 간격 유지 (중간 삽입 여유 확보)
- toggle의 dep_fields는 별도 order 없이 부모 order에 귀속
- 탭 구분: 정책정보 탭 10~199 / 예외처리 탭 200~299 / 제출 9999

---

## 시나리오 번호 표준 (신규 페이지 추가 시 필수 준수)

모든 페이지(scan_mode 무관)는 **동일한 시나리오 번호 체계**를 따른다.
해당하는 시나리오가 없으면 실행하지 않고 `⏭ 시나리오 N: ... (해당 없음)` 으로 출력한다.
이 규칙은 2026-04-07 합의 이후 추가되는 모든 페이지에 적용한다.

### 마스터 시나리오 테이블

| 번호 | 이름 | 포함 항목 | modal_form | list_page |
|------|------|---------|-----------|-----------|
| **1** | UI 구조 | 탭 전환 / 테이블 헤더 / 검색창 | ✅ (없는 항목만 개별 skip) | ✅ |
| **2** | 입력 구조 | 모달 필드 / 초기값 / 필수입력 검증 | ✅ | ✅ |
| **3** | 동작 검증 | CRUD / 정책복사 / 오버플로 / 버튼 동작 / 중복처리 | ✅ | ✅ |
| **4** | 수정 시나리오 | 저장값 로드 / 재확인 | ✅ | ✅ (list_modify) |
| **5** | 케이스 검증 | 제품 설정 ON/OFF 프로파일 전환 | ✅ (test_profiles 있을 때) | ⏭ 해당 없음 |

> **시나리오 3 설계 원칙**: 동작 검증은 범위가 넓어도 된다.
> 버튼 동작 / 입력 박스 비정상 케이스 / 오버플로 등 실제 이슈가 가장 많이 나오는 구간.
> 정상 추가 → 오버플로 시도 → 복사 → 삭제 순서로 흐름이 자연스럽게 이어진다.

### 적용 기준

- **시나리오 번호는 페이지 유형에 상관없이 동일하게 사용한다**
- 해당 시나리오 자체가 없으면 → `⏭ 시나리오 N: (이름) — 해당 없음 (이유)` 출력
- 시나리오 내 특정 항목이 없으면 → 해당 항목 결과만 `skip` 처리, 시나리오 헤더는 출력
- 예: RDP 정책은 탭이 없지만 시나리오 1을 출력하고 탭 항목만 `⏭` 처리

### 출력 예시

```
━━ 시나리오 1: UI 구조 ━━━━━━━━━━━━━━━━━━━━━━
  ⏭ [tab] 탭 전환 — 해당 없음 (단일 탭 페이지)
  ✅ [button] 버튼 존재 — 추가/수정/삭제
  ✅ [table] 테이블 컬럼 — 정책명/등록일/수정일
  ✅ [search] 검색창 — 존재 확인

━━ 시나리오 2: 입력 구조 ━━━━━━━━━━━━━━━━━━━━
  ✅ [text_input] 정책 이름 ...
  ✅ [tag_input] 보호할 확장자 ...

  ... (중략) ...

⏭ 시나리오 5: 케이스 검증 — 해당 없음 (list_page 페이지)

━━ 시나리오 6: 오버플로 ━━━━━━━━━━━━━━━━━━━━━
  ⚠️ [overflow] 보호할 확장자 오버플로: 500자 태그 후 서버 오류
```

### 신규 페이지 추가 체크리스트 (시나리오 관련)

```
□ YAML에 scan_mode 명시 (modal_form / list_page)
□ 시나리오 1: list_ui 섹션 작성 (탭/버튼/테이블/검색 — 없는 항목은 생략)
□ 시나리오 2: modal 필드 / required_submit 작성
□ 시나리오 3: crud 섹션 작성
□ 시나리오 4: 수정 검증 (modal_form: get_verify_values / list_page: list_modify)
□ 시나리오 5: test_profiles 작성 (ON/OFF 케이스가 있는 경우만)
□ 시나리오 3: overflow_tests 작성 (태그 입력 필드가 있는 경우 — 시나리오 3에 통합)
```

---

## 데이터 안전 규칙

- 복사/삭제 조작은 `[AUTO]` 접두사 정책만 허용
- 이 규칙은 어떤 경우에도 우회하지 않는다
- Page 클래스 메서드 내부에서 접두사 검사 후 미충족 시 `Exception` 발생

---

## fixture 규칙

### 계정 정보
- 계정 정보는 파일에 하드코딩하지 않는다. (`settings.yaml`, `.env` 모두 금지)
- pytest 실행 시 터미널에서 직접 입력받는다 (`pytest_configure` 훅 → `input` / `getpass`)
- 테스트에서 계정이 필요하면 `credentials` fixture를 인자로 받는다.

```
# 실행 시 표시되는 프롬프트
==================================================
  매니저 로그인 계정을 입력하세요
==================================================
ID [admin]: <입력 (엔터만 치면 admin 기본값)>
Password:   <입력값 화면에 표시 안 됨>
==================================================
```

```python
# 올바른 사용
def test_something(self, fresh_page, settings, credentials):
    login_page.login(credentials["admin"]["username"], credentials["admin"]["password"])

# 잘못된 사용 — 계정을 파일에서 읽으려 하면 안 됨
def test_something(self, fresh_page, settings):
    login_page.login(settings["credentials"]["admin"]["username"], ...)
```

### 페이지 fixture 선택 기준

| 테스트 대상 | 사용할 fixture | 이유 |
|---|---|---|
| 로그인 기능 자체 (test_login.py) | `fresh_page` | 매 케이스마다 로그인 상태를 직접 제어해야 함 |
| 로그인 이후 기능 (방화벽, DLP 등) | `logged_in_page` | 세션 1회 로그인 후 공유하여 실행 속도 향상 |

### 새 테스트 파일 추가 시 fixture 선택 규칙
- `test_login.py` → `fresh_page` + `credentials`
- 그 외 모든 기능 테스트 → `logged_in_page`
- `logged_in_page`는 이미 로그인된 상태이므로 `LoginPage.login()` 호출 불필요

```python
# 로그인 이후 기능 테스트 예시
class TestFirewallPolicy:
    def test_create_policy(self, logged_in_page, settings):
        policy_page = FirewallPolicyPage(logged_in_page, settings)
        policy_page.create("test-policy")
        ...
```