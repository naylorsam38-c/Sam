# Defect Report Generator — component 5 of the chain

Turns the Live Playwright Tester's real report JSON
(`report_normal.json` / `report_backend_down.json`) into a list of defects,
each naming the exact numbered spec id it traces back to (`SCR-nnn`,
`ACT-nnn`) with what the spec declared and what was actually observed.
No judgement calls: every rule is a direct, named comparison between a value
the spec declares and a value the report recorded. Nothing the reports don't
already cover is reported on, and a failed request to a third party (this
sandbox's own egress policy denying `accounts.google.com`, for instance —
see `packages/playwright-tester/README.md`) is never attributed to the app,
only a failed request to the app's own origin.

## Output

`DEFECTS.json` — machine-readable, what the fix-and-retest loop (component 6)
hands back to the Builder. `DEFECTS.md` — the same thing, readable. Exit code
0 with zero defects, 1 otherwise — the same convention as every other gate
in this chain (`specgate.py`, `check_template.py`, `validate_graph.py`).

## Tested against real reports, not hand-written fakes

`tests/test_defect_report.py` runs the real Builder and the real Playwright
tester to produce real report JSON — a clean pass reports zero defects, and
the same wrong-`on_unavailable`-message scenario
`tests/test_playwright_tester.py` already proves the tester catches produces
exactly one defect, correctly attributed to `SCR-001`, with the real expected
and observed text as evidence.
