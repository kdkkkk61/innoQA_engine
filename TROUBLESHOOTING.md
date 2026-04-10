# TROUBLESHOOTING — QA Tool 이슈 기록

빌드된 EXE 또는 소스 실행 중 발생한 문제와 해결책 모음.
같은 증상 발생 시 이 파일을 먼저 확인할 것.

---

## 목차

1. [Chromium 크래시 — libuv Windows 타이머 assertion](#1-chromium-크래시--libuv-windows-타이머-assertion)
2. [테스트가 무한 대기 상태로 멈춤](#2-테스트가-무한-대기-상태로-멈춤)
3. [진행 화면 status가 "running"에서 안 바뀜](#3-진행-화면-status가-running에서-안-바뀜)
4. [pytest "ERROR: usage: __main__.py" 즉시 실패](#4-pytest-error-usage-__main__py-즉시-실패)
5. [결함 카드에 스크린샷이 안 보임](#5-결함-카드에-스크린샷이-안-보임)
6. [EXE 실행 시 콘솔 창이 잠깐 번쩍임](#6-exe-실행-시-콘솔-창이-잠깐-번쩍임)
7. [Inno Setup 빌드 오류 모음](#7-inno-setup-빌드-오류-모음)
8. [설치 후 바탕화면 바로가기 생성 실패 (0x80070005)](#8-설치-후-바탕화면-바로가기-생성-실패-0x80070005)
9. [테스트 대상 서버 IP/URL 변경 방법](#9-테스트-대상-서버-ipurl-변경-방법)
10. [base_url URL 형식 변경 시 navigate_to 오류](#10-base_url-url-형식-변경-시-navigate_to-오류)
11. [VM 환경에서 앱 창이 안 뜸 (pywebview 실패)](#11-vm-환경에서-앱-창이-안-뜸-pywebview-실패)
12. [화면 OFF(headless) 모드에서 테스트가 아무것도 안 됨 — CREATE_NO_WINDOW 문제](#12-화면-offheadless-모드에서-테스트가-아무것도-안-됨--create_no_window-문제)

---

## 1. Chromium 크래시 — libuv Windows 타이머 assertion

### 증상
```
Assertion failed: new_time >= loop->time,
file src\win\core.c, line 327
```
Playwright가 Chromium을 띄우자마자 즉시 크래시. Windows 11 26100 이상 / VM 환경에서 재현.

### 원인
Windows 11 고해상도 타이머와 Playwright 내부 libuv의 시간 단조 증가 가정 충돌.
VM 환경에서는 타이머 동기화 문제로 더 자주 발생.

### 해결 (2중 적용)

**1) `app.py` — pytest 서브프로세스 env에 추가:**
```python
env["UV_USE_IO_RINGS"] = "0"
```

**2) `conftest.py` — Chromium 실행 args 추가 (VM 환경 필수):**
```python
_chromium_args = [
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-software-rasterizer",
]
br = playwright_instance.chromium.launch(headless=headless, slow_mo=slow_mo, args=_chromium_args)
```

> `UV_USE_IO_RINGS=0` 만으로 해결되지 않으면 Chromium args 방식이 유효.
> 일반 PC 환경에서도 이 플래그는 기능에 영향 없음.

### 적용 위치
- `app.py` → `/start` route → `env = ...` 블록
- `conftest.py` → `browser` fixture → `chromium.launch()` 호출부

---

## 2. 테스트가 무한 대기 상태로 멈춤

### 증상
- 진행 화면에서 시나리오 1~2 진행 후 영구 정지
- 소스에서 실행 시 터미널도 응답 없음
- Chromium이 크래시된 후 pytest가 무한 대기

### 원인
pytest-timeout 미설치 상태에서 `--timeout=180` 옵션 전달 →
pytest가 옵션을 무시하거나 오류 → 타임아웃 없이 무한 대기.

### 해결
```bash
pip install pytest-timeout==2.3.1
```
> `requirements.txt`에 이미 포함되어 있음. 새 환경 구성 시 반드시 실행.

`app.py` pytest 명령에도 명시:
```python
"--timeout=180",    # 테스트 1개당 최대 3분 강제 종료
```

### 확인 방법
```bash
python -c "import pytest_timeout; print('OK')"
```

---

## 3. 진행 화면 status가 "running"에서 안 바뀜

### 증상
- 테스트가 크래시/timeout으로 종료됐는데 "실행 중" 상태 유지
- 재시작 버튼을 눌러도 "이미 실행 중" 오류

### 원인
`_proc`이 종료됐는데 `_state["status"]`가 "running"에 고착.

### 해결
`app.py` → `/start` route 진입 시 프로세스 생존 여부 체크:
```python
if _state["status"] == "running" and _proc is not None:
    if _proc.poll() is not None:
        _state["status"] = "done"   # 자동 복구
```

### 적용 위치
`app.py` → `/start` route 상단 (line ~283)

---

## 4. pytest "ERROR: usage: __main__.py" 즉시 실패

### 증상
진행 화면 "오류 발생" 섹션에 아래 메시지 표시:
```
ERROR: usage: __main__.py [options] [file_or_dir] [file_or_dir] [...]
```
테스트가 한 건도 실행되지 않고 즉시 종료.

### 원인
`pytest-timeout`이 설치되지 않은 Python 환경에서 `--timeout=180` 전달 →
pytest가 알 수 없는 옵션으로 인식 → usage 에러 출력.

### 해결
```bash
pip install pytest-timeout==2.3.1
```

### 확인 방법
```bash
python -c "import pytest_timeout; print('OK')"
# → ModuleNotFoundError가 뜨면 미설치
```

### 소스 vs 설치 버전
- **소스 버전**: 가상환경에 pip install 필요
- **설치 버전(EXE)**: `build/build_all.bat` 실행 시 자동 설치됨  
  (`pip install -r requirements.txt` 포함)

---

## 5. 결함 카드에 스크린샷이 안 보임

### 증상
최종 보고서 결함 카드에 스크린샷 영역이 비어있거나 깨진 아이콘만 표시.

### 원인
`<img src="C:\...\reports\screenshots\xxx.png">` 로컬 파일 경로 직접 사용.
브라우저 보안 정책상 `file://` 경로를 `http://` 페이지에서 로드 불가.

### 해결
`app.py` → finalize route에서 스크린샷을 base64 data URI로 변환:
```python
import base64 as _b64
_ss_data = _b64.b64encode(ss_p.read_bytes()).decode("ascii")
_ss_mime = "image/png" if ss_p.suffix.lower() == ".png" else "image/jpeg"
ss_data_uri = f"data:{_ss_mime};base64,{_ss_data}"
```

### 적용 위치
`app.py` → `/finalize` route

---

## 6. EXE 실행 시 콘솔 창이 잠깐 번쩍임

### 증상
QA Tool EXE 실행 시 검은 콘솔 창이 0.1~0.5초 번쩍이고 사라짐.

### 원인
`launcher.py`가 `python.exe app.py`를 실행할 때 콘솔 창이 열림.
설치된 Python에는 `pythonw.exe`가 없어 `python.exe`를 쓸 수밖에 없음.

### 해결
`build/launcher.py` — Popen에 `STARTUPINFO(SW_HIDE)` 적용:
```python
si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = subprocess.SW_HIDE
subprocess.Popen([str(py), str(APP_SCRIPT)], cwd=..., startupinfo=si)
```

> `CREATE_NO_WINDOW` 플래그는 사용하지 말 것.
> Playwright의 CDP 파이프 통신을 끊어 자식 프로세스(Chromium) 실행 불가.

---

## 7. Inno Setup 빌드 오류 모음

### 7-1. `Flags: checked` — 인식 불가

**오류**: `[Tasks] Flags: checked` 라인에서 컴파일 실패  
**원인**: Inno Setup 6에서 `checked` 플래그 미지원 (기본값이 checked)  
**해결**: `Flags: checked` 제거

---

### 7-2. `SetEnvironmentVariable` — 알 수 없는 식별자

**오류**: Pascal Script에서 `SetEnvironmentVariable` 호출 시 컴파일 실패  
**원인**: Inno Setup Pascal Script의 내장 함수가 아님  
**해결**: 임시 `.bat` 파일 생성 후 `cmd /C` 실행으로 환경변수 설정:
```pascal
SaveStringToFile(batPath, 'set "VAR=value"', False);
Exec(ExpandConstant('{cmd}'), '/C "' + batPath + '"', '', SW_HIDE, ewWaitUntilTerminated, code);
```

---

### 7-3. `HKCU` — 알 수 없는 식별자

**오류**: Pascal Script에서 `HKCU` 사용 시 컴파일 실패  
**원인**: Inno Setup Pascal Script에서는 `HKEY_CURRENT_USER` 전체 이름 필요  
**해결**: `HKCU` → `HKEY_CURRENT_USER`

---

### 7-4. `WizardForm.StatusLabel` — 신뢰할 수 없음

**원인**: Inno Setup 6에서 `WizardForm.StatusLabel` 접근이 불안정  
**해결**: 해당 코드 제거 (설치 진행 상태는 기본 Inno Setup 진행바 사용)

---

## 8. 설치 후 바탕화면 바로가기 생성 실패 (0x80070005)

### 증상
설치 마법사 마지막 단계에서 `0x80070005 (접근 거부)` 오류.

### 원인
`{commondesktop}` = 공용 바탕화면 (`C:\Users\Public\Desktop`) 접근 시 관리자 권한 필요.  
Inno Setup이 관리자 권한 없이 실행된 경우 실패.

### 해결
`build/qatool_setup.iss` → `[Icons]` 섹션:
```ini
; 변경 전
Root: {commondesktop}

; 변경 후
Root: {userdesktop}    ; 현재 사용자 바탕화면 — 관리자 권한 불필요
```

---

## 9. 테스트 대상 서버 IP/URL 변경 방법

### 증상 / 상황
테스트 대상 서버 IP가 변경되어 기존 URL로 접속 불가.

### 해결 방법 (UI)
실행 설정 화면 최상단 URL 바에 새 URL 입력 후 테스트 시작.
→ `/start` route가 `settings.yaml`의 `base_url`을 자동으로 업데이트.

### 해결 방법 (직접 수정)
`config/settings.yaml`:
```yaml
base_url: "http://새IP또는도메인:포트/"
```

### URL 형식 주의
- 끝에 `/` 포함 권장
- `#!/` 포함 여부는 무관 (`urlparse`로 host만 추출)
- 예: `http://192.168.1.100/#!/` 또는 `http://innotium.iptime.org:14180/` 모두 가능

---

## 10. base_url URL 형식 변경 시 navigate_to 오류

### 증상
서버 URL 형식이 `http://IP/#!/` → `http://도메인:포트/`로 변경된 후,
테스트 중 페이지 이동이 잘못된 URL로 가거나 세션 만료 처리가 발생.

### 원인
기존 코드:
```python
host = self.base_url.split("/#!/")[0].rstrip("/")
```
URL에 `/#!/`가 없으면 split이 되지 않아 host에 `/`가 포함될 수 있음.

### 해결
`pages/base_page.py` — `host_origin` 프로퍼티 추가 (`urlparse` 사용):
```python
from urllib.parse import urlparse

@property
def host_origin(self) -> str:
    parsed = urlparse(self.base_url)
    return f"{parsed.scheme}://{parsed.netloc}"
```

모든 Page 클래스의 `navigate_to()`에서 교체:
```python
# 변경 전
host = self.base_url.split("/#!/")[0].rstrip("/")
self.page.goto(f"{host}/manager/main.html")

# 변경 후
self.page.goto(f"{self.host_origin}/manager/main.html")
```

### 적용 파일
- `pages/base_page.py` — `host_origin` 프로퍼티 정의
- `pages/ransom_detect_policy_page.py`
- `pages/rdp_policy_page.py`
- `pages/common_process_page.py`

---

## 11. VM 환경에서 앱 창이 안 뜸 (pywebview 실패)

### 증상
EXE 실행 후 아무 창도 표시되지 않음. 앱이 실행은 됐는지조차 알 수 없음.

### 원인
pywebview가 Edge WebView2 + GPU 가속을 필요로 하는데, VM 환경에서 GPU 드라이버가
제한되어 창을 렌더링하지 못하거나 초기화 실패.

### 확인 방법
설치 경로 `logs\app_날짜시간.log` 파일 열기. 아래 내용이 있으면 Flask는 정상:
```
Running on http://127.0.0.1:5321
```

### 즉시 해결 (앱이 실행 중인 경우)
VM 안 브라우저에서 직접 접속:
```
http://127.0.0.1:5321
```

### 근본 해결
`app.py` — pywebview 실패 시 자동으로 기본 브라우저 fallback:
```python
try:
    import webview
    webview.create_window(...)
    webview.start()
except Exception:
    webbrowser.open("http://127.0.0.1:5321")
    # 메인 스레드 유지
    while True: time.sleep(1)
```
다음 빌드부터 VM에서도 자동으로 브라우저가 열림.

---

## 12. 화면 OFF(headless) 모드에서 테스트가 아무것도 안 됨 — CREATE_NO_WINDOW 문제

### 증상
- 화면 ON 모드(headed)에서는 테스트가 정상 실행됨
- 화면 OFF 모드(headless)로 전환하면 pytest가 시작되자마자 아무 로그도 없이 테스트가 한 건도 실행되지 않음
- 실시간 로그 패널에 출력이 전혀 없거나 즉시 종료됨

### 원인
`app.py`에서 pytest 서브프로세스를 생성할 때 `CREATE_NO_WINDOW` 플래그를 사용한 것이 원인.

- **headed 모드**: Chromium이 GUI 윈도우를 자체 생성하므로 `CREATE_NO_WINDOW` 영향 없음 → 정상 동작
- **headless 모드**: Chromium이 GUI 없이 CDP 파이프만으로 Playwright와 통신해야 하는데,
  `CREATE_NO_WINDOW`가 자식 프로세스의 콘솔 핸들 상속을 차단 → CDP 파이프 통신 실패 → 테스트 0건

### 해결
`CREATE_NO_WINDOW` 대신 `STARTUPINFO`의 `SW_HIDE`를 사용한다.

- `SW_HIDE`: pytest 프로세스 자체의 콘솔 창만 숨김
- `CREATE_NO_WINDOW`와 달리 하위 프로세스(Playwright / Chromium)에 핸들 상속 제약 없음
- 검은 콘솔 창도 안 뜨고, headless Playwright도 정상 동작

```python
# 변경 전
_proc = subprocess.Popen(
    cmd,
    ...
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
)

# 변경 후
_startupinfo = None
if os.name == "nt":
    _startupinfo = subprocess.STARTUPINFO()
    _startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _startupinfo.wShowWindow = subprocess.SW_HIDE

_proc = subprocess.Popen(
    cmd,
    ...
    startupinfo=_startupinfo,
    # CREATE_NO_WINDOW 제거 — headless Playwright 자식 프로세스 통신 보장
)
```

> `CREATE_NO_WINDOW`는 launcher.py에서 app.py를 실행할 때는 사용 불가 (동일 이유).
> launcher.py도 `STARTUPINFO(SW_HIDE)` 방식 사용.

### 적용 위치
`app.py` → `_run()` 함수 내 `subprocess.Popen()` 호출부

---

## 빠른 체크리스트 (EXE 설치 후 테스트 안 될 때)

```
[ ] 1. 창이 안 뜸? → logs\ 폴더 확인, 브라우저로 http://127.0.0.1:5321 접속
[ ] 2. Chromium 크래시? → conftest.py browser fixture args 확인 + UV_USE_IO_RINGS=0
[ ] 3. 테스트 즉시 "ERROR: usage"? → pytest-timeout 설치 여부 확인
[ ] 4. 진행 화면이 멈춤? → _proc.poll() 복구 로직 확인 (app.py /start)
[ ] 5. 스크린샷 안 보임? → finalize route에서 base64 data URI 변환 확인
[ ] 6. 서버 URL 변경? → settings.yaml base_url 또는 UI URL 바 입력
[ ] 7. 설치 바로가기 실패? → qatool_setup.iss에서 {userdesktop} 사용 여부 확인
[ ] 8. 화면 OFF만 테스트 안 됨? → app.py Popen에 CREATE_NO_WINDOW 없는지 확인 (SW_HIDE 방식 사용)
```

---

*마지막 업데이트: 2026-04-10*
