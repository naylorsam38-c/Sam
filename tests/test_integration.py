"""Cross-package integration: spec-writer -> real template -> real specgate.

Each package's own suite passes in isolation. Neither exercises the seam
between them: spec-writer's fixtures use a stub gate and an invented
two-field template, so its tests never see schema/spec.template.yaml or
specgate.py. These tests run the writer against the real ones.
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPECGATE = ROOT / "packages" / "specgate"
sys.path.insert(0, str(ROOT / "packages" / "spec-writer"))
sys.path.insert(0, str(SPECGATE))

from spec_writer.gate_adapter import banned_outside_asks, load_banned_words  # noqa: E402
from spec_writer.io import extract_asks  # noqa: E402
from spec_writer.writer import SpecWriter, WriterConfig  # noqa: E402

TEMPLATE = SPECGATE / "schema" / "spec.template.yaml"
GATE = SPECGATE / "specgate.py"
RULES = SPECGATE / "specgate_rules.txt"
GOOD = SPECGATE / "examples" / "good.spec.yaml"

# The marker format used by specgate.py's ASK_RE, the spec template, all three
# model prompts and both question banks.
REAL_ASK = "[ASK: What host and port does this run on, and how does it restart?]"


class StubModel:
    """Stands in for the three model calls. Extract, gap scan, then draft."""

    def __init__(self, gaps, draft):
        self.gaps = gaps
        self.draft = draft
        self.calls = 0

    def call(self, system, user):
        self.calls += 1
        if self.calls == 1:
            return json.dumps({"items": []})
        if self.calls == 2:
            return json.dumps({"gaps": self.gaps})
        return self.draft


def _write(tmp_path, gaps, draft):
    config = WriterConfig(
        template_path=TEMPLATE,
        rules_path=RULES,
        gate_path=GATE,
        drafts_dir=tmp_path / "drafts",
        transcripts_dir=tmp_path / "transcripts",
    )
    model = StubModel(gaps, draft)
    result = SpecWriter(config, client=model).write("Sam: build it\n", slug="probe")
    assert model.calls == 3, "the three-call invariant"
    return result


def test_real_ask_marker_is_recognised():
    """extract_asks matched only a bare '[ASK]', so every real marker was invisible."""
    doc = {"bounds": {"environment": REAL_ASK}}
    assert extract_asks(doc) == [(("bounds", "environment"), REAL_ASK)]


def test_banned_word_inside_a_real_ask_is_exempt():
    """A question may quote a banned word; only answers are held to R4."""
    banned = load_banned_words(GATE)
    assert banned, "banned list must be readable from the real specgate.py"
    text = yaml.safe_dump({"intent": {"success": "[ASK: does the export work as expected?]"}})
    assert banned_outside_asks(text, banned) == set()


def test_banned_word_outside_an_ask_is_still_caught():
    banned = load_banned_words(GATE)
    text = yaml.safe_dump({"intent": {"success": "the export works as expected"}})
    assert banned_outside_asks(text, banned) == {"works", "as expected"}


def test_complete_spec_passes_the_real_gate(tmp_path):
    result = _write(tmp_path, gaps=[], draft=GOOD.read_text(encoding="utf-8"))
    assert result.gate_exit_code == 0


def test_spec_with_an_open_question_is_ask_ready(tmp_path):
    """The normal case: the conversation left something unsettled.

    Before the seam fix this raised 'A5 missing ASK for gap' and never
    reached the gate at all.
    """
    spec = yaml.safe_load(GOOD.read_text(encoding="utf-8"))
    spec["bounds"]["environment"] = REAL_ASK
    gaps = [{"field": "bounds.environment", "ask": REAL_ASK}]

    result = _write(tmp_path, gaps, yaml.safe_dump(spec, sort_keys=False))

    assert result.gate_exit_code == 3, "ask-ready, not releasable and not broken"
    assert result.gaps == gaps


def test_gate_rules_file_covers_every_implemented_rule():
    """The writer is handed specgate_rules.txt as its statement of the rules."""
    import specgate

    text = RULES.read_text(encoding="utf-8")
    for rule in [f"R{n}" for n in range(1, 13)]:
        assert rule in text, f"{rule} is implemented but undocumented for the writer"
    for word in specgate.BANNED:
        assert word in text, f"banned word {word!r} missing from the rules file"


@pytest.mark.parametrize("marker", ["[ASK]", "[ASK: who?]", "  [ASK: who?]  "])
def test_ask_marker_variants(marker):
    assert extract_asks({"a": marker})
