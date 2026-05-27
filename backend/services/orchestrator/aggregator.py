"""Response aggregation from multiple agent outputs."""

from __future__ import annotations

from typing import Any, Dict, List

from .messages import OrchestratorPlan, TaskDivision


def merge_divisions(
    primary: List[TaskDivision],
    supplemental: List[TaskDivision],
) -> List[TaskDivision]:
    """Merge divisions without duplicating agent short ids."""
    seen = {d.short for d in primary}
    merged = list(primary)
    for d in supplemental:
        if d.short not in seen:
            merged.append(d)
            seen.add(d.short)
    return merged


def aggregate_agent_results(
    plan: OrchestratorPlan,
    agent_outputs: Dict[str, str],
) -> OrchestratorPlan:
    """Combine per-agent stdout/summary into orchestrator metadata."""
    if not agent_outputs:
        return plan
    summaries: List[str] = []
    for short, output in agent_outputs.items():
        preview = output.strip()[:400]
        if preview:
            summaries.append(f"**{short}**: {preview}")
    if summaries:
        plan.metadata["agent_outputs"] = agent_outputs
        plan.thinking = plan.thinking + [f"Collected output from {len(agent_outputs)} agent(s)"]
    return plan
