# 스크린샷 캡처 타이밍 — 케이스 정리

> **목적**: 결함 감지 시 사용자(검수자)가 카드 한 장에서 cause + effect를 모두 확인할 수 있는 스크린샷 보장.
> **원칙**: 1결함 = 1스크린샷. cause와 effect가 한 프레임에 담기는 시점에 캡처.
> **작성일**: 2026-04-30 (최근 보고서 RansomCruncher 2026-04-30, nPouch 2026-04-28 기반)
> **상태**: 분석 완료 — 수정 미착수

---

## 1. 현재 발생 케이스 (보고서 기반)

### RansomCruncher · 공통 프로세스 (2026-04-30 09:13)

| Status | Pattern | Label | 이슈 요약 |
|---|---|---|---|
| WARN | list_modal_overflow | 글자수 제한 누락 — 프로세스 명 (500자) | 클라이언트 검증 없음 → 서버 오류 모달 |
| WARN | list_modal_overflow | 글자수 제한 누락 — 전자서명 (500자) | 동일 |
| WARN | list_modal_overflow | 글자수 제한 누락 — 설명 (500자) | 동일 |
| FAIL | list_crud | CRUD — 항목 추가 | `[AUTO]_cp_test` 추가 후 목록에 없음 |

### nPouch · 태그 관리 (2026-04-28)

| Status | Pattern | Label | 이슈 요약 |
|---|---|---|---|
| WARN | scenario_test | 태그 이름 — 글자수 제한 | DOM maxlength 없음 / 200자 저장됨 |
| WARN | scenario_test | 설명 — 글자수 제한 | 400자 저장됨 |
| WARN | scenario_test | 중복 이름 에러(i18n 미번역) | `COLUMN.NAME.WR_ALREADY_PROCESS` 키 노출 |

---

## 2. 처리 코드 위치 매핑

| Pattern | 처리 위치 | 캡처 함수 | dismiss 위치 |
|---|---|---|---|
| `list_modal_overflow` | `core/list_page_runner.py:340-435` | `self._take_screenshot()` (자체) | line 401 (`_CONFIRM_BTN` 클릭) |
| `list_crud` | `core/list_page_runner.py:660-720` | `self._take_screenshot()` (자체) | dismiss 없음 (목록 비교만) |
| `overflow` (validators) | `validators/overflow.py:457-497` | `_take_screenshot()` (자체) | `_handle_modal()` 내부 (line 478, 484, 489) |
| `required_submit` | `validators/required_submit.py` | `ctx.take_screenshot()` | `ctx.dismiss_warning_dialog()` (line 173, 247, 291) |
| `toggle_checkbox` | `validators/toggle_checkbox.py:218` | `ctx.take_screenshot()` | dismiss 없음 (UI 상태) |
| `scenario_test` | `pages/npouch_*_page.py` (페이지별) | `pages.base_page.take_screenshot()` | 페이지별 상이 |

→ **캡처 함수 3종 + dismiss 패턴 4종**이 혼재. 통일 필요.

---

## 3. 캡처 타이밍 분석

### 현재 동작 (문제)

```
list_modal_overflow:
  1. 500자 입력
  2. 등록 클릭
  3. 서버 오류 모달 출현
  4. 모달 텍스트 캡처
  5. 확인 버튼 클릭 → 모달 닫힘  ← dismiss
  6. _known_bug() 호출
       └─ _take_screenshot() 실행  ← 이미 dismiss 후, 빈 화면 캡처
```

### 이상적인 동작

```
list_modal_overflow:
  1. 500자 입력
  2. 등록 클릭
  3. 서버 오류 모달 출현
  4. 모달 텍스트 캡처
  4-5. 스크린샷 캡처  ← dismiss 직전, cause(입력값) + effect(모달) 한 프레임
  5. 확인 버튼 클릭 → 모달 닫힘
  6. _known_bug(screenshot=ss)  ← 받은 ss 사용, 재촬영 X
```

---

## 4. Type 분류 (4종)

### Type 1 — 모달 출현형
**dismiss 직전 캡처. 모달 + 뒤에 비치는 입력값이 한 프레임에 담김.**

해당 케이스:
- `list_modal_overflow` (현재 보고서 3건)
- `validators/overflow.py` 의 모든 케이스
- `validators/required_submit.py` (필수 미입력 → 경고 모달)

### Type 2 — UI 상태형
**모달 없음. 검증 실패 감지 시점에 캡처. UI 상태 자체가 증거.**

해당 케이스:
- `validators/toggle_checkbox.py` (토글 OFF인데 종속 필드 enabled)
- 라디오 초기값 검증

### Type 3 — 결과 검증형
**모달 없음. 검증 실패 시점 캡처. cause는 화면에서 사라짐 → detail 텍스트로 보완.**

해당 케이스:
- `list_crud` (CRUD 추가 후 목록에 없음)
- `list_modify_verify` (저장값 재확인 실패)

### Type 4 — Silent block형
**입력 시도 직후 캡처. 입력값 그대로 + 미반영 상태가 한 프레임에.**

해당 케이스:
- 태그 입력 거부 (한글, 중복 등)
- `validators/tag_input.py`

---

## 5. 수정 영향 범위

### 패턴 A: ScanContext 표준
- 파일: `core/scan_context.py`, `validators/required_submit.py`, `validators/toggle_checkbox.py`
- 변경: `last_warning_screenshot` 필드 추가 + `dismiss_warning_dialog()` 안에서 캡처
- 호출자: `last_warning_screenshot` 사용으로 교체 (기존 `take_screenshot` 호출 제거)

### 패턴 B: validators/overflow.py
- 파일: `validators/overflow.py`
- 변경: `_handle_modal()` 시그니처 → `tuple[bool|None, str|None]`
- `_make_*_overflow_result` 시그니처 → `page` 대신 `ss` 받기
- 8곳의 `_take_screenshot()` 호출 정리

### 패턴 C: list_page_runner 인라인  ← **앞서 빠진 케이스**
- 파일: `core/list_page_runner.py`
- 변경: `list_modal_overflow` 처리부(line 340-435) 내부에서 dismiss 전 캡처
- `_known_bug`, `_fail` 호출에 미리 캡처한 ss 전달 (재촬영 방지)

→ **세 패턴 모두 손대야 함.** A·B·C 각각 독립적으로 작업 가능.

---

## 6. 미확정 항목

- [ ] **검수자 UX 검증**: 카드 1장당 스크린샷 1장이 정말 충분한가? 부족한 경우 detail 텍스트 보완 충분?
- [ ] **Type 3, 4의 cause 정보**: 화면에서 사라진 입력값을 어떻게 detail에 일관되게 담을지 (포맷 통일)
- [ ] **`scenario_test` 패턴**: nPouch 페이지별 자체 구현 — 통일 정책 필요한지?
- [ ] **screenshot 보관 기간 / 정리 정책**: 매 실행마다 누적되는데 자동 cleanup 필요?
- [ ] **회귀 시나리오**: 같은 페이지 같은 케이스의 스크린샷 비교 (시간 추이 추적)?

---

## 7. 작업 우선순위 (제안)

1. 본 문서 리뷰 + 케이스 분류 확정
2. 패턴 A 수정 + `required_submit.py`로 검증 (가장 호출 많고 표준 패턴)
3. 패턴 C 수정 (현재 보고서의 WARN 3건이 여기 해당 — 사용자 체감 효과 가장 큼)
4. 패턴 B 수정 (`validators/overflow.py` — 호출 적지만 통일성)
5. 검수 흐름 종합 회귀 (실 페이지 돌려서 카드별 스크린샷 1장만 나오는지 확인)
6. `scenario_test` 패턴 검토 (필요 시 별도 작업)

---

## 8. 작업 시 주의사항

- **이미지 중복 방지**: 패턴 A·B·C 각각 수정 시 호출자의 기존 `take_screenshot` 호출을 반드시 제거. 안 하면 dismiss 전 1장 + 후 1장 = 2장.
- **Type 2/3/4는 그대로**: 모달 없는 케이스는 기존 흐름이 옳음. 건드리면 안 됨.
- **회귀 검증**: 패턴별 수정 후 반드시 1회 풀 스캔 → 스크린샷 폴더에 빈 화면 없는지 확인.
- **`docs/TROUBLESHOOTING.md` 기록**: 수정 후 즉시 기록 (CLAUDE.md 규칙).
