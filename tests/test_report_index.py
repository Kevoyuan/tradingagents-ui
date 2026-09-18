"""Tests for report section parser, heading normalisation, and verdict extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from trade_ui.report_index import (
    AgentBlock,
    ReportSection,
    extract_verdict,
    load_report_sections,
    normalize_headings,
)


def test_nbis_real_report_regression() -> None:
    """Assert verdict extraction on the real NBIS 2026-09-18 report fixture.

    Secondary regression guard (runs locally when reports exist on disk).
    Primary regression guard is test_verdict_regression_guard_synthetic, which runs in CI.

    The merged complete_report.md contains:
      - Line 1029: ## 最终交易建议：BUY NBIS（NMS），分批建仓
      - Line 1423: ## 最终交易建议：SELL NBIS (NMS)
      - Line 1735: **Rating**: Underweight
    Whole-document keyword scans get this wrong. Reading the PM decision file yields Underweight.
    """
    report_path = Path("~/.tradingagents/logs/NBIS/2026-09-18/reports").expanduser()
    if not report_path.is_dir():
        pytest.skip("Fixture directory ~/.tradingagents/logs/NBIS/2026-09-18/reports does not exist")

    verdict = extract_verdict(report_path)
    assert verdict is not None

    # Regression assertions: must be Underweight from portfolio, not Buy and not Sell
    assert verdict.rating == "Underweight"
    assert verdict.source_section == "portfolio"
    assert verdict.price_target == "194.0"
    assert verdict.rating != "Buy"
    assert verdict.rating != "Sell"
    assert verdict.executive_summary is not None
    assert "Underweight" in verdict.executive_summary

    # Defect 2 assertion: numeric fields backfilled from 3_trading/trader.md
    assert verdict.entry_price == "223.54"
    assert verdict.stop_loss == "240.41"
    assert verdict.position_sizing is not None

    # Check sections model and heading normalisation on real report
    sections = load_report_sections(report_path)
    assert len(sections) == 5

    expected_slugs = ["analysts", "research", "trading", "risk", "portfolio"]
    assert [s.slug for s in sections] == expected_slugs

    # Section 1 has 4 analyst blocks
    analyst_sec = sections[0]
    assert analyst_sec.title == "I. Analyst Team Reports"
    assert len(analyst_sec.blocks) == 4
    analyst_slugs = [b.slug for b in analyst_sec.blocks]
    assert analyst_slugs == ["market", "sentiment", "news", "fundamentals"]

    # Verify heading normalisation was applied (+3 demotion):
    # market.md originally starts with '# NBIS（Nebius Group N.V.）技术分析报告'
    # After +3 normalisation, it must become '#### NBIS（Nebius Group N.V.）技术分析报告'
    market_block = analyst_sec.blocks[0]
    assert market_block.name == "Market Analyst"
    assert market_block.complete is True
    assert "#### NBIS（Nebius Group N.V.）技术分析报告" in market_block.markdown
    # Ensure there are no top-level H1, H2, or H3 in normalized agent markdown
    for line in market_block.markdown.splitlines():
        if line.startswith("#"):
            assert line.startswith("####"), f"Expected heading to be demoted to H4+, got: {line[:30]}"


def test_synthetic_report_regression_guard(tmp_path: Path) -> None:
    """Primary regression guard for CI: builds a synthetic report tree with the conflicting trap.

    The synthetic tree encodes the exact trap seen on real reports:
    - reports/complete_report.md containing an early line '## 最终交易建议：BUY ...'
      and a later line '## 最终交易建议：SELL ...', so any whole-document keyword scan yields Buy
    - reports/5_portfolio/decision.md containing '**Rating**: Underweight' and '**Price Target**: 194.0'
    - reports/4_risk/aggressive.md and reports/2_research/bull.md each carrying conflicting recommendation lines

    Assert extract_verdict returns rating 'Underweight', source_section 'portfolio',
    price_target '194.0', and explicitly assert it is NOT 'Buy' and NOT 'Sell'.
    """
    reports_dir = tmp_path / "reports"
    (reports_dir / "2_research").mkdir(parents=True)
    (reports_dir / "4_risk").mkdir(parents=True)
    (reports_dir / "5_portfolio").mkdir(parents=True)

    (reports_dir / "complete_report.md").write_text(
        "# NBIS 综合研报\n\n"
        "## 最终交易建议：BUY NBIS（NMS），分批建仓\n\n"
        "中间研究内容...\n\n"
        "## 最终交易建议：SELL NBIS (NMS)\n\n"
        "## V. Portfolio Manager Decision\n\n"
        "**Rating**: Underweight\n\n"
        "**Price Target**: 194.0\n",
        encoding="utf-8",
    )

    (reports_dir / "2_research" / "bull.md").write_text(
        "# Bull Researcher\n\n"
        "## 最终交易建议：BUY NBIS\n"
        "**Action**: Strong Buy\n",
        encoding="utf-8",
    )

    (reports_dir / "4_risk" / "aggressive.md").write_text(
        "# Aggressive Risk Analyst\n\n"
        "## 最终交易建议：SELL NBIS\n"
        "**Action**: Aggressive Sell\n",
        encoding="utf-8",
    )

    (reports_dir / "5_portfolio" / "decision.md").write_text(
        "# Portfolio Manager Decision\n\n"
        "**Rating**: Underweight\n\n"
        "**Price Target**: 194.0\n\n"
        "**Executive Summary**: 对 NBIS 执行 Underweight：分批降低净敞口。\n",
        encoding="utf-8",
    )

    verdict = extract_verdict(reports_dir)
    assert verdict is not None
    assert verdict.rating == "Underweight"
    assert verdict.source_section == "portfolio"
    assert verdict.price_target == "194.0"
    assert verdict.rating != "Buy"
    assert verdict.rating != "Sell"


def test_synthetic_fallback_to_trader_backfills_and_preserves_pm_values(tmp_path: Path) -> None:
    """Synthetic test with no skip: verify fallback_to_trader defaults to True.

    1. When PM decision omits entry/stop/sizing, trader values backfill them.
    2. When PM decision already provides entry/stop/sizing, trader values DO NOT overwrite them.
    3. When fallback_to_trader=False is explicitly passed, no backfill occurs.
    """
    reports_dir = tmp_path / "reports"
    (reports_dir / "3_trading").mkdir(parents=True)
    (reports_dir / "5_portfolio").mkdir(parents=True)

    # 1. PM decision omits entry/stop/sizing; Trader plan provides them
    (reports_dir / "3_trading" / "trader.md").write_text(
        "**Action**: Buy\n\n"
        "**Entry Price**: 223.54\n\n"
        "**Stop Loss**: 240.41\n\n"
        "**Position Sizing**: 分批减仓 1/3\n",
        encoding="utf-8",
    )
    (reports_dir / "5_portfolio" / "decision.md").write_text(
        "**Rating**: Underweight\n\n"
        "**Price Target**: 194.0\n\n"
        "**Executive Summary**: Portfolio manager underweight decision.\n",
        encoding="utf-8",
    )

    # Default fallback_to_trader=True backfills numeric and sizing fields
    verdict = extract_verdict(reports_dir)
    assert verdict is not None
    assert verdict.source_section == "portfolio"
    assert verdict.rating == "Underweight"
    assert verdict.price_target == "194.0"
    assert verdict.entry_price == "223.54"
    assert verdict.stop_loss == "240.41"
    assert verdict.position_sizing == "分批减仓 1/3"

    # Explicit fallback_to_trader=False keeps them None
    verdict_no_fallback = extract_verdict(reports_dir, fallback_to_trader=False)
    assert verdict_no_fallback is not None
    assert verdict_no_fallback.entry_price is None
    assert verdict_no_fallback.stop_loss is None
    assert verdict_no_fallback.position_sizing is None

    # 2. PM decision provides its own entry/stop/sizing: trader values must NOT overwrite
    (reports_dir / "5_portfolio" / "decision.md").write_text(
        "**Rating**: Underweight\n\n"
        "**Price Target**: 194.0\n\n"
        "**Entry Price**: 210.00\n\n"
        "**Stop Loss**: 225.00\n\n"
        "**Position Sizing**: PM sizing 5%\n",
        encoding="utf-8",
    )
    verdict_pm_provided = extract_verdict(reports_dir)
    assert verdict_pm_provided is not None
    assert verdict_pm_provided.entry_price == "210.00"
    assert verdict_pm_provided.stop_loss == "225.00"
    assert verdict_pm_provided.position_sizing == "PM sizing 5%"


def test_normalize_headings_basic_and_clamping() -> None:
    """Test +3 heading demotion and clamping at H6 per Section 4."""
    text = (
        "# Heading 1\n"
        "## Heading 2\n"
        "### Heading 3\n"
        "#### Heading 4\n"
        "##### Heading 5\n"
        "###### Heading 6\n"
        "Regular prose paragraph\n"
    )
    expected = (
        "#### Heading 1\n"
        "##### Heading 2\n"
        "###### Heading 3\n"
        "###### Heading 4\n"
        "###### Heading 5\n"
        "###### Heading 6\n"
        "Regular prose paragraph\n"
    )
    assert normalize_headings(text) == expected


def test_normalize_headings_preserves_code_blocks() -> None:
    """Ensure python comments and headings inside code fences are not demoted."""
    text = (
        "# Outer Heading\n"
        "```python\n"
        "# This is a python comment, not a markdown heading\n"
        "## Another comment\n"
        "def foo():\n"
        "    return 42\n"
        "```\n"
        "~~~\n"
        "# Tilde fence comment\n"
        "~~~\n"
        "## After Code\n"
    )
    expected = (
        "#### Outer Heading\n"
        "```python\n"
        "# This is a python comment, not a markdown heading\n"
        "## Another comment\n"
        "def foo():\n"
        "    return 42\n"
        "```\n"
        "~~~\n"
        "# Tilde fence comment\n"
        "~~~\n"
        "##### After Code\n"
    )
    assert normalize_headings(text) == expected


def test_normalize_headings_preserves_non_headings() -> None:
    """Ensure hashtags or text without space after hash are not demoted."""
    text = "#hashtag #123\n#\n###\n"
    expected = "#hashtag #123\n####\n######\n"
    assert normalize_headings(text) == expected


def test_missing_and_empty_section_files_skipped(tmp_path: Path) -> None:
    """Gracefully skip missing and empty files without raising."""
    report_dir = tmp_path / "reports"
    analysts_dir = report_dir / "1_analysts"
    analysts_dir.mkdir(parents=True)

    # market.md has real content
    (analysts_dir / "market.md").write_text("# Market\nMarket analysis text.", encoding="utf-8")
    # sentiment.md is empty (0 bytes)
    (analysts_dir / "sentiment.md").write_text("", encoding="utf-8")
    # news.md is whitespace only
    (analysts_dir / "news.md").write_text("   \n\n\t   ", encoding="utf-8")
    # fundamentals.md is missing entirely

    sections = load_report_sections(report_dir)
    assert len(sections) == 1
    sec = sections[0]
    assert sec.slug == "analysts"
    # Only market.md is included
    assert len(sec.blocks) == 1
    assert sec.blocks[0].slug == "market"
    assert sec.blocks[0].name == "Market Analyst"
    assert "#### Market" in sec.blocks[0].markdown


def test_partial_sections_directory(tmp_path: Path) -> None:
    """A report directory with only some sections present still returns a coherent section list."""
    report_dir = tmp_path / "reports"
    (report_dir / "1_analysts").mkdir(parents=True)
    (report_dir / "1_analysts" / "market.md").write_text("Market text", encoding="utf-8")

    (report_dir / "3_trading").mkdir(parents=True)
    (report_dir / "3_trading" / "trader.md").write_text("Trader text", encoding="utf-8")

    sections = load_report_sections(report_dir)
    assert len(sections) == 2
    assert sections[0].title == "I. Analyst Team Reports"
    assert sections[0].slug == "analysts"
    assert sections[1].title == "III. Trading Team Plan"
    assert sections[1].slug == "trading"


def test_empty_or_missing_report_dir(tmp_path: Path) -> None:
    """Empty or non-existent report directories return empty sections and None verdict."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    assert load_report_sections(empty_dir) == []
    assert extract_verdict(empty_dir) is None

    non_existent = tmp_path / "does_not_exist"
    assert load_report_sections(non_existent) == []
    assert extract_verdict(non_existent) is None


def test_trader_fallback_when_portfolio_missing(tmp_path: Path) -> None:
    """When PM decision has not landed, emit verdict from Trader plan."""
    report_dir = tmp_path / "reports"
    trading_dir = report_dir / "3_trading"
    trading_dir.mkdir(parents=True)

    (trading_dir / "trader.md").write_text(
        "**Action**: Buy\n\n"
        "**Reasoning**: Solid momentum and fundamentals.\n\n"
        "**Entry Price**: 150.25\n\n"
        "**Stop Loss**: 142.50\n\n"
        "**Position Sizing**: 5-10%\n\n"
        "FINAL TRANSACTION PROPOSAL: **BUY**\n",
        encoding="utf-8",
    )

    verdict = extract_verdict(report_dir)
    assert verdict is not None
    assert verdict.rating == "Buy"
    assert verdict.source_section == "trader"
    assert verdict.entry_price == "150.25"
    assert verdict.stop_loss == "142.50"
    assert verdict.position_sizing == "5-10%"
    assert verdict.price_target is None
    assert verdict.executive_summary == "Solid momentum and fundamentals."


def test_portfolio_wins_over_trader(tmp_path: Path) -> None:
    """When PM decision lands, it wins over Trader plan."""
    report_dir = tmp_path / "reports"
    (report_dir / "3_trading").mkdir(parents=True)
    (report_dir / "3_trading" / "trader.md").write_text(
        "**Action**: Buy\n\n**Entry Price**: 200.0\n\nFINAL TRANSACTION PROPOSAL: **BUY**\n",
        encoding="utf-8",
    )
    (report_dir / "5_portfolio").mkdir(parents=True)
    (report_dir / "5_portfolio" / "decision.md").write_text(
        "**Rating**: Sell\n\n"
        "**Executive Summary**: Overvalued; trim risk.\n\n"
        "**Price Target**: 175.0\n",
        encoding="utf-8",
    )

    verdict = extract_verdict(report_dir)
    assert verdict is not None
    assert verdict.rating == "Sell"
    assert verdict.source_section == "portfolio"
    assert verdict.price_target == "175.0"
    assert verdict.executive_summary == "Overvalued; trim risk."
    assert verdict.rating != "Buy"


def test_report_section_model_aliases_and_properties() -> None:
    """Ensure ReportSection can be accessed via blocks or agent_blocks."""
    block = AgentBlock(name="Market Analyst", slug="market", markdown="#### Content", complete=True)
    sec1 = ReportSection(title="Analyst Team", slug="analysts", blocks=[block])
    assert sec1.blocks == [block]
    assert sec1.agent_blocks == [block]

    sec2 = ReportSection(title="Analyst Team", slug="analysts", agent_blocks=[block])
    assert sec2.blocks == [block]
    assert sec2.agent_blocks == [block]
