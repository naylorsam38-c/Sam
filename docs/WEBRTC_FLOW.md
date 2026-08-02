# WebRTC Session Flow

How a client establishes a live avatar session, from authentication to teardown.

## Public vs private surface

Only the **Gateway (REST)** and **LiveKit** (WebRTC transport) are reachable by
the client. The STT/TTS/render models, the renderer, and the Command Desk brain
run on the internal network and are **never** exposed. The short-lived token from
the gateway is the only credential the client ever holds, and it is scoped to a
single room owned by a single user.

## Numbered sequence

1. **Authenticate + get token.** Client `POST /v1/session` with header
   `x-user-id`. The gateway rate-limits the caller, then issues an HMAC-signed,
   ~120 s token bound to a freshly minted room, and claims that room for the user
   in the session registry. Response: `{token, room, transport_url, expires_at}`.
2. **(Optional) verify.** The transport side calls `POST /v1/session/verify` to
   confirm the token's signature/expiry and that the room is owned by this user
   (`403` if not). This enforces isolation before any media flows.
3. **Join the LiveKit room.** Client connects to `transport_url` (LiveKit) using
   `token` and `room`. The data channel opens for events + controls.
4. **Publish mic.** Client publishes its microphone track. Mic PCM flows to the
   `VADWorker`, which emits `VAD` start/stop on the bus.
5. **Receive A/V + data events.** As the user speaks and the brain responds, Aura
   publishes synchronized audio + video (audio is the master clock; every frame
   carries the audio PTS) and pushes `Envelope` events — `state`,
   `partial_transcript`, `final_transcript`, `response_text`, `timing`, `drift`,
   `quality`, `interrupted`, `error`.
6. **Controls.** The client sends `interrupt`, `mute`/`unmute`, `set_avatar`,
   `text_input`, or `end_session` over the data channel at any time.
7. **Teardown.** On `end_session` (or disconnect) the session closes, workers
   drain/cancel in-flight work, the room is released, and temp audio/frame files
   are cleaned up. The token expires on its own regardless.

## Sequence diagram

```
 Client                Gateway (public)        LiveKit (public)      Aura runtime (private)
   │                        │                        │                Command Desk (private)
   │  POST /v1/session      │                        │                        │
   │  x-user-id ───────────▶│ rate-limit, issue tok  │                        │
   │◀── token,room,url ─────│ claim room             │                        │
   │                        │                        │                        │
   │  POST /verify ────────▶│ verify sig+owner       │                        │
   │◀── 200 payload ────────│                        │                        │
   │                        │                        │                        │
   │  join(room, token) ───────────────────────────▶│                        │
   │  publish mic track ───────────────────────────▶│── mic PCM ────────────▶│ VAD
   │                        │                        │                        │  └▶STT
   │                        │                        │            final text ─┼─▶Command Desk
   │◀── data: final_transcript ─────────────────────│                        │◀─ phrase stream
   │◀── data: state SPEAKING ───────────────────────│                        │ TTS→Render
   │◀═══ audio + video (synced, audio-master) ══════│◀═══════════════════════│ Publisher
   │◀── data: drift / timing / quality ─────────────│                        │
   │                        │                        │                        │
   │  control: interrupt ──────────────────────────▶│───────────────────────▶│ barge-in
   │◀── data: interrupted, state RECOVERING→LISTENING│                        │
   │                        │                        │                        │
   │  control: end_session ────────────────────────▶│───────────────────────▶│ close+cleanup
```

## State the client observes

The `state` events track the server's deterministic machine:
`IDLE → LISTENING → USER_SPEAKING → THINKING → STARTING_SPEECH → SPEAKING`, with
`SPEAKING → INTERRUPTED → RECOVERING → LISTENING` on barge-in and any state able
to drop to `ERROR` then `RECOVERING`. See [BARGE_IN](BARGE_IN.md) and
[API_CONTRACTS](API_CONTRACTS.md).

## Reconnection

If the WebRTC connection drops, the client re-authenticates (or reuses an
unexpired token) and rejoins the same room. Reconnects are counted per turn
(`TurnMetrics.reconnects`). See [FAILURE_HANDLING](FAILURE_HANDLING.md).
