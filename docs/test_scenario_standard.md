# 테스트 시나리오 표준 — 개요 및 사용 정의

> 작성일: 2026-04-21 / 최종 수정: 2026-04-29
> QA 자동화 테스트의 6개 시나리오 구조와 공통 규칙을 정의한다.
> 세부 검증 항목은 각 시나리오 파일 참고.

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
| **1** | UI 구조 | 화면 요소 존재 확인 | 전 페이지 |
| **2** | 입력 구조 | 필드 구조 + 검증 로직 확인 | 모달 있는 페이지 |
| **3** | 동작 검증 | CRUD 흐름 + 비정상 케이스 | 전 페이지 |
| **4** | 수정 시나리오 | 저장값 로드 + 수정 후 재확인 | 전 페이지 |
| **5** | 케이스 검증 | 전체 필드 / 필수만 — 저장 재확인 | 모달 있는 페이지 |
| **6** | 연계 데이터 준비 | 다음 테스트에서 사용할 항목 생성 후 남겨둠 | 연계 대상 있는 페이지 |

> 해당 시나리오가 없으면: `[SKIP] 시나리오 N — 해당 없음 (이유)` 출력

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
