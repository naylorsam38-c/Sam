# Nova v2 — A Multi-Model Orchestration Pattern for Conviction and Efficiency

**For:** Sam · **Status:** design, evidence-backed, red-teamed, not yet implemented · **Date:** 22 August 2026
**Built on:** the two prior reports (orchestration patterns; brief structure) plus four further research passes (drift, conviction, model-tier routing, deep-research architectures), then an adversarial design review and a citation audit. Every design decision in §10 carries a source and an honest evidence grade. No code.

---

## 1. What this optimises for, and the one-paragraph answer

You asked for the best multi-LLM system for *conviction* (you can trust what comes back) and *efficiency* (you pay only for what moves the answer), from a brief write-up to a deep dive, with minimal drift. The evidence points to a shape narrower than "multi-agent" usually means:

**One frontier controller (Nova) that owns every non-mechanical decision; a deterministic runtime (the Rail) that owns every handoff, every bound, and every mechanical check and can override Nova on bounds; stateless workers one tier below the controller that only read and return; a verifier from a different model family that grades against the original brief; one writer; and a claim-level grounding pass plus a final deliverable gate before anything reaches you.** Depth is bought by widening the read phase under a bounded gap loop, never by lengthening chains or parallelising writing. Conviction is earned rung by rung — snapshot-checked evidence first, entailment second, cross-family judgement third — and carried as a typed label whose name says which check earned it. Efficiency comes from static role-to-tier assignment, low reasoning effort by default, a two-stage escalation maximum, and stop rules keyed to evidence novelty.

What it deliberately is not: agents talking to each other, debate, blended mixture-of-agents synthesis, learned per-query routing, persona prompts, or any loop whose termination lives inside a model (§11).

Two things the red-team made me say plainly. First, this design is more expensive per task than a single agent — roughly 2–3× a single-agent run at T2 and around 3× at T3 (§9) — and buys *reliability*, not cheapness; "efficiency" here means no token is spent without a check that can fail. Second, several load-bearing mechanisms (recitation, progress ledgers, reference-not-summary, deterministic rails) are universally shipped and never ablated; they rest on grade-C evidence and §14 says so.

---

## 2. The six invariants

Everything else is derived from these.

1. **Nova owns every non-mechanical decision; the Rail owns every bound and every mechanical check, and overrides Nova on bounds.** Centralised coordination contained error amplification to 4.4× versus 17.2× for independent agents in the one multi-topology study ([Google/MIT](https://arxiv.org/abs/2512.08296), single preprint); adding a final-authority step and a verification step to ChatDev raised success +9.4% and +15.6% ([MAST](https://arxiv.org/html/2503.13657v3)). Workers have no write access to shared state, the verifier's inputs, tests, or other workers.

2. **Every handoff is a self-contained, fixed-key, structured brief; no transcript crosses a boundary.** A fully specified single turn recovers ~95% of what incremental delivery loses ([Laban et al.](https://arxiv.org/abs/2505.06120) — multi-turn chat, same model; applied here by inference); fixed-key formats lost 4.7 points over six relay hops where prose lost up to 21.8, for weak relay models ([relay study, 2026](https://arxiv.org/html/2607.09678)).

3. **No worker reads another worker's output or the Writer's. All worker output passes through the Rail, the Verifier, and Nova's ledger before the Writer sees it.** The ledger *is* a relay hop, and the design treats it as one: the Writer reads artifacts by reference for any finding that is not `checked`, never Nova's paraphrase alone (§5, §6). Injected errors persist 83–100% through relays and are never repaired ([relay study](https://arxiv.org/html/2607.09678)).

4. **"Done" is decided by something the worker does not control.** Self-reported completion is false in 13–79% of failures by model ([Confident Closing, 2026](https://arxiv.org/html/2606.09863)); same-family judges favour their own outputs ([Panickssery](https://arxiv.org/pdf/2404.13076)); intrinsic self-correction is flat or negative ([Huang et al.](https://arxiv.org/abs/2310.01798)). Snapshot checks run first, a cross-family Verifier second, Nova last and only for what the first two cannot reach. Stop rules are Rail-owned.

5. **Conviction is a typed label named after the check that earned it, never a scalar and never "verified" by agreement alone.** Verbalised confidence clusters at 80–100% with ECE 0.18–0.52 ([Xiong et al.](https://proceedings.iclr.cc/paper_files/paper/2024/file/6733cf15e10e2cd1d59af033c3bb8507-Paper-Conference.pdf)); frontier-model sample agreement correlates only ρ 0.20–0.59 with correctness and 48% of GPQA answers at agreement ≥0.8 were wrong ([2607.08065](https://arxiv.org/html/2607.08065v1)); scores become semantically incompatible across pipeline boundaries ([2604.23505](https://arxiv.org/html/2604.23505v1)).

6. **Width over depth; reading over writing; selection over synthesis.** Parallel section-writing produced disjoint reports ([LangChain ODR](https://www.langchain.com/blog/open-deep-research)); diverse candidates help when a judge *selects* (0.81 win rate) and hurt when *blended* (0.18) ([selection bottleneck, 2026](https://arxiv.org/html/2603.20324v1)).

---

## 3. Topology and roles

```
You ⇄ Nova (controller, frontier; holds conversation; works from the Task Ledger)
          │  writes Ledger + Briefs
          ▼
       The Rail (code: pre-send gate, dispatch, snapshots, bounds, stalls, escalation, audit log)
          │
   ┌──────┼──────────┐
   ▼      ▼          ▼
 Extract  Research   Code/Compute   ← stateless, read-only, one tier below Nova
   │      │          │
   └──────┴──────────┘  Returns + snapshotted artifacts
          ▼
   Rung 1: Rail re-checks every evidence pointer against the SNAPSHOT (never live)
          ▼
   Verifier (≥ worker tier, family ≠ worker, high effort; sees brief + criteria pointers + snapshots; no worker prose)
          ▼
   Nova: compress into findings ledger · gap analysis · decisions (audit-logged)
          ▼
   Writer (controller tier, fresh context; reads ledger + artifacts by reference)
          ▼
   Grounding pass (snapshot span-exists → entailment → independence heuristic → labels)
          ▼
   Deliverable gate (Verifier panel grades the REPORT against acceptance_criteria; one bounded rewrite)
          ▼
   You (with labels, conflicts, unmet criteria, and spend)
```

| Role | Tier (default) | Effort | May read | May write | Notes |
|---|---|---|---|---|---|
| Nova | Frontier (Opus-class) | Medium | Ledger; Verifier verdicts; labelled findings; artifacts by ref | Ledger, Briefs, decisions | Never reads raw worker prose before Rail + Verifier have labelled it. Its transcript is compacted by the Rail's policy (§7.5), and it works from the Ledger, not memory. |
| The Rail | Code | — | Everything | Dispatch, snapshots, bounds, labels (mechanical ones), audit log | Every loop — including the Nova↔gate bounce loop — has a Rail-side bound. 68 confirmed infinite-loop defects across 47 real agent projects lived in framework feedback paths, not top-level counters ([Hou et al.](https://arxiv.org/html/2607.01641v1)). |
| Extraction worker | Small (Haiku / Flash-Lite / mini class) | Low | Its brief | Return | Schema + 2 examples in brief. Run 2×, compare at field level (§8 Rung 2). Escalate to mid tier by Rail rule: input > ~30 pages or schema > ~100 fields — Gemini 3.5 Flash fell from 87.9% on short docs to 27.9% on long ([ExtractBench](https://arxiv.org/html/2607.29677)). |
| Research worker | Mid (Sonnet / Flash class) | Low | Its brief; web/corpus via Rail-proxied fetch | Return; artifacts to snapshot store | Higher effort was flat or negative on research tasks for 3 of 4 frontier models at 1.5–3× cost ([FutureSearch](https://futuresearch.ai/effort-paradox/)). |
| Code/compute worker | Mid (Sonnet / Haiku 4.5 class) | Low–medium | Brief; sandbox | Return; artifacts | Haiku 4.5: 73.3% SWE-bench Verified, "similar… at one-third the cost" of Sonnet 4 (vendor, [Anthropic](https://www.anthropic.com/news/claude-haiku-4-5)). Tests are read-only to the worker ([ImpossibleBench](https://arxiv.org/abs/2510.20270)). |
| Verifier | ≥ worker tier by *task*, **family ≠ worker** | High | Original brief; `criteria[]` ids + evidence pointers; snapshots | Per-criterion verdicts | For correctness: a single judge at ≥ worker tier — judge accuracy tracks solver accuracy ([JudgeBench](https://arxiv.org/abs/2410.12784): GPT-4o 56.6%, o1-preview 75.4%). For rubric/format criteria only: a three-judge cross-family small panel (κ 0.763 vs 0.627 for single GPT-4 on NQ, 7–8× cheaper — [PoLL](https://arxiv.org/abs/2404.18796)). The brief tags each criterion `correctness` or `rubric`. |
| Writer | Controller tier, fresh context | Medium | Ledger; artifacts by ref (mandatory for non-`checked` findings) | Draft | Single pass. |
| Grounding | Code + small entailment model | Low | Draft; snapshots | Claim labels | Entailment error rate is measured on a labelled set and stamped on every `entailed` label (§7.4). |
| Deliverable gate | Verifier (correctness) or panel (rubric) | High | Report; `acceptance_criteria[]`; Ledger objective | Verdict; one rewrite request | The report is the only artifact you see; it is verified like any Return. |

**Families and substitution.** "Family" = vendor (Anthropic, OpenAI, Google are three). A Claude worker therefore requires a non-Anthropic Verifier. Rung 5 escalation must differ from the *worker's* family and be graded by a Verifier that differs from the *escalation model's* family; with three vendors this pins the assignment (e.g. worker A, Verifier B, escalation C graded by B or A-frontier — never C-by-C). If the required family is unavailable, the Rail pauses the rung and queues; it never silently falls back to same-family.

---

## 4. Depth tiers

Every task enters at the lowest tier that can answer it. Nova picks the entry tier — that is a model making a routing decision, and §14 notes it is unevaluated; mitigation is that the triggers below are Rail-checked and escalation is cheap relative to a wrong deep dive. Two well-known products' *lighter* tiers beat their own deep-research tiers on analyst tasks ([FutureSearch](https://arxiv.org/abs/2506.06287)), so the default is down, not up.

**T0 — Direct.** Nova answers from context. *Up-trigger:* the answer depends on a fact Nova would have to guess, or you ask for sources.

**T1 — Lookup.** One research worker, ≤10 tool calls, ≤3 minutes. Grounding on every factual claim. *Up-trigger:* `partial`/`blocked`, any load-bearing claim `unsupported`, or a comparison in the question.

**T2 — Brief write-up.** Scope (Nova, ≤2 clarifying questions, before any dispatch) → 2–4 disjoint research briefs in parallel, 10–15 calls each → Rung 1 → Verifier → compress → one Writer → grounding → deliverable gate. *Up-trigger:* >2 lines of inquiry `partial`, or a `conflicted` finding on a load-bearing criterion, or your request.

**T3 — Deep dive.**
1. *Scope.* Nova restates the question, writes `acceptance_criteria[]`, asks you ≤2 clarifying questions *now* (this is the cheap moment; later escalations are expensive).
2. *Pre-read.* Two mid-tier workers, 5 calls each, map the territory. Cost is ~5% of T3; it prevents locking a plan built on Nova's priors.
3. *Perspectives and outline, locked.* Nova writes the perspectives and outline from the pre-read. Outline-first raised organisation +25 points and breadth +10 on Wikipedia-style articles ([STORM](https://arxiv.org/abs/2402.14207)) — applied here by inference to reports generally.
4. *Read round.* 5–10 research workers, one per perspective × sub-question, ≤15 calls each.
5. *Compress.* After *every* round, Nova writes the findings ledger from Verifier-labelled Returns (one entry per finding: text, `refs[]`, label, perspectives served, `conflicts_with[]`). Forgetting earlier findings was the strongest failure correlate in Deep Research Bench traces (coefficient −0.843, [FutureSearch](https://arxiv.org/abs/2506.06287)).
6. *Gap analysis and bounded replan.* Nova compares ledger to criteria; may revise the outline once here; spawns round 2 (and at most round 3) only for named gaps. A replan consumes a round. The Rail ends the loop when a round adds no novel evidence-bearing source *and* query diversity is exhausted (stall rules in §5). On short-answer search tasks 77–94% of episodes add nothing and a 20-episode cap retained 86–92% of accuracy ([2608.01913](https://arxiv.org/html/2608.01913v1)); the long-form analogue is unmeasured (§14).
7. *Single write.* Writer from outline + ledger; opens artifacts by reference for every non-`checked` finding.
8. *Grounding and conflict pass.* Span-exists against snapshot → entailment → independence → labels. Conflicts are surfaced, never silently resolved. Unverifiable claims are labelled, never dropped, never promoted.
9. *Deliverable gate.* Report graded against `acceptance_criteria[]` and objective; one bounded rewrite; then to you with labels, conflicts, unmet criteria, and spend.

**Budgets** — see §9 for the worked model. Starting caps, in *cache-adjusted billed input-equivalent tokens*: T1 ≤ 150k; T2 ≤ 1M; T3 ≤ 5M — set above the typical-with-one-escalation figures in §9 so a single Rung 5 does not breach the cap. Wall-clock targets: T1 ≤ 3 min; T2 ≤ 12 min; T3 ≤ 45 min. On budget stop the Rail forces partial Returns from running workers, Nova compresses what exists, the Writer runs on the partial ledger with every finding from an unverified round labelled `unsupported`, and the deliverable states which criteria are unmet.

---

## 5. Drift controls

Ranked by measured effect; grade in brackets.

**Goal drift → the objective travels verbatim and is criterion zero.** A goal-restating scaffold kept Claude 3.5 Sonnet near-perfect past 100k tokens where every unscaffolded model drifted ([Arike et al., eval repo](https://github.com/RaunoArike/goal-drift-evals) — unreviewed, one model family; C). Field 2 of every brief is the Ledger `objective`, which Nova writes *in third person* at scope time and you confirm; it is then immutable and string-matched by the gate (so your phrasing never reaches workers and the match is exact).

**Plan drift → pre-read, then lock, then one bounded replan.** Plan-then-execute cut tokens 64% and gained +4.4 points over step-wise reacting across six benchmarks ([ReWOO](https://billxbf.github.io/works/ReWOO_preprint.pdf), 2023 models; D as applied to research outlines). Coding agents that reach the right code then overwrite it account for 32–40% of edit-quality failures (~23% of all failures); five intermediate patches bit-identical to the correct one were discarded and all five were recoverable with an edit-commit checkpoint ([TRAJEVAL, 2026](https://arxiv.org/abs/2603.24631)). Every worker artifact is a committed snapshot; nothing is overwritten in place.

**Scope drift → the Verifier grades against the brief; the deliverable gate grades the report against the criteria.** +15.6% from a verification step checking output against the high-level spec ([MAST](https://arxiv.org/html/2503.13657v3); B).

**Semantic drift across hops → one structured hop per direction; artifacts by reference; the ledger treated as a lossy hop.** Compaction loses artifact facts (paths, what changed) worst of all dimensions — 2.19–2.45 out of 5 across three production compactors ([Factory](https://factory.ai/news/evaluating-compression); B). Hence the Writer must open artifacts for anything not `checked`, and ledger entries carry `refs[]` that the grounding pass checks against, not Nova's text.

**Instruction drift in Nova's own long conversation → Nova works from the Ledger, and the Rail compacts Nova's transcript.** System-prompt adherence drifts significantly within eight rounds ([Li et al.](https://arxiv.org/abs/2402.10962)); instruction-following fell 0.877 → 0.707 by turn 3 ([Multi-IF](https://arxiv.org/abs/2410.15553)). The Ledger, not the transcript, is re-injected at each decision; §7.5 gives the compaction policy.

**Sycophantic drift → no worker sees your words; the Verifier sees pointers, not prose.** Judges flip 84.5% under a bare rebuttal ([Kim et al.](https://arxiv.org/html/2509.16533v1)); third-person framing cut sycophantic flips by up to 63.8% in a debate setting ([SYCON-Bench](https://arxiv.org/abs/2505.23840)). The Verifier's inputs are exactly: the brief, `criteria[].{id, evidence_pointer}`, and the snapshots those pointers resolve to. It does not receive `summary`, `claims[]` text, `assumptions_made`, `failure.message`, or `blocked_on` — those go to Nova *after* the verdict.

**Stall → Rail-owned, on repetition and novelty, defined precisely.** A worker is stopped (with a forced partial Return, not a kill) when any of: same action+observation 4×, same action+error 3×, alternating ping-pong 6× ([OpenHands thresholds](https://docs.openhands.dev/sdk/guides/agent-stuck-detector)); or two consecutive rounds with zero *novel sources*, where a novel source is a normalised URL whose content hash is not already in the snapshot store. A T3 gap loop ends when a round adds zero novel sources across all workers *and* Nova's next-round query set overlaps ≥80% (normalised) with prior queries — both conditions, so sparse topics with bad queries get one more chance with new queries rather than a confident thin report. Redundant re-querying is "the cleanest behavioral predictor of failure" in research traces ([2608.01913](https://arxiv.org/html/2608.01913v1)). The worker-side `stop_hint` in the brief is advisory only.

---

## 6. The canonical brief

Final form. Delimited sections; XML tags for Claude-family workers, Markdown headings for OpenAI-family; structure matters, syntax does not for frontier models ([He et al.](https://arxiv.org/abs/2411.10541); [2602.05447](https://arxiv.org/abs/2602.05447)). Under 2k tokens excluding inputs; ≤5 hard constraints.

**Section order is chosen for cache stability first, then for the long-input rule:** the sections that are identical across many briefs (identity schema, policy, output schema) sit first so the prefix caches; large variable inputs sit last, immediately followed by a one-line restatement of the objective and criteria ids (the "instruction adjacent to data" rule — local instruction repetition lifted GPT-4o from 31.5% to 54.3% at 16k tokens, [LongIns](https://arxiv.org/html/2406.17588v3)). Cached input is ~0.1× list price ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)).

```
<brief>
<missing_information_policy>            ← constant text, cached
  If an input needed for any criterion is absent or ambiguous: return status=blocked with the
  precise question and candidate answers. If a reasonable assumption exists and the criterion is
  not marked load_bearing: proceed and record it in assumptions_made. Never fill a gap silently.
  If the task is infeasible as specified, or inputs contradict the criteria: return status=rejected
  with both sides. Reporting a criterion unmet is acceptable; claiming it met without the named
  evidence is not.
</missing_information_policy>

<output_schema>                         ← constant per role, cached (§7.2)
</output_schema>

<identity>
  task_id · parent_id · attempt N of MAX · tier · role
  if attempt > 1: previous_failure_class · criteria the Verifier marked unmet, verbatim
</identity>

<objective>
  [Ledger objective, verbatim, third person. "The task is to return …"]
</objective>

<scope>
  in: […]   out: […; named sibling tasks not to duplicate]
</scope>

<constraints>
  [≤5, positive, content → format, precedence notes for any pair that could conflict]
</constraints>

<budget>
  max_tool_calls · max_turns · max_wall_time
  stop_hint (advisory): a round with no source you have not already cited is a signal to finish
</budget>

<definition_of_done>
  C0 (always): the output serves the objective above.
  C1 [correctness|rubric] [load_bearing?]: [the observation that proves it]
  C2 …
</definition_of_done>

<sources>  (research/extraction only)
  allowed tiers · do-not-cite: user-generated content unless corroborated by a non-UGC source
  rule: every factual claim carries ref_id + quoted span; fetch only through the Rail proxy
</sources>

<sandbox>  (code only)
  writable paths · test command (run-only; tests are read-only) · abort: if tests and spec conflict, return rejected with both
</sandbox>

<inputs>                                ← large, variable, last
  [verbatim records/documents; everything else as ref_id · title · one-line extract]
</inputs>

<restate>
  Objective: [one line]. Criteria: C0–Cn. Output per <output_schema>. Reasoning, if any, in <working> before the block.
</restate>
</brief>
```

**Wording rules** (prior report): positive constraints, no emphasis markers, no persona line, no motivational framing, two format-faithful examples for extraction workers in `<output_schema>`.

---

## 7. Ledger, Return, verdict, labels, and Nova's memory

### 7.1 Task Ledger (Nova-owned, Rail-enforced, versioned)

`objective` (immutable after scope) · `acceptance_criteria[]` (id, text, type `correctness|rubric`, `load_bearing`, observation) · `tier` · `budget` / `spent` (billed-equivalent tokens, wall time, per-rung attribution) · `plan` + `plan_version` · `findings[]` · `open_gaps[]` · `assumptions[]` (with Nova's accept/reject) · `conflicts[]` · `decisions[]` (timestamp, reason, model id, prompt version, brief version) · `escalation` · `follow_ups[]` (a later question inherits this Ledger at T1 and escalates normally).

### 7.2 Return (worker → Rail)

1. `criteria[]` — `{id, met, evidence_pointer}`; the pointer is a snapshot id + locator (file/line, URL/hash/span offsets, command + captured stdout hash). 2. `artifacts[]` — `{id, type, snapshot_hash}`. 3. `status` — `done | partial | blocked | rejected | failed`. 4. `blocked_on`. 5. `assumptions_made[]`. 6. `failure` — `{class, retryable, message, attempted[]}`. 7. `side_effects[]`. 8. `usage` — calls, tokens, wall, `novel_sources_this_round`, verbalised confidence (triage only). 9. `claims[]` — `{text, ref_id, span_locator}`. 10. `summary` ≤150 words.

Items 1 and 2 go to the Verifier (pointers and snapshots only). Items 3–10, including `usage` and its verbalised confidence, go to Nova after the verdict.

### 7.3 Verifier verdict

Per criterion `{id, verdict: met | unmet | unverifiable, checked: [pointers], reason}`; C0 `serves_objective` graded from artifacts, not from any description of them; `conflicts_detected[]`.

### 7.4 Conviction labels — named after the check

| Label | Earned by | Who assigns | Error rate carried |
|---|---|---|---|
| `checked` | A deterministic check passed against a snapshot: test executed in a fresh sandbox with stdout hash match; schema validated; span-exists at locator; artifact hash matches. | Rail | ~0 (the check is exact) |
| `entailed` | `checked` span-exists *and* the entailment model says the span supports the claim. | Rail + small model | The entailment model's measured false-positive/negative rate on your labelled set, stamped on the label (e.g. `entailed@0.08`). |
| `corroborated` | `entailed` by ≥2 sources that pass the independence heuristic (different registrable domain; no shared byline/wire marker; content similarity below threshold). | Rail | Heuristic misses syndication; treated as `entailed`-grade for load-bearing decisions until the heuristic is evaluated. |
| `sample-agreed` | Two small-model extraction samples agreed at field level (normalised). **Not** `checked`. Correlated samples agree on the same wrong answer; this label gates escalation, it does not prove correctness. | Rail | Unknown until measured (§13 Rung 2 precision); until then it carries no evidential weight for load-bearing decisions — a load-bearing extraction field must additionally be `checked` (schema + source span) before the Writer may rely on it. |
| `single-source` | One `entailed` source. | Rail | as `entailed` |
| `unsupported` | Asserted with no span, or span does not entail. Kept, labelled, never promoted. Synthesis claims that rest only on other labelled claims are `derived(from: ids)`, not `unsupported`. | Rail | — |
| `conflicted` | Independent `entailed` sources disagree. Surfaced with both sides. Nova may downgrade one side only on a *mechanical* ground (source is UGC; source is superseded by a later version of the same publisher's document) and must log it; Nova never resolves a conflict by preference. | Rail / Nova (logged) | — |

When Nova merges findings into a ledger entry, the entry takes the *weakest* label among its sources unless every source is independently `entailed`, in which case `corroborated`.

### 7.5 Nova's own context

The Rail compacts Nova's transcript whenever it exceeds a threshold (start: 60% of window), using a fixed procedure: the Ledger is never compacted (it is re-injected whole); the transcript is replaced by `decisions[]` plus the last two turns; artifact facts are never summarised into prose, only referenced. In T3 the ledger is pruned for re-injection to entries touching `open_gaps[]` and load-bearing criteria, with the rest available by reference. This is the single largest drift surface the prior design ignored.

---

## 8. Conviction and efficiency ladder, in cost order

**Rung 0 — Pre-send gate** (code, plus a ~20–90 ms classifier; bounded at 3 Nova↔gate bounces, then escalate to you). Checks: required sections present; `objective` string-matches the Ledger after whitespace normalisation; ≤5 constraints; no known-impossible constraint pairs; every criterion names an observation *of an allowed observation type* (command+expected output, file/field, URL/span, schema) — free-text "observations" bounce; every criterion tagged `correctness|rubric`; token count within tier; every `ref_id` resolves; injection scan on embedded third-party text ([Prompt Guard 2](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M): 88.7–97.5% recall at 1% FPR). Specification failures are ~44% of multi-agent failures ([MAST](https://arxiv.org/html/2503.13657v3)); constraint count alone predicts compliance within ~10% ([2509.21051](https://arxiv.org/abs/2509.21051)). This gate checks *form*; a well-formed vague brief passes, and the bounce-reason metric (§12) is how you find out.

**Post-dispatch injection.** Workers fetch through a Rail proxy that snapshots and scans every fetched document before it enters the worker's context; artifacts are untrusted until scanned. The brief-boundary scan alone protects nothing the worker reads later.

**Rung 1 — Snapshot re-check** (code; not free in time, but no side effects). Every `evidence_pointer` resolves against the content-addressed snapshot captured at worker time — never a live re-fetch. Commands are re-executed only if declared side-effect-free in the brief and then in a fresh sandbox; otherwise the check is "captured stdout hash matches." Failure → `unmet` regardless of the worker's claim. This is the strongest conviction mechanism available: it is what makes sample coverage cashable (SWE-bench Lite 15.9% → 56% at 250 samples *with* a verifier, [Large Language Monkeys](https://arxiv.org/abs/2407.21787v3)). Many research criteria are not mechanically checkable; those are tagged `rubric` at scope time and skip to Rung 4.

**Rung 2 — Agreement gate, small extraction workers only** (2–3× small-model cost). Two samples; field-level comparison after normalisation (dates, units, whitespace, case) with a per-field tolerance declared in the schema. Agree → `sample-agreed`, continue. Disagree on any load-bearing field → third sample; 2-of-3 wins, else escalate the same brief once to the **mid tier** (this is the extraction escalation path; Rung 5 is the Verifier-disagreement path, and they never chain). Five-sample agreement raised failure-prediction AUROC 54.8% → 92.7% on arithmetic ([Xiong](https://proceedings.iclr.cc/paper_files/paper/2024/file/6733cf15e10e2cd1d59af033c3bb8507-Paper-Conference.pdf)) but is weak on knowledge tasks and unreliable for frontier models ([2607.08065](https://arxiv.org/html/2607.08065v1)); that is why it gates escalation and never earns `checked`.

**Rung 3 — Grounding** (one small-model call per claim). Span-exists (snapshot) → entailment → independence → label. Vendor-reported: span-level citation enforcement took one customer's source hallucinations from 10% to 0% ([Anthropic Citations](https://claude.com/blog/introducing-citations-api); C). Search-augmented claim verification agreed with humans 72% and won 76% of disputes at >20× lower cost ([SAFE](https://arxiv.org/abs/2403.18802)) — which also means 28% disagreement, hence the stamped error rate. Scale of the problem: even GPT-5 averaged 43.8 unsupported claims per market-analysis report and Open Deep Research 91.9 ([LiveResearchBench](https://arxiv.org/html/2510.14240v1)).

**Rung 4 — Cross-family Verifier** (one call at high effort; ≈ cost of the worker run). Inputs per §5. Correctness criteria: single judge at ≥ worker tier by task; rubric criteria: three-judge small panel. Expect ~2 effective independent votes however many judges you add (9 judges across 7 families gave n_eff ≈ 2.18, [2605.29800](https://arxiv.org/html/2605.29800v1)); never buy more than three. Verification costing as much as generation is the steady state of this design, not a bug.

**Rung 5 — Disagreement-triggered escalation** (one frontier call + re-grade). Trigger: the Verifier marks a *load-bearing* criterion `unmet` that the worker claimed `met`. Non-load-bearing disagreements go to Nova as `unsupported`. The same brief goes once to a frontier model from a family ≠ worker; the Verifier (family ≠ escalation model) re-grades. A two-model cascade captured up to 79.5% cost reduction at 90% of ceiling quality and fixed chains deeper than two underperformed the pairwise envelope ([2605.06350](https://arxiv.org/html/2605.06350v1)). Never a third stage; after Rung 5 the result is labelled as it stands.

**Rung 6 — Nova's judgement.** Only for criteria marked `unverifiable`. Reference-guided: Nova sketches the expected answer first, then grades (cut GPT-4's math-judging failure rate from 70% to 15% in [MT-Bench](https://arxiv.org/html/2306.05685v4)); Nova never sees the worker's argument.

**Rung 7 — You.** The question, the candidates, a deadline, and a declared default. **Default is `park`** for anything with declared `side_effects[]`, any load-bearing criterion, or any T3 run; "proceed on stated assumption, labelled `unsupported`" is allowed only for non-load-bearing claims. If you answer after a default fired, the Rail re-opens the task at the affected criterion and logs the rollback.

**Efficiency rules across the rungs.** Static role-to-tier assignment: learned routers recover only 7.5–14.4% of oracle gains ([2608.08265](https://arxiv.org/html/2608.08265v1)) and the top fifteen differ by 0.23 points ([Routing Plateau](https://arxiv.org/html/2606.07587)) — evidence that one alternative is bad, not that static is optimal (B). Effort low for workers, high for Verifier and for math-like verifiable steps ([FutureSearch](https://futuresearch.ai/effort-paradox/)); model tier beats token budget: "upgrading to Claude Sonnet 4 is a larger performance gain than doubling the token budget" ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Retriever quality before iteration count: a better retriever was worth ~15 points on BrowseComp-Plus and reduced calls ([2508.06600](https://arxiv.org/abs/2508.06600)). Tool results capped per call (start: 4k tokens, extractive) so worker context stays bounded. Concurrency caps per provider and per search API, with backoff, set in the Rail.

---

## 9. Worked cost model

Assumptions: tool results capped at ~4k tokens; research worker context grows to ~30–40k by call 10–15; cache reads at 0.1×; "tokens" throughout means *billed input-equivalent* (cache-adjusted input + output). Figures are order-of-magnitude and must be replaced by your own logs.

| Tier | Workers | Verifier | Nova (scope, compress, decide) | Writer | Grounding | Typical total | With one Rung 5 |
|---|---|---|---|---|---|---|---|
| T1 | 1 × ~40k | 1 × ~15k | ~10k | — | ~10 claims × 1.5k = 15k | **~80k** | ~130k |
| T2 | 3 × ~120k = 360k | 3 × ~40k = 120k | ~60k (2 compress + decisions) | ~25k | ~60 claims → 90k | **~650k** | ~900k |
| T3 | R1 7 × ~150k + R2/R3 ~6 × 150k ≈ 2M | ~15 × 40k = 600k | pre-read 2 × 30k; compress ×3 ~150k; decisions ~40 × pruned ledger ~15k = 600k | ~60k | ~300 claims → 450k | **~3.9M** | ~4.5M |

Where the ladder multiplies: Rung 2 makes extraction 2–3× by construction (4–6× if tolerances are too strict); Rung 4 is ≈1× the worker again; Rung 5 adds a frontier run of the same brief plus a re-grade — in the table that is +50k at T1, +250k at T2, +600k at T3, i.e. roughly 1.3–4× the escalated worker's own cost depending on tier — and, if the false-success baseline holds, will fire on a meaningful minority of Returns unless the load-bearing filter is used; ledger re-injection in T3 is the quiet quadratic and is why §7.5 prunes. Wall-clock for T3 is three sequential rounds each bounded by the slowest worker plus a high-effort Verifier pass: 30–45 minutes is realistic.

The honest summary: T2 costs roughly 2–3× a single-agent run of the same task and T3 roughly 3×; the premium buys labelled claims, a verified deliverable, and bounded drift. If you want cheaper, drop Rung 4 for rubric criteria and Rung 2 for non-load-bearing fields first; never drop Rung 1 or the deliverable gate.

---

## 10. Evidence map

Grades: **A** replicated benchmark/controlled study; **B** single benchmark or preprint, or instrumented production report; **C** vendor guidance or practitioner consensus; **D** inference from adjacent evidence.

| Decision | Source | Grade |
|---|---|---|
| Single controller; Rail owns bounds | Google/MIT 4.4× vs 17.2× (one preprint); MAST +9.4/+15.6% (one framework) | B |
| Workers read, never coordinate; parallel reads only | Cognition; LangChain ODR disjoint writing; Anthropic research system | C, converging |
| Deterministic Rail carries handoffs; every loop bounded | OpenAI "via your code"; Stripe blueprints; Hou et al. 68 loop defects | B/C |
| Fixed-key briefs and Returns; no transcripts | Laban (multi-turn chat, by inference); relay study (weak-relay condition) | B/D |
| Ledger treated as a lossy hop; Writer opens artifacts | Factory compaction 2.19–2.45/5 on artifacts; relay persistence 83–100% | B |
| Objective verbatim, third person, criterion zero | Arike eval repo (unreviewed); Anthropic contract; SYCON third-person | C/B |
| Pre-read → plan lock → one replan | ReWOO (2023, by inference); TRAJEVAL checkpoint recovery (coding) | D |
| Verifier grades against brief; deliverable gate grades report | MAST +15.6% | B |
| Verifier family ≠ worker; ≥ worker tier by task; panel for rubric only | Panickssery; JudgeBench; PoLL; n_eff 2.18 | A |
| Verifier sees pointers + snapshots, never worker prose | Confident Closing AUROC ≤0.65 on closing language; Kim et al. 84.5% | B |
| Snapshot re-check before any model judgement | Large Language Monkeys (verifier-limited selection); ImpossibleBench (editable checks get gamed) | B/D |
| Agreement gate = escalation trigger only, small workers only | Xiong M=5; 2607.08065 | B (scope-limited) |
| Span grounding + entailment with stamped error rate | SAFE 72%/76%; Anthropic Citations (vendor anecdote); LiveResearchBench | B/C |
| Labels named after checks; no scalar | Xiong ECE; 2607.08065; 2604.23505 (framework paper) | B |
| Selection over synthesis | Selection bottleneck 0.81 vs 0.18 | B |
| No debate | Smit et al.; Zhang et al. | A |
| No blended MoA | Selection bottleneck 0.18. Note: a 2026 compute-matched study ([2605.01566](https://arxiv.org/html/2605.01566)) finds MoA *beats* self-consistency by +2.7 points at equal compute and +7 at 20× — MoA is excluded here because blending loses to selection, not because it fails to beat sampling | B |
| Static tier assignment | LLMRouterBench/Routing Plateau/2608.08265 (routers bad ≠ static optimal) | B |
| Small models for short-doc extraction, mid for long | ExtractBench (Gemini 3.5 Flash) | B |
| Effort low for research, high for verification | FutureSearch effort paradox (research); AIME effort curves from third-party harness, not the cited page | B/C |
| Two-stage cascade maximum | 2605.06350 | B |
| Gap loop bounded by novelty + query-diversity | 2608.01913 (short-answer tasks) | D for long-form |
| Outline before retrieval | STORM (Wikipedia-style) | B for that genre, D generally |
| Findings ledger | FutureSearch forgetting coefficient; Tongyi IterResearch; Anthropic harness | B/C |
| Single writer from labelled evidence | LangChain ODR; LiveResearchBench aggregation | B |
| Unverifiable labelled, never dropped | Claude Code `/deep-research`; Tow Center >60% citation failure baseline | C/B |
| UGC down-weight | WARP 17–23% UGC; 38–51% mention rate from a single poisoned URL | B |
| Stall rules | OpenHands; Magentic-One ≤2; 2608.01913 redundancy predictor | B/C |
| Human escalation: park default, deadline, rollback | Temporal durable timers; ImpossibleBench abort effect | C |
| Pre-send gate | MAST spec failures; 2509.21051; Stacking Collapse conflicts; SWE-bench Verified screening (benchmark tasks, not briefs) | B/C |
| Tier ladder, default down | FutureSearch; Anthropic effort rules; Gemini two-tier | B/C |

---

## 11. Deliberately excluded

Agent-to-agent messaging (MAST chatty frameworks fail 41–87%); multi-agent debate (≈ self-consistency at higher cost — [Smit](https://arxiv.org/pdf/2311.17371), [Zhang](https://arxiv.org/html/2502.08788v3)); blended MoA synthesis (loses to selection; see the honest note in §10); learned per-query routing (plateaued); persona lines, emphasis markers, motivational framing, "don't do X" constraints (null or negative); reflection loops without an external signal (flat or negative); worker write access to tests, shared state, or other workers' artifacts (30–76% reward hacking when the checker is editable); any unbounded loop; any live re-fetch as a verification step.

---

## 12. Production requirements the design now states

- **Permissions and secrets.** Per role: network allow-list (workers only via the Rail proxy), filesystem paths, credentials scoped per task and revoked at Return; the Verifier has no write access anywhere; sandboxes are fresh per attempt and destroyed after snapshot.
- **Observability.** One event log keyed `run_id → task_id → attempt → rung`, with model id, prompt/brief/template version, tokens, wall, cost, and label transitions; full replay from snapshots. §13's metrics are computed from this log.
- **Versioning.** Brief templates, the constant brief sections, role→tier table, entailment model, and thresholds are versioned; every `decisions[]` entry records the versions in force.
- **Partial results.** On budget or stall stop: forced partial Returns; unverified-round findings labelled `unsupported`; deliverable lists unmet criteria and spend.
- **Progress and cancellation.** Per-tier progress events (stage, round, spend vs budget, findings so far); cancellation at any Rail checkpoint returns what exists.
- **Provider outage.** Required-family unavailable → rung paused and queued with a deadline; never same-family fallback; you are told.
- **Evaluation harness.** A labelled set of ~50 tasks per tier with ground truth and human-graded criteria, used to measure false-success rate, entailment error rate, and agreement-gate precision before thresholds are trusted — the design's numbers are literature priors, not yours.

---

## 13. Instrumentation

Per run, from the event log: run-level best/worst spread on repeated tasks (Vending-Bench: every model has derailing runs while means look fine — [Andon Labs](https://arxiv.org/abs/2502.15840)); false-success rate (`done` with any `unmet`; literature 13–79%); `unsupported` claims per deliverable (best systems ~44–92 per report); redundant-query ratio per worker; pre-send bounce rate *by reason* (high "criterion not observable" = Nova's brief-writing is the problem); tokens per `entailed`-or-better claim by tier; Rung 5 trigger rate and human-escalation rate; `conflicted` labels per deliverable (zero is suspicious); entailment false-positive/negative on the labelled set; Rung 2 precision (sample-agreed but later `unmet`).

---

## 14. Open questions

1. Most load-bearing numbers are 2024–25 vintage; the one 2026 replication (sample agreement) showed the signal weakening. Re-measure on your tasks before tuning.
2. Recitation, progress ledgers, reference-not-summary, deterministic rails: universally shipped, never ablated (grade C).
3. Gap-loop saturation for long-form work is unmeasured; the novelty + query-diversity rule is a design choice.
4. Whether the `rejected`/abort path reduces gaming on Claude-family workers (ImpossibleBench's 6× effect barely moved Opus 4.1).
5. Effective independence of cross-family checks on long-form outputs; ~2 effective votes is measured for judges on classification, not reports.
6. Style-consistency cost of crossing families at the Verifier/escalation boundary: unmeasured; mixing is confined to selection points.
7. Nova's entry-tier choice is a model routing decision with no evaluation; the default-down rule and cheap up-triggers are the mitigation.
8. A source-credibility scorer: universally needed, not published; the UGC rule is a placeholder.
9. The independence heuristic for `corroborated` will miss syndication until evaluated.
10. If you later need a guarantee ("≤10% of `corroborated` wrong"), a conformal wrapper on the Verifier's acceptance ([SCOPE](https://arxiv.org/html/2602.13110v3), pairwise judging) is the evidenced route and needs your labelled set.
