"""Shared HTTP helpers for OpenAI-compatible LLM APIs."""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .base import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    ProviderConfig,
    ProviderHealth,
    ProviderHealthStatus,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """
    Base for providers exposing an OpenAI-style `/v1/chat/completions` API.
    Grok (xAI) and DeepSeek use this shape; Gemini has a separate adapter.
    """

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        default_base_url: str,
        default_models: List[str],
        default_cost_per_1k: float = 0.0,
    ) -> None:
        self.provider_id = provider_id
        self.display_name = display_name
        self.default_base_url = default_base_url.rstrip("/")
        self.default_models = default_models
        self.default_cost_per_1k = default_cost_per_1k

    def _base_url(self, config: ProviderConfig) -> str:
        return (config.base_url or self.default_base_url).rstrip("/")

    def _model(self, config: ProviderConfig, request: CompletionRequest) -> str:
        return request.model or config.default_model or self.default_models[0]

    def is_configured(self, config: ProviderConfig) -> bool:
        return bool(config.api_key and config.api_key.strip())

    def _headers(self, config: ProviderConfig) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, config: ProviderConfig, request: CompletionRequest) -> Dict[str, Any]:
        return {
            "model": self._model(config, request),
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }

    async def health_check(self, config: ProviderConfig) -> ProviderHealth:
        if not self.is_configured(config):
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderHealthStatus.UNCONFIGURED,
                message="API key not configured",
            )
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(
                    f"{self._base_url(config)}/models",
                    headers=self._headers(config),
                )
            latency = int((time.perf_counter() - started) * 1000)
            if resp.status_code in (200, 201):
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderHealthStatus.HEALTHY,
                    latency_ms=latency,
                )
            if resp.status_code in (401, 403):
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderHealthStatus.UNAVAILABLE,
                    latency_ms=latency,
                    message=f"Auth failed ({resp.status_code})",
                )
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderHealthStatus.DEGRADED,
                latency_ms=latency,
                message=f"HTTP {resp.status_code}",
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderHealthStatus.UNAVAILABLE,
                message=str(e),
            )

    async def complete(
        self, config: ProviderConfig, request: CompletionRequest
    ) -> CompletionResult:
        if not self.is_configured(config):
            raise RuntimeError(f"{self.display_name}: API key not configured")

        model = self._model(config, request)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url(config)}/chat/completions",
                headers=self._headers(config),
                json=self._payload(config, request),
            )
            resp.raise_for_status()
            data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        cost = self.estimate_cost(
            tokens,
            ProviderConfig(
                provider_id=config.provider_id,
                display_name=config.display_name,
                cost_per_1k_tokens=config.cost_per_1k_tokens or self.default_cost_per_1k,
            ),
        )
        return CompletionResult(
            content=content.strip(),
            model=model,
            provider_id=self.provider_id,
            tokens_used=tokens,
            cost_estimate=cost,
            finish_reason=choice.get("finish_reason"),
            raw=data,
        )

    async def stream(
        self, config: ProviderConfig, request: CompletionRequest
    ) -> AsyncIterator[str]:
        if not self.is_configured(config):
            raise RuntimeError(f"{self.display_name}: API key not configured")

        payload = self._payload(config, request)
        payload["stream"] = True
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url(config)}/chat/completions",
                headers=self._headers(config),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        import json

                        obj = json.loads(chunk)
                        delta = (
                            (obj.get("choices") or [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if delta:
                            yield delta
                    except Exception:
                        continue
