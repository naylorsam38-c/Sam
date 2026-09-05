from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

from .io import leaf_paths, is_empty_leaf, key_paths, leaf_key_paths, extract_asks
from .gate_adapter import banned_outside_asks


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_draft(
    draft_path: Path,
    template,
    gaps: list[dict],
    banned_words: set[str],
) -> ValidationResult:
    errors = []
    text = draft_path.read_text(encoding="utf-8")

    try:
        draft = yaml.safe_load(text)
    except Exception as exc:
        return ValidationResult(False, [f"A1 invalid YAML: {exc}"])

    if not isinstance(draft, type(template)):
        errors.append("A2 root type differs from template")

    # A2: mapping structure must contain every template key path.
    missing = key_paths(template) - key_paths(draft)
    if missing:
        errors.append("A2 missing keys: " + ", ".join(".".join(p) for p in sorted(missing)))

    # A3: every template leaf path must exist and be non-empty.
    template_leaves = leaf_key_paths(template)
    draft_leaves = dict(leaf_paths(draft))
    for path in sorted(template_leaves):
        if path not in draft_leaves:
            errors.append(f"A3 missing leaf: {'.'.join(path)}")
        elif is_empty_leaf(draft_leaves[path]):
            errors.append(f"A3 empty leaf: {'.'.join(path)}")

    # A4
    hits = banned_outside_asks(text, banned_words)
    if hits:
        errors.append("A4 banned words outside [ASK]: " + ", ".join(sorted(hits)))

    # A5: each gap field must have an ASK at the named path.
    draft_asks = dict(extract_asks(draft))
    for gap in gaps:
        field = tuple(str(gap["field"]).split("."))
        if field not in draft_asks:
            errors.append(f"A5 missing ASK for gap: {gap['field']}")

    return ValidationResult(not errors, errors)
