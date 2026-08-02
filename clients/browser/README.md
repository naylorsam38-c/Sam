# Aura — Browser Reference Client

A **thin** single-page web client for the self-hosted Aura live avatar service.
It does the minimum a client should do and nothing more — all speech-to-text,
the brain/LLM, text-to-speech, and lip-sync rendering happen on the server.

## What it does (the six client responsibilities)

1. **Authenticate + get a token** — `POST GATEWAY_URL/v1/session` with an
   `x-user-id` header, receiving `{token, room, transport_url, expires_at}`.
2. **Join the avatar session** — connects to the self-hosted LiveKit room using
   `transport_url` + `token`.
3. **Send input** — publishes the microphone track *or* sends typed text
   (`text_input` control).
4. **Receive the avatar** — attaches the remote video + audio tracks.
5. **Receive events** — parses data-channel `Envelope` JSON into state and
   transcript updates.
6. **Send controls** — `interrupt`, `mute`/`unmute`, `set_avatar`, `text_input`,
   `end_session` as JSON via `publishData`.

## Files

- `index.html` — the UI (avatar video, state badge, transcript, mic toggle,
  text box, interrupt button, avatar selector). Dark/gold theme.
- `aura-client.js` — reusable framework-agnostic `AuraClient` class. `index.html`
  is just a thin wiring layer on top of it.

## Configure

Edit the constants at the top of the `<script>` block in `index.html`:

```js
const GATEWAY_URL = "http://localhost:8080"; // your Aura gateway
const USER_ID     = "demo-user";             // app user identity (x-user-id)
```

## Run

The page only needs to be served over HTTP(S) — it is fully static. From this
directory:

```bash
python3 -m http.server 5173
# then open http://localhost:5173
```

Or any static server (`npx serve`, nginx, etc.).

> **Microphone note:** browsers only allow `getUserMedia` on `https://` or
> `http://localhost`. Serve over localhost during development, or terminate TLS
> in front of the page in production.

Make sure the Aura gateway (default `:8080`) and the self-hosted LiveKit server
(`transport.url`, default `ws://livekit:7880` in `config/aura.yaml`) are
reachable from the browser.

## Using AuraClient directly

```js
const client = new AuraClient({
  gatewayUrl: "http://localhost:8080",
  userId: "demo-user",
  callbacks: {
    onState:    (s)    => console.log("state", s),
    onPartial:  (t)    => console.log("partial", t),
    onFinal:    (t)    => console.log("you said", t),
    onResponse: (t)    => console.log("avatar says", t),
    onError:    (e)    => console.error(e),
    onVideoTrack: (el) => document.body.appendChild(el),
    onAudioTrack: (el) => document.body.appendChild(el),
  },
});

await client.connect();     // /v1/session + LiveKit join
await client.enableMic();   // publish microphone
client.sendText("Hello");   // or type instead of speaking
client.interrupt();         // barge-in
client.setAvatar("halo");   // nova | halo | gaia
await client.endSession();  // leave cleanly
```

## Wire contract (must match `aura/protocol.py`)

**Inbound** (data channel) — `Envelope {type, session_id, turn_id, data, ts}`
with `type` ∈ `state`, `partial_transcript`, `final_transcript`,
`response_text`, `timing`, `drift`, `quality`, `interrupted`, `error`.

**Outbound** controls — `{type, ...}` with `type` ∈ `interrupt`, `mute`,
`unmute`, `set_avatar`, `text_input`, `end_session`. `text_input` carries
`{text}`; `set_avatar` carries `{avatar}`.

This is reference code — deliberately small and dependency-free (LiveKit SDK
only) so it is easy to read and port.
