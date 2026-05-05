# inno_test_tool — 설계 문서

> 다른 Claude 세션에서 이 문서를 읽고 대화를 이어갈 수 있도록 작성된 설계 가이드.
> 코드, 결정 배경, 미래 방향을 모두 담는다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 목적 | 보안 제품 매니저 웹 UI 자동화 테스트 |
| 대상 | Bootstrap 3 기반 SPA (Angular 추정), 내부망 `http://192.168.13.141` |
| 스택 | Python 3.12, pytest, playwright (sync), pytest-html, PyYAML |
| 실행 | `pytest tests/ --html=reports/report.html --self-contained-html -v` |
| 계정 입력 | pytest 실행 시 터미널에서 getpass로 입력 (파일 저장 금지) |

---

## 2. 현재 파일 구조

```
inno_test_tool/
├── CLAUDE.md                        # Claude Code 설계 원칙 (필독)
├── design.md                        # 이 파일
├── config/
│   └── settings.yaml                # URL, 브라우저 설정 (계정 없음)
├── pages/
│   ├── base_page.py                 # 공통 메서드 (모든 Page의 부모)
│   ├── login_page.py                # 로그인/로그아웃
│   └── ransom_detect_policy_page.py # 탐지정책 CRUD + 입력 검증
├── tests/
│   ├── test_login.py                # 로그인 3개 테스트
│   └── test_ransom_detect_policy.py # 탐지정책 4개 테스트
├── conftest.py                      # fixture 정의
├── reports/
│   └── screenshots/                 # 실패·이벤트 스크린샷 자동 저장
└── requirements.txt
```

---

## 3. 아키텍처 원칙 (CLAUDE.md 핵심)

```
config/   → 환경 설정만 (코드 없음)
pages/    → 페이지 조작만 (검증 로직 없음)
tests/    → 검증만 (Page 객체 import해 사용, Playwright 직접 조작 금지)
utils/    → 순수 유틸리티 (페이지/테스트 의존 없음)
```

- selector는 Page 클래스 상단 **상수**로 모음 (메서드 내 하드코딩 금지)
- `sleep()` 금지 → `wait_for_selector` / `expect` 사용
- 테스트 함수 하나 = 시나리오 하나
- 복사/삭제 조작은 `[AUTO]` 접두사 정책만 허용 (데이터 안전 규칙)

---

## 4. 구현 완료 기능

### 4-1. fixture 구조 (conftest.py)

| fixture | scope | 용도 |
|---------|-------|------|
| `settings` | session | settings.yaml 로드 |
| `credentials` | session | getpass로 ID/PW 입력 |
| `fresh_page` | function | 로그인 안 된 새 페이지 — test_login.py 전용 |
| `logged_in_page` | session | 1회 로그인 후 공유 — 나머지 기능 테스트 전용 |

### 4-2. 클릭 차단 오버레이

자동화 실행 중 사람의 실수 클릭을 차단하는 UI 보호 레이어.

| 요소 | 역할 |
|------|------|
| `qa-block-overlay` | 전체화면 div, `pointer-events: all`, `cursor: not-allowed`, `z-index: 99998` |
| `qa-test-banner` | 우측 하단 고정 배너, `pointer-events: none`, `z-index: 99999` |

**주입 방식:**
- `context.add_init_script()`: 모든 페이지 로드 시 자동 주입
- `_inject_overlay(page)`: logged_in_page 로그인 완료 후 수동 주입
- `_remove_overlay(page)`: yield 이후 try/except 안전 처리

### 4-3. BasePage 주요 메서드

```python
click(selector)           # JS el.click() — 오버레이 hit-testing 우회
click_attached(selector)  # attached 상태 요소 클릭 (Bootstrap 3 모달 버튼용)
fill(selector, text)      # 텍스트 입력
wait_for(selector, state) # 상태 대기
is_visible(selector)      # 가시 여부 반환
take_screenshot(name)     # reports/screenshots/ 에 저장
_toggle_overlay(enabled)  # 오버레이 pointer-events 토글 (자동화 클릭 허용/차단)
_on_error(action, error)  # 에러 로그 + 자동 스크린샷
```

**중요: `force=True` 사용 불가**
- `force=True`는 actionability 체크만 스킵, 좌표 기반 클릭은 오버레이에 막힘
- `locator.evaluate("el => el.click()")` 패턴으로 hit-testing 완전 우회

### 4-4. Bootstrap 3 모달 감지 특이사항

```python
SEL_ERROR_MODAL        = "div#__globalMessageModal"
SEL_ERROR_MODAL_OPENED = "div#__globalMessageModal.in"  # .in 클래스 → 모달 열림 감지
```

- Bootstrap 3은 `position: relative + 큰 offset` 구조 → Playwright `visible` 체크 실패
- 해결: `.in` 클래스 부착 여부로 열림 감지 (`state="attached"` 사용)

### 4-5. 완성된 테스트 목록 (7개, 전부 pass)

| 파일 | 테스트 | 내용 |
|------|--------|------|
| test_login.py | `test_login_success` | 정상 로그인 |
| test_login.py | `test_login_failure` | 잘못된 계정 에러 모달 |
| test_login.py | `test_logout` | 로그아웃 후 로그인 화면 복귀 |
| test_ransom_detect_policy.py | `test_policy_lifecycle` | 생성→수정→복사→삭제 전체 흐름 |
| test_ransom_detect_policy.py | `test_policy_name_validation` | 빈값/maxlength/중복 에러 모달 |
| test_ransom_detect_policy.py | `test_extension_validation` | 확장자 태그 추가/중복/에러 모달 |
| test_ransom_detect_policy.py | `test_toggle_activation` | 토글 ON/OFF → 종속 필드 활성화 검증 |

### 4-6. 탐지정책 모달 UI 요소 (확인된 selector)

```
# 목록 테이블
SEL_TABLE_ROW         = "tr.ng-scope"
SEL_TABLE_ROW_ACTIVE  = "tr.tActive"

# ADD 모달
SEL_ADD_BTN           = "button#__ransomDetectPolicyAddBtn"
SEL_ADD_MODAL         = "div#addModal.in"
SEL_POLICY_NAME       = "input#policyName"
SEL_EXT_INPUT         = "input.tag-input"
SEL_EXT_TAG_LIST      = "ul.tag-list"
SEL_REGISTER_BTN      = "button#modalSaveBtn"

# MODIFY 모달
SEL_MODIFY_BTN        = "button#__ransomDetectPolicyModifyBtn"
SEL_MODIFY_MODAL      = "div#modifyModal.in"

# 공통 확인 모달 (에러/성공 메시지)
SEL_CONFIRM_MODAL_OPENED = "div#confirmModal.in"
SEL_CONFIRM_BTN          = "button#confirmBtn"
SEL_MODAL_BODY_TEXT      = "div.modal-body-text"

# 토글 ON/OFF (체크박스)
SEL_TOGGLE_EXCEPT_DETECT  = "input#isExceptDetect"
SEL_TOGGLE_ROLLBACK_USE   = "input#isRollbackUse"
SEL_TOGGLE_BLOCK_PROCESS  = "input#isBlockProcess"
SEL_TOGGLE_EXCEPT_PERIOD  = "input#isExceptProcessCollect"
SEL_TOGGLE_POLICY_UPDATE  = "input#isPolicyUpdateInterval"
SEL_TOGGLE_AUTH_PASSWORD  = "input#isAuthorizationPassword"

# 토글 종속 필드 (토글 ON 시 활성화)
SEL_FIELD_FILE_PATH_EXCEPT    = "input#isFilePathExcept"
SEL_FIELD_PROCESS_PATH_EXCEPT = "input#isProcessPathExcept"
SEL_FIELD_DIGITAL_SIGN_EXCEPT = "input#isDigitalSignExcept"
SEL_FIELD_ROLLBACK_MAX_SIZE   = "input#rollbackFileMaxSize"
SEL_FIELD_ROLLBACK_WAIT_MIN   = "input#blockRollbackWaitMinute"
SEL_FIELD_REMOVE_ISOLATED     = "input#isRemoveIsolatedProcess"
SEL_FIELD_EXCEPT_PERIOD       = "input#exceptProcessCollectPeriod"
SEL_FIELD_POLICY_UPDATE_MIN   = "input#policyUpdateIntervalMinute"
SEL_FIELD_AUTH_PASSWORD       = "input#authorizationPassword"
```

### 4-7. 탐지정책 상수 (ransom_detect_policy_page.py)

```python
_TIMEOUT_TABLE      = 5000   # 테이블 XHR 완료 대기
_TIMEOUT_MODAL      = 3000   # 모달 응답 대기
_TIMEOUT_STALE      = 1000   # 잔여 모달 빠른 확인
_HASH_PAGE_SIZE_100 = "#!/managerRansomCruncherDetectPolicy?pageNo=1&pageSize=100&..."
```

---

## 5. 알려진 버그 (제품 이슈)

| 항목 | 내용 | 확인일 |
|------|------|--------|
| 인증 암호 필드 | 토글 OFF 시에도 필드가 활성화 상태 유지됨 | 2026-03-12 |

---

## 6. 다음 개발 방향 (미구현 — 설계 단계)

### 6-1. 최종 목표

```
UI 요소 자동 스캔
  → 패턴별 검증 실행 + 스크린샷 캡처
    → 리포트 생성 (pytest-html + xlsx)
```

### 6-2. 구현 순서

```
1단계: UI 요소 스캔 + 패턴 라이브러리 검증
2단계: 리포트 통합 (스크린샷 임베딩 + xlsx 출력)
```

---

## 7. 1단계 설계 — UI 스캔 + 패턴 라이브러리

### 개념

> 요소 유형(패턴)별 검증 방식을 미리 정의해두고,
> 실제 페이지를 자동 스캔해서 탐지된 요소에 자동으로 검증을 실행한다.

### 패턴 유형 (초안)

| 패턴 이름 | 대표 요소 | 검증 항목 |
|-----------|-----------|-----------|
| `tag_input` | 보호할 확장자 | 중복 입력 처리, 형식 제한, 글자 수 제한, 추가 버튼 동작, 삭제 버튼 동작 |
| `checkbox` | 소프트웨어 인증 사용, 각 토글 | ON→OFF→ON 정상 동작, 종속 필드 활성화/비활성화 |
| `text_input` | 정책 이름 | maxlength 적용 확인, 필수값 검증, 공백 trim |
| `modal_trigger` | 저장 버튼, 삭제 버튼 | 트리거 → 모달 출력 → 스크린샷 캡처 |
| `number_input` | 롤백 크기, 갱신 주기 | min/max 범위 제한, 숫자 외 입력 차단 |

### 설정 방식 (config/ui_patterns.yaml — 예시, 미확정)

```yaml
# 요소 유형별 검증 방식 정의
patterns:
  tag_input:
    tests:
      - duplicate_entry        # 중복 입력 → 거부 또는 무시 확인
      - format_restriction     # 허용 형식 외 입력 → 거부 확인
      - char_limit             # maxlength 적용 확인
      - add_button             # 추가 버튼 클릭 → 태그 생성 확인
      - delete_button          # ×버튼 클릭 → 태그 제거 확인
    capture_on: [modal, fail]

  checkbox:
    tests:
      - toggle_on_off          # ON → OFF → ON 상태 전환
      - dependent_fields       # ON 시 종속 필드 활성화, OFF 시 비활성화
    capture_on: [each_state]

  text_input:
    tests:
      - max_length             # maxlength 초과 입력 차단
      - required               # 빈값 → 에러 모달
    capture_on: [modal]

  modal_trigger:
    tests:
      - trigger_and_capture    # 버튼 클릭 → 모달 출력 → 스크린샷
    capture_on: [always]

# 정책별 요소 → 패턴 매핑 (HTML 스캔 후 자동 초안 생성 예정)
ransom_detect_policy:
  add_modal:
    - selector: "input.tag-input"
      label: "보호할 확장자"
      pattern: tag_input
      options:
        format_regex: "^[a-zA-Z0-9]+$"
        max_length: 10

    - selector: "input#isAuthorizationPassword"
      label: "소프트웨어 인증 사용"
      pattern: checkbox

    - selector: "input#policyName"
      label: "정책 이름"
      pattern: text_input
      options:
        max_length: 20
        required: true
```

### 예상 파일 구조 (구현 후)

```
pages/
  ui_scanner.py              # 실제 페이지 HTML 분석 → 요소 유형 탐지
  patterns/
    __init__.py
    tag_input.py             # tag_input 패턴 검증 함수
    checkbox.py              # checkbox 패턴 검증 함수
    text_input.py            # text_input 패턴 검증 함수
    modal_trigger.py         # modal_trigger 패턴 검증 함수

config/
  ui_patterns.yaml           # 패턴 정의 + 정책별 매핑

tests/
  test_ransom_ui_scan.py     # 스캔 결과로 자동 검증 실행
```

---

## 8. 2단계 설계 — 리포트 통합

### 리포트 유형

| 유형 | 형식 | 대상 | 현황 |
|------|------|------|------|
| Type 1 | pytest-html | 개발자, 전문가 | 현재 사용 중 (실패 스크린샷만) |
| Type 2 | xlsx | 개발자 + 일반인 | 미구현 |

### 스크린샷 임베딩 방향

- 현재: 테스트 실패 시에만 자동 캡처 (`pytest_runtest_makereport` 훅)
- 목표: 모달 출력 시마다 캡처 → 리포트에 결과와 함께 첨부

```
예시 결과:
  중복 이름 입력 → 에러 모달 출력 → 정상 ✅  [스크린샷]
  빈값 등록 시도 → 에러 모달 출력 → 정상 ✅  [스크린샷]
  확장자 태그 추가 → 정상 ✅                  [스크린샷]
  확장자 삭제 버튼 → 정상 ✅                  [스크린샷]
```

### xlsx 구조 (초안 — 미확정)

```
시트: 정책명 (예: 탐지정책)
  A: UI 요소명
  B: 패턴 유형
  C: 검증 항목
  D: 결과 (✅ 정상 / ❌ 실패 / ⚠️ 버그)
  E: 비고 / 에러 메시지
  F: 스크린샷 경로 (또는 하이퍼링크)
```

---

## 9. 미결 사항 (다른 Claude와 논의 필요)

| # | 항목 | 현재 상태 |
|---|------|-----------|
| 1 | HTML 스캔 방식 | Playwright로 라이브 페이지 스캔 vs HTML 파일 오프라인 분석 |
| 2 | 패턴 매핑 초안 | 수동 작성 vs HTML 스캔 자동 생성 후 검토 |
| 3 | xlsx 시트 구조 | 정책별 시트 분리 vs 단일 시트 |
| 4 | 스캔 범위 | 탐지정책만 vs 다른 정책 모달도 동일 방식 확장 예정 |
| 5 | 패턴 라이브러리 위치 | `pages/patterns/` vs `utils/patterns/` |

---

## 10. 기술적 주의사항 (다음 개발자를 위해)

1. **SPA 네비게이션**: `window.location.hash` 변경 방식으로 이동, `page.goto()`는 전체 리로드라 세션이 끊김
2. **Bootstrap 3 모달**: `.in` 클래스 부착 여부로 열림 감지, `visible` 상태 체크 불가
3. **오버레이 + jQuery 이벤트**: `dispatchEvent()`는 jQuery 위임 핸들러를 트리거하지 않음 → 네이티브 `click()`만 사용
4. **SPA 재주입 타이밍**: 네비게이션 후 `add_init_script`가 오버레이를 재주입 → pointer-events 토글 방식 사용 불가 (JS click 사용 이유)
5. **pageSize=100**: CRUD 후 pageSize가 10으로 리셋됨 → `_restore_page_size()`로 복원 필요
6. **getpass**: pytest의 stdin 캡처를 자동 우회 (`-s` 불필요)
