# Rerunning this proof

cd verification
python3 gen_fixtures.py     # rebuilds the real shelf (§3.6/§3.7 records + aliases.json), templates, choice.json
python3 verify_build.py     # runs all 23 proving-table rows, 2 extra hardening rows, round 4's generic-check row (G1), and round 5's H-T3 rows (G2/G3) against the real build.py, for real
python3 test_readiness.py   # round 5: proves readiness_and_library.py's compute_readiness()/promote_to_library() against the real project directories the two runs above just left on disk

Requires Flask and Playwright (with Chromium installed) on PATH.
build.py itself has no dependencies beyond the Python standard library.

## Round 4 addition

Row G1 proves build_checks()'s generic compute-capability check generator
(see ../review.md, "Round 4") against two capabilities (CAP-0010, CAP-0011)
the generator has never had a branch written for by id, plus a third
(CAP-0012) with no declared ROUTE/METHOD at all, to prove it skips rather
than guesses. 27/27 total.

## Round 5 addition

Rows G2/G3 prove the H-T3 subset-match change to `match_contract()` — a
capability stricter/broader than its slot requires still binds (G2), a
capability genuinely missing a required security constraint still HELDs
(G3). 29/29 total in `verify_build.py`.

`test_readiness.py` is new: it proves round 5's readiness/library logic
against 13 real fixture rows (every readiness state a real build.py run can
reach), plus the promotion accept/refuse paths and the full
`PROVEN → LIBRARY_STORED → READY` sequence against a real `BUILT` app. 20/20.

## Round 6 addition

Readiness/library (round 5's separate `readiness_and_library.py`) is folded
into `build.py` itself as stage three — see `../CANONICAL_SPEC.md`,
`../STAGE_CROSS_REFERENCE.md`, `../END_TO_END_PROOF.md`, and `../review.md`
"Round 6" for the full writeup. `test_readiness.py` now calls
`python3 build.py --readiness ...` / `--promote ...` as real subprocesses
(matching exactly how a person runs it) instead of importing a module.
Several `verify_build.py` assertions were fixed for the new trailing
`promoted`/`readiness` output line stage three now always prints. Still
29/29 + 20/20.

## Round 7 addition

`gen_real_todo_app.py` — a real, rerunnable generator for "todo list" (item
#1 of Sam's real 43 app-type list), sourced from the real, published
TodoMVC spec, not the CAP-0001 fixture every row above uses. Run it with:

    python3 gen_real_todo_app.py    # writes real_todo_proof/{shelf,templates,APPS_LIST.md,choice.json}
    cp ../build.py real_todo_proof/build.py
    # edit real_todo_proof/build.py: ALLOW_LAYER3 = True -> False (no repair needed, same as END_TO_END_PROOF.md)
    cd real_todo_proof && python3 build.py

Proving this surfaced a real gap in `build_checks()` (host-check gating
hardcoded to `"CAP-0001"`, and the generic compute-check generator only ever
proven against zero-input GETs) — see `../REAL_APP_PROOF.md` and
`../review.md` "Round 7" for the full writeup and every real transcript,
including a separate real restart-survives-data proof. Every fix was
reproven against this file's own suite before and after: still 29/29 +
20/20, zero regressions, plus the new real app's own 9/9.
