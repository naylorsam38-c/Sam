# Deployment (spec §27)

## Prerequisites
- A GPU host (Linux, CUDA) for the full stack; a CPU host runs the fallback only.
- Docker + Docker Compose. `ffmpeg` and `espeak-ng` (in the image).
- Your Command Desk brain reachable on the internal network.

## Steps
1. `cp .env.template .env` and fill: `AURA_TOKEN_SECRET`, `AURA_BRAIN_ENDPOINT`,
   `LIVEKIT_API_KEY/SECRET`, model paths, `CUDA_VISIBLE_DEVICES`.
2. **Pin licences:** on the build host, fill every `PIN_ME`/`sha256` in
   `config/dependency_lock.yaml`, eliminate dynamic downloads, then
   `make audit` until `STATUS: PASS`.
3. Download model weights into `./models` (kokoro, musetalk, liveportrait, yunet,
   gfpgan, whisper). Do **not** copy MuseTalk test data. Remove InsightFace models.
4. `make build` (blocked unless the audit passes) then `docker compose up`.
5. Put TLS (a reverse proxy) in front of the gateway. Expose only the gateway +
   LiveKit media ports; keep model/render/Command Desk ports internal.

## Services (`docker-compose.yml`)
- `gateway` — public API (tokens, isolation, health). Only public HTTP surface.
- `avatar-runtime` — the worker set + session (GPU).
- `livekit` — self-hosted transport.
- Command Desk is **not** deployed here; Aura calls it at `AURA_BRAIN_ENDPOINT`.

## Scaling
Start with `AURA_MAX_SESSIONS=1` (one reliable user). To scale: pin workers to
separate GPUs via `gpu.devices`, run multiple `avatar-runtime` replicas behind
the gateway, and add a room→worker scheduler. Load-test drift + latency before
raising the cap.
