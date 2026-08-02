# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No TTS backend` / no audio | espeak-ng missing and Kokoro not loaded | `apt-get install -y espeak-ng`; on GPU host install Kokoro |
| Phase-1 proof errors | ffmpeg missing | `apt-get install -y ffmpeg` |
| STT returns empty / "uncertain" | faster-whisper not installed → fallback | install faster-whisper on GPU host; check `AURA` device/model |
| Avatar frozen | GPU renderer failed AND fallback failed to load | check `assets/*.png` exists + anchors in `render/base.py`; logs show renderer path |
| High drift / choppy | render can't keep up | quality ladder should step down; verify GPU, lower fps/level, check queue depth |
| `token expired` | short-lived token elapsed | request a new session token (TTL 120s) before joining |
| `room owned by another user` / 403 | isolation working as intended | each user gets their own room; don't share tokens |
| `capacity reached` | `AURA_MAX_SESSIONS=1` | raise cap only after single-user is proven |
| GPU OOM at startup | models exceed VRAM | lower level, split `gpu.devices`, or use a bigger card (see GPU_BUDGET) |
| `make build` fails at audit | licence gate (intended) | pin commits + SHA-256, remove dynamic downloads, then `make audit` = PASS |
| Audit flags a forbidden package | XTTS/CodeFormer/Wav2Lip/InsightFace pulled in transitively | remove it; use the approved alternative (Kokoro/GFPGAN/YuNet/MuseTalk) |
