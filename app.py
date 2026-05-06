"""TradingAgents UI - Lightweight Streamlit wrapper with CLI-style layout."""

import os
import time
import datetime
import threading
import html as html_lib
import traceback
import base64
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values, set_key, unset_key

from preferences import PREFS_DIR, load_preferences, save_preferences
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS

from ui_config import (
    ALL_TEAMS,
    ANALYST_KEY_MAP,
    ANALYST_OPTIONS,
    ANALYST_REPORT_MAP,
    AZURE_ENV_FIELDS,
    DEPTH_OPTIONS,
    LANGUAGES,
    OPTIONAL_API_KEY_PROVIDERS,
    PROVIDERS,
    PROVIDER_API_KEY_ENV,
    PROVIDER_BASE_URL_ENV,
    PROVIDER_MODEL_OPTIONS,
    PROVIDER_RUNTIME,
    PROVIDER_URLS,
)
from ui_panels import render_messages_panel, render_progress_panel
from ui_styles import CUSTOM_CSS

USER_ENV_FILE = PREFS_DIR / ".env"
SECRET_ENV_NAMES = tuple(
    dict.fromkeys(
        [
            *PROVIDER_API_KEY_ENV.values(),
            *PROVIDER_BASE_URL_ENV.values(),
            *(env_name for env_name, _, _ in AZURE_ENV_FIELDS),
            "ALPHA_VANTAGE_API_KEY",
        ]
    )
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_model_choices(provider: str, mode: str) -> list[str]:
    p = provider.lower()
    if p in PROVIDER_MODEL_OPTIONS and mode in PROVIDER_MODEL_OPTIONS[p]:
        return [d for d, _ in PROVIDER_MODEL_OPTIONS[p][mode]]
    if p in MODEL_OPTIONS and mode in MODEL_OPTIONS[p]:
        return [d for d, _ in MODEL_OPTIONS[p][mode]]
    return []


def get_model_id(provider: str, mode: str, display: str) -> str:
    p = provider.lower()
    if p in PROVIDER_MODEL_OPTIONS and mode in PROVIDER_MODEL_OPTIONS[p]:
        for d, mid in PROVIDER_MODEL_OPTIONS[p][mode]:
            if d == display:
                return mid
    if p in MODEL_OPTIONS and mode in MODEL_OPTIONS[p]:
        for d, mid in MODEL_OPTIONS[p][mode]:
            if d == display:
                return mid
    return display


def get_model_display(provider: str, mode: str, model_id: str, choices: list[str]) -> str | None:
    p = provider.lower()
    provider_options = PROVIDER_MODEL_OPTIONS.get(p, MODEL_OPTIONS.get(p))
    if not model_id or not provider_options or mode not in provider_options:
        return None
    for display, mid in provider_options[mode]:
        if model_id == mid or model_id in display:
            return display
    return choices[-1] if choices and get_model_id(provider, mode, choices[-1]) == "custom" else None


def is_compatible_provider(provider: str) -> bool:
    return provider in PROVIDER_RUNTIME


def get_provider_label(provider: str) -> str:
    return next((display for display, key in PROVIDERS if key == provider), provider)


def get_provider_base_url(provider: str, env_values: dict[str, str] | None = None) -> str | None:
    if provider in PROVIDER_BASE_URL_ENV:
        base_url_env = PROVIDER_BASE_URL_ENV[provider]
        if env_values and env_values.get(base_url_env):
            return env_values[base_url_env]
        if f"base_url_{provider}" in st.session_state:
            return st.session_state.get(f"base_url_{provider}", "").strip() or PROVIDER_URLS.get(provider)
        return os.environ.get(base_url_env, "") or PROVIDER_URLS.get(provider)
    return PROVIDER_URLS.get(provider)


def get_runtime_llm_config(provider: str, api_env_values: dict[str, str]) -> tuple[str, str | None, dict[str, str]]:
    runtime_provider = PROVIDER_RUNTIME.get(provider, provider)
    backend_url = get_provider_base_url(provider, api_env_values)
    runtime_env_values = dict(api_env_values)

    source_api_env = PROVIDER_API_KEY_ENV.get(provider)
    runtime_api_env = PROVIDER_API_KEY_ENV.get(runtime_provider)
    if source_api_env and runtime_api_env and source_api_env != runtime_api_env:
        source_key = api_env_values.get(source_api_env) or os.environ.get(source_api_env, "")
        if source_key:
            runtime_env_values[runtime_api_env] = source_key
            if runtime_provider == "anthropic":
                runtime_env_values["ANTHROPIC_AUTH_TOKEN"] = source_key
        elif provider in OPTIONAL_API_KEY_PROVIDERS and not os.environ.get(runtime_api_env):
            runtime_env_values[runtime_api_env] = "sk-no-key-required"
            if runtime_provider == "anthropic":
                runtime_env_values["ANTHROPIC_AUTH_TOKEN"] = "sk-no-key-required"

    return runtime_provider, backend_url, runtime_env_values


def render_model_selector(label: str, provider: str, mode: str, saved_model: str) -> str:
    choices = get_model_choices(provider, mode)
    if not choices:
        return st.text_input(f"{label} ID", value=saved_model or "")

    saved_display = get_model_display(provider, mode, saved_model, choices)
    index = choices.index(saved_display) if saved_display in choices else 0
    display = st.selectbox(label, choices, index=index)
    selected_id = get_model_id(provider, mode, display)
    if selected_id == "custom":
        return st.text_input(f"{label} Custom ID", value=saved_model if saved_model != "custom" else "")
    return selected_id


def init_session_state():
    if "initialized" not in st.session_state:
        prefs = load_preferences()
        saved_env = load_saved_api_env_values()
        apply_api_env_values(saved_env, override=False)

        st.session_state.ticker = prefs.get("ticker", "")
        st.session_state.analysis_date = datetime.date.today().isoformat()
        st.session_state.language = prefs.get("output_language", "English")
        st.session_state.analysts = normalize_saved_analysts(prefs.get("analysts", []))
        st.session_state.depth_key = prefs.get("depth_key", "Deep (5 rounds)")
        st.session_state.provider = prefs.get("llm_provider", "deepseek")
        st.session_state.quick_model = prefs.get("quick_think_llm", "")
        st.session_state.deep_model = prefs.get("deep_think_llm", "")

        for provider, env_name in PROVIDER_API_KEY_ENV.items():
            st.session_state[f"api_key_{provider}"] = os.environ.get(env_name, saved_env.get(env_name, ""))
        for provider, env_name in PROVIDER_BASE_URL_ENV.items():
            st.session_state[f"base_url_{provider}"] = os.environ.get(
                env_name,
                saved_env.get(env_name, PROVIDER_URLS.get(provider, "") or ""),
            )
        for env_name, _, _ in AZURE_ENV_FIELDS:
            st.session_state[env_name] = os.environ.get(env_name, saved_env.get(env_name, ""))
        st.session_state["ALPHA_VANTAGE_API_KEY"] = os.environ.get(
            "ALPHA_VANTAGE_API_KEY",
            saved_env.get("ALPHA_VANTAGE_API_KEY", ""),
        )

        # Analysis state
        st.session_state.running = False
        st.session_state.agent_status = {}
        st.session_state.messages = []
        st.session_state.tool_calls = []
        st.session_state.report_sections = {}
        st.session_state.final_report = None
        st.session_state.start_time = None
        st.session_state.llm_calls = 0
        st.session_state.tool_call_count = 0
        st.session_state.tokens_in = 0
        st.session_state.tokens_out = 0
        st.session_state.initialized = True


def save_current_config():
    save_preferences({
        "ticker": st.session_state.get("ticker", ""),
        "output_language": st.session_state.get("language", "English"),
        "analysts": st.session_state.get("analysts", []),
        "depth_key": st.session_state.get("depth_key", "Deep (5 rounds)"),
        "llm_provider": st.session_state.get("provider", "deepseek"),
        "quick_think_llm": st.session_state.get("quick_model", ""),
        "deep_think_llm": st.session_state.get("deep_model", ""),
    })
    save_api_env_file(get_all_api_env_values())


def load_saved_api_env_values() -> dict[str, str]:
    """Load persisted user credentials from the UI-owned .env file."""
    try:
        raw_values = dotenv_values(USER_ENV_FILE)
    except OSError:
        return {}
    return {
        env_name: str(value).strip()
        for env_name, value in raw_values.items()
        if env_name in SECRET_ENV_NAMES and value
    }


def get_all_api_env_values() -> dict[str, str]:
    """Collect all secret fields, including currently hidden provider keys."""
    env_values = {}
    for provider, env_name in PROVIDER_API_KEY_ENV.items():
        env_values[env_name] = st.session_state.get(f"api_key_{provider}", "").strip()
    for provider, env_name in PROVIDER_BASE_URL_ENV.items():
        env_values[env_name] = st.session_state.get(f"base_url_{provider}", "").strip()
    for env_name, _, _ in AZURE_ENV_FIELDS:
        env_values[env_name] = st.session_state.get(env_name, "").strip()
    env_values["ALPHA_VANTAGE_API_KEY"] = st.session_state.get("ALPHA_VANTAGE_API_KEY", "").strip()
    return env_values


def save_api_env_file(env_values: dict[str, str]):
    """Persist user credentials to ~/.tradingagents/.env."""
    PREFS_DIR.mkdir(parents=True, exist_ok=True)
    USER_ENV_FILE.touch(exist_ok=True)
    try:
        os.chmod(USER_ENV_FILE, 0o600)
    except OSError:
        pass

    existing_values = dotenv_values(USER_ENV_FILE)
    for env_name in SECRET_ENV_NAMES:
        value = env_values.get(env_name, "").strip()
        if value:
            set_key(str(USER_ENV_FILE), env_name, value, quote_mode="always")
        elif env_name in existing_values:
            unset_key(str(USER_ENV_FILE), env_name)


def get_api_env_values(provider: str) -> dict[str, str]:
    """Collect non-empty runtime credentials from the sidebar."""
    env_values = {}
    api_key_env = PROVIDER_API_KEY_ENV.get(provider)
    if api_key_env:
        api_key = st.session_state.get(f"api_key_{provider}", "").strip()
        if api_key:
            env_values[api_key_env] = api_key

    base_url_env = PROVIDER_BASE_URL_ENV.get(provider)
    if base_url_env:
        base_url = st.session_state.get(f"base_url_{provider}", "").strip()
        if base_url:
            env_values[base_url_env] = base_url

    if provider == "azure":
        for env_name, _, _ in AZURE_ENV_FIELDS:
            value = st.session_state.get(env_name, "").strip()
            if value:
                env_values[env_name] = value

    alpha_vantage_key = st.session_state.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if alpha_vantage_key:
        env_values["ALPHA_VANTAGE_API_KEY"] = alpha_vantage_key

    return env_values


def apply_api_env_values(env_values: dict[str, str], override: bool = True):
    """Expose sidebar credentials to TradingAgents."""
    for env_name, value in env_values.items():
        if value:
            if override or not os.environ.get(env_name):
                os.environ[env_name] = value


def missing_required_credentials(provider: str, env_values: dict[str, str]) -> list[str]:
    missing = []
    api_key_env = PROVIDER_API_KEY_ENV.get(provider)
    if (
        api_key_env
        and provider not in OPTIONAL_API_KEY_PROVIDERS
        and not (env_values.get(api_key_env) or os.environ.get(api_key_env))
    ):
        missing.append(api_key_env)

    if provider == "azure":
        for env_name, _, _ in AZURE_ENV_FIELDS:
            if not (env_values.get(env_name) or os.environ.get(env_name)):
                missing.append(env_name)

    base_url_env = PROVIDER_BASE_URL_ENV.get(provider)
    if base_url_env and not (env_values.get(base_url_env) or os.environ.get(base_url_env) or PROVIDER_URLS.get(provider)):
        missing.append(base_url_env)

    return missing


def format_tokens(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def extract_content_string(content) -> str | None:
    """Extract readable text from common LangChain/OpenAI message content shapes."""
    if content is None:
        return None
    if isinstance(content, str):
        text = content.strip()
        return text or None
    if isinstance(content, dict):
        text = content.get("text") or content.get("content") or ""
        text = str(text).strip()
        return text or None
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
            else:
                text = str(item)
            text = str(text).strip()
            if text:
                parts.append(text)
        return " ".join(parts) or None
    text = str(content).strip()
    return text or None


def classify_message(message) -> tuple[str, str | None]:
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    content = extract_content_string(getattr(message, "content", None))
    if isinstance(message, HumanMessage):
        return "User", content
    if isinstance(message, ToolMessage):
        return "Data", content
    if isinstance(message, AIMessage):
        return "Agent", content
    return "System", content


def get_tool_call_name_args(tool_call) -> tuple[str, object]:
    """Support both LangChain ToolCall objects and dict-shaped tool calls."""
    if isinstance(tool_call, dict):
        return str(tool_call.get("name") or "tool"), tool_call.get("args", {})
    return str(getattr(tool_call, "name", "tool")), getattr(tool_call, "args", {})


def compact_text(value, max_length: int) -> str:
    text = str(value).replace("\n", " ").strip()
    return text[: max_length - 3] + "..." if len(text) > max_length else text


def report_total_for_analysts(selected_analysts: list[str]) -> int:
    # One report per selected analyst, plus investment, trader, and final decision.
    return len(selected_analysts) + 3


def parse_saved_date(value: str | None) -> datetime.date:
    if not value:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return datetime.date.today()


def normalize_saved_analysts(values) -> list[str]:
    valid = {key for _, key in ANALYST_OPTIONS}
    selected = [value for value in values if value in valid] if isinstance(values, list) else []
    return selected or ["market", "social", "news", "fundamentals"]


def render_inline_html(html: str, height: int):
    """Render inline HTML using the modern iframe API when available."""
    if hasattr(st, "iframe"):
        encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
        src = f"data:text/html;base64,{encoded}"
        try:
            st.iframe(src, height=height, scrolling=False)
        except TypeError:
            st.iframe(src, height=height)
        return

    import streamlit.components.v1 as components

    components.html(html, height=height)


def render_report_with_nav(report_content: str, id_prefix: str = "report"):
    """Render report with a navigation sidebar in the left column."""
    import re
    if not report_content:
        st.markdown(
            '<div style="color:#666;font-style:italic;padding:1rem 0;">Waiting for analysis report...</div>',
            unsafe_allow_html=True,
        )
        return

    # Extract headers and inject anchors
    toc = []
    lines = []
    for line in str(report_content).split("\n"):
        match = re.match(r"^(#+)\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            # Slugify matching Streamlit's likely behavior or our custom anchor
            slug = re.sub(r"[^\w\s-]", "", title.lower())
            slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
            if slug:
                unique_slug = f"{id_prefix}-{slug}"
                toc.append((level, title, unique_slug))
                # Inject anchor before header with spacing to not break markdown
                lines.append(f'\n<div id="{unique_slug}"></div>\n')
        lines.append(line)
    
    processed_content = "\n".join(lines)

    if not toc:
        st.markdown(f'<div class="report-section">{report_content}</div>', unsafe_allow_html=True)
        return

    # Create column layout for nav + content
    col_nav, col_content = st.columns([1, 3], gap="medium")

    with col_nav:
        st.markdown('<div class="report-nav-title">Report Content</div>', unsafe_allow_html=True)
        with st.container(height=720, border=False):
            nav_html = '<div class="report-nav">'
            for level, title, slug in toc:
                indent = (level - 1) * 16
                level_class = f"nav-level-{level}"
                nav_html += f'<a href="#{slug}" target="_self" class="report-nav-item {level_class}" style="padding-left: {12+indent}px;">{title}</a>'
            nav_html += '</div>'
            st.markdown(nav_html, unsafe_allow_html=True)
        
        # Copy Button via inline iframe
        import json
        
        # ensure_ascii=False keeps Chinese characters readable, escaping for JS script block
        safe_content = json.dumps(report_content, ensure_ascii=False)
        # Avoid closing script tag prematurely if the content happens to contain </script>
        safe_content = safe_content.replace("</script>", "<\\/script>")
        
        copy_html = f"""
        <style>
        body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
        .report-copy-btn {{
            width: 100%;
            background: transparent;
            border: 1px solid rgba(0, 255, 136, 0.3);
            color: #00ff88;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: block;
            box-sizing: border-box;
        }}
        .report-copy-btn:hover {{
            background: rgba(0, 255, 136, 0.1);
            border-color: #00ff88;
        }}
        .report-copy-btn:active {{
            transform: scale(0.98);
        }}
        </style>
        <button id="copy-btn" class="report-copy-btn">COPY MARKDOWN</button>
        <script>
            const content = {safe_content}; 
            const btn = document.getElementById("copy-btn");
            btn.onclick = function() {{
                navigator.clipboard.writeText(content).then(() => {{ 
                    btn.innerText = "COPIED!"; 
                    btn.style.background = "#00ff88";
                    btn.style.color = "#000";
                    setTimeout(() => {{ 
                        btn.innerText = "COPY MARKDOWN"; 
                        btn.style.background = "transparent";
                        btn.style.color = "#00ff88";
                    }}, 2000); 
                }}).catch(err => {{
                    // Fallback
                    const textArea = document.createElement("textarea");
                    textArea.value = content;
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {{
                        document.execCommand("copy");
                        btn.innerText = "COPIED!"; 
                        btn.style.background = "#00ff88";
                        btn.style.color = "#000";
                        setTimeout(() => {{ 
                            btn.innerText = "COPY MARKDOWN"; 
                            btn.style.background = "transparent";
                            btn.style.color = "#00ff88";
                        }}, 2000); 
                    }} catch(e) {{
                        btn.innerText = "ERROR";
                    }}
                    document.body.removeChild(textArea);
                }});
            }};
        </script>
        """
        import streamlit.components.v1 as components
        components.html(copy_html, height=45)

    with col_content:
        with st.container(height=800, border=False):
            st.markdown(f'<div class="report-section">', unsafe_allow_html=True)
            st.markdown(processed_content, unsafe_allow_html=True)
            st.markdown(f'</div>', unsafe_allow_html=True)


# ── Analysis Runner (background thread) ────────────────────────────────────────

def _run_analysis_thread(
    ticker, date, language, analysts, depth, provider, quick_model, deep_model, api_env_values, state
):
    """Run analysis in a background thread, writing results to shared state dict."""
    runtime_provider, backend_url, runtime_env_values = get_runtime_llm_config(provider, api_env_values)
    apply_api_env_values(runtime_env_values)

    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from cli.stats_handler import StatsCallbackHandler

    try:
        date_str = str(date)
        chunks = []

        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = depth
        config["max_risk_discuss_rounds"] = depth
        config["quick_think_llm"] = quick_model
        config["deep_think_llm"] = deep_model
        config["backend_url"] = backend_url
        config["llm_provider"] = runtime_provider
        config["output_language"] = language

        stats_handler = StatsCallbackHandler()

        # Initialize agent statuses
        for team, agents in ALL_TEAMS.items():
            for agent in agents:
                # Only include analysts that were selected + always-include agents
                is_analyst = agent in ANALYST_KEY_MAP.values()
                if is_analyst:
                    analyst_key = [k for k, v in ANALYST_KEY_MAP.items() if v == agent][0]
                    if analyst_key not in analysts:
                        continue
                state["agent_status"][agent] = "pending"

        # Set first analyst to in_progress
        for analyst_key in analysts:
            agent = ANALYST_KEY_MAP.get(analyst_key)
            if agent and agent in state["agent_status"]:
                state["agent_status"][agent] = "in_progress"
                break

        state["messages"].append((now_str(), "System", f"Analyzing {ticker} on {date_str}"))

        graph = TradingAgentsGraph(analysts, config=config, debug=True, callbacks=[stats_handler])
        init_state = graph.propagator.create_initial_state(ticker, date_str)
        args = graph.propagator.get_graph_args(callbacks=[stats_handler])

        seen_message_ids = set()
        seen_tool_call_ids = set()
        
        for chunk in graph.graph.stream(init_state, **args):
            chunks.append(chunk)

            # Extract messages from various chunk formats (updates or full state)
            msgs_to_process = []
            if "messages" in chunk:
                msgs_to_process = chunk["messages"]
            else:
                for node_val in chunk.values():
                    if isinstance(node_val, dict) and "messages" in node_val:
                        msgs_to_process.extend(node_val["messages"])

            # Process messages with duplicate detection
            for message in msgs_to_process:
                # Use message ID if available, otherwise hash the content
                msg_id = getattr(message, "id", None) or hash(str(message))
                if msg_id in seen_message_ids:
                    continue
                seen_message_ids.add(msg_id)

                mtype, content = classify_message(message)
                if content:
                    state["messages"].append((now_str(), mtype, compact_text(content, 300)))

                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        tc_id = tc.get("id") or hash(str(tc))
                        if tc_id in seen_tool_call_ids:
                            continue
                        seen_tool_call_ids.add(tc_id)
                        name, args = get_tool_call_name_args(tc)
                        state["tool_calls"].append((now_str(), name, compact_text(args, 80)))

            # Update analyst statuses
            selected_set = set(analysts)
            found_active = False
            for ak in ["market", "social", "news", "fundamentals"]:
                if ak not in selected_set:
                    continue
                agent = ANALYST_KEY_MAP[ak]
                report_key = ANALYST_REPORT_MAP[ak]
                if chunk.get(report_key):
                    state["report_sections"][report_key] = chunk[report_key]
                has_report = bool(state["report_sections"].get(report_key))
                if has_report:
                    state["agent_status"][agent] = "completed"
                elif not found_active:
                    state["agent_status"][agent] = "in_progress"
                    found_active = True

            # Research team
            if chunk.get("investment_debate_state"):
                ds = chunk["investment_debate_state"]
                if ds.get("judge_decision", "").strip():
                    for a in ["Bull Researcher", "Bear Researcher", "Research Manager"]:
                        state["agent_status"][a] = "completed"
                    state["agent_status"]["Trader"] = "in_progress"
                elif ds.get("bull_history", "").strip() or ds.get("bear_history", "").strip():
                    for a in ["Bull Researcher", "Bear Researcher", "Research Manager"]:
                        if state["agent_status"].get(a) == "pending":
                            state["agent_status"][a] = "in_progress"

            # Trading team
            if chunk.get("trader_investment_plan"):
                state["report_sections"]["trader_investment_plan"] = chunk["trader_investment_plan"]
                if state["agent_status"].get("Trader") != "completed":
                    state["agent_status"]["Trader"] = "completed"
                    state["agent_status"]["Aggressive Analyst"] = "in_progress"

            # Risk management
            if chunk.get("risk_debate_state"):
                rs = chunk["risk_debate_state"]
                if rs.get("judge_decision", "").strip():
                    for a in ["Aggressive Analyst", "Conservative Analyst", "Neutral Analyst", "Portfolio Manager"]:
                        state["agent_status"][a] = "completed"
                    state["report_sections"]["final_trade_decision"] = rs["judge_decision"]

            # Update stats
            stats = stats_handler.get_stats()
            state["llm_calls"] = stats.get("llm_calls", 0)
            state["tool_call_count"] = stats.get("tool_calls", 0)
            state["tokens_in"] = stats.get("tokens_in", 0)
            state["tokens_out"] = stats.get("tokens_out", 0)

            # Update current report
            current = state["report_sections"].get("final_trade_decision") or \
                      state["report_sections"].get("trader_investment_plan") or \
                      state["report_sections"].get("investment_plan")
            if current:
                if isinstance(current, list):
                    current = "\n".join(str(x) for x in current)
                state["current_report"] = str(current)

        # Final
        final_state = chunks[-1] if chunks else {}
        if final_state.get("final_trade_decision"):
            graph.process_signal(final_state.get("final_trade_decision", ""))

        # Save reports
        results_dir = Path(config["results_dir"]) / ticker / date_str
        results_dir.mkdir(parents=True, exist_ok=True)
        report_dir = results_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        all_sections = {
            "market_report": final_state.get("market_report"),
            "sentiment_report": final_state.get("sentiment_report"),
            "news_report": final_state.get("news_report"),
            "fundamentals_report": final_state.get("fundamentals_report"),
            "investment_plan": final_state.get("investment_plan"),
            "trader_investment_plan": final_state.get("trader_investment_plan"),
            "final_trade_decision": final_state.get("final_trade_decision"),
        }
        for sn, content in all_sections.items():
            if content:
                text = "\n".join(str(i) for i in content) if isinstance(content, list) else str(content)
                (report_dir / f"{sn}.md").write_text(text, encoding="utf-8")

        complete = []
        for sn, content in all_sections.items():
            if content:
                text = "\n".join(str(i) for i in content) if isinstance(content, list) else str(content)
                complete.append(f"## {sn.replace('_', ' ').title()}\n\n{text}")
        complete_report = "\n\n---\n\n".join(complete)
        (report_dir / "complete_report.md").write_text(complete_report, encoding="utf-8")

        # Create a symlink to the latest report in the user data directory.
        latest_symlink = Path.home() / ".tradingagents" / "latest_report.md"
        try:
            latest_symlink.parent.mkdir(parents=True, exist_ok=True)
            if latest_symlink.exists() or latest_symlink.is_symlink():
                latest_symlink.unlink()
            latest_symlink.symlink_to(report_dir / "complete_report.md")
        except Exception:
            pass  # Fallback if OS prevents symlinking

        # Mark all agents completed
        for a in state["agent_status"]:
            state["agent_status"][a] = "completed"

        state["final_report"] = complete_report
        state["report_dir"] = str(report_dir)
        state["messages"].append((now_str(), "System", f"Completed analysis for {date_str}"))

    except Exception as e:
        state["messages"].append((now_str(), "System", f"ERROR: {e}"))
        state["error"] = str(e)
        state["traceback"] = traceback.format_exc()
    finally:
        state["done"] = True


# ── UI Renderers ───────────────────────────────────────────────────────────────



def render_stats_bar(agent_status, llm_calls, tool_calls, tokens_in, tokens_out, report_sections, start_time, selected_analysts):
    """Render the footer stats bar."""
    completed = sum(1 for s in agent_status.values() if s == "completed")
    total = len(agent_status)
    reports_done = sum(1 for v in report_sections.values() if v)
    reports_total = report_total_for_analysts(selected_analysts)

    parts = [
        f"Agents: <b>{completed}/{total}</b>",
        f"LLM: <b>{llm_calls}</b>",
        f"Tools: <b>{tool_calls}</b>",
        f"Tokens: <b>{format_tokens(tokens_in)}</b>&uarr; <b>{format_tokens(tokens_out)}</b>&darr;",
        f"Reports: <b>{reports_done}/{reports_total}</b>",
    ]
    if start_time:
        elapsed = time.time() - start_time
        parts.append(f"&#9201; <b>{int(elapsed // 60):02d}:{int(elapsed % 60):02d}</b>")

    return '<div class="stats-bar">' + " &nbsp; " + " ".join(f"<span>{p}</span>" for p in parts) + "</div>"


def render_analysis_view(analysis_state: dict, selected_analysts: list[str]):
    """Render the full analysis view with Progress + Messages + Report."""
    # Top row: Progress (left) + Messages (right)
    col_left, col_right = st.columns([2, 3], gap="small")

    with col_left:
        progress_html = render_progress_panel(
            analysis_state.get("agent_status", {}), selected_analysts
        )
        st.markdown(
            f'<div class="panel top-panel"><div class="scanning-line"></div><div class="panel-title">Progress</div>{progress_html}</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        messages_html = render_messages_panel(
            analysis_state.get("messages", []),
            analysis_state.get("tool_calls", []),
        )
        st.markdown(
            f'<div class="panel messages-panel"><div class="scanning-line"></div><div class="panel-title">Messages &amp; Tools</div><div class="messages-scroll">{messages_html}</div></div>',
            unsafe_allow_html=True,
        )

    # Report section
    report = analysis_state.get("current_report") or analysis_state.get("final_report")
    st.markdown(f'<div class="panel"><div class="scanning-line"></div><div class="panel-title">Analysis Report</div>', unsafe_allow_html=True)
    render_report_with_nav(report, id_prefix="live")
    st.markdown('</div>', unsafe_allow_html=True)

    # Stats bar
    stats_html = render_stats_bar(
        analysis_state.get("agent_status", {}),
        analysis_state.get("llm_calls", 0),
        analysis_state.get("tool_call_count", 0),
        analysis_state.get("tokens_in", 0),
        analysis_state.get("tokens_out", 0),
        analysis_state.get("report_sections", {}),
        analysis_state.get("start_time"),
        selected_analysts,
    )
    st.markdown(stats_html, unsafe_allow_html=True)


def browse_reports_ui():
    """Browse and display previous reports."""
    report_dirs = []

    logs_dir = Path.home() / ".tradingagents" / "logs"
    if logs_dir.exists():
        for td in sorted(logs_dir.iterdir(), reverse=True):
            if td.is_dir():
                for dd in sorted(td.iterdir(), reverse=True):
                    rp = dd / "reports" / "complete_report.md"
                    if rp.exists():
                        report_dirs.append(dd)

    if not report_dirs:
        st.info("No previous reports found.")
        return

    # Let user pick a report
    options = []
    for rp in report_dirs:
        parent = rp.parent.name
        name = rp.name
        rf = rp / "complete_report.md"
        if not rf.exists():
            rf = rp / "reports" / "complete_report.md"
        mod_time = datetime.datetime.fromtimestamp(rf.stat().st_mtime)
        options.append((f"{parent}/{name}  —  {mod_time.strftime('%Y-%m-%d %H:%M')}", rp))

    selected = st.selectbox(
        "Select a report",
        options,
        index=0,
        label_visibility="collapsed",
        format_func=lambda option: option[0],
    )

    if selected:
        _, rp = selected
        rf = rp / "complete_report.md"
        if not rf.exists():
            rf = rp / "reports" / "complete_report.md"
        if rf.exists():
            content = rf.read_text(encoding="utf-8")
            st.markdown("---")
            render_report_with_nav(content, id_prefix="browse")
            st.markdown("---")
            st.caption(f"Path: `{rf}`")


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:0.5rem 0 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 1.5rem;">'
            '<div style="font-size:2.2rem;font-weight:800;color:#00ff88;letter-spacing:-0.03em;line-height:1.1;text-shadow: 0 0 12px rgba(0,255,136,0.4);">TradingAgents</div>'
            '<div style="font-size:0.75rem;color:#8b949e;font-family:\'JetBrains Mono\',monospace;opacity:0.8;margin-top:0.6rem;letter-spacing:0.05em;">'
            'v1.2.0 &middot; INDUSTRIAL CONTROL PANEL</div></div>',
            unsafe_allow_html=True,
        )

        ticker = st.text_input("Ticker Symbol", value=st.session_state.ticker, placeholder="SPY, NVDA, 0700.HK")
        ticker = ticker.strip().upper()
        st.session_state.ticker = ticker

        analysis_date = st.date_input(
            "Analysis Date",
            value=parse_saved_date(st.session_state.analysis_date),
        )
        st.session_state.analysis_date = analysis_date.isoformat()

        language = st.selectbox("Output Language", LANGUAGES,
            index=LANGUAGES.index(st.session_state.language) if st.session_state.language in LANGUAGES else 0)
        st.session_state.language = language

        analysts = st.multiselect("Analysts Team",
            options=[v for _, v in ANALYST_OPTIONS],
            default=st.session_state.analysts,
            format_func=lambda v: next(k for k, val in ANALYST_OPTIONS if val == v))
        st.session_state.analysts = analysts

        depth_key = st.selectbox("Research Depth", list(DEPTH_OPTIONS.keys()),
            index=list(DEPTH_OPTIONS.keys()).index(st.session_state.depth_key) if st.session_state.depth_key in DEPTH_OPTIONS else 2)
        st.session_state.depth_key = depth_key

        provider_display = [d for d, _ in PROVIDERS]
        provider_keys = [k for _, k in PROVIDERS]
        provider_idx = provider_keys.index(st.session_state.provider) if st.session_state.provider in provider_keys else 4
        provider = st.selectbox("LLM Provider", provider_display, index=provider_idx)
        provider_key = provider_keys[provider_display.index(provider)]
        st.session_state.provider = provider_key
        if is_compatible_provider(provider_key):
            runtime_provider = PROVIDER_RUNTIME[provider_key]
            st.caption(
                f"Runs through TradingAgents as `{runtime_provider}` with a custom endpoint, "
                "so original TradingAgents providers stay separate."
            )
        else:
            st.caption("Native TradingAgents provider.")

        st.markdown("#### API Keys")
        api_key_env = PROVIDER_API_KEY_ENV.get(provider_key)
        if api_key_env:
            st.text_input(
                f"{get_provider_label(provider_key)} API Key",
                type="password",
                key=f"api_key_{provider_key}",
                placeholder=api_key_env,
                help=f"Saved to {USER_ENV_FILE} when you save preferences or run analysis.",
            )
            if os.environ.get(api_key_env):
                st.caption(f"{api_key_env} is already available in the current environment.")
        else:
            st.caption("Ollama does not require an API key.")

        base_url_env = PROVIDER_BASE_URL_ENV.get(provider_key)
        if base_url_env:
            st.text_input(
                "Base URL",
                key=f"base_url_{provider_key}",
                placeholder=PROVIDER_URLS.get(provider_key) or "https://host.example/v1",
                help=(
                    f"Saved as {base_url_env}. For OpenAI-compatible providers, use the Chat "
                    "Completions base URL, usually ending in /v1."
                ),
            )

        if provider_key == "azure":
            for env_name, label, placeholder in AZURE_ENV_FIELDS:
                st.text_input(
                    label,
                    key=env_name,
                    placeholder=placeholder,
                    help=f"Saved to {USER_ENV_FILE} when you save preferences or run analysis.",
                )
                if os.environ.get(env_name):
                    st.caption(f"{env_name} is already available in the current environment.")

        with st.expander("Data API Keys", expanded=False):
            st.text_input(
                "Alpha Vantage API Key",
                type="password",
                key="ALPHA_VANTAGE_API_KEY",
                placeholder="ALPHA_VANTAGE_API_KEY",
                help=f"Only needed if your TradingAgents data vendor config uses Alpha Vantage. Saved to {USER_ENV_FILE}.",
            )
            if os.environ.get("ALPHA_VANTAGE_API_KEY"):
                st.caption("ALPHA_VANTAGE_API_KEY is already available in the current environment.")

        quick_model = render_model_selector(
            "Quick-Thinking Model",
            provider_key,
            "quick",
            st.session_state.quick_model,
        )
        st.session_state.quick_model = quick_model

        deep_model = render_model_selector(
            "Deep-Thinking Model",
            provider_key,
            "deep",
            st.session_state.deep_model,
        )
        st.session_state.deep_model = deep_model

        st.divider()
        if st.button("Save Preferences", use_container_width=True):
            save_current_config()
            st.toast("Preferences and API keys saved!", icon="✅")

    api_env_values = get_api_env_values(provider_key)
    return ticker, analysis_date, language, analysts, depth_key, provider_key, quick_model, deep_model, api_env_values


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="TradingAgents", page_icon="📊", layout="wide")

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    init_session_state()

    (
        ticker,
        analysis_date,
        language,
        analysts,
        depth_key,
        provider_key,
        quick_model,
        deep_model,
        api_env_values,
    ) = render_sidebar()

    tab_run, tab_reports = st.tabs(["Run Analysis", "Browse Reports"])

    with tab_run:
        # Start button
        col_btn, col_info = st.columns([1, 5])
        with col_btn:
            run_clicked = st.button(
                "Run Analysis",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.get("running", False),
            )
        with col_info:
            summary = {
                "ticker": ticker or "(no ticker)",
                "date": str(analysis_date),
                "language": language,
                "provider": provider_key,
                "depth": depth_key,
                "quick": quick_model,
                "deep": deep_model,
                "analysts": ", ".join(analysts) or "(none)",
            }
            st.markdown(
                f"<div style='font-size:0.82rem;color:#888;padding-top:0.5rem;'>"
                f"<b>{html_lib.escape(summary['ticker'])}</b> &middot; {html_lib.escape(summary['date'])} &middot; "
                f"{html_lib.escape(summary['language'])} &middot; {html_lib.escape(summary['provider'])} &middot; "
                f"{html_lib.escape(summary['depth'])}<br>"
                f"Quick: {html_lib.escape(summary['quick'])} &middot; Deep: {html_lib.escape(summary['deep'])} &middot; "
                f"Analysts: {html_lib.escape(summary['analysts'])}</div>",
                unsafe_allow_html=True,
            )

        if run_clicked:
            if not ticker:
                st.error("Please enter a ticker symbol.")
            elif not analysts:
                st.error("Please select at least one analyst.")
            elif not quick_model or not deep_model:
                st.error("Please select both thinking models.")
            elif missing_required_credentials(provider_key, api_env_values):
                missing = ", ".join(missing_required_credentials(provider_key, api_env_values))
                st.error(f"Please enter required credentials: {missing}")
            else:
                save_current_config()
                # Reset analysis state
                st.session_state.agent_status = {}
                st.session_state.messages = []
                st.session_state.tool_calls = []
                st.session_state.report_sections = {}
                st.session_state.final_report = None
                st.session_state.current_report = None
                st.session_state.start_time = time.time()
                st.session_state.llm_calls = 0
                st.session_state.tool_call_count = 0
                st.session_state.tokens_in = 0
                st.session_state.tokens_out = 0
                st.session_state.running = True
                st.session_state.analysis_done = False
                st.session_state.analysis_error = None
                st.session_state.report_dir = None

                # Build shared state dict for the thread
                state = {
                    "agent_status": st.session_state.agent_status,
                    "messages": st.session_state.messages,
                    "tool_calls": st.session_state.tool_calls,
                    "report_sections": st.session_state.report_sections,
                    "current_report": None,
                    "final_report": None,
                    "llm_calls": 0,
                    "tool_call_count": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "done": False,
                    "error": None,
                    "report_dir": None,
                }
                st.session_state["_analysis_state"] = state

                thread = threading.Thread(
                    target=_run_analysis_thread,
                    args=(ticker, analysis_date, language, analysts, DEPTH_OPTIONS[depth_key],
                          provider_key, quick_model, deep_model, api_env_values, state),
                    daemon=True,
                )
                thread.start()
                st.rerun()

        has_analysis_output = bool(
            st.session_state.get("running")
            or st.session_state.get("current_report")
            or st.session_state.get("final_report")
            or st.session_state.get("messages")
            or st.session_state.get("analysis_error")
        )

        # If analysis is running or has results, show the live view
        if has_analysis_output:
            state = st.session_state.get("_analysis_state", {})

            # Sync stats back from thread state
            st.session_state.llm_calls = state.get("llm_calls", 0)
            st.session_state.tool_call_count = state.get("tool_call_count", 0)
            st.session_state.tokens_in = state.get("tokens_in", 0)
            st.session_state.tokens_out = state.get("tokens_out", 0)
            if state.get("current_report"):
                st.session_state.current_report = state["current_report"]
            if state.get("final_report"):
                st.session_state.final_report = state["final_report"]
                st.session_state.current_report = state["final_report"]
            if state.get("report_dir"):
                st.session_state.report_dir = state["report_dir"]
            if state.get("error"):
                st.session_state.analysis_error = state["error"]

            # Render the analysis view
            render_analysis_view(
                {
                    "agent_status": st.session_state.agent_status,
                    "messages": st.session_state.messages,
                    "tool_calls": st.session_state.tool_calls,
                    "report_sections": st.session_state.report_sections,
                    "current_report": st.session_state.get("current_report"),
                    "final_report": st.session_state.get("final_report"),
                    "llm_calls": st.session_state.llm_calls,
                    "tool_call_count": st.session_state.tool_call_count,
                    "tokens_in": st.session_state.tokens_in,
                    "tokens_out": st.session_state.tokens_out,
                    "start_time": st.session_state.start_time,
                },
                analysts,
            )

            # Auto-refresh while running
            if st.session_state.get("running") and not state.get("done"):
                time.sleep(1.5)
                st.rerun()
            elif st.session_state.get("running"):
                st.session_state.running = False
                st.session_state.analysis_done = True
                if state.get("error"):
                    st.error(f"Analysis failed: {state['error']}")
                    if state.get("traceback"):
                        with st.expander("Error details"):
                            st.code(state["traceback"])
                else:
                    st.success(f"Analysis complete! Report saved to `{st.session_state.get('report_dir', '')}`")
            elif st.session_state.get("analysis_error"):
                st.error(f"Analysis failed: {st.session_state.analysis_error}")

    with tab_reports:
        browse_reports_ui()


if __name__ == "__main__":
    main()
