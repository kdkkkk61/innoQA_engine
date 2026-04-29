# 테스트 파이프라인

> 태그: [공통 — 새 test_*.py 파일 추가 시]
> 새 테스트 파일을 추가하거나 파이프라인 구조를 파악해야 할 때 이 문서를 읽는다.

---

## 파이프라인 구조

모든 테스트(modal_form / list_page 계열 모두)는 동일한 파이프라인을 사용한다.

```
test_*.py
  → ScanResult / PageScanReport 객체 생성
  → request.node._scan_report 에 첨부
  → conftest pytest_runtest_makereport 에서 _scan_reports 수집
  → pytest_unconfigure 에서 html_reporter.py 로 HTML 생성
  → [HTML 리포트] 라인 출력 → app.py 감지
```

파이프라인 관련 금지사항:
- `print()`만으로 결과를 출력하고 ScanResult 객체를 만들지 않는 것
- 제품마다 별도 리포트 생성 코드(예: `npouch_reporter.py`)를 만드는 것
- conftest / html_reporter 파이프라인을 우회하는 것

---

## 두 계열 비교

| 항목 | modal_form (랜섬크런처 계열) | list_page (nPouch 계열) |
|---|---|---|
| 테스트 구조 | `@pytest.mark.parametrize("page_id", ...)` 단일 함수 | `class TestNpouchXxx` + 시나리오별 메서드 5개 |
| page_id 전달 | `item.callspec.params["page_id"]` | `item._npouch_page_id` |
| 리포트 수집 | 테스트 1개당 1 PageScanReport | 시나리오 5개 → conftest에서 page_id별 머지 |
| print 출력 | 없음 | 있음 (실시간 로그용, ScanResult와 병행) |

---

## ScanResult 패턴

(코드 예시: `_r(status, label, detail, sc)` 호출 → print용 문자열 + ScanResult 동시 반환)

(코드 예시: 테스트 메서드 끝에서 `PageScanReport` 생성 → `request.node._scan_report` 첨부 → conftest 수집)

---

## 이슈 발생 시 자동 스크린샷 패턴 (list_page 계열)

### 원칙

- `fail` / `warn` 감지 시 **정리(모달 닫기 등) 전에** 즉시 현재 화면을 캡처한다
- 특정 위치에 하드코딩하지 않는다 — `_make_r(sc)` 로 생성한 로컬 `r`을 사용하면
  모든 호출 시점에서 자동 캡처된다

### 구현

```python
class TestNpouchXxx:

    def _make_r(self, sc: int):
        """이슈 감지 즉시 현재 화면을 자동 캡처하는 _r() 래퍼 생성.
        fail/warn 상태에서 호출 시점의 화면을 저장한다.
        반드시 정리(모달 닫기 등) 전에 호출할 것."""
        _page = self.p.page
        def r(status: str, label: str, detail: str = "") -> tuple:
            return _r(status, label, detail, sc=sc, page=_page)
        return r

    def test_scenario3_crud(self):
        r = self._make_r(3)   # ← 시나리오 시작 시 한 번만 선언
        lines, srs = [], []
        ...
        # 이슈 감지 위치에서 r() 호출 — 자동 캡처
        t, s = r("fail" if ... else "pass", "라벨", "디테일")
        # 그 다음 정리
        p.close_modal()
```

### 주의사항

- `r()` 호출은 반드시 `close_modal()` / `click_attached(submit)` 등 **정리 이전**에 둔다
- 정리 후 `r()` 를 호출하면 이미 화면이 바뀌어 의미 있는 캡처가 안 된다
- `_make_r`은 클래스 메서드이며, 모듈 레벨 `_r()`을 대체한다 (삭제하지 않음)

---

## 테스트 파일 작성 절차

다음은 새 `test_*.py`를 작성할 때 따르는 절차이며, 동시에 작업 진행 중 지켜야 할 원칙이다.

1. **`docs/test_scenario_standard.md`를 무조건 먼저 읽는다**
   - 새 테스트 파일 작성 전 반드시 확인
   - 시나리오 번호·출력 포맷·필드 레이블 기준이 모두 거기에 있다

2. **페이지별 디테일은 사용자가 확인 후 진행**
   - 각 페이지는 겉보기엔 비슷해도 필드 구성·동작이 다르다
   - 추정으로 먼저 구현하면 기본 틀이 깨진다
   - 순서: 시나리오 1개 구현 → 실행 → 결과 확인 → 다음 시나리오

3. **앞서서 만들지 않는다**
   - 사용자가 "다음"이라고 하기 전까지 다음 시나리오·다음 페이지 코드를 작성하지 않는다
   - 한 번에 여러 시나리오를 묶어서 구현하는 것은 금지
   - 실행 결과(HTML 리포트)를 보고 난 뒤에만 다음 단계로 이동

4. **검증되지 않은 코드는 남기지 않는다**
   - 실행 확인 없이 작성된 코드는 즉시 제거 대상
   - 미확인 import, 미확인 상수, 미확인 클래스는 파일에 두지 않는다

---

## 관련 문서

- `docs/architecture.md` — 레이어 구조, pages/ 규칙, fixture 선택 기준
- `docs/scan-output-format.md` — modal_form 계열 출력 형식 상세 (list_page 해당 없음)
- `docs/test_scenario_standard.md` — 시나리오 번호 체계, 출력 포맷 기준
