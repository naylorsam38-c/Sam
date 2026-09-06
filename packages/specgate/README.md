# Spec Builder — the deterministic core, built and tested

Implements the build order from the design document dated 23 August 2026:
steps 1–3 (pure code, no model) built and tested; step 4 (the model steps)
shipped as briefs ready to run against any model.

## What is here

```
specgate.py               the rejection-rule linter, R1–R12  (step 1)
schema/spec.template.yaml the fixed field set                (step 2)
decompose.py              packet validation + materialiser   (step 3)
prompts/2-extract.md      model-step briefs                  (step 4)
prompts/3-gapscan.md
prompts/4-draft.md
examples/good.spec.yaml   the Linked Services spec, complete, passes clean
tests/test_gate.py        22 tests: every rule fires; good spec passes
```

Requires Python 3 + PyYAML (`pip install pyyaml`). Tests: `python3 -m pytest tests/`.

## Usage

```
python3 specgate.py my.spec.yaml
#   exit 0  → releasable (subject to Sam's approval, which is never automated)
#   exit 3  → ask-ready: the ONLY failures are unresolved [ASK] markers —
#             structurally complete; surface the [ASK] list to Sam
#   exit 2  → back to draft, with the JSON failure list to fix

python3 decompose.py my.spec.yaml packets/
#   validates the authored split (D1–D8), writes one YAML per packet with
#   attempt=1 and a deterministic idempotency_key, and plan.json whose
#   "waves" are the parallel execution groups
```

Failures are JSON lines `{rule, path, message}` — a list, not prose — so the
DRAFT step can consume them directly, exactly as the design requires.

## Five decisions the design document left open, and how they are resolved

1. **The pipeline runs GATE before ASK, but R2 fails any unresolved [ASK].**
   Resolved with exit codes: R2-only failures exit 3 ("ask-ready") and route
   to the ASK step; any other failure exits 2 and routes back to DRAFT.
2. **"Empty is not allowed" vs genuinely absent categories** (an app with no
   externals). Silence is still rejected (R1), but *declared* absence is
   accepted: `externals: {none: "fully offline"}`. Declared absence also
   suppresses the per-item rules for that category (R6 has nothing to check).
3. **Human-judgement criteria vs R3/R4.** A criterion marked `human: true`
   needs no runnable verify and is exempt from the banned-word scan; the gate
   counts machine and human criteria separately in its summary, and human
   criteria never count toward automatic pass — exactly as Part Two requires.
4. **R10 is not fully mechanisable.** "Depends on the builder's own report"
   is a judgement; the script implements the mechanical shadow of it — the
   verify string is scanned for self-report tells (builder / confirms /
   manually / attests / self-report / "I verified"). The residue is caught
   only at Sam's approval, and the README says so rather than pretending.
5. **"Decomposition is a script, no model" cannot invent a split.** The split
   is *authored* in the spec (`packets[]`, written at DRAFT, approved by Sam)
   and *validated* mechanically here: required packet fields (D3), inline
   inputs with no cross-packet references (D4), every machine criterion
   covered by exactly one packet (D5), known acceptance ids (D6), an acyclic
   dependency graph with computed parallel waves (D7), and packet budgets
   within the spec budget (D8). The script decides nothing; it refuses.

Two smaller mechanical choices: banned-word matching is word-boundary and
inflection-tolerant ("networks" does not trip "works"; "handled gracefully"
still trips "handles gracefully"), and `[ASK` is matched anywhere in any
string field of the document, so a marker cannot hide in a nested control.

## What this deliberately does not do

No model is imported anywhere in `specgate.py` or `decompose.py` — that is
checkable by reading the imports. The gate does not score, rank, or suggest;
it refuses with rule ids. Sam's approval (step 7) has no code because it must
not have any.
