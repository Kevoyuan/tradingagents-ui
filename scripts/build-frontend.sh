#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${PROJECT_DIR}/frontend"

echo "Building frontend in ${FRONTEND_DIR}..."
cd "${FRONTEND_DIR}"

if command -v npm >/dev/null 2>&1; then
  if [ -f "package-lock.json" ]; then
    npm ci || npm install
  else
    npm install
  fi
  npm run build
else
  echo "Error: npm is required to build the frontend." >&2
  exit 1
fi

echo "Frontend build complete: static assets written to trade_ui/static"
