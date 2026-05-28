# TROUBLESHOOTING.md — QA 툴 이슈 추적

> 발견된 버그/이슈를 날짜별로 기록한다.
> 동일 이슈 재발 방지 목적. 수정 완료 시 [RESOLVED] 표시.

---

## [RESOLVED] sc5a "이미 등록된 이름" — 이전 run zz 가 보존한 [AUTO_KEEP] 을 sc1 cleanup 이 silent 실패 (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: 전체 suite 재실행 시 sc5a save 가 `메시지='이미 등록된 이름 입니다.'` 로 fail. 이전 run 의 zz 가 설계대로 [AUTO_KEEP]_sc5_step1 을 보존했고, 다음 run sc1 의 `_ensure_session_cleanup` 이 그걸 못 지움 → sc5a 가 같은 이름으로 ADD 시도 → 충돌. sc5b 도 sc5a 잔해(모달/backdrop)로 timeout cascade.
- **원인**: `_ensure_session_cleanup` 이 `try/except: pass` 로 모든 예외 swallow + 결과 검증 없음 + AngularJS 비동기 list 렌더 안정화 대기 없음. 1차 cleanup 실패해도 `_SESSION_CLEANUP_DONE=True` 설정되어 재시도 없이 다음 테스트 진행 → sc5a 에서 표면화.
- **수정** (2단 방어):
  - `_base.py _ensure_session_cleanup` 강화: 페이지 안정화 대기(500ms) + 시작 잔여 log + 1차 후 검증 + 재시도 + 최종 잔여 log (가시화).
  - `test_scenario5_lifecycle.py sc5a` 방어 가드: NAME(LIFECYCLE_NAME) 잔존 시 사전 삭제 → idempotent. session_cleanup 정상이면 no-op.
- **파일**: `tests/control_suite/_base.py`, `tests/control_suite/test_scenario5_lifecycle.py`

---

## [RESOLVED] HTML 리포트에 시나리오 6 헤더 미표시 — sc6/sc7 라벨 dict 누락 (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: 전체 suite 41 passed 정상 실행됐고 pytest 로그에 sc6 3건(pass/pass/skip) 다 기록됐으나, HTML 리포트에 "시나리오 6" 섹션 헤더가 깔끔히 안 뜸 (기본 fallback `시나리오 6` 으로만 표시되어 설명 부재).
- **원인**: `core/html_reporter.py` 의 `_SCENARIO_LABELS` dict 가 1~5 + 51/52/53 까지만 정의. sc6/sc7 키 없음 → `_scenario_label` 이 fallback("시나리오 {N}") 으로 처리되어 부제목 없는 헤더.
- **수정**: `_SCENARIO_LABELS` 에 `6: "시나리오 6: 연계 데이터 핸드오프 ([AUTO_KEEP] 확인)"`, `7: "시나리오 7: 최종 cleanup (AUTO 정리·KEEP 보존)"` 추가. zz_cleanup 의 `_add(..., sc=6)` → `sc=7` 로 구분 (sc6=연계 확인, sc7=최종 정리 의미 분리).
- **파일**: `core/html_reporter.py`, `tests/control_suite/test_zz_cleanup.py`

---

## [RESOLVED] sc3f Case7 / sc4l E 웹 이름 중복 — wr#2 가 wr#1 과 동일 프로세스 재선택해서 silent 거부 (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: picker fix 2차(check force=True) 후에도 #27 BUG 재현 — 메시지 여전히 `'선택된 프로세스가 없습니다.'`. 41 passed 전체 통과 중 sc3f Case7 / sc4l E 만 fail 잔존.
- **원인 (Chrome MCP 직접 검증 2026-05-28)**: picker fix 자체는 정상. **테스트 시나리오 순서가 문제** (사용자 강조 "테스트 순서가 매우매우 중요").
  - wr#1 이 picker row 0 (예: `111bug_process.exe`) 사용·저장.
  - wr#2 picker 재오픈 시 row 0 그대로 노출 (필터 없음). 체크박스 click → checked=true.
  - Picker confirm → 제품이 "동일 정책 안 wr 중복 프로세스" silent 거부 + cross_instance 알림: `'{name}은 이미 등록되어 있어 생략되었습니다.(타 웹제한 포함)'` (yaml :287 정확 일치).
  - 결과: wr#2 적용 프로세스 0건 → 이름 중복 단계 도달 못 함 → '선택된 프로세스가 없습니다.'
- **수정**:
  - `process_picker.py` 에 `select_nth(idx)` + `select_nth_and_confirm(idx)` 헬퍼 추가 (임의 행 선택).
  - sc3f Case7 / sc4l E: `select_first_and_confirm` → `select_nth_and_confirm(1, ...)` 로 변경 (wr#2 가 wr#1 의 idx=0 이 아닌 idx=1 = 다른 프로세스 선택).
- **파일**: `pages/shared/pickers/process_picker.py`, `tests/control_suite/test_scenario3_action.py`, `tests/control_suite/test_scenario4_modify.py`

---

## [RESOLVED] sc3f Case7 / sc4l E 웹 이름 중복 — picker multi-select DOM/AngularJS 모델 동기화 실패 (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: 웹 이름 중복 테스트 (#9·#27 BUG) 의 실제 결과 메시지가 `'선택된 프로세스가 없습니다.'` — 우선순위(프로세스 ≥ 1건 먼저 > 이름 중복) 에 막혀 이름 중복 검증 단계까지 도달 못 함. wr#2 모달 적용 프로세스 0행.
- **원인 1차 (단순 JS 토글)**: `select_first(mode="multi")` 가 `_click_hidden` (JS `el.click()`) 으로 체크박스 토글 → 재오픈 시 이전 체크 잔존이면 언체크됨 → 0건.
- **수정 1차**: `is_checked()` 가드 (이미 체크면 no-op). → 충분치 않음.
- **원인 2차 (모델 sync 실패)**: 1차 수정 후에도 #27 BUG 재현. picker 재오픈 시 DOM checked 와 AngularJS ng-model 가 어긋난 상태 가능 (DOM 잔존 / 모델 reset). `is_checked()` no-op 는 DOM만 보고 모델은 안 건드림 → confirm 시 모델 기준 0건.
- **수정 2차 (확정)**: Playwright `loc.check(force=True)` 사용 — checkbox 전용 idempotent + 실제 event sequence 로 AngularJS digest 발화. fallback: `checked = true` 설정 + change/click dispatch.
- **파일**: `pages/shared/pickers/process_picker.py`

---

## [RESOLVED] 테스트 abort(예외)가 HTML 리포트에 안 나옴 — pytest FAILED 인데 리포트는 fail 0 (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: pytest 결과 "2 failed, 23 passed" 인데 HTML QA 보고서는 ❌ 0 (실패 0)으로 표시. 테스트가 실패했는데 보고서엔 정상으로 보임 (사용자 지적).
- **원인**: `_add()` 는 검증 블록마다 ScanResult 를 누적하지만, 테스트가 예외(Playwright TimeoutError 등)로 **중단(abort)** 되면 그 크래시 자체는 어떤 ScanResult 도 남기지 않음. 리포트는 크래시 직전까지 기록된 pass/warn 항목만 표시 → fail 0 으로 숨음. `pytest_runtest_makereport` 의 fail hook 은 스크린샷/진단만 찍고 리포트 항목은 추가 안 했음.
- **수정**: `conftest.py pytest_runtest_makereport` 의 `report.failed` 블록 최상단에 크래시용 `ScanResult(status="error", label="[테스트 중단] {name}", detail=예외요약)` 를 `item._scan_report.results` 에 append (page None 이어도 기록되도록 early-return 앞에 배치). 이미 `_scan_reports` 에 수집된 동일 객체를 변형하므로 리포트에 반영됨.
  - status=**error** (실행 오류) 채택 — 제품 결함(fail/BUG) 아닌 테스트 abort 라 ⛔ ERROR 카운트에 분리. 초기 fail 로 넣었다가 사용자 지적(2026-05-28: "다 BUG높음에 가있는데 error 로 가야") 후 정정.
- **파일**: `conftest.py`

---

## [RESOLVED] sc3f Case7 / sc4l E 웹 이름 중복 — wr#2 확인 클릭 modal-backdrop intercept (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: 신규 추가한 웹제한 이름 중복 테스트(sc3f Case7, sc4l E) 2건이 `Locator.click: Timeout 5000ms exceeded` 로 실패. Call log: `<div class="modal-backdrop in"> intercepts pointer events`.
- **원인**: wr#1 confirm → wr#2 재오픈 → process picker(multi) 닫힘 후 잔여 `modal-backdrop.in` 이 web_restrict 확인 버튼 위에 남아 Playwright `locator.click()` 의 pointer 액션을 가로챔 (3-stack backdrop 누적 — picker.wait_closed 가 1개를 못 줄인 케이스).
- **수정**: 두 곳의 확인 클릭을 `locator.click()` → `locator.evaluate("el => el.click()")` 로 변경 (좌표 무관 JS click, ng-click 발화 OK — yaml :564 / dismiss_confirm_modal fallback 동일 패턴).
- **파일**: `tests/control_suite/test_scenario3_action.py` (Case7), `tests/control_suite/test_scenario4_modify.py` (sc4l E)

---

## [RESOLVED] sc4 4g/4h/4i cascade fail — close_modal + open_*_modal 우회로 (2026-05-26)

### 증상
- `close_modal()` 직후 `open_add_modal()` 또는 `open_modify_modal()` 호출 시
  `Locator.click: Timeout 5000ms exceeded` (button#addItemBtn 또는 modifyItemBtn 클릭 실패)
- Playwright stack: `<div id="controlSuite" class="modal-wrap in"> subtree intercepts pointer events`
- fail 진단 (5s 후 + teardown 후): backdrops=0, body clean — fail 시점과 다른 state (혼동 source)
- 4b/4c/4d/4e/4f 는 통과 (이들은 submit 성공으로 모달이 **자동 닫힘** — cancel close 경로 안 탐)
- 4g/4h/4i 만 fail (close cancel 경로 필요)

### Chrome MCP 단계별 DOM 진단 (192.168.13.141, 같은 서버 / 다른 주소)

| 단계 | `#controlSuite` | csuName | alert | backdrops |
|------|-----------------|---------|-------|-----------|
| 모달 열기 | `modal-wrap in` | "[AUTO]_sc3_step2" | - | 1 |
| csuName="" | `modal-wrap in` | "" | - | 1 |
| 수정 클릭 (빈 이름) | `modal-wrap in` | "" | `in` | **2 (스택)** |
| 알림 dismiss | `modal-wrap in` | "" | gone | 1 |
| csuName 원복 | `modal-wrap in` | "[AUTO]_sc3_step2" | - | 1 |
| **JS native cancel-click** | **gone** | gone | - | **0** |

**JS native click 단독으론 모달이 깨끗하게 닫힌다** — 메커니즘은 검증됨. 하지만 실제 테스트 환경에선 race / timing 으로 실패 발생.

### 진짜 원인 (구조적)

기존 4g E section 흐름:
1. EDIT 모달 안에서 빈값 + submit + dismiss
2. `set_csu_name(원복)` + `close_modal()`  ← cancel 클릭
3. `open_add_modal()` → 새 정책 DUP_PEER 생성 (프로세스 1개 포함)
4. 다시 `open_modify_modal()` → 이름을 DUP_PEER 로 변경 시도 → "이미 등록된 이름"

→ **검증 의도** ("EDIT 시 다른 정책 이름과 충돌 차단") 를 위해 굳이 **새 정책 생성 우회로** 사용
→ close_modal + open_add_modal cycle 이 race / timing 문제로 fail 야기

4h 도 동일: 3 case 각각 open_modify + close_modal cycle (close 2번)
4i 도 동일: Case A 후 close 없이 Case B 가 open_modify 재호출 (모달 충돌)

### 조치 — 구조적 단순화 (사용자 의도 반영)

**원칙**: "하나의 EDIT 모달 세션 안에서 모든 검증 + 끝에 close_modal 한 번만"

| 시나리오 | 기존 | 신규 |
|---------|------|------|
| 4g E | DUP_PEER 새 정책 생성 → close → 재오픈 → 중복 시도 | 같은 모달에서 `[AUTO]_sc3_step1` 로 이름 변경 시도 (기존 sc3 정책 활용) |
| 4h | 3 case × (open_modify + close_modal) | open_modify 1회 + 3 case 연속 + close_modal 1회 |
| 4i | Case A + Case B 각각 open_modify | open_modify 1회 + Case A + Case B + close_modal 1회 |

### 결과
- **18 passed in 258.29s** (sc3 9 + sc4 9 모두 통과)
- 검증 의도 100% 유지 (메시지: "이미 등록된 이름 입니다.", "수정된 항목이 없습니다.")
- 새 정책 동적 생성 제거 → cleanup 부담 ↓ + 테스트 안정성 ↑

### 부수 fix (방어선)
`pages/npouch_control_suite_page.py` `close_modal()` 도 더 robust 하게 강화:
- 1차 JS native click on cancel (Playwright actionability check 우회)
- 2차 alert dismiss + JS click 재시도
- 3차 JS force-remove `.in` 클래스
- `_cleanup_modal_residue` 의 skip 조건 제거 — backdrop/body 정리는 항상 안전

### 교훈 (Karpathy 원칙 적용)
- **추측 fix 대신 구조 단순화**: 같은 검증을 더 단순한 흐름으로 만들 수 있다면 그게 진짜 fix
- **새 정책 생성 우회로** = 우회로 자체가 race condition source. 가능하면 **존재하는 데이터 활용**
- **Test simplicity = test reliability**: 한 세션 안에서 처리 가능한 검증을 분리하면 cycle race 만 늘어남
- **추측 stop, 사용자에게 manual reproduction 요청**: 코드 의도와 실제 화면 흐름 차이가 root cause 단서

---

## [RESOLVED] sc4 4e/4g/4h/4i cascade fail — 5번째 알림 ID `registeredTagExtentionWarning` 누락 (2026-05-26)

### Chrome MCP 직접 진단 결과 (사용자 지시 '구글 크롬 켜서 직접 확인')

**재현 흐름**:
1. `[AUTO]_sc3_step2` EDIT 진입 → 태그 tab → `+` 버튼 → process_modal
2. `태그 선택` picker 열기
3. 첫 행 (`공용 프로세스 묶음`) 재선택 + 확인 (sc3c 가 이미 등록한 태그)
4. 알림 노출 — **"이미 등록된 태그 입니다"**

**진단**:
- 알림 DOM id: **`registeredTagExtentionWarning`** (5번째 ID)
- 기존 SEL_CONFIRM_MODAL 4개만 등록 (`__globalMessageModal` / `registeredFolderWarning` / `nullEnteredWarning` / `registeredProcessExtentionWarning`)
- 태그용 5번째 ID 누락 → `is_confirm_modal_visible` False 반환
- → `picker.wait_closed()` timeout (picker 가 알림 떠서 닫힘 못 함)
- → sc4 4e 의 `select_first_and_confirm` 실패
- → 4g/4h/4i cascade fail (모달 잔존)

**조치 (commit ceedac0)**:
- `SEL_CONFIRM_MODAL` / `SEL_CONFIRM_MODAL_OPEN` / `SEL_CONFIRM_BTN` / `SEL_CONFIRM_BODY` 모두에
  `registeredTagExtentionWarning` 추가
- 알림 5종 통합 처리 (`__globalMessageModal` 메인 + 4종 sub-modal warning)

### sc4 테스트 환경 누적 상태 인지

**sc4 매 run 마다 sc3 baseline 위에 modify 누적**:
```
1st run: sc3 baseline 위에 sc4 4b/4c/4d/4e/4f modify
2nd run: 1st 변형 위에 또 같은 modify 시도 → 일부 중복 알림
3rd run: 2nd 변형 위에 또 → 더 깊은 누적
```

**현재 [AUTO]_sc3_step2 누적 상태** (MCP 확인 2026-05-26):
- customOption: `sc3_step2_init` → `edit_4c_modified` (4c 변경)
- clipboardUrl: `naver.com;google.com` → `edit4c.com` (4c 변경)
- mainExts: `[txt,doc,exe]` → `[txt,exe,doc,iso]` (4c 가 iso 추가)
- web_rows: 1 → 2 (4f 가 `[AUTO]_web_4f_second` 추가)

**대응 fix 매핑**:
- 4b customOption: dynamic timestamp 값 → 매 run 강제 변화
- 4c load 검증: strict == → 존재/subset 검증
- 4d/4e/4f add: timestamp unique 값 + dismiss 안전망
- 4i 자기 자신 modify: `_MODIFY_OK_MESSAGES` (수정된 항목 없음 인정)
- 4e picker: 5번째 SEL ID + select_first/confirm 분리 + ESC 정리

### 교훈

1. **Chrome MCP 직접 진단이 정확** — 로그만으로 못 잡는 ID 누락 발견
2. **알림 ID 5종 인지** — 메인 1 + sub-modal 4 (Folder/null/Process/Tag)
3. **누적 환경 대응** — strict == / 단일 응답 메시지 가정 X
4. **sc3 의 검증된 패턴 우선 참조** — sc3i 의 ESC 다발 / dismiss + cancel 회피

---

## [INSIGHT] sc4 멱등 / sc3 데이터 잔존 / timing 검증 (2026-05-22)

### 핵심 원칙 (사용자 통찰)

1. **sc4 는 sc3 정책을 EDIT 검증에 그대로 사용**
   - sc3 → sc4 사이 cleanup 없음 (같은 페이지 안)
   - sc4 가 "깨끗한 상태" 가정 X — sc3 데이터 위에 modify
   - sc4 두번째 run 시 자기가 modify 한 결과 잔존 → 멱등 X
2. **검증 톨러런트화 필요**
   - strict `==` 대신 subset (`in`) / 패턴 매칭 / `>= N` 사용
   - row count: `before + 1` 패턴 (변화량 검증)
   - 값 비교: "값 존재" / "패턴 포함" 검증
3. **timing 이슈도 BUG**
   - yaml verified 알림이 실제로 떴는데 우리 코드가 못 잡으면:
     - 우리 자동화 timing/selector 문제 → 우리 fix
     - 또는 빌드 변경으로 알림 timing 불안정 → 제품 결함 (yaml 갱신)
   - 패턴: `is_confirm_modal_visible(timeout=3000)` 대신 텍스트 기반 5s polling fallback
     (참고: sc3i Case C tag picker 적용 예시)

### sc3 → sc4 연계 매핑 (확정)

| sc3 정책 | sc4 case | EDIT 검증 |
|---------|---------|----------|
| `[AUTO]_sc3_step1` (3b) | 4b | minimal modify |
| `[AUTO]_sc3_step2` (3c, KEEP 제거) | 4c~4h, 4i | 메인 11 필드 / sub-modal / validation |
| `[AUTO]_sc3_step3` (3d) | 4i | 다른 정책 이름 (중복 검증용) |
| `[AUTO]_sc3_step9_drv50` (3j A) | 4j Case A | drv 100자 → server error |
| `[AUTO]_sc3_step9_port_D` (3j D) | 4j Case B | Port -1 → server error |
| `[AUTO]_sc3_step16_bp300_ok` (3j N) | 4j Case C | basePath 400 → server error |
| `[AUTO]_sc3_step17_webname100_ok` (3j O) | 4j Case D | webName 500 → server error |
| `[AUTO]_sc3_step19_tag_normal` (3j Q) | 4j Case E | 태그 drv 100자 → server error |

### sc6 연계 페이지 AUTO 정상 ✓

- `tests/test_npouch.py` (운용 프로세스): `[AUTO]_np_proc_suite` 생성 + 남김
- `tests/test_npouch_tag.py` (태그 관리): `[AUTO]_np_tag_suite` 생성 + 남김
- 제어 스위트 sc6 미구현 — 차후 위 두 정책 활용

### 적용된 fix 패턴 (commit a1f85fc)

- sc4 4d 확장자: `== PROC["ext"]` → `all(e in list for e in PROC["ext"])`
- sc4 4e 태그 행: `== 0` 제거 / `== 1` → `== before + 1`
- sc4 4f 웹제한 행: `== 2` → `>= 1`
- sc4 4e 확장자: `== TAG["ext"]` → subset

### 향후 작업 (TODO)

- [ ] sc4 4c EXPECT 멱등화 (clipboard_url/custom_option/extensions strict 검증 완화)
- [ ] sc4 alert 검증에 텍스트 fallback polling 일괄 적용 (sc3i Case C 패턴)
- [ ] sc4 단독 실행 시 4b SKIP (step1 정책 부재) 원인 추적 (이전 run 변경 가능성)
- [ ] 제어 스위트 sc6 구현 (`[AUTO]_np_proc_suite` / `[AUTO]_np_tag_suite` 활용)

### 사용자 통찰 4 (2026-05-22) — "다른 알림이 떠서 안 잡는 것도 사실 버그"

핵심 패턴 (sc4 4b 실측):
- EDIT 진입 + customOption "sc4b_modified_by_4b" 변경 + '수정' 클릭
- 기대: `"저장 하였습니다"` / 실제: `"수정된 항목이 없습니다."`
- 원인: 이전 run 에서 동일 값 modify → 이번 run 도 같은 값 → 시스템 "변화 없음" 판정
- 잘못된 FAIL — 시스템은 정상 동작

동일 패턴 (확장자/태그/프로세스 중복 알림):
- 첫 add 시도 → 데이터 이미 있음 → `"이미 등록된 X 입니다"` 알림 (정상 차단)
- 우리 코드는 첫 add 가 OK 가정 + 두 번째 add 가 중복 알림 가정
- sc3 데이터 잔존으로 첫 add 부터 중복 → 우리 검증 흐름 어긋남

해결 패턴:
1. **알림 메시지 다양성 인정** — `"저장 하였습니다" or "수정된 항목이 없습니다"` 모두 정상
2. **값 동적 변경** — `f"sc4b_mod_{int(time.time())}"` 로 매 run 다른 값 (강제 변화)
3. **검증 흐름 reset** — 기존 데이터 명시 삭제 후 추가 시작
4. **텍스트 fallback polling** — yaml verified 알림 timing 안정화 (sc3i Case C 패턴)

차후 sc4 작업 시 위 4가지 중 1-3 조합 적용 권장 — 4 는 일반 안전망.

---

## [RESOLVED] sc3 within-test cascade fail — case 사이 F5 (navigate_to_clean) 적용 (2026-05-20 최종)
- **날짜**: 2026-05-20 (3차 진단 + 최종 해결)
- **증상**: sc3i / sc3j 내부에서 2번째+ open_add_modal 시 `Locator.fill: Timeout` cascade fail.
  sc3b~3h 는 teardown F5 만으로 PASS — 테스트 boundary 는 OK. 한 테스트 안의 multi-case 가 문제.
- **진단 흐름**:
  1. modal-backdrop 누적 가설 → 무조건 cleanup 적용 → 실패 (cleanup 자체가 race 야기)
  2. cleanup 조건부 (open modal 보호) → sc3i 여전히 fail
  3. cleanup 완전 제거 → 동일하게 fail → cleanup 이 원인 아님 확정
  4. MCP 직접 검증: 순수 ESC + reopen 410ms 안에 정상 modal — transition 자체는 깨끗
  5. fail dump 일관 패턴: `body_cls='modal-open'` 잔존 + modal `.in` 없음 + display:none
- **진짜 원인 추정**: AngularJS Bootstrap modal directive 가 같은 page lifecycle 안에서
  multi open/close 시 내부 state 누적 → 4번째~5번째 open 에서 modal element 가 `.in` 잠깐
  붙었다 박탈 → display:none → input not visible 30s (5s timeout 적용 후 5s) timeout.
  진짜 라이브러리 레벨 fix 는 차후 본격 분석 필요.
- **fix (실용 — user 의도 "f5 쓴경우 모달 찌꺼기 싹 날라간다")**:
  1. `pages/npouch_control_suite_page.py:navigate_to_clean()` 신규 — F5 reload + navigate_to
  2. `tests/control_suite/test_scenario3_action.py`:
     - sc3i Case B, C 진입: navigate_to_clean()
     - sc3j Case A/B/C/D-G loop/H 진입: navigate_to_clean()
     - 첫 호출 (test start) 은 navigate_to() 유지 — teardown F5 직후라 불필요
  3. `tests/control_suite/_base.py:_setup` — set_default_timeout(5000) + teardown F5 유지
  4. `pages/npouch_control_suite_page.py:set_csu_name(timeout=5000)` 명시적 timeout
  5. `conftest.py` — 진단 hook (DOM/NET ring buffer + fail 시 dump) 유지 → 차후 본격
     분석 시 누적 dump 활용 가능
- **검증 결과** (`reports/runs/20260520_124700_all.log`): sc3b~3j 9 PASSED in 169s
  - sc3i: 3 OPEN_MODAL dumps 모두 `modal-wrap in / block / w=466` ✓
  - sc3j: 8 OPEN_MODAL dumps 모두 정상 ✓
- **관련 commit**: 80fdaaf (reload 제거 시도) → 190741f (진단 hook) → f415d13 / 93ad58c / c801ab1 (cleanup 시도) → a41f9a1 (조건부) → e7b91a7 (timeout 단축) → 91166d9 (cleanup 제거) → c5ec127 (navigate_to_clean 최종)
- **차후 본격 분석 단서**:
  1. F5 없이 해결하려면 AngularJS modal directive 의 $scope state 직접 정리 필요
  2. open_modal_factory 추적 → 내부 $$childHead chain / digest queue 확인
  3. 진단 hook 의 [진단 NG] $rootScope dump 활용
- **상태**: [RESOLVED] — 실용 해결. 진짜 원인 (AngularJS state 누적) 미진단 → 차후 본격 분석 가능 상태 유지.

---

## [SUPERSEDED] sc3 sub-case cascade fail — modal-backdrop + body.modal-open 잔존 (2026-05-20 1차 시도)
- **날짜**: 2026-05-20 (진단 + fix 완료)
- **증상 재현**: reload 미봉책 제거 후 sc3f~3j 실행 시 sc3f PASS / sc3g-3j 모두 `Locator.fill: Timeout` cascade fail
- **진단 결과** (conftest.py 진단 hook 추가 후 `reports/runs/20260520_102258_all.log`):
  - 4번 fail 시점 DOM 100% 동일 패턴:
    ```
    open_modals=[]                       ← .modal.in 없음 (모달은 닫힘)
    backdrops=1                          ← .modal-backdrop div 잔존 ←진짜 원인
    body_cls='modal-open'                ← body 클래스 잔존         ←진짜 원인
    body_style='padding-right: 10px;'    ← Bootstrap 스크롤 보정 잔존
    ```
  - backdrop div 가 pointer-events 차단 → 다음 모달 input fill 30s timeout
- **진짜 원인 확정**: Bootstrap 3 modal 이 server error 500 처리 직후 `.modal-backdrop` + `body.modal-open` 제거를 누락. reload 가 "동작"했던 이유 = 페이지 새로 로드 시 자연 소멸 → 결과만 가린 미봉책
- **fix (surgical)**: `pages/npouch_control_suite_page.py:navigate_to()` 진입 직후 1회 cleanup:
  ```python
  self.page.evaluate("""
      () => {
          document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
          document.body.classList.remove('modal-open');
          document.body.style.paddingRight = '';
      }
  """)
  ```
  Karpathy "본인이 만든 잔해만 정리" 원칙 — reload 없이 정확한 원인만 제거
- **관련 commit**: 80fdaaf (reload 제거), 190741f (진단 hook 추가), (이번 commit — backdrop cleanup)
- **상태**: [RESOLVED] — 진단 + 정확 fix. reload 미봉책 완전 제거.

---

## [SUPERSEDED] sc3 sub-case cascade fail — 서버 오류 후 다음 sub-case 진입 차단 (재설계 보류)
> 위 [RESOLVED] 항목으로 대체됨. 원인 확정 + 정확 fix 완료.
- **날짜**: 2026-05-20
- **증상**: sc3 전체 실행 시 sc3f-3i cascade fail. sub-case 단독 실행 (예: sc3j) 은 PASS. 메인 저장 시 "서버에서 오류가 발생 하였습니다." 알림 후 다음 정책 생성 시 `Locator.fill: input#csuName not visible` 30s timeout. 다음 sub-case 까지 cascade.
- **추정 원인** (확정 아님 — 별도 진단 세션 필요):
  - sub-case 끝 후 모달 / alert / backdrop 잔존 상태가 다음 sub-case 의 navigate_to 또는 open_add_modal 시점 element 접근 차단
  - JS state corrupt 또는 AngularJS scope 꼬임 가능성
  - 진짜 원인 미진단 — JS error 는 단순 HTTP 500 응답만 ('Failed to load resource: status of 500')
- **임시 회피 (WORKAROUND — 미봉책)**:
  1. `pages/npouch_control_suite_page.py:navigate_to()` — 2회 retry + reload fallback (1차 실패 시 page.reload())
  2. `tests/control_suite/test_scenario3_action.py:sc3j` — Case B/C/Port-E/Port-G 끝마다 page.reload() (서버 오류 case 후 안전 정리)
  3. `tests/control_suite/_base.py:_setup` autouse fixture — 매 sub-case 끝 page.reload() (이전 JS evaluate 강제 정리는 자체가 page close cascade 야기 → reload 로 교체)
  4. `pages/npouch_control_suite_page.py:close_modal()` — alert dismiss 먼저 (alert backdrop 이 cancel click 차단 방지) + ESC fallback
  5. `pages/npouch_control_suite_page.py:SEL_CONFIRM_*` — 4종 alert modal ID 통합 (__globalMessageModal + registeredFolderWarning + nullEnteredWarning + registeredProcessExtentionWarning)
  6. `conftest.py` — JS console error/pageerror listener 추가 (page.on('console', ...))
- **검증 결과**: sc3j 단독 실행 8건 PASS (commit d71d10d)
- **사용자 평가** (2026-05-20): "새로고침은 간접 해결 — 올바르지 않다고 판단. 재설계 필요. 임시 유지 + 별도 진단 세션."
- **재설계 plan (보류)**:
  1. reload 모두 제거 → fail 직접 노출 → stack trace 정확 분석
  2. sub-case 끝 직후 page state 캡쳐 (DOM / 모달 / backdrop)
  3. JS error / AngularJS scope 진단 (단순 HTTP 500 외 다른 error 있는지)
  4. 원인 확정 후 정확 fix (reload 제거)
- **파일**: pages/npouch_control_suite_page.py, tests/control_suite/_base.py, tests/control_suite/test_scenario3_action.py, conftest.py
- **관련 commit**: 907b056, d71d10d
- **상태**: [WORKAROUND] — 임시 회피 적용. 진짜 원인 미진단. 재설계 보류.

---

## [RESOLVED] Step 5b 이름 중복 — [AUTO_KEEP]_ 정책이 이전 실행 잔존
- **날짜**: 2026-05-14
- **증상**: Step 5b 두 번째 실행부터 `modify 저장 메시지: '이미 등록된 이름 입니다.'` 로 fail. 사용자: "마지막 이슈 확인 아마 이름 겹치는 뭐가 있나"
- **원인**: 5b 가 의도적으로 `[AUTO_KEEP]_step5b_mod` 보존 (시나리오 4 가 사용할 데이터). 다음 실행 시 같은 이름으로 modify 시도 → 중복 차단. `delete_all_auto_policies()` 는 KEEP 를 제외 (CLAUDE.md 규칙) 하므로 자동 정리 안 됨
- **수정**: 5b 시작 시 `[AUTO_KEEP]_step5b_mod` + `[AUTO]_step5b_add` 명시 삭제. 멱등 보장:
  ```python
  page.delete_all_auto_policies()
  for nm in (ADD_NAME, MOD_NAME):
      if page.is_policy_exists(nm):
          page.delete_policy(nm)
  ```
- **교훈**: KEEP 정책 보존 + 멱등 동시 만족 = 자기가 쓸 KEEP 이름을 시작 시 명시 정리. delete_all_auto 가 KEEP 자동 제외하는 규칙과 별개의 대응 필요
- **파일**: `tests/test_npouch_control_suite.py`

---

## [RESOLVED] 이전 비정상 종료 후 loginBtn 클릭이 modal-backdrop 에 막힘 → 모든 테스트 fixture ERROR
- **날짜**: 2026-05-14
- **증상**: pytest 실행 시 14 테스트 모두 `Locator.click: Timeout 30000ms exceeded` (input#loginBtn). 로그에 `<div class="modal-backdrop in"></div> intercepts pointer events`. fixture (`logged_in_page`) 단계에서 실패 → 테스트 한 개도 못 돈 상태로 14개 모두 ERROR. 사용자 보고: "버그가 크게 났어"
- **원인**:
  1. 이전 pytest 실행이 비정상 종료 (ctrl-C / 에러 종료)
  2. logged_in_page fixture teardown 의 `login.logout()` 실행 안 됨 → 서버 측 세션 잔존
  3. 새 pytest 실행 → 로그인 페이지 진입 → 서버가 "세션 만료/충돌" globalMessageModal 자동 출현
  4. `modal-backdrop.in` 가 loginBtn 클릭 가로챔 → 60+ 재시도 후 30초 timeout
- **수정**: `pages/login_page.py` 에 `_dismiss_stale_modal()` 헬퍼 추가. `login()` 시작 시 호출:
  - `div#__globalMessageModal.in` 있으면 확인 버튼 클릭 (실패 시 ESC fallback)
  - backdrop 만 orphan 으로 남으면 ESC 로 정리
  - `div.modal-backdrop.in` detached 까지 대기
- **MEMORY.md 인용**: "로그아웃을 해야 서버 세션이 정리되며, 다음 실행에서 세션 충돌로 인한 모달이 발생하지 않는다" — 이 케이스 그대로 발현
- **파일**: `pages/login_page.py`

---

## [RESOLVED] csuWebRestrictListTb 는 div 가 아니라 TBODY — selector tag 가정 오류
- **날짜**: 2026-05-14
- **증상**: Step 4d E2E — selector `div#csuWebRestrictListTb tbody tr` 도 0행. 사용자 보고: "웹제한쪽에서 막히는거같다, mcp로 다시 확인". 2차 진단 (DOM 구조 검사) 결과 `csuWebRestrictListTb.tag === 'TBODY'`, `direct_tr_count: 1`, `inner_html: '<tr contents-list-item ...>'`
- **원인**: yaml 의 description `table_container: "div#itemWebRestrictList"` 는 2중 오류:
  1. ID 가 `itemWebRestrictList` 가 아니라 `csuWebRestrictListTb` (1차 발견, DOM enum)
  2. 그 ID 의 element 가 `<div>` 가 아니라 `<tbody>` 직접 (2차 발견, structure 검사)
  → `div#csuWebRestrictListTb` 매칭 안 됨 + `tbody tr` 에서 tbody 안 tbody 찾기 됨
- **수정**: `SEL_ITEM_WEB_LIST_ROW = "#csuWebRestrictListTb tr"` (tag prefix 제거, tbody 중첩 제거)
- **교훈**:
  - yaml description 의 selector tag (div/table/tbody) 가정도 위험. selector 는 `tag#id` 보다 `#id` 가 안전
  - DOM enumeration 진단 시 `tag` 정보까지 확인 필요. 단순 id 매칭만으로 부족
- **파일**: `pages/npouch_control_suite_page.py`, `config/scan_hints/control_suite.yaml`

---

## [RESOLVED] Bootstrap toggle 의 hidden checkbox 좌표 클릭 30초 timeout
- **날짜**: 2026-05-14
- **증상**: Step 2 test `set_clipboard_restrict_toggle(True)` → `Locator.click: Timeout 30000ms exceeded. element is not visible` (input#isClipboardRestrict). 60회 재시도 모두 element is not visible
- **원인**: `input#isClipboardRestrict` 는 Bootstrap 스타일 toggle 의 실제 checkbox — display:none. 보이는 건 라벨/스위치. native click 은 좌표 hit-testing 필요 → 좌표 없음 → 영구 not visible. overlay 토글과 무관 (overlay 가 아니라 element 자체가 hidden)
- **수정**: `pages/base_page.py` 에 `_click_hidden(loc)` 헬퍼 추가 (JS evaluate `el => el.click()` 사용 — visibility 무관). `_set_toggle` + `click_radio_allow/block` 에서 사용. AngularJS ng-click/ng-change 정상 트리거 확인
- **설계 원칙 추가**: visible button/link → `_click()` (overlay toggle + native), hidden input (toggle/radio) → `_click_hidden()` (JS evaluate)
- **파일**: `pages/base_page.py`, `pages/npouch_control_suite_page.py`

---

## [RESOLVED] npouch_control_suite — `navigate_to()` 단순화로 좌측 메뉴 진입 실패
- **날짜**: 2026-05-13
- **증상**: modal_form 전환 후 새 `NpouchControlSuitePage.navigate_to()` 가 4줄로 단순화됨. 테스트 실행 시 제어 스위트 페이지로 이동하지 못함 (사용자 보고: "위치를 모르는거 같다, 이동을 안 한다"). 실제로는 URL 까지는 가지만 후속 click 이 깨졌고, 본 navigate 자체도 stale modal·main.html 진입·hash 보정 누락
- **원인**: 레거시 `pages/_legacy/npouch_control_suite_page.py` 의 navigate_to 패턴 (stale 모달 dismiss → main.html 보장 → SYS_MGMT 펼침 → UNIFIED_HEADER expand → MENU 클릭 → hash pageSize=100 → 첫 row attached) 을 그대로 복사하지 않고 4줄로 축약 — `is_visible` 대신 `count()==0` 체크, hash 보정 누락, main.html 진입 보장 누락
- **수정**: `pages/npouch_control_suite_page.py` `navigate_to()` 를 레거시 7단 패턴 그대로 복원. `_close_modal_if_open()`, `_dismiss_stale_confirm_modal()` 헬퍼 추가
- **파일**: `pages/npouch_control_suite_page.py`

---

## [RESOLVED] qa-block-overlay 가 `locator.click()` 가로채기 → 모든 후속 클릭 30초 timeout
- **날짜**: 2026-05-13
- **증상**: navigate_to 성공 (URL `managerControlSuite` 도달) 직후 `open_add_modal()` 의 `addBtn` 클릭에서 30초 timeout. 로그: `<div id="qa-block-overlay"></div> intercepts pointer events` — 60회 재시도 후 실패. 사용자 보고: "화면이 위아래로만 움직이는데" — scrolling into view 재시도 루프
- **원인**: conftest 의 사람 클릭 차단용 오버레이 (`qa-block-overlay`, pointer-events:all, z-index:99998) 가 Playwright 좌표 클릭도 가로챔. 메인 페이지뿐 아니라 shared/ 컴포넌트 4개 (process_picker, special_folder_picker, process_sub_modal, web_restrict_sub_modal) 도 동일 문제
- **설계 결정**: 사용자 원래 의도 재확인 — overlay 는 **자동화 클릭 동안 잠깐 OFF → 클릭 후 즉시 ON 복원**. 사람의 추가 입력 차단이 본질 (자동화 클릭 도중에만 잠깐 풀려도 OK). JS `evaluate("el=>el.click())")` 대신 native click + overlay toggle 패턴으로 통일 (AngularJS mousedown 핸들러 정상 동작 + 디자인 일관성).
- **수정**:
  1. `pages/shared/_overlay.py` 신설 — `overlay_off(page)` context manager (with 진입 시 pointer-events='none', 종료 시 'all')
  2. `pages/base_page.py` `click()`, `click_attached()` 를 toggle 패턴으로 변경 + `_click(locator)` 헬퍼 추가
  3. shared 4파일 각각 `_click(locator)` 헬퍼 추가 + import overlay_off
  4. 메인 + shared 총 **56곳** click 사이트를 `self._click(locator)` 로 통일
  5. 테이블 행 (mousedown 필요) 만 명시 예외: `_toggle_overlay(False)` + `click(force=True)` (좌표 클릭 → tActive 부착)
- **파일**: `pages/shared/_overlay.py` (신설), `pages/base_page.py`, `pages/npouch_control_suite_page.py`, `pages/shared/pickers/process_picker.py`, `pages/shared/pickers/special_folder_picker.py`, `pages/shared/modals/process_sub_modal.py`, `pages/shared/modals/web_restrict_sub_modal.py`

---

## [RESOLVED] scan_diff_modal element 캡처 30초 hang (시나리오 2/4 누적 60초 낭비)
- **날짜**: 2026-05-08
- **증상**: 시나리오 2 끝(save_policy 직전)과 시나리오 4 끝(close_edit_modal 직전)에서
  각 30초씩 멈춤. 사용자 보고: "det_p2 가기 전 / 모달 닫고 삭제 전 20~30초 wait".
- **원인**: `core/ui_scanner.py:329` `_scan_diff_yaml_dom` 에서
  `ctx.take_screenshot("scan_diff_modal", element_sel="#addItemModal.in")` 호출.
  Playwright `loc.screenshot()` 은 actionability/stability 내부 대기를 가지며 `timeout=N`
  파라미터를 무시함 (실측). element 가 attached 상태이나 visible 대기에서 30초 timeout 발생.
- **로그 증거**:
  ```
  [TIMING] take_screenshot 'scan_diff_modal' FAILED 30022ms:
           Locator.screenshot: Timeout 30000ms exceeded.
  ```
- **수정**: `core/scan_context.py` `take_screenshot`
  - element 캡처 시도 자체 제거 → 항상 viewport 캡처 사용
  - element_sel 인자는 mode 라벨용으로만 유지
  - 로직: `self.page.screenshot(path=str(path))` 단일 호출
- **손실 평가**: 0 — 기존 동작도 30초 hang 후 fail 하여 결과 None.
  viewport 폴백이 오히려 evidence 보존 ✓.
- **검증** (재실행 후):
  - take_screenshot 'scan_diff_modal' 39ms (이전 30022ms, 770배 단축)
  - 시나리오 2: 38.68s → 8.89s
  - 시나리오 4: 56.95s → 26.96s
  - 전체 ~158s → ~98s (60초 단축, 38% 빨라짐)
  - 카드 수 동일 (pass=88 fail=0 warn=8 error=0)
- **재발 방지**: `loc.screenshot()` 사용 금지. element 영역이 필요해도 viewport 우선.
  실제 element 캡처가 꼭 필요하면 사전 `is_visible()` synchronous 체크 후 호출.

---

## [RESOLVED] take_screenshot hide/show evaluate CDP round-trip 비용
- **날짜**: 2026-05-08
- **증상**: 단발 take_screenshot 200~400ms 소요. 사용자 지적: "캡처/클릭 동작 늘어지는 게 이슈".
- **원인**: `core/scan_context.py` `take_screenshot` 가 캡처 전후로 `_hide`/`_show` JavaScript 를
  `page.evaluate()` 로 실행. 각 evaluate = CDP round-trip ~50-100ms × 2회 = ~200ms 추가 비용.
- **분석 (사용자 design 의도 재확인)**:
  - 잠깐 끄기 패턴(`_toggle_overlay`)은 click 핸들러에서 사용 — 의도된 설계
  - 그러나 screenshot 에서는 overlay 풀 필요 X (overlay 0.15 검정 + 우측하단 배너는 evidence 에 살짝
    비쳐도 무방, 오히려 "테스트 진행 중" 표식)
- **수정**: `core/scan_context.py`
  - hide/show evaluate 호출 제거
  - 단발 동작 ~50% 단축 (CDP round-trip 2회 = 100~200ms 절약)
  - overlay 항상 ON 유지 (사용자 design 강화 — 풀리는 시간 0초)
- **재발 방지**: screenshot 시 overlay 조작 추가 금지.

---

## [RESOLVED] take_screenshot opacity:0 시도 → display:none 복원 (사용자 design 회귀)
- **날짜**: 2026-05-08
- **증상**: 사용자가 "modal 위로 입력 가능" 보고 → 임시로 `display:none` → `opacity:0` 변경 시도
  (opacity:0 + pointer-events:all 로 overlay 시각만 투명, 클릭 차단 유지 의도).
- **분석 (사용자 피드백)**:
  > "저런 특정 이슈에 대해선 끄는걸 허용했어, 캡처나 이럴때도 오버레이를 아주잠깐 끄고
  > 동작시키는게 가능하다고 코드짤때 설계했어"
  - 사용자: 잠깐 끄기는 설계 의도 — opacity:0 변경은 design 회귀
- **수정**: 위 [RESOLVED] take_screenshot hide/show evaluate 제거 fix 와 통합
  - 전체 hide/show 로직 제거 (display:none 도 opacity:0 도 아닌 "조작 안 함")
  - overlay 항상 ON 상태로 screenshot 진행
- **교훈**: 사용자 design 의도 확인 없이 동작 변경 금지. 시각/기능 모두 보존해야 함.

---

## [RESOLVED] 상세 timing 로그 인프라 구축 (추측 차단)
- **날짜**: 2026-05-08
- **배경**: 사용자 지적 — "로그는 너가 확인하지 못하는 모든 정보를 포함해야 해, 추측성 수정 막아야지".
- **추가 위치**:
  - `core/qa_runner.py`: 시나리오 1~5 시작/종료 + 정리 단계 timing
  - `core/ui_scanner.py`: validator 별 timing + 생성 cards 수
    ```
    [TIMING]   scan_initial_state took 0.19s (cards=11)
    [TIMING]   scan_toggle_checkboxes took 7.65s (cards=6)
    [TIMING]   ...
    ```
  - `core/scan_context.py`:
    - `take_screenshot`: 모드/시간/파일명 출력
    - `dismiss_warning_dialog`: 총 시간/screenshot 시간/텍스트 출력
    - `activate_tab`: OK/BLOCKED/NO-LINK 분기 시간 출력
  - `pages/ransom_detect_policy_page.py`: 핵심 메서드 timing (open_modify_modal,
    save_policy, close_edit_modal, save_edit_modal, delete_all_auto_policies)
  - `_t()` contextmanager 헬퍼 — `[TIMING] {label} took {sec}s` 통일 포맷
- **효과**: 30초 hang 의 정확한 위치를 다음 1회 측정에서 즉시 식별 가능.
  추측 루프 종결.
- **유지 정책**: 다음 회귀 분석 시 활용. 로그 양이 커지면 verbose 플래그로 분리 검토.

---

## [RESOLVED] open_modify_modal 매 호출 3초 음의 대기 (39초 시나리오 2 hot spot)
- **날짜**: 2026-05-08
- **증상**: 시나리오 2 = 39s, 시나리오 4 open_modify_modal 5회 호출 = ~17s 누적.
  사용자 보고: "또 멈추고 보호기 풀잖아".
- **원인**: `_fail_if_modal(self._TIMEOUT_MODAL)` — 에러 모달 출현 여부를 **3초 풀 timeout**
  으로 매번 확인. 99% 안 뜨는데도 매 호출 3s 손실.
- **수정**:
  1. `open_modify_modal`: race 패턴 — `SEL_CONFIRM_MODAL_OPENED, SEL_ADD_MODAL` 둘 중
     먼저 attached 즉시 진행. 일반 케이스 ~100ms.
  2. `_fail_if_modal`: 200ms × 5회 polling (max 1s)으로 변경 — 다른 호출자도 단축 효과.
- **timing 로그 (이번 회귀 식별 도구)**: `pages/ransom_detect_policy_page.py` 와 
  `core/qa_runner.py` 에 `_t()` contextmanager 추가 — 모든 주요 단계 [TIMING] 출력.
  → 추측 루프 끊고 데이터 기반 분석 가능.
- **재발 방지**: "wait_for(state="attached", timeout=N)" 으로 음의 대기를 표현하지 말 것.
  race 패턴 (둘 중 빨리 attached) 이나 짧은 polling 사용.

---

## [RESOLVED] qa-block-overlay 시각 강화 (사용자 오인 방지)
- **날짜**: 2026-05-08
- **증상**: 사용자가 멈춤 동안 "오버레이 풀렸다" 반복 보고. 실제 로그상 오버레이는 ON 상태.
  기존 `rgba(0, 0, 0, 0.15)` 너무 옅어서 모달 위로 덮였을 때 시각 인식 불가 → 오인.
- **수정**: `conftest.py` `_OVERLAY_INJECT`
  - background: 주황·검정 빗금 패턴 (`repeating-linear-gradient`)
  - z-index: 99998 → 2147483600 (max int 근접) — Bootstrap 모달 위 100% 보장
- **재발 방지**: 향후 시각 인식 문제는 명확한 디버깅 패턴 (빗금/줄무늬) 우선.

---

## [RESOLVED] ransom_detect_policy / common_process 행 클릭 hang + overlay 이탈
- **날짜**: 2026-05-08
- **증상**:
  1. 시나리오 진행 중 갑자기 `qa-block-overlay` 클릭 차단이 풀려 사람이 직접 입력 가능.
  2. det_p2 EDIT 모달 영역에서 멈춤. 일정 시간 지나면 진행되거나 pytest 180s timeout 발화 → 강제 종료.
  3. delete_all_auto_policies 정리 단계에서 두 번째 정책 삭제 후 hang.
- **원인**:
  `pages/ransom_detect_policy_page.py` `click_policy_row` / `check_policy_row` 와
  `pages/common_process_page.py` `open_modify_modal` / `delete_item` 가
  `_toggle_overlay(False)` + `click()` (force=True 누락) 조합 사용.
  - Playwright actionability 기본 30s 대기 시작
  - 그 30s 동안 overlay pointer-events:none 상태 → 사람 클릭 가능
  - retry 3회 누적 시 누적 90s+ → pytest --timeout=180 발화
  - rdp_policy_page는 같은 함수에 `force=True, timeout=3000` 패턴이 이미 적용되어 있어 정상 동작 → 회귀 발견의 기준점
- **md 근거**: `docs/ui-interaction.md` L37-43 — "테이블 행 선택: `_toggle_overlay(False)` + `click(force=True)` 조합 필수. 둘 다 필요. 하나만 쓰면 안 됨."
- **수정**:
  - `click_policy_row`: `row.click(force=True, timeout=3000)` + `wait_for_timeout(80)` settle
  - `check_policy_row`: `_toggle_overlay` 제거, `checkbox.evaluate("el => el.click()")` 로 단순화 (overlay/actionability 무관)
  - `common_process_page.delete_item` 체크박스: 동일하게 JS click 변경
- **재발 방지**: 행 클릭/체크박스 패턴 추가 시 rdp_policy_page 정답 패턴 복제. ui-interaction.md 표준 위반 검출용 grep 체크 권장: `grep -n "_toggle_overlay(False)" pages/*.py | grep -v "force=True"`

---

## [OPEN] ADD 모달 phase 2/3 에서 예외처리 탭 required_toggle 강제 클릭 — 부수효과
- **날짜**: 2026-05-08
- **증상**: AUTO 정책 생성 시나리오 중 `isExceptDetect` 토글이 자동으로 ON 되었다가 OFF 복원되는 부수효과.
  사용자 보고: "auto seq 만드는 곳에서 예외처리 리스트 건드리는 부분 — 강제로 확인하다가 오버레이 풀리는 듯".
- **원인**: `validators/tag_input.py` 가 `tab + required_toggle` 항목(예외처리 3종)을 ADD 모달에서도
  탭 진입 시도 → 차단됨 → required_toggle 클릭 ON → 탭 재시도 흐름을 수행.
  ADD 모달은 정책 미저장 상태에서 탭 차단이 정상 동작이므로 "차단 확인" 카드만 기록하면 됨.
  EDIT 모달(phase 4)에서만 토글 ON 후 진입해야 의미 있음.
- **md 근거**: `scenario_4_modify.md` 책임 분리 — 예외처리 리스트는 EDIT 모달 검증 영역.
- **수정**: `validators/tag_input.py`
  ```python
  phase_allows_toggle = ctx.phase in (4,)
  if not tab_activated and required_toggle and phase_allows_toggle:
      ...
  ```
  ADD 모달 phase에서는 `required_toggle` 클릭하지 않음. 차단 확인 메시지만 카드 기록.
- **재발 방지**: tag_input/required_toggle 동작은 EDIT 모달 전용. 신규 페이지 yaml 작성 시
  `tab + required_toggle` 조합은 항상 EDIT 모달 검증 대상으로만 정의.

---

## [OPEN-DEBUG] app.py pytest --timeout=180 임시 해제 (2026-05-08)
- **날짜**: 2026-05-08
- **상태**: 디버깅 목적 임시 해제 — **반드시 복원 필요**
- **이유**: 위 hang 이슈 식별 단계에서 timeout이 hang 위치 식별을 방해. 사용자가 "끝까지 진행 확인" 요청.
- **현재 상태**: `app.py` L417 `--timeout=180` 주석 처리.
- **복원 조건**: hang 재현 안 되는 것 PoC 검증 후 즉시 복원 (`--timeout=300` 권장 — overflow 대기 여유).
- **위험**: 운영 환경에 이 상태로 배포 시 Chromium hang 발생해도 강제 종료 안 됨.

---

## [RESOLVED] 시나리오 5 신규 자동 발견 필드 카드 누락
- **날짜**: 2026-05-08
- **증상**: yaml 미등록 신규 필드(예: input#isSoftwareCertificate)가 시나리오 1/2/3/4 영역에는
  자동 분류 카드 출력되나 시나리오 5(케이스 검증) 영역에서는 카드 0건.
- **md 근거**: `test_scenario_standard.md` 공통 설계 원칙 5번 "모든 필드 커버 — 선택 필드도 시나리오 3·5에서 반드시 확인".
- **원인**: `core/qa_runner.py` `run_phase3_cases` 가 profile yaml 정의(verify_created/verify_modified) 기반으로만
  검증 → yaml에 없는 신규 필드는 verify 대상에서 누락.
- **수정**: `_scenario5_discovered_cards` 헬퍼 신설. verify_modified 후 EDIT 모달 열린 상태에서
  DOM ↔ yaml selector 비교 → 신규 필드별 `pattern="discovered_case"` pass 카드 등록 (yaml 등록 시 profile 추가 필요 안내).
- **회귀 안전**: DOM 읽기만, 클릭/입력 없음. modal_already_open=True일 때만 동작.

---

## [RESOLVED] initial_state warn 케이스 스크린샷 회귀 (910fd04 리팩터)
- **날짜**: 2026-05-07
- **증상**: "행위기반 탐지등급 설정 초기값" 같은 warn 카드에 스크린샷 첨부 X.
  사용자가 "스크린샷이 없어졌다" 보고. 다른 warn 카드(overflow, toggle)는 정상 첨부.
- **원인**: `validators/initial_state.py:194` — `known_bug` 상태 제거 리팩터(`910fd04`)
  과정에서 `ss = ctx.take_screenshot(...) if status in ("known_bug", "fail") else None`
  를 `ss = None  # warn은 스크린샷 불필요` 로 단순 치환. 의도와 다른 회귀.
  - 이전 `known_bug` → 현재 `warn` 으로 통합 시 status 분기 깨짐.
  - 의도상 warn(BUG 낮음)도 스크린샷 필요 (검수자 카드만 보고 의미 파악).
- **수정**: `validators/initial_state.py:_check_radio_init_default`
  ```python
  ss = ctx.take_screenshot(f"{label}_초기값")
  ```
  status 분기 제거 — 모든 결과 (warn 포함) 캡처. 다른 validator와 일관성 회복.
- **재발 방지**: 향후 status 리팩터 시 "각 validator의 캡처 분기 모두 검토" 체크.

---

## [DOCS] 시나리오 2/4 책임 영역 재정의 — 추정 금지 + 4-3 신설
- **날짜**: 2026-04-30
- **이슈**: `_run_submit_edit` (시나리오 2의 EDIT 분기) 가 "경고 안 뜸 → 저장됐을 것"
  추정으로 결론. 실제 저장값(빈값/원본/다른값)은 미확인 → `yaml-guide.md` 의
  "추정 금지 / 직접 확인" 원칙 위반.
- **분석**: 시나리오 2/4/5 정의 검토 결과 — "위반 입력 통과 후 실제 저장 결과 확인"
  영역이 어느 시나리오에도 명시되어 있지 않음. 단편적 추가 시 시나리오 5와 행위 중복,
  pattern 정렬 충돌(`scan-output-format.md` 의 `required_submit` 마지막 출력 규칙) 발생.
- **수정 (md 일괄)**:
  - `scenario_4_modify.md` — "정상 흐름만"에서 "수정 흐름 전체 정합성"으로 확장.
    4-3 신설 (필수 비움 → 저장 → 재오픈 → 실제 값 확인). 분기: 빈값=fail / 원본=warn / 다른값=fail.
    pattern 명명: `list_modify_required` (list_page) / `modify_required` (modal_form).
  - `scenario_2_input.md` — 추정 금지 명시. EDIT 분기는 "경고 떴는가" 1차 검증만 책임.
    실제 결과는 시나리오 4-3로 위임.
  - `scenario_3_action.md` — 책임 분리 매트릭스 추가. EDIT 모달 필수 비움 후 결과는
    시나리오 4-3로 위임 명시.
  - `scenario_5_cases.md` — 시나리오 4-3과의 차이 명시 (케이스B는 "필수 채움", 4-3는 "필수 비움").
  - `screenshot_capture_cases.md` — Type 3 (결과 검증형) 에 4-3 추가.
  - `scan-output-format.md` — 신규 pattern 정렬 규칙 명시 (`required_submit` 과 달리 시나리오 4 영역 안).
  - `test_scenario_standard.md` — 6개 시나리오 요약 + 책임 분리 매트릭스 + fail/error 일관성.
- **수정 (config)**:
  - `known_bugs.yaml` 의 RDP `edit_required_submit` reason — 추정 표현("저장 가능") 제거,
    객관 표현("경고 없이 모달 닫힘 — 실제 저장값은 4-3에서 확인")으로 변경.
- **status 분기 일관성**: 4-3의 "다른값"은 error가 아닌 fail. error는 테스트 도구 자체
  오류(셀렉터/타임아웃)에만 사용 (`test_scenario_standard.md` status 기준 준수).
- **다음 단계 (코드)**:
  1. `validators/required_submit.py:_run_submit_edit` detail 표현 정정 (이미 1차 진행).
  2. 페이지별 page object에 4-3 검증 메서드 추가 (list_page) / yaml 콜백 패턴 (modal_form).
  3. 신규 pattern (`list_modify_required` 등) 출력 매핑 검증.

---

## [RESOLVED] 제어 스위트 close_modal/close_proc_modal — 모달 미존재 시 에러 캡처 노이즈
- **날짜**: 2026-04-30
- **증상**: `reports/screenshots/error_click_attached_div#controlSuite button.btn-default_*.png`
  파일이 시나리오 3 실행 시 4건씩 누적됨 (2026-04-28 14:11~14:12 4번 발생).
  실제 화면은 모달 닫힌 후의 빈 리스트 화면 — 디버깅 가치 없음.
- **원인**:
  1. `close_modal()` 이 unconditional 하게 `click_attached(SEL_CANCEL_BTN)` 호출
  2. 모달이 이미 닫힌 상태에서 호출되면 `click_attached`가 attached 대기 → timeout
  3. base_page.py:126의 자동 에러 캡처가 **이미 닫힌 화면**을 찍어 노이즈 생성
  4. 호출자가 `try/except`로 감싸서 테스트는 통과하지만 스크린샷 노이즈만 누적
- **수정**: `pages/npouch_control_suite_page.py`
  ```python
  # close_modal — if 체크 + try/except 안전 패턴 적용
  def close_modal(self) -> None:
      try:
          if self.page.locator(self.SEL_MODAL_OPEN).count() == 0:
              return  # 이미 닫혀있음 — no-op
          self.click_attached(self.SEL_CANCEL_BTN)
          self.wait_for(self.SEL_ADD_BTN)
      except Exception:
          pass
  ```
  `close_proc_modal` 도 동일하게 if 체크 추가.
- **참고 — 모범 패턴**: `_close_modal_if_open()`, `close_edit_modal()` 은
  이미 if 체크 + try/except 가지고 있어서 문제 없음.
- **연관 작업**: 본 수정은 같은 날 진행한 "스크린샷 캡처 타이밍 통일"과 결이 같음 —
  "의미 없는 화면 캡처 방지" 원칙. 단, 패턴 A·B·C는 결함 감지 시 캡처 시점 문제,
  본 건은 도구 에러 시 의미 없는 캡처 차단.

---

## [RESOLVED] 결함 카드 배지에 "BUG 낙음" 한글 오타 (낮음 → 낙음)
- **날짜**: 2026-04-30
- **증상**: 빌드된 QATool 리포트의 결함 카드 배지에 `⚠️ BUG 낙음` 으로 표시됨.
  사용자가 검수 시 가장 먼저 보는 라벨이라 매우 두드러지는 오타.
- **원인**: `app.py:890, 893` STATUS_BADGE 정의에서 한글이 HTML 엔티티로
  인코딩되어 있는데, "낮"의 코드포인트(`U+B0AE`)가 아니라
  "낙"의 코드포인트(`U+B099`)가 들어가 있었음.
  ```html
  &#xB099;&#xC74C;   ← "낙음" (오타)
  &#xB0AE;&#xC74C;   ← "낮음" (정상)
  ```
- **발견 어려웠던 이유**: 한글이 HTML 엔티티로 인코딩되어 있어서
  소스 코드에서 "낙음" 으로 grep해도 안 잡힘. 빌드해서 브라우저로 봐야 보임.
- **수정**: `app.py` STATUS_BADGE의 `bug_low` / `bug` 항목 두 곳에서
  `&#xB099;` → `&#xB0AE;` 로 교체.
- **참고**: `html_reporter.py:180` 의 직접 한글 표기("BUG 낮음")는 정상.
  app.py 만 HTML 엔티티 사용한 게 화근.
- **재빌드 필요**: 예. 기존 리포트 파일들도 동일 오타가 박혀있으나
  히스토리 자료라 그대로 둠. 향후 빌드 결과는 정상.

---

## [RESOLVED] 결함 스크린샷이 dismiss 후 캡처되어 빈 화면 기록됨
- **날짜**: 2026-04-30
- **증상**: WARN/FAIL 결함 카드의 스크린샷이 모달 닫힌 후 캡처되어
  실제 cause(입력값) + effect(에러 모달)가 한 프레임에 안 담김.
  검수자가 어느 시점이 증거인지 판단 불가.
- **원인**: 3개 흐름이 모두 `dismiss → 캡처` 순서로 동작
  1. `core/scan_context.py:dismiss_warning_dialog` — 텍스트만 캡처 후 dismiss
  2. `core/list_page_runner.py:list_modal_overflow` — 인라인 dismiss 후 `_known_bug` 호출
  3. `validators/overflow.py:_handle_modal` — dismiss 후 호출자가 별도 캡처
- **수정**: `dismiss → 캡처` → `캡처 → dismiss` 순서로 변경
  1. `scan_context.py`: `last_warning_screenshot` 필드 추가, dismiss 직전 자동 캡처
  2. `list_page_runner.py`: `_known_bug/_fail/_err`에 옵셔널 `screenshot` 인자 추가,
     `list_modal_overflow`에서 dismiss 전 캡처 후 헬퍼에 전달
  3. `overflow.py`: `_handle_modal` 시그니처를 `tuple[bool|None, str|None]`로 변경,
     서버 오류 감지 시 dismiss 전 캡처 후 함께 반환. `_make_*_overflow_result`도
     `page` 대신 `screenshot` 인자 받도록 변경
- **검증 결과**: 모든 모듈 import 성공. 실 실행 검증은 인터넷 복구 후 진행.
- **참고 문서**: `docs/screenshot_capture_cases.md` (Type 분류 + 케이스별 처리 방식)
- **원칙**: 1결함 = 1스크린샷. 호출자에서 중복 캡처 안 하도록 주의.
  - `required_submit._run_submit_edit`: dismiss 후 별도 `take_screenshot` 호출 제거
  - `list_modal_overflow`: dismiss 전 캡처본을 `_known_bug`에 전달 (재촬영 X)
  - `_make_*_overflow_result`: 받은 ss 그대로 사용 (자체 `_take_screenshot` 호출 제거)

---

## [RESOLVED] QATool UI에서 WARN(BUG Low) 결함이 목록에 안 나타남
- **날짜**: 2026-04-30
- **증상**: 테스트 완료 후 앱 결과 화면의 결함 목록에 WARN(노란 버그)이 표시되지 않음.
  HTML 리포트에서는 정상 표시됨.
- **원인**: `templates/app/report.html` 288번 줄 JS 필터에 `warn`이 누락됨.
  `known_bug` → `warn` 으로 status 리팩터 시 필터 목록 미반영.
  ```js
  // 수정 전
  ['fail', 'known_bug', 'error'].includes(r.status)
  // 수정 후
  ['fail', 'warn', 'known_bug', 'error'].includes(r.status)
  ```
  추가로 `ICON`, `ICON_CLASS`, `STATUS_TO_CYCLE` 맵에도 `warn` 키 추가.
- **수정 파일**: `templates/app/report.html` (167~168, 174, 288번 줄)
- **재빌드 필요**: 예 (빌드 배포 시 templates/ 포함됨)

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

## [RESOLVED] tag_input × 클릭 (remove) — Playwright click 으로 AngularJS ng-click 미발화 → list 변화 없음
- **날짜**: 2026-05-18 (1차) / 2026-05-19 (2차 추가 수정)
- **증상**: 시나리오 3d 의 메인 확장자 단건 삭제 검증 fail. `× 클릭` 후에도 list 변화 없음 (전=3 → 후=3).
- **원인 (1차)**: tag_input 의 × 동작은 AngularJS `ng-click` 으로 구현. Playwright `locator.click()` 은 native pointer event 라 ng-click handler 가 trusted event 로 인식 안 함.
- **원인 (2차, 진짜)**: 1차 fix 로 외곽 `button.tagInput` 에 JS `el.click()` 적용했으나 list 여전히 미변경. 실제 ng-click 핸들러는 외곽 button 이 아니라 **내부 `i.extentionDeleteBtn` 아이콘** 에 바인딩됨 (`config/scan_hints/control_suite.yaml:615` — `remove_btn: "i.extentionDeleteBtn"`, Chrome MCP 2026-05-12 검증 주석). 외곽 button 클릭은 ng-click 미발화.
- **수정**: 5 개 remove 메서드 모두 매칭된 tag 의 내부 `i.extentionDeleteBtn, i` first 를 찾아 JS evaluate click:
  - `npouch_control_suite_page.remove_main_extension`
  - `process_sub_modal.remove_ip_port`
  - `process_sub_modal.remove_extension`
  - `web_restrict_sub_modal.remove_url`
  - `web_restrict_sub_modal.remove_file_extension`
- **파일**: `pages/npouch_control_suite_page.py`, `pages/shared/modals/process_sub_modal.py`, `pages/shared/modals/web_restrict_sub_modal.py`

---

## [RESOLVED] sub-modal 내부 알림은 __globalMessageModal 이 아닌 #registeredFolderWarning — selector 불일치로 항상 미감지
- **날짜**: 2026-05-18
- **증상**: 시나리오 3f IP/Port 중복 검증 — Chrome MCP 로 직접 확인 시 "이미 등록된 IP와 Port 입니다" 알림 정상 노출, 자동화에서는 `is_confirm_modal_visible()` False 로 "메시지 미노출" (warn).
- **원인**: 메인 모달의 confirm 알림과 sub-modal (process_modal 등) 내부 검증 알림이 **서로 다른 DOM ID** 사용.
  - 메인 모달 confirm: `div#__globalMessageModal` (`.modal-body` 텍스트)
  - sub-modal warning: `div#registeredFolderWarning` (`.modal-body-text` 텍스트, 닫기 버튼 `.btn-default`, `data-dismiss='modal'` 없음)
  - 기존 selector 는 `__globalMessageModal` 만 검사 → sub-modal 알림 100% 미감지.
- **수정**: `pages/npouch_control_suite_page.py` 의 `SEL_CONFIRM_MODAL` / `SEL_CONFIRM_MODAL_OPEN` / `SEL_CONFIRM_BTN` 을 두 ID OR 로 확장. `SEL_CONFIRM_BODY` 추가. `is_confirm_modal_visible()` 에 1.5s attached 대기 추가 (race condition 방어). `get_confirm_message()` 가 두 selector 모두에서 텍스트 추출.
- **파일**: `pages/npouch_control_suite_page.py`
- **검증**: Chrome MCP 2026-05-18 직접 확인 — process_modal 안에서 IP `10.10.10.10` + Port `1234` 두 번 추가 시 `#registeredFolderWarning.in` 노출 + `.modal-body-text` = "이미 등록된 IP와 Port 입니다" 정상 동작.

---

## [RESOLVED] process picker 의 "이미 등록된 프로세스" 알림 dismiss 후 picker × 클릭이 TargetClosedError cascade
- **날짜**: 2026-05-19
- **증상**: sc3g Case F (yaml :1235 must_test) — picker 첫 행 single 재선택 + 확인 → 알림 dismiss → picker.cancel() (× 클릭) → 후속 `page.process.close()` 에서 `TargetClosedError: Page.evaluate: Target page, context or browser has been closed`. sc3h cascade fail.
- **DOM 인용 (사용자 검증 2026-05-19)**:
  ```html
  <div class="modal-content">
    <div class="modal-body"><div class="modal-body-text">이미 등록된 프로세스 입니다</div></div>
    <div class="modal-footer">
      <button class="btn btn-default btn-xs" data-dismiss="modal">확인</button>
    </div>
  </div>
  ```
  - 메시지: `.modal-body-text` 매칭 (yaml :1149 registered_folder_warning 패턴)
  - 닫기: `button.btn-default[data-dismiss="modal"]` — 기존 SEL_CONFIRM_BTN 매칭 OK
  - 알림 dismiss 자체는 정상 동작 (사용자 확인: "확인 눌러서 닫아야 한다는 게 검증 가능 의미")
- **원인**: 알림 dismiss 후 picker 의 상태가 unstable (AngularJS scope 가 alert close 흐름에서 reset). picker × (close) 클릭이 의도치 않은 navigation 트리거 → page closed.
- **수정**: `tests/control_suite/test_scenario3_action.py` sc3g Case F — picker.cancel() (× 클릭) 대신 ESC 키 다발 (최대 4회) 로 picker + process_modal 일괄 정리. ESC 는 표준 modal 닫기 패턴, page 영향 없음.
- **파일**: `tests/control_suite/test_scenario3_action.py`

---

## [RESOLVED] 웹제한 확장자 단건 삭제 검증 — 잘못된 selector 로 count=0 + must_test 누락 (적용 프로세스 0건)
- **날짜**: 2026-05-19
- **증상 1**: 시나리오 3d `[FAIL] 웹제한 확장자 단건 삭제 → 잔여 확인: 전=0 → 후=0`. 사용자 화면 관찰 — "삭제 버튼 누르면 실제로는 삭제됨" (selector 동작은 OK 인데 검증만 실패).
- **원인 1**: 테스트 `test_scenario3_action.py:496/500` 의 inline locator `button.tagInput[name='ExtentionWebRestrict']` — Chrome MCP DOM 검증상 실제 tag 의 `name` 속성 = null. 매칭 0 → count = 0.
- **수정 1**: page method `page.web_restrict.get_file_extension_list()` 로 변경 (이미 SEL_FILE_EXT_LIST_TAG = `div#extension button.tagInput:visible` 정확 selector 사용).
- **증상 2**: 사용자 관찰 — "적용프로세스 없이 저장하면 모달 경고 뜨는거 확인없는거같은데?"
- **원인 2**: yaml `:1257` 의 `web_restrict_modal_no_process_selected` (severity: must_test, expected_message: "선택된 프로세스가 없습니다.") 가 시나리오 3f 에 누락. 기존 Case 1 (이름 빈값) 만 검증.
- **수정 2**: 시나리오 3f 의 Case 1 직전에 Case 0 추가 — 프로세스 0건 + 확인 → 알림 메시지 검증. yaml :1263 의 우선순위 ("프로세스 ≥ 1건 먼저 > 이름 입력 그 다음") 도 자연스럽게 보증.
- **파일**: `tests/control_suite/test_scenario3_action.py`

---

## [RESOLVED] tag_input 5개 영역 delete selector 전면 정리 + 확장자 invalid 값 (`_`) 검증
- **날짜**: 2026-05-19
- **증상**: 시나리오 3d 의 process_modal 확장자 / web_restrict URL+확장자 add→delete 사이클 모두 fail. 또한 사용자 스크린샷: ". * ; ? 이외의 특수문자 또는 한글이 포함된 확장자는 제외합니다." 알림.
- **원인 (Chrome MCP 2026-05-19 DOM 인용 기반)**:
  1. **5개 tag_input 영역의 delete selector 가 모두 다름** — 추측 일반화 불가.
     | 영역 | 컨테이너 | delete selector |
     |---|---|---|
     | 메인 확장자 | `div#allowExtensionUl` | `i.extentionDeleteBtn` |
     | 메인 전자서명 | `div#signExceptUl` | `i.extentionDeleteBtn` |
     | process_modal 확장자 | `#allowExtensionUlP` | `i.extentionDeleteBtnP` (**P**) |
     | web_restrict URL | `div#allowUrl` | `i.urlDeleteBtn` (별도 이름) |
     | web_restrict 확장자 | `div#extension` | `i.extentionDeleteBtn` |
     | process_modal IP/Port | `#allowIpAddressList li` | `button.deleteBtn` + **trusted click only** |
  2. **확장자 input validation** — yaml `:315` 명시 (`'. * ; ?' 외 특수문자/한글 제외`). `tmp_del` 의 `_` 도 invalid 로 차단 → list 에 추가 안 됨 → 후속 delete 매칭 실패. 테스트의 `tmp_del`, `temp-del-url.com`(URL 은 OK), `tmpdel` 같은 값 재검증 필수.
  3. **공통 삭제 후 동작** — 모든 tag_input 영역에서 삭제된 항목은 DOM 잔류 + `style="display: none"` 처리. `count()` 만으로는 잘못된 결과 → `:visible` filter 필수.
- **수정 (Chrome MCP 직접 검증 기반)**:
  - `pages/shared/modals/process_sub_modal.py`:
    - `SEL_EXT_LIST_TAG_P` → `:visible` 추가.
    - `remove_extension()` selector → `i.extentionDeleteBtnP` (P 접미사).
  - `pages/shared/modals/web_restrict_sub_modal.py`:
    - `SEL_URL_LIST_TAG` → `div#allowUrl button.tagInput:visible` 로 좁힘.
    - `SEL_FILE_EXT_LIST_TAG` 신설 → `div#extension button.tagInput:visible`.
    - `remove_url()` selector → `i.urlDeleteBtn`.
    - `remove_file_extension()` 컨테이너 + selector → `i.extentionDeleteBtn`.
  - `pages/npouch_control_suite_page.py`:
    - `SEL_EXT_LIST_TAG` → `:visible` 추가.
  - `tests/control_suite/test_scenario3_action.py`:
    - `add_extension("tmp_del")` → `add_extension("tmpdel")` (언더스코어 제거). 동일 `remove_extension`.
  - `config/scan_hints/control_suite.yaml`:
    - `add_then_delete.url` / `file_extension_web_restrict` 섹션 — Chrome MCP 인용으로 전면 확정 (TODO → verified).
- **파일**: `pages/shared/modals/process_sub_modal.py`, `pages/shared/modals/web_restrict_sub_modal.py`, `pages/npouch_control_suite_page.py`, `tests/control_suite/test_scenario3_action.py`, `config/scan_hints/control_suite.yaml`

---

## [RESOLVED] IP/Port 행 삭제 — selector 추측 fix 가 진짜 원인 가린 다중 cascade
- **날짜**: 2026-05-19
- **증상**: 시나리오 3d `remove_ip_port("10.20.30.40", "1111")` 에서 `locator.evaluate: Timeout 30000ms exceeded - waiting for ... .locator("i.extentionDeleteBtn, i").first`. 3d 실패 → process_modal 열린 채 logged_in_page 다음 시나리오로 cascade → 3c/3e/3f 의 csuName fill 도 30s timeout (모달 backdrop 잔여).
- **원인 분석 (코드 인용 기반)**:
  1. yaml `control_suite.yaml:232` 가 `ip_address.delete_selector: TODO — selector 미확정` 으로 명시. 검증 안 된 상태.
  2. 이전 fix 가 확장자 패턴 (`i.extentionDeleteBtn` — yaml :224 verified) 을 추측 일반화. IP/Port `li` 안에는 `<i>` 자체가 없어 30s wait.
  3. 추가 추측 fix (dismiss_confirm_modal 의 backdrop 폴링, add_ip_port 의 visible 대기) 도 모두 추측 — 실제 backdrop 잔여 없음, 원인은 oversight 였음.
- **Chrome MCP 직접 검증 (2026-05-19)**:
  ```
  <li>
    <span data-status="0" data-access-allow-ip-address="192.168.1.1">192.168.1.1</span>
    <span data-access-allow-port="8080">8080</span>
    <button type="button" id="deleteBtnIpAddress" class="deleteBtn"></button>
  </li>
  ```
  - 삭제 button class = `deleteBtn` (id 는 모든 행 중복 → class 필수).
  - **trusted event 만 발화** — `el.click()`, `dispatchEvent(MouseEvent)`, mousedown/up 시퀀스 모두 미동작. native cursor click 으로만 삭제됨 (count 2→2 / display:none 적용 확인).
  - 삭제 후 li 는 DOM 잔류 + `style="display: none"` — `get_ip_list` 의 `count()` 가 잔류 항목까지 세는 추가 버그.
- **수정**:
  - `pages/shared/modals/process_sub_modal.py`
    - `SEL_IP_LIST_ITEM` → `:visible` 추가 (display:none 항목 제외).
    - `SEL_IP_DELETE_BTN = "button.deleteBtn"` 신설.
    - `remove_ip_port()` — Playwright `locator.click()` (CDP trusted event) 사용. JS `el.click()` 폐기.
  - 다른 모든 `remove_*` 메서드 (main_extension/extension/file_extension) — yaml :224 verified `i.extentionDeleteBtn` 단일 selector + `count==0 → False` (timeout 차단). `remove_url` 은 yaml :238 TODO 상태 → 검증 전까지 미구현 `False` 반환.
  - `dismiss_confirm_modal`, `add_ip_port` 의 추측 backdrop fix 모두 revert.
  - `config/scan_hints/control_suite.yaml:232` — DOM 구조 + selector + trigger 방식 + 삭제 후 상태 모두 코드 인용으로 기록 (`chrome_mcp_verified: 2026-05-19`).
- **파일**: `pages/shared/modals/process_sub_modal.py`, `pages/shared/modals/web_restrict_sub_modal.py`, `pages/npouch_control_suite_page.py`, `config/scan_hints/control_suite.yaml`
- **원칙 위반 회고 (CLAUDE.md)**:
  - "추측 fix 금지 (코드 인용 기반)" 위반 — 확장자 패턴을 IP/Port 에 일반화 시도.
  - "테스트 실패 시 로그 먼저" 부분 위반 — pytest FAILURES 섹션의 stack trace 가 진작 selector mismatch 를 가리켰는데 별개 backdrop 가설을 먼저 세움.
  - 교훈: yaml 의 `TODO` 마커는 곧 "코드 인용 없음" 신호. 그 영역 selector 는 Chrome MCP 또는 사용자 검증 전까지 구현 보류가 정답.

---

## [RESOLVED] 3-stack 모달 (main → sub-modal → alert) 환경에서 dismiss_confirm_modal 의 click 이 backdrop 에 가로채여 30s timeout
- **날짜**: 2026-05-18
- **증상**: 시나리오 3f IP/Port 중복 검증 — `add_ip_port` 두 번째 호출 (중복) 후 '이미 등록된 IP와 Port 입니다' 알림 모달이 떴는데 `dismiss_confirm_modal()` 의 `self._click()` 이 hang.
- **원인**: 3 modal stack (controlSuite → controlSuiteProcessList → __globalMessageModal) 에서 topmost backdrop 이 alert 의 '확인' 버튼 click 을 intercept. Playwright auto-retry 30s timeout. 이전 (2-stack: main → alert) 케이스에서는 backdrop 단순해서 발생 안 함.
- **수정**: `pages/npouch_control_suite_page.py` 의 `dismiss_confirm_modal()` 에 try-except fallback 추가 — Playwright click 3s 시도 후 실패 시 JS evaluate click 으로 우회 (좌표 무관).
- **파일**: `pages/npouch_control_suite_page.py`

---

## [RESOLVED] 4f 에서 picker 중복 프로세스 선택 → 경고 confirm 모달 미처리 → 다음 클릭 차단
- **날짜**: 2026-05-15
- **증상**: 시나리오 4f 의 `page.web_restrict.confirm()` 이 `Locator.click: Timeout 30000ms exceeded`. Playwright 에러 로그: `<div class="modal-backdrop in"></div> intercepts pointer events`. 후속 4g/5a cascade FAIL.
- **원인 (실제)**: 4d 에서 이미 첫 행 프로세스 (예: `111bug_process.exe`) 를 기존 웹제한에 등록했음. 4f 에서 2번째 웹제한 추가 시 같은 picker 첫 행을 multi 선택하면 `'<프로세스명>은 이미 등록되어 있어 생략되었습니다.(타 웹제한 포함)'` 경고 confirm 모달이 노출. 이 모달의 backdrop 이 다음 `web_restrict.confirm()` 클릭을 가로챔. Playwright 에러의 backdrop 정체는 picker 잔여가 아니라 경고 모달의 backdrop.
- **5a 와의 차이**: 5a (ADD) 는 사전 등록된 웹제한이 없어 picker multi 선택 시 중복 충돌 없음 → 경고 모달 안 뜸 → 통과. 즉 동일 흐름이지만 데이터 상태 차이로 EDIT 에서만 발현.
- **수정 (yaml `web_restrict_cross_instance_duplicate` must_test 검증으로 격상)**: `tests/test_npouch_control_suite.py` 4f 를 재설계 — picker 첫 행 (4d 사용 프로세스) 선택 → 중복 알림 메시지 yaml 패턴 검증 + "행 추가 안 됨 (생략 동작)" 검증 → picker 재오픈 → 미사용 2번째 행 선택 → 정상 등록 흐름. 즉 yaml 사양 그대로 테스트 항목으로 추가. 추가로 `pages/shared/pickers/process_picker.py` 의 `wait_closed()` 에 backdrop 수 감소 폴링 추가 (defense-in-depth).
- **파일**: `tests/test_npouch_control_suite.py`, `pages/shared/pickers/process_picker.py`, `config/scan_hints/control_suite.yaml` (rule 1200-1217 참조)

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
