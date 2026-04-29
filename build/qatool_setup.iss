; qatool_setup.iss
;
; Build: ISCC.exe qatool_setup.iss
; Output: output\qatool_setup.exe
;
; Directory layout (relative to this .iss file = build\):
;   build\dist_launcher\qatool.exe   <- launcher EXE
;   build\dist_pkg\python\*          <- embedded Python + packages
;   ..\app.py                        <- app source (project root)
;   ..\templates\*, ..\config\* ...  <- app assets

[Setup]
AppName=QA Tool
AppVersion=1.0
AppPublisher=QA Team
DefaultDirName={autopf}\QATool
DefaultGroupName=QA Tool
OutputBaseFilename=qatool_setup
OutputDir=output
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayName=QA Tool
DisableDirPage=no

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional tasks:"

[Files]
; launcher EXE (in build\dist_launcher\)
Source: "dist_launcher\qatool.exe"; DestDir: "{app}"; Flags: ignoreversion

; embedded Python (in build\dist_pkg\python\)
Source: "dist_pkg\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; app source files (project root = ..\)
Source: "..\app.py";       DestDir: "{app}"; Flags: ignoreversion
Source: "..\conftest.py";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\pytest.ini";   DestDir: "{app}"; Flags: ignoreversion

; app assets
Source: "..\templates\*";   DestDir: "{app}\templates";   Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\static\*";      DestDir: "{app}\static";      Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\config\*";      DestDir: "{app}\config";      Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\tests\*";       DestDir: "{app}\tests";       Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\pages\*";       DestDir: "{app}\pages";       Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\core\*";        DestDir: "{app}\core";        Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\validators\*";  DestDir: "{app}\validators";  Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\utils\*";       DestDir: "{app}\utils";       Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dashboard\*";   DestDir: "{app}\dashboard";   Flags: ignoreversion recursesubdirs createallsubdirs

; placeholder files for empty dirs
Source: "placeholder.txt";  DestDir: "{app}\reports\screenshots"; Flags: ignoreversion
Source: "placeholder.txt";  DestDir: "{app}\logs";                Flags: ignoreversion

[Dirs]
Name: "{app}\browsers"
Name: "{app}\reports\screenshots"
Name: "{app}\logs"

[Icons]
Name: "{group}\QA Tool";         Filename: "{app}\qatool.exe"
Name: "{group}\Uninstall QATool"; Filename: "{uninstallexe}"
Name: "{userdesktop}\QA Tool"; Filename: "{app}\qatool.exe"; Tasks: desktopicon

[UninstallDelete]
Type: filesandordirs; Name: "{app}\browsers"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\reports"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
{ 임시 .bat 파일로 PLAYWRIGHT_BROWSERS_PATH 설정 후 playwright install 실행 }
procedure InstallPlaywrightBrowser();
var
  PythonExe:    string;
  BrowsersPath: string;
  BatPath:      string;
  BatLines:     TArrayOfString;
  ResultCode:   Integer;
begin
  PythonExe    := ExpandConstant('{app}\python\python.exe');
  BrowsersPath := ExpandConstant('{app}\browsers');
  BatPath      := ExpandConstant('{tmp}\pw_install.bat');

  { 임시 bat 작성 — env var 설정 후 playwright install }
  SetArrayLength(BatLines, 4);
  BatLines[0] := '@echo off';
  BatLines[1] := 'set "PLAYWRIGHT_BROWSERS_PATH=' + BrowsersPath + '"';
  BatLines[2] := '"' + PythonExe + '" -m playwright install chromium';
  BatLines[3] := 'exit /b %errorlevel%';
  SaveStringsToFile(BatPath, BatLines, False);

  if not Exec(ExpandConstant('{cmd}'),
              '/C "' + BatPath + '"',
              ExpandConstant('{app}'),
              SW_HIDE,
              ewWaitUntilTerminated,
              ResultCode) then
  begin
    MsgBox('Playwright browser install failed.' + #13#10 +
           'Run install_browser.bat manually after installation.',
           mbError, MB_OK);
  end else if ResultCode <> 0 then
  begin
    MsgBox('Playwright browser install returned error code: ' + IntToStr(ResultCode) + #13#10 +
           'Run install_browser.bat manually if browser is missing.',
           mbInformation, MB_OK);
  end;

  { PLAYWRIGHT_BROWSERS_PATH 를 사용자 환경변수에 영구 등록 }
  RegWriteStringValue(HKEY_CURRENT_USER,
    'Environment',
    'PLAYWRIGHT_BROWSERS_PATH',
    BrowsersPath);
end;

{ 재설치용 helper bat 생성 }
procedure CreateBrowserInstallHelper();
var
  BatPath:  string;
  BatLines: TArrayOfString;
begin
  BatPath := ExpandConstant('{app}\install_browser.bat');
  SetArrayLength(BatLines, 6);
  BatLines[0] := '@echo off';
  BatLines[1] := 'set "PLAYWRIGHT_BROWSERS_PATH=' + ExpandConstant('{app}\browsers') + '"';
  BatLines[2] := 'echo Installing Playwright Chromium...';
  BatLines[3] := '"' + ExpandConstant('{app}\python\python.exe') + '" -m playwright install chromium';
  BatLines[4] := 'echo Done.';
  BatLines[5] := 'pause';
  SaveStringsToFile(BatPath, BatLines, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateBrowserInstallHelper();
    InstallPlaywrightBrowser();
  end;
end;
