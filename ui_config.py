"""Shared UI configuration, with upstream metadata as the source of truth."""

try:
    from tradingagents.llm_clients.api_key_env import PROVIDER_API_KEY_ENV as UPSTREAM_API_KEY_ENV
except (ImportError, ModuleNotFoundError):
    UPSTREAM_API_KEY_ENV = {}

ANALYST_OPTIONS = [
    ("Market Analyst", "market"),
    ("Social Media Analyst", "social"),
    ("News Analyst", "news"),
    ("Fundamentals Analyst", "fundamentals"),
]

DEPTH_OPTIONS = {
    "Shallow (1 round)": 1,
    "Medium (3 rounds)": 3,
    "Deep (5 rounds)": 5,
}

LANGUAGES = [
    "English", "Chinese", "Japanese", "Korean", "Hindi",
    "Spanish", "Portuguese", "French", "German", "Arabic", "Russian",
]

PROVIDERS = [
    ("TradingAgents · OpenAI", "openai"),
    ("TradingAgents · Google", "google"),
    ("TradingAgents · Anthropic", "anthropic"),
    ("TradingAgents · xAI", "xai"),
    ("TradingAgents · DeepSeek", "deepseek"),
    ("TradingAgents · Qwen", "qwen"),
    ("TradingAgents · Qwen (CN)", "qwen-cn"),
    ("TradingAgents · GLM", "glm"),
    ("TradingAgents · GLM (CN)", "glm-cn"),
    ("TradingAgents · OpenRouter", "openrouter"),
    ("TradingAgents · Azure OpenAI", "azure"),
    ("TradingAgents · Ollama", "ollama"),
    ("TradingAgents · MiniMax", "minimax"),
    ("TradingAgents · MiniMax (CN)", "minimax-cn"),
    ("TradingAgents · Mistral", "mistral"),
    ("TradingAgents · Kimi (Moonshot)", "kimi"),
    ("TradingAgents · Groq", "groq"),
    ("TradingAgents · NVIDIA NIM", "nvidia"),
    ("TradingAgents · Bedrock", "bedrock"),
    ("TradingAgents · OpenAI-compatible", "openai_compatible"),
    ("Custom · Kimi Coding Plan", "kimi_coding"),
    ("Custom · Moonshot", "moonshot"),
    ("Custom · DeepSeek Anthropic API", "deepseek_anthropic"),
    ("Custom · Volcengine Ark Coding", "volcengine"),
    ("Custom · Xiaomi MiMo", "mimo"),
    ("Custom · Xiaomi MiMo Token Plan", "mimo_tokenplan"),
    ("Custom · Aliyun Bailian Coding", "bailian"),
    ("Custom · Ollama Anthropic API", "ollama_anthropic"),
    ("Custom · LiteLLM Anthropic API", "litellm"),
    ("Compatible · Custom Anthropic API", "custom_anthropic"),
]

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1", "google": None,
    "anthropic": "https://api.anthropic.com/", "xai": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com",
    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "qwen-cn": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "glm": "https://api.z.ai/api/paas/v4/",
    "glm-cn": "https://open.bigmodel.cn/api/paas/v4/",
    "openrouter": "https://openrouter.ai/api/v1",
    "azure": None, "ollama": "http://localhost:11434/v1",
    "minimax": "https://api.minimax.io/v1",
    "minimax-cn": "https://api.minimaxi.com/v1",
    "mistral": "https://api.mistral.ai/v1",
    "kimi": "https://api.moonshot.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "bedrock": None,
    "openai_compatible": "",
    "kimi_coding": "https://api.kimi.com/coding/",
    "moonshot": "https://api.moonshot.cn/anthropic",
    "deepseek_anthropic": "https://api.deepseek.com/anthropic",
    "volcengine": "https://ark.cn-beijing.volces.com/api/coding",
    "mimo": "https://api.xiaomimimo.com/anthropic",
    "mimo_tokenplan": "https://token-plan-cn.xiaomimimo.com/anthropic",
    "bailian": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
    "ollama_anthropic": "http://localhost:11434",
    "litellm": "http://localhost:4000",
    "custom_openai": "",
    "custom_anthropic": "",
}

PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "qwen-cn": "DASHSCOPE_CN_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "glm-cn": "ZHIPU_CN_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "minimax-cn": "MINIMAX_CN_API_KEY",
    **UPSTREAM_API_KEY_ENV,
    "kimi_coding": "KIMI_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "deepseek_anthropic": "DEEPSEEK_ANTHROPIC_API_KEY",
    "volcengine": "ARK_API_KEY",
    "mimo": "MIMO_API_KEY",
    "mimo_tokenplan": "MIMO_TOKENPLAN_API_KEY",
    "bailian": "BAILIAN_API_KEY",
    "ollama_anthropic": "OLLAMA_ANTHROPIC_API_KEY",
    "litellm": "LITELLM_API_KEY",
    "custom_openai": "CUSTOM_OPENAI_API_KEY",  # legacy preference/env migration only
    "custom_anthropic": "CUSTOM_ANTHROPIC_API_KEY",
}

AZURE_ENV_FIELDS = (
    ("AZURE_OPENAI_ENDPOINT", "Azure Endpoint", "https://<resource>.openai.azure.com/"),
    ("AZURE_OPENAI_DEPLOYMENT_NAME", "Azure Deployment", "deployment-name"),
    ("OPENAI_API_VERSION", "Azure API Version", "2025-03-01-preview"),
)

BEDROCK_ENV_FIELDS = (
    ("AWS_BEARER_TOKEN_BEDROCK", "Bedrock Bearer Token", "Optional when using the AWS credential chain", True),
    ("AWS_DEFAULT_REGION", "AWS Region", "us-west-2", False),
    ("AWS_PROFILE", "AWS Profile", "Optional named profile", False),
)

PROVIDER_BASE_URL_ENV = {
    "openai_compatible": "OPENAI_COMPATIBLE_BASE_URL",
    "kimi_coding": "KIMI_BASE_URL",
    "moonshot": "MOONSHOT_BASE_URL",
    "deepseek_anthropic": "DEEPSEEK_ANTHROPIC_BASE_URL",
    "volcengine": "ARK_BASE_URL",
    "mimo": "MIMO_BASE_URL",
    "mimo_tokenplan": "MIMO_TOKENPLAN_BASE_URL",
    "bailian": "BAILIAN_BASE_URL",
    "ollama_anthropic": "OLLAMA_ANTHROPIC_BASE_URL",
    "litellm": "LITELLM_BASE_URL",
    "custom_openai": "CUSTOM_OPENAI_BASE_URL",
    "custom_anthropic": "CUSTOM_ANTHROPIC_BASE_URL",
}

PROVIDER_RUNTIME = {
    "kimi_coding": "anthropic",
    "moonshot": "anthropic",
    "deepseek_anthropic": "anthropic",
    "volcengine": "anthropic",
    "mimo": "anthropic",
    "mimo_tokenplan": "anthropic",
    "bailian": "anthropic",
    "ollama_anthropic": "anthropic",
    "litellm": "anthropic",
    "custom_openai": "openai_compatible",
    "custom_anthropic": "anthropic",
}

OPTIONAL_API_KEY_PROVIDERS = {"ollama", "openai_compatible", "custom_openai", "ollama_anthropic", "litellm"}

PROVIDER_MODEL_OPTIONS = {
    "kimi_coding": {
        "quick": [("Kimi K2.5", "sonnet"), ("Custom model ID", "custom")],
        "deep": [("Kimi K2.5", "sonnet"), ("Custom model ID", "custom")],
    },
    "moonshot": {
        "quick": [("Kimi K2.5", "sonnet"), ("Custom model ID", "custom")],
        "deep": [("Kimi K2.5", "sonnet"), ("Custom model ID", "custom")],
    },
    "deepseek_anthropic": {
        "quick": [("DeepSeek V4 Flash", "deepseek-v4-flash"), ("DeepSeek V4 Pro", "deepseek-v4-pro"), ("Custom model ID", "custom")],
        "deep": [("DeepSeek V4 Pro", "deepseek-v4-pro"), ("DeepSeek V4 Flash", "deepseek-v4-flash"), ("Custom model ID", "custom")],
    },
    "volcengine": {
        "quick": [("Custom endpoint model ID", "custom")],
        "deep": [("Custom endpoint model ID", "custom")],
    },
    "mimo": {
        "quick": [("MiMo-V2.5-Pro", "mimo-v2.5-pro"), ("Custom model ID", "custom")],
        "deep": [("MiMo-V2.5-Pro", "mimo-v2.5-pro"), ("Custom model ID", "custom")],
    },
    "mimo_tokenplan": {
        "quick": [("MiMo-V2.5-Pro", "mimo-v2.5-pro"), ("Custom model ID", "custom")],
        "deep": [("MiMo-V2.5-Pro", "mimo-v2.5-pro"), ("Custom model ID", "custom")],
    },
    "bailian": {
        "quick": [("Qwen 3.6 Plus", "qwen3.6-plus"), ("Qwen 3 Coder Next", "qwen3-coder-next"), ("Kimi K2.5", "kimi-k2.5"), ("MiniMax-M2.5", "MiniMax-M2.5"), ("Custom model ID", "custom")],
        "deep": [("Qwen 3.6 Plus", "qwen3.6-plus"), ("Qwen 3 Coder Plus", "qwen3-coder-plus"), ("GLM-5", "glm-5"), ("MiniMax-M2.5", "MiniMax-M2.5"), ("Custom model ID", "custom")],
    },
    "ollama_anthropic": {
        "quick": [("Custom local model ID", "custom")],
        "deep": [("Custom local model ID", "custom")],
    },
    "litellm": {
        "quick": [("Custom model ID", "custom")],
        "deep": [("Custom model ID", "custom")],
    },
    "custom_openai": {
        "quick": [("Custom model ID", "custom")],
        "deep": [("Custom model ID", "custom")],
    },
    "custom_anthropic": {
        "quick": [("Custom model ID", "custom")],
        "deep": [("Custom model ID", "custom")],
    },
}

ALL_TEAMS = {
    "Analyst Team": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
    "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
    "Trading Team": ["Trader"],
    "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
    "Portfolio Management": ["Portfolio Manager"],
}

ANALYST_KEY_MAP = {"market": "Market Analyst", "social": "Social Analyst", "news": "News Analyst", "fundamentals": "Fundamentals Analyst"}
ANALYST_REPORT_MAP = {"market": "market_report", "social": "sentiment_report", "news": "news_report", "fundamentals": "fundamentals_report"}
