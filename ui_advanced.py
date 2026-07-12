"""Advanced TradingAgents v0.3.1 settings for the Streamlit sidebar."""

from __future__ import annotations

from typing import Any

import streamlit as st


def _safe_index(options: list[Any], value: Any) -> int:
    return options.index(value) if value in options else 0


def render_advanced_settings(provider: str, saved: dict[str, Any]) -> dict[str, Any]:
    with st.expander("Advanced Settings", expanded=False):
        checkpoint_enabled = st.checkbox(
            "Resume interrupted analyses",
            value=bool(saved.get("checkpoint_enabled", False)),
            help="Uses TradingAgents checkpoints. Successful runs remove their checkpoint.",
        )
        llm_max_retries = st.number_input(
            "LLM max retries",
            min_value=0,
            value=saved.get("llm_max_retries"),
            step=1,
            placeholder="Upstream default",
        )
        temperature = st.number_input(
            "Temperature",
            min_value=0.0,
            value=saved.get("temperature"),
            step=0.1,
            placeholder="Upstream default",
        )
        settings: dict[str, Any] = dict(saved)
        settings.update(
            {
                "checkpoint_enabled": checkpoint_enabled,
                "llm_max_retries": int(llm_max_retries) if llm_max_retries is not None else None,
                "temperature": float(temperature) if temperature is not None else None,
            }
        )
        if provider == "openai":
            settings["openai_reasoning_effort"] = st.selectbox(
                "OpenAI reasoning effort",
                [None, "low", "medium", "high"],
                index=_safe_index([None, "low", "medium", "high"], saved.get("openai_reasoning_effort")),
                format_func=lambda value: "Upstream default" if value is None else value.title(),
            )
        elif provider == "google":
            settings["google_thinking_level"] = st.selectbox(
                "Google thinking level",
                [None, "minimal", "low", "medium", "high"],
                index=_safe_index(
                    [None, "minimal", "low", "medium", "high"], saved.get("google_thinking_level")
                ),
                format_func=lambda value: "Upstream default" if value is None else value.title(),
            )
        elif provider == "anthropic":
            settings["anthropic_effort"] = st.selectbox(
                "Anthropic effort",
                [None, "low", "medium", "high"],
                index=_safe_index([None, "low", "medium", "high"], saved.get("anthropic_effort")),
                format_func=lambda value: "Upstream default" if value is None else value.title(),
            )
        return settings


def render_data_vendor_settings(saved: dict[str, str]) -> dict[str, str]:
    defaults = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
        "macro_data": "fred",
        "prediction_markets": "polymarket",
    }
    values = {**defaults, **saved}
    with st.expander("Data Sources", expanded=False):
        st.caption("Each selection is exact. TradingAgents does not silently add an unselected fallback.")
        result = {}
        labels = {
            "core_stock_apis": "Core stock data",
            "technical_indicators": "Technical indicators",
            "fundamental_data": "Fundamentals",
            "news_data": "News",
        }
        for key, label in labels.items():
            options = ["yfinance", "alpha_vantage", "yfinance,alpha_vantage"]
            current = values.get(key, defaults[key])
            result[key] = st.selectbox(label, options, index=options.index(current) if current in options else 0)
        macro_options = ["fred", "disabled"]
        prediction_options = ["polymarket", "disabled"]
        result["macro_data"] = st.selectbox(
            "Macro data",
            macro_options,
            index=_safe_index(macro_options, values.get("macro_data")),
            help="FRED requires FRED_API_KEY. Disabled tool calls return an explicit unavailable result.",
        )
        result["prediction_markets"] = st.selectbox(
            "Prediction markets",
            prediction_options,
            index=_safe_index(prediction_options, values.get("prediction_markets")),
            help="Polymarket is keyless. Disabled tool calls return an explicit unavailable result.",
        )
        return result
