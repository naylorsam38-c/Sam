# RETIRED — challenge-platform (CTFd)

**Retired:** 2026-09-19, by direct instruction ("FINAL CLAUDE CODE HANDOFF —
Django/PostgreSQL + Attach-Point Harvest Architecture").

**Why:** Rule A was rewritten to admit only Django + PostgreSQL sources.
CTFd (`CTFd/CTFd`) is Flask. It was correctly admitted under the *previous*
Rule A (Flask + PostgreSQL) and passed that admission check honestly —
nothing here was ever found defective as a harvest. It fails only the new,
narrower Rule A. Retirement is a rule change, not a finding against this
app or its harvest.

(For what it's worth, this app's own harvest already surfaced real,
independent findings that have nothing to do with this retirement —
`bind_shelf_parts`'s class-only binding rejecting every plain-function view
CTFd has, and the `X-Shelf-Capability` stamp not proving a request was
served by the shelf's own part. See `evidence/TWO_MORE_APPS.md` below;
those findings stand regardless of framework.)

**What is preserved here, unchanged:**

- `complete_source/` — the **complete CTFd working tree** at the pinned
  commit (`8864bc0cea5b67d9ae96978b5d559e70330ff071`), `.git` history
  excluded, exact commit recorded in `complete_source/COMMIT.txt`. This is
  the whole application, not just the harvested fragments below — added
  2026-09-19 per direct instruction.
- `shelf/` — all eight harvested capabilities (`CAP-0001`, `CAP-0002`,
  `CAP-0003`, `CAP-0011`–`CAP-0015`), each with `source.py`,
  `PROVENANCE.json` (`symbol_verified: true`), and `LICENCE.txt`, moved
  verbatim from `pack/shelf/challenge-platform/`.
- `form.json` — the filled harvest form, moved verbatim from
  `pack/forms/challenge-platform.form.json`.
- `tree.json` / `tree.txt` — the N4 app tree, moved verbatim from
  `pack/trees/`.
- `host_test.py` — the app-specific host-proof suite
  (`host_test_challenge_platform.py`), moved verbatim from `pack/4_host/`.
- `evidence/` — a **copy** of `evidence/challenge-platform/` (journey.webm,
  RUN.md, record_journey.py) and of `evidence/TWO_MORE_APPS.md` (the
  originals stay in place at `pack/evidence/`, per "do not delete
  evidence").

**What was NOT deleted:**

- `APP-002`'s number in `number_registry.json` — marked `"status":
  "retired"`, never reused (N1).
- `CAP-0001`/`0002`/`0003` ("register account"/"log in"/"log out") are
  shared with the other two retired apps under N2 and remain valid
  numbers a future Django implementation would reuse.
  `CAP-0011`–`CAP-0015` ("list challenges", "submit flag", "view
  scoreboard", "create team", "join team") are CTFd-specific; their
  numbers stay reserved and reusable by a future challenge-platform
  category admission with the same real concepts.

**A note for whoever picks the next challenge-platform candidate:** this
harvest's own PostgreSQL-support investigation (see
`evidence/TWO_MORE_APPS.md`) is worth reading regardless — the same kind of
"tested against but not the primary datastore" caveat may well recur.

**Not listed as admitted:** the relevant `shelf/capabilities/*.json` and
`IMPL-01` records now read `"status": "retired"`. Nothing under
`pack/shelf/` still references `challenge-platform`.
