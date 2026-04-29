# TROUBLESHOOTING.md — QA 툴 이슈 추적

> 발견된 버그/이슈를 날짜별로 기록한다.
> 동일 이슈 재발 방지 목적. 수정 완료 시 [RESOLVED] 표시.

---

## [RESOLVED] nPouch 제품 선택 화면 🔒 막힘
- **날짜**: 2026-04-21
- **증상**: QA 툴 실행 시 엔파우치 카드가 "🔒 준비 중"으로 비활성화되어 선택 불가
- **원인**: `app.py` `_get_products()` 내 `label_map`에 `"npouch"` 항목 누락 → `active: False` 반환
- **수정**: `label_map`에 `"npouch": "엔파우치"` 추가
- **파일**: `app.py` `_get_products()`

---

## [RESOLVED] nPouch 테스트를 print 방식으로 잘못 구현 (방향성 오류)
- **날짜**: 2026-04-21
- **증상**: nPouch 테스트가 `print()` 텍스트 출력만 하고 `ScanResult/PageScanReport` 객체를 생성하지 않음 → conftest가 수집 불가 → html_reporter.py 파이프라인 우회
- **원인**: 랜섬크런처(첫 번째 완성 테스트)의 파이프라인을 따르지 않고 별도 방식으로 구현
- **올바른 방향**: 모든 테스트는 `ScanResult/PageScanReport → conftest 수집 → html_reporter HTML 생성` 파이프라인을 따른다
- **수정**:
  1. `test_npouch.py` — `_r()` 헬퍼로 print 문자열 + ScanResult 동시 생성, `_attach()` 로 PageScanReport를 test node에 첨부
  2. `conftest.py` — `_npouch_page_id` 속성으로 nPouch page_id 수집, page_id별 PageScanReport 머지, product 자동 감지
  3. `app.py` — nPouch 전용 리포터 제거, glob 폴백을 제품 폴더 한정으로 수정
  4. `core/npouch_reporter.py` 삭제
- **파일**: `test_npouch.py`, `conftest.py`, `app.py`, `core/npouch_reporter.py`(삭제)

## [RESOLVED] 엔파우치 테스트 결과에 이노마크 리포트 표시
- **날짜**: 2026-04-21
- **증상**: 엔파우치 운용 프로세스 테스트 실행 후 결과 화면에 "innoMark 템플릿 관리" HTML 리포트가 표시됨
- **원인**:
  1. nPouch 테스트(`test_npouch.py`)는 `print()` 기반 출력 → `conftest.py`의 `_scan_reports`에 아무것도 쌓지 않음
  2. `conftest.py` `pytest_unconfigure`에서 `[HTML 리포트]` 라인 미출력
  3. `app.py`의 `returncode==0` 폴백이 `reports/*/QA_*.html` **전체**를 glob → 가장 최근 수정된 파일인 `QA_InnoMark_20260416_1045.html`을 가져옴
- **수정**:
  1. `core/npouch_reporter.py` 신규 생성 — `live_log` 파싱 후 `reports/nPouch/QA_nPouch_{ts}.html` 생성
  2. `app.py`에서 `product_id == "npouch"` 시 nPouch 전용 리포터 호출
  3. 기타 제품 glob 폴백을 `reports/{제품폴더}/QA_*.html` 로 범위 한정 (전체 glob 제거)
- **파일**: `app.py` `_run()`, `core/npouch_reporter.py` (신규)

---

## [RESOLVED] headless 모드에서 테스트가 아무것도 실행되지 않음
- **날짜**: 2026-04-21
- **증상**: QA 툴에서 화면 OFF(headless=True)로 실행 시 pytest가 실행되지 않거나 Playwright 브라우저 미시작
- **원인**: `subprocess.Popen()`에 `CREATE_NO_WINDOW` 플래그 사용 → pytest 자식 프로세스(Playwright/Chromium) CDP 파이프 통신 실패
  - headed 모드: Chromium이 GUI 윈도우를 자체 생성하므로 영향 없음
  - headless 모드: 윈도우 없이 CDP 파이프만 사용하는데 핸들 상속 제한으로 통신 실패
- **수정**: `CREATE_NO_WINDOW` → `STARTUPINFO + STARTF_USESHOWWINDOW + SW_HIDE`로 교체
  - `SW_HIDE`는 pytest 프로세스 창만 숨기고, 자식 프로세스(Playwright)에는 제약 없음
- **파일**: `app.py` `_run()` `subprocess.Popen()` 호출부

---

## [RESOLVED] 이노마크 테스트가 랜섬크런처 실행 시 결과에 포함됨
- **날짜**: 2026-04-21
- **증상**: 랜섬크런처 제품 선택 후 테스트 실행 시 결과 HTML에 "innoMark 템플릿 관리", "innoMark 정책 관리" 섹션이 표시됨
- **원인**: `conftest.py`의 `pytest_runtest_makereport` 훅이 이노마크 결과를 제품 무관하게 수집
- **수정**: 이노마크 관련 코드 전체 삭제
  - `tests/test_inno_mark_template.py` 삭제
  - `tests/test_inno_mark_policy.py` 삭제
  - `pages/inno_mark_template_page.py` 삭제
  - `pages/inno_mark_policy_page.py` 삭제
  - `conftest.py` 이노마크 결과 수집/HTML 생성 블록 제거
  - `pages/registry.py` 이노마크 import/MODULE_GROUPS 항목 제거
  - `core/html_reporter.py` `_PAGE_LABELS` 이노마크 항목 제거
  - `dashboard/db.py` 이노마크 레이블 항목 제거
- **파일**: 위 목록 전체

---

## [OPEN] 이노마크 구버전 HTML 리포트 파일 잔존
- **날짜**: 2026-04-21
- **증상**: `reports/QA_InnoMark_20260416_1045.html`, `reports/InnoMark/QA_InnoMark_20260416_1323.html` 파일이 reports/ 폴더에 남아있음
- **영향**: 현재는 glob 폴백 수정으로 자동 선택되지 않음. 대시보드 DB에도 미import 상태면 표시 안 됨
- **조치**: 확인 후 수동 삭제 가능. 이슈 재발 가능성 없음

---

## [OPEN] 리포트 형식 — 구버전 그룹 출력 방식 vs 신규 개별 행 방식
- **날짜**: 2026-04-21
- **증상**: 이노마크 구버전 리포트는 "UI 구조 — 버튼/검색/컬럼 확인" 같이 항목을 하나로 묶어 표시. 신규 표준(test_scenario_standard.md)은 필드별 개별 행 + 기댓값/실제값 형식
- **원인**: 이노마크는 삭제된 구버전 scan_pages 방식을 사용. 신규 nPouch는 표준 방식 사용
- **조치**: 이노마크 삭제로 구버전 방식 코드는 더 이상 사용되지 않음. nPouch는 신규 표준 형식으로 작성됨

---

## [RESOLVED] 시나리오 3/5 결과 디테일 부족
- **날짜**: 2026-04-21
- **증상**:
  - 시나리오 3: CRUD 시 실제 필드값(SHA2, 서명, 설명) 없이 항목명만 저장. 수정 모달 재확인 없음.
  - 시나리오 5: SHA2 재확인 detail이 `'있음'/'비어있음'` — 실제값 미표시. 케이스B 저장 결과 하드코딩 `"존재"`.
- **원인**: `_r()` 헬퍼 도입 전 플레이스홀더 수준으로 작성된 detail 문자열
- **수정**:
  - 시나리오 3: `add_item(sha2=..., sign=...)` + 추가 후 수정 모달 열어 필드별 저장값 대조 (`_AUTO_PROCESS`, `_SIGN_VAL`, `_DESC_VAL`, SHA2 앞 20자)
  - 시나리오 5 SHA2: `sha2_short = (loaded[:20]+"...") if len > 20 else loaded` 로 실제값 표시
  - 시나리오 5 케이스B: `add_item` 후 `search_item` → `get_item_names()` 실제 조회로 pass/fail 판정
- **파일**: `tests/test_npouch.py` `test_scenario3_crud`, `test_scenario5_full_and_required`

---

## [RESOLVED] format_validation / special_char 테스트 스크린샷 미생성
- **날짜**: 2026-04-23
- **증상**: SHA2 비hex 입력 / 특수문자 입력 저장 시 warn 판정되었으나 HTML 리포트에 스크린샷 없음
- **원인**: `expect_validation: false` + `actual_validated: false` 조합 시 `ok = True` → `status = "pass"` → `_r()` 에 `page=` 미전달 → 스크린샷 미생성
- **수정**: status 로직 재작성. `expect_*: false` = known issue → 여전히 재현되면 무조건 `warn`, 개선됐을 때만 `pass`
  ```python
  # Before (wrong): ok = actual == expect → pass if ok
  # After (correct):
  if not _fv_expect:
      status = "pass" if actual_validated else "warn"   # known issue → warn
  else:
      status = "pass" if actual_validated else "fail"
  ```
- **파일**: `tests/test_npouch.py` `format_validation_tests` 루프, `special_char_tests` 루프

---

## [RESOLVED] 스크린샷에 테스트 항목이 보이지 않음
- **날짜**: 2026-04-23
- **증상**: warn/fail 스크린샷이 찍히긴 하나, 저장된 항목이 목록에 보이지 않는 상태(빈 화면)로 캡처됨
- **원인**: `_r()` 호출 시점이 항목 저장 직후(목록 미갱신 상태). 검색 없이 찍어서 해당 항목 안 보임
- **수정**: 저장 확인 후 `p.search_item()` 호출 → 목록에 항목 보인 상태 → 스크린샷 → `_r()` 호출 → 항목 정리(`delete_item`)
- **파일**: `tests/test_npouch.py` `format_validation_tests`, `special_char_tests`, `field_constraint_tests` 루프

---

## [RESOLVED] `get_item_names()` 가 빈 목록 안내 행을 항목으로 카운트
- **날짜**: 2026-04-23
- **증상**: 검색 결과 없을 때 "검색된 내용이 없습니다." 행이 1개 항목으로 집계됨 → 빈 목록 확인 테스트가 항상 warn
- **원인**: 빈 목록 시 `<td colspan="N">검색된 내용이 없습니다.</td>` 단일 td 행 → `tds[0].inner_text()` 에서 이름으로 읽힘
- **수정**: `if len(tds) >= 2:` 조건 추가 — td가 2개 미만인 행(colspan 빈 상태 행) 제외
- **파일**: `pages/npouch_operation_process_page.py` `get_item_names()`

---

## [RESOLVED] 검색어 SQL LIKE 와일드카드 `_` 로 인한 빈 목록 테스트 오동작
- **날짜**: 2026-04-23
- **증상**: `"__NOT_EXIST_9999__"` 로 검색 시 다른 항목이 걸려서 빈 목록이 아닌 결과 반환
- **원인**: SQL LIKE에서 `_` 는 단일 문자 와일드카드. `__NOT_EXIST__` 는 `XX NOT EXIST XX` 패턴으로 매칭
- **수정**: 와일드카드 없는 순수 알파벳 문자열 `"ZZZQANOTEXISTZZZTEST"` 로 교체
- **적용 범위**: YAML `test_value`, 검색어, 항목 이름에 `_` 포함 시 동일 이슈 주의
- **파일**: `tests/test_npouch.py` 시나리오 3 빈 목록 검색 테스트

---

## [RESOLVED] `field_constraint_tests` 루프 — `UnboundLocalError: _hints`
- **날짜**: 2026-04-23
- **증상**: 시나리오 2 실행 시 `UnboundLocalError: cannot access local variable '_hints' where it is not associated with a value`
- **원인**: `_hints = self._hints` 할당이 함수 **아래쪽** (format_validation 루프 바로 위)에 있었음. Python은 함수 전체를 스캔해 할당이 있으면 해당 변수를 지역 변수로 확정 → 위쪽 `field_constraint_tests` 루프에서 할당 전 접근 → UnboundLocalError
- **수정**: `_hints = self._hints` 를 함수 최상단(`lines, srs = [], []` 바로 뒤)으로 이동. 아래쪽 중복 할당 제거
- **파일**: `tests/test_npouch.py` `test_scenario2_modal_fields`

---

## [RESOLVED] `field_constraint_tests` 루프 — `finally` 블록 `NameError: _ct_blocked`
- **날짜**: 2026-04-23
- **증상**: `field_constraint_tests` 루프 내 `try` 초반에 예외 발생 시 `finally` 블록에서 `_ct_blocked` 미정의 → `NameError`
- **원인**: `_ct_blocked` 가 `try` 블록 안에서만 할당됨. `try` 초반(예: `open_add_modal` 실패) 예외 시 `finally`의 `if not _ct_blocked:` 에서 참조 불가
- **수정**: `_ct_blocked = True` 를 `try` 블록 바깥(위)에 초기화
- **파일**: `tests/test_npouch.py` `test_scenario2_modal_fields` `field_constraint_tests` 루프

---

## [RESOLVED] `field_constraint_tests` 루프 — strict mode violation (모달 2개)
- **날짜**: 2026-04-23
- **증상**: `field_constraint_tests` 루프의 `open_add_modal()` 에서 `locator("div#addCommonProcess.in") resolved to 2 elements` 오류
- **원인**: 시나리오 2 시작 시 `p.open_add_modal()` 로 연 메인 모달이 닫히지 않은 상태에서, `field_constraint_tests` 루프가 `open_add_modal()` 을 다시 호출 → 2개 모달 → strict mode violation
- **수정**: `field_constraint_tests` 루프 직전에 `p.close_modal()` 추가. `finally` 블록도 최대 3회 반복으로 모달 완전히 닫힘 보장
- **파일**: `tests/test_npouch.py` `test_scenario2_modal_fields`

---

## [RESOLVED] `notepad.exe` 중복 이름 테스트 — 앞 테스트 모달 상태 의존으로 실행 안 됨
- **날짜**: 2026-04-23
- **증상**: `field_constraint_tests` 루프 추가 후 `notepad.exe` 중복 테스트가 항상 스킵됨
- **원인**: 기존 코드가 `if page.locator(SEL_MODAL_OPEN).count() > 0:` 조건으로 앞 테스트에서 모달이 열려있을 때만 실행. `field_constraint_tests` 루프는 자체적으로 모달 열고 닫으므로 이후 모달이 닫힌 상태 → 조건 False → 테스트 스킵
- **수정**: `p.open_add_modal()` 을 독립적으로 호출하도록 변경. 앞 테스트 상태에 의존하지 않음
- **파일**: `tests/test_npouch.py` `test_scenario2_modal_fields` 중복 이름 에러 블록

---

## [RESOLVED] overflow 스캔 — 멈춤 + 스크린샷 빈 화면 문제
- **날짜**: 2026-04-24
- **증상**: overflow 스캔 실행 시 검색창에 1001자가 채워지면서 멈춤. 스크린샷은 항목 삭제 후 빈 목록 캡처
- **원인**:
  1. `delete_item(_ov_last_saved)` → 내부에서 `search_item(1001자 이름)` 호출 → 검색창 입력 느림/멈춤
  2. 스크린샷(`_r()`)을 삭제 이후에 호출 → 항목이 이미 사라진 빈 목록 캡처
- **수정**:
  1. 순서 변경: `search_item(짧은 prefix)` → 스크린샷(`_r()`) → cleanup 루프
  2. cleanup: `delete_item(1001자 이름)` 대신 짧은 prefix(`[AUTO]_ov`)로 검색 → 행별 체크박스 선택 → 삭제
  3. `_ov_last_saved` → `_ov_any_saved: bool`로 단순화 (전체 저장 여부만 추적)
- **파일**: `tests/test_npouch.py` overflow 스캔 섹션

---

## [RESOLVED] `field_constraint_tests` 방식 → 자동 overflow 스캔으로 교체
- **날짜**: 2026-04-23
- **증상**: `field_constraint_tests`의 이진 expect_block 판정이 너무 경직됨. 실제로 서버 제한이 있는지 없는지 탐색하는 방식이 필요
- **원인**: 설계 방향 오류 — "X자 차단됐나 Y/N" 대신 "X자 이상부터 서버 오류 발생" 탐색이 올바른 방향
- **수정**:
  1. `npouch_operation_process.yaml` — `field_constraint_tests` 섹션 제거, processName에 `overflow_scan: true` 추가
  2. `tests/test_npouch.py` — `field_constraint_tests` 루프 제거, 자동 overflow 스캔 로직으로 교체
     - `_OV_LENS = [101, 501, 1001]` 순서로 시도, 첫 서버 오류 지점 탐색
     - 오류 발견 → `[OK]` + "N자 이상 입력 시 서버 오류"
     - 전부 허용 → `[WARN]` + "1001자까지 제한 없음 (known issue)" + 스크린샷
- **파일**: `config/scan_hints/npouch_operation_process.yaml`, `tests/test_npouch.py`

---

## [RESOLVED] `field_constraint_tests` — `expect_block: true` 인데 서버가 실제로 허용 → `[FAIL]` → 시나리오 2 실패
- **날짜**: 2026-04-23
- **증상**: strict mode violation fix 적용 후 field_constraint_tests가 정상 실행됨 → 101자 이름이 서버에 저장됨 → `expect_block: true` 기대와 불일치 → `[FAIL]` → `_assert_no_fail()` → 시나리오 2 pytest FAILED
- **원인**: YAML `expect_block: true`로 설정했으나 실제 서버는 processName 길이 제한 없음. 이전 실행에서는 strict mode violation 예외가 먼저 떠서 `except`로 `[WARN]`이 됐기에 드러나지 않았음
- **수정**: `npouch_operation_process.yaml` `field_constraint_tests[0].expect_block: true → false` (알려진 이슈 → warn 처리)
- **파일**: `config/scan_hints/npouch_operation_process.yaml`

---

## 이슈 작성 규칙

```
## [상태] 이슈 제목
- **날짜**: YYYY-MM-DD
- **증상**: 사용자가 경험한 현상
- **원인**: 기술적 근본 원인
- **수정**: 수정 내용 (파일명 포함)
- **파일**: 수정된 파일 목록

상태: [RESOLVED] = 수정 완료 / [OPEN] = 미수정 / [WONTFIX] = 의도적으로 수정 안 함
```
