# Nova — idea to verified app

Everything from the Nova project in one repository: nine research reports, three
code packages, and the plan that connects them.

**Start with [PLAN.md](PLAN.md)** — where this is, what is missing, and the route.

## Layout

```
PLAN.md                      status, gap analysis, and the build order
docs/research/               the nine reports (Markdown is the source of truth)
  INDEX.md                   what each report covers
  exports/                   the same reports as PDF and Word, plus the combined PDF
packages/specgate/           the spec gate: R1-R12 linter + D1-D8 decomposer
packages/spec-writer/        transcript -> spec draft, in three model calls
packages/crawler/            deterministic browser smoke-test harness
tests/                       cross-package integration tests
```

## Running it

```bash
pip install pyyaml pytest
pytest                       # 40 tests across all three packages
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
