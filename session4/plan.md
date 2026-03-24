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

### A (QA): "자동화의 목적은 반복 검증이다"
수동 테스트로는 UI 변경 시마다 전체를 재검증하기 어렵다.
페이지마다 scan_hints YAML을 작성하면 새 정책 추가 시 YAML만 추가하면 된다.
Chrome MCP로 실제 DOM을 보면서 YAML 값을 확정하는 것이 핵심이다.

### B (개발): "코드는 YAML이 바꿔도 수정 안 해야 한다"
UIScanner + scan_hints 구조가 맞다. 새 페이지는 YAML만 추가하면 된다.
동작 테스트는 단계별로 추가하되, 불안정한 테스트는 skip 처리하고 원인을 명시한다.
리포트는 pytest-html 우선, xlsx는 2단계에서 추가한다.

---

## 구현 목표 (우선순위 순)

### P0 — 현재 오류 수정 (즉시)
1. `pytest tests/test_ui_scan.py -v -s --tb=long` 실행 → 실제 오류 확인
2. 오류 원인에 따라 대응:
   - YAML `default:` 불일치 → Chrome MCP로 실제 기본값 확인 후 수정
   - 태그 추가 동작 실패 → 정책 이름 없이 add 불가 시 예외 처리
   - 라디오 JS 클릭 무반응 → wait_for_timeout 조정

### P1 — EDIT 모달 스캔 지원 (다음)
3. `[AUTO]` 정책 1개 생성 → 수정 모달 오픈 → 예외처리 탭 접근
4. ADD 모달에서는 `tab_activated=False`인 예외처리 탭 → EDIT 모달에서 `tab_activated=True`
5. EDIT 모달 스캔 시: 기존 값 기록 → 수정 → 검증 → 원복 (상태 보존 원칙)

### P2 — 리포트 강화 (이후)
6. 스크린샷 자동 첨부 (pass/fail 모두)
7. xlsx 리포트 (심각도별 시트)
8. JSON export (CI/CD용)

### P3 — 범위 확장 (장기)
9. 다른 정책 페이지로 확장 (scan_hints YAML만 추가)
10. common_validations: XSS, SQLi 입력 테스트

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

## 알려진 제품 버그 (테스트 실패 아님)

| 항목 | 내용 | 상태 |
|------|------|------|
| 인증 암호 필드 | 토글 OFF 시에도 필드 활성화 유지 | known_bug (YAML is_known_bug: true) |
| 라디오 기본값 없음 | ADD 모달 4개 옵션 모두 unchecked (의도적 설계) | default: null로 처리 |

---

## 참조 문서

| 문서 | 내용 |
|------|------|
| `design.md` | 전체 설계 원칙, selector 상수, 기술 제약 |
| `log3.md` | 직전 세션 인계 노트, 오류 원인 추정 |
| `ui_scan_requirements.md` | core/ + validators/ 상세 설계 (Phase별 구현 순서) |
| `config/scan_hints/ransom_detect_policy.yaml` | Chrome MCP 확인 완료 YAML |
