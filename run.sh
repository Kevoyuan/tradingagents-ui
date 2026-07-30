#!/bin/bash
# Run TradingAgents UI through the local launcher wrapper.
set -euo pipefail

# Unset global PYTHONPATH to avoid Hermes-Agent cli.py shadowing tradingagents' cli package.
unset PYTHONPATH

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_VERSION="${TRADINGAGENTS_UI_PYTHON_VERSION:-3.13}"
LOG_FILE="${TRADINGAGENTS_UI_LOG_FILE:-/dev/stderr}"
source "${PROJECT_DIR}/scripts/python-env.sh"

echo ""
cd "${PROJECT_DIR}"
PYTHON_BIN="$(resolve_tradingagents_ui_python)"
exec "${PYTHON_BIN}" -m trade_ui.cli "$@"
