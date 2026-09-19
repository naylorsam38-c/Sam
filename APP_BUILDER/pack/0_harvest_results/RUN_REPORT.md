# RUN_REPORT — Django/PostgreSQL + Attach-Point + Exemplar-Matched Category Harvest

Validation run: registry categories 1 (Todo List), 25 (Appointment Booking), 27 (Event Ticketing).
Production run (`--categories all`, all 70 categories) has NOT been executed — this session paused
after the validation run for review, per explicit instruction.

Generated 2026-09-19T01:59:33Z.

---

## 1. Rule document — `cat pack/rules/GOD_MODE_RULE_HARVEST_ADMISSION.md`

```
# God Mode — Harvest Admission Rule

**Status:** active. Governs every capability that enters the shelf.

**Supersedes:** the earlier proposed version of this file, which admitted repos
by framework alone and left the payload question open. Both are settled here.

**Superseding note, 2026-09-19:** Rule A was rewritten from Flask to Django,
and Rule G was added, per direct instruction ("FINAL CLAUDE CODE HANDOFF —
Django/PostgreSQL + Attach-Point Harvest Architecture"). Every capability
admitted under the previous (Flask) Rule A — Indico, Redash, CTFd, thirty
capabilities across three apps — was retired to `pack/retired/` as a direct
consequence, not because any of those harvests were found defective. See
`pack/retired/*/RETIRED.md` and `GOD_MODE/REGISTERS/CHANGE_HISTORY.md`.

**Scope.** Applies to every capability that enters the shelf, whether harvested
from an external codebase or written directly against the stack below.

It does **not** grandfather the capabilities previously produced by
`verification/gen_common.py`. Those were machine-generated, their
implementation records carry `"commit": "gen_common.py"` rather than a real
upstream commit, and they are not a parts source. They fail Rule A on
provenance and are out of scope as stock, not exempt from it.

---

## Rule A — One stack, library-wide

Every source admitted to the library runs on **Django and PostgreSQL.** No
"close enough": not Flask, not FastAPI, not Node, not Rails. A source on any
other framework is not admitted, whatever else it has going for it.

A capability may be harvested only from a codebase already built on that stack.

**Reason.** This is the rule the whole library rests on. Parts are only
interchangeable if they speak the same language underneath. Two parts harvested
from different stacks cannot coexist in one app — one wants an ORM session the
other has never heard of, one wants async the other is sync. Fixing that at
assembly time is a rewrite, and a rewrite is where invented code enters the
library.

Pick the stack once, and every part ever harvested fits every other part.
Django's signals also give every admitted app a built-in attach-point system
(see Rule G) to map against — a second, independent reason to pick it over an
otherwise-equivalent Flask app.

No exceptions for "close enough". Reject the repo.

## Rule B — Published API documentation

The source app must publish REST API documentation.

**Reason.** The capability contract is routes, methods, input fields, output
fields and error codes. If the app documents its API, that contract is already
written down and can be recorded rather than inferred. If it does not, every
contract axis is a reading of source under time pressure, which is where
defects come from.

## Rule C — Licence

Permissive only: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0.

## Rule D — Structural match

The repo must match the commercial exemplar it was chosen against, in structure
and capability set. Recorded in one sentence on the form.

## Rule E — One source per app

All capabilities in a single app come from a single source repo.

**Reason.** Rule A makes parts compatible at the stack level. Rule E keeps them
compatible at the application level — one source means one set of models, one
session model, one set of conventions. Mixing two Django apps in one build is
still mixing two designs.

Cross-app reuse of a part is governed separately, by the shelf, not by this
rule.

## Rule F — Where no exemplar exists, build the part

If no repo on the stack provides a capability, the capability is **written
directly against the stack** — Django, PostgreSQL, and the Shared Library
(`CAP-0000`).

A part written this way is a first-class shelf part. It carries the same
records, the same contract and the same approval as a harvested one. What it
does not carry is an upstream commit, so its implementation record names this
system as its origin and says so plainly.

**Reason.** Without this rule the shelf has holes it can never fill, and the
only ways to fill them are to bend Rule A or to fake a part. This rule is what
makes Rule A affordable: the stack stays uniform *because* there is a legitimate
way to fill a gap without leaving it.

Rule F is a fallback, not a shortcut. If a qualifying repo exists, harvest it.

## Rule G — Attach points, declared at admission

Every admitted source has its attach points written down at the moment of
admission, in a file named `ATTACH_POINTS.md` alongside its clone. Nothing is
admitted without it.

An attach point is a named place in an application where a feature can hook in
without editing the application's core source. There are three kinds:

- **EVENT** — the application announces something happened (e.g.
  `booking.confirmed`, `user.created`, `payment.succeeded`). Django signals
  are valid event sources.
- **SLOT** — a named place in the UI where a capability can render (e.g.
  `listing.actions`, `profile.sidebar`, `booking.actions`).
- **DATA** — a named entity a capability can access through the shared
  library contract (e.g. `bookings`, `messages`, `listings`).

For every attach point, `ATTACH_POINTS.md` records: name, kind, where it lives
in the code, source symbol where applicable, payload/data shape, evidence,
whether it is native to the source or requires an adapter, and whether it is
externally consumable.

At least `MIN_HOOKS` usable, nameable attach points must exist, backed by real
evidence — a keyword appearing in documentation is not evidence. Where a
mechanism already exists (Django signals, a plugin system, entry points,
middleware, webhooks), map it. Do not invent an attach point without evidence.

**Adapters.** Where an application does not naturally expose a required
standard attach point, a thin adapter may be written by our system. It belongs
to our architecture, never modifies the harvested application's core source,
must be explicitly recorded, and is marked `ADAPTER`, never represented as
`NATIVE`.

**Reason.** Rule A makes parts share a stack; Rule G makes them share a real,
evidenced integration surface, so a capability can declare what it needs
(`attaches_to`) without ever naming a specific application, and compatibility
becomes a real comparison (see `match_contract` in `pack/3_assembly/build.py`)
rather than an assumption.

---

## The payload question — settled for Flask, reopened for Django

A harvested part **runs as its source wrote it.** The host does not require
foreign code to be rewritten into a neutral module shape before it will run.
This remains the design intent under Rule A regardless of which single stack
is chosen.

**What was true under the Flask-era Rule A, and is not automatically true
under this one:** `4_host/host.py` was built entirely around Flask's own
serving model — `app.url_map`, `Blueprint`, `app.view_functions`,
`add_url_rule` — and `3_assembly/build.py`'s `_extract_route_meta` reads
Flask's specific route-declaration shapes (decorator form, `add_url_rule`
call form, blueprint `url_prefix`). None of that is how Django routes a
request (`urls.py`, `URLconf`, `path()`/`re_path()`, class-based views via
`.as_view()`). Rewriting the host and the route reader to run Django parts
natively is real, separate work that this rule change does not itself do —
see `4_host/host.py`'s own admission that no application is named in it,
which was proven true for Flask but has not yet been proven true, or even
attempted, for Django. Until that work happens, "a harvested part runs as its
source wrote it" is this rule's *intent* for Django, not yet a *demonstrated
fact* the way it was for Flask (see `evidence/LIVE_RUN_EVIDENCE.md` and
`evidence/TWO_MORE_APPS.md`, both retired-app evidence proving and then
stress-testing the Flask case).

Route reading, the stamp header, `bind_shelf_parts`' class-only binding
requirement — every host-layer finding recorded against the three retired
apps (see their `RETIRED.md` and `evidence/TWO_MORE_APPS.md`) was a Flask
finding. Whether the same mechanisms, or different ones, hold for Django is
unproven until a Django part is actually run through the host for real.

---

## Enforcement

Enforced by `harvest_parts.py`, **at the point code is fetched**. A source that
fails any rule is refused before a single byte is written, so nothing
downstream has to inspect it afterwards. Nothing that reaches the shelf ever
failed a rule.

| Rule | What is refused | Setting |
|---|---|---|
| A framework | not Django | `REQUIRED_FRAMEWORK` |
| A datastore | not PostgreSQL | `REQUIRED_DATASTORE`, `DATASTORE_ALIASES` |
| B | no published REST API documentation | `REQUIRE_API_DOCS` |
| C | licence not permissive | `ALLOWED_LICENCES` |
| D | no structural match to the exemplar recorded | `REQUIRE_STRUCTURAL_MATCH` |
| E | capabilities naming more than one repo | `ONE_SOURCE_PER_APP` |
| G | no usable attach points, or fewer than `MIN_HOOKS` | `REQUIRE_ATTACH_POINTS`, `MIN_HOOKS` |

All switchable in that script's config block. `ENFORCE_ADMISSION = False`
turns the lot off, which is a decision to admit code the host cannot run.

Refusal is all-or-nothing: one failed rule refuses the whole source. A
partially admitted source is a shelf with a part on it that no rule allowed.

Quality scoring (commit recency, contributors, releases, test suite,
documentation, issue closure ratio, third-party plugin evidence) ranks
otherwise-eligible candidates against each other. It never overrides a hard
gate — a high-scoring Flask app is still rejected on Rule A; a Django app with
no usable attach points is still rejected on Rule G.

Rule F needs no check. A part written against the stack is written to the
stack by definition; what it needs is an origin naming this system rather than
an upstream commit, recorded on its implementation record.

The former `check_form_godmode.py` is deleted. It inspected a filled form
after the fact; refusal now happens where the code is fetched, which is the
only place it can stop a bad part actually landing.

## Known god mode gaps this rule interacts with

Recorded, not fixed:

- `dispatch()` handles GET and POST only. A harvested REST verb 404s silently.
- `_RAW_PATH_BYPASS_RE` covers one bypass shape, so a novel raw-path read in
  harvested code can slip the static scan.
- No login rate limiting exists anywhere, so a harvested auth capability
  inherits none — including one harvested from a source that had its own.
- `_master_key()` is one local key: no rotation, no per-tenant separation, no
  external KMS.
- A multipart upload cannot be the Playwright journey target.
- **The host and the route reader are Flask-shaped code, unchanged by this
  rule.** Every Django part on the shelf, from this rule onward, is admitted
  and evidenced correctly — but running it through `host.py` the way Flask
  parts were run has not been built, attempted, or proven. See "The payload
  question", above.
```

## 2. Rule document byte identity

```
b8c49db2ebc268c7e3f41fd664644c3e73d706596f469c4caf2fe19c097315f8  rules/GOD_MODE_RULE_HARVEST_ADMISSION.md
b8c49db2ebc268c7e3f41fd664644c3e73d706596f469c4caf2fe19c097315f8  ../GOD_MODE/ACTIVE/GOD_MODE_RULE_HARVEST_ADMISSION.md
```

Identical hashes — both copies byte-identical.

## 3. `find APP_BUILDER/pack/0_harvest_results -type f | sort`

```
0_harvest_results/HARVEST_SUMMARY.md
0_harvest_results/RUN_REPORT.md
0_harvest_results/analytics-and-bi/CATEGORY_SUMMARY.md
0_harvest_results/analytics-and-bi/manjunathgouda7-django-pbi/ATTACH_POINTS.md
0_harvest_results/analytics-and-bi/manjunathgouda7-django-pbi/REPORT.md
0_harvest_results/analytics-and-bi/manjunathgouda7-django-pbi/evidence/candidate_spec.json
0_harvest_results/analytics-and-bi/manjunathgouda7-django-pbi/evidence/git_quality_metrics.json
0_harvest_results/analytics-and-bi/manjunathgouda7-django-pbi/evidence/keyword_signal_sweep.json
0_harvest_results/analytics-and-bi/marinho-django-bi/ATTACH_POINTS.md
0_harvest_results/analytics-and-bi/marinho-django-bi/REPORT.md
0_harvest_results/analytics-and-bi/marinho-django-bi/evidence/candidate_spec.json
0_harvest_results/analytics-and-bi/marinho-django-bi/evidence/git_quality_metrics.json
0_harvest_results/analytics-and-bi/marinho-django-bi/evidence/keyword_signal_sweep.json
0_harvest_results/analytics-and-bi/paxalia-paxalia-dashboard/ATTACH_POINTS.md
0_harvest_results/analytics-and-bi/paxalia-paxalia-dashboard/REPORT.md
0_harvest_results/analytics-and-bi/paxalia-paxalia-dashboard/evidence/candidate_spec.json
0_harvest_results/analytics-and-bi/paxalia-paxalia-dashboard/evidence/git_quality_metrics.json
0_harvest_results/analytics-and-bi/paxalia-paxalia-dashboard/evidence/keyword_signal_sweep.json
0_harvest_results/appointment-booking/CATEGORY_SUMMARY.md
0_harvest_results/appointment-booking/DISCOVERY.md
0_harvest_results/appointment-booking/aarongeb-health-booking-system/ATTACH_POINTS.md
0_harvest_results/appointment-booking/aarongeb-health-booking-system/FEATURE_MATCH.md
0_harvest_results/appointment-booking/aarongeb-health-booking-system/REPORT.md
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/attach_points.json
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/candidate_spec.json
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/feature_match.json
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/gates.json
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/git_quality_metrics.json
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/keyword_signal_sweep.json
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/provenance.txt
0_harvest_results/appointment-booking/aarongeb-health-booking-system/evidence/quality.json
0_harvest_results/appointment-booking/adamspd-django-appointment/ATTACH_POINTS.md
0_harvest_results/appointment-booking/adamspd-django-appointment/FEATURE_MATCH.md
0_harvest_results/appointment-booking/adamspd-django-appointment/REPORT.md
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/attach_points.json
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/candidate_spec.json
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/feature_match.json
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/gates.json
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/git_quality_metrics.json
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/keyword_signal_sweep.json
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/provenance.txt
0_harvest_results/appointment-booking/adamspd-django-appointment/evidence/quality.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/ATTACH_POINTS.md
0_harvest_results/appointment-booking/llazzaro-django-scheduler/FEATURE_MATCH.md
0_harvest_results/appointment-booking/llazzaro-django-scheduler/REPORT.md
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/attach_points.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/candidate_spec.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/feature_match.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/gates.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/git_quality_metrics.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/keyword_signal_sweep.json
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/provenance.txt
0_harvest_results/appointment-booking/llazzaro-django-scheduler/evidence/quality.json
0_harvest_results/challenge-platform/CATEGORY_SUMMARY.md
0_harvest_results/challenge-platform/angstromctf-djangoctf/ATTACH_POINTS.md
0_harvest_results/challenge-platform/angstromctf-djangoctf/REPORT.md
0_harvest_results/challenge-platform/angstromctf-djangoctf/evidence/candidate_spec.json
0_harvest_results/challenge-platform/angstromctf-djangoctf/evidence/git_quality_metrics.json
0_harvest_results/challenge-platform/angstromctf-djangoctf/evidence/keyword_signal_sweep.json
0_harvest_results/challenge-platform/pdogg-ctfmanager/ATTACH_POINTS.md
0_harvest_results/challenge-platform/pdogg-ctfmanager/REPORT.md
0_harvest_results/challenge-platform/pdogg-ctfmanager/evidence/candidate_spec.json
0_harvest_results/challenge-platform/pdogg-ctfmanager/evidence/git_quality_metrics.json
0_harvest_results/challenge-platform/pdogg-ctfmanager/evidence/keyword_signal_sweep.json
0_harvest_results/challenge-platform/sniperoj-jeopardy-platform/ATTACH_POINTS.md
0_harvest_results/challenge-platform/sniperoj-jeopardy-platform/REPORT.md
0_harvest_results/challenge-platform/sniperoj-jeopardy-platform/evidence/candidate_spec.json
0_harvest_results/challenge-platform/sniperoj-jeopardy-platform/evidence/git_quality_metrics.json
0_harvest_results/challenge-platform/sniperoj-jeopardy-platform/evidence/keyword_signal_sweep.json
0_harvest_results/challenge-platform/super1337-super1337-ctf/ATTACH_POINTS.md
0_harvest_results/challenge-platform/super1337-super1337-ctf/REPORT.md
0_harvest_results/challenge-platform/super1337-super1337-ctf/evidence/candidate_spec.json
0_harvest_results/challenge-platform/super1337-super1337-ctf/evidence/git_quality_metrics.json
0_harvest_results/challenge-platform/super1337-super1337-ctf/evidence/keyword_signal_sweep.json
0_harvest_results/event-ticketing/CATEGORY_SUMMARY.md
0_harvest_results/event-ticketing/DISCOVERY.md
0_harvest_results/event-ticketing/definitelynotanassassin-ticketmanagementsystem/ATTACH_POINTS.md
0_harvest_results/event-ticketing/definitelynotanassassin-ticketmanagementsystem/REPORT.md
0_harvest_results/event-ticketing/definitelynotanassassin-ticketmanagementsystem/evidence/candidate_spec.json
0_harvest_results/event-ticketing/definitelynotanassassin-ticketmanagementsystem/evidence/git_quality_metrics.json
0_harvest_results/event-ticketing/definitelynotanassassin-ticketmanagementsystem/evidence/keyword_signal_sweep.json
0_harvest_results/event-ticketing/fossasia-eventyay/ATTACH_POINTS.md
0_harvest_results/event-ticketing/fossasia-eventyay/FEATURE_MATCH.md
0_harvest_results/event-ticketing/fossasia-eventyay/REPORT.md
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/attach_points.json
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/candidate_spec.json
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/feature_match.json
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/gates.json
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/git_quality_metrics.json
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/keyword_signal_sweep.json
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/provenance.txt
0_harvest_results/event-ticketing/fossasia-eventyay/evidence/quality.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/ATTACH_POINTS.md
0_harvest_results/event-ticketing/iyanuashiri-meethub/FEATURE_MATCH.md
0_harvest_results/event-ticketing/iyanuashiri-meethub/REPORT.md
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/attach_points.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/candidate_spec.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/feature_match.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/gates.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/git_quality_metrics.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/keyword_signal_sweep.json
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/provenance.txt
0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/quality.json
0_harvest_results/event-ticketing/pyconsk-django-konfera/ATTACH_POINTS.md
0_harvest_results/event-ticketing/pyconsk-django-konfera/REPORT.md
0_harvest_results/event-ticketing/pyconsk-django-konfera/evidence/candidate_spec.json
0_harvest_results/event-ticketing/pyconsk-django-konfera/evidence/git_quality_metrics.json
0_harvest_results/event-ticketing/pyconsk-django-konfera/evidence/keyword_signal_sweep.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/ATTACH_POINTS.md
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/FEATURE_MATCH.md
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/REPORT.md
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/attach_points.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/candidate_spec.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/feature_match.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/gates.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/git_quality_metrics.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/keyword_signal_sweep.json
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/provenance.txt
0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/evidence/quality.json
0_harvest_results/event-ticketing/suenkler-django-tickets/ATTACH_POINTS.md
0_harvest_results/event-ticketing/suenkler-django-tickets/REPORT.md
0_harvest_results/event-ticketing/suenkler-django-tickets/evidence/candidate_spec.json
0_harvest_results/event-ticketing/suenkler-django-tickets/evidence/git_quality_metrics.json
0_harvest_results/event-ticketing/suenkler-django-tickets/evidence/keyword_signal_sweep.json
0_harvest_results/todo-list/CATEGORY_SUMMARY.md
0_harvest_results/todo-list/DISCOVERY.md
0_harvest_results/todo-list/crowdersoup-vtodo/ATTACH_POINTS.md
0_harvest_results/todo-list/crowdersoup-vtodo/FEATURE_MATCH.md
0_harvest_results/todo-list/crowdersoup-vtodo/REPORT.md
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/attach_points.json
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/candidate_spec.json
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/feature_match.json
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/gates.json
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/git_quality_metrics.json
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/keyword_signal_sweep.json
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/provenance.txt
0_harvest_results/todo-list/crowdersoup-vtodo/evidence/quality.json
0_harvest_results/todo-list/shacker-django-todo/ATTACH_POINTS.md
0_harvest_results/todo-list/shacker-django-todo/FEATURE_MATCH.md
0_harvest_results/todo-list/shacker-django-todo/REPORT.md
0_harvest_results/todo-list/shacker-django-todo/evidence/attach_points.json
0_harvest_results/todo-list/shacker-django-todo/evidence/candidate_spec.json
0_harvest_results/todo-list/shacker-django-todo/evidence/feature_match.json
0_harvest_results/todo-list/shacker-django-todo/evidence/gates.json
0_harvest_results/todo-list/shacker-django-todo/evidence/git_quality_metrics.json
0_harvest_results/todo-list/shacker-django-todo/evidence/keyword_signal_sweep.json
0_harvest_results/todo-list/shacker-django-todo/evidence/provenance.txt
0_harvest_results/todo-list/shacker-django-todo/evidence/quality.json
```

## 4. `cat HARVEST_SUMMARY.md`

```
# HARVEST_SUMMARY

## Todo List (id 1)
candidates inspected: 2
selected: ADMITTED CrowderSoup/vTodo @ 56745365951cda11f9958bc0e9e6c9941985ea78 match 0.53 vs Todoist

## Appointment Booking (id 25)
candidates inspected: 3
selected: NONE ADMITTED

## Event Ticketing (id 27)
candidates inspected: 3
selected: NONE ADMITTED

```

## 5. Library index — the harvest's section in the existing library index

Path: `APP_BUILDER/GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md` (this is the file the
repository's own governance layer already names for the library — see Section 25). Its
pre-existing content (43 canonical / 6 composed / 15 coverage-expansion apps under a
`verification/`+`OUTPUT_LIBRARY/` tree) refers to an older, unrelated system whose directories
do not exist in this checkout — a pre-existing condition reported here, not something
this harvest created or altered. This harvest appends only the clearly separate section below.

```
## Django/PostgreSQL Attach-Point Harvest — Library Index

Entries below are written only by pack/0_harvest/hunt.py's write_library_index(), one row per ADMITTED category winner (Section 25). A category recorded NONE ADMITTED gets no row.

| # | Category | Exemplar | Feature match | Repository | Commit | Licence | Attach points |
|---|----------|----------|----------------|------------|--------|---------|---------------|
| 1 | Todo List | Todoist | 0.53 | https://github.com/CrowderSoup/vTodo | 56745365951cda11f9958bc0e9e6c9941985ea78 | MIT | 58 |
```

## 6. Test command and complete output

Command:
```
cd APP_BUILDER/pack/1_harvest && python3 -m pytest test_admission.py test_registry_harvest.py -v
```

Output:
```
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /usr/local/bin/python3
cachedir: .pytest_cache
rootdir: /home/user/Sam/APP_BUILDER/pack/1_harvest
collecting ... collected 52 items

test_admission.py::TestFrameworkGate::test_django_candidate_passes_framework_gate PASSED [  1%]
test_admission.py::TestFrameworkGate::test_flask_candidate_is_rejected PASSED [  3%]
test_admission.py::TestFrameworkGate::test_fastapi_candidate_is_rejected PASSED [  5%]
test_admission.py::TestFrameworkGate::test_node_candidate_is_rejected PASSED [  7%]
test_admission.py::TestFrameworkGate::test_postgresql_remains_mandatory PASSED [  9%]
test_admission.py::TestAttachPointGate::test_keyword_only_hook_does_not_satisfy_min_hooks PASSED [ 11%]
test_admission.py::TestAttachPointGate::test_real_usable_extension_point_satisfies_requirement PASSED [ 13%]
test_admission.py::TestAttachPointGate::test_min_hooks_is_enforced PASSED [ 15%]
test_admission.py::TestAttachPointGate::test_missing_attach_points_causes_rejection PASSED [ 17%]
test_admission.py::TestAttachPointGate::test_native_vs_adapter_points_remain_distinguishable PASSED [ 19%]
test_admission.py::TestAttachPointGate::test_unrecognised_implementation_value_is_not_usable PASSED [ 21%]
test_admission.py::TestQualityScoringCannotOverrideHardGates::test_flask_high_quality_still_rejected PASSED [ 23%]
test_admission.py::TestQualityScoringCannotOverrideHardGates::test_django_no_attach_points_still_rejected PASSED [ 25%]
test_admission.py::TestApplicationSpecificCapabilityDependenciesRejected::test_capability_naming_an_application_identity_is_wrong_shape PASSED [ 26%]
test_admission.py::TestCapabilityAttachPointCompatibility::test_no_attaches_to_skips_axis PASSED [ 28%]
test_admission.py::TestCapabilityAttachPointCompatibility::test_incomplete_attach_point_coverage_is_rejected PASSED [ 30%]
test_admission.py::TestAttachPointsFileMandatory::test_atp_md_written_on_successful_harvest PASSED [ 32%]
test_admission.py::TestCapRecordSchema::test_attaches_to_field_present_and_synced PASSED [ 34%]
test_admission.py::TestRealRepoFlaskRejection::test_indico_is_really_flask_in_its_own_source PASSED [ 36%]
test_admission.py::TestRealRepoFlaskRejection::test_indico_is_rejected_under_current_rule_a PASSED [ 38%]
test_admission.py::TestRealRepoDjangoAcceptance::test_django_repo_really_declares_django PASSED [ 40%]
test_admission.py::TestRealRepoDjangoAcceptance::test_django_framework_value_passes_the_gate PASSED [ 42%]
test_admission.py::TestRealRepoFastAPIRejection::test_fastapi_repo_really_declares_fastapi PASSED [ 44%]
test_admission.py::TestRealRepoFastAPIRejection::test_fastapi_framework_value_is_rejected PASSED [ 46%]
test_admission.py::TestRealRepoNodeRejection::test_express_repo_really_declares_node PASSED [ 48%]
test_admission.py::TestRealRepoNodeRejection::test_node_framework_value_is_rejected PASSED [ 50%]
test_admission.py::TestHuntCandidatePipeline::test_exact_commit_and_provenance_recorded PASSED [ 51%]
test_admission.py::TestHuntCandidatePipeline::test_unverified_provenance_is_recorded_as_not_researched PASSED [ 53%]
test_registry_harvest.py::TestMechanicalEventDetection::test_signal_defined_but_never_sent_does_not_count PASSED [ 55%]
test_registry_harvest.py::TestMechanicalEventDetection::test_signal_with_real_send_site_counts PASSED [ 57%]
test_registry_harvest.py::TestMechanicalEventDetection::test_model_signals_excluded_by_default PASSED [ 59%]
test_registry_harvest.py::TestMechanicalEventDetection::test_model_signals_counted_when_flag_true PASSED [ 61%]
test_registry_harvest.py::TestMechanicalDataDetection::test_orphan_model_does_not_count PASSED [ 63%]
test_registry_harvest.py::TestMechanicalDataDetection::test_reachable_model_counts_as_data PASSED [ 65%]
test_registry_harvest.py::TestMechanicalDataDetection::test_abstract_base_is_not_itself_a_data_point PASSED [ 67%]
test_registry_harvest.py::TestMechanicalSlotDetection::test_block_in_rendered_template_is_a_slot PASSED [ 69%]
test_registry_harvest.py::TestMechanicalSlotDetection::test_block_in_untraced_template_is_not_usable PASSED [ 71%]
test_registry_harvest.py::TestAdapterNeverNative::test_render_never_marks_adapter_as_native PASSED [ 73%]
test_registry_harvest.py::TestExemplarFeatureLoading::test_feature_with_no_source_url_is_dropped PASSED [ 75%]
test_registry_harvest.py::TestFeatureMatchVerdicts::test_keyword_in_model_name_scores_matched_with_evidence PASSED [ 76%]
test_registry_harvest.py::TestFeatureMatchVerdicts::test_keyword_only_in_readme_scores_docs_only_weight PASSED [ 78%]
test_registry_harvest.py::TestFeatureMatchVerdicts::test_not_found_keyword_scores_zero PASSED [ 80%]
test_registry_harvest.py::TestFeatureMatchVerdicts::test_rejected_candidate_is_not_measured PASSED [ 82%]
test_registry_harvest.py::TestRanking::test_higher_quality_lower_match_does_not_win PASSED [ 84%]
test_registry_harvest.py::TestRanking::test_min_feature_match_floor_yields_none_admitted PASSED [ 86%]
test_registry_harvest.py::TestDiscoveryRecording::test_every_query_and_every_hit_recorded_kept_and_dropped PASSED [ 88%]
test_registry_harvest.py::TestRealRepoMechanicalMeasurement::test_real_clone_produces_usable_data_points_with_evidence PASSED [ 90%]
test_registry_harvest.py::TestRealRepoMechanicalMeasurement::test_real_clone_never_modified_by_measurement PASSED [ 92%]
test_registry_harvest.py::TestRegistryDriven::test_registry_has_seventy_categories_with_required_fields PASSED [ 94%]
test_registry_harvest.py::TestRegistryDriven::test_categories_subset_produces_exactly_those_folders_and_no_others PASSED [ 96%]
test_registry_harvest.py::TestRegistryDriven::test_none_admitted_category_produces_no_library_index_entry PASSED [ 98%]
test_registry_harvest.py::TestRegistryDriven::test_exemplar_names_never_appear_as_candidate_identity PASSED [100%]

======================== 52 passed in 114.13s (0:01:54) ========================
```

## 7. Harvest commands and complete stdout/stderr

Command:
```
cd APP_BUILDER/pack/0_harvest && python3 run_registry_harvest.py --categories 1,25,27
```

Output:
```
registry: /home/user/Sam/APP_BUILDER/pack/0_harvest/../CATEGORY_REGISTRY.json (70 categories)
selected: 3 categories

======================================================================
Todo List  (id 1, slug todo-list, exemplar Todoist)
======================================================================

=== Todo List :: CrowderSoup/vTodo ===
  ADMITTED  score=6.8608  feature_match=0.5333  attach_points=58  commit=56745365951c

=== Todo List :: shacker/django-todo ===
  REJECTED  score=9.2231  feature_match=None  attach_points=27  commit=95e3a022d239
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

======================================================================
Appointment Booking  (id 25, slug appointment-booking, exemplar Calendly)
======================================================================

=== Appointment Booking :: adamspd/django-appointment ===
  REJECTED  score=11.7679  feature_match=None  attach_points=11  commit=55706a2bb8da
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

=== Appointment Booking :: aaronGeb/health_booking_system ===
  REJECTED  score=1.0986  feature_match=None  attach_points=1  commit=be523259842a
    - Rule B: source publishes no REST API documentation

=== Appointment Booking :: llazzaro/django-scheduler ===
  REJECTED  score=8.8328  feature_match=None  attach_points=27  commit=ab3618013b3d
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

======================================================================
Event Ticketing  (id 27, slug event-ticketing, exemplar Eventbrite / Ticketmaster)
======================================================================

=== Event Ticketing :: iyanuashiri/meethub ===
  REJECTED  score=3.3026  feature_match=None  attach_points=28  commit=500925d0962f
    - Rule B: source publishes no REST API documentation

=== Event Ticketing :: SalahEddine-Ghannouch/GetTicket_Events_Django ===
  REJECTED  score=3.7842  feature_match=None  attach_points=148  commit=30ff0da00881
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

=== Event Ticketing :: fossasia/eventyay ===
  REJECTED  score=15.4738  feature_match=None  attach_points=1329  commit=786bd095c63b
    - Rule C licence: UNRESOLVED -- see researcher_notes is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0)
    - Rule B: source publishes no REST API documentation

library index updated: /home/user/Sam/APP_BUILDER/GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md (1 new entry, 1 total rows in the harvest section)


=== RUN COMPLETE ===
Todo List: ADMITTED CrowderSoup/vTodo @ 56745365951c match 0.53  (2 candidates inspected)
Appointment Booking: NONE ADMITTED  (3 candidates inspected)
Event Ticketing: NONE ADMITTED  (3 candidates inspected)
```

## 8. Per-ADMITTED-winner content

One winner this run: **CrowderSoup/vTodo** (Todo List, id 1).

### 8.1 REPORT.md

```
# CrowderSoup/vTodo

category: Todo List (id 1, slug todo-list)
repository: CrowderSoup/vTodo
repository URL: https://github.com/CrowderSoup/vTodo
exact commit: 56745365951cda11f9958bc0e9e6c9941985ea78
licence: MIT
framework: django
datastore: postgresql

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 9 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 58
  event attach points: 0
  slot attach points: 43
  data attach points: 15
defined-but-unusable points measured (not counted): 63

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 4.762173934797756
  contributors: 1.0986122886681096
  tagged_releases: 0.0
  test_suite_present: 1.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 6.8608
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Todoist
features checked: 15  matched(code): 8  docs-only: 0  not found: 7
feature_match: 0.53

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 116,
  "contributors": 2,
  "tagged_releases": 0,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "extension": 1,
  "signal": 4,
  "signals": 4,
  "event": 5,
  "middleware": 3,
  "extend": 2,
  "contrib": 17,
  "django.dispatch": 2,
  "receiver": 2
}

## Admission result
**ADMITTED**

## Researcher notes
Real clone inspected directly (commit above). Django>=6.0, manage.py present -- a real deployable project, not a pluggable library. psycopg2-binary>=2.9 in pyproject.toml; config/settings.py reads DATABASE_URL via django-environ, defaulting to sqlite only when unset -- README documents PostgreSQL under Requirements and the Docker/production path is Postgres-driven. MIT LICENSE file present and verified verbatim. Very active: last commit 2026-09-18 (day before this run). No CONTRIBUTING.md / plugin-authoring docs found; no third-party dependents found via WebSearch.
```

### 8.2 ATTACH_POINTS.md

```
# Attach Points

Application: CrowderSoup/vTodo
Repository: CrowderSoup/vTodo
Commit: 
Framework: django
Datastore: postgresql

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|
| CrowderSoup__vTodo.login.body_class | templates/login.html | apps/accounts/views.py | NATIVE | templates/login.html:5, apps/accounts/views.py |
| CrowderSoup__vTodo.login.title | templates/login.html | apps/accounts/views.py | NATIVE | templates/login.html:6, apps/accounts/views.py |
| CrowderSoup__vTodo.login.content | templates/login.html | apps/accounts/views.py | NATIVE | templates/login.html:8, apps/accounts/views.py |
| CrowderSoup__vTodo.base.title | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:7 |
| CrowderSoup__vTodo.base.body_class | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:26 |
| CrowderSoup__vTodo.base.content | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:118 |
| CrowderSoup__vTodo.base.extra_scripts | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:121 |
| CrowderSoup__vTodo.invite_accept.body_class | templates/teams/invite_accept.html | apps/teams/views.py | NATIVE | templates/teams/invite_accept.html:3, apps/teams/views.py |
| CrowderSoup__vTodo.invite_accept.title | templates/teams/invite_accept.html | apps/teams/views.py | NATIVE | templates/teams/invite_accept.html:4, apps/teams/views.py |
| CrowderSoup__vTodo.invite_accept.content | templates/teams/invite_accept.html | apps/teams/views.py | NATIVE | templates/teams/invite_accept.html:6, apps/teams/views.py |
| CrowderSoup__vTodo.general.settings_title | templates/users/settings/general.html | apps/users/views.py | NATIVE | templates/users/settings/general.html:3, apps/users/views.py |
| CrowderSoup__vTodo.general.settings_content | templates/users/settings/general.html | apps/users/views.py | NATIVE | templates/users/settings/general.html:5, apps/users/views.py |
| CrowderSoup__vTodo.board.settings_title | templates/users/settings/board.html | apps/users/views.py | NATIVE | templates/users/settings/board.html:3, apps/users/views.py |
| CrowderSoup__vTodo.board.settings_header | templates/users/settings/board.html | apps/users/views.py | NATIVE | templates/users/settings/board.html:5, apps/users/views.py |
| CrowderSoup__vTodo.board.settings_content | templates/users/settings/board.html | apps/users/views.py | NATIVE | templates/users/settings/board.html:15, apps/users/views.py |
| CrowderSoup__vTodo.calendar.settings_title | templates/users/settings/calendar.html | apps/users/views.py | NATIVE | templates/users/settings/calendar.html:3, apps/users/views.py |
| CrowderSoup__vTodo.calendar.settings_header | templates/users/settings/calendar.html | apps/users/views.py | NATIVE | templates/users/settings/calendar.html:5, apps/users/views.py |
| CrowderSoup__vTodo.calendar.settings_content | templates/users/settings/calendar.html | apps/users/views.py | NATIVE | templates/users/settings/calendar.html:15, apps/users/views.py |
| CrowderSoup__vTodo.teams.settings_title | templates/users/settings/teams.html | apps/users/views.py | NATIVE | templates/users/settings/teams.html:3, apps/users/views.py |
| CrowderSoup__vTodo.teams.settings_header | templates/users/settings/teams.html | apps/users/views.py | NATIVE | templates/users/settings/teams.html:5, apps/users/views.py |
| CrowderSoup__vTodo.teams.settings_content | templates/users/settings/teams.html | apps/users/views.py | NATIVE | templates/users/settings/teams.html:15, apps/users/views.py |
| CrowderSoup__vTodo.api.settings_title | templates/users/settings/api.html | apps/users/views.py | NATIVE | templates/users/settings/api.html:3, apps/users/views.py |
| CrowderSoup__vTodo.api.settings_header | templates/users/settings/api.html | apps/users/views.py | NATIVE | templates/users/settings/api.html:5, apps/users/views.py |
| CrowderSoup__vTodo.api.settings_content | templates/users/settings/api.html | apps/users/views.py | NATIVE | templates/users/settings/api.html:15, apps/users/views.py |
| CrowderSoup__vTodo._base.body_class | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:3 |
| CrowderSoup__vTodo._base.title | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:4 |
| CrowderSoup__vTodo._base.settings_title | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:4 |
| CrowderSoup__vTodo._base.content | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:6 |
| CrowderSoup__vTodo._base.settings_header | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:8 |
| CrowderSoup__vTodo._base.settings_content | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:35 |
| CrowderSoup__vTodo.dashboard.admin_title | templates/siteadmin/dashboard.html | apps/siteadmin/views.py | NATIVE | templates/siteadmin/dashboard.html:3, apps/siteadmin/views.py |
| CrowderSoup__vTodo.dashboard.admin_content | templates/siteadmin/dashboard.html | apps/siteadmin/views.py | NATIVE | templates/siteadmin/dashboard.html:5, apps/siteadmin/views.py |
| CrowderSoup__vTodo._base.body_class | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:3 |
| CrowderSoup__vTodo._base.title | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:4 |
| CrowderSoup__vTodo._base.admin_title | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:4 |
| CrowderSoup__vTodo._base.content | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:6 |
| CrowderSoup__vTodo._base.admin_content | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:20 |
| CrowderSoup__vTodo.board.body_class | templates/boards/board.html | apps/users/views.py | NATIVE | templates/boards/board.html:3, apps/users/views.py |
| CrowderSoup__vTodo.board.title | templates/boards/board.html | apps/users/views.py | NATIVE | templates/boards/board.html:4, apps/users/views.py |
| CrowderSoup__vTodo.board.content | templates/boards/board.html | apps/users/views.py | NATIVE | templates/boards/board.html:6, apps/users/views.py |
| CrowderSoup__vTodo.calendar.body_class | templates/calendar/calendar.html | apps/users/views.py | NATIVE | templates/calendar/calendar.html:3, apps/users/views.py |
| CrowderSoup__vTodo.calendar.title | templates/calendar/calendar.html | apps/users/views.py | NATIVE | templates/calendar/calendar.html:4, apps/users/views.py |
| CrowderSoup__vTodo.calendar.content | templates/calendar/calendar.html | apps/users/views.py | NATIVE | templates/calendar/calendar.html:6, apps/users/views.py |

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| teams.Team | Team | READ, WRITE | name, created_at | apps/teams/models.py:8, apps/teams/views.py (write path) |
| teams.TeamMembership | TeamMembership | READ, WRITE | team, user, role, joined_at | apps/teams/models.py:16, apps/teams/views.py (write path) |
| teams.TeamInvite | TeamInvite | READ | team, email, token, invited_by, created_at, expires_at, accepted_at | apps/teams/models.py:37, apps/teams/admin.py (referenced) |
| emailauth.EmailIdentity | EmailIdentity | READ, WRITE | user, email, verified, created_at | apps/emailauth/models.py:5, apps/teams/tests/test_views.py (write path) |
| tasks.TaskStatus | TaskStatus | READ, WRITE | user, team, name, slug, order, color, is_done | apps/tasks/models.py:17, apps/teams/tests/test_views.py (write path) |
| tasks.Task | Task | READ, WRITE | user, team, assignee, title, notes, status, previous_status, order, due_date, due_time, duration_minutes, tags, is_archived, recurrence_days, recurrence_from, created_at, updated_at, completed_at | apps/tasks/models.py:71, apps/teams/tests/test_views.py (write path) |
| tasks.TaskComment | TaskComment | READ, WRITE | task, body, created_at | apps/tasks/models.py:157, apps/boards/views.py (write path) |
| tasks.TaskActivity | TaskActivity | READ, WRITE | task, actor, field, old_value, new_value, created_at | apps/tasks/models.py:169, apps/teams/views.py (write path) |
| siteadmin.SiteSettings | SiteSettings | READ, WRITE | signup_mode | apps/siteadmin/models.py:8, apps/siteadmin/tests/test_selectors.py (write path) |
| siteadmin.SiteInvite | SiteInvite | READ | email, token, invited_by, created_at, expires_at, accepted_at | apps/siteadmin/models.py:32, apps/siteadmin/selectors.py (referenced) |
| integrations.ExternalLink | ExternalLink | READ, WRITE | task, provider, external_id, external_url, synced_at, metadata | apps/integrations/models.py:7, apps/integrations/google_calendar/sync.py (write path) |
| integrations.GoogleCalendarConnection | GoogleCalendarConnection | READ, WRITE | user, calendar_id, refresh_token_encrypted, is_active, created_at, last_synced_at, last_sync_error | apps/integrations/models.py:37, apps/users/tests/test_views.py (write path) |
| boards.Board | Board | READ, WRITE | user, team, name, created_at | apps/boards/models.py:5, apps/teams/views.py (write path) |
| boards.Column | Column | READ, WRITE | board, label, filter_config, order, color | apps/boards/models.py:50, apps/teams/tests/test_views.py (write path) |
| boards.SavedFilter | SavedFilter | READ, WRITE | board, name, filter_config, created_at | apps/boards/models.py:77, apps/boards/tests/test_calendar_views.py (write path) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
```

### 8.3 FEATURE_MATCH.md

```
# FEATURE_MATCH — CrowderSoup/vTodo

exemplar: Todoist
features checked: 15
features matched (CODE): 8
docs-only: 0
not found: 7
feature_match: 0.53

| Feature | Verdict | Keyword | Evidence |
|---------|---------|---------|----------|
| recurring tasks | MATCHED | recurrence | apps/tasks/models.py:129 ('spawn_recurrence') |
| labels | MATCHED | label | apps/users/views.py:88 ('_saved_filters_with_labels') |
| custom filters | MATCHED | filter | apps/teams/admin.py:21 ('list_filter') |
| reminders | NOT_FOUND | - | - |
| sub-tasks | NOT_FOUND | - | - |
| sections | NOT_FOUND | - | - |
| karma productivity tracking | NOT_FOUND | - | - |
| shared projects | MATCHED | share | apps/teams/tests/test_views.py:40 ('test_team_create_creates_shared_team_board') |
| task assignment | MATCHED | assign | apps/teams/tests/test_views.py:227 ('test_member_remove_unassigns_the_removed_user_from_team_tasks') |
| task priorities | NOT_FOUND | - | - |
| board (kanban) view | MATCHED | board | config/urls.py:13 ('board/') |
| project templates | NOT_FOUND | - | - |
| natural language quick add | NOT_FOUND | - | - |
| calendar integration | MATCHED | calendar | config/urls.py:14 ('calendar/') |
| task comments and file attachments | MATCHED | comment | apps/tasks/models.py:155 ('TaskComment') |
```

## 9. EXEMPLAR_FEATURES.json entry used for this winner's category (id 1, Todo List)

```json
{
  "id": 1,
  "category": "Todo List",
  "exemplar": "Todoist",
  "secondary_exemplar": null,
  "features": [
    {
      "name": "recurring tasks",
      "keywords": [
        "recurring",
        "recurrence",
        "repeat",
        "rrule",
        "due date"
      ],
      "source_url": "https://www.todoist.com/help/todoist/features/introduction-to-recurring-dates-YUYVJJAV",
      "retrieved": "2026-09-19"
    },
    {
      "name": "labels",
      "keywords": [
        "label",
        "tag",
        "@label",
        "categorize"
      ],
      "source_url": "https://www.todoist.com/help/categories/features/filters-and-labels",
      "retrieved": "2026-09-19"
    },
    {
      "name": "custom filters",
      "keywords": [
        "filter",
        "query",
        "saved search",
        "syntax"
      ],
      "source_url": "https://www.todoist.com/help/todoist/features/introduction-to-filters-V98wIH",
      "retrieved": "2026-09-19"
    },
    {
      "name": "reminders",
      "keywords": [
        "reminder",
        "notification",
        "alert",
        "due time"
      ],
      "source_url": "https://www.todoist.com/help/articles/introduction-to-reminders-9PezfU",
      "retrieved": "2026-09-19"
    },
    {
      "name": "sub-tasks",
      "keywords": [
        "subtask",
        "sub-task",
        "parent task",
        "indent",
        "breakdown"
      ],
      "source_url": "https://www.todoist.com/help/todoist/features/use-sub-tasks-in-todoist-kMamDo",
      "retrieved": "2026-09-19"
    },
    {
      "name": "sections",
      "keywords": [
        "section",
        "group tasks",
        "project phase",
        "organize"
      ],
      "source_url": "https://www.todoist.com/help/articles/introduction-to-sections-rOrK0aEn",
      "retrieved": "2026-09-19"
    },
    {
      "name": "karma productivity tracking",
      "keywords": [
        "karma",
        "points",
        "streak",
        "productivity",
        "gamification"
      ],
      "source_url": "https://www.todoist.com/karma",
      "retrieved": "2026-09-19"
    },
    {
      "name": "shared projects",
      "keywords": [
        "share",
        "collaborator",
        "invite",
        "team project"
      ],
      "source_url": "https://www.todoist.com/help/articles/collaborate-with-friends-or-family-in-todoist-tzkGUy",
      "retrieved": "2026-09-19"
    },
    {
      "name": "task assignment",
      "keywords": [
        "assign",
        "assignee",
        "responsible",
        "delegate"
      ],
      "source_url": "https://www.todoist.com/help/articles/manage-team-tasks-in-todoist-S99543QzY",
      "retrieved": "2026-09-19"
    },
    {
      "name": "task priorities",
      "keywords": [
        "priority",
        "p1",
        "p2",
        "urgency"
      ],
      "source_url": "https://www.todoist.com/help/articles/introduction-to-priorities-Wy82Jp",
      "retrieved": "2026-09-19"
    },
    {
      "name": "board (kanban) view",
      "keywords": [
        "board",
        "kanban",
        "column",
        "drag and drop"
      ],
      "source_url": "https://www.todoist.com/inspiration/kanban-board",
      "retrieved": "2026-09-19"
    },
    {
      "name": "project templates",
      "keywords": [
        "template",
        "preset",
        "copy project",
        "workflow"
      ],
      "source_url": "https://www.todoist.com/help/articles/introduction-to-templates-in-todoist-uofJ8i40M",
      "retrieved": "2026-09-19"
    },
    {
      "name": "natural language quick add",
      "keywords": [
        "quick add",
        "natural language",
        "parse date",
        "nlp"
      ],
      "source_url": "https://www.todoist.com/help/articles/use-task-quick-add-in-todoist-va4Lhpzz",
      "retrieved": "2026-09-19"
    },
    {
      "name": "calendar integration",
      "keywords": [
        "calendar",
        "sync",
        "google calendar",
        "outlook",
        "ical"
      ],
      "source_url": "https://www.todoist.com/help/todoist/integrations/use-the-calendar-integration-rCqwLCt3G",
      "retrieved": "2026-09-19"
    },
    {
      "name": "task comments and file attachments",
      "keywords": [
        "comment",
        "attachment",
        "file upload",
        "discussion"
      ],
      "source_url": "https://www.todoist.com/help/articles/introduction-to-comments-and-file-uploads-CwiA50",
      "retrieved": "2026-09-19"
    }
  ]
}
```

## 10. CATEGORY_SUMMARY.md for all three validation categories

### todo-list
```
# CATEGORY_SUMMARY — Todo List

category: Todo List (id 1, slug todo-list)
exemplar: Todoist
candidates inspected: 2
candidates passing hard gates (ADMITTED): 1
candidates rejected: 1

## Rankings (eligible candidates only -- feature match first, quality score tiebreak)
  feature_match=0.53  quality=6.86  CrowderSoup/vTodo  (56745365951cda11f9958bc0e9e6c9941985ea78)

## Rejected, with reasons
  shacker/django-todo:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

## Selected candidate
**CrowderSoup/vTodo** @ 56745365951cda11f9958bc0e9e6c9941985ea78  (feature_match 0.53 vs Todoist, quality 6.86)
```

### appointment-booking
```
# CATEGORY_SUMMARY — Appointment Booking

category: Appointment Booking (id 25, slug appointment-booking)
exemplar: Calendly
candidates inspected: 3
candidates passing hard gates (ADMITTED): 0
candidates rejected: 3

## Rankings (eligible candidates only -- feature match first, quality score tiebreak)

## Rejected, with reasons
  adamspd/django-appointment:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation
  aaronGeb/health_booking_system:
    - Rule B: source publishes no REST API documentation
  llazzaro/django-scheduler:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

## Selected candidate
**NONE ADMITTED**

Reason: every inspected candidate failed at least one hard admission rule -- see each candidate's own REPORT.md for which
```

### event-ticketing
```
# CATEGORY_SUMMARY — Event Ticketing

category: Event Ticketing (id 27, slug event-ticketing)
exemplar: Eventbrite / Ticketmaster

This category folder holds evidence from two runs: the pre-registry
three-category pilot (`iyanuashiri/meethub`, `fossasia/eventyay`,
`pyconsk/django-konfera`, `suenkler/django-tickets`,
`DefinitelyNotAnAssassin/TicketManagementSystem` -- same real-world domain,
run before CATEGORY_REGISTRY.json/exemplar feature matching existed), and
this registry-driven validation run (`iyanuashiri/meethub` re-verified at
the same commit, `fossasia/eventyay` re-recorded, plus newly discovered
`SalahEddine-Ghannouch/GetTicket_Events_Django`). All candidates from both
runs are kept per Section 11/24 ("do not discard inspected candidates").

candidates inspected (this run): 3
candidates inspected (pre-registry pilot, same category domain, kept above): 5
candidates passing hard gates (ADMITTED), either run: 0
candidates rejected, either run: 6 distinct repositories (meethub and
eventyay appear in both runs; not double-counted)

## Rankings (eligible candidates only -- feature match first, quality score tiebreak)

(none -- no candidate from either run passed the hard gates)

## Rejected, with reasons (this run)
  iyanuashiri/meethub:
    - Rule B: source publishes no REST API documentation
  SalahEddine-Ghannouch/GetTicket_Events_Django:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation
  fossasia/eventyay:
    - Rule C licence: UNRESOLVED -- see researcher_notes is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0)
    - Rule B: source publishes no REST API documentation

## Rejected, with reasons (pre-registry pilot, kept for the complete record)
  DefinitelyNotAnAssassin/TicketManagementSystem:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule C licence: (not recorded) is not permissive
  pyconsk/django-konfera:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation
  suenkler/django-tickets:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

## Selected candidate
**NONE ADMITTED**

Reason: every inspected candidate across both runs failed at least one hard admission rule -- see each candidate's own REPORT.md for which
```


## 11. `git status --porcelain` and `git log --oneline -30`

(captured after the recovery in Section 12's "mistake made and corrected" note, before this
report's own commit)

```
 M APP_BUILDER/GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md
 M APP_BUILDER/pack/0_harvest/hunt.py
 M APP_BUILDER/pack/0_harvest/run_three_category_pilot.py
 M APP_BUILDER/pack/0_harvest_results/HARVEST_SUMMARY.md
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/CATEGORY_SUMMARY.md
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/ATTACH_POINTS.md
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/REPORT.md
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/evidence/candidate_spec.json
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/ATTACH_POINTS.md
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/REPORT.md
 M APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/candidate_spec.json
 M APP_BUILDER/pack/1_harvest/harvest_parts.py
 M APP_BUILDER/pack/1_harvest/test_admission.py
?? APP_BUILDER/pack/0_harvest/candidates/
?? APP_BUILDER/pack/0_harvest/discover.py
?? APP_BUILDER/pack/0_harvest/run_registry_harvest.py
?? APP_BUILDER/pack/0_harvest_results/RUN_REPORT.md
?? APP_BUILDER/pack/0_harvest_results/appointment-booking/
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/DISCOVERY.md
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/FEATURE_MATCH.md
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/evidence/attach_points.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/evidence/feature_match.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/evidence/gates.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/evidence/provenance.txt
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/fossasia-eventyay/evidence/quality.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/FEATURE_MATCH.md
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/attach_points.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/feature_match.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/gates.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/provenance.txt
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/iyanuashiri-meethub/evidence/quality.json
?? APP_BUILDER/pack/0_harvest_results/event-ticketing/salaheddine-ghannouch-getticket-events-django/
?? APP_BUILDER/pack/0_harvest_results/todo-list/
?? APP_BUILDER/pack/1_harvest/attach_points.py
?? APP_BUILDER/pack/1_harvest/exemplar_match.py
?? APP_BUILDER/pack/1_harvest/test_registry_harvest.py
?? APP_BUILDER/pack/CATEGORY_REGISTRY.json
?? APP_BUILDER/pack/EXEMPLAR_FEATURES.json
```

```
e5b1360 Final report for the Django/attach-point architecture phase; register updates
6f9e9c4 Run the three-category validation pilot: event ticketing, analytics/BI, challenge platform
b7524da Add Section 20 admission/attach-point test suite (28 tests, all passing)
a0726b8 Extend capability schema with attaches_to; match_contract gets a 13th axis
407f834 Add pack/0_harvest/hunt.py: candidate discovery, evidence, scoring, admission
30f2d02 harvest_parts.py: Django admission + Rule G attach-point enforcement
1ea4a06 Rewrite Rule A to Django+PostgreSQL, add Rule G, bring complete source of all three retired apps into the repo
033abd7 Retire Indico, Redash, and CTFd to pack/retired/ (Rule A: Django, not Flask)
09ea091 Complete both apps' emptied-part proofs, chain runs, and Playwright evidence
eed9158 Harvest Redash and CTFd, run host/chain, capture emptied-part proof for CTFd
45f85a3 Add APP_BUILDER pack: existing shelf, harvest/host/chain machinery, and spec for harvesting Redash and CTFd
8da67a5 Initial commit
```

## 12. Final classification

### IMPLEMENTED
- Rule A (Django/PostgreSQL, library-wide) and Rule G (attach points, declared at admission) — pre-existing, unchanged this run beyond adding MIN_EVENTS/MIN_SLOTS/MIN_DATA/REQUIRE_MODEL_SIGNALS_COUNT to the CONFIG block and per-kind checks to `check_admission()` (`APP_BUILDER/pack/1_harvest/harvest_parts.py`).
- Mechanical attach-point measurement (Section 33) — `APP_BUILDER/pack/1_harvest/attach_points.py`: real AST parsing for Django `Signal()` definitions + `.send()`/`.send_robust()` sites, model discovery + reachability, template `{% block %}` / dynamic `{% include %}` / hook-named inclusion tags / menu-registry detection, extension-system evidence (entry_points, `AppConfig.ready()`, pluggy/stevedore, PLUGINS/EXTENSIONS/HOOKS settings, plugin-authoring docs).
- Exemplar feature matching (Section 26.2) — `APP_BUILDER/pack/1_harvest/exemplar_match.py`: MATCHED/DOCS_ONLY/NOT_FOUND verdicts against real code identifiers and doc headings, `feature_match` scoring, `EXEMPLAR_FEATURES.json` loader that drops any feature lacking a real `source_url`.
- Canonical category registry — `APP_BUILDER/pack/CATEGORY_REGISTRY.json` (supplied, placed, 70 categories).
- `EXEMPLAR_FEATURES.json` — `APP_BUILDER/pack/EXEMPLAR_FEATURES.json`, populated for the 3 validation categories only (41 features, every one carrying a real `source_url` found via live WebSearch this session — see Section 9 above for category id 1's entry verbatim). The remaining 67 categories are NOT YET RESEARCHED, recorded as such in the file's own top-level note, not silently absent.
- PROVENANCE gate (Section 32) — `git status --porcelain` checked for real after every inspection step in `hunt.run_candidate()`; a dirty clone forces REJECTED.
- Registry-driven orchestration — `APP_BUILDER/pack/0_harvest/run_registry_harvest.py` (`--categories all|ids|slugs`, `--dry-run`), `APP_BUILDER/pack/0_harvest/discover.py` (DISCOVERY.md writer, every query and every returned repo recorded, kept or filtered).
- Library index registration — `hunt.write_library_index()`, appending to the pre-existing `APP_LIBRARY_MANIFEST.md` under a new, clearly separated section; never touching its older, unrelated content.
- Quality scoring rewritten to Section 34's weighted `log1p` formula with configurable `W_*` weights (`hunt.quality_score()`).
- A real performance fix in the reachability scan (file-content cache instead of re-reading every file per model/registry candidate) — found and fixed during this run, not left as a known slowdown.
- A real bug fix in `git_quality_metrics()` (`git fetch --unshallow` was called unconditionally against an already-full clone, silently zeroing commit/contributor/tag counts for every candidate) — found and fixed during this run.

### TESTED
- 52 tests, `python3 -m pytest test_admission.py test_registry_harvest.py` — all pass (Section 6 above has the full, real output). 28 pre-existing (Section 20) + 24 new (Section 36): mechanical EVENT/DATA/SLOT detection against real fixture files (signal-defined-not-sent, orphan model, untraced template block, abstract-base exclusion, model-signal exclusion/inclusion under the config flag), ADAPTER-never-NATIVE rendering, `EXEMPLAR_FEATURES.json`'s no-`source_url` filter, MATCHED/DOCS_ONLY/NOT_FOUND verdicts against real files, ranking (feature match first, quality tiebreak), `MIN_FEATURE_MATCH` floor, discovery recording, registry structure (70 categories with required fields), `--categories` subset scoping, no-library-entry-for-NONE-ADMITTED (structural check against the real orchestrator source), no-exemplar-identity-in-candidate-files (real file scan), and two real-clone tests (mechanical measurement produces evidenced points; harvesting never modifies the clone).
- The real 3-category validation harvest itself (Section 7's captured output) — real clones, real gates, real admission/rejection, real feature-match scoring.

### A mistake made and corrected during this run
While re-running the validation harvest for a clean second pass (after
fixing the library-index path), this session ran `rm -rf` on the
`event-ticketing/` results folder to force a clean re-run. That folder was
not new: it already held real evidence from the pre-registry three-category
pilot (`pyconsk/django-konfera`, `suenkler/django-tickets`,
`DefinitelyNotAnAssassin/TicketManagementSystem`), because the pilot's own
ad-hoc slug for "event ticketing" collides with the canonical registry's
slug for category id 27. The `rm -rf` deleted those three candidates'
evidence. This was caught before committing: `git status --porcelain`
showed the deletions, all three were restored verbatim with
`git checkout HEAD --`, and `event-ticketing/CATEGORY_SUMMARY.md` was
hand-corrected to record all candidates from both runs (Section 10 above
shows the corrected file). Recorded here because it happened, not because
it changed any admission outcome (all six event-ticketing candidates
remain REJECTED either way).

### OBSERVED
- `CrowderSoup/vTodo` ADMITTED for Todo List (id 1): commit `56745365951cda11f9958bc0e9e6c9941985ea78`, MIT, 58 usable attach points (0 EVENT / 43 SLOT / 15 DATA), feature_match 0.53 vs Todoist — see `0_harvest_results/todo-list/crowdersoup-vtodo/REPORT.md`, `ATTACH_POINTS.md`, `FEATURE_MATCH.md`, `evidence/*.json` (Section 8 above).
- Appointment Booking (id 25) and Event Ticketing (id 27): NONE ADMITTED, every real candidate rejected on stated, evidenced grounds (mostly Rule A datastore and Rule B API docs) — see `0_harvest_results/appointment-booking/CATEGORY_SUMMARY.md` and `0_harvest_results/event-ticketing/CATEGORY_SUMMARY.md` (Section 10 above), and each candidate's own `REPORT.md`.
- `fossasia/eventyay`'s Apache/AGPL licence-provenance conflict (re-recorded from the pre-registry pilot, not re-cloned this pass — see `candidates/event-ticketing.py`'s module docstring for why) — `0_harvest_results/event-ticketing/fossasia-eventyay/REPORT.md`.
- `APP_LIBRARY_MANIFEST.md`'s pre-existing content is orphaned: it names 64 app slugs across three tiers under `verification/` and `OUTPUT_LIBRARY/` directories that do not exist anywhere in this checkout — observed via direct filesystem check, reported per Section 24's instruction to report rather than merge/delete another category/index list found elsewhere. This is a pre-existing condition, not something this harvest run created.
- Rule document byte identity: both copies confirmed identical (Section 2 above, sha256).
- `pack/retired/{challenge-platform,data-dashboard,event-ticketing}/` (Indico/Redash/CTFd under their pre-registry slugs) confirmed still present, still carrying `RETIRED.md` + full `complete_source/` clones, and not listed as ADMITTED anywhere in this run's own output.

### DESIGNED, NOT YET PROVEN
- The full 70-category production harvest (`--categories all`) — the orchestrator and every gate it depends on are implemented and tested against 3 real categories, but running it end-to-end across all 70 has not been attempted this session (paused for review, per explicit instruction after the validation run).
- `EXEMPLAR_FEATURES.json` entries for the other 67 registry categories — the loader/matcher is proven against the 3 populated entries; the remaining categories will score `feature_match: NOT MEASURED (no exemplar feature entry yet)` until researched and added.
- Real GitHub-API-backed scoring (issue closure ratio, third-party plugin counts via GitHub code search) — deliberately not built. This session's GitHub access is scoped to `naylorsam38-c/Sam` only (per the environment's own repository-scope policy) and the system prompt directs all GitHub interaction through the scoped MCP tools, so `issue_closure_ratio` stays 0/stated-gap and third-party-plugin evidence stays researcher-supplied via WebSearch, exactly as the pre-existing `hunt.py` docstring already documented for the same reason before this session began.
- Attach-point coverage of a real ADMITTED Django capability flowing all the way through `match_contract()`'s `attaches_to` axis and an actual assembled app via `build.py`/`host.py` — `attaches_to` is proven by Tier-1 synthetic unit tests only; no capability has yet been harvested from vTodo into `pack/shelf/` and run through assembly/hosting. `host.py`/`build.py`'s Flask-shaped route-reading (noted as an open gap in the rule document itself) has not been re-examined this session.
