@echo off
setlocal

set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PYTHON%" (
  set "PYTHON_EXE=%BUNDLED_PYTHON%"
  goto run_server
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PYTHON_EXE=py"
  goto run_server
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PYTHON_EXE=python"
  goto run_server
)

echo Python executable was not found. Install Python 3.11+ and try again.
exit /b 1

:run_server
"%PYTHON_EXE%" -m uvicorn main:app --reload
