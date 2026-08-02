# GPU & Memory Budget (spec §9)

Do not assume all models fit in one uncontrolled GPU process. Aura declares
explicit budgets, warms models up, and lets you move stages to separate GPUs
later **without code changes** (config only).

## Config (`config/aura.yaml` → `gpu:`)
```yaml
gpu:
  stt_mem_mb: 1500
  tts_mem_mb: 1500
  render_mem_mb: 6000
  warmup: true
  devices: {stt: cuda:0, tts: cuda:0, render: cuda:0}   # -> cuda:1 to split later
```

## Indicative VRAM (verify on your host)
| Stage | Model | Approx VRAM |
|---|---|---|
| STT | faster-whisper small.en int8_float16 | ~1–1.5 GB |
| TTS | Kokoro-82M | ~0.5–1.5 GB |
| Lip-sync | MuseTalk | ~4–6 GB |
| Motion | LivePortrait | ~2–3 GB |
| Enhance | GFPGAN (targeted) | ~1–2 GB |

## Sizing
- **Single RTX 4090 (24 GB):** comfortably runs the full Level-3 stack for one
  user. Start here (spec §25: one reliable user first).
- **Smaller card (e.g. 3060 8–12 GB):** run at Level 1–2, or split render onto a
  second GPU via `devices.render: cuda:1`.
- **CPU-only:** only the fallback renderer runs (stylised, real-time-ish); GPU
  models are disabled automatically.

Warm-up runs one dummy forward per model at startup so the first real frame isn't
cold. Each worker respects its `*_mem_mb` budget; on OOM the quality ladder and
fallback protect the session (see FAILURE_HANDLING).
