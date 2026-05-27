# API Documentation

REST and WebSocket reference for the **AI Orchestrator** backend (`backend/main.py`).

> **Note:** The [`downloader_page/`](../downloader_page/) project has a separate FastAPI app for serving installer downloads. This document describes the main orchestrator API only.

---

## Base URL

- **Development:** `http://localhost:8000`
- **Production:** configure via `API_HOST` / `API_PORT` in `backend/.env`

Most routes are prefixed with `/api`. Health and OpenAPI are also available at the root.

---

## Authentication

Session/user scoping is evolving. Many endpoints accept a default user in development. Treat production deployments as requiring proper auth before exposure to a network.

---

## Health

### `GET /health`

Returns application and database status.

### `GET /api/health`

Same payload as `/health` (useful when the frontend proxy only forwards `/api/*`).

**Example:**
```bash
curl http://localhost:8000/health
```

---

## Sessions — `/api/sessions`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sessions` | Create a session |
| GET | `/api/sessions` | List sessions |
| GET | `/api/sessions/{session_id}` | Get session |
| GET | `/api/sessions/{session_id}/messages` | List messages |

---

## Providers — `/api/providers`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/providers` | List AI providers |
| GET | `/api/providers/{provider_id}` | Get provider |
| POST | `/api/providers/{provider_id}/credentials` | Store credentials |
| GET | `/api/providers/{provider_id}/credentials` | Get masked credentials |

---

## Orchestrator — `/api/orchestrator`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/orchestrator/dispatch` | Dispatch a task to the routing engine |
| POST | `/api/orchestrator/chat` | Chat with the orchestrator LLM |
| GET | `/api/orchestrator/config` | Get orchestrator configuration |
| POST | `/api/orchestrator/config/reset` | Reset configuration |
| GET | `/api/orchestrator/providers/health` | Provider health summary |

---

## Runtimes — `/api/runtimes`

Manage CLI agent PTY runtimes (parallel terminals).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/runtimes` | List runtimes |
| GET | `/api/runtimes/active` | Active runtimes |
| POST | `/api/runtimes/spawn` | Spawn a runtime |
| GET | `/api/runtimes/{runtime_id}` | Runtime details |
| POST | `/api/runtimes/{runtime_id}/approve` | Approve pending runtime |
| POST | `/api/runtimes/{runtime_id}/pause` | Pause runtime |
| POST | `/api/runtimes/{runtime_id}/resume` | Resume runtime |

---

## Workspace — `/api/workspace`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/workspace/git` | Git status |
| POST | `/api/workspace/git/run` | Run allowlisted git command |
| GET | `/api/workspace/shared` | Shared context files |
| GET | `/api/workspace/context` | Session context files |
| POST | `/api/workspace/context` | Upload context file |
| GET | `/api/workspace/artifacts` | List artifacts |
| POST | `/api/workspace/artifacts` | Create artifact |

---

## Analytics — `/api/analytics`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analytics/usage` | Usage statistics |
| GET | `/api/analytics/routes` | Routing history |
| GET | `/api/analytics/providers` | Provider metrics |
| GET | `/api/analytics/sessions/{session_id}` | Session analytics |

---

## Settings — `/api/settings`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Application settings |
| GET | `/api/settings/cli-registry` | CLI registry (installer/bootstrapper) |
| POST | `/api/settings/reset` | Reset settings |

---

## Onboarding — `/api/onboarding`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/onboarding/complete` | Complete first-run onboarding |

---

## Tools — `/api/tools`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tools/mcp` | List MCP tools |
| POST | `/api/tools/mcp/{tool_name}/invoke` | Invoke MCP tool |

---

## WebSocket — terminals

### `WS /ws/terminals/{runtime_id}`

Bi-directional PTY stream for a spawned CLI runtime (xterm.js client).

**Server → client (examples):**
```json
{"type": "hello", "runtime_id": 1, "status": "running", "pid": 1234}
{"type": "output", "data": "prompt$ "}
{"type": "error", "error": "Runtime not found"}
```

**Client → server:**
```json
{"type": "input", "data": "npm test\r"}
{"type": "resize", "cols": 120, "rows": 40}
```

---

## Interactive documentation

When the backend is running:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

---

## Error responses

Validation and application errors return JSON:

```json
{
  "error": "Validation Error",
  "detail": "...",
  "code": "VALIDATION_ERROR"
}
```

Common status codes: `200`, `201`, `400`, `404`, `422`, `500`.

---

## Related documentation

- [QUICK_START.md](QUICK_START.md) — run the main app
- [ARCHITECTURE.md](ARCHITECTURE.md) — system design
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — repo layout
- [downloader_page/README.md](../downloader_page/README.md) — download site API (separate app)

---

Last Updated: 2026-05-27
