SPEC AUTHORITY CLEANUP REPORT

Decision: HOLD

Authority document: CANONICAL_SPEC.md (repo root)

Date evidence: `CANONICAL_SPEC.md` was first committed (`ba9389b`, 2026-09-12 19:10:50 UTC) in the same commit as the first 43-app build — neutral, not evidence either way. It received 6 more commits, last at 2026-09-13 01:34:56 UTC (`22e5f92`). Real app-library work continued after that: `HEAD` (`a1653ea`, 02:47:14) is not reflected in it, and the current uncommitted working tree goes much further still (336 files, 21,710 insertions vs. `HEAD`) — none of it reflected anywhere in the spec. The app library has no discrete "built" instant for the spec to be dated "after." See `SPEC_AUTHORITY_DECISION.md` §C.1 for full evidence.

Alignment result: 10 of 13 evaluated contract rows PASS outright (C.1–C.3, C.5, C.7 fully; C.6's engine list and one of its two documented gaps). Two named, quoted passages are stale: §C.4's "genuine gaps" paragraph describes a cross-app data-filename collision class as still open that this session's own generation-time guard has since closed (proven via real break/restore); §C.6's gap item (1) overstates a limitation that no longer applies to the per-slot compute-check family (only to the separate Playwright journey, which is genuinely still limited that way). Two real, working mechanisms (arrangement rendering; the authenticated-slot proving check) have no corresponding rule anywhere in the spec. Full rule-by-rule table in `SPEC_AUTHORITY_DECISION.md` §C.2.

Files moved: NONE (no specification was promoted or superseded, so Phase E did not run)

Files preserved: The prior, less formal cleanup report (from before this work order existed) was copied — not deleted — to `spec/archive/reports/SPEC_AUTHORITY_CLEANUP_REPORT_prior_2026-09-13.md`, with a SUPERSEDED notice prepended, so this filename could be regenerated in the new required format without losing the earlier record. `CANONICAL_SPEC.md` and every other inventoried document preserved unchanged.

Files deleted: NONE

Verification result: PASS (`verification/spec_authority_check.py`, 6/6 checks — see full output below)

Open issues:
1. `CANONICAL_SPEC.md` §C.4's "genuine gaps" paragraph needs rewriting to reflect the now-closed cross-app data-filename collision guard.
2. `CANONICAL_SPEC.md` §C.6's gap item (1) needs to distinguish the Playwright journey (still limited) from the per-slot compute check (no longer limited).
3. Two real mechanisms (arrangement rendering; the authenticated-slot proving check) are undocumented in the spec.
4. No mechanism exists yet to keep the spec and the code in lockstep going forward (no "update spec in the same commit as the code it describes" rule, no automated drift check).
5. The four externally-named authority documents (the Bible, `BUILD_PY_SPEC_v1.md`, `NUMBERING.md`, `TEMPLATE_STANDARD.md`) still do not exist anywhere on this machine — re-confirmed, not assumed from a prior report. Not required to resolve this HOLD, but any future claim of alignment with them specifically remains impossible until supplied.
6. Deliverable `SPEC_MANIFEST.json` (listed in the work order's §11 as always-required) was **not** produced. Resolution taken: Phase D's own text scopes manifest creation to "Only if the decision is PROMOTE," which this decision is not — creating an "active" manifest for a spec being held, not promoted, would itself be a false authority claim. This deviation is recorded here explicitly rather than resolved silently, per rule 9 ("Do not mark the task complete if a required check is inconclusive") — flagging the contradiction between §7 and §11 rather than picking a side unannounced.

Next action: Commit the current working tree (336 files, currently uncommitted — the single biggest driver of this HOLD). In the same commit or the one immediately after, correct `CANONICAL_SPEC.md` §C.4 and §C.6 per Open Issues 1–2, and add the two missing rules per Open Issue 3. Then re-run this exact work order — at that point both the date test and the alignment test compare two facts that finally refer to the same, fixed, dated state, giving this decision a real chance of resolving to PROMOTE.

---

## Full verification output

```
PASS  SPEC_AUTHORITY_INVENTORY.json exists and parses
PASS  CANONICAL_SPEC.md unchanged since inventory
PASS  SPEC_AUTHORITY_DECISION.md states the expected decision
PASS  no active spec manifest exists (consistent with HOLD)
PASS  application verification evidence present and PASS  -- overall='PASS'
PASS  archived prior cleanup report preserved

OVERALL: PASS  (6/6 checks passed)
```

## Deliverables produced by this work order

1. `SPEC_AUTHORITY_INVENTORY.json` — 26 governance/specification documents inventoried: path, filename, SHA-256 (working tree + HEAD), git tracked/dirty status, filesystem mtime, git first/last commit, cross-references, classification with evidence.
2. `SPEC_AUTHORITY_INVENTORY.md` — human-readable rendering of the same.
3. `APP_BASELINE_ALIGNMENT_REPORT.md` — all 10 required baseline items, each VERIFIED against existing or freshly-confirmed evidence (none UNVERIFIED).
4. `SPEC_AUTHORITY_DECISION.md` — the C.1 date test, C.2 rule-by-rule alignment table, C.3 decision.
5. `spec/archive/reports/SPEC_AUTHORITY_CLEANUP_REPORT_prior_2026-09-13.md` — the preserved prior report, marked SUPERSEDED.
6. `verification/spec_authority_check.py` — deterministic checker, config block at top, 6/6 PASS.
7. This file.

No `spec/active/` set was created (see Open Issue 6). No application code was modified. No specification was deleted, archived-as-superseded, or silently rewritten.
