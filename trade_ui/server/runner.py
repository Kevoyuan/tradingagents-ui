"""Runners for TradingAgents execution: StubRunner for tests/offline, UpstreamRunner for real execution."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from collections.abc import Callable

from trade_ui.model_pricing import PRICING_AS_OF, estimate_cost
from trade_ui.server.event_bus import EventBus
from trade_ui.server.models import RunConfig, RunHeader, TeamName

logger = logging.getLogger(__name__)


class CancellationToken:
    """Thread-safe cooperative cancellation token."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Return True if cancellation has been requested."""
        return self._event.is_set()

    def wait(self, timeout: float) -> bool:
        """Wait up to timeout seconds or until cancelled."""
        return self._event.wait(timeout)


class StubRunner:
    """Fake/stub upstream runner simulating the complete analysis workflow without network calls."""

    def __init__(
        self,
        header: RunHeader,
        config: RunConfig,
        event_bus: EventBus,
        cancel_token: CancellationToken,
        on_header_update: Callable[[RunHeader], None],
    ) -> None:
        self.header = header
        self.config = config
        self.event_bus = event_bus
        self.cancel_token = cancel_token
        self.on_header_update = on_header_update

    def run(self) -> None:
        ticker = self.header.ticker
        trade_date = self.header.trade_date
        config_dict = self.config.model_dump()
        step_delay = self.config.step_delay

        def check_cancelled() -> bool:
            if self.cancel_token.is_cancelled:
                self.event_bus.publish(
                    kind="run_state",
                    payload={"status": "cancelled", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
                )
                self.header.status = "cancelled"
                self.header.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.on_header_update(self.header)
                return True
            if step_delay > 0 and self.cancel_token.wait(step_delay):
                return check_cancelled()
            return False

        try:
            # 1. Transition to running
            self.header.status = "running"
            self.header.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.on_header_update(self.header)
            self.event_bus.publish(
                kind="run_state",
                payload={"status": "running", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
            )
            if check_cancelled():
                return

            # 2. User/System message
            self.event_bus.publish(
                kind="user_message",
                payload={"text": f"Starting TradingAgents analysis for {ticker} on {trade_date}"},
            )
            if check_cancelled():
                return

            # 3. Analyst Team
            analysts = self.config.analysts or ["market", "social", "news", "fundamentals"]
            for analyst in analysts:
                if check_cancelled():
                    return
                # Status: running
                self.event_bus.publish(
                    kind="agent_status",
                    agent=analyst,
                    team="analyst",
                    payload={"agent": analyst, "status": "running"},
                )
                if check_cancelled():
                    return

                # Agent message
                self.event_bus.publish(
                    kind="agent_message",
                    agent=analyst,
                    team="analyst",
                    payload={
                        "text": f"Completed analysis of {analyst} indicators for {ticker}.",
                        "model": self.config.quick_model or "stub-model",
                        "tokens_in": 150,
                        "tokens_out": 220,
                        "latency_ms": 15,
                        "cost_usd": 0.001,
                    },
                )
                if check_cancelled():
                    return

                # Tool call
                call_id = f"call_{analyst}_01"
                tool_name = f"fetch_{analyst}_data"
                self.event_bus.publish(
                    kind="tool_call",
                    agent=analyst,
                    team="analyst",
                    payload={"tool": tool_name, "args": {"ticker": ticker, "date": trade_date}, "call_id": call_id},
                )
                if check_cancelled():
                    return

                # Tool result
                self.event_bus.publish_tool_result(
                    tool=tool_name,
                    call_id=call_id,
                    ok=True,
                    duration_ms=10,
                    result=f'{{"status": "ok", "ticker": "{ticker}", "analyst": "{analyst}"}}',
                    agent=analyst,
                    team="analyst",
                )
                if check_cancelled():
                    return

                # Report section
                self.event_bus.publish(
                    kind="report_section",
                    agent=analyst,
                    team="analyst",
                    payload={
                        "key": f"{analyst}_report",
                        "title": f"{analyst.capitalize()} Analyst",
                        "markdown": f"## {analyst.capitalize()} Analysis\n\nDetailed signals for {ticker} evaluated.",
                        "complete": True,
                    },
                )
                if check_cancelled():
                    return

                # Status: done
                self.event_bus.publish(
                    kind="agent_status",
                    agent=analyst,
                    team="analyst",
                    payload={"agent": analyst, "status": "done"},
                )

            # 4. Research Team
            researchers = ["bull_researcher", "bear_researcher", "research_manager"]
            for researcher in researchers:
                if check_cancelled():
                    return
                self.event_bus.publish(
                    kind="agent_status",
                    agent=researcher,
                    team="research",
                    payload={"agent": researcher, "status": "running"},
                )
                if check_cancelled():
                    return
                researcher_text = (
                    f"Synthesized research debate and consensus for {ticker}."
                    if researcher == "research_manager"
                    else f"Formulated {researcher.replace('_', ' ')} thesis for {ticker}."
                )
                self.event_bus.publish(
                    kind="agent_message",
                    agent=researcher,
                    team="research",
                    payload={
                        "text": researcher_text,
                        "model": self.config.deep_model or "stub-model",
                        "tokens_in": 180,
                        "tokens_out": 260,
                        "latency_ms": 20,
                        "cost_usd": 0.0015,
                    },
                )
                if check_cancelled():
                    return
                self.event_bus.publish(
                    kind="agent_status",
                    agent=researcher,
                    team="research",
                    payload={"agent": researcher, "status": "done"},
                )

            # 5. Trading Team
            if check_cancelled():
                return
            self.event_bus.publish(
                kind="agent_status",
                agent="trader",
                team="trading",
                payload={"agent": "trader", "status": "running"},
            )
            if check_cancelled():
                return
            self.event_bus.publish(
                kind="agent_message",
                agent="trader",
                team="trading",
                payload={
                    "text": f"Trader formulated proposed entry at 115.0 and target 194.0 for {ticker}.",
                    "model": self.config.deep_model or "stub-model",
                    "tokens_in": 160,
                    "tokens_out": 200,
                    "latency_ms": 15,
                    "cost_usd": 0.0012,
                },
            )
            if check_cancelled():
                return
            self.event_bus.publish(
                kind="agent_status",
                agent="trader",
                team="trading",
                payload={"agent": "trader", "status": "done"},
            )

            # 6. Risk Team
            risk_analysts = ["aggressive_analyst", "neutral_analyst", "conservative_analyst"]
            for risk_agent in risk_analysts:
                if check_cancelled():
                    return
                self.event_bus.publish(
                    kind="agent_status",
                    agent=risk_agent,
                    team="risk",
                    payload={"agent": risk_agent, "status": "running"},
                )
                if check_cancelled():
                    return
                self.event_bus.publish(
                    kind="agent_message",
                    agent=risk_agent,
                    team="risk",
                    payload={
                        "text": f"Risk assessment from {risk_agent.replace('_', ' ')}: sizing and stop-loss validated.",
                        "model": self.config.quick_model or "stub-model",
                        "tokens_in": 140,
                        "tokens_out": 180,
                        "latency_ms": 12,
                        "cost_usd": 0.001,
                    },
                )
                if check_cancelled():
                    return
                self.event_bus.publish(
                    kind="agent_status",
                    agent=risk_agent,
                    team="risk",
                    payload={"agent": risk_agent, "status": "done"},
                )

            # 7. Portfolio Manager Decision & Verdict
            if check_cancelled():
                return
            self.event_bus.publish(
                kind="agent_status",
                agent="portfolio_manager",
                team="portfolio",
                payload={"agent": "portfolio_manager", "status": "running"},
            )
            if check_cancelled():
                return
            self.event_bus.publish(
                kind="agent_message",
                agent="portfolio_manager",
                team="portfolio",
                payload={
                    "text": f"Portfolio manager approved trade recommendation for {ticker}.",
                    "model": self.config.deep_model or "stub-model",
                    "tokens_in": 220,
                    "tokens_out": 320,
                    "latency_ms": 22,
                    "cost_usd": 0.002,
                },
            )
            if check_cancelled():
                return
            self.event_bus.publish(
                kind="agent_status",
                agent="portfolio_manager",
                team="portfolio",
                payload={"agent": "portfolio_manager", "status": "done"},
            )
            if check_cancelled():
                return

            verdict_payload = {
                "rating": "Buy",
                "source_section": "portfolio",
                "price_target": "194.0",
                "executive_summary": f"High conviction Buy for {ticker} based on technical and fundamental setup.",
                "entry_price": "115.0",
                "stop_loss": "110.0",
                "position_sizing": "2-3%",
            }
            self.event_bus.publish(
                kind="verdict",
                agent="portfolio_manager",
                team="portfolio",
                payload=verdict_payload,
            )
            self.header.verdict = verdict_payload

            # 8. Stats
            stats_payload = {
                "llm_calls": 12,
                "tool_calls": len(analysts),
                "tokens_in": 1900,
                "tokens_out": 2700,
                "cost_usd": 0.0165,
            }
            self.event_bus.publish(kind="stats", payload=stats_payload)
            self.header.stats = stats_payload

            # 9. Terminal completed state
            if check_cancelled():
                return

            self.event_bus.publish(
                kind="run_state",
                payload={"status": "completed", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
            )
            self.header.status = "completed"
            self.header.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.on_header_update(self.header)

        except Exception as err:
            logger.exception("Error in StubRunner execution: %s", err)
            tb = traceback.format_exc()
            self.event_bus.publish(kind="error", payload={"message": str(err), "traceback": tb})
            self.event_bus.publish(
                kind="run_state",
                payload={"status": "failed", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
            )
            self.header.status = "failed"
            self.header.error = {"message": str(err), "traceback": tb}
            self.header.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.on_header_update(self.header)
        finally:
            self.event_bus.close()

class UpstreamRunner:
    """Runner delegating to upstream TradingAgents graph with cooperative cancellation."""

    def __init__(
        self,
        header: RunHeader,
        config: RunConfig,
        event_bus: EventBus,
        cancel_token: CancellationToken,
        on_header_update: Callable[[RunHeader], None],
    ) -> None:
        self.header = header
        self.config = config
        self.event_bus = event_bus
        self.cancel_token = cancel_token
        self.on_header_update = on_header_update

    def run(self) -> None:
        ticker = self.header.ticker
        trade_date = self.header.trade_date
        config_dict = self.config.model_dump()

        from runtime_environment import temporary_environment
        from trade_ui.server.run_config import resolve_run_config

        resolved = resolve_run_config(self.config)
        if resolved.missing_credentials:
            missing_str = ", ".join(resolved.missing_credentials)
            err_msg = (
                f"Missing required credentials for provider '{resolved.provider}': {missing_str}. "
                f"Please configure them in ~/.tradingagents/.env or Settings."
            )
            logger.error("Run %s rejected: %s", self.header.run_id, err_msg)
            self.header.status = "failed"
            self.header.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.header.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.header.error = {"message": err_msg, "traceback": ""}
            self.on_header_update(self.header)
            self.event_bus.publish(
                kind="error",
                payload={"message": err_msg, "traceback": ""},
            )
            self.event_bus.publish(
                kind="run_state",
                payload={"status": "failed", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
            )
            self.event_bus.close()
            return

        try:
            self.header.status = "running"
            self.header.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.on_header_update(self.header)
            self.event_bus.publish(
                kind="run_state",
                payload={"status": "running", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
            )

            with temporary_environment(resolved.runtime_env_values):
                from cli.stats_handler import StatsCallbackHandler
                from tradingagents.graph.trading_graph import TradingAgentsGraph

                from tradingagents_adapter import TradingAgentsAdapter, detect_asset_type

                analysts = resolved.analysts
                stats_handler = StatsCallbackHandler()
                graph = TradingAgentsGraph(
                    analysts,
                    config=resolved.upstream_config,
                    debug=False,
                    callbacks=[stats_handler],
                )
                runner = TradingAgentsAdapter(graph, callbacks=[stats_handler])

                asset_type = detect_asset_type(ticker)
                cancelled = False

                # Upstream runs with stream_mode="values"
                # (tradingagents/graph/propagation.py), so every chunk is the full
                # AgentState dict. There are NO node-keyed chunks, which is why an
                # earlier attempt to map chunk keys to agents never matched once:
                # every event went out as agent=None and the UI rendered "System".
                #
                # The real signal is state field transitions, the same one the
                # retired Streamlit UI used. A report field going non-empty means
                # that agent finished; the debate states name their latest speaker.
                # Slugs match the frontend roster (INITIAL_ROSTER in App.tsx).
                report_agents: dict[str, tuple[str, TeamName]] = {
                    "market_report": ("market", "analyst"),
                    "sentiment_report": ("social", "analyst"),
                    "news_report": ("news", "analyst"),
                    "fundamentals_report": ("fundamentals", "analyst"),
                    "investment_plan": ("research_manager", "research"),
                    "trader_investment_plan": ("trader", "trading"),
                    "final_trade_decision": ("portfolio_manager", "portfolio"),
                }
                debate_speakers: dict[str, tuple[str, TeamName]] = {
                    "Bull": ("bull_researcher", "research"),
                    "Bear": ("bear_researcher", "research"),
                    "Research Manager": ("research_manager", "research"),
                    "Aggressive": ("aggressive_analyst", "risk"),
                    "Neutral": ("neutral_analyst", "risk"),
                    "Conservative": ("conservative_analyst", "risk"),
                    "Judge": ("portfolio_manager", "portfolio"),
                }
                REPORT_TITLES = (
                    ("market_report", "Market Analyst"),
                    ("sentiment_report", "Sentiment Analyst"),
                    ("news_report", "News Analyst"),
                    ("fundamentals_report", "Fundamentals Analyst"),
                    ("investment_plan", "Research Manager"),
                    ("trader_investment_plan", "Trader"),
                    ("final_trade_decision", "Portfolio Manager"),
                )
                finished: set[str] = set()
                last_slug: str | None = None
                last_team: TeamName | None = None
                last_text_by_agent: dict[str, str] = {}
                last_stats_at = 0.0
                seen_reports: set[str] = set()
                # An analyst's first assistant message lands BEFORE its report
                # field is filled, so at that moment no agent has started yet.
                # Buffer those and hand them to whichever agent starts next.
                pending_unattributed: list[str] = []

                def start(slug: str, team: TeamName) -> None:
                    """Mark an agent as running the first time we see it work."""
                    nonlocal last_slug, last_team
                    if slug in finished or slug == last_slug:
                        return
                    if last_slug is not None:
                        finish(last_slug)
                    self.event_bus.publish(
                        kind="agent_status",
                        payload={"agent": slug, "status": "running"},
                        agent=slug,
                        team=team,
                    )
                    last_slug, last_team = slug, team
                    while pending_unattributed:
                        text = pending_unattributed.pop(0)
                        if last_text_by_agent.get(slug) == text:
                            continue
                        last_text_by_agent[slug] = text
                        self.event_bus.publish(
                            kind="agent_message",
                            payload={
                                "text": text,
                                "model": "upstream",
                                "tokens_in": 0,
                                "tokens_out": 0,
                                "latency_ms": 0,
                                "cost_usd": None,
                            },
                            agent=slug,
                            team=team,
                        )

                def finish(slug: str) -> None:
                    if slug not in finished:
                        finished.add(slug)
                        self.event_bus.publish(
                            kind="agent_status", payload={"agent": slug, "status": "done"}, agent=slug
                        )

                for chunk in runner.stream(ticker, trade_date, asset_type=asset_type):
                    if self.cancel_token.is_cancelled:
                        cancelled = True
                        break

                    # Who is working right now, per the state we were just handed.
                    for field, mapping in report_agents.items():
                        if chunk.get(field) and field not in seen_reports:
                            seen_reports.add(field)
                            start(*mapping)
                            finish(mapping[0])
                            # The reducer counts report_section events to drive
                            # the Reports n/7 figure. The upstream runner never
                            # published any, so that counter sat at zero for the
                            # whole run even after every report was written.
                            self.event_bus.publish(
                                kind="report_section",
                                payload={
                                    "key": field,
                                    "title": dict(REPORT_TITLES).get(field, field),
                                    "markdown": str(chunk.get(field) or ""),
                                    "complete": True,
                                },
                                agent=mapping[0],
                                team=mapping[1],
                            )

                    for debate_field in ("investment_debate_state", "risk_debate_state"):
                        debate = chunk.get(debate_field) or {}
                        speaker = debate.get("latest_speaker") if isinstance(debate, dict) else None
                        mapping = debate_speakers.get(str(speaker))
                        if mapping:
                            start(*mapping)

                    slug, team = last_slug, last_team
                    for msg in chunk.get("messages") or []:
                        content = getattr(msg, "content", str(msg))
                        if not content or not str(content).strip():
                            continue
                        # The graph re-emits the same message on several ticks;
                        # without this the record showed "SNDK" six times and the
                        # same sentence five times.
                        if slug and last_text_by_agent.get(slug) == content:
                            continue
                        if not slug:
                            if last_text_by_agent.get("__pending__") != content:
                                last_text_by_agent["__pending__"] = content
                                pending_unattributed.append(content)
                            continue
                        if slug:
                            last_text_by_agent[slug] = content
                        self.event_bus.publish(
                            kind="agent_message",
                            payload={
                                "text": content,
                                "model": "upstream",
                                "tokens_in": 0,
                                "tokens_out": 0,
                                "latency_ms": 0,
                                "cost_usd": None,
                            },
                            agent=slug,
                            team=team,
                        )

                    # Emit counters from the stats handler. Without this the
                    # upstream path never published stats at all, so LLM calls,
                    # tool calls, tokens and the burn chart sat at zero for the
                    # whole run. Throttled because a long analysis yields a
                    # chunk per node tick and this is only a display counter.
                    now_mono = time.monotonic()
                    if now_mono - last_stats_at >= 2.0:
                        last_stats_at = now_mono
                        self._publish_stats(stats_handler)

                if last_slug is not None:
                    finish(last_slug)
                self._publish_stats(stats_handler)

                if cancelled or self.cancel_token.is_cancelled:
                    self.event_bus.publish(
                        kind="run_state",
                        payload={
                            "status": "cancelled",
                            "ticker": ticker,
                            "trade_date": trade_date,
                            "config": config_dict,
                        },
                    )
                    self.header.status = "cancelled"
                else:
                    self.event_bus.publish(
                        kind="run_state",
                        payload={
                            "status": "completed",
                            "ticker": ticker,
                            "trade_date": trade_date,
                            "config": config_dict,
                        },
                    )
                    self.header.status = "completed"

                self.header.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.on_header_update(self.header)

        except Exception as err:
            logger.exception("Error in UpstreamRunner execution: %s", err)
            tb = traceback.format_exc()
            self.event_bus.publish(kind="error", payload={"message": str(err), "traceback": tb})
            self.event_bus.publish(
                kind="run_state",
                payload={"status": "failed", "ticker": ticker, "trade_date": trade_date, "config": config_dict},
            )
            self.header.status = "failed"
            self.header.error = {"message": str(err), "traceback": tb}
            self.header.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.on_header_update(self.header)
        finally:
            self.event_bus.close()


    def _cost_model(self) -> str:
        """The model the deep-thinking calls dominate, so price on it."""
        config = getattr(self.config, "deep_model", None) or getattr(self.config, "quick_model", None)
        return str(config or "")

    def _publish_stats(self, stats_handler) -> None:  # noqa: ANN001 - upstream handler
        """Publish the live counters the run stats panel and burn chart read."""
        try:
            stats = stats_handler.get_stats() or {}
        except Exception:
            return
        tokens_in = int(stats.get("tokens_in", 0) or 0)
        tokens_out = int(stats.get("tokens_out", 0) or 0)
        # Upstream's stats handler has no cost field, so the figure comes from
        # the generated price table. A model with no entry yields None, which
        # the UI renders as an em dash: an unknown price must not look like a
        # price of zero. Refresh the table with the llm-pricing skill.
        cost = estimate_cost(self._cost_model(), tokens_in, tokens_out)
        payload = {
            "llm_calls": int(stats.get("llm_calls", 0) or 0),
            "tool_calls": int(stats.get("tool_calls", 0) or 0),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost,
            "pricing_as_of": PRICING_AS_OF,
        }
        self.event_bus.publish(kind="stats", payload=payload)
        self.header.stats = payload
