# 시나리오 3: 동작 검증

> 목적: 실제 CRUD 전체 흐름 + 페이지에서 발생 가능한 비정상 케이스 에러 처리 확인.
> 비정상 케이스 범위는 페이지 특성에 따라 해당되는 항목을 선택해 구현한다.

---

## 반드시 커버해야 할 항목

| 카테고리 | 내용 | 비고 |
|----------|------|------|
| **비정상 케이스** | 아래 목록 중 해당 항목 선택 | 없는 항목은 SKIP |
| **추가 (C)** | 항목 생성 → 목록 확인 | 필수 |
| **저장값 확인** | 추가 후 수정 모달에서 전 필드 대조 | 필수, 실행경로 포함 |
| **수정 (U)** | 필드 변경 → 저장 → 목록 잔존 + 수정값 재확인 | 필수 |
| **삭제 (D)** | 항목 삭제 → 목록에서 사라짐 확인 | 필수 |

---

## 비정상 케이스 카테고리 (해당되는 것만 구현)

| 케이스 | 적용 조건 | 예시 |
|--------|----------|------|
| 미선택 수정 경고 | list_page, 행 선택 후 수정 버튼 구조 | "선택된 항목이 없습니다." |
| 미체크 삭제 경고 | list_page, 체크박스 + 삭제 버튼 구조 | "삭제할 항목을 체크해 주세요." |
| 오버플로 입력 | 텍스트/태그 입력 필드 있는 경우 | 매우 긴 문자열 입력 → 서버 에러 여부 |
| 경계값 입력 | 숫자 필드 있는 경우 | min/max 초과값 입력 → 클램핑 or 에러 |
| 특수문자 입력 | 이름 필드에 제한 있는 경우 | 특수문자 입력 → 통과 or 에러 |
| 중복 저장 시도 | 고유 이름 필드 있는 경우 | 동일 이름 추가 → 에러 메시지 |
| 복사 기능 | 복사 버튼 있는 경우 | 복사 후 이름 변경 여부 확인 |
| 읽기 전용 필드 | 수정 모달에서 disabled 필드 | 수정 불가 필드 확인 |

> 위 중 해당 없는 항목은 `[SKIP] {케이스명} — 해당 없음 (이유)` 으로 기록

---

## 다른 시나리오와 책임 분리

| 영역 | 시나리오 |
|------|----------|
| **CRUD 1사이클 흐름** | 시나리오 3 (추가→저장값 확인→수정→삭제) |
| **수정 흐름의 정합성 깊이** | 시나리오 4 (전 필드 로드 + 변경 재확인 + 위반 결과) |
| **입력 조합 (전체/최소) 정합성** | 시나리오 5 (정상 입력 조합) |
| **입력 검증 동작 유무 (1차)** | 시나리오 2 (빈값 제출 → 경고 떴는가) |

→ 비정상 케이스 중 "EDIT 모달 필수 비움 후 결과"는 **시나리오 4-3**에서 처리.
   시나리오 3은 ADD/CRUD 흐름 + 카테고리별 비정상 입력에 집중.

---

## 코드 패턴 참조

### 비정상 케이스 — list_page (nPouch 계열)

```python
# 미선택 수정
page.locator("button#modifyItemBtn").first.evaluate("el => el.click()")
p.page.wait_for_timeout(400)
if p.is_confirm_modal_visible():
    msg = p.get_modal_message()
    expected = "선택된 항목이 없습니다."  # yaml error_messages 참조
    t, s = _r("pass" if msg == expected else "warn",
              "수정 버튼 — 미선택 시 경고",
              f"입력: 미선택 상태로 수정 버튼 클릭 / 결과: {msg!r}", sc=3)
    p.dismiss_confirm_modal()
```

### CRUD + 저장값 확인 — list_page (nPouch 계열)

```python
# 추가 — 가능한 모든 필드 채워서 생성
p.add_item(_AUTO_NAME, **FIELD_VALUES)
# add_item에 없는 필드는 수정 모달로 보완 후 저장
p.search_item(_AUTO_NAME)
exists = _AUTO_NAME in p.get_item_names()
t, s = _r("pass" if exists else "fail", "항목 추가 — 목록 확인",
          f"입력: {_AUTO_NAME!r} + 전체 필드 / 결과: {'목록에 존재' if exists else '없음'}", sc=3)

# 저장값 확인 — 전 필드 수정 모달에서 대조 (실행경로 포함)
p.open_modify_modal(_AUTO_NAME)
for sel, label, expected in FIELD_VERIFY_LIST:  # yaml 또는 클래스 상수 참조
    loaded = p.get_field_value(sel)
    t, s = _r("pass" if loaded == expected else "fail", label,
              f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=3)
p.close_modal()

# 수정 — 특정 필드 변경 후 저장, 수정값 재확인
p.open_modify_modal(_AUTO_NAME)
p.page.locator(SEL_TARGET_FIELD).first.fill(NEW_VALUE)
p.click_attached(SEL_SUBMIT_BTN)
p._handle_confirm_modal()
p.search_item(_AUTO_NAME)
# 수정 후 모달 재오픈 → 변경값 확인
p.open_modify_modal(_AUTO_NAME)
loaded = p.get_field_value(SEL_TARGET_FIELD)
t, s = _r("pass" if loaded == NEW_VALUE else "fail", "수정값 재확인",
          f"입력: {NEW_VALUE!r} 수정 / 결과: {loaded!r}", sc=3)
p.close_modal()

# 삭제
p.delete_item(_AUTO_NAME)
p.search_item(_AUTO_NAME)
gone = _AUTO_NAME not in p.get_item_names()
t, s = _r("pass" if gone else "fail", "항목 삭제 — 목록에서 사라짐",
          f"입력: {_AUTO_NAME!r} 삭제 / 결과: {'목록에서 사라짐' if gone else '아직 존재'}", sc=3)
```

### CRUD — modal_form (RansomCruncher 계열)

```python
# scan_hints yaml의 crud 섹션 참조
# 복사/삭제는 [AUTO] 접두사 정책만 허용
# copy_item → rename → verify → delete 흐름
```

---

## 저장값 확인 원칙

- 추가 후 수정 모달에서 **모든 필드** 값을 대조한다
- 필드 목록은 yaml의 `fields` 섹션 전체 (실행경로 등 선택 필드 포함)
- SHA2 / 긴 문자열: 전체 비교 어려우면 앞 20자 + 존재 여부로 확인
- 수정 후에도 **모달 재오픈 → 변경값 재확인** 필수

---

## 주의사항

- 비정상 케이스는 "전부 다" 가 아니라 **페이지에 해당되는 것만** 구현
- 해당 없는 케이스는 코드에서 생략하지 말고 `[SKIP]`으로 기록
- CRUD 순서: 추가 → 저장값 확인 → 수정 → 수정값 재확인 → 삭제

---

## 자동 검증 카드 (신규 발견 요소 — `discovered_fill`)

시나리오 1 의 `discovered_new` 로 발견된 yaml 미등록 신규 필드는 시나리오 3 (생성 흐름)
영역에도 **자동으로 카드 등록**된다. 추가 흐름(`save_policy` 직전) 에 끼어들어
신규 text/number 필드는 자동 채워보고, 신규 checkbox/toggle/radio 는 default 유지로 통과.

### 동작 분기 (DOM type 기반)

| DOM type | 동작 | status | detail 예시 |
|---|---|---|---|
| `text` / `number` / `textarea` / `password` / `email` | `fill()` 로 자동 채우기 (값: `core/qa_runner.py:_fill_discovered_text_fields` 참조 — number 는 `"1"`, 그 외 `"auto_test"`) | pass (성공) / skip (disabled) | `타입: text / "auto_test" 자동 입력 (시나리오 3 추가 흐름)` |
| `checkbox` / `radio` | 동작 안 함 — default 유지 | pass | `타입: checkbox / default 유지 (시나리오 3 추가 흐름 영향 없음)` |
| 그 외 (select 등) | 미지원 | skip | `타입: ? / 미지원` |

→ **추가 흐름에 영향 없음**: 신규 필드 채우기 실패해도 기존 정책 추가 자체는 정상 진행.
   신규 필드 검증 결과는 별도 카드로만 등장.

### 카드 라벨 컨벤션

- `label = "[신규] " + 한국어 라벨` (예: `[신규] 소프트웨어 인증 사용`)
- `detail = "[자동 분류 — yaml 미등록] " + 동작 설명`
- pattern: `discovered_fill`
- 시나리오 3 영역 끝 (order: 시나리오 3 범위 최대 — 일반 동작 카드 다음)

### 종속 필드 한계 (현재 미지원)

- 자동 발견된 신규 필드의 **종속 관계는 모름** (DOM 만으로는 매칭 불가).
- 신규 toggle 의 dependent_fields 는 빈 list 로 시작 → 단독 검증만.
- yaml 등록 시 정식 종속 매핑 시작 (자동 종속 매칭은 현재 미지원).

### 회귀 안전

- 추가 모달이 열린 상태(`save_policy` 직전 시점) 에서만 실행.
- 자동 채우기 실패 (disabled / 숨김 등) 는 무시 — 정책 추가 흐름 깨지지 않게.
- 자동 분류 결과 자체가 검증 목적 — pass/skip 표시.

→ 자동 분류 메커니즘 전체 흐름은 `test_scenario_standard.md` "자동 분류 메커니즘 (B-1 시리즈)" 참조.
