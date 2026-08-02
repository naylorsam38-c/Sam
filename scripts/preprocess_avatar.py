#!/usr/bin/env python3
"""
Validate + prepare an avatar source image (spec §21, §13 one-time enhancement).

    python scripts/preprocess_avatar.py assets/nova.png --out assets/nova_bundle
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aura.render.preprocess import build_bundle, validate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", default="assets/bundle")
    ap.add_argument("--enhancer", default="gfpgan")
    args = ap.parse_args()

    chk = validate(args.image)
    print("validation:", json.dumps(chk.__dict__, indent=2))
    if not chk.ok:
        print("Source FAILED hard requirements. Fix before use.")
    manifest = build_bundle(args.image, args.out, args.enhancer)
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print("bundle ->", args.out)


if __name__ == "__main__":
    main()
