"""Credential persistence, redaction, and environment file management."""

from __future__ import annotations

import contextlib
import copy
import json
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key, unset_key

import preferences
from ui_config import (
    AZURE_ENV_FIELDS,
    BEDROCK_ENV_FIELDS,
    PROVIDER_API_KEY_ENV,
    PROVIDER_BASE_URL_ENV,
)

# Tuple of all managed env vars that the UI or server might configure
MANAGED_ENV_NAMES = tuple(
    dict.fromkeys(
        env_name
        for env_name in [
            *PROVIDER_API_KEY_ENV.values(),
            *PROVIDER_BASE_URL_ENV.values(),
            *(env_name for env_name, _, _ in AZURE_ENV_FIELDS),
            *(env_name for env_name, _, _, _ in BEDROCK_ENV_FIELDS),
            "ALPHA_VANTAGE_API_KEY",
            "FRED_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "CUSTOM_OPENAI_API_KEY",
            "CUSTOM_OPENAI_BASE_URL",
        ]
        if env_name
    )
)

SECRET_KEY_SUBSTRINGS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH")
NON_SECRET_KEYS = {
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "OPENAI_API_VERSION",
    "AWS_DEFAULT_REGION",
    "AWS_PROFILE",
}


def get_prefs_dir() -> Path:
    """Return configured or default preferences directory."""
    env_dir = os.environ.get("TRADINGAGENTS_PREFS_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return preferences.PREFS_DIR


def get_prefs_file() -> Path:
    """Return configured or default preferences JSON file."""
    env_file = os.environ.get("TRADINGAGENTS_PREFS_FILE")
    if env_file:
        return Path(env_file).expanduser().resolve()
    return get_prefs_dir() / "ui_preferences.json"


def get_env_file() -> Path:
    """Return configured or default credentials .env file."""
    env_file = os.environ.get("TRADINGAGENTS_ENV_FILE")
    if env_file:
        return Path(env_file).expanduser().resolve()
    return get_prefs_dir() / ".env"


def is_secret(key: str) -> bool:
    """Determine if an environment variable key represents a sensitive secret."""
    if key in NON_SECRET_KEYS:
        return False
    if "BASE_URL" in key or "ENDPOINT" in key or "REGION" in key or "PROFILE" in key:
        return False
    upper = key.upper()
    return any(s in upper for s in SECRET_KEY_SUBSTRINGS)


def mask_secret(value: str) -> str:
    """Create a masked hint for a secret value without exposing the secret."""
    val = str(value or "").strip()
    if not val:
        return ""
    if len(val) <= 8:
        return "••••••••"
    prefix = val[:3]
    suffix = val[-4:]
    return f"{prefix}••••••••{suffix}"


def load_saved_preferences() -> dict[str, Any]:
    """Load user preferences from the active preferences file."""
    prefs_file = get_prefs_file()
    try:
        if prefs_file.exists():
            return json.loads(prefs_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    if prefs_file == preferences.PREFS_FILE:
        return preferences.load_preferences()
    return {}


def save_saved_preferences(prefs: dict[str, Any]) -> None:
    """Save user preferences to the active preferences file."""
    prefs_file = get_prefs_file()
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    prefs_file.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")


def load_saved_env() -> dict[str, str]:
    """Load persisted credentials from the UI-owned .env file."""
    env_file = get_env_file()
    try:
        if not env_file.exists():
            return {}
        raw_values = dotenv_values(str(env_file))
        return {
            str(k): str(v).strip()
            for k, v in raw_values.items()
            if v is not None and str(v).strip()
        }
    except OSError:
        return {}


def _redact_secrets_in_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask any values under api_key_profiles or secret keys."""
    res = copy.deepcopy(d)
    if "api_key_profiles" in res and isinstance(res["api_key_profiles"], dict):
        for _prov, profs in res["api_key_profiles"].items():
            if isinstance(profs, dict):
                for prof_id, key_val in profs.items():
                    if key_val:
                        profs[prof_id] = mask_secret(key_val)
    return res


def get_credentials_response() -> dict[str, Any]:
    """Return stored preferences and credential status with secrets strictly redacted."""
    raw_prefs = load_saved_preferences()
    saved_env = load_saved_env()

    # Redact any secrets inside ui_preferences.json
    prefs = _redact_secrets_in_dict(raw_prefs)

    credentials_map: dict[str, dict[str, Any]] = {}
    for env_name in MANAGED_ENV_NAMES:
        raw_val = saved_env.get(env_name, "")
        secret = is_secret(env_name)
        is_set = bool(raw_val)

        if not is_set:
            credentials_map[env_name] = {
                "is_set": False,
                "is_secret": secret,
                "hint": "",
            }
        elif secret:
            credentials_map[env_name] = {
                "is_set": True,
                "is_secret": True,
                "hint": mask_secret(raw_val),
            }
        else:
            credentials_map[env_name] = {
                "is_set": True,
                "is_secret": False,
                "hint": raw_val,
                "value": raw_val,
            }

    # Extract standard preferences with defaults matching app.py
    ticker = str(prefs.get("ticker", "NBIS"))
    output_language = str(prefs.get("output_language", "English"))
    analysts = prefs.get("analysts", ["market", "social", "news", "fundamentals"])
    depth_key = str(prefs.get("depth_key", "Deep (5 rounds)"))
    llm_provider = str(prefs.get("llm_provider", "deepseek"))
    quick_think_llm = str(prefs.get("quick_think_llm", ""))
    deep_think_llm = str(prefs.get("deep_think_llm", ""))
    provider_model_profiles = prefs.get("provider_model_profiles", {})
    advanced_settings = prefs.get("advanced_settings", {})
    data_vendors = prefs.get("data_vendors", {})

    return {
        "ticker": ticker,
        "output_language": output_language,
        "analysts": analysts,
        "depth_key": depth_key,
        "llm_provider": llm_provider,
        "quick_think_llm": quick_think_llm,
        "deep_think_llm": deep_think_llm,
        "provider_model_profiles": provider_model_profiles,
        "advanced_settings": advanced_settings,
        "data_vendors": data_vendors,
        "preferences": prefs,
        "credentials": credentials_map,
    }


def save_credentials(data: dict[str, Any]) -> dict[str, Any]:
    """Update preferences and save credentials to .env, preserving unrelated keys."""
    # 1. Update preferences
    existing_prefs = load_saved_preferences()

    pref_keys = [
        "ticker",
        "output_language",
        "analysts",
        "depth_key",
        "llm_provider",
        "quick_think_llm",
        "deep_think_llm",
        "provider_model_profiles",
        "advanced_settings",
        "data_vendors",
        "provider_schema_version",
    ]

    for k in pref_keys:
        if k in data:
            existing_prefs[k] = data[k]

    if "preferences" in data and isinstance(data["preferences"], dict):
        for k, v in data["preferences"].items():
            if k != "api_key_profiles":  # Do not overwrite profiles with redacted values
                existing_prefs[k] = v

    save_saved_preferences(existing_prefs)

    # 2. Update .env file
    env_file = get_env_file()
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.touch(exist_ok=True)
    with contextlib.suppress(OSError):
        os.chmod(env_file, 0o600)

    # Collect credential updates from "credentials" or "env" or root data
    cred_updates: dict[str, Any] = {}
    if "credentials" in data and isinstance(data["credentials"], dict):
        cred_updates.update(data["credentials"])
    if "env" in data and isinstance(data["env"], dict):
        cred_updates.update(data["env"])

    # Also check if any managed env names are directly at top level
    for env_name in MANAGED_ENV_NAMES:
        if env_name in data:
            cred_updates[env_name] = data[env_name]

    clear_keys = set(data.get("clear_keys", []))

    for env_name, new_val in cred_updates.items():
        if not isinstance(env_name, str):
            continue
        env_name = env_name.strip()
        if not env_name:
            continue

        if isinstance(new_val, dict):
            new_val = new_val.get("value", "")

        val_str = str(new_val or "").strip()

        # Never overwrite an existing secret with a masked hint or placeholder
        if "••••" in val_str or val_str.startswith("••"):
            continue

        if val_str:
            set_key(str(env_file), env_name, val_str, quote_mode="always")
        elif env_name in clear_keys:
            unset_key(str(env_file), env_name)

    return get_credentials_response()
