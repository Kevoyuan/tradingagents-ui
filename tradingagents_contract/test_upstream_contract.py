"""Upstream contract tests asserting TradingAgents symbols and behavior."""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest


def test_trading_agents_graph_constructor_and_stream(monkeypatch):
    """Assert TradingAgentsGraph constructor signature, .graph.stream, and _run_signature."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-contract-test")

    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Symbol tradingagents.graph.trading_graph.TradingAgentsGraph missing or failed to import: {exc}")

    # Check constructor signature
    init_sig = inspect.signature(TradingAgentsGraph.__init__)
    expected_params = ["selected_analysts", "debug", "config", "callbacks"]
    for param in expected_params:
        assert param in init_sig.parameters, (
            f"Symbol TradingAgentsGraph.__init__ missing expected parameter '{param}'"
        )

    # Check _run_signature method
    assert hasattr(TradingAgentsGraph, "_run_signature"), (
        "Symbol TradingAgentsGraph._run_signature missing from TradingAgentsGraph class"
    )
    assert callable(TradingAgentsGraph._run_signature), (
        "Symbol TradingAgentsGraph._run_signature is not callable"
    )

    # Instantiate graph and verify graph.stream
    graph_inst = TradingAgentsGraph(config=DEFAULT_CONFIG)
    assert hasattr(graph_inst, "graph"), "TradingAgentsGraph instance missing .graph attribute"
    assert hasattr(graph_inst.graph, "stream"), "TradingAgentsGraph.graph missing .stream attribute"
    assert callable(graph_inst.graph.stream), "TradingAgentsGraph.graph.stream is not callable"

    # Verify _run_signature produces non-empty string
    sig = graph_inst._run_signature("stock")
    assert isinstance(sig, str) and sig, "TradingAgentsGraph._run_signature did not return a valid string"


def test_graph_propagator_create_initial_state(monkeypatch):
    """Assert create_initial_state signature and payload shape on propagator."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-contract-test")

    try:
        from tradingagents.graph.propagation import Propagator
        from tradingagents.graph.trading_graph import TradingAgentsGraph
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Propagator or TradingAgentsGraph failed to import: {exc}")

    # Check class signature
    sig = inspect.signature(Propagator.create_initial_state)
    expected_params = ["company_name", "trade_date", "asset_type", "past_context", "instrument_context"]
    for param in expected_params:
        assert param in sig.parameters, (
            f"Symbol Propagator.create_initial_state missing expected parameter '{param}'"
        )

    # Check instance propagator
    from tradingagents.default_config import DEFAULT_CONFIG

    graph_inst = TradingAgentsGraph(config=DEFAULT_CONFIG)
    assert hasattr(graph_inst, "propagator"), "TradingAgentsGraph instance missing .propagator attribute"
    assert hasattr(graph_inst.propagator, "create_initial_state"), (
        "TradingAgentsGraph.propagator missing .create_initial_state attribute"
    )

    state = graph_inst.propagator.create_initial_state(
        company_name="AAPL",
        trade_date="2026-05-01",
        asset_type="stock",
        past_context="",
        instrument_context="AAPL stock",
    )
    assert isinstance(state, dict), "create_initial_state must return a dict"
    for expected_key in [
        "messages",
        "company_of_interest",
        "trade_date",
        "investment_debate_state",
        "risk_debate_state",
        "market_report",
        "fundamentals_report",
        "sentiment_report",
        "news_report",
    ]:
        assert expected_key in state, f"create_initial_state return dict missing key '{expected_key}'"


def test_graph_workflow_compile(monkeypatch):
    """Assert graph.workflow.compile(checkpointer=...) exists and behaves as expected."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-contract-test")

    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    graph_inst = TradingAgentsGraph(config=DEFAULT_CONFIG)
    assert hasattr(graph_inst, "workflow"), "TradingAgentsGraph instance missing .workflow attribute"
    assert hasattr(graph_inst.workflow, "compile"), "TradingAgentsGraph.workflow missing .compile attribute"
    assert callable(graph_inst.workflow.compile), "TradingAgentsGraph.workflow.compile is not callable"

    compile_sig = inspect.signature(graph_inst.workflow.compile)
    assert "checkpointer" in compile_sig.parameters, (
        "TradingAgentsGraph.workflow.compile signature missing parameter 'checkpointer'"
    )

    compiled = graph_inst.workflow.compile(checkpointer=None)
    assert hasattr(compiled, "stream"), "Compiled graph missing .stream method"
    assert callable(compiled.stream), "Compiled graph .stream is not callable"


def test_write_report_tree_directory_structure(tmp_path: Path):
    """Assert write_report_tree produces the 1_analysts/2_research/3_trading/4_risk/5_portfolio directory structure."""
    try:
        from tradingagents.reporting import write_report_tree
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Symbol tradingagents.reporting.write_report_tree missing: {exc}")

    assert callable(write_report_tree), "tradingagents.reporting.write_report_tree is not callable"

    reports_dir = tmp_path / "reports"
    final_state = {
        "market_report": "# Market Report\nAnalysis details",
        "sentiment_report": "# Sentiment Report\nSentiment details",
        "news_report": "# News Report\nNews details",
        "fundamentals_report": "# Fundamentals Report\nFundamentals details",
        "investment_debate_state": {
            "bull_history": "Bull hypothesis",
            "bear_history": "Bear thesis",
            "judge_decision": "Research manager decision",
        },
        "trader_investment_plan": "Execute long order",
        "risk_debate_state": {
            "aggressive_history": "Aggressive stance",
            "conservative_history": "Conservative stance",
            "neutral_history": "Neutral stance",
            "judge_decision": "**Rating**: Underweight\nTarget: 194.0",
        },
    }

    result_path = write_report_tree(final_state, "TEST", reports_dir)
    assert Path(result_path).is_file(), f"write_report_tree return path does not exist: {result_path}"

    # 1. Analysts
    analysts_dir = reports_dir / "1_analysts"
    assert analysts_dir.is_dir(), "Missing 1_analysts directory"
    for name in ["market.md", "sentiment.md", "news.md", "fundamentals.md"]:
        f = analysts_dir / name
        assert f.is_file(), f"Missing file 1_analysts/{name}"
        assert len(f.read_text(encoding="utf-8")) > 0

    # 2. Research
    research_dir = reports_dir / "2_research"
    assert research_dir.is_dir(), "Missing 2_research directory"
    for name in ["bull.md", "bear.md", "manager.md"]:
        f = research_dir / name
        assert f.is_file(), f"Missing file 2_research/{name}"
        assert len(f.read_text(encoding="utf-8")) > 0

    # 3. Trading
    trading_dir = reports_dir / "3_trading"
    assert trading_dir.is_dir(), "Missing 3_trading directory"
    trader_file = trading_dir / "trader.md"
    assert trader_file.is_file(), "Missing file 3_trading/trader.md"
    assert len(trader_file.read_text(encoding="utf-8")) > 0

    # 4. Risk
    risk_dir = reports_dir / "4_risk"
    assert risk_dir.is_dir(), "Missing 4_risk directory"
    for name in ["aggressive.md", "conservative.md", "neutral.md"]:
        f = risk_dir / name
        assert f.is_file(), f"Missing file 4_risk/{name}"
        assert len(f.read_text(encoding="utf-8")) > 0

    # 5. Portfolio
    portfolio_dir = reports_dir / "5_portfolio"
    assert portfolio_dir.is_dir(), "Missing 5_portfolio directory"
    decision_file = portfolio_dir / "decision.md"
    assert decision_file.is_file(), "Missing file 5_portfolio/decision.md"
    assert len(decision_file.read_text(encoding="utf-8")) > 0

    # Complete report
    complete_report = reports_dir / "complete_report.md"
    assert complete_report.is_file(), "Missing complete_report.md"
    assert len(complete_report.read_text(encoding="utf-8")) > 0


def test_safe_ticker_component():
    """Assert tradingagents.dataflows.utils.safe_ticker_component exists and works."""
    try:
        from tradingagents.dataflows.utils import safe_ticker_component
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Symbol tradingagents.dataflows.utils.safe_ticker_component missing: {exc}")

    assert callable(safe_ticker_component), "safe_ticker_component is not callable"
    assert safe_ticker_component("AAPL") == "AAPL"
    assert safe_ticker_component("BTC-USD") == "BTC-USD"


def test_model_catalog_contract():
    """Assert tradingagents.llm_clients.model_catalog.MODEL_OPTIONS exists."""
    try:
        from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Symbol tradingagents.llm_clients.model_catalog.MODEL_OPTIONS missing: {exc}")

    assert isinstance(MODEL_OPTIONS, dict), "MODEL_OPTIONS must be a dict"
    for provider in ["openai", "anthropic"]:
        assert provider in MODEL_OPTIONS, f"Expected provider '{provider}' missing from MODEL_OPTIONS"


def test_provider_api_key_env_contract():
    """Assert tradingagents.llm_clients.api_key_env.PROVIDER_API_KEY_ENV exists."""
    try:
        from tradingagents.llm_clients.api_key_env import PROVIDER_API_KEY_ENV
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Symbol tradingagents.llm_clients.api_key_env.PROVIDER_API_KEY_ENV missing: {exc}")

    assert isinstance(PROVIDER_API_KEY_ENV, dict), "PROVIDER_API_KEY_ENV must be a dict"
    assert "openai" in PROVIDER_API_KEY_ENV, "Missing 'openai' in PROVIDER_API_KEY_ENV"
    assert PROVIDER_API_KEY_ENV["openai"] == "OPENAI_API_KEY"


def test_ratings_contract():
    """Assert tradingagents.agents.utils.rating.RATINGS_5_TIER and parse_rating exist."""
    try:
        from tradingagents.agents.utils.rating import RATINGS_5_TIER, parse_rating
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Symbols RATINGS_5_TIER or parse_rating missing from tradingagents.agents.utils.rating: {exc}")

    assert isinstance(RATINGS_5_TIER, tuple | list), "RATINGS_5_TIER must be a tuple or list"
    expected = ("Buy", "Overweight", "Hold", "Underweight", "Sell")
    assert tuple(RATINGS_5_TIER) == expected, f"RATINGS_5_TIER mismatch: {RATINGS_5_TIER} != {expected}"

    assert callable(parse_rating), "parse_rating is not callable"
    assert parse_rating("**Rating**: Buy") == "Buy"
    assert parse_rating("**Rating**: Underweight") == "Underweight"
    assert parse_rating("**Rating**: Hold") == "Hold"


def test_cli_stats_handler_contract():
    """Assert cli.stats_handler.StatsCallbackHandler exists and is importable without PYTHONPATH shadowing."""
    pythonpath = os.environ.get("PYTHONPATH")

    # Step 1: Import top-level cli package
    try:
        import cli
    except (ImportError, ModuleNotFoundError) as exc:
        msg = f"Failed to import upstream 'cli' package: {exc}."
        if pythonpath:
            msg += f" Global PYTHONPATH is set ({pythonpath}) which may shadow upstream's 'cli' package."
        pytest.fail(msg)

    # Step 2: Import cli.stats_handler
    try:
        import cli.stats_handler
        from cli.stats_handler import StatsCallbackHandler
    except (ImportError, ModuleNotFoundError) as exc:
        cli_file = getattr(cli, "__file__", "unknown")
        msg = (
            f"Failed to import StatsCallbackHandler from cli.stats_handler: {exc}. "
            f"'cli' package was resolved to '{cli_file}'. "
            "Upstream TradingAgents ships a top-level 'cli' package. "
        )
        if pythonpath:
            msg += f"Global PYTHONPATH is set to '{pythonpath}'; unset PYTHONPATH to avoid shadowing upstream's cli."
        else:
            msg += "Check if a local directory named 'cli' is shadowing the upstream package."
        pytest.fail(msg)

    assert inspect.isclass(StatsCallbackHandler), "StatsCallbackHandler is not a class"


def test_stream_mode_is_values():
    """The run monitor's agent attribution assumes the stream is full state.

    Upstream runs with stream_mode="values", so every chunk is a complete
    AgentState and there are no node-keyed chunks. Attribution therefore reads
    state field transitions. If upstream switches to "updates" the chunks become
    {node: delta} and every message goes out unattributed again: all rows render
    as "System" and the roster and stage rail stay at zero. That failure shipped
    three times before the assumption was written down here.
    """
    monkeypatch_env = {"OPENAI_API_KEY": "sk-contract-test"}
    previous = {k: os.environ.get(k) for k in monkeypatch_env}
    os.environ.update(monkeypatch_env)
    try:
        from tradingagents.graph.propagation import Propagator
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"Propagator missing or failed to import: {exc}")
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    args = Propagator().get_graph_args()
    assert args.get("stream_mode") == "values", (
        "get_graph_args() no longer returns stream_mode='values' "
        f"(got {args.get('stream_mode')!r}). Agent attribution reads state fields, "
        "not node keys; revisit trade_ui/server/runner.py before bumping upstream."
    )


def test_agent_state_fields_used_for_attribution():
    """Attribution keys on these AgentState fields; a rename breaks it silently."""
    try:
        from tradingagents.agents.utils.agent_states import AgentState
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"agent_states.AgentState missing or failed to import: {exc}")

    annotations = set(getattr(AgentState, "__annotations__", {}))
    required = {
        "messages",
        "market_report",
        "sentiment_report",
        "news_report",
        "fundamentals_report",
        "investment_debate_state",
        "investment_plan",
        "trader_investment_plan",
        "risk_debate_state",
        "final_trade_decision",
    }
    missing = sorted(required - annotations)
    assert not missing, (
        f"AgentState no longer declares {missing}. trade_ui/server/runner.py maps "
        "these fields to agents and publishes report_section events from them."
    )


def test_debate_state_latest_speaker_values():
    """Debate attribution follows latest_speaker, so its value set is a contract."""
    import pathlib as _pathlib

    try:
        import tradingagents.agents as agents_pkg
    except (ImportError, ModuleNotFoundError) as exc:
        pytest.fail(f"tradingagents.agents missing or failed to import: {exc}")

    root = _pathlib.Path(agents_pkg.__file__).parent
    texts = [
        p.read_text(encoding="utf-8", errors="replace")
        for p in root.rglob("*.py")
        if p.name
        in {
            "aggressive_debator.py",
            "neutral_debator.py",
            "conservative_debator.py",
            "portfolio_manager.py",
            "research_manager.py",
        }
    ]
    assert texts, "none of the debate/manager source files were found to inspect"

    joined = "\n".join(texts)
    required = {"Aggressive", "Neutral", "Conservative", "Judge"}
    missing = sorted(v for v in required if f'"latest_speaker": "{v}"' not in joined)
    assert not missing, (
        f"latest_speaker values {missing} no longer appear in the debate/manager "
        "sources. runner.py's debate_speakers map depends on them."
    )
