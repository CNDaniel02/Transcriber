@echo off
setlocal enabledelayedexpansion

cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Virtual environment not found. Running setup first...
  cmd /c config\setup_windows.bat
  if errorlevel 1 (
    echo [ERROR] Environment setup failed.
    pause
    exit /b 1
  )
)

echo [INFO] Launching desktop app...
.venv\Scripts\python.exe gui\app.py
if errorlevel 1 (
  echo [ERROR] Desktop app exited with an error.
  pause
  exit /b 1
)

exit /b 0
