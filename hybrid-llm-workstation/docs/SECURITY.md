# Security

## Threat model

The system assumes:

- The cloud LLM (running on rented, third-party hardware) is **not
  inherently trusted**. A prompt injection, a compromised model, or a bug
  anywhere between it and the laptop should not be able to run arbitrary
  commands on the laptop.
- The control plane, while trusted more than the cloud LLM, is still
  software that can have bugs or misconfiguration. It should not be a
  single point of failure for laptop safety.
- The local execution agent, running on the laptop itself, is the last
  line of defense and must hold even if everything upstream of it is
  wrong.

## Defense in depth: two independent policy engines

`workstation_core/policy_engine.py` (used by the control API) and
`local-agent/src/agent/policy/engine.py` (used by the agent) implement the
same classification logic against the same `config/policies.yaml` file —
**deliberately as two separate, non-shared implementations**. This is not
an oversight; it's stated directly in both modules' docstrings. If the
control plane's copy had a bug, or a future change accidentally widened
what it considers safe, or the control plane itself were compromised, the
agent's own independent classification is what actually decides whether
anything executes on the laptop. The agent never trusts the control
plane's classification — it only trusts:

1. A valid HMAC-SHA256 signature over `(request_id, operation, timestamp)`
   keyed by `EXECUTION_AGENT_TOKEN`, with a 60-second replay window
   (`local-agent/src/agent/auth/signature.py`). Only a holder of that
   shared secret can get a request past this check at all.
2. Its own `allowed_paths`/`allowed_commands` check, re-run inside the
   executor itself (`local-agent/src/agent/executor/operations.py`) even
   after the same check already ran during classification — belt and
   suspenders within the agent, not just between the agent and the control
   plane.
3. For `APPROVAL`-level operations, a non-empty `approval_token` on the
   request. The agent cannot verify that token against the control
   plane's approval database (they may not even share a network beyond
   this one HTTP hop) — its presence is what the control plane's
   `execute_now()` sends only after a human has approved the associated
   `Approval` row. The real guarantee an attacker without the shared
   secret can't produce a validly signed request at all is what actually
   matters; the approval_token is an audit/workflow signal layered on top.
4. For `RESTRICTED` operations (unknown to `policies.yaml`, or whose
   target path/command falls outside the configured allowlist), the agent
   refuses unconditionally — an `approval_token`, however it was obtained,
   changes nothing.

Verified in `local-agent/tests/test_audit_and_bypass.py`:
`test_forged_approval_token_cannot_bypass_the_signature_check` and
`test_approval_token_cannot_bypass_restricted_path_boundary`, and across
the real process boundary (not the control API's internal test double) in
`tests/integration/test_control_to_real_agent.py`.

## Default posture: restrictive

`config/policies.yaml` ships with every operation at `level: APPROVAL` and
no operation at `TRUSTED`. Nothing runs without an explicit approval by
default. `RESTRICTED` is not a level anyone configures directly in this
file — it's the value `classify()` returns automatically the moment a
request's target falls outside `allowed_paths`/`allowed_commands`,
regardless of what level was configured for that operation.

**Before first use**, edit `allowed_paths` in `config/policies.yaml` on the
machine running the agent. The shipped default (`~/workstation-workspace`)
is a placeholder; both policy engines refuse any operation outside it
unconditionally, so nothing will work against your real project
directories until you point it at them.

## Authentication

- **User ↔ control API**: username/password (bcrypt-hashed,
  `workstation_core/security.py`) issuing a JWT (`HS256`, `AUTH_SECRET`).
  Every mutating endpoint requires it (`Depends(get_current_user)`), and
  every state-changing action is written to `audit_events` in the same
  transaction as the change.
- **Control API ↔ local agent**: HMAC-SHA256, not JWT — see above.
  `EXECUTION_AGENT_TOKEN` must differ from `AUTH_SECRET`; they protect
  different boundaries and a leak of one must not compromise the other.
- **Open WebUI ↔ control API** (for the cloud proxy only):
  `OPEN_WEBUI_PROXY_TOKEN`, a separate static secret. This one is
  intentionally weaker (a fixed bearer token, no replay protection) — its
  purpose is only to stop other devices on the local network from riding
  along on metered cloud GPU time, not to gate a genuinely sensitive
  operation. It is never used to authorize a laptop action.

## What was verified vs. what needs a real deployment

Verified with automated tests in this build environment (151 tests, 146
passing / 5 explicitly skipped — see `TEST_REPORT.md`):

- JWT tampering, `alg: none` downgrade, expired tokens, tokens for deleted
  users, wrong-secret signing (`tests/security/`, `tests/unit/test_security.py`).
- SQL-injection-shaped input into login and task fields, verified inert
  (SQLAlchemy's parameterized queries; never raw string interpolation
  anywhere in this codebase).
- HMAC replay-window enforcement, forged tokens, path-traversal (`../`)
  attempts, and out-of-scope commands against the real agent
  (`local-agent/tests/`).
- The proxy endpoint refusing to act as an open relay for arbitrary hosts.

Not verifiable without your own infrastructure, and not claimed as
verified:

- Network-level exposure of the control API/agent ports on your actual
  home/office network (firewall rules, whether `0.0.0.0` binding is safe
  in your environment) — bind them to `127.0.0.1` or a VPN interface if
  the laptop and control API aren't the same machine, or add a reverse
  proxy with TLS in front of both.
- The real RunPod API's current authentication and rate-limiting behavior.
- Anything about a specific cloud provider's own security posture (their
  hypervisor isolation, network egress rules, etc.) — that's the
  provider's responsibility, not this codebase's.

## Secrets

Never commit `.env`. `scripts/dev/bootstrap.sh` generates
`AUTH_SECRET`/`EXECUTION_AGENT_TOKEN`/`OPEN_WEBUI_PROXY_TOKEN` freshly on
first run. `database/seeds/seed_admin.py` refuses to fabricate a default
admin password — it fails loudly if neither `--password` nor
`WORKSTATION_ADMIN_PASSWORD` is supplied.
