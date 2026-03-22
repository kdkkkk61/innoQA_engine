# code_log1.md — inno_test_tool 작업 이력 (세션 1)

> 다음 세션에서 이 파일을 먼저 읽고 이어서 작업할 것.
> 프로젝트 루트: `C:\Users\D.K.Kim\cl\inno_test_tool\`

---

## 현재 상태 (2026-03-13 기준)

### 테스트 결과 (마지막 실행)
```
1 failed, 5 passed, 1 skipped in 59.91s
FAILED: test_policy_lifecycle — TimeoutError: div#addItemModal.in (30초 타임아웃)
```

- **test_login** 3개 → ✅ pass
- **test_ransom_detect_policy** 5개 중 4개 pass, 1개 fail (`test_policy_lifecycle`)
- `test_policy_lifecycle` 실패 원인 → 수정 사항 6번 참고
- **아직 재실행 안 함** → 다음 세션에서 첫 번째로 pytest 실행하여 확인할 것

---

## 완료된 수정 사항

### 1. `conftest.py` — logged_in_page 테어다운에 로그아웃 추가
```python
yield page
_remove_overlay(page)
try:
    login.logout()
except Exception as e:
    print(f"\n[logged_in_page 정리] 로그아웃 실패 (무시됨): {e}")
finally:
    context.close()
```
- **이유**: 서버 단일세션 정책 — 이전 실행이 로그아웃 없이 종료되면 다음 실행 시 세션 충돌

### 2. `config/settings.yaml` — slow_mo 변경
```yaml
slow_mo: 500   # 0 → 500 (Bootstrap 3 모달 애니메이션 대기용)
```

### 3. `pages/ransom_detect_policy_page.py` — 선택자 상수 교체
| 삭제 | 추가 |
|------|------|
| `SEL_ADMIN_LINK = "a#__layoutAdminLinkBtn"` (존재하지 않는 요소) | `SEL_LEFT_NAV = "ul.leftNavList"` |
| | `SEL_APP_SETTING_PANEL = "ul.managerAppSettingList"` |
| | `SEL_RC_SECTION_HEADER = "a.managerRansomCruncher"` |

기존 유지:
- `SEL_APP_SETTING_MENU = "a[data-menuid='managerAppSetting']"`
- `SEL_RC_DETECT_POLICY = "a[data-menuid='managerRansomCruncherDetectPolicy']"`

### 4. `pages/ransom_detect_policy_page.py` — navigate_to() 완전 재작성
올바른 네비게이션 흐름:
1. 모달 정리 (`_close_modal_if_open`, `_dismiss_stale_confirm_modal`)
2. 이미 탐지정책 페이지면 즉시 반환 (`SEL_ADD_BTN` visible + URL에 "RansomCruncher" 포함)
3. `manager/main.html` 루트로 강제 goto
4. `ul.leftNavList` 없으면 세션 만료 RuntimeError (3초 조기 감지)
5. `ul.managerAppSettingList` 없으면 `SEL_APP_SETTING_MENU` 클릭해 패널 열기
6. `SEL_RC_DETECT_POLICY` 없으면 `SEL_RC_SECTION_HEADER` 클릭해 아코디언 펼치기
7. `SEL_RC_DETECT_POLICY` 클릭 → `SEL_ADD_BTN` 대기

### 5. `pages/ransom_detect_policy_page.py` — modify_policy() 이름 입력 방식 교체
```python
# 이전 (동작 안 함)
self.page.locator(self.SEL_POLICY_NAME).first.evaluate("el => { el.focus(); el.select(); }")
self.page.locator(self.SEL_POLICY_NAME).first.fill(new_name)

# 현재
loc = self.page.locator(self.SEL_POLICY_NAME).first
loc.evaluate("el => { el.value = ''; }")
loc.fill(new_name)
loc.evaluate("el => el.dispatchEvent(new Event('input',  {bubbles: true}))")
loc.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
```

### 6. `pages/ransom_detect_policy_page.py` — click_policy_row() + modify_policy() 수정 ← 최신
**문제**: `click_policy_row()`에서 `el.click()`만 호출 시 행 선택(파란 하이라이트) 미발생
→ 수정 버튼 클릭 시 "선택된 항목이 없습니다" 모달 발생
→ `_fail_if_modal()`이 수정 버튼 클릭 이전에 위치해 에러를 못 잡고 30초 타임아웃으로 실패

**수정 내용**:

`click_policy_row()` — mousedown/mouseup/click 이벤트 모두 dispatch:
```python
self.page.locator(self.SEL_TABLE_ROW).filter(has_text=policy_name).first.evaluate(
    """el => {
        el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
        el.dispatchEvent(new MouseEvent('mouseup',   {bubbles: true, cancelable: true}));
        el.click();
    }"""
)
```

`modify_policy()` — `_fail_if_modal()` 위치를 수정 버튼 클릭 이후로 이동:
```python
self.click_policy_row(policy_name)
self.wait_for_enabled(self.SEL_MODIFY_BTN)
self.click(self.SEL_MODIFY_BTN)
self._fail_if_modal()   # ← 수정 버튼 클릭 후로 이동 (에러 모달은 여기서 발생)
self.wait_for(self.SEL_ADD_MODAL, state="attached")
```

### 7. `pages/ransom_detect_policy_page.py` — _dismiss_stale_confirm_modal() 추가
navigate_to() 에서 잔여 확인/세션만료 모달 닫기 (1초 타임아웃).

---

## 다음 세션에서 할 일

### Step 1: pytest 실행하여 수정 사항 6번 효과 확인
```bash
cd C:\Users\D.K.Kim\cl\inno_test_tool
pytest tests/ --html=reports/report.html --self-contained-html -v
```

### Step 2a: test_policy_lifecycle pass → 완료
모든 테스트 pass이면 작업 완료.

### Step 2b: test_policy_lifecycle 여전히 실패 시 추가 시도
"선택된 항목이 없습니다" 모달이 아직 발생한다면 → 행 선택 확인 후 진행하도록 수정:
```python
# click_policy_row() 이후, 행이 선택 상태(.active, .selected 등)가 될 때까지 대기
# 또는 tr 요소에 특정 클래스가 추가되는지 확인
```
실제 선택 시 tr에 추가되는 클래스명을 브라우저 DevTools로 확인한 뒤 wait_for 추가.

---

## 파일 구조 (현재)
```
inno_test_tool/
├── CLAUDE.md
├── conftest.py                        ← 수정됨 (logout 추가)
├── config/settings.yaml               ← 수정됨 (slow_mo: 500)
├── pages/
│   ├── base_page.py
│   ├── login_page.py
│   └── ransom_detect_policy_page.py   ← 수정됨 (navigate_to, modify_policy, click_policy_row)
├── tests/
│   ├── test_login.py
│   └── test_ransom_detect_policy.py
├── reports/screenshots/
└── requirements.txt
```

## 실행 명령
```bash
cd C:\Users\D.K.Kim\cl\inno_test_tool
pytest tests/ --html=reports/report.html --self-contained-html -v
```
