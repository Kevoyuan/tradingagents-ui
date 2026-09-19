"""Tests for credentials API, secrets redaction, and preferences persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_prefs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create an isolated temporary preferences and env directory for tests."""
    prefs_dir = tmp_path / ".tradingagents"
    prefs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TRADINGAGENTS_PREFS_DIR", str(prefs_dir))
    monkeypatch.setenv("TRADINGAGENTS_PREFS_FILE", str(prefs_dir / "ui_preferences.json"))
    monkeypatch.setenv("TRADINGAGENTS_ENV_FILE", str(prefs_dir / ".env"))
    return prefs_dir


def test_get_credentials_surfaces_saved_preferences_and_redacts_secrets(
    client: TestClient,
    temp_prefs_dir: Path,
) -> None:
    # 1. Write a temporary ui_preferences.json with known preferences and a secret in api_key_profiles
    secret_deepseek_key = "sk-super-secret-key-123456789"
    secret_openai_key = "sk-openai-secret-abcdefghij"
    unrelated_key = "SOME_UNRELATED_KEY_FOR_OTHER_TOOL"
    unrelated_val = "unrelated-value-should-be-kept"

    prefs_data = {
        "ticker": "NBIS",
        "output_language": "Chinese",
        "analysts": ["market", "social", "news", "fundamentals"],
        "depth_key": "Deep (5 rounds)",
        "llm_provider": "deepseek",
        "quick_think_llm": "deepseek-v4-flash",
        "deep_think_llm": "deepseek-v4-flash",
        "provider_model_profiles": {
            "deepseek": {
                "quick": "deepseek-v4-flash",
                "deep": "deepseek-v4-flash",
            }
        },
        "advanced_settings": {
            "checkpoint_enabled": False,
            "temperature": 0.7,
        },
        "data_vendors": {
            "core_stock_apis": "yfinance",
        },
        "api_key_profiles": {
            "deepseek": {
                "deepseek|quick:deepseek-v4-flash|deep:deepseek-v4-flash": secret_deepseek_key,
            }
        },
    }
    (temp_prefs_dir / "ui_preferences.json").write_text(json.dumps(prefs_data), encoding="utf-8")

    # 2. Write a temporary .env with real secrets and an unrelated key
    env_lines = [
        f"DEEPSEEK_API_KEY={secret_deepseek_key}\n",
        f"OPENAI_API_KEY={secret_openai_key}\n",
        f"{unrelated_key}={unrelated_val}\n",
    ]
    (temp_prefs_dir / ".env").write_text("".join(env_lines), encoding="utf-8")

    # 3. Call GET /api/credentials
    res = client.get("/api/credentials")
    assert res.status_code == 200
    data = res.json()

    # Assert saved preferences are surfaced
    assert data["ticker"] == "NBIS"
    assert data["output_language"] == "Chinese"
    assert data["analysts"] == ["market", "social", "news", "fundamentals"]
    assert data["depth_key"] == "Deep (5 rounds)"
    assert data["llm_provider"] == "deepseek"
    assert data["quick_think_llm"] == "deepseek-v4-flash"
    assert data["deep_think_llm"] == "deepseek-v4-flash"
    assert data["advanced_settings"]["temperature"] == 0.7
    assert data["data_vendors"]["core_stock_apis"] == "yfinance"

    # Assert credentials status
    creds = data["credentials"]
    assert creds["DEEPSEEK_API_KEY"]["is_set"] is True
    assert creds["DEEPSEEK_API_KEY"]["is_secret"] is True
    # Masked hint only
    assert "sk-" in creds["DEEPSEEK_API_KEY"]["hint"]
    assert "••••" in creds["DEEPSEEK_API_KEY"]["hint"]

    # ANTI-REGRESSION: The raw text response must NEVER contain the secret keys!
    raw_response_text = res.text
    assert secret_deepseek_key not in raw_response_text
    assert secret_openai_key not in raw_response_text


def test_put_credentials_preserves_unrelated_keys_and_updates_env(
    client: TestClient,
    temp_prefs_dir: Path,
) -> None:
    # 1. Initialize .env with an unrelated key
    unrelated_line = "CUSTOM_TOOL_SECRET=keep-this-unrelated-content\n"
    (temp_prefs_dir / ".env").write_text(unrelated_line, encoding="utf-8")

    # 2. Call PUT /api/credentials to update ticker and set an API key
    payload = {
        "ticker": "TSLA",
        "output_language": "English",
        "credentials": {
            "DEEPSEEK_API_KEY": "sk-new-deepseek-key-12345678",
        },
    }
    res = client.put("/api/credentials", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["ticker"] == "TSLA"
    assert data["output_language"] == "English"
    assert data["credentials"]["DEEPSEEK_API_KEY"]["is_set"] is True

    # Check that .env has preserved the unrelated key
    env_content = (temp_prefs_dir / ".env").read_text(encoding="utf-8")
    assert "CUSTOM_TOOL_SECRET=keep-this-unrelated-content" in env_content
    assert "DEEPSEEK_API_KEY" in env_content
    assert "sk-new-deepseek-key-12345678" in env_content

    # Check that ui_preferences.json has updated ticker
    prefs_content = json.loads((temp_prefs_dir / "ui_preferences.json").read_text(encoding="utf-8"))
    assert prefs_content["ticker"] == "TSLA"
