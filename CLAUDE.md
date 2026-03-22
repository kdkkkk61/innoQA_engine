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