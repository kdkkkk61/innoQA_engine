# 시나리오 4: 수정 시나리오

> 목적: **수정 흐름 전체의 정합성** 검증.
> 정상 입력의 로드/재확인뿐 아니라, **위반 입력 시도 후 실제 저장값**까지 확인한다.
> 추정 금지 — 모든 결과는 재오픈 후 직접 확인.

---

## 정의 변경 이력

- **2026-04-30**: "정상 흐름만"에서 **"수정 흐름 전체 정합성"** 으로 확장.
  - 4-3 추가 — 위반 입력 (필수 필드 비움) 시도 후 실제 저장값 확인.
  - 배경: 시나리오 2가 EDIT 모달에서 "경고 안 떴다 → 저장됐겠지" 추정으로
    끝났는데, 실제로 빈값/원본/다른값 중 어디로 저장됐는지 정확한 결과 파악
    불가. 이를 시나리오 4 영역으로 정리 (시나리오 2의 책임 영역은 1차 검증만).

---

## 반드시 커버해야 할 항목

| 단계 | 내용 | 비고 |
|------|------|------|
| **4-1. 로드 확인** | 수정 모달 열기 → 전 필드 저장값 확인 | 실행경로 포함 전 필드 |
| **4-2. 수정 후 재확인** | 필드 변경 → 저장 → 모달 재오픈 → 변경값 확인 | 생략 불가 |
| **4-3. 위반 결과 확인** | 필수 필드 비움 → 저장 시도 → 재오픈 → **실제 저장값** 확인 | 생략 불가 |

> - 4-1만 구현하고 4-2를 생략 → "수정 동작" 자체 미검증
> - 4-1·2만 구현하고 4-3 생략 → "위반 시 데이터 처리" 미검증 (서버가 빈값으로 저장하는 데이터 손상 등 미감지)

---

## 4-3 위반 결과 확인 — 결과 분기

| 재오픈 시 실제 값 | 의미 | status |
|---|---|---|
| `""` (빈값) | 클라이언트·서버 모두 검증 누락 — 데이터 손상 | **fail** |
| `original` (이전값 유지) | 서버가 빈값 거부 — UX 혼란 (사용자는 "저장됐다" 착각) | **warn** |
| 그 외 다른 값 | 제품의 예상 못한 동작 (자동 채움 등) | **fail** |

> error는 테스트 도구 자체 오류(셀렉터 못 찾음·타임아웃)에만 사용. 제품 동작 결과는
> fail/warn으로 분류 (`test_scenario_standard.md` status 기준 준수).
>
> 시나리오 2의 EDIT 1차 검증 ("경고 떴는가") 에서 "경고 안 뜸"으로 끝난 케이스의
> 실제 결과를 여기서 분기 판정한다. 정직한 검증의 핵심.

---

## Pattern 명명 (출력·정렬용)

| 페이지 유형 | pattern 이름 |
|---|---|
| **list_page** (공통 프로세스, 제어 스위트, nPouch) | `list_modify_required` |
| **modal_form** (RDP, 랜섬 탐지) | `modify_required` |

**시나리오 4 영역 출력**: `required_submit` 패턴이 시나리오 2 끝(order 9999)에 위치하는 것과
달리, 신규 pattern은 **시나리오 4 영역 안** 에 위치 (4-2 다음, 시나리오 5 이전).

→ 출력 정렬 규칙은 `scan-output-format.md` 참조.

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

    # ── 4-1. 수정 모달 열기 → 전 필드 로드 확인 ─────────────────────
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

    # ── 4-2. 수정 후 재확인 (필수) ───────────────────────────────────
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

    # ── 4-3. 위반 결과 확인 (필수) ───────────────────────────────────
    # 필수 필드 비움 → 저장 시도 → 재오픈 → 실제 저장값 확인
    REQUIRED_FIELD = SEL_NAME    # 페이지별 필수 필드
    REQUIRED_LABEL = "이름"
    original_required = p.get_field_value(REQUIRED_FIELD)

    # 필수 필드 비우고 저장 시도
    p.page.locator(REQUIRED_FIELD).first.fill("")
    p.page.wait_for_timeout(150)
    p.click_attached(SEL_SUBMIT_BTN)
    p.dismiss_warning_dialog()  # 경고 떴으면 닫고 — 떴는 안 떴는 시나리오 2가 이미 봤음
    p.wait_for(SEL_ADD_BTN)

    # 재오픈 → 실제 값 확인 (추정 금지)
    p.open_modify_modal(_AUTO_NAME)
    actual = p.get_field_value(REQUIRED_FIELD)
    if actual == "":
        status, detail = "fail", f"빈값 그대로 저장됨 — 데이터 손상 (입력: 비움 / 결과: '')"
    elif actual == original_required:
        status, detail = "warn", f"서버가 빈값 거부 → 이전값 유지 (입력: 비움 / 결과: {actual!r})"
    else:
        status, detail = "fail", f"제품의 예상 못한 동작 (입력: 비움 / 결과: {actual!r})"
    # pattern: list_modify_required (list_page) / modify_required (modal_form)
    t, s = _r(status, f"{REQUIRED_LABEL} — 빈값 저장 시도 후 결과",
              detail, sc=4)

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
#
# 4-3 위반 결과 확인:
#   - get_required_fields() 로 필수 필드 목록 획득
#   - 각 필수 필드 비우고 저장 시도 → 재오픈 → 실제 값 확인
#   - 결과 분기: 빈값 / 원본 / 다른값 → fail / warn / error
```

---

## 주의사항

- 로드 확인 시 수정 모달을 닫지 않고 바로 4-2로 이어가도 됨
- 4-2의 수정할 필드는 실제 변경이 잘 되는 필드 선택 (이름 필드는 중복 가능성 있어 피하는 게 나음)
- 4-2의 NEW_VALUE는 매 실행마다 다른 값이 되도록 타임스탬프 등 활용 권장
- **4-3 주의**: 필수 필드를 비우고 저장 시도 후 모달이 닫혔는지 / 경고가 떴는지는 시나리오 2가
  이미 판정함. 시나리오 4-3는 **그 후 실제 저장된 값**만 본다 (책임 분리).
- **4-3는 페이지별 필수 필드 모두에 적용** (이름 필드만 보지 말고 yaml `required: true` 전부)
