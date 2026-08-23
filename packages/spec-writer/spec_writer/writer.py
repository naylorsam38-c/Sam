from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys

from .io import load_text, load_yaml, dump_yaml
from .models import ModelClient, OpenAICompatibleClient
from .prompts import (
    EXTRACT_SYSTEM,
    GAP_SYSTEM,
    DRAFT_SYSTEM,
    build_extract_user,
    build_gap_user,
    build_draft_user,
)
from .gate_adapter import load_banned_words, run_gate
from .validate import validate_draft


@dataclass
class WriterConfig:
    template_path: Path
    rules_path: Path
    gate_path: Path
    drafts_dir: Path = Path("specs/drafts")
    transcripts_dir: Path = Path("specs/transcripts")


@dataclass
class WriteResult:
    draft_path: Path
    transcript_path: Path
    gate_exit_code: int
    gaps: list[dict]


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    return value.strip("-_") or "spec"


def _next_revision(directory: Path, slug: str) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(slug)}-(\d+)\.yaml$")
    numbers = []
    for path in directory.iterdir():
        m = pattern.match(path.name)
        if m:
            numbers.append(int(m.group(1)))
    return max(numbers, default=0) + 1


def _parse_json_object(raw: str, label: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} did not return a JSON object")
    return value


class SpecWriter:
    """
    Drop-in Spec Writer.

    The three model calls are deliberately separate method invocations. Their
    outputs are passed as data; no reasoning from one stage is exposed to
    another beyond the explicit contract data.
    """

    def __init__(self, config: WriterConfig, client: ModelClient | None = None):
        self.config = config
        self.client = client or OpenAICompatibleClient.from_env()

    def write(
        self,
        transcript: str,
        slug: str,
        *,
        prior_spec: Path | None = None,
        answers: dict[str, str] | None = None,
    ) -> WriteResult:
        if not transcript.strip():
            raise ValueError("No transcript supplied. Spec Writer requires a transcript.")

        template_text = load_text(self.config.template_path)
        template = load_yaml(self.config.template_path)
        rules = load_text(self.config.rules_path)
        banned = load_banned_words(self.config.gate_path)

        slug = _slug(slug)
        revision = _next_revision(self.config.drafts_dir, slug)

        transcript_path = self.config.transcripts_dir / f"{slug}.txt"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        if not transcript_path.exists():
            transcript_path.write_text(transcript, encoding="utf-8")

        # CALL 1 — Extract
        extract_raw = self.client.call(
            EXTRACT_SYSTEM,
            build_extract_user(transcript),
        )
        extracted = _parse_json_object(extract_raw, "Extract call")

        # CALL 2 — Gap scan
        gap_raw = self.client.call(
            GAP_SYSTEM,
            build_gap_user(
                json.dumps(extracted, ensure_ascii=False, indent=2),
                rules,
                template_text,
            ),
        )
        gap_result = _parse_json_object(gap_raw, "Gap scan call")
        gaps = gap_result.get("gaps")
        if not isinstance(gaps, list):
            raise RuntimeError("Gap scan did not return a 'gaps' list")

        # Answers are data for the next revision. They do not permit this pass
        # to bypass the three-call architecture.
        if answers:
            extracted = dict(extracted)
            extracted["answers"] = answers
        if prior_spec:
            extracted = dict(extracted)
            extracted["prior_spec"] = prior_spec.read_text(encoding="utf-8")

        # CALL 3 — Draft
        draft_raw = self.client.call(
            DRAFT_SYSTEM,
            build_draft_user(
                json.dumps(extracted, ensure_ascii=False, indent=2),
                json.dumps(gap_result, ensure_ascii=False, indent=2),
                template_text,
                banned,
            ),
        )

        if draft_raw.lstrip().startswith("```"):
            draft_raw = re.sub(r"^```(?:yaml|yml)?\s*", "", draft_raw)
            draft_raw = re.sub(r"\s*```$", "", draft_raw)

        draft_path = self.config.drafts_dir / f"{slug}-{revision}.yaml"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(draft_raw.strip() + "\n", encoding="utf-8")

        result = validate_draft(draft_path, template, gaps, banned)
        if not result.ok:
            raise RuntimeError("Writer acceptance validation failed:\n- " + "\n- ".join(result.errors))

        gate_code = run_gate(self.config.gate_path, draft_path)

        return WriteResult(
            draft_path=draft_path,
            transcript_path=transcript_path,
            gate_exit_code=gate_code,
            gaps=gaps,
        )
