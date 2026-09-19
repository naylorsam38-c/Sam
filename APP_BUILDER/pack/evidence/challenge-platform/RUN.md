# challenge-platform (CTFd) — browser journey recording

**Run:** chain terminal state **HELD**, `RUN-0001` (baseline), `RUN-0003`
(CAP-0002 emptied), confirmed restored via a direct suite run (`pack/runs/RUN-0007`)
after the full `chain.py` path hit CTFd's own intermittent plugin-loader
deadlock on repeated retries (see `evidence/TWO_MORE_APPS.md`).

**Date:** 2026-09-18/19.

**What the video shows:** the journey drives the **real, unmodified
`host.py`** in its real serving mode (`python3 host.py --app
challenge-platform`, no `--check`), exactly as a real deployment would run
it. `host.py` printed:

```
shelf parts bound: 3
  NOT BOUND  CAP-0001: part has no class named by 'register'
  NOT BOUND  CAP-0002: part has no class named by 'login'
  NOT BOUND  CAP-0003: part has no class named by 'logout'
  NOT BOUND  CAP-0014: part has no class named by 'new'
  NOT BOUND  CAP-0015: part has no class named by 'join'
REFUSED: a capability on the shelf could not be bound to its own part -- the app would be served by code the shelf does not govern
```

and exited before ever binding to port 8001. The browser then genuinely
could not reach `http://127.0.0.1:8001/login` —
`net::ERR_CONNECTION_REFUSED` — because there was nothing listening. That
connection-refused moment is what `journey.webm` shows: a real browser, a
real failed navigation, against the host exactly as it would be started for
real.

**This is the correct, honest result of this app's real state**, per Step 5:
`shelf parts bound` (3/8) did not equal the capability count, and
`FAIL_ON_UNRESOLVED` was left exactly as shipped. The journey was never
going to succeed against `host.py` as-is, and this is not routed around by
using a more lenient harness for this deliverable — the whole point of this
step is to show what a real person's browser actually experiences.

(The separate `host_test_challenge_platform.py` harness used for Steps 5–6
is deliberately more lenient — it records a bind failure as a check result
and keeps serving anyway, which is what made the emptied-part proof and the
class-vs-function findings possible to observe at all. Driving *that*
server with Playwright would have shown a working-looking login page — see
`evidence/TWO_MORE_APPS.md` Step 6 for exactly why that would have been
misleading: the route is served by CTFd's own unmodified code, not the
shelf's part.)
