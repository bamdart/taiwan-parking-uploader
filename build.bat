@echo off
REM ============================================
REM  taiwan-parking-uploader - PyInstaller Build
REM  Entry:   main.py (project root)
REM  Output:  dist-pyinstaller\<RELEASE_NAME>-<APP_VERSION>.exe
REM  Names / version single-sourced from scheduler\branding.py
REM ============================================

cd /d "%~dp0"
chcp 65001 >nul
echo [INFO] Working dir: %CD%

REM PyInstaller builds with an ASCII internal name to avoid any Chinese-path
REM issues in the bootloader / temp extraction. The final artifact is renamed
REM to the (possibly Chinese) release name by Python at the end, which handles
REM UTF-8 cleanly - unlike batch string handling.
set INTERNAL_NAME=app

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed
    exit /b 1
)

echo [2/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist-pyinstaller rmdir /s /q dist-pyinstaller
if exist %INTERNAL_NAME%.spec del /q %INTERNAL_NAME%.spec

echo [3/4] Building with PyInstaller (onefile mode)...
set ICON_PATH=%CD%\scheduler\resources\favicon.ico

REM Onefile mode: single self-contained .exe, no external resources needed.
REM Favicon is embedded as base64 in scheduler/gui/_favicon.py.
REM
REM --runtime-tmpdir: extract _MEI<pid> to %LOCALAPPDATA%\HITech-TPU instead of
REM the system Temp folder, giving a consistent location users can whitelist in
REM antivirus. Batch %% escapes to %, so PyInstaller stores the literal
REM "%LOCALAPPDATA%\HITech-TPU" and the bootloader expands it at runtime.
REM
REM VC++ / UCRT DLL bundling: if the target machine lacks the VC++ Redistributable,
REM python3xx.dll fails to load. We scan common locations and bundle any found.
call :build_vcrt_args

pyinstaller ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --name %INTERNAL_NAME% ^
    --icon "%ICON_PATH%" ^
    --runtime-tmpdir "%%LOCALAPPDATA%%\HITech-TPU" ^
    --paths . ^
    --distpath dist-pyinstaller ^
    --workpath build ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtSvg ^
    %VCRT_ARGS% ^
    main.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

echo [4/4] Renaming artifact to release name...
REM Python reads branding.py (UTF-8) and renames app.exe -> <RELEASE_NAME>-<ver>.exe
python -c "import os;from scheduler import branding;src=os.path.join('dist-pyinstaller','%INTERNAL_NAME%.exe');dst=os.path.join('dist-pyinstaller',branding.RELEASE_NAME+'-'+branding.APP_VERSION+'.exe');os.replace(src,dst);print('[DONE] '+dst)"
if errorlevel 1 (
    echo [ERROR] Rename step failed
    exit /b 1
)

exit /b 0

REM ============================================================
REM  :build_vcrt_args
REM  Collect --add-binary flags for VC++ runtime DLLs found on this machine
REM  so target machines don't need the Visual C++ Redistributable installed.
REM ============================================================
:build_vcrt_args
set VCRT_ARGS=

for %%D in (
    "%SystemRoot%\System32"
    "%SystemRoot%\SysWOW64"
) do (
    if exist "%%~D\vcruntime140.dll" set VCRT_ARGS=%VCRT_ARGS% --add-binary "%%~D\vcruntime140.dll;."
    if exist "%%~D\vcruntime140_1.dll" set VCRT_ARGS=%VCRT_ARGS% --add-binary "%%~D\vcruntime140_1.dll;."
    if exist "%%~D\msvcp140.dll" set VCRT_ARGS=%VCRT_ARGS% --add-binary "%%~D\msvcp140.dll;."
    if exist "%%~D\ucrtbase.dll" set VCRT_ARGS=%VCRT_ARGS% --add-binary "%%~D\ucrtbase.dll;."
)

if defined VCRT_ARGS (
    echo [INFO] Bundling VC++ runtime DLLs for redistribution.
) else (
    echo [WARN] No VC++ runtime DLLs found on this machine.
    echo        Target machines must install Visual C++ Redistributable.
)
goto :eof
