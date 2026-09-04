# Requirements Engine v3 — question graph, interview, validator

What is here

| File | What it is |
|---|---|
| `build_graph.py` | **Single source of truth.** Every question, gate, done-rule, spec field, locked default, derivation and deploy input. Config block at the top. Run it to regenerate the two files below. |
| `question_graph_v3.json` | Machine-readable graph (the artifact the handoff listed as missing). What Nova + the script run from. |
| `INTERVIEW_v3.md` | The readable numbered interview, generated from the graph. Never hand-edited. |
| `validate_graph.py` | Mechanical no-guessing check. `python validate_graph.py question_graph_v3.json` → PASS/FAIL with every violation. `--selftest` breaks a good graph eight ways and proves each break is caught. |
| `AUDIT_FINDINGS.md` | Independent review of the uploaded handoff: 31 divergence points, why its proof runner proves nothing, 4 open decisions for Sam. |
| `VISUAL_QUESTIONS.md` | v3.5: which of the 122 questions become show-and-tap instead of text (40 questions, 20 widgets — form builder, access matrix, pipeline editor, clickable wireframe walkthrough...). Same questions, same gates, same done-rules; the graph now carries a `widget` field. `render_html.py`'s output marks each visual question with a 👁 chip. |
| `interview_v3.html` / `render_html.py` | Styled, browsable rendering of the interview itself (not a spec for any built app). Regenerate with `python render_html.py`. |

Numbers: 122 questions (61 fixed, 61 per-instance), 47 locked defaults, 15 derivations, 11 deploy inputs, 222 spec fields — each spec field has exactly one source (validator-enforced). 40 of the 122 questions carry a visual answer widget (see `VISUAL_QUESTIONS.md`).

Templates (added in the same bundle)

| File | What it is |
|---|---|
| `build_templates.py` | Five app templates reverse-engineered from mature apps (Asana, Pipedrive, Acuity, Odoo core, Xero), authored as pre-filled interview answers. Run to regenerate `templates/*.json` + `CONFIG_MAP.md`. |
| `templates/*.json` | One saved answer-set per template: inventory, fixed answers, per-instance answers keyed `QID:Instance`, `ask_customer` list, feature map. |
| `CONFIG_MAP.md` | Interview answer → template feature, per template, plus how templates combine (union inventories + answers, re-run the checker). |
| `check_template.py` | Proves a template fits the graph: real question IDs, legal options, every role/record/field/stage resolves, and full coverage — every question that fires is answered or explicitly left to the customer. `--all`, `--selftest` (six breaks, all caught). |

Template status: all five PASS (accounting 152 answers, booking 118, CRM 121, ERP 196, PM 120). The interview itself was not changed.

Change a question: edit `build_graph.py`, run `python build_graph.py`, run `python validate_graph.py question_graph_v3.json`. If it prints FAIL, the message says which question or spec field broke and why.

How the graph is meant to be run: the script walks `part_order`; for each part it instantiates once per confirmed item from A.15; for each question it evaluates `gate`; Nova asks in whatever words fit the person; the script evaluates `done` against the answer and re-asks until it passes; `creates` spawns new instances (a record lifecycle becomes a workflow, a stage-change alert becomes a notification); `feeds: OPS` answers are collected by derivation D11 and read back in Z.01.
