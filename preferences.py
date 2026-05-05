"""Persistent user preferences for the TradingAgents UI."""

import json
from pathlib import Path
from typing import Any, Optional

PREFS_DIR = Path.home() / ".tradingagents"
PREFS_FILE = PREFS_DIR / "ui_preferences.json"


def _ensure_dir():
    PREFS_DIR.mkdir(parents=True, exist_ok=True)


def load_preferences() -> dict:
    """Load preferences from disk. Returns empty dict if file missing/corrupt."""
    try:
        if PREFS_FILE.exists():
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_preferences(prefs: dict):
    """Save preferences to disk."""
    _ensure_dir()
    PREFS_FILE.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")


def get_preference(key: str, fallback: Any = None) -> Any:
    """Get a single preference value."""
    return load_preferences().get(key, fallback)


def set_preference(key: str, value: Any):
    """Set a single preference value and save."""
    prefs = load_preferences()
    prefs[key] = value
    save_preferences(prefs)


def save_run_config(config: dict):
    """Save the full run configuration as preferences."""
    save_preferences(config)
