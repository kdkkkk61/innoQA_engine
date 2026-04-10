"""
launcher.py — qatool.exe 의 원본 스크립트

PyInstaller 로 컴파일해 qatool.exe 를 생성한다:
  pyinstaller --onefile --noconsole --name qatool launcher.py

역할:
  1. 이 EXE 옆에 있는 python\python.exe 를 찾는다
  2. 같은 폴더의 app.py 를 그 Python 으로 실행한다
  3. 앱이 뜨면 즉시 종료한다 (launcher 는 daemon 이 아님)
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

# EXE가 위치한 폴더 = 설치 루트
INSTALL_DIR = Path(sys.executable).parent

PYTHON_EXE = INSTALL_DIR / "python" / "python.exe"
APP_SCRIPT  = INSTALL_DIR / "app.py"


def _error(msg: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, msg, "QA Tool — 오류", 0x10)
    sys.exit(1)


def main() -> None:
    if not PYTHON_EXE.exists():
        _error(
            f"Python 인터프리터를 찾을 수 없습니다.\n\n"
            f"경로: {PYTHON_EXE}\n\n"
            f"재설치를 시도하세요."
        )

    if not APP_SCRIPT.exists():
        _error(
            f"앱 파일(app.py)을 찾을 수 없습니다.\n\n"
            f"경로: {APP_SCRIPT}\n\n"
            f"재설치를 시도하세요."
        )

    # pythonw.exe 가 있으면 콘솔 창 없이 실행 (선택)
    pythonw = PYTHON_EXE.parent / "pythonw.exe"
    py = pythonw if pythonw.exists() else PYTHON_EXE

    subprocess.Popen(
        [str(py), str(APP_SCRIPT)],
        cwd=str(INSTALL_DIR),
    )
    # launcher 는 여기서 종료 — 실제 앱은 별도 프로세스로 계속 실행됨


if __name__ == "__main__":
    main()
