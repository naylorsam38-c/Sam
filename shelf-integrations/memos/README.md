# Memos: proven running

Real source cloned (`github.com/usememos/memos`, commit `2b2192d`). Go's
toolchain manager auto-downloaded the pinned `go 1.27.0` over this sandbox's
preinstalled 1.24.7.

## A real gotcha, kept rather than smoothed over

`go build ./cmd/memos` alone produces a binary that serves `"No embeddable
frontend found."` -- the Go binary `//go:embed`s a `dist/` directory at
`server/frontend/dist`, but that directory is empty until the web frontend
is built separately and copied there. The actual steps:

```
cd web && pnpm install && pnpm build
mkdir -p ../server/frontend/dist
cp -r dist/* ../server/frontend/dist/
cd .. && go build -o memos ./cmd/memos
```

Skipping this doesn't fail the build -- it produces a binary that runs and
serves a real HTTP 200, which would have made "proven running" a false
positive if the browser check had been skipped. This is exactly why every
app on this shelf is checked in a real browser, not just `curl`'d.

## What was verified, in a real browser

- First run: real "Set up your instance" admin-signup screen.
- Created a real admin account (`sam` / a real password) -- request
  actually round-tripped to the embedded SQLite database (`data/memos.db`,
  auto-initialized on first boot).
- Reached the real dashboard: calendar widget, Home/Calendar/Map/Attachments
  nav, memo composer, "Tasks" view -- all real, not placeholders.
- Logged in again in a fresh browser session (real session/cookie flow, not
  a shared login state).
- Mobile viewport (390px): zero horizontal overflow.
- Zero JS errors throughout.

See `evidence/real-dashboard.png`.
