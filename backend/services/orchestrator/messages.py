"""Structured message types for orchestration and A2A communication."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageKind(str, Enum):
    USER = "user"
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    A2A = "a2a"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class OrchestratorMessage:
    id: str
    kind: MessageKind
    content: str
    sender: str
    recipient: Optional[str] = None
    session_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)

    @classmethod
    def create(
        cls,
        kind: MessageKind,
        content: str,
        sender: str,
        **kwargs: Any,
    ) -> "OrchestratorMessage":
        return cls(
            id=str(uuid.uuid4()),
            kind=kind,
            content=content,
            sender=sender,
            **kwargs,
        )


@dataclass
class TaskDivision:
    """
    Work unit assigned to a CLI agent.

    Ownership and dependency fields prevent conflicts between agents:
      - owns_files:  relative paths (under artifact_base) this agent WRITES.
                     No two divisions in the same plan may share an owned path.
      - reads_files: relative paths this agent reads (produced by another agent).
      - depends_on:  short IDs of agents that must complete before this one starts.
      - parallel_group: 0 = runs immediately/in parallel with other group-0 tasks;
                        1+ = runs after the previous group finishes.
    """

    agent: str
    short: str
    task: str
    color: str = "#6366f1"
    status: str = "queued"
    provider_id: Optional[int] = None
    parallel_group: int = 0
    depends_on: List[str] = field(default_factory=list)
    owns_files: List[str] = field(default_factory=list)
    reads_files: List[str] = field(default_factory=list)


@dataclass
class OrchestratorPlan:
    """Structured orchestrator output consumed by the UI and agents."""

    content: str
    thinking: List[str] = field(default_factory=list)
    divisions: List[TaskDivision] = field(default_factory=list)
    artifacts: List[Dict[str, str]] = field(default_factory=list)
    model: str = "local-router"
    provider_id: Optional[str] = None
    tokens_used: int = 0
    cost_estimate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Resolved path of the shared artifact directory for this session.
    # Set by the orchestrator route when a workspace is active.
    artifact_base: str = ""

    def to_metadata_dict(self) -> Dict[str, Any]:
        return {
            "thinking": self.thinking,
            "divisions": [
                {
                    "agent": d.agent,
                    "short": d.short,
                    "color": d.color,
                    "task": d.task,
                    "status": d.status,
                    "parallel_group": d.parallel_group,
                    "depends_on": d.depends_on,
                    "owns_files": d.owns_files,
                    "reads_files": d.reads_files,
                }
                for d in self.divisions
            ],
            "artifacts": self.artifacts,
            "artifact_base": self.artifact_base,
            "model": self.model,
            "provider_id": self.provider_id,
            **self.metadata,
        }
