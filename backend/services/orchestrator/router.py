"""Provider selection, prioritization, fallback, and retry."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..providers.base import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    ProviderConfig,
    ProviderHealth,
)
from ..providers.registry import ProviderRegistry, get_provider_registry

logger = logging.getLogger(__name__)

# Per-user round-robin cursor for ROUTING_STRATEGY=round_robin
_rr_index: Dict[int, int] = {}


@dataclass
class RoutingDecision:
    provider_id: str
    model: str
    reason: str
    attempts: int = 1
    fallbacks_used: List[str] = field(default_factory=list)
    routing_strategy: str = "auto"


class ProviderRouter:
    """
    Selects LLM providers by priority, runs health-aware fallback chains,
    and applies retry with exponential backoff.
    """

    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
    ) -> None:
        self.registry = registry or get_provider_registry()
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    async def health_check_all(
        self, configs: List[ProviderConfig]
    ) -> List[ProviderHealth]:
        tasks = []
        for cfg in configs:
            impl = self.registry.get(cfg.provider_id)
            if impl:
                tasks.append(impl.health_check(cfg))
        if not tasks:
            return []
        return await asyncio.gather(*tasks)

    def order_configs(
        self,
        configs: List[ProviderConfig],
        routing_strategy: str = "auto",
        user_id: int = 0,
        preferred_provider_id: Optional[str] = None,
    ) -> List[ProviderConfig]:
        """Order enabled configs per orchestrator routing strategy (CRIT-005)."""
        enabled = [
            c
            for c in configs
            if c.enabled and (c.api_key or (c.extra or {}).get("oauth"))
        ]
        if preferred_provider_id:
            preferred = [c for c in enabled if c.provider_id == preferred_provider_id]
            if preferred:
                rest = [c for c in enabled if c.provider_id != preferred_provider_id]
                enabled = preferred + rest

        strategy = (routing_strategy or "auto").lower().replace("-", "_")
        if strategy in ("least_cost", "least-cost"):
            return sorted(enabled, key=lambda c: (c.cost_per_1k_tokens, c.priority))
        if strategy in ("fastest", "fast"):
            latencies = {
                c.provider_id: float((c.extra or {}).get("latency_ms", c.priority * 100))
                for c in enabled
            }
            return sorted(enabled, key=lambda c: (latencies.get(c.provider_id, 9999), c.priority))
        if strategy in ("round_robin", "round-robin"):
            if not enabled:
                return []
            idx = _rr_index.get(user_id, 0) % len(enabled)
            _rr_index[user_id] = idx + 1
            return enabled[idx:] + enabled[:idx]
        return sorted(enabled, key=lambda c: c.priority)

    async def complete_with_fallback(
        self,
        configs: List[ProviderConfig],
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        routing_strategy: str = "auto",
        user_id: int = 0,
        preferred_provider_id: Optional[str] = None,
    ) -> Tuple[CompletionResult, RoutingDecision]:
        ordered = self.order_configs(
            configs,
            routing_strategy=routing_strategy,
            user_id=user_id,
            preferred_provider_id=preferred_provider_id,
        )
        fallbacks: List[str] = []
        last_error: Optional[Exception] = None

        for cfg in ordered:
            impl = self.registry.get(cfg.provider_id)
            if not impl or not impl.is_configured(cfg):
                continue

            for attempt in range(1, self.max_retries + 1):
                try:
                    result = await impl.complete(
                        cfg,
                        CompletionRequest(
                            messages=messages,
                            model=model or cfg.default_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        ),
                    )
                    return result, RoutingDecision(
                        provider_id=cfg.provider_id,
                        model=result.model,
                        reason=f"primary after {len(fallbacks)} fallback(s)"
                        if fallbacks
                        else "primary provider",
                        attempts=attempt,
                        fallbacks_used=fallbacks,
                        routing_strategy=routing_strategy,
                    )
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Provider %s attempt %s failed: %s",
                        cfg.provider_id,
                        attempt,
                        e,
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_base_delay * attempt)

            fallbacks.append(cfg.provider_id)

        raise RuntimeError(
            f"All configured LLM providers failed. Last error: {last_error}"
        )
