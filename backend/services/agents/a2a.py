"""Agent-to-Agent (A2A) structured messaging."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional
import uuid

from ..orchestrator.messages import MessageKind, OrchestratorMessage


@dataclass
class A2AEnvelope:
    """Message envelope for inter-agent communication."""

    id: str
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "request"  # request | response | broadcast | handoff
    session_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def create(
        cls,
        from_agent: str,
        to_agent: str,
        content: str,
        **kwargs: Any,
    ) -> "A2AEnvelope":
        return cls(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            **kwargs,
        )


class A2ABus:
    """
    In-process message bus for agent-to-agent communication.

    Production deployments can swap this for Redis/NATS while keeping the same API.
    """

    def __init__(self, max_queue: int = 500) -> None:
        self._queues: Dict[str, Deque[A2AEnvelope]] = defaultdict(
            lambda: deque(maxlen=max_queue)
        )
        self._history: Deque[A2AEnvelope] = deque(maxlen=2000)
        self._lock = asyncio.Lock()

    async def send(self, envelope: A2AEnvelope) -> A2AEnvelope:
        async with self._lock:
            if envelope.to_agent == "*":
                for q in self._queues.values():
                    q.append(envelope)
            else:
                self._queues[envelope.to_agent].append(envelope)
            self._history.append(envelope)
        return envelope

    async def receive(
        self, agent_id: str, limit: int = 20
    ) -> List[A2AEnvelope]:
        async with self._lock:
            q = self._queues[agent_id]
            out: List[A2AEnvelope] = []
            while q and len(out) < limit:
                out.append(q.popleft())
            return out

    async def history(
        self, session_id: Optional[int] = None, limit: int = 50
    ) -> List[A2AEnvelope]:
        async with self._lock:
            items = list(self._history)
        if session_id is not None:
            items = [m for m in items if m.session_id == session_id]
        return items[-limit:]

    def to_orchestrator_message(self, env: A2AEnvelope) -> OrchestratorMessage:
        return OrchestratorMessage.create(
            kind=MessageKind.A2A,
            content=env.content,
            sender=env.from_agent,
            recipient=env.to_agent,
            session_id=env.session_id,
            metadata={"message_type": env.message_type, **env.metadata},
        )


_bus: Optional[A2ABus] = None


def get_a2a_bus() -> A2ABus:
    global _bus
    if _bus is None:
        _bus = A2ABus()
    return _bus
