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

## G. The screenshot, the tests, and the three HTML files

### G1. `test_compare.py` — I ran it. 25/25 passed.

Byte-identical to the copy in the snapshot. The deterministic half of the oversight brain genuinely works: wrong amounts caught, money formatting not creating false mismatches, invented months and weekdays caught, genuine intent not falsely accused.

**One bug:** the run command in its own docstring is wrong. `python -m oversight.test_compare` fails with `ImportError: attempted relative import beyond top-level package`. The working command is:

```bash
cd backend && python3 -m core.oversight.test_compare
```

### G2. The screenshot — `[research] ok` is not in any code you've sent me.

Dated **Thu 30 July**, showing the Research room returning `[research] ok` to "hello". I searched every package: that reply exists nowhere in the current backend, nor in any of the six front-end bundles. Two things follow:

- It came from whatever was running on the box on 30 July — consistent with the COMMAND doc's Stage 0 note that builder and tester were frozen on a stale refusal and personal_assistant returned an empty reply.
- There's no login screen in the screenshot, which fits: 30 July predates the Stage 1 gate.

So this is most likely a **historical** picture, not current state. I can't confirm that without the box.

### G3. `commanddesk_2.html` — this is a working unauthenticated client for the exposure in F3.

It posts straight to `/commanddesk/chat` with `{avatar, theme, agent, message}` and **no session_id and no login**. Served from airexploit.com it reaches the agents. This isn't a theoretical hole — this file is a demonstration of it.

### G4. `commanddesk_match.html` is superseded. Don't treat it as current.

It certifies "Nova, full body, animated face — blinks when idle, mouth moves when she speaks." The live system has **motion stripped, static only**, per your later explicit instruction. The document describes an earlier build.

### G5. `reviewqueue.html` is a mockup, not wired.

Hardcoded example cases (the same Acme/March fixtures as the tests). The buttons only fade the card — no backend call, nothing written to `review_queue`. Also: it pulls fonts from `fonts.googleapis.com`, so every view of your private oversight page makes a request to Google. Worth removing before it goes anywhere real.

---

## H. The two roadmaps — and why one of them can't run

### H1. `COMMANDDESKFINALROADMAP` assumes PostgreSQL. Your live system is SQLite.

This is the blocker. Verified: `core/db.py` line 37 is `sqlite3.connect(...)`. There is no Postgres anywhere in the snapshot.

| Roadmap step | Requires | On SQLite |
|---|---|---|
| **Step 7** — `observer_readonly` DB role, `GRANT SELECT`, revoke public | Postgres roles + grants | **Impossible.** SQLite has no users, no roles, no GRANT. |
| Step 5 — `payload jsonb`, `timestamptz` | Postgres types | Not available |
| Step 9 — RLS via `current_setting('app.tenant_id')` | Postgres row-level security | Not available |
| Step 14 — Terraform, RDS, migration chain 001→005 | AWS RDS | Live system is a file on the EC2 box |

Step 7 is the one the roadmap itself singles out: *"it's the only guarantee that survives prompt injection. Everything else assumes the model is behaving."* That guarantee cannot be built on the database you're actually running.

`tenant_id` does exist — but as a plain `TEXT` column in SQLite. It's a label, not a boundary. Nothing enforces it.

**Also absent — every file the roadmap's first half builds:**

```
MISSING  core/versioning.py      MISSING  core/events.py
MISSING  core/policy.py          MISSING  core/enforcement.py
MISSING  core/policy.yaml        MISSING  sql/observer_thresholds.sql
```

`core/migrations/` contains one Python file (`m001_seed_six_templates.py`), not the `001`–`005` SQL chain with down-scripts the roadmap assumes.

**The decision this forces:** either migrate SQLite → Postgres/RDS first, or rewrite the roadmap's enforcement steps for SQLite and accept that Step 7's protection can't exist. That's yours to make, and nothing past Step 4 should start until it's made.

### H2. `COWORKROADMAPcommanddeskv2` is badly out of date. Treat it as history.

Its "confirmed state" section describes a system you no longer have:

| It says | Reality in the live snapshot |
|---|---|
| Backend local at `127.0.0.1:8765` | Deployed on EC2, live at airexploit.com/commanddesk |
| **"Zero Anthropic API credit. No live Claude call verified yet"** | Claude calls working; Hub on `claude-sonnet-5` |
| Flutter Android APK is the client | A static web frontend is the client |
| Project folder inside OneDrive | `/home/ubuntu/commanddesk/` on the box |

One thing it does confirm: *"Model string corrected to `claude-sonnet-5` throughout."* That settles the model-ID question from the start of this session.

### H3. Two of the five files are exact duplicates.

- `test_compare_2.py` — byte-identical to the copy I already ran (25/25 passed).
- `Command_Desk_Frontend_Workspaces_2.zip` — every file identical to the earlier Workspaces zip.

### H4. `app_3.js` is yet another front end, and it matches none of the others.

I diffed it against every bundled `app.js`. It's distinct. That makes **at least seven separate front-end builds** in circulation, only one of which — `full_system/frontend` — is live. This one has:

- **no login** — same gap as the other non-live builds
- posts to `/commanddesk/chat`, the ungated path from F3
- an animated blinking/mouth-moving avatar, superseded by your later static-only instruction
- `iframe` app panels with `referrerpolicy="no-referrer"` (sensible), and `escapeHtml` on all transcript rendering (also sensible — no injection hole there)

---

## I. What's been dropped — cross-comparing all five dispatch docs

### I1. `DISPATCHv4buildspec` — nothing lost. Safe to discard.

`COMMANDDESKFINALROADMAP` says it supersedes this, and it does. FINAL is a strict superset: it adds reversible migrations with tested down-scripts (Step 2), Hub's event-completion guarantee (Step 6), the 72-hour approval TTL, health-as-counts detail, and 8 acceptance tests instead of 5. Nothing in v4 is absent from FINAL. The same PostgreSQL blocker (section H) applies to both.

### I2. `BACKEND_SPEC_for_Dispatch` — six requirements never built, and absent from the final COMMAND doc.

This is the real find. Verified against the live code, not the README.

| Requirement | Status in the live system |
|---|---|
| **Per-app status updates ~once a minute** | **NOT BUILT.** Impossible as designed — there is no scheduler of any kind in the codebase. `vault.py:19` states it outright. |
| **Nightly Nova + memory debrief** | **NOT BUILT.** Same reason — nothing can fire on a nightly cadence. |
| **Hub's own read-only link to each app**, separate from the worker's | **NOT BUILT**, and it contradicts the current design, which deliberately funnels all Gmail through one place. |
| **Two independent summaries, Nova cross-references and adjudicates** | **DIFFERENT.** Oversight compares Hub's *stated intent* against *what happened* — not a worker summary against a watcher summary. Angel writes to a `review_queue` for you, so there's **no tiebreaker and no escalation path through Nova**. |
| **Red-flag alerting that interrupts immediately** | **NOT BUILT** — and directly contradicted by `PROMPTS v3`: *"Nothing is ever pushed as an alert. Everything is available on demand."* Two of your own documents disagree. |
| **Calendar: Command Desk's own view + two-way sync** | **NOT BUILT.** No calendar module exists anywhere. |
| Email style mimicry | **BUILT** — `core/style_profile.py`. |

### I3. A number conflict worth settling in one line.

`BACKEND_SPEC` says worker memory is **14 daily summaries (two weeks)**. The live code says:

```python
MEMORY_WINDOW_DAYS = int(os.getenv("MEMORY_WINDOW_DAYS", "4"))  # 3-5, tunable
```

and the snapshot README calls 4 *"Sam's locked 3-5 day spec."* Fourteen versus four. It's env-tunable so changing it is trivial — but two of your documents record different things as "locked."

### I4. A stated invariant that isn't quite true.

The snapshot README says the Gmail tool *"lives in exactly one place… no other path in the codebase touches the Gmail API."* There is a second path: `style_profile.py:60` builds its own Gmail service and reads your sent mail directly.

It is auth-gated at the route (`/api/style_profile/build` has `require_auth`) and it does write to the audit log — so this is **not** a security hole. But it bypasses the permission layer, so that read creates no action record and gets no independent session re-check. The invariant is worth either restoring or restating.

### I5. `Dispatch_ORDER_full` — do not hand this to anyone now.

It opens: *"Do all of it. Don't come back until it's done… Do not ping Sam mid-run with questions."*

That is the direct opposite of the final COMMAND doc, which says *"One stage at a time. Finish, prove, STOP, wait for go"* and requires every task be reverse-engineered and brought back to you **before** work starts. It also tells dispatch to copy `assets/video/*` (video is now explicitly dropped) and defaults the mail worker to Ollama (live runs Haiku). Superseded on every major point.

### I6. Superseded across the older docs — for the record

- **Nova as a 7-second video loop** (`COMMAND_CHAIN_final` Stage 1, plus `Dispatch_ORDER` and `Dispatch_Checklist` both saying copy `assets/video/`) → the final COMMAND doc drops video entirely, and the live frontend is static-only.
- **"Backend Python untouched, never restarted"** (`Dispatch_Checklist`, `COMMAND_CHAIN` pin 2) → superseded. The Python backend has since had the permission layer, router, state machine, oversight and auth built into it.
- `Dispatch_Checklist` steps 2.1–2.9 (mail worker read → draft → send) → all completed; they're Stages 2–4 in the final doc.

### I7. Net: what's actually still missing from everything built

1. Calendar — own view, two-way sync. Never started.
2. Any scheduled work at all — the 1-minute heartbeat and the nightly debrief both need a scheduler that doesn't exist.
3. Hub's independent read-only view per app ("what happened in Gmail today?").
4. Worker-vs-watcher dual summaries with Nova adjudicating a disagreement.
5. Interrupt-level alerting for something clearly wrong — pending your call on push-vs-pull, since your docs conflict.

---

## E. Open question I can't answer from the files

The doc says Nova speaks and Sam types for this phase. The front end does have interactive chat wired to `hub`. If what you're missing is interactive **voice**, that's the parked mic (A6/B8) and it's a later stage by the doc's own order. If what you're missing is interactive **text on the live site**, tell me — because the code for that exists in `commanddesk_rebuild` and the question becomes why it isn't working on the box, which is a Stage 0 answer, not a rebuild.
