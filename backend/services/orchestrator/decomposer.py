"""Task decomposition heuristics and LLM-assisted planning."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .context import SharedContext
from .messages import OrchestratorPlan, TaskDivision

AGENT_COLORS = {
    "claude": "#f59e0b",
    "gemini": "#6366f1",
    "gemini-api": "#6366f1",
    "codex": "#10b981",
    "copilot": "#71717a",
    "deepseek": "#a855f7",
    "deepseek-api": "#a855f7",
    "grok": "#ef4444",
    "kimi": "#f43f5e",
    "cline": "#06b6d4",
    "orchestrator": "#8b5cf6",
}

ORCHESTRATOR_SYSTEM_PROMPT = """You are the central orchestrator for a multi-agent AI development platform.
You coordinate CLI coding agents that the user has enabled.

Respond with a SINGLE JSON object — no markdown fences — matching:
{
  "content": "<short friendly reply, 1-3 sentences>",
  "thinking": ["<step>", "..."],
  "divisions": [
    {"agent": "<display name>", "short": "<agent id>", "color": "#hex", "task": "<one line>", "status": "running|queued|done"}
  ],
  "artifacts": [{"name": "<file>", "kind": "md|ts|py|json|txt"}],
  "no_delegation": true|false
}

Rules:
- Use divisions only when work should be split across agents; otherwise [].
- Use artifacts only when files would be produced; otherwise [].
- Delegate using the exact agent ID (the short identifier like 'gemini-api' or 'claude') as the "short" value in the divisions list, not their display name.
- Set no_delegation to true if no agents are needed (e.g. for general/conversational queries), and false if agents are dispatched.
- Prefer parallel independent tasks when possible.
"""


def _strip_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[: -len("```")]
    return s.strip()


def try_repair_json(s: str) -> str:
    """Balance unclosed brackets, braces, and quotes in truncated JSON."""
    s = s.strip()
    if not s:
        return s
    if s.endswith(","):
        s = s[:-1].strip()
    
    stack = []
    in_string = False
    escape = False
    
    for char in s:
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in ('{', '['):
                stack.append(char)
            elif char in ('}', ']'):
                if stack:
                    top = stack[-1]
                    if (char == '}' and top == '{') or (char == ']' and top == '['):
                        stack.pop()
    
    if in_string:
        s += '"'
    
    while stack:
        top = stack.pop()
        s = s.strip()
        if s.endswith(","):
            s = s[:-1].strip()
        if top == '{':
            s += '}'
        elif top == '[':
            s += ']'
    return s


def parse_llm_plan(raw: str, fallback: str) -> Dict[str, Any]:
    cleaned = _strip_fences(raw)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    
    # Try normal parse first
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(cleaned[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # Partial-parse recovery attempt
    if start != -1:
        repaired = try_repair_json(cleaned[start:])
        try:
            obj = json.loads(repaired)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # If it completely fails, raise JSONDecodeError
    raise json.JSONDecodeError("Failed to parse or repair LLM plan JSON", raw, 0)


def _task_for_agent(agent_id: str, message: str) -> str:
    preview = " ".join(message.strip().split())[:180] or "the requested change"
    templates = {
        "gemini": f"Analyze UX/product requirements and propose the frontend approach for: {preview}",
        "gemini-api": f"Analyze UX/product requirements and propose the frontend approach for: {preview}",
        "codex": f"Implement code changes and run focused verification for: {preview}",
        "claude": f"Break down architecture, risks, and implementation order for: {preview}",
        "copilot": f"Handle implementation glue, tests, and docs for: {preview}",
        "deepseek": f"Check edge cases, performance, and failure modes for: {preview}",
        "deepseek-api": f"Check edge cases, performance, and failure modes for: {preview}",
        "grok": f"Explore creative solutions and rapid prototyping for: {preview}",
        "kimi": f"Refine copy, naming, and user-facing details for: {preview}",
        "cline": f"Execute repo automation and validation commands for: {preview}",
    }
    return templates.get(agent_id, f"Work on your assigned slice of: {preview}")


def local_divisions(ctx: SharedContext, limit: int = 6) -> List[TaskDivision]:
    """Deterministic split across enabled CLI agents. All divisions are dispatched simultaneously."""
    divisions: List[TaskDivision] = []
    for i, agent in enumerate(ctx.enabled_agents[:limit]):
        short = agent.get("name", "agent")
        divisions.append(
            TaskDivision(
                agent=agent.get("display_name", short),
                short=short,
                color=AGENT_COLORS.get(short, "#6366f1"),
                task=_task_for_agent(short, ctx.user_message),
                status="running" if i == 0 else "queued",
            )
        )
    return divisions


def build_plan_from_dict(
    data: Dict[str, Any],
    ctx: SharedContext,
    model: str,
    provider_id: Optional[str] = None,
    tokens: int = 0,
    cost: float = 0.0,
) -> OrchestratorPlan:
    raw_divs = data.get("divisions") or []
    divisions: List[TaskDivision] = []
    for d in raw_divs:
        if not isinstance(d, dict):
            continue
        short = str(d.get("short") or d.get("agent") or "agent")
        divisions.append(
            TaskDivision(
                agent=str(d.get("agent") or short),
                short=short,
                color=str(d.get("color") or AGENT_COLORS.get(short, "#6366f1")),
                task=str(d.get("task") or _task_for_agent(short, ctx.user_message)),
                status=str(d.get("status") or "queued"),
            )
        )
    no_delegation = bool(data.get("no_delegation", False))
    if not divisions and ctx.enabled_agents and not no_delegation and "divisions" not in data:
        divisions = local_divisions(ctx)

    content = str(data.get("content") or "").strip()
    if not content:
        content = (
            f"I split this into {len(divisions)} agent assignment(s)."
            if divisions
            else "No enabled agents are available. Configure providers in Settings."
        )

    return OrchestratorPlan(
        content=content,
        thinking=[str(x) for x in (data.get("thinking") or [])][:8],
        divisions=divisions,
        artifacts=list(data.get("artifacts") or []),
        model=model,
        provider_id=provider_id,
        tokens_used=tokens,
        cost_estimate=cost,
    )


def offline_plan(ctx: SharedContext, reason: str) -> OrchestratorPlan:
    divisions = local_divisions(ctx)
    return OrchestratorPlan(
        content=(
            f"I routed this locally across {len(divisions)} enabled agent(s). "
            f"({reason})"
            if divisions
            else "No LLM providers configured and no CLI agents enabled."
        ),
        thinking=[
            "Parsed request locally.",
            f"Enabled agents: {', '.join(ctx.agent_names()) or 'none'}",
            reason,
        ],
        divisions=divisions,
        artifacts=[{"name": "divisions.md", "kind": "md"}] if divisions else [],
        model="local-router",
    )
