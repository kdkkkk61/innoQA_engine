# 시나리오 0 — UIScanner DOM 스캔 (yaml ↔ 실제 DOM diff)

> [기본 경로] sc0 = 회귀 감지 본질. yaml(baseline 명세) 과 실제 DOM 을 비교해
> **추가/삭제/숨김** 을 자동 감지한다. sc1~6(수동 시나리오)의 앞단.
> 근거 코드: `core/ui_scanner.py`(scan), `core/scan_diff.py`(extract_yaml_selectors / discovered_*),
> 검증된 레퍼런스: `tests/npouch_policy/test_scenario0_scan.py` (실환경 192.168.13.141 실행 검증).
> 방식 선택(A modal_form / B list_page)은 `docs/scan-architecture.md` 참조 — 본 문서는 sc0 시나리오 자체.

---

## 1. 목적

sc0 은 **화면을 사람이 다시 확인하지 않아도 "명세(yaml) 대비 UI 가 바뀌었는지"** 를 매 실행 잡아낸다.
- baseline = yaml 스키마(그 페이지에서 존재해야 할 요소들의 selector).
- 실제 DOM = 모달을 열어 UIScanner 가 추출한 요소(입력/선택 요소).
- 둘을 diff → 사람이 읽는 변경사항 카드.

`scanner.scan(page_id=..., phase=2, modal_open_fn=..., modal_close_fn=...)` 형태.
phase=2 = ADD 모달 열고 yaml↔DOM diff (저장 안 함). 모달 여러 개면 스캔 여러 개(yaml 파일 분리).

---

## 2. 3종 변경 감지 (코드 인용: `npouch_policy/test_scenario0_scan.py`)

| 종류 | pattern | 의미 |
|------|---------|------|
| **추가** | `discovered_new` | DOM 에만 존재 (yaml 미정의) — 신규 기능/요소 |
| **삭제** | `discovered_missing` | yaml 에만 존재, DOM 미발견 — 기능 삭제(회귀) |
| **숨김** | `discovered_hidden` | yaml+DOM 둘 다 있으나 `display:none` — 있는데 안 보임 (`detect_hidden: true` 켠 yaml) |

- 하나라도 있으면 요약 카드 = **warn** (변경사항 있음), 없으면 pass.
- 종류별 개별 카드(`변경사항(추가/삭제/숨김) — 기능명`)로 노출. 스크린샷 없음
  (삭제=요소 없음 / 숨김=display:none → 화면 증거 무의미).

---

## 3. ★스캔 스키마 포함/제외 정책 (이 문서의 핵심)

> "실환경에서 쓰이는 기능인데 **구조상 스캔이 오탐**하는 것"과 "**진짜 삭제/숨김된 회귀**"를
> 구분하는 게 sc0 설계의 핵심. 전자는 스키마에서 **의도적으로 제외**하고, 그 이유를 yaml 주석에 남긴다.

### 3.1 스캔 대상 (yaml 에 넣는 것)
`core/scan_diff.py:extract_yaml_selectors` 가 읽는 키 — **id 있는** 요소만:
`text_inputs` / `radio_groups[].options` / `plain_checkboxes` / `toggle_checkboxes` / `tag_input` / `add_modal.fields`.
DOM 추출도 **id 있는 input/textarea/select** 기준.

### 3.2 제외 vs 등재 — ★핵심 (오해 주의)

**DOM 에 있는 요소를 yaml 에서 빼면 안 된다 → 오히려 `discovered_new`(신규) 오탐이 된다.**
(실수 사례 2026-07-07: 폴더동기화 조건부 필드를 "숨김이니 제외" 했더니 요일 체크박스 등 13개가
`discovered_new` 로 잡힘. DOM 엔 항상 존재하니 yaml 에 없으면 "신규"로 판정.)

| 상황 | 처리 | 왜 |
|------|------|----|
| **DOM 추출이 애초에 못 잡는 것** — contenteditable div / id 없는 요소(name 만 있는 radio) | yaml 에서 **뺀다** (DOM 셋에 없으니 diff 무관) | 넣으면 `discovered_missing` 오탐 |
| **조건부 숨김이지만 DOM 엔 항상 존재** (스케줄 하위필드 executeHour/minutes/days/요일/원본삭제 등) | **등재한다** — 단 `add_modal.fields`(diff 만, UI 검증 미트리거)로 + **`detect_hidden: false`** | 빼면 `discovered_new` / text_inputs 로 넣으면 select '초기값 빈값' 오탐 / detect_hidden 켜면 `discovered_hidden` 노이즈 |
| **항상 노출 + 상호작용 가능** | `text_inputs`/`plain_checkboxes`/`radio_groups` (UI 검증 대상) | 정상 |

→ **조건부 필드의 "어떤 상황에서 노출되는지"(gating 동작)는 sc0 이 아니라 sc1(조건부 노출)·sc2(gating 존재)가 검증.**
  sc0 = 정적 존재 확인. 조건부 노출을 sc0 로 잡으려 하지 말 것(모달은 한 상태 스냅샷만 봄).
→ 등재/제외 판단은 반드시 yaml 주석으로 근거를 남긴다.
→ **select 은 `add_modal.fields` 로** (text_inputs 로 넣으면 '초기값 빈값' 텍스트 검증이 select 기본값에 걸려 fail).

### 3.3 진짜 삭제/숨김(회귀)은 그대로 잡힌다
제외는 "구조상 오탐하는 것"만. **baseline yaml 에 정당히 있던 요소가 실제로 사라지거나 숨겨지면**
`discovered_missing`/`discovered_hidden` 로 warn — 이게 sc0 의 존재 이유. 제외 정책이 회귀 감지를 무력화하면 안 된다.

### 3.4 첫 실행 튜닝 (bootstrapping)
새 페이지 sc0 은 **첫 실행이 튜닝 단계**다. 첫 diff 가 잡은 것을 판정:
- 신규가 진짜 신규 기능 → yaml 에 등재(다음부터 baseline).
- 오탐(위 3.2 사유) → yaml 에서 제외 + 주석.
- 진짜 삭제/숨김 → 제품 회귀로 보고.

---

## 4. 레퍼런스 예시 — nPouch 정책 sc0 (`tests/npouch_policy/test_scenario0_scan.py`)

실환경(192.168.13.141)에서 실제 돌려본 검증된 구현. 신규 페이지 sc0 은 이걸 복제·발전시킨다.

```python
scanner = UIScanner(logged_in_page, config_dir="config")
report = scanner.scan(page_id="npouch_policy", phase=2,
                      modal_open_fn=page.open_add_modal, modal_close_fn=page.close_modal)
# 분류: discovered_new / discovered_missing / discovered_hidden + UI 패턴 fail/warn/pass
# 요약 카드(warn if changed) + 종류별 개별 카드(screenshot=False) + UI 패턴 카드
```

발전형(모달 여러 개): 특수폴더 sc0 = 1단계+내용(바로가기/레지스트리) 3스캔,
폴더동기화 sc0 = 1단계+내용 2스캔 — 각 모달 yaml 파일 분리(`_content` 등 page_id 별도).

---

## 5. 보고 카드 규칙

- 요약 1장(변경 건수 + UI 검증 pass/fail/warn 카운트).
- 변경사항 종류별 개별 카드 — 라벨 `변경사항(추가/삭제/숨김) — 기능명`, 라벨 중복 prefix 제거, `screenshot=False`.
- UI 패턴 fail/warn 개별 카드.
- ※ sc0 은 sub-numbering 안 함(`_attach` 에서 sn=0 skip) — parent sc 와 충돌 방지.

---

## 6. 새 페이지 sc0 추가 절차

1. yaml 스키마 작성 — §3.1 키로 **id 있는 스캔 대상만**, §3.2 는 주석으로 제외 명시.
2. `test_scenario0_scan.py` — nPouch 정책 sc0 복제, `page_id`/`modal_open_fn`/`modal_close_fn` 만 교체.
3. 모달 여러 개면 스캔·yaml 분리(page_id `_content` 등).
4. **첫 실행 = 튜닝**(§3.4). 오탐은 제외+주석, 신규는 등재, 회귀는 보고.

---

## 관련 문서/코드
- `docs/scan-architecture.md` — 방식 A/B 선택, 신규 감지 동작(§4).
- `docs/test_scenario_standard.md` — 시나리오 표준(스캔↔yaml 비교 위치).
- `core/scan_diff.py` `extract_yaml_selectors` / `core/ui_scanner.py` — 구현.
- `tests/npouch_policy/test_scenario0_scan.py` — 검증된 레퍼런스 예시.
