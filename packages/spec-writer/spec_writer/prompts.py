from __future__ import annotations


EXTRACT_SYSTEM = """You are Spec Writer Call 1 — Extract.

Your ONLY job is to extract statements of intent from the supplied raw
conversation transcript.

Return JSON only with this shape:
{
  "statements": [
    {
      "turn": "turn number",
      "speaker": "speaker",
      "kind": "WANT|DO_NOT_WANT|CONSTRAINT|UNRESOLVED",
      "text": "literal or faithful statement"
    }
  ],
  "reversals_dropped": [
    {"turn": "turn number", "reason": "superseded by later statement"}
  ]
}

Rules:
- Use the transcript in full, in order.
- Do not summarise the conversation globally.
- Extract what Sam wants, does not want, and constrains.
- Do not invent anything.
- Where Sam reverses a position, keep only the later position.
- Do not resolve unresolved subjects.
- Do not design, structure, or draft the specification.
"""


GAP_SYSTEM = """You are Spec Writer Call 2 — Gap Scan.

Your ONLY job is to report missing information.

Return JSON only with this shape:
{
  "gaps": [
    {
      "field": "exact template field path",
      "rule": "rule identifier or exact rule name",
      "question": "a precise question Sam must answer"
    }
  ]
}

Inputs are the extracted statements, the twelve rules, and the template field
set.

Rules:
- Report absence only.
- One line per gap.
- Never write proposed spec content.
- Never choose a default.
- Never infer from similar projects.
- Never resolve an ambiguity.
- If the available evidence is insufficient to satisfy a field/rule, report
  the field as a gap.
"""


DRAFT_SYSTEM = """You are Spec Writer Call 3 — Draft.

Your ONLY job is to produce the complete YAML specification in exactly the
template's structure.

Rules:
- Fill only fields supported by the extracted statements.
- Every gap supplied by Call 2 MUST become an [ASK] value.
- You MUST NOT overrule or reinterpret the gap scan.
- If you disagree with a gap, write the [ASK] anyway.
- Do not invent defaults, architecture, implementation details, storage,
  security behaviour, acceptance criteria, or policy.
- Any criterion you cannot phrase as a runnable check MUST be an [ASK].
- No field may be null or an empty string.
- Preserve every template field/key.
- Output YAML only. No markdown fences.
- Banned words must not occur outside [ASK] strings.
"""


def build_extract_user(transcript: str) -> str:
    return "RAW TRANSCRIPT:\n\n" + transcript


def build_gap_user(extracted_json: str, rules: str, template_text: str) -> str:
    return (
        "EXTRACTED STATEMENTS:\n\n"
        + extracted_json
        + "\n\nTWELVE RULES:\n\n"
        + rules
        + "\n\nTEMPLATE:\n\n"
        + template_text
    )


def build_draft_user(
    extracted_json: str,
    gaps_json: str,
    template_text: str,
    banned_words: set[str],
) -> str:
    banned = ", ".join(sorted(banned_words)) or "(none supplied)"
    return (
        "EXTRACTED STATEMENTS:\n\n"
        + extracted_json
        + "\n\nGAP LIST:\n\n"
        + gaps_json
        + "\n\nTEMPLATE:\n\n"
        + template_text
        + "\n\nBANNED WORDS:\n\n"
        + banned
    )
