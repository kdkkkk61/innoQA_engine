# ENVIRONMENT.md — inno_test_tool 현재 상태

> 코드 직접 확인 기반. 추측 없음. 코드에 명시되지 않은 항목은 "확인 필요"로 표시.
> 작성일: 2026-05-06 (커밋 bc3b1e1 기준)

---

## 1. 코드 구조

### 1.1 폴더 구조 (Python 코드 기준)

```
inno_test_tool/
├── app.py                       # PyWebView + Flask 앱 진입점
├── conftest.py                  # pytest 루트 conftest
├── server_app.py                # 별도 Flask 앱 (확인 필요 — 본 분석 범위 아님)
├── core/
│   ├── __init__.py
│   ├── html_reporter.py         # HTML 리포트 생성
│   ├── innorelease_client.py    # innoRelease 서버 연동 클라이언트
│   ├── list_page_runner.py      # list_page scan_mode 통합 러너
│   ├── models.py                # ScanResult, PageScanReport 데이터 클래스
│   ├── qa_runner.py             # 페이지별 스캔 디스패처 (modal_form / list_page)
│   ├── report_parser.py         # (확인 필요 — 본 분석 범위 아님)
│   ├── reporter.py              # 콘솔 출력 (print_phase_report, print_combined_report)
│   ├── scan_context.py          # ScanContext (page, log, known_bugs 보유)
│   ├── scanner.py               # (확인 필요 — 본 분석 범위 아님)
│   └── ui_scanner.py            # UIScanner (modal_form scan_mode 검증 호출)
├── validators/
│   ├── __init__.py
│   ├── button_action.py
│   ├── initial_state.py         # 필드 초기값 검증 + 저장값 로드 검증
│   ├── list_ui.py               # list_page UI 검증 (탭/검색/버튼/테이블)
│   ├── overflow.py              # 글자수 제한 검증
│   ├── plain_checkbox.py
│   ├── radio_group.py
│   ├── required_submit.py       # 필수 미입력 검증 + 시나리오 4-3
│   ├── tag_input.py
│   ├── text_input.py
│   └── toggle_checkbox.py
├── pages/
│   ├── base_page.py             # BasePage 공통 메서드
│   ├── login_page.py
│   ├── registry.py              # PAGE_REGISTRY (page_id → PageClass), MODULE_GROUPS
│   ├── ransom_detect_policy_page.py
│   ├── rdp_policy_page.py
│   ├── common_process_page.py
│   ├── npouch_operation_process_page.py
│   ├── npouch_tag_page.py
│   ├── npouch_control_suite_page.py
│   ├── npouch_origin_protect_policy_page.py
│   └── npouch_policy_page.py
├── tests/
│   ├── conftest.py
│   ├── test_login.py
│   ├── test_scan_pages.py       # 범용 (ransom_cruncher 모듈)
│   ├── test_npouch.py           # 운용 프로세스
│   ├── test_npouch_tag.py
│   ├── test_control_suite.py
│   ├── test_ransom_detect_policy.py
│   ├── test_ui_scan.py
│   └── archive/                 # 보관용
├── utils/
│   └── scan_logger.py
├── dashboard/
│   ├── __init__.py
│   ├── db.py
│   └── routes.py                # Flask Blueprint (/dashboard 경로)
├── config/
│   ├── settings.yaml            # 앱 전역 설정 (base_url, browser, innorelease 등)
│   ├── known_bugs.yaml
│   ├── scan_hints/{page_id}.yaml × 9개  # 페이지별 검증 힌트
│   ├── agent_maps/              # (확인 필요)
│   └── test_profiles/           # (확인 필요)
├── templates/
│   ├── app/                     # 앱 UI 템플릿 (index, run_setup, progress, report 등)
│   └── dashboard/               # 대시보드 UI 템플릿
├── static/images/               # 정적 자산
├── docs/                        # 시나리오 정의 + 운영 문서
├── md_list/                     # 작업 노트
├── scripts/extract_bug_cases.py # 보고서 BUG 추출 헬퍼
├── reports/                     # 실행 결과 출력 (gitignore)
├── logs/                        # app.py 로그 (gitignore)
├── data/qa.db, qa_test.db       # SQLite (gitignore)
├── build/
│   ├── build_all.bat
│   ├── launcher.py              # PyInstaller 진입점
│   ├── qatool.spec              # PyInstaller spec
│   └── qatool_setup.iss         # Inno Setup 인스톨러
├── requirements.txt
├── pytest.ini
├── CLAUDE.md
├── .gitignore
└── .claude/settings.json
```

### 1.2 파일 간 import 관계 (실제 코드 grep 결과)

**진입점 → 분기 (app.py)**:
- `app.py`가 직접 import 하는 모듈: `flask`, `subprocess`, `dashboard` (try/except optional)
- `app.py`는 pytest를 subprocess로 호출 — 직접 코드를 import 하지 않음.

**pytest 흐름 (test_scan_pages.py 기준)**:
```
test_scan_pages.py
  ├─ from core.qa_runner import run_scan
  └─ from pages.registry import PAGE_REGISTRY, MODULE_GROUPS
```

**core/qa_runner.py imports**:
```python
from core.ui_scanner        import UIScanner
from core.models            import PageScanReport, ScanResult
from core.reporter          import print_phase_report, print_combined_report
from pages.registry         import PAGE_REGISTRY
from validators.overflow    import scan_overflow_tests
from validators.list_ui     import scan_list_ui
```

**core/ui_scanner.py imports**:
```python
from playwright.sync_api import Page
from utils.scan_logger import make_scan_logger
from core.models import ScanResult, PageScanReport
from core.scan_context import ScanContext
from validators.initial_state   import scan_initial_state, scan_loaded_values
from validators.toggle_checkbox import scan_toggle_checkboxes
from validators.plain_checkbox  import scan_plain_checkboxes
from validators.radio_group     import scan_radio_groups
from validators.text_input      import scan_text_inputs
from validators.tag_input       import scan_tag_inputs
from validators.required_submit import scan_required_submit
from validators.button_action   import scan_button_actions
```

**core/list_page_runner.py imports**:
```python
from core.models import ScanResult, PageScanReport
from core.reporter import print_combined_report
from validators.list_ui import scan_list_ui
```

→ list_page는 자체 인라인 검증 위주. validators 외부 호출은 list_ui 1개.

---

## 2. 진입점과 실행 흐름

### 2.1 실행 명령

**개발 실행** (`app.py:1` 주석 명시):
```
python app.py
```

**EXE 실행** (`build/launcher.py:6` 명시):
```
qatool.exe   # launcher → 같은 폴더의 python\python.exe로 app.py 실행
```

**pytest 직접 실행** (`tests/test_scan_pages.py:13~17`):
```
pytest tests/test_scan_pages.py -v -s                      # 전체
pytest tests/test_scan_pages.py -v -s -m ransom_cruncher   # 모듈 필터
pytest tests/test_scan_pages.py -v -s -k common_process    # 페이지 필터
```

### 2.2 호출 순서 (`python app.py` 기준)

1. **`app.py:1~30`**: Flask + PyWebView import, BASE_DIR 결정
2. **`app.py:115~119`**: dashboard Blueprint 등록 (있을 경우)
3. **`app.py:276`** `@app.route("/")`: 제품 선택 화면 — `index.html`
4. **`app.py:284`** `@app.route("/test-type")`: 테스트(페이지) 선택 — `test_type.html`
5. **`app.py:294`** `@app.route("/run-setup")`: ID/PW + 옵션 입력 — `run_setup.html`
6. **`app.py:326`** `@app.route("/start", methods=["POST"])`: 실행
   - 6.1 `target_url` 입력 시 `config/settings.yaml` 의 `base_url` 즉시 갱신 (`app.py:339~351`)
   - 6.2 `_state` 초기화 (status, page_status, scenario_status)
   - 6.3 pytest 명령 구성 (`app.py:402~420`):
     - 환경변수: `TEST_ID`, `TEST_PW`, `TEST_HEADLESS`, `PLAYWRIGHT_BROWSERS_PATH`, `UV_USE_IO_RINGS`
     - 명령: `python -u -m pytest {test_files} -v -s --timeout=180 -k {filter}`
   - 6.4 `subprocess.Popen` 으로 pytest 실행 (`app.py:435~455`)
   - 6.5 stdout 한 줄씩 읽으며 `_state["live_log"]` / `page_status` / `scenario_status` 갱신
7. **`app.py:708`** `@app.route("/progress")`: 진행 화면 — `progress.html`
8. **`app.py:714`** `@app.route("/status")`: `_state` JSON 반환
9. **`app.py:784`** `@app.route("/report")`: 1차 리포트 편집 화면 — `report.html`
10. **`app.py:790`** `@app.route("/report-data")`: `last_report.json` 반환
11. **`app.py:865`** `@app.route("/finalize", methods=["POST"])`: 편집 결과 반영 → 최종 HTML 덮어쓰기

### 2.3 pytest 내부 흐름 (`run_scan` 호출)

`tests/test_scan_pages.py:42~54` (`test_page_scan`):
1. `logged_in_page` fixture (conftest 정의) — Playwright Page 로그인 완료 상태
2. `run_scan(logged_in_page, settings, page_id)` 호출 (`core/qa_runner.py:263`)
3. `core/qa_runner.py:284` — `scan_hints/{page_id}.yaml` 로드 → `scan_mode` 분기
   - `scan_mode == "list_page"` → `run_list_page_scan` (`core/qa_runner.py:336`)
     - `PAGE_REGISTRY[page_id]` 인스턴스화 → `navigate_to()` → `delete_all_auto_items()`
     - `ListPageRunner(playwright_page, page_obj, hints).run()` 호출
   - 그 외 (modal_form 기본) → `run_3phase_scan` (`core/qa_runner.py:384`)
     - phase 1/2/3 + 시나리오 3 오버플로 + 시나리오 4 (UIScanner.scan(phase=4))
     - phase 4: `scanner.scan(phase=4, modal_open_fn=..., modal_close_fn=...)` (`core/qa_runner.py:519`)
4. `request.node._scan_report = combined` (conftest로 전달)
5. `combined.errors` 가 있으면 pytest fail (도구 오류만)

### 2.4 데이터 흐름

| 단계 | 생성 | 소비 |
|---|---|---|
| 1. yaml 로드 | `hints: dict` (qa_runner.py:280) | scanner / runner |
| 2. ScanContext 생성 | `ctx` (ui_scanner.py:102) | 모든 validator |
| 3. validator 실행 | `ScanResult` × N | `report.results` 누적 |
| 4. PageScanReport 반환 | report (`core/models.py:44`) | `request.node._scan_report` |
| 5. conftest 수집 | `combined: PageScanReport` | `core/html_reporter.py` |
| 6. HTML 생성 | `reports/{product}/QA_{...}.html` + `last_report.json` | `app.py:/report-data` |

---

## 3. 입력

### 3.1 설정 파일

**`config/settings.yaml`** (`conftest.py:323~327` 로드):
```yaml
base_url: "http://innotium.iptime.org:14180/"
product_name: "RansomCruncher"
qa_server_url: "http://192.168.13.55:8080"
innorelease:
  url: "http://192.168.13.55:8090"
  username: "admin"
  password: "zxcvb1234"
browser:
  headless: false
  slow_mo: 0
  timeout: 30000
selectors:
  login:
    username_input: "input#memberId"
    password_input: "input#password"
    submit_button:  "input#loginBtn"
```

**`config/scan_hints/{page_id}.yaml`** × 9개 — 페이지별 검증 힌트
- 파일명 = `page_id` (PAGE_REGISTRY 키와 일치)
- 최상위 키: `scan_mode` (`modal_form` 기본 / `list_page`), `nav`, `tabs`, `fields`, `modal_actions`, `required_submit_sequence`, `overflow_tests`, `crud`, 등
- 페이지별 스키마는 검증 패턴에 따라 다름 (단일 통합 스키마 없음).

**`config/known_bugs.yaml`** — 알려진 버그 매핑
- 키: `selector`, `pattern`, `test_name`, `reason`, `reported_date`, `ticket`, `page_id`, `status` (open/fixed/wont_fix)
- `core/scan_context.py:153` `is_known_bug(selector, test_name)` 에서 매칭

**`config/agent_maps/`, `config/test_profiles/`** — 본 분석 범위 외 (확인 필요)

### 3.2 환경 변수 (`grep "os.environ"` 결과)

| 변수 | 사용처 | 의미 |
|---|---|---|
| `TEST_ID` | `conftest.py:204`, `app.py:407` | 로그인 ID (subprocess로 전달) |
| `TEST_PW` | `conftest.py:205`, `conftest.py:461`, `app.py:408` | 로그인 PW |
| `TEST_HEADLESS` | `conftest.py:356`, `app.py:409` | "1" / "0" — Playwright headless 강제 |
| `QA_SERVER_URL` | `app.py:674` | 결과 업로드 서버 URL (없으면 업로드 X) |
| `PLAYWRIGHT_BROWSERS_PATH` | `app.py:410` (`_get_browsers_env`) | 설치 폴더 browsers/ 있으면 자동 설정 |
| `UV_USE_IO_RINGS` | `app.py:411` (`"0"` 고정) | Windows libuv assertion 회피 (Chromium 크래시 방지) |
| `PYTHONUNBUFFERED` | `app.py:421` (`"1"` 고정) | pytest 출력 즉시 flush |

### 3.3 명령줄 인자

- `app.py`: 코드 내 `argparse` 등 인자 처리 없음 (확인: `app.py` 상단 `import` 목록에 argparse 없음).
- `pytest`: 표준 pytest 인자 + `pytest.ini` 정의 마커 (`ui_scan`, `ransom_cruncher`, `inno_mark`, `unclassified`, `npouch`).

### 3.4 사용자 입력 (앱 UI)

- 제품 선택 (`/test-type` POST data: `product_id`)
- 페이지 선택 (`/run-setup` POST data: `page_ids`)
- ID/PW + headless 토글 + target_url (`/start` POST data: `test_id`, `test_pw`, `headless`, `target_url`, `page_ids`)

---

## 4. 출력

### 4.1 생성 파일

| 경로 | 형식 | 생성 위치 |
|---|---|---|
| `reports/{product}/QA_{product}_{YYYYMMDD}_{HHMM}.html` | HTML | `core/html_reporter.py` (`out_path.write_text` line 550) |
| `reports/{product}/last_report.json` | JSON | `core/html_reporter.py:589` (`last_json.write_text`) |
| `reports/last_report.json` | JSON | `core/html_reporter.py:593` (루트 폴백, `app.py:/report-data` 우선 탐색) |
| `reports/screenshots/*.png` | PNG | `validators/*` 의 `_take_screenshot` 또는 `ScanContext.take_screenshot` |
| `reports/runs/*.log` | TEXT | pytest stdout 캡처 (`app.py:434` `_LOG_FILE`) |
| `logs/app_*.log` | TEXT | app.py 자체 로그 (gitignore) |

### 4.2 `last_report.json` 실제 구조 (직접 파싱)

**최상위 키**:
```json
{
  "generated_at": "2026-04-30T09:13:47.042783",
  "html_path":    "C:\\...\\reports\\RansomCruncher\\QA_RansomCruncher_20260430_0913.html",
  "pages":        [...]
}
```

**`pages[i]` 키**:
```json
{
  "page_id":   "common_process",
  "label":     "공통 프로세스",
  "is_list":   true,
  "results":   [...]
}
```

**`results[j]` 키** (= `ScanResult` 직렬화, `core/html_reporter.py:570~579`):
```json
{
  "phase":        4,
  "order":        9999,
  "pattern":      "list_modal_overflow",
  "label":        "글자수 제한 누락 — 프로세스 명 (500자)",
  "status":       "warn",
  "detail":       "클라이언트 검증 없어 서버 오류 발생: '서버에서 오류가 발생 하였습니다.'",
  "screenshot":   "reports/screenshots/BUG_xxx.png",
  "scenario":     2,
  "scenario_tag": "시나리오 2"
}
```

### 4.3 사용자 최종 산출물

**앱 UI 흐름** (`app.py` route 기반):
1. 진행 화면 (`progress.html`) — 실시간 page_status / scenario_status
2. 1차 리포트 편집 화면 (`report.html`) — `/report-data` API로 `last_report.json` 표시
3. 결함 카드별 "맞음/아님" + 의견 입력 → `/finalize` POST
4. 최종 HTML — `reports/{product}/QA_*.html` (다운로드 또는 외부 브라우저 오픈)

---

## 5. 외부 의존성

### 5.1 Python 패키지 (`requirements.txt`)

```
pytest==8.3.4
pytest-playwright==0.6.2
pytest-html==4.1.1
pytest-timeout==2.3.1
PyYAML==6.0.2
flask>=3.1.0
pywebview>=6.1
requests>=2.31.0
beautifulsoup4>=4.12.0
```

### 5.2 PyInstaller 설정 (`build/qatool.spec`)

- 진입 스크립트: `launcher.py`
- 출력: `qatool.exe` (단일 EXE, `--onefile` 추정 — qatool.spec EXE 정의에 datas/binaries 있음)
- `console=False` (확인 필요 — spec 후반부 미확인)
- launcher 동작 (`build/launcher.py:1~30`):
  1. `INSTALL_DIR = Path(sys.executable).parent`
  2. `python\python.exe` 와 `app.py` 가 같은 폴더에 있다고 가정
  3. `subprocess`로 그 Python으로 app.py 실행

### 5.3 빌드 파이프라인 (`build/build_all.bat`)

3단계 (배치 파일 헤더 명시):
1. Python 3.12 embedded 셋업 (`python-3.12.2-embed-amd64.zip` 사용)
2. PyInstaller로 `qatool.exe` (launcher) 빌드
3. Inno Setup으로 `qatool_setup.exe` 인스톨러 빌드 (`build/qatool_setup.iss`)

### 5.4 실행 환경 요구사항

- **OS**: Windows (코드 명시)
  - `app.py:411` `UV_USE_IO_RINGS=0` — Windows 한정
  - `app.py:436~440` `subprocess.STARTUPINFO()` + `STARTF_USESHOWWINDOW` + `SW_HIDE` — Windows 한정
  - `build/launcher.py:14` `ctypes.windll.user32.MessageBoxW` — Windows 한정
- **Python**: 3.12 (embedded zip 명시: `python-3.12.2-embed-amd64.zip`)
- **외부 서버 연결**:
  - 매니저 페이지 — `settings.yaml` `base_url` 또는 `target_url` 입력값
  - innoRelease — `settings.yaml` `innorelease.url` (있을 경우)
  - QA 서버 — `settings.yaml` `qa_server_url` (있을 경우)
- **계정**: 매 실행 시 터미널 입력 또는 `TEST_ID`/`TEST_PW` 환경변수
  - `conftest.py:185~230` `pytest_configure` 에서 `getpass`로 입력 또는 환경변수 사용

---

## 확인 필요 항목

- `core/scanner.py` — import 그래프에 안 잡힘. 사용 여부 확인 필요.
- `core/report_parser.py` — 동일.
- `server_app.py` — 별도 Flask 앱. 본 분석 범위 외.
- `config/agent_maps/`, `config/test_profiles/` — 디렉토리 구조만 확인. 내용 미파악.
- `qatool.spec` 의 `console=` 옵션 등 후반부 — 미확인.
- `dashboard/db.py`, `dashboard/routes.py` — 사용 여부는 `app.py:115~119` try/except optional 처리됨.
