# 개발 방향 합의서 — QA 전문가 × 시니어 개발자 논의 결과

> QA 전문가(A)와 시니어 개발자(B)의 논의·토의를 거쳐 합의된 개발 방향.
> 이 파일의 내용이 다른 문서와 충돌 시, 이 파일이 우선한다.

---

## 제품 개요

| 항목 | 내용 |
|------|------|
| 목적 | 보안 제품 매니저 웹 UI 자동화 테스트 |
| 대상 앱 | Bootstrap 3 + AngularJS SPA, `http://192.168.13.141` |
| 스택 | Python 3.12, pytest, Playwright (sync) |
| 테스트 실행 | `pytest tests/ --html=reports/report.html --self-contained-html -v` |
| Chrome 연동 | Claude Chrome MCP — DOM 확인, 동작 검증, 실제 클릭 시뮬레이션 |

---

## 핵심 방향 합의

### A (QA): "시나리오 기반 QA — 사용자 행동을 따라가며 휴먼에러를 잡는다"
단순 UI 요소 점검표가 아닌, 실제 사용자 시나리오(생성→동작→수정)를 따라가며 검증한다.
"이진 라디오 초기값 없음", "ADD에서 접근 불가 탭" 같은 UX 결함도 감지 대상이다.
Chrome MCP로 실제 DOM을 보면서 YAML 값을 확정하는 것이 핵심이다.

### B (개발): "코드는 YAML이 바꿔도 수정 안 해야 한다"
UIScanner + scan_hints 구조가 맞다. 새 페이지는 YAML만 추가하면 된다.
Phase 기반 scan으로 확장: `scan(phase=1|2|3)` → 모달을 단계별로 열며 검증한다.
리포트는 Phase별 섹션으로 구분, xlsx는 2단계에서 추가한다.

---

## 구현 목표 (우선순위 순)

### P0 — Phase 기반 스캔 아키텍처 (즉시)

**Phase 구조 (모달 3회 열기 패턴):**

| Phase | 모달 | 목적 |
|-------|------|------|
| Phase 1 | ADD 1회차 | 초기값 스냅샷 + 필수입력 검증 + 저장 |
| Phase 2 | ADD 2회차 | 중복이름 시도 + UI 요소 동작 + 저장 |
| Phase 3 | EDIT | 수정 시나리오 + 정리 |

**Phase 1 내부 순서 (중요 — 순서 엄수):**
```
① 모달 열기 (터치 전)
② 초기값 스냅샷  ← require_default, text/checkbox 기본값 — 반드시 터치 전 실행
③ 필수입력 검증  ← 빈 채로 등록 버튼 클릭 → 경고 확인
④ 저장           ← [AUTO]_xxx_1
```

**Phase 2 내부 순서:**
```
① 모달 열기
② 중복이름 시도  ← Phase 1 이름으로 시도 → 오류 확인
③ UI 요소 동작   ← 현재 A안 전체 (라디오, 체크박스, dep_fields, text_input)
④ 저장           ← [AUTO]_xxx_2 (Phase 3용)
```

### P1 — UX 감지 패턴 확장
- HE-05: ADD 모달 접근 불가 탭 → 리포트에 UX 이슈로 명시
  - 탐지정책 예외처리 탭 → YAML `accessible_in: ["edit"]` 플래그
  - 현재: 스킵 처리만 → 개선: `ux_issue` 상태로 리포트

### P2 — 리포트 강화
- Phase별 섹션 헤더
- 스크린샷 자동 첨부 (fail 시)
- xlsx 리포트 (Phase별 / 심각도별)

### P3 — 범위 확장
- 다른 정책 페이지로 확장
- XSS/SQLi 입력 테스트

---

## 아키텍처 합의

```
config/scan_hints/{page_id}.yaml  ← 페이지별 검사 정의 (YAML만 추가, 코드 수정 없음)
core/ui_scanner.py                ← 스캔 엔진 (범용 — 특정 페이지 로직 금지)
tests/test_ui_scan.py             ← 실행 진입점
tests/conftest.py                 ← restore_after_scan fixture
pages/{page}_page.py              ← 모달 열기/닫기만 (검증 로직 없음)
```

### Chrome MCP 활용 원칙
- selector, default 값 추정 금지 → Chrome MCP로 직접 확인 후 YAML 작성
- 동작 확인: Chrome MCP로 클릭 → 결과 관찰 → 코드 반영
- 운영 데이터 보호: `[AUTO]` 접두사 정책만 생성/삭제

### 동작 테스트 안정성 원칙
- AngularJS ng-model 동기화 지연 → `wait_for_function` 또는 timeout 조정
- 불안정한 테스트는 즉시 재시도 금지 → 원인 분석 후 수정
- ADD 모달에서 정책 이름 없는 상태 → 확장자 add 불가 가능성 고려

---

## 알려진 제품 버그 / UX 결함 (테스트 실패 아님)

| 항목 | 페이지 | 상태 |
|------|--------|------|
| 인증 암호 필드 토글 OFF 시에도 필드 활성 | 탐지정책 | known_bug |
| RDP EDIT 모달 필수필드 미검증 | RDP 정책 | known_bug |
| 연결 설정(이진 라디오) 초기값 없음 | RDP 정책 | known_bug (UX 결함) |
| 연결 시간 제한(이진 라디오) 초기값 없음 | RDP 정책 | known_bug (UX 결함) |
| 예외처리 탭 ADD 모달에서 접근 불가 | 탐지정책 | HE-05 미구현 (현재 스킵 처리) |

## UX 감지 패턴 (HE: Human Error)

| ID | 패턴명 | 구현 상태 |
|----|--------|-----------|
| HE-01 | 이진 라디오 초기값 없음 | ✅ `require_default` |
| HE-02 | EDIT 필수필드 미검증 | ✅ `known_bug` |
| HE-03 | 라디오 종속필드 잠금/해제 | ✅ `dependent_fields` |
| HE-04 | 토글 OFF 종속필드 활성 유지 | ✅ `known_bug` |
| HE-05 | ADD 모달 접근 불가 탭 | ❌ 미구현 |

---

## 참조 문서

| 문서 | 내용 |
|------|------|
| `design.md` | 전체 설계 원칙, selector 상수, 기술 제약 |
| `log3.md` | 직전 세션 인계 노트, 오류 원인 추정 |
| `ui_scan_requirements.md` | core/ + validators/ 상세 설계 (Phase별 구현 순서) |
| `config/scan_hints/ransom_detect_policy.yaml` | Chrome MCP 확인 완료 YAML |
