# API Contracts

Three surfaces: the **internal** presentation request (Command Desk → Aura), the
**public** gateway REST API, and the **data-channel** events + control messages
(client ⇄ Aura over WebRTC).

## 1. Internal API — `PresentationRequest`

Defined in `aura/protocol.py`. Command Desk streams these to the avatar; each
`text` may be one phrase chunk of a larger turn, sharing `session_id` + `turn_id`.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `session_id` | string | — (required) | The session this speech belongs to. |
| `text` | string | — | What to say (this chunk). Max 20000 chars. |
| `turn_id` | string | auto (12 hex) | Groups chunks of one response turn. |
| `avatar` | string | `nova` | Which avatar to present. |
| `voice` | string | `nova` | TTS voice. |
| `emotion` | string | `neutral` | e.g. reassuring, happy, serious. |
| `intensity` | float | `0.35` | Expression strength, clamped to 0..1. |
| `gesture` | string \| null | `null` | e.g. `small_nod`, `head_tilt`. |
| `interruptible` | bool | `true` | May the user barge in over this? |
| `final` | bool | `true` | Is this the last chunk of the turn? |

`validate()` requires `session_id`, clamps `intensity` to `[0,1]`, and rejects
text longer than 20000 chars.

### Example (canonical)

```json
{
  "session_id": "abc123",
  "text": "Here is what I found.",
  "turn_id": "9f1c2a7b4e10",
  "avatar": "nova",
  "voice": "nova",
  "emotion": "reassuring",
  "intensity": 0.35,
  "gesture": "small_nod",
  "interruptible": true,
  "final": true
}
```

## 2. Gateway REST (`aura/gateway/app.py`)

The gateway is the **only public surface**. Model, render, and Command Desk ports
are never exposed. Run it behind TLS.

### `POST /v1/session`

Authenticate the app user and issue a short-lived token + room.

- Header: `x-user-id: <user>` (required; 401 if missing)
- Rate limited per user (429 on exceed)

Response:

```json
{
  "token": "eyJ1aWQ...base64body.base64sig",
  "room": "aura-<user>-1a2b3c4d",
  "transport_url": "ws://livekit:7880",
  "expires_at": 1735689600
}
```

### `POST /v1/session/verify`

Verify a token before admitting a client to a room.

Request:

```json
{ "token": "<token>" }
```

Response (200) — the decoded payload:

```json
{ "uid": "user42", "room": "aura-user42-1a2b3c4d", "iat": 1735689480, "exp": 1735689600, "jti": "…" }
```

- `401` if the token is malformed, has a bad signature, or is expired.
- `403` if the room is not owned by this user (isolation).

### `GET /healthz`

```json
{ "status": "ok", "version": "1.0.0" }
```

### `GET /metrics`

Prometheus-style operational metrics (session counts, worker metrics when wired).

## 3. Data-channel events — `Envelope`

Every message Aura pushes to the client is one `Envelope` (JSON over the WebRTC
data channel).

### Envelope shape

```json
{
  "type": "state",
  "session_id": "abc123",
  "turn_id": "9f1c2a7b4e10",
  "data": { "prev": "THINKING", "state": "SPEAKING" },
  "ts": 1735689500.482
}
```

### Event types (`Event` enum)

| `type` | `data` payload | When |
|---|---|---|
| `state` | `{prev, state}` | Every state-machine transition. |
| `partial_transcript` | `{text}` | Live STT hypothesis. |
| `final_transcript` | `{text}` | Finalized user utterance. |
| `response_text` | `{text}` | Text the avatar is about to speak. |
| `timing` | per-turn metric sample | Turn latency breakdown. |
| `drift` | `{drift_ms, over_budget}` | A/V drift, especially when over budget. |
| `interrupted` | `{turn_id}` | A turn was barged-in. |
| `quality` | `{level, …}` | Current quality-ladder level changed. |
| `error` | `{source, message}` | A recoverable error surfaced to the client. |

### Examples

```json
{ "type": "partial_transcript", "session_id": "abc123", "turn_id": "…", "data": { "text": "what's the wea" }, "ts": 1735689500.1 }
```
```json
{ "type": "drift", "session_id": "abc123", "turn_id": "…", "data": { "drift_ms": 96.4, "over_budget": true }, "ts": 1735689502.7 }
```
```json
{ "type": "interrupted", "session_id": "abc123", "turn_id": "9f1c2a7b4e10", "data": {}, "ts": 1735689503.0 }
```

## 4. Control messages — client → gateway (`Control` enum)

Sent by the client over the data channel.

| `type` | Meaning |
|---|---|
| `interrupt` | Barge-in via UI button (same effect as VAD-detected speech). |
| `mute` / `unmute` | Stop / resume sending mic audio. |
| `set_avatar` | Switch the presented avatar. |
| `text_input` | Typed input instead of mic. |
| `end_session` | Tear the session down. |

### Example

```json
{ "type": "text_input", "session_id": "abc123", "data": { "text": "Show me tomorrow's schedule." } }
```
```json
{ "type": "interrupt", "session_id": "abc123", "data": {} }
```
