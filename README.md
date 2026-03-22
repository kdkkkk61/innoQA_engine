# Manager UI 자동화 테스트 툴

보안 제품의 매니저 웹 UI를 자동으로 테스트하는 Playwright + pytest 기반 도구입니다.

---

## 프로젝트 구조

```
inno_test_tool/
├── config/
│   └── settings.yaml          # URL, 계정 정보, 브라우저 설정, Selector 정의
├── pages/
│   ├── base_page.py           # 공통 메서드 추상화 (BasePage)
│   └── login_page.py          # 로그인 페이지 Page Object
├── tests/
│   └── test_login.py          # 로그인 테스트 케이스 3개
├── reports/
│   └── screenshots/           # 실패 시 자동 저장되는 스크린샷
├── conftest.py                # pytest fixture (브라우저, 설정 로드)
└── requirements.txt
```

---

## 설치 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. Playwright 브라우저 바이너리 설치
playwright install chromium
```

---

## 실행 전 설정

`config/settings.yaml` 파일을 열어 실제 환경에 맞게 수정합니다.

```yaml
base_url: "http://192.168.1.100"   # 실제 매니저 URL로 변경

credentials:
  admin:
    username: "admin"              # 실제 관리자 계정
    password: "realpassword"       # 실제 비밀번호
  invalid:
    username: "wrong"
    password: "wrong"

browser:
  headless: false    # true로 설정하면 브라우저 창 없이 백그라운드 실행
  slow_mo: 0         # 디버깅 시 500 정도로 올리면 액션이 느리게 실행됨
  timeout: 30000     # ms 단위 (30초)
```

---

## 테스트 실행

```bash
# 전체 테스트 실행 + HTML 리포트 생성
pytest tests/ --html=reports/report.html --self-contained-html -v

# 특정 테스트만 실행
pytest tests/test_login.py::TestLogin::test_login_success -v

# 헤드리스 모드로 실행 (settings.yaml 대신 환경변수로 덮어쓰기 불가, yaml 직접 수정)
# → settings.yaml의 browser.headless: true 로 변경 후 실행
```

### 리포트 확인

실행 후 `reports/report.html` 파일을 브라우저로 열면 테스트 결과를 확인할 수 있습니다.
실패한 테스트의 스크린샷은 `reports/screenshots/` 폴더에 자동 저장됩니다.

---

## Selector 커스터마이징

실제 제품의 HTML 구조에 따라 로그인 폼의 selector가 다를 수 있습니다.
`config/settings.yaml`의 `selectors.login` 섹션만 수정하면 됩니다.

```yaml
selectors:
  login:
    # 아이디 입력란 — 실제 HTML에 맞는 selector로 변경
    username_input: "input[name='loginId']"

    # 비밀번호 입력란
    password_input: "input[type='password']"

    # 로그인 버튼
    submit_button: "button#btn-login"

    # 에러 메시지 영역
    error_message: "div.login-error-msg"

    # 로그아웃 버튼/링크
    logout_button: "a.btn-logout"
```

### Selector 찾는 방법

1. Chrome 개발자 도구(F12) → Elements 탭
2. 로그인 입력란 클릭 후 우클릭 → "검사(Inspect)"
3. `id`, `name`, `class`, `aria-label` 속성 확인
4. 확인된 속성으로 위 yaml 값을 교체

---

## 테스트 케이스 목록

| 테스트 | 설명 |
|---|---|
| `test_login_success` | 정상 계정으로 로그인 후 URL이 `/login`에서 벗어나는지 확인 |
| `test_login_failure` | 잘못된 계정으로 로그인 시 에러 메시지가 표시되는지 확인 |
| `test_logout` | 로그인 후 로그아웃 시 로그인 페이지로 돌아오는지 확인 |

---

## 새 테스트 추가 방법

CLAUDE.md의 아키텍처 원칙을 따릅니다.

1. `pages/` 에 새 Page 클래스 파일 생성 (`BasePage` 상속)
2. selector를 클래스 상단 상수로 정의
3. 메서드 단위로 페이지 조작 구현
4. `tests/` 에 대응하는 테스트 파일 생성
5. 기존 파일은 수정하지 않음

예시:
```
pages/firewall_policy_page.py  ← 신규
tests/test_firewall_policy.py  ← 신규
```
