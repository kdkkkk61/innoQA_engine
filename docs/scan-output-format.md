# 스캔 결과 출력 형식

> 태그: [확장 경로 — modal_form 전용]
> 이 문서는 modal_form 계열 페이지에만 적용된다. list_page 계열(nPouch 등)은 해당 없음.
> 출력 순서나 toggle 종속 필드 표현에 문제가 있을 때 이 문서를 읽는다.

---

## 핵심 원칙: 화면 순서 = 출력 순서

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
  ✅ [text_input] 정책 이름                  ← order=10
  ✅ [plain_checkbox] 소프트웨어 인증 사용   ← order=30
  ✅ [radio_group] 행위기반 탐지등급         ← order=40
  ✅ [toggle_checkbox] 롤백 기능 사용        ← order=80
       └ ✅ [number_input] 복구 대상파일 최대용량
       └ ✅ [number_input] 차단 후 롤백 대기시간
  ✅ [toggle_checkbox] 프로세스 격리기능     ← order=90
       └ ✅ [plain_checkbox] 격리 프로세스 삭제
```

---

## 출력 구현 필수 요건

1. **정렬**: `order` 값 오름차순. `order` 없는 항목은 맨 뒤.
2. **탭 구간 헤더**: `report.tab_sections`를 이용해 탭 경계마다 구분선 출력.
   - `required_submit` 패턴은 탭 구분 제외 (항상 마지막, order 9999).
   - 시나리오 4-3 패턴 (`list_modify_required` / `modify_required`)은 일반 정렬 적용
     (시나리오 4 영역 안에 위치 — order 4-2 다음, 시나리오 5 이전).
   - DOM 스캔 패턴 (`discovered_new` / `discovered_missing`)은 시나리오 1 영역
     마지막에 위치 — 검수자가 즉시 인지하도록 시나리오 1 끝 (order: 시나리오 1 범위
     안에서 가장 큰 값, 다른 시나리오보다는 앞).
   - 자동 분류 패턴 (`discovered_fill` / `discovered_case` / `[신규]` prefix 라벨)은 해당
     시나리오 영역 안의 일반 카드와 함께 정렬 (시나리오 2~5 각 영역 끝).
   - 탭 없는 페이지도 동일 코드 사용 (단순히 헤더 출력 안 됨).
3. **종속 필드**: `toggle_checkbox`의 `dep_fields`는 부모 바로 아래 `└` 트리로 출력.
   - `r.extra.get("dependent_labels")` / `dependent_types` / `dependent_results` 활용.
4. **새 테스트 파일 추가 시**: `_print_phase_report`에 탭 헤더 + toggle dep 필드 출력 코드 반드시 포함.

### 자동 분류 패턴 매핑 (B-1 시리즈)

| pattern | 등장 시나리오 | label 형식 | 회귀 본질 |
|---|---|---|---|
| `discovered_new` | 1 | `신규 기능 감지 — "label" (selector)` | DOM 추가 감지 |
| `discovered_missing` | 1 | `제거된 기능 — "label" (selector)` | DOM 제거 감지 |
| `text_input` / `plain_checkbox` / `toggle_checkbox` / `radio_group` / `tag_input` (라벨에 `[신규]` prefix) | 2 | `[신규] {라벨}` | 신규 요소 동작 검증 |
| `discovered_fill` | 3 | `[신규] {라벨}` | 신규 필드 추가 흐름 자동 채우기 |
| `initial_state` (라벨에 `[신규]` prefix) | 4 | `[신규] {라벨} 로드값 확인` | 신규 필드 EDIT 모달 default 유지 |
| `discovered_case` | 5 | `[신규] [{case_label}] {라벨}` | 신규 필드 케이스(ON/OFF) 시점 DOM 값 |

상세 정의는 `test_scenario_standard.md` "자동 분류 메커니즘 (B-1 시리즈)" 와 각 시나리오
문서의 "자동 검증 카드" 섹션 참조.

---

## toggle dep 필드 출력 패턴

(코드 예시: `sorted(report.results, key=_sort_key)` 순회 → `toggle_checkbox` 행에서 `r.extra`의 `dependent_labels` / `dependent_types` / `dependent_results` 꺼내 `└` 들여쓰기로 하위 필드 출력)

---

## YAML order 값 규칙

- 화면 상단 요소 = 낮은 order 값 / 하단 요소 = 높은 order 값
- 10단위 간격 유지 (중간 삽입 여유 확보)
- toggle의 `dep_fields`는 별도 order 없이 부모 order에 귀속
- 탭 구분 범위: 정책정보 탭 10~199 / 예외처리 탭 200~299 / 제출 9999

---

## 관련 문서

- `docs/test-pipeline.md` — 파이프라인 전체 구조, 두 계열 비교
- `docs/yaml-guide.md` — YAML 필드 구성 작성 규칙
