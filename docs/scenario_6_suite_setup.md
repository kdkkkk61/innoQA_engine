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
