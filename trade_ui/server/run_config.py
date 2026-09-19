# Duplication is deliberate: app.py keeps its own copy until it is deleted.
# Do NOT refactor app.py to share this module; the legacy UI is on its way out
# and touching it risks breaking a working app for no benefit.

"""Run configuration resolution, credential precedence, and upstream config assembly."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Any

from runtime_environment import effective_environment
from trade_ui.server.credentials import (
    MANAGED_ENV_NAMES,
    load_saved_env,
    load_saved_preferences,
)
from trade_ui.server.models import RunConfig
from ui_config import (
    AZURE_ENV_FIELDS,
    DEPTH_OPTIONS,
    OPTIONAL_API_KEY_PROVIDERS,
    PROVIDER_API_KEY_ENV,
    PROVIDER_BASE_URL_ENV,
    PROVIDER_MODEL_OPTIONS,
    PROVIDER_RUNTIME,
    PROVIDER_URLS,
)

try:
    from tradingagents.default_config import DEFAULT_CONFIG
except (ImportError, ModuleNotFoundError):
    DEFAULT_CONFIG = {}

try:
    from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
except (ImportError, ModuleNotFoundError):
    MODEL_OPTIONS = {}


def get_provider_base_url(provider: str, env_values: dict[str, str] | None = None) -> str | None:
    """Resolve base URL for provider from environment values or known defaults."""
    if provider in PROVIDER_BASE_URL_ENV:
        base_url_env = PROVIDER_BASE_URL_ENV[provider]
        if env_values and env_values.get(base_url_env):
            return env_values[base_url_env]
        return PROVIDER_URLS.get(provider)
    return PROVIDER_URLS.get(provider)


def get_runtime_llm_config(provider: str, api_env_values: dict[str, str]) -> tuple[str, str | None, dict[str, str]]:
    """Map provider key to runtime provider, backend URL, and populated environment dict."""
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


def missing_required_credentials(provider: str, env_values: dict[str, str]) -> list[str]:
    """Validate that all mandatory credentials for provider are present."""
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
    if provider == "bedrock" and importlib.util.find_spec("langchain_aws") is None:
        missing.append('Bedrock dependencies (`uv pip install -e ".[bedrock]"`)')

    base_url_env = PROVIDER_BASE_URL_ENV.get(provider)
    if base_url_env and not (
        env_values.get(base_url_env) or PROVIDER_URLS.get(provider)
    ):
        missing.append(base_url_env)

    return missing


def get_effective_api_env_values(
    provider: str,
    explicit_values: dict[str, str] | None = None,
    process_environment: dict[str, str] | None = None,
) -> dict[str, str]:
    """Resolve credentials in order: saved/explicit values, then ~/.tradingagents/.env, then process environment."""
    saved_env = load_saved_env()
    sidebar_or_explicit = explicit_values or {}
    return effective_environment(
        MANAGED_ENV_NAMES,
        sidebar_values=sidebar_or_explicit,
        secret_values=saved_env,
        process_environment=process_environment or os.environ,
    )


def resolve_provider_models(
    provider: str,
    quick_model: str | None,
    deep_model: str | None,
    prefs: dict[str, Any],
) -> tuple[str, str]:
    """Determine quick and deep model IDs for provider from input, preferences, or defaults."""
    p = provider.lower()
    profiles = prefs.get("provider_model_profiles", {})
    provider_profile = profiles.get(p, {}) if isinstance(profiles, dict) else {}

    # Quick model
    resolved_quick = (
        quick_model
        or (provider_profile.get("quick") if isinstance(provider_profile, dict) else None)
        or (prefs.get("quick_think_llm") if p == prefs.get("llm_provider") else None)
    )
    if not resolved_quick:
        # Pick from options
        if p in PROVIDER_MODEL_OPTIONS and "quick" in PROVIDER_MODEL_OPTIONS[p]:
            resolved_quick = PROVIDER_MODEL_OPTIONS[p]["quick"][0][1]
        elif p in MODEL_OPTIONS and "quick" in MODEL_OPTIONS[p]:
            resolved_quick = MODEL_OPTIONS[p]["quick"][0][1]
        else:
            resolved_quick = "deepseek-v4-flash"

    # Deep model
    resolved_deep = (
        deep_model
        or (provider_profile.get("deep") if isinstance(provider_profile, dict) else None)
        or (prefs.get("deep_think_llm") if p == prefs.get("llm_provider") else None)
    )
    if not resolved_deep:
        # Pick from options
        if p in PROVIDER_MODEL_OPTIONS and "deep" in PROVIDER_MODEL_OPTIONS[p]:
            resolved_deep = PROVIDER_MODEL_OPTIONS[p]["deep"][0][1]
        elif p in MODEL_OPTIONS and "deep" in MODEL_OPTIONS[p]:
            resolved_deep = MODEL_OPTIONS[p]["deep"][0][1]
        else:
            resolved_deep = "deepseek-v4-pro"

    return str(resolved_quick), str(resolved_deep)


@dataclass
class ResolvedRunConfig:
    """Complete resolved run configuration ready for UpstreamRunner."""

    provider: str
    runtime_provider: str
    backend_url: str | None
    quick_model: str
    deep_model: str
    depth: int
    language: str
    analysts: list[str]
    data_vendors: dict[str, Any]
    advanced_settings: dict[str, Any]
    runtime_env_values: dict[str, str]
    upstream_config: dict[str, Any]
    missing_credentials: list[str]


def resolve_run_config(run_config: RunConfig) -> ResolvedRunConfig:
    """Resolve RunConfig against preferences, .env, and defaults to build upstream config."""
    prefs = load_saved_preferences()
    cfg_dict = dict(run_config.config or {})

    # 1. Provider
    provider = (
        run_config.provider
        or cfg_dict.get("llm_provider")
        or cfg_dict.get("provider")
        or prefs.get("llm_provider")
        or "deepseek"
    )

    # 2. Depth
    depth_val = run_config.depth
    if depth_val is None or depth_val <= 0:
        saved_depth_key = prefs.get("depth_key", "Deep (5 rounds)")
        depth_val = DEPTH_OPTIONS.get(saved_depth_key, 5)

    # 3. Language
    language = (
        cfg_dict.get("output_language")
        or prefs.get("output_language")
        or "English"
    )

    # 4. Analysts
    analysts = (
        run_config.analysts
        or cfg_dict.get("analysts")
        or prefs.get("analysts")
        or ["market", "social", "news", "fundamentals"]
    )

    # 5. Models
    quick_model, deep_model = resolve_provider_models(
        provider,
        run_config.quick_model or cfg_dict.get("quick_think_llm"),
        run_config.deep_model or cfg_dict.get("deep_think_llm"),
        prefs,
    )

    # 6. Data vendors and advanced settings
    data_vendors = cfg_dict.get("data_vendors") or prefs.get("data_vendors") or {}
    advanced_settings = cfg_dict.get("advanced_settings") or prefs.get("advanced_settings") or {}

    # 7. Credentials resolution
    explicit_credentials = (
        cfg_dict.get("credentials")
        or cfg_dict.get("env")
        or cfg_dict.get("api_env_values")
        or {}
    )
    effective_env = get_effective_api_env_values(provider, explicit_values=explicit_credentials)

    # 8. Check missing credentials
    missing = missing_required_credentials(provider, effective_env)

    # 9. Get runtime provider, backend url, and runtime env dict
    runtime_provider, backend_url, runtime_env_values = get_runtime_llm_config(provider, effective_env)

    # 10. Assemble upstream config dict
    upstream_config = DEFAULT_CONFIG.copy()
    upstream_config["max_debate_rounds"] = depth_val
    upstream_config["max_risk_discuss_rounds"] = depth_val
    upstream_config["quick_think_llm"] = quick_model
    upstream_config["deep_think_llm"] = deep_model
    upstream_config["backend_url"] = backend_url
    upstream_config["llm_provider"] = runtime_provider
    upstream_config["output_language"] = language

    if data_vendors:
        upstream_config["data_vendors"] = data_vendors
    if advanced_settings:
        upstream_config.update({k: v for k, v in advanced_settings.items() if v is not None})

    # Merge any remaining explicit config items
    for k, v in cfg_dict.items():
        if k not in (
            "credentials",
            "env",
            "api_env_values",
            "llm_provider",
            "quick_think_llm",
            "deep_think_llm",
            "backend_url",
            "output_language",
            "max_debate_rounds",
            "max_risk_discuss_rounds",
            "data_vendors",
            "advanced_settings",
        ) and v is not None:
            upstream_config[k] = v

    return ResolvedRunConfig(
        provider=provider,
        runtime_provider=runtime_provider,
        backend_url=backend_url,
        quick_model=quick_model,
        deep_model=deep_model,
        depth=depth_val,
        language=language,
        analysts=analysts,
        data_vendors=data_vendors,
        advanced_settings=advanced_settings,
        runtime_env_values=runtime_env_values,
        upstream_config=upstream_config,
        missing_credentials=missing,
    )
