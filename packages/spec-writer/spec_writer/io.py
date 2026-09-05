from __future__ import annotations

from pathlib import Path
import re
import yaml


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_yaml(path: Path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value is None:
        raise ValueError(f"YAML file is empty: {path}")
    return value


def dump_yaml(value, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def leaf_paths(value, prefix=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaf_paths(child, prefix + (str(key),))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from leaf_paths(child, prefix + (str(i),))
    else:
        yield prefix, value


def get_path(value, path):
    cur = value
    for part in path:
        if isinstance(cur, dict):
            cur = cur[part]
        elif isinstance(cur, list):
            cur = cur[int(part)]
        else:
            raise KeyError(path)
    return cur


def set_path(value, path, new_value):
    if not path:
        raise ValueError("cannot set root")
    cur = value
    for part in path[:-1]:
        if isinstance(cur, dict):
            cur = cur[part]
        elif isinstance(cur, list):
            cur = cur[int(part)]
        else:
            raise KeyError(path)
    last = path[-1]
    if isinstance(cur, dict):
        cur[last] = new_value
    elif isinstance(cur, list):
        cur[int(last)] = new_value
    else:
        raise KeyError(path)


def key_paths(value):
    """All mapping key paths, including nested mappings."""
    result = set()
    def walk(v, p=()):
        if isinstance(v, dict):
            for k, child in v.items():
                np = p + (str(k),)
                result.add(np)
                walk(child, np)
        elif isinstance(v, list):
            for i, child in enumerate(v):
                walk(child, p + (str(i),))
    walk(value)
    return result


def leaf_key_paths(value):
    return {path for path, _ in leaf_paths(value)}


def is_empty_leaf(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


# The ASK marker as specgate.py defines it (ASK_RE): "[ASK" followed by optional
# question text and an optional closing bracket. Every prompt, question-bank entry
# and spec template in this repo writes it as "[ASK: <question>]", so matching only
# the bare "[ASK]" form silently misses every real marker.
ASK_RE = re.compile(r"\[ASK(?![\w-])")


def is_ask(value) -> bool:
    return isinstance(value, str) and bool(ASK_RE.match(value.strip()))


def normalize_ask(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def extract_asks(value):
    asks = []
    for path, leaf in leaf_paths(value):
        if is_ask(leaf):
            asks.append((path, normalize_ask(leaf)))
    return asks
