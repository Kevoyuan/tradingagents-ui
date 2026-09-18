"""Tests for Report API routes: GET /api/reports and GET /api/reports/{ticker}/{date}."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trade_ui.server import create_app


def create_synthetic_report_dir(root: Path, ticker: str, date: str) -> Path:
    """Create a synthetic report directory encoding the BUY/SELL/Underweight trap."""
    rep_dir = root / ticker / date / "reports"
    (rep_dir / "1_analysts").mkdir(parents=True)
    (rep_dir / "2_research").mkdir(parents=True)
    (rep_dir / "3_trading").mkdir(parents=True)
    (rep_dir / "4_risk").mkdir(parents=True)
    (rep_dir / "5_portfolio").mkdir(parents=True)

    # Trap: complete_report.md has early BUY and later SELL
    (rep_dir / "complete_report.md").write_text(
        f"# {ticker} 综合研报\n\n"
        "## 最终交易建议：BUY（多头建仓）\n\n"
        "中间过程...\n\n"
        "## 最终交易建议：SELL（空头避险）\n\n"
        "## V. Portfolio Manager Decision\n\n"
        "**Rating**: Underweight\n"
        "**Price Target**: 194.0\n"
        "**Executive Summary**: 估值过高，下调至减持评级。\n",
        encoding="utf-8",
    )

    (rep_dir / "1_analysts" / "market.md").write_text(
        "# 市场技术分析\n\n## 动量指标\nRSI 超买，近期可能回调。\n",
        encoding="utf-8",
    )
    (rep_dir / "2_research" / "bull.md").write_text(
        "# 多方观点\n\n## 核心逻辑\n长期基本面优秀，建议 BUY。\n",
        encoding="utf-8",
    )
    (rep_dir / "3_trading" / "trader.md").write_text(
        "# 交易计划\n\n"
        "**Entry Price**: 150.00\n"
        "**Stop Loss**: 140.00\n"
        "**Position Sizing**: 3%\n",
        encoding="utf-8",
    )
    (rep_dir / "4_risk" / "aggressive.md").write_text(
        "# 激进风险观点\n\n建议 SELL 规避波动。\n",
        encoding="utf-8",
    )
    (rep_dir / "5_portfolio" / "decision.md").write_text(
        "# 投资组合经理最终决策\n\n"
        "**Rating**: Underweight\n\n"
        "**Price Target**: 194.0\n\n"
        "**Executive Summary**: 维持减持评级，估值过高。\n",
        encoding="utf-8",
    )

    return rep_dir


def test_reports_index_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/reports returns empty list when no reports exist."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with TestClient(app) as client:
        res = client.get("/api/reports")
        assert res.status_code == 200
        assert res.json() == []


def test_reports_index_and_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/reports returns discovered reports; GET /api/reports/{ticker}/{date} returns details."""
    logs_dir = tmp_path / "logs"
    create_synthetic_report_dir(logs_dir, "NBIS", "2026-09-18")
    create_synthetic_report_dir(logs_dir, "AAPL", "2026-09-19")
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with TestClient(app) as client:
        # Index listing
        index_res = client.get("/api/reports")
        assert index_res.status_code == 200
        reports = index_res.json()
        assert len(reports) == 2

        # Sorted descending by date
        assert reports[0]["ticker"] == "AAPL"
        assert reports[0]["trade_date"] == "2026-09-19"
        assert reports[1]["ticker"] == "NBIS"
        assert reports[1]["trade_date"] == "2026-09-18"

        # Detail for NBIS report
        detail_res = client.get("/api/reports/NBIS/2026-09-18")
        assert detail_res.status_code == 200
        data = detail_res.json()

        assert data["ticker"] == "NBIS"
        assert data["trade_date"] == "2026-09-18"

        # Trap assertion: must be Underweight, NOT Buy and NOT Sell
        verdict = data["verdict"]
        assert verdict is not None
        assert verdict["rating"] == "Underweight"
        assert verdict["source_section"] == "portfolio"
        assert verdict["price_target"] == "194.0"
        assert verdict["rating"] != "Buy"
        assert verdict["rating"] != "Sell"

        # Sections and blocks
        sections = data["sections"]
        assert len(sections) == 5
        slugs = [s["slug"] for s in sections]
        assert slugs == ["analysts", "research", "trading", "risk", "portfolio"]

        # Heading normalisation (+3 demotion):
        # market.md '# 市场技术分析' -> '#### 市场技术分析'
        analysts_sec = sections[0]
        market_block = analysts_sec["blocks"][0]
        assert market_block["name"] == "Market Analyst"
        assert "#### 市场技术分析" in market_block["markdown"]
        assert "##### 动量指标" in market_block["markdown"]


def test_report_detail_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /api/reports/{ticker}/{date} returns 404 for missing reports."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)
    monkeypatch.setenv("TRADINGAGENTS_LOGS_DIR", str(logs_dir))

    app = create_app(runs_dir=tmp_path / "runs", use_stub=True)
    with TestClient(app) as client:
        res = client.get("/api/reports/NONEXISTENT/2026-01-01")
        assert res.status_code == 404
