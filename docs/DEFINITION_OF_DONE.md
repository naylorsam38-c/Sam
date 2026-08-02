# Definition of Done (spec §27)

A checkable list. `[x]` = implemented + (where testable) covered by tests/proof
in this repo. `[~]` = implemented as a GPU-host integration seam. `[ ]` = open.

## Runtime behaviour
- [x] All 9 deterministic states with enforced legal transitions (`aura/state.py`, tested)
- [x] Barge-in: detect user, stop TTS, discard audio, cancel frames, return to
      LISTENING, notify Command Desk (`session.barge_in`, tested)
- [x] Phrase streaming 4–12 words on natural boundaries (`aura/phrasing.py`, tested)
- [x] Audio is master clock; every frame carries an audio PTS; drift measured
      continuously; 80 ms budget (`metrics.DriftMeter`, `render/*`, tested)
- [x] Alive in every state (idle/listen/think/speak/interrupt/recover); never a
      frozen photo unless the renderer fully fails (`render/fallback.py`)
- [x] Quality ladder degrades visuals before speech/timing/stability/session
      (`render/quality.py`, tested)

## Workers & resilience (spec §8)
- [x] 7 workers; each with bounded queue, health, timeout, cancellation,
      backpressure, structured logs, supervised restart, metrics (`aura/worker.py`,
      `aura/workers/*`, tested)
- [x] Config-driven models, not hardcoded (`config/aura.yaml`, `aura/config.py`)
- [~] Per-GPU scheduling / move workers to separate GPUs (config present; wire on
      multi-GPU host)

## Interfaces & clients
- [x] Internal API (PresentationRequest) + data-channel events + controls
- [x] Gateway REST + signed tokens + isolation + rate limit
- [x] Browser clients: self-hosted plain-WebRTC (`webrtc.html`) + LiveKit variant;
      Flutter client; iOS/Android guidance (thin)
- [x] **Self-hosted WebRTC publishing (aiortc)** — real video+audio+data-channel
      to the browser, no LiveKit server, no paid service; frame-over-WebRTC and the
      signaling route are covered by tests. LiveKit remains an optional transport.

## Media models
- [x] CPU fallback renderer (runnable, proven)
- [~] MuseTalk lip-sync / LivePortrait motion / Kokoro TTS / faster-whisper STT
      (adapters + warm-up seams; run on GPU host with pinned weights)

## Security & ops (spec §17–19)
- [x] Short-lived signed tokens; no public model ports; rate limit; per-user room
      isolation; upload validation; temp cleanup policy (`gateway/*`, tested)
- [x] Per-turn metrics list; health checks; structured JSON logging
- [x] Failure handling defined for all §20 cases (`docs/FAILURE_HANDLING.md`)

## Licensing (spec §22–23)
- [x] Human register + machine manifest + build-failing audit gate
- [ ] **Status PASS** — blocked until every commit + SHA-256 is pinned and
      dynamic downloads eliminated on the build host (audit currently FAIL/PENDING
      by design). Do not label "licensing verified" until `licence_audit.py` = PASS.

## Scale
- [x] One reliable user first (`AURA_MAX_SESSIONS=1`); multi-user is a later phase
