# Security Review

Self-review of this build against the threat model in `docs/SECURITY.md`
and the spec's stated security requirements (sections 15-17, operational
rules 5-6).

## Reviewed and verified

| Control | Verified by |
|---|---|
| Every mutating control-API endpoint requires a valid JWT | `tests/security/test_auth_and_injection.py::test_missing_auth_header_on_every_mutating_endpoint` |
| JWT `alg: none` downgrade rejected | `test_none_algorithm_token_is_rejected` |
| Wrong-secret / expired / deleted-user tokens rejected | same file |
| Passwords bcrypt-hashed, never logged/returned | `tests/unit/test_security.py`; `schemas.py`'s `LoginRequest`/`User` model never exposes `password_hash` |
| SQL-injection-shaped input handled safely (parameterized queries only) | `test_sql_injection_style_*` |
| Local agent independently re-authenticates every request (HMAC + replay window) | `local-agent/tests/test_execute.py` |
| Local agent independently re-classifies every request (ignores control-plane's decision) | `local-agent/tests/test_audit_and_bypass.py`, `tests/integration/test_control_to_real_agent.py` |
| `RESTRICTED` classification cannot be bypassed by any approval_token | `test_approval_token_cannot_bypass_restricted_path_boundary` |
| Path traversal (`../`) resolved and checked, not string-matched | `tests/unit/test_policy_engine.py::test_symlink_or_traversal_path_resolves_before_the_bounds_check` |
| Command execution uses `shlex.split` + an explicit binary allowlist, never `shell=True` | `local-agent/src/agent/executor/operations.py` |
| Command timeout enforced | `test_command_timeout_is_reported_as_failed` |
| Cross-user data isolation (tasks, notifications) | `apps/control/tests/test_tasks.py::test_task_not_visible_to_other_user`, `test_notifications.py::test_cannot_read_other_users_notification` |
| Audit trail exists on both sides (control-plane `audit_events`, agent's own SQLite) and cannot be silently skipped | `test_every_call_is_audited_regardless_of_outcome` |
| GPU never terminates active inference without explicit `force=true` | `apps/control/tests/test_gpu.py`, `test_gpu_monitor.py::test_busy_gpu_is_never_touched_by_monitor` |
| Cost limits actually stop the GPU, not just report a number | `test_gpu_monitor.py::test_cost_limit_forces_stop` |
| Cloud proxy cannot be used as an open relay | `test_proxy_endpoint_cannot_be_used_to_reach_arbitrary_hosts` |
| Secrets never committed | `.gitignore` excludes `.env`, `*.pem`, `*.key`; `.env.example` contains only placeholders |
| No fabricated default credentials | `database/seeds/seed_admin.py` refuses to run without an explicit password |

## Findings from this review (all fixed — see `TEST_REPORT.md` for detail)

- Two independent policy engines existing is a deliberate defense, but it
  also means they can drift out of sync if one is edited and not the
  other. **Residual risk, accepted by design**: both load the same
  `config/policies.yaml` file, so drift would require someone to
  deliberately maintain two *different* files, which isn't how the system
  is set up to be operated. Flagged here rather than silently assumed.
- The approval-token mechanism (`local-agent`'s `APPROVAL` level) relies
  on the HMAC signature being the actual security boundary — the token
  itself is not independently verifiable by the agent. This is documented
  explicitly in `docs/SECURITY.md` rather than presented as a stronger
  guarantee than it is.

## Not reviewed / out of scope for this build

- **Network exposure.** Nothing here configures TLS, a firewall, or
  restricts which interfaces the control API/agent bind to beyond what
  `APP_HOST=0.0.0.0` (control API) and `agent_host=0.0.0.0` (agent)
  default to. **Action required before any deployment beyond localhost**:
  put a reverse proxy with TLS in front of both, or bind them to a
  private/VPN interface only. This is called out in `docs/SECURITY.md`
  but not enforced in code — enforcing it would require knowing your
  actual network topology, which this build cannot know.
- **Dependency vulnerability scanning.** No `pip-audit`/`safety`/Dependabot
  configuration was set up. Pinned version *ranges* exist
  (`requirements.txt`) but no lockfile with exact hashes.
- **Rate limiting / brute-force protection on `/api/auth/login`.** Not
  implemented. For a single-user personal system reachable only on a
  trusted network this is a reasonable initial posture, but it is a real
  gap if the control API is ever exposed to the open internet.
- **RunPod's own security posture** (their API's rate limiting, auth
  token scoping, network isolation between tenants) — reviewed only to
  the extent of reading their public GraphQL schema shape to build the
  provider adapter; not independently audited.
- **Supply-chain integrity of the Open WebUI image** — `ghcr.io/open-webui/open-webui:main`
  is pulled and trusted as-is; no image signature verification is
  configured.

## Recommendation

Safe for the personal, single-user, trusted-network use case this spec
describes, once you: set real secrets (not the placeholders in
`.env.example`), edit `config/policies.yaml`'s `allowed_paths` to your
real project directories, and keep the control API and agent off any
network you don't trust without adding TLS/a firewall in front of them.
Not reviewed for, and not recommended as-is for, multi-tenant or
internet-facing deployment without the network-exposure and rate-limiting
gaps above being addressed first.
