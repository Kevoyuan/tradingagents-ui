"""Backward-compatible provider preference migrations."""

from __future__ import annotations

from typing import Any

PROVIDER_SCHEMA_VERSION = 2


def migrate_provider_preferences(prefs: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    migrated = dict(prefs)
    if int(migrated.get("provider_schema_version", 0) or 0) >= PROVIDER_SCHEMA_VERSION:
        return migrated, []

    notes: list[str] = []
    aliases = {"kimi": "kimi_coding", "custom_openai": "openai_compatible"}
    old_provider = str(migrated.get("llm_provider", ""))
    if old_provider in aliases:
        migrated["llm_provider"] = aliases[old_provider]
        notes.append(f"Migrated provider {old_provider} to {aliases[old_provider]}.")

    for key in ("provider_model_profiles", "api_key_profiles"):
        profiles = dict(migrated.get(key, {}) or {})
        for old, new in aliases.items():
            if old in profiles and new not in profiles:
                profiles[new] = profiles.pop(old)
        migrated[key] = profiles

    migrated["provider_schema_version"] = PROVIDER_SCHEMA_VERSION
    return migrated, notes
