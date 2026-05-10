# 테스트 시나리오 표준 — 개요 및 사용 정의

> 작성일: 2026-04-21 / 최종 수정: 2026-04-30
> QA 자동화 테스트의 6개 시나리오 구조와 공통 규칙을 정의한다.
> 세부 검증 항목은 각 시나리오 파일 참고.

> **2026-04-30 변경**: 시나리오 2/4의 책임 영역 명확화
> - 시나리오 2 = 입력 검증 동작 유무 (1차) — 추정 금지
> - 시나리오 4 = 수정 흐름 전체 정합성 (정상 + 위반 결과 4-3 추가)
>
> **2026-05-06 변경**: 시나리오 1 책임 확장
> - 시나리오 1 = UI 구조 + **DOM 스캔 ↔ yaml 비교** (회귀 본질 — 신규/제거 감지)
>
> **2026-05-08 변경**: 자동 분류 메커니즘 (B-1 시리즈) 도입
> - 시나리오 1 신규 발견 → DOM type 기반 분류 → 시나리오 2~5 영역에 자동 카드 등록
> - 검수자가 신규 기능에 대해서도 시나리오 1~5 각 영역에서 결과 확인 가능
> - 기존 validator 재활용 (text_inputs / plain_checkboxes / toggle_checkboxes)
> - 라벨 컨벤션: `[신규]` prefix + 케이스명 prefix (`[전체 ON]` / `[전체 OFF]`)

---

## 파일 구조

```
docs/
├── test_scenario_standard.md   ← 이 파일 (개요 + 공통 규칙)
├── scenario_1_ui.md            ← 시나리오 1: UI 구조
├── scenario_2_input.md         ← 시나리오 2: 입력 구조
├── scenario_3_action.md        ← 시나리오 3: 동작 검증
├── scenario_4_modify.md        ← 시나리오 4: 수정 시나리오
├── scenario_5_cases.md         ← 시나리오 5: 케이스 검증
└── scenario_6_suite_setup.md   ← 시나리오 6: 연계 데이터 준비

config/scan_hints/
└── {page_id}.yaml              ← 페이지별 필드 구성 (Chrome MCP 직접 확인)
```

---

## 6개 시나리오 요약

| 번호 | 이름 | 목적 | 적용 |
|------|------|------|------|
| **1** | UI 구조 | 화면 요소 존재 확인 + **DOM ↔ yaml 비교 (신규/제거 감지)** | 전 페이지 |
| **2** | 입력 구조 | 필드 구조 + **입력 검증 동작 유무 (1차)** | 모달 있는 페이지 |
| **3** | 동작 검증 | CRUD 흐름 + 비정상 케이스 | 전 페이지 |
| **4** | 수정 시나리오 | 저장값 로드 + 수정 후 재확인 + **위반 입력 결과 (4-3)** | 전 페이지 |
| **5** | 케이스 검증 | 전체 필드 / 필수만 — 저장 재확인 (정상 조합) | 모달 있는 페이지 |
| **6** | 연계 데이터 준비 | 다음 테스트에서 사용할 항목 생성 후 남겨둠 | 연계 대상 있는 페이지 |

### 책임 분리 매트릭스 (위반 입력 처리)

| 단계 | 시나리오 | 무엇을 보는가 |
|------|----------|---------------|
| 1차 — 입력 검증 동작 | 시나리오 2 | "빈 값 제출 → 경고 떴는가" (Yes=pass, No=fail) |
| 2차 — 위반 통과 후 결과 | 시나리오 4-3 | "재오픈 시 실제 값" (빈값=fail / 원본=warn / 다른값=fail) |

### 책임 분리 매트릭스 (회귀 본질 — 변화 감지)

| 변화 종류 | 시나리오 | pattern | status |
|-----------|----------|---------|--------|
| 신규 요소 (DOM 추가) | 시나리오 1 | `discovered_new` | warn |
| 제거된 요소 (DOM 누락) | 시나리오 1 | `discovered_missing` | warn |
| 정의된 요소 동작 검증 | 시나리오 2~5 | 패턴별 | pass/fail/warn |
| 신규 요소의 자동 동작 검증 | 시나리오 2 | `text_input` / `plain_checkbox` / `toggle_checkbox` (`[신규]` 라벨) | pass/fail/warn |
| 신규 요소의 자동 채우기 (CRUD 추가 흐름) | 시나리오 3 | `discovered_fill` | pass/skip |
| 신규 요소의 자동 로드값 확인 (수정 흐름) | 시나리오 4 | `initial_state` (`[신규]` 라벨) | pass/fail |
| 신규 요소의 자동 케이스 분류 (ON/OFF 시점) | 시나리오 5 | `discovered_case` | pass |

**추정 금지**: 시나리오 2에서 "경고 안 뜸 → 저장됐겠지" 같은 추정으로 결론내지 말 것.
실제 결과는 시나리오 4-3가 직접 재오픈 후 확인한다.

**fail vs error 구분 재확인**: error는 테스트 도구 자체 오류(셀렉터·타임아웃)에만 사용.
"제품의 예상 못한 동작"은 fail. 4-3의 "다른값" 케이스도 fail.

> 해당 시나리오가 없으면: `[SKIP] 시나리오 N — 해당 없음 (이유)` 출력

---

## 자동 분류 메커니즘 (B-1 시리즈)

신규 발견 요소(시나리오 1의 `discovered_new`)는 그 시점에 멈추지 않고
**시나리오 2~5 영역에도 자동으로 검증 카드를 등록**한다. 검수자가 신규 기능에 대해
"이 기능이 시나리오별로 어떻게 동작하는가"를 한눈에 확인할 수 있게 하는 핵심 회귀 본질.

### 원칙: 기존 시나리오 재활용 (참조 테스트)

신규 요소를 위한 별도 검증 로직을 새로 작성하지 않는다. 대신:
1. DOM 속성으로 신규 요소를 **공통 타입에 매핑**한다 (text_input / plain_checkbox / toggle_checkbox).
2. 매핑된 타입에 따라 **기존 validator를 재호출**한다.
3. 검증 결과 카드에 `[신규]` prefix 부착해 검수자가 자동 분류 카드를 즉시 식별 가능하게 한다.

→ "참조 테스트" — 같은 UI 패턴의 신규 요소는 기존 validator 그대로 사용.
→ "공통 시나리오 부분 참조" — 신규 요소가 시나리오 3·4·5 흐름의 일부 (예: 추가 모달 채우기,
   수정 모달 로드값 확인) 에 자연스럽게 끼어든다.

### DOM type → validator 매핑

| DOM type 속성 | 매핑된 validator | 시나리오 2 카드 패턴 |
|---|---|---|
| `text` / `textarea` / `number` / `password` / `email` | `scan_text_inputs` | `text_input` |
| `checkbox` (toggle 속성 없음) | `scan_plain_checkboxes` | `plain_checkbox` |
| `checkbox` (toggle 속성 있음) | `scan_toggle_checkboxes` | `toggle_checkbox` |
| `radio` | (미지원 — B-1-C 단계) | — |

`toggle 속성`은 ON/OFF 종속 필드를 가지는 토글 식별용. DOM 자동 감지로는 종속 관계를
모르므로 `dependent_fields = []`로 단독 검증만 진행.

### 카드 등록 위치 (시나리오별)

| 시나리오 | 자동 등록 카드 | 라벨 형식 | 동작 |
|---|---|---|---|
| 2 | `[신규] {라벨}` (text/plain/toggle 패턴) | `[신규] 소프트웨어 인증 사용` | 기본 동작 검증 (존재/초기값/클릭) |
| 3 | `[신규] {라벨}` (`discovered_fill`) | `[신규] 소프트웨어 인증 사용` | text/number 신규 필드 자동 채우기, checkbox는 default 유지 |
| 4 | `[신규] {라벨} 로드값 확인` (`initial_state`) | `[신규] 소프트웨어 인증 사용 로드값 확인` | EDIT 모달 재오픈 시 default 값 유지 확인 |
| 5 | `[신규] [{케이스명}] {라벨}` (`discovered_case`) | `[신규] [전체 ON] 소프트웨어 인증 사용` | ON/OFF 케이스 시점 각각 DOM 값 캡처 |

### 라벨 컨벤션

- **`[신규]` prefix**: yaml 미등록 신규 요소를 검수자가 즉시 식별 (CP949 호환 — 이모지 X).
- **케이스 prefix**: 시나리오 5에서 같은 신규 요소가 ON/OFF 시점 각각 1장 = 총 2장 카드.
  케이스 prefix(`[전체 ON]` / `[전체 OFF]`)로 시점 구분.
- **detail에 `[자동 분류 — yaml 미등록]` prefix**: 검수자에게 yaml 등록 시 정식 검증 시작
  필요함을 안내.

### 라벨 fallback 우선순위 (한국어 라벨 확보)

신규 요소의 한국어 라벨은 다음 순서로 검색:
1. yaml의 동일 selector 항목 (`text_inputs` / `plain_checkboxes` / `toggle_checkboxes` /
   `radio_groups[].options[]`) 의 `label`
2. DOM에서 `<label for="..">` 또는 인접 `<dt>` / 표 텍스트
3. 위 둘 다 없으면 selector 그대로 (`input#xxx`) — 검수자가 yaml 추가 작업 시 식별 가능

### 안전 default

- `required = false` (DOM에서 알 수 없으므로 보수적)
- `maxlength` = DOM 속성 그대로 (없으면 null)
- `dependent_fields = []` (자동 매칭 불가, B-1-C 단계에서 yaml 매칭 추가)
- 모든 자동 분류 카드는 `pass` 기본, 동작 실패 시 `fail`/`warn` (검증 누락 없음 보장).

### 회귀 안전 보장

- 모든 자동 분류는 **DOM 읽기 + 기존 validator 호출**만 사용. 새 클릭/입력 동작 없음.
- 추가 모달이 열린 상태(modal_already_open=True)에서만 실행 (사이드 이펙트 0).
- 자동 분류 실패 시 silent skip (회귀 위험 차단).

---

## 페이지 유형

현재 두 가지 유형이 존재하며 구조가 다르다.

| 유형 | 특징 | 예시 |
|------|------|------|
| `modal_form` | 탭 구조, 필드별 yaml scan_hints | RansomCruncher 탐지정책, RDP 정책 |
| `list_page` | 목록 + 모달, 시나리오 클래스 구조 | nPouch 운용 프로세스, 태그 관리 |

- modal_form: `@pytest.mark.parametrize("page_id", [...])` 단일 함수 + yaml 기반
- list_page: `class TestXxx` + 시나리오별 메서드 5개 + `_r()` 헬퍼

두 유형 모두 동일한 파이프라인을 사용한다.

---

## 파이프라인 (절대 준수)

```
test_*.py
  → ScanResult / PageScanReport 생성
  → request.node._scan_report 첨부
  → conftest 수집 → html_reporter HTML 생성
  → [HTML 리포트] 출력 → app.py 감지
```

---

## 공통 출력 규칙

### 헤더
```
━━ [{PAGE_NAME}] 시나리오 N: {이름} ━━━━━━━━━━━━━━━━━━━━━━━━
```

### detail 형식 (HTML 파서 분리 기준)
```
입력: {무엇을 했는지 / 어떤 값을 넣었는지} / 결과: {어떻게 됐는지}
```

### 상태 기준

| 상태 | 코드 | 색상 | 의미 |
|------|------|------|------|
| `[OK]` | `pass` | 초록 | 정상 동작 |
| `[FAIL]` | `fail` | 빨강 | **버그 (높음)** — 기능 결함, 데이터 손상, 저장 실패 등 실제 동작에 영향 |
| `[WARN]` | `warn` | 노랑 | **버그 (낮음)** — 검증 누락, UX 불편, 동작은 되나 허술한 경우 |
| `[ERR]` | `error` | 빨강 | **테스트 툴 오류** — 셀렉터 못 찾음, 타임아웃, 예외 발생 등 툴 자체 문제 |
| `[SKIP]` | `skip` | 회색 | 해당 없는 항목 (이유 명시) |

#### fail vs warn 판단 기준

| 항목 | fail (빨강) | warn (노랑) |
|------|-------------|-------------|
| 저장/수정 실패 | O | |
| 데이터 손상 가능 | O | |
| 정상 업무 흐름 차단 | O | |
| 글자수 제한 누락 | | O |
| 초기값 없음 (라디오 등) | | O |
| UX 불편 (암묵적 동작) | | O |

#### fail vs error 구분

- `fail` — 제품 버그. 테스트 로직은 정상 실행됐으나 제품이 잘못 동작함
- `error` — 툴 버그. 셀렉터 없음, 타임아웃, 예외 발생 등 테스트 자체가 실행 안 됨

#### known_bug 처리 원칙

알려진 버그(known_bugs.yaml 등록)도 동일하게 `fail` 또는 `warn`으로 분류한다.
별도 상태 없음. 리포트 비고란에 "알려진 버그: [내용]" 텍스트만 추가한다.

```
# 예시
[FAIL] SHA2 초기화 버그 — 알려진 버그: 전자서명 수정 시 SHA2 상태 초기화됨 (미수정)
[WARN] 글자수 제한 없음  — 알려진 버그: 서버 측 제한 없음, 클라이언트 미검증 (추적 중)
```

---

## 페이지별 필드 구성 관리 (YAML)

페이지별 셀렉터, maxlength, 필수 여부, 기본값 등은 **yaml 파일에 기록**한다.
코드에 하드코딩하지 않는다.

```yaml
# config/scan_hints/{page_id}.yaml 예시
fields:
  - id: processName
    label: "프로세스 이름(*)"
    required: true
    maxlength_dom: null        # DOM maxlength 없음
    maxlength_server: 100      # 서버 제한 확인값
    default: ""

  - id: execPath
    label: "실행경로"
    required: false
    maxlength_dom: null
    maxlength_server: null     # 미확인 → Chrome MCP로 확인 후 기록
    default: ""
```

### YAML 작성 절차
1. Chrome MCP로 페이지 직접 접속
2. 각 필드 outerHTML + 속성 추출 (`el.attributes` JS 실행)
3. 실제 경계값 입력 테스트 (maxlength+1 입력 → 실제 길이 확인)
4. 확인한 값을 yaml에 기록 (`confirmed: true / confirmed_date: YYYY-MM-DD`)

---

## 공통 설계 원칙

1. **[AUTO] / [AUTO_KEEP] 접두사 필수** — 생성/삭제는 `[AUTO]`로 시작하는 항목만.
   시나리오 6에서 다음 테스트에 남겨둘 항목은 `[AUTO_KEEP]` 사용 (상세: `docs/scenario_6_suite_setup.md`)
2. **검색 후 확인** — 추가 후 `search_item(name)` 먼저 호출
3. **사전 정리** — 시나리오 시작 시 `delete_all_auto_items()` 호출 (시나리오 6 제외)
4. **에러 메시지 == 비교** — `in` 체크 금지, 정확한 문자열 비교
5. **모든 필드 커버** — 선택 필드도 시나리오 3·5에서 반드시 확인
6. **[WARN] 활용** — 버그 의심이지만 테스트를 fail 처리하면 안 되는 경우

---

## 신규 페이지 추가 체크리스트

```
사전 준비:
□ Chrome MCP로 페이지 접속 → 모든 필드 outerHTML 추출
□ config/scan_hints/{page_id}.yaml 작성 (confirmed: true까지)
□ pages/{page_id}_page.py 작성 (BasePage 상속, selector 상수)
□ html_reporter.py _PAGE_LABELS 에 page_id → 한국어 레이블 추가

구현 순서 (한 시나리오씩, 실행 확인 후 다음):
□ 시나리오 1 구현 → 실행 확인
□ 시나리오 2 구현 → 실행 확인
□ 시나리오 3 구현 → 실행 확인
□ 시나리오 4 구현 → 실행 확인
□ 시나리오 5 구현 → 실행 확인
□ 시나리오 6 구현 → 실행 확인 (다른 페이지가 사용할 데이터가 있으면 [AUTO_KEEP] 항목 생성 후 남겨둠)
```
