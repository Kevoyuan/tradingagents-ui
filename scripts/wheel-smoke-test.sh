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
  "${TEMP_DIR}/venv/bin/python" -c '
import sys
import zipfile
from pathlib import Path
import trade_ui
from trade_ui.cli import _resolve_app_path

wheel_path = sys.argv[1]
with zipfile.ZipFile(wheel_path) as z:
    names = z.namelist()
    assert any("trade_ui/static/index.html" in n for n in names), (
        f"Missing trade_ui/static/index.html in wheel archive {wheel_path}"
    )
    assert any("trade_ui/static/assets/" in n for n in names), (
        f"Missing trade_ui/static/assets in wheel archive {wheel_path}"
    )

pkg_static = Path(trade_ui.__file__).resolve().parent / "static"
assert (pkg_static / "index.html").is_file(), (
    f"Missing index.html in installed package static directory: {pkg_static}"
)

assert _resolve_app_path().is_file()
print("Wheel smoke test and static assets verification passed.")
' "${WHEEL}"
  "${TEMP_DIR}/venv/bin/trade-ui" --help >/dev/null
)
