# The Build Chain

What each script is, what it does, and what it will not do.

This is the document to read. The Build Chain Standard stays locked in god mode
as the authority the scripts were built against — this describes what actually
exists and has been run.

Built and proven 2026-09-15 against the real Indico-backed host: real
PostgreSQL, real Redis, real chromium.

---

## One command

```
python chain.py
```

That is the whole interface. It runs to the end without stopping to ask
anything, and finishes on one of three words.

**BUILT** — every check passed, a person was driven through the app in a real
browser, and the audit agreed the run did what it claims.

**HELD** — something is missing that the shelf cannot supply, and either a new
part is waiting for your approval or layer three could not run.

**BROKEN** — something is wrong with the chain itself, not the app: a repair
that does not repair, a regression, too many restarts, or a run that could not
be audited.

The last line is the verdict and only the verdict.

---

## The six files

| File | What it is |
|---|---|
| `chain.py` | The orchestrator. The only one you run. |
| `layer1_checks.py` | The hard checks. Free. The whole job on a good day. |
| `layer2_repair.py` | Repair from the shelf. Free. Never invents. |
| `layer3_gap.py` | Build the missing part. The only place a model is touched. |
| `watch.py` | The audit. Read-only. The last gate before BUILT. |
| `run_record.py` | The record a run leaves behind, so it can be audited. |

Every one opens with a plainly labelled config block above any logic, one
comment per setting saying what it does and what changes if you alter it.

---

## `chain.py` — the orchestrator

Runs layer one. If everything passed, hands the run to the audit; if the audit
agrees, that is BUILT. If anything failed, it goes to layer two, and if the
shelf has nothing, to layer three.

**A repair never resumes.** After any repair the chain restarts from the
beginning as a new numbered run and every check runs again from scratch.
Resuming would mean the checks before the repair ran against a different system
than the ones after it.

It stops on five things and nothing else:

- **BUILT** — layer one green, a level-1 journey passed, the audit passed.
- **HELD** — layer three cannot produce the part, or is switched off.
- **BROKEN, loop guard** — the same check fails again after the same part was
  applied to fix it. That part does not fix that failure, so applying it again
  wastes a run. It names both numbers and every run they were applied in.
- **BROKEN, restart ceiling** — more restarts than `MAX_RESTARTS`. Something is
  failing in a way the shelf keeps almost-fixing.
- **BROKEN, regression** — a check that passed earlier now fails after a repair.
  The repair took something from somewhere else. It stops immediately rather
  than repairing on top of a repair.

Worth knowing: `ALLOW_LAYER_THREE = False` runs the entire chain at zero cost.
No model is ever called; the chain reports HELD at the point it would have gone
looking for one.

---

## `layer1_checks.py` — the hard checks

No model. No cost. This is the whole job on a good day.

Rebuilds the working directory, starts the real system as a real process on its
own port, runs every check, drives a real browser through a human journey,
shuts the process down including on failure, and writes the run record.

It does not reimplement any of that. The checks that prove this app are already
written and already proven — `host_test.py` — and layer one runs that for real
as its own process, then reads the record it left behind. Two copies of the same
checks would drift, and the copy that drifted would be the one reporting PASS.

**It does not trust the suite's exit code on its own.** The record is the
evidence; the exit code is a claim about it. Where the two disagree, that is
itself reported as a fault rather than resolved in favour of the friendlier one.

**Never** repairs, calls a model, or decides what happens next.

Exit codes: `0` all passed · `1` something failed, and a failure record was
written for layer two · `2` could not start the system, so it claims no checks
at all · `3` no level-1 check ran, so nothing proved a person can use the app.

---

## `layer2_repair.py` — repair from the shelf

No model. Still free.

Takes one failure record, matches the failure's **own message** against the
failure-pattern map in its config block, and applies the mapped part by number
and version.

**It never invents a fix.** It only places parts already on the shelf. No entry
in the map means "no part", and the chain escalates. A layer two that improvises
is indistinguishable from a layer three with no record of what it did.

**It prints the failure first, in full, before anything about repairing it.** The
failure is never erased.

**It never prints PASS for what it just repaired.** The proof of a repair is the
next run, not this one.

Two things it refuses to guess at. If two patterns claim the same failure it
stops and names both, because the map is wrong and picking one silently is
exactly the guess that is not allowed. If the map names a part the shelf does
not hold, or holds at a different version, it stops rather than applying
something close.

**The map starts empty**, and that is correct. An entry is added only after
layer three has built a part, the part has been approved and numbered onto the
shelf, and the failure it fixes has been seen for real. A pattern written ahead
of a part is a guess about a failure nobody has had yet.

Exit codes: `0` part applied · `1` no matching part · `2` could not complete.

---

## `layer3_gap.py` — build the missing part

The only place a model is touched, and the last place the chain goes.

**The division of labour is the point of the whole design.** The script
diagnoses; the model builds. The model is never shown the failure and asked what
to do. It is handed a gap record and told to build exactly that.

The order is not negotiable: classify the gap, write the numbered gap record,
and only then call a model. A model called before the record exists is a model
being asked to work out what is wrong, which is the thing this design exists to
avoid.

If the failure message is too vague to specify a part, it says so and stops.
That is a fault in the check, not in the shelf, and handing the vagueness to a
model would bury it.

**Several candidates, never one.** The same gap record goes to more than one
framing of the problem. Every candidate is judged by a script driving the real
system — the models are raw material, the judge is real. Candidates that fail
are discarded silently and you never see them. If more than one passes, the one
touching the least wins.

**The winner is held for approval, never shelved automatically.** New part
numbers are permanent, so they are the one thing that waits.

**It never decides that it should be called.** `chain.py` decides that. A model
that can invoke itself has no ceiling on scope or cost.

**Today it refuses to run**, because `LAYER3_ENDPOINT`, `LAYER3_MODEL` and
`LAYER3_CREDENTIAL` are empty. It names the missing setting and stops. It does
not fall back to anything. When a key lands in the config block it runs — that
is the only thing standing between here and layer three working.

Exit codes: `0` part built and held · `1` candidates tried, none passed · `2`
gap could not be classified, or a setting is missing.

---

## `watch.py` — the audit

Everything else is trying to make the app work. This is trying to catch it
having only *appeared* to.

**Read-only.** Never repairs, never writes to the shelf, never calls a model,
never touches the app. A script that could fix what it audits would have a
reason to go easy on it.

Twenty-two checks in three groups:

**Did the run really run** — the working directory was rebuilt, the app ran as
its own process and was shut down, the datastores were real, nothing was mocked.

**Was it actually proved** — a level-1 journey ran in a real browser and passed,
the landing page threw no javascript errors, every claimed check carries a
verdict, and the final verdict matches what the checks actually say.

**Did the loop behave** — what this run needed; every repair came off the shelf
and restarted the chain rather than resuming; and if a model was called, the gap
record existed first and was complete, the model got the record and nothing
else, several candidates were generated, the winner was proved rather than
trusted and touched only the part, and it was held for approval. Plus: no gap
raised twice, no regression, every part's origin recorded as harvested or
written.

**It distinguishes "this did not happen" from "this happened correctly."** A run
that never entered layer three reports those checks as SKIP and still passes,
because not needing a model is not a failure. A run that skipped its browser
check does not.

Any single FAIL means the chain must not report BUILT.

Exit codes: `0` audit passed · `1` audit failed, and the failing W-numbers are
named · `2` could not audit, because the records are missing or unreadable. A
run that cannot be audited is not BUILT.

Every check can be switched off individually in the config block — and when one
is, the audit prints `NARROWED` and names it before anything else, because a
silently weakened audit is worse than no audit.

---

## `run_record.py` — what a run leaves behind

`watch.py` never watches a run happen. It reads what the run wrote down
afterwards. This file is that written-down form, and nothing else defines it.

One record per run, one numbered directory per run, never reused. A record is
written even when the run fails, and even when the run could not start — because
a run that leaves no record cannot be audited, and a run that cannot be audited
is not BUILT.

Every field starts at a value meaning "this was not established", never at one
meaning "this was fine". An audit that reads a default and treats it as a pass
is the exact failure this guards against.

---

## What has been proved

Run for real, each break restored afterwards.

| Break | Result |
|---|---|
| The static fix reverted, so layer one genuinely fails | layer one FAIL → layer two no part → layer three refuses, naming `LAYER3_ENDPOINT` → **HELD** |
| The same with layer three switched off | **HELD**, naming the check and saying layer three is off |
| Database not rebuilt between runs | layer one reported PASS and exit 0; the audit refused it on `W-01` → **BROKEN** |
| PostgreSQL stopped and the suite forbidden from starting it | 0 checks claimed, UNPROVEN → **BROKEN**, nothing was proved |
| A part applied twice for the same failure | **BROKEN, loop guard**, naming the check, the part, and both runs |
| The run record truncated, then deleted | audit exit 2, `NOT AUDITED, and therefore not BUILT` |
| An audit check switched off | `NARROWED` printed before anything else |
| A part's provenance removed | `W-22` FAIL — origin recorded as unknown, never quietly assumed harvested |

A second pass in the same session pressure-tested every script against
adversarial input — missing suites, absent run directories, empty failure files,
unreachable endpoints. All four obey their stated exit codes exactly, and none
claims anything on a run it could not complete.

Four further defects were found and fixed in that pass. Layer two was writing
repairs into a directory the app never reads. Layer three was judging candidates
it had never applied, so the verdict belonged to the unchanged app rather than
the candidate. Layer three refused to retry a gap whose previous attempt built
nothing, which would have made that gap permanently unfixable. And no check
recorded which capability it drove, so layer three would have refused every
failure the day a key arrived — the test knew the capability all along and now
writes it down.

Two earlier defects were found by the break tests and fixed: layer two was treating a
level of `0` as a missing field and rejecting every non-level-1 failure record,
and the chain was reporting layer two's exit 2 as "matched a part and could not
apply it" when it also covers "could not run at all".

Clean state, end to end: `chain.py` → **BUILT**, exit 0.

## The shelf runs the app

Fixed 2026-09-15, and it was the thing blocking layers two and three.

The shelf's own copy of each part is now the code that serves its route. The
host builds the runtime a part needs, then replaces what was behind each shelf
route with the part sitting on the shelf. Each part names its own entry symbol
in its `PROVENANCE.json`, and the host reads it.

**Nothing in the host names an application.** The runtime factory, the model
loader and the view adapter are all facts about a particular app, so they live
in that app's own form under `harvest_source`, not in the host's config block.
Point the host at a different app's form and it builds that app's runtime and
binds that app's parts. The source repository's name survives only in each
part's provenance, where the licence requires it, and nothing reads it to
decide behaviour.

Proved by emptying `CAP-0002`'s part on the shelf: log in failed immediately,
the chain escalated to layer two, found no part, and layer three held naming the
setting it lacks. Restored, and the chain returned to BUILT.

This is also what gives a repair somewhere to land. The part file is now the
thing that executes, so a part written into it changes the app.

---

## The finding this replaced — a repair had nowhere to land

Found by pressure test, 2026-09-15, and it blocks layers two and three entirely.

`CAP-0002`'s `source.py` was emptied on the shelf and every check still passed.
Nothing noticed, because nothing executes that file.

`host.py` reads `shelf/<app>/<CAP-id>/source.py` only to decide **which**
capabilities exist. The code that actually runs is the source application's own,
resolved live from its URL map. The shelf governs which routes are served. It
does not govern what they do.

That meant there was no location where a repair or a built part changed the
app's behaviour. Layer two would place a part into a directory nothing
executed. Layer three would build one with nowhere to put it. **Fixed above.**

**Neither fails silently, and that was checked.** Layer three applies each
candidate and judges it by running the real system, so a candidate landing
somewhere inert fails its check and is discarded — it can never be held for
approval on the strength of a run it did not affect. Layer two applies and the
chain restarts; the same failure recurs and the loop guard stops it by name. The
system reports the truth in both cases. It just cannot yet repair anything.

It was the thing to solve before a model key was worth buying, and it is solved.

---

## What has not been proved

Named rather than glossed over.

- **`W-13` to `W-19`** audit layer three. No run has entered layer three far
  enough to reach a model, because the model settings are empty. Those seven
  checks have never fired against real data, and no gap was fabricated to
  exercise them. Layer three's own path up to the model call **has** now been
  driven for real, against a real unreachable endpoint: it classified the
  failure, refused where the failure named no capability, wrote no gap number it
  would then abandon, and discarded every candidate with the real reason.

- **A model has never been called.** Layer three's request shape, its candidate
  extraction, and its winner selection are written and parse, but no real reply
  has ever passed through them. That waits on an endpoint.
- **The restart ceiling** in `chain.py` has not fired. Reaching it needs several
  distinct parts each failing to fix the same thing, and the shelf holds one
  relevant part. The loop guard, which fires first in the simpler case, has been
  proven.
- **`chain.py`'s own regression guard** has not fired. It needs a passing run,
  then a repair, then a break — which needs a real shelf part that genuinely
  repairs something. `watch.py`'s regression check, `W-21`, has been proven
  against real runs.

All three unblock the same way: a real part on the shelf, or a key in layer
three's config block.
