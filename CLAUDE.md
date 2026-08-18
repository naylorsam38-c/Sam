# Command Desk — standing instructions and the pre-live fix list

This file is memory. Read it before touching the Command Desk package.

## Standing constraints (owner, verbatim in intent)

- Do NOT deploy to production. Do NOT modify live nginx, production auth, the
  production database, or the live model. Work only on the coding project.
- Do not invent live-only values — no AWS values, PM2 state, production `.env`,
  adapter paths, ports or credentials. Mark anything needing the host
  `REQUIRED_FROM_LIVE`.
- Credentials and tokens MUST: be encrypted at rest; be scoped to the right
  user/account/tenant; never appear in normal UI, worker prompts, chat history,
  ordinary API responses, or plaintext logs; and be revocable.
- Do NOT silently alter the foundation (the worker roster).
- Marketing performs ONLY what its contract defines. It is not a research or
  web-information worker by default.
- Build the gateways, not the user's credentials. Users connect their own
  accounts; no worker ever holds the secret.
- No mocks, no simulation, no canned results, no PASS from source inspection.
- Builder → Tester → Playwright is a mandatory gate on the exact same artifact.
- The pre-live master checklist is a governed acceptance contract: read it before
  any change, use it as the definition of completion, re-run it after every
  repair loop, and do not report complete unless every applicable item is.

## Verification commands (the only acceptable evidence)

    npm test / test:unit / test:integration / test:security / test:e2e
    npm run prelive:gate        # Builder → Tester → Playwright, real Chromium
    npm run prelive:checklist   # every §14 line, re-runnable, exits non-zero unless all DONE
    npm run prelive:roles       # the §12 role job checklist, generated
    npm run governance:verify   # the hash-locked governance bundle

Playwright is never vendored (the product ships dependency-free). Point the gate
at an out-of-tree install: `PLAYWRIGHT_ROOT=/path/to/node_modules`.

---

# THE FIX LIST (owner-supplied, applied to CommandDesk_CONNECTIONS_v5.zip)

Coding project only. The owner is not changing that ZIP; this is the fix list and
the standard to engineer against.

## A. Connection Gateway — definite gaps
1. Add `project_id` to connection identity.
2. Add `provider_account_identity`.
3. Implement token refresh instead of requiring reconnect after expiry.
4. Strengthen key custody beyond a single environment variable.
5. Document/protect credential backup safety.
6. Make capability registration action-specific: scope, policy, approval requirement.
7. Separate provider permissions from Command Desk authorization.
8. Add governed scope expansion.
9. Add scope-downgrade handling that removes capabilities correctly.
10. Add proper health taxonomy: missing, expired, revoked, insufficient scope, rate-limited.
11. Add per-connection quota accounting.
12. Add connection-aware backoff/rate limiting.
13. Add provider push ingress and its trust boundary.
14. Resolve Brain disconnect/retention semantics.
15. Add per-connection cost attribution.
16. Complete shared capability interfaces / frontend independence.
17. Separate dev/test/production credentials.

## B. OAuth
18. Fix the provider callback so the actual provider redirect method works. The
    real provider must redirect directly to the registered callback. Do not rely
    on the UI converting it into another request.

## C. Research / Brain
19. Complete Forge/Mind research capability.
20. Add evidence provenance to research results.
21. Complete the Brain Builder service boundary.
22. Live-qualify Brain Builder.
23. Resolve and implement Brain retention/disconnect behaviour.

## D. Governance
24. Fix the worker-roster governance hole — changes to `LLM_WORKER_ROLES` /
    `NON_WORKER_CONTRACTS` must be covered by the freeze/acceptance mechanism.
25. Resolve the §24 worker-roster decision.

## E. LLM / pipeline completeness
26. Verify every LLM's actual contract against its intended job.
27. Verify every LLM-to-LLM handoff exists in code.
28. Verify every handoff has input/output contracts.
29. Verify failure/retry paths.
30. Verify persistence/audit at each stage.
31. Verify Guardian supervision is actually connected to the pipeline.
32. Verify Independent Summary is actually connected where required.
33. Verify Builder → Tester → Playwright is a mandatory gate.
34. Verify the Forge ↔ Mind repair loop.
35. Verify the Builder ↔ Tester ↔ Playwright repair loop.
36. Verify Consolidator cannot accept incomplete evidence.

## F. Hands / laptop
37. Every Hands adapter has a complete capability/permission/approval contract.
38. Laptop advertised capabilities exactly match implemented actions.
39. Laptop job identity / result identity preserved end to end.
40. Laptop reconnect/restart path remains governed and auditable.
41. Laptop Hands reachable from every role that is supposed to use it.

## G. Test-system problems
42. Find and fix tests that give false confidence — tests that call internal
    functions instead of real HTTP routes, don't exercise the real HTTP method,
    mock providers, use simulation, bypass governance, bypass authentication,
    inject fake results, or bypass the actual handoff.
43. Builder → Tester → Playwright must test the exact same artifact.
44. Verify artifact ID / hash continuity.
45. Failed Playwright tests return to Builder/Tester for repair.
46. Consolidator requires Builder + Tester + Playwright evidence.

## H. Live qualification — NOT done, must not be reported as PASS
AC-001, AC-002, AC-004, AC-005, AC-006, AC-007, AC-008 have not been live
validated. No real provider account has been connected. They remain
**NOT LIVE QUALIFIED**.

## I. Platform / live gate — host-side, still outstanding
47. Real production inventory.       48. Real PM2 topology/parity.
49. Real nginx / effective port.     50. Real configuration values.
51. Real OWNER authentication/session. 52. Real database.
53. Real Ollama.                     54. Real roster/rooms.
55. Real Dispatch/laptop round trip. 56. Real adapter integration.
57. Real Desk Protocol bridge.       58. Real browser acceptance.
59. `simulation_mode=false`.         60. Clean PM2 restart/resurrection.
61. Final active-path / drift scan.

## Bottom line the owner stated

Offline validation passing does not mean the live requirements are complete.
Order of work: Connections completeness → OAuth → Brain/Research → governance
roster → LLM handoffs → Builder/Tester/Playwright gate → test false-confidence →
remaining live qualification hooks.
