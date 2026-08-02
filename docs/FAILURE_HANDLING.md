# Failure Handling (spec §20)

| Failure | Detection | Response | State |
|---|---|---|---|
| Uncertain transcription | STT low avg_logprob / empty | don't send junk to brain; re-prompt "sorry, could you repeat?" | LISTENING |
| No speech detected | VAD never fires / empty final | stay attentive; optional timeout nudge | LISTENING |
| Command Desk timeout | brain worker item_timeout | speak a graceful recovery line; log; keep session | RECOVERING→LISTENING |
| TTS failure | engine raises / no audio | try fallback voice (espeak); if still failing, emit ERROR event | RECOVERING |
| Avatar renderer slowdown | render latency > frame budget / drift over budget | quality ladder steps down; if renderer raises, switch to CPU fallback | SPEAKING (degraded) |
| GPU OOM | CUDA OOM on warm-up/infer | drop to lower level / fallback renderer; shed the heaviest model; alert | RECOVERING |
| WebRTC disconnection | transport close / ICE fail | client auto-reconnect with fresh token; count reconnects; resume | RECOVERING→LISTENING |
| Phone lock / app backgrounding | client lifecycle event | mute mic, pause publish, hold session briefly, then end if no resume | IDLE→(END) |
| Repeated interruptions | interruption count spikes | keep cancelling cleanly; optionally shorten replies; never wedge | LISTENING |
| Malformed avatar assets | preprocess validation fails | reject at load; use last-good identity or default; never ship bad asset | ERROR at setup |
| Worker crash | supervised loop catches exception | restart with exponential backoff; health check flips; drain stale queue | worker-local; session continues |

General rules: **never sacrifice speech, timing, stability, or the session to keep
visual quality** (spec §15). Every failure is logged as a structured JSON line
with an `error_source`, and counted in per-turn metrics (spec §19).
