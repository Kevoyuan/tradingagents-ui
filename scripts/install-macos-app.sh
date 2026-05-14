#!/bin/bash
# Create a double-clickable macOS app that launches the local Streamlit web app.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH_SCRIPT="${PROJECT_DIR}/scripts/launch-local-webapp.sh"
APP_PATH="${PROJECT_DIR}/TradingAgents UI.app"

chmod +x "${LAUNCH_SCRIPT}"
osacompile -o "${APP_PATH}" -e "do shell script quoted form of \"${LAUNCH_SCRIPT}\""

echo "Created: ${APP_PATH}"
