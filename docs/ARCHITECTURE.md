# Architecture

Aura is a pipeline of small, independently-managed workers connected by an
in-process event bus, orchestrated per user by a `Session`. Everything model-
related is configuration (`config/aura.yaml`), never hardcoded.

## Components

| Component | File | Responsibility |
|---|---|---|
| Gateway | `aura/gateway/app.py` | Only public REST surface: auth, rate limit, session isolation, health/metrics. |
| Auth | `aura/gateway/auth.py` | Short-lived HMAC-signed session tokens scoped to one room + one user. |
| Security | `aura/gateway/security.py` | Rate limiter, session registry, upload validation, temp cleanup. |
| Session | `aura/session.py` | Per-user orchestrator: owns the state machine, drift meter, turn metrics, barge-in. |
| State machine | `aura/state.py` | Deterministic, legal-transition-only state graph. |
| Phrasing | `aura/phrasing.py` | Splits streamed brain text into 4–12 word phrases. |
| Bus | `aura/bus.py` | Async pub/sub between workers; swappable for cross-process transport. |
| BaseWorker | `aura/worker.py` | Shared worker contract (see below). |
| Metrics | `aura/metrics.py` | `TurnMetrics` per turn + `DriftMeter` (audio vs video PTS). |
| Runtime | `aura/runtime.py` | Assembles the worker set + session + transport for one user. |

## The worker set (`aura/workers/`)

Each worker extends `BaseWorker` and does exactly one job. They are separate on
purpose: independently managed, independently restartable, and **movable to
separate processes/GPUs later** without touching their code, because they only
talk through the bus and their queues.

| Worker | Consumes | Produces | Default engine |
|---|---|---|---|
| `VADWorker` (vad) | mic PCM | `VAD` start/stop | Silero VAD (energy-gate fallback) |
| `STTWorker` (stt) | utterance audio | `TRANSCRIPT_PARTIAL`, `TRANSCRIPT_FINAL` | faster-whisper |
| `BrainConnector` (brain) | final transcript | streamed `PresentationRequest`s | Command Desk connector (HTTP stream) |
| `TTSWorker` (tts) | phrase | `TTS_AUDIO` | Kokoro (espeak-ng fallback) |
| `RendererWorker` (render) | `TTS_AUDIO` | `RENDER_FRAME` | MuseTalk GPU / CPU fallback |
| `PublisherWorker` (publish) | `RENDER_FRAME`, `TTS_AUDIO` | WebRTC A/V + drift log | LiveKit transport |

The `brain` worker is only a **transport** for text in and streamed text out. It
never contains reasoning — that stays in Command Desk.

## Bus topics (`aura/bus.py` `Topic`)

```
USER_AUDIO ─▶ VAD ─▶ TRANSCRIPT_PARTIAL / TRANSCRIPT_FINAL ─▶ BRAIN_REQUEST
   ─▶ RESPONSE_PHRASE ─▶ TTS_AUDIO ─▶ RENDER_FRAME ─▶ (publisher)
BARGE_IN ─▶ cancels everything downstream        STATE ─▶ client
```

| Topic | Payload |
|---|---|
| `USER_AUDIO` | raw mic frames |
| `VAD` | `{kind: start\|stop, ts}` |
| `TRANSCRIPT_PARTIAL` / `TRANSCRIPT_FINAL` | `{text, [uncertain]}` |
| `BRAIN_REQUEST` | final transcript → Command Desk |
| `RESPONSE_PHRASE` | streamed phrase chunk → TTS |
| `TTS_AUDIO` | `{session_id, turn_id, wav_path, pts, sample_rate}` |
| `RENDER_FRAME` | `{frame, audio_pts, video_pts}` |
| `BARGE_IN` | `{session_id}` |
| `STATE` | state change |

Today the bus is asyncio callbacks in one process. To split workers across
processes/GPUs, replace `Bus.publish` with a ZeroMQ/Redis-Streams transport —
worker code does not change because it only calls `publish`/subscribes handlers.

## BaseWorker contract (`aura/worker.py`)

Every worker gets, for free:

- **Bounded input queue** (`asyncio.Queue(maxsize=…)`) — prevents unbounded memory.
- **Backpressure policy** when the queue is full:
  - `drop_oldest` — discard the oldest queued item, count it in `metrics.dropped`
    (used where freshness beats completeness: vad, render, publish).
  - `block` — await space, applying real backpressure (used where every item must
    be processed).
- **Per-item timeout** (`asyncio.wait_for`) → `on_timeout` hook.
- **Cooperative cancellation** — `cancel_current()` aborts the in-flight item;
  this is the barge-in hook that stops TTS/render mid-phrase.
- **Health** — `healthy()` checks a heartbeat (`last_beat`) and that the task is alive.
- **Structured JSON logs** via `log()` (one line per event).
- **Metrics** — `WorkerMetrics{processed, errors, dropped, restarts, last_latency_ms, queue_depth}`.
- **Supervised restart** — the run loop catches exceptions, logs, and restarts the
  processing loop with exponential backoff (0.5 → 8.0 s). The runtime supervisor
  additionally restarts any worker that reports unhealthy.

### Queue sizing (defaults)

| Worker | maxsize | timeout | on_full |
|---|---|---|---|
| vad | 64 | 1.0 s | drop_oldest |
| stt | 8 | 10.0 s | block |
| brain | 8 | timeout+5 s | block |
| tts | 16 | 8.0 s | block |
| render | 4 | 15.0 s | drop_oldest |
| publish | 8 | 2.0 s | drop_oldest |

## GPU / memory budget overview

Defaults from `config/aura.yaml` `gpu:`:

| Stage | VRAM budget |
|---|---|
| STT (faster-whisper small.en int8_float16) | ~1500 MB |
| TTS (Kokoro-82M) | ~1500 MB |
| Render (MuseTalk VAE+UNet+feature extractor) | ~6000 MB |

Warm-up (`warmup: true`) loads each model and runs one dummy forward so the first
real frame/word is not cold. See [GPU_BUDGET](GPU_BUDGET.md) for full sizing.

## Moving workers to separate GPUs

Because workers only touch queues and the bus, scaling out is a **config** change,
not a code change:

1. Set per-stage devices in `config/aura.yaml`:
   ```yaml
   gpu:
     devices: { stt: "cuda:0", tts: "cuda:0", render: "cuda:1" }
   ```
2. To split across **machines**, swap the in-process `Bus` for a networked one
   (ZeroMQ/Redis Streams) and run each worker as its own service. In
   `docker-compose.yml` each stage can become its own service pinned to a GPU via
   `deploy.resources.reservations.devices`.

The single-process reference build (`runtime.build_session`) is the starting
point; the seams to split it out already exist.
