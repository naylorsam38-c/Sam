# Command Desk — review sheet

Go through it line by line. Mark each one. Bring it back and I run the lot.

Marks: `OK` = correct/yes · `NO` = wrong/no · `?` = don't know yet · or write over the top of it.

---

## A. What I found in the files. Confirm or correct me.

| # | Finding | Mark |
|---|---|---|
| A1 | `SPEC.html` is **Aura** — a self-hosted talking-avatar system. A different project from Command Desk. Two copies were uploaded; they are byte-identical. | |
| A2 | `CommandDesk_COMMAND_final_merged.md` is the governing document. Stages 0–5. Everything else defers to it. | |
| A3 | `commanddesk_rebuild` (30 Jul, 22:04, 378-line `app.js`) is **newer and fuller** than `Command_Desk_Home_Redesign` (30 Jul, 17:18, 70-line `app.js`). | |
| A4 | ~~Neither front end has a login gate.~~ **CORRECTED.** True only of the front-end-only zips. `command_desk_full_system` (dated today) has the gate built properly — see section F. | |
| A5 | ~~Stage 1 not done, Stage 3 must not start.~~ **CORRECTED.** Stages 1–4 are built and live. | |
| A6 | The older front-end-only bundles still wire `webkitSpeechRecognition`. The live frontend in `full_system` is static-only with motion stripped. | |
| A7 | ~~No backend in any zip.~~ **CORRECTED.** `command_desk_full_system` contains the whole backend — 4,347 lines of Python. | |
| A8 | Clean: no `.mp4`, no `<video>`, straight quotes throughout, chat contract intact (`{avatar, theme, agent, message, session_id}` → `/commanddesk/chat`). | |
| A9 | The doc says zips are **not** deployment candidates — "the live running system is the ONLY truth." These files are reference. | |
| A10 | Nothing built in this chat session (the 8787 app) relates to Command Desk. It came from a wrong description of the handoff. | |

---

## B. Decisions only you can make.

| # | Question | My recommendation | Your answer |
|---|---|---|---|
| B1 | Which front end is the base to work from? | `commanddesk_rebuild` — newer and far more complete | |
| B2 | Can anything in this session reach the EC2 box? If not, where does the real work happen? | If there's no path, run Claude Code on a machine that can reach it | |
| B3 | The 8787 app and PR #3 — close and delete, or keep parked? | Close it. It's unrelated. | |
| B4 | Is Stage 0 actually done? Have all six agents answered a *fresh* question since the 30 July stale-context freeze? | Unknown to me — needs checking on the box | |
| B5 | Login credentials still `command` / `Nova` as written in the doc? | Confirm before I build the gate around them | |
| B6 | Gmail OAuth — still at "credential downloaded, NOT installed on the box, allow-tap not done"? | Confirm; it gates Stage 2 | |
| B7 | Does Aura stay a separate project, parked for now? | Yes — it needs a CUDA GPU and shares nothing with Command Desk | |
| B8 | Mic: stays parked as the doc says, or is the phone-app path (record → Whisper on the box → Nova) now in scope? | Stays parked. Don't open two unknowns at once. | |

---

## C. The work queue. Tick what I do when you come back.

| # | Task | Touches live system? | Tick |
|---|---|---|---|
| C1 | Full audit of `commanddesk_rebuild` against every PIN and every rule in the COMMAND doc. Output: line-by-line pass/fail with file and line references. | No | |
| C2 | **Build the identity gate.** Backend-checked (never in front-end source), covers the whole page, HTTPS-only, bound to the same `session_id` the state machine uses, lockout after 5 failed attempts, failed attempts logged. New files only — nothing overwritten. | Code written here, deployed only on your go | |
| C3 | Park the mic properly — remove the dead `webkitSpeechRecognition` path so it can't half-fire. Keep Nova speaking replies out. | No | |
| C4 | State machine in SQLite: `idle → listening → processing → idle`, with the timeouts from the doc (120s on `awaiting_confirmation`, 30s on reads and sends, expiry → `error` → `idle`, late results discarded). | Yes — needs the box | |
| C5 | Audit log schema in the existing SQLite: timestamp, state, trigger, result, on every hop. | Yes — needs the box | |
| C6 | Router as its own module: text in → named worker + confidence out, logged every time. Low confidence → ask Sam, never guess. | Yes — needs the box | |
| C7 | Permission layer skeleton: worker requests an action, layer holds the tool and the gate. Gmail READ first. Send stays off until Stage 4. | Yes — needs the box | |
| C8 | The six backend gaps listed at the end of `PROMPTScommanddeskv3.md`: per-task telemetry · `decisions` table · health-metric calculations · risk register · Observer's five thresholds as SQL · deterministic Mode C trigger. Report which already exist and which must be built. | Yes — needs the box | |
| C9 | Exactly-once send (Stage 4B): `in_flight` written before the Gmail call, reconcile after, never resend on a lost reply. | Yes — Stage 4, later | |

---

## D. Things I will not do without you saying so

- Touch airexploit.com, /commanddesk, or nginx on that host.
- Deploy anything from a zip.
- Write "tested" or "works" for anything only you can see on your phone.
- Start a stage before the one before it is proven.
- Build a second unknown at the same time as a first.

---

## F. Audit of the live system snapshot (`command_desk_full_system`, dated 2026-08-02)

I traced these through the source myself rather than trusting the README.

### F1. The identity gate is real. It holds.

| Check | Result |
|---|---|
| Password stored hashed, never plaintext-compared | **PASS** — bcrypt, `checkpw` (`auth.py:47`) |
| Never in any front-end file | **PASS** — backend-only constant |
| Gate on backend actions, not just the page | **PASS** — `require_auth` on every gated route, and the permission layer re-checks independently |
| HTTPS only | **PASS** — `secure=True`, `httponly=True`, `samesite='lax'` |
| One session identity, shared with the state machine | **PASS** — login opens the real `sessions` row; no parallel session concept |
| Lockout on repeated guesses | **PASS** — 5 failures / 15-min rolling window → 429 |

The `samesite='lax'` choice is correct and the reasoning in the code is right: `strict` would silently break the Google OAuth callback.

### F2. Gmail is NOT exposed to an unauthenticated caller. Your absolute failure condition holds.

`permission_layer.request_gmail_read` calls `validate_session` **before** any action row, any state transition, and any Gmail call (`permission_layer.py:212`). Draft and send do the same. So even reached through an ungated route, an unauthenticated caller gets `"Not authenticated -- Gmail read refused."` The defence-in-depth is genuine.

### F3. **One real exposure.** `/commanddesk/chat` is public and unauthenticated.

Traced end to end: `https://airexploit.com/commanddesk/chat` → nginx `location /commanddesk/` → adapter :8000 `/chat` → core `/api/chat` → `handle_turn()` → **the brain**. No `require_auth` anywhere on that path.

Consequences:
- Anyone who finds the URL can talk to your models and **spend your Anthropic budget**.
- It accepts a caller-supplied `session_id`, so an outsider can write into session transcript and continuity.
- It contradicts the doc: *"It covers the whole page, not just Gmail... one gate in front of everything leaves no gap to slip through."*

Not affected: Gmail (F2 blocks it).

### F4. The other ungated routes are less alarming than the README implies.

`/api/tools`, `/api/groups`, `/api/agents/*`, `/api/memory/*`, `/api/decision`, `/api/nudge` are all ungated — but core binds `127.0.0.1` and nginx proxies only three core prefixes (`/auth/`, `/oauth/`, `/nova/`). None of them are reachable from the internet. Reachable only from the box itself. Worth fixing, not urgent.

Credit where due: `tools.py` strips credentials out of every read path (`get_tool_public`, `_public`), so even locally nothing leaks a stored token.

### F5. Rotate the login password.

`core/auth.py` carries `DEFAULT_PASSWORD = 'Nova'` as a cleartext constant, and the same credential is written into the COMMAND doc. Both are now in zips that have moved around. The README flags this itself. It's a one-line fix on the box.

---

## E. Open question I can't answer from the files

The doc says Nova speaks and Sam types for this phase. The front end does have interactive chat wired to `hub`. If what you're missing is interactive **voice**, that's the parked mic (A6/B8) and it's a later stage by the doc's own order. If what you're missing is interactive **text on the live site**, tell me — because the code for that exists in `commanddesk_rebuild` and the question becomes why it isn't working on the box, which is a Stage 0 answer, not a rebuild.
