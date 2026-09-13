#!/usr/bin/env python3
"""
canonical_app_types.py — the ONE spelling of each of the 43 app-type names,
plus a normalizer so a document written with a different (but equivalent)
spelling never silently breaks build.py's exact-string app_type matching.

Why this exists: the Master Build-to-Library Specification's own 43-item
list and TEMPLATE_REFERENCE.md's list agree on all 43 app types in content
and order, but disagree on punctuation for 7 of them ("and" vs "&" -- e.g.
"calendar and scheduling" vs "calendar & scheduling"). build.py checks
choice.json's app_type by exact string membership against APPS_LIST.md, and
slugifies that exact string (including "&", verbatim) into the template
filename it looks for. Left alone, those 7 app types would silently hit
BROKEN choice app_type / BROKEN template not found the day APPS_LIST.md and
a template happen to use different spellings.

The call this file makes: canonical spelling is "and" (the Master Spec's own
wording), because build.py turns app_type directly into a filesystem path
and "and" has no special characters, unlike "&". This is a reversible,
one-file decision -- if Sam wants "&" instead, change CANONICAL_APP_TYPES
below and every consumer of this file inherits the change.
"""

from typing import Dict, List, Tuple

# ==============================================================================
# CONFIGURATION BLOCK — one comment per setting, above all logic.
# ==============================================================================

# The one true spelling of every app type, in the Master Spec's own order
# (1-43). If altered: whatever string sits here becomes the app_type that
# must appear, verbatim, in APPS_LIST.md, every choice.json, and every
# template's filename slug for that app type.
CANONICAL_APP_TYPES: List[str] = [
    "todo list", "note taking", "habit tracker", "calendar and scheduling",
    "expense tracker", "invoicing", "accounting ledger", "CRM",
    "helpdesk ticketing", "payroll", "project management", "team chat",
    "video conferencing", "email client", "file storage and sync",
    "collaborative document editor", "spreadsheet", "form builder and survey",
    "e-commerce storefront", "multi-vendor marketplace", "auction",
    "food delivery", "ride hailing", "parcel tracking", "appointment booking",
    "property rental", "event ticketing", "restaurant POS",
    "inventory and warehouse", "fleet tracking", "dating", "social feed",
    "photo sharing", "short video feed", "music streaming", "video streaming",
    "podcast", "fitness tracking", "meditation and wellbeing",
    "language learning", "online course LMS", "quiz and flashcards",
    "recipe and meal planning",
]

# Known alternate spellings that must resolve to a canonical name above,
# keyed by the alternate string exactly as some other document spells it. If
# altered: add a line here any time a new document uses a different spelling
# for an app type that already has a canonical entry -- never silently guess
# which canonical name an unrecognized string means.
KNOWN_ALIASES: Dict[str, str] = {
    "calendar & scheduling": "calendar and scheduling",
    "file storage & sync": "file storage and sync",
    "form builder & survey": "form builder and survey",
    "inventory & warehouse": "inventory and warehouse",
    "meditation & wellbeing": "meditation and wellbeing",
    "quiz & flashcards": "quiz and flashcards",
    "recipe & meal planning": "recipe and meal planning",
}

# ==============================================================================
# END OF CONFIGURATION BLOCK
# ==============================================================================

_CANON_SET = set(CANONICAL_APP_TYPES)
assert len(CANONICAL_APP_TYPES) == 43, f"expected 43 canonical app types, found {len(CANONICAL_APP_TYPES)}"
assert len(_CANON_SET) == 43, "duplicate canonical app type name"
for alt, canon in KNOWN_ALIASES.items():
    assert canon in _CANON_SET, f"alias {alt!r} points at {canon!r}, which is not a canonical name"


def normalize(app_type: str) -> str:
    """Returns the canonical spelling for app_type. Raises ValueError (never
    guesses) if app_type is neither a canonical name nor a known alias."""
    if app_type in _CANON_SET:
        return app_type
    if app_type in KNOWN_ALIASES:
        return KNOWN_ALIASES[app_type]
    raise ValueError(f"{app_type!r} is not a canonical app type or a known alias — "
                      f"add it to KNOWN_ALIASES rather than guessing")


def verify_list(candidate: List[str], label: str) -> Tuple[List[str], List[str], List[str]]:
    """Checks `candidate` (43 app-type strings, any order) against the
    canonical list. Returns (exact_matches, normalized_matches, unresolved) —
    unresolved is never silently dropped; it means this candidate list
    contains a name this file doesn't know how to canonicalize."""
    exact, normalized, unresolved = [], [], []
    for item in candidate:
        if item in _CANON_SET:
            exact.append(item)
        elif item in KNOWN_ALIASES:
            normalized.append(item)
        else:
            unresolved.append(item)
    return exact, normalized, unresolved


if __name__ == "__main__":
    # Self-check: every canonical name normalizes to itself, every known
    # alias normalizes to its canonical name, and an unknown string is
    # refused rather than guessed.
    for name in CANONICAL_APP_TYPES:
        assert normalize(name) == name
    for alt, canon in KNOWN_ALIASES.items():
        assert normalize(alt) == canon
    try:
        normalize("not a real app type")
        raise AssertionError("normalize() should have refused an unknown name")
    except ValueError:
        pass
    print(f"OK — {len(CANONICAL_APP_TYPES)} canonical names, {len(KNOWN_ALIASES)} known aliases, "
          f"self-check passed")
