from __future__ import annotations

import os

import pytest

from reporting_adapter import save_ui_reports
from runtime_environment import effective_environment, temporary_environment
from ui_advanced import DEFAULT_DATA_VENDORS, SUPPORTED_DATA_VENDORS


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


def test_data_vendors_use_only_upstream_supported_values():
    for category, configured in DEFAULT_DATA_VENDORS.items():
        assert configured in SUPPORTED_DATA_VENDORS[category]
        assert configured != "disabled"


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


def test_streamlit_secret_lookup_does_not_log_values(capsys):
    import app

    values = app.get_streamlit_secret_values({"OPENAI_API_KEY": "secret-value"})
    assert values["OPENAI_API_KEY"] == "secret-value"
    output = capsys.readouterr()
    assert "secret-value" not in output.out
    assert "secret-value" not in output.err


@pytest.mark.parametrize(
    ("version", "update_available", "notice"),
    [
        ("0.3.1", False, False),
        ("0.3.2", False, False),
        ("0.3.9", False, False),
        ("0.3.0", True, True),
        ("0.4.0", False, True),
    ],
)
def test_update_status_never_downgrades_compatible_versions(monkeypatch, version, update_available, notice):
    import app

    app.cached_tradingagents_update_status.clear()
    monkeypatch.setattr(app, "find_tradingagents_checkout", lambda: None)
    monkeypatch.setattr(app, "is_tradingagents_installed", lambda: True)
    monkeypatch.setattr(app, "installed_tradingagents_version", lambda: version)
    monkeypatch.setattr(app, "latest_remote_tradingagents_tag", lambda: "v0.3.1")
    status = app.cached_tradingagents_update_status()
    assert status["update_available"] is update_available
    assert bool(status.get("notice")) is notice
    app.cached_tradingagents_update_status.clear()


def test_local_checkout_update_never_mutates_worktree(tmp_path, monkeypatch):
    import app

    monkeypatch.setattr(app, "checkout_has_local_changes", lambda _path: False)
    ok, message = app.update_tradingagents_from_app({"path": str(tmp_path)})
    assert not ok
    assert "left unchanged" in message


def test_missing_tradingagents_offers_target_install(monkeypatch):
    import app

    app.cached_tradingagents_update_status.clear()
    monkeypatch.setattr(app, "find_tradingagents_checkout", lambda: None)
    monkeypatch.setattr(app, "is_tradingagents_installed", lambda: False)
    monkeypatch.setattr(app, "latest_remote_tradingagents_tag", lambda: "v0.3.1")
    status = app.cached_tradingagents_update_status()
    assert status["installed_version"] == "missing"
    assert status["update_available"] is True
    app.cached_tradingagents_update_status.clear()


def test_ui_version_is_package_metadata():
    from tradingagents_compat import ui_version

    assert ui_version() == "1.3.0"
