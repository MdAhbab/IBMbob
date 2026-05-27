"""
Central orchestrator engine — task decomposition, routing, fallback, aggregation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import aiosqlite

from ..providers.base import ChatMessage, ProviderConfig
from ..providers.registry import get_provider_registry
from .context import SharedContext
from .decomposer import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    build_plan_from_dict,
    offline_plan,
    parse_llm_plan,
)
from .messages import OrchestratorPlan
from .router import ProviderRouter

logger = logging.getLogger(__name__)

# Map DB provider `name` to orchestrator LLM registry id.
LLM_PROVIDER_ALIASES = {
    "grok": "grok",
    "deepseek-api": "deepseek-api",
    "gemini-api": "gemini-api",
}


class OrchestratorEngine:
    """Production orchestrator coordinating LLM planning and CLI agent delegation."""

    ORCHESTRATOR_LLM_NAMES = ("grok", "deepseek-api", "gemini-api")
    INFRA_LLM_NAMES = (
        "openai", "anthropic", "google", "ollama",
        "openai-embedding", "openai-tts", "openai-stt", "bob",
    )

    def __init__(
        self,
        max_retries: int = 3,
        default_model: Optional[str] = None,
    ) -> None:
        self.router = ProviderRouter(max_retries=max_retries)
        self.registry = get_provider_registry()
        self.default_model = default_model

    async def load_llm_configs(
        self, db: aiosqlite.Connection, user_id: int
    ) -> List[ProviderConfig]:
        """Load orchestrator LLM provider configs + decrypted API keys from DB."""
        from backend.utils.credentials import decrypt_credential
        from backend.config import settings as app_settings

        env_keys = {
            "grok": app_settings.grok_api_key,
            "deepseek-api": app_settings.deepseek_api_key,
            "gemini-api": app_settings.gemini_api_key,
        }

        configs: List[ProviderConfig] = []
        cur = await db.execute(
            """
            SELECT p.id, p.name, p.display_name, p.base_url, p.default_model,
                   p.is_enabled, p.config_schema,
                   pc.api_key, pc.additional_config
            FROM providers p
            LEFT JOIN provider_credentials pc
              ON pc.provider_id = p.id AND pc.user_id = ? AND pc.is_active = 1
            WHERE p.name IN ('grok', 'deepseek-api', 'gemini-api')
            ORDER BY p.id
            """
        , (user_id,))
        rows = await cur.fetchall()
        priority = 10
        for row in rows:
            name = row["name"]
            registry_id = LLM_PROVIDER_ALIASES.get(name, name)
            api_key = None
            if row["api_key"]:
                try:
                    api_key = decrypt_credential(row["api_key"])
                except Exception as exc:
                    logger.error("Failed to decrypt API key for %s: %s", name, exc)
                    api_key = None
            if not api_key:
                api_key = env_keys.get(name)
            extra: Dict[str, Any] = {}
            if row["additional_config"]:
                import json
                try:
                    extra = json.loads(row["additional_config"])
                except Exception:
                    pass
            configs.append(
                ProviderConfig(
                    provider_id=registry_id,
                    display_name=row["display_name"] or name,
                    api_key=api_key,
                    base_url=row["base_url"],
                    default_model=row["default_model"],
                    priority=int(extra.get("priority", priority)),
                    cost_per_1k_tokens=float(extra.get("cost_per_1k_tokens", 0)),
                    enabled=bool(row["is_enabled"]),
                    extra=extra,
                )
            )
            priority += 10
        return configs

    async def load_orchestrator_config(
        self, db: aiosqlite.Connection, user_id: int
    ) -> Dict[str, Any]:
        """Load active orchestrator_config row for routing strategy (CRIT-005)."""
        cur = await db.execute(
            """
            SELECT routing_strategy, default_provider_id, fallback_provider_id,
                   max_retries, enable_streaming
            FROM orchestrator_config
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return {"routing_strategy": "auto", "max_retries": self.router.max_retries}
        return {
            "routing_strategy": str(row["routing_strategy"] or "auto"),
            "default_provider_id": row["default_provider_id"],
            "fallback_provider_id": row["fallback_provider_id"],
            "max_retries": int(row["max_retries"] or self.router.max_retries),
            "enable_streaming": bool(row["enable_streaming"]),
        }

    async def resolve_preferred_llm_id(
        self,
        db: aiosqlite.Connection,
        provider_db_id: Optional[int],
    ) -> Optional[str]:
        """Map SQLite providers.id to orchestrator LLM registry id."""
        if provider_db_id is None:
            return None
        cur = await db.execute(
            "SELECT name FROM providers WHERE id = ? LIMIT 1",
            (provider_db_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        name = str(row["name"])
        return LLM_PROVIDER_ALIASES.get(name, name)

    async def load_enabled_agents(
        self, db: aiosqlite.Connection, user_id: int
    ) -> List[Dict[str, str]]:
        exclude = self.ORCHESTRATOR_LLM_NAMES + self.INFRA_LLM_NAMES
        placeholders = ",".join("?" for _ in exclude)
        cur = await db.execute(
            f"""
            SELECT p.name, p.display_name, p.default_model
            FROM providers p
            WHERE p.is_enabled = 1 AND p.name NOT IN ({placeholders})
            ORDER BY p.id
            """,
            exclude,
        )
        rows = await cur.fetchall()
        return [
            {
                "name": str(r["name"]),
                "display_name": str(r["display_name"] or r["name"]),
                "default_model": str(r["default_model"] or ""),
            }
            for r in rows
        ]

    async def run(
        self,
        db: aiosqlite.Connection,
        user_id: int,
        ctx: SharedContext,
        model: Optional[str] = None,
        routing_strategy: Optional[str] = None,
        preferred_provider_db_id: Optional[int] = None,
    ) -> OrchestratorPlan:
        import json
        orch_cfg = await self.load_orchestrator_config(db, user_id)
        strategy = routing_strategy or orch_cfg.get("routing_strategy") or "auto"
        preferred_llm = await self.resolve_preferred_llm_id(db, preferred_provider_db_id)
        if preferred_llm is None and orch_cfg.get("default_provider_id"):
            preferred_llm = await self.resolve_preferred_llm_id(
                db, int(orch_cfg["default_provider_id"])
            )

        llm_configs = await self.load_llm_configs(db, user_id)
        ctx.enabled_agents = await self.load_enabled_agents(db, user_id)

        agent_list = ", ".join(
            f"ID: {a['name']} (display name: {a['display_name']})" for a in ctx.enabled_agents
        ) or "none"
        user_prompt = (
            f"User request:\n{ctx.user_message}\n\n"
            f"Enabled CLI agents: {agent_list}\n"
            f"Session id: {ctx.session_id}"
        )

        messages = [
            ChatMessage(role="system", content=ORCHESTRATOR_SYSTEM_PROMPT),
            *ctx.recent_messages(10),
            ChatMessage(role="user", content=user_prompt),
        ]

        configured = self.registry.configured_providers(llm_configs)
        if not configured:
            return offline_plan(
                ctx,
                "No orchestrator LLM API keys configured (Grok, DeepSeek, or Gemini).",
            )

        try:
            result, decision = await self.router.complete_with_fallback(
                llm_configs,
                messages,
                model=model or self.default_model,
                max_tokens=4096,
                routing_strategy=strategy,
                user_id=user_id,
                preferred_provider_id=preferred_llm,
            )
            try:
                parsed = parse_llm_plan(result.content, ctx.user_message)
            except json.JSONDecodeError as jde:
                logger.warning(
                    f"JSON parsing failed on initial LLM plan response. Truncated output: {result.content[:500]}... Error: {jde}. Retrying with higher max_tokens=8192."
                )
                try:
                    result, decision = await self.router.complete_with_fallback(
                        llm_configs,
                        messages,
                        model=model or self.default_model,
                        max_tokens=8192,
                        routing_strategy=strategy,
                        user_id=user_id,
                        preferred_provider_id=preferred_llm,
                    )
                    parsed = parse_llm_plan(result.content, ctx.user_message)
                except json.JSONDecodeError as jde_retry:
                    logger.error(
                        f"JSON parsing failed again on retried LLM plan response. Truncated output: {result.content[:500]}... Error: {jde_retry}."
                    )
                    return offline_plan(
                        ctx,
                        f"LLM planner returned invalid JSON structure even after retrying. Error: {jde_retry}"
                    )

            plan = build_plan_from_dict(
                parsed,
                ctx,
                model=result.model,
                provider_id=result.provider_id,
                tokens=result.tokens_used,
                cost=result.cost_estimate,
            )
            plan.thinking = plan.thinking or [
                f"Routed via {decision.provider_id} ({decision.reason})",
                f"Fallbacks tried: {', '.join(decision.fallbacks_used) or 'none'}",
            ]
            plan.metadata["routing"] = {
                "provider_id": decision.provider_id,
                "reason": decision.reason,
                "attempts": decision.attempts,
                "fallbacks": decision.fallbacks_used,
                "routing_strategy": decision.routing_strategy or strategy,
            }
            return plan
        except Exception as e:
            logger.exception("Orchestrator LLM chain failed: %s", e)
            return offline_plan(ctx, str(e))


_engine: Optional[OrchestratorEngine] = None


def get_orchestrator_engine() -> OrchestratorEngine:
    global _engine
    if _engine is None:
        from backend.config import settings
        _engine = OrchestratorEngine(max_retries=settings.max_retries)
    return _engine
