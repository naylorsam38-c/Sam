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
| A4 | **Neither front end has a login gate.** No login form, no password check, no auth anywhere. `authMode: "Existing site session"` in `config.js` is a label, not a lock. | |
| A5 | By the doc's own rule, that means Stage 1 is not done and Stage 3 must not start. | |
| A6 | Both front ends still wire `webkitSpeechRecognition` — the dead link the doc says to park, and the one that cannot work in iPhone Safari. | |
| A7 | No backend in any zip. No hub, no six agents, no Ollama, no SQLite, no EC2. Stages 0, 2, 3, 4 have no code here. | |
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

## E. Open question I can't answer from the files

The doc says Nova speaks and Sam types for this phase. The front end does have interactive chat wired to `hub`. If what you're missing is interactive **voice**, that's the parked mic (A6/B8) and it's a later stage by the doc's own order. If what you're missing is interactive **text on the live site**, tell me — because the code for that exists in `commanddesk_rebuild` and the question becomes why it isn't working on the box, which is a Stage 0 answer, not a rebuild.
