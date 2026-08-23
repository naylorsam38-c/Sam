# EXTRACT — step 2 brief (model step)

The task is to pull stated requirements from a conversation transcript.
Extraction only. No invention. No inference beyond resolving pronouns.

## Inputs
The raw transcript, verbatim, with line numbers.

## Rules
- Extract only what was actually said. If the speaker did not state it, it is
  not a requirement — it is a gap, and gaps belong to the GAP SCAN, not to you.
- Every extracted item carries the line number(s) where it was said.
- Preserve the speaker's own words for `success` — that field is for humans.
- Contradictions in the transcript are extracted as BOTH statements, marked
  `conflict: [line_a, line_b]`. Never resolve a conflict by choosing.
- If a statement is ambiguous between two readings, extract it once with
  `ambiguous: "<reading A> | <reading B>"`. Never pick one silently.

## Output
A YAML list. Each item:
  - text: the requirement, one sentence
    said_at: [line numbers]
    maps_to: header|intent|surfaces|data|actions|externals|permissions|bounds|acceptance
    conflict: []        # only when present
    ambiguous: ""       # only when present

Returning fewer items than the transcript supports is a failure.
Returning an item with no `said_at` is a failure.
Reporting "nothing stated" for a category is an acceptable outcome.
