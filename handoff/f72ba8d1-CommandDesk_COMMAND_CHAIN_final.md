# Command Desk — the command chain to the goal

**THE GOAL:** A live interface Sam talks to. Sam speaks to Nova. Nova routes the job to whichever LLM worker is set up for it. The worker does the job, sorts it, and Sam sees the end result on screen.

This is the chain that gets there. Hand it to Dispatch ONE stage at a time. Each stage is proven on the live site before the next starts. I ran this through several passes and closed every place Dispatch tends to wander — those are the PINS, and they apply to every stage.

---

## THE PINS — apply to every stage, never break

1. **One live path only.** Work in /var/www/commanddesk. Prove on airexploit.com/commanddesk. Old zips and side copies are not real — if it isn't the live path, ignore it.
2. **Backend Python untouched.** Never overwrite or restart it. Back up the webroot and the front end before touching anything; keep the old front end restorable.
3. **Straight quotes only** in every command. Copy assets/video/* on deploy. Curl HTTP 200 before any deploy is called done.
4. **The state machine is a real variable, not a vibe.** One variable holds the current state. Every action reads it. It is code.
5. **Anything with consequences is behind a hard gate.** The action function cannot run unless the state is awaiting_confirmation AND a confirmation word was captured. Off until its stage.
6. **"Done" means proof, not "the code ran."** Done = the audit log shows the states firing on the live site, and Sam has seen/heard it himself. Dispatch cannot watch Sam's phone — it proves what it can (logs, generated files it can inspect) and does NOT claim to have seen the live phone result. Sam is the final eyes.
7. **One stage at a time.** Finish it, prove it, STOP, wait for Sam to say go. Do not start the next stage early.
8. **Don't stall on questions.** One interruption allowed only if a key or permission is genuinely missing — one line, then carry on. Otherwise make your own calls.
9. **The audit log is always on.** Every state change and action writes one line: timestamp, state, trigger, result.

---

## STAGE 0 — Turn the lights on (inventory, no building)

We cannot call any plan flawless in the dark. First, find out what's actually there.

- Confirm the live path and that the backend is running.
- List every LLM worker / model already wired on the box — names, which is reachable (Ollama, Claude key, etc.), what each is meant to do.
- Trace the voice pipeline and report its four links: mic capture, speech-to-text, reply, text-to-speech — which exist, which are dead.
- Report all of it. Build nothing.

**Done:** a plain report of what workers exist, what the voice pipeline's state is, and what's missing. This tells us exactly what Stages 1–4 can promise.

---

## STAGE 1 — The interface he can talk to

- Nova loop as the skin: the seven-second clip, continuous, crossfaded at the loop point so there is NO jump. No tiles. Just her, plus a mic/talk control and one empty panel for results later.
- Voice both ways: Sam speaks, Nova speaks back out loud on the live page.
- Fix the voice one link at a time, in order (mic -> speech-to-text -> reply -> text-to-speech). Report which link was dead.
- State machine live: idle -> listening -> processing -> idle.

**Done:** Sam talks on the live site and hears Nova reply. Log shows the states firing. No mail, no routing yet.

---

## STAGE 2 — She routes to a worker and shows the result

- Nova takes the spoken text and picks the right worker. The router must output an explicit worker name + the instruction, and log it. If nothing matches, she says so — she does NOT improvise or pretend.
- Start with a no-consequence job (reading/checking/summarising — nothing that sends or changes anything). The chosen worker does it, sorts it, returns a result.
- Result appears in the panel AND Nova says it out loud.

**Done:** Sam speaks a job, the right worker runs it, and the real result shows on screen and is spoken. Nothing with consequences yet.

---

## STAGE 3 — Action, behind the gate

- Now allow a job that DOES something (e.g. draft an email — draft only first, then send).
- State reaches draft_ready -> awaiting_confirmation and STOPS. Nova shows the draft, asks "send it?"
- Send is a separate locked function. It only unlocks on a captured "yes / send it". "Change it" -> back to processing. Never sends without the word.

**Done:** Sam speaks the ask, sees the draft, says yes, it sends. Log shows the confirmation that opened the gate.

---

## STAGE 4 — Clone

- Once one worker runs end to end, the rest are copies. Swap the worker + its instruction. Same router, same gate, same log.

**Done:** a second worker works the same way.

---

## Why this order can't get lost
Every stage proves ONE new link and nothing else: Stage 0 shows what's real, Stage 1 proves voice, Stage 2 proves routing with zero risk, Stage 3 adds the only dangerous part behind a gate, Stage 4 just repeats. Dispatch is never asked to build two unknowns at once, never asked to prove something it can't see, and never allowed to send without a caught yes.
