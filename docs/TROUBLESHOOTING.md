# TROUBLESHOOTING.md — QA 툴 이슈 추적

> 발견된 버그/이슈를 날짜별로 기록한다.
> 동일 이슈 재발 방지 목적. 수정 완료 시 [RESOLVED] 표시.

---

## [RESOLVED] 정책 페이지 delete_policy — 참조 잠금(DELETE 422) timeout ERROR — 2026-06-05

- **증상**: origin_protect sc5a (그리고 npouch_policy) lifecycle ADD 에서
  `[AUTO_KEEP]_sc5_origin_protect` 삭제 시도 → `DELETE 422` (엔파우치 정책이 부여 중, 참조 잠금)
  → 차단 모달이 안 닫힘 → `delete_policy` 의 `wait_for(detached)` 5초 timeout × 2(재시도) → ERROR 테스트 중단.
- **원인**: origin_protect / npouch_policy 의 `delete_policy` 에 차단 처리(rename fallback) 없음.
  프로세스/태그엔 있었지만 정책 페이지엔 미적용.
- **수정** (2026-06-05, 양쪽 정책 페이지):
  1. `delete_policy`: 2차 시도도 실패 시 → `_rename_policy_to_delme(name)` 호출 (timeout raise 대신).
     → `[AUTO]_DELME_<base>` 로 이름 변경, 테스터 수동 정리. 테스트는 진행 (중단 안 됨).
  2. `_rename_policy_to_delme`: open_modify_modal → 이름 필드 변경 → 저장.
  3. cleanup (`delete_all_auto_policies` / `delete_all_test_data`): `[AUTO]_DELME_` 제외 (재rename/무한 방지).
- **효과**: 참조 잠금으로 못 지우는 KEEP 정책 → rename 후 진행. sc5a 가 NAME 사라진 걸 보고 fresh 재생성.
  더이상 timeout ERROR 없음.
- **남은 점**: rename 후 원래 참조(엔파우치→원본보호 DELME)는 유지 — 테스터가 부여 해제 후 DELME 수동 삭제.
- **control_suite 도 추가** (2026-06-05): delete_policy 가 `while True` 루프라 참조된 정책(원본보호가 사용 중)
  만나면 **무한루프 위험**이었음. 동일 rename fallback + `[AUTO]_DELME_` 제외 + "삭제 후에도 이름 잔존 시 break" 안전망 추가.
- **참조잠금 rename fallback 적용 완료 = 5페이지 전부**: operation_process / tag / control_suite / origin_protect / npouch_policy.

### [수정 2026-06-05] rename fallback → fast-skip(재사용)로 전환 (사용자 방향)

- **배경**: rename fallback 이 매 실행 `[AUTO]_DELME_` 누적 + 삭제 2×5초 timeout 으로 sc1 멈춤(느림).
- **사용자 방향**: "auto keep 삭제 불가 = 정상 (삭제되면 결함). rename 누적 말고 재사용."
- **수정** (origin_protect / npouch_policy):
  1. `delete_policy`: 5초 detached-wait 제거 → "확인 클릭 후 ~1.2초 대기 → 모달 잔존 시 차단(참조 중)" 빠른 감지 →
     `'blocked'` 반환 + skip (hang/rename 없음). 반환값 `'deleted'|'blocked'|'skipped'`.
  2. origin_protect `sc5a`: 삭제 차단(blocked)이면 **재생성 안 하고 기존 재사용** (`_reused` 분기).
     보고서에 "참조 중이라 삭제 차단 → 정상 → 재사용 (삭제되면 결함)" pass 기록.
  3. npouch_policy: 참조 그래프 최상위라 자기 KEEP 미참조 → 항상 삭제 성공. delete_policy fast-skip 만 적용.
- **효과**: sc1 멈춤 해소 (5초×2 → ~1.2초), DELME 누적 0 (재사용), "삭제 불가=정상" 의도 반영.
- **남은 작업**: control_suite 는 아직 이전 rename fallback (느리지만 hang 안 함) — 추후 fast-skip 통일.
  날짜 기반 prefix (`[AUTO]_<날짜>`) 전환은 27파일 영향 → 별도 PDCA.

---

## [RESOLVED] origin_protect sc5 중복 실행 — sc6 의 클래스 import 로 pytest 재수집 — 2026-06-04

- **증상**: `tests/origin_protect/test_scenario6_keep_verify.py::TestOriginProtectScenario5Lifecycle::test_scenario5a_lifecycle_add` 가 FAIL.
- **원인**: `test_scenario6_keep_verify.py:11` 의 `from ... import TestOriginProtectScenario5Lifecycle`
  → pytest 가 sc6 파일에서도 `TestOriginProtectScenario5Lifecycle` 를 재수집 → sc5a/b/c 가 2회 실행됨 → 두 번째는 이미 만든 정책과 충돌 → FAIL.
- **수정** (2026-06-04):
  - sc6 의 import 를 alias 로 변경: `as _Sc5Lifecycle`
  - 사용처 `_Sc5Lifecycle.LIFECYCLE_NAME` 으로 변경
  - alias 가 underscore prefix 이므로 pytest 수집 대상 제외.
- **재발 방지 원칙**: 형제 test 파일에서 Test* 클래스 import 시 항상 alias (`as _XXX`) 사용.

---

## [PENDING] 제품 결함 — 원본보호에 부여된 제어스위트 삭제 가능 + 후속 오류 — 2026-06-04

- **제품 결함** (사용자 발견 2026-06-04, 테스트 중 인지):
  - 원본보호 정책에 부여된 제어스위트를 제어스위트 페이지에서 삭제 가능
  - 삭제 후 후속 화면에서 오류 메시지 출력 (참조 무결성 깨짐)
  - 기대 동작: "사용 중" 차단 모달 (npouch_policy → origin_protect 흐름은 정상 차단)
- **참조 그래프 동작 비대칭** (제품 자체 결함):
  | 부여 흐름 | 잠금 동작 |
  |---------|--------|
  | npouch_policy → origin_protect | ✅ 차단 (정상) |
  | origin_protect → control_suite | ❌ 삭제됨 + 오류 (결함) |
  | control_suite → tag | 미확인 |
  | tag → operation_process | 미확인 |
- **테스트 설계 — cross-page 패턴** (다음 PDCA 사이클):
  ```
  sc — cross_ref_<상위>_<하위>_blocked:
    1. <상위> 페이지 → AUTO 항목 + AUTO_KEEP 하위 참조 (이미 sc5 lifecycle 산출물)
    2. <하위> 페이지 navigate
    3. AUTO_KEEP_sc5_<하위> 삭제 시도
    4. 검증 — pass=차단 / fail=삭제됨 (known_bug 🔴)
    5. (선택) 후속 오류 화면 캡처
    6. 정리: 상위 페이지 복귀 후 AUTO 삭제
  ```
  - 단일 시나리오 내 페이지 이동 1회 — CLAUDE.md "함수 1개=시나리오 1개" 원칙 준수
  - 결함 발견 시 fail + known_bug 마킹 + 화면 캡처
- **참조 그래프 사전 확인 필요** (Chrome MCP):
  - 각 부여 흐름의 차단 모달 selector / 메시지
  - 결함 페이지의 후속 오류 화면 selector
- **현 상태**: 미수정 — exe 배포 우선. 다음 PDCA 사이클에서 cross-page 검증 + rename fallback + sc5 KEEP 명시 통합.

---

## [PENDING] 참조 그래프 연계 누락 — sc5 부여 시 KEEP 명시 비대칭 — 2026-06-04

- **확진 (코드 기반)**:
  - `npouch_policy/test_scenario5_lifecycle.py:189` → `_select_origin_protect_keep(page)` 명시 ✅
  - `origin_protect/test_scenario5_lifecycle.py:206` → `_csu_select_first(page)` (default "AUTO" 검색) ❌
    - `[AUTO_KEEP]_sc5_control_suite` 명시 선택 보장 없음
    - 다른 AUTO 잔존 시 그것 선택 → sc1 cleanup 에서 삭제됨 → 참조 끊김
    - 결과: control_suite AUTO_KEEP 이 참조 잠금 시나리오 미재현
  - `control_suite/sc6` (태그 적용) — 디렉토리 패턴이지만 sc6 lifecycle 의 KEEP 명시 여부 미확인
  - `tag/sc6` / `operation_process/sc6` — sc6 자체 미완성 (별도 PENDING 참조)
- **수정 방향** (다음 PDCA):
  1. `origin_protect sc5` 의 `_csu_select_first(page)` → `_csu_search_and_select(page, "[AUTO_KEEP]_sc5_control_suite")` 로 변경
  2. `control_suite sc5/sc6` lifecycle KEEP 명시 확인 + 보강 (태그 적용 시)
  3. `tag/operation_process` sc6 디렉토리 패턴 업그레이드 시 KEEP 명시 보장
  4. 일관 원칙: **모든 sc5 lifecycle 의 상위 참조 선택은 `[AUTO_KEEP]_sc5_<참조페이지>` 명시 검색** — 무작위 AUTO 선택 금지
- **현 상태**: 미수정 — exe 배포 우선, 다음 PDCA 사이클에서 통합 처리.

---

## [RESOLVED] cross-page 검증 예외 'NpouchTagPage' object has no attribute 'settings' — 2026-06-04

- **증상**: 태그 sc6 cross-page 검증이 `'NpouchTagPage' object has no attribute 'settings'` 예외로 실행 안 됨.
- **원인**: `base_page.py` 가 settings 를 `base_url`/`timeout` 으로만 추출 후 버림. cross-page 코드의
  `NpouchOperationProcessPage(self.p.page, settings)` 생성 시 settings 참조 실패.
- **수정** (2026-06-04):
  - `base_page.py:__init__` → `self.settings = settings` 저장.
  - `test_npouch_tag.py` cross-page → `self.p.settings` 직접 참조 (잘못된 `getattr(self, "settings")` 제거).

---

## [RESOLVED/오판정정] 태그 등록 프로세스 삭제 — 테스트 로직 오판 (제품 정상) — 2026-06-04

- **초기 오판**: cross-page 가 1단계 confirm("삭제 하시겠습니까?")만 보고 "차단 없음 = 제품 결함" 으로 fail/known_bug 마킹.
- **Chrome 직접 검증 (192.168.13.141 — innotium.iptime.org 만 차단됐던 것)**:
  - 1) 삭제 클릭 → `"선택한 항목을 삭제 하시겠습니까?"` (확인/취소)
  - 2) **확인** → 서버 검증 → `"태그에 해당 프로세스가 할당 되어 있습니다."` (차단, 확인만)
  - 3) 프로세스 **보존** (삭제 안 됨)
  - = **제품 정상 동작.** 참조 잠금이 confirm 후 2단계 서버 검증으로 작동.
- **실제 원인 = 테스트 로직 결함**: 1단계 confirm 만 검사, 2단계 응답 미확인.
- **수정** (2026-06-04):
  - cross-page 검증을 2단계로: 삭제 → 확인 → 2단계 모달 메시지 검사 → "할당" 있으면 pass.
  - `_delete_or_rename` (operation_process + tag 양쪽): 동일 2단계 — 확인 후 차단 모달 감지 시 rename.
  - known_bug 마킹 / SEL_MODAL_CANCEL 철회 (제품 결함 아님).
- **교훈**: confirm 프롬프트와 서버 검증 응답은 별개 모달. 삭제류 검증은 반드시 확인 후 2단계 응답까지 확인.

---

## [RESOLVED] rename fallback 구현 — 참조 잠금 차단 시 [AUTO]_DELME_ rename — 2026-06-04

- **배경**: sc1 clean slate (`cleanup_with_keep`) 가 `[AUTO_KEEP]` 항목 삭제 시도 시, 그게 다른 페이지(태그 등)에
  참조 중이면 "할당/사용/참조" 차단 → cleanup 멈춤.
- **사용자 결정 (2026-06-04)**: 참조 잠금 나오면 테스트 위해 그냥 이름 변경.
- **구현** (operation_process + tag 양쪽 페이지):
  - `rename_item(old, new)`: 수정 모달 → 이름 필드 변경 → 저장.
  - `_delete_or_rename(name)`: 삭제 시도 → 모달 메시지에 "할당/사용/참조" 있으면 → dismiss → `[AUTO]_DELME_<base>` rename → 'renamed' 반환. 아니면 정상 삭제 'deleted'.
  - `delete_all_auto_items` / `cleanup_with_keep`: `delete_item` → `_delete_or_rename` 로 교체.
  - **무한루프 방지**: cleanup 대상 필터에서 `[AUTO]_DELME_` 제외 (rename 후 재선택 안 됨).
- **효과**: cleanup 차단 없이 진행. `[AUTO]_DELME_*` 항목은 테스터가 참조 해제 후 수동 삭제.

---

## [DECISION] 사용자 테스트 설계 결정 — 2026-06-04

- **maxlength=None 처리**: 현행 유지 (필드별 WARN). 서버 검증 설계이지만 필드별 명시 표시 선호.
  DOM 속성 체크라 screenshot 없음 — 정상 (비시각적).
- **cross-page 참조 잠금 검증 위치**: **양쪽 다**.
  - 태그 sc6: 등록한 프로세스 삭제 차단 검증 (settings fix 후 활성).
  - 다음 페이지 (control_suite/origin_protect): 해당 페이지 도달 시 각 참조 흐름별 cross-page 검증 추가 (forward task).
    - control_suite → tag 적용 시 tag 삭제 차단
    - origin_protect → control_suite 부여 시 control_suite 삭제 차단
  - **삭제류 검증 표준** (2026-06-04 교훈): 삭제 → confirm "하시겠습니까" 확인 클릭 → 2단계 서버 응답("할당" 차단 등)까지 확인. 1단계 confirm 만 보고 판단 금지.
  - **참조 그래프 전체 Chrome 직접 검증 완료 (2026-06-04, 서버 192.168.13.141)**:
    | 흐름 | 차단 메시지 | 동작 |
    |----|--------|----|
    | tag → operation_process | "태그에 해당 프로세스가 할당 되어 있습니다" | ✅ 정상 2단계 |
    | control_suite → tag | "제어스위트에 해당 태그가 할당 되어 있습니다" | ✅ 정상 2단계 |
    | npouch_policy → origin_protect | "엔파우치 정책에 해당 정책이 할당 되어 있습니다" | ✅ 정상 2단계 |
    - 모두 정상 차단 — 참조 무결성 제품 결함 없음. 초기 "결함" 판정은 테스트 1단계-only 오판이었음.
    - 검증 방법: 임시로 상위에 하위 등록 → 하위 삭제 시도 → 차단 확인 → 임시 등록 원복.

---

## [PENDING] 참조 무결성 검증 누락 — 전 페이지 공통 시나리오 부재 — 2026-06-04

- **제품 동작 (정상)**: 상위가 하위를 참조 중이면 하위 삭제 차단.
  - operation_process ← tag (태그가 프로세스 등록)
  - tag ← control_suite / origin_protect (적용)
  - origin_protect ← npouch_policy (부여)
- **누락된 검증** (모든 페이지 공통):
  | 페이지 | 누락 검증 |
  |------|--------|
  | operation_process | 태그에 등록된 프로세스 삭제 차단 |
  | tag | 제어스위트/원본보호에 적용된 태그 삭제 차단 |
  | origin_protect | 엔파우치 정책에 부여된 원본보호 정책 삭제 차단 |
- **왜 앞 시나리오에서 이슈가 안 났나**:
  - sc6 lifecycle 의 AUTO_KEEP 잔존이 미완성 (태그 sc6 보고 참조)
  - 후속 페이지에서 참조 발생 안 함 → cleanup 충돌 회피됨
  - 단독 실행 = false PASS (참조 잠금 케이스 자체 미실행)
- **추후 수정 방향**:
  - **sc3 또는 sc4 에 참조 잠금 검증 추가** (각 페이지별):
    1. AUTO 하위 항목 생성
    2. AUTO 상위 항목 생성 + 1번 참조
    3. 하위 삭제 시도 → 차단 확인 (정상)
    4. 상위에서 참조 해제 또는 상위 삭제
    5. 하위 삭제 재시도 → 성공 확인
  - **sc6 lifecycle 완성** (태그/제어스위트 디렉토리 패턴 업그레이드 포함):
    - AUTO_KEEP 정상 잔존 → 다음 실행 cleanup 에서 참조 충돌 검증 가능
  - **cleanup 순서 보정** (참조 그래프 역순):
    `npouch_policy → origin_protect → control_suite → tag → operation_process`
  - **차단 모달 정보** (사용자 캡처 2026-06-04 — origin_protect 케이스):
  - 메시지 텍스트: `"엔파우치 정책에 해당 정책이 할당 되어 있습니다."`
  - 버튼: "확인" (전역 알림 modal 동일 selector 추정)
  - 매칭 키워드 후보: `"할당 되어 있습니다"`, `"할당"`, `"사용"` 중 어느 게 모든 페이지 공통인지 추가 조사 필요
- **rename fallback 패턴** (사용자 제안 2026-06-04 — 채택):
    - 삭제 시도 → "참조 사용 중" 차단 모달 감지 시 → 이름을 `[AUTO]_DELME_<원이름>` 으로 변경 → 진행 계속.
    - `base_page.py` 공통 메서드 `delete_or_rename_fallback()` 추가.
    - sc1/sc5c cleanup 가드: `[AUTO_KEEP]_*` + `[AUTO]_DELME_*` 둘 다 자동 삭제 제외.
    - 사용자가 수동 정리 (참조 해제 → 삭제) — 테스트 진행은 중단 없음.
    - 보고서에 "삭제 차단 → rename" 결과 명시 (의도 추적).
    - 차단 모달 메시지/selector 는 Chrome MCP 로 페이지별 사전 확인 필요.
- **현 상태**: 미수정 — exe 배포 우선, 추후 별도 PDCA 진행.

---

## [PENDING] 원본보호 정책 부여 시 삭제 잠금 — 검증 시나리오 누락 + cleanup 충돌 가능 — 2026-06-04

- **제품 동작 (정상)**: 원본보호 정책이 엔파우치 정책에 부여돼 있으면 해당 원본보호 정책 삭제 불가 (참조 무결성).
- **검증 누락**:
  - npouch_policy sc3/sc4 에서 원본보호 정책 부여 후, origin_protect 쪽에서 삭제 시도 → "삭제 차단" 확인 검증 없음.
  - 부여 해제 후 삭제 가능 검증 없음.
- **cleanup 충돌 가능 시나리오**:
  - 5 페이지 동시 실행 시 page 순서에 따라:
    - origin_protect sc1 cleanup → AUTO_KEEP 정책 삭제 시도
    - 그러나 직전 실행에서 `[AUTO_KEEP]_sc5_origin_protect` 가 `[AUTO_KEEP]_sc5_npouch_policy` 에 부여된 상태 잔존 → 삭제 실패
  - 사용자 보고: 테스트 중 실제 이슈 발생 (2026-06-04).
- **추후 수정 방향**:
  - **검증 추가** (sc3 또는 sc4): "참조된 원본보호 정책 삭제 차단" 케이스를 npouch_policy 디렉토리에 새 시나리오로 추가.
  - **cleanup 순서 보정**: page 실행 순서를 `npouch_policy → origin_protect` 로 강제하거나,
    origin_protect sc1 cleanup 전에 npouch_policy AUTO/AUTO_KEEP 항목 먼저 삭제 (참조 해제) 후 진행.
  - 또는 origin_protect cleanup 에서 삭제 실패 시 "부여 해제 → 재시도" fallback.
- **현 상태**: 미수정 — exe 배포 우선, 추후 별도 PDCA 진행.

---

## [RESOLVED] 페이지 검색 "[AUTO]" 가 [AUTO_KEEP]_* 못 잡음 — 2026-06-04

- **증상**: `search_item("[AUTO]")` 검색 결과에 `[AUTO_KEEP]_sc6_*` 항목 미포함 → cleanup 누락.
- **원인**: `[AUTO]` substring 매칭 시 `[AUTO_KEEP]` 의 6번째 글자 `_` vs `]` 다름 → 검색 결과 안 들어옴.
- **수정** (2026-06-04): `search_item("[AUTO]")` → `search_item("[AUTO")` (close bracket 제거).
  영향: `delete_all_auto_items`, `cleanup_with_keep` 양쪽 페이지.
- **사용자 발견**: 검색창에 `[auto` 입력 시 KEEP 도 매칭됨을 확인.

---

## [RESOLVED] 글자수 제한(overflow) 스캔 — 느린 서버 에러 놓침 → "제한 없음" 오판 — 2026-06-04

- **증상 (사용자 보고)**: 프로세스 이름에 긴 값 입력+저장 시 "서버에서 오류가 발생 하였습니다" 발생하는데,
  테스트는 "1001자까지 입력 가능 — 서버 측 글자수 제한 없음 (known issue)" 으로 오판.
- **증거 (로그)**: `[WARN] 프로세스 이름 — 글자수 제한 스캔: 1001자까지 입력 가능` +
  `[NET 5xx] POST 500 .../tag?tagName=[AUTO]_ov_XXX...` (실제 500 에러 발생).
- **원인**: overflow 스캔이 `try_submit()` 후 `wait_for_timeout(600)` + 즉시 `is_confirm_modal_visible()`(count() 무대기).
  긴 값(1001자)은 서버 처리가 600ms 보다 느려 그 시점에 에러 모달 미출현 → `else` 분기 → `_ov_any_saved=True` ('저장됨/제한없음' 오판).
- **수정** (2026-06-04, test_npouch.py + test_npouch_tag.py 동일):
  - `wait_for_timeout(600)` + 즉시검사 → `SEL_CONFIRM_MODAL.wait_for(state="attached", timeout=6000)` 로 변경.
    모달이 빨리 뜨면 즉시 반환(정상 케이스 영향 없음), 느린 에러도 6초까지 포착.
  - 모달 미출현 시 '저장됨' 가정 금지 → 재검색으로 실제 저장 여부 확인 (test_npouch.py).
- **사용자 지적 핵심**: maxlength 는 DOM 속성 체크(None→WARN)만이 아니라 실제 입력+저장+서버응답 검증 필요.
  overflow 스캔이 그 역할인데 버그로 무력화됐던 것.
- **2차 원인 (진짜 핵심, 2026-06-04)**: `_SAVE_SUCCESS_KEYWORDS` 에 `"하였습니다"` 포함 →
  에러 메시지 `"서버에서 오류가 발생 하였습니다"` 가 success 로 오분류 (any() True).
  타이밍 fix 후에도 여전히 "제한 없음" 오판한 진짜 이유.
  - **수정**: 에러 키워드(`오류`/`실패`/`에러`) 먼저 검사 → 있으면 무조건 에러 처리.
    `_ov_is_err = ("오류" in msg) or ...; if (not _ov_is_err) and success_kw: 저장 else: 에러`
  - test_npouch.py(overflow 스캔) + test_npouch_tag.py(설명 글자수) 양쪽 적용.
- **스크린샷 추가**: overflow 에러 모달 떠 있는 동안 `_ss()` 캡처 → 결과 extra["screenshot"] 첨부
  (이전엔 결과 보고 시점에 모달 이미 닫혀 캡처 무의미했음).
- **Chrome 직접 검증 (192.168.13.141)**: 프로세스 이름 1015자 → "서버에서 오류가 발생 하였습니다" 확인.
- **보고서 캡처 미표시 원인 (2026-06-04)**: overflow 결과가 "pass" 였는데 html_reporter.py:526
  `bug_items = status in (fail/warn/known_bug/error)` — pass 는 defect 카드 없음 → 스크린샷 첨부해도 미표시.
  - **수정**: generic 500 응답은 결함(graceful 검증 메시지 부재)이므로 `pass` → `warn` + `🔴 (known_bug)` 로 변경
    (디렉토리 패턴 origin_protect sc3n 와 일관). 이제 defect 카드 + 캡처 렌더링.
- **빨간 하이라이트 (사용자 요청 2026-06-04)**: 코드 전체에 element 빨간 표시 기능 없었음 (캡처는 viewport 만).
  scan_context 주석: element 캡처는 Playwright actionability 대기로 30초 hang → viewport 만 사용.
  - **신규 추가**: overflow 에러 시 문제 input 에 `el.style.outline='3px solid red'` + boxShadow 입힌 후
    viewport 캡처 (스타일링은 hang 없음). 문제 필드가 빨갛게 표시된 화면 캡처.

---

## [RESOLVED] 운용 프로세스 — maxlength 검증 과거 잔재 + overflow 필드 누락 — 2026-06-04

- **사용자 지적**: DOM maxlength(None) × 5필드 WARN = 프로세스 이름 초과 이슈와 같은 것 (중복 노이즈).
  서명/SHA2/실행경로/설명에 긴 값 → 서버 오류 날 텐데 overflow 검증이 processName 만 있어 누락.
  → 캡처도 부실해지는 악순환. maxlength DOM 체크 자체가 우리 방향(실입력+저장+서버응답+캡처)과 안 맞는 과거 잔재.
- **수정** (2026-06-04):
  1. YAML: 서명/SHA2/실행경로/설명에 `overflow_scan: true` 추가 (processName 포함 5필드 전부 실제 긴값 검증).
  2. overflow 루프: 비-이름 필드는 유효 processName(`[AUTO]_ov_<id>`) 먼저 채운 후 대상 필드에 긴 값 입력
     (이름 빈값이면 "이름 입력" 에러가 먼저 떠 필드 길이검증 불가). 저장 시 검색용 짧은 이름이라 cleanup 도 prefix 로 처리.
  3. DOM maxlength 체크: `warn`(None) → `pass`(info) — 실제 검증은 overflow_scan 이 담당, 중복 WARN 제거.
- **효과**: 5필드 각각 "X자 이상 서버 오류 🔴 known_bug" + 빨간 하이라이트 캡처. maxlength 노이즈 5건 제거.

---

## [PENDING] 단일 파일 sc 의 fail/warn 자동 screenshot 누락 — 2026-06-04

- **현황**: `tests/test_npouch.py`, `tests/test_npouch_tag.py` 의 `_r(...)` 호출이 대부분 `page=` 인자 없이 호출 → fail/warn 결과에 screenshot 첨부 안 됨.
  ```python
  def _r(status, label, detail, sc=0, page=None):
      if page and status in ("fail", "warn"):
          ss_path = _ss(page, label)   # 인자 안 넘기면 skip
  ```
- **빨간색 highlight** 기능은 디렉토리 패턴 (UIScanner 기반) 만 사용. 단일 파일은 plain screenshot 만 가능.
- **추후 수정 방향**:
  - 작은: 핵심 fail 위치 (sc6 cross-page, modal 차단) 만 `page=` 추가
  - 큰: 단일 파일 → 디렉토리 패턴 업그레이드 (highlight + capture 표준 적용)
- **현 상태**: 미수정 — 단계적 적용 예정.

---

## [RESOLVED] select_process_by_name fallback — 매칭 실패 시 첫 행 무조건 선택 — 2026-06-04

- **증상**: 태그 sc6 에서 `[AUTO_KEEP]_sc6_np_proc_suite` 등록 의도였으나 무관한 `111bug_process.exe` 가 등록됨.
- **원인**: `pages/npouch_tag_page.py:355-398` 의 `select_process_by_name` 끝부분 fallback:
  ```python
  # fallback: 첫 번째 항목 선택  ← 잘못된 프로세스 선택!
  first_row = rows[0]
  cb.click()
  return proc_name
  ```
  추가로 검색 대기 `wait_for_timeout(400)` 가 AJAX 적용 시간보다 짧아 매칭 실패 빈번.
- **수정** (2026-06-04):
  1. 검색 후 대기를 `locator.filter(has_text=name).wait_for(state="visible", timeout=2000)` 로 변경 (적용 확인까지 대기).
  2. fallback 제거 — 매칭 실패 시 `raise Exception(...)` + 상위 5건 진단 정보 포함.

---

## [PENDING] 태그 sc2 — 설명 긴 값 입력 시 이슈 확인 타임아웃 대기 — 2026-06-04

- **현상**: 태그 페이지 sc2 (`tests/test_npouch_tag.py`) 에서 설명 필드에 긴 값 입력 후
  이슈 확인 단계에서 타임아웃 (긴 wait) 발생. 옛 로직 잔존.
- **영향**: 태그 페이지 전체 실행 시간 증가.
- **추후 수정 방향**: 태그 페이지를 디렉토리 패턴 (`tests/npouch_tag/`) 으로 업그레이드.
  긴 값 입력 후 검증은 단축 timeout 패턴 적용 (origin_protect / npouch_policy 패턴 참조).
- **현 상태**: 미수정 — exe 배포 우선, 이후 별도 PDCA 진행.

---

## [PENDING] 태그 sc6 — AUTO_KEEP 항목 미잔존 — 2026-06-04

- **현상**: 태그 페이지 sc6 lifecycle 종료 시 `[AUTO_KEEP]_sc5_*` 항목이 남지 않아
  후속 테스트에서 활용 불가.
- **영향**: lifecycle 연계 데이터 부재.
- **추후 수정 방향**: 디렉토리 패턴 업그레이드 시 sc5c (npouch_policy 패턴) AUTO-only cleanup 적용,
  `cleanup_all_auto_keep` 제외 로직 추가.
- **현 상태**: 미수정 — exe 배포 우선, 이후 별도 PDCA 진행.

---

## [RESOLVED] qatool 시나리오 0 표시 위치 — append 로 뒤에 표시됨 — 2026-06-04

- **증상**: 시나리오 0 (UIScanner) 가 sc1~5(6) 뒤에 표시됨.
- **원인**: `app.py:538` 동적 sc 항목 추가가 `append` — `_LIST_SCENARIOS` 에 sc1~5(6) 만 hardcoded 라
  sc0 는 헤더 print 시 끝에 추가됨.
- **수정** (2026-06-04): `append` → `sc_num` 오름차순 정렬 insert.
  ```python
  insert_at = next((i for i, s in enumerate(sc_list) if s["num"] > sc_num), len(sc_list))
  sc_list.insert(insert_at, new_sc)
  ```
- **효과**: sc0 → sc1 → sc2 → ... 순으로 표시. 다른 동적 sc 항목도 자동 정렬.

---

## [RESOLVED] qatool 시나리오 진행 표시 — sub-num (a/b/c) 정규식 미매칭 — 2026-06-04

- **증상**: control_suite/origin_protect/npouch_policy 실행 중 시나리오 헤더 "시나리오 2c:", "시나리오 4w:" 등이
  UI 에 "예정"으로만 표시. 디렉토리 패턴 페이지의 모든 sub-num 시나리오 해당.
- **원인**: `app.py:437` 정규식 `r'시나리오\s+(\d+)\s*[:：]\s*(.+)'` 가
  "시나리오 2c:" 의 sub-num `c` 를 허용 안 함 → 매칭 fail → sc_status 갱신 안 됨.
- **수정** (2026-06-04): `(\d+)` 뒤에 `[a-z]?` optional 추가.
  ```python
  _SC_RE = _re.compile(r'시나리오\s+(\d+)[a-z]?\s*[:：]\s*(.+)')
  ```
- **효과**: sub-num 무시하고 sc_num 정수만 추출 → 같은 sc_num 의 모든 sub 가 동일 항목으로 묶여 표시.

---

## [RESOLVED] qatool UI 진행 표시 — 디렉토리 패턴 페이지 실시간 추적 불가 — 2026-06-04

- **현상**: 5 페이지 선택 후 실행 시 `npouch_control_suite` / `npouch_origin_protect` / `npouch_policy`
  의 진행 상태가 "예정/대기중" 으로만 표시. 시나리오 헤더 실시간 갱신 안 됨.
- **원인**: `app.py:488-489` stdout 매칭이 단일 클래스명 매핑 (`_NPOUCH_PAGE_TO_CLASS`) 기반.
  디렉토리 패턴의 실제 클래스 prefix (`TestScenario*`, `TestOriginProtect*`, `TestNpouchPolicyScenario*`)
  와 매핑값 (`TestNpouchControlSuite` 등) 불일치 → `current_page` 갱신 실패 → 시나리오 헤더 미감지.
- **영향**: 보고서 결과는 정상 (테스트 자체는 실행됨) / 실시간 UI 만 정지.
- **추후 수정 방향**:
  - `_NPOUCH_PAGE_TO_CLASS` 를 prefix 또는 파일 경로 기반 dict 로 변경
    (e.g. `{"npouch_control_suite": ("control_suite/", "control_suite\\")}`).
  - pytest stdout 의 `tests/<dir>/` 또는 `::Prefix*::` 매칭 로직 추가.
- **수정** (2026-06-04):
  - `app.py:482-501` 페이지 감지를 `_NPOUCH_PAGE_TO_FILE` 기반 경로 매칭으로 변경.
    - 단일 파일: `f"{file}::" in line` / `f"{file} " in line`
    - 디렉토리: `f"/{dir}/" in line` / `f"\\{dir}\\" in line`
  - `app.py:550` `in_summary` 에 디렉토리 3개 경로 추가 (FAILED 감지용).
  - 클래스명 prefix 매칭 회피 — control_suite/ 의 `TestScenario*` 가 generic 이라 안전.

---

## [RESOLVED] [AUTO_KEEP] 정책 cleanup 실패 — check_policy_row 가드가 [AUTO] 만 허용
- **날짜**: 2026-06-01
- **증상**: sc1 의 session cleanup 호출 후에도 `[AUTO_KEEP]_sc5_origin_protect` 잔존 → 사용자가 수동 삭제
- **사용자 보고**: "아무리봐도 auto킵은 안지워, 지우는 로직이 없어"
- **원인**: `pages/npouch_origin_protect_policy_page.py:check_policy_row` 의 가드
  - 이전: `if not name.startswith("[AUTO]"): raise Exception(...)`
  - `[AUTO_KEEP]_X`.startswith(`[AUTO]`) = False (괄호 다음 `_` vs `]` 다름)
  - `delete_policy([AUTO_KEEP]_X)` → `check_policy_row` 가드에서 Exception
  - `delete_all_test_data` 의 `try/except` 가 silent 잡음 → [AUTO_KEEP] 잔존
- **수정**: `check_policy_row` 가드를 `[AUTO]` OR `[AUTO_KEEP]` 둘 다 허용
- **파일**: `pages/npouch_origin_protect_policy_page.py:172~`

---

## [RESOLVED] sc5b 다중 필드 EDIT 저장 fail — JS `el.click()` untrusted click 으로 AngularJS form ng-model 동기화 skip
- **날짜**: 2026-06-01
- **증상**:
  - sc5b lifecycle modify 저장 시 server msg='제어 스위트를 선택해 주세요.'
  - EDIT 진입 시 UI 의 CSU 표시는 '전사 시큐어존 테스트' 로 정상 load
  - 4 필드 (Label/Quota/Opacity/Degree) fill 후 즉시 _save_click → server reject
  - 사용자 의문 적중: "sc3/sc4 에서도 검증돼야 하는데 sc5 만 나오는 게 말이 안돼"
- **사용자 가설**: 자동화 코드 결함 가능성 → Chrome MCP 로 수동 vs 자동 비교 진행
- **Chrome MCP 검증 (2026-06-01, ss_0916/ss_10452/ss_33250/ss_6408)**:
  - 수동 (triple_click + keyboard type + 좌표 click) → "저장 하였습니다" ✓
  - 자동화 동등 (JS `el.value=v` + dispatch input + 좌표 trusted click) → "저장 하였습니다" ✓
  - 자동화 동등 (JS `el.value=v` + dispatch input + **JS `btn.click()`**) → "제어 스위트 선택" ✗
  - active element blur 강제 + JS click → 여전히 fail (blur 도 우회 못 함)
- **원인**:
  - `_save_click` 의 `el.click()` (untrusted JS click) 가 AngularJS form 의 ng-model 동기화 단계 skip
  - controlSuiteId 등 picker-bound ng-model 이 stale 빈값으로 form submit
  - trusted click (mouse down) 만이 active element blur + digest cycle 발화 → ng-model 동기화
  - **sc3/sc4 미노출 이유**:
    - ADD = picker 선택이 마지막 액션 → ng-model OK
    - sc4 EDIT = 1 필드만 변경 → 1 ng-model stale 가능하지만 다른 필드 EDIT load 값 그대로 → server 통과
    - **sc5b 만 4 필드 동시 변경 → controlSuiteId 포함 다수 ng-model stale 가능성 노출**
- **수정**:
  - `tests/origin_protect/test_scenario3_add.py:_save_click` → `Locator.click(force=True)` (trusted click)
  - `tests/origin_protect/test_scenario4_modify.py:_save_click` → `Locator.click(force=True)` (trusted click)
- **파일**: `tests/origin_protect/test_scenario3_add.py`, `tests/origin_protect/test_scenario4_modify.py`
- **후속 검토**: sc4 에 다중 필드 변경 EDIT 메서드 추가 — 단일 필드만 변경하는 한계로 결함 검출 못한 것을 보강.

---

## [RESOLVED] 원본보호 sc1c — 탭 native click 이 qa-block-overlay 에 intercept (2026-05-28)
- **날짜**: 2026-05-28
- **증상**: sc1c (비기본 탭 차단 메시지 검증) → `TimeoutError: Locator.click: Timeout 5000ms exceeded` + `<div id="qa-block-overlay"></div> intercepts pointer events`.
- **원인**: conftest 의 qa-block-overlay (인간 클릭 차단용, z-index 99998) 가 모달 안 `<a>` 탭의 native Playwright click 을 actionability check 단계에서 intercept. (`.fill()` 은 actionability 우회라 sc1d input 입력은 정상 — click 만 차단.)
- **수정**: `tabs.nth(idx).click()` → `tabs.nth(idx).evaluate("el => el.click()")` — control_suite 의 "버튼/모달 내부: JS 직접 호출" 패턴 적용 (CLAUDE.md memory).
- **파일**: `tests/origin_protect/test_scenario1_ui.py`
- **교훈**: 원본보호 후속 시나리오에서도 모달 안 버튼/탭 click 은 native click 대신 JS evaluate 사용해야 안전.

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

## [RESOLVED] B-1 시리즈 list_page 확장 — 신규 발견 시 휴리스틱 동작 + yaml stub 자동 (2026-05-29)
- **상황**: MEMORY.md "B-1 시리즈 자동 분류 — modal_form (ransom_detect_policy, rdp_policy) 완전 적용 / list_page (제어스위트, 원본보호) 별도 계획 (미적용)" 상태. 사용자 요청 "신규 발견된 요소도 동일 type 다른 요소와 똑같이 자동 검증 진행".
- **검토 과정**: 두 접근 비교 후 사용자 결정.
  - 옵션 A (testable_aspects 가이드): yaml 메타로 type 별 "이런 검증 가능합니다" 출력. 부작용 0 / 자동 결과 0.
  - 옵션 B (휴리스틱 자동 실행): type 별 안전 검증 실행 후 결과 카드 1줄. 즉시 회귀 신호.
  - 사용자 결정: **B (휴리스틱)** — 자동 회귀 신호 우선.
- **변경**: `core/ui_scanner.py` 의 `_scan_diff_yaml_dom` 신규 발견 카드에 두 가지 추가
  - **Step 1 — yaml stub 자동 제안** (`_build_yaml_stub`): 발견된 요소의 type/maxlength/has_toggle 등 DOM 속성 기반으로 yaml 한 줄 stub 자동 생성. 검수자 복붙 → 다음 run 부터 자동 검증 시작.
  - **Step 2 — type 별 안전 휴리스틱 동작 검증** (`_run_heuristic_test`):
    - text/textarea: maxlength=null 시 warn ("긴 입력 시 server generic error 위험" — sc3n 패턴과 동일 신호)
    - checkbox: click ON↔OFF 토글 가능 여부 검증 (원상복구 포함, 데이터 변경 X)
    - radio: name 그룹 옵션 수 검출 + yaml options[] 작성 권장
  - 결과는 신규 발견 카드 `detail` 안에 한 줄 합침 (별도 카드 안 만들어 보고서 시끄러움 방지)
- **안전 원칙**: 저장 시도 / 종속 자동 탐색 / DOM mutation 추적 등 부작용 위험 휴리스틱 제외. step 3+ 추후 사용자 결정.
- **파일**: `core/ui_scanner.py`

---

## [RESOLVED] control_suite.yaml — pre-existing 3건 YAML 구문 위반 (UIScanner 처음 load 로 노출)
- **날짜**: 2026-05-29
- **상황**: tests/control_suite/test_scenario0_scan.py 의 UIScanner.scan(page_id="control_suite") 호출이 control_suite.yaml 을 처음 parse 시도하면서 yaml.parser.ParserError 노출. 기존 sc1~sc6 시나리오 테스트는 yaml 을 안 읽었기 때문에 발견 안 됐던 잠재 결함.
- **원인 (3건 모두 동일 패턴 — flow-mixed-block 위반)**:
  1. line 1370 `processAuth` radio: flow-style `{...}` 안에 block-style `options:` 리스트 (line 1373-1375 들여쓰기)
  2. line 1378 `otherFolderAccessAuth`: 동일 패턴
  3. line 1387 `optionTextBtn` expand_button: flow mapping 안 value 뒤 콤마 누락
  4. line 1419 `isUrl` toggle_checkbox: flow `{...}` 안 block `verified:` 리스트
  5. line 1423 `isDataDecrypt` radio: 동일 + reaction block
  6. line 1548 `unified_selectors`: message_modal_dialogs sequence 안에 mapping key 혼입 (sequence + mapping mix)
- **수정**: 6 곳 모두 block style 로 변환. (1)~(5) 는 `{...}` flow mapping → indented mapping. (6) 은 top-level `message_modal_unified_selectors` 로 분리 (소비자 코드 없음 — 문서용 메타).
- **검증**: `python -c "import yaml; yaml.safe_load(open(...))"` 통과. 32 top-level keys 로드.
- **재발 방지**: 신규 yaml 추가 시 `python -c "import yaml; yaml.safe_load(open(F))"` 1회 통과 확인 권장. UIScanner 통합이 가장 빠른 syntax 검증 트리거.
- **파일**: `config/scan_hints/control_suite.yaml`

---

## [OPEN — 🔴 HIGH 사용자 재확정] 원본보호 EDIT — 이름 중복 검증 부재 (예상 동작 아님 / 같은 이름 저장됨)
- **사용자 판정 2026-05-29**: "중복 이름에 대해 차단 못 하고 있어. 버그 맞아 예상한 동작이 아니라 같은 이름으로 저장이 되니까."
- **이전 항목 (아래) 와 동일 결함** — 강조 표시.
- **날짜**: 2026-05-29 (sc4 MCP 검증 중 발견)
- **증상**: EDIT 모달에서 정책 이름을 기존 다른 정책 이름으로 변경 + 저장 → 차단 메시지 없이 "저장 하였습니다" 성공 → list 에 같은 이름 정책 2건 공존.
- **재현 (Chrome MCP 2026-05-29)**: `[AUTO]_sc3g_normal_save` EDIT → `[AUTO]_sc3b_dup` 으로 rename + 저장 → list 에 `[AUTO]_sc3b_dup` 2건 (등록일 11:48:48 / 11:48:06).
- **ADD 와 비교**: sc3b 가 ADD 시점 동일 이름 시도 → "정책 이름이 이미 등록되어 있습니다." 차단 확인됨. EDIT 에서만 차단 X.
- **권장 수정 (제품 측)**: EDIT 저장 시점에도 본인 row 제외 후 이름 중복 검증 — sc3b 메시지와 동일 차단.
- **테스트 측 대응**: yaml `known_bugs.edit_name_duplicate_not_blocked` 등록 ✓. sc4 메서드 작성 시 검증 항목 포함 예정.
- **파일**: `config/scan_hints/npouch_origin_protect_policy.yaml`

---

## [OPEN — 🟡 MEDIUM 사용자 재확정] 원본보호 EDIT — 거짓 성공 메시지 + silent revert (필수 입력 검증 부재)
- **사용자 판정 2026-05-29**: "이름 빈값 넣으면 오류를 출력하는 게 아니라 기존의 내용을 출력하는 것도 버그야."
- **날짜**: 2026-05-29
- **증상**: EDIT 에서 필수 필드 (정책 이름 / driveLetter / driveLabel) 빈값 + 저장 → "저장 하였습니다" 거짓 메시지 + 모달 자동 닫힘 → 재 진입 시 기존값 그대로 (실제 변경 안 됨, silent revert).
- **추가 사실 (2026-05-29)**: 정책 이름도 동일 패턴 — sc4b 검증으로 originProtectPolicyName 도 verified_fields 에 등록.
- **ADD 와 비교**: ADD sc3a 는 "드라이브 문자를 입력해 주세요." 명확 차단 메시지 + 모달 안 닫힘. EDIT 는 동작 불일치.
- **재현 (Chrome MCP 2026-05-29)**: `driveLetter=''` 저장 → list 행 클릭 → detail panel: `드라이브 문자: Y` / 다시 EDIT → `value='Y'`.
- **데이터 안전성**: 실제 빈값 저장 안 되므로 데이터 무결성 영향 없음. 단 사용자가 변경했다고 오인 가능 = UX 결함.
- **다른 필드 추정**: driveLabel / Quota / CSU 동일 패턴 가능성 — 별도 검증 필요.
- **테스트 측**: yaml `known_bugs.edit_required_validation_silent_skip_with_false_success` 등록 ✓

---

## [RESOLVED] Crash entry 가 잘못된 sc 그룹에 노출 (sc0 에 sc4 crash 9건 표시)
- **날짜**: 2026-05-29 (사용자 지적 — 보고서에 "시나리오 0" 그룹 하에 sc4 9 error 표시됨)
- **증상**: conftest hook 의 crash ScanResult 가 `extra={"scenario": 0}` 고정 → 모든 crash entry 가 보고서의 "시나리오 0: UIScanner 자동 스캔" 그룹 헤더 하에 분류되어 노출. 실제로는 sc4a~sc4i 메서드의 crash 인데 sc4 그룹 안 보임.
- **원인**: `conftest.py:574` 의 crash ScanResult 생성 시 `extra={"scenario": 0, "crash": True}` 하드코딩. 메서드 이름에서 sc 번호 추출 안 함.
- **수정**: hook 안에서 `item.name` 의 `test_scenarioNX_...` 패턴 정규식 match → sn=0 이면 0 유지, 그 외는 `sn*100+sub` 로 scenario 동적 계산. 결과: sc4 crash → scenario=401~409 → "시나리오 4" 그룹 헤더 하에 정확 분류.
- **파일**: `conftest.py`

---

## [RESOLVED] sc3+sc4 통합 실행 시 sc4 9건 cascade fail — 검색 input 잔존 (sc3k → sc4)
- **날짜**: 2026-05-29 (사용자 보고 + log + Chrome MCP 직접 확인)
- **증상**: sc3 단독 실행 OK / sc3+sc4 통합 실행 시 sc4 9건 다 `RuntimeError: row '[AUTO]_sc3g_normal_save' list 에 미발견`. sc3g 가 정책 정상 저장한 후에도 sc4 가 list 에서 못 찾음.
- **원인 (Chrome MCP 직접 확인)**: 
  - URL: `?pageNo=1&pageSize=20&searchText=auto`
  - search_input: `"auto"` (소문자 잔존)
  - sc3k 가 line 720 에서 `search.fill(NAME)` 으로 EDIT 재진입 검색 사용 후 비우지 않음 → sc3l/sc4 cascade 영향
  - AngularJS 검색이 case-sensitive 또는 partial match 안 함 → "auto" 입력으로 "[AUTO]" 매칭 0 → list 필터링됨
  - sc4 의 `_enter_edit_modal` 의 `SEL_TABLE_ROW.filter(has_text=name)` 가 필터링된 list 에서 못 찾음 → row not found
  - `_ensure_sc3g_policy` 의 `is_policy_exists` 는 다른 경로로 정책 존재 확인 → fallback skip
  - `page.navigate_to()` 의 early return 케이스에서 검색 input reset 안 됨
- **수정 2건**:
  1. `_enter_edit_modal` 진입 시 search input 명시 reset (navigate_to early return 안전망)
  2. `sc3k` 끝 (page.close_modal 후) 검색 input 비우기 (책임 분리)
- **파일**: `tests/origin_protect/test_scenario3_add.py`, `tests/origin_protect/test_scenario4_modify.py`

---

## [RESOLVED] sc4b — 이름 빈값 차단 기대 → 실제 silent revert + 거짓 성공 (sc4d 와 같은 패턴)
- **날짜**: 2026-05-29
- **증상**: sc4b 가 `'정책 이름을 입력해 주세요.'` 차단 메시지 기대했는데 EDIT 에서 `'저장 하였습니다'` + PUT 200 + 모달 자동 닫힘 → fail. 후속 `page.close_modal()` 30초 timeout (모달 이미 닫힘).
- **사실**: EDIT 에서 이름 빈값도 sc4d (driveLetter/driveLabel) 와 같은 **silent revert** 결함. ADD sc3a 차단 vs EDIT 거짓 성공. data 안전 (실제 변경 안 됨) / UX 결함.
- **수정**: sc4b 로직을 silent revert 검증 패턴으로 변경 — `'저장 하였습니다'` 떴으면 다시 진입해서 이름 보존 확인 → reverted=True 면 warn (known_bug:edit_required_validation_silent_skip_with_false_success). 모달 닫혀있을 가능성 cover (close_modal try/except).
- **파일**: `tests/origin_protect/test_scenario4_modify.py`

---

## [RESOLVED] sc4c — 결함 재현 성공 / 원상복구 fail (rename row 식별 결함)
- **날짜**: 2026-05-29
- **증상**: sc4c 의 `[WARN] 결함 재현 (success 메시지): True` 정상 등록. 그러나 pytest FAILED — 원상복구 단계에서 `_enter_edit_modal(page, other_name)` 가 `filter(has_text=other_name).first` 사용 → other_name 정책 2건 (rename 된 sc3g + 기존) 중 어느 게 rename 된 건지 식별 못 함 → 잘못된 row click 또는 RuntimeError.
- **수정**: 원상복구 로직을 JS 로 직접 처리 — `td 컬럼 텍스트 정확 매칭` + `latest mtime row 식별` + tActive 시퀀스 직접 dispatch → modifyItemBtn click → 이름 복구. `defect_reproduced=False` 이면 rename 안 일어남 → 원상복구 skip. exception 발생해도 sc4c 검증 자체는 영향 없음 (print 만).
- **파일**: `tests/origin_protect/test_scenario4_modify.py`

---

## [RESOLVED] sc3k FAIL — backdrop=2 잔존 (sc3j 끝 + reload 후에도 잔존 → sc3l/m/n/o cascade)
- **날짜**: 2026-05-29
- **증상**: sc3k 진단 DUMP — `backdrops=2 body_style='padding-right: 10px;'` + `angular not loaded`. sc3l 시작 시 `click:button#addItemBtn` 가 `selectCommonPolicyItemModal` subtree intercept pointer events → 5초 timeout. sc3l/m/n cascade fail.
- **원인**: sc3j 끝의 `page.close_modal()` 가 Bootstrap modal cancel 만 했고 `.modal-backdrop` element + `body.modal-open` class + body inline `padding-right` 잔존. `_setup` fixture 의 `page.reload()` 가 AngularJS SPA 에서 backdrop cleanup 못 함 (또는 reload 자체 fail + except swallowed).
- **수정**: `_base.py:_setup` yield 후 reload 다음에 **backdrop 강제 JS cleanup** 추가:
  ```python
  p.evaluate("""() => {
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
      document.body.classList.remove('modal-open');
      document.body.style.removeProperty('padding-right');
  }""")
  ```
- **파일**: `tests/origin_protect/_base.py`

---

## [RESOLVED] sc4a csu 기대값 결함 — 환경 의존 ([AUTO_KEEP] 부재 시 첫 행 사용)
- **날짜**: 2026-05-29
- **증상**: sc4a 의 csu 검증 `기대: '[AUTO_KEEP]_sc5_step1' / 실제: '전사 시큐어존 테스트'` fail. 그러나 sc3g 가 picker 첫 행 선택했으므로 실제 저장값 = 환경 의존 (cleanup 후 첫 행).
- **수정**: csu 기대값 제거 + 별도 검증 — 빈값 아니고 "없음" 아니면 pass (정책 이름 무관).
- **파일**: `tests/origin_protect/test_scenario4_modify.py`

---

## [RESOLVED 2차] CSU picker `_csu_select_first` — JS evaluate click → trusted click 최종 확정
- **날짜**: 2026-05-29
- **진단 (log 기반)**: sc3+sc4 통합 실행 후 보고서 분석:
  - `[OK] sc3g — CSU picker 선택 → controlSuiteId span 바인딩: csuId len=2`
  - `[FAIL] sc3g — 정상 저장 메시지: msg='제어 스위트를 선택해 주세요.'`
  - `[FAIL] sc3g — 새 정책 list 등록 확인: exists=False`
- **확정 원인**: JS `evaluate("el => el.click()")` 가 AngularJS ng-change watch 미발화 → ng-model `controlSuiteId` 빈값 유지 → 저장 시 빈 CSU 전송 → server "제어 스위트를 선택해 주세요." 차단. `csuId len=2` = "없음" textContent 길이 (선택 안 된 상태).
- **이전 rollback 오해**: 사용자가 "원래 없었는데" 라고 한 list 의 [AUTO]_sc3* 5건 = 이전 trusted click fix 적용 시 만들어진 잔존 정책. JS evaluate click 자체는 항상 fail 이었음 (sc3g pytest 는 pass 지만 내부 _add 결과는 fail).
- **최종 수정**: `_csu_select_first` 다시 Playwright trusted click 으로 복구 (multi-fallback 없는 단순 버전)
  - picker open → `.in` attached wait (5초)
  - row Playwright `click(force=True, timeout=5초)` → ng-click 핸들러 발화 → radio + ng-model 동기화
  - 확인 버튼 Playwright trusted click
- **파일**: `tests/origin_protect/test_scenario3_add.py`

---

## [ROLLBACK] CSU picker fix 누적 — 사용자 "원래 없었는데" 회귀 결함 의심 (1차 시도)
- **날짜**: 2026-05-29
- **상황**: 누적된 fix (`_csu_select_first` multi-fallback / `_csu_search_and_select` Enter press + 0건 fallback) 가 원래 작동하던 sc3 흐름을 깼을 가능성. 사용자 직접 알림 "원래 없었는데".
- **사실 (Chrome MCP)**: 원본보호 list 에 [AUTO]_sc3* 5건 존재 → **원래 단순 evaluate JS 패턴이 정상 작동했음** 확정.
- **수정**: 두 함수 원래 코드로 rollback (단순 evaluate JS click)
  - `_csu_select_first`: picker open → radio click → confirm click (각 evaluate JS, wait 사이)
  - `_csu_search_and_select`: picker open → search fill → search btn click → radios.count()>0 면 first click → confirm click
- **유지 fix**:
  - `_enter_edit_modal` list 렌더 wait 강화 (SEL_TABLE_ROW first attached 10초 + 정책 row 5초)
  - `_ensure_sc3g_policy` list 등록 확인 + RuntimeError (silent fail 차단)
  - `conftest.py` crash 분류 (메서드 이름 기반 sc 번호 추출)
  - `_base.py:_setup` PAGE_ID 미리 attach
- **파일**: `tests/origin_protect/test_scenario3_add.py`

---

## [RESOLVED] CSU picker `_csu_select_first` — radio.click(force=True) 만으로 stuck (Bootstrap radio + AngularJS)
- **날짜**: 2026-05-29 (사용자 캡처 — picker 열린 상태에서 radio click 안 됨, 모든 라디오 unchecked)
- **증상**: `_csu_select_first` 호출 → picker 열림 (74건 라디오 표시) → 첫 radio 의 `click(force=True, timeout=3000)` 가 3000ms timeout → except 의 JS fallback 도 ng-model 동기화 못 함 → picker stuck → test hang.
- **원인**: AngularJS picker 의 Bootstrap radio 는 input 자체가 `display:none` 가능성 — force click 도 actionable check 부분 통과 못 함. 또한 radio click 보다 row (tr) click 이 AngularJS ng-click 핸들러 활용 가능.
- **수정**: `_csu_select_first` 다중 fallback 으로 재작성
  1. picker 모달 `.in` 클래스 명시 wait (5초 timeout)
  2. **첫 행 `tr` Playwright trusted click** (force=True) — 행 자체가 ng-click 핸들러 보유
  3. row click 실패 → radio.click(force=True) fallback
  4. radio click 실패 → JS dispatch (`checked=true` + click/input/change 3 event) 최종 fallback
  5. 확인 버튼도 trusted click + JS fallback
- **파일**: `tests/origin_protect/test_scenario3_add.py:_csu_select_first`

---

## [RESOLVED] CSU picker — JS click 만으로 ng-change 미발화 → POST 422
- **날짜**: 2026-05-29 (sc4 재실행 보고서 + log 분석)
- **증상**: `_ensure_sc3g_policy` 호출 → CSU picker 첫 행 JS click + 확인 → 저장 시도 → **`POST 422` server reject** → sc3g 정책 list 등록 실패 → sc4 9 메서드 다 timeout (row not found).
- **원인**: `_csu_select_first` 의 radio click 이 `.evaluate("el => el.click()")` JS-only → AngularJS ng-change watch 미발화 → controlSuiteId ng-model 빈값 유지 → 저장 시 빈 CSU id 전송 → server 422 거부.
- **수정**:
  1. `_csu_select_first` 의 radio click 을 **Playwright `radio.click(force=True)` trusted event** 로 교체 (JS fallback 보강)
  2. `_ensure_sc3g_policy` 에 저장 후 list 확인 + 실패 시 명시 예외 (silent skip 방지)
- **파일**: `tests/origin_protect/test_scenario3_add.py`, `tests/origin_protect/test_scenario4_modify.py`
- **참고**: `control_suite.yaml` line 1395 "JS .click() 으로 ng-change watch 미동작 → trusted event 만 sync 발화" 메모와 동일 패턴.

---

## [OPEN] CSU picker 검색 — 정확한 keyword 입력해도 결과 0건 (ng-change 미발화 또는 특수문자 escape 결함)
- **날짜**: 2026-05-29 (사용자 보고서 캡처)
- **증상**: sc3g 의 CSU picker 검색 input 에 '[AUTO_KEEP]_sc5_step1' 정확히 입력 → 검색결과 0 → "선택된 항목 없습니다" 알림 → 정책 저장 실패. 실제 정책은 존재 ("적용중 제어 스위트" 텍스트로 노출됨).
- **원인 후보**: (1) AngularJS ng-change watch 가 JS dispatch event 만으로 미발화 — control_suite.yaml line 1395 'trusted event 만 sync 발화' 메모와 동일 패턴. (2) 검색 keyword 의 `[` `]` 특수문자 escape 결함.
- **테스트 측 workaround** (sc3g 수정 2026-05-29): `_csu_search_and_select` 가 검색 0건 시 input 비우고 전체 list 에서 첫 행 fallback. `si.press("Enter")` 보강으로 trusted event 시도.
- **권장 수정 (제품 측)**: 검색 input 의 ng-change 즉시 발화 + partial match 검색 결과 반환.
- **테스트 측**: yaml `known_bugs.csu_picker_search_returns_zero_with_exact_keyword` 등록 ✓

---

## [RESOLVED] 테스트 crash 가 보고서 error 카운트에 안 잡힘 — _add 호출 전 abort 시 누락
- **날짜**: 2026-05-29 (사용자 지적 — sc4 9 메서드 FAILED 인데 보고서 error=0)
- **증상**: pytest 가 FAILED 9건 처리했는데 보고서 상단 stats 의 "실행 오류(error)" 카운트 0. sc4 메서드들이 _add() 호출 전 (fallback / EDIT 진입 단계) crash → ScanResult 0건 → conftest hook 의 crash ScanResult 등록 분기에서 `_npouch_page_id` attribute 미설정으로 page_id 추출 실패 → 등록 skip.
- **원인**: `tests/{origin_protect,control_suite}/_base.py:_setup` 가 PAGE_ID 를 `_attach` 호출 시점에만 set (= 첫 _add 호출 후). 그 전에 crash 나면 node 에 `_npouch_page_id` 없음 → hook 의 `_page_id = getattr(item, "_npouch_page_id", None)` = None → ScanResult 등록 elif 분기 진입 실패.
- **수정**: 두 `_base.py` 의 `_setup` fixture 시작 시 `request.node._npouch_page_id = self.PAGE_ID` 미리 attach. 어떤 시점 crash 라도 hook 이 page_id 추출 가능 → status="error" ScanResult 정상 등록 → 보고서 stats 에 error 카운트 노출.
- **파일**: `tests/origin_protect/_base.py`, `tests/control_suite/_base.py`, `conftest.py` (변경 없음 — hook 자체는 정상)
- **날짜**: 2026-05-29 (sc4 MCP 검증 추가 사이클)
- **증상**: EDIT 에서 Quota (originProtectDriveQuota) 빈값 + 저장 → "저장 하였습니다" 거짓 메시지 + 모달 닫힘 + 재 진입 시 **Quota='0' 실 저장 확인**. ADD sc3a 의 "원본보호 드라이브 용량을 입력해 주세요." 차단 메시지 부재.
- **재현 (Chrome MCP 2026-05-29)**: `Quota='200'` (sc3g 저장값) → EDIT 빈값 저장 → 재 진입 `value='0'` 확인. 사용자 의도 없이 200 → 0 으로 변경.
- **다른 필드와 비교**:
  - driveLetter / driveLabel 빈값: silent revert (기존값 유지, **data 안전**)
  - Quota 빈값: silent zero 변환 (실제 저장됨, **data 변경**)
  - 필드별 일관성도 결함.
- **권장 수정**: ADD sc3a 와 동일 차단 메시지 + 모달 안 닫힘. 또는 적어도 silent revert 로 통일 (data 안전).
- **테스트 측**: yaml `known_bugs.edit_quota_empty_silent_zero_conversion` 등록 ✓

---

## [OPEN — 🟡 MEDIUM] 원본보호 EDIT — 4-3 위반 패턴 부재 (검증 실패 시 모달 자동 닫힘)
- **날짜**: 2026-05-29
- **증상**: ADD sc3a 는 검증 실패 시 모달 안 닫힘 (사용자 수정 기회). EDIT 는 거짓 성공 메시지 후 모달 자동 닫힘 — 사용자가 수정 못 함.
- **테스트 측**: yaml `known_bugs.edit_4_3_pattern_missing` 등록 ✓

---

## [OPEN] 원본보호 EDIT — CSU picker 진입 시 radio 전부 unchecked
- **날짜**: 2026-05-29
- **증상**: EDIT 모달 → CSU '설정' click → picker 진입 시 상단 텍스트 "적용중인 제어 스위트 : [AUTO_KEEP]_sc5_step1" 정상 표시. 하지만 radio 20/20 모두 unchecked.
- **회색 영역**: '새로 선택할 항목' 만 radio 로 표시하는 도메인 의도일 가능성 — 사용자 결정 필요.
- **테스트 측**: yaml `known_bugs.edit_csu_picker_radio_unchecked_on_reopen` 등록 ✓

---

## [OPEN] 원본보호 EDIT — modal title="정책 추가" 그대로 (UX 결함)
- **날짜**: 2026-05-29
- **증상**: EDIT 모달 진입 시 modal title 이 'ADD' 와 동일 '정책 추가' 그대로. 하단 버튼 라벨은 '수정' 정상. modal 컨테이너 (#addItemModal) 가 ADD/EDIT 공통 재사용이라 title 만 dynamic 업데이트 누락.
- **권장 수정**: EDIT 진입 시 title '정책 수정' 으로 변경.
- **테스트 측**: yaml `known_bugs.edit_modal_title_not_updated` 등록 ✓.

---

## [OPEN] 원본보호 ADD/EDIT — 워터마크 투명도/각도 default 표시 불일치
- **날짜**: 2026-05-29
- **증상**: ADD 신규 모달 = '' (빈) / EDIT 진입 = '0'. 저장 시 ''→0 변환 후 load 시 '0' 표시.
- **권장 수정**: ADD/EDIT default 통일 (둘 다 '' 또는 '0').
- **테스트 측**: yaml `known_bugs.edit_watermark_numeric_default_inconsistent` 등록 ✓.

---

## [OPEN — 제품팀 수정 대기] 원본보호 — 파일 감시 토글 OFF 시 tag [X] 삭제 버튼은 여전히 클릭 가능 (종속 disabled 불완전)
- **날짜**: 2026-05-29 (사용자 스크린샷) → 2026-05-29 Chrome MCP 직접 재현 완료
- **증상**: 파일 감시기능 토글 (isWatchFileExtension) OFF 상태에서 input/추가 버튼/헤더 체크박스는 disabled 되지만, 등록된 확장자/예외폴더 tag 의 [X] 삭제 버튼은 클릭 가능 → tag 실제 삭제됨.
- **결함 카테고리**: 토글 OFF 의도 = "변경 불가" 라면 삭제도 막아야 함. 입력/추가 차단 vs 삭제 허용 = 일관성 결함.
- **재현 사실** (Chrome MCP 2026-05-29):
  - selector: **`i.extentionDeleteBtn`** (두 list 공통 — 확장자/예외폴더)
  - 토글 OFF 후 dump: `disabled_attr=null`, `pointer-events='auto'`, parent button `disabled=false`
  - 실제 click: `tags_before=2 → tags_after=1` / **삭제됨 확정**
- **테스트 측 대응**:
  - yaml `known_bugs_origin_protect.toggle_off_tag_delete_still_clickable` 등록 (selector + 재현 사실) ✓
  - yaml `toggle_dependencies.isWatchFileExtension.deps_defect[]` 격상 (deps_todo → deps_defect, selector 포함) ✓
  - sc3o 검증 보강: tag 1건씩 등록 → 토글 OFF → click → 삭제 여부 확인 (warn 재현) ✓
- **권장 수정 (제품 측)**: `i.extentionDeleteBtn` parent button 또는 i 자체에 토글 OFF 시 disabled 속성 부여. 또는 click handler 에서 토글 OFF 시 early return.
- **파일**: `config/scan_hints/npouch_origin_protect_policy.yaml`, `tests/origin_protect/test_scenario3_add.py`, `docs/TROUBLESHOOTING.md`

---

## [PARTIAL] 원본보호 정책 ADD 영역 — 미커버 갭 inventory (2026-05-29)
- **상황**: 사용자 요청 "부족한 부분 뽑아봐". sc3 14건 (a~n) 으로 ADD 핵심 동작은 커버되었으나 4 카테고리 미커버 잔존.
- **A. 토글 종속 disabled (RESOLVED via sc3o)**: 5 토글 / 16 종속 — Chrome MCP 직접 검증 2026-05-29 후 yaml `toggle_dependencies` 명세화 + sc3o 메서드 신규 추가. 토글 OFF → 전부 disabled=true 정상 동작 확인.
- **B. 다른 3 탭 (모달 안) — 미커버**: "허용 프로세스 / 예외처리 프로세스 / 실행차단 프로세스" 탭 ADD 시점 진입 가능 여부 / 차단 메시지 — 검증 0건.
- **C. CSU picker 추가 동작 — 미커버**: 검색 / cancel / multi-page navigation / 다른 행 선택 / 미선택 후 확인 차단 — sc3g 가 '첫행 선택' 만 다룸.
- **D. 워터마크 토글 자체 ON↔OFF 시 값 보존/복구 — 미커버**: sc3o 가 OFF → disabled 만 검증. 재 ON 시 text/체크박스 값 복구 동작은 아직.
- **사용자 결정**: A 만 진행 (sc3o). B/C/D 는 sc3 마감 후 별도 결정.
- **파일**: `config/scan_hints/npouch_origin_protect_policy.yaml`, `tests/origin_protect/test_scenario3_add.py`, `docs/TROUBLESHOOTING.md`

---

## [RESOLVED] 시나리오 점진 추가 시 검증 중복 5건 누적 (메타 결함)
- **날짜**: 2026-05-29 (사용자 지적 — 보고서 + 로그 교차 점검 요청)
- **증상**: 원본보호 정책 sc3 시리즈에 같은 결함을 다른 시나리오/다른 시점에서 중복 검증한 줄이 5건 누적. 보고서가 같은 사실을 여러 번 표시 → 사용자 입장에서 "결함 N건" 처럼 보이지만 실제로는 결함 1건이 N번 노출된 것.
- **재현된 중복 항목**:
  1. sc3n Part 1 (maxlength=null 5건) ↔ sc3n Part 2 (3000자 save reject 5건) — 같은 결함을 attribute / functional 2회 검증
  2. sc3j '종료 알림 maxlength=null / 500자 OK' 2건 ↔ sc3n save reject — 같은 사실의 다른 표현
  3. sc3k '저장 전 PC+Time 체크 결과' ↔ sc3f case 3 — 화학적 동일 결과
  4. sc3k 'text 수동 비움 → 체크박스 ON 유지' ↔ sc3f state3 — 100% 동일 검증
  5. sc3f / sc3m 'state1 setup 결과' 각 1건 ↔ 각자 case 3 — yaml 명세 1:1 매핑 부작용
- **원인**:
  1. 시나리오 신규 추가 시 기존 검증 라벨 inventory 와 교차 점검 누락 (점진 누적의 함정)
  2. yaml 명세 항목 ≠ 검증 1건 원칙 미준수 (transitions state1/2/3 를 기계적으로 3건 검증 줄로 노출)
  3. "추정 금지" + "결함 다 잡아야" 강박 충돌 → attribute / functional 양쪽 박는 과잉 검증
- **수정**:
  1. sc3n Part 1 제거 / sc3j maxlength 2줄 제거 / sc3k 의 중복 2줄 setup precondition assert 로 변환 / sc3f / sc3m state1 검증 줄 제거
  2. yaml `resolved_2026_05_28` 에 중복 제거 결정 기록 → 다음 시나리오 추가 시 reference
- **예방 규칙** (CLAUDE.md 차원 권장):
  - 시나리오 신규 추가 전 `grep "scN.* —" test_scenarioN*.py` 로 기존 라벨 inventory 훑기
  - "결함 1건 = 검증 1건" 원칙 — attribute / functional 두 각도로 잡고 싶으면 yaml inventory + functional 1건으로 분담
  - 매 시나리오 추가 후 `last_report.json` 라벨 `uniq -c | sort -rn` 교차 점검
- **파일**: `tests/origin_protect/test_scenario3_add.py`, `config/scan_hints/npouch_origin_protect_policy.yaml`

---

## [OPEN] 원본보호 정책 — 텍스트 길이 클라 가드 부재 + 서버 generic error (5 필드 + 전수 점검)
- **날짜**: 2026-05-29 (사용자 지적 '이름에도 검증해야' 반영하여 확장)
- **증상**: 모달 안 13개 text/textarea 입력 **전부** `maxlength=null` + `ng-maxlength=null` + `ng-pattern=null` (Chrome MCP 전수 dump). 무제한 입력 허용 → 저장 시 "서버에서 오류가 발생 하였습니다." generic 에러. 사용자가 실패 사유 알 길 없음.
- **재현 확정 (3 필드, Chrome MCP 2026-05-29)**: `allowProcessShutdownText` / `screenWaterMarkText` / `printWaterMarkText` 각 3000자 + 저장 → 동일 server error 메시지.
- **가드 부재만 확정, save reject 미검증 (2 필드)**: `originProtectPolicyName` / `driveLabel` — sc3n 추가 테스트가 검증.
- **원인**: 프론트엔드 입력 검증 부재 전수. 서버 에러 메시지도 사유 미명시 (generic).
- **권장 수정 (제품 측)**: (1) 5 필드 모두 클라 maxlength 부여, 또는 (2) 서버 응답에 한계값 명시 ("정책 이름은 최대 N자입니다").
- **테스트 측 대응**: yaml `known_bugs_origin_protect.text_length_no_client_guard_generic_server_error` 에 full_inventory 13건 + verified/unverified 분리. sc3n 메서드 5 필드 maxlength 부재 + 3000자 저장 reject warn 재현.
- **파일**: `config/scan_hints/npouch_origin_protect_policy.yaml`, `tests/origin_protect/test_scenario3_add.py`

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

---

## [2026-06-10] secure_zone 테스트 5분 → teardown full reload 제거

- **증상**: `tests/secure_zone/` 39 tests 실행 344s(5:44). 평균 8.8s/test.
- **원인**: `tests/secure_zone/_base.py` `_setup` 픽스처(autouse, function scope) teardown 이
  매 테스트마다 `p.set_default_timeout(30000)` + `p.reload(wait_until="domcontentloaded", timeout=15000)` 실행.
  이중 비용: ① SPA full reload 39회 ② reload 후 URL hash 소실 → 다음 `navigate_to()` early-return 가드
  (`SecureZoneAccessControlPolicy` + `pageSize=100` in url) 무효화 → App Setting→SecureZone 아코디언 풀 네비게이션 매번 재실행.
- **수정**: teardown 의 `set_default_timeout(30000)` + `reload` + `wait_for_timeout(200)` 제거.
  모달/백드롭 청소 JS(`.modal-backdrop` 제거 + `modal-open` 클래스/`padding-right` 제거)만 유지.
  열린 모달은 다음 `navigate_to()` 의 `_close_modal_if_open()` 가 닫으므로 격리 유지.
  `_SC_DEFAULT_TIMEOUT = 5000`(5초)은 변경 없음.
- **파일**: `tests/secure_zone/_base.py`
- **검증**: collect 39 tests 정상. 실측 단축폭은 사용자 pytest 재실행으로 확인 예정.

상태: [RESOLVED]

---

## [2026-06-11] 시큐어존 정책 sc3b — 템플릿 picker selector/wait 오류로 TimeoutError

- **증상**: sc3b normal_create 가 `select_template_top` 의 `picker.wait_for(state="visible")` 3초 TimeoutError.
- **원인 2가지**:
  1. **버튼 selector 오류**: `a.addTemplate` 는 템플릿설정 탭 '설정' 버튼 6개(hidden)만 매칭. 기본정책 탭 '템플릿 선택'은
     `button.addTemplate`(2개, [0]드라이브 [1]제어스위트) — 태그가 button. → nth(0/1) 이 엉뚱/hidden 요소 지정.
  2. **wait 상태 오류**: 템플릿 picker(`#selectCommonPolicyItemModal`)는 Bootstrap 모달이라 Playwright `state="visible"` 판정 실패
     (열려도 visible=false 취급). MEMORY.md "Bootstrap 모달 position offset → visible 체크 실패" 동일.
- **수정**: `pages/secure_zone_agent_policy_page.py`
  - `SEL_TEMPLATE_BTN`: `a.addTemplate` → `button.addTemplate`.
  - picker selector: 텍스트 필터 → 실측 id `div#selectCommonPolicyItemModal.in`.
  - `wait_for(state="visible")` → `state="attached"`.
- **검증**: Chrome MCP 로 생성(드라이브+제어스위트+이름+저장→"저장 하였습니다")+삭제 end-to-end 확인, [AUTO] 정리.
- **파일**: `pages/secure_zone_agent_policy_page.py`

상태: [RESOLVED]

---

## [2026-06-15] nPouch sc1c — navigate_to 'Angular not loaded' race 로 메뉴 클릭 30초 TimeoutError

- **증상**: 실제환경(192.168.13.141) 실행 중 sc1c_pdf_tab_access 만 ERROR (1 failed / 57 passed, 런은 계속).
  `[BasePage] 오류 — click:a[data-menuid='managerAppSetting'] | wait_for(visible) Timeout 30000ms`.
- **원인**: 필드/가드 문제 아님. sc1c `navigate_to()` 가 풀 리로드(main.html+bundle) 직후 **Angular 미부트스트랩**
  상태에서 App Setting 메뉴를 클릭 → 메뉴 아이콘 미렌더 → 30초 timeout.
  진단 DUMP: `open_modals=[] backdrops=0`(모달 무관) + `{'error':'angular not loaded'}` + NET 에 main.html/bundle 재로딩.
  실제환경 세션·500 일시 불안정과 겹친 flaky (innotium 58 passed 에선 미발생).
- **수정**: `pages/npouch_policy_page.py navigate_to` — 메뉴 상호작용 전 **메뉴 DOM 렌더 대기**
  (`wait_for_function(document.querySelector('[data-menuid]'), _TIMEOUT_TABLE)`). 렌더돼 있으면 즉시 통과.
- **⚠ 회귀 주의 (같은 날 발견·수정)**: 처음엔 `window.angular !== undefined` 조건을 넣었는데, 이 매니저 앱은
  **webpack 번들이라 angular 전역 미노출** → 조건 **항상 false** → 매 navigate_to 가 15초 hang → 테스트 전체 급격 저하.
  → `window.angular` 제거, `[data-menuid]` 렌더 여부만 확인. (진단의 'angular not loaded'도 window.angular 체크라 오해 유발)
- **검증**: 구문 OK. 정상 시 즉시 통과(no-op), 리로드 중일 때만 대기. innotium 영향 없음.
- **파일**: `pages/npouch_policy_page.py`

상태: [RESOLVED] (window.angular 회귀 수정 — [data-menuid] 렌더 대기로 변경)

---

## [2026-06-17] nPouch 운용/태그 — dev 서버(:88) 검색 컬럼 drift + cross-page backdrop + 헤더 라벨 빌드차

- **증상**: dev 서버(`http://192.168.13.141/` → :88)에서 운용/태그 **6 fail**(운용 sc1/3/4/5/6 + 태그 sc2).
  실서버(:40010)에선 1 fail(태그 sc6). 헤더 '프로세스 이름' 없음 / 저장 항목을 목록서 못 찾음(`filter(has_text=...)` timeout) / 태그 sc6 메뉴 클릭 30초.
- **원인 3가지** (Chrome 직접 확인 2026-06-17 — 로그인 세션 공유로 dev DOM 실측):
  1. **검색 컬럼 drift**: `search_item` 이 드롭다운 안 박고 URL 해시(`searchOption=processName`)에만 의존 →
     dev 빌드선 해시가 드롭다운에 미반영 → "설명"으로 남아 이름 검색 0건("검색된 내용이 없습니다", 단 목록엔 1,252건 존재).
     `search_item_with_option` 은 라벨 "프로세스 이름"으로 select → dev 라벨은 "프로세스명"이라 select 실패.
     (실측: 옵션 라벨 "프로세스명", **value=processName 은 빌드 무관 안정** — value: processName/sign/description)
  2. **cross-page backdrop**: 태그 sc6 → `operation_process.navigate_to` 가 url 이 이미 main.html 이라 리로드 skip →
     이전 태그 모달의 잔여 `modal-backdrop in` 이 좌측 메뉴(`managerGlobalCommonProcess`) 클릭을 30초 차단.
  3. **헤더 라벨 빌드차**: dev="프로세스명" vs 실서버="프로세스 이름".
- **수정**:
  - `pages/npouch_operation_process_page.py`:
    - `search_item` 이 `select#searchOption` 을 **value="processName" 로 명시 선택**(`_select_search_option`), 해시 의존 제거.
    - `search_item_with_option` 은 라벨 → value 매핑(`_SEARCH_OPTION_VALUE`).
    - `navigate_to` 진입 시 잔여 `.modal-backdrop` + `modal-open` 제거.
  - `tests/test_npouch.py`, `tests/test_npouch_tag.py`: 헤더 체크가 **"프로세스명"/"프로세스 이름" 둘 다 허용**.
- **검증**: dev 서버 재실행 **12/12 통과**(이전 6 fail), Chrome 으로 value 선택+`[AUTO` 검색 시 4건 조회 실증.
- **파일**: `pages/npouch_operation_process_page.py`, `tests/test_npouch.py`, `tests/test_npouch_tag.py`

상태: [RESOLVED]

---

## [2026-06-17] 공통 페이지 리포트 오판 + 생성 prefix 통일 (운용/태그/제어스위트)

- **배경**: 운용프로세스/태그/제어스위트는 nPouch·SecureZone 공용 페이지(menuid 동일). 시큐어존 런에 공통 태그가 끼면
  page_id `npouch_tag` 때문에 제품 판별이 **nPouch 로 오판**(시큐어존 런인데 `reports/nPouch/` 로 생성).
- **수정**:
  - `conftest.py` 제품 판별: 공통 3개(`npouch_operation_process`/`npouch_tag`/`npouch_control_suite`)를 **판별에서 제외** →
    같이 돈 제품에 귀속(시큐어존+공통 → SecureZone). 공통만 단독 실행 시 "Common".
  - 생성 데이터 prefix **`np` → `cm`(공통)** 통일: `[AUTO]_cm_process` 등, `[AUTO_KEEP]_sc6_cm_proc_suite`/`_tag_suite`.
    교차참조(운용 sc6 생성 → 태그 sc6 소비) 일치. 제어스위트는 이미 `[AUTO]_sc1_step1` 식이라 무관.
- **미적용(Phase 2 예정)**: 파일/클래스/page_id 의 `npouch_*` → `common_*` rename (app.py 6군데+ 강결합이라 별도 작업).
- **파일**: `conftest.py`, `tests/test_npouch.py`, `tests/test_npouch_tag.py`

상태: [RESOLVED] (리포트 귀속·prefix 통일 / 파일명 중립화는 Phase 2)
