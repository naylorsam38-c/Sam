# Fix-and-retest loop + Definition of Done — component 6

One cycle: **Build → start the real server → Live Playwright Tester
(normal, then backend-down) → stop the server → Defect Report.** Definition
of Done is exactly what it has to be: the run passes only when the defect
count is zero across both modes — never because the build alone succeeded.

## What "the Builder fixes the defects" means here

`packages/builder/builder.py` has no model in it. Every generation rule is a
fixed, explicit function of the spec, and it refuses on anything it doesn't
recognise rather than inventing (see its own README). It cannot rewrite its
own generation rules — that is real engineering, done between runs of this
script, not something an automated retry can substitute for.

So the loop does exactly what re-running is honestly good for: it tells a
flake apart from a real defect by re-running the identical cycle against the
identical, unchanged Builder output, and stops as soon as either a cycle
comes back clean, or **two consecutive cycles report the same defects** —
which proves re-running alone will not fix it, and it says so rather than
burning through its iteration budget pretending otherwise. It never reports
`done: True` because a defect stopped reappearing on its own.

## Definition of Done, precisely

```json
{"done": true, "cycles_run": 1, "history": [...]}
```

`done` is `true` only when a cycle's defect list is empty. A build that
succeeds but whose app fails Playwright verification is `done: false`, with
the defects that failed it. That is the whole point of the gate — see the
task's own line 6: not done because it built, done because the spec is
satisfied *and* the real application passed verification.

## Tested with a real, deliberately injected defect

`tests/test_loop.py` proves the loop against a clean spec (done in one
cycle) and against a **real** defect: a temporary, labelled copy of
`builder.py` with one line changed (the integration screen's error text
ignores the spec's real `on_unavailable` message) — the same
break-it-on-purpose pattern `validate_graph.py`'s and `check_template.py`'s
own `--selftest` already use, not a stand-in for a real product's answers.
The loop correctly reports `done: False`, stops after exactly two cycles
(not the full budget) once the same defect repeats, and names the defect
that needs a real fix.

## Usage

```bash
python run_chain.py SPEC.json -o out/ --port 8990 --iterations 3 \
    --oauth-client-id <client-id-if-the-spec-has-an-integration>
```
