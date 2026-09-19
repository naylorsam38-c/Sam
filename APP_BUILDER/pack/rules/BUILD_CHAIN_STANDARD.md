> **Read `ACTIVE/THE_BUILD_CHAIN.md` instead.** That document describes the five
> scripts as they actually exist — what each one does, what it refuses to do,
> and what has and has not been proved. This spec stays locked here as the
> authority they were built against, and is what settles a disagreement. It is
> no longer the thing to read first.

# THE BUILD CHAIN — SPEC

**Companion to THE SCRIPT STANDARD. That is the standard. This is the machinery.**
Locked 2026-09-08. Repointed to god mode 2026-09-15 — see UNRESOLVED.

Written to be handed to a builder without further conversation. Everything here
obeys the Script Standard; where they disagree, the Script Standard wins.

---

## WHAT IS BEING BUILT

**One command.** It runs straight through to the end without stopping to ask
anything. It finishes in one of three states and no others:

- **BUILT** — the whole chain is green, with a level-1 check proving a human can
  actually use it. Production ready.
- **HELD** — a numbered gap the shelf genuinely cannot fill. Stops, names it,
  hands it over.
- **BROKEN** — the chain cannot make progress (see the loop guard). Stops, names
  what is going in circles.

"Built" never means "the script ran." It never means "it was explained." It means
a real person's journey completed in a real browser against a real system, and
the ledger says so.

---

## THE FOUR SCRIPTS

| Script | Job | Model? |
|---|---|---|
| `chain.py` | The one command. Orchestrates everything below. | No |
| `layer1_checks.py` | Runs the hard checks. Pass or fail. | No |
| `layer2_repair.py` | Places a numbered part from the shelf. | No |
| `layer3_gap.py` | Writes a gap record, and only then calls a model to build one part. | Only here |
| `watch.py` | Audits the whole run against god mode. Read-only: never repairs, never calls a model. | No |

Only `chain.py` is run by a human. Everything else is called by it.

All five obey Script Standard §1.3 — plainly labelled config block first, every setting
commented, double-clickable, no terminal required.

---

## `chain.py` — THE ORCHESTRATOR

### The loop

```
  start
    │
    ▼
  new RUN number ──────────────────────────┐
    │                                      │
    ▼                                      │
  layer1_checks.py                         │
    │                                      │
    ├── all PASS, level-1 present ──▶ watch.py ──▶ BUILT
    │                                      │
    └── any FAIL                           │
          │                                │
          ▼                                │
      layer2_repair.py                     │
          │                                │
          ├── part found ──▶ apply ────────┤  restart from the top
          │                                │  as a NEW run number
          └── no part                      │
                │                          │
                ▼                          │
            layer3_gap.py                  │
                │                          │
                ├── part built + numbered ─┘
                │
                └── cannot build ──▶ HELD
```

**A repair never resumes.** After any repair the chain restarts from the
beginning as a new numbered run, and every check runs again from scratch. A
repaired run is re-proved from the top, never patched in the middle. This is the chain's own
rule and it is not negotiable — resuming means the checks before the repair ran
against a different system than the ones after it.

### Stopping conditions

It stops, and only stops, on:

1. **BUILT** — layer one fully green, at least one level-1 check passed, `watch.py`
   passed its audit.
2. **HELD** — layer three cannot produce the part.
3. **BROKEN — loop guard.** The same check number fails again after the same part
   number was applied to fix it. That part does not fix that failure. Applying it
   again is a waste of a run. Stop and name both numbers.
4. **BROKEN — restart ceiling.** More restarts than the configured maximum. This
   means something is failing in a way the shelf keeps almost-fixing. Stop and
   print the restart history: which check, which part, which run.
5. **BROKEN — regression.** A check that passed in an earlier run of this chain now
   fails after a repair. The repair took something from somewhere else.
   Stop immediately; do not attempt a second repair on top of the first.

It does **not** stop to ask a question. It does not pause between layers. It does
not wait for approval mid-run. The only approval in the system is on new part
numbers, and that happens after the chain has stopped, not during it.

### What it prints

Nothing during the run except check lines, repair lines, and run headers. At the
end:

```
RUN-0091   chain finished
BUILT
```

or

```
RUN-0091   chain finished
HELD  GAP-0012  no shelf part binds option sources on a public form
```

or

```
RUN-0091   chain finished
BROKEN  loop guard  CHK-041 still fails after option_source_binding@1.2.0 (applied RUN-0088, RUN-0090)
```

The last line is the verdict and only the verdict. Script Standard §5 — Sam reads
`FAIL` lines, `UNPROVEN` lines, and the last line.

### Config block must expose

- Path to the thing being built
- Path to the run ledger
- Path to the parts shelf
- Maximum restarts before BROKEN
- Whether layer three may be reached at all, or the chain should HOLD instead
- Which model layer three calls, and its credential
- Where reports are written

---

## `layer1_checks.py` — THE HARD CHECKS

No model. No cost. This is the whole job on a good day.

**Does:**

- Deletes and rebuilds the working directory (Script Standard §6).
- Starts the real system as a real process on its own port.
- Runs every check in the suite. Each check emits: check number, authority level
  1–5, the claim in plain English, and PASS / FAIL / SKIP with a message on
  failure.
- Drives at least one complete human journey in a real browser at level 1, and
  reports javascript errors on the page (Script Standard §1.2, §5).
- Shuts the process down, including on failure.
- Writes the full run record to the ledger.

**Never:** repairs anything, calls a model, or decides what to do next. It reports
and exits. Judgement belongs to `chain.py`.

**Exit codes:** 0 all pass; 1 one or more fail; 2 could not start the system; 3 no
level-1 check present in the suite.

---

## `layer2_repair.py` — REPAIR FROM THE SHELF

No model. Still free.

**Input:** one failure record from layer one — check number, authority level,
failure message.

**Does:**

- Reads the failure's own message and matches it against the failure-pattern map
  in its config block.
- On a match, applies the mapped part by number and version.
- Prints the original failure, then the part applied, then the layer that applied
  it. Script Standard §3 — the failure is never erased.
- Returns control to `chain.py`, which restarts from the top.

**Never invents a fix.** It only places parts that already exist on the shelf. If
the map has no entry, it returns "no part" and the chain escalates. A layer two
that improvises is indistinguishable from a layer three with no record of what it
did.

**Never prints PASS for the failure it just repaired.** The proof of the repair is
the next run, not this one.

**Exit codes:** 0 part applied; 1 no matching part; 2 part found but failed to
apply.

---

## `layer3_gap.py` — BUILD THE MISSING PART

The only place a model is touched, and the last place the chain goes.

**The division of labour, and this is the point of the whole design:** the script
diagnoses, the model builds. The model is never shown the failure and asked what
to do. It is handed a gap record and told to build exactly that.

**Does, in order:**

1. **Classifies the gap** — from the failure message, the check number, and the
   authority level, works out what class of behaviour is missing.
2. **Writes a numbered gap record** — `GAP-nnnn`, containing: the failing check
   number and text, the failure message verbatim, the authority level, what the
   missing part must do, and what would prove it exists.
3. **Only then calls the models**, handing each one the gap record and nothing
   else. Not the conversation. Not the wider codebase. Not "here's an error, fix
   it." Several candidates are generated, not one — see CANDIDATE GENERATION
   below.
4. **Runs every candidate through the full chain** and keeps only what passes at
   level 1. Rejects anything that changes more than the part.
5. **Holds it for approval.** New part numbers are permanent, so they are the one
   thing that waits (Script Standard §4). The chain records HELD and stops.
6. **On approval,** the part is numbered onto the shelf and its failure pattern is
   added to layer two's map. Layer two owns that failure from then on — layer
   three is never called for it again.

**Every trip through here permanently shrinks how often it is needed.** If the
same gap number is raised twice, the system is broken: the part was built but
never numbered onto the shelf, or its pattern was never added to layer two's map.
`chain.py` treats a repeated gap number as BROKEN.

**Never:** decides that it should be called. `chain.py` decides that. A model that
can invoke itself has no ceiling on scope or cost.

**Exit codes:** 0 part built and held; 1 gap classified but model could not build
it; 2 gap could not be classified — the failure message was not specific enough,
which is itself a fault in the check, reported as such.

---

## CANDIDATE GENERATION

The part of layer three that makes it work at all.

**The problem it solves:** a model asked to build a part once has to be right
once. That is a bet on reliability, and models are not reliable. Stacking models
to check each other does not fix it — three unreliable judges do not make a
reliable one, they agree confidently and wrongly. That approach has already been
tried and it does not hold.

**The flip:** the models stop being the judges and become the raw material. The
judge is a script driving a real browser. It cannot be persuaded and it cannot
hallucinate a pass.

### How it runs

- The same gap record goes to **several models, and to the same model under
  several different framings of the problem.**
- Each returns a candidate part. None of them are trusted.
- **Every candidate is run through the full chain** — real build, real process,
  real browser, level-1 journey.
- Candidates that fail are discarded silently. Sam never sees them.
- Candidates that pass are held for approval. If more than one passes, the one
  touching the least is preferred (Script Standard §1.6).
- If none pass, the chain reports HELD with the gap number and how many
  candidates were tried.

### Why variety, not quality

A human catches problems because they come at it from a different angle. So does
a different model, a different prompt, a different framing of the same gap. The
value is **variety of approach, not quality of judgement.** Do not tune the
models toward agreement — agreement is what killed the previous design. Spread
them apart deliberately.

### Why this is affordable

Rejection costs nothing but compute. One good part out of five is a win, and the
four bad ones are never seen. The trade is compute for correctness, and that is
the right way round: compute is cheap, being wrong is not.

This is also the answer to "how does a script invent something that does not
exist yet." It does not. It **specifies the absence precisely**, generates many
attempts, and lets a real check decide. The invention is disposable; the filter
is not.

### The counters that matter

Log per gap: candidates generated, candidates passed, which model and framing
produced the winner. If one model or framing never wins, drop it. If the pass
rate falls toward zero, the gap records are not specific enough — that is a fault
in the diagnosis, not in the models.

---

## HANDOFF CONTRACTS

The scripts pass records, not prose. Every field is required.

**Failure record** — layer one to layer two:

```
run          RUN-0087
check        CHK-041
level        1
text         the public form dropdowns were empty
message      <verbatim failure message from the run>
```

**Repair record** — layer two to the ledger and back to the chain:

```
run          RUN-0087
check        CHK-041
part         option_source_binding@1.2.0
layer        2
restarted_as RUN-0088
```

**Gap record** — layer three to the shelf and to the model:

```
gap          GAP-0012
run          RUN-0087
check        CHK-041
level        1
message      <verbatim failure message>
missing      binds option sources to fields on a public form
proves_it    a public form renders with populated dropdowns at level 1
```

If any field cannot be filled, the record is not written and the chain reports
BROKEN with the missing field named. An incomplete record is how invented work
gets in.

---

## `watch.py` — THE AUDIT

The last gate before BUILT, and the only script whose job is to disbelieve the
other four.

Everything above it is trying to make the app work. `watch.py` is trying to
catch it having only *appeared* to. It is the difference between a run that says
BUILT and a run that has earned it.

**It never repairs, never writes to the shelf, never calls a model, and never
touches the app.** It opens the run's records read-only and answers one
question: did this run actually do what it claims. A script that could fix what
it audits would have a reason to go easy on it.

### What it audits

Three groups. Any single FAIL means the chain must not report BUILT.

**Group one — did the run really run.** Script Standard §6 and §1.1.

| | Check |
|---|---|
| W-01 | The working directory was deleted and rebuilt this run. A pass read off a database left behind by the last run is not a pass. |
| W-02 | The app was served by a real process on its own port, started by the run and shut down by it, including on failure. |
| W-03 | The datastores the app needs were real and reachable. No substitute, no in-memory stand-in, no testing-mode swap. |
| W-04 | Nothing in the run was mocked, simulated, faked or stubbed — in the code or in the test data. Product answers and requirements were real, not synthesised to exercise a path. |

**Group two — was it actually proved.** Script Standard §1.2, §5, §7.

| | Check |
|---|---|
| W-05 | At least one level-1 journey ran, in a real browser, driven from outside the app. |
| W-06 | That journey passed. A `SKIP` is not a pass, and a run reporting only SKIPs is UNPROVEN, not BUILT. |
| W-07 | The page a person lands on threw no javascript errors. A page that renders 200 with no stylesheet and no scripts is not the capability working. |
| W-08 | Every check the run claims has a verdict against it. A check that was counted but never ran is a claim, not evidence. |
| W-09 | The output contract held — one line per check, verdict and count last, readable from the FAIL lines and the last line alone. |

**Group three — did the loop behave.** This is the part that audits the build
chain as a machine rather than the app as a product.

| | Check |
|---|---|
| W-10 | **Did anything need building?** If layer one went green with no repair and no gap, say so plainly. That is the cheapest possible BUILT and it should be visible as one. |
| W-11 | Every repair layer two applied was a **numbered part already on the shelf**. Layer two never invents. |
| W-12 | Every repair **restarted the chain as a new run number**. A repair that resumed mid-run is a rule break even if the app ended up working. |
| W-13 | **Did it go to a model?** If layer three was entered, a numbered gap record exists, and it was written **before** the model was called — not after, not alongside. |
| W-14 | That gap record has **every field filled**: gap number, run, check, level, verbatim failure message, what the missing part must do, and what would prove it exists. An incomplete record is how invented work gets in. |
| W-15 | The model was handed **the gap record and nothing else**. Not the conversation, not the wider codebase, not "here is an error, fix it." |
| W-16 | **Several candidates were generated, not one**, across more than one model or framing. |
| W-17 | **Did it build it right?** Every candidate kept was driven through the full chain — real build, real process, real browser, level-1 journey — and the winner passed. No candidate was kept on a model's word. |
| W-18 | The winning candidate **touched only the part**. A candidate that changed anything beyond the gap is rejected however well it works (§1.6). |
| W-19 | The new part was **held for approval, not numbered onto the shelf automatically**. New numbers are permanent and are the one thing that waits (§4). |
| W-20 | **No gap number was raised twice.** A repeat means the part was built but never shelved, or its pattern was never added to layer two's map. |
| W-21 | **No regression.** Nothing that passed earlier in this run or the previous run fails now. |
| W-22 | Every part the run put into the app has its **origin recorded — harvested or written**. A harvested part runs as its source wrote it; a written part was built against the gap record. The two are not interchangeable and the record says which. |

### What it prints

Script Standard §5, same as everything else. One line per check, `PASS` / `FAIL`
/ `SKIP`, the verdict and the count last.

Where a group does not apply, it says so rather than passing it. A run that
never entered layer three reports W-13 to W-19 as `SKIP  layer three was not
entered` — and `watch.py` still passes, because not needing a model is not a
failure. **The distinction it must never blur is between "this did not happen"
and "this happened correctly."**

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Audit passed. The chain may report BUILT. |
| 1 | Audit failed. The chain reports BROKEN and names the W-numbers that failed. A failing audit **never** downgrades to a warning. |
| 2 | Could not audit — the run's records are missing, unreadable, or incomplete. Claims nothing, exactly as a script that cannot start claims no checks. A run that cannot be audited is not BUILT. |

### Config block must expose

Script Standard §1.3 — plainly labelled, above all logic, one comment per
setting.

- Where the run's records live, and which run number to audit
- Which checks are level 1, so W-05 can tell a level-1 journey from a lower one
- The minimum number of candidates W-16 requires
- Whether an unreadable record is exit 2 or exit 1, defaulting to 2
- Every W-number switchable off individually, each one commented with what stops
  being audited if it is — because a silently narrowed audit is worse than no
  audit

### Proving it

`watch.py` is a script, so Script Standard §7 applies to it in full: it does not
ship until it has been seen to fail. At minimum it must be shown catching a run
where the browser check was skipped, a run where a gap record is missing a
field, a run where layer two resumed instead of restarting, a run where a
candidate was kept without being driven through the chain, and a run whose
records are unreadable.

An audit that has never caught anything has not been tested.

---

## PROVING THE CHAIN ITSELF

The chain is subject to its own standard. Script Standard §7 — a check never
seen to fail has not been tested.

Before delivery, break each of these on purpose and show the real output:

| Break | Must produce |
|---|---|
| A check that fails and has no shelf part | HELD with a numbered gap |
| A check that fails and has a shelf part | repair, restart as a new run, then pass |
| A shelf part that does not actually fix its failure | BROKEN, loop guard, both numbers named |
| A repair that breaks a previously passing check | BROKEN, regression, named immediately |
| A suite with no level-1 check | layer one exit code 3, chain refuses to report BUILT |
| The system failing to start at all | layer one exit code 2, no checks claimed |
| More restarts than the ceiling | BROKEN, restart history printed |

Those runs go in the ledger like any other. A chain with no recorded failures of
its own is not proven.

---

## WHY THREE LAYERS AND NOT TWO

A script cannot build something that does not exist yet. That is the only reason
layer three is in the design.

Which means layer three is temporary by nature. Every part it builds moves a
failure permanently down into layer two, where it costs nothing. A mature shelf
reaches layer three almost never, and the chain becomes a two-layer system on its
own, without being redesigned.

If layer three is being reached often, that is not the chain working. That is the
shelf being empty, or parts being built and never numbered.


---

## UNRESOLVED — what repointing could not resolve

This document was written as a companion to THE BIBLE v3, which is not in this
tree. Every reference to it has been repointed at the Script Standard, and each
repointed claim was checked to exist there before the reference was changed.
Nothing was mapped on assumption.

Three references had **no equivalent** in the Script Standard. They were not
invented and they were not quietly dropped:

| Was | What it asserted | Where it now stands |
|---|---|---|
| Bible R00 | a repair never resumes; the chain restarts as a new numbered run | kept as the chain's own rule, stated in full in the loop section above. It is not in the Script Standard. |
| Bible R09 | a repair that breaks a previously passing check is a regression and stops the chain immediately | kept as a stopping condition above, with no external authority behind it. |
| Bible Part Eight | the specification for `watch.py` | **resolved 2026-09-15, not recovered.** The original was never supplied. A spec was written fresh, at Sam's direction, derived entirely from god mode's two standards and from what this document already said the chain does. It claims no lineage to Bible Part Eight and does not reproduce it. |

The first two are safe as they stand: the chain states them itself and enforces
them itself.

The third was a real hole and is now closed. `watch.py` has a full specification
above — twenty-two checks in three groups, read-only, with its own exit codes and
its own break tests. Every check traces to something already locked: the Script
Standard's hard rules and output contract, or this document's own account of what
each layer may and may not do. Nothing in it was invented to fill the gap.

**Built 2026-09-15.** `watch.py` exists, audits a real run, and has been seen to
fail seven ways — including a run that reported PASS and exit 0 which the audit
refused anyway. The run-record contract it reads is `run_record.py`; nothing
defined one before, and a run that leaves no record cannot be audited.

**What is still unproven.** `W-13` to `W-19` audit layer three, and no real run
has entered layer three because `layer3_gap.py` does not exist. Those seven
checks have never fired against real data, and a gap was not fabricated to
exercise them. They stay unproven until the chain raises a real one.
