from __future__ import annotations

from pathlib import Path
import yaml

from spec_writer.prompts import EXTRACT_SYSTEM, GAP_SYSTEM, DRAFT_SYSTEM
from spec_writer.writer import SpecWriter, WriterConfig


class FakeClient:
    def __init__(self):
        self.calls = []

    def call(self, system, user):
        self.calls.append((system, user))
        if system is EXTRACT_SYSTEM:
            return """{
              "statements": [
                {"turn":"4","speaker":"Sam","kind":"DO_NOT_WANT","text":"Use PostgreSQL; SQLite is not wanted."}
              ],
              "reversals_dropped": [
                {"turn":"1","reason":"superseded by later statement"}
              ]
            }"""
        if system is GAP_SYSTEM:
            return """{
              "gaps": [
                {"field":"storage.decision","rule":"R7","question":"Where must persistent state be stored?"}
              ]
            }"""
        if system is DRAFT_SYSTEM:
            return """goal:
  statement: "Build the specification writer."
constraints:
  list:
    - "Do not guess."
storage:
  decision: "[ASK] Where must persistent state be stored?"
acceptance:
  check: "Run the executable acceptance checks."
"""
        raise AssertionError("unexpected fourth call")


# The project's real rules file. The placeholder this used to point at listed a
# different R1-R12 than specgate.py implements, and was resolved relative to the
# working directory, so the test only passed when run from the package root.
RULES = Path(__file__).resolve().parents[2] / "specgate" / "specgate_rules.txt"


def test_writer_makes_exactly_three_model_calls(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    gate = fixtures / "fake_specgate.py"
    client = FakeClient()

    writer = SpecWriter(
        WriterConfig(
            template_path=fixtures / "template.yaml",
            rules_path=RULES,
            gate_path=gate,
            drafts_dir=tmp_path / "drafts",
            transcripts_dir=tmp_path / "transcripts",
        ),
        client=client,
    )

    result = writer.write(
        (fixtures / "reversal.txt").read_text(),
        "reversal",
    )

    assert len(client.calls) == 3
    assert result.gate_exit_code == 3

    extracted_user = client.calls[0][1]
    assert "TURN 1" in extracted_user
    assert "TURN 4" in extracted_user

    draft = yaml.safe_load(result.draft_path.read_text())
    assert draft["storage"]["decision"].startswith("[ASK]")
