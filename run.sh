#!/bin/bash
# Run TradingAgents UI through the local launcher wrapper.
set -euo pipefail

# Unset global PYTHONPATH to avoid Hermes-Agent cli.py shadowing tradingagents' cli package.
unset PYTHONPATH

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Starting a second server on a port that is already bound does not fail fast:
# uvicorn finishes its roughly two second startup and then exits with
# EADDRINUSE, which reads as "the app ran for two seconds and quit". Reuse the
# server that is already there instead. Port parsing mirrors trade_ui.cli.
UI_PORT="${TRADINGAGENTS_UI_PORT:-8501}"
UI_HELP_REQUESTED=false
_previous_arg=""
for _arg in "$@"; do
  case "${_arg}" in
    -h|--help) UI_HELP_REQUESTED=true ;;
  esac
  if [[ "${_previous_arg}" == "--port" ]]; then
    UI_PORT="${_arg}"
  fi
  _previous_arg="${_arg}"
done

if [[ "${UI_HELP_REQUESTED}" == "false" ]] \
  && command -v lsof >/dev/null 2>&1 \
  && lsof -nP -iTCP:"${UI_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  # Probe the FastAPI app's own /health (trade_ui/server/app.py) over IPv4, and
  # check the payload. A 200 alone means nothing here: Streamlit answers
  # /health with 200 and an HTML index, so a stray legacy server would
  # otherwise be mistaken for the web app and reused.
  if curl -fsS "http://127.0.0.1:${UI_PORT}/health" 2>/dev/null \
    | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    echo ""
    echo "TradingAgents UI is already running at http://localhost:${UI_PORT}"
    echo "Reusing the running server instead of starting a second one."
    if command -v open >/dev/null 2>&1; then
      open "http://localhost:${UI_PORT}" || true
    fi
    exit 0
  fi
  echo "" >&2
  echo "Port ${UI_PORT} is already in use by another process." >&2
  echo "Stop it first, or start on another port: ./run.sh --port 8502" >&2
  exit 1
fi

PYTHON_VERSION="${TRADINGAGENTS_UI_PYTHON_VERSION:-3.13}"
LOG_FILE="${TRADINGAGENTS_UI_LOG_FILE:-/dev/stderr}"
source "${PROJECT_DIR}/scripts/python-env.sh"

echo ""
cd "${PROJECT_DIR}"
PYTHON_BIN="$(resolve_tradingagents_ui_python)"
exec "${PYTHON_BIN}" -m trade_ui.cli "$@"
