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
    "wav2lip",          # weights are research-licensed; murky in every fork
    "insightface",      # non-commercial weights; blocks InstantID/IP-Adapter-FaceID
    "flux.1-dev",       # non-commercial; FLUX.1-schnell (Apache-2.0) is the swap
    "sonic",            # portrait animation — repo states non-commercial outright
    "float",            # DeepBrain FLOAT — CC-BY-NC-ND (no commercial, no derivatives)
    # ── Speech traps: permissive CODE, restricted WEIGHTS ──────────────────
    "f5-tts", "f5_tts",  # MIT code, CC-BY-NC-4.0 weights (Emilia dataset)
    "fish-speech", "fish_speech", "openaudio",   # CC-BY-NC-SA-4.0 weights
    "vibevoice",        # MIT label, but Microsoft disclaims commercial use and
                        #   pulled the TTS inference code after misuse
    "canary-1b",        # original NVIDIA Canary is CC-BY-NC-4.0. The -Flash,
                        #   -v2 and Canary-Qwen variants are CC-BY-4.0 and fine.
)

# Components that are USABLE but carry a condition you can grow out of. These are
# not banned — banning them would be wrong — but shipping one without recording
# the condition is how a licence becomes a lawsuit two funding rounds later.
#
# Format: name -> the condition that ends your free use.
CONDITIONAL_COMPONENTS = {
    "ltx-2": "free only under $10M annual revenue; above that a paid Commercial "
             "Use Agreement is mandatory, with 2x liquidated damages for "
             "unlicensed commercial use above the cap. Marketed as open weights.",
    "ltx-video": "same revenue-capped Lightricks licence as ltx-2.",
    "hunyuanvideo": "Tencent Community Licence, NOT Apache-2.0 despite common "
                    "reporting. Licence does not apply in the EU, UK or South "
                    "Korea at all; separate licence required above 100M MAU; "
                    "outputs may not train competing models; attribution required.",
    "duix": "Duix.Avatar/HeyGem community licence: free commercial use only "
            "below 100k users AND $10M revenue. Also offline-only — it does not "
            "do real-time interaction.",
    "heygem": "see 'duix' — same project, renamed.",
    "liveportrait": "MIT code, but pulls InsightFace buffalo_l at inference, "
                    "which is non-commercial. Swap the detector (YuNet) or the "
                    "whole pipeline inherits the restriction.",
    "livetalking": "Apache-2.0, but videos published to Bilibili / WeChat Channels "
                   "/ Douyin must carry a LiveTalking watermark and attribution.",
    "echomimic": "Apache-2.0 itself, but built on Wan2.1-Fun-V1.1-1.3B-InP — the "
                 "base model's own terms still apply and must be checked.",
    "indextts": "Apache-2.0 code, but the WEIGHTS carry a custom bilibili Model "
                "Use Licence requiring prior WRITTEN authorisation for commercial "
                "use. Free tier still needs registration. PRC arbitration.",
    "higgs-audio": "v2 is Apache-2.0 and fine. v3 flips to a Research and "
                   "Non-Commercial Licence — commercial needs a paid Boson "
                   "licence. Also: the tokenizer repo is licensed separately.",
    "minicpm-o": "Apache badge, but commercial use is gated by a registration "
                 "questionnaire and caps (<=5,000 edge devices OR <1M DAU).",
    "kyutai-tts": "CC-BY-4.0 and commercially fine, BUT some bundled voices come "
                  "from the Expresso dataset and are CC-BY-NC. Use only CC0 "
                  "donor voices or your own clone.",
    "voxtral-tts": "Mistral's other 2026 models are Apache-2.0; Voxtral TTS "
                   "specifically is CC-BY-NC-4.0. Commercial is API-only.",
}


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
