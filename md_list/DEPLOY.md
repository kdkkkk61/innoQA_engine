# 배포 가이드 — inno_test_tool

## 방식 A : setup.bat + start.bat (권장 — VM/PC 배포)

Python이 설치된 환경이라면 이 방법이 가장 단순하고 안정적입니다.

### 요구사항
- Windows 10 / 11
- Python 3.10 이상 ([python.org](https://www.python.org/downloads/))
- 인터넷 연결 (최초 설치 시 패키지 다운로드)

### 배포 단계

```
1. 프로젝트 폴더 전체를 대상 PC/VM에 복사
2. setup.bat  더블클릭  →  가상환경 생성 + 패키지 + 브라우저 자동 설치 (1회만)
3. start.bat  더블클릭  →  앱 시작
```

### 폴더 구조

```
inno_test_tool/
├── setup.bat      ← 초기 설치 (1회)
├── start.bat      ← 앱 실행
├── app.py
├── requirements.txt
├── config/
├── templates/
├── static/
├── tests/
└── ...
```

---

## 방식 B : PyInstaller EXE 빌드

Python 설치 없이 더블클릭만으로 실행하는 EXE를 만들 수 있습니다.

> **주의**: pytest 서브프로세스 실행을 위해 EXE 배포 폴더에도 venv가 필요합니다.
> Python이 완전히 필요 없는 독립 실행은 지원하지 않습니다.

### 빌드 (개발자 PC에서 1회)

```
setup.bat        ← 아직 없으면 먼저 실행
build_exe.bat    ← EXE 빌드 (약 2~3분)
```

빌드 완료 후 `dist\inno_test_tool\` 폴더가 생성됩니다.

### EXE 배포 단계

```
1. dist\inno_test_tool\ 폴더 통째로 대상 PC/VM에 복사
2. setup_venv.bat 실행  →  pytest용 venv 구성 (Python 필요, 1회)
3. inno_test_tool.exe   →  더블클릭 실행
```

---

## 패키지 버전 고정

```
requirements.txt 에 모든 의존성 버전이 명시되어 있습니다.
오프라인 환경에서는 pip download 로 패키지를 미리 받아 두세요.

pip download -r requirements.txt -d packages/
pip install --no-index --find-links packages/ -r requirements.txt
```

---

## 주요 경로

| 항목 | 경로 |
|------|------|
| 앱 로그 | `logs/app_YYYYMMDD_HHMMSS.log` |
| 스캔 결과 HTML | `reports/qa_report_*.html` |
| known_bugs | `config/known_bugs.yaml` |
| scan_hints | `config/scan_hints/*.yaml` |
