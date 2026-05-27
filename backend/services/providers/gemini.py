"""Google Gemini provider (Generative Language API)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List

import httpx

from .base import (
    CompletionRequest,
    CompletionResult,
    LLMProvider,
    ProviderConfig,
    ProviderHealth,
    ProviderHealthStatus,
)

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    provider_id = "gemini-api"
    display_name = "Gemini"
    default_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]

    def is_configured(self, config: ProviderConfig) -> bool:
        return bool(config.api_key and config.api_key.strip())

    def _model(self, config: ProviderConfig, request: CompletionRequest) -> str:
        return request.model or config.default_model or self.default_models[0]

    def _contents(self, request: CompletionRequest) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for m in request.messages:
            if m.role == "system":
                out.append({"role": "user", "parts": [{"text": f"[System]\n{m.content}"}]})
                out.append({"role": "model", "parts": [{"text": "Understood."}]})
            else:
                role = "model" if m.role == "assistant" else "user"
                out.append({"role": role, "parts": [{"text": m.content}]})
        return out

    def _generation_config(self, request: CompletionRequest) -> Dict[str, Any]:
        return {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        }

    async def health_check(self, config: ProviderConfig) -> ProviderHealth:
        if not self.is_configured(config):
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderHealthStatus.UNCONFIGURED,
                message="API key not configured",
            )
        started = time.perf_counter()
        url = f"{GEMINI_BASE}/models"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params={"key": config.api_key})
            latency = int((time.perf_counter() - started) * 1000)
            if resp.status_code == 200:
                return ProviderHealth(
                    provider_id=self.provider_id,
                    status=ProviderHealthStatus.HEALTHY,
                    latency_ms=latency,
                )
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderHealthStatus.UNAVAILABLE,
                latency_ms=latency,
                message=f"HTTP {resp.status_code}: {resp.text[:200]}",
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
            raise RuntimeError("Gemini: API key not configured")

        model = self._model(config, request)
        url = f"{GEMINI_BASE}/models/{model}:generateContent"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url,
                params={"key": config.api_key},
                json={
                    "contents": self._contents(request),
                    "generationConfig": self._generation_config(request),
                },
            )
            resp.raise_for_status()
            data = resp.json()

        parts = (
            (data.get("candidates") or [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        usage = data.get("usageMetadata") or {}
        tokens = int(usage.get("totalTokenCount") or 0)
        return CompletionResult(
            content=text.strip(),
            model=model,
            provider_id=self.provider_id,
            tokens_used=tokens,
            cost_estimate=config.cost_per_1k_tokens * (tokens / 1000.0),
            raw=data,
        )

    async def stream(
        self, config: ProviderConfig, request: CompletionRequest
    ) -> AsyncIterator[str]:
        """True streaming via Gemini streamGenerateContent SSE (MED-007)."""
        if not self.is_configured(config):
            raise RuntimeError("Gemini: API key not configured")

        model = self._model(config, request)
        url = f"{GEMINI_BASE}/models/{model}:streamGenerateContent"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": config.api_key, "alt": "sse"},
                json={
                    "contents": self._contents(request),
                    "generationConfig": self._generation_config(request),
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    parts = (
                        (chunk.get("candidates") or [{}])[0]
                        .get("content", {})
                        .get("parts", [])
                    )
                    for part in parts:
                        text = part.get("text") if isinstance(part, dict) else None
                        if text:
                            yield text


GEMINI_PROVIDER = GeminiProvider()
