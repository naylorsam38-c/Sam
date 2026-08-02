# Avatar Source-Image Requirements (spec §21)

A source portrait must be:
- front-facing or nearly front-facing;
- eyes fully visible;
- mouth visible and preferably closed;
- evenly lit;
- sufficient resolution (≥512×512; higher is better);
- free of obstruction over the mouth or jaw;
- inclusive of shoulders when breathing motion is required;
- on a separated or fixed background;
- accompanied by recorded **identity ownership + consent**.

## Preprocessing pipeline (`aura/render/preprocess.py`)
1. **Validate** against the rules above (type/size/dimensions + face checks via a
   commercially-licensed detector — YuNet, **never** InsightFace).
2. **Enhance once** — identity-preserving restoration of the source portrait
   (GFPGAN), cached. Do **not** restore every frame (spec §13) to avoid teeth/eye
   shimmer and drift.
3. **Detect anchors** (mouth/eyes) for landmark stabilisation.
4. **Background lock** — mask so the background stays fixed unless animated.
5. Emit a manifest (`manifest.json`) recording source, identity image, and checks.

Run: `python scripts/preprocess_avatar.py <image> --out assets/<name>_bundle`.
Assets like Nova/Halo/Gaia each get their own validated bundle + consent record.
