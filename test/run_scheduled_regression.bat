@echo off
REM ============================================================================
REM  Scheduled Regression launcher (for Windows Task Scheduler)
REM
REM  IMPORTANT - this file must stay pure ASCII.
REM  cmd.exe parses .bat using the OEM code page (cp950 on this machine);
REM  UTF-8 Chinese characters inside echo/REM lines break command parsing.
REM
REM  Design notes:
REM    * Fixed working directory - does not rely on the CWD the scheduler gives
REM    * Absolute Python path - does not rely on PATH
REM    * Forces UTF-8 for Python stdout so the log keeps Chinese output readable
REM    * Headless - no desktop session, no pre-opened Chrome required
REM    * stdout + stderr both written to a timestamped log file
REM    * Propagates the Python exit code back to Task Scheduler (Last Result)
REM
REM  Exit code contract (from tools/scheduled_regression.py):
REM    0 = no new regression, safety audit passed
REM    1 = NEW FAIL / MISSING CASE / safety violation
REM    2 = runner / browser / result parsing failure
REM ============================================================================

setlocal EnableExtensions

set "TEST_DIR=D:\Jietech\test"
set "PYTHON_EXE=C:\Users\Water\AppData\Local\Programs\Python\Python314\python.exe"
set "LOG_DIR=%TEST_DIR%\output\automation\logs"

REM Force UTF-8 for Python I/O (Windows console default is cp950)
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist "%TEST_DIR%" (
    echo [ERROR] working directory not found: %TEST_DIR%
    exit /b 2
)
cd /d "%TEST_DIR%"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] python not found: %PYTHON_EXE%
    exit /b 2
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Timestamp.
REM wmic was removed in Windows 11 (build 26xxx), so use PowerShell and fall
REM back to a %DATE%/%TIME% based stamp if PowerShell is unavailable.
set "STAMP="
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" 2^>nul') do set "STAMP=%%I"
if not defined STAMP (
    set "STAMP=%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
    set "STAMP=%STAMP: =0%"
)

set "LOG_FILE=%LOG_DIR%\scheduled_%STAMP%.log"

echo [%DATE% %TIME%] scheduled regression start >> "%LOG_FILE%"
echo [INFO] cwd=%CD% >> "%LOG_FILE%"
echo [INFO] python=%PYTHON_EXE% >> "%LOG_FILE%"

"%PYTHON_EXE%" -m tools.scheduled_regression >> "%LOG_FILE%" 2>&1
set "RC=%ERRORLEVEL%"

echo [%DATE% %TIME%] scheduled regression end, exit code=%RC% >> "%LOG_FILE%"

REM endlocal would discard RC, so pass it out explicitly.
endlocal & exit /b %RC%
