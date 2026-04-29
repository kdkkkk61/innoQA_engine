# 아키텍처 원칙

> 태그: [공통 — 새 pages/ 파일 추가 시]
> 새 Page 클래스 파일을 추가하거나 레이어 구조 판단이 필요할 때 이 문서를 읽는다.

---

## 레이어 구조

```
config/     → 환경 설정만 (코드 없음)
pages/      → 페이지 조작만 (검증 로직 없음)
tests/      → 검증만 (페이지 조작 직접 하지 않음)
utils/      → 순수 유틸리티만 (페이지/테스트 의존 없음)
```

각 레이어는 자신의 역할만 수행한다. 역할이 애매하면 utils/에 넣기 전에 먼저 물어볼 것.

---

## pages/ 규칙

- 파일 하나 = 페이지(또는 기능 영역) 하나
- 모든 Page 클래스는 `BasePage`를 상속한다
- selector는 클래스 상단에 **상수**로 모아둔다 (메서드 안에 하드코딩 금지)
- 하나의 파일이 200줄을 넘으면 분리를 검토한다
- `base_page.py`에 특정 페이지 전용 로직 추가 금지

(코드 예시: 클래스 상단 `SEL_*` 상수 정의 vs 메서드 안 selector 문자열 하드코딩)

---

## tests/ 규칙

- 파일 하나 = 기능 영역 하나 (`test_login.py`, `test_firewall_policy.py` ...)
- 테스트 함수 하나는 하나의 시나리오만 검증한다
- Page 객체를 import해서 사용한다 — Playwright `page` 객체를 테스트 코드에서 직접 조작하지 않는다
- 하드코딩된 `sleep()` 사용 금지 — `wait_for_selector` 또는 `expect` 사용
- `conftest.py`에 테스트 케이스 로직 추가 금지

---

## utils/ 규칙

- 특정 페이지나 테스트에 종속되지 않는 **순수 함수**만 둔다
- 예: 로그 파싱, 날짜 포맷, yaml 로드, 스크린샷 네이밍
- 역할이 애매한 코드를 utils/에 무작정 넣지 않는다 — 먼저 물어볼 것

---

## 새 페이지 추가 순서

새로운 페이지 테스트를 추가할 때 반드시 이 순서를 따른다.

```
1. pages/ 에 새 Page 클래스 파일 생성 (BasePage 상속)
2. selector를 클래스 상단 상수로 정의
3. 메서드 단위로 페이지 조작 구현
4. tests/ 에 대응하는 테스트 파일 생성
5. 기존 파일에 관련 없는 코드를 추가하지 않는다
```

(확장 예시: 기존 페이지 유지 + 신규 페이지 추가하는 pages/, tests/ 디렉토리 구조)

기존 파일은 건드리지 않는다.

---

## fixture 규칙

### 계정 정보

- 계정 정보는 파일에 하드코딩하지 않는다 (`settings.yaml`, `.env` 모두 금지)
- pytest 실행 시 터미널에서 직접 입력받는다 (`pytest_configure` 훅 → `input` / `getpass`)
- 테스트에서 계정이 필요하면 `credentials` fixture를 인자로 받는다

(코드 예시: `credentials` fixture를 인자로 받아 `credentials["admin"]["username"]` 참조 vs `settings`에서 계정 직접 읽기)

### 페이지 fixture 선택 기준

| 테스트 대상 | 사용할 fixture | 이유 |
|---|---|---|
| 로그인 기능 자체 (`test_login.py`) | `fresh_page` | 매 케이스마다 로그인 상태를 직접 제어해야 함 |
| 로그인 이후 기능 (방화벽, DLP 등) | `logged_in_page` | 세션 1회 로그인 후 공유하여 실행 속도 향상 |

### 새 테스트 파일 추가 시

- `test_login.py` → `fresh_page` + `credentials`
- 그 외 모든 기능 테스트 → `logged_in_page`
- `logged_in_page`는 이미 로그인된 상태이므로 `LoginPage.login()` 호출 불필요

(코드 예시: `logged_in_page`를 인자로 받는 메서드 + `LoginPage.login()` 호출 없이 바로 Page 객체 생성 후 동작 테스트)

---

## 관련 문서

- `docs/test-pipeline.md` — 테스트 파일 작성 절차, 파이프라인 구조
- `docs/ui-interaction.md` — 클릭 방식, 오버레이, 인코딩 규칙
