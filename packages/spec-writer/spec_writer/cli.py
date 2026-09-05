from __future__ import annotations

import argparse
from pathlib import Path

from .writer import SpecWriter, WriterConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Spec Writer — Component 2b")
    p.add_argument("--transcript", required=True, type=Path)
    p.add_argument("--template", required=True, type=Path)
    p.add_argument("--rules", required=True, type=Path)
    p.add_argument("--gate", required=True, type=Path)
    p.add_argument("--slug", required=True)
    p.add_argument("--drafts-dir", type=Path, default=Path("specs/drafts"))
    p.add_argument("--transcripts-dir", type=Path, default=Path("specs/transcripts"))
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    transcript = args.transcript.read_text(encoding="utf-8")

    config = WriterConfig(
        template_path=args.template,
        rules_path=args.rules,
        gate_path=args.gate,
        drafts_dir=args.drafts_dir,
        transcripts_dir=args.transcripts_dir,
    )

    result = SpecWriter(config).write(transcript, args.slug)

    print(f"draft={result.draft_path}")
    print(f"transcript={result.transcript_path}")
    print(f"gate_exit={result.gate_exit_code}")
    print(f"gaps={len(result.gaps)}")
    return result.gate_exit_code
