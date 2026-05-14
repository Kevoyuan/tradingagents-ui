"""TradingAgents UI - Lightweight Streamlit wrapper with CLI-style layout."""

from __future__ import annotations

import datetime
import html as html_lib
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values, set_key, unset_key

try:
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
except ModuleNotFoundError:
    DEFAULT_CONFIG = {}
    MODEL_OPTIONS = {}

from preferences import PREFS_DIR, load_preferences, save_preferences
from ui_config import (
    ALL_TEAMS,
    ANALYST_KEY_MAP,
    ANALYST_OPTIONS,
    ANALYST_REPORT_MAP,
    AZURE_ENV_FIELDS,
    DEPTH_OPTIONS,
    LANGUAGES,
    OPTIONAL_API_KEY_PROVIDERS,
    PROVIDER_API_KEY_ENV,
    PROVIDER_BASE_URL_ENV,
    PROVIDER_MODEL_OPTIONS,
    PROVIDER_RUNTIME,
    PROVIDER_URLS,
    PROVIDERS,
)
from ui_panels import render_messages_panel, render_progress_panel
from ui_styles import CUSTOM_CSS

MANAGED_ENV_NAMES = tuple(
    dict.fromkeys(
        [
            *PROVIDER_API_KEY_ENV.values(),
            *PROVIDER_BASE_URL_ENV.values(),
            *(env_name for env_name, _, _ in AZURE_ENV_FIELDS),
            "ALPHA_VANTAGE_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        ]
    )
)
RUN_ENV_LOCK = threading.Lock()
USER_ENV_FILE = PREFS_DIR / ".env"
PROJECT_ROOT = Path(__file__).resolve().parent
BAOYU_MARKDOWN_TO_HTML_SCRIPT = PROJECT_ROOT / "tools" / "baoyu-markdown-to-html" / "scripts" / "main.ts"
BAOYU_MARKDOWN_TO_HTML_DIR = BAOYU_MARKDOWN_TO_HTML_SCRIPT.parent
BAOYU_INSTALL_LOCK = threading.Lock()
HTML_REPORT_THEME_VERSION = "quant-terminal-readme-shot-v2"
TRADINGAGENTS_REPO_URL = "https://github.com/TauricResearch/TradingAgents.git"


def is_local_persistence_enabled() -> bool:
    return os.environ.get("TRADINGAGENTS_UI_LOCAL") == "1"


def find_tradingagents_checkout() -> Path | None:
    """Return an explicitly configured local TradingAgents checkout, if present."""
    env_dir = os.environ.get("TRADINGAGENTS_DIR")
    if not env_dir:
        return None
    candidate = Path(env_dir).expanduser().resolve()
    return candidate if (candidate / ".git").exists() else None


def is_tradingagents_installed() -> bool:
    return importlib.util.find_spec("tradingagents") is not None


def installed_tradingagents_version() -> str:
    try:
        return importlib.metadata.version("tradingagents")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def git_output(args: list[str], cwd: Path | None = None, timeout: int = 15) -> str:
    return subprocess.check_output(
        args,
        cwd=cwd,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    ).strip()


def tag_sort_key(tag: str) -> tuple:
    """Best-effort version-ish sort key for git tags such as v0.1.2."""
    parts = re.split(r"([0-9]+)", tag.lstrip("vV"))
    return tuple((0, int(part)) if part.isdigit() else (1, part.lower()) for part in parts)


def normalize_version_tag(value: object) -> str:
    """Normalize package versions and git tags enough for update comparisons."""
    cleaned = str(value or "").strip()
    if not cleaned or cleaned in {"unknown", "missing"}:
        return ""
    return cleaned.split("+", 1)[0].lstrip("vV")


def latest_remote_tradingagents_tag() -> str:
    output = git_output(["git", "ls-remote", "--tags", "--refs", TRADINGAGENTS_REPO_URL], timeout=20)
    tags = []
    for line in output.splitlines():
        ref = line.rsplit("/", 1)[-1].strip()
        if ref:
            tags.append(ref)
    return sorted(tags, key=tag_sort_key)[-1] if tags else "unknown"


def latest_local_checkout_tag(repo_dir: Path) -> str:
    try:
        return git_output(["git", "describe", "--tags", "--abbrev=0", "HEAD"], cwd=repo_dir, timeout=10)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def checkout_has_local_changes(repo_dir: Path) -> bool:
    try:
        return bool(git_output(["git", "status", "--porcelain"], cwd=repo_dir, timeout=10))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return True


@st.cache_data(ttl=3600, show_spinner=False)
def cached_tradingagents_update_status() -> dict[str, str | bool]:
    """Check GitHub update status for TradingAgents without mutating the environment."""
    checkout = find_tradingagents_checkout()
    try:
        remote_tag = latest_remote_tradingagents_tag()
    except Exception as exc:
        return {
            "mode": "local checkout" if checkout else "installed package",
            "installed": is_tradingagents_installed(),
            "installed_version": installed_tradingagents_version(),
            "local_tag": latest_local_checkout_tag(checkout) if checkout else "unknown",
            "remote_tag": "unknown",
            "dirty": checkout_has_local_changes(checkout) if checkout else False,
            "update_available": False,
            "error": str(exc),
        }

    if checkout:
        local_tag = latest_local_checkout_tag(checkout)
        dirty = checkout_has_local_changes(checkout)
        return {
            "mode": "local checkout",
            "path": str(checkout),
            "installed": is_tradingagents_installed(),
            "installed_version": installed_tradingagents_version(),
            "local_tag": local_tag,
            "remote_tag": remote_tag,
            "dirty": dirty,
            "update_available": bool(remote_tag != "unknown" and local_tag != "unknown" and remote_tag != local_tag),
            "error": "",
        }

    installed = is_tradingagents_installed()
    installed_version = installed_tradingagents_version() if installed else "missing"
    normalized_installed = normalize_version_tag(installed_version)
    normalized_remote = normalize_version_tag(remote_tag)
    return {
        "mode": "installed package",
        "installed": installed,
        "installed_version": installed_version,
        "local_tag": "unknown",
        "remote_tag": remote_tag,
        "dirty": False,
        "update_available": bool(
            (not installed)
            or (normalized_installed and normalized_remote and normalized_installed != normalized_remote)
        ),
        "error": "",
    }


def should_show_tradingagents_update_icon(status: dict[str, str | bool]) -> bool:
    """Only surface the update control when the silent check found useful action."""
    return bool(status.get("update_available") and not status.get("error"))


def update_tradingagents_from_app(status: dict[str, str | bool]) -> tuple[bool, str]:
    """Install or update TradingAgents from the Streamlit app."""
    checkout_path = status.get("path")
    if checkout_path:
        repo_dir = Path(str(checkout_path))
        if checkout_has_local_changes(repo_dir):
            return False, f"Local TradingAgents checkout has uncommitted changes: {repo_dir}"
        try:
            try:
                subprocess.run(["git", "pull", "--ff-only"], cwd=repo_dir, check=True, text=True, capture_output=True)
            except subprocess.CalledProcessError:
                subprocess.run(["git", "pull", "--rebase"], cwd=repo_dir, check=True, text=True, capture_output=True)
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repo_dir), "--quiet"], check=True)
            return True, f"Updated local TradingAgents checkout: {repo_dir}"
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return False, detail

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", f"git+{TRADINGAGENTS_REPO_URL}", "--quiet"],
            check=True,
            text=True,
            capture_output=True,
        )
        return True, "Installed or updated TradingAgents from GitHub."
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, detail


def safe_report_filename_part(value: str) -> str:
    """Make provider/model IDs safe and readable in saved report filenames."""
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "-" for ch in str(value or "unknown"))
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned[:80] or "unknown"

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
                return str(mid)
    return display


def get_model_display(provider: str, mode: str, model_id: str, choices: list[str]) -> str | None:
    p = provider.lower()
    provider_options = PROVIDER_MODEL_OPTIONS.get(p, MODEL_OPTIONS.get(p))
    if not model_id or not provider_options or mode not in provider_options:
        return None
    for display, mid in provider_options[mode]:
        if model_id == mid or model_id in display:
            return str(display)
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
        return PROVIDER_URLS.get(provider)
    return PROVIDER_URLS.get(provider)


def get_runtime_llm_config(provider: str, api_env_values: dict[str, str]) -> tuple[str, str | None, dict[str, str]]:
    runtime_provider = PROVIDER_RUNTIME.get(provider, provider)
    backend_url = get_provider_base_url(provider, api_env_values)
    runtime_env_values = dict(api_env_values)

    source_api_env = PROVIDER_API_KEY_ENV.get(provider)
    runtime_api_env = PROVIDER_API_KEY_ENV.get(runtime_provider)
    if source_api_env and runtime_api_env and source_api_env != runtime_api_env:
        source_key = api_env_values.get(source_api_env, "")
        if source_key:
            runtime_env_values[runtime_api_env] = source_key
            if runtime_provider == "anthropic":
                runtime_env_values["ANTHROPIC_AUTH_TOKEN"] = source_key
        elif provider in OPTIONAL_API_KEY_PROVIDERS:
            runtime_env_values[runtime_api_env] = "sk-no-key-required"
            if runtime_provider == "anthropic":
                runtime_env_values["ANTHROPIC_AUTH_TOKEN"] = "sk-no-key-required"

    return runtime_provider, backend_url, runtime_env_values


def render_model_selector(label: str, provider: str, mode: str, saved_model: str) -> str:
    choices = get_model_choices(provider, mode)
    if not choices:
        return st.text_input(f"{label} ID", value=saved_model or "", key=f"model_text_{provider}_{mode}")

    saved_display = get_model_display(provider, mode, saved_model, choices)
    index = choices.index(saved_display) if saved_display in choices else 0
    display = st.selectbox(label, choices, index=index, key=f"model_select_{provider}_{mode}")
    selected_id = get_model_id(provider, mode, display)
    if selected_id == "custom":
        return st.text_input(
            f"{label} Custom ID",
            value=saved_model if saved_model != "custom" else "",
            key=f"model_custom_{provider}_{mode}",
        )
    return selected_id


def get_saved_provider_model(provider: str, mode: str, fallback: str) -> str:
    profiles = st.session_state.setdefault("provider_model_profiles", {})
    provider_profile = profiles.get(provider, {})
    return str(provider_profile.get(mode, fallback))


def remember_provider_models(provider: str, quick_model: str, deep_model: str):
    profiles = st.session_state.setdefault("provider_model_profiles", {})
    profiles[provider] = {"quick": quick_model, "deep": deep_model}


def build_api_key_profile_id(provider: str, quick_model: str, deep_model: str) -> str:
    return f"{provider}|quick:{quick_model or ''}|deep:{deep_model or ''}"


def sync_provider_api_key_input(provider: str, profile_id: str):
    """Switch the visible API key field when provider/model profile changes."""
    profiles = st.session_state.setdefault("api_key_profiles", {})
    provider_profiles = profiles.setdefault(provider, {})
    current_cursor = f"{provider}::{profile_id}"
    previous_cursor = st.session_state.get("_api_key_profile_cursor")

    if previous_cursor and previous_cursor != current_cursor:
        prev_provider, prev_profile = previous_cursor.split("::", 1)
        prev_profiles = profiles.setdefault(prev_provider, {})
        prev_value = st.session_state.get(f"api_key_{prev_provider}", "").strip()
        prev_profiles[prev_profile] = prev_value
        st.session_state[f"api_key_{prev_provider}"] = prev_value

    if previous_cursor != current_cursor:
        fallback = st.session_state.get(f"api_key_{provider}", "")
        st.session_state[f"api_key_{provider}"] = provider_profiles.get(profile_id, fallback)
        st.session_state["_api_key_profile_cursor"] = current_cursor


def init_session_state():
    if "initialized" not in st.session_state:
        prefs = load_preferences()
        saved_env = load_saved_api_env_values() if is_local_persistence_enabled() else {}

        st.session_state.ticker = prefs.get("ticker", "")
        st.session_state.analysis_date = datetime.date.today().isoformat()
        st.session_state.language = prefs.get("output_language", "English")
        st.session_state.analysts = normalize_saved_analysts(prefs.get("analysts", []))
        st.session_state.depth_key = prefs.get("depth_key", "Deep (5 rounds)")
        st.session_state.provider = prefs.get("llm_provider", "deepseek")
        st.session_state.quick_model = prefs.get("quick_think_llm", "")
        st.session_state.deep_model = prefs.get("deep_think_llm", "")
        st.session_state.provider_model_profiles = prefs.get("provider_model_profiles", {})
        st.session_state.api_key_profiles = prefs.get("api_key_profiles", {}) if is_local_persistence_enabled() else {}

        for provider, env_name in PROVIDER_API_KEY_ENV.items():
            st.session_state[f"api_key_{provider}"] = saved_env.get(env_name, "")
        for provider, env_name in PROVIDER_BASE_URL_ENV.items():
            st.session_state[f"base_url_{provider}"] = saved_env.get(env_name, PROVIDER_URLS.get(provider, "") or "")
        for env_name, _, _ in AZURE_ENV_FIELDS:
            st.session_state[env_name] = saved_env.get(env_name, "")
        st.session_state["ALPHA_VANTAGE_API_KEY"] = saved_env.get("ALPHA_VANTAGE_API_KEY", "")

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
        "provider_model_profiles": st.session_state.get("provider_model_profiles", {}),
        **({"api_key_profiles": st.session_state.get("api_key_profiles", {})} if is_local_persistence_enabled() else {}),
    })
    if is_local_persistence_enabled():
        save_api_env_file(get_all_api_env_values())


def load_saved_api_env_values() -> dict[str, str]:
    """Load persisted local credentials from the UI-owned .env file."""
    try:
        raw_values = dotenv_values(USER_ENV_FILE)
    except OSError:
        return {}
    return {
        env_name: str(value).strip()
        for env_name, value in raw_values.items()
        if env_name in MANAGED_ENV_NAMES and value
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
    """Persist local credentials to ~/.tradingagents/.env."""
    PREFS_DIR.mkdir(parents=True, exist_ok=True)
    USER_ENV_FILE.touch(exist_ok=True)
    try:
        os.chmod(USER_ENV_FILE, 0o600)
    except OSError:
        pass

    existing_values = dotenv_values(USER_ENV_FILE)
    for env_name in MANAGED_ENV_NAMES:
        if env_name == "ANTHROPIC_AUTH_TOKEN":
            continue
        value = env_values.get(env_name, "").strip()
        if value:
            set_key(str(USER_ENV_FILE), env_name, value, quote_mode="always")
        elif env_name in existing_values:
            unset_key(str(USER_ENV_FILE), env_name)


def credential_help_text() -> str:
    if is_local_persistence_enabled():
        return f"Saved locally to {USER_ENV_FILE} when you save preferences or run analysis."
    return "Used only for the current app session. It is not saved to GitHub, Streamlit Secrets, or disk."


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
    if override:
        for env_name in MANAGED_ENV_NAMES:
            os.environ.pop(env_name, None)
    for env_name, value in env_values.items():
        if value and (override or not os.environ.get(env_name)):
            os.environ[env_name] = value


def missing_required_credentials(provider: str, env_values: dict[str, str]) -> list[str]:
    missing = []
    api_key_env = PROVIDER_API_KEY_ENV.get(provider)
    if (
        api_key_env
        and provider not in OPTIONAL_API_KEY_PROVIDERS
        and not env_values.get(api_key_env)
    ):
        missing.append(api_key_env)

    if provider == "azure":
        for env_name, _, _ in AZURE_ENV_FIELDS:
            if not env_values.get(env_name):
                missing.append(env_name)

    base_url_env = PROVIDER_BASE_URL_ENV.get(provider)
    if base_url_env and not (
        env_values.get(base_url_env) or PROVIDER_URLS.get(provider)
    ):
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


def get_bun_command() -> list[str]:
    """Return a Bun command suitable for the vendored baoyu markdown converter."""
    if shutil.which("bun"):
        return ["bun"]
    if shutil.which("npx"):
        return ["npx", "-y", "bun"]
    raise RuntimeError("Generate HTML requires `bun` or `npx` to run the bundled markdown converter.")


def ensure_baoyu_dependencies():
    """Install vendored converter dependencies on first use."""
    package_json = BAOYU_MARKDOWN_TO_HTML_DIR / "package.json"
    marked_package = BAOYU_MARKDOWN_TO_HTML_DIR / "node_modules" / "marked" / "package.json"
    if marked_package.exists():
        return
    if not package_json.exists():
        raise RuntimeError(f"Bundled markdown converter package.json not found: {package_json}")

    with BAOYU_INSTALL_LOCK:
        if marked_package.exists():
            return
        cmd = [*get_bun_command(), "install"]
        result = subprocess.run(
            cmd,
            cwd=BAOYU_MARKDOWN_TO_HTML_DIR,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"Failed to install HTML converter dependencies: {detail}")


def clean_export_meta_value(value: object) -> str:
    return str(value or "").strip()


def current_report_export_meta() -> dict[str, str]:
    """Read the currently selected report metadata from the UI configuration."""
    model = clean_export_meta_value(st.session_state.get("deep_model")) or clean_export_meta_value(
        st.session_state.get("quick_model")
    )
    return {
        "ticker": clean_export_meta_value(st.session_state.get("ticker")),
        "date": clean_export_meta_value(st.session_state.get("analysis_date")),
        "model": model,
    }


def report_export_meta_from_path(report_path: Path) -> dict[str, str]:
    """Infer metadata for downloaded historical reports from the saved report path."""
    meta: dict[str, str] = {}
    parts = report_path.parts
    if len(parts) >= 4 and report_path.parent.name == "reports":
        meta["date"] = report_path.parent.parent.name
        meta["ticker"] = report_path.parent.parent.parent.name

    match = re.search(r"complete_report__deep-(.+)\.md$", report_path.name)
    if match:
        meta["model"] = match.group(1)
    return meta


def generate_html_report(markdown_report: str, metadata: dict[str, str] | None = None) -> tuple[str, str]:
    """Generate a self-contained HTML report with the vendored baoyu markdown-to-html skill."""
    if not BAOYU_MARKDOWN_TO_HTML_SCRIPT.exists():
        raise RuntimeError(f"Bundled markdown converter not found: {BAOYU_MARKDOWN_TO_HTML_SCRIPT}")
    ensure_baoyu_dependencies()
    metadata = metadata or {}

    with tempfile.TemporaryDirectory(prefix="tradingagents-report-") as tmp:
        markdown_path = Path(tmp) / "tradingagents_report.md"
        markdown_path.write_text(markdown_report, encoding="utf-8")
        cmd = [
            *get_bun_command(),
            str(BAOYU_MARKDOWN_TO_HTML_SCRIPT),
            str(markdown_path),
            "--theme",
            "quant-terminal",
            "--keep-title",
        ]
        if metadata.get("ticker"):
            cmd.extend(["--qt-ticker", metadata["ticker"]])
        if metadata.get("date"):
            cmd.extend(["--qt-date", metadata["date"]])
        if metadata.get("model"):
            cmd.extend(["--qt-model", metadata["model"]])
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"HTML generation failed: {detail}")

        try:
            payload = json.loads(result.stdout)
            html_path = Path(payload["htmlPath"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(f"HTML generation returned invalid output: {result.stdout}") from exc
        return html_path.read_text(encoding="utf-8"), html_path.name


@st.cache_data(show_spinner=False)
def cached_generate_html_report(
    markdown_report: str,
    metadata_items: tuple[tuple[str, str], ...],
) -> tuple[str, str]:
    """Cache deterministic HTML exports so opening a report does not re-run the converter."""
    return generate_html_report(markdown_report, dict(metadata_items))


def render_open_html_button(html_report: str, key: str):
    """Render a browser-side button that opens the generated HTML in a new tab."""
    import streamlit.components.v1 as components

    safe_html = json.dumps(html_report, ensure_ascii=False).replace("</script>", "<\\/script>")
    open_html = f"""
    <style>
    body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
    .open-html-btn {{
        width: 100%;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.22);
        color: #f5f5f5;
        padding: 10px 12px;
        border-radius: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 0.88rem;
        font-weight: 650;
        cursor: pointer;
        transition: all 0.2s;
        display: block;
        box-sizing: border-box;
    }}
    .open-html-btn:hover {{
        border-color: rgba(0, 255, 136, 0.65);
        color: #00ff88;
        background: rgba(0, 255, 136, 0.08);
    }}
    .open-html-btn:active {{ transform: scale(0.99); }}
    </style>
    <button id="{key}" class="open-html-btn">Open HTML</button>
    <script>
        const html = {safe_html};
        const btn = document.getElementById({json.dumps(key)});
        btn.onclick = function() {{
            const blob = new Blob([html], {{ type: "text/html;charset=utf-8" }});
            const url = URL.createObjectURL(blob);
            const opened = window.open(url, "_blank", "noopener,noreferrer");
            if (!opened) {{
                btn.innerText = "Allow pop-ups and click again";
                setTimeout(() => {{
                    btn.innerText = "Open HTML";
                }}, 2500);
            }}
            setTimeout(() => URL.revokeObjectURL(url), 60000);
        }};
    </script>
    """
    components.html(open_html, height=48)


def render_inline_html(html: str, height: int, scrolling: bool = True):
    """Render inline HTML in a script-capable iframe."""
    import streamlit.components.v1 as components

    components.html(html, height=height, scrolling=scrolling)


def render_copy_markdown_button(report_content: str):
    """Render the report Markdown copy button."""
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
    if hasattr(st, "html"):
        st.html(copy_html)
    else:
        import streamlit.components.v1 as components
        components.html(copy_html, height=45)


def render_report_with_nav(
    report_content: str,
    id_prefix: str = "report",
    export_metadata: dict[str, str] | None = None,
    show_copy_button: bool = True,
):
    """Render report with a navigation sidebar in the left column."""
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
                nav_html += (
                    f'<a href="#{slug}" target="_self" class="report-nav-item {level_class}"'
                    f' style="padding-left: {12+indent}px;">{title}</a>'
                )
            nav_html += '</div>'
            st.markdown(nav_html, unsafe_allow_html=True)

        if show_copy_button:
            render_copy_markdown_button(report_content)

        export_ready = id_prefix != "live" or st.session_state.get("analysis_done", False)
        if export_ready:
            try:
                metadata = export_metadata or current_report_export_meta()
                metadata_items = tuple(sorted((str(k), str(v)) for k, v in metadata.items()))
                metadata_items = (("__theme_version", HTML_REPORT_THEME_VERSION), *metadata_items)
                with st.spinner("Preparing HTML..."):
                    html_report, _html_filename = cached_generate_html_report(report_content, metadata_items)
                render_open_html_button(
                    html_report,
                    key=f"{id_prefix}-open-html-btn",
                )
                st.caption("HTML export is no-token and does not call a model.")
            except Exception as exc:
                st.error(str(exc))
        else:
            st.caption("HTML export is available after the report is complete.")

    with col_content, st.container(height=800, border=False):
        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown(processed_content, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── Analysis Runner (background thread) ────────────────────────────────────────

def _run_analysis_thread(
    ticker, date, language, analysts, depth, provider, quick_model, deep_model, api_env_values, state
):
    """Run analysis in a background thread, writing results to shared state dict."""
    with RUN_ENV_LOCK:
        try:
            runtime_provider, backend_url, runtime_env_values = get_runtime_llm_config(provider, api_env_values)
            apply_api_env_values(runtime_env_values)

            from cli.stats_handler import StatsCallbackHandler
            from tradingagents.graph.trading_graph import TradingAgentsGraph

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
            for _team, agents in ALL_TEAMS.items():
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
                agent_name: str | None = ANALYST_KEY_MAP.get(analyst_key)
                if agent_name and agent_name in state["agent_status"]:
                    state["agent_status"][agent_name] = "in_progress"
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
            complete_report_path = report_dir / "complete_report.md"
            complete_report_path.write_text(complete_report, encoding="utf-8")
            model_report_name = (
                "complete_report__"
                f"deep-{safe_report_filename_part(deep_model)}.md"
            )
            model_report_path = report_dir / model_report_name
            model_report_path.write_text(complete_report, encoding="utf-8")

            # Create a symlink to the latest report in the user data directory.
            latest_symlink = Path.home() / ".tradingagents" / "latest_report.md"
            try:
                latest_symlink.parent.mkdir(parents=True, exist_ok=True)
                if latest_symlink.exists() or latest_symlink.is_symlink():
                    latest_symlink.unlink()
                latest_symlink.symlink_to(complete_report_path)
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
            for env_name in MANAGED_ENV_NAMES:
                os.environ.pop(env_name, None)
            state["done"] = True


# ── UI Renderers ───────────────────────────────────────────────────────────────



def render_stats_bar(
    agent_status, llm_calls, tool_calls, tokens_in, tokens_out, report_sections, start_time, selected_analysts,
):
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
            '<div class="panel top-panel"><div class="scanning-line"></div>'
            f'<div class="panel-title">Progress</div>{progress_html}</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        messages_html = render_messages_panel(
            analysis_state.get("messages", []),
            analysis_state.get("tool_calls", []),
        )
        st.markdown(
            '<div class="panel messages-panel"><div class="scanning-line"></div>'
            '<div class="panel-title">Messages &amp; Tools</div>'
            f'<div class="messages-scroll">{messages_html}</div></div>',
            unsafe_allow_html=True,
        )

    # Report section
    report = analysis_state.get("current_report") or analysis_state.get("final_report")
    st.markdown(
        '<div class="panel"><div class="scanning-line"></div><div class="panel-title">Analysis Report</div>',
        unsafe_allow_html=True,
    )
    render_report_with_nav(report or "", id_prefix="live")
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

    # Let user pick a report — sort by creation time, newest first
    entries: list[dict[str, object]] = []
    for rp in report_dirs:
        parent = rp.parent.name
        name = rp.name
        reports_dir = rp / "reports"
        model_reports = sorted(
            reports_dir.glob("complete_report__deep-*.md"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ) if reports_dir.exists() else []
        rf = model_reports[0] if model_reports else reports_dir / "complete_report.md"
        stat = rf.stat()
        created_ts = getattr(stat, "st_birthtime", None) or stat.st_ctime or stat.st_mtime
        created_time = datetime.datetime.fromtimestamp(created_ts)
        entries.append(
            {
                "label": f"{parent}/{name}  —  {created_time.strftime('%Y-%m-%d %H:%M')}",
                "report_path": rf,
                "sort_time": created_time,
            }
        )
    entries.sort(key=lambda x: x["sort_time"], reverse=True)  # type: ignore[arg-type,return-value]
    labels = [str(item["label"]) for item in entries]
    label_to_path: dict[str, Path] = {str(item["label"]): Path(str(item["report_path"])) for item in entries}

    select_col, view_col, copy_col = st.columns([5, 2, 5], gap="medium", vertical_alignment="center")
    with select_col:
        selected = st.selectbox(
            "Select a report",
            labels,
            index=0,
            label_visibility="collapsed",
        )

    if selected:
        rf = label_to_path[selected]
        if rf.exists():
            content = rf.read_text(encoding="utf-8")
            metadata = report_export_meta_from_path(rf)
            with view_col:
                view_mode = st.radio(
                    "Report view",
                    ["HTML", "Markdown"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="browse_report_view_mode",
                )
            with copy_col:
                render_copy_markdown_button(content)
            if view_mode == "HTML":
                try:
                    metadata_items = tuple(sorted((str(k), str(v)) for k, v in metadata.items()))
                    metadata_items = (("__theme_version", HTML_REPORT_THEME_VERSION), *metadata_items)
                    with st.spinner("Rendering HTML report..."):
                        html_report, _html_filename = cached_generate_html_report(content, metadata_items)
                    render_inline_html(html_report, height=1100, scrolling=True)
                except Exception as exc:
                    st.error(str(exc))
                    st.caption("Showing Markdown fallback.")
                    render_report_with_nav(
                        content,
                        id_prefix="browse",
                        export_metadata=metadata,
                        show_copy_button=False,
                    )
            else:
                render_report_with_nav(
                    content,
                    id_prefix="browse",
                    export_metadata=metadata,
                    show_copy_button=False,
                )
            st.markdown("---")
            st.caption(f"Path: `{rf}`")


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar_brand():
    update_status = cached_tradingagents_update_status()
    show_update_icon = should_show_tradingagents_update_icon(update_status)
    brand_html = (
        '<div style="padding:0.5rem 0 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.05);'
        ' margin-bottom: 1.5rem;">'
        '<div style="font-size:2.2rem;font-weight:800;color:#00ff88;letter-spacing:-0.03em;'
        'line-height:1.1;text-shadow: 0 0 12px rgba(0,255,136,0.4);">TradingAgents</div>'
        '<div style="font-size:0.75rem;color:#8b949e;font-family:\'JetBrains Mono\',monospace;'
        'opacity:0.8;margin-top:0.6rem;letter-spacing:0.05em;">'
        'v1.2.0 &middot; INDUSTRIAL CONTROL PANEL</div></div>'
    )

    if not show_update_icon:
        st.markdown(brand_html, unsafe_allow_html=True)
        return

    logo_col, update_col = st.columns([0.82, 0.18], vertical_alignment="top")
    with logo_col:
        st.markdown(brand_html, unsafe_allow_html=True)
    with update_col:
        st.markdown("<div style='height:0.42rem'></div>", unsafe_allow_html=True)
        help_text = (
            f"Update TradingAgents to {update_status.get('remote_tag', 'the latest GitHub version')}"
        )
        can_update = not bool(update_status.get("dirty"))
        if st.button("↥", key="tradingagents_update_icon", help=help_text, disabled=not can_update):
            with st.spinner("Updating TradingAgents..."):
                ok, message = update_tradingagents_from_app(update_status)
            cached_tradingagents_update_status.clear()
            if ok:
                st.success(message)
                st.caption("Restart the app to make sure loaded TradingAgents modules refresh.")
            else:
                st.error(message)
        if update_status.get("dirty"):
            st.caption("Local changes")


def render_sidebar():
    with st.sidebar:
        render_sidebar_brand()

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

        depth_key = st.selectbox(
            "Research Depth", list(DEPTH_OPTIONS.keys()),
            index=list(DEPTH_OPTIONS.keys()).index(st.session_state.depth_key)
            if st.session_state.depth_key in DEPTH_OPTIONS else 2,
        )
        st.session_state.depth_key = depth_key

        provider_display = [d for d, _ in PROVIDERS]
        provider_keys = [k for _, k in PROVIDERS]
        provider_idx = (
            provider_keys.index(st.session_state.provider)
            if st.session_state.provider in provider_keys else 4
        )
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

        quick_model = render_model_selector(
            "Quick-Thinking Model",
            provider_key,
            "quick",
            get_saved_provider_model(provider_key, "quick", st.session_state.quick_model),
        )
        st.session_state.quick_model = quick_model

        deep_model = render_model_selector(
            "Deep-Thinking Model",
            provider_key,
            "deep",
            get_saved_provider_model(provider_key, "deep", st.session_state.deep_model),
        )
        st.session_state.deep_model = deep_model
        remember_provider_models(provider_key, quick_model, deep_model)

        st.markdown("#### API Keys")
        api_key_env = PROVIDER_API_KEY_ENV.get(provider_key)
        if api_key_env:
            profile_id = build_api_key_profile_id(provider_key, quick_model, deep_model)
            sync_provider_api_key_input(provider_key, profile_id)
            st.text_input(
                f"{get_provider_label(provider_key)} API Key",
                type="password",
                key=f"api_key_{provider_key}",
                placeholder=api_key_env,
                help=credential_help_text(),
            )
            active_value = st.session_state.get(f"api_key_{provider_key}", "").strip()
            st.session_state.setdefault("api_key_profiles", {}).setdefault(provider_key, {})[profile_id] = active_value
        else:
            st.caption("Ollama does not require an API key.")

        base_url_env = PROVIDER_BASE_URL_ENV.get(provider_key)
        if base_url_env:
            st.text_input(
                "Base URL",
                key=f"base_url_{provider_key}",
                placeholder=PROVIDER_URLS.get(provider_key) or "https://host.example/v1",
                help=(
                    f"Used as {base_url_env}. For OpenAI-compatible providers, "
                    "use the Chat Completions base URL, usually ending in /v1."
                ),
            )

        if provider_key == "azure":
            for env_name, label, placeholder in AZURE_ENV_FIELDS:
                st.text_input(
                    label,
                    key=env_name,
                    placeholder=placeholder,
                    help=credential_help_text(),
                )

        with st.expander("Data API Keys", expanded=False):
            st.text_input(
                "Alpha Vantage API Key",
                type="password",
                key="ALPHA_VANTAGE_API_KEY",
                placeholder="ALPHA_VANTAGE_API_KEY",
                help=(
                    "Only needed if your TradingAgents data vendor config uses Alpha Vantage."
                    f" {credential_help_text()}"
                ),
            )

        st.divider()
        if st.button("Save Preferences", use_container_width=True):
            save_current_config()
            if is_local_persistence_enabled():
                st.toast("Preferences and local API keys saved.", icon="✅")
            else:
                st.toast("Preferences saved. API keys stay session-only.", icon="✅")

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
                f"Quick: {html_lib.escape(summary['quick'])} &middot; "
                f"Deep: {html_lib.escape(summary['deep'])} &middot; "
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
