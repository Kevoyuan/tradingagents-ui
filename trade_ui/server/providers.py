"""Provider catalog, model options, and upstream compatibility helpers."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from tradingagents_compat import (
    TRADINGAGENTS_MAX_VERSION,
    TRADINGAGENTS_REPO_URL,
    TRADINGAGENTS_TARGET_TAG,
    tradingagents_compatibility,
    version_tuple,
)
from ui_config import (
    ANALYST_OPTIONS,
    AZURE_ENV_FIELDS,
    BEDROCK_ENV_FIELDS,
    DEPTH_OPTIONS,
    LANGUAGES,
    OPTIONAL_API_KEY_PROVIDERS,
    PROVIDER_API_KEY_ENV,
    PROVIDER_BASE_URL_ENV,
    PROVIDER_MODEL_OPTIONS,
    PROVIDER_RUNTIME,
    PROVIDER_URLS,
    PROVIDERS,
)

try:
    from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
except (ImportError, ModuleNotFoundError):
    MODEL_OPTIONS = {}


def get_provider_credential_requirements(provider: str) -> dict[str, list[str]]:
    """Return required and optional environment variable names for a provider."""
    required: list[str] = []
    optional: list[str] = []

    api_key_env = PROVIDER_API_KEY_ENV.get(provider)
    if api_key_env:
        if provider in OPTIONAL_API_KEY_PROVIDERS:
            optional.append(api_key_env)
        else:
            required.append(api_key_env)

    if provider == "azure":
        for env_name, _, _ in AZURE_ENV_FIELDS:
            if env_name not in required:
                required.append(env_name)

    if provider == "bedrock":
        for item in BEDROCK_ENV_FIELDS:
            env_name = item[0]
            if env_name not in optional and env_name not in required:
                optional.append(env_name)

    base_url_env = PROVIDER_BASE_URL_ENV.get(provider)
    if base_url_env:
        default_url = PROVIDER_URLS.get(provider)
        if default_url:
            optional.append(base_url_env)
        else:
            required.append(base_url_env)

    return {"required": required, "optional": optional}


def get_provider_catalog() -> dict[str, Any]:
    """Assemble provider and model catalog for frontend and API consumers."""
    providers_list = [{"id": key, "label": display, "value": key} for display, key in PROVIDERS]
    analysts_list = [{"id": key, "label": display, "value": key} for display, key in ANALYST_OPTIONS]

    azure_fields = [
        {"name": f[0], "label": f[1], "placeholder": f[2]}
        for f in AZURE_ENV_FIELDS
    ]
    bedrock_fields = [
        {"name": f[0], "label": f[1], "placeholder": f[2], "optional": f[3] if len(f) > 3 else False}
        for f in BEDROCK_ENV_FIELDS
    ]

    reqs = {key: get_provider_credential_requirements(key) for _, key in PROVIDERS}

    return {
        "providers": providers_list,
        "PROVIDERS": [list(item) for item in PROVIDERS],
        "provider_model_options": PROVIDER_MODEL_OPTIONS,
        "PROVIDER_MODEL_OPTIONS": PROVIDER_MODEL_OPTIONS,
        "upstream_model_options": MODEL_OPTIONS,
        "MODEL_OPTIONS": MODEL_OPTIONS,
        "provider_api_key_env": PROVIDER_API_KEY_ENV,
        "PROVIDER_API_KEY_ENV": PROVIDER_API_KEY_ENV,
        "provider_base_url_env": PROVIDER_BASE_URL_ENV,
        "PROVIDER_BASE_URL_ENV": PROVIDER_BASE_URL_ENV,
        "provider_urls": PROVIDER_URLS,
        "provider_runtime": PROVIDER_RUNTIME,
        "azure_env_fields": azure_fields,
        "AZURE_ENV_FIELDS": [list(item) for item in AZURE_ENV_FIELDS],
        "bedrock_env_fields": bedrock_fields,
        "BEDROCK_ENV_FIELDS": [list(item) for item in BEDROCK_ENV_FIELDS],
        "depth_options": DEPTH_OPTIONS,
        "DEPTH_OPTIONS": DEPTH_OPTIONS,
        "languages": LANGUAGES,
        "LANGUAGES": LANGUAGES,
        "analyst_options": analysts_list,
        "ANALYST_OPTIONS": [list(item) for item in ANALYST_OPTIONS],
        "optional_api_key_providers": sorted(OPTIONAL_API_KEY_PROVIDERS),
        "credential_requirements": reqs,
        "requirements": reqs,
    }


# ── Upstream Status Caching (without importing app.py) ──────────────────────────

_upstream_status_cache: dict[str, Any] | None = None
_upstream_status_cache_time: float = 0.0
_upstream_status_lock = threading.Lock()
UPSTREAM_CACHE_TTL = 3600.0


def _git_output(args: list[str], cwd: Path | None = None, timeout: int = 15) -> str:
    return subprocess.check_output(
        args,
        cwd=cwd,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    ).strip()


def _find_tradingagents_checkout() -> Path | None:
    env_dir = os.environ.get("TRADINGAGENTS_DIR")
    if not env_dir:
        return None
    candidate = Path(env_dir).expanduser().resolve()
    return candidate if (candidate / ".git").exists() else None


def _is_tradingagents_installed() -> bool:
    return importlib.util.find_spec("tradingagents") is not None


def _installed_tradingagents_version() -> str:
    try:
        return importlib.metadata.version("tradingagents")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _latest_remote_tradingagents_tag() -> str:
    try:
        output = _git_output(
            ["git", "ls-remote", "--tags", "--refs", TRADINGAGENTS_REPO_URL, f"refs/tags/{TRADINGAGENTS_TARGET_TAG}"],
            timeout=20,
        )
        return TRADINGAGENTS_TARGET_TAG if output else "unknown"
    except Exception:
        return "unknown"


def _latest_local_checkout_tag(repo_dir: Path) -> str:
    try:
        return _git_output(["git", "describe", "--tags", "--abbrev=0", "HEAD"], cwd=repo_dir, timeout=10)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def _checkout_has_local_changes(repo_dir: Path) -> bool:
    try:
        return bool(_git_output(["git", "status", "--porcelain"], cwd=repo_dir, timeout=10))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return True


def get_upstream_status(force_refresh: bool = False) -> dict[str, Any]:
    """Return TradingAgents upstream compatibility and update status, cached for 1 hour."""
    global _upstream_status_cache, _upstream_status_cache_time

    now = time.time()
    with _upstream_status_lock:
        if (
            not force_refresh
            and _upstream_status_cache is not None
            and (now - _upstream_status_cache_time) < UPSTREAM_CACHE_TTL
        ):
            return dict(_upstream_status_cache)

        checkout = _find_tradingagents_checkout()
        installed = _is_tradingagents_installed()
        installed_version = _installed_tradingagents_version() if installed else "missing"
        compatibility = tradingagents_compatibility(installed_version)

        if checkout:
            local_tag = _latest_local_checkout_tag(checkout)
            res: dict[str, Any] = {
                "mode": "local checkout",
                "path": str(checkout),
                "installed": installed,
                "installed_version": installed_version,
                "local_tag": local_tag,
                "remote_tag": TRADINGAGENTS_TARGET_TAG,
                "dirty": _checkout_has_local_changes(checkout),
                "update_available": False,
                "error": "",
                "notice": (
                    f"Local TradingAgents checkout detected ({local_tag}). "
                    f"This app will not change its branch. Required compatibility: >=0.3.1,<0.4."
                ),
            }
            _upstream_status_cache = res
            _upstream_status_cache_time = now
            return dict(res)

        if compatibility.compatible:
            res = {
                "mode": "installed package",
                "installed": installed,
                "installed_version": installed_version,
                "local_tag": "unknown",
                "remote_tag": TRADINGAGENTS_TARGET_TAG,
                "dirty": False,
                "update_available": False,
                "error": "",
            }
            _upstream_status_cache = res
            _upstream_status_cache_time = now
            return dict(res)

        v_tuple = version_tuple(installed_version)
        if installed and v_tuple and v_tuple >= TRADINGAGENTS_MAX_VERSION:
            res = {
                "mode": "installed package",
                "installed": True,
                "installed_version": installed_version,
                "local_tag": "unknown",
                "remote_tag": TRADINGAGENTS_TARGET_TAG,
                "dirty": False,
                "update_available": False,
                "error": "",
                "notice": compatibility.message,
            }
            _upstream_status_cache = res
            _upstream_status_cache_time = now
            return dict(res)

        try:
            remote_tag = _latest_remote_tradingagents_tag()
        except Exception as exc:
            res = {
                "mode": "installed package",
                "installed": installed,
                "installed_version": installed_version,
                "local_tag": "unknown",
                "remote_tag": "unknown",
                "dirty": False,
                "update_available": False,
                "error": str(exc),
            }
            _upstream_status_cache = res
            _upstream_status_cache_time = now
            return dict(res)

        res = {
            "mode": "installed package",
            "installed": installed,
            "installed_version": installed_version,
            "local_tag": "unknown",
            "remote_tag": remote_tag,
            "dirty": False,
            "update_available": remote_tag == TRADINGAGENTS_TARGET_TAG,
            "error": "",
            "notice": compatibility.message,
        }
        _upstream_status_cache = res
        _upstream_status_cache_time = now
        return dict(res)
