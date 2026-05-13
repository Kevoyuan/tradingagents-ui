#!/bin/bash
# Launch TradingAgents UI for devices on the same local network.
set -e
cd "$(dirname "$0")"

echo ""
exec "${PYTHON:-python3}" -m trade_ui.cli --lan "$@"
