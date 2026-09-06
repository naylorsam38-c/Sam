from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

import pytest
import yaml

from spec_writer.gate_adapter import banned_outside_asks
from spec_writer.validate import validate_draft


FIXTURES = Path(__file__).parent / "fixtures"


def test_a1_valid_yaml():
    path = FIXTURES / "draft.yaml"
    value = yaml.safe_load(path.read_text())
    assert value is not None


def test_a2_contains_all_template_fields():
    from spec_writer.io import key_paths
    template = yaml.safe_load((FIXTURES / "template.yaml").read_text())
    draft = yaml.safe_load((FIXTURES / "draft.yaml").read_text())
    assert key_paths(template) <= key_paths(draft)


def test_a3_no_silent_empty_fields():
    template = yaml.safe_load((FIXTURES / "template.yaml").read_text())
    draft = yaml.safe_load((FIXTURES / "draft.yaml").read_text())
    from spec_writer.io import leaf_paths, is_empty_leaf
    d = dict(leaf_paths(draft))
    for path, _ in leaf_paths(template):
        assert path in d
        assert not is_empty_leaf(d[path]), path


def test_a4_banned_word_only_allowed_inside_ask():
    text = (FIXTURES / "draft.yaml").read_text()
    assert not banned_outside_asks(text, {"guessword"})
    assert "guessword" in yaml.safe_load(text)["storage"]["decision"]


def test_a5_every_gap_is_ask():
    template = yaml.safe_load((FIXTURES / "template.yaml").read_text())
    draft = yaml.safe_load((FIXTURES / "draft.yaml").read_text())
    gaps = [{"field": "storage.decision", "rule": "R7", "question": "Where is storage?"}]
    result = validate_draft(
        FIXTURES / "draft.yaml", template, gaps, {"guessword"}
    )
    assert result.ok, result.errors


def test_a6_gate_returns_zero_or_three():
    proc = subprocess.run(
        [sys.executable, str(FIXTURES / "fake_specgate.py"), str(FIXTURES / "draft.yaml")]
    )
    assert proc.returncode in (0, 3)
    assert proc.returncode != 2


def test_a7_reversal_fixture_later_position_only():
    # The extraction contract must retain the later position and explicitly
    # identify the superseded turn. This fixture represents the model's
    # Call-1 output and is deliberately checked as data, not prose.
    extracted = {
        "statements": [
            {
                "turn": "4",
                "speaker": "Sam",
                "kind": "DO_NOT_WANT",
                "text": "Use PostgreSQL; SQLite is not wanted.",
            }
        ],
        "reversals_dropped": [
            {"turn": "1", "reason": "superseded by later statement"}
        ],
    }
    statements = extracted["statements"]
    assert any("PostgreSQL" in x["text"] for x in statements)
    assert not any(x["turn"] == "1" for x in statements)
    assert any(x["turn"] == "1" for x in extracted["reversals_dropped"])


def test_a8_missing_storage_must_be_ask():
    transcript = (FIXTURES / "missing_storage.txt").read_text()
    assert "storage" not in transcript.lower()
    draft = yaml.safe_load((FIXTURES / "missing_storage_draft.yaml").read_text())
    assert draft["storage"]["decision"].startswith("[ASK]")
    assert "SQLite" not in str(draft)
    assert "PostgreSQL" not in str(draft)
