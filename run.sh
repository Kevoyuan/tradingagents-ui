#!/bin/bash
# Run TradingAgents UI through the CLI wrapper so update checks stay consistent.
set -e
cd "$(dirname "$0")"

echo ""
exec "${PYTHON:-python3}" -m trade_ui.cli "$@"
