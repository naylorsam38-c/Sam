# End-to-end clean-room proof — round 6, 2026-09-12

What this is: a completely fresh unzip, in an isolated directory, of `build.py` plus a real
(non-fixture-in-the-sense-of-fake — real Flask code, real Playwright browser check) shelf and
template, run exactly once with `python3 build.py` — no test harness, no in-process function calls,
just the real script a person would run — proving every handoff `STAGE_CROSS_REFERENCE.md`
describes actually happens, by inspecting the real files each stage left behind afterward.

**Scope, stated plainly**: this proves stages 1–3 (assemble → prove → readiness/library) — the
whole of what `build.py` itself implements. It uses this session's established real fixture shelf
(Todo List App / CAP-0001, a genuinely working Flask app + real browser journey, not one of the
43 real catalogue app types — see `CANONICAL_SPEC.md` Part B.7 for why: no real shelf/template
exists yet for any of the 43, and harvesting/template-generation aren't part of this session).

## Setup

```
rm -rf /tmp/e2e_cleanroom && mkdir -p /tmp/e2e_cleanroom
cd /tmp/e2e_cleanroom && unzip -q e2e-clean-room.zip
cd round6
# before: no builds/, library/, registry.json, reports/, run_ledger.jsonl — confirmed empty
```

One config edit, and only one: `ALLOW_LAYER3 = True → False` in `build.py`'s own config block.
This scenario has no failing capability, so no repair is ever needed — leaving `ALLOW_LAYER3=True`
with empty `LAYER3_MODEL`/`LAYER3_CREDENTIAL`/`LAYER3_ENDPOINT` would correctly refuse to run at
all (Bible rule 13: empty credentials refuse, never proceed silently), which is real, correct
behavior, not a bug — for a run that's actually expected to need repair, those three settings need
real values, same as every other row in this session's proving table that sets `ALLOW_LAYER3=False`
on purpose for the rows that don't need layer three.

## The real run

```
$ python3 build.py
2  choice read  app_type='Todo List App'
3  template resolved  todo_list_app
4  APP-001  allocated
1  fresh directory  /tmp/e2e_cleanroom/round6/builds/APP-001
5  parts copied  CAP-0001
6  skin laid  skin-001@1.0.0
7  wired  1 screen, 1 button(s)
9  registry written  13/13 invariants passed
10  app.json + locators.json written
template tests ok
11  template tests passed
12  APP-001  assembled  /tmp/e2e_cleanroom/round6/builds/APP-001

RUN-0001
PASS  a person arrives and sees the item list screen
PASS  adding an item through the API returns the created record
PASS  a person clicks add item and sees it appear in the list
3/3 checks passed — PASS
RUN-0001   build finished
BUILT
promoted  promoted APP-001 to library/APP-001 with 1 evidence run(s)
readiness  READY  --  promoted, with registry/app/locators and at least one evidence run report present

EXIT CODE: 0
```

One process, one command, one real run, all three stages, ending at `READY` — the Master Spec's
own top state, only reachable after `build_passed, start_passed, health_check_passed,
browser_tests_passed, evidence_saved, registry_updated` are ALL true (Part A §19).

## Proving each handoff — real file contents, inspected after the run

**Stage 1 → Stage 2**: `builds/APP-001/app.json`, exactly what Stage 2 used to start the real
subprocess:
```json
{"start": ["python3", "modules/CAP-0001/app.py"], "port": 5000, "health": "/health"}
```
Stage 2's own console output (`RUN-0001` / `PASS` lines above) is the direct proof it used exactly
this: port 5000, the declared health path, the declared start command — nothing else was available
to it.

**Stage 2's own unconditional write**: `reports/RUN-0001.json` — written before any repair/gap
decision, regardless of outcome:
```json
{"run": "RUN-0001", "checks_passed": ["CHK-001", "CHK-002", "CHK-020"],
 "checks_failed": [], "browser_check_present": true, "browser_check_passed": true}
```

**Stage 2 → canonical registry (→ Stage 3's gate)**: `run_ledger.jsonl`'s one line for this run:
```json
{"run": "RUN-0001", "app": "APP-001", "outcome": "BUILT", "checks_passed": ["CHK-001", "CHK-002", "CHK-020"], "checks_failed": [], "browser_check_passed": true}
```
and the canonical `registry.json` entry Stage 2 flipped from `candidate` to `active` the instant
this ledger line was written (the same `stage2_prove()` code path, build.py:1215–1221 writes both
in sequence — not two independently-timed events that could drift):
```
APP-001  active
```
This is exactly the signal `stage3_readiness_and_promote()` reads to decide whether to promote —
inspected post-run here, but its *source* is unambiguous: nothing except a real `BUILT` outcome
ever sets canonical status to `active` anywhere in this file (confirmed in `STAGE_CROSS_REFERENCE.md`).

**Stage 3's promotion**: `library/APP-001/` now holds a copy of the proof, plus its evidence:
```
library/APP-001/PROMOTED.json
library/APP-001/app.json
library/APP-001/evidence/RUN-0001.json
library/APP-001/locators.json
library/APP-001/modules/CAP-0001/app.py
library/APP-001/registry.json
library/APP-001/skin.json
```
```json
{"app_id": "APP-001", "promoted_from": ".../builds/APP-001",
 "evidence_runs": ["RUN-0001"], "canonical_status_at_promotion": "active"}
```
`evidence_runs` names the exact run id whose `reports/RUN-0001.json` was copied into
`library/APP-001/evidence/` — the same file inspected two steps up. The promotion did not
re-derive or re-guess a verdict; it copied the one that already existed.

## Two more real checks in the same clean room, same session

**Standalone query, no build run** — proves `--readiness` works as a real CLI against files a
completed run already left behind, independent of the process that made them:
```
$ python3 build.py --readiness "Todo List App" APP-001
READY  --  promoted, with registry/app/locators and at least one evidence run report present
```

**A second real run, same directory** — proves numbering integrity survives a real second
end-to-end pass through all three stages in the same project, not just in isolated single-row
fixtures:
```
$ python3 build.py
...
4  APP-002  allocated
...
BUILT
promoted  promoted APP-002 to library/APP-002 with 1 evidence run(s)
readiness  READY  --  ...

$ APP-001 active
  APP-002 active
```
APP-001 was never touched or reused; APP-002 is a fresh, independent, fully-proven allocation.

## What this does and does not claim

Does: proves, with real files inspected after a real single-process run (no mocks, no stubs, no
in-process shortcuts — a real Flask server, a real Playwright browser, real subprocess start/stop),
that `build.py` really is Sam's "one script" for every stage it implements, and that every claimed
handoff between those stages is real, not asserted.

Does not: prove the harvest → template-generation stages, which aren't part of this session (see
`CANONICAL_SPEC.md` Part B.7). Does not use one of the 43 real catalogue app types, because no real
shelf/template exists yet for any of them — this run demonstrates the mechanism is sound using the
same real (not synthetic-behavior, genuinely working) fixture this session's whole proving table is
built on.
