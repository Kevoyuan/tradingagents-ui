#!/bin/bash
# Create a double-clickable macOS app that launches the local Streamlit web app.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH_SCRIPT="${PROJECT_DIR}/scripts/launch-local-webapp.sh"
TEMPLATE_DIR="${PROJECT_DIR}/scripts/macos-app"
APP_PATH="${PROJECT_DIR}/TradingAgents UI.app"
TEMP_APP="${PROJECT_DIR}/.TradingAgents UI.new.app"
GO_BIN="$(command -v go || true)"

chmod +x "${LAUNCH_SCRIPT}"

if [[ -z "${GO_BIN}" ]]; then
  echo "Go is required to build the native macOS launcher." >&2
  echo "Install it with: brew install go" >&2
  exit 1
fi

if [[ -e "${TEMP_APP}" ]]; then
  TEMP_APP="${PROJECT_DIR}/.TradingAgents UI.new.$$.app"
fi

mkdir -p "${TEMP_APP}/Contents/MacOS" "${TEMP_APP}/Contents/Resources"
cp "${TEMPLATE_DIR}/Info.plist" "${TEMP_APP}/Contents/Info.plist"
GO111MODULE=off "${GO_BIN}" build -trimpath -ldflags="-s -w" \
  -o "${TEMP_APP}/Contents/MacOS/TradingAgents UI" \
  "${TEMPLATE_DIR}/launcher.go"

if [[ -f "${APP_PATH}/Contents/Resources/applet.icns" ]]; then
  cp "${APP_PATH}/Contents/Resources/applet.icns" \
    "${TEMP_APP}/Contents/Resources/applet.icns"
fi

xattr -cr "${TEMP_APP}"
codesign --force --deep --sign - "${TEMP_APP}" >/dev/null 2>&1

if [[ -e "${APP_PATH}" ]]; then
  BACKUP_APP="${APP_PATH}.previous"
  BACKUP_INDEX=2
  while [[ -e "${BACKUP_APP}" ]]; do
    BACKUP_APP="${APP_PATH}.previous.${BACKUP_INDEX}"
    BACKUP_INDEX=$((BACKUP_INDEX + 1))
  done
  mv "${APP_PATH}" "${BACKUP_APP}"
fi
mv "${TEMP_APP}" "${APP_PATH}"

echo "Created: ${APP_PATH}"
