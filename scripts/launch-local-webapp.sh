#!/bin/bash
# Start TradingAgents UI in the background and open it in a standalone app window.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${TRADINGAGENTS_UI_PORT:-8501}"
HOST="${TRADINGAGENTS_UI_HOST:-localhost}"
URL="http://${HOST}:${PORT}"
LOG_DIR="${HOME}/Library/Logs/tradingagents-ui"
PID_FILE="${LOG_DIR}/streamlit.pid"
LOG_FILE="${LOG_DIR}/streamlit.log"

mkdir -p "${LOG_DIR}"

port_is_listening() {
  lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1
}

server_is_healthy() {
  curl -fsS "http://localhost:${PORT}/_stcore/health" >/dev/null 2>&1
}

if ! port_is_listening; then
  cd "${PROJECT_DIR}"
  TRADINGAGENTS_UI_NO_UPDATE=1 nohup "${PYTHON:-python3}" -m trade_ui.cli --no-update --port "${PORT}" \
    >"${LOG_FILE}" 2>&1 &
  echo "$!" >"${PID_FILE}"
fi

for _ in $(seq 1 60); do
  if server_is_healthy; then
    break
  fi
  sleep 0.5
done

if [ -d "/Applications/Google Chrome.app" ]; then
  open -na "Google Chrome" --args --app="${URL}" --user-data-dir="${LOG_DIR}/chrome-profile"
elif [ -d "/Applications/Microsoft Edge.app" ]; then
  open -na "Microsoft Edge" --args --app="${URL}" --user-data-dir="${LOG_DIR}/edge-profile"
else
  open "${URL}"
fi
