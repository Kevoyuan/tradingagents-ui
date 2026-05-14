@echo off
setlocal

set "PROJECT_DIR=%~dp0.."
set "PORT=%TRADINGAGENTS_UI_PORT%"
if "%PORT%"=="" set "PORT=8501"
set "URL=http://localhost:%PORT%"
set "LOG_DIR=%LOCALAPPDATA%\TradingAgents UI\Logs"
set "LOG_FILE=%LOG_DIR%\streamlit.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

powershell -NoProfile -Command ^
  "$port=%PORT%; if (Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet) { exit 0 } else { exit 1 }" >nul 2>nul

if errorlevel 1 (
  pushd "%PROJECT_DIR%"
  set "TRADINGAGENTS_UI_NO_UPDATE=1"
  where python >nul 2>nul
  if errorlevel 1 (
    start "TradingAgents UI Server" /min cmd /c "py -3 -m trade_ui.cli --no-update --port %PORT% > ""%LOG_FILE%"" 2>&1"
  ) else (
    start "TradingAgents UI Server" /min cmd /c "python -m trade_ui.cli --no-update --port %PORT% > ""%LOG_FILE%"" 2>&1"
  )
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
