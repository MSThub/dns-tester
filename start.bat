@echo off
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% == 0 (
    goto :run_script
) else (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs -WorkingDirectory '%~dp0'"
    exit /b
)

:run_script
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found in PATH.
    pause
    exit /b 1
)

python dns-checker.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Script exited with error code %errorlevel%
)
pause