@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT_DIR=%~dp0.."
set "PORT=%TRADINGAGENTS_UI_PORT%"
if "%PORT%"=="" set "PORT=8501"
set "PYTHON_VERSION=%TRADINGAGENTS_UI_PYTHON_VERSION%"
if "%PYTHON_VERSION%"=="" set "PYTHON_VERSION=3.11"
set "URL=http://localhost:%PORT%"
set "LOG_DIR=%LOCALAPPDATA%\TradingAgents UI\Logs"
set "LOG_FILE=%LOG_DIR%\streamlit.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

powershell -NoProfile -Command ^
  "$port=%PORT%; if (Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>nul

if errorlevel 1 (
  pushd "%PROJECT_DIR%"
  set "PYTHON_CMD="
  set "VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"

  if exist "!VENV_PYTHON!" (
    "!VENV_PYTHON!" -c "import streamlit" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=!VENV_PYTHON!"
  )

  if "!PYTHON_CMD!"=="" (
    where python >nul 2>nul
    if not errorlevel 1 (
      python -c "import streamlit" >nul 2>nul
      if not errorlevel 1 set "PYTHON_CMD=python"
    )
  )

  if "!PYTHON_CMD!"=="" (
    set "UV_CMD="
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
    if "!UV_CMD!"=="" if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
    if "!UV_CMD!"=="" (
      where uv >nul 2>nul
      if not errorlevel 1 set "UV_CMD=uv"
    )

    > "%LOG_FILE%" echo Bootstrapping Python environment with uv.
    if "!UV_CMD!"=="" (
      >> "%LOG_FILE%" echo No Python interpreter with Streamlit was found, and uv is not installed.
      >> "%LOG_FILE%" echo Install uv, then launch again:
      >> "%LOG_FILE%" echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
      popd
      exit /b 1
    )

    >> "%LOG_FILE%" echo   uv: !UV_CMD!
    >> "%LOG_FILE%" echo   Python: %PYTHON_VERSION%
    >> "%LOG_FILE%" echo   venv: %PROJECT_DIR%\.venv
    if not exist "!VENV_PYTHON!" (
      "!UV_CMD!" venv --python "%PYTHON_VERSION%" "%PROJECT_DIR%\.venv" >> "%LOG_FILE%" 2>&1
      if errorlevel 1 (
        popd
        exit /b 1
      )
    )
    "!UV_CMD!" pip install --python "!VENV_PYTHON!" -e "%PROJECT_DIR%" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
      popd
      exit /b 1
    )
    "!VENV_PYTHON!" -c "import streamlit" >nul 2>nul
    if errorlevel 1 (
      >> "%LOG_FILE%" echo Bootstrapped environment still cannot import Streamlit.
      popd
      exit /b 1
    )
    set "PYTHON_CMD=!VENV_PYTHON!"
  )

  start "TradingAgents UI Server" /min cmd /c ""!PYTHON_CMD!" -m trade_ui.cli --port %PORT% >> ""%LOG_FILE%"" 2>&1"
  popd
)

for /l %%i in (1,1,60) do (
  powershell -NoProfile -Command ^
    "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 '%URL%/_stcore/health'; if ($r.Content -match 'ok') { exit 0 } } catch {}; exit 1" >nul 2>nul
  if not errorlevel 1 goto open_app
  timeout /t 1 /nobreak >nul
)

:open_app
start "" "%URL%"
