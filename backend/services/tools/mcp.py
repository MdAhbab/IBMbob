"""
Model Context Protocol (MCP) tool integration layer.

Provides a transport-agnostic interface for registering and invoking MCP-compatible
tools that agents and the orchestrator can call during task execution.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

ToolHandler = Callable[[Dict[str, Any]], Awaitable[Any]]


@dataclass
class MCPToolDescriptor:
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[ToolHandler] = None


@dataclass
class MCPToolResult:
    tool: str
    success: bool
    output: Any = None
    error: Optional[str] = None


class MCPToolRegistry:
    """Registry of MCP-style tools available to the orchestrator and agents."""

    def __init__(self) -> None:
        self._tools: Dict[str, MCPToolDescriptor] = {}

    def register(self, tool: MCPToolDescriptor) -> None:
        self._tools[tool.name] = tool
        logger.info("Registered MCP tool: %s", tool.name)

    def list_tools(self) -> List[MCPToolDescriptor]:
        return list(self._tools.values())

    def get(self, name: str) -> Optional[MCPToolDescriptor]:
        return self._tools.get(name)

    async def invoke(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        tool = self._tools.get(name)
        if not tool:
            return MCPToolResult(tool=name, success=False, error=f"Unknown tool: {name}")
        if not tool.handler:
            return MCPToolResult(
                tool=name, success=False, error="Tool has no handler registered"
            )
        try:
            output = await tool.handler(arguments)
            return MCPToolResult(tool=name, success=True, output=output)
        except Exception as e:
            logger.exception("MCP tool %s failed", name)
            return MCPToolResult(tool=name, success=False, error=str(e))


def _register_builtin_tools(registry: MCPToolRegistry) -> None:
    async def echo_handler(args: Dict[str, Any]) -> Any:
        return {"echo": args.get("message", "")}

    async def workspace_list_handler(args: Dict[str, Any]) -> Any:
        from pathlib import Path

        root_arg = args.get("path", ".")
        workspace_root = args.get("workspace_root")
        if workspace_root:
            base = Path(str(workspace_root)).resolve()
        else:
            base = Path(".").resolve()
        target = (base / str(root_arg)).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return {"files": [], "error": "path outside workspace root"}
        if not target.is_dir():
            return {"files": [], "error": "not a directory"}
        files = [p.name for p in target.iterdir() if p.is_file()][:100]
        return {"files": files, "path": str(target)}

    registry.register(
        MCPToolDescriptor(
            name="echo",
            description="Echo a message (connectivity test)",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
            handler=echo_handler,
        )
    )
    registry.register(
        MCPToolDescriptor(
            name="workspace.list_files",
            description="List files in a workspace directory",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
            handler=workspace_list_handler,
        )
    )


_registry: Optional[MCPToolRegistry] = None


def get_mcp_registry() -> MCPToolRegistry:
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
        _register_builtin_tools(_registry)
    return _registry
