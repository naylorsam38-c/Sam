# RETIRED — event-ticketing (Indico)

**Retired:** 2026-09-19, by direct instruction ("FINAL CLAUDE CODE HANDOFF —
Django/PostgreSQL + Attach-Point Harvest Architecture").

**Why:** Rule A was rewritten to admit only Django + PostgreSQL sources.
Indico (`indico/indico`) is Flask. It was correctly admitted under the
*previous* Rule A (Flask + PostgreSQL) and every capability here parsed,
ran, and was proven live under that rule — nothing here was ever found
defective. It fails only the new, narrower Rule A. Retirement is a rule
change, not a finding against this app or its harvest.

**What is preserved here, unchanged:**

- `shelf/` — all ten harvested capabilities (`CAP-0001`–`CAP-0010`), each
  with `source.py`, `PROVENANCE.json` (`symbol_verified: true`), and
  `LICENCE.txt`, moved verbatim from `pack/shelf/event-ticketing/`.
- `form.json` — the filled harvest form, moved verbatim from
  `pack/forms/event-ticketing.form.json`.
- `tree.json` / `tree.txt` — the N4 app tree, moved verbatim from
  `pack/trees/`.
- `host_test.py` — the original host-proof suite (the one referred to
  elsewhere in this pack simply as `host_test.py`), moved verbatim from
  `pack/4_host/`. It is Indico-specific (`INDICO_CONFIG`, Indico routes and
  selectors) despite its generic name.
- `evidence/LIVE_RUN_EVIDENCE.md` — a **copy** (the original stays at
  `pack/evidence/LIVE_RUN_EVIDENCE.md`, per "do not delete evidence" — this
  is real, general architectural evidence about the host/chain system
  itself, proven live via Indico, not solely an admission record).

**What was NOT deleted:**

- `APP-001`'s number in `number_registry.json` — apps are numbered once and
  never reused (N1); the entry is marked `"status": "retired"`, not
  removed.
- `CAP-0001`–`CAP-0010`'s numbers — these represent durable capability
  *concepts* ("register account", "log in", ..., "generate report"),
  independent of which framework implements them. `CAP-0001`/`0002`/`0003`
  ("register account"/"log in"/"log out") are shared with the other two
  retired apps under N2 and remain valid numbers a future Django
  implementation of the same concept would reuse. Their
  `shelf/capabilities/*.json` records are marked `"status": "retired"`
  (see `GOD_MODE/REGISTERS/CHANGE_HISTORY.md` for the full accounting).

**Not listed as admitted:** `shelf/capabilities/CAP-0001.json` through
`CAP-0010.json` and their `IMPL-01` records now read `"status": "retired"`
rather than `"active"`/`"approved"`. Nothing under `pack/shelf/` still
references `event-ticketing`.
