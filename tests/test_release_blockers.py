from __future__ import annotations

import os

import pytest

from reporting_adapter import save_ui_reports
from runtime_environment import effective_environment, temporary_environment


@pytest.mark.parametrize("ticker", ["../../../tmp/file", "..", "...", "AAPL/../../x", "A" * 33])
def test_unsafe_ticker_cannot_create_report_files(tmp_path, ticker):
    with pytest.raises(ValueError):
        save_ui_reports({}, ticker, "2026-07-12", tmp_path, "model", lambda value: value)
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.parametrize("ticker", ["BTC-USD", "^GSPC", "GC=F"])
def test_safe_ticker_writes_only_below_results_root(tmp_path, ticker):
    report_dir, complete = save_ui_reports(
        {"market_report": "market", "final_trade_decision": "hold"},
        ticker,
        "2026-07-12",
        tmp_path,
        "model/x",
        lambda value: value.replace("/", "-"),
    )
    assert report_dir.is_relative_to(tmp_path)
    assert (report_dir / "complete_report.md").is_file()
    assert "Trading Analysis Report" in complete


def test_environment_restores_existing_values_after_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "process-key")
    with temporary_environment({"OPENAI_API_KEY": "sidebar-key", "EMPTY": ""}):
        assert os.environ["OPENAI_API_KEY"] == "sidebar-key"
    assert os.environ["OPENAI_API_KEY"] == "process-key"
    assert "EMPTY" not in os.environ


def test_environment_restores_existing_values_after_exception(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "process-fred")
    with pytest.raises(RuntimeError), temporary_environment({"FRED_API_KEY": "sidebar-fred"}):
        raise RuntimeError("expected")
    assert os.environ["FRED_API_KEY"] == "process-fred"


def test_empty_sidebar_preserves_environment_and_missing_key_stays_missing(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "process-alpha")
    monkeypatch.delenv("MISSING_KEY", raising=False)
    values = effective_environment(
        ("ALPHA_VANTAGE_API_KEY", "MISSING_KEY"),
        {},
        {},
    )
    assert values == {"ALPHA_VANTAGE_API_KEY": "process-alpha"}
    with temporary_environment(values):
        assert os.environ["ALPHA_VANTAGE_API_KEY"] == "process-alpha"
        assert "MISSING_KEY" not in os.environ
    assert os.environ["ALPHA_VANTAGE_API_KEY"] == "process-alpha"
    assert "MISSING_KEY" not in os.environ


def test_sidebar_then_secret_then_process_precedence(capsys):
    values = effective_environment(
        ("TOKEN",),
        {"TOKEN": "sidebar-secret"},
        {"TOKEN": "streamlit-secret"},
        {"TOKEN": "process-secret"},
    )
    assert values == {"TOKEN": "sidebar-secret"}
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""


def test_ui_version_is_package_metadata():
    from tradingagents_compat import ui_version

    assert ui_version() == "1.3.0"
