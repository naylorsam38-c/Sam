# Aura Licensing Register (spec §22, §23, §26)

> ## ⚠️ STATUS: NOT "LICENSING VERIFIED"
> This repository must **not** be labelled "licensing verified" until the
> complete **transitive** dependency tree, all model weights, voices, datasets
> and test assets have passed the audit gate in `scripts/licence_audit.py`
> against a fully-filled `config/dependency_lock.yaml` (exact repo URL, commit
> hash, package version, weight filename, SHA-256, licence per component).
> Until then the machine status is **PENDING**. Run `python scripts/licence_audit.py`.
>
> **The build FAILS (audit gate) if any of these are true:**
> 1. a dependency has no licence;
> 2. code licence and model-weight licence differ and either is unapproved;
> 3. a model downloads weights dynamically from an unverified source;
> 4. test assets or datasets carry non-commercial restrictions;
> 5. InsightFace weights appear anywhere in the final image;
> 6. CodeFormer, XTTS-v2 or Wav2Lip are included (even transitively).

**Rule this project follows:** open-source is *not* automatically free for every
commercial use. Every component below is classified for commercial use, and any
licence / redistribution / patent / model-use / voice-cloning risk is flagged.
This register is the source of truth; the default `config/aura.yaml` is chosen to
stay in the **green** column.

> This is engineering due-diligence, not legal advice. Confirm each item against
> its current upstream licence and, for anything amber/red, get sign-off from a
> lawyer before commercial release.

## Verdict legend
- 🟢 **Clear** — permissive/commercial-ok (MIT/Apache/BSD or explicit commercial grant)
- 🟡 **Conditional** — commercial-ok *only if* a condition is met (swap a sub-model, attribution, OpenRAIL use limits, MAU caps)
- 🔴 **Blocked for commercial** — non-commercial licence; do not ship without a separate paid/again licence

## Core infrastructure
| Component | Role | Licence | Commercial | Notes / conditions |
|---|---|---|---|---|
| LiveKit (server + SDKs) | WebRTC transport | Apache-2.0 | 🟢 | Self-host; only public surface |
| aiortc | local WebRTC (reference client) | BSD-3 | 🟢 | Optional path |
| FastAPI / Uvicorn / httpx / PyYAML | gateway + glue | MIT/BSD/Apache | 🟢 | — |
| NumPy / OpenCV (headless) | rendering math | BSD / Apache-2.0 | 🟢 | Use `opencv-python-headless` |
| ffmpeg | mux / encode | LGPL-2.1+ (GPL if built with GPL bits) | 🟡 | Use an LGPL build; **see codec row for H.264 patents** |
| Prometheus client | metrics | Apache-2.0 | 🟢 | — |

## Speech-to-text
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| faster-whisper (code) | MIT | 🟢 | — |
| Whisper weights (OpenAI) | MIT | 🟢 | Commercial ok |
| Silero VAD | MIT | 🟢 | Commercial ok |

## Text-to-speech
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| **Kokoro-82M** (default) | Apache-2.0 | 🟢 | Weights Apache-2.0; already used in commercial APIs. **Recommended.** |
| Piper | MIT (code) | 🟡 | Code MIT, but **per-voice** licences vary (CC0/CC-BY/other). Verify each voice; keep attribution for CC-BY. |
| **XTTS-v2 / Coqui TTS** | Coqui Public Model License (CPML) | 🔴 | **Non-commercial.** Do not use commercially without a separate Coqui licence. Aura config excludes it. |
| Voice cloning (any engine) | — | 🟡/🔴 | Cloning a real person's voice needs that person's **consent**; some jurisdictions restrict it. Only clone voices you own/licensed. |

## Facial animation / lip-sync
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| **MuseTalk** (default lip-sync) — code | MIT | 🟢 | Code is MIT. |
| **MuseTalk** — trained model | "commercial use allowed" (per official repo) | 🟡 | Commercial use of the model is allowed, BUT (a) every **bundled dependency** must be audited + pinned separately, and (b) MuseTalk's **supplied test data / datasets are NON-COMMERCIAL** and must **not** be shipped or reused. Do NOT record MuseTalk as OpenRAIL-M. Not clear until the dependency lock + audit gate passes. |
| **LivePortrait** (motion) | MIT (code) | 🟡 | Code is MIT, **but ships InsightFace detection models that are NON-COMMERCIAL**. For commercial use you **must replace the InsightFace detector** (Aura default detector = OpenCV YuNet). The adapter refuses `detector=insightface`. |
| InsightFace models | InsightFace non-commercial | 🔴 | Research/non-commercial only. Enterprise licence sold separately. Avoid; swap for YuNet/commercial RetinaFace. |
| **Wav2Lip** weights | Non-commercial research | 🔴 | Original weights are non-commercial. Do not use commercially. MuseTalk preferred. |
| SadTalker | mixed (code Apache; some sub-models restricted) | 🟡 | If ever used, audit each sub-model separately. |

## Face enhancement / restoration
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| **GFPGAN** (default) | Apache-2.0 (code) | 🟢 | Verify weight provenance; generally commercial-ok. |
| **CodeFormer** | **S-Lab License 1.0** | 🔴 | **Non-commercial.** Explicitly requires contacting authors for commercial use. Aura's `Enhancer` refuses it unless `allow_noncommercial=True`. |
| RealESRGAN (if used for upscale) | BSD-3 / mixed | 🟡 | Some weights differ from code licence; verify. |

## Face detector (needed by motion/preprocess)
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| **OpenCV YuNet** (default) | Apache-2.0 / permissive | 🟢 | Use this instead of InsightFace. |
| InsightFace detector | non-commercial | 🔴 | See above. |

## Codec / patents
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| **VP8 / VP9** (default) | BSD + **royalty-free** patent grant | 🟢 | Aura default codec — avoids patent fees. |
| AV1 | royalty-free (AOMedia) | 🟢 | Higher CPU; optional. |
| H.264 | patent pool (Via LA / MPEG-LA) | 🟡 | Software is fine; **commercial distribution can owe patent royalties**. Only enable knowingly. |

## The external brain (out of Aura's scope, noted for completeness)
| Component | Licence | Commercial | Notes |
|---|---|---|---|
| Command Desk / your LLM | your choice | — | Aura does not include or relicense it. If you run Llama, the **Llama Community License** permits commercial use but adds conditions (e.g. "Built with Llama" attribution and a >700M-MAU clause). That's your existing decision, unaffected by Aura. |

## Per-asset register (fill in at deploy time)
Track for **every** weight/voice/avatar you actually install:

| Asset | Version | Download source | SHA-256 | Licence | Commercial condition | Attribution required | Redistribution allowed |
|---|---|---|---|---|---|---|---|
| kokoro-82M | … | huggingface.co/hexgrad/Kokoro-82M | … | Apache-2.0 | none | no | yes |
| musetalk (code) | pin commit | github.com/TMElyralab/MuseTalk | … | MIT | none | no | yes |
| musetalk (model weights) | pin | huggingface.co/TMElyralab/MuseTalk | … | commercial-use-allowed | audit+pin bundled deps | no | yes |
| musetalk TEST DATA | — | (do NOT ship) | — | **NON-COMMERCIAL** | must not reuse/redistribute | — | **no** |
| gfpgan v1.4 | … | github.com/TencentARC/GFPGAN | … | Apache-2.0 | verify weights | no | yes |
| yunet | … | opencv zoo | … | permissive | none | no | yes |
| nova.png (avatar) | … | your asset | … | **you must own/consent** | identity consent recorded | — | — |

## Commercial-safe starting route (corrected)
- **Lip sync:** MuseTalk — but **audit and pin every dependency and weight**; do not ship its test data.
- **TTS:** Kokoro.
- **Motion:** LivePortrait **only after completely removing InsightFace pretrained models** and replacing its face-detection/landmark dependency with a commercially-permitted alternative (Aura default: YuNet).
- **Restoration:** **do not use CodeFormer.**
- **Voice cloning:** **do not use XTTS-v2.**
- **Fallback lip sync:** **do not use Wav2Lip.**

## Bottom line
- **Candidate green stack (PENDING full transitive audit):** LiveKit + faster-whisper + Silero + Kokoro + MuseTalk(+audited deps) + GFPGAN + YuNet + VP8.
- **Never ship commercially:** XTTS-v2, CodeFormer, Wav2Lip weights, InsightFace models — and the audit gate fails the build if any appear transitively.
- **Honour conditions:** MuseTalk bundled-dep audit + test-data exclusion, per-voice licences (Piper), H.264 patents, and avatar-identity consent (§21).
- **Not "licensing verified"** until `scripts/licence_audit.py` returns PASS on a complete `config/dependency_lock.yaml`.
