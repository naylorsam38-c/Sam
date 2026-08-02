# Quality Ladder (spec §15)

Degrade **visuals only** — never speech, timing, stability, or the session.
Controller: `aura/render/quality.py` (hysteresis so it doesn't oscillate).

| Level | Resolution | FPS | Enhancement | Motion |
|---|---|---|---|---|
| **3** | 720p | 30 | full | full head/expression |
| **2** | 720p | 25 | reduced | full |
| **1** | 512p | 25 | none | lip-sync + essential motion |
| **Fallback (0)** | 512p | 25 | none | pre-rendered idle loop + lightweight local mouth/viseme (CPU) |

Down-shift triggers (any): drift over budget, dropped frames, render latency >
frame budget, GPU memory > 92%. Up-shift only when comfortably relaxed and after
a cooldown. The CPU `FallbackRenderer` is Level 0 and is always available, so the
avatar never freezes while the session lives.
