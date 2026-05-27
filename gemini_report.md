# System Audit Report - IBMbob (Gemini)

This report details a thorough step-by-step system audit of the IBMbob codebase to identify bugs, architectural issues, and missing corner-case logic. The findings have been classified by severity and location.

---

## 1. Major Issues

### Missing TypeScript Configuration in Frontend
- **Location**: `frontend/package.json` and `downloader_page/package.json`
- **Issue**: Both the `frontend` and `downloader_page` directories contain TypeScript and TSX files (along with `vite-env.d.ts` and `tsconfig` components), yet neither includes `typescript` as a dependency in `devDependencies`.
- **Impact**: While Vite (via `esbuild`) will compile `.ts`/`.tsx` files to JavaScript, it does so **without performing any type checking**. This leads to silent compilation of invalid TypeScript, entirely defeating the purpose of using the language.
- **Recommended Fix**: Run `npm install -D typescript @types/react @types/react-dom` in both directories. Ensure that a proper `tsconfig.json` exists with `strict: true` and that type checking is integrated into the build step (e.g., `"build": "tsc -b && vite build"`).

---

## 2. Code-Level Bugs and Anomalies (Backend)

### 2.1. Undefined Type Annotations (Static Typing Failure)
- **Location**: `backend/services/orchestrator/decomposer.py` (Line 109)
- **Issue**: The `Optional` type hint is used in a function signature (`provider_id: Optional[str] = None`), but it is never imported from the `typing` module.
- **Impact**: While `from __future__ import annotations` prevents a `NameError` crash at runtime, any static type checker (like mypy, pyright) or IDE will throw an undefined name error.
- **Recommended Fix**: Add `from typing import Optional` to the imports at the top of the file.

### 2.2. Improper Error Handling (Bare `except:`)
- **Location**:
  - `backend/services/orchestrator_service.py` (Line 416)
  - `backend/services/session_service.py` (Line 360)
- **Issue**: The code uses bare `except:` blocks.
- **Impact**: Bare `except:` catches *everything*, including `KeyboardInterrupt` and `SystemExit`. This makes it impossible to cleanly terminate the process with Ctrl+C and masks critical system errors (like MemoryError).
- **Recommended Fix**: Change `except:` to `except Exception as e:` and optionally log the exception for better traceability.

### 2.3. Unused Assignment
- **Location**: `backend/api/routes/orchestrator.py` (Line 384)
- **Issue**: The local variable `cursor` is assigned the result of `await db.execute(...)` but is never read or used subsequently in that function block.
- **Impact**: Creates clutter, potential memory inefficiency, and triggers linter warnings (Ruff F841).
- **Recommended Fix**: Remove the `cursor = ` assignment or utilize it if `.lastrowid` or `.rowcount` needs to be checked.

### 2.4. Ambiguous Variable Naming
- **Location**: `backend/api/routes/workspace.py` (Line 225)
- **Issue**: The variable `l` is used in a list comprehension (`[l for l in porc.splitlines() if l.strip()]`).
- **Impact**: The lowercase letter `l` is visually ambiguous and easily confused with the number `1` or uppercase `I` (Ruff E741).
- **Recommended Fix**: Rename the variable to a more descriptive name, such as `line`.

---

## 3. Maintenance and Code Quality (Backend)

### 3.1. Massive Orphaned Legacy Service Tier
- **Location**: `backend/services/` (specifically `provider_service.py`, `workspace_service.py`, `runtime_service.py`, `orchestrator_service.py`, `analytics_service.py`, `session_service.py`, `encryption_service.py`)
- **Issue**: The entire object-oriented, synchronous `sqlite3`-based service tier was completely abandoned during a migration to asynchronous FastAPI routes (which use `aiosqlite` directly). None of these `*Service` classes are instantiated or used by the active `api/routes/` endpoints. 
- **Impact**: Thousands of lines of untested, synchronous legacy code are sitting in the active codebase causing massive architectural bloat and confusion for developers trying to trace execution logic.
- **Recommended Fix**: Safely delete these orphaned `*_service.py` files. Ensure that any residual utility functions (if actually used) are migrated to `backend/utils/`.

### 3.2. Extensive Unused Imports
- **Location**: Multiple backend files (e.g., `agents.py`, `analytics.py`, `providers.py`, `session_service.py`).
- **Issue**: There are approximately 90+ linting issues related to unused imports (Ruff F401) and module-level imports placed below definitions (Ruff E402). For example: `fastapi.HTTPException` in `agents.py` and `cryptography.fernet.Fernet` in `providers.py` are imported but not used.
- **Impact**: Increases memory footprint slightly, complicates the reading of dependencies, and decreases overall code cleanliness.
- **Recommended Fix**: Run a static analyzer auto-fix like `ruff check --fix ./backend` or `isort ./backend` to automatically remove unused imports and re-sort them to the top of the files.

---

## 4. Pending Features (TODOs)

During the audit, the following incomplete implementations (TODOs) were identified which represent architectural gaps:

1. **Missing Authentication Implementation**:
   - **Location**: `backend/api/dependencies.py` (Line 80)
   - **Note**: "TODO: Implement proper authentication". Currently, the function `get_current_user_id` blindly returns `1` or the provided `user_id`.
   - **Recommended Fix**: Implement a JWT or session-based authentication flow securely using FastAPI dependencies.

2. **Missing Cost Estimation**:
   - **Location**: `backend/api/routes/orchestrator.py` (Line 203)
   - **Note**: "TODO: Implement cost estimation". The `DispatchResponse` currently returns `estimated_cost=None`.
   - **Recommended Fix**: Integrate the tokenizer tracking from the provider services and map tokens to pricing models to return accurate cost metrics.

---

## 5. Architectural / Corner Case Considerations

### 5.1. Database Initialization Paths
- **Location**: `backend/database/init_db.py`
- **Issue**: The initialization logic strongly enforces that the database resides under a directory named `data/`. If an admin attempts to mount or override the database URL using an absolute path that does not contain a folder exactly named `data`, it throws a `ValueError` explicitly refusing to create it.
- **Impact**: This breaks flexibility in containerized or highly customized environments where an orchestrator admin might prefer an arbitrary mount point (e.g., `/var/lib/ibmbob/bob.db`).
- **Recommended Fix**: Relax the strict directory name constraint, and simply ensure the parent directory has appropriate write permissions instead of relying on the strict "data" folder name match.

### 5.2 JSON Serialization Timezone Issues
- **Location**: `backend/main.py`
- **Issue**: A custom `_error_json` handler attempts to dump Pydantic objects using `model_dump(mode="json")` and passes it through `json.dumps()` before `json.loads()`. While effective, it's slightly inefficient and implies past struggles with native FastAPI serialization.
- **Recommended Fix**: Trust `fastapi.responses.JSONResponse(content=payload.model_dump(mode="json"))` directly, as Pydantic's JSON mode safely stringifies `datetime` objects without needing the `json.dumps` -> `json.loads` round-trip hack.

---

## 6. Integration & Connection Gaps (Backend-Frontend)

### 6.1. Unhandled Promise Rejections in WebSocket Broadcasts
- **Location**: `backend/api/websockets/terminals.py` (Line 73)
- **Issue**: The `on_chunk` callback wraps `websocket.send_text(...)` in `asyncio.ensure_future(...)` without an attached error handler or `try/except` block inside the coroutine. 
- **Impact**: When a client abruptly disconnects from the terminal, any pending or actively writing output chunk will trigger a `WebSocketDisconnect` inside that orphaned task. Python's `asyncio` event loop will catch it, log an "Task exception was never retrieved" warning, and spam the backend logs during normal disconnections.
- **Recommended Fix**: Wrap the `send_text` call inside a mini-coroutine that explicitly catches and suppresses `WebSocketDisconnect` and `RuntimeError`.

### 6.2. Fetch Cancellation Corner Cases (Frontend)
- **Location**: `frontend/src/app/lib/api.ts` (Line 41)
- **Issue**: The `apiFetch` wrapper utilizes `AbortSignal.timeout(timeoutMs)` to abandon hung backend responses. However, if the user explicitly triggers an abort via a navigation event or component unmount (by passing their own signal inside the `init` config), the wrapper blindly favors `AbortSignal.timeout()` or the `rest.signal` exclusively, it doesn't gracefully combine them using `AbortSignal.any()`.
- **Impact**: If a component passes a cancellation signal, the custom timeout behavior from `apiFetch` is bypassed, meaning long requests initiated right before a component unmount could theoretically hang if the component's signal is poorly formed.
- **Recommended Fix**: Use `AbortSignal.any([rest.signal, AbortSignal.timeout(timeoutMs)])` if both exist to ensure timeout resilience is never dropped.

### 6.3. Concurrency Edge Cases in PTY Sessions
- **Location**: `backend/services/pty_service.py`
- **Issue**: The `PtyManager` allows creating interactive PowerShell instances via `pywinpty` for the agents. When reading the stream in the background thread, it polls using non-blocking I/O inside a busy loop with a hardcoded `time.sleep(0.02)`. Furthermore, if multiple frontend tabs connect to the *same* runtime terminal, they all share one session, but there's no heartbeat timeout ensuring that an orphaned terminal (where all WebSockets closed) automatically tears down its child process.
- **Impact**: If the frontend crashes or is closed, the underlying PowerShell instances will live indefinitely in the backend memory and OS process tree, resulting in memory leaks over long up-times.
- **Recommended Fix**: Implement a reference counter (or connection array) in `PtySession` that counts active WebSocket connections. When the count drops to zero, initiate a 5-minute teardown timer to kill the PTY process automatically if no one reconnects.

---

## 7. Backend ↔ Frontend API Coverage Matrix

Legend: **Wired** = frontend calls endpoint · **Partial** = called but wrong payload/response handling · **Missing** = backend exists, no frontend · **Mock** = UI shows data without API

### 7.1 Orchestrator (`/api/orchestrator/*`)

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `POST /chat` | `App.tsx` | **Partial** | Sends `{session_id, message}` only — ignores `model_name`, `stream`, `context_files`, `provider_id`, `metadata` |
| `GET /config` | — | **Missing** | Settings writes prefs to `/api/settings` instead |
| `PUT /config` | — | **Missing** | Routing model/retries/timeout never persisted to `orchestrator_config` table |
| `POST /config/reset` | — | **Missing** | No UI reset orchestrator defaults |
| `POST /dispatch` | — | **Missing** | No "dispatch task" button wired; chat is only entry point |
| `GET /providers/health` | — | **Missing** | No health badges for Grok/Gemini/DeepSeek in Settings |

**Planning corner case:** User changes orchestrator model in Settings → chat still uses backend default/env because `model_name` is never sent (**GF-001**).

**Planning corner case:** User sets routing to `cheapest` in UI → backend `OrchestratorEngine` never reads `user_preferences`; only LLM priority in DB/env applies (**GF-002**).

### 7.2 Agents & A2A (`/api/agents/*`)

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET /agents` | — | **Missing** | Processes view builds agents from `/providers` + spawn, not discovery API |
| `POST /a2a/send` | — | **Missing** | No UI for agent-to-agent messages |
| `GET /a2a/inbox/{id}` | — | **Missing** | Terminals don't poll inbox |
| `GET /a2a/history` | — | **Missing** | No session A2A timeline in chat |

**Planning corner case:** Orchestrator returns `divisions[]` in chat metadata but never calls A2A — agents only get tasks if user manually reads divisions and types into PTY (**GF-003**).

### 7.3 MCP Tools (`/api/tools/*`)

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET /tools/mcp` | — | **Missing** | No tools panel in Settings |
| `POST /tools/mcp/{name}/invoke` | — | **Missing** | Orchestrator/terminals can't invoke MCP tools from UI |

### 7.4 Runtimes & WebSocket

| Endpoint / WS | Frontend | Status | Gap |
|---------------|----------|--------|-----|
| `GET /runtimes/live` | `App.tsx` | **Wired** | Used for active snapshot |
| `GET /runtimes/active` | — | **Missing** | Alias exists on backend; frontend uses `/live` only (OK) |
| `POST /runtimes/spawn` | `TerminalCard.tsx` | **Wired** | Spawns on every card mount |
| `DELETE /runtimes/{id}` | `TerminalCard.tsx` | **Partial** | Reload path; errors not surfaced |
| `POST .../pause\|resume` | `TerminalCard.tsx` | **Partial** | UI exists; state may desync from PTY |
| `POST .../approve` | `TerminalCard.tsx` | **Partial** | Approval UI never populated from WS |
| `GET /runtimes` (list) | — | **Missing** | No runtime history view |
| `GET /runtimes/{id}` (detail+logs) | — | **Missing** | No log viewer in UI |
| `WS /ws/terminals/{id}` | `TerminalCard.tsx` | **Partial** | Handles `output`, `ask.*`; ignores agent A2A delivery |

**WS message types (backend → frontend) not handled in UI:**

| Type | Handled? | Impact |
|------|----------|--------|
| `hello` | Partial | Connection ack not shown |
| `output` | Yes | Terminal output |
| `ask.token` / `ask.done` / `ask.error` | Yes | Ask orchestrator stream |
| `error` | Partial | Generic xterm red text |
| `status` | No | Agent state stuck at `running` |
| `permission` / approval prompts | No | Approve button never activates (**GF-004**) |

### 7.5 Sessions & Messages

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `POST /sessions` | — | **Missing** | Session created implicitly by chat only |
| `GET /sessions` | `Sidebar.tsx`, `App.tsx` | **Partial** | Sidebar maps incomplete fields; falls back to demo data |
| `GET /sessions/{id}` | — | **Missing** | No session detail panel |
| `GET /sessions/{id}/messages` | `App.tsx` | **Partial** | Loads on init for latest session only; switching sessions not wired |
| `PUT /sessions/{id}` | — | **Missing** | Can't rename/pause session from UI |
| `DELETE /sessions/{id}` | `SessionHistory.tsx` | **Partial** | May only clear local store — verify backend DELETE called |

**Corner case:** User opens app → loads messages for session id from `GET /sessions?limit=1` only. Creating new chat via dispatch doesn't refresh sidebar until 15s poll (**GF-005**).

**Corner case:** No UI to pick a past session from sidebar and load its messages into ChatView (**GF-006**).

### 7.6 Providers & Credentials

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET /providers` | `App.tsx`, `store.tsx` | **Wired** | `enabled_only=true` vs `false` used inconsistently |
| `PUT /providers/{id}` | `Settings.tsx` | **Wired** | Enables/disables globally |
| `POST/GET/DELETE .../credentials` | `Settings.tsx`, `Onboarding.tsx` | **Partial** | Masked key overwrite bug; onboarding uses same paths |
| Orchestrator LLM ids | `store.tsx` | **Mismatch** | UI has `grok` provider; backend orchestrator LLMs also `gemini-api`, `deepseek-api` — **not in DEFAULT_PROVIDERS** |

**Corner case:** User configures Gemini via Settings (`id: gemini` CLI) but orchestrator LLM is separate row `gemini-api` — two different provider records, one API key store (**GF-007**).

### 7.7 Workspace

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET /workspace/shared` | `App.tsx` | **Wired** | Processes view context |
| `GET /workspace/git` | `Sidebar.tsx`, `TopBar.tsx` | **Wired** | |
| `POST /workspace/git/run` | `Sidebar.tsx` | **Partial** | No `res.ok` check |
| `POST /workspace/context` | `GlobalChatBar.tsx` | **Partial** | Blocked until session exists |
| `GET /workspace/context` | — | **Missing** | Settings context tab uses mock `INITIAL_CTX` |
| `GET/POST /workspace/artifacts` | — | **Missing** | Chat shows artifact chips from chat metadata only; no artifact browser |

### 7.8 Analytics

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET /analytics/usage` | `App.tsx` | **Wired** | Powers quota display on terminal cards |
| `GET /analytics/events/recent` | `TopBar.tsx` | **Wired** | Notifications dropdown |
| `GET /analytics/routes` | — | **Missing** | `OrchestratorGraph` uses hardcoded mock logs |
| `GET /analytics/providers` | — | **Missing** | No provider comparison dashboard |
| `GET /analytics/sessions/{id}` | — | **Missing** | No per-session analytics in SessionHistory |
| `POST /analytics/events` | — | **Missing** | Frontend never tracks client events |

**Mock vs real:** `AnalyticsStrip.tsx` — CPU **45.2%** and tasks **38** are **hardcoded**, not from `/analytics/usage` (**GF-008**).

### 7.9 Settings & Onboarding

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET/PUT /settings` | `store.tsx` | **Wired** | Debounced sync; no error UI on failure |
| `GET /settings/cli-registry` | `store.tsx` | **Wired** | Merges install metadata |
| `POST /onboarding/complete` | `Onboarding.tsx` | **Wired** | Disables unselected providers including orchestrator LLMs |

### 7.10 Health

| Endpoint | Frontend | Status | Gap |
|----------|----------|--------|-----|
| `GET /health` | `Sidebar.tsx` via `healthCheckUrl()` | **Wired** | |
| `GET /api/health` | — | **Optional** | Backend exposes both; frontend uses `/health` (correct for Vite proxy) |

---

## 8. Enum & Schema Mismatches (Frontend ↔ Backend)

| Concept | Frontend (`store.tsx` / Settings) | Backend (`models.py` / DB) | Issue |
|---------|-----------------------------------|----------------------------|-------|
| Routing strategy | `specialty`, `cheapest`, `fastest`, `round_robin` | `auto`, `manual`, `least_cost`, `fastest`, `round_robin` | **`specialty` and `cheapest` have no backend equivalent** (**GF-009**) |
| Provider filter for terminals | `provider_type === "llm"` | CLI agents AND orchestrator LLMs both `llm` | Spawns PTYs for API providers (**GF-010**) |
| Orchestrator models UI | `grok-3`, `gemini-2.5-pro`, `deepseek-chat` | DB `default_model` per provider row | Not synced on chat unless `model_name` sent |
| Session status | `active`, `completed`, `failed` | `active`, `paused`, `completed`, `archived`, `failed` | `paused`/`archived` mapped incorrectly in Sidebar (**GF-011**) |
| Message roles in UI | `user`, `orchestrator` | `user`, `assistant`, `system`, … | Display works; ensure API returns match ChatView types |
| Provider ids | `claude`, `gemini`, `grok`, … | Same + `gemini-api`, `deepseek-api` | Orchestrator API providers absent from frontend defaults (**GF-007**) |

**Recommended fix:** Add shared OpenAPI-generated types or a `shared/api-schema.ts` consumed by both sides; map UI enums explicitly in one `routingStrategyToBackend()` helper.

---

## 9. End-to-End Planning Flow — Missing Connections

Intended flow vs what is actually connected:

```
User task → POST /orchestrator/chat → OrchestratorEngine (LLM plan)
    → divisions[] in response metadata
    → write divisions.md (backend ✓)
    → UI ChatView shows divisions (✓)
    → applyDivisionsToAgents() patches TerminalCard.task (Partial ✓)
    → CLIAgentAdapter.assign_task / A2A send (✗ NOT CONNECTED)
    → PTY receives task text via WS input (Manual ✓ if user clicks dispatch)
    → Agent output → aggregator → chat reply (✗ NOT CONNECTED)
    → MCP tools during planning (✗ NOT CONNECTED)
    → POST /orchestrator/dispatch for subtasks (✗ NOT CONNECTED)
```

### 9.1 Planning step gaps

| Step | Expected | Actual | ID |
|------|----------|--------|-----|
| Load chat history into LLM context | Prior messages inform plan | Only current message in `SharedContext` | **GF-012** |
| Attach context files to plan | `context_files` IDs in ChatRequest | Field ignored by chat route | **GF-013** |
| Stream plan to UI | SSE/chunked thinking | Single JSON response; `stream: true` default ignored | **GF-014** |
| Parallel task groups | `parallel_group` in TaskDivision | Set in local router only; UI doesn't visualize groups | **GF-015** |
| Re-route button | Re-call orchestrator with new strategy | `ChatView` button has no handler | **GF-016** |
| Watch processes | Navigate + highlight assigned agents | Button exists; may not scroll/focus terminal | **GF-017** |

### 9.2 Division → agent assignment gaps

| Scenario | Expected | Actual | ID |
|----------|----------|--------|-----|
| `division.short === "gemini"` but card id from provider name | Match and set task | Also matches `division.agent === cli.name` — fragile if display_name differs | **GF-018** |
| Division for disabled agent | Skip or warn | Division still shown; no terminal card | **GF-019** |
| Division for agent without PTY (501) | Show install hint | Spawn fails; generic error in xterm | **GF-020** |
| Multiple divisions same agent | Queue tasks | Last division wins in `applyDivisionsToAgents` | **GF-021** |

### 9.3 Post-plan execution gaps

| Scenario | Expected | Actual | ID |
|----------|----------|--------|-----|
| User clicks "Dispatch" on terminal card | Send task via WS `input` | Works if `cli.task` set | Partial |
| Auto-dispatch all divisions | Optional setting | Not implemented | **GF-022** |
| Agent completes → update division status `done` | WS or polling | Status stays `running` in UI | **GF-023** |
| Collect agent stdout into orchestrator summary | A2A or log API | Not implemented | **GF-024** |

---

## 10. Frontend Internal Wiring Gaps (No Backend Call)

| Component | Issue | Severity | Fix |
|-----------|-------|----------|-----|
| `OrchestratorGraph.tsx` | 100% mock data | High | Wire `GET /analytics/routes` + live PTY buffer |
| `AnalyticsStrip.tsx` | CPU/tasks hardcoded | High | Derive from `/analytics/usage` + runtime count |
| `SessionHistory.tsx` | Uses `useStore` local sessions; unclear if DELETE hits API | Medium | Wire `DELETE /sessions/{id}` |
| `ContextDropzone.tsx` (Settings) | `INITIAL_CTX` mock | Medium | `GET /workspace/shared` + upload |
| `CommandPalette.tsx` | Navigation only; no session/provider commands | Low | Add "New session", "Health check" actions |
| `react-router` in dependencies | Never used; `/terminal/:id` 404 | High | Add routes or remove dep |
| `ProcessesView.tsx` | Subtitle still IBM-era copy | Low | Update copy |
| `store.tsx` demo sessions | Shown when API returns [] | High | Empty state only |

---

## 11. Corner Cases & Failure Modes (Planning + Runtime)

### 11.1 Chat / orchestrator

| # | Trigger | Failure | Recommended handling |
|---|---------|---------|----------------------|
| CC-01 | All LLM keys missing | Local router plan; user may not understand why | Banner: "Configure Grok/Gemini/DeepSeek in Settings" |
| CC-02 | LLM returns invalid JSON | `parse_llm_plan` falls back to raw text; empty divisions | Show parse warning in thinking[] |
| CC-03 | LLM returns divisions for unknown agent ids | UI shows divisions; no matching terminal | Grey out + "enable agent in Settings" |
| CC-04 | Chat while backend down | `apiFetch` timeout → error message in chat | ✓ partially implemented |
| CC-05 | Double-click Dispatch | Duplicate user messages | Disable input while in-flight |
| CC-06 | Very long message | No max length in UI; backend may truncate LLM | Client-side warn >8k chars |
| CC-07 | `session_id` stale after DB reset | Inserts into missing session? | Backend should 404; frontend should clear id |

### 11.2 Provider / credentials

| # | Trigger | Failure | Recommended handling |
|---|---------|---------|----------------------|
| CC-08 | Save credentials with unchanged masked field | Sends `"***"` | Skip empty/masked values |
| CC-09 | `dbId` undefined before sync | Spawn with `provider_id: undefined` | Block spawn until providers hydrated |
| CC-10 | Toggle provider off in Settings | Global DB flag; other tabs still show until poll | Optimistic UI + rollback on error |
| CC-11 | Onboarding skip with no workspace path | May persist empty path | Validate path or use project root default |

### 11.3 Terminals / PTY

| # | Trigger | Failure | Recommended handling |
|---|---------|---------|----------------------|
| CC-12 | Non-Windows host | 501 on spawn | Hide Processes or show "PTY requires Windows" |
| CC-13 | 8 agents enabled | 8 simultaneous spawns | Respect `parallelism` from orchestrator config |
| CC-14 | HMR reload during dev | WS reconnect; duplicate onData handlers | Fix handler registration |
| CC-15 | Backend restart | runtime_ids invalid; WS fail | Detect 404 on spawn; auto-respawn |
| CC-16 | Two browser tabs same runtime | Shared PTY OK; input from both | Document or lock input |

### 11.4 Git / workspace

| # | Trigger | Failure | Recommended handling |
|---|---------|---------|----------------------|
| CC-17 | Backend offline | Git shows "waiting for backend" | ✓ improved |
| CC-18 | Not a git repo | Shows "not a git repo" | OK |
| CC-19 | `git push` via API | Executes on server workspace | Confirm dialog in UI |
| CC-20 | `shared/` empty | Context panel empty | Onboarding should seed skill.md |

### 11.5 State sync / hydration

| # | Trigger | Failure | Recommended handling |
|---|---------|---------|----------------------|
| CC-21 | localStorage `onboarded=true` but backend `ui.onboarded=false` | Flash wrong screen | Wait for hydration gate |
| CC-22 | Settings change on two tabs | Last write wins to `/settings` | ETag or version field |
| CC-23 | Provider poll clears cards on error | Empty Processes view | Keep stale data + banner |
| CC-24 | Voice partial transcript stale | Empty voice message | Use ref in VoiceButton |

---

## 12. Additional Code-Level Issues (Append)

### 12.1 Missing `typescript` in frontend devDependencies
- **Location:** `frontend/package.json` — no `typescript`, `@types/react`, `@types/react-dom`
- **Impact:** Vite/esbuild transpiles without typechecking; aligns with §1 Major Issues
- **Fix:** Add TS toolchain; `"build": "tsc -b && vite build"`

### 12.2 Missing `Optional` import in decomposer
- **Location:** `backend/services/orchestrator/decomposer.py:109`
- **Fix:** `from typing import Optional`

### 12.3 No `tsconfig.json` in frontend
- **Location:** `frontend/` root
- **Impact:** IDE strictness inconsistent; no path alias enforcement for `@/`
- **Fix:** Add `tsconfig.json` with `"strict": true`

### 12.4 Inconsistent fetch wrapper usage
- **Location:** Most components use raw `fetch(apiPath(...))` without timeout; only chat/onboarding/git use `apiFetch`
- **Impact:** Hung requests on sessions, providers, settings
- **Fix:** Standardize on `apiFetch` with per-route timeouts

### 12.5 `react-router` installed but unused
- **Location:** `frontend/package.json`, `TerminalCard` full-screen path
- **Impact:** Dead dependency; broken navigation
- **Fix:** Implement minimal router or remove package

### 12.6 Backend chat never loads prior messages for LLM
- **Location:** `backend/api/routes/orchestrator.py` + `SharedContext`
- **Impact:** Multi-turn planning incoherent
- **Fix:** Query `messages` for `session_id` before `engine.run()`

### 12.7 Frontend never calls `GET /orchestrator/providers/health`
- **Impact:** Settings cannot show Grok/Gemini/DeepSeek connectivity
- **Fix:** Health panel in Settings → Orchestrator tab

### 12.8 `gemini-api` / `deepseek-api` not in frontend provider list
- **Location:** `store.tsx` DEFAULT_PROVIDERS
- **Impact:** User cannot configure orchestrator LLM keys separately from CLI `gemini`/`deepseek`
- **Fix:** Add orchestrator provider section or clarify combined credentials

---

## 13. Recommended Wiring Priority (Frontend ↔ Backend)

When implementing fixes, wire in this order:

1. **GF-010 / CRIT-004** — Fix terminal provider filter (CLI only)
2. **GF-001 / GF-002 / GF-009** — Wire Settings ↔ `/orchestrator/config`; map routing enums; send `model_name` on chat
3. **GF-007 / GF-012** — Add orchestrator LLM providers to UI; load session history server-side
4. **GF-003 / GF-022** — Auto-dispatch divisions to PTY via WS after plan
5. **GF-008** — Replace mock AnalyticsStrip / OrchestratorGraph with real analytics endpoints
6. **GF-005 / GF-006** — Session list click → load messages; refresh on new chat
7. **GF-004 / GF-023** — Handle WS `status` / approval messages in TerminalCard
8. A2A + MCP UI (lower priority until core loop stable)

---

## 14. Issue ID Index (Gemini-specific)

**Integration gaps:** GF-001 … GF-024  
**Corner cases:** CC-01 … CC-24  

---

*Last updated: 2026-05-27 — appended backend-frontend matrix, planning flow, and corner-case catalog.*