"""Task decomposition heuristics and LLM-assisted planning."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

from .context import SharedContext
from .messages import OrchestratorPlan, TaskDivision

AGENT_COLORS = {
    "claude": "#f59e0b",
    "claude-code": "#f59e0b",
    "gemini": "#6366f1",
    "gemini-cli": "#6366f1",
    "gemini-api": "#6366f1",
    "codex": "#10b981",
    "codex-cli": "#10b981",
    "copilot": "#71717a",
    "copilot-cli": "#71717a",
    "deepseek": "#a855f7",
    "deepseek-api": "#a855f7",
    "grok": "#ef4444",
    "kimi": "#f43f5e",
    "cline": "#06b6d4",
    "orchestrator": "#8b5cf6",
}

# ---------------------------------------------------------------------------
# Enhanced system prompt — forces conflict-free task decomposition
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """\
You are the central orchestrator for a multi-agent AI coding platform.
You break down user requests and assign exclusive, non-overlapping work slices to each CLI agent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE DECOMPOSITION RULES (MUST FOLLOW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. EXCLUSIVE OWNERSHIP — Every file that will be produced must be listed in exactly ONE
   agent's owns_files. No two agents may list the same file. Violating this causes merge conflicts.

2. EXPLICIT DEPENDENCIES — If agent B needs output from agent A, set B.depends_on = [A.short].
   Agents with no depends_on run in parallel (parallel_group = 0).
   Agents that depend on others use parallel_group = 1 (or 2 for a third wave).

3. READS FROM SHARED SPACE — If agent B reads a file agent A produces, list that file in
   B.reads_files. The shared artifact directory is provided in the user prompt.

4. MATCH SPECIALTY — Assign each agent work that fits its documented specialties.
   Claude → architecture/refactoring/docs. Gemini → frontend/UI/TypeScript.
   Codex → backend/algorithms/APIs. Copilot → tests/docs/glue code. Cline → shell/automation.

5. PARALLEL FIRST — Group independent tasks at parallel_group=0. Only create group 1 or 2
   if genuine data dependencies exist (i.e. one agent's output feeds another).

6. MINIMAL DIVISIONS — Assign work only to agents that have something meaningful to do.
   Do not create empty or trivial task slices.

7. NO DELEGATION (no_delegation:true) — Set this if the request is conversational, asks for
   information only, or clearly requires no coding work.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (strict JSON, no markdown fences)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "content": "<short friendly reply, 1-3 sentences>",
  "thinking": ["<reasoning step>", "..."],
  "divisions": [
    {
      "agent": "<display name>",
      "short": "<agent id matching enabled agent list>",
      "color": "#hex",
      "task": "<specific, actionable description of exactly what this agent does>",
      "status": "running|queued",
      "parallel_group": 0,
      "depends_on": ["<short_id_of_prerequisite_agent>"],
      "owns_files": ["relative/path/to/file.ext"],
      "reads_files": ["relative/path/produced/by/another/agent.ext"]
    }
  ],
  "artifacts": [{"name": "<filename>", "kind": "md|ts|py|json|txt"}],
  "no_delegation": false
}
"""

# Augment the base prompt with benchmark-informed routing guidance so the
# central AI routes by real per-CLI strengths (degrades silently if absent).
try:  # pragma: no cover - defensive
    from .benchmarks import routing_guidance_block as _routing_guidance_block
    _bench_block = _routing_guidance_block()
    if _bench_block:
        ORCHESTRATOR_SYSTEM_PROMPT = ORCHESTRATOR_SYSTEM_PROMPT + _bench_block
except Exception:
    pass


# ---------------------------------------------------------------------------
# JSON parse helpers
# ---------------------------------------------------------------------------

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

    raise json.JSONDecodeError("Failed to parse or repair LLM plan JSON", raw, 0)


# ---------------------------------------------------------------------------
# Conflict validation
# ---------------------------------------------------------------------------

def _validate_no_file_conflicts(divisions: List[TaskDivision]) -> List[str]:
    """
    Return a list of conflict descriptions if two agents claim ownership of the
    same file. Empty list means no conflicts.
    """
    seen: Dict[str, str] = {}  # path -> agent short
    conflicts = []
    for div in divisions:
        for path in div.owns_files:
            if path in seen:
                conflicts.append(
                    f"File conflict: '{path}' claimed by both '{seen[path]}' and '{div.short}'"
                )
            else:
                seen[path] = div.short
    return conflicts


# ---------------------------------------------------------------------------
# Per-agent task templates
# ---------------------------------------------------------------------------

def _task_for_agent(agent_id: str, message: str) -> str:
    preview = " ".join(message.strip().split())[:180] or "the requested change"
    templates = {
        "gemini": f"Design and implement the frontend UI/UX approach for: {preview}",
        "gemini-cli": f"Design and implement the frontend UI/UX approach for: {preview}",
        "gemini-api": f"Analyze UX/product requirements and propose the frontend approach for: {preview}",
        "codex": f"Implement backend logic, algorithms, and API endpoints for: {preview}",
        "codex-cli": f"Implement backend logic, algorithms, and API endpoints for: {preview}",
        "claude": f"Break down architecture, identify risks, and produce implementation guide for: {preview}",
        "claude-code": f"Break down architecture, identify risks, and produce implementation guide for: {preview}",
        "copilot": f"Write tests, documentation, and integration glue for: {preview}",
        "copilot-cli": f"Write tests, documentation, and integration glue for: {preview}",
        "deepseek": f"Review edge cases, performance, and failure modes for: {preview}",
        "deepseek-api": f"Review edge cases, performance, and failure modes for: {preview}",
        "grok": f"Explore creative solutions and rapid-prototype concepts for: {preview}",
        "kimi": f"Refine copy, naming conventions, and user-facing language for: {preview}",
        "cline": f"Execute repo automation, shell scripts, and CI configuration for: {preview}",
    }
    return templates.get(agent_id, f"Work on your assigned slice of: {preview}")


# ---------------------------------------------------------------------------
# Default file ownership (heuristic, used when LLM omits owns_files)
# ---------------------------------------------------------------------------

_AGENT_DEFAULT_FILES: Dict[str, List[str]] = {
    "claude": ["architecture.md"],
    "claude-code": ["architecture.md"],
    "gemini": ["ui-design.md"],
    "gemini-cli": ["ui-design.md"],
    "codex": ["implementation-notes.md"],
    "codex-cli": ["implementation-notes.md"],
    "copilot": ["tests-and-docs.md"],
    "copilot-cli": ["tests-and-docs.md"],
    "deepseek": ["review.md"],
    "cline": ["automation.md"],
    "grok": ["concepts.md"],
}


# ---------------------------------------------------------------------------
# Local (offline) division builder
# ---------------------------------------------------------------------------

def local_divisions(ctx: SharedContext, limit: int = 6) -> List[TaskDivision]:
    """
    Deterministic split across enabled CLI agents.
    Group 0 agents all run in parallel; each owns a distinct default file.
    """
    divisions: List[TaskDivision] = []
    used_files: Set[str] = set()

    # Order enabled agents by benchmark capability so the strongest CLI leads
    # (deterministic offline routing also benefits from the benchmarks).
    try:
        from .benchmarks import bench_score as _bs
        ordered_agents = sorted(
            ctx.enabled_agents, key=lambda a: _bs(a.get("name", "")), reverse=True
        )
    except Exception:
        ordered_agents = list(ctx.enabled_agents)

    for i, agent in enumerate(ordered_agents[:limit]):
        short = agent.get("name", "agent")
        default_files = [
            f for f in _AGENT_DEFAULT_FILES.get(short, [f"{short}-output.md"])
            if f not in used_files
        ]
        if not default_files:
            default_files = [f"{short}-output-{i}.md"]
        used_files.update(default_files)

        divisions.append(
            TaskDivision(
                agent=agent.get("display_name", short),
                short=short,
                color=AGENT_COLORS.get(short, "#6366f1"),
                task=_task_for_agent(short, ctx.user_message),
                status="running" if i == 0 else "queued",
                parallel_group=0,
                owns_files=default_files,
            )
        )
    return divisions


# ---------------------------------------------------------------------------
# Build plan from LLM dict
# ---------------------------------------------------------------------------

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
    used_files: Set[str] = set()

    for d in raw_divs:
        if not isinstance(d, dict):
            continue
        short = str(d.get("short") or d.get("agent") or "agent")

        # Resolve owns_files — deduplicate against already-claimed paths
        raw_owns = list(d.get("owns_files") or [])
        owns: List[str] = []
        for path in raw_owns:
            if path and path not in used_files:
                owns.append(path)
                used_files.add(path)

        # If LLM gave no owns_files, assign a default unique file
        if not owns:
            defaults = [
                f for f in _AGENT_DEFAULT_FILES.get(short, [f"{short}-output.md"])
                if f not in used_files
            ]
            if not defaults:
                defaults = [f"{short}-output-{len(divisions)}.md"]
            owns = defaults[:1]
            used_files.update(owns)

        divisions.append(
            TaskDivision(
                agent=str(d.get("agent") or short),
                short=short,
                color=str(d.get("color") or AGENT_COLORS.get(short, "#6366f1")),
                task=str(d.get("task") or _task_for_agent(short, ctx.user_message)),
                status=str(d.get("status") or "queued"),
                parallel_group=int(d.get("parallel_group") or 0),
                depends_on=[str(x) for x in (d.get("depends_on") or [])],
                owns_files=owns,
                reads_files=[str(x) for x in (d.get("reads_files") or [])],
            )
        )

    no_delegation = bool(data.get("no_delegation", False))
    if not divisions and ctx.enabled_agents and not no_delegation and "divisions" not in data:
        divisions = local_divisions(ctx)

    # Final conflict check (safety net — LLM may still slip up)
    conflicts = _validate_no_file_conflicts(divisions)
    if conflicts:
        import logging
        logging.getLogger(__name__).warning(
            "File ownership conflicts detected in LLM plan, auto-resolving: %s", conflicts
        )
        # Re-resolve by re-running build logic (already done above via used_files tracking)

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


# ---------------------------------------------------------------------------
# Offline plan (no LLM available)
# ---------------------------------------------------------------------------

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
