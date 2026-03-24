# 작업 진행 체크리스트

> 새 세션을 시작한 Claude는 이 파일을 먼저 읽고 현재 상태를 파악한다.
> 작업 완료 시 해당 항목을 `[x]`로 변경하고, 결과/날짜를 기록한다.
> 세부 내용이 길어지면 `checklist_1.md`에 기록하고 여기서 참조한다.

---

## 현재 세션 상태 요약

| 항목 | 상태 |
|------|------|
| 마지막 작업 세션 | 세션 4 (2026-03-24) |
| 현재 브랜치 | main |
| 아키텍처 결정 | Option C 확정 — validators/ 분리 완료 |
| 다음 작업 | P0: `pytest tests/test_ui_scan.py -v -s --tb=long` 실행 → 오류 확인 |

---

## 완료된 작업

### 기반 구조
- [x] 프로젝트 초기 셋업 (pytest, playwright, conftest.py)
- [x] `pages/base_page.py` — JS click, angular_fill, overlay 제어
- [x] `config/settings.yaml` — URL, 브라우저 설정
- [x] fixture 구조 — `fresh_page`, `logged_in_page`, `credentials`, `settings`
- [x] 클릭 차단 오버레이 (`#qa-block-overlay`, `#qa-test-banner`) 주입 로직

### 로그인 테스트 (`tests/test_login.py`) — 3개 전부 pass
- [x] `test_login_success` — 정상 로그인
- [x] `test_login_failure` — 잘못된 계정 에러 모달
- [x] `test_logout` — 로그아웃 후 로그인 화면 복귀

### 탐지정책 CRUD 테스트 (`tests/test_ransom_detect_policy.py`) — 4개 전부 pass
- [x] `test_policy_lifecycle` — 생성→수정→복사→삭제 전체 흐름
- [x] `test_policy_name_validation` — 빈값/maxlength/중복 에러 모달
- [x] `test_extension_validation` — 확장자 태그 추가/중복/에러 모달
- [x] `test_toggle_activation` — 토글 ON/OFF → 종속 필드 활성화 검증

### UIScanner 기반 스캔 시스템 (Option C 리팩토링 완료 — 2026-03-24)
- [x] `core/models.py` — ScanResult, PageScanReport 데이터 클래스 (신규 분리)
- [x] `core/scan_context.py` — ScanContext (page + log + 공용 헬퍼) (신규)
- [x] `validators/__init__.py` — 패키지 초기화 (신규)
- [x] `validators/toggle_checkbox.py` — 토글 검증 + _check_toggle_with_deps (신규)
- [x] `validators/plain_checkbox.py` — 일반 체크박스 검증 (신규)
- [x] `validators/radio_group.py` — 라디오 그룹 검증 (신규)
- [x] `validators/text_input.py` — 텍스트 입력 검증 (신규)
- [x] `validators/tag_input.py` — 태그 입력 검증 (신규)
- [x] `validators/required_submit.py` — 필수 입력 제출 검증 (신규)
- [x] `core/ui_scanner.py` — 오케스트레이터로 축소 (1630줄 → 313줄)
- [x] `utils/scan_logger.py` — 스캔 결과 로거
- [x] `tests/conftest.py` — `restore_after_scan` fixture
- [x] `tests/test_ui_scan.py` — 스캔 실행 테스트
- [x] `config/scan_hints/ransom_detect_policy.yaml` — Chrome MCP DOM 직접 확인 완료
  - [x] text_inputs: `rcDetectPolicyName` (maxlength 20, required)
  - [x] tag_input: `extension_input`, `except_file_path`, `except_process_path`, `except_digital_sign`
  - [x] plain_checkboxes: 4개 (default 확인 완료)
  - [x] radio_groups: `behaviorDetectLevelType` (default: null 확인)
  - [x] toggle_checkboxes: 6개 (default 확인 완료)
  - [x] required_submit_sequence: 3단계 검증 정의
- [x] `_dismiss_warning_dialog` 버그 수정 — `div#__globalMessageModal.in` 직접 지정
- [x] 예외처리 탭 경고 다이얼로그 처리 — `tab_activated=False` → 동작 테스트 스킵

### YAML default 값 확인 (Chrome MCP, 2026-03-23)
- [x] 라디오 `behaviorDetectLevelType` — 전부 unchecked (default: null)
- [x] 토글 6개 — 전부 false
- [x] plain_checkbox 4개 — 전부 false

---

## 미완료 작업

### P0 — 즉시 (오류 수정) ← 앱 실행 필요
- [ ] `pytest tests/test_ui_scan.py -v -s --tb=long` 실행 → 실제 오류 스택 확인
- [ ] 오류 원인 파악 (의심 원인 → `log3.md` 참조)
- [ ] 수정 후 테스트 통과 확인
- [ ] `core/scanner.py` 삭제 (사용 안 됨 — ui_scanner.py에 통합됨)

### P1 — 다음 (EDIT 모달 지원)
- [ ] EDIT 모달 스캔 추가 (`ui_scanner.py` 확장)
  - [ ] `[AUTO]` 정책 1개 생성 → 수정 모달 오픈
  - [ ] 예외처리 탭 `tab_activated=True` 확인 (EDIT 모달에서만 가능)
  - [ ] 기존 값 기록 → 수정 → 검증 → 원복 로직
- [ ] YAML `default:` 주석 처리된 항목 주석 해제 (Chrome MCP 재확인 후)
  ```
  # 확인 대상:
  # - 라디오 default: null (현재 주석 해제 완료)
  # - 6개 토글 default: false (현재 주석 해제 완료)
  ```

### P2 — 이후 (리포트 강화)
- [ ] 스크린샷 자동 첨부 (pass/fail 모두)
- [ ] `reports/generators/xlsx_report.py` — 심각도별 시트
- [ ] `reports/generators/json_export.py` — CI/CD용

### P3 — 장기 (범위 확장)
- [ ] 다른 정책 페이지 scan_hints YAML 추가
- [ ] XSS/SQLi 입력 테스트 (`common_validations.yaml`)
- [ ] `validators/` 레이어 구현 (ui_scan_requirements.md Phase 1~5)

---

## 참조

| 파일 | 내용 |
|------|------|
| `session4/personal.md` | 에이전트 역할 정의 (Instructions/Knowledge/Tools) |
| `session4/plan.md` | 개발 방향, 우선순위, 아키텍처 합의 |
| `log3.md` | 직전 세션 인계 노트 (오류 원인 추정 포함) |
| `design.md` | 전체 설계, selector 상수, 기술 제약 |
| `ui_scan_requirements.md` | core/ + validators/ 상세 설계 |
