# 시나리오 1: UI 구조

> 목적: 화면에 있어야 할 요소가 전부 존재하는지 확인. 동작 테스트 없음.
> 모든 페이지 유형(modal_form / list_page)에 적용.

---

## 반드시 커버해야 할 항목

| 항목 | 내용 | 없으면 |
|------|------|--------|
| 탭 전환 | 탭이 있는 페이지: 각 탭 존재 확인 | `[SKIP] 탭 없음` |
| 버튼 | 추가/수정/삭제 및 페이지 전용 버튼 존재 | fail |
| 테이블 헤더 | 예상 컬럼명 존재 여부 | fail |
| 검색 기능 | 검색창 / 옵션 / 버튼 존재 | fail |

---

## 코드 패턴 참조

### list_page 패턴 (nPouch 계열)

```python
def test_scenario1_ui(self):
    page = self.p.page
    lines, srs = [], []

    # 탭 없는 페이지
    t, s = _r("skip", "탭 전환", "단일 뷰 페이지 — 탭 없음", sc=1)
    lines.append(t); srs.append(s)

    # 탭 있는 페이지 (해당 시 사용)
    # for tab in TABS:
    #     exists = page.locator(f"...{tab}...").count() > 0
    #     t, s = _r("pass" if exists else "fail", f"탭 — {tab}",
    #               f"입력: (없음) / 결과: {'존재' if exists else '없음'}", sc=1)

    # 버튼 목록은 페이지별 yaml 또는 클래스 상수 참조
    for btn_id, label in BTN_LIST:
        exists = page.locator(f"button#{btn_id}").count() > 0
        t, s = _r("pass" if exists else "fail", f"{label} — 존재",
                  f"입력: (없음) / 결과: {'존재' if exists else '없음'}", sc=1)
        lines.append(t); srs.append(s)

    # 테이블 헤더 — 예상 헤더 목록은 페이지별 정의
    headers = [th.inner_text().strip() for th in page.locator("table thead th").all()]
    for h in EXPECTED_HEADERS:
        t, s = _r("pass" if h in headers else "fail", f"테이블 헤더 — {h}",
                  f"입력: (없음) / 결과: {'존재' if h in headers else '없음'}", sc=1)
        lines.append(t); srs.append(s)

    # 검색 영역
    for loc, label in SEARCH_ELEMENTS:
        exists = loc.count() > 0
        t, s = _r("pass" if exists else "fail", label,
                  f"입력: (없음) / 결과: {'존재' if exists else '없음'}", sc=1)
        lines.append(t); srs.append(s)

    for r in lines: print(r)
    self._attach(srs)
    _assert_no_fail(lines, "시나리오 1")
```

### modal_form 패턴 (RansomCruncher 계열)

```python
# scan_hints yaml에서 list_ui 섹션을 읽어 버튼/테이블/검색 자동 검증
# qa_runner.py가 yaml 기반으로 처리 — 테스트 파일에 직접 코드 없음
```

---

## 주의사항

- 버튼/헤더 목록은 코드에 하드코딩하지 않고 **페이지 클래스 상수** 또는 **yaml**로 관리
- 기능 동작 확인(클릭, 검색 실행 등)은 시나리오 3에서
- 탭이 없는 페이지는 탭 항목만 `[SKIP]` 처리, 나머지 동일하게 진행
