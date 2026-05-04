# 시나리오 2: 입력 구조

> 목적: 추가 모달의 모든 필드 구조, 초기값, **입력 검증 동작 유무** 확인.
> 모달이 없는 페이지는 `[SKIP]` 처리.
> **추정 금지 원칙**: 검증 결과가 불확실한 경우(EDIT 모달의 빈값 시도 후 결과 등)는
> 시나리오 2에서 추정으로 판정하지 말고, 후속 시나리오로 위임한다.

---

## 정의 변경 이력

- **2026-04-30**: "추정 금지" 명시 + EDIT 모달의 빈값 후 결과 책임 분리.
  - 시나리오 2 = 입력 검증 **동작 유무 (1차)** — "경고 떴는가, 통과되는가"
  - 시나리오 4-3 = 통과된 위반 입력의 **실제 저장 결과 (2차)**
  - 배경: 시나리오 2의 EDIT 검증이 "경고 안 뜸 → 저장됐겠지" 추정으로 끝나
    실제 저장값(빈값/원본/다른값)을 모름. 이를 시나리오 4로 이전.

---

## 반드시 커버해야 할 항목

| 카테고리 | 내용 | 비고 |
|----------|------|------|
| 모달 기본 | 제목, 제출/취소 버튼 텍스트 | 없으면 fail |
| 필드 존재 | 모달에 있는 **전체 필드** 존재 확인 | 한 개라도 누락 금지 |
| 초기값 | 각 필드의 기본값 (빈값 or 기본값) | yaml 기준 |
| maxlength | DOM 속성 또는 서버 제한 — **입력 가능한 모든 필드** | 필수/선택 무관 |
| 필수 검증 (1차) | 빈 값 제출 → **경고 메시지 떴는가** | 필수 필드별로. EDIT 결과는 시나리오 4-3 |
| 글자수 제한 | 경계값+1 입력 → 결과 확인 | maxlength 있는 필드 |
| 중복 검증 | 기존 등록명으로 제출 → 에러 메시지 | 고유 이름 필드 있는 경우 |

---

## 필드별 검증 원칙

### 모든 필드에 적용
- 필드 존재 여부
- 초기값 (yaml의 `default` 기준)

### 텍스트/textarea 입력 필드에 추가 적용
- DOM maxlength 속성 확인
- DOM maxlength 없으면 → 서버 제한 직접 테스트 (긴 값 입력 후 저장)
- 결과에 관계없이 확인 결과를 기록 (없으면 WARN)

### 특수 형식 필드 (SHA2, IP, 포트 등)
- 포맷 검증 여부 확인 (비정상 형식 입력 → 서버 에러 vs 통과)
- 포맷 검증 없으면 WARN 기록

> **규칙**: 필드 목록은 yaml의 `fields` 섹션에서 가져온다.
> 코드에 필드 목록을 하드코딩하지 않는다.

---

## 코드 패턴 참조

### list_page 패턴 (nPouch 계열)

```python
def test_scenario2_modal_fields(self):
    p = self.p
    lines, srs = [], []
    p.open_add_modal()

    # 모달 기본 확인
    title = p.get_modal_title()
    t, s = _r("pass" if "추가" in title else "warn", "모달 제목",
              f"입력: 모달 오픈 / 결과: 제목={title!r}", sc=2)

    # 전체 필드 순회 — 필드 목록은 클래스 상수 또는 yaml에서
    for sel, label, required in FIELD_LIST:
        exists = page.locator(sel).count() > 0
        t, s = _r("pass" if exists else "fail", f"{label} — 필드 존재",
                  f"입력: (없음) / 결과: {'존재' if exists else '없음'}", sc=2)
        if not exists:
            continue

        # 초기값
        val = p.get_field_value(sel)
        t, s = _r("pass" if val == "" else "warn", f"{label} — 초기값",
                  f"입력: 초기 상태 / 결과: {val!r}", sc=2)

        # maxlength — 필수/선택 구분 없이 전체 적용
        ml = page.locator(sel).first.get_attribute("maxlength")
        t, s = _r("warn" if ml is None else "pass", f"{label} — DOM maxlength",
                  f"입력: maxlength 속성 확인 / 결과: {ml!r}", sc=2)
        # maxlength 없으면 yaml의 maxlength_server 참조해서 경계값 테스트 진행

    # 필수 검증, 글자수, 중복은 필드별 yaml 설정 참조
    p.close_modal()
    self._attach(srs)
```

### modal_form 패턴 (RansomCruncher 계열)

```python
# scan_hints yaml의 required_submit / text_input / number_input 섹션을 읽어 자동 처리
# qa_runner.py가 yaml 기반으로 필드별 검증 실행
# 테스트 파일에서는 yaml 경로만 지정
```

---

## YAML 연동

```yaml
# config/scan_hints/{page_id}.yaml
fields:
  - id: fieldId
    label: "필드명(*)"          # (*) = 필수
    required: true/false
    maxlength_dom: 100          # null이면 DOM maxlength 없음
    maxlength_server: 100       # 실제 테스트로 확인한 서버 제한값
    default: ""
    format: null                # "sha2" / "ip" / "port" 등 특수 형식
    confirmed: true
    confirmed_date: YYYY-MM-DD
```

---

## 주의사항

- 모달에 있는 필드를 **하나라도 누락하면 안 됨** (yaml에 없으면 Chrome MCP로 확인 후 추가)
- maxlength는 필수/선택 구분 없이 **입력 가능한 모든 필드**에 확인
- 에러 메시지 텍스트는 yaml의 `error_messages` 섹션에 기록 후 참조

---

## 책임 분리 (다른 시나리오와 겹침 방지)

### EDIT 모달의 필수 비움 시도 — 1차/2차 분리

```
시나리오 2 (1차)              시나리오 4-3 (2차)
──────────────────         ──────────────────
빈 값 제출                  필수 비움 + 저장
   ↓                            ↓
경고 떴나?                  모달 재오픈
   ├ Yes → pass             재로드된 실제 값 확인
   └ No  → fail (검증 누락)     ├ "" → fail (데이터 손상)
                                 ├ 원본 → warn (서버 거부, UX 혼란)
                                 └ 그외 → error (예상 못한 동작)
```

**핵심 원칙**:
- 시나리오 2는 **"경고 떴는가"** 만 본다. **추정 금지** (저장값을 안 보고 결론 내지 말 것).
- 통과된 케이스의 실제 결과는 시나리오 4-3가 본다.
- detail 표현: 추정 표현 금지 (`"저장됐다"`, `"저장된 것으로 보임"` 등 사용 금지).
  객관 표현만 (`"경고 없이 모달 닫힘"`, `"클라이언트 검증 누락"`).

### 입력 검증 깊이별 시나리오 매핑

| 검증 깊이 | 시나리오 |
|---|---|
| 필드 존재·구조 | 시나리오 2 |
| 입력 검증 동작 유무 (1차) | 시나리오 2 |
| 정상 입력 후 저장 정합성 | 시나리오 4 (4-1, 4-2) |
| 위반 입력 후 저장 정합성 | 시나리오 4 (4-3) |
| 정상 입력 조합별 저장 정합성 | 시나리오 5 |
| CRUD 1사이클 흐름 | 시나리오 3 |
| CRUD 중 비정상 케이스 (오버플로 등) | 시나리오 3 |
