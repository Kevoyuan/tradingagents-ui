#!/bin/bash
# Start TradingAgents UI in the background and open it in a standalone app window.
set -euo pipefail

# Unset global PYTHONPATH to avoid Hermes-Agent cli.py shadowing tradingagents' cli package.
unset PYTHONPATH

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${TRADINGAGENTS_UI_PORT:-8501}"
HOST="${TRADINGAGENTS_UI_HOST:-localhost}"
PYTHON_VERSION="${TRADINGAGENTS_UI_PYTHON_VERSION:-3.13}"
URL="http://${HOST}:${PORT}"
LOG_DIR="${HOME}/Library/Logs/tradingagents-ui"
PID_FILE="${LOG_DIR}/streamlit.pid"
LOG_FILE="${LOG_DIR}/streamlit.log"

mkdir -p "${LOG_DIR}"
source "${PROJECT_DIR}/scripts/python-env.sh"

port_is_listening() {
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1
}

server_is_healthy() {
  curl -fsS "http://localhost:${PORT}/_stcore/health" >/dev/null 2>&1
}

if ! port_is_listening; then
  cd "${PROJECT_DIR}"
  : >"${LOG_FILE}"
  PYTHON_BIN="$(resolve_tradingagents_ui_python)"
  nohup "${PYTHON_BIN}" -m trade_ui.cli --port "${PORT}" \
    >>"${LOG_FILE}" 2>&1 &
  echo "$!" >"${PID_FILE}"
fi

HEALTHY=false
for _ in $(seq 1 60); do
  if server_is_healthy; then
    HEALTHY=true
    break
  fi
  sleep 0.5
done

if [[ "${HEALTHY}" != true ]]; then
  osascript \
    -e 'display alert "TradingAgents UI could not start" message "Check ~/Library/Logs/tradingagents-ui/streamlit.log for details." as critical' \
    >/dev/null 2>&1 || true
  exit 1
fi

if [ -d "/Applications/Google Chrome.app" ]; then
  open -na "Google Chrome" --args --app="${URL}" --user-data-dir="${LOG_DIR}/chrome-profile"
elif [ -d "/Applications/Microsoft Edge.app" ]; then
  open -na "Microsoft Edge" --args --app="${URL}" --user-data-dir="${LOG_DIR}/edge-profile"
else
  open "${URL}"
fi
