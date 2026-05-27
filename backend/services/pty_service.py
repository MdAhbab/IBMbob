"""
Real Windows PTY service for the Parallel Terminals page.

Each agent card in the UI is backed by a `PtySession` that wraps a real
PowerShell process via pywinpty. Output is broadcast to all attached WS
subscribers, and a rolling ring buffer is kept so newly attached clients
get the recent history.
"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# pywinpty is Windows-only.
try:
    from winpty import PTY as WinPTY  # type: ignore
    _PTY_AVAILABLE = sys.platform == "win32"
except Exception as e:  # pragma: no cover
    WinPTY = None  # type: ignore
    _PTY_AVAILABLE = False
    logger.warning(f"pywinpty unavailable: {e}")


PTY_AVAILABLE = _PTY_AVAILABLE


def _default_shell() -> List[str]:
    """Return the preferred shell command line for this platform."""
    if sys.platform == "win32":
        # PowerShell is preferred; fall back to cmd if missing.
        ps = os.environ.get("ComSpec", "cmd.exe")
        powershell = None
        for candidate in (
            r"C:\Program Files\PowerShell\7\pwsh.exe",
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        ):
            if Path(candidate).exists():
                powershell = candidate
                break
        if powershell:
            return [powershell, "-NoLogo"]
        return [ps]
    # Non-Windows (development convenience): use bash.
    return ["/bin/bash", "-i"]


class PtySession:
    """A single PTY-backed shell session that streams output to subscribers."""

    def __init__(
        self,
        runtime_id: int,
        provider_id: Optional[int],
        provider_name: str,
        cwd: str,
        cols: int = 120,
        rows: int = 30,
    ) -> None:
        self.runtime_id = runtime_id
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.cwd = str(cwd)
        self.cols = cols
        self.rows = rows

        self._pty: Optional[WinPTY] = None
        self._pid: Optional[int] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stopped = threading.Event()
        # Ring buffer of UTF-8 chunks (rendered output, ANSI included).
        self._buffer: Deque[str] = deque(maxlen=4000)
        # Subscriber callbacks. Each one accepts a single string chunk.
        self._subscribers: List[Callable[[str], None]] = []
        self._exit_code: Optional[int] = None
        self._started_at: float = time.time()
        self._status: str = "starting"
        self._lock = threading.Lock()
        self.user_id: Optional[int] = None
        self._idle_timer: Optional[threading.Timer] = None
        self._idle_seconds: float = 300.0  # 5 min — gives user time to reconnect

    @property
    def status(self) -> str:
        return self._status

    @property
    def pid(self) -> Optional[int]:
        return self._pid

    @property
    def exit_code(self) -> Optional[int]:
        return self._exit_code

    def buffer_snapshot(self) -> str:
        with self._lock:
            return "".join(self._buffer)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Spawn the underlying shell and begin pumping output."""
        if not PTY_AVAILABLE or WinPTY is None:
            raise RuntimeError(
                "Native PTY is not available on this platform. "
                "Install pywinpty (Windows only)."
            )
        self._loop = loop

        argv = _default_shell()
        appname = argv[0]
        cmdline_args = " ".join(f'"{a}"' if " " in a else a for a in argv[1:]) if len(argv) > 1 else None
        try:
            self._pty = WinPTY(self.cols, self.rows)
            ok = self._pty.spawn(appname, cmdline=cmdline_args, cwd=self.cwd)
            if not ok:
                raise RuntimeError(f"PTY spawn failed for {appname} {cmdline_args or ''}")
            self._pid = getattr(self._pty, "pid", None)
        except Exception as e:
            self._status = "failed"
            raise RuntimeError(f"Failed to start PTY: {e}") from e

        self._status = "running"
        self._reader_thread = threading.Thread(
            target=self._read_loop, name=f"pty-reader-{self.runtime_id}", daemon=True
        )
        self._reader_thread.start()

    def _read_loop(self) -> None:
        assert self._pty is not None
        # ConPTY's `blocking=True` behaviour is unreliable; poll non-blocking
        # and sleep briefly. This keeps the reader responsive to kill().
        idle_strikes = 0
        try:
            while not self._stopped.is_set():
                try:
                    chunk = self._pty.read(blocking=False)
                except Exception as e:
                    logger.debug(f"pty[{self.runtime_id}] read error: {e}")
                    break
                if not chunk:
                    # Nothing to read right now. If the process is gone, exit.
                    try:
                        alive = self._pty.isalive()
                    except Exception:
                        alive = False
                    if not alive:
                        idle_strikes += 1
                        if idle_strikes > 10:
                            break
                    else:
                        idle_strikes = 0
                    time.sleep(0.02)
                    continue
                idle_strikes = 0
                if isinstance(chunk, bytes):  # safety
                    try:
                        chunk = chunk.decode("utf-8", errors="replace")
                    except Exception:
                        chunk = chunk.decode("latin-1", errors="replace")
                with self._lock:
                    self._buffer.append(chunk)
                self._dispatch(chunk)
        finally:
            # Process exit handling
            try:
                if self._pty is not None and not self._pty.isalive():
                    self._exit_code = self._pty.get_exitstatus()
            except Exception:
                self._exit_code = None
            self._status = "exited"
            self._dispatch("\r\n[orch] process exited\r\n", system=True)

    def _dispatch(self, chunk: str, system: bool = False) -> None:
        # Snapshot the subscriber list to avoid holding the lock during callbacks.
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(chunk)
            except Exception as e:
                logger.warning(f"pty subscriber error: {e}")

    def attach(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)
            if self._idle_timer is not None:
                self._idle_timer.cancel()
                self._idle_timer = None

    def detach(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass
            if not self._subscribers:
                self._schedule_idle_teardown()

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def _schedule_idle_teardown(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()

        def _teardown() -> None:
            with self._lock:
                if self._subscribers:
                    return
            pty_manager.remove(self.runtime_id)

        self._idle_timer = threading.Timer(self._idle_seconds, _teardown)
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def write(self, data: str) -> None:
        if self._pty is None or not self._pty.isalive():
            return
        try:
            self._pty.write(data)
        except Exception as e:
            logger.warning(f"pty[{self.runtime_id}] write failed: {e}")

    def resize(self, cols: int, rows: int) -> None:
        if self._pty is None:
            return
        try:
            self.cols = max(20, int(cols))
            self.rows = max(5, int(rows))
            self._pty.set_size(self.cols, self.rows)
        except Exception as e:
            logger.debug(f"pty resize ignored: {e}")

    def pause(self) -> None:
        """Best-effort pause: Suspend Windows process via ntdll."""
        self._status = "paused"
        if sys.platform == "win32" and self._pid:
            try:
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x0800, False, self._pid)
                if handle:
                    ctypes.windll.ntdll.NtSuspendProcess(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
            except Exception as e:
                logger.warning(f"Failed to suspend process {self._pid}: {e}")

    def resume(self) -> None:
        if self._pty is not None and self._pty.isalive():
            self._status = "running"
            if sys.platform == "win32" and self._pid:
                try:
                    import ctypes
                    handle = ctypes.windll.kernel32.OpenProcess(0x0800, False, self._pid)
                    if handle:
                        ctypes.windll.ntdll.NtResumeProcess(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                except Exception as e:
                    logger.warning(f"Failed to resume process {self._pid}: {e}")

    def kill(self) -> None:
        self._stopped.set()
        try:
            if self._pty is not None:
                # Sending Ctrl+C is friendlier first.
                try:
                    self._pty.write("\x03")
                except Exception:
                    pass
                # Then close the PTY.
                try:
                    del self._pty
                except Exception:
                    pass
        finally:
            self._pty = None
            if self._status not in ("exited", "failed"):
                self._status = "killed"

    def is_alive(self) -> bool:
        if self._pty is None:
            return False
        try:
            return bool(self._pty.isalive())
        except Exception:
            return False


class PtyManager:
    """Singleton manager that owns all PTY sessions in the process."""

    def __init__(self) -> None:
        self._sessions: Dict[int, PtySession] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        self._ws_tokens: Dict[int, Tuple[str, float]] = {}

    def generate_ws_token(self, runtime_id: int) -> str:
        with self._lock:
            now = time.time()
            if runtime_id in self._ws_tokens:
                token, expires = self._ws_tokens[runtime_id]
                if expires - now > 15.0:
                    return token
            token = secrets.token_hex(16)
            self._ws_tokens[runtime_id] = (token, now + 30.0)
            return token

    def verify_ws_token(self, runtime_id: int, token: Optional[str]) -> bool:
        if not token:
            return False
        with self._lock:
            if runtime_id not in self._ws_tokens:
                return False
            stored_token, expires = self._ws_tokens[runtime_id]
            if time.time() > expires:
                del self._ws_tokens[runtime_id]
                return False
            is_valid = secrets.compare_digest(stored_token, token)
            if is_valid:
                del self._ws_tokens[runtime_id]
            return is_valid

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop

    def has(self, runtime_id: int) -> bool:
        with self._lock:
            return runtime_id in self._sessions

    def get(self, runtime_id: int) -> Optional[PtySession]:
        with self._lock:
            return self._sessions.get(runtime_id)

    def active_for_provider(
        self, provider_id: int, user_id: Optional[int] = None
    ) -> Optional[PtySession]:
        with self._lock:
            for session in list(self._sessions.values()):
                if session.provider_id != provider_id or not session.is_alive():
                    continue
                if user_id is not None and session.user_id not in (None, user_id):
                    continue
                return session
            return None

    def list_active(self) -> List[PtySession]:
        with self._lock:
            return [s for s in list(self._sessions.values()) if s.is_alive()]

    def create(
        self,
        runtime_id: int,
        provider_id: Optional[int],
        provider_name: str,
        cwd: str,
        user_id: Optional[int] = None,
    ) -> PtySession:
        with self._lock:
            if runtime_id in self._sessions:
                existing = self._sessions[runtime_id]
                if user_id is not None:
                    existing.user_id = user_id
                return existing
            session = PtySession(
                runtime_id=runtime_id,
                provider_id=provider_id,
                provider_name=provider_name,
                cwd=cwd,
            )
            session.user_id = user_id
            session.start(self.loop)
            self._sessions[runtime_id] = session
            return session

    def remove(self, runtime_id: int) -> None:
        with self._lock:
            session = self._sessions.pop(runtime_id, None)
        if session is not None:
            session.kill()

    def shutdown(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for s in sessions:
            s.kill()


# Global singleton consumed by routes + websockets.
pty_manager = PtyManager()
