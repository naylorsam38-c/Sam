# Idea to verified app — where this is and how it finishes

**Date:** 23 August 2026 · **Scope:** the whole Nova project, consolidated and
audited against a running interpreter.

---

## 1. The answer first

Three things, in order of how much they should change what you do next.

**The front of the pipeline is real, the middle does not exist, and the back is
one-tenth built.** Everything shipped so far turns a conversation into an
approved, decomposed spec. Nothing turns a packet into a running application,
and nothing proves a running application matches the spec it came from. That is
not a criticism of the work; it is the honest read of the critical path, and it
means the remaining effort is concentrated in two components neither of which
has been started.

**The two shipped packages did not actually work together.** Each passes its own
tests — 22 and 9 — because each is tested against a stub of the other.
Run against the real gate and the real template, the writer fails on the normal
case: any spec containing an open question. Two defects, both now fixed and
covered by regression tests (§3). Worth stating plainly because it is the
failure mode the reports themselves predict: components that pass their own
checks and break at the seam.

**Do not build an app generator.** This is the strategic recommendation and it
cuts against the obvious reading of "idea to app, fully automated." Coding
agents already generate applications, competently, and that capability is
commoditising monthly. What they cannot do is prove the thing they generated
works — false-success rates of 13-79%, and the specific failure you hit was
panels that render with dead controls. Your spec format already forces every
control to declare its endpoint. That makes the spec a verification manifest,
which is the piece the market does not have. **The differentiated automation is
spec → (let an existing coding agent build) → mechanically prove it against the
spec.** You write the compiler from spec to proof, not the compiler from spec to
code. This is what your own reports 04, 07 and 08 argue when read together, and
it shortens the critical path by removing the hardest component from it.

---

## 2. Where this is, component by component

Audited by running it, not by reading it. ✅ built and tested · ⚠️ built, gap
named · ❌ not started.

| # | Stage | Artifact | State |
|---|---|---|---|
| 0 | Structured interview → answers | `requirements-engine`: 122-question graph, 47 defaults, 15 derivations, 222 spec fields | ✅ graph validates; validator self-test catches all 8 breaks |
| 0b | Pre-filled answer sets per app category | five templates (Asana, Pipedrive, Acuity, Odoo core, Xero) | ✅ all five fit the graph; checker self-test catches all 6 breaks |
| 1 | Conversation → transcript | — | ⚠️ manual, and appropriately so |
| 2 | Transcript → spec draft | `spec-writer`, 3 model calls, 732 lines | ⚠️ works; never run against a real model endpoint |
| 3 | Gap detection from the question bank | `questions/universal.yaml` (28), `parts.yaml` (50) | ❌ **78 questions authored, none loaded by any code** — and see §2b |
| 4 | Answer loop (`[ASK]` → revision n+1) | `write(prior_spec, answers)` exists | ⚠️ accepted programmatically, not exposed by the CLI; no loop |
| 5 | The gate, R1-R12 | `specgate.py`, 272 lines, 22 tests | ✅ |
| 6 | Human approval | — | ✅ deliberately has no code |
| 7 | Spec → work packets, D1-D8 | `decompose.py`, 158 lines | ✅ validates the authored split, computes parallel waves |
| 8 | **Packet → running code** | — | ❌ **nothing** |
| 9 | **Deploy** | — | ❌ **nothing** |
| 10 | Crawl a running app | `crawler.py`, 186 lines | ⚠️ works; smoke test only, 0 tests |
| 11 | **Spec → manifest → click-proof** | — | ❌ **nothing** |
| 12 | API conformance from `verify` commands | — | ❌ nothing (the commands exist in the spec) |
| 13 | Evidence bundle | — | ❌ nothing |
| 14 | Conviction record | schema designed, report 03 §7.4 | ❌ design only |
| 15 | The Rail (bounds, dispatch, snapshots) | designed, report 03 §3 | ❌ design only |
| 16 | Parts library | 9 parts named, criteria format proposed | ❌ design only |

Stages 1-7 reach approval and decomposition. Stages 8-16 are the product.

### 2b. Two front ends now exist, and only one of them is wired

This is the decision the requirements engine forces, and it changes Phase 1.

There are now two ways into a spec, built to different designs:

- **`spec-writer` + `specgate`** — a free-form transcript, three model calls, a
  78-question bank that no code loads, producing `spec.template.yaml` and
  gated by R1–R12.
- **`requirements-engine`** — a 122-question graph with gates, done-rules,
  locked defaults, derivations, and 222 spec fields each with exactly one
  validator-enforced source, plus five pre-filled templates that reduce a new
  app to ~17 customer questions.

The second is substantially further along and mechanically stronger: it is
generated from one source of truth, both its validators bite, and its outputs
regenerate byte-for-byte. The first has the model-facing pipeline and the
approval/decompose path the second lacks.

They are not competitors so much as two halves that have never met: the
engine knows *what to ask and what a complete answer set looks like*;
`specgate`/`decompose` know *how to refuse a bad spec and split an approved one
into work packets*. Nothing currently converts an engine answer set into a
`spec.template.yaml`.

**Recommended: make the engine the front end and keep the gate as the gate.**
Then Phase 1's "wire the question banks" becomes the wrong task — the 78-question
bank is superseded by the 122-question graph, and the work is instead a
compiler from engine answers → spec YAML. Whether the `[ASK]` loop survives at
all depends on that call, because the graph's done-rules already do the job
`[ASK]` markers were invented for. This is open decision 4 in §8.

### What running it proved

- 48 tests pass from the repo root (22 gate + 9 writer + 9 integration + 8 engine).
- The requirements engine's claims hold: the graph validates, both self-tests
  catch every break they advertise (8 and 6), all five templates fit the graph,
  and every generated artifact regenerates byte-for-byte from its source script.
  Its README was wrong on one checkable number — it claimed 60 fixed / 62
  per-instance questions where the graph has 61 / 61. Fixed, with a test.
- `specgate.py` accepts the worked example clean: 3 machine criteria, 1 human.
- The crawler works. Pointed at a test site it found 2 pages and 4 buttons,
  correctly skipped `Delete account` as destructive, and captured a thrown
  page error. **It also reported a deliberately broken button and a
  handler-less `Save` button as `clicked`** — which is the limitation its own
  README warns about, reproduced on demand. A click succeeding in the browser
  is not evidence the product action happened. That single observation is the
  whole argument for stage 11.

---

## 3. What was fixed while consolidating

Both are seam defects: real, small, and invisible to either package's own suite.

**The `[ASK]` marker format did not match.** `specgate.py` matches `[ASK` with
optional question text. Every prompt, both question banks and the spec template
write markers as `[ASK: <question>]`. The writer matched only a bare `[ASK]`
prefix. Consequences: `extract_asks()` returned nothing for real markers, so the
writer's A5 check ("every gap has an ASK at the named path") failed for every
spec with an open question — the normal case — and never reached the gate:

```
FAILED: Writer acceptance validation failed:
- A5 missing ASK for gap: bounds.environment
```

And `banned_outside_asks()` flagged banned words *inside* questions, so the gap
scan could not quote the vocabulary it exists to ask about. Fixed by giving both
sides one shared matcher.

**The rules file handed to the writer described different rules.**
`spec_writer_rules.example.txt` listed an R1-R12 ("Goal is explicit", "Scope is
explicit"…) unrelated to the R1-R12 `specgate.py` implements. The writer was
being briefed against rules that do not exist. Replaced with
`packages/specgate/specgate_rules.txt`, generated from the implementation, with
a test asserting every rule id and every banned word appears in it.

Also: a test resolved its rules path relative to the working directory, so it
only passed when run from inside the package; and a root `conftest.py` plus
`pytest.ini` now make one `pytest` from the root run all three suites.

**The lesson worth keeping.** The reports say specification failures are ~44% of
multi-agent failures and that a component's own tests do not catch integration
drift. This repository demonstrated both within an hour of being assembled. Any
new component gets a cross-package test before it is called done.

---

## 4. The recommended build order

Sequenced by de-risking, not by pipeline order. The reason verification comes
before the build bridge: the harness pays off immediately against apps built any
way at all, including by hand or by Claude Code ad hoc; it is the piece with no
competitor; and automating the build *without* it just industrialises the
false-success rate.

### Phase 1 — Close the spec loop · ~1 week

The cheapest missing piece and it unblocks everything downstream.

1. **Wire the question banks.** 78 authored questions currently load nowhere.
   The gap-scan prompt names the files; nothing reads them. Load
   `universal.yaml` always, `parts.yaml` riders per selected part, and inject
   them as data with their ids, so every `[ASK]` carries its bank id.
2. **`specctl`, one CLI over the whole front end.** `new` (transcript → draft),
   `ask` (print the open questions for a human), `answer` (answers → revision
   n+1, never overwriting), `gate`, `approve`, `decompose`.
3. **Fix the exit-code contract.** The writer raises on gate exit 2, but 2 is a
   legitimate outcome meaning "back to draft with this JSON failure list" — the
   loop the DRAFT prompt is written to consume. Make it a return value.
4. **Run it against a real model once.** Stage 2 has never touched a live
   endpoint. Everything about the three-call design is currently unvalidated.

*Done when:* one conversation transcript becomes an approved, decomposed spec
with no hand-editing of YAML.

### Phase 2 — The conformance harness · ~2-3 weeks

Report 07's own estimate, for one engineer who knows Playwright. This is the
moat piece: nothing on the market diffs declared controls against live ones.

1. **Spec → manifest.** Mechanical. R5 already guarantees every control names an
   endpoint or is `display_only`, so the manifest is a projection of the
   approved spec. No second authoring step, so no drift by construction.
2. **Census.** Playwright `toMatchAriaSnapshot` against the live page, diffed
   against declared controls. Fail in both directions: a declared control
   missing, or an undeclared control present.
3. **Click-proof.** Per control: real click via `getByRole`, block until the
   declared endpoint responds 2xx, service workers blocked, HAR and trace on.
4. **Server-side confirmation.** Inject `X-Request-Id` per control and look it
   up in the backend log. A 2xx proves something answered; this proves the
   declared handler ran. This is the step that closes the dead-button class.
5. **API suite.** Run the spec's `verify` commands as-is; add Schemathesis over
   the OpenAPI description where one exists.
6. **Evidence bundle.** Trace archive, scrubbed HAR, manifest version, request-ID
   lookups, commit SHA, URL, timestamp. Write-once storage. Not JUnit XML —
   that records that assertions passed, not what was observed.

Upgrade `crawler.py` from discovery to proof rather than replacing it; its
crawl-and-enumerate half is the census input.

*Done when:* the harness fails on an app whose Save button posts nowhere, and
says which control and which endpoint.

### Phase 3 — The build bridge · ~2 weeks

Only now, and deliberately thin.

1. **Rail-lite.** Read `plan.json` waves; per packet render the canonical brief
   (report 03 §6: policy and schema first for cache stability, inputs last,
   objective restated after them); dispatch to a coding agent in a fresh
   sandbox; collect the Return schema (§7.2). Every loop bounded in code.
2. **Tests are read-only to the builder.** Non-negotiable; 30-76% reward hacking
   when the checker is editable.
3. **The verifier is a separate identity** — its own credentials, no write
   access to the system under test, and the builder cannot modify the harness or
   the manifest between approval and verification.
4. **Wire in Phase 2.** A packet is done when the harness says so, not when the
   builder says so.

*Done when:* `specctl build` takes an approved spec to a deployed app with a
green conformance run, or stops with the named failing criterion.

### Phase 4 — Parts library · ongoing, start after the first vertical slice

Start with Auth, Records, Forms — the three that appear in essentially every
source. Each ships `criteria.yaml` in the report 08 format: six mechanical
fields plus `active_when` (the criterion for a disabled feature does not exist,
so pass-counts stay honest) and instance-namespaced ids. This converts per-app
criteria authoring into per-app configuration, which is what makes the pipeline
repeatable rather than bespoke.

### Phase 5 — Record and schedule

Emit the Conviction record per verified deliverable; put the same suite on a
daily cron. A pass proves a point in time; the schedule is what makes "still
working" a standing fact.

---

## 5. The milestone that actually matters

Not a phase — a vertical slice, run as early as Phase 2 allows. **Take one real
idea end to end and hold the whole pipeline to it.** The Linked Services spec in
`packages/specgate/examples/good.spec.yaml` already passes the gate clean, so it
is the natural candidate.

Conversation → spec → approval → packets → built → deployed → conformance run →
evidence bundle. One app, narrow, boring, finished. Every phase above is
justified only by what that slice exposes. Build the slice thin and early; the
generality comes from the second and third app, not from designing for them now.

---

## 6. Effort and shape

Roughly **six to nine weeks of one focused engineer** to an automated pipeline
for a narrow class of applications — CRUD-plus-auth web apps with declared
endpoints. Phase 1 is a week, Phase 2 is the bulk and the value, Phase 3 is
thin because it delegates the hard part to an existing coding agent.

The pipeline will be genuinely automated at the ends and human at exactly one
point: approval, which has no code by design.

---

## 7. What this will not do, stated now

Taken from report 07 §4, because it is better believed early than discovered
late.

- **Business-logic correctness is out of reach.** The harness proves the
  declared handler ran and returned the declared shape. A handler that runs and
  computes the wrong answer passes, unless a criterion pins the answer.
- **Controls invisible to the accessibility tree** — a clickable `div` with no
  role — are not enumerable. Treat census mismatches as defects rather than
  pretending this is solved.
- **Destructive controls cannot be safely click-proven on production** without a
  test tenant and a cleanup contract. They get a tenant or they stay human-gated.
- **Universal absence claims** ("never leaks") cannot be verified, only falsified.
- **Judgement qualities need a human.** The `human: true` label exists so these
  are counted separately and never contribute to an automatic pass.
- **The gate checks form, not substance.** A well-formed vague spec passes R1-R12
  cleanly. The mitigation is the bounce-reason metric: a high rate of "criterion
  not observable" means the spec writer is the problem, not the builder.
- **WebSocket payloads and `sendBeacon` traffic** do not appear in HAR evidence.

---

## 8. The open decisions

These need answers from you; each changes the work.

1. **Which coding agent is the builder** in Phase 3, and does it run in your
   infrastructure or a vendor's? Changes the sandbox and credential model.
2. **Is the first target class narrow enough?** "CRUD-plus-auth web apps" is the
   assumption behind the six-to-nine-week estimate. A wider target invalidates it.
3. **Where does the backend log live** for the request-ID lookup in Phase 2.4?
   That adapter is the one genuinely bespoke piece of the harness.
4. **Which front end wins — the 122-question graph or the transcript-plus-gap-scan
   pipeline?** See §2b. My recommendation is the graph, with `specgate` kept as
   the gate and a new compiler between them; that retires the 78-question bank
   and probably the `[ASK]` loop with it. Answering this changes Phase 1
   entirely, so it is the first thing to settle.
5. **Is the product the pipeline or the verification record?** Report 04 argues
   the record is the fundable thing and the pipeline is its best demo. The
   phases above serve both, but the ordering assumes the record matters; if you
   want the pipeline as the product, Phase 3 moves ahead of Phase 2 and you
   accept the false-success rate in exchange for a faster demo.
