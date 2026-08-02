# Build Roadmap (spec §24)

Build in this order; each phase has a hard gate.

**Phase 1 — Offline visual proof.** Prerecorded speech → stable talking avatar
for ≥2 continuous minutes. Pass only when: identity stays recognisable; eyes,
hair, jaw, face outline stable; teeth don't flicker; lips match speech; no
progressive facial drift; smooth transitions. *Status: implemented — CPU
fallback path via `scripts/phase1_proof.py` (PASS). GPU MuseTalk path is the
quality target, enabled on a GPU host.*

**Phase 2 — Streaming text-to-avatar.** Accept typed streamed text; start
speaking/animating before the full response arrives (phrase chunker 4–12 words).
*Status: implemented (`aura/phrasing.py`, session `present()`); tested.*

**Phase 3 — Command Desk connection.** Stream the existing Command Desk response
into the avatar without changing the brain. *Status: implemented
(`aura/workers/brain.py`), streaming + interrupt-notify.*

**Phase 4 — Live microphone.** VAD, STT, echo cancellation, interruption,
cancellation, recovery. *Status: implemented and verified. Audio-input worker
buffers mic PCM, forwards to VAD, and on end-of-speech captures the utterance wav
and hands it to STT; integration tests drive synthetic mic frames through the
real workers and confirm the VAD→capture→STT→brain loop and a real VAD-triggered
barge-in that recovers to LISTENING. Echo cancellation + noise suppression +
auto-gain are set on browser capture (WebRTC AEC). Remaining for a live device:
run STT with faster-whisper weights on the host.*

**Phase 5 — WebRTC clients.** Browser + Flutter reference clients, then iOS/
Android guidance. *Status: DONE + verified. Self-hosted WebRTC transport (aiortc)
streams real avatar video+audio to a plain-WebRTC browser client with a data
channel for events/controls — no LiveKit server, no paid service. A signaling
route (`POST /v1/rtc/offer`) builds the pipeline behind a peer connection. Tests
cover a real frame streaming over WebRTC and the signaling handshake. Flutter +
iOS/Android guidance provided; LiveKit remains an optional transport.*

**Phase 6 — Hardening.** Auth, monitoring, quality scaling, worker recovery,
security, licensing records, deployment, tests, docs. *Status: DONE. Signed
tokens enforced on the RTC route; rate-limit + per-user isolation; live
`/healthz` + Prometheus `/metrics` from real per-worker health/counters/drift;
quality ladder; supervised restart; docker-compose + a one-process self-hosted
run script; licence dependency-lock + audit gate; 47 tests; full docs. Multi-user
scaling comes after one reliable user (spec §25).*
