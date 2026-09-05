# Nova — idea to verified app

Everything from the Nova project in one repository: nine research reports, three
code packages, and the plan that connects them.

Command Desk itself: **[COMMAND_DESK_INTERVIEW_ANSWERS.md](COMMAND_DESK_INTERVIEW_ANSWERS.md)**
(the answers that govern it) compiled into **[COMMAND_DESK_COMPILE.md](COMMAND_DESK_COMPILE.md)**
(numbered items, part bindings, and the live proof) plus
[PROPOSED_ANSWERS.md](PROPOSED_ANSWERS.md) (the plumbing filled in under
0.01 = guided, for Sam to correct).

**Start with [PLAN.md](PLAN.md)** — where this is, what is missing, and the route.

## Layout

```
PLAN.md                      status, gap analysis, and the build order
docs/research/               the nine reports (Markdown is the source of truth)
  INDEX.md                   what each report covers
  exports/                   the same reports as PDF and Word, plus the combined PDF
packages/requirements-engine/ the v3 question graph (122 questions), its two
                             validators, and five app templates
packages/assembly-engine/    completed answers -> one numbered spec (component 2)
packages/builder/            numbered spec -> a real, running application (component 3)
                             + shelf.py: the parts shelf's lifecycle (TESTED -> PRODUCT_QUALIFIED -> FROZEN),
                             source revisions, receipts, provenance — see PARTS_SHELF.md "Lifecycle"
packages/playwright-tester/  numbered spec -> real Playwright against the live app (component 4)
                             + seams.py: seam journeys between shelf parts; the only thing that
                             can make a part PRODUCT_QUALIFIED
packages/defect-report/      real Playwright reports -> defects tied to numbered spec ids (component 5)
packages/loop/               fix-and-retest loop + Definition of Done gate (component 6)
packages/frontdoor/          eight questions a non-technical person can answer -> a built,
                             tested app with three interfaces. catalogue.py is the honest list
                             of what can and cannot be built — see packages/frontdoor/README.md
packages/interfaces/         the five families built end to end + 15 working interfaces
                             (3 designs x 5 families), every control driven in real Chromium
                             — see FINDINGS_2026-09-05_INTERFACES.md
packages/specgate/           the spec gate: R1-R12 linter + D1-D8 decomposer
packages/spec-writer/        transcript -> spec draft, in three model calls
packages/crawler/            deterministic browser smoke-test harness
packages/hands/              the paperwork-execution engine: defined workflows,
                             value provenance, a backend-enforced Trust Gate,
                             an operator screen, and 29 live tests
tests/                       cross-package integration tests
```

## Running it

```bash
pip install pyyaml pytest
pytest                       # 227 tests across every package (a dozen of them drive real Chromium)
```

The requirements engine is self-contained and needs no model:

```bash
cd packages/requirements-engine
python validate_graph.py question_graph_v3.json   # the graph is sound
python validate_graph.py --selftest               # ...and the validator bites
python check_template.py --all                    # all five templates fit the graph
```

The pipeline, as far as it currently reaches:

```bash
# 1. transcript -> draft spec (needs a model endpoint; see packages/spec-writer)
python -m spec_writer \
  --transcript specs/transcripts/my-idea.txt \
  --template packages/specgate/schema/spec.template.yaml \
  --rules    packages/specgate/specgate_rules.txt \
  --gate     packages/specgate/specgate.py \
  --slug     my-idea

# 2. gate it
python packages/specgate/specgate.py specs/drafts/my-idea-1.yaml
#   0 = releasable   3 = ask-ready (open questions)   2 = back to draft

# 3. after approval, split into work packets
python packages/specgate/decompose.py my-idea.yaml packets/

# 4. smoke-test a running app (discovery only, not proof — see PLAN.md)
python packages/crawler/crawler.py --url http://localhost:3000 --same-origin-only
```

Steps 1-3 are built and tested. Turning packets into a running application, and
proving that the running application matches the spec, are not built. That is
what PLAN.md is about.

## The one invariant

A spec is refused, never scored. `specgate.py` imports no model, which is
checkable by reading its imports. It does not rank or suggest; it returns rule
ids and exits non-zero. Human approval has no code because it must not have any.
