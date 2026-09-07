# Architecture

## Scope

This is the standalone personal LLM workstation described in the build
spec. It is not the app-builder, Command Desk, Document Hands, or any
other existing application. Nothing here assumes integration with those
systems.

## System diagram

```
                         ┌───────────────────────┐
                         │       USER            │
                         │       Browser         │
                         └───────────┬───────────┘
                                     │
                         ┌───────────▼───────────┐
                         │      OPEN WEBUI       │
                         │   PRIMARY INTERFACE   │
                         └───────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
             ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
             │ LOCAL OLLAMA │ │ CLOUD GPU   │ │ TASK SYSTEM │
             │ (native, on  │ │ (rented,    │ │ (worker(s), │
             │  the laptop) │ │  on demand) │ │  DB-backed) │
             └──────────────┘ └──────┬──────┘ └──────┬──────┘
                                     │                │
                              ┌──────▼────────────────▼──────┐
                              │     CONTROL API (FastAPI)    │
                              │  model registry · GPU        │
                              │  lifecycle · routing ·       │
                              │  notifications · policy      │
                              └──────────────┬───────────────┘
                                             │ HMAC-signed HTTP
                                  ┌──────────▼──────────┐
                                  │ LOCAL EXECUTION     │
                                  │ AGENT (independent) │
                                  │ files · commands ·   │
                                  │ tests · approvals    │
                                  └─────────────────────┘
```

## Process/trust boundaries

There are four kinds of process in this system, and the boundary between
them is deliberate, not incidental:

1. **Control API** (`apps/control`) — the only process that ever holds a
   live connection to a cloud GPU provider. Owns the GPU state machine.
2. **Worker** (`worker`) — one or more independent processes that claim
   tasks from the shared database and execute them. A worker never talks
   to a GPU provider directly; when a task needs the cloud GPU, the worker
   asks the control API (`POST /api/gpu/start`) and then polls the shared
   `gpu_sessions` row directly for the endpoint once it's `READY`.
3. **Local execution agent** (`local-agent`) — runs on the laptop, is the
   only thing that can touch the laptop's filesystem or run a command, and
   is the last line of defense: it re-authenticates and re-classifies
   every request against its own copy of `config/policies.yaml`
   independently of whatever the control plane decided. See
   [`SECURITY.md`](SECURITY.md) for why this is two independent
   implementations rather than one shared library.
4. **Open WebUI** — an off-the-shelf container. It talks to local Ollama
   directly and to the cloud GPU through the control API's stable reverse
   proxy (`/proxy/cloud`) rather than a raw, session-specific IP.

## Why a shared library (`workstation_core`) instead of the control API

The build spec's original folder sketch put task/notification/audit
services under `apps/control/src/control/*`. During the build, the worker
needed those same services (a task's failure has to create a notification
and an audit record no matter which process — control API or worker —
happened to touch it last), and importing from `apps/control` inside
`worker` would have made the worker depend on the control API's FastAPI
app package for no FastAPI-specific reason. Those services were moved into
`libs/core/workstation_core` (`task_service`, `notification_service`,
`audit_service`, `routing_service`, `execution_service`, `agent_client`,
`gpu_activity`) so that both processes import the same pure-database logic
from a package that has no framework dependency of its own. The control
API's `apps/control/src/control/*` package is now just the FastAPI routers,
dependency wiring, and the GPU lifecycle manager (which genuinely is
control-API-only, since it's the one thing that holds a live object — the
provider connection — that can't be shared between processes).

The local execution agent deliberately does **not** depend on
`workstation_core` at all — see `libs/core/workstation_core/__init__.py`'s
docstring and [`SECURITY.md`](SECURITY.md).

## Model registry: never fabricate availability

`ModelRecord.status` is only ever set to `available` because an inference
engine actually answered — `workstation_core`'s `OllamaClient`/
`CloudInferenceClient` hit a real HTTP endpoint. The registry's cloud check
does not depend on a static `CLOUD_LLM_BASE_URL`: because a real provider
(RunPod et al.) hands out a new IP every session, the registry (and
`/health/cloud`) fall back to whatever the GPU lifecycle manager currently
has recorded as the live endpoint (`gpu_sessions.session_metadata.endpoint`)
when no static override is configured. A model that was previously
discovered stays in the table with `status=unavailable` once its GPU
session ends — the row (and therefore the ability to select it again,
which is what should trigger the GPU to restart) persists; only its
verified-live status does not.

## Task routing

Three modes exist, matching spec section 10:

- **Explicit** (the default): the request names a `model_id`. If it's a
  local model, it must currently be `available`. If it's a cloud model, it
  may be `unavailable` right now — selecting it is exactly what should
  make the worker start the GPU back up. This distinction
  (`workstation_core/routing_service.py`) is what makes "select a cloud
  model" → "GPU automatically starts" possible from a cold start.
- **Automatic**: the request sets `input.routing_mode: "automatic"` plus
  `input.required_capabilities`; the router picks the best available match
  (local preferred over cloud, then by `cost_class`).
- **Background**: a task with no model_id resolved at creation time is
  re-resolved by the worker at claim time using the same logic.

## GPU lifecycle

State machine, protected states, idle timeout, max session duration, and
cost-limit enforcement are implemented in
`apps/control/src/control/gpu/lifecycle.py` against the transition table in
`workstation_core/enums.py`. See that module's docstrings for the exact
state diagram and for how a control-API restart reconciles GPU state
without ever silently assuming an unknown state is safe.

## Providers

`gpu/provider_interface/base.py` defines the contract; `gpu/registry.py` is
the only place that imports a concrete provider. Implemented: `mock` (a
real local HTTP server standing in for a cloud GPU — used for dev and this
repository's own tests, never for production) and `runpod` (RunPod's
GraphQL API, exercised in tests via mocked HTTP since this build
environment has no live account — see `gpu/providers/runpod/provider.py`'s
docstring). `vast` and `lambdalabs` are documented interface stubs that
raise `NotImplementedError` rather than silently doing nothing.

## A note on naming

`gpu/providers/lambdalabs/` (not `lambda/`) — `lambda` is a reserved
Python keyword and cannot be a package name. The directory identifies the
same provider (Lambda Cloud); only the on-disk/import name differs from
the build spec's prose.
