# Barge-In & Cancellation

Barge-in is what makes Aura feel like a real conversation: the moment the user
starts speaking while the avatar is talking, the avatar stops **immediately**,
discards everything it was about to say, tells Command Desk it was interrupted,
and returns to listening. This is implemented in `Session.barge_in`
(`aura/session.py`).

## Trigger

Barge-in fires when the `VADWorker` publishes a `VAD` `start` while the session
is in `SPEAKING` or `STARTING_SPEECH` (see `Session._on_vad`). A user can also
trigger it explicitly with the `interrupt` control message from the UI. It only
applies to turns that are `interruptible` (the default).

## The 6 steps

```
SPEAKING ──(VAD start)──▶ INTERRUPTED ─┐
                                       │  1. stop TTS generation
                                       │  2. discard unplayed audio
                                       │  3. cancel in-flight frames + drain queues
                                       │  4. publish BARGE_IN; notify Command Desk "interrupted"
                                       │  5. RECOVERING (flush phrase buffer)
                                       ▼
                                   LISTENING  6. attentive listening again
```

1. **Enter INTERRUPTED.** `sm.to(State.INTERRUPTED)` — a legal transition from
   `SPEAKING`/`STARTING_SPEECH`. A `state` event goes to the client.
2. **Cancel the in-flight work.** For both the `tts` and `render` workers:
   `cancel_current()` aborts the item being processed *right now* (the phrase
   being synthesized / the frames being rendered) via cooperative
   `asyncio.CancelledError`.
3. **Drain the queues.** `_drain(worker.q)` empties each worker's bounded queue so
   no already-queued phrases or frames get spoken after the interruption.
4. **Announce it.** Publish `BARGE_IN` on the bus (any other downstream consumer
   cancels), then submit an `{interrupted: true}` item to the `brain` worker,
   which `POST`s an interrupted notice to Command Desk
   (`<endpoint>/interrupted`) so the brain knows its previous response was cut off
   and can adjust. An `interrupted` event (with the interrupted `turn_id`) is
   pushed to the client, and `TurnMetrics.interruptions` is incremented.
5. **Recover.** `sm.to(State.RECOVERING)` and flush the phrase chunker so no
   leftover half-phrase survives.
6. **Listen.** `sm.to(State.LISTENING)` — back to attentive listening, ready for
   the new utterance that triggered the barge-in.

## What gets cancelled vs drained

| Target | Action | Mechanism |
|---|---|---|
| TTS current phrase | cancelled mid-synthesis | `tts.cancel_current()` |
| TTS queued phrases | dropped | `_drain(tts.q)` |
| Render current frames | cancelled mid-render | `render.cancel_current()` |
| Render queued audio | dropped | `_drain(render.q)` |
| Unplayed audio | discarded | queue drain + publisher stops on cancel |
| Phrase buffer | flushed | `chunker.flush()` |
| Command Desk | told "interrupted" | `brain.submit({interrupted:true})` → `/interrupted` |

The cancellation is **cooperative**: the CPU fallback renderer yields control with
`await asyncio.sleep(0)` between frames precisely so a barge-in can interrupt it
between frames rather than after a whole clip.

## How Command Desk is told

The `BrainConnector` (`aura/workers/brain.py`) handles the `{interrupted}` item by
`POST`ing to `<AURA_BRAIN_ENDPOINT>/interrupted` with `{session_id, turn_id}`.
Failure to deliver the notice is logged as a warning but never blocks recovery —
the user experience (stop + listen) always takes priority.

## Latency intent

Because step 2–3 cancel in-flight work rather than waiting for it to finish, the
avatar stops within a frame/phrase boundary — the user should perceive the
interruption as immediate. Timing is captured in per-turn metrics so regressions
are visible (see [MONITORING](MONITORING.md)).
