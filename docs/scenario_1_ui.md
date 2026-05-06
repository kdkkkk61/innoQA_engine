# 시나리오 1: UI 구조

> 목적: 화면에 있어야 할 요소가 전부 존재하는지 확인 + **DOM 자동 스캔으로 신규/제거된 요소 감지**.
> 모든 페이지 유형(modal_form / list_page)에 적용.
>
> **2026-05-06 변경**: 시나리오 1 책임 확장 — "yaml 정의 요소 존재 확인"에서
> "yaml ↔ DOM 양방향 비교"로. 회귀 테스트 본질(기능 추가/제거 감지)이 시나리오 1 영역.

---

## 정의 변경 이력

- **2026-05-06**: DOM 자동 스캔 + yaml 비교 영역 신설.
  - 배경: yaml에 정의된 요소만 검증하면 새 기능 추가/제거를 감지 못 함 (회귀 본질 누락).
  - 영역: 시나리오 1에 "DOM 스캔 → yaml 비교 → 차이 표시" 추가.
  - 패턴: `discovered_new` (DOM에만 존재 = 신규) / `discovered_missing` (yaml에만 존재 = 제거).

---

## 반드시 커버해야 할 항목

| 항목 | 내용 | 없으면 |
|------|------|--------|
| 탭 전환 | 탭이 있는 페이지: 각 탭 존재 확인 | `[SKIP] 탭 없음` |
| 버튼 | 추가/수정/삭제 및 페이지 전용 버튼 존재 | fail |
| 테이블 헤더 | 예상 컬럼명 존재 여부 | fail |
| 검색 기능 | 검색창 / 옵션 / 버튼 존재 | fail |
| **DOM 스캔 (신규/제거 감지)** | yaml ↔ DOM 양방향 비교 | warn (검수자 확인 필요) |

---

## DOM 스캔 + yaml 비교 (신규 — 회귀 본질)

### 목적
기능이 **추가되거나 제거됐을 때** 자동 감지. yaml만 의존하면 새 기능을 모르고 지나감.

### 메커니즘
```
1. 모달/페이지 컨텍스트의 DOM 자동 스캔 → 셀렉터 set_A
   대상: input / textarea / select / checkbox / radio (id 있는 것만)
2. yaml hints에서 정의된 셀렉터 추출 → set_B
3. 비교:
   - set_A - set_B  → 🆕 신규 요소 (DOM에만 존재)
   - set_B - set_A  → ❌ 제거된 요소 (yaml에만 존재)
   - set_A ∩ set_B  → 정상 (그 외 시나리오에서 검증)
```

### 결과 분류

| 패턴 | 의미 | status |
|------|------|--------|
| `discovered_new` | DOM에 있는데 yaml에 없음 → 신규 기능 가능성 | warn |
| `discovered_missing` | yaml에 있는데 DOM에 없음 → 기능 제거 가능성 | warn |

### 검수자 후속 처리
- 🆕 신규: yaml에 추가 (의도된 기능이면 정식 검증 시작) / 의도된 제거면 무시
- ❌ 제거: yaml에서 제거 (의도된 변경) / 회귀면 제품팀 보고

### 사용자 검증 절차 (자동 회귀 메커니즘 자체 검증)
1. yaml 일부 항목 주석 처리
2. 테스트 실행
3. 보고서에 "🆕 신규 요소" WARN 카드 출현 확인
4. 주석 복원 → 카드 사라짐 확인
→ 메커니즘 동작 보장.

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
