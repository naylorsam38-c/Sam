"""
Single source of truth for what is cleared for commercial use.

Both the runtime provider registry and the build-time gate
(`scripts/licence_audit.py`) read this table, so a licence can never be approved
in one place and banned in the other.

Policy: allow-list only. An unknown licence string is NOT cleared. That is
deliberate — the failure mode of guessing wrong here is shipping someone else's
non-commercial weights in a product you sell.
"""
from __future__ import annotations

# Permissive licences we accept for code and for weights.
APPROVED = frozenset({
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0",
    "LGPL-2.1-or-later", "CC0-1.0", "CC-BY-4.0", "Unlicense",
    # explicit grants recorded after reading the actual model card
    "commercial-use-allowed",
})

# Substrings that mark a licence as non-commercial no matter what else it says.
NONCOMMERCIAL_MARKERS = (
    "non-commercial", "noncommercial", "-nc", "cc-by-nc", "cpml", "s-lab",
    "research only", "research-only", "openrail", "flux-1-dev",
    "stability-ai-community",
)

# Components that must never appear in a commercial build, at any depth.
# Kept here so the runtime and the audit gate ban exactly the same set.
FORBIDDEN_COMPONENTS = (
    "codeformer",       # S-Lab 1.0 — non-commercial
    "xtts", "xtts-v2", "xtts_v2",
    "tts",              # coqui 'TTS' on PyPI bundles XTTS (exact token only)
    "coqui-tts", "coqui-ai-tts",
    "wav2lip",          # non-commercial research weights
    "insightface",      # non-commercial weights; blocks InstantID/IP-Adapter-FaceID
    "flux.1-dev",       # non-commercial; FLUX.1-schnell (Apache-2.0) is the swap
)


def is_noncommercial(licence: str | None) -> bool:
    if not licence:
        return False
    low = str(licence).lower()
    return any(m in low for m in NONCOMMERCIAL_MARKERS)


def commercial_ok(licence: str | None) -> bool:
    """True only for an explicitly approved licence that carries no
    non-commercial marker. Unknown -> False."""
    if not licence:
        return False
    if is_noncommercial(licence):
        return False
    return str(licence) in APPROVED
