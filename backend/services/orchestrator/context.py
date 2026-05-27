"""Unified session context shared across agents and the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..providers.base import ChatMessage


@dataclass
class SharedContext:
    """In-memory + persistable context for a session."""

    session_id: int
    workspace_path: Optional[str] = None
    user_message: str = ""
    enabled_agents: List[Dict[str, str]] = field(default_factory=list)
    history: List[ChatMessage] = field(default_factory=list)
    task_state: Dict[str, Any] = field(default_factory=dict)
    shared_files: List[str] = field(default_factory=list)

    def append_history(self, role: str, content: str) -> None:
        self.history.append(ChatMessage(role=role, content=content))

    def recent_messages(self, limit: int = 12) -> List[ChatMessage]:
        return self.history[-limit:]

    def agent_names(self) -> List[str]:
        return [a.get("name", "") for a in self.enabled_agents if a.get("name")]
