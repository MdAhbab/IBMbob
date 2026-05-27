"""xAI Grok provider (OpenAI-compatible API)."""

from .http_llm import OpenAICompatibleProvider

GROK_PROVIDER = OpenAICompatibleProvider(
    provider_id="grok",
    display_name="Grok",
    default_base_url="https://api.x.ai/v1",
    default_models=["grok-3", "grok-3-mini", "grok-2-1212"],
    default_cost_per_1k=0.005,
)
