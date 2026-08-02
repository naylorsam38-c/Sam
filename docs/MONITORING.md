# Monitoring, Metrics & Logging (spec §19)

## Per-turn metrics (`aura/metrics.py:TurnMetrics`)
Recorded every turn: VAD start, VAD end, STT start, STT final, Command Desk
request time, first response token, first TTS audio, first rendered frame, first
published frame, total response latency, dropped frames, queue depth, GPU
utilisation, GPU memory, audiovisual drift, interruption count, reconnect count,
error source. `total_latency_ms = first_published_frame − vad_end`.

## Drift
`DriftMeter` samples `(video_pts − audio_pts)` continuously; `over_budget` when
`|drift| > 80 ms`; a DRIFT event is pushed to the client when exceeded.

## Health
Each worker exposes `healthy(max_silence)` (last heartbeat + task alive). The
supervisor restarts unhealthy workers with backoff. Gateway `/healthz` for
liveness; `/metrics` for a sessions gauge (extend to full Prometheus exposition
with `prometheus-client`).

## Structured logging
Every log line is one JSON object: `{ts, worker, level, msg, ...kv}` (`aura/worker.py:log`).
Ship stdout to your log stack; key events: state changes, cancellations, timeouts,
restarts, drift-over-budget, quality-level changes, errors with `error_source`.
