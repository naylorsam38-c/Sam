# Round 5 rulings — authority order + the held decisions (H1–H5, H-T1–H-T6)

Sam asked (verbatim): "Can you finish the other three now, please?" — referring to the three
items from the original Master Spec audit I had left as recommendations rather than resolutions:
the authority-order mapping, the readiness-state translation (delivered as code —
`readiness_and_library.py`, proven against 29 real fixtures — see `review.md` Round 5), and the
still-open held decisions (H1–H5 from NUMBERING.md, H-T1–H-T6 from TEMPLATE_STANDARD.md).

This document is the other two: a formal ruling on authority order, and a formal ruling on each
held decision. Every ruling here is made **from the memory-summary record of this session**, not
from re-reading NUMBERING.md/TEMPLATE_STANDARD.md/BUILD_PY_SPEC_v1.md/the Bible directly — those
source files were not re-uploaded this round. Where a ruling depends on something only the source
document itself can settle, that is said plainly rather than guessed past.

---

## 1. Authority order

The Master Spec (Section 2) names seven documents in order:

1. THE BIBLE
2. BUILD CHAIN SPECIFICATION
3. NUMBERING.md
4. TEMPLATE BUILD GUIDE
5. HARVEST SPECIFICATION
6. CONSTITUTION AND GOVERNANCE FILES
7. THIS MASTER BUILD-TO-LIBRARY SPECIFICATION

Sam's actual, locked authority order (confirmed earlier in this engagement) is four real
documents: **the Bible → BUILD_PY_SPEC_v1.md → NUMBERING.md → TEMPLATE_STANDARD.md**.

**Ruling: these are not in conflict — they map cleanly onto each other, and the apparent
"conflict" flagged in the original audit was a naming gap, not a contradiction.**

| Master Spec slot | Real document | Ruling |
|---|---|---|
| 1. THE BIBLE | The Bible (14 rules) | Exact match. No action. |
| 2. BUILD CHAIN SPECIFICATION | `BUILD_PY_SPEC_v1.md` | Same role, different name — this is the document that governs build.py's own machinery (stage1/stage2, layer 1/2/3, the ledger). Read every future "Build Chain Specification" citation as `BUILD_PY_SPEC_v1.md`. |
| 3. NUMBERING.md | `NUMBERING.md` | Exact match. No action. |
| 4. TEMPLATE BUILD GUIDE | `TEMPLATE_STANDARD.md` | Same role, different name — this is the document that governs template shape, the "template references, never contains" rule, and the don't-touch rule for approved templates. Read every future "Template Build Guide" citation as `TEMPLATE_STANDARD.md`. |
| 5. HARVEST SPECIFICATION | **no document on record** | `TEMPLATE_REFERENCE.md` is a harvest *deliverable* (43 app types' worth of completed harvest output), not a harvest *specification* (the rules that produced it). If a Harvest Specification exists separately from `TEMPLATE_REFERENCE.md`, it has not been part of this engagement — flagged honestly rather than assumed absent or silently substituted. |
| 6. CONSTITUTION AND GOVERNANCE FILES | **no document on record** | Same treatment as slot 5 — nothing under this name has been seen in this engagement. Flagged, not guessed. |
| 7. THIS MASTER BUILD-TO-LIBRARY SPECIFICATION | The Master Spec itself | Already correctly last — it explicitly states it "coordinates the build process" and "does not replace" the documents above it (Section 2). No action needed; it already defers correctly by its own text. |

**Net effect:** Sam's real, locked 4-document order is a strict sub-sequence of the Master Spec's
7-slot order, in the same relative positions (1, 2, 3, 4 against the Master Spec's 1, 2, 3, 4).
Nothing needs to change about the locked order. The two open items are document-existence
questions, not ordering questions:

- Does a Harvest Specification exist separately from `TEMPLATE_REFERENCE.md`? If yes, it should be
  supplied so it can take slot 5 for real; if no, slot 5 should be formally marked N/A in any
  document that cites this authority order, rather than left implicitly unresolved.
- Do Constitution/Governance files exist? Same treatment.

Per the Master Spec's own conflict-handling rule (Section 2, "if two documents conflict: do not
silently choose, record the conflict, apply the higher authority, stop only where the conflict
prevents safe execution") — there is no conflict here to apply higher authority to, so nothing
stops. This ruling records that explicitly rather than leaving the audit's original "CONFLICTING"
label standing uncorrected.

---

## 2. Held decisions — NUMBERING.md (H1–H5)

**H1 — where does "repair never resumes a run" get cited from?**

Ruling: cite `BUILD_PY_SPEC_v1.md`'s own section on stage2_prove/repair semantics, not the Bible.
This is proven, tested machinery behavior specific to build.py's repair loop (loop guard, restart
ceiling, regression guard — all reproven again this round, 29/29), not a universal principle the
Bible would state at the level of its 14 rules. Adding it as a 15th Bible rule would misplace a
build-chain-specific fact into the Bible's role as universal law.

**H2 — watch.py's place in the spec set.**

Ruling: retire it from the spec set entirely. Its gate role is already performed, for real, by
`build.py`'s own `stage2_prove()` — proven this round and every prior round (rows 17–21 in the
proving table exercise exactly the gate behavior watch.py would have provided). Keeping a
superseded document in the authority set invites exactly the kind of silent-drift risk the Bible's
own rules warn against.

**H3 — moot, given H2.** The Bible has 14 rules; any "R" numbers referenced beyond 14 should cite
`BUILD_PY_SPEC_v1.md`'s own machinery sections, not a phantom 15th–16th Bible rule.

**H4 — what were the NOT-/RPT-/WFL- prefixes proposed to number?**

Ruling: **genuinely unresolvable from this session's memory record.** I do not have the original
proposal that introduced these prefixes, and guessing at their intended scope (notifications?
reports? workflow-something?) would be exactly the kind of fabrication Bible rule 4 and Sam's own
"do not guess, pause, identify the gap, surface it clearly" standard exist to prevent. This one
stays open. If the original NUMBERING.md draft or proposal that introduced NOT-/RPT-/WFL- still
exists, that is the source to resolve it from — not inference.

**H5 — does UNPROVEN get added as a 4th check status?**

Ruling: no — fold it in, don't add it. build.py's real, tested code (`chk["run"]` return contract
in `run_layer_one()`, confirmed again this round while adding the `is_browser` field) uses exactly
three statuses: PASS/FAIL/SKIP. A proving-table row is either checked (PASS/FAIL) or explicitly
skipped for a stated reason (SKIP, e.g. row G1's CAP-0012 with no declared route) — there is no
observed real case where "unproven" means something PASS/FAIL/SKIP doesn't already cover. Adding a
4th value would be a speculative addition to tested, working machinery, which is the wrong
direction to change proven code in.

---

## 3. Held decisions — TEMPLATE_STANDARD.md (H-T1–H-T6)

**H-T1 — template ID format.**

Ruling: `TPL-nnnn`, 4 digits — matching `CAP-`/`GAP-`'s convention, not `APP-`/`SCR-`/`BTN-`'s
3-digit convention. Reasoning: template cardinality is expected to exceed 999 once all 43 app
types' variants are counted (multiple templates per app type over time, per the Master Spec's own
per-type harvest→build flow), the same growth pattern that justified 4 digits for CAP-/GAP- over
the 3-digit APP-/SCR-/BTN- allocations.

**H-T2 — "most robust" template definition.**

Ruling: approve as-is. `TEMPLATE_REFERENCE.md` is already a complete, proven 43/43 deliverable
built exactly to this definition (confirmed in the original audit's canonical-app-type check:
43/43 resolved with zero unresolved entries). There is no observed case in this engagement where
the definition produced an ambiguous or unusable template.

**H-T3 — exact-equality vs. subset matching on contract axes.**

**Implemented in code this round, not just ruled on.** `match_contract()` in `build.py` now uses a
directional subset match on two axes — `nullable_fields` (a capability may declare a field
nullable only if the caller already expects it nullable: `cap_nullable ⊆ exp_nullable`) and
`security_constraints` (every constraint the caller requires must be present and equal on the
capability; the capability may declare additional constraints the caller didn't ask for) — while
keeping the other five axes (`input_types`, `output_types`, `permissions`, `requires_auth`,
`side_effects`) at exact equality. Proven with two new real fixtures this round: CAP-0013/row G2
(a capability that is strictly *more* lenient/secure than required — must bind) and
CAP-0014/row G3 (a capability that genuinely fails to meet a required security constraint — must
still HELD). 29/29 pass, including the full pre-existing suite.

**H-T4 — templates/ directory placement.**

Ruling: `templates/` stays a peer of `shelf/`, not nested under it. This matches build.py's
existing, proven `CONFIG_BLOCK` layout and reinforces TEMPLATE_STANDARD's own "a template
REFERENCES capabilities, never contains one" rule structurally — nesting templates under shelf
would visually imply containment the data model explicitly forbids.

**H-T5 — can a template be approved with unbound `target_capabilities`?**

Ruling: yes. Design-lock (a template's slot layout, entry screen, and contract expectations being
final) and capability-binding (whether a real shelf CAP/IMPL currently satisfies each slot) are
separate concerns, and this round's own `readiness_and_library.py` already models them as
separate states — a template can be accepted (`HARVESTED` → template-accepted) while its required
capabilities are still `CAPABILITIES_UNBOUND`, proven for real against `row06_missing_shelf_cap`
this round. Critically, build.py's own assembly step already refuses to build any app whose
required capabilities aren't bound to an approved, active implementation (row 6 in the proving
table, reproven this round) — so approving a template with unbound capabilities carries no risk of
an app actually shipping without them; it only means the design is locked before the shelf catches
up.

**H-T6 — what change earns a new template variation (a "Q variation")?**

Ruling — a Q variation is earned by a change to any of:
- `required_capabilities` (the set of capabilities the template depends on),
- any slot's `target_capability` (which capability a given slot is wired to),
- `entry_screen_name` or any slot's name (structural identity of the template),
- any axis of a slot's `expected_contract` (the exact thing H-T3 above governs the matching
  strictness of).

A Q variation is **not** earned by:
- a capability's display-name changing (cosmetic; the id is what the template actually depends
  on),
- reordering optional (non-required) capabilities,
- JSON formatting/whitespace differences with no semantic change.

This mirrors the don't-touch rule's own spirit (approved templates never silently rewritten) while
keeping genuinely cosmetic diffs from forcing unnecessary re-derivation and re-approval churn.

---

## Summary table

| Item | Status |
|---|---|
| Authority order | Resolved — real 4-doc order maps cleanly onto Master Spec's 7-slot order; slots 5–6 flagged as no-document-on-record, not guessed |
| H1 | Resolved — cite BUILD_PY_SPEC_v1.md, not the Bible |
| H2 | Resolved — retire watch.py, superseded by stage2_prove() |
| H3 | Resolved (moot given H2) |
| H4 | **Open — genuinely unresolvable from this session's memory alone; needs the original proposal** |
| H5 | Resolved — fold UNPROVEN in, keep PASS/FAIL/SKIP |
| H-T1 | Resolved — TPL-nnnn, 4 digits |
| H-T2 | Resolved — approved as-is |
| H-T3 | **Resolved and implemented in code** — see build.py's match_contract(), rows G2/G3 |
| H-T4 | Resolved — templates/ stays a peer of shelf/ |
| H-T5 | Resolved — yes, design-lock and capability-binding are separate; build.py already enforces the safety net |
| H-T6 | Resolved — Q-variation trigger list given above |
