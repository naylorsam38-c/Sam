# Command Desk — Backend Build Spec

**For:** Dispatch
**From:** Sam
**Scope:** Backend only. The frontend (cockpit) is built, tested, and deployed separately. This spec is the machinery that makes the cockpit's controls move real things. Nothing here changes the frontend contract.

---

## The frame Sam is working to

You → **Nova (the hub)** → **worker LLMs** → **apps**. Commands flow down, results flow back up. Nova orchestrates and is the smart one; she never operates an app herself. The workers do the work. A separate **memory LLM** holds the archive so Nova doesn't carry that load.

The hard truth this spec answers: **apps like Gmail, Calendar, Maps, Claude, ChatGPT will not open inside the app viewer** — they block embedding. So the interface can't be where the work visibly happens. The backend has to do the work and feed back a record Nova and Sam can trust. Everything below exists to make the system *reliable and well-remembered* rather than *visibly live inside the frame*.

---

## 1. Tool layer (how workers actually do anything)

Right now workers can only talk. They need real capability. Build a backend tool layer so a worker LLM can act on a real service and return a result.

- Each connected service (Gmail, Calendar, etc.) gets a backend connection the worker can call.
- The worker requests an action ("read latest email", "draft reply", "what's on the calendar Thursday").
- The tool layer performs it and returns structured results the worker can reason over.
- **No action is taken silently.** Every action produces a record (see §4).

**Email behaviour (specific ask):** the email worker should learn and **mimic how Sam himself writes emails** — tone, length, phrasing — and get more accurate over time as it sees more of his real messages. When an email comes in, the worker surfaces *what was received and from whom*, and *the drafted reply*, so Sam can see both side by side. Drafts are not sent without Sam's approval.

---

## 2. Watching without embedding (the oversight model)

Since Sam can't watch the work happen inside the app, oversight is done by **other agents watching, plus per-app updates** — not a live video of the app.

- **Per-app status updates** flow into the viewer roughly **once a minute** — a running account of what the worker has done in that app ("checked 3 emails, drafted 1 reply, nothing sent"). Not real-time; a steady heartbeat.
- Nova reads these and always knows the state of play across every app without operating anything.
- **The hub has its own read-only link to each app** (separate from the worker's connection) so Sam can open Nova and ask "what's been done in Gmail today?" and get a straight answer. This keeps the wires from crossing — the hub observes, the worker acts, and they don't share one tangled connection.

---

## 3. Cross-checked summaries (keeping the LLMs in line)

For each significant piece of work, produce **two independent summaries**:

1. The **worker's own** summary of what it did.
2. A **separate watcher agent's** summary of the same work.

Nova **cross-references the two**. If they agree, fine. **If they disagree, Nova flags it** — this is the point of having two. The watcher/summary agent does *not* have to be the hub; workers summarise themselves, a separate agent summarises them, and those roll up to Nova.

> Build note (constructive, per Sam's request for criticism): decide the **tiebreaker** when the two summaries disagree — Nova adjudicates, and if it can't resolve, it escalates to Sam rather than silently picking one. Also add **red-flag alerting** for anything clearly wrong so it surfaces immediately instead of waiting for the next minute-summary. A one-minute cadence can miss a fast mistake; an exception should interrupt, not queue.

---

## 4. Memory (the backbone — highest priority for Sam)

Memory is the point of the whole system. The value is never starting from scratch — "we've dealt with this before, here's what we learned."

**Two tiers:**

- **Worker memory:** each worker keeps a rolling **14 daily summaries (two weeks)** of its own work. Enough to stay current without noise.
- **Long-term memory LLM (the vault):** a dedicated, lightweight agent (a "llama that just holds shit") that stores **all** summaries from every agent, long-term. It does not orchestrate or decide — it indexes and retrieves. Nova asks it "have we seen this before / does this keyword mean anything?" and it answers **yes, here it is** or **no**. This offloads memory work from Nova and keeps her free to orchestrate.

**Retention:** keep the things that matter — hub↔worker conversations, the daily planner, email threads and their drafted replies, and the summaries. (Exact retention/archival window is **TBD — Sam will tune this by trial once it's live.** Design it so the window is a setting, not a hardcode.)

**Nightly review:** each night, **Nova + the memory LLM run a debrief** — "is there anything we haven't touched lately, anything we've missed, anything old worth following up?" The memory agent retrieves; **Nova decides** what, if anything, to act on. Memory surfaces; the hub judges.

---

## 5. What is explicitly OUT (Sam ruled these out — do not build)

- **Do not** run Claude or ChatGPT *inside* Command Desk as embedded apps, and **do not** try to wire Claude-with-its-full-tools into the system. Sam wanted a closed loop with Claude keeping all its native tools; that isn't available, he knows it, it's decided. Drop it. (These services may still appear as pickable apps in the frontend, but the "LLM operates them live in the frame" path is not a build target.)
- **Do not** rely on embedding any app that blocks it. Assume Gmail/Calendar/Maps/etc. cannot be shown in an iframe; the backend link + per-app updates is the substitute.

---

## 6. Calendar (needs to be visual, unlike email)

Email can be handled as text (received message + drafted reply). **Calendar can't** — Sam needs to actually *see* it. Since Google Calendar won't embed, build it as **Command Desk's own calendar view backed by a two-way sync**:

- Sam works inside Command Desk's calendar.
- It syncs with the external calendar both ways: changes made anywhere propagate to the other, on update.
- Nova/agents can read it to brief and plan ("here's your day planner").

---

## Priority order (suggested)

1. Tool layer + per-app updates (nothing works until workers can act and report).
2. Memory: worker 14-day window + long-term vault + retrieval API for Nova.
3. Cross-checked dual summaries + Nova adjudication + red-flag alerts.
4. Hub's read-only links per app ("what happened today?").
5. Nightly Nova+memory debrief.
6. Visual calendar with two-way sync.

---

## Open items Sam will decide by trial (don't block on these)

- Exact memory retention window and archival policy.
- Whether the long-term vault is one agent or folds into the hub (Sam leans: separate agent, less load on Nova).
- Summary cadence fine-tuning (starting point: ~1 min per-app; nightly debrief).
- How much history to keep visible vs archived-but-searchable.

*This spec is a working draft from a live design session — Sam is building it in real time. Treat the priority order and the two-tier memory model as firm; treat the tunables above as expected to change once it's running with real users.*
