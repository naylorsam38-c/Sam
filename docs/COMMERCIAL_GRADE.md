# Getting to commercial grade

The honest path from what this repo does today to something you can sell, and
what each step costs.

## Where the quality actually comes from

Three things decide whether an avatar reads as a person. In order of leverage:

1. **A driving video, not a still.** Every lip-sync model — MuseTalk, and every
   hosted service — inpaints the mouth over an existing frame sequence. One
   still image means one fixed head pose for every frame, and the result reads
   as a photo with a moving mouth no matter how good the mouth is. A 20-second
   loop of the subject sitting still, blinking and shifting slightly closes most
   of the perceptual gap. It costs one clip.
2. **Viseme lip-sync, not amplitude.** The bundled CPU renderer warps the mouth
   region by audio RMS. It moves in time with speech but is not forming the
   words. That is the difference between the `fallback` provider and `musetalk`.
3. **Latency.** Under ~800ms end-to-end the conversation feels alive; over
   ~1.5s it feels like a video call with a bad connection. This is where the
   hosted services have spent their two years.

## The switch

`config/aura.yaml` → `providers.policy` decides how you pay:

| policy | what runs | what you pay |
|---|---|---|
| `api` | Cartesia + Deepgram + Simli | ~$0.058/conversation-minute, no capex |
| `selfhosted` | Kokoro + faster-whisper + MuseTalk | ~$0.50/GPU-hour, no per-minute fee |
| `auto` | local when it can, API when it can't | whichever applies |
| `offline` | espeak + CPU warp | nothing, and it shows |

Nothing outside that block changes. The session, state machine, barge-in, drift
budget and transport are identical on both paths.

### Which one you should be on

**Break-even is ~14% GPU utilisation — about 3.5 conversation-hours per day.**

A $0.50/hr GPU bills whether or not anyone is talking, so idle time is what
makes it expensive per useful minute:

| GPU busy | effective cost/conversation-minute |
|---|---|
| 100% | $0.008 |
| 50% | $0.017 |
| 25% | $0.033 |
| 10% | $0.083 |

Below ~14% busy, the API is cheaper *and* better quality. Above it, owning the
card wins decisively. Start on `api`, watch your real utilisation, switch when
the numbers say so — which is exactly what the switch is for.

`GET /healthz` reports which provider actually won and why the others were
skipped, so a stack that silently degraded to the CPU fallback is visible rather
than mysterious.

## Build order

**1. Own your avatar asset.**
```bash
python scripts/make_avatar.py --name nova --image portrait.png \
    --subject "Name" --consent-ref "release-2026-04-11"
```
Produces `portrait.png`, `driving.mp4` and a `bundle.json` recording model,
licence, consent and SHA-256 for each. `--verify` re-hashes and re-checks it.
With no GPU the driving loop is procedural (synthesised head motion) — better
than a frozen still, not a substitute for real footage.

**2. Ship on the API path.** Set `AURA_PROVIDER_POLICY=api` and the four keys in
`.env`. This gets you commercial quality with zero capex while you learn what
your real usage looks like.

**3. Stand up the GPU path in parallel.** One RTX 4090 / L40S serves 1–3
concurrent sessions. Install MuseTalk, download and pin the weights, set
`AURA_MUSETALK_HOME`. The `musetalk` provider only reports itself available
after a real forward pass — a renderer that claims readiness and then raises
produces a frozen face, which is the exact bug this codebase was bitten by
before.

**4. Flip the switch** when utilisation crosses break-even.

## What is still open

- `MuseTalkAvatar._dummy_forward` and `speaking_frames` are the GPU integration
  point. The loader, driving-frame handling and fallback-within-a-turn are done;
  the inference call is not, and it needs a GPU to write against.
- `WanVideo.generate` likewise — the procedural backend covers it until then.
- `SimliAvatar.speaking_frames` deliberately raises. Simli streams video
  client-direct over its own WebRTC connection; relaying it through your server
  costs 100ms+ for no quality gain. `start_session()` implements the fast path.
- LiveKit transport is still unimplemented. The self-hosted aiortc transport
  works and is tested, so this only matters if you want LiveKit's scaling.

## Licensing traps specific to this build

The audit gate (`make audit`) hard-fails on all of these, but know them:

- **FLUX.1-dev is non-commercial.** FLUX.1-schnell is Apache-2.0. One string
  apart, identical-looking output.
- **InsightFace is non-commercial**, which also rules out InstantID and
  IP-Adapter-FaceID — the usual identity-consistency route. Use a LoRA or a
  YuNet-based pipeline.
- **Wan 2.2 is Apache-2.0 on code *and* weights**, which is unusual for video
  models; most carry field-of-use restrictions.
- **The bundled `assets/nova.png` is not shippable.** AI-generated, unknown
  model, cropped UI chrome still in frame, no consent record. Rule R7 fails any
  bundle without valid provenance — generate or record a clean one.
