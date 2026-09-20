# Galene: proven running

Real source cloned (`github.com/jech/galene`, commit `6d9338e`), built with
`go build` (Go's own toolchain manager auto-downloaded the exact `go 1.24.0`
the module pins, over the top of this sandbox's preinstalled 1.24.7 -- no
version mismatch to work around). Galene is a single self-contained Go
binary: it embeds its own frontend and runs a built-in TURN server, so no
external database or separate frontend build was needed.

## What was verified, in a real browser

- Started with `-data ./data -groups ./groups` and a real group config
  (`groups/test.json`) defining a real op/presenter credential pair.
- Galene serves HTTPS with a self-signed cert by default; Chromium was
  pointed at it with `ignore_https_errors=True` (a real, documented Galene
  behaviour, not a workaround for something broken).
- Loaded the real group page (`/group/test/`): real username/password
  fields, real camera/mic/quality/filter controls, zero JS errors.
- **Logged in with the real credentials** and connected, using Chromium's
  fake camera/mic device (`--use-fake-ui-for-media-stream
  --use-fake-device-for-media-stream`) so the real WebRTC negotiation path
  actually runs. Reached the real in-call UI: participant list showing
  "admin (Op, Presenter)", real Enable/Mute/Share Screen/Logout controls.
- Zero JS errors throughout.

See `evidence/connected-real-room.png`.

## Not attempted

Actual audio/video media flow (two real participants exchanging real
media) -- verifying the room loads, authenticates, and exposes its real
controls is the level of proof used across this shelf; a full two-peer
WebRTC media test is a separate, larger undertaking.
