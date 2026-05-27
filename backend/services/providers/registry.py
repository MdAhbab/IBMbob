"""Provider registration and discovery."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import LLMProvider, ProviderConfig
from .deepseek import DEEPSEEK_PROVIDER
from .gemini import GEMINI_PROVIDER
from .grok import GROK_PROVIDER


class ProviderRegistry:
    """Central registry for orchestrator LLM backends."""

    def __init__(self) -> None:
        self._providers: Dict[str, LLMProvider] = {}
        self.register(GROK_PROVIDER)
        self.register(DEEPSEEK_PROVIDER)
        self.register(GEMINI_PROVIDER)

    def register(self, provider: LLMProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> Optional[LLMProvider]:
        return self._providers.get(provider_id)

    def list_ids(self) -> List[str]:
        return list(self._providers.keys())

    def list_providers(self) -> List[LLMProvider]:
        return list(self._providers.values())

    def configured_providers(
        self, configs: List[ProviderConfig]
    ) -> List[tuple[LLMProvider, ProviderConfig]]:
        out: List[tuple[LLMProvider, ProviderConfig]] = []
        for cfg in sorted(configs, key=lambda c: c.priority):
            if not cfg.enabled:
                continue
            impl = self.get(cfg.provider_id)
            if impl and impl.is_configured(cfg):
                out.append((impl, cfg))
        return out


_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
