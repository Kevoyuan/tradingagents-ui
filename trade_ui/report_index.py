"""Report section parser, heading normalisation, and verdict extraction.

Implements Phase P2 from webapp-migration-plan.md:
- Section 4: Report section model and +3 heading normalisation (clamped at H6)
- Section 3: Verdict contract extraction (PM decision wins; trader plan fallback)
- Robust reading of on-disk report directories (~/.tradingagents/logs/<TICKER>/<DATE>/reports/)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from tradingagents.agents.utils.rating import parse_rating

from trade_ui.server.models import VerdictPayload

ReportVerdict = VerdictPayload


class AgentBlock(BaseModel):
    """An agent block within a report section."""

    name: str
    slug: str
    markdown: str
    complete: bool = True


class ReportSection(BaseModel):
    """A document section containing an ordered list of agent blocks."""

    title: str
    slug: str
    blocks: list[AgentBlock] = Field(
        default_factory=list,
        validation_alias=AliasChoices("blocks", "agent_blocks"),
    )

    model_config = ConfigDict(populate_by_name=True)

    @property
    def agent_blocks(self) -> list[AgentBlock]:
        """Alias for blocks matching the plan description."""
        return self.blocks


class ReportSummary(BaseModel):
    """Metadata summary of a discovered report on disk."""

    ticker: str
    trade_date: str
    path: str
    verdict: VerdictPayload | None = None
    sections_count: int = 0


SECTION_SPECS: list[dict[str, Any]] = [
    {
        "title": "I. Analyst Team Reports",
        "slug": "analysts",
        "dir": "1_analysts",
        "agents": [
            ("Market Analyst", "market", "market.md"),
            ("Sentiment Analyst", "sentiment", "sentiment.md"),
            ("News Analyst", "news", "news.md"),
            ("Fundamentals Analyst", "fundamentals", "fundamentals.md"),
        ],
    },
    {
        "title": "II. Research Team Decision",
        "slug": "research",
        "dir": "2_research",
        "agents": [
            ("Bull Researcher", "bull", "bull.md"),
            ("Bear Researcher", "bear", "bear.md"),
            ("Research Manager", "manager", "manager.md"),
        ],
    },
    {
        "title": "III. Trading Team Plan",
        "slug": "trading",
        "dir": "3_trading",
        "agents": [
            ("Trader", "trader", "trader.md"),
        ],
    },
    {
        "title": "IV. Risk Management Team Decision",
        "slug": "risk",
        "dir": "4_risk",
        "agents": [
            ("Aggressive Analyst", "aggressive", "aggressive.md"),
            ("Conservative Analyst", "conservative", "conservative.md"),
            ("Neutral Analyst", "neutral", "neutral.md"),
        ],
    },
    {
        "title": "V. Portfolio Manager Decision",
        "slug": "portfolio",
        "dir": "5_portfolio",
        "agents": [
            ("Portfolio Manager", "decision", "decision.md"),
        ],
    },
]


def normalize_headings(markdown: str, demote_by: int = 3) -> str:
    """Normalize agent markdown headings by demoting them by +demote_by levels.

    Per Section 4 of webapp-migration-plan:
    - agent H1 -> H4
    - agent H2 -> H5
    - agent H3 -> H6
    - clamped at H6

    Preserves code blocks (both ``` and ~~~ fences) without modifying internal comments.
    """
    lines = markdown.splitlines(keepends=True)
    result: list[str] = []
    in_code_block = False
    fence_char = ""
    fence_len = 0

    fence_re = re.compile(r"^( {0,3})(`{3,}|~{3,})")
    heading_re = re.compile(r"^( {0,3})(#{1,6})((\s.*)?)$")

    for line in lines:
        stripped_line = line.rstrip("\r\n")
        if not in_code_block:
            m_fence = fence_re.match(stripped_line)
            if m_fence:
                in_code_block = True
                fence_char = m_fence.group(2)[0]
                fence_len = len(m_fence.group(2))
                result.append(line)
                continue

            m_heading = heading_re.match(stripped_line)
            if m_heading:
                indent = m_heading.group(1)
                level = len(m_heading.group(2))
                rest = m_heading.group(3)
                new_level = min(6, level + demote_by)
                new_hashes = "#" * new_level
                ending = line[len(stripped_line):]
                result.append(f"{indent}{new_hashes}{rest}{ending}")
            else:
                result.append(line)
        else:
            closing_re = rf"^( {{0,3}}){re.escape(fence_char)}{{{fence_len},}}\s*$"
            if re.match(closing_re, stripped_line):
                in_code_block = False
            result.append(line)

    return "".join(result)


def _extract_field(text: str, label: str) -> str | None:
    pattern = rf"(?:^|\n)\s*\*{{0,2}}{re.escape(label)}\*{{0,2}}\s*:\s*([^\n\r]+)"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    val = re.sub(r"^\*+|\*+$", "", m.group(1).strip()).strip()
    return val if val else None


def _extract_numeric_field(text: str, label: str) -> str | None:
    val = _extract_field(text, label)
    if not val:
        return None
    num_match = re.search(r"(\d+(?:\.\d+)?)", val)
    if num_match:
        return num_match.group(1)
    return val


def _extract_section_text(text: str, label: str) -> str | None:
    pattern = rf"(?:^|\n)\s*\*{{0,2}}{re.escape(label)}\*{{0,2}}\s*:\s*(.+?)(?=\n\s*(?:\*\*[A-Z]|#{{1,6}}\s)|\Z)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    val = re.sub(r"^\*+|\*+$", "", m.group(1).strip()).strip()
    return val if val else None


def extract_verdict(
    report_dir: Path | str,
    fallback_to_trader: bool = True,
) -> VerdictPayload | None:
    """Extract verdict per Section 3 contract from on-disk reports.

    Never scans the whole merged complete_report.md for action words.
    Reads the Portfolio Manager decision (5_portfolio/decision.md) if present;
    otherwise falls back to Trader plan (3_trading/trader.md).
    When PM decision is present, numeric trade parameters (entry_price, stop_loss,
    position_sizing) are backfilled from Trader plan if PM omitted them,
    without overwriting any values PM explicitly provided.
    """
    path = Path(report_dir).expanduser()
    if (path / "reports").is_dir():
        path = path / "reports"

    if not path.is_dir():
        return None

    pm_file = path / "5_portfolio" / "decision.md"
    trader_file = path / "3_trading" / "trader.md"

    if pm_file.is_file():
        pm_text = pm_file.read_text(encoding="utf-8")
        if pm_text.strip():
            rating = parse_rating(pm_text)
            price_target = _extract_numeric_field(pm_text, "Price Target")
            executive_summary = _extract_section_text(pm_text, "Executive Summary")
            entry_price = _extract_numeric_field(pm_text, "Entry Price")
            stop_loss = _extract_numeric_field(pm_text, "Stop Loss")
            position_sizing = _extract_field(pm_text, "Position Sizing")

            if fallback_to_trader and trader_file.is_file():
                trader_text = trader_file.read_text(encoding="utf-8")
                if trader_text.strip():
                    if entry_price is None:
                        entry_price = _extract_numeric_field(trader_text, "Entry Price")
                    if stop_loss is None:
                        stop_loss = _extract_numeric_field(trader_text, "Stop Loss")
                    if position_sizing is None:
                        position_sizing = _extract_field(trader_text, "Position Sizing")

            return VerdictPayload(
                rating=rating,  # type: ignore[arg-type]
                source_section="portfolio",
                price_target=price_target,
                executive_summary=executive_summary,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_sizing=position_sizing,
            )

    if trader_file.is_file():
        trader_text = trader_file.read_text(encoding="utf-8")
        if trader_text.strip():
            rating = parse_rating(trader_text)
            price_target = _extract_numeric_field(trader_text, "Price Target")
            executive_summary = _extract_section_text(trader_text, "Executive Summary") or _extract_section_text(
                trader_text, "Reasoning"
            )
            entry_price = _extract_numeric_field(trader_text, "Entry Price")
            stop_loss = _extract_numeric_field(trader_text, "Stop Loss")
            position_sizing = _extract_field(trader_text, "Position Sizing")

            return VerdictPayload(
                rating=rating,  # type: ignore[arg-type]
                source_section="trader",
                price_target=price_target,
                executive_summary=executive_summary,
                entry_price=entry_price,
                stop_loss=stop_loss,
                position_sizing=position_sizing,
            )

    return None


def load_report_sections(
    report_dir: Path | str,
    normalize: bool = True,
    demote_by: int = 3,
) -> list[ReportSection]:
    """Read per-section files from report directory per Section 4.

    Missing files and empty files are skipped gracefully.
    Demotes headings in agent files by +demote_by levels (clamped at H6) if normalize=True.
    Returns only sections that have at least one block present.
    """
    path = Path(report_dir).expanduser()
    if (path / "reports").is_dir():
        path = path / "reports"

    if not path.is_dir():
        return []

    sections: list[ReportSection] = []

    for spec in SECTION_SPECS:
        sec_dir = path / spec["dir"]
        blocks: list[AgentBlock] = []

        for name, slug, filename in spec["agents"]:
            file_path = sec_dir / filename
            if not file_path.is_file():
                continue

            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                continue

            md = normalize_headings(content, demote_by=demote_by) if normalize else content
            blocks.append(
                AgentBlock(
                    name=name,
                    slug=slug,
                    markdown=md,
                    complete=True,
                )
            )

        if blocks:
            sections.append(
                ReportSection(
                    title=spec["title"],
                    slug=spec["slug"],
                    blocks=blocks,
                )
            )

    return sections


get_report_sections = load_report_sections
get_verdict = extract_verdict


def list_reports(logs_dir: Path | str | None = None) -> list[ReportSummary]:
    """Index previous reports from logs directory (default ~/.tradingagents/logs/).

    Returns summaries sorted by date descending, then ticker ascending.
    """
    if logs_dir is None:
        root = Path.home() / ".tradingagents" / "logs"
    else:
        root = Path(logs_dir).expanduser()

    if not root.exists() or not root.is_dir():
        return []

    reports: list[ReportSummary] = []

    for ticker_dir in sorted(root.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name.startswith(".") or ticker_dir.name == "archive":
            continue

        ticker = ticker_dir.name
        for date_dir in sorted(ticker_dir.iterdir(), reverse=True):
            if not date_dir.is_dir() or date_dir.name.startswith("."):
                continue

            rep_dir = date_dir / "reports"
            if not rep_dir.is_dir():
                continue

            verdict = extract_verdict(rep_dir)
            sections = load_report_sections(rep_dir, normalize=False)

            reports.append(
                ReportSummary(
                    ticker=ticker,
                    trade_date=date_dir.name,
                    path=str(rep_dir),
                    verdict=verdict,
                    sections_count=len(sections),
                )
            )

    reports.sort(key=lambda r: (r.trade_date, r.ticker), reverse=True)
    return reports
