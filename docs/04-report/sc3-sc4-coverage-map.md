# sc3(생성/ADD) ↔ sc4(수정/EDIT) 검증 커버리지 매핑

> 목적: 같은 검증이 생성(sc3)·수정(sc4) 양쪽에 대칭으로 존재하는지 점검.
> 원칙: 테스트 통과가 목적이 아니라 **모든 이슈를 찾는 것**이 포인트.
> ADD 에서 발견되는 결함은 EDIT 에서도 동일하게 재현되어야 회귀가 완성된다.
> 상태: ✅ 양쪽 존재 / ❌ 누락 / ➖ 한쪽만 의미있음(대칭 불필요)

작성: 2026-05-27 (코드 인용 기반)

---

## 영역 1 — 메인 스위트 모달

| # | 검증 유형 | sc3 (ADD) | sc4 (EDIT) | 상태 |
|---|----------|-----------|------------|------|
| 1 | minimal 저장/수정 | 3b | 4b | ✅ |
| 2 | 메인 필드 CRUD | 3c | 4c | ✅ |
| 3 | csuName maxlength=50 | 3e A | 4g A | ✅ |
| 4 | csuName 빈값 차단 | 3e B | 4g B | ✅ |
| 5 | csuName 중복 차단 | 3e E | 4g E | ✅ |
| 6 | ADD vs EDIT 빈값 메시지 차이 | — | 4g B-extra | ➖ (EDIT 전용 회귀) |
| 7 | 미선택 상태 "수정" 버튼 | 3e C | ➖ | EDIT 은 행 선택 후 진입이라 무의미 |
| 8 | 미체크 "삭제" 버튼 | 3e D | ➖ | delete 시나리오 (별도) |
| 9 | 변경 없이 "수정" → "수정된 항목 없음" | ➖ | 4g F / 4i A | ADD 무의미 (저장이 첫 생성) |
| 10 | 메인 확장자 중복 | 3c (확장자 중복) | 4k A | ✅ |
| 10b | 메인 확장자 형식(특수문자) 거부 | 3 형식거부 | 4k A2 | ✅ (2026-05-28 추가) |
| 11 | 전자서명 예외 중복 | 3f Case6 | 4k B | ✅ |
| 12 | csuName 길이 100/300/500 | 3h A | 4g A(100만) | 🟡 EDIT 300/500 미검증 |
| 13 | customOption 길이 100/300/500 | 3h B | 4p B | ✅ |
| 14 | clipboardAllowUrl 길이 500/1000 | 3h C | 4p C | ✅ |

---

## 영역 2 — 프로세스별 제어 (개별 프로세스)

| # | 검증 유형 | sc3 (ADD) | sc4 (EDIT) | 상태 |
|---|----------|-----------|------------|------|
| 15 | 프로세스 전체 필드 등록/수정 | 3c | 4d | ✅ |
| 16 | 프로세스 미선택 + 확인 차단 | 3f Case0 / 3g E | ➖ | EDIT 은 기존 행 진입 (미선택 무의미) |
| 17 | IP+Port 중복 차단 | 3f Case2 | 4m A | ✅ |
| 18 | 프로세스 확장자 중복 차단 | 3f Case4 | 4m B | ✅ |
| 18b | 프로세스 확장자 형식(특수문자) 거부 | 3 형식거부 | 4m B2 | ✅ (2026-05-28 추가) |
| 19 | Port 비숫자 'abc' 차단 | 3g A | 4o A | ✅ |
| 20 | Port 최대값 초과 99999 차단 | 3g A2 | 4o A2 | ✅ |
| 21 | IP 범위 초과 256.256 차단 | 3g B1 | 4o B1 | ✅ |
| 22 | IP 형식 invalid 차단 | 3g B | 4o B | ✅ |
| 23 | process 설명 1000자 → 300 제한 | 3g C | 4o C | ✅ |
| 24 | process picker 첫행 재선택 중복 | 3i A | 4n A | ✅ |
| 25 | cacheFolder reserved_word 중복 | 3i D | ❌ | **누락** (special_picker) |
| 26 | drive letter 50자 정상 저장 | 3j A | 4q A | ✅ |
| 27 | drive letter 100자 → 서버오류 | 3j B | 4j A | ✅ |
| 28 | Port=8080 정상 저장 | 3j D | 4q D | ✅ |
| 29 | Port=-1 → 서버오류 | 3j E | 4j B | ✅ |
| 30 | Port=0 정상 저장 | 3j F | 4q F | ✅ |
| 31 | Port=빈값 → 서버오류 | 3j G | 4j G | ✅ (2026-05-27 보완) |
| 32 | cacheFolderInput 500자 → 서버오류 | 3j K | 4j K | ✅ |

---

## 영역 3 — 프로세스별 제어 (태그)

| # | 검증 유형 | sc3 (ADD) | sc4 (EDIT) | 상태 |
|---|----------|-----------|------------|------|
| 33 | 태그 전체 필드 등록/수정 | 3c (태그) | 4e | ✅ |
| 34 | tag picker 동일 태그 중복 | 3i C | 4e (중복 거부) | ✅ |
| 35 | 태그 drive letter 100자 → 서버오류 | 3j L | 4j E | ✅ |
| 36 | 태그 Port=-1 → 서버오류 | 3j M | 4j M | ✅ (2026-05-27 보완) |
| 37 | 태그 cacheFolderInput 500자 → 서버오류 | 3j P | 4j P | ✅ |

---

## 영역 4 — 웹제한 기능

| # | 검증 유형 | sc3 (ADD) | sc4 (EDIT) | 상태 |
|---|----------|-----------|------------|------|
| 38 | 웹제한 전체 등록/수정 | 3d | 4f | ✅ |
| 39 | 웹제한 이름 빈값 차단 | 3f Case1 | 4l A | ✅ |
| 39b | 웹제한 이름 중복 차단 | 3f Case7 | 4l E | ✅ (2026-05-28 추가 — 2차 Chrome 확인 갭) |
| 39c | cross_instance 프로세스 중복 silent 거부 + 알림 (yaml :287) | 3f Case8 | 4l F | ✅ (2026-05-28 추가 — Chrome 직접 확정, yaml 명세 있던 갭) |
| 40 | URL 중복 차단 + 메시지 일관성 | 3f Case3 | 4l B | ✅ (일관성 분리검증 4l) |
| 41 | 웹 확장자 중복 차단 | 3f Case5 | 4l C | ✅ |
| 41b | 웹 확장자 형식(특수문자) 거부 | 3 형식거부 | 4l C2 | ✅ (2026-05-28 추가) |
| 42 | web_restrict picker 중복 (multi) | 3i B | 4n B | ✅ |
| 43 | web 설명 1000자 → 300 제한 | 3g D | 4o D | ✅ |
| 44 | basePath 400자 → 서버오류 | 3j C | 4j C | ✅ |
| 45 | basePath 300자 정상 저장 | 3j N | 4q N | ✅ |
| 46 | webRestrictName 500자 → 서버오류 | 3j H | 4j H | ✅ |
| 47 | webRestrictName 100자 정상 저장 | 3j O | 4q O | ✅ |
| 48 | attachAllowUrl 1000자 → 서버오류 | 3j I | 4j I | ✅ (2026-05-27 보완) |
| 49 | allowFileExtention 500자 → 서버오류 | 3j J | 4j J | ✅ (2026-05-27 보완) |
| 50 | 복호화 대상 → 업로드암호화 강제 (정방향) | 2e | ➖ | sc2 입력검증 (ADD 모달) |
| 51 | 업로드암호화 먼저 클릭 (역순) | 2e (2026-05-27 보완) | ❌ | **EDIT 웹제한 재진입 대응 누락** |

---

## 영역 5 — sub-modal 토글 OFF lifecycle (sc5 전용)

| # | 검증 유형 | sc3/sc4 | sc5 | 상태 |
|---|----------|---------|-----|------|
| 52 | 메인+sub-modal 토글 ON 생성 → 재오픈 ON | ➖ | 5a | sc5 lifecycle 전용 |
| 53 | 메인+sub-modal 토글 전부 OFF → 재오픈 OFF | ➖ | 5b | sc5 lifecycle 전용 |
| 54 | 모든 요소 제거 → 빈 정책(이름만) | ➖ | 5c | sc5 lifecycle 전용 |

---

## 누락 종합 (보완 대상)

| 우선 | 항목 | 위치 | 비고 |
|------|------|------|------|
| 🔴 | #25 cacheFolder reserved_word 중복 EDIT | sc4n 에 추가 | sc3i D 의 EDIT 버전, special_folder_picker 필요 |
| 🟡 | #51 업로드암호화 역순 EDIT | sc4f/4l 에 추가 | sc2e 역순의 EDIT(웹제한 재진입) 대응 |
| 🟡 | #12 csuName 300/500자 EDIT | 4g 또는 4p 에 추가 | 현재 4g 는 100자만 |

## 이미 보완 완료 (2026-05-27)

- #31 Port 빈값 EDIT (sc4j Case G)
- #36 태그 Port=-1 EDIT (sc4j Case M)
- #48 attachAllowUrl 1000자 EDIT (sc4j Case I)
- #49 allowFileExtention 500자 EDIT (sc4j Case J)
- #51 업로드암호화 역순 (sc2e) — EDIT 대응은 아직 누락

## 대칭성 결론

- **server-error 결함 (영역2/3/4)**: sc3 11개 = sc4 11개 → 대칭 (홀수 21 원인이던 sc4 4개 누락 보완 완료)
- **남은 비대칭**: #25 (cache reserved EDIT), #51 (암호화 역순 EDIT), #12 (csuName 300/500 EDIT)
