# Aura — Live Interactive Avatar Presentation Service

Aura is a **self-hosted, real-time interactive avatar** that gives a face and a
voice to an existing AI brain. A user speaks; Aura listens, transcribes, asks the
brain what to say, and renders a lip-synced talking avatar back over WebRTC with
audio and video kept tightly in sync. The user can interrupt at any time, exactly
like a real conversation.

## What Aura is

- A **presentation layer**: microphone in → WebRTC → VAD → STT → external brain →
  streamed phrases → TTS → lip-sync render → synchronized WebRTC A/V → app.
- A deterministic, interruptible, low-latency conversational front end.
- Fully self-hostable on infrastructure you control.

## What Aura is NOT

- **It is not the brain.** The reasoning, agents, memory and oversight live in an
  external system called **Command Desk**. Aura connects to Command Desk over an
  internal endpoint and never rebuilds, replaces, or relicenses it. Command Desk
  streams text to Aura; Aura turns that text into a talking face.
- It is not a cloud service. There are no required per-use SaaS fees (see cost note).

## Target architecture

```
                        ┌──────────────────────── Aura (self-hosted) ────────────────────────┐
                        │                                                                     │
  ┌────────┐   mic PCM  │  ┌─────┐   ┌─────┐   ┌───────────────┐  phrase   ┌─────┐  audio     │
  │  App   │──WebRTC────┼─▶│ VAD │──▶│ STT │──▶│ Command Desk  │──stream──▶│ TTS │───┐        │
  │(browser│   audio    │  └─────┘   └─────┘   │  (EXTERNAL     │           └─────┘   │        │
  │ mobile)│            │     │                │   brain, never │                     ▼        │
  │        │◀──WebRTC───┼──┐  │ barge-in       │   rebuilt)     │              ┌───────────┐   │
  │        │  A/V + data│  │  └───────────────▶└───────────────┘              │ Renderer  │   │
  └────────┘            │  │                        lip-sync (MuseTalk GPU /   │(lip-sync) │   │
       ▲                │  │  ┌───────────┐  synced  CPU fallback)             └───────────┘   │
       │  state/timing/ │  └──│ Publisher │◀── A/V ──────────────────────────────────┘        │
       └── transcript ──┼─────│ (WebRTC)  │   audio = master clock; every frame carries        │
             events     │     └───────────┘   the audio PTS; drift budget 80 ms                │
                        └─────────────────────────────────────────────────────────────────────┘
     Only the Gateway (REST) + LiveKit are public. Model / render / Command Desk ports are private.
```

## Repository structure

```
aura-avatar-service/
├── aura/
│   ├── protocol.py        # State/Event/Control enums, PresentationRequest, Envelope
│   ├── state.py           # deterministic state machine + legal transitions
│   ├── session.py         # per-user orchestrator + barge-in
│   ├── phrasing.py        # 4–12 word phrase chunker
│   ├── bus.py             # in-process async event bus + Topic names
│   ├── worker.py          # BaseWorker (queue/health/timeout/cancel/backpressure/logs/restart/metrics)
│   ├── metrics.py         # TurnMetrics + DriftMeter
│   ├── config.py          # config loader (config is source of truth, not code)
│   ├── runtime.py         # wires workers + session + transport for one user
│   ├── gateway/           # public REST surface: app.py, auth.py, security.py
│   ├── workers/           # vad, stt, brain, tts, renderer, publisher
│   ├── render/            # fallback (CPU), musetalk_adapter, liveportrait_adapter,
│   │                      #   quality ladder, preprocess, enhance, regions, base
│   └── transport/         # livekit_transport, base (Null/local)
├── clients/               # browser / flutter / mobile thin clients
├── config/aura.yaml       # runtime configuration (commercial-safe defaults)
├── scripts/               # run_service.py, phase1_proof.py, preprocess_avatar.py
├── docker-compose.yml     # gateway + avatar-runtime + livekit
├── assets/nova.png        # bundled demo avatar
└── docs/                  # this documentation set
```

## Two ways to pay, one codebase

`config/aura.yaml` → `providers.policy` decides whether you pay per minute or
per GPU-hour. Nothing else changes when you flip it — same session logic, same
barge-in, same drift budget.

| policy | engines | cost |
|---|---|---|
| `api` | Cartesia + Deepgram + Simli | ~$0.058/conversation-min, no capex |
| `selfhosted` | Kokoro + faster-whisper + MuseTalk | ~$0.50/GPU-hour, no per-min fee |
| `auto` | local when possible, API when not | whichever applies |
| `offline` | espeak + CPU warp | free, and it shows |

**Break-even is ~14% GPU utilisation (~3.5 conversation-hours/day).** Below
that the API is cheaper and better; above it, own the card. `GET /healthz`
reports which provider actually won and why the others were skipped.

See [COMMERCIAL_GRADE](docs/COMMERCIAL_GRADE.md) for the full build order.

## Build your own avatar

You do not need to buy an avatar from a vendor:

```bash
python scripts/make_avatar.py --name nova --prompt "portrait of ..."      # generate
python scripts/make_avatar.py --name sam --image me.png \
    --subject "Sam Naylor" --consent-ref "release-2026-04-11"             # your own photo
python scripts/make_avatar.py --verify assets/generated/nova              # re-check
```

Produces a portrait, a driving loop, and a `bundle.json` recording the model,
its licence, consent and a SHA-256 per file. The build gate refuses any bundle
whose provenance is missing or whose hashes no longer match.

**The driving loop matters more than anything else.** Lip-sync models inpaint
the mouth onto existing frames — one still image gives one fixed head pose for
every frame, which is what reads as "photo with a moving mouth". With no GPU the
loop is synthesised procedurally; record ~20s of the real subject for commercial
output.

## Quickstart

### 1. CPU fallback proof (works on any machine, no GPU)

Proves the audio-mastered pipeline end to end using the CPU `FallbackRenderer`
and offline espeak-ng speech. Requires `espeak-ng` and `ffmpeg` on PATH.

```bash
pip install -r requirements.txt
python scripts/phase1_proof.py --minutes 2
# -> frames=... target>=... stable_size=True -> PASS
# -> review: samples/phase1.mp4
```

On a CPU-only box **only the fallback renderer runs**. It keeps the avatar alive
and lip-synced to the audio, but it does **not** match GPU MuseTalk quality.

### 1b. End-to-end turn (Phase 2+3, no GPU/mic/paid services)

```bash
python scripts/e2e_demo.py      # mock Command Desk -> real pipeline -> talking clip
# -> samples/e2e_turn.mp4  (state timeline + drift printed)
python scripts/perceptual_qa.py samples/e2e_turn.mp4   # identity/lip-sync QA -> PASS
```

### 1c. Live, self-hosted WebRTC (no LiveKit server, no paid service)

```bash
python scripts/run_selfhosted.py                # gateway + WebRTC + pipeline, :8080
# open clients/browser/webrtc.html against the gateway origin and press "Start talking"
```
This streams the avatar's real video + audio to the browser over WebRTC (aiortc),
carries state/transcript on a data channel, and takes your microphone back for
barge-in — all on infrastructure you control.

### 2. Full stack (containers)

```bash
cp .env.template .env       # set AURA_TOKEN_SECRET, AURA_BRAIN_ENDPOINT, LiveKit keys
docker compose up           # gateway (8080) + avatar-runtime + livekit
```

The GPU adapters (MuseTalk, LivePortrait, Kokoro) are **integration seams**: they
activate automatically on a GPU host with the model weights installed. Without a
GPU they stay dormant and the fallback path serves every request.

## Honest cost statement

Aura has **no required external per-use service fees** — the default stack is
open-source and self-hosted. That is **not** the same as "free": **local GPU
hardware, electricity, hosting, bandwidth, storage and maintenance all cost
money.** Budget for the machine and its running costs, not for API calls.

## Documentation

| Doc | Contents |
|---|---|
| [ARCHITECTURE](docs/ARCHITECTURE.md) | components, workers, bus, queues, GPU budget |
| [API_CONTRACTS](docs/API_CONTRACTS.md) | PresentationRequest, REST, events, controls |
| [WEBRTC_FLOW](docs/WEBRTC_FLOW.md) | full session sequence |
| [BARGE_IN](docs/BARGE_IN.md) | interruption / cancellation design |
| [QUALITY_LADDER](docs/QUALITY_LADDER.md) | 4-level degradation |
| [FAILURE_HANDLING](docs/FAILURE_HANDLING.md) | every failure mode + recovery |
| [SECURITY](docs/SECURITY.md) | tokens, isolation, transport, cleanup |
| [AVATAR_SOURCE_REQUIREMENTS](docs/AVATAR_SOURCE_REQUIREMENTS.md) | source image rules + preprocessing |
| [GPU_BUDGET](docs/GPU_BUDGET.md) | VRAM budgets, multi-GPU |
| [MONITORING](docs/MONITORING.md) | per-turn metrics, health, logging |
| [DEPLOYMENT](docs/DEPLOYMENT.md) | docker-compose, env, TLS |
| [TEST_PROCEDURE](docs/TEST_PROCEDURE.md) | manual + pytest |
| [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) | common problems |
| [ROADMAP](docs/ROADMAP.md) | the 6 build phases + status |
| [DEFINITION_OF_DONE](docs/DEFINITION_OF_DONE.md) | checkable acceptance criteria |
| [LICENSING_REGISTER](docs/LICENSING_REGISTER.md) | commercial-use classification of every component |
| [COMMERCIAL_GRADE](docs/COMMERCIAL_GRADE.md) | API vs self-hosted, cost break-even, build order |
| [MODEL_LANDSCAPE](docs/MODEL_LANDSCAPE.md) | researched Aug-2026 open-model survey, licences, traps, hardware |
```
