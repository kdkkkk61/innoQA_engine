# 시나리오 4: 수정 시나리오

> 목적: 저장된 값이 수정 모달에 올바르게 로드되는지 + 수정 후 값이 실제 반영되는지 확인.
> **두 단계 모두 필수**: 로드 확인 → 수정 후 재확인

---

## 반드시 커버해야 할 항목

| 단계 | 내용 | 비고 |
|------|------|------|
| **4-1. 로드 확인** | 수정 모달 열기 → 전 필드 저장값 확인 | 실행경로 포함 전 필드 |
| **4-2. 수정 후 재확인** | 필드 변경 → 저장 → 모달 재오픈 → 변경값 확인 | 생략 불가 |

> 4-1만 구현하고 4-2를 생략하면 "수정 동작" 자체를 검증하지 않은 것

---

## 반드시 커버해야 할 필드

- 수정 모달에 존재하는 **모든 필드** (yaml `fields` 섹션 전체)
- 필수 필드: 저장값과 `==` 일치 여부
- 선택 필드: 저장된 값 또는 빈값 그대로 표시
- 실행경로 등 선택 필드라도 누락 금지

---

## 코드 패턴 참조

### list_page 패턴 (nPouch 계열)

```python
def test_scenario4_modify(self):
    p = self.p
    lines, srs = [], []

    # 사전 조건: 항목 추가
    p.delete_all_auto_items()
    p.add_item(_AUTO_NAME)

    # 4-1. 수정 모달 열기 → 전 필드 로드 확인
    p.open_modify_modal(_AUTO_NAME)
    title = p.get_modal_title()
    t, s = _r("pass" if "수정" in title else "warn", "수정 모달 — 제목",
              f"입력: 수정 모달 오픈 / 결과: 제목={title!r}", sc=4)

    for sel, label, expected in FIELD_LOAD_LIST:  # yaml 또는 클래스 상수 참조
        loaded = p.get_field_value(sel)
        if expected is not None:  # 필수 필드: 정확한 값 비교
            t, s = _r("pass" if loaded == expected else "fail",
                      f"{label} — 수정 모달 로드",
                      f"입력: {expected!r} 저장 / 결과: {loaded!r}", sc=4)
        else:  # 선택 필드: 값 표시만
            t, s = _r("pass", f"{label} — 수정 모달 로드",
                      f"입력: 저장 후 로드 / 결과: {loaded!r}", sc=4)

    # 4-2. 수정 후 재확인 (필수)
    TARGET_FIELD = SEL_DESCRIPTION  # 페이지별로 수정할 필드 선택
    NEW_VALUE = "scan_mod_" + str(int(time.time()))[-4:]  # 고유값
    p.page.locator(TARGET_FIELD).first.fill(NEW_VALUE)
    p.page.wait_for_timeout(150)
    p.click_attached(SEL_SUBMIT_BTN)
    p._handle_confirm_modal()
    p.wait_for(SEL_ADD_BTN)

    p.open_modify_modal(_AUTO_NAME)
    loaded_new = p.get_field_value(TARGET_FIELD)
    t, s = _r("pass" if loaded_new == NEW_VALUE else "fail",
              f"{TARGET_LABEL} — 수정 후 재확인",
              f"입력: {NEW_VALUE!r} 수정 / 결과: {loaded_new!r}", sc=4)
    p.close_modal()

    # 사후 정리
    try:
        p.delete_item(_AUTO_NAME)
    except Exception:
        pass

    for r in lines: print(r)
    self._attach(srs)
    _assert_no_fail(lines, "시나리오 4")
```

### modal_form 패턴 (RansomCruncher 계열)

```python
# scan_hints yaml의 list_modify / list_modify_verify 섹션 참조
# 수정 모달 열기 → 각 필드 값 로드 확인 → 변경 → 저장 → 재확인
# get_verify_values() 메서드로 기대값 반환
```

---

## 주의사항

- 로드 확인 시 수정 모달을 닫지 않고 바로 4-2로 이어가도 됨
- 수정할 필드는 실제 변경이 잘 되는 필드 선택 (이름 필드는 중복 가능성 있어 피하는 게 나음)
- 4-2의 NEW_VALUE는 매 실행마다 다른 값이 되도록 타임스탬프 등 활용 권장
