# Rerunning this proof — clean-room instructions

These are the exact commands to reproduce the full verification claim —
43/43 canonical apps, all 3 composed apps, the compatibility gate, the
dependency-graph and hidden-access audit, the generalization regression
suite, and real end-to-end functional tests — starting from **nothing but
the extracted ZIP**, on a machine that has never seen this project before
and that cannot install anything from the network beyond what's already
vendored here.

## 0. Requirements

- Python 3.9+ (this project was built and proven against 3.11).
- Linux x86_64 is the only platform with a fully offline Python-package
  install path (two vendored wheels — `greenlet`, `markupsafe` — are
  compiled for `cp311`/`manylinux`). Any other OS/CPU/Python version still
  works, but `bootstrap.py` automatically falls back to a normal networked
  `pip install` for those two packages — see `vendor/README.md`.
- A real Chromium binary for one specific check (`CHK-020`, a real
  Playwright-driven browser journey). This is the **one** thing that
  cannot be vendored offline (a browser binary is 300-600MB — no real
  project vendors that into source control). `bootstrap.py` step 3 finds
  one for you automatically if you have one; otherwise it needs one-time
  network access to `playwright install chromium`. Everything else in this
  suite — assembly, the compatibility gate, the dependency-graph audit,
  and every HTTP-level functional check — needs no browser at all.

## 1. Extract and bootstrap

    unzip sam-verification-package.zip -d sam
    cd sam/verification
    python3 bootstrap.py

`bootstrap.py` is idempotent and self-locating (it only ever reads paths
relative to its own file, never the current working directory or anything
from the original development machine). It:

1. Checks the Python version.
2. Installs Flask, Playwright, and their complete dependency trees from
   `vendor/wheels/` with `--no-index` (zero network access) on Linux
   x86_64 + CPython 3.11; falls back to a normal `pip install -r
   requirements.txt` from PyPI on any other platform or if the vendored
   wheels don't match.
3. Looks for a Chromium binary in this order: (a) an
   `PLAYWRIGHT_CHROMIUM_EXECUTABLE` you already set, (b) a system
   `chromium`/`chromium-browser`/`google-chrome` on `PATH`, (c) a real
   network install via `playwright install chromium`. It reports plainly
   which one worked (or that none did) rather than failing silently.

If step 3 finds a browser that isn't the one Playwright's own package
expects at its default path (this can happen with a pre-installed system
Chromium at a different build number than the pinned `playwright` package
expects), export the path it prints before continuing:

    export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/it/printed

## 2. Run the full verification suite

    python3 run_full_verification.py

This one command runs, as real subprocesses, every one of the following,
against files it creates fresh under `verification/` on every run —
`library_build/`, `work/`, `fixtures/`, `gen_prove/`, `functest_scratch/` —
**never** against the committed `OUTPUT_LIBRARY/` or
`NEW_APPS_FROM_LIBRARY/` (all runtime/functional tests operate on
disposable `shutil.copytree` copies with their data files reset to `[]`,
so the shipped library is never mutated by running its own proof):

1. `gen_fixtures.py` + `verify_build.py` + `test_readiness.py` — the
   internal proving-table regression suite (29/29 + 20/20 — see the round
   history below for what each row proves).
2. `build_batch.py` — assembles and proves all 43 canonical app types from
   their real shelf capabilities, expects 43/43 READY.
3. `new_app_event_board.py`, `new_app_fitness_challenge.py`,
   `new_app_course_enrollment.py` — three apps composed from
   never-before-combined capability sets, each expected READY.
4. `prove_generalization.py` — regression-proves that the generic
   capability-generator engines (threshold, bounded-counter,
   symmetric-relationship, calendar/event) reproduce the original
   hand-written apps' behaviour byte-for-byte.
5. `audit_dependency_graph.py` — walks the declared dependency graph and
   the Common Capability Contract v2 across every capability in every
   project at once: missing dependency targets, cycles, contract
   structural violations, and hidden/undeclared data access (checked
   against the real source, not just the declared contract).
6. `functional_tests.py` — real HTTP-level end-to-end tests against real
   running Flask processes for 6 apps spanning both the canonical and
   composed sets.

It writes one machine-readable result to `verification_result.json` and
prints it to stdout; exit code is 0 only if every section passed:

    {
      "sections": {
        "proving_table": {"verify_build_29": "29/29 pass", "verify_build_ok": true, "test_readiness_ok": true},
        "canonical_apps": {"result_line": "43/43 READY", "ok": true, "expected_count": 43},
        "new_composed_apps": {"new_app_event_board.py": true, "new_app_fitness_challenge.py": true, "new_app_course_enrollment.py": true},
        "generalization_regression": {"ok": true, "all_match": true},
        "dependency_graph_audit": {"ok": true, "output": "CLEAN: 0 missing targets, 0 cycles, 0 contract violations, 0 hidden data access across 266 capabilities in 46 projects."},
        "functional_tests": {"ok": true, "passed": 19, "total": 19, "checks": [...]}
      },
      "overall": "PASS"
    }

## 3. If you have no network access at all and no pre-existing browser

Every step above except the one `CHK-020` browser check inside each app's
proving run still works with zero network access. If Chromium truly cannot
be provided, `run_full_verification.py`'s canonical/composed app sections
will report `BROWSER_TEST_FAILED` for that one check per app while every
other section (the compatibility gate, the dependency graph, and all
HTTP-level functional tests, none of which touch a browser) still runs and
reports honestly. This is the one dependency this project deliberately
does not vendor — see `vendor/README.md` for why.

## Manual / individual steps

The commands above are `run_full_verification.py` automated end to end.
To run any one piece by hand instead:

    cd verification
    python3 gen_fixtures.py     # rebuilds the real shelf (§3.6/§3.7 records + aliases.json), templates, choice.json
    python3 verify_build.py     # runs all 23 proving-table rows, 2 extra hardening rows, round 4's generic-check row (G1), and round 5's H-T3 rows (G2/G3) against the real build.py, for real
    python3 test_readiness.py   # round 5: proves readiness_and_library.py's compute_readiness()/promote_to_library() against the real project directories the two runs above just left on disk
    python3 build_batch.py      # all 43 canonical apps
    python3 new_app_event_board.py         # composed app 1/3
    python3 new_app_fitness_challenge.py   # composed app 2/3
    python3 new_app_course_enrollment.py   # composed app 3/3
    python3 prove_generalization.py        # generic-engine regression
    python3 audit_dependency_graph.py      # compatibility gate + dependency graph + hidden-access audit
    python3 functional_tests.py            # real HTTP end-to-end tests, disposable copies only

Requires Flask and Playwright (with Chromium installed) on PATH — see
"Extract and bootstrap" above for how to get both with zero network access
on Linux x86_64 + CPython 3.11.
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
