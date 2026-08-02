#!/usr/bin/env python3
"""
Build an avatar bundle: portrait + driving loop + provenance manifest.

    # generate a synthetic face (needs a GPU for photoreal; degrades gracefully)
    python scripts/make_avatar.py --name nova --prompt "portrait of a woman, ..."

    # use a portrait you already own (a real person needs consent recorded)
    python scripts/make_avatar.py --name sam --image photo.png \
        --subject "Sam Naylor" --consent-ref "release-2026-04-11"

    # check a bundle still matches what was cleared
    python scripts/make_avatar.py --verify assets/generated/nova

Point the runtime at the result:
    avatar.source_image:  assets/generated/<name>/portrait.png
    avatar.driving_video: assets/generated/<name>/driving.mp4
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aura.config import Config  # noqa: E402
from aura.studio import AvatarStudio, verify_bundle  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="avatar")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--image", help="use an existing portrait instead of generating")
    ap.add_argument("--subject", help="real person's name (with --image)")
    ap.add_argument("--consent-ref", help="signed release reference (with --image)")
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--verify", metavar="BUNDLE_DIR",
                    help="verify an existing bundle and exit")
    args = ap.parse_args()

    if args.verify:
        problems = verify_bundle(args.verify)
        if problems:
            print(f"BUNDLE INVALID: {args.verify}")
            for p in problems:
                print("  ✗", p)
            return 2
        print(f"BUNDLE OK: {args.verify} — hashes match, provenance sufficient")
        return 0

    if not args.prompt and not args.image:
        ap.error("supply --prompt (generate) or --image (use your own)")

    cfg = Config.load()
    studio = AvatarStudio(cfg.studio, fps=cfg.avatar.output_fps)
    try:
        bundle = await studio.build(
            prompt=args.prompt, name=args.name, source_image=args.image,
            subject=args.subject, consent_reference=args.consent_ref,
            seconds=args.seconds, seed=args.seed)
    except Exception as e:
        print(f"BUILD FAILED: {e}")
        return 1

    print(json.dumps(bundle.summary(), indent=2))
    print("\nPoint config/aura.yaml at it:")
    print(f"  avatar.source_image:  {bundle.portrait}")
    print(f"  avatar.driving_video: {bundle.driving_video}")
    for n in bundle.notes:
        print(f"  note: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
