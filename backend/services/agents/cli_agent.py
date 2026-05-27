"""CLI agent adapter — bridges PTY runtimes to the agent registry."""

from __future__ import annotations

from typing import Optional

from .a2a import A2AEnvelope, get_a2a_bus
from .registry import AgentDescriptor, AgentStatus, get_agent_registry


class CLIAgentAdapter:
    """Send tasks to a live CLI runtime and relay A2A messages."""

    def __init__(self, descriptor: AgentDescriptor) -> None:
        self.descriptor = descriptor
        self.bus = get_a2a_bus()
        self.registry = get_agent_registry()

    async def assign_task(self, task: str, session_id: Optional[int] = None) -> A2AEnvelope:
        self.registry.update_status(self.descriptor.agent_id, AgentStatus.BUSY)
        envelope = A2AEnvelope.create(
            from_agent="orchestrator",
            to_agent=self.descriptor.agent_id,
            content=task,
            message_type="request",
            session_id=session_id,
            metadata={"runtime_id": self.descriptor.runtime_id},
        )
        await self.bus.send(envelope)
        return envelope

    async def handoff(
        self,
        to_agent: str,
        summary: str,
        session_id: Optional[int] = None,
    ) -> A2AEnvelope:
        envelope = A2AEnvelope.create(
            from_agent=self.descriptor.agent_id,
            to_agent=to_agent,
            content=summary,
            message_type="handoff",
            session_id=session_id,
        )
        await self.bus.send(envelope)
        return envelope
