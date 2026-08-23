from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import sys


BANNED_NAMES = {
    "BANNED_WORDS",
    "BANNED_WORD",
    "BANNED",
    "FORBIDDEN_WORDS",
    "FORBIDDEN_WORD",
    "FORBIDDEN",
}


def load_banned_words(gate_path: Path) -> set[str]:
    """
    Read a literal banned-word collection from specgate.py without executing it.

    Supported forms:
      BANNED_WORDS = ["foo", "bar"]
      BANNED_WORDS = {"foo", "bar"}
      BANNED_WORDS = ("foo", "bar")
      BANNED_WORDS = {"foo": "...", "bar": "..."}  # keys are used

    If no recognised literal exists, return an empty set rather than inventing
    a banned list. The gate remains authoritative.
    """
    tree = ast.parse(gate_path.read_text(encoding="utf-8"), filename=str(gate_path))
    found: set[str] = set()

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [
            target.id for target in node.targets
            if isinstance(target, ast.Name)
        ]
        if not any(name in BANNED_NAMES for name in names):
            continue
        try:
            value = ast.literal_eval(node.value)
        except Exception:
            continue
        if isinstance(value, dict):
            found.update(str(k) for k in value.keys())
        elif isinstance(value, (list, tuple, set)):
            found.update(str(x) for x in value)

    return {x for x in found if x}


def banned_outside_asks(yaml_text: str, banned_words: set[str]) -> set[str]:
    """
    Scan parsed YAML leaf values. `[ASK]` values are exempt.

    This intentionally works on parsed YAML rather than raw YAML syntax so a
    banned word in a key is still visible to the caller separately.
    """
    import yaml

    from .io import is_ask

    value = yaml.safe_load(yaml_text)
    hits = set()

    def walk(v):
        if isinstance(v, dict):
            for k, child in v.items():
                walk(k)
                walk(child)
        elif isinstance(v, list):
            for child in v:
                walk(child)
        elif isinstance(v, str):
            if is_ask(v):
                return
            for word in banned_words:
                if re.search(rf"\b{re.escape(word)}\b", v, re.IGNORECASE):
                    hits.add(word)

    walk(value)
    return hits


def run_gate(gate_path: Path, draft_path: Path) -> int:
    proc = subprocess.run(
        [sys.executable, str(gate_path), str(draft_path)],
        text=True,
        capture_output=True,
    )
    if proc.returncode not in (0, 3):
        raise RuntimeError(
            "specgate.py returned structural/error code "
            f"{proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc.returncode
