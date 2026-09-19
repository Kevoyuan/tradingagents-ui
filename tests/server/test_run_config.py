"""Tests for run config resolution, credential hierarchy, and runner execution."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from trade_ui.server.event_bus import EventBus
from trade_ui.server.models import RunConfig, RunHeader
from trade_ui.server.run_config import (
    get_effective_api_env_values,
    get_runtime_llm_config,
    missing_required_credentials,
    resolve_run_config,
)
from trade_ui.server.runner import CancellationToken, UpstreamRunner


@pytest.fixture
def temp_prefs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create an isolated temporary preferences and env directory."""
    prefs_dir = tmp_path / ".tradingagents"
    prefs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TRADINGAGENTS_PREFS_DIR", str(prefs_dir))
    monkeypatch.setenv("TRADINGAGENTS_PREFS_FILE", str(prefs_dir / "ui_preferences.json"))
    monkeypatch.setenv("TRADINGAGENTS_ENV_FILE", str(prefs_dir / ".env"))
    # Clear process env of deepseek key for clean testing
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return prefs_dir


def test_missing_required_credentials_detection() -> None:
    # DeepSeek requires DEEPSEEK_API_KEY
    assert "DEEPSEEK_API_KEY" in missing_required_credentials("deepseek", {})
    assert len(missing_required_credentials("deepseek", {"DEEPSEEK_API_KEY": "sk-test"})) == 0

    # Azure requires endpoint, deployment, version, key
    azure_missing = missing_required_credentials("azure", {})
    assert "AZURE_OPENAI_API_KEY" in azure_missing
    assert "AZURE_OPENAI_ENDPOINT" in azure_missing

    # Ollama is optional
    assert len(missing_required_credentials("ollama", {})) == 0


def test_credential_precedence_hierarchy(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Set in process environment
    monkeypatch.setenv("DEEPSEEK_API_KEY", "process-env-key")

    res = get_effective_api_env_values("deepseek")
    assert res["DEEPSEEK_API_KEY"] == "process-env-key"

    # 2. Set in .env file (should take precedence over process env)
    (temp_prefs_dir / ".env").write_text("DEEPSEEK_API_KEY=dotenv-key\n", encoding="utf-8")
    res2 = get_effective_api_env_values("deepseek")
    assert res2["DEEPSEEK_API_KEY"] == "dotenv-key"

    # 3. Explicit sidebar/request value (should take highest precedence)
    res3 = get_effective_api_env_values("deepseek", explicit_values={"DEEPSEEK_API_KEY": "explicit-key"})
    assert res3["DEEPSEEK_API_KEY"] == "explicit-key"


def test_runtime_llm_config_and_backend_url() -> None:
    # DeepSeek Anthropic compatible provider maps to anthropic runtime and injects base url
    provider = "deepseek_anthropic"
    api_values = {"DEEPSEEK_ANTHROPIC_API_KEY": "test-key"}
    runtime_prov, backend_url, runtime_env = get_runtime_llm_config(provider, api_values)

    assert runtime_prov == "anthropic"
    assert backend_url == "https://api.deepseek.com/anthropic"
    assert runtime_env["ANTHROPIC_API_KEY"] == "test-key"
    assert runtime_env["ANTHROPIC_AUTH_TOKEN"] == "test-key"


def test_resolve_run_config_assembles_upstream_config(temp_prefs_dir: Path) -> None:
    # Configure user preferences
    (temp_prefs_dir / ".env").write_text("DEEPSEEK_API_KEY=sk-test-key-1234\n", encoding="utf-8")

    run_config = RunConfig(
        ticker="AAPL",
        provider="deepseek",
        quick_model="deepseek-v4-flash",
        deep_model="deepseek-v4-pro",
        depth=3,
        analysts=["market", "news"],
        config={"output_language": "Chinese"},
    )

    resolved = resolve_run_config(run_config)
    assert resolved.provider == "deepseek"
    assert resolved.runtime_provider == "deepseek"
    assert resolved.quick_model == "deepseek-v4-flash"
    assert resolved.deep_model == "deepseek-v4-pro"
    assert resolved.depth == 3
    assert resolved.language == "Chinese"
    assert resolved.analysts == ["market", "news"]
    assert len(resolved.missing_credentials) == 0

    # Assert upstream_config dict assembled correctly
    cfg = resolved.upstream_config
    assert cfg["llm_provider"] == "deepseek"
    assert cfg["quick_think_llm"] == "deepseek-v4-flash"
    assert cfg["deep_think_llm"] == "deepseek-v4-pro"
    assert cfg["max_debate_rounds"] == 3
    assert cfg["max_risk_discuss_rounds"] == 3
    assert cfg["output_language"] == "Chinese"


def test_anti_regression_run_with_missing_credential_is_rejected(
    tmp_path: Path,
    temp_prefs_dir: Path,
) -> None:
    """Anti-regression requirement:

    A test asserting a run started with a provider whose required credential is absent is
    REJECTED, and that no request is made to upstream defaults (OpenAI).
    """
    # Ensure no DEEPSEEK_API_KEY exists in .env or process environment
    (temp_prefs_dir / ".env").write_text("", encoding="utf-8")

    run_dir = tmp_path / "run-test-reject"
    run_dir.mkdir(parents=True, exist_ok=True)
    event_bus = EventBus(run_dir=run_dir, run_id="test-reject")
    cancel_token = CancellationToken()

    header = RunHeader(
        run_id="test-reject",
        status="pending",
        ticker="NBIS",
        trade_date="2026-09-18",
    )

    run_config = RunConfig(
        ticker="NBIS",
        provider="deepseek",
        quick_model="deepseek-v4-flash",
        deep_model="deepseek-v4-flash",
        use_stub=False,
    )

    on_header_update = MagicMock()

    runner = UpstreamRunner(
        header=header,
        config=run_config,
        event_bus=event_bus,
        cancel_token=cancel_token,
        on_header_update=on_header_update,
    )

    # Patch TradingAgentsGraph to assert it is NEVER called when credentials are missing
    with patch("tradingagents.graph.trading_graph.TradingAgentsGraph") as mock_graph:
        runner.run()
        # Assert TradingAgentsGraph was NEVER instantiated with OpenAI or anything else
        mock_graph.assert_not_called()

    # Assert run was rejected and failed
    assert runner.header.status == "failed"
    assert runner.header.error is not None
    err_msg = runner.header.error["message"]
    assert "Missing required credentials for provider 'deepseek': DEEPSEEK_API_KEY" in err_msg


def test_runner_temporary_environment_restores_process_env(
    tmp_path: Path,
    temp_prefs_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert temporary_environment restores process globals after run."""
    # Set a dummy key in .env
    (temp_prefs_dir / ".env").write_text("DEEPSEEK_API_KEY=sk-injected-for-run\n", encoding="utf-8")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert "DEEPSEEK_API_KEY" not in os.environ

    run_dir = tmp_path / "run-test-env"
    run_dir.mkdir(parents=True, exist_ok=True)
    event_bus = EventBus(run_dir=run_dir, run_id="test-env")
    cancel_token = CancellationToken()

    header = RunHeader(
        run_id="test-env",
        status="pending",
        ticker="AAPL",
        trade_date="2026-05-05",
    )

    run_config = RunConfig(
        ticker="AAPL",
        provider="deepseek",
        quick_model="deepseek-v4-flash",
        deep_model="deepseek-v4-flash",
        use_stub=False,
    )

    captured_env_during_run = {}

    def mock_stream(*args, **kwargs):
        captured_env_during_run["DEEPSEEK_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY")
        return iter([])

    with (
        patch("tradingagents.graph.trading_graph.TradingAgentsGraph"),
        patch("tradingagents_adapter.TradingAgentsAdapter.stream", side_effect=mock_stream),
    ):
        runner = UpstreamRunner(
            header=header,
            config=run_config,
            event_bus=event_bus,
            cancel_token=cancel_token,
            on_header_update=MagicMock(),
        )
        runner.run()

    # During the run, the environment variable was injected
    assert captured_env_during_run.get("DEEPSEEK_API_KEY") == "sk-injected-for-run"

    # After the run, the process environment variable was restored (not present)
    assert "DEEPSEEK_API_KEY" not in os.environ
