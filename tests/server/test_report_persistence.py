"""The runner must persist the report tree that the Reports screen reads.

Regression: the streaming runner published `report_section` events, so the
Monitor's report counter advanced and the run looked complete, but it never
called the report writer. Upstream never calls `write_report_tree` on its own —
the retired Streamlit app was the only caller — so completed analyses never
reached `logs/<TICKER>/<DATE>/reports/`. The Reports screen could therefore only
ever show reports left behind by the old app, and a fresh run was silently
invisible there.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trade_ui.report_index import list_reports
from trade_ui.server.event_bus import EventBus
from trade_ui.server.models import RunConfig, RunHeader
from trade_ui.server.runner import CancellationToken, UpstreamRunner

# Keyed exactly as upstream's live AgentState is: the Portfolio Manager
# decision reaches section V through `risk_debate_state.judge_decision`, and
# the trader's plan lives in `trader_investment_plan`. (The JSON state *log*
# renames that second key to `trader_investment_decision`, which is a trap when
# reconstructing a report from a log — see _log_state upstream.)
FINAL_STATE: dict = {
    "company_of_interest": "SNDK",
    "trade_date": "2026-09-19",
    "market_report": "## Market\n\nPrice above all key averages.",
    "sentiment_report": "## Sentiment\n\nNeutral.",
    "news_report": "## News\n\nQuiet into the index inclusion.",
    "fundamentals_report": "## Fundamentals\n\nSolid.",
    "investment_debate_state": {
        "bull_history": "Bull case.",
        "bear_history": "Bear case.",
        "judge_decision": "Research manager plan.",
    },
    "trader_investment_plan": "**Action**: Buy",
    "risk_debate_state": {
        "aggressive_history": "Aggressive case.",
        "conservative_history": "Conservative case.",
        "neutral_history": "Neutral case.",
        "judge_decision": (
            "**Rating**: Underweight\n\n"
            "**Executive Summary**: Trim into strength.\n\n"
            "**Price Target**: 1650.0"
        ),
    },
    "final_trade_decision": "**Rating**: Underweight",
}


def _runner(tmp_path: Path, logs_dir: Path) -> UpstreamRunner:
    header = RunHeader(run_id="persist01", status="running", ticker="SNDK", trade_date="2026-09-19")
    return UpstreamRunner(
        header=header,
        config=RunConfig(ticker="SNDK", trade_date="2026-09-19"),
        event_bus=EventBus(run_dir=tmp_path / "run", run_id=header.run_id),
        cancel_token=CancellationToken(),
        on_header_update=lambda _header: None,
        logs_dir=logs_dir,
    )


def test_completed_run_writes_a_report_the_index_can_read(tmp_path: Path) -> None:
    """Write and read are wired to the same tree, which is what was broken."""
    logs_dir = tmp_path / "logs"
    _runner(tmp_path, logs_dir)._persist_reports(FINAL_STATE, "deepseek-v4-flash")

    report_dir = logs_dir / "SNDK" / "2026-09-19" / "reports"
    assert (report_dir / "complete_report.md").is_file()
    assert (report_dir / "1_analysts" / "market.md").is_file()
    assert (report_dir / "3_trading" / "trader.md").is_file()
    assert (report_dir / "5_portfolio" / "decision.md").is_file()
    # The model-specific copy is the naming convention the archive already uses.
    assert (report_dir / "complete_report__deep-deepseek-v4-flash.md").is_file()

    summaries = list_reports(logs_dir=logs_dir)
    assert [(summary.ticker, summary.trade_date) for summary in summaries] == [("SNDK", "2026-09-19")]
    # The verdict comes from 5_portfolio/decision.md, so seeing it here proves the
    # whole path travelled: runner -> writer -> disk -> reader.
    assert summaries[0].verdict is not None
    assert summaries[0].verdict.rating == "Underweight"


def test_blank_state_writes_no_report(tmp_path: Path) -> None:
    """A cancelled or failed run must not leave a fabricated report behind."""
    logs_dir = tmp_path / "logs"
    _runner(tmp_path, logs_dir)._persist_reports({}, "deepseek-v4-flash")
    assert not (logs_dir / "SNDK").exists()


def test_write_failure_does_not_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The analysis succeeded even if its report cannot be written."""
    import reporting_adapter

    def explode(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(reporting_adapter, "save_ui_reports", explode)
    _runner(tmp_path, tmp_path / "logs")._persist_reports(FINAL_STATE, "deepseek-v4-flash")


def test_completed_run_writes_reports_without_being_asked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive the real completion path so deleting the call site fails here.

    Testing `_persist_reports` alone would still pass if the runner stopped
    calling it, which is precisely the regression: the writer existed and
    worked, nothing invoked it.
    """
    import tradingagents.graph.trading_graph as graph_module

    import trade_ui.server.run_config as run_config_module
    import tradingagents_adapter
    from trade_ui.server.run_config import ResolvedRunConfig

    logs_dir = tmp_path / "logs"
    resolved = ResolvedRunConfig(
        provider="deepseek",
        runtime_provider="deepseek",
        backend_url=None,
        quick_model="deepseek-v4-flash",
        deep_model="deepseek-v4-flash",
        depth=1,
        language="English",
        analysts=["market"],
        data_vendors={},
        advanced_settings={},
        runtime_env_values={},
        upstream_config={"results_dir": str(logs_dir)},
        missing_credentials=[],
    )
    monkeypatch.setattr(run_config_module, "resolve_run_config", lambda _config: resolved)
    monkeypatch.setattr(graph_module, "TradingAgentsGraph", lambda *a, **k: object())

    class FakeAdapter:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def stream(self, _ticker, _trade_date, asset_type: str = "stock"):
            yield {"company_of_interest": "SNDK", "trade_date": "2026-09-19", "asset_type": asset_type, **FINAL_STATE}

    monkeypatch.setattr(tradingagents_adapter, "TradingAgentsAdapter", FakeAdapter)

    runner = _runner(tmp_path, logs_dir)
    runner.run()

    assert runner.header.status == "completed"
    assert (logs_dir / "SNDK" / "2026-09-19" / "reports" / "complete_report.md").is_file()


def test_cancelled_run_writes_no_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A cancelled run is not a result; it must not leave a half-report behind."""
    import tradingagents.graph.trading_graph as graph_module

    import trade_ui.server.run_config as run_config_module
    import tradingagents_adapter
    from trade_ui.server.run_config import ResolvedRunConfig

    logs_dir = tmp_path / "logs"
    resolved = ResolvedRunConfig(
        provider="deepseek",
        runtime_provider="deepseek",
        backend_url=None,
        quick_model="deepseek-v4-flash",
        deep_model="deepseek-v4-flash",
        depth=1,
        language="English",
        analysts=["market"],
        data_vendors={},
        advanced_settings={},
        runtime_env_values={},
        upstream_config={"results_dir": str(logs_dir)},
        missing_credentials=[],
    )
    monkeypatch.setattr(run_config_module, "resolve_run_config", lambda _config: resolved)
    monkeypatch.setattr(graph_module, "TradingAgentsGraph", lambda *a, **k: object())

    runner_holder: dict = {}

    class FakeAdapter:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def stream(self, _ticker, _trade_date, asset_type: str = "stock"):
            yield {"company_of_interest": "SNDK", "trade_date": "2026-09-19", "asset_type": asset_type, **FINAL_STATE}
            # Cancel after work has happened, the way Stop does mid-analysis.
            # Cancelling before the first chunk would leave an empty state and
            # pass on the blank-state guard alone, proving nothing about whether
            # a partly-built report can leak out of a cancelled run.
            runner_holder["runner"].cancel_token.cancel()
            yield {"company_of_interest": "SNDK", "trade_date": "2026-09-19", "asset_type": asset_type, **FINAL_STATE}

    monkeypatch.setattr(tradingagents_adapter, "TradingAgentsAdapter", FakeAdapter)

    runner = _runner(tmp_path, logs_dir)
    runner_holder["runner"] = runner
    runner.run()

    assert runner.header.status == "cancelled"
    assert not (logs_dir / "SNDK").exists()
