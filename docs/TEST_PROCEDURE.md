# Test Procedure (spec §27)

## Automated
- `pytest` — unit/integration: state machine, phrasing, worker queues +
  backpressure + cancellation, barge-in, quality ladder, drift, auth, isolation.
  Expected: **all pass** (33 tests in this revision).
- `python scripts/phase1_proof.py --minutes 2` — offline render proof; expected
  **PASS** (one stable frame per audio frame; review `samples/phase1.mp4`).
- `python scripts/licence_audit.py` / `make audit` — expected **FAIL/PENDING**
  until the manifest is pinned on the build host; **PASS** required before release.

## End-to-end (per phase)
1. **Phase 1:** run the proof; visually confirm identity stability, no teeth
   flicker, no drift over 2 minutes.
2. **Phase 2:** POST streamed text to the session; confirm it starts speaking/
   animating before the full text arrives (phrase chunks).
3. **Phase 3:** point `AURA_BRAIN_ENDPOINT` at Command Desk; confirm a real
   response streams through unchanged; confirm interrupt-notify reaches the brain.
4. **Phase 4:** speak into the browser client; confirm VAD → transcript → reply;
   interrupt mid-reply and confirm it stops, discards, and returns to LISTENING.
5. **Phase 5:** run the browser then Flutter client; confirm A/V + data events;
   verify drift < 80 ms under load.
6. **Phase 6:** kill a worker and confirm supervised restart; expire a token and
   confirm rejection; force a renderer error and confirm quality drop/fallback,
   not a frozen face or dropped session.

## Acceptance
See `docs/DEFINITION_OF_DONE.md`. Release requires: tests pass, phase gates pass,
and `licence_audit.py` returns PASS.
