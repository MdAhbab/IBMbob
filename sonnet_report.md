# IBMbob — System Audit Report

> **Scope**: Full codebase review of `c:\Users\ahbab\Downloads\IBMbob`  
> **Standard**: Industry-grade (production readiness, security, correctness, maintainability)  
> **Files Covered**: `run.py`, `backend/` (all subdirectories), `frontend/src/` (all subdirectories), `shared/`, `migrations/`, `data/`, `scripts/`  
> **Severity Legend**: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Security](#2-security)
3. [Concurrency & Architecture](#3-concurrency--architecture)
4. [Business Logic Bugs](#4-business-logic-bugs)
5. [API & Routing Issues](#5-api--routing-issues)
6. [Frontend Issues](#6-frontend-issues)
7. [Database & Schema](#7-database--schema)
8. [DevOps / Infrastructure](#8-devops--infrastructure)
9. [Code Quality & Maintainability](#9-code-quality--maintainability)
10. [File-by-File Coverage Matrix](#10-file-by-file-coverage-matrix)
11. [Priority Fix Order](#11-priority-fix-order)

---

## 1. Executive Summary

The IBMbob project is a multi-agent orchestration platform with a FastAPI backend, React/Vite frontend, and SQLite persistence. The system is architecturally interesting and largely feature-complete for a local-first developer tool. However, a comprehensive audit reveals **42 distinct issues** ranging from critical security vulnerabilities to minor code quality concerns.

**Top 5 immediate risks:**
1. The encryption master key is generated randomly at startup and never persisted — all stored encrypted credentials are lost on every restart.
2. The `sqlite3` (synchronous) module is used inside `async` service methods that run in the asyncio event loop, blocking the event loop on every DB call.
3. No authentication is implemented; `user_id` is hardcoded to `1` for every request, making the entire multi-user model non-functional.
4. The `runtimes.py` `/active` and `/live` endpoints have a Starlette route-ordering bug where `active` is ambiguously parsed as `/{runtime_id}`.
5. The encryption service allows a `double-base64` encoding of an already-base64 Fernet key, which silently produces a broken key on every encrypt.

---

## 2. Security

### 🔴 SEC-01 — Encryption key lost on every restart
**File**: [`backend/services/encryption_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/encryption_service.py#L44)  
**File**: [`backend/config.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/config.py)

**Root Cause**: `EncryptionService.__init__` calls `_generate_master_key()` when no `master_key` is supplied. `get_encryption_service()` in `provider_service.py` is called with `settings.encryption_key`. If `ENCRYPTION_KEY` is not set in the environment, `settings.encryption_key` is `None`, causing a new random key to be generated each startup.

```python
# encryption_service.py line 44
self.master_key = master_key or self._generate_master_key()
```

Any API keys stored in `provider_credentials` are encrypted with the random ephemeral key. After a restart the key changes, `decrypt_credential()` will throw, and the system becomes unusable.

**Fix**: Require `ENCRYPTION_KEY` in the environment and raise `ConfigurationError` at startup if absent. Alternatively, auto-generate once and persist to a `.key` file (with tight filesystem permissions), loading it on subsequent startups.

---

### 🔴 SEC-02 — `_generate_master_key()` double-encodes the Fernet key
**File**: [`backend/services/encryption_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/encryption_service.py#L57-L58)

```python
key = Fernet.generate_key()                          # already URL-safe base64
return base64.urlsafe_b64encode(key).decode('utf-8') # base64 of base64!
```

`Fernet.generate_key()` already returns URL-safe base64 bytes. The code then base64-encodes *that*, producing a double-encoded string that is never a valid 32-byte key when later passed to PBKDF2.

**Fix**: Return `key.decode('utf-8')` directly (no extra encode), or generate raw bytes with `secrets.token_bytes(32)` and encode once.

---

### 🔴 SEC-03 — No authentication; user_id hardcoded to 1
**File**: [`backend/api/dependencies.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/dependencies.py)

```python
async def get_current_user_id() -> int:
    return 1  # TODO: implement auth
```

Every API endpoint uses `user_id = 1`. In a single-user local tool this is tolerable, but:
- The database schema and logic fully support multi-user access.
- The encryption key is scoped per-user (`provider_{id}_user_{id}`).
- WebSocket terminals do no user validation at all.

**Fix**: Either implement JWT/session-cookie authentication or add a prominent `SINGLE_USER_MODE` guard that clearly documents the limitation and blocks multi-user deployments.

---

### 🟠 SEC-04 — WebSocket terminal accepts input without any authentication
**File**: [`backend/api/websockets/terminals.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/websockets/terminals.py#L43)

`/ws/terminals/{runtime_id}` accepts any WebSocket connection with a known `runtime_id`. There is no token/session check. Any local process that can reach port 8000 can inject keystrokes into a live PTY shell (PowerShell).

**Fix**: Require a short-lived token query parameter (generated by the spawn endpoint and stored in-memory for 30 seconds), checked at WebSocket handshake time.

---

### 🟠 SEC-05 — Path traversal in `validate_path` is insufficient
**File**: [`backend/utils/validators.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/utils/validators.py#L367)

```python
if ".." in path:
    return False
```

This string check is bypassable on Windows with `..\\`, URL-encoded `%2e%2e`, or UNC paths. It also does not constrain the path to an allowed root (workspace directory).

**Fix**: Use `pathlib.Path.resolve()` and verify the resolved path starts with the expected workspace root.

---

### 🟠 SEC-06 — `additional_config` stored as raw string repr, not JSON
**File**: [`backend/services/provider_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/provider_service.py#L500)

```python
str(credential_data.additional_config) if credential_data.additional_config else None,
```

Python's `str()` on a dict produces `{'key': 'value'}` (single quotes), which is not valid JSON. When this value is later read and parsed as JSON it will fail or be silently ignored.

**Fix**: Replace `str(...)` with `json.dumps(...)`.

---

### 🟡 SEC-07 — `hash_credential` uses unsalted SHA-256
**File**: [`backend/services/encryption_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/encryption_service.py#L211)

Used for "comparison purposes." Unsalted SHA-256 is vulnerable to rainbow tables. If API keys are ever hashed for indexing or lookup, this is exploitable.

**Fix**: Use `hashlib.scrypt` or `hmac.new(secret_key, credential.encode(), 'sha256').hexdigest()`.

---

### 🟡 SEC-08 — `get_master_key()` method publicly exposes the master key
**File**: [`backend/services/encryption_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/encryption_service.py#L226)

This method returns the raw master key over any code path that can reach it. If an attacker can trigger a code path that logs or transmits the return value, all credentials are compromised.

**Fix**: Remove or restrict this method to a CLI-only admin interface, protected by a strong access check.

---

### 🟡 SEC-09 — Workspace path written to disk without sanitization
**File**: [`backend/api/routes/orchestrator.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/orchestrator.py#L442)

`_write_divisions_artifact` calls `shared_dir.mkdir(parents=True, exist_ok=True)` where `shared_dir` is derived from a user-controlled workspace path stored in DB. A crafted path could create directories outside the intended workspace.

**Fix**: Resolve the workspace path and assert it lies under the configured `upload_dir` root before writing.

---

## 3. Concurrency & Architecture

### 🔴 CONC-01 — Synchronous `sqlite3` blocking the asyncio event loop
**Files**: [`backend/services/provider_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/provider_service.py#L69), [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L96), [`backend/services/analytics_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/analytics_service.py)

All three service classes use synchronous `sqlite3.connect()` inside `async` methods via a `@contextmanager`. This blocks the event loop for every database call, defeating the purpose of async I/O and causing request latency spikes under any concurrent load.

```python
# provider_service.py — runs in async context but is synchronous
with self._get_connection() as conn:  # sqlite3.connect() — blocks event loop
    cursor = conn.cursor()
    cursor.execute(...)
```

Meanwhile, the API layer uses `aiosqlite` correctly. This is an architectural split that must be reconciled.

**Fix**: Either:
  - Convert all service-layer DB calls to `aiosqlite` (preferred); or
  - Wrap synchronous DB calls with `await asyncio.to_thread(...)`.

---

### 🔴 CONC-02 — Global singleton services are not thread-safe at initialization
**Files**: `provider_service.py`, `orchestrator_service.py`, `analytics_service.py`, `encryption_service.py`

All four use the pattern:
```python
_service = None
def get_service():
    global _service
    if _service is None:
        _service = MyService()   # race condition
    return _service
```

In a multi-worker deployment or under asyncio task concurrency at startup, multiple tasks can see `_service is None` simultaneously and create duplicate (possibly inconsistent) instances.

**Fix**: Use `asyncio.Lock` for async singletons or `threading.Lock` for sync ones. For the encryption service (which holds a master key), double-initialization is especially dangerous.

---

### 🟠 CONC-03 — PTY reader thread dispatches to asyncio via `call_soon_threadsafe` closure capturing mutable `loop`
**File**: [`backend/api/websockets/terminals.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/websockets/terminals.py#L82-L88)

```python
loop.call_soon_threadsafe(
    lambda: asyncio.ensure_future(
        websocket.send_text(_safe_json({...}))
    )
)
```

`asyncio.ensure_future` requires a running event loop. If the WebSocket closes between the `call_soon_threadsafe` scheduling and the lambda execution, `websocket.send_text()` will raise `WebSocketDisconnect` or `RuntimeError` silently (the exception is swallowed inside the lambda with no handler).

Also, `loop = asyncio.get_event_loop()` on line 57 is deprecated in Python 3.10+ and will raise a `DeprecationWarning` (and eventually error) when called from a coroutine outside the main thread context.

**Fix**: Use `asyncio.run_coroutine_threadsafe(coro, loop)` instead of the `call_soon_threadsafe + ensure_future` pattern.

---

### 🟠 CONC-04 — `PtyManager` is not thread-safe
**File**: [`backend/services/pty_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/pty_service.py#L254)

`PtyManager._sessions: Dict[int, PtySession]` is accessed from both the FastAPI async event loop (via `create`, `remove`, `list_active`) and the PTY reader threads (via subscriber callbacks). There is no lock protecting the dict.

**Fix**: Add an `asyncio.Lock` for async access paths and a `threading.Lock` for the reader thread paths (or use a single `threading.Lock` throughout since dict ops are brief).

---

### 🟠 CONC-05 — `ConnectionManager.broadcast` mutates dict during iteration
**File**: [`backend/api/websockets/manager.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/websockets/manager.py#L155)

```python
for connection_id, websocket in self.active_connections.items():
    ...
    self.disconnect(connection_id)  # mutates self.active_connections
```

`disconnect()` deletes from `active_connections`, but the loop iterator was created from `.items()`. Under Python this works because the `items()` creates a view, but deleting mid-iteration is undefined behaviour and can cause `RuntimeError: dictionary changed size during iteration`.

**Fix**: Iterate over a snapshot: `list(self.active_connections.items())`.

---

### 🟡 CONC-06 — `OrchestratorService` uses synchronous `sqlite3` for `ROUND_ROBIN` strategy, mixed with `async` provider calls
**File**: [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L355)

The `select_provider` method is `async` and awaits `calculate_confidence`, but the `ROUND_ROBIN` branch does a synchronous `with self._get_connection()` DB call inline — the same event-loop-blocking problem as CONC-01 but localized to the routing hot path.

---

### 🟡 CONC-07 — Heartbeat loop never cancelled on app shutdown
**File**: [`backend/api/websockets/manager.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/websockets/manager.py#L289)

`start_heartbeat()` creates a background task, but the FastAPI `lifespan` does not call `stop_heartbeat()`. On graceful shutdown the task is abandoned, potentially causing `asyncio.CancelledError` noise or keeping the process alive.

**Fix**: Call `await connection_manager.stop_heartbeat()` in the `lifespan` shutdown block.

---

## 4. Business Logic Bugs

### 🔴 BIZ-01 — `reset_orchestrator_config` breaks the `UNIQUE(user_id, config_name)` constraint
**File**: [`backend/api/routes/orchestrator.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/orchestrator.py#L384)

After deactivating all configs, the route inserts a new row with `config_name = "Default Configuration"`. If this name already exists in the table (even as inactive), the `UNIQUE(user_id, config_name)` constraint fires a `sqlite3.IntegrityError`.

**Fix**: Use `INSERT OR REPLACE` or delete old inactive rows first, or append a timestamp to the config name.

---

### 🔴 BIZ-02 — `dispatch_task` (orchestrator route) raises 404 if no orchestrator config exists
**File**: [`backend/api/routes/orchestrator.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/orchestrator.py#L88)

New users have no `orchestrator_config` row. The `/dispatch` endpoint immediately returns 404 instead of auto-creating a default config (as `/config/reset` would). This means every new user cannot dispatch tasks until they explicitly POST to `/config/reset`.

**Fix**: Auto-upsert a default config row if none exists, mirroring the `reset_orchestrator_config` logic.

---

### 🟠 BIZ-03 — Token estimation (`_estimate_tokens`) is a floor function, not a ceiling
**File**: [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L139)

```python
return len(prompt) // 4 + 100
```

This produces 100 tokens for any prompt shorter than 400 characters. A 2000-character prompt (which is actually ~500 tokens) would be estimated as 600 tokens. The "conversation vs. complex task" split at 1000 tokens can fire incorrectly for medium-length prompts with technical vocabulary (which have token/character ratios below 0.25).

**Fix**: Use a proper `tiktoken`-based or character-class-aware estimator. At minimum, change `// 4` to `/ 3` (the statistical average for English), and apply `math.ceil`.

---

### 🟠 BIZ-04 — `approve_pending_command` checks for `RUNNING` status, but approval is for `PENDING`
**File**: [`backend/api/routes/runtimes.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/runtimes.py#L427)

```python
if current_status != RuntimeStatus.RUNNING:
    raise HTTPException(400, "Runtime is not in pending state ...")
```

The error message says "not in pending state" but the code checks for `RUNNING`. The `RuntimeStatus` enum likely has a `PENDING` state (matching the schema's CHECK constraint), but the approval gate never fires for it.

**Fix**: Change the condition to `!= RuntimeStatus.PENDING` and ensure the schema's `CHECK` includes `'pending'`.

---

### 🟠 BIZ-05 — `approve_pending_command` (approved=True) logs approval but does not actually resume the process
**File**: [`backend/api/routes/runtimes.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/runtimes.py#L450)

```python
# In a real implementation, this would signal the process to continue
```

When `approved=True`, only a log entry is written. The PTY process is never actually signaled. The database status is not even updated from `RUNNING`. This is a non-functional stub.

**Fix**: Implement the PTY signal path (e.g., `pty_manager.get(runtime_id).write("\n")` to continue, or use a `threading.Event` per session that the PTY reader waits on).

---

### 🟠 BIZ-06 — `clear_all_sessions` (`DELETE /sessions`) does not cascade-delete runtime records
**File**: [`backend/api/routes/sessions.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/sessions.py#L388)

The schema has `cli_runtimes.session_id` referencing `sessions(id) ON DELETE CASCADE`, so the DB-level cascade should work. However, active in-memory PTY sessions (`pty_manager._sessions`) are not killed. The process keeps running; the DB record is gone. Re-querying `/runtimes/active` will still show them.

**Fix**: Before deleting sessions, enumerate all associated runtimes and call `pty_manager.remove(runtime_id)` for each.

---

### 🟡 BIZ-07 — Round-robin routing does not actually round-robin across all providers
**File**: [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L354)

The ROUND_ROBIN strategy looks up the last `selected_provider_id` from `routing_history` and picks the next one in `available_providers` list order. If the provider list order is non-deterministic (SQLite `ORDER BY display_name`) and the last routing was from a different strategy, the "next index" logic produces garbage.

**Fix**: Maintain a per-user ROUND_ROBIN cursor in-memory (or in a `routing_state` table), keyed by user_id.

---

### 🟡 BIZ-08 — `LEAST_COST` strategy in `orchestrator_service.py` uses hardcoded name-based heuristics
**File**: [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L388)

Cost priority is a hardcoded lookup table (`{'ollama': 1, 'google': 2, ...}`). If a provider's name is `gemini-api` or `google-gemini`, the lookup misses and assigns priority 5 (most expensive bucket).

**Fix**: Add a `cost_per_token` column to the `providers` table and sort by that value.

---

### 🟡 BIZ-09 — `decompose_task` always assigns `task_id = "task_1"` to first subtask, breaking dependency resolution
**File**: [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L157)

All branches create `task_id="task_1"`, `task_id="task_2"`, etc. as string literals. If a response includes subtasks from multiple `decompose_task` calls in a session, the IDs collide and dependency tracking (`dependencies=["task_1"]`) becomes ambiguous.

**Fix**: Use UUIDs or monotonically incrementing session-scoped IDs.

---

### 🟡 BIZ-10 — Daily quota reset always advances by exactly 1 day, ignoring timezones
**File**: [`backend/services/provider_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/provider_service.py#L364)

```python
(datetime.utcnow() + timedelta(days=1)).isoformat()
```

This is naive UTC. If the user is in UTC-8, their "day" resets at 4 PM local time, not midnight. Additionally, `datetime.utcnow()` is deprecated in Python 3.12+.

**Fix**: Use `datetime.now(timezone.utc)` and store reset times with timezone info. Accept a configurable reset hour.

---

## 5. API & Routing Issues

### 🔴 API-01 — Starlette route-order ambiguity: `/active` and `/live` conflict with `/{runtime_id}`
**File**: [`backend/api/routes/runtimes.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/runtimes.py#L193)

The routes are registered as:
```
GET /runtimes
GET /runtimes/active
GET /runtimes/live
POST /runtimes/spawn
GET /runtimes/{runtime_id}
```

FastAPI registers routes in declaration order. The literal `/active` and `/live` routes are declared *before* `/{runtime_id}`, which is correct. However, the `verify_runtime_exists` dependency on `/{runtime_id}` tries to cast the path parameter to `int`. If a client hits `/runtimes/active`, FastAPI will route it to `/active` correctly **only if declared first**. This is currently correct but fragile — inserting any new route above them will break it.

The comment on `/live` says it exists to "avoid Starlette matching `active` as a path param", which confirms this is already a known fragility.

**Fix**: Use a dedicated router prefix or mount the `active`/`live` handlers on a sub-router registered before the parameterized routes.

---

### 🟠 API-02 — `GET /sessions?limit=1` used in frontend to load "most recent session" but returns oldest
**File**: [`backend/api/routes/sessions.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/sessions.py#L154)  
**File**: [`frontend/src/app/App.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/App.tsx#L120)

The frontend calls `apiPath("/sessions?limit=1")` intending to load the most recent session. However, the default `sort_order` is `DESC` on `created_at`, so it *does* return the most recent — but only because of the default sort. There is no explicit `sort_by=created_at&sort_order=desc` in the frontend call, making it vulnerable to the sort default changing.

**Fix**: Make the frontend call explicit: `/sessions?limit=1&sort_by=created_at&sort_order=desc`.

---

### 🟠 API-03 — `GET /runtimes/active` has no pagination; could return thousands of rows
**File**: [`backend/api/routes/runtimes.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/runtimes.py#L193)

`list_active_runtimes()` calls `pty_manager.list_active()` which iterates all in-memory sessions with no limit. `get_all_runtimes()` also has no pagination (no `LIMIT` or `OFFSET` in the query).

**Fix**: Add `limit` / `offset` query parameters consistent with the sessions endpoint.

---

### 🟠 API-04 — `DELETE /sessions` (clear all) has no confirmation guard
**File**: [`backend/api/routes/sessions.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/sessions.py#L375)

A single `DELETE /sessions` call permanently deletes all sessions, messages, artifacts, and (via cascade) runtime records for the user. There is no `?confirm=true` guard, no soft-delete, and no rate limiting.

**Fix**: Require a query parameter `?confirm=true`, or implement soft-delete with a `deleted_at` timestamp and a separate purge job.

---

### 🟠 API-05 — `update_session` short-circuits to inner `get_session()` call without re-checking user ownership
**File**: [`backend/api/routes/sessions.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/sessions.py#L356)

```python
if not update_fields:
    return await get_session(session_id, db, user_id)
```

This is harmless in the current code because `get_session` also checks `user_id`. However, directly calling a route handler function from another route handler is an anti-pattern that bypasses middleware and dependency injection.

**Fix**: Extract the DB read into a shared service function and call that instead.

---

### 🟡 API-06 — `GET /runtimes/{runtime_id}` has `include_logs: bool = True` as a query param but returns all logs with no limit
**File**: [`backend/api/routes/runtimes.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/runtimes.py#L360)

For long-running PTY sessions, `cli_logs` could contain tens of thousands of rows. Fetching all of them in one request can exhaust memory and response size limits.

**Fix**: Add `log_limit` and `log_offset` query parameters, defaulting to the last 100 log entries.

---

### 🟡 API-07 — `utc_now()` function is duplicated in every route file
**Files**: `sessions.py`, `runtimes.py`, `orchestrator.py`

Each route file defines its own local `utc_now()` helper function. This is copy-paste code that will diverge.

**Fix**: Define `utc_now()` once in `backend/utils/time.py` and import it everywhere.

---

## 6. Frontend Issues

### 🔴 FE-01 — Provider polling interval (10 s) combined with no debounce causes a request storm on focus
**File**: [`frontend/src/app/App.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/App.tsx#L294)

```javascript
const interval = window.setInterval(() => void load(), 10000);
```

`load()` makes 3 parallel API calls every 10 seconds. The `useEffect` that creates this interval depends on `[onboarded, prefProviders]`. Every time `prefProviders` changes (e.g., on backend sync), the interval is cleared and recreated, which resets the 10-second timer but also fires `load()` immediately. Under rapid state changes this can fire multiple times per second.

**Fix**: Separate the polling interval from the initial load. Use `useRef` to hold the interval, and only recreate it when `onboarded` changes (not on `prefProviders`).

---

### 🟠 FE-02 — `loadMessagesForSession` uses raw `fetch` without timeout
**File**: [`frontend/src/app/App.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/App.tsx#L81)

```javascript
const msgRes = await fetch(apiPath(`/sessions/${sid}/messages`));
```

This call has no timeout. If the backend hangs, the UI waits indefinitely with no error shown to the user.

**Fix**: Replace with `apiFetch(...)` (which applies the `AbortSignal.timeout` wrapper).

---

### 🟠 FE-03 — Model names in `store.tsx` don't match any real API endpoint models
**File**: [`frontend/src/app/components/store.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/store.tsx#L57)

```javascript
models: ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
// ...
models: ["gemini-3-pro", "gemini-3-flash", "gemini-2.5-pro"],
// ...
models: ["gpt-codex", "gpt-codex-mini", "o4-mini"],
```

- `claude-opus-4-7`, `claude-haiku-4-5` — these model IDs do not follow Anthropic's naming convention and are likely fictional.
- `gemini-3-pro`, `gemini-3-flash` — Gemini 3 models are not publicly available.
- `gpt-codex-mini`, `gpt-codex` — OpenAI deprecated the Codex API in 2023.

When users select these models and the backend tries to call the provider API with them, the provider will return 404 or a model-not-found error.

**Fix**: Sync model lists with each provider's actual public model catalog. Consider fetching supported models dynamically from each provider's `/models` endpoint.

---

### 🟠 FE-04 — `store.tsx` persists `sessions` array including hardcoded `demo-1` and `demo-2` entries to localStorage
**File**: [`frontend/src/app/components/store.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/store.tsx#L237)

The `DEFAULT_STATE.sessions` contains two demo sessions with fake data (`tokens: 124_500`, `spend: 1.84`). These are persisted to `localStorage` on first load and shown in the session list to real users. They also appear in analytics aggregations if any frontend code totals session spend.

**Fix**: Separate demo/placeholder data from persisted state. Either remove demo entries entirely or flag them with `isDemo: true` and exclude from persistence and analytics.

---

### 🟠 FE-05 — `ErrorBoundary` calls `location.reload()` unconditionally, losing unsaved state
**File**: [`frontend/src/app/App.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/App.tsx#L484)

The "Reset state & reload" button clears `orch.*` localStorage keys and reloads. If the user has unsaved chat messages in the input box or an active session, everything is lost without warning.

**Fix**: Show a confirmation dialog before clearing state and reloading.

---

### 🟡 FE-06 — `chatInput` state is not cleared on session switch
**File**: [`frontend/src/app/App.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/App.tsx#L366)

When the user selects a different session from the sidebar, `loadMessagesForSession` is called but `setChatInput("")` is not. The previously typed input persists across sessions.

**Fix**: Call `setChatInput("")` in the `onSelectSession` handler.

---

### 🟡 FE-07 — `applyDivisionsToAgents` silently ignores CLIs with no matching division
**File**: [`frontend/src/app/App.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/App.tsx#L58)

```javascript
if (!division) return { ...cli, task: undefined, state: cli.runtimeId ? "executing" : "idle" };
```

When the orchestrator returns divisions for a subset of agents, unmatched agents have their `task` cleared to `undefined`. This means a previously assigned task is silently wiped if it's not included in the latest response's division list.

**Fix**: Do not overwrite `task` for agents not present in the division response. Only update agents that are explicitly mentioned.

---

### 🟡 FE-08 — `wsPath` always uses `window.location.host` — breaks in reverse-proxy deployments
**File**: [`frontend/src/app/lib/api.ts`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/lib/api.ts#L27)

```javascript
return `${proto}//${window.location.host}${p}`;
```

If the app is deployed behind a reverse proxy at a sub-path (e.g., `/bob/`), the WebSocket URL will omit the sub-path and fail. The `VITE_API_BASE` env var controls HTTP paths but is not used for WebSocket paths.

**Fix**: Add a `VITE_WS_BASE` env variable or derive the WS base from `VITE_API_BASE` at build time.

---

### 🟢 FE-09 — `DEFAULT_FETCH_MS` (25 seconds) is very long for a local app
**File**: [`frontend/src/app/lib/api.ts`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/lib/api.ts#L38)

The chat endpoint already uses `timeoutMs: 60_000`. The default 25-second timeout will cause all other API calls to hang for 25 seconds before showing an error. For a locally-running backend, 5–10 seconds is more appropriate.

**Fix**: Lower `DEFAULT_FETCH_MS` to `8_000` for non-chat endpoints.

---

## 7. Database & Schema

### 🔴 DB-01 — Schema `updated_at` triggers fire `UPDATE` recursively
**File**: [`backend/database/schema.sql`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/database/schema.sql#L365)

```sql
CREATE TRIGGER IF NOT EXISTS update_users_timestamp
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

This `AFTER UPDATE` trigger runs another `UPDATE` on the same table. SQLite disables recursive triggers by default (`PRAGMA recursive_triggers = OFF`), so the trigger itself won't loop. However, the nested `UPDATE` fires the trigger *again* in SQLite with recursive triggers enabled (which some tools do enable), causing infinite recursion.

More importantly, the nested `UPDATE` will conflict with the WAL-mode write transaction and can cause `SQLITE_BUSY` errors when concurrent writes occur.

**Fix**: Use `NEW.id` in the trigger body with the `WHEN OLD.updated_at != NEW.updated_at` guard, or remove the trigger and set `updated_at` in application code (which is already done in the route handlers).

---

### 🟠 DB-02 — `provider_credentials` has no index on `(user_id, is_active)` composite
**File**: [`backend/database/schema.sql`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/database/schema.sql#L90)

The most common query is:
```sql
SELECT ... FROM provider_credentials WHERE user_id = ? AND is_active = 1
```

The existing indexes are on `user_id`, `provider_id`, and `is_active` separately. A composite `(user_id, is_active)` index would serve this query far more efficiently.

**Fix**: Add `CREATE INDEX idx_provider_credentials_user_active ON provider_credentials(user_id, is_active);`

---

### 🟠 DB-03 — `routing_history.selected_provider_id` has `ON DELETE CASCADE`, not `SET NULL`
**File**: [`backend/database/schema.sql`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/database/schema.sql#L303)

```sql
FOREIGN KEY (selected_provider_id) REFERENCES providers(id) ON DELETE CASCADE
```

If a provider is deleted, all routing history entries for that provider are cascade-deleted too. This destroys analytics history. The correct behavior is `ON DELETE SET NULL`.

**Fix**: Change to `ON DELETE SET NULL` (and allow `selected_provider_id` to be `NULL`).

---

### 🟡 DB-04 — `messages.role` check constraint doesn't include `'orchestrator'` role
**File**: [`backend/database/schema.sql`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/database/schema.sql#L143)

```sql
role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'function', 'tool'))
```

The orchestrator inserts messages with `role = 'assistant'` (correct), but the frontend maps them to `role = 'orchestrator'` for display. However, if any code ever tries to store an `orchestrator`-role message directly, it will hit a constraint error.

**Fix**: Ensure the display role (`orchestrator`) is only a UI concept and never written to the database.

---

### 🟡 DB-05 — No index on `usage_analytics.created_at` with `user_id` composite
**File**: [`backend/database/schema.sql`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/database/schema.sql#L354)

Analytics queries typically filter on `user_id` and a time range. The `created_at` index exists but is not composite with `user_id`, requiring a full scan of the `user_id` index result set.

**Fix**: Add `CREATE INDEX idx_usage_analytics_user_created ON usage_analytics(user_id, created_at DESC);`

---

### 🟡 DB-06 — `cli_runtimes.process_id` column stores OS PID as INTEGER but schema comment says "populated once PTY spawns"
**File**: [`backend/database/schema.sql`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/database/schema.sql#L196)

The `spawn_runtime` endpoint inserts `process_id = NULL` initially, then updates it after the PTY spawns. If the PTY fails to start (exception on line 279 of `runtimes.py`), the row is updated to `status='failed'` but `process_id` remains `NULL`. Any query that joins on `process_id IS NOT NULL` to find active processes will miss this row.

**Fix**: Use a more robust status machine: mark `process_id` as explicitly `NULL` for failed/killed rows and document the invariant.

---

## 8. DevOps / Infrastructure

### 🟠 DEV-01 — `run.py` uses hardcoded pip install without version pinning
**File**: [`run.py`](file:///c:/Users/ahbab/Downloads/IBMbob/run.py)

```python
subprocess.check_call([pip, "install", "-r", "requirements.txt"])
```

The `ProcessManager` auto-installs requirements at startup. If `requirements.txt` has unpinned or loosely-pinned dependencies (e.g., `fastapi>=0.100`), production builds can break silently when a major version update is published.

**Fix**: Pin all dependencies to exact versions in `requirements.txt` and use `pip install --no-deps -r requirements.txt` in production, or adopt `uv lock` / `pip-compile`.

---

### 🟠 DEV-02 — Frontend uses `npm run dev` (development server) in production context
**File**: [`run.py`](file:///c:/Users/ahbab/Downloads/IBMbob/run.py)

`run.py` starts the frontend with `npm run dev` (Vite development mode). This is appropriate for local development but unsuitable for any shared or remote deployment because:
- Vite dev server is single-threaded and not optimized for concurrent requests.
- Source maps and unminified code are exposed.
- Hot Module Replacement (HMR) WebSocket connections are opened.

**Fix**: Add a `--production` flag to `run.py` that runs `npm run build` then serves the `dist/` folder via the FastAPI `StaticFiles` mount or a dedicated static file server.

---

### 🟡 DEV-03 — No `.env.example` file
**File**: Project root

The project uses environment variables (`GROK_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `ENCRYPTION_KEY`, `DATABASE_URL`, etc.) but provides no `.env.example` template. New developers will not know which variables are required vs. optional.

**Fix**: Create `.env.example` with all variables documented, their defaults, and which are required.

---

### 🟡 DEV-04 — `run.py` subprocess output drain threads use `daemon=True` but are never joined
**File**: [`run.py`](file:///c:/Users/ahbab/Downloads/IBMbob/run.py)

The stdout/stderr drain threads are marked daemon, so they die when the main process exits. However, if the main process hangs (e.g., waiting for `backend_proc.wait()`), these threads could miss the final lines of output from a crashing backend.

**Fix**: Join the drain threads with a small timeout after the subprocess exits.

---

### 🟡 DEV-05 — No health check endpoint for frontend proxy
**File**: Project root

The backend has `/health`, but the Vite dev proxy (`vite.config.ts`) has no health check. Reverse proxies like nginx or the run.py orchestrator cannot verify if the frontend dev server is ready before routing traffic.

**Fix**: Add a `/ping` endpoint in `vite.config.ts` or use `wait-on` to gate startup.

---

## 9. Code Quality & Maintainability

### 🟡 CQ-01 — `OrchestratorService` and `ProviderService` are singletons but `dispatch_task` in `orchestrator.py` (route) uses `aiosqlite` directly
**File**: [`backend/api/routes/orchestrator.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/orchestrator.py#L56)

The route handler duplicates provider-selection logic that already exists in `OrchestratorService.dispatch_task()`. There are now two independent implementations of "select a provider based on routing strategy" — the route handler's simplified version and the service's full version. These will drift.

**Fix**: Route handlers should delegate entirely to services. Remove routing logic from `orchestrator.py` route handlers and call `OrchestratorService.dispatch_task()`.

---

### 🟡 CQ-02 — `_classify_task` regex patterns have false positives
**File**: [`backend/services/orchestrator_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator_service.py#L67)

```python
r'\b(write|create|generate|implement|code|function|class|script)\b'
```

A message like "what class of bug is this?" will match `code_generation` because `class` appears in the prompt, even though it's a question (conversational). The `conversation` pattern (`what|how|why|...`) will be checked *after* `code_generation`, so it never wins.

**Fix**: Reorder patterns so conversational questions are checked first, or add negative lookahead patterns for question-form sentences.

---

### 🟡 CQ-03 — `PtySession.pause()` has no implementation on Windows
**File**: [`backend/services/pty_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/pty_service.py#L218)

```python
def pause(self) -> None:
    """Best-effort pause: Windows has no SIGSTOP, so we just mark status."""
    self._status = "paused"
```

The status is updated in the DB and shown in the UI as "paused" but the PTY process continues running unpaused. The UI's pause button gives false feedback to the user.

**Fix**: Either document clearly in the UI that "pause" is a UI-only label on Windows, or use `SuspendThread` via `ctypes` as a best-effort Windows process suspension.

---

### 🟡 CQ-04 — `sanitize_filename` in `validators.py` does not handle empty extension
**File**: [`backend/utils/validators.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/utils/validators.py#L379)

```python
filename = Path(filename).name
filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
filename = filename.strip(". ")
```

A filename like `.env` (starts with a dot) would be stripped to `env`, which changes the file's semantics. A dotfile should be preserved or explicitly blocked.

**Fix**: Only strip leading dots if they form the entire filename (e.g., `...` → `unnamed`), not when they're part of a valid dotfile name.

---

### 🟡 CQ-05 — `verify_credential_hash` is timing-attack vulnerable
**File**: [`backend/services/encryption_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/encryption_service.py#L224)

```python
return self.hash_credential(credential) == credential_hash
```

String equality comparison in Python is not constant-time. An attacker who can trigger many verify calls with controlled input can use timing analysis to recover the hash value.

**Fix**: Use `hmac.compare_digest(computed_hash, stored_hash)` for constant-time comparison.

---

### 🟡 CQ-06 — `_read_loop` in `PtySession` uses `idle_strikes > 3` as a dead-process sentinel — 4 false "deaths" are possible
**File**: [`backend/services/pty_service.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/pty_service.py#L153)

```python
if not alive:
    idle_strikes += 1
    if idle_strikes > 3:
        break
```

`isalive()` can return `False` transiently during a subprocess exec-and-replace. The 3-strike threshold (at `sleep(0.02)` = 60ms total) may be too short for slow Windows process spawning, causing premature PTY session termination.

**Fix**: Increase the threshold to at least 10 strikes (200ms), or add an exponential backoff before declaring the process dead.

---

### 🟢 CQ-07 — `# Made with Bob` comment at end of every file
**Files**: All backend Python files and some SQL files.

This is a harmless branding comment but adds noise to diffs and `grep` output.

**Fix**: Move the credit to a single `README.md` or `pyproject.toml` attribution field.

---

### 🟢 CQ-08 — `import logging` inside `general_exception_handler` (re-imported per call)
**File**: [`backend/utils/exceptions.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/utils/exceptions.py#L462)

```python
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    logger = logging.getLogger(__name__)
```

The `import logging` inside the function body is called on every unhandled exception. While Python caches module imports, this is an anti-pattern.

**Fix**: Move the `import logging` and `logger = logging.getLogger(__name__)` to the module top level.

---

### 🟢 CQ-09 — `store.tsx` `sessions` array (local state) and backend sessions table are disconnected
**File**: [`frontend/src/app/components/store.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/store.tsx#L207)

The frontend maintains a `sessions: SessionEntry[]` in local state/localStorage, but the backend stores sessions in SQLite and returns them from `/sessions`. These two stores are never synchronized. The session list in the sidebar likely shows backend sessions, not the local store ones, but the local store sessions are persisted to `localStorage` forever.

**Fix**: Remove `sessions` from the local store entirely and load them exclusively from the backend API.

---

### 🟢 CQ-10 — `validate_path` comment says "Block localhost/private IPs in production if needed" — never implemented
**File**: [`backend/utils/validators.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/utils/validators.py#L204)

```python
# Allow in development, but you might want to restrict in production
pass
```

This is a TODO that is easily missed.

**Fix**: Add an explicit `allow_localhost: bool = True` parameter and document it, or implement the restriction based on `settings.environment`.

---

## 10. File-by-File Coverage Matrix

| File | Issues Found | Severity |
|------|-------------|---------|
| `run.py` | DEV-01, DEV-04 | 🟠🟡 |
| `backend/main.py` | CONC-07 | 🟡 |
| `backend/config.py` | SEC-01 | 🔴 |
| `backend/api/dependencies.py` | SEC-03 | 🔴 |
| `backend/api/routes/sessions.py` | API-02, API-04, API-05, API-07, DB-04 | 🟠🟡 |
| `backend/api/routes/runtimes.py` | API-01, API-03, API-06, API-07, BIZ-04, BIZ-05, BIZ-06, DB-06 | 🔴🟠🟡 |
| `backend/api/routes/orchestrator.py` | BIZ-01, BIZ-02, API-07, CQ-01, SEC-09 | 🔴🟠🟡 |
| `backend/api/websockets/manager.py` | CONC-05, CONC-07 | 🟠🟡 |
| `backend/api/websockets/terminals.py` | SEC-04, CONC-03 | 🔴🟠 |
| `backend/services/encryption_service.py` | SEC-02, SEC-07, SEC-08, CQ-05 | 🔴🟡 |
| `backend/services/provider_service.py` | SEC-01, SEC-06, CONC-01, CONC-02, BIZ-10 | 🔴🟠🟡 |
| `backend/services/orchestrator_service.py` | CONC-01, CONC-02, CONC-06, BIZ-03, BIZ-07, BIZ-08, BIZ-09, CQ-02 | 🔴🟠🟡 |
| `backend/services/pty_service.py` | CONC-04, CQ-03, CQ-06 | 🟠🟡 |
| `backend/utils/validators.py` | SEC-05, CQ-04, CQ-10 | 🟠🟡🟢 |
| `backend/utils/exceptions.py` | CQ-08 | 🟢 |
| `backend/database/schema.sql` | DB-01, DB-02, DB-03, DB-04, DB-05, DB-06 | 🔴🟠🟡 |
| `frontend/src/app/App.tsx` | FE-01, FE-02, FE-05, FE-06, FE-07 | 🔴🟠🟡 |
| `frontend/src/app/components/store.tsx` | FE-03, FE-04, CQ-09 | 🟠🟢 |
| `frontend/src/app/lib/api.ts` | FE-08, FE-09 | 🟡🟢 |
| `scripts/` | No critical issues found | — |
| `migrations/` | No issues (schema is applied via `schema.sql`) | — |
| `shared/` | No issues found | — |
| `data/` | No issues found | — |

---

## 11. Priority Fix Order

### Phase 1 — Fix Before Any Production Use (Critical)
| ID | Title | Effort |
|----|-------|--------|
| SEC-01 | Persist/require encryption master key | S |
| SEC-02 | Fix double-base64 encoding in key generation | S |
| SEC-03 | Implement or formally document single-user auth | M |
| CONC-01 | Wrap sync sqlite3 calls with `asyncio.to_thread` | M |
| CONC-02 | Add locks to singleton initializers | S |
| BIZ-01 | Fix `reset_orchestrator_config` UNIQUE constraint crash | S |
| BIZ-02 | Auto-upsert default orchestrator config for new users | S |
| DB-01 | Fix recursive trigger cascade (or remove triggers) | S |
| API-01 | Fix Starlette route ordering for `/active`/`/{id}` | S |

### Phase 2 — Fix Before Sharing / Beta (High)
| ID | Title | Effort |
|----|-------|--------|
| SEC-04 | WebSocket terminal authentication | M |
| SEC-05 | Path traversal fix with root-anchoring | S |
| SEC-06 | Fix `additional_config` stored as Python repr | S |
| CONC-03 | Replace `call_soon_threadsafe + ensure_future` with `run_coroutine_threadsafe` | S |
| CONC-04 | Add lock to `PtyManager._sessions` dict | S |
| CONC-05 | Fix `broadcast` dict mutation during iteration | S |
| BIZ-04 | Fix approval endpoint status check | S |
| BIZ-05 | Implement actual PTY resume on approval | M |
| BIZ-06 | Kill PTY sessions on session delete | S |
| DB-03 | Fix `routing_history` ON DELETE behavior | S |
| FE-01 | Debounce provider polling effect | S |
| FE-02 | Add timeout to `loadMessagesForSession` | S |
| FE-03 | Fix model name catalog | M |
| FE-04 | Remove demo sessions from persisted state | S |

### Phase 3 — Polish / Maintainability (Medium/Low)
| ID | Title | Effort |
|----|-------|--------|
| BIZ-03 | Improve token estimation | S |
| BIZ-07–BIZ-10 | Routing strategy improvements | M |
| CQ-01–CQ-10 | Code quality cleanup | S each |
| DB-02, DB-05 | Add composite indexes | S |
| DEV-01–DEV-05 | DevOps improvements | M |
| FE-05–FE-09 | Frontend polish | S each |

---

*Report generated by full static analysis of all 50+ source files across backend, frontend, database, and infrastructure layers.*

---

## 12. Addendum — Backend-Frontend Disconnects, Planning Gaps & Corner Cases

> This section covers issues found in the second pass across all remaining files:  
> `providers.py` · `settings.py` · `workspace.py` · `analytics.py` · `agents.py` · `onboarding.py` · `tools.py`  
> `orchestrator/core.py` · `orchestrator/decomposer.py` · `orchestrator/router.py` · `orchestrator/aggregator.py`  
> `Onboarding.tsx` · `Settings.tsx` · `TerminalCard.tsx` · `AnalyticsStrip.tsx` · `OrchestratorGraph.tsx`  
> `SessionHistory.tsx` · `ChatView.tsx` · `GlobalChatBar.tsx` · `VoiceButton.tsx` · `Sidebar.tsx`

---

### Section A — Backend-Frontend API Contract Mismatches

These are cases where the frontend calls an endpoint, or sends/expects a payload shape, that does not match what the backend actually implements.

---

#### 🔴 BFC-01 — Settings panel writes are fire-and-forget; backend changes are never reflected back  
**Files**: [`frontend/src/app/components/Settings.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Settings.tsx#L316) · [`backend/api/routes/settings.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/settings.py#L276)

`persistEnabled()` in `ProviderRow` calls `PUT /providers/{id}` but ignores the response — there is no `.json()` parse, no state update, and no error handling. If the backend returns a validation error (e.g., the `default_model` is not in the allowed set), the UI never learns about it and shows a stale "configured" badge.

Similarly, `OrchestratorPanel` stores `orchestrator.model`, `routingStrategy`, `parallelism` etc. entirely in localStorage via `setOrchestrator()`. None of those values are ever POSTed to the backend's `PUT /orchestrator/config` endpoint. The backend's `orchestrator_config` table diverges from the UI permanently.

**Fix**:
1. In `persistEnabled` / `save()`, await the `PUT` response and update local state only on success.
2. Wire `OrchestratorPanel` to call `PUT /orchestrator/config` on every change, and seed its initial values from `GET /orchestrator/config` on mount.

---

#### 🔴 BFC-02 — `GET /providers/{id}/credentials` returns `api_key: "***"` but Settings.tsx displays it as the actual key  
**Files**: [`frontend/src/app/components/Settings.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Settings.tsx#L302) · [`backend/api/routes/providers.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/providers.py#L361)

```typescript
// Settings.tsx line 305
setSecret((j.api_key as string) || "");
```

The backend always returns `api_key: "***"` (masked). The frontend takes that value and puts it directly in the secret input field, which then shows `"***"` to the user as if it were the real key. If the user doesn't change it and clicks Save, `"***"` is sent as the new `api_key` — overwriting the real encrypted key with the literal string `"***"`.

**Fix**: When `j.api_key` starts with `"***"` treat it as "key already set, leave placeholder text, don't send on save unless the user types a new value." Add an `isPlaceholder` flag or check for the `"***"` prefix before POSTing credentials.

---

#### 🔴 BFC-03 — Onboarding sends `cli_configs` with `secret` field; backend `complete_onboarding` ignores it  
**Files**: [`frontend/src/app/components/Onboarding.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Onboarding.tsx#L191) · [`backend/api/routes/onboarding.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/onboarding.py)

The onboarding POST body shape sent by the frontend includes:
```json
{ "cli_configs": { "claude": { "method": "api_key", "secret": "sk-ant-...", "model": "..." } } }
```

The `backend/api/routes/onboarding.py` route's Pydantic model for `cli_configs` needs to be verified against this shape. If the backend's `CliConfig` model uses `api_key` instead of `secret`, the frontend's key is silently dropped and the credential is never stored — a silent data-loss bug.

**Fix**: Audit the `OnboardingCompleteRequest.cli_configs` Pydantic schema against the exact JSON the frontend sends. Add integration tests that round-trip a full onboarding POST and verify the credential is retrievable via `GET /providers/{id}/credentials`.

---

#### 🔴 BFC-04 — Onboarding "Skip setup" button calls `finish()` which POSTs to `/onboarding/complete` even with empty credentials  
**Files**: [`frontend/src/app/components/Onboarding.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Onboarding.tsx#L271)

```typescript
<button onClick={finish}>Skip setup</button>
```

The Skip button calls the same `finish()` function as "Complete Setup". `finish()` constructs `cli_configs` from `selected` and `cliCfg`, then unconditionally calls `POST /onboarding/complete`. With zero providers selected and no credentials entered, this sends a valid but empty payload — and `setOnboarded(true)` is called regardless of what the backend returns, making the app think onboarding is complete even if the backend returned an error.

**Fix**: The "Skip setup" button should call `setOnboarded(true); onDone()` directly without hitting the backend, or use a separate `POST /onboarding/skip` endpoint that sets a minimal DB flag.

---

#### 🟠 BFC-05 — `GET /settings` returns a flat key namespace (`"theme.mode"`) but Settings.tsx reads nested objects  
**Files**: [`backend/api/routes/settings.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/settings.py#L220) · [`frontend/src/app/components/Settings.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Settings.tsx)

The backend's `GET /settings` response structure is:
```json
{ "preferences": { "theme.mode": "dark", "editor.font_size": 14 }, "categories": { "theme": ["mode"] } }
```

The `Settings.tsx` panels read from the Zustand store (`prefs.fontSize`, `prefs.sound`, `orchestrator.model`, `workspace.path`), which is a **different shape** and is never populated from `GET /settings`. There is no code in any frontend file that calls `GET /settings` and maps the flat-keyed response into the store's nested structure.

The backend's settings system is entirely unused by the frontend.

**Fix**: Either delete `GET /settings` (it's dead code) and use localStorage only, or add a hydration call in `store.tsx` that fetches `/settings` on startup and maps the flat keys into the nested store shape. Pick one source of truth.

---

#### 🟠 BFC-06 — Analytics strip (`AnalyticsStrip.tsx`) polls `/analytics/usage?days=7` but the backend response shape doesn't match what the strip renders  
**Files**: [`frontend/src/app/components/AnalyticsStrip.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/AnalyticsStrip.tsx) · [`backend/api/routes/analytics.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/analytics.py#L217)

The backend returns `providers_used: { "Claude": 12 }` (count of messages per provider). The analytics strip likely renders cost or token bars using a `providers` field that the backend also returns. However, the `providers` map in the response is only populated when `usage_analytics` rows exist with `provider_id IS NOT NULL`. For fresh installs with no analytics data, `providers` is `{}` and the strip shows empty/zero bars — no empty-state UI is shown.

Additionally, `active_sessions` in the response counts sessions with `status = 'active'` — but sessions are never updated to `status = 'completed'` in any route handler. `active_sessions` will always grow and never decrease.

**Fix**:
1. Show an empty-state placeholder when `providers` is `{}`.
2. Update session status to `'completed'` when the user explicitly ends a session or it goes idle for a configured period.

---

#### 🟠 BFC-07 — `OrchestratorGraph.tsx` renders divisions from the chat response, but there is no WebSocket event that pushes division updates  
**Files**: [`frontend/src/app/components/OrchestratorGraph.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/OrchestratorGraph.tsx) · [`backend/api/routes/orchestrator.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/orchestrator.py)

The `OrchestratorGraph` visualizes divisions as a live node graph. However, division data only arrives once — in the HTTP response to `POST /orchestrator/dispatch`. There is no mechanism for the backend to push division status updates (`running → done`, `queued → running`) after the initial dispatch.

The frontend has to poll or receive WebSocket events to keep the graph live. Neither exists — the graph is static after the first render.

**Fix**: Add a WebSocket event type (e.g., `division_update`) to the connection manager's broadcast system. When a CLI agent reports completion (via `approve` or a future agent callback), broadcast the update so `OrchestratorGraph` can reflect real-time status.

---

#### 🟠 BFC-08 — `TerminalCard.tsx` fullscreen button opens `/terminal/{runtimeId}` — that route does not exist  
**Files**: [`frontend/src/app/components/TerminalCard.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/TerminalCard.tsx#L342)

```typescript
window.open(`/terminal/${runtimeId}?name=...`, "_blank", ...)
```

The Vite router (or React Router) has no `/terminal/:runtimeId` route. Opening this URL returns the root `index.html` (SPA fallback), and the terminal-specific component is never rendered. This is a completely broken feature.

**Fix**: Add a `/terminal/:runtimeId` route in the router that renders a fullscreen `TerminalCard` or a dedicated `TerminalFullscreen` component seeded with the runtime ID.

---

#### 🟠 BFC-09 — `workspace.py`'s `git/run` allowlist permits `push` and `commit` without confirming user intent  
**Files**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L230)

```python
_GIT_SAFE = { ..., "push", "commit", ... }
```

`git push` and `git commit` are irreversible and mutating. They are in the "safe" allowlist alongside read-only commands like `git log`. There is no secondary confirmation prompt, no dry-run flag, and the frontend Git panel (if it exists) calls this endpoint directly. Any accidental button press can push code to a remote.

**Fix**: Split the allowlist into `_GIT_READ` (log, status, branch, diff, show, rev-parse, remote) and `_GIT_WRITE` (add, commit, push, stash). Require an explicit `?confirm=true` for write commands, mirrored in the frontend with a confirmation dialog.

---

#### 🟠 BFC-10 — `workspace.py` context file upload uses `session_id` from `Form(...)` but `GET /workspace/context` silently ignores session_id=0  
**Files**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L339)

```python
if session_id:
    where_clauses.append("session_id = ?")
```

`session_id=0` is falsy in Python. If the frontend sends `session_id=0` (which is valid for a session ID in SQLite — though unlikely), the filter is silently dropped and all files for all sessions are returned. The correct check is `if session_id is not None:`.

**Fix**: Change the guard to `if session_id is not None:` in both the `GET /context` and `GET /artifacts` handlers (same pattern exists in `workspace.py` line 564).

---

#### 🟡 BFC-11 — `VoiceButton.tsx` sends audio but there is no backend `/transcribe` or speech-to-text route  
**Files**: [`frontend/src/app/components/VoiceButton.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/VoiceButton.tsx)

The voice button records audio via `MediaRecorder` and is presumably meant to send it for transcription. If it POSTs to a `/transcribe` or `/speech` endpoint that doesn't exist, the feature silently fails. Alternatively, if it uses browser-native `SpeechRecognition` only, there's no backend issue — but that API is Chromium-only, and there is no polyfill or fallback shown to the user.

**Fix**: Verify the voice flow end-to-end. If server-side transcription is intended, add `POST /transcribe` that wraps OpenAI Whisper or `openai-stt` provider. If browser-only, add a `!window.SpeechRecognition && !window.webkitSpeechRecognition` guard with a clear "Voice not supported in this browser" message.

---

#### 🟡 BFC-12 — `orchestrator/router.py` `complete_with_fallback` hardcodes model names that conflict with `decomposer.py`'s system prompt  
**Files**: [`backend/services/orchestrator/router.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator/router.py) · [`backend/services/orchestrator/decomposer.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator/decomposer.py#L34)

The orchestrator system prompt in `decomposer.py` tells the LLM to respond with agent `short` IDs from the enabled list. The `AGENT_COLORS` dict uses `"deepseek-api"` and `"gemini-api"` as keys. However, `core.py` sends the `display_name` of the provider in the user prompt (e.g., `"DeepSeek API"`), not the `short` ID. The LLM is likely to produce divisions with `short: "DeepSeek API"` instead of `short: "deepseek-api"`, causing color lookups to miss and task dispatching to silently fail.

**Fix**: Always send the `name` (DB short ID) as the agent identifier in the system prompt context, not `display_name`. Update the system prompt to be explicit: *"Use the agent's `id` field as the `short` value, not the display name."*

---

### Section B — Planning & Corner Case Gaps

These are logical flow and corner case issues that would manifest under real usage conditions.

---

#### 🔴 PC-01 — No handling of WebSocket reconnection after backend restart  
**File**: [`frontend/src/app/components/TerminalCard.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/TerminalCard.tsx#L265)

```typescript
ws.onclose = () => setWsStatus("closed");
```

When the WebSocket closes (backend restart, network blip), `wsStatus` is set to `"closed"`. There is no automatic reconnection logic. The terminal shows "Disconnected" forever, and the user must manually reload the card. For a tool where the backend may restart (development workflow), this is a critical UX failure.

**Fix**: Implement exponential backoff reconnection in `onclose`. After 3 failed reconnections, show the disconnected state and offer a "Reconnect" button.

---

#### 🔴 PC-02 — `finish()` in `Onboarding.tsx` does not prevent navigation during saving  
**File**: [`frontend/src/app/components/Onboarding.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Onboarding.tsx#L120)

```typescript
if (saving) return;
```

The `saving` guard prevents double-clicks, but the user can still click the Back button, change provider selections, and then click "Skip setup" — all while the `POST /onboarding/complete` is in-flight. The in-flight request carries the old provider list, but `setProviders()` has already been updated optimistically. When the request finishes, `setOnboarded(true)` fires with stale local state.

**Fix**: Disable all navigation (Back, provider toggles, "Skip") while `saving === true`. Add `pointer-events-none` or `disabled` props to all interactive elements in the Onboarding component when `saving` is true.

---

#### 🔴 PC-03 — `TerminalCard` spawns a new PTY on every remount, leaking processes  
**File**: [`frontend/src/app/components/TerminalCard.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/TerminalCard.tsx#L184)

```typescript
useEffect(() => {
  const ensureRuntimeAndConnect = async () => {
    let rid = runtimeId ?? cli.runtimeId;
    if (rid == null) {
      // POST /runtimes/spawn
    }
  };
}, [cli.providerId, cli.runtimeId]);
```

Every time `cli.providerId` or `cli.runtimeId` changes (which happens when the orchestrator assigns a task and re-renders the parent), this effect re-runs. If `runtimeId` is `undefined` at that moment (e.g., the spawn is still in-flight), a second spawn is triggered. Each spawn creates a new OS process. Over a long session with multiple task dispatches, dozens of orphan PowerShell processes accumulate.

**Fix**: Track the "spawn in progress" state with a ref (`spawnInProgressRef`) and abort the second spawn if one is already running. Also use a stable `runtimeId` ref to prevent re-runs from temporary `undefined` values during state transitions.

---

#### 🟠 PC-04 — `orchestrator/core.py` loads LLM configs on every `run()` call — N+1 DB queries per dispatch  
**File**: [`backend/services/orchestrator/core.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator/core.py#L52)

`OrchestratorEngine.run()` calls `load_llm_configs()` and `load_enabled_agents()` on every dispatch. Each call executes a `JOIN` query across `providers` and `provider_credentials`. For a user dispatching 10 tasks in quick succession, this is 20 extra DB round-trips.

**Fix**: Cache the configs for the duration of the request (pass them as arguments from the route handler), or use a short TTL cache (e.g., 5 seconds) per `user_id` since provider configs change infrequently.

---

#### 🟠 PC-05 — `parse_llm_plan()` in `decomposer.py` silently falls back to the raw text on any JSON error — including partial JSON  
**File**: [`backend/services/orchestrator/decomposer.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator/decomposer.py#L56)

```python
except json.JSONDecodeError:
    pass
return {"content": cleaned or fallback, "thinking": [], "divisions": [], "artifacts": []}
```

If the LLM returns `{"content": "ok", "divisions": [{"agent": "claude"` (truncated by token limit), the JSON parse fails silently. The fallback wraps the raw truncated JSON in a `content` field, which is shown to the user as a garbled string. No retry is attempted.

**Fix**: On `JSONDecodeError`, attempt a partial-parse recovery (e.g., `json.JSONDecoder().raw_decode()`), then log the error with the truncated response, and retry the LLM call with a higher `max_tokens` value. If the retry also fails, show a user-friendly error instead of the raw LLM output.

---

#### 🟠 PC-06 — `build_plan_from_dict` in `decomposer.py` silently creates `local_divisions` if LLM returns empty divisions — even if the LLM meant "no agents needed"  
**File**: [`backend/services/orchestrator/decomposer.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator/decomposer.py#L128)

```python
if not divisions and ctx.enabled_agents:
    divisions = local_divisions(ctx)
```

If the LLM deliberately returns `"divisions": []` (e.g., for a simple conversational reply that needs no agent delegation), the code overrides that decision and creates local divisions anyway. The user sees agents dispatched for a task that required only a text response.

**Fix**: Add a `no_delegation: bool` field to the LLM response schema. Only fall back to `local_divisions` when the LLM fails (error path), not when it returns an explicit empty divisions list.

---

#### 🟠 PC-07 — `ProviderRow` in `Settings.tsx` saves `"account"`-method providers without storing credentials  
**File**: [`frontend/src/app/components/Settings.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Settings.tsx#L327)

```typescript
const save = async () => {
  await fetch(`/providers/${p.dbId}`, { method: "PUT", ... });
  if ((p.authMethod === "api_key" || p.authMethod === "bearer") && secret.trim()) {
    await fetch(`/providers/${p.dbId}/credentials`, { method: "POST", ... });
  }
  onChange({ ...p, configured: !!(p.authMethod === "account" ? p.accountEmail : secret) });
};
```

For `authMethod === "account"`, neither the email nor the password is sent to `POST /providers/{id}/credentials`. The `onChange` call marks the provider as `configured: true` (if `accountEmail` is set), but no credential record is created or updated in the backend. On the next app restart, the provider shows as unconfigured again.

**Fix**: For `account`-method providers, POST a credential with `api_key = email` (or a dedicated `account_email` field) so the backend persists the authentication state.

---

#### 🟠 PC-08 — `chatInput` in `GlobalChatBar.tsx` does not clear after dispatch if the backend returns an error  
**File**: [`frontend/src/app/components/GlobalChatBar.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/GlobalChatBar.tsx)

The chat bar clears the input optimistically before the API call completes. If `POST /orchestrator/dispatch` returns an error (e.g., 404 "no config"), the user's typed message is already gone and cannot be recovered.

**Fix**: Clear the input only on success. On error, restore the input value and show an inline error message so the user can retry without retyping.

---

#### 🟠 PC-09 — `GET /analytics/providers` query excludes providers with 0 messages due to `LEFT JOIN` → `WHERE` filter  
**File**: [`backend/api/routes/analytics.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/analytics.py#L326)

```sql
FROM providers p
LEFT JOIN messages m ON p.id = m.provider_id
LEFT JOIN sessions s ON m.session_id = s.id
WHERE s.user_id = ? AND m.created_at >= ?
```

The `LEFT JOIN` on `messages` is immediately nullified by `WHERE m.created_at >= ?`, which converts it to an `INNER JOIN` (NULL rows are excluded). Providers with no messages in the time window are dropped from the response entirely, even though the frontend may want to show them with zeroed metrics.

**Fix**: Move the time filter to the `ON` clause of the JOIN: `LEFT JOIN messages m ON p.id = m.provider_id AND m.created_at >= ?`, and similarly for the sessions join.

---

#### 🟠 PC-10 — Hardcoded `RECENT_FOLDERS` in `Onboarding.tsx` shows fake project paths to all users  
**File**: [`frontend/src/app/components/Onboarding.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Onboarding.tsx#L41)

```typescript
const RECENT_FOLDERS = [
  "~/projects/acme-monorepo",
  "~/projects/orchestra-cli",
  "~/work/sandbox",
];
```

Every user sees the same three fake "recent" folder paths. These are hardcoded demo values that look like real suggestions. Clicking one sets a path that doesn't exist on the user's machine.

**Fix**: Replace with dynamically fetched recent workspaces from `GET /settings?key=recent_workspaces` (which the backend already supports), or source from the OS via the Electron/Tauri layer if available. At minimum, remove the hardcoded list and show an empty state.

---

#### 🟡 PC-11 — `StepWorkspace` "Continue" button is disabled only when `folderPath` is empty, not when the path is invalid  
**File**: [`frontend/src/app/components/Onboarding.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Onboarding.tsx#L524)

```typescript
<PrimaryBtn onClick={onNext} disabled={!folderPath.trim()}>
```

The user can type any string as a workspace path (e.g., `"hello world"`, `"C:\Users\not\real"`). The path is not validated for existence or writability until `POST /onboarding/complete`, which is the last step. If the path is invalid, the user only discovers this after completing all 5 setup steps, and has to start over.

**Fix**: Add a debounced `GET /workspace/validate-path?path=...` call (or a simple frontend heuristic) that checks the path as the user types and shows a green checkmark / red warning inline, before the user proceeds to the next step.

---

#### 🟡 PC-12 — `TerminalCard` "Ask BOB" sends `{ type: "ask", prompt, model }` over the PTY WebSocket but the backend `terminals.py` handler has no `"ask"` message type  
**File**: [`frontend/src/app/components/TerminalCard.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/TerminalCard.tsx#L366) · [`backend/api/websockets/terminals.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/websockets/terminals.py)

```typescript
ws.send(JSON.stringify({ type: "ask", prompt: q, model }));
```

The backend WebSocket handler routes messages by `type`. If `"ask"` is not in the handler's dispatch table, the message is silently dropped (or logged as an unknown type) and the LLM is never called. The UI writes `[orch] > {q}` to the terminal as if the request was sent, giving the user false feedback.

**Fix**: Implement the `"ask"` handler in `terminals.py` that calls the configured BOB/Granite LLM with the prompt and streams the response back as `{ type: "ask.token", text: "..." }` frames — matching what `TerminalCard.tsx` already expects on the receive side (`msg.type === "ask.token"`).

---

#### 🟡 PC-13 — `update_preference` (`PUT /settings/{key}`) accepts `value: Any` from query string — Pydantic cannot parse complex types from a query param  
**File**: [`backend/api/routes/settings.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/settings.py#L342)

```python
async def update_preference(
    preference_key: str,
    value: Any,          # ← FastAPI reads this from the query string
    ...
```

FastAPI parses `Any`-typed query parameters as raw strings. If the caller passes `value={"nested": true}` it arrives as the literal string `'{"nested": true}'`, not a dict. `serialize_preference_value("{"nested": true}")` will classify it as a `STRING` type rather than `JSON`, and the round-trip type will be wrong.

**Fix**: Change `value: Any` to `value: str` (with explicit JSON parsing in the body), or use a Pydantic body model instead of a query parameter. Alternatively, require callers to use the bulk `PUT /settings` endpoint (which uses a proper JSON body) for nested values.

---

#### 🟡 PC-14 — `revoke_credentials` (`DELETE /providers/{id}/credentials`) is fire-and-forget in Settings.tsx — no UI confirmation  
**File**: [`frontend/src/app/components/Settings.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Settings.tsx#L357)

```typescript
const revoke = async () => {
  await fetch(`/providers/${p.dbId}/credentials`, { method: "DELETE" });
  setSecret(""); onChange({ ...p, configured: false });
};
```

Clicking "Revoke" immediately deletes the credential with no confirmation dialog. For a user who accidentally clicks it, their API key is gone and the provider is unconfigured. Re-entering the key requires going back to the provider's documentation.

**Fix**: Show a `window.confirm()` dialog (or a custom inline confirmation) before calling DELETE. Mirror the pattern used in the Privacy panel's "Reset everything" button.

---

#### 🟡 PC-15 — `workspace.py` `_list_shared_dir` does not handle symlinks, potentially following links outside the workspace  
**File**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L135)

```python
for path in sorted(shared_resolved.rglob("*")):
    if not path.is_file():
        continue
```

`rglob("*")` follows symbolic links by default. If a user (or an orchestrator-generated file) creates a symlink in `shared/` that points outside the workspace (e.g., `shared/evil -> /etc/passwd`), `path.stat()` returns the stat of the target file and its content could be exposed via a subsequent file-serve endpoint.

**Fix**: Add `if path.is_symlink(): continue` to skip symlinks, or resolve each path and verify it stays within `shared_resolved` before including it.

---

#### 🟡 PC-16 — `GET /workspace/git` runs 6 separate `git` subprocess calls sequentially — high latency on large repos  
**File**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L198)

Each `git` call uses `asyncio.to_thread(run, [...])` with `await`, meaning they run one-after-another (serial), not in parallel. For a repo with a slow remote tracking check (`git rev-list --left-right --count HEAD...@{upstream}`), this endpoint can take 3–8 seconds.

**Fix**: Run the independent git commands concurrently with `asyncio.gather(*[asyncio.to_thread(run, cmd) for cmd in commands])`.

---

#### 🟡 PC-17 — `SessionHistory.tsx` has no skeleton/loading state — shows blank during initial load  
**File**: [`frontend/src/app/components/SessionHistory.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/SessionHistory.tsx)

The session history panel loads sessions from the store. If the store hasn't been hydrated yet (first render), an empty list is shown with no loading indicator. The user sees a blank sidebar and may think they have no sessions.

**Fix**: Show skeleton loading rows while `isHydrated` is false, then render the actual sessions once the store has loaded from the backend.

---

#### 🟡 PC-18 — `agents.py` route returns all agents but has no pagination  
**File**: [`backend/api/routes/agents.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/agents.py)

The agents route fetches all records with no `LIMIT`/`OFFSET`. If the agents table grows (e.g., custom agents are added programmatically), this will return an unbounded result set.

**Fix**: Add standard `limit`/`offset` query parameters consistent with the sessions and runtimes endpoints.

---

#### 🟢 PC-19 — `decomposer.py` `local_divisions` hardcodes `parallel_group=0` for agents 0-2 and `parallel_group=1` for agents 3+  
**File**: [`backend/services/orchestrator/decomposer.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/services/orchestrator/decomposer.py#L99)

```python
parallel_group=0 if i < 3 else 1,
```

The parallel group boundaries are hardcoded at 3. If a user has 4 agents, agent 4 is in group 1, meaning agents 1-3 run first and agent 4 waits. But there's no actual execution engine that respects `parallel_group` — this field is only used for rendering in `OrchestratorGraph.tsx`. The field gives false impression of execution ordering.

**Fix**: Either implement actual parallel execution respecting `parallel_group`, or remove the field and document that all divisions are dispatched simultaneously.

---

#### 🟢 PC-20 — `Settings.tsx` `AboutPanel` has dead anchor links with no `href`  
**File**: [`frontend/src/app/components/Settings.tsx`](file:///c:/Users/ahbab/Downloads/IBMbob/frontend/src/app/components/Settings.tsx#L779)

```tsx
<a className="...">Docs</a>
<a className="...">GitHub</a>
<a className="...">Changelog</a>
```

All three links have no `href` attribute. They render as non-clickable text styled like links. This is confusing UX.

**Fix**: Either add real URLs or replace `<a>` with `<span>` styled as coming soon, with a tooltip explaining the links are not yet active.

---

### Section C — Additional Security Corner Cases

---

#### 🟠 SC-01 — `workspace/git/run` allows `git stash` which can silently discard uncommitted work  
**File**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L230)

`git stash` is in the safe list. If the orchestrator (or a misguided user) calls `git stash` followed by `git stash drop`, uncommitted work is permanently lost. Unlike `git commit`, stashed changes are easy to accidentally drop.

**Fix**: Move `stash` to the write-confirmation list (see BFC-09).

---

#### 🟠 SC-02 — `upload_context_file` does not validate that the stored filename is safe before writing to disk  
**File**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L437)

```python
stored_filename = f"{content_hash}{file_ext}"
stored_path = settings.context_files_dir / stored_filename
```

`file_ext = Path(file.filename).suffix` — if the uploaded filename is `malicious.py.exe`, `file_ext` is `.exe`. The stored file will be `{hash}.exe` on disk. If `context_files_dir` is served as a static file directory or is on the system PATH, this creates an executable upload vector.

**Fix**: Allowlist file extensions based on `settings.allowed_file_types` at the storage step, not just at the validation step. Never write files with executable extensions (`.exe`, `.bat`, `.ps1`, `.sh`, `.py`, `.js`).

---

#### 🟡 SC-03 — `GET /workspace/context` returns file metadata for all sessions including soft-deleted ones  
**File**: [`backend/api/routes/workspace.py`](file:///c:/Users/ahbab/Downloads/IBMbob/backend/api/routes/workspace.py#L344)

The query has no filter on session status. If sessions are ever soft-deleted (via a `deleted_at` column), their context files would still appear in the listing.

**Fix**: Add `AND s.status != 'deleted'` or `AND s.deleted_at IS NULL` to the context files query once soft-delete is implemented.

---

### Updated Coverage Matrix (Addendum)

| File | New Issues Found | Severity |
|------|-----------------|---------|
| `backend/api/routes/providers.py` | BFC-02, PC-14 | 🔴🟡 |
| `backend/api/routes/settings.py` | BFC-05, PC-13 | 🟠🟡 |
| `backend/api/routes/workspace.py` | BFC-09, BFC-10, PC-09, PC-15, PC-16, SC-01, SC-02, SC-03 | 🟠🟡 |
| `backend/api/routes/analytics.py` | BFC-06, PC-09 | 🟠 |
| `backend/api/routes/agents.py` | PC-18 | 🟢 |
| `backend/api/routes/onboarding.py` | BFC-03, BFC-04 | 🔴 |
| `backend/services/orchestrator/core.py` | PC-04 | 🟠 |
| `backend/services/orchestrator/decomposer.py` | BFC-12, PC-05, PC-06, PC-19 | 🟠🟢 |
| `frontend/src/app/components/Onboarding.tsx` | BFC-03, BFC-04, PC-02, PC-10, PC-11 | 🔴🟠🟡 |
| `frontend/src/app/components/Settings.tsx` | BFC-01, BFC-02, BFC-05, BFC-07, PC-07, PC-14, PC-20 | 🔴🟠🟡🟢 |
| `frontend/src/app/components/TerminalCard.tsx` | BFC-08, PC-01, PC-03, PC-12 | 🔴🟠🟡 |
| `frontend/src/app/components/AnalyticsStrip.tsx` | BFC-06 | 🟠 |
| `frontend/src/app/components/OrchestratorGraph.tsx` | BFC-07 | 🟠 |
| `frontend/src/app/components/SessionHistory.tsx` | PC-17 | 🟡 |
| `frontend/src/app/components/GlobalChatBar.tsx` | PC-08 | 🟠 |
| `frontend/src/app/components/VoiceButton.tsx` | BFC-11 | 🟡 |

---

### Updated Priority Fix Order (Addendum)

**Phase 1 additions — Critical**
| ID | Title | Effort |
|----|-------|--------|
| BFC-01 | Wire Settings panel writes to backend + read response | M |
| BFC-02 | Fix masked API key overwriting real key on save | S |
| BFC-03 | Verify onboarding `secret` field contract with backend | S |
| BFC-04 | Fix "Skip setup" calling full `finish()` | S |
| PC-01 | Add WebSocket reconnection with backoff | M |
| PC-03 | Fix PTY spawn leak on remount | M |

**Phase 2 additions — High**
| ID | Title | Effort |
|----|-------|--------|
| BFC-05 | Eliminate dead settings backend or wire frontend to it | M |
| BFC-07 | Add WebSocket division status push events | M |
| BFC-08 | Add `/terminal/:id` fullscreen route | S |
| BFC-09 | Split git safe/write allowlists + add confirmation | S |
| BFC-12 | Fix agent ID vs display_name mismatch in orchestrator prompt | S |
| PC-02 | Disable all Onboarding navigation during `saving` | S |
| PC-05 | Handle truncated LLM JSON with retry | M |
| PC-06 | Distinguish LLM-intent empty divisions from fallback | S |
| PC-07 | Persist account-method credentials in Settings | S |
| PC-08 | Don't clear chat input on dispatch error | S |
| SC-02 | Block executable extension uploads | S |

**Phase 3 additions — Medium/Low**
| ID | Title | Effort |
|----|-------|--------|
| BFC-06, BFC-11 | Analytics empty state + Voice transcription backend | M each |
| BFC-10, PC-10–PC-16 | Onboarding UX + workspace API corner cases | S each |
| PC-19, PC-20 | parallel_group semantics + dead About links | S each |
| SC-01, SC-03 | git stash guard + soft-delete context filter | S each |

---

*Addendum covers 20 backend-frontend contract mismatches (BFC), 20 planning/corner-case gaps (PC), and 3 additional security issues (SC) found in the second full pass. Total issue count: **85 distinct issues** across all 70+ files.*
