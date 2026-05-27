"""
Abstract LLM provider interface for the orchestration platform.

All cloud LLM integrations (Grok, DeepSeek, Gemini, future providers) implement
`LLMProvider` and register via `ProviderRegistry`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional


class ProviderHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNCONFIGURED = "unconfigured"


@dataclass
class ProviderHealth:
    provider_id: str
    status: ProviderHealthStatus
    latency_ms: Optional[int] = None
    message: Optional[str] = None
    checked_at: Optional[str] = None


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class CompletionRequest:
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 4096
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResult:
    content: str
    model: str
    provider_id: str
    tokens_used: int = 0
    cost_estimate: float = 0.0
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class ProviderConfig:
    """Runtime credentials + options loaded from DB or env."""

    provider_id: str
    display_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    priority: int = 100
    cost_per_1k_tokens: float = 0.0
    enabled: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Contract every orchestrator LLM backend must implement."""

    provider_id: str
    display_name: str
    default_models: List[str]

    @abstractmethod
    def is_configured(self, config: ProviderConfig) -> bool:
        """Return True when credentials are sufficient for API calls."""

    @abstractmethod
    async def health_check(self, config: ProviderConfig) -> ProviderHealth:
        """Lightweight connectivity / auth probe."""

    @abstractmethod
    async def complete(
        self, config: ProviderConfig, request: CompletionRequest
    ) -> CompletionResult:
        """Non-streaming chat completion."""

    async def stream(
        self, config: ProviderConfig, request: CompletionRequest
    ) -> AsyncIterator[str]:
        """Streaming tokens. Default: single-chunk fallback from complete()."""
        result = await self.complete(config, request)
        yield result.content

    def estimate_cost(self, tokens: int, config: ProviderConfig) -> float:
        if config.cost_per_1k_tokens <= 0:
            return 0.0
        return (tokens / 1000.0) * config.cost_per_1k_tokens
