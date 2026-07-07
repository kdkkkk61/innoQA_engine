# 시나리오 6: 연계 데이터 준비

> 목적: 다음 테스트에서 사용할 데이터를 생성하고 **삭제하지 않고 남겨둔다**.
> 연계 대상이 없는 페이지는 `[SKIP]` 출력만 하고 종료한다.

---

## 적용 기준

| 조건 | 처리 |
|------|------|
| 하위 연계 테스트가 존재함 | 연계 항목 생성 → 삭제하지 않고 남김 |
| 하위 연계 테스트가 없음 | `[SKIP] 시나리오 6 — 연계 대상 없음` 출력 후 종료 |

---

## 항목 이름 규칙

```
[AUTO]_{제품약자}_{종류}_suite
```

| 예시 | 설명 |
|------|------|
| `[AUTO]_np_proc_suite` | nPouch 운용 프로세스 연계용 |
| `[AUTO]_np_tag_suite`  | nPouch 태그 연계용 |

- `[AUTO]` 접두사 필수 → cleanup 대상으로 관리됨
- `_suite` 접미사로 "연계 데이터"임을 명시

---

## AUTO / AUTO_KEEP Lifecycle (2026-05-22 명세)

### 전체 흐름

```
세션 시작 (sc1a / _ensure_session_cleanup)
  → delete_all_test_data() = AUTO + AUTO_KEEP 모두 삭제 (clean slate)

sc1~5 실행
  → AUTO + AUTO_KEEP 생성 / 검증
  → 같은 페이지 안 시나리오 사이는 삭제 이벤트 없음
    (sc3 가 만든 [AUTO]_sc3_step1 등은 sc4 가 EDIT 검증에 그대로 사용 가능)

sc1~5 끝 (필요 시 명시 cleanup)
  → delete_all_auto_policies() = AUTO 만 삭제 / AUTO_KEEP 유지

sc6 (연계 페이지 / 다음 정책 페이지)
  → AUTO_KEEP 정책 확인 후 유지 (다음 페이지가 사용)
  → 예: 운용 프로세스 [AUTO]_np_proc_suite — 태그 페이지가 사용

zz_cleanup (test_zz_cleanup.py — 최종)
  → delete_all_auto_policies() = AUTO 만 삭제 / AUTO_KEEP 보존
  → AUTO_KEEP 최종 정리는 "다음 run 의 sc1 시작 (delete_all_test_data)" 가 담당
    (zz 가 keep 을 지우면 sc6 '남겨둠' 의도와 충돌 → 사용자 결정 2026-05-28 로 변경)
```

### cleanup 책임 분담 (사용자 결정 2026-05-28 — 제어 스위트 확정)

| 시점 | 호출 | 대상 |
|------|------|------|
| sc1 시작 (`_ensure_session_cleanup`) | `delete_all_test_data()` | AUTO + AUTO_KEEP 전부 (clean slate) |
| sc5 완료 (5c) | `delete_all_auto_policies()` | AUTO 만 / AUTO_KEEP 보존 (+ 프로세스 1건 재채움) |
| sc6 | (cleanup 없음) | AUTO_KEEP 존재·내용 **확인/표시만** → 다음 연계 사용 신호 |
| zz_cleanup (최종) | `delete_all_auto_policies()` | AUTO 안전망 / AUTO_KEEP 보존 |

- AUTO_KEEP 은 run 종료 후에도 남아 다음 연계(통합정책 등)·수동 확인에 사용. 다음 run sc1 이 최종 wipe.
- 제어 스위트 sc6 는 다운스트림(통합정책) 테스트 **미구현** 상태라 "생성" 대신 "sc5 산출물 확인"으로 재정의 (`test_scenario6_suite_setup.py`). 통합정책 구현 시 실제 연계 사용 추가.

### sc3 / sc4 관계 (생성-수정 연계, 같은 페이지 안)

- sc3 가 `[AUTO]_sc3_step{N}` 또는 `[AUTO_KEEP]_sc3_step{N}` 생성 → 세션 안 보존
- sc4 가 동일 정책 사용해 EDIT 검증 → 이름 변경 / 새로 생성 불필요
- sc4 단독 실행 시 sc3 정책 없으면 `pytest.skip` 처리 (의존 명시)

### 두 접두사가 일정 기간 공존

- 기존 코드는 `[AUTO]_*_suite` 형식으로 보존 데이터를 표시하고 있음
- 신규 시나리오 6 작성 시부터 `[AUTO_<MMDD>]_*` 날짜본 형식 적용 ('KEEP' 용어 폐기 — 아래 명명 통일 참조)
- 기존 코드(nPouch 등 `[AUTO_KEEP]`) 마이그레이션은 별도 작업 예정

### 명명 통일: `[AUTO_KEEP]` → `[AUTO_<날짜MMDD>]` 날짜본 (2026-06-10 결정, 2026-06-30 'KEEP' 용어 폐기)

영속·연계 역할 접두사를 고정명 `[AUTO_KEEP]` 대신 날짜를 붙인 `[AUTO_0610]` '날짜본'으로 한다. 'KEEP'이라는 별도 용어를 버리고 **날짜 유무**로만 구분한다(날짜 없음=휘발성 / 날짜 있음=영속).

| 접두사 | 역할 | cleanup |
|--------|------|---------|
| `[AUTO]` (날짜 없음) | 휘발성 테스트 데이터 | 삭제 대상 (sc1 시작 / sc5 종료) |
| `[AUTO_0610]` (날짜 MMDD) | 날짜본 (영속·연계용) | 삭제 안 함 |

- **이유**: `[AUTO_KEEP]` 고정명은 **다른 날 재실행 시 이전 KEEP 이 아직 등록/연계(상위 정책이 참조 중 등)돼 있으면 같은 이름 → "이미 등록된 이름 입니다" 충돌**(삭제도 참조 잠금으로 막힘). 날짜본(`[AUTO_0610]`)은 run 일자로 이름이 달라 이전 KEEP 이 살아 있어도 안 겹침. 같은 날 재실행은 동명 재사용(없을 때만 생성).
- **핵심 (cleanup 코드 무변경 성립)**: `name.startswith("[AUTO]")` 는 `[AUTO]_x` 는 True, `[AUTO_0610]_x` 는 6번째 글자가 `]` 가 아니라 `_` 라 **False**. 따라서 기존 `delete_all_auto_policies()`(= `startswith("[AUTO]")` 만 삭제)가 그대로 "날짜 없는 `[AUTO]` 만 삭제 / 날짜본 KEEP 보존" 을 만족한다.

#### 현재 적용 상태 (사실)
- `secure_zone` 접근제어 정책: 독립 페이지(연계 대상 없음) → `[AUTO]` 휘발성만 사용. KEEP 미사용. (`tests/secure_zone/`)
- **시큐어존 템플릿(시큐어드라이브)**: `[AUTO_<날짜>]` **첫 실제 적용**. sc6(`test_scenario6_suite_setup.py`)가 `[AUTO_<MMDD>]_sztpl_sd`(시큐어드라이브 2건 + 반출) 생성 → `delete_all_auto()`(= `startswith("[AUTO]")` 만 삭제)로 휘발성 `[AUTO]` 전부 삭제, 날짜본 보존·남김. 상위 시큐어존 정책이 템플릿 참조(속성 모달 '사용처'에 표시) — 정책 테스트는 미구현이라 현재는 날짜본 seed 생성·보존까지.
- nPouch 계열: 기존 `[AUTO_KEEP]` 형식 그대로 사용 중. `[AUTO_<날짜>]` 미적용.
- `[AUTO_<날짜>]` 형식은 KEEP 연계가 필요한 페이지에서 도입한다. 도입 시 안전 가드를 `^\[AUTO(_\d{4,8})?\]` 정규식으로 확장(날짜 없는 `[AUTO]` + 날짜본 둘 다 테스트 데이터로 인식)한다. nPouch 마이그레이션 범위는 현재 미확정.
  - 시큐어존 템플릿 page 의 안전 가드 `_AUTO_ANY = ^\[AUTO(_\d{4,8})?\]` 가 이 확장형(날짜 4~8자리)을 이미 반영.

---

## 연계 순서 (nPouch 계열)

```
운용 프로세스 (test_npouch.py)
  → 시나리오 6: [AUTO]_np_proc_suite 생성 (삭제 안 함)
  ↓
태그 관리 (test_npouch_tag.py)
  → 시나리오 6: [AUTO]_np_proc_suite 프로세스를 [AUTO]_np_tag_suite 태그에 등록 (삭제 안 함)
  ↓
제어 스위트 (test_npouch_suite.py) — 미구현
  → 시나리오 6: [AUTO]_np_tag_suite 태그를 사용하는 스위트 생성 (삭제 안 함)
  ↓
통합정책 (test_npouch_policy.py) — 미구현
  → 시나리오 6: 스위트를 연계한 정책 생성
```

---

## 연계 순서 (시큐어존 템플릿 계열 — 2026-07-07 추가)

```
템플릿 탭별 sc6: 날짜본 seed 생성 (삭제 안 함)
  특수폴더:   [AUTO_<MMDD>]_sz_mf_link / _reg (용도 2종, 각 매핑 1건)
  폴더동기화: [AUTO_<MMDD>]_sz_sync (매핑 1건 — 스케줄 매주·월 포함)
  ↓
시큐어존 정책 (연계 테스트 미구현)
  → 정책의 템플릿설정 탭에서 위 날짜본을 picker 로 선택
  → 템플릿 속성 모달 '※ 사용처 확인' 섹션에 정책명 표시됨 (연계 확인 지점)
```

- **seed 는 실사용 가능해야 한다**: 이름만 있는 빈 템플릿이 아니라 매핑(+탭 고유 설정 —
  폴더동기화는 스케줄)을 포함해, 정책이 참조했을 때 실동작 검증이 가능한 상태로 남긴다.
  근거 코드: `tests/secure_zone_template_sync_folder/test_scenario6_suite_setup.py` (sync_suite_seed 매주·월).
- **cross-page 검증 3종** (태그 sc6a~6c 에서 확립 — 정책 연계 테스트 작성 시 동일 적용):
  ① 참조 등록(연계 생성) ② 참조 잠금 — 참조되는 쪽 삭제 시도 → 차단 경고가 떠야 정상
  ③ 사용처 표시 — 참조되는 쪽 속성 모달에 참조하는 쪽 이름 표시.
  근거 코드: `tests/common/tag/test_scenario6_suite_setup.py` (sc6b 삭제 차단 / sc6c 사용처 표시).

---

## 코드 패턴

### 연계 대상 있음 (nPouch 운용 프로세스 → 태그)

```python
def test_scenario6_suite_setup(self):
    """시나리오 6: 연계 데이터 준비 — [AUTO]_np_proc_suite 생성 후 남겨둠"""
    print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 6: 연계 데이터 준비 ━━━━━━━━━━━━━━━━━━")
    p = self.p
    lines, srs = [], []

    _SUITE = "[AUTO]_np_proc_suite"

    # 기존 suite 항목 정리 (중복 방지)
    try:
        p.search_item(_SUITE)
        if _SUITE in p.get_item_names():
            p.delete_item(_SUITE)
    except Exception:
        pass
    p._restore_page_size()

    # 연계 항목 생성
    try:
        p.add_item(_SUITE)
        p.search_item(_SUITE)
        exists = _SUITE in p.get_item_names()
        t, s = _r("pass" if exists else "fail",
                  "연계 프로세스 생성 — 목록 확인",
                  f"입력: {_SUITE!r} 생성 / 결과: {'목록에 존재' if exists else '없음'}", sc=6)
        lines.append(t); srs.append(s)
    except Exception as e:
        t, s = _r("fail", "연계 프로세스 생성", str(e), sc=6)
        lines.append(t); srs.append(s)

    # 삭제하지 않고 종료 — 태그 테스트에서 사용
    t, s = _r("skip", "연계 데이터 남겨두기",
              f"{_SUITE!r} — 태그 관리(시나리오 6)에서 사용 예정", sc=6)
    lines.append(t); srs.append(s)

    for r in lines: print(r)
    self._attach(srs)
    _assert_no_fail(lines, "시나리오 6")
```

### 연계 대상 없음 (skip 패턴)

```python
def test_scenario6_suite_setup(self):
    """시나리오 6: 연계 데이터 준비 — 해당 없음"""
    print(f"\n\n━━ [{self.PAGE_NAME}] 시나리오 6: 연계 데이터 준비 ━━━━━━━━━━━━━━━━━━")
    lines, srs = [], []
    t, s = _r("skip", "시나리오 6: 연계 데이터 준비",
              "연계 대상 없음 — 이 페이지 이후에 사용되는 하위 테스트 없음", sc=6)
    lines.append(t); srs.append(s)
    for r in lines: print(r)
    self._attach(srs)
```

---

## 태그 테스트에서의 시나리오 6 패턴 (프로세스 등록)

```python
def test_scenario6_suite_setup(self):
    """시나리오 6: 연계 데이터 준비 — [AUTO]_np_tag_suite 생성 + proc_suite 프로세스 등록"""
    p = self.p
    lines, srs = [], []

    _SUITE_TAG  = "[AUTO]_np_tag_suite"
    _SUITE_PROC = "[AUTO]_np_proc_suite"   # 운용 프로세스 테스트(시나리오 6)에서 생성

    # 기존 suite 태그 정리
    try:
        p.search_item(_SUITE_TAG)
        if _SUITE_TAG in p.get_item_names():
            p.delete_item(_SUITE_TAG)
    except Exception:
        pass
    p._restore_page_size()

    # 태그 생성
    try:
        p.add_item(_SUITE_TAG)
        p.search_item(_SUITE_TAG)
        exists = _SUITE_TAG in p.get_item_names()
        t, s = _r("pass" if exists else "fail", "연계 태그 생성", ..., sc=6)
    except Exception as e:
        t, s = _r("fail", "연계 태그 생성", str(e), sc=6)
    lines.append(t); srs.append(s)

    # 수정 모달 열기 → + 버튼 → 프로세스 서브모달 → proc_suite 선택 → 확인 → 저장
    try:
        p.open_modify_modal(_SUITE_TAG)
        p.open_process_list_modal()
        # _SUITE_PROC 이름으로 서브모달 내부 검색 후 선택 (또는 첫 번째 선택)
        registered = p.select_process_by_name(_SUITE_PROC)   # 구현 필요
        p.confirm_process_selection()
        p.click_attached(p.SEL_SUBMIT_BTN)
        p._handle_confirm_modal()
        p.wait_for(p.SEL_ADD_BTN)

        cnt = p.get_process_count_in_list(_SUITE_TAG)
        t, s = _r("pass" if cnt >= 1 else "fail", "연계 프로세스 등록 확인",
                  f"입력: {_SUITE_PROC!r} 등록 / 결과: 프로세스 수={cnt}", sc=6)
    except Exception as e:
        t, s = _r("fail", "연계 프로세스 등록", str(e), sc=6)
    lines.append(t); srs.append(s)

    # 삭제하지 않고 종료
    t, s = _r("skip", "연계 데이터 남겨두기",
              f"{_SUITE_TAG!r} (proc 포함) — 제어스위트 테스트에서 사용 예정", sc=6)
    lines.append(t); srs.append(s)

    for r in lines: print(r)
    self._attach(srs)
    _assert_no_fail(lines, "시나리오 6")
```

---

## 주의사항

- **삭제 금지**: 시나리오 6은 `delete_all_auto_items()` 호출 금지
  - 단, 기존 중복 suite 항목은 사전 정리 가능 (시나리오 재실행 대비)
- **`[AUTO]` 접두사 필수**: cleanup 대상으로 관리되어야 함
- **연계 항목이 없을 때 fail 처리 금지**: 상위 테스트가 아직 실행 안 된 경우를 대비해 `warn`으로 처리
- **pytest 실행 순서**: `test_npouch.py` → `test_npouch_tag.py` 순서 보장 필요
  - `pytest.ini` 또는 `conftest.py`의 `collect_order` 설정 확인

---

## 신규 페이지 추가 체크리스트 (시나리오 6 관련)

```
□ 연계 대상 있음/없음 판단
□ 있음: _suite 접미사 항목 이름 결정 (명명 규칙 준수)
□ 있음: 상위 연계 항목이 없을 때 warn 처리 (fail 금지)
□ 있음: 항목 삭제하지 않고 [SKIP] 남겨두기 결과 출력
□ 없음: [SKIP] 출력 후 종료
```
