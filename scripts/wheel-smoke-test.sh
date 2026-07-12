#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEEL="$(find "${PROJECT_DIR}/dist" -maxdepth 1 -name 'tradingagents_ui-*.whl' -print -quit)"

if [[ -z "${WHEEL}" ]]; then
  echo "Build a wheel before running this smoke test." >&2
  exit 1
fi

TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TEMP_DIR}"' EXIT
"${PYTHON:-python3}" -m venv "${TEMP_DIR}/venv"
"${TEMP_DIR}/venv/bin/python" -m pip install --quiet --no-deps "${WHEEL}"
(
  cd "${TEMP_DIR}"
  "${TEMP_DIR}/venv/bin/python" -c 'import trade_ui; from trade_ui.cli import _resolve_app_path; assert _resolve_app_path().is_file(); print("ok")'
  "${TEMP_DIR}/venv/bin/trade-ui" --help >/dev/null
)
