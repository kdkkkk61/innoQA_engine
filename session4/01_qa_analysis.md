# QA 전문가 관점 분석 — Universal Page Scanner

작성일: 2026-03-25
대상 플랜: `C:\Users\D.K.Kim\.claude\plans\generic-drifting-cook.md`

---

## 1. 현재 설계의 QA 품질 평가

### 1.1 잘 된 것

| 항목 | 평가 |
|------|------|
| 3-Phase 구조 | Phase 1(초기값+필수), Phase 2(동작), Phase 3(수정) 분리로 책임 명확 |
| known_bug 분리 | fail 카운트에서 제외하되 추적 유지 — 회귀 감지 가능 |
| YAML 기반 테스트 정의 | 테스트 의도가 코드 아닌 선언적 문서로 표현됨 |
| `[AUTO]` 접두사 데이터 안전 규칙 | 실제 데이터 오염 방지 |
| `reset_after` / `reset_tag_after` | 스텝 간 폼 상태 격리 |

### 1.2 누락된 QA 관점 항목

---

## 2. 누락 항목 상세

### 2.1 Phase 간 의존성 오류 처리 부재

**현재 문제:**

```python
# qa_runner.py (계획 중)
report1 = scanner.scan(...)  # Phase 1 — p1_name 저장 시도
...
report2 = scanner.scan(
    context_extra={"existing_name": p1_name},  # Phase 1 성공을 전제
)
```

Phase 1 `close_fn`(save_policy)이 실패하면:
- `[AUTO]_rdp_policy_p1` 정책이 저장되지 않음
- Phase 2의 `existing_name` 중복 검증은 의미없는 값으로 실행됨
- 오류 없이 Phase 2가 진행되어 잘못된 pass 결과가 나옴

**권고:**
```python
# Phase 1 저장 성공 여부를 qa_runner에서 확인
try:
    page_obj.save_policy(p1_name)
    p1_saved = True
except Exception as e:
    p1_saved = False
    # p2의 context_extra에서 existing_name 제거 또는 skip 처리
```

---

### 2.2 실패 시 스크린샷 자동 캡처 없음

**현재:** `BasePage._on_error()`에 스크린샷 있지만 QA 스캔 실패(ScanResult status=fail) 시 캡처 없음.

**현상:** 실패 결과는 텍스트 detail만 남고, 당시 UI 상태 증거 없음.

**권고:**

`core/reporter.py`에서 fail/error 결과 출력 시 스크린샷 경로도 함께 기록:
```python
# ScanResult에 screenshot_path 필드 추가 (Optional[str] = None)
# validators에서 fail 판정 시 ctx.page.screenshot() 저장
```

또는 최소한: `report.failed`가 있으면 `qa_runner.py`에서 스크린샷 1회 촬영:
```python
if combined.failed:
    page.screenshot(path=f"reports/screenshots/fail_{page_id}_{timestamp}.png")
```

---

### 2.3 Phase 3가 Phase 2 정책 존재에 전적으로 의존

**현재 문제:**

```python
# Phase 3 — p2_name 정책이 목록에 있어야 열림
report3 = scanner.scan(
    modal_open_fn=lambda: page_obj.open_modify_modal(p2_name),
    ...
)
```

Phase 2 저장 실패 시:
- `open_modify_modal(p2_name)` → 행을 찾지 못함 → Exception
- finally 블록에서 `delete_all_auto_policies()` 실행
- report3=None으로 처리됨 → **Phase 3 테스트 결과가 통째로 누락**

**권고:**
```python
# Phase 2 저장 성공 여부 추적
p2_saved = False
def close_phase2():
    nonlocal p2_saved
    page_obj.save_policy(p2_name)
    p2_saved = True

# Phase 3 조건부 실행
if p2_saved:
    report3 = scanner.scan(...)
else:
    print(f"  ⏭ Phase 3 스킵 — p2 저장 실패")
```

---

### 2.4 p2_name 포맷에서 page_id 포함 시 이름 길이 문제

**현재 계획:**
```python
p1_name = f"[AUTO]_{page_id}_p1"
p2_name = f"[AUTO]_{page_id}_p2"
```

예: `ransom_detect_policy` → `[AUTO]_ransom_detect_policy_p1` = 30자

**문제:**
- `ransom_detect_policy`의 정책 이름 maxlength = **20**
- 저장 시 앱이 20자로 잘라버리거나 에러 발생
- Phase 2 중복 이름 테스트에서 `existing_name`이 실제 저장된 이름과 달라짐

**권고:**

Page 클래스에서 `AUTO_NAME_PREFIX` 클래스 상수 정의:
```python
class RansomDetectPolicyPage(BasePage):
    AUTO_NAME_PREFIX = "[AUTO]_det"   # 10자 — maxlength=20 내

# qa_runner.py
p1_name = f"{page_obj.AUTO_NAME_PREFIX}_p1"
p2_name = f"{page_obj.AUTO_NAME_PREFIX}_p2"
```

또는 qa_runner에서 maxlength 확인 후 truncate:
```python
# YAML text_inputs에서 required=True 필드의 maxlength 읽어 제한
```

---

### 2.5 모달이 이미 열린 상태에서 Phase 시작될 경우 처리 없음

**시나리오:**
1. Phase 1 `close_fn`에서 `page_obj.save_policy()` 호출 중 타임아웃
2. 모달이 열린 채로 Phase 2 `modal_open_fn` 호출
3. `click(SEL_ADD_BTN)` → 두 번째 모달이 이미 열린 상태 → 예상치 못한 동작

**권고:**
`qa_runner.py`의 각 Phase 시작 전 모달 상태 초기화:
```python
def _ensure_modal_closed(page_obj):
    try:
        if page_obj.page.locator(page_obj.SEL_ADD_MODAL).count() > 0:
            page_obj.close_modal()
    except Exception:
        page_obj.navigate_to()  # 네비게이션으로 강제 초기화
```

---

### 2.6 report3=None일 때 combined 리포트 Phase 3 누락 표시 없음

**현재 코드:**
```python
reports = [r for r in (report1, report2, report3) if r is not None]
combined = PageScanReport.merge(*reports)
```

report3=None이면 combined에 Phase 3 데이터가 없지만 출력에서 아무 언급 없음.

**권고:**
```python
if report3 is None:
    print(f"  ⏭ [Phase 3] 실행되지 않음 (Phase 2 사전조건 미충족)")
```

---

### 2.7 `delete_all_auto_policies()` finally 블록 실패 시 오염 데이터 잔류

**현재:** finally 블록 내 Exception을 pass로 무시:
```python
finally:
    try:
        page_obj.navigate_to()
        page_obj.delete_all_auto_policies()
    except Exception:
        pass   # ← 정리 실패 시 [AUTO] 정책이 잔류
```

**문제:** 다음 테스트 실행 시 잔류 정책이 중복 이름 충돌 유발.

**권고:**
정리 실패 시 경고 출력:
```python
except Exception as e:
    print(f"\n  ⚠️  [{page_id}] 정리 실패 — 잔여 [AUTO] 정책이 남아있을 수 있습니다: {e}")
```

---

### 2.8 각 페이지별 테스트 격리 수준

**현재 격리 수준:** 세션 공유 (`logged_in_page` — 로그인 1회 후 전체 테스트 공유)

**parametrize 환경에서 문제:**
- `ransom_detect_policy` 테스트 중 세션 만료 → `rdp_policy` 테스트도 실패
- 한 페이지 테스트의 잔여 모달이 다음 페이지 테스트에 영향

**권고:**
`qa_runner.py`에서 각 page_id 시작 시 세션 유효성 확인:
```python
if not page_obj.page.locator("ul.leftNavList").is_visible():
    raise RuntimeError(f"[{page_id}] 세션 만료 — pytest를 재실행하세요")
```

---

## 3. 추가 권고 사항 (우선순위 낮음)

### 3.1 Phase 1/2 결과를 별도 리포트 파일로 저장

```
reports/
  scan_ransom_detect_policy_20260325_143022.json
  scan_rdp_policy_20260325_143155.json
```

회귀 비교 시 이전 결과와 diff 가능.

### 3.2 `button_action` 패턴 Phase 2에서만 실행되는지 확인

현재 `button_actions` (전체선택 버튼 등)은 Phase 구분 없이 실행됨. Phase 1 초기값 스냅샷 중 버튼 클릭이 발생하지 않도록 Phase 제한 확인 필요.

### 3.3 YAML `order` 값 중복 감지

같은 order 값을 가진 두 필드가 있으면 출력 순서가 비결정적. YAML 로딩 시 order 중복 경고 출력 권고.

---

## 4. 요약

| 우선순위 | 항목 | 영향 |
|----------|------|------|
| 🔴 HIGH | 2.4 p2_name 길이 초과 (maxlength) | 저장 실패 → Phase 3 통째 스킵 |
| 🔴 HIGH | 2.1 Phase 간 의존성 오류 처리 | 잘못된 pass 결과 출력 |
| 🟡 MED | 2.3 Phase 3 조건부 실행 | 불명확한 테스트 결과 |
| 🟡 MED | 2.5 모달 열린 상태 Phase 시작 | 불안정한 테스트 |
| 🟡 MED | 2.2 실패 시 스크린샷 없음 | 디버깅 증거 부재 |
| 🟢 LOW | 2.6 report3=None 미표시 | 결과 가독성 |
| 🟢 LOW | 2.7 정리 실패 무시 | 데이터 오염 잠재 리스크 |
| 🟢 LOW | 2.8 페이지 간 격리 | 세션 공유 환경 한계 |
