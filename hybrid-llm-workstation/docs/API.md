# Control API Reference

Base URL: `http://<host>:8000` (default). Interactive docs at `/docs`
(FastAPI's generated OpenAPI UI) once the server is running.

All endpoints except `/health*` and `POST /api/auth/login` require
`Authorization: Bearer <token>`, obtained from login. Request/response
bodies below are illustrative — see `libs/core/workstation_core/schemas.py`
for the exact Pydantic models.

## Auth

```
POST /api/auth/login
  { "username": "...", "password": "..." } -> { "access_token": "...", "token_type": "bearer" }
```

## Health

```
GET /health                 overall control-API liveness
GET /health/local-ollama    is Ollama reachable at OLLAMA_LOCAL_URL
GET /health/cloud           is the cloud engine reachable (static CLOUD_LLM_BASE_URL,
                            or the current GPU session's live endpoint if unset)
GET /health/worker          has any worker heartbeated in the last 90s
GET /health/agent           is the local execution agent reachable
```

Each returns `{"component": "...", "healthy": true|false, "detail": "...", "checked_at": "..."}`.

## Models

```
GET  /api/models              all models, local and cloud
GET  /api/models/local
GET  /api/models/cloud
GET  /api/models/{id}
POST /api/models/refresh      re-verify against the real Ollama/cloud endpoints;
                               returns {"local": {...}, "cloud": {...}} health report
```

A model's `status` is `available` only if the last refresh actually
reached that engine. Selecting a `cloud` model with `status=unavailable`
is allowed — it's what triggers the GPU to start. Selecting a `local`
model with `status=unavailable` is rejected (nothing will make Ollama have
a model it doesn't have).

## GPU

```
GET  /api/gpu           current status, endpoint, cost limits
POST /api/gpu/start     idempotent; returns immediately, poll GET /api/gpu for READY
POST /api/gpu/stop?force=false
                        409 if status is BUSY/STARTING/BOOTING/PROVISIONING and force=false
POST /api/gpu/restart
GET  /api/gpu/cost      {"status", "session_minutes", "estimated_cost", "max_hourly_cost", "over_limit"}
```

## Tasks

```
GET  /api/tasks[?status_=QUEUED]
POST /api/tasks
  { "type": "chat" | "generate" | "execution", "model_id": "...", "environment": "local"|"cloud",
    "input": {"messages": [...]} }        # chat/generate
  { "type": "execution",
    "input": {"operation": "read_file", "parameters": {...}, "working_directory": "..."} }
GET  /api/tasks/{id}
POST /api/tasks/{id}/cancel
POST /api/tasks/{id}/pause     -> PAUSED (from QUEUED or RUNNING)
POST /api/tasks/{id}/resume    -> QUEUED
GET  /api/tasks/{id}/result    409 until the task reaches COMPLETED or FAILED
```

`type: "execution"` tasks have no `model_id`/`environment` — they're
routed through the same approval flow as `POST /api/execution/requests`
(see below), and the task's own status mirrors the resulting
`ExecutionRequest` automatically (`REQUIRES_APPROVAL` while pending,
`COMPLETED`/`FAILED` once resolved) — no separate "resume" call needed
once a human approves.

## Notifications

```
GET  /api/notifications[?unread_only=true]
POST /api/notifications/{id}/read
```

## Approvals

```
GET  /api/approvals[?status_=PENDING]
POST /api/approvals/{id}/approve
POST /api/approvals/{id}/deny
```

## Execution (local agent proxy)

```
POST /api/execution/requests
  { "operation": "read_file"|"list_directory"|"write_file"|"run_command"|"run_script"|"run_tests",
    "parameters": {...}, "working_directory": "...", "task_id": null }
GET  /api/execution/requests/{id}
POST /api/execution/requests/{id}/approve   shortcut for approving via the linked Approval
POST /api/execution/requests/{id}/deny
```

Response `status` is one of `PENDING`, `AWAITING_APPROVAL`, `DENIED`,
`RUNNING`, `COMPLETED`, `FAILED` — see `docs/SECURITY.md` for what each
means and who decides it.

## Cloud proxy (for Open WebUI, not for direct API use)

```
GET/POST /proxy/cloud/{path}
  Header: Authorization: Bearer <OPEN_WEBUI_PROXY_TOKEN>
```

Forwards to whatever the current GPU session's live endpoint is. 503 if
the GPU isn't `READY`. See `docker-compose.yml`'s comments for wiring this
into Open WebUI's connection settings.
