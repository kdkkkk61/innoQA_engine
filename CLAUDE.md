# 프로젝트 설계 원칙 (Claude Code 필독)

> **모든 개발·수정·문서 작업 시작 전 이 파일을 반드시 읽는다.**
> 해당 작업의 태그를 찾아 연결된 문서를 읽은 뒤 진행한다.

---

## 작업별 참조 문서

| 문서 | 태그 |
|------|------|
| `docs/test_scenario_standard.md` | [기본 경로 — 필독] |
| `docs/scenario_N_*.md` (1~6) | [기본 경로] |
| `docs/architecture.md` | [공통 — 새 pages/ 파일 추가 시] [공통 — docs/ 파일 작성·수정 시] |
| `docs/ui-interaction.md` | [공통 — 클릭/인코딩 문제 발생 시] |
| `docs/test-pipeline.md` | [공통 — 새 test_*.py 파일 추가 시] |
| `docs/yaml-guide.md` | [확장 경로 — YAML 스캔 적용 시] |
| `docs/scan-output-format.md` | [확장 경로 — modal_form 전용] |
| `docs/TROUBLESHOOTING.md` | [공통 — 이슈 수정 후 필기록] |

---

## 고정 운영 규칙

### 1. 이슈 수정 후 즉시 기록
코드 버그·오동작·설계 오류 수정 시 → `docs/TROUBLESHOOTING.md` 에 항목 추가.
기록 없이 넘어가는 것은 규칙 위반이다.

### 2. 테스트 실패 시 로그 먼저
추측으로 수정하기 전에 반드시 로그를 읽는다.
- `logs/` — app.py 실행 로그
- `reports/runs/*.log` — pytest 출력 전체 (가장 최근 타임스탬프 파일)

---

## 코드 수정 전 확인 절차

1. **영향 범위 파악**: 수정 대상을 import하거나 호출하는 파일 목록 먼저 확인
2. **연계 파일 맥락 확인**: 관련 파일 실제로 읽기 (YAML ↔ runner ↔ 테스트 연계 흐름 포함)
3. **맥락 파악 후 즉시 실행**: 설명 없이 Edit 도구로 바로 수정
4. **금지**: 연계 파일 확인 없이 수정 대상 파일만 보고 바로 수정 시작

---

## 데이터 안전 규칙

- `[AUTO]` 접두사 항목만 생성·삭제 가능. 미충족 시 Page 클래스에서 Exception 발생
- `[AUTO_KEEP]` 접두사: 시나리오 6에서 다른 페이지의 테스트가 사용할 데이터를
  의도적으로 남겨둘 때 사용. 세션 종료 전까지 보존되며 delete_all_auto_items()
  대상에서 제외된다.
- 두 접두사가 일정 기간 공존한다:
  - 기존 코드는 `[AUTO]_*_suite` 형식으로 보존 데이터를 표시하고 있음
  - 신규 시나리오 6 작성 시부터 `[AUTO_KEEP]_*` 형식 적용
  - 기존 코드 마이그레이션은 별도 작업 예정 (이번 문서 정리 범위 아님)
- 상세는 `docs/scenario_6_suite_setup.md` 참조
- 이 규칙은 어떤 경우에도 우회하지 않는다

---

## 절대 하지 말아야 할 것

**파이프라인** → `docs/test-pipeline.md` 참조
- conftest/html_reporter 파이프라인 우회 금지
- ScanResult 객체 없이 print()만으로 결과 출력 금지

**아키텍처** → `docs/architecture.md` 참조
- `base_page.py`에 특정 페이지 전용 로직 추가 금지
- 하나의 테스트 함수에서 여러 시나리오 검증 금지
- 하드코딩된 sleep() 사용 금지 (wait_for_selector 또는 expect 사용)

**진행 방식**
- 사용자가 "다음"이라고 하기 전에 다음 시나리오·다음 페이지 코드 작성 금지
- 실행 확인 없이 작성된 코드는 즉시 제거 대상
- 백업 없이 기존 파일 덮어쓰기 금지
