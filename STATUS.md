# Build Status & Honest State (read me)

## This revision applied your licensing correction
- **MuseTalk is NOT recorded as OpenRAIL-M.** Corrected everywhere (register,
  config, adapter, requirements) to: **code = MIT; trained model = commercial-use
  allowed; bundled dependencies must be audited separately; supplied test data is
  non-commercial and must not be shipped/reused.**
- Added **`config/dependency_lock.yaml`** — a lock + licence manifest with the
  mandatory fields (repo URL, commit hash, package version, weight filename,
  SHA-256, code licence, weight licence) for every component.
- Added **`scripts/licence_audit.py`** — a build gate that **fails** on: no
  licence; code/weight licence conflict with an unapproved side; dynamic weight
  download from an unverified source; non-commercial dataset/test asset shipped;
  InsightFace weights anywhere; or CodeFormer / XTTS-v2 / Wav2Lip present
  transitively. Wired into the Dockerfile (`make build` is blocked until it
  passes) and `Makefile`.
- The repo is **NOT** labelled "licensing verified". Current machine status:
  **FAIL/PENDING by design** (faster-whisper + GFPGAN fetch weights dynamically →
  must be pinned on the build host; every commit/SHA-256 is still `PIN_ME`).

## What is real and verified in this environment
- `pytest` → **33 passing tests** (state machine, phrasing, workers + backpressure
  + cancellation, barge-in, quality ladder, drift, auth, session isolation).
- `python scripts/phase1_proof.py` → **PASS** (renders a continuous talking clip
  on CPU; one stable frame per audio frame — audio is the master clock).
- `python scripts/licence_audit.py` → **exit 2 (FAIL)**, correctly stopping the
  build (demonstrates the gate is real, not cosmetic).
- Full runtime imports cleanly; the CPU fallback renderer keeps the avatar alive
  and lip-syncs with no GPU/keys/paid services.

## What is a GPU-host integration seam (defined, not mockup, not yet run here)
MuseTalk, LivePortrait (InsightFace removed → YuNet), Kokoro, faster-whisper,
LiveKit transport. Each has a load/warm-up adapter with a clear TODO where the
weights plug in; on CPU the renderer auto-falls back so nothing freezes.

## Build progress — Phase 2 + 3 now RUN locally (this revision)
- **End-to-end pipeline runs with no GPU/mic/paid services.**
  `python scripts/e2e_demo.py` starts a mock Command Desk, streams a response
  through the **real** Session + workers (phrase chunking → TTS → renderer →
  synchronised A/V capture) and assembles one talking clip. Verified:
  4 streamed phrases → 4 TTS segments → 171 frames, **drift 0 ms** (audio-master
  clock), state timeline `THINKING → STARTING_SPEECH → SPEAKING`.
- **Real bug fixed:** the MuseTalk seam reported itself "available" while its
  inference raised, so the renderer never fell back → **0 frames**. Now the GPU
  adapter reports unavailable until real weights load, and the renderer falls
  back to CPU within a turn. The avatar never freezes.
- **Wiring fixed:** `TTS_AUDIO → renderer` was unconnected; now wired on the bus.
- **Added:** `CaptureTransport`, mock Command Desk, named fallback-animation set
  (`aura/render/idle.py`), and a **Phase-1 perceptual QA harness**
  (`scripts/perceptual_qa.py`: identity SSIM + mouth-motion/flicker) — PASSES on
  the e2e clip. Test suite now **43 passing**.
- Swap the mock for your real Command Desk via `AURA_BRAIN_ENDPOINT` — nothing
  else changes (that is Phase 3).

## Phase 4 — live audio path now RUNS + verified (this revision)
- Added the **audio-input worker** (`aura/workers/audio_input.py`): buffers mic
  PCM with pre-roll, forwards frames to VAD, and on end-of-speech writes the
  utterance wav and hands it to STT — closing mic → transcript.
- Integration tests push **synthetic mic frames through the real workers** and
  confirm: VAD start/stop moves the session (LISTENING→USER_SPEAKING→THINKING),
  STT emits a final transcript, and voice during SPEAKING triggers a **real
  barge-in** that cancels queued speech and recovers to LISTENING.
- Browser capture sets echoCancellation + noiseSuppression + autoGainControl.
- Test suite now **45 passing**.

## Phase 5 + 6 — DONE + verified (this revision)
- **Self-hosted WebRTC streaming (aiortc)** — no LiveKit server, no paid service.
  `AiortcTransport` streams real avatar video + audio + a data channel to a plain
  `RTCPeerConnection` browser client (`clients/browser/webrtc.html`). A signaling
  route (`POST /v1/rtc/offer`, token-gated) builds the pipeline behind the peer
  connection. Tests prove a real frame streams over WebRTC and the handshake
  returns a valid answer.
- **Renderer is alive while idle** — a breathing/blinking idle loop emits frames
  between utterances (kept in sync with session state); disabled for the offline
  capture demo so that clip stays clean.
- **Live health + metrics** — `/healthz` and Prometheus `/metrics` report real
  per-worker health, counters, queue depth and A/V drift.
- **One-command self-hosted run:** `python scripts/run_selfhosted.py` (gateway +
  WebRTC + pipeline in one process). Test suite now **47 passing**.

## The only boundary I can't cross in this sandbox (honest)
- **A GPU** for the photoreal MuseTalk/LivePortrait renderer — the adapters are
  wired and fall back to the CPU renderer here; photoreal quality activates on a
  GPU host with pinned weights.
- **A physical microphone + faster-whisper weights** for a real spoken session —
  the entire server-side audio path is implemented and tested with synthetic
  audio and real WebRTC mic ingest.
- **Licence audit stays FAIL/PENDING by design** until commits + SHA-256 are
  pinned on the build host. Everything else is built, wired, and tested.
