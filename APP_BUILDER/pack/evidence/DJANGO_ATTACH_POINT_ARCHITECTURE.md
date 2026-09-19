# Django/PostgreSQL + Attach-Point Harvest Architecture — final report

Covers the full handoff: rewriting Rule A to Django+PostgreSQL, adding Rule G
(attach points), retiring the three Flask-era apps, building the discovery/
scoring stage, extending the capability contract, the admission test suite,
and the three-category validation pilot (event ticketing, analytics/BI,
challenge platform).

Every claim below is labeled **IMPLEMENTED** (code exists and was run
successfully at least once), **TESTED** (covered by an automated test that
passed), **OBSERVED** (a real, first-hand-verified fact about a repository or
run, not a design intention), **DESIGNED** (the code exists and is believed
correct but was not exercised end-to-end in this session), or **NOT YET
PROVEN** (a real, named gap). Nothing here claims proof it does not have.

## 1. Files changed, created, and retired

Full commit range for this phase: `033abd7..6f9e9c4` on
`claude/harvest-redash-ctfd-hyyyc7`, on top of the already-merged-in-progress
Redash/CTFd harvest (`45f85a3..09ea091`, covered separately in
`TWO_MORE_APPS.md`).

**Retired** (moved, not deleted — `pack/retired/<slug>/`), each with its
harvested shelf parts, `form.json`, `tree.json`/`.txt`, `host_test.py`,
`evidence/`, a new `RETIRED.md` explaining why, and a new `complete_source/`
(full working tree at the pinned commit, `.git` stripped) + `COMMIT.txt`:
- `event-ticketing` (Indico, `indico/indico` @ `eb90264caec7d1210959c453d1f93ad88a98e6ce`, MIT)
- `data-dashboard` (Redash, `getredash/redash` @ `8f6b15d30da4...`, BSD-2-Clause)
- `challenge-platform` (CTFd, `CTFd/CTFd` @ `8864bc0cea5b...`, Apache-2.0)

**Created:**
- `pack/1_harvest/test_admission.py` — the Section 20 test suite (see §7)
- `pack/0_harvest/hunt.py` — discovery/scoring stage (see §5)
- `pack/0_harvest/run_three_category_pilot.py` — the pilot's driver, a
  permanent re-runnable record of the real evidence behind every
  admit/reject decision
- `pack/0_harvest_results/` — the pilot's real output: one `REPORT.md`,
  `ATTACH_POINTS.md` and `evidence/` per candidate, one `CATEGORY_SUMMARY.md`
  per category, one `HARVEST_SUMMARY.md` overall (12 candidates)
- Per-app `ATTACH_POINTS.md` / `ATTACH_POINTS.json` sidecars, written by
  `harvest_parts.py` at admission time (mechanism only — no live app has
  been harvested under it yet; see §9)

**Modified:**
- `pack/rules/GOD_MODE_RULE_HARVEST_ADMISSION.md` and
  `GOD_MODE/ACTIVE/GOD_MODE_RULE_HARVEST_ADMISSION.md` — Rule A rewritten,
  Rule G added (see §2)
- `GOD_MODE/REGISTERS/RULE_REGISTER.md` — Harvest Admission row and the
  Capability Record Contract row (now thirteen axes) both updated
- `pack/1_harvest/harvest_parts.py` — `REQUIRED_FRAMEWORK`, Rule G config
  and enforcement, `usable_attach_points()`, `render_attach_points_md()`,
  the `ATTACH_POINTS.md`/`.json` write (see §3)
- `pack/1_harvest/shelf_records.py` and `pack/3_assembly/build.py` —
  `attaches_to` field, 13th `match_contract` axis (see §4)
- `pack/4_host/host.py`, `pack/5_chain/layer1_checks.py`,
  `layer2_repair.py`, `layer3_gap.py` — stale `APP_SLUG`/`CHECK_SUITE`
  values pointing at now-retired apps blanked, each with a dated comment
- `pack/number_registry.json` and `pack/2_numbering/number_registry.json`
  (kept byte-identical) — three apps marked `"status": "retired"`, numbers
  1-3 and capability numbers 1-20 preserved, never reused (N1)
- 40 shelf record files (`CAP-0001`..`CAP-0020` and their `IMPL-01.json`) —
  `status` changed to `"retired"`

**IMPLEMENTED.** All of the above exist in the working tree and are
committed and pushed to `claude/harvest-redash-ctfd-hyyyc7` (PR #8).

## 2. Rules changed, rules preserved

- **Rule A rewritten**: "Django and PostgreSQL", was "Flask and PostgreSQL".
  **IMPLEMENTED** in both copies of the admission-rule document and in
  `harvest_parts.py`'s `REQUIRED_FRAMEWORK`.
- **Rule G added**: attach points (EVENT/SLOT/DATA), declared at admission,
  backed by real evidence, at least `MIN_HOOKS` of them, adapters marked
  `ADAPTER` never `NATIVE`. **IMPLEMENTED** as an enforcement block in
  `check_admission()` and **TESTED** (§7).
- **Rules B, C, D, E, F preserved unchanged** — published API docs,
  permissive licence (MIT/Apache-2.0/BSD-2/BSD-3/ISC/MPL-2.0), structural
  match, one source per app, write-the-part fallback. **OBSERVED**: all five
  fired correctly and independently of Rule A/G during the pilot (§6) —
  e.g. `pdogg/ctfmanager` was rejected on Rule A datastore alone, cleanly
  passing Rule C.
- **Governance/provenance/licensing rules outside the harvest-admission
  document** — untouched. **OBSERVED**: `git diff` for this phase touches
  no file under `GOD_MODE/ACTIVE/active_standards/`.

## 3. Byte-identity of the two rule-document copies

`sha256sum` on both, checked at the end of this phase:
```
b8c49db2ebc268c7e3f41fd664644c3e73d706596f469c4caf2fe19c097315f8  pack/rules/GOD_MODE_RULE_HARVEST_ADMISSION.md
b8c49db2ebc268c7e3f41fd664644c3e73d706596f469c4caf2fe19c097315f8  GOD_MODE/ACTIVE/GOD_MODE_RULE_HARVEST_ADMISSION.md
```
**OBSERVED — identical.** Both copies were edited together throughout; this
hash check was re-run at the very end of the phase, not just once after the
initial rewrite, to confirm no later edit desynced them.

## 4. Capability-contract changes

- `attaches_to: list[str]` added to the capability record schema
  (`CAP_RECORD_KEYS` in both `build.py` and `shelf_records.py` — a
  pre-existing, deliberate duplication kept in sync by hand rather than
  unified, consistent with how that duplication already existed before this
  session). **IMPLEMENTED**, **TESTED** (`TestCapRecordSchema`, §7).
- `match_contract()` gained a 13th axis: required attach points (named, not
  application-specific) must all be present in the target application's
  `ATTACH_POINTS.json`. Three states are distinguished, not collapsed to a
  boolean: no requirement (axis skipped, prior behaviour unchanged),
  requirement + unknown target coverage (refused, not assumed compatible),
  requirement + proven coverage (checked for real). **IMPLEMENTED**,
  **TESTED** (`TestCapabilityAttachPointCompatibility`, §7).
- `read_available_attach_points(slug)` reads `shelf/<slug>/ATTACH_POINTS.json`
  and returns `None` (unknown) vs. `set()` (proven zero) distinctly — the
  same None/empty-set distinction `match_contract` relies on.
  **IMPLEMENTED**.

## 5. Discovery/scoring stage

`pack/0_harvest/hunt.py` — clones a real candidate at a pinned commit,
verifies the resolved commit matches, runs a keyword-signal sweep (Section 7,
discovery only, never proof on its own), computes git-derived quality
metrics (commit recency, contributors, tags — real, from the clone's own
history; test-suite presence is a heuristic), scores candidates (heaviest
weight on third-party plugin evidence, per Section 8), and runs the same
`check_admission()` `harvest_parts.py` will later use, imported rather than
copied. Writes `REPORT.md`, `ATTACH_POINTS.md`, and `evidence/` per
candidate, `CATEGORY_SUMMARY.md` per category, `HARVEST_SUMMARY.md` overall.
Never writes to the shelf; never auto-promotes.

**IMPLEMENTED and OBSERVED working**: run twice in this session — once as a
smoke test against `django/django` (cleaned up afterward), once for real as
the three-category pilot (§6), 12 real candidates, all output verified by
hand against the actual `REPORT.md` files it wrote.

## 6. Three-category validation pilot

Categories confirmed by direct instruction: event ticketing, analytics and
BI (Redash-equivalent), challenge platform (CTFd-equivalent). 12 real
candidates inspected — cloned at a pinned commit, LICENSE file read
verbatim, `settings.py`/`requirements.txt` read for framework and datastore,
grepped for real signal/plugin/API evidence, `git log` read for activity —
then run through `hunt.py`'s real admission gate.

**Result: zero candidates admitted, in every category.**

| Category | Candidates inspected | Admitted | Rejected |
|---|---|---|---|
| Event ticketing | 5 | 0 | 5 |
| Analytics and BI | 3 | 0 | 3 |
| Challenge platform | 4 | 0 | 4 |

**Winner per category: none.** Full reasoning per candidate is in
`0_harvest_results/<category>/<candidate>/REPORT.md`; the headline reasons:

- **Event ticketing** — `iyanuashiri/meethub` (Django 5.2.4, PostgreSQL,
  MIT, actively maintained) is real and structurally close, but its one
  DRF API route is commented out of `urls.py` (Rule B: no published API,
  Rule G: no usable attach point). `fossasia/eventyay` is the strongest
  structural match — active, a real inherited plugin entry-point mechanism
  (`eps.select(group='pretix.plugin')`) — but its own `NOTICE` file
  discloses portions derived from pretix/pretalx/venueless (AGPL-3.0
  upstream) with no stated relicensing permission, despite a top-level
  Apache-2.0 `LICENSE` file. That conflict is recorded as **licence
  UNRESOLVED**, not guessed either way (Rule C). The rest are abandoned
  (2017) or structurally mismatched (`django-tickets` is a helpdesk
  tracker, not event-ticket sales).
- **Analytics/BI** — **OBSERVED**: no production-quality Django-native BI
  application exists in the space searched. The real open-source BI
  ecosystem (Metabase, Apache Superset, Redash, Grafana, Lightdash,
  Evidence) runs on Clojure, Flask, Go, and TypeScript/Node — not Django.
  The Django-tagged candidates found are a dead single-purpose library
  (`django-bi`, LGPL, inactive since 2019) or single-commit scaffolds
  created within days of this pilot, with no track record.
- **Challenge platform** — every real Django CTF platform found
  (`SniperOJ/Jeopardy-Platform`, `pdogg/ctfmanager`, `super1337/Super1337-CTF`,
  `angstromctf/djangoctf`) is abandoned 6-12 years (last commits 2014-2019)
  and fails licence (GPL-3.0, or none recorded) or datastore (MySQL) before
  quality/activity is even considered.

**Library promotion**: not exercised. The mandatory promotion instruction is
conditional on successful admission ("anything that is successfully
admitted and validated must be placed into the active Library") — nothing
was admitted, so no promotion, and no new `LIBRARY_INDEX.md`/manifest entry
was written. **NOT YET PROVEN**: which library mechanism a future admitted
Django app should be promoted into is a genuinely open question this pilot
surfaced but did not need to resolve — `GOD_MODE/ACTIVE/active_apps/
APP_LIBRARY_MANIFEST.md` describes a separate, much larger 43+6+15-app
library with its own `verification/`, `OUTPUT_LIBRARY/`, and
`consolidate_library.py` pipeline, already listing an unrelated
`event_ticketing` canonical app; whether `pack/`'s harvest/shelf system is
meant to feed that library or promote through a mechanism scoped to `pack/`
itself was never stated and is not guessed here.

## 7. Tests executed and results

`APP_BUILDER/pack/1_harvest/test_admission.py`, Section 20's 21-item list
across two tiers:

- **Tier 1** (pure gate logic, constructed input): framework gate
  (Django passes; Flask/FastAPI/Node rejected; PostgreSQL mandatory),
  attach-point gate (keyword-only evidence insufficient; a real point
  satisfies; `MIN_HOOKS` enforced; missing points rejected; NATIVE vs
  ADAPTER distinguishable; an unrecognised implementation value is not
  usable), quality scoring cannot override hard gates (confirmed via
  `inspect.signature` that `check_admission()` has no scoring parameter at
  all), application-specific capability dependencies rejected,
  capability/attach-point compatibility (skip-axis; incomplete coverage
  rejected), the `ATTACH_POINTS.md`/`.json` write path (exercised for real
  through `harvest_form()` itself, network mocked, everything else real —
  not simulated), capability-record schema sync between `build.py` and
  `shelf_records.py`.
- **Tier 2** (real repository evidence): Indico's checked-in
  `pack/retired/event-ticketing/complete_source/` used as the real Flask
  rejection case, per direct instruction; fresh real shallow clones of
  `django/django`, `tiangolo/fastapi`, `expressjs/express` for the other
  framework-gate cases; `hunt.py`'s real `run_candidate()` pipeline
  exercised against a real `django/django` clone, verifying exact-commit
  recording and that unresearched `CandidateSpec` fields render literally
  as `"NOT RESEARCHED"` rather than a silent false default.

**TESTED — 28/28 passed**, no skips (all four network-dependent clone
fixtures succeeded), no warnings, run twice for reproducibility. Command:
`cd pack/1_harvest && python3 -m pytest test_admission.py -v`.

## 8. Attach points discovered, third-party plugin evidence, plugin doc evidence, adapters

- **Attach points discovered (real, evidenced)**: exactly one, in
  `fossasia/eventyay` — a SLOT-kind point, the `pretix.plugin` setuptools
  entry-point group read at `app/eventyay/config/settings.py:384`.
  **OBSERVED**, not admitted (see §6, licence).
- **Third-party plugin evidence**: none independently verified in this
  pilot. eventyay's plugin mechanism is real and live in its own settings,
  but no specific third-party plugin package was inspected to confirm it
  actually loads through that mechanism — recorded as `NOT RESEARCHED` in
  its `CandidateSpec`, not defaulted to "no evidence found."
- **Plugin-authoring documentation**: eventyay's `doc/` tree contains
  material inherited from pretix's own docs (including a live reference to
  `docs.pretix.eu` for API auth, `settings.py:1568`) — recorded as present,
  with the caveat that it documents the inherited pretix plugin mechanism,
  not something FOSSASIA wrote fresh for Eventyay's own contributors.
- **Adapters**: none written. No candidate was admitted in this pilot, so
  no capability was harvested and no adapter code was produced. **NOT
  APPLICABLE this phase** — the `ADAPTER` vs `NATIVE` distinction is
  implemented and tested (§7) but has no real adapter instance to point to
  yet.

## 9. Remaining gaps

- **The Flask-era host/route-reader machinery (`pack/4_host/host.py`,
  `_extract_route_meta`) is unproven for Django.** Rule A now requires
  Django; nothing in this phase rewrote the host to read Django URLconfs
  instead of Flask route decorators. **NOT YET PROVEN** — stated plainly
  in the admission-rule document's own "payload question" section, not
  hidden. No app has been harvested under the new rules yet, so this gap
  has not blocked anything real — but it will, the moment a Django
  candidate is admitted and reaches `host.py --check`.
- **`ATTACH_POINTS.md`/`.json` writing is implemented and tested against a
  synthetic `harvest_form()` call (§7), but has never run against a real,
  admitted Django application** — because none has been admitted yet (§6).
  **DESIGNED and TESTED in isolation, NOT YET PROVEN end-to-end against a
  real admitted app.**
- **Library promotion mechanism target is unresolved** (§6) — a genuine
  open question, not a guess either way.
- **`check_form_godmode.py`'s coverage of Rule G** was not checked in this
  phase (the file was not found in this repository tree by search; the
  existing `RULE_REGISTER.md` note that Rules A/E/F are "in force but not
  checked by `check_form_godmode.py`" predates this session and was not
  independently re-verified here — flagged, not silently assumed current).
- **`eventyay`'s licence status remains genuinely unresolved**, not
  resolved to either "clean Apache-2.0" or "actually AGPL" — a legal
  question this pilot cannot answer and does not pretend to.

## 10. Section-24 canonical category registry

Out of scope, unchanged from the original instruction: the user's own
handoff left this path as `[PATH — fill in before sending]`, unfilled. No
work in this phase touches it, guesses at it, or assumes a location for it.
