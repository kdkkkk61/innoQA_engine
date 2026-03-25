# 작업 진행 체크리스트

> 새 세션을 시작한 Claude는 이 파일을 먼저 읽고 현재 상태를 파악한다.
> 작업 완료 시 해당 항목을 `[x]`로 변경하고, 결과/날짜를 기록한다.
> 세부 내용이 길어지면 `checklist_1.md`에 기록하고 여기서 참조한다.

---

## 현재 세션 상태 요약

| 항목 | 상태 |
|------|------|
| 마지막 작업 세션 | 세션 5 (2026-03-25) |
| 현재 브랜치 | main |
| 아키텍처 결정 | Option C 확정 + 시나리오 기반 QA 방향 확정 |
| 전체 테스트 | 4 passed (test_ui_scan 2 + test_rdp_policy_scan 2) |
| 다음 작업 | Phase 구조 설계 → UIScanner 멀티 페이즈 확장 |

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

### RDP 정책 스캔 추가 (2026-03-25)
- [x] `pages/rdp_policy_page.py` — RdpPolicyPage 클래스 (Chrome MCP DOM 확인 완료)
- [x] `config/scan_hints/rdp_policy.yaml` — dependent_fields + require_default 포함
- [x] `tests/test_rdp_policy_scan.py` — ADD/EDIT 스캔 2 passed
- [x] `validators/radio_group.py` 확장 — dependent_fields, require_default 지원
- [x] `config/known_bugs.yaml` — 3건 추가 (RDP EDIT 필수검증, isConnect/isAlwaysConnect 초기값)

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

### P0 — 즉시 (Phase 기반 스캔 아키텍처)
- [ ] `core/ui_scanner.py` — `scan(phase=1|2|3)` 멀티 페이즈 지원
- [ ] `config/scan_hints/*.yaml` — 각 항목에 `phase: 1|2` 태그 추가
- [ ] `tests/test_rdp_policy_scan.py` — 3 Phase 호출 구조로 리팩토링
- [ ] `validators/initial_state.py` — Phase 1 전용 초기값 스냅샷 (모달 열리자마자 실행)
- [ ] 탐지정책도 동일 Phase 구조로 전환

### P1 — 다음 (UX 감지 패턴 확장)
- [ ] HE-05: `tab_access_restriction` validator
  - ADD 모달에서 접근 불가 탭 → `known_bug` 또는 `ux_issue`로 리포트
  - 탐지정책 예외처리 탭 케이스 적용
  - YAML: 탭 정의에 `accessible_in: ["edit"]` 플래그 추가
- [ ] Phase 2: 중복이름 검증 validator (`validators/duplicate_name.py`)
- [ ] Phase별 리포트 섹션 헤더 표시

### P2 — 이후 (리포트 강화)
- [ ] 스크린샷 자동 첨부 (fail 시)
- [ ] `reports/generators/xlsx_report.py` — Phase별 / 심각도별 시트
- [ ] `reports/generators/json_export.py` — CI/CD용

### P3 — 장기 (범위 확장)
- [ ] 다른 정책 페이지 scan_hints YAML 추가
- [ ] XSS/SQLi 입력 테스트 (`common_validations.yaml`)
- [ ] `core/scanner.py` 삭제 (사용 안 됨 — 잔재 파일)

---

## 참조

| 파일 | 내용 |
|------|------|
| `session4/personal.md` | 에이전트 역할 정의 (Instructions/Knowledge/Tools) |
| `session4/plan.md` | 개발 방향, 우선순위, 아키텍처 합의 |
| `log3.md` | 직전 세션 인계 노트 (오류 원인 추정 포함) |
| `design.md` | 전체 설계, selector 상수, 기술 제약 |
| `ui_scan_requirements.md` | core/ + validators/ 상세 설계 |
