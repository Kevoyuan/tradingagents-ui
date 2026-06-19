#!/usr/bin/env bash
# Resolve or bootstrap the Python environment used by local launchers.

: "${PROJECT_DIR:?PROJECT_DIR must be set before sourcing scripts/python-env.sh}"
: "${PYTHON_VERSION:=${TRADINGAGENTS_UI_PYTHON_VERSION:-3.11}}"
: "${LOG_FILE:=/dev/stderr}"

log_python_env() {
  printf '%s\n' "$*" >>"${LOG_FILE}"
}

python_has_streamlit() {
  [[ -x "$1" ]] && "$1" -c "import streamlit" >/dev/null 2>&1
}

find_uv() {
  local candidates=(
    "${HOME}/.local/bin/uv"
    "${HOME}/.cargo/bin/uv"
    "/opt/homebrew/bin/uv"
    "/usr/local/bin/uv"
  )

  local path_uv
  path_uv="$(command -v uv 2>/dev/null || true)"
  if [[ -n "${path_uv}" ]]; then
    candidates+=("${path_uv}")
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return
    fi
  done
}

find_existing_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    if python_has_streamlit "${PYTHON}"; then
      printf '%s\n' "${PYTHON}"
      return
    fi
    log_python_env "Ignoring PYTHON=${PYTHON} because it cannot import Streamlit."
  fi

  local candidates=(
    "${PROJECT_DIR}/.venv/bin/python"
    "${PROJECT_DIR}/venv/bin/python"
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.9/bin/python3"
  )

  local path_python
  path_python="$(command -v python3 2>/dev/null || true)"
  if [[ -n "${path_python}" ]]; then
    candidates+=("${path_python}")
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    if python_has_streamlit "${candidate}"; then
      printf '%s\n' "${candidate}"
      return
    fi
  done
}

bootstrap_python_env() {
  local uv_bin
  uv_bin="$(find_uv)"
  if [[ -z "${uv_bin}" ]]; then
    log_python_env "No Python interpreter with Streamlit was found, and uv is not installed."
    log_python_env "Install uv, then launch again:"
    log_python_env "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 1
  fi

  local venv_dir="${PROJECT_DIR}/.venv"
  local venv_python="${venv_dir}/bin/python"

  log_python_env "Bootstrapping Python environment with uv."
  log_python_env "  uv: ${uv_bin}"
  log_python_env "  Python: ${PYTHON_VERSION}"
  log_python_env "  venv: ${venv_dir}"

  if [[ ! -x "${venv_python}" ]]; then
    "${uv_bin}" venv --python "${PYTHON_VERSION}" "${venv_dir}" >>"${LOG_FILE}" 2>&1
  fi

  "${uv_bin}" pip install --python "${venv_python}" -e "${PROJECT_DIR}" >>"${LOG_FILE}" 2>&1

  if ! python_has_streamlit "${venv_python}"; then
    log_python_env "Bootstrapped environment still cannot import Streamlit."
    return 1
  fi

  printf '%s\n' "${venv_python}"
}

resolve_tradingagents_ui_python() {
  local python_bin
  python_bin="$(find_existing_python)"
  if [[ -z "${python_bin}" ]]; then
    python_bin="$(bootstrap_python_env)"
  fi
  printf '%s\n' "${python_bin}"
}
