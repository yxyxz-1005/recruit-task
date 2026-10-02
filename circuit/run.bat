@echo off
REM ===================================================================
REM  One-click runner for the circuit simulation scripts.
REM
REM  Usage (open a terminal in this folder):
REM      run.bat               runs circuit 1 (RC low-pass, default)
REM      run.bat thevenin      runs circuit 2 (Thevenin equivalent)
REM      run.bat nmos          runs circuit 3 (NMOS common-source amp)
REM      run.bat all           runs all three
REM
REM  Why this script exists:
REM  PySpice is installed in a project-local virtual environment, not in the
REM  global Python. Running "python rc_lowpass.py" directly would fail with
REM  "No module named 'PySpice'". This script finds the right interpreter
REM  automatically, and falls back to whatever "python" is on PATH.
REM
REM  Note: this file is ASCII-only on purpose -- cmd.exe parses .bat files
REM  using the system code page, so non-ASCII text here would show up as
REM  garbled characters.
REM ===================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM --- find an interpreter that actually has PySpice ---
set "PY="
set "CANDIDATE=%USERPROFILE%\.workbuddy\binaries\python\envs\pyspice\Scripts\python.exe"
if exist "%CANDIDATE%" (
    "%CANDIDATE%" -c "import PySpice" >nul 2>&1
    if !errorlevel! == 0 set "PY=%CANDIDATE%"
)

if not defined PY (
    where python >nul 2>&1
    if !errorlevel! == 0 (
        python -c "import PySpice" >nul 2>&1
        if !errorlevel! == 0 set "PY=python"
    )
)

if not defined PY (
    echo [ERROR] No Python interpreter with PySpice was found.
    echo.
    echo Install the dependencies first:
    echo     pip install PySpice numpy matplotlib
    echo.
    echo Note: the PySpice wheel does NOT bundle the ngspice shared library.
    echo On Windows you also have to supply ngspice.dll and its dependencies.
    echo See the "Troubleshooting" section of README.md for the full story.
    exit /b 1
)

echo Interpreter: %PY%
echo.

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=rc"

if /i "%TARGET%"=="all" (
    call :run rc_lowpass.py "Circuit 1 - RC low-pass filter"
    call :run thevenin.py   "Circuit 2 - Thevenin equivalent"
    call :run nmos_amp.py   "Circuit 3 - NMOS common-source amplifier"
    goto :done
)

if /i "%TARGET%"=="rc" (
    call :run rc_lowpass.py "Circuit 1 - RC low-pass filter"
    goto :done
)
if /i "%TARGET%"=="thevenin" (
    call :run thevenin.py "Circuit 2 - Thevenin equivalent"
    goto :done
)
if /i "%TARGET%"=="nmos" (
    call :run nmos_amp.py "Circuit 3 - NMOS common-source amplifier"
    goto :done
)

echo [ERROR] Unknown argument "%TARGET%". Use: rc / thevenin / nmos / all
exit /b 1

:run
echo ==================================================
echo   %~2
echo ==================================================
"%PY%" "%~1"
echo.
exit /b 0

:done
echo Waveform plots have been written to the .png files in this folder.
endlocal
