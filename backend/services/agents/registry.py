"""Agent registration and discovery for CLI agents and orchestrator workers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class AgentDescriptor:
    """Metadata for a registered agent (CLI or internal worker)."""

    agent_id: str
    name: str
    display_name: str
    agent_type: str  # cli | llm | tool
    provider_id: Optional[int] = None
    runtime_id: Optional[int] = None
    status: AgentStatus = AgentStatus.IDLE
    capabilities: List[str] = field(default_factory=list)
    ws_url: Optional[str] = None
    registered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_provider_row(
        cls,
        name: str,
        display_name: str,
        provider_id: int,
        runtime_id: Optional[int] = None,
        ws_url: Optional[str] = None,
    ) -> "AgentDescriptor":
        return cls(
            agent_id=name,
            name=name,
            display_name=display_name,
            agent_type="cli",
            provider_id=provider_id,
            runtime_id=runtime_id,
            ws_url=ws_url,
            capabilities=["code", "terminal", "file_edit"],
        )


class AgentRegistry:
    """In-memory agent registry (backed by DB providers + live PTY sessions)."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentDescriptor] = {}

    def register(self, agent: AgentDescriptor) -> None:
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> Optional[AgentDescriptor]:
        return self._agents.get(agent_id)

    def list_agents(self, status: Optional[AgentStatus] = None) -> List[AgentDescriptor]:
        agents = list(self._agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        return agents

    def update_status(self, agent_id: str, status: AgentStatus) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].status = status


_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
