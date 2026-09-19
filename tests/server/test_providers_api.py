"""Tests for provider catalog, credential requirements, and upstream compatibility API."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_providers_catalog(client: TestClient) -> None:
    res = client.get("/api/providers")
    assert res.status_code == 200
    data = res.json()

    # 1. Assert deepseek is in providers
    providers = data["providers"]
    provider_ids = [p["id"] for p in providers]
    assert "deepseek" in provider_ids
    assert "openai" in provider_ids
    assert "anthropic" in provider_ids

    # 2. Check catalog structure
    assert "provider_model_options" in data
    assert "upstream_model_options" in data
    assert "provider_api_key_env" in data
    assert "provider_base_url_env" in data
    assert "azure_env_fields" in data
    assert "bedrock_env_fields" in data
    assert "depth_options" in data
    assert "languages" in data
    assert "analyst_options" in data

    # 3. Check credential requirements
    reqs = data["credential_requirements"]
    assert "deepseek" in reqs
    assert "DEEPSEEK_API_KEY" in reqs["deepseek"]["required"]
    assert len(reqs["deepseek"]["optional"]) == 0

    assert "openai_compatible" in reqs
    assert "OPENAI_COMPATIBLE_BASE_URL" in reqs["openai_compatible"]["required"]

    assert "ollama" in reqs
    # Ollama has optional api key and default url
    assert "OLLAMA_API_KEY" in reqs["ollama"]["optional"] or len(reqs["ollama"]["required"]) == 0

    assert "azure" in reqs
    assert "AZURE_OPENAI_ENDPOINT" in reqs["azure"]["required"]


def test_get_upstream_status(client: TestClient) -> None:
    res = client.get("/api/upstream")
    assert res.status_code == 200
    data = res.json()

    assert "mode" in data
    assert "installed" in data
    assert "installed_version" in data
    assert "remote_tag" in data
    assert "update_available" in data
