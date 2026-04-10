@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo.
echo ================================================
echo   inno_test_tool - qatool_setup.exe Build
echo ================================================
echo.
echo Steps:
echo   1. Python 3.12 embedded setup
echo   2. Build qatool.exe (launcher) via PyInstaller
echo   3. Build qatool_setup.exe via Inno Setup
echo.
pause

REM === Path setup ===
set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%.."
set "DIST_PKG=%SCRIPT_DIR%dist_pkg"
set "EMBED_DIR=%SCRIPT_DIR%dist_pkg\python"
set "DIST_LAUNCHER=%SCRIPT_DIR%dist_launcher"

set "PY_VER=3.12.2"
set "PY_ZIP=python-%PY_VER%-embed-amd64.zip"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/%PY_ZIP%"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

echo [paths]
echo   SCRIPT_DIR = %SCRIPT_DIR%
echo   ROOT       = %ROOT%
echo   EMBED_DIR  = %EMBED_DIR%
echo.

REM === Check developer Python ===
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Install Python first.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   Dev Python: %%v

REM === Step 0: Clean previous build ===
echo.
echo [0/5] Cleaning previous build...
if exist "%DIST_PKG%"      rmdir /s /q "%DIST_PKG%"
if exist "%DIST_LAUNCHER%" rmdir /s /q "%DIST_LAUNCHER%"
mkdir "%DIST_PKG%"
mkdir "%EMBED_DIR%"
mkdir "%DIST_LAUNCHER%"
echo   done.

REM === Step 1: Download and configure Python embedded ===
echo.
echo [1/5] Python %PY_VER% embedded setup...

if not exist "%SCRIPT_DIR%%PY_ZIP%" (
    echo   Downloading from %PY_URL% ...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%SCRIPT_DIR%%PY_ZIP%' -UseBasicParsing"
    if errorlevel 1 (
        echo [ERROR] Download failed: %PY_URL%
        pause & exit /b 1
    )
    echo   Download OK.
) else (
    echo   Using cached %PY_ZIP%
)

echo   Extracting...
powershell -NoProfile -Command "Expand-Archive -Path '%SCRIPT_DIR%%PY_ZIP%' -DestinationPath '%EMBED_DIR%' -Force"
if errorlevel 1 (
    echo [ERROR] Extract failed.
    pause & exit /b 1
)

echo   Enabling site (uncomment import site in _pth)...
for %%f in ("%EMBED_DIR%\python*._pth") do (
    powershell -NoProfile -Command "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
)

if not exist "%SCRIPT_DIR%get-pip.py" (
    echo   Downloading get-pip.py...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%SCRIPT_DIR%get-pip.py' -UseBasicParsing"
)

echo   Installing pip into embedded Python...
"%EMBED_DIR%\python.exe" "%SCRIPT_DIR%get-pip.py" --no-warn-script-location -q
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)
echo   Step 1 done.

REM === Step 2: Install packages into embedded Python ===
echo.
echo [2/5] Installing packages into embedded Python...
"%EMBED_DIR%\python.exe" -m pip install ^
    --target="%EMBED_DIR%\Lib\site-packages" ^
    --no-warn-script-location -q ^
    -r "%ROOT%\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Package install failed.
    pause & exit /b 1
)
echo   Step 2 done.

REM === Step 3: Build qatool.exe via PyInstaller ===
echo.
echo [3/5] Building qatool.exe (launcher)...

python -m pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo   Installing PyInstaller...
    python -m pip install pyinstaller -q
)

if exist "%SCRIPT_DIR%build_pi" rmdir /s /q "%SCRIPT_DIR%build_pi"

REM cd into build dir to avoid trailing-backslash quote-escape bug in paths
pushd "%SCRIPT_DIR%"
python -m PyInstaller --onefile --noconsole --name qatool --distpath dist_launcher --workpath build_pi --specpath . launcher.py
popd

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause & exit /b 1
)
echo   qatool.exe built OK.

REM === Step 4: Find Inno Setup ===
echo.
echo [4/5] Checking Inno Setup...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
where ISCC.exe > nul 2>&1
if not errorlevel 1 set "ISCC=ISCC.exe"

if "!ISCC!"=="" (
    echo   Inno Setup not found.
    echo   Install from: https://jrsoftware.org/isdl.php
    echo   Then re-run this script.
    echo.
    echo   Fallback: creating dist_final folder instead...
    goto :fallback
)

echo   Found: !ISCC!
if not exist "%SCRIPT_DIR%output" mkdir "%SCRIPT_DIR%output"
"!ISCC!" "%SCRIPT_DIR%qatool_setup.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup build failed.
    pause & exit /b 1
)

echo.
echo ================================================
echo   BUILD COMPLETE
echo   Output: build\output\qatool_setup.exe
echo   Send this single file to the target VM.
echo ================================================
goto :end

REM === Fallback: create manual dist folder ===
:fallback
set "FINAL=%SCRIPT_DIR%dist_final"
if exist "%FINAL%" rmdir /s /q "%FINAL%"
mkdir "%FINAL%"

xcopy /E /I /Y /Q "%EMBED_DIR%"         "%FINAL%\python\"
xcopy /E /I /Y /Q "%ROOT%\templates"    "%FINAL%\templates\"
xcopy /E /I /Y /Q "%ROOT%\static"       "%FINAL%\static\"
xcopy /E /I /Y /Q "%ROOT%\config"       "%FINAL%\config\"
xcopy /E /I /Y /Q "%ROOT%\tests"        "%FINAL%\tests\"
xcopy /E /I /Y /Q "%ROOT%\pages"        "%FINAL%\pages\"
xcopy /E /I /Y /Q "%ROOT%\core"         "%FINAL%\core\"
xcopy /E /I /Y /Q "%ROOT%\validators"   "%FINAL%\validators\"
xcopy /E /I /Y /Q "%ROOT%\utils"        "%FINAL%\utils\"

copy /Y "%ROOT%\app.py"         "%FINAL%\app.py"
copy /Y "%ROOT%\conftest.py"    "%FINAL%\conftest.py"
if exist "%ROOT%\pytest.ini" copy /Y "%ROOT%\pytest.ini" "%FINAL%\pytest.ini"
copy /Y "%DIST_LAUNCHER%\qatool.exe" "%FINAL%\qatool.exe"

if not exist "%FINAL%\reports\screenshots" mkdir "%FINAL%\reports\screenshots"
if not exist "%FINAL%\logs"                mkdir "%FINAL%\logs"

REM --- browser install helper (relative paths via %%~dp0) ---
(
    echo @echo off
    echo chcp 65001 ^> nul
    echo set "APP_DIR=%%~dp0"
    echo set "PLAYWRIGHT_BROWSERS_PATH=%%APP_DIR%%browsers"
    echo echo ================================================
    echo echo   QA Tool - Playwright Chromium Setup
    echo echo ================================================
    echo echo.
    echo echo Downloading Chromium ^(~400MB^). Please wait...
    echo echo.
    echo "%%APP_DIR%%python\python.exe" -m playwright install chromium
    echo if errorlevel 1 ^(
    echo     echo [ERROR] Browser install failed.
    echo ^) else ^(
    echo     echo Done^^! Double-click qatool.exe to start.
    echo ^)
    echo pause
) > "%FINAL%\install_browser.bat"

echo.
echo ================================================
echo   FALLBACK COMPLETE
echo   Folder: build\dist_final\
echo.
echo   On target machine:
echo     1. Copy the dist_final folder
echo     2. Run install_browser.bat  (once)
echo     3. Double-click qatool.exe
echo ================================================

:end
echo.
pause
endlocal
