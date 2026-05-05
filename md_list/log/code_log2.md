# inno_test_tool 개발 로그 (2권)

> 1권 요약: MVP 완성, 로그인 3개 테스트 pass, 오버레이/배너 구현 완료.
> 이 로그는 RansomCruncher 탐지정책 CRUD 자동화 작업 기록이다.

---

## 현재 상태 (2026-03-19 기준)

### 테스트 결과
```
test_login.py         3개 pass  (완료)
test_ransom_detect_policy.py
  test_policy_lifecycle        FAIL  <- 현재 작업 중
  test_policy_name_validation  SKIP (lifecycle 의존)
  test_extension_validation    pass
  test_toggle_activation       pass
```

### 통과한 단계
| 단계 | 내용 | 상태 |
|------|------|------|
| 초기 정리 | delete_all_auto_policies | OK |
| 1 정책 생성 | add_policy("[AUTO]_lifecycle", ["txt"]) | OK |
| 2 수정 | modify_policy -> [AUTO]_lifecycle_수정 | OK |
| 3 복사 | copy_policy -> [AUTO]_lifecycle_수정 (1) 생성 | OK |
| 4 복사본 수정 | modify_policy -> [AUTO]_lifecycle_복사_수정 | FAIL |
| 5 전체 삭제 | delete_all_auto_policies | 미도달 |
| 6 초기 상태 비교 | final == initial | 미도달 |

---

## 주요 해결 이력

### 1. 확인 버튼 클릭 실패 (Bootstrap 3 모달)
- 문제: .btn-primary 로 확인 버튼을 못 찾음 (gray 버튼인 경우)
- 원인: 성공/오류 모달 확인 버튼이 btn-default 클래스 사용
- 해결: SEL_CONFIRM_BTN = "div#__globalMessageModal button:has-text('확인')" 으로 텍스트 매칭

### 2. 복사 후 목록 미갱신 (75->75 문제)
- 문제: 복사 전 75개 -> 복사 후 75개로 검출됨
- 원인: copy_policy() 내부에서 navigate_to() 조기 반환 (early return 조건 충족)
- 해결: 복사 후 테이블 행 attached 5초 대기 추가

### 3. 복사 검증 방식 오류 (전체 이름 집합 비교)
- 문제: 복사 후 75->0개로 검출 (SPA 테이블 로딩 전에 읽음)
- 원인: 해시 이동 후 ADD_BTN은 빠르게 나타나지만 테이블 행은 늦게 로드됨
- 해결: 전체 75개 비교 -> [AUTO] 접두사만 필터링해 집합 차이 계산
  - 복사 전: {'[AUTO]_lifecycle_수정'}
  - 복사 후: {'[AUTO]_lifecycle_수정', '[AUTO]_lifecycle_수정 (1)'}
  - 차이: {'[AUTO]_lifecycle_수정 (1)'} -> copied_name 확정

### 4. 복사본 이름 하드코딩 제거
- 문제: "(1)" suffix 규칙이 기능마다 다를 수 있음
- 해결: set 차이로 복사본 이름 동적 감지 (이름 하드코딩 없음)

### 5. add_policy 성공 모달 오판
- 문제: "저장 하였습니다" 성공 모달을 오류로 판단 -> Exception 발생
- 해결: 모달 메시지 먼저 읽고 "이미 등록되어 있습니다" 만 중복 오류로 처리

### 6. check_policy_row jQuery 이벤트 문제
- 문제: dispatchEvent(change) 방식으로는 Angular 모델 미반영
- 원인: jQuery는 document 레벨 click 이벤트 위임 처리 (list-checkbox-item 커스텀 디렉티브)
  - dispatchEvent 로는 jQuery 핸들러 트리거 안 됨
- 해결: 오버레이 pointer-events 일시 none -> Playwright 네이티브 click() -> 복원
  - 네이티브 클릭만이 실제 브라우저 이벤트를 생성해 jQuery 위임 핸들러를 트리거

### 7. delete_policy 에러 모달 미처리
- 문제: "선택된 항목이 없습니다" 에러 모달을 조용히 통과 -> 삭제 안 됨
- 해결: 모달 메시지 체크 추가 - "하시겠습니까" 가 없으면 Exception 발생

### 8. modify_policy 중복 이름 저장 실패 감지
- 문제: 중복 이름 시 에러 모달 처리 후 수정 모달이 열린 채 남음 -> 조용히 실패
- 해결: 저장 후 addItemModal.in 존재 여부 체크 -> 존재하면 닫고 Exception 발생

---

## 현재 진행 중인 버그 (step 4 수정 실패)

### 증상
```
AssertionError: 복사 정책 수정 실패: [AUTO]_lifecycle_복사_수정 이 목록에 없음
copied_name = '[AUTO]_lifecycle_수정 (1)'
```
- modify_policy() 가 예외 없이 정상 반환
- 하지만 is_policy_exists('[AUTO]_lifecycle_복사_수정') = False

### 유력 가설: CRUD 후 pageSize URL 리셋 버그
```
modify_policy 실행 순서:
  1. 성공 모달 처리 완료
  2. wait_for(ADD_BTN) -> 반환 (ADD_BTN은 pageSize=20 에서도 보임)
  3. SPA가 URL을 pageSize=20 기본값으로 리셋
  4. is_policy_exists() -> get_policy_names() -> 첫 20개만 조회
  5. '[AUTO]_lifecycle_복사_수정' 이 20위권 밖이면 False
```

동일 문제가 delete_all_auto_policies 에서도 발생 가능:
```
delete_policy 후 pageSize=20 리셋
-> get_policy_names() -> 첫 20개만 조회
-> 20위 밖의 [AUTO] 정책 못 찾음 -> while 루프 조기 종료
```

### 수정 방향
_restore_page_size() 헬퍼 추가:
```python
def _restore_page_size(self) -> None:
    if "pageSize=100" not in self.page.url:
        self.page.evaluate("window.location.hash = '#!/managerRansomCruncherDetectPolicy..."
        # 테이블 행 로드 대기 (5초)
```
- modify_policy, copy_policy, delete_policy 종료 시 모두 호출

---

## 관찰된 현상 설명

### "로그인을 두 번 하는 것 같다"
정상 동작이다. 두 번의 로그인은 서로 다른 컨텍스트:
1. test_login.py -> fresh_page (function-scope, 매 테스트 새 컨텍스트, 3개 테스트)
2. test_ransom_detect_policy.py -> logged_in_page (session-scope, 1회만 로그인)
   - test_login.py 완료 직후 생성되어 연속으로 두 번 로그인처럼 보임
   - 이는 설계상 의도된 것 (서로 다른 브라우저 컨텍스트 사용)

### "[AUTO] 잔재 삭제 기능이 없어진 것 같다"
코드상 delete_all_auto_policies() 함수는 존재하며 작동 중이다.
다만 pageSize 리셋 버그로 인해 20위권 밖의 [AUTO] 정책을 못 찾는 경우 있음.
[AUTO] 정책은 최신 순 정렬 1~2위에 위치하므로 대부분 정상 동작.
pageSize 복원 헬퍼 추가 후 완전 해결 예정.

---

## 아키텍처 현황

```
pages/
  base_page.py              <- click, fill, wait_for, click_attached 등 공통
  login_page.py             <- 로그인/로그아웃
  ransom_detect_policy_page.py  <- 탐지정책 CRUD (현재 작업 파일)

tests/
  test_login.py             <- 로그인 3개 테스트 (fresh_page)
  test_ransom_detect_policy.py  <- 탐지정책 4개 테스트 (logged_in_page)

conftest.py                 <- fixture, 오버레이, 스크린샷 훅
config/settings.yaml        <- URL, 브라우저 설정
```

## BasePage 핵심 메서드

| 메서드 | 설명 |
|--------|------|
| click(sel) | wait_for(visible) -> el.click() JS 직접 호출 (오버레이 우회) |
| click_attached(sel) | wait_for(attached) -> el.click() (Bootstrap 3 모달 내부 버튼용) |
| fill(sel, text) | wait_for(visible) -> fill() |
| wait_for(sel, state) | locator.first.wait_for(state) |

## RansomDetectPolicyPage 핵심 패턴

```python
# 체크박스 클릭 (jQuery 이벤트 위임 대응)
# 오버레이 pointer-events=none -> 네이티브 click -> all 복원

# 행 클릭 (tr.tActive 확인)
# 오버레이 비활성화 -> 네이티브 click -> 복원 -> tActive 3회 재시도

# 모든 CRUD: _attempt() + except -> navigate_to() + retry 패턴

# navigate_to() early return 조건:
# ADD_BTN visible AND "RansomCruncher" in URL AND "pageSize=100" in URL
```

---

## ✅ 2권 완료 (2026-03-19)

**7 passed in 62.97s**

```
test_login.py                          3 passed
test_ransom_detect_policy.py
  test_policy_lifecycle                passed  ← 핵심 CRUD 전체 흐름
  test_policy_name_validation          passed
  test_extension_validation            passed
  test_toggle_activation               passed
```

---

## 3권 예정: 리팩토링

### 목표
기능 동작은 완전하므로 코드 품질 개선. 파일 분리 없이 내부 정리만.

### 작업 범위

#### 1. base_page.py — `_toggle_overlay()` 공통 헬퍼 추가
ransom_detect_policy_page.py 에서 동일 JS 코드 2회 반복 → BasePage로 이동

```python
def _toggle_overlay(self, enabled: bool) -> None:
    value = "all" if enabled else "none"
    self.page.evaluate(
        f"var el = document.getElementById('qa-block-overlay');"
        f"if (el) el.style.pointerEvents = '{value}';"
    )
```

#### 2. ransom_detect_policy_page.py — 내부 정리
- **타임아웃 상수화**: 5000/3000/1000ms 매직 넘버 7곳 → 클래스 상수 3개
  ```python
  _TIMEOUT_TABLE = 5000   # 테이블 XHR 완료 대기
  _TIMEOUT_MODAL = 3000   # 모달 응답 대기
  _TIMEOUT_STALE = 1000   # 잔여 모달 빠른 확인
  ```
- **URL 해시 상수화**: 동일 해시 문자열 3곳 반복 → `_HASH_PAGE_SIZE_100` 상수
- **`_toggle_overlay()` 호출 교체**: 인라인 JS → BasePage 메서드 호출 (2곳)
- **`_validate_name_length()` 헬퍼 추출**: add_policy/modify_policy 중복 maxlength 검증 통합
  ```python
  def _validate_name_length(self, name: str, selector: str) -> None:
      loc = self.page.locator(selector).first
      maxlen = loc.get_attribute("maxlength")
      if maxlen and len(name) > int(maxlen):
          raise ValueError(f"이름이 maxlength({maxlen}자)를 초과: {name!r} ({len(name)}자)")
  ```

#### 3. 수정하지 않는 파일
- `conftest.py`, `login_page.py`, `tests/` — 동작 완전, 변경 없음

### 검증
리팩토링 후 `pytest tests/ -s -v` → **7 passed 유지 확인**
