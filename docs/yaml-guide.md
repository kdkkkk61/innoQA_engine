# YAML 스캔 작성 가이드

> 태그: [확장 경로 — YAML 스캔 적용 시]
> 이 문서는 `config/scan_hints/` YAML을 사용하는 페이지에만 적용된다.
> list_page 계열(nPouch 등)은 YAML 스캔을 사용하지 않으므로 해당 없음.

---

## Chrome MCP 탐색 목적

HTML 속성만 읽는 것은 금지. Chrome MCP는 **실제 값을 입력·제출하는 시나리오**를 수행해서
서버 동작을 확인하고, 그 결과를 YAML에 기록하는 데 사용한다.

1. **글자수 제한 탐색** — `overflow_scan` 결정: 큰 값 직접 입력·제출 → 서버 오류 여부 확인
2. **포맷 검증 탐색** — `format_validation_tests` 결정: 잘못된 포맷 값 제출 → 서버 검증 여부 확인
3. **특수문자 차단 탐색** — `special_char_tests` 결정: 특수문자 포함 값 제출 → 실제 차단 여부 확인
4. **필드 구조 파악** — selector / required 여부 / 초기값 / 종속 필드 관계

---

## 탐색 순서

### 1단계: 필드 구조 파악 (속성 확인)

(코드 예시: Chrome MCP javascript_tool로 `el.attributes` 순회 → 모든 속성 name/value를 JSON으로 추출)

| 확인 항목 | 이유 |
|---|---|
| `type` | text / number / checkbox / radio 구분 |
| `maxlength` | DOM 제한 여부 — 없으면 2단계에서 서버 직접 탐색 |
| `required` / `ng-required` | 필수 필드 여부 |
| `ng-model` | AngularJS 바인딩 키 |
| `disabled` | 종속 필드 여부 |

### 2단계: 서버 동작 시나리오 탐색 (Chrome MCP로 직접 수행)

속성 확인 후 반드시 **실제 값을 입력·제출**해서 서버 반응을 확인한다.

**글자수 제한 탐색** (`overflow_scan` 결정 기준)
```
[Chrome MCP 수행]
1. 추가 모달 열기
2. 필드에 200자 이상 입력 (JS로 value 직접 세팅 후 input 이벤트 발생)
3. 제출 버튼 클릭
4. 서버 오류 모달 → overflow_scan: true / 서버가 저장 → 1000자도 시도 → overflow_scan: true (known issue)
```
**포맷 검증 탐색** (`format_validation_tests` 결정 기준)
```
[Chrome MCP 수행]
1. 추가 모달 열기
2. SHA2 필드에 "XXXXNOTVALIDHEX" 입력, 이름 필드도 채운 후 제출
3. 서버 오류 모달 → expect_validation: true / 서버가 저장 → expect_validation: false (known issue)
```
**특수문자 차단 탐색** (`special_char_tests` 결정 기준)
```
[Chrome MCP 수행]
1. 추가 모달 열기
2. 이름 필드에 "[TEST]_sc';!@#$" 입력 후 제출
3. 서버 오류/차단 모달 → expect_block: true / 서버가 저장 → expect_block: false (known issue)
   주의: HTML < > 사용 금지 (inner_text 파싱 실패로 cleanup 불가)
```
**중복값 에러 메시지 확인**
```
[Chrome MCP 수행]
1. 이미 존재하는 이름으로 추가 시도
2. 에러 모달 텍스트를 정확히 복사 → 테스트 코드의 expected 문자열에 사용
```

### 3단계: YAML 작성

```yaml
fields:
  - id: processName
    selector: "input#processName"
    label: "프로세스 이름"
    required: true
    order: 10
    overflow_scan: true        # Chrome MCP 탐색: 1001자 저장됨 → 제한 없음(known issue)
    overflow_prefix: "[AUTO]_ov_"

format_validation_tests:      # Chrome MCP 탐색에서 서버 검증 없음 확인 시에만 추가
  - field: sha2
    label: "SHA2 — 비hex 입력 유효성 검사"
    test_value: "XXXXNOTVALIDHEX"
    item_name: "[AUTO]_fv_sha2"
    expect_validation: false   # Chrome MCP 탐색 결과: 검증 없음(known issue)
    # 확인일: 2026-04-23

special_char_tests:            # Chrome MCP 탐색에서 차단 없음 확인 시에만 추가
  - field: processName
    label: "프로세스 이름 — 특수문자 입력 차단 여부"
    test_value: "[AUTO]_sc';!@#$"
    expect_block: false        # Chrome MCP 탐색 결과: 차단 없음(known issue)
    # 확인일: 2026-04-23
```

---

## 접근 방식

```
❌ 잘못된 접근
  화면 생김새만 보고 필드 정의 — 실제 제출 테스트 없이 YAML 작성
  maxlength 속성 없으니까 overflow_scan 안 함
  "아마 특수문자는 막겠지" 추정으로 expect_block: true 설정
  Chrome MCP에서 속성만 읽고 값 입력·제출 없이 완료 선언

✅ 올바른 접근
  Chrome MCP로 실제 값 입력·제출 → 서버 반응 직접 확인
  서버가 허용하면 known issue로 기록, 서버가 막으면 정상 동작으로 기록
  탐색 결과가 YAML expect_* 값의 근거가 된다 — 추정 금지
  확인 안 된 필드는 YAML note에 "미확인" 명시
```

---

## YAML 주석 기록 기준

```yaml
overflow_scan: true
# 확인일: 2026-04-23 / Chrome MCP 탐색: 101자·501자·1001자 모두 저장됨 → 제한 없음(known issue)

expect_validation: false
# 확인일: 2026-04-23 / Chrome MCP 탐색: "XXXXNOTVALIDHEX" 제출 → 저장됨(서버 포맷 검증 없음)
```

---

## 관련 문서

- `docs/scan-output-format.md` — YAML `order` 값이 출력 정렬에 직결됨
- `docs/test-pipeline.md` — YAML 스캔이 파이프라인 안에서 어떻게 처리되는지
- `docs/test_scenario_standard.md` — modal_form 계열 페이지의 시나리오 구성 기준
