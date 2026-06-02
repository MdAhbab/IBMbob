"""
Installer API routes — REST + Server-Sent Events for CLI installation.

Mount at /api/installer via the main app router.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.api.dependencies import get_current_user_id
from backend.services.cli_installer import (
    CLIInstallEvent,
    InstallStatus,
    detect_node,
    get_cli_installer_service,
)

router = APIRouter(prefix="/installer", tags=["installer"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class NodeStatusResponse(BaseModel):
    installed: bool
    version: Optional[str] = None
    npm_version: Optional[str] = None
    meets_requirement: bool
    min_required: int
    error: Optional[str] = None


class CLIStatusResponse(BaseModel):
    slug: str
    name: str
    installed: bool
    version: Optional[str] = None
    bin_path: Optional[str] = None
    node_required: bool
    api_only: bool
    description: str
    specialties: List[str]
    npm_package: Optional[str] = None
    fallback_doc_url: str = ""


class InstallerStatusResponse(BaseModel):
    node: NodeStatusResponse
    install_prefix: str
    clis: List[CLIStatusResponse]


class InstallAllRequest(BaseModel):
    slugs: Optional[List[str]] = None  # None = install all; list = install subset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_to_sse(event: CLIInstallEvent) -> str:
    """Format a CLIInstallEvent as a Server-Sent Event string."""
    data = json.dumps({
        "slug": event.slug,
        "status": event.status.value,
        "message": event.message,
        "progress_pct": event.progress_pct,
        "detail": event.detail,
    })
    return f"data: {data}\n\n"


def _done_event(slug: str) -> str:
    data = json.dumps({"slug": slug, "status": "stream_end"})
    return f"data: {data}\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=InstallerStatusResponse)
async def get_installer_status(
    _user_id: int = Depends(get_current_user_id),
) -> InstallerStatusResponse:
    """Return Node.js status and install status for all registered CLIs."""
    svc = get_cli_installer_service()
    raw = svc.status_all()
    n = raw["node"]
    return InstallerStatusResponse(
        node=NodeStatusResponse(**n),
        install_prefix=raw["install_prefix"],
        clis=[CLIStatusResponse(**c) for c in raw["clis"]],
    )


@router.post("/install/node")
async def install_node(
    _user_id: int = Depends(get_current_user_id),
):
    """
    Install or upgrade Node.js.
    Returns a Server-Sent Events stream of CLIInstallEvent objects.
    """
    svc = get_cli_installer_service()

    async def _stream():
        try:
            async for event in svc.install_node_stream():
                yield _event_to_sse(event)
        except Exception as exc:
            err = CLIInstallEvent("node", InstallStatus.ERROR, str(exc), 100)
            yield _event_to_sse(err)
        finally:
            yield _done_event("node")

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/install/{slug}")
async def install_single_cli(
    slug: str,
    _user_id: int = Depends(get_current_user_id),
):
    """
    Install a single CLI by slug (e.g. "claude-code", "gemini-cli").
    Returns a Server-Sent Events stream of CLIInstallEvent objects.
    """
    svc = get_cli_installer_service()

    async def _stream():
        try:
            async for event in svc.install_cli_stream(slug):
                yield _event_to_sse(event)
        except Exception as exc:
            err = CLIInstallEvent(slug, InstallStatus.ERROR, str(exc), 100)
            yield _event_to_sse(err)
        finally:
            yield _done_event(slug)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/install")
async def install_all_clis(
    body: InstallAllRequest,
    _user_id: int = Depends(get_current_user_id),
):
    """
    Install all CLIs (or a subset by slug list).
    Returns a Server-Sent Events stream of CLIInstallEvent objects.
    """
    svc = get_cli_installer_service()

    async def _stream():
        try:
            async for event in svc.install_all_stream(slugs=body.slugs):
                yield _event_to_sse(event)
        except Exception as exc:
            err = CLIInstallEvent("all", InstallStatus.ERROR, str(exc), 100)
            yield _event_to_sse(err)
        finally:
            yield _done_event("all")

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/verify/{slug}")
async def verify_cli(
    slug: str,
    _user_id: int = Depends(get_current_user_id),
) -> CLIStatusResponse:
    """Re-verify whether a specific CLI is installed and working."""
    svc = get_cli_installer_service()
    entry_list = [e for e in svc.get_registry() if e.get("slug") == slug]
    if not entry_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown CLI slug: {slug}",
        )
    entry = entry_list[0]
    result = svc.verify(slug)
    return CLIStatusResponse(
        slug=slug,
        name=entry.get("name", slug),
        installed=result.installed,
        version=result.version,
        bin_path=result.bin_path,
        node_required=entry.get("node_required", True),
        api_only=not entry.get("node_required", True),
        description=entry.get("description", ""),
        specialties=entry.get("specialties", []),
        npm_package=entry.get("npm_package") or entry.get("package"),
        fallback_doc_url=entry.get("fallback_doc_url", ""),
    )
