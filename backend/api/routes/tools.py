"""MCP tool integration API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.tools.mcp import get_mcp_registry

router = APIRouter(prefix="/tools", tags=["tools"])


class MCPToolInvokeRequest(BaseModel):
    arguments: Dict[str, Any] = Field(default_factory=dict)


@router.get("/mcp")
async def list_mcp_tools() -> List[Dict[str, Any]]:
    registry = get_mcp_registry()
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in registry.list_tools()
    ]


@router.post("/mcp/{tool_name}/invoke")
async def invoke_mcp_tool(tool_name: str, body: MCPToolInvokeRequest) -> Dict[str, Any]:
    registry = get_mcp_registry()
    result = await registry.invoke(tool_name, body.arguments)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "tool failed")
    return {"tool": result.tool, "output": result.output}
