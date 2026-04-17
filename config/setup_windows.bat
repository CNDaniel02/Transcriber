@echo off
setlocal enabledelayedexpansion

cd /d %~dp0\..
set PROJECT_ROOT=%CD%
set VENV_DIR=%PROJECT_ROOT%\.venv

echo [INFO] Project root: %PROJECT_ROOT%

if not exist "%VENV_DIR%\Scripts\python.exe" (
  where py >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python launcher 'py' was not found.
    echo [ERROR] Install Python 3.11 and ensure py.exe is available.
    exit /b 1
  )

  echo [INFO] Creating virtual environment at %VENV_DIR%
  py -3.11 -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    exit /b 1
  )
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Failed to activate virtual environment.
  exit /b 1
)

echo [INFO] Upgrading pip tooling
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip tooling.
  exit /b 1
)

echo [INFO] Installing Torch CUDA 12.1 wheels
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
  echo [ERROR] Failed to install torch CUDA wheels.
  exit /b 1
)

echo [INFO] Installing project requirements
pip install -r "%PROJECT_ROOT%\config\requirements.txt"
if errorlevel 1 (
  echo [ERROR] Failed to install project requirements.
  exit /b 1
)

echo [INFO] Running environment checks
python "%PROJECT_ROOT%\config\check_env.py"
if errorlevel 1 (
  echo [ERROR] Environment checks failed.
  exit /b 1
)

echo [DONE] Environment setup complete.
exit /b 0
