# Independent audit of `requirements_engine_COMPLETE_HANDOFF.zip`

Read: all 20 files (the two nested zips unpacked; `question_catalogue.md` and `source_notes.txt` confirmed identical at 386 node IDs; `RESEARCH_FINDINGS_previous_pass.md` confirmed identical to `claude_research_refinement.md`).

Test applied to every claim: **could two competent builders, both honestly following the owner's answers, ship different products?** Where yes, the handoff's 88-question interview is not enough. Where the answer could not be given at all, the app is not buildable.

Verdict on the handoff: the structure is right (ten parts, closed choices, record-anchored authority, flagged metrics). The final interview still leaves **31 divergence points**, its "PASS" proof is keyword matching, and it has no machine-checkable done-rules — so nothing in it could actually drive Nova + script. All 31 are closed in v3 (`INTERVIEW_v3.md` / `question_graph_v3.json`).

## A. Product-level gaps (the app cannot be started without these)

| # | Gap in handoff | Why two builders diverge | v3 |
|---|---|---|---|
| 1 | Platform never asked (web / iOS / Android / desktop) | The single largest fork. Part B Q14 silently assumes responsive web. | A.06 |
| 2 | App name dropped between passes (`app_name` existed in the catalogue) | Appears on every screen and email. | A.05 |
| 3 | Country / language never asked | DD/MM vs MM/DD, currency symbol, timezone. Sam's users are in Australia; a US-default builder ships MM/DD. | A.13 + `sys_locale_formatting` |
| 4 | Public (no-login) surfaces never asked | Landing page? Public booking form? Q7 only asks whether login exists. | A.10 |
| 5 | Existing data import never asked | "Complete working app" with an empty database is not complete for a business migrating from a spreadsheet. | A.12 |
| 6 | Inbound API / webhooks never asked | Other systems pulling data is a different product. | A.11 → Public API integration instance |
| 7 | No "super role" question | Q32–35 force the owner to tick Admin on every record × 4 verbs. | A.16 — named once, skipped everywhere |
| 8 | Landing screen after login classed as SYSTEM_DEFAULT (`auth_success_auth_flow`) | Dashboard vs list vs last record — product-visible, per role. | C.06 |
| 9 | Terms / privacy acceptance never asked | Legal checkbox at signup is a visible product decision. | AU.14 + DI.11 |
| 10 | No first-admin bootstrap anywhere | Nothing in the handoff creates the first login. | `sys_first_admin` + DI.04 |
| 11 | No deploy inputs (domain, sender email, gateway keys, support contact) | The app cannot send an email or take a payment. | 11 deploy inputs (block 0 form, not interview) |

## B. Auth / roles

| # | Gap | v3 |
|---|---|---|
| 12 | Default role for self-registered users never asked (one builder makes signups Members, another Admins) | AU.05 |
| 13 | Invite flow: who invites, what role the invitee gets — never asked | AU.06 |
| 14 | MFA method: classification says "kept as closed choice", final interview lost it | AU.07 |
| 15 | Account deletion: Q24 asks what happens to data but not **who** may delete (self / admin) | AU.12 |
| 16 | Multiple roles per person never asked (single-select vs multi-select assignment) | P.00 |

## C. Records (where most of the two-builder risk actually lives)

| # | Gap | v3 |
|---|---|---|
| 17 | "One choice from a list" — the options are never asked | R.02 `options` required |
| 18 | Uniqueness never asked (email, SKU, invoice number) | R.02 `unique` required |
| 19 | "Link to another record" — target record never asked at field level | R.02 `target_record` required |
| 20 | "Number" is one type — whole vs decimal diverges | `whole_number` / `decimal_number` |
| 21 | Title/display field never asked — what a record is *called* in lists, links and notifications | R.03 |
| 22 | Human-readable numbering (INV-0001) never asked; UUID default hides it | R.04 |
| 23 | **Scope "their team" used to resolve the audit's own Manager example, then dropped from Q32's closed choices** (only all/own offered) | R.05/R.07/R.08 add `linked` + `via` |
| 24 | **"Own" never defined** — created_by vs assigned_to | R.09, gated on any "own" scope |
| 25 | Relationship cardinality never asked (one-to-many vs many-to-many) | R.11 |
| 26 | Non-CRUD buttons (duplicate, send, print, mark paid) have no home — handoff derives all actions from CRUD + transitions, so they can never exist | R.15, feeds the numbered action inventory |

## D. Forms / Flow / Notify / Reports / Billing / Tenants

| # | Gap | v3 |
|---|---|---|
| 27 | Conditional fields: classified "asked only if the owner indicates", but no prompt can surface it | F.03 |
| 28 | Workflow moves only by a person; automatic transitions ("Paid when payment arrives") impossible | FL.03 mover = roles \| automatic |
| 29 | Rejection target locked as "standard advance/revert" — back-to-previous vs back-to-start vs terminal Rejected are three products | FL.06 |
| 30 | Preconditions, read-only-after-stage, and stage-change notifications never prompted | FL.04, FL.09, FL.11 |
| 31 | Free trial, pay-by-invoice, usage unit, org admin role, cross-org operator role, integration timing and per-user vs org connection, report screen-vs-document, scheduled report delivery — all absent | B.05, B.07, B.06, T.03, T.05, FLX.03, FLX.04, RP.03, RP.08 |

## E. Structural problems with the handoff itself

1. **`proof_runner.py` proves nothing.** Its PASS is `re.search(r"metric", interview)` and friends — six keyword greps. It also crashes on any second run (`shutil.rmtree` without `import shutil`; reproduced). Replaced by `validate_graph.py`: gates must point backwards at real questions, gate values must be options of the target, every question must carry a done-rule, every spec field must have exactly one source, every duration/schedule answer must land in the recurring-ops derivation. Self-test breaks a good graph eight ways and proves each is caught.
2. **No done-rules.** The handoff says "the engine may ask in whatever order… and only re-ask if the answer was too ambiguous to build from" — but nothing defines "too ambiguous". Sam's rule is *model controls wording, script controls done*. v3 gives every question a machine-evaluable done-rule (`one_of`, `roles_scoped_min1` with named scopes, `fields_list` with per-type required keys, `per_transition`, …).
3. **Prose and structure could drift.** Four documents restate the same question set by hand (final interview, classification, traceability, derivations) and already disagree (MFA method, "team" scope). v3 has one source (`build_graph.py`) that emits both the JSON and the readable interview.
4. **Counts are wrong in both directions.** `CODEX_HANDOFF.md` says 0 two-builder failures; `MISSING_FILES.md` says 2; this audit finds 31. `FINAL_USER_INTERVIEW.md` claims "86 fixed prompts" — 38 are fixed (Parts A, B, C, K, L), 48 are per-instance templates.
5. **Recurring / other-side operations have no namespace** (Sam's locked rule). Retention purges, stage time-outs, date-relative reminders, renewals, trial expiries, syncs were scattered inside free-text answers. v3 tags every such answer `feeds: OPS`, derivation D11 collects them, Z.01 reads the list back for confirmation, each gets an OPS id.
6. **`question-graph.json` was never produced.** It now exists.

## F. Alignment with Sam's locked model

- Ten parts: Auth (AU), Forms (F), Records (R), Permissions (P), Notify (N), Files (FI), Reports (RP), Flow (FL + FLX), Billing (B), Client (C). Integrations folded into Flow as locked.
- Block 0 (logging, audit, config, error handling, health, backups) is the locked-defaults table plus deploy inputs — never asked.
- Involvement dial is 0.01, asked before every part; changes read-back depth only.
- Every button and transition gets a number via D12 and is read back in Z.02; D15 states the verification rule: perform action N as each role, assert the declared outcome and location — no LLM in the pass/fail path.

## G. Open decisions — not guessed, surfaced

- **OD-1 — Where do tenants live?** Sam's ten parts define *Client* as the interface. The handoff's CLIENT category is tenants/organisations. v3 keeps Client = interface (Sam's later, locked meaning) and puts organisation questions in a separate Part T. If tenants should be a part, name it; if they belong inside Permissions, say so and T merges into P.
- **OD-2 — Public API as an integration.** A.11 = yes spawns a Flow/external-system instance named "Public API". An inbound API may deserve its own template (auth keys, rate limits, which records are exposed). Decide whether the FLX template is enough or a dedicated one is needed.
- **OD-3 — Involvement dial semantics.** 0.01 changes how many derived values are read back. It does not skip any *required* question. If hands-off should also accept defaults for optional questions (R.04, R.15, F.03, FL.04, FL.09, FL.10, RP.08 — all `min: 0` / optional) without asking, that is a one-line change in the engine, but it must be decided, not assumed.
- **OD-4 — Ambiguous metric term list.** The list is a config block in `build_graph.py`. "average" and "rate" are included on the strict side; they will fire RP.05 often. Trim if that is too noisy.
