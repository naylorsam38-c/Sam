# GAP SCAN — step 3 brief (model step)

The task is to find what the conversation did NOT settle, using the fifteen-
dimension completeness model. Detection only. Never answer a gap yourself.

## Inputs
1. The EXTRACT output (stated requirements with line citations).
2. The question bank: questions/universal.yaml (all 28, always), plus questions/parts.yaml riders for every selected part, the composition questions, and the custom-build detectors. Ask them in that order.
3. The fifteen dimensions:
   1 who · 2 entry · 3 surfaces · 4 actions (endpoint/success/failure/empty/
   loading per control) · 5 data · 6 externals + credential custody ·
   7 identity · 8 permissions · 9 errors · 10 empty states · 11 money and
   limits · 12 environment · 13 rollback · 14 acceptance · 15 out of scope

## Rules
- A dimension is covered only if an extracted item maps to it, or the
  transcript explicitly declared it out of scope. Silence is not an answer.
- Work question by question from the bank. A question is covered only if an
  extracted item answers it — cite the item. Anything else becomes an [ASK]
  carrying the bank question's text verbatim and its id.
- Dimensions 3, 4, 6, 9, 10 get per-item scrutiny: every surface mentioned
  must have every control's endpoint/failure/empty/loading settled or ASKed;
  every external must have credential custody settled or ASKed.
- Do not manufacture gaps for things the fifteen dimensions do not cover.

## Output
A YAML list:
  - dimension: 6
    ask: "[ASK: Who supplies the Google OAuth client secret, and where is it pasted?]"
    candidates: ["Sam pastes into .env", "already present in .env from the old build"]
    because: "transcript line 41 mentions Gmail OAuth but never credentials"

An empty list is an acceptable outcome only when all fifteen dimensions are
covered; state which extracted item covers each.
