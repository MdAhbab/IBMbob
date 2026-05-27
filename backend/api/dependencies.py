"""
Common dependencies for API routes.
Provides database session management and other shared dependencies.
"""

from typing import AsyncGenerator, Optional
import aiosqlite
from fastapi import Depends, HTTPException, Query, status
from pathlib import Path

from backend.config import settings


# Database connection pool (simple implementation for SQLite)
_db_connection: Optional[aiosqlite.Connection] = None


async def get_db_connection() -> aiosqlite.Connection:
    """Get or create database connection."""
    global _db_connection

    if _db_connection is None:
        db_path = settings.database_path.resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db_connection = await aiosqlite.connect(
            str(db_path),
            check_same_thread=False,
        )
        await _db_connection.execute("PRAGMA foreign_keys = ON")
        await _db_connection.execute("PRAGMA journal_mode = WAL")
        _db_connection.row_factory = aiosqlite.Row

    return _db_connection


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Dependency for getting database connection.
    Provides a database connection for the request lifecycle.
    """
    conn = await get_db_connection()
    try:
        yield conn
    finally:
        pass


async def close_db_connection():
    """Close the database connection. Called on application shutdown."""
    global _db_connection
    if _db_connection is not None:
        await _db_connection.close()
        _db_connection = None


class CommonQueryParams:
    """Common query parameters for list endpoints."""

    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ):
        self.skip = max(0, skip)
        self.limit = min(limit, 1000)
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "desc"


async def get_current_user_id() -> int:
    """
    Return the authenticated user id.

    Single-user mode: always user 1 until JWT/session auth is implemented.
    The spoofable user_id query parameter has been removed (CRIT-001).
    """
    if not settings.single_user_mode:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Multi-user mode is not implemented. Set SINGLE_USER_MODE=True in backend/config.py or environment variables."
        )
    return 1


async def verify_session_owned_by_user(
    session_id: int,
    user_id: int,
    db: aiosqlite.Connection,
) -> int:
    """Verify session exists and belongs to the current user."""
    cursor = await db.execute(
        "SELECT id FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Session {session_id} not found or access denied",
        )
    return session_id


async def verify_session_exists(
    session_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> int:
    """Verify that a session exists and belongs to the current user."""
    return await verify_session_owned_by_user(session_id, user_id, db)


async def verify_provider_exists(
    provider_id: int,
    db: aiosqlite.Connection = Depends(get_db),
) -> int:
    """Verify that a provider exists and return its ID."""
    cursor = await db.execute(
        "SELECT id FROM providers WHERE id = ?",
        (provider_id,),
    )
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider with id {provider_id} not found",
        )

    return provider_id


async def verify_runtime_owned_by_user(
    runtime_id: int,
    user_id: int,
    db: aiosqlite.Connection,
) -> int:
    """Verify runtime exists and is owned by the user (via session or single-user PTY)."""
    cursor = await db.execute(
        """
        SELECT cr.id
        FROM cli_runtimes cr
        LEFT JOIN sessions s ON s.id = cr.session_id
        WHERE cr.id = ?
          AND (
            (cr.session_id IS NOT NULL AND s.user_id = ?)
            OR (cr.session_id IS NULL AND ? = 1)
          )
        LIMIT 1
        """,
        (runtime_id, user_id, user_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Runtime {runtime_id} not found or access denied",
        )
    return runtime_id


async def verify_runtime_exists(
    runtime_id: int,
    db: aiosqlite.Connection = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> int:
    """Verify that a CLI runtime exists and belongs to the current user."""
    return await verify_runtime_owned_by_user(runtime_id, user_id, db)


async def verify_ws_access(
    runtime_id: int,
    token: Optional[str] = Query(default=None),
    db: aiosqlite.Connection = Depends(get_db),
) -> int:
    """
    WebSocket access check. Single-user mode accepts default user;
    optional token must match SECRET_KEY prefix when provided.
    """
    user_id = await get_current_user_id()
    if token:
        expected = (settings.secret_key or "")[:32]
        if not expected or token != expected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid WebSocket token",
            )
    return await verify_runtime_owned_by_user(runtime_id, user_id, db)


def validate_file_type(filename: str) -> bool:
    """Validate if file type is allowed."""
    file_ext = Path(filename).suffix.lower()
    return file_ext in settings.allowed_file_types


def validate_file_size(file_size: int) -> bool:
    """Validate if file size is within limits."""
    return file_size <= settings.max_upload_size


async def fetch_active_workspace_path(
    db: aiosqlite.Connection, user_id: int
) -> Optional[str]:
    """Return filesystem path of the user's active workspace, if any."""
    cur = await db.execute(
        "SELECT path FROM workspaces WHERE user_id = ? AND is_active = 1 "
        "ORDER BY updated_at DESC LIMIT 1",
        (user_id,),
    )
    row = await cur.fetchone()
    if row and row["path"]:
        return str(row["path"])
    return None
