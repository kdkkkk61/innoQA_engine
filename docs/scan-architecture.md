# 스캔 아키텍처 분기 가이드

> **현재 프로젝트에는 두 가지 UI 스캔 아키텍처가 공존한다.** 새 페이지 추가 / 기존 페이지 확장 시 어느 방식을 따를지 이 문서로 결정한다.

CLAUDE.md 의 [공통 — 새 pages/ 파일 추가 시] [공통 — 새 test_*.py 파일 추가 시] 태그 작업 진입 전 필독.

---

## 1) 두 방식 개요

### 방식 A — modal_form (UIScanner 자동)
**적용 페이지**: RansomCruncher 탐지정책 / RDP 정책

- yaml = **Truth source** — text_inputs / toggle_checkboxes / radio_groups / tag_input 명세대로 UIScanner 가 자동 검증
- 단일 메서드 + phase 1+2+3 순차 호출
- 검증 메서드 거의 작성 안 함 (UIScanner 가 yaml 명세 자동 실행)

코드 인용 (`tests/archive/test_ransom_detect_policy_scan.py`):
```python
class TestRansomDetectPolicyScan:
    def test_detect_scenario_qa(self, logged_in_page, settings, request):
        scanner = UIScanner(logged_in_page, config_dir="config")

        # Phase 1 — 초기값 + 필수입력 (ADD 1차)
        report1 = scanner.scan("ransom_detect_policy", phase=1,
                               modal_open_fn=page_obj.open_add_modal,
                               modal_close_fn=close_phase1)

        # Phase 2 — UI 요소 동작 전체 (ADD 2차) = 시나리오 1 + 시나리오 2 자동
        report2 = scanner.scan("ransom_detect_policy", phase=2, ...)

        # Phase 3 — EDIT 모달 (시나리오 4)
        report3 = scanner.scan("ransom_detect_policy", phase=3,
                               modal_open_fn=lambda: open_modify_modal(p2_name))
```

### 방식 B — list_page + sc0 (수동 시나리오 + UIScanner 일부)
**적용 페이지**: 제어스위트 (npouch_control_suite) / 원본보호 정책 (npouch_origin_protect)

- yaml = **참조 메모** (truth source 역할 일부) — Chrome MCP 검증 사실 기록
- 시나리오 1~6 별도 메서드 수동 작성 (검증 1건 = 메서드 1줄)
- sc0 만 UIScanner phase=2 단발 호출 — 신규 기능 감지 + yaml 명세된 항목 자동 검증

코드 인용 (`tests/control_suite/test_scenario0_scan.py`):
```python
class TestScenario0Scan(ControlSuiteBase):
    def test_scenario0a_add_modal_scan(self, logged_in_page, settings):
        scanner = UIScanner(logged_in_page, config_dir="config")
        report = scanner.scan(
            page_id="control_suite",
            phase=2,
            modal_open_fn=page.open_add_modal,
            modal_close_fn=page.close_modal,
        )
        # 결과: 신규 감지 카드 + yaml 명세 UI 패턴 자동 검증 카드만
```

수동 메서드는 `test_scenario3_add.py` 의 `sc3a~sc3o` 같이 직접 작성:
```python
def test_scenario3a_required_empty_messages(self, logged_in_page, settings):
    # 필수 빈값 5건 + 발화순서 검증 (수동)
    for case_id, label, fill_args, expected in cases:
        page.open_add_modal()
        _fill(**fill_args)
        _save_click(page)
        ...
        self._add("pass" if msg == expected else "fail", ...)
```

---

## 2) 적용 페이지 현황 (코드 사실)

| 페이지 | 방식 | yaml | scan 호출 test | 시나리오 메서드 |
|--------|------|------|---------------|----------------|
| RansomCruncher 탐지정책 | **A — modal_form** | `ransom_detect_policy.yaml` (truth) | `tests/archive/test_ransom_detect_policy_scan.py` | 단일 메서드 phase 1+2+3 |
| RDP 정책 | **A — modal_form** | `rdp_policy.yaml` (truth) | `tests/archive/test_rdp_policy_scan.py` | 단일 메서드 |
| **제어스위트** | **B — list_page + sc0** | `control_suite.yaml` (참조) | `tests/control_suite/test_scenario0_scan.py` (sc0 만) | sc1~sc6 수동 (50+ 메서드) |
| **원본보호 정책** | **B — list_page + sc0** | `npouch_origin_protect_policy.yaml` (참조) | `tests/origin_protect/test_scenario0_scan.py` (sc0 만) | sc1~sc3o 수동 (20+ 메서드) |
| InnoMark 정책/템플릿 | (미통합) | `inno_mark_*.yaml` | 없음 | 없음 |

> **`scan_mode` 표기 (yaml header)**: A 방식 = `scan_mode: modal_form` / B 방식 = `scan_mode: list_page` 또는 `modal_form` (혼재).

---

## 3) 새 페이지 추가 시 결정 가이드

### A 방식 선택 기준
- 페이지가 **단일 모달** 중심 (ADD/EDIT) — 모달 안 input/checkbox/radio 검증이 회귀의 본질
- 시나리오 간 의존 적음 (각 phase 가 독립적)
- yaml 명세에 모든 요소 정확히 등록 가능 (text_inputs, toggle_checkboxes, radio_groups, tag_input)
- 빠른 자동 검증 우선 — 신규 페이지 → yaml 작성 → 메서드 작성 거의 0

### B 방식 선택 기준
- 페이지가 **다단 모달** 중심 — main_modal → sub_modal → picker 같은 3+ 단계 흐름
- **시나리오 간 의존**이 본질 (예: sc3 의 [AUTO] 정책 → sc4 EDIT 진입 → sc5 lifecycle)
- 도메인 사실이 복잡 (toggle 종속 / 다중구분자 / 단방향 sync 결함 등) — UIScanner 자동 규칙으로 cover 불가
- 정밀한 메시지/순서 검증 필요 (필수 입력 5건 발화 순서 등)

### 모호한 경우 (둘 다 가능)
- B 방식 + sc0 (UIScanner) 통합 — 자동 발견 + 수동 깊이 둘 다 확보
- 단점: sc0 와 sc1~6 사이 중복 검증 가능성 (보고서 dedup 점검 필요)

---

## 4) 방식별 신규 기능 감지 동작

### A 방식 (modal_form)
- phase=2 가 시나리오 1 (yaml↔DOM diff) + 시나리오 2 (UI 요소 동작) 자동
- 신규 요소 발견 시 시나리오 1 카드 + DOM 속성 자동 dump
- yaml 에 등록 후 다음 run 부터 시나리오 2 자동 검증 진입

### B 방식 (list_page + sc0)
- sc0 호출만으로 신규 발견 카드 + 자동 검증 결과 노출
- **신규 발견 카드 detail 안에 다음 4가지 자동 표시 (2026-05-29 적용)**:
  1. DOM 속성 dump (type / maxlength / has_toggle / checked)
  2. **휴리스틱 검증 결과** (text → maxlength=null warn / checkbox → click 토글 / radio → name 그룹 옵션 수)
  3. **yaml stub 한 줄 자동 제안** — 검수자 복붙용
  4. 모달 영역 스크린샷

코드 인용 (`core/ui_scanner.py:_run_heuristic_test` + `_build_yaml_stub`):
```python
def _run_heuristic_test(page, selector, attrs, label):
    t = attrs.get("type", "")
    if t in ("text", "password", "email", "url", "tel", "textarea"):
        ml = attrs.get("maxlength")
        if ml is None:
            return ("warn", "휴리스틱: 클라 길이 가드 부재 ...")
    if t == "checkbox":
        # click ON↔OFF→복구 (원상복구, 데이터 변경 X)
        ...
```

---

## 5) Sub-numbering 규칙 (방식 B 전용)

방식 B 의 `tests/{control_suite,origin_protect}/_base.py` 에 sub-num 자동 매핑 적용:
- 메서드 이름 `test_scenarioNX_...` → sc = `N*100 + sub_idx` (a=1, b=2, ..., z=26)
- 예: `sc3a` → 301, `sc3o` → 315, `sc1a` → 101
- **sn=0 (sc0 시리즈) 은 skip** — sub-num = sub 자체가 되어 다른 시나리오 parent sc 와 충돌

코드 인용 (`tests/control_suite/_base.py:_add`):
```python
if sn != 0 and sc in (0, sn):
    sc = sn * 100 + sub  # sc3a → 301 etc.
```

### 라벨 등록 — 누락 시 보고서에 raw num "313" 노출됨
`core/html_reporter.py:_SCENARIO_LABELS_BY_PAGE` 에 page_id 별 라벨 dict — sub-num 마다 한 줄 등록 필수:
```python
"npouch_origin_protect": {
    313: "시나리오 3m: 출력 워터마크 토큰 동작",
    314: "시나리오 3n: 텍스트 길이 클라 가드 부재",
    315: "시나리오 3o: 토글 종속 disabled",
}
```
**미등록 sub-num 은 fallback "시나리오 3.13" 식으로 표시** (`_format_num_pretty`) — raw "313" 노출 안 됨.

> 새 sc 메서드 추가 시 반드시 `_SCENARIO_LABELS_BY_PAGE` 에 라벨 한 줄 추가.

---

## 6) 캡처에 이슈 위치 강조 (highlight) — 방식 B 적용

이슈 발생 위치를 캡처에 시각적으로 표시. `_ss(page, label, highlight=Locator)` 호출 시 해당 요소에 **빨간 outline (3px solid #ff2d2d) + 그림자** 임시 주입 → scroll_into_view → screenshot → outline 제거.

### `_add()` 호출에서 highlight 넘기는 방식
```python
self._add("warn" if cleared_pc is True else "pass",
          "sc3k — [화면 워터마크] 단방향 sync 결함",
          f"결과: text='', pc.checked={cleared_pc}",
          sc=3, highlight=page.page.locator(page.SEL_SCREEN_WM_PC_INFO))
```

코드 인용 (`tests/origin_protect/_base.py:_ss`):
```python
if highlight is not None:
    highlight.first.scroll_into_view_if_needed(timeout=1000)
    highlight.first.evaluate(
        "el => { el.style.outline='3px solid #ff2d2d';"
        " el.style.outlineOffset='2px';"
        " el.style.boxShadow='0 0 0 6px rgba(255,45,45,0.25)'; }"
    )
    injected = True
page.screenshot(path=str(path))
if injected:
    # outline 제거 — 다른 검증에 영향 없도록
    highlight.first.evaluate("el => { el.style.outline=''; el.style.boxShadow=''; }")
```

### 적용 가이드
- **fail/warn 단계의 _add() 호출** 에 가능하면 `highlight=loc` 추가 — 보고서 캡처가 어느 요소인지 명확.
- 동일 검증 안 여러 검증 줄은 각자 다른 locator 강조 가능 (예: sc3k 의 text/PC체크박스 분리).
- `_ss` 의 highlight 파라미터는 optional — 기존 호출부 안 깨짐, 점진 적용 가능.
- 라벨에 `[화면 워터마크]` 같은 영역명 prefix 같이 쓰면 더 명확 (사용자 요구 패턴).

---

## 6.5) Crash 시점 page_id 미리 attach (방식 B 필수)

`_add()` 호출 전 예외로 abort 되면 conftest 의 `pytest_runtest_makereport` hook 이 page_id 못 찾아 status="error" ScanResult 등록 실패 → 보고서 "실행 오류" 카운트 0 으로 누락 (사용자 지적 2026-05-29 RESOLVED).

방식 B `_base.py:_setup` fixture 는 yield 전에 반드시:
```python
request.node._npouch_page_id = self.PAGE_ID
```

이 한 줄로 어느 시점 crash 라도 보고서에 error 정상 등록.

---

## 6.6) 시나리오 6 정의 + AUTO 검색 정책 (방식 B 전용 — 사용자 정책 2026-05-29)

### 시나리오 6 = 페이지 lifecycle 종료 + 다음 단계 연계

| 케이스 | 형태 | 동작 |
|--------|------|------|
| **단일 페이지 테스트** | `sc6X` (sub-num — sc6a/sc6b 등) | 페이지 내 마지막 정리 (zz_cleanup 유사) |
| **여러 페이지 통합 테스트** | `sc6` (parent) | `[AUTO_KEEP]_` 정책을 다음 페이지로 연계 |

**cleanup 흐름 (방식 B 공통):**
- **sc1 시작**: `delete_all_test_data()` — `[AUTO]_` + `[AUTO_KEEP]_` 둘 다 cleanup (clean slate)
- **sc2/3/4**: cleanup 없음 (이전 시나리오 정책 재사용)
- **sc5 끝 (5c)**: `delete_all_auto_policies()` — `[AUTO]_` 만 cleanup, `[AUTO_KEEP]_` 보존 (lifecycle 종료 + 다음 연계)
- **sc6**: `[AUTO_KEEP]_` 활용 또는 단일 페이지 마무리 정리

### AUTO 검색 정책 (CSU/process/tag picker 공통)

picker (다른 페이지의 정책/프로세스 선택) 호출 시 **3단계 fallback chain**:

```
1) AUTO 검색 시도 → 결과 있으면 매칭 첫 행 (KEEP 정책 우선 — sc6 연계 의도)
2) AUTO 결과 0건 → 검색 reset → 전체 list 첫 행 (sc6 미실행 / sc1 cleanup 후 정상 fallback)
3) 전체 list 도 비어있음 (rare) → picker close (막히는 현상 방지)
```

**핵심**: 사용자 명시 (2026-05-29) "**AUTO 없으면 자동으로 맨위 유동적 사용 — 막히는 현상 방지**".

### 적용 helper 패턴 (코드 인용)

`tests/origin_protect/test_scenario3_add.py:_csu_select_first` (line 20-):
```python
def _csu_select_first(page, prefer_keyword="AUTO"):
    """CSU picker 선택 — AUTO 검색 → 매칭 첫 행 / 없으면 전체 list 첫 행."""
    page.page.locator(page.SEL_CSU_SELECT_BTN).first.evaluate("el => el.click()")
    page.page.locator("#selectCommonPolicyItemModal.in").wait_for(state="attached", timeout=5000)
    # ① AUTO 검색 시도
    try:
        si = page.page.locator("#selectCommonPolicyItemModal input#searchText").first
        si.fill(prefer_keyword)
        page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(800)
    except Exception:
        pass
    # ② radio 0건 → 검색 reset → 전체 list 첫 행
    radios = page.page.locator("#selectCommonPolicyItemModal input[type='radio'][name='selectTemplate']")
    if radios.count() == 0:
        si.fill("")
        page.page.locator("#selectCommonPolicyItemModal button.searchBtn").first.evaluate("el => el.click()")
        page.page.wait_for_timeout(800)
    # ③ valid_rows 확인 — 비어있으면 close 안전 종료
    valid_rows = page.page.locator(
        "#selectCommonPolicyItemModal table tbody tr:has(input[type='radio'][name='selectTemplate'])"
    )
    if valid_rows.count() > 0:
        valid_rows.first.evaluate("el => el.click()")  # raw JS click — ng-click directive 발화
        page.page.wait_for_timeout(500)
        page.page.locator("#selectCommonPolicyItemModal .btn-primary").first.evaluate("el => el.click()")
    else:
        # rare — list 자체 비어있음, picker close
        page.page.locator("#selectCommonPolicyItemModal button.close, ...[data-dismiss='modal']").first.evaluate("el => el.click()")
```

같은 패턴이 `_pick_process_in_picker` (`test_scenario4_modify.py:90`) 에도 적용 — process picker (multi-select 체크박스) 의 AUTO 검색 + fallback.

### 새 페이지 추가 시 picker helper 작성 규칙

새 페이지에 picker 추가 (예: 태그 picker, special folder picker) 시:

1. **prefer_keyword 인자 default "AUTO"** — 호출부 변경 없이 정책 적용
2. **3단계 fallback 명시**:
   - 검색 시도 → 결과 있으면 사용
   - 결과 0건 → 검색 reset
   - 전체 비어있음 → 안전 종료 (close)
3. **AngularJS ng-click 발화 보장** — raw JS `el.click()` (Playwright trusted `force=True click` 보다 안정)
4. **timeout 명시** — picker `.in` 클래스 attached wait (5초)

### 사용자 보고 — 적용 누락 경고

사용자 명시 (2026-05-29): "**지금 AUTO 만들고 안 쓰고 있는 곳 있는 거 같아서**" — 새 picker helper 추가 시 위 규칙 위반 자주 발생.

체크리스트 (각 picker helper 점검):
- [ ] prefer_keyword 인자 + AUTO default
- [ ] 검색 0건 시 검색 reset 단계 포함
- [ ] 전체 비어있음 시 close 안전 종료
- [ ] AngularJS ng-click 발화 (raw JS click)

---

## 7) 작업 진입 전 체크리스트

새 페이지 추가:
- [ ] 페이지가 A vs B 어느 방식이 적합한지 3절 가이드로 판정
- [ ] yaml `page_id` / `modal_id` / `scan_mode` 헤더 작성
- [ ] A 방식: 단일 메서드 + phase 1/2/3 호출 작성
- [ ] B 방식: sc0 (UIScanner 호출) + sc1~6 수동 메서드 + `_base.py` 신규 (PAGE_ID 미리 attach 포함) + `_SCENARIO_LABELS_BY_PAGE` 에 라벨 dict 추가
- [ ] yaml syntax 통과: `python -c "import yaml; yaml.safe_load(open('config/scan_hints/X.yaml'))"`

기존 페이지 확장:
- [ ] 같은 페이지의 기존 방식 따라간다 (혼합 금지)
- [ ] sc0 (방식 B) 신규 발견 시 → yaml 정식 등록 vs ignored 결정
- [ ] **새 sc 메서드 추가 시 `_SCENARIO_LABELS_BY_PAGE` 에 라벨 한 줄 추가** (누락 시 보고서 raw num 노출)
- [ ] **fail/warn 검증의 `_add()` 호출에 `highlight=loc` 추가 가능 여부 점검**
- [ ] 중복 검증 점검 — sc0 자동 ↔ sc1~6 수동 중복 시 dedup
- [ ] **`_base.py:_setup` 에서 PAGE_ID 미리 attach 확인** (crash 시 error 등록 보장)

새 picker helper 작성 (6.6절 정책 적용):
- [ ] **prefer_keyword="AUTO" default 인자** — 호출부 변경 없이 정책 적용
- [ ] **3단계 fallback** — AUTO 검색 → 0건 시 검색 reset → 전체 비어있음 시 close 안전 종료
- [ ] **AngularJS ng-click 발화** — raw JS `el.click()` (Playwright trusted click 대신)
- [ ] picker `.in` 클래스 attached wait 5초 timeout

cleanup 호출 위치 (방식 B 라이프사이클):
- [ ] **sc1 시작**: `delete_all_test_data()` (AUTO + KEEP 둘 다)
- [ ] **sc2/3/4**: cleanup 호출 X (정책 재사용)
- [ ] **sc5c (lifecycle 종료)**: `delete_all_auto_policies()` (AUTO 만, KEEP 보존)
- [ ] **sc6**: 단일 페이지면 sc6X / 통합이면 KEEP 활용

---

## 8) 관련 문서

- `docs/architecture.md` — 페이지/테스트 디렉토리 구조 + 모듈 책임
- `docs/test-pipeline.md` — 새 test 파일 추가 시 conftest/html_reporter 파이프라인
- `docs/scan-output-format.md` — modal_form 전용 scan 출력 형식 (A 방식)
- `docs/scenario_N_*.md` — 방식 B 의 각 시나리오 상세 (1~6)
- `docs/TROUBLESHOOTING.md` — yaml 구문 위반 / B-1 시리즈 list_page 확장 등 이슈 history
