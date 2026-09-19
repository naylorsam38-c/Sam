# data-dashboard (Redash) — browser journey recording

**Run:** chain terminal state **HELD**, `RUN-0002` (baseline), `RUN-0004`
(CAP-0002 emptied), `RUN-0005` (restored, confirmed recovery) — all three
via the full `chain.py` path, no retries needed (unlike CTFd, Redash never
hit an internal deadlock in this session).

**Date:** 2026-09-18/19.

**What the video shows:** the journey drives the **real, unmodified
`host.py`** in its real serving mode (`python3 host.py --app
data-dashboard`, no `--check`). `host.py` printed:

```
shelf parts bound: 4
  NOT BOUND  CAP-0001: part did not load: AssertionError: The setup method 'route' can no longer be called on the blueprint 'redash'. It has already been registered at least once, any changes will not be applied consistently.
  NOT BOUND  CAP-0002: part did not load: AssertionError: [same]
  NOT BOUND  CAP-0003: part did not load: AssertionError: [same]
  NOT BOUND  CAP-0017: part did not load: AssertionError: [same]
REFUSED: a capability on the shelf could not be bound to its own part -- the app would be served by code the shelf does not govern
```

and exited before binding to port 8002. The browser then genuinely could
not reach `http://127.0.0.1:8002/login` — `net::ERR_CONNECTION_REFUSED` —
because nothing was listening. `journey.webm` shows that real, failed
navigation.

**This is the correct, honest result of this app's real state**, per Step 5:
`shelf parts bound` (4/8) did not equal the capability count, and
`FAIL_ON_UNRESOLVED` was left exactly as shipped. As with CTFd, the more
lenient `host_test_data_dashboard.py` harness used for Steps 5–6 would have
shown a working-looking login page — served by Redash's own unmodified
code, per the emptied-part proof, not by the shelf's part — so it was not
used for this deliverable.
