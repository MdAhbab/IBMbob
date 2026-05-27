"""DeepSeek provider (OpenAI-compatible API)."""

from .http_llm import OpenAICompatibleProvider

DEEPSEEK_PROVIDER = OpenAICompatibleProvider(
    provider_id="deepseek-api",
    display_name="DeepSeek",
    default_base_url="https://api.deepseek.com/v1",
    default_models=["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
    default_cost_per_1k=0.0014,
)
