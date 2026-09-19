"""Runners for TradingAgents execution: StubRunner for tests/offline, UpstreamRunner for real execution."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from collections.abc import Callable

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

                # The upstream graph keys every chunk by node name, and that key
                # is the only thing that says which agent produced the messages.
                # Flattening the chunk threw it away, so every event went out as
                # agent=None and the UI could only render "System" - the roster,
                # the five-stage rail and the agent counters never moved.
                # Slugs are the ones the frontend roster uses (see INITIAL_ROSTER
                # in App.tsx); note upstream calls the social analyst
                # "Sentiment Analyst", so this cannot be a string-equality match.
                node_agents: dict[str, tuple[str, TeamName]] = {
                    "Market Analyst": ("market", "analyst"),
                    "Sentiment Analyst": ("social", "analyst"),
                    "News Analyst": ("news", "analyst"),
                    "Fundamentals Analyst": ("fundamentals", "analyst"),
                    "Bull Researcher": ("bull_researcher", "research"),
                    "Bear Researcher": ("bear_researcher", "research"),
                    "Research Manager": ("research_manager", "research"),
                    "Trader": ("trader", "trading"),
                    "Aggressive Analyst": ("aggressive_analyst", "risk"),
                    "Neutral Analyst": ("neutral_analyst", "risk"),
                    "Conservative Analyst": ("conservative_analyst", "risk"),
                    "Portfolio Manager": ("portfolio_manager", "portfolio"),
                }
                finished: set[str] = set()
                last_slug: str | None = None
                last_team: TeamName | None = None
                last_text_by_agent: dict[str, str] = {}

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

                    # Walk the chunk per node so the node key survives. Unknown
                    # keys (tool nodes, message-clear nodes) belong to whichever
                    # agent most recently spoke.
                    for node, node_value in chunk.items():
                        resolved_agent = node_agents.get(node)
                        slug, team = resolved_agent if resolved_agent else (last_slug, last_team)

                        if resolved_agent and slug not in finished and slug != last_slug:
                            if last_slug is not None:
                                finish(last_slug)
                            self.event_bus.publish(
                                kind="agent_status",
                                payload={"agent": slug, "status": "running"},
                                agent=slug,
                                team=team,
                            )
                            last_slug, last_team = slug, team

                        msgs = []
                        if isinstance(node_value, dict) and "messages" in node_value:
                            msgs = node_value["messages"]
                        elif node == "messages" and isinstance(node_value, list):
                            msgs = node_value

                        for msg in msgs:
                            content = getattr(msg, "content", str(msg))
                            if not content or not str(content).strip():
                                continue
                            # The graph re-emits the same message on several
                            # ticks; without this the record showed "SNDK" six
                            # times and the same sentence five times.
                            if slug and last_text_by_agent.get(slug) == content:
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

                if last_slug is not None:
                    finish(last_slug)

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
