# llazzaro/django-scheduler

category: Appointment Booking (id 25, slug appointment-booking)
repository: llazzaro/django-scheduler
repository URL: https://github.com/llazzaro/django-scheduler
exact commit: ab3618013b3de2f194e3d2898653bcf88d6ec163
licence: BSD-3-Clause
framework: django
datastore: 

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 7 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 27
  event attach points: 0
  slot attach points: 21
  data attach points: 6
defined-but-unusable points measured (not counted): 29

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 0.0
  contributors: 4.574710978503383
  tagged_releases: 3.258096538021482
  test_suite_present: 1.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 8.8328
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Calendly
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule A datastore: needs postgresql, source says (not recorded); Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 96,
  "tagged_releases": 25,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "extension": 1,
  "hook": 1,
  "hooks": 1,
  "event": 39,
  "middleware": 1,
  "extend": 2,
  "contrib": 9
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule B: source publishes no REST API documentation

## Researcher notes
Real clone inspected (commit above). BSD-3-Clause LICENSE.txt verified verbatim ('Copyright (c) 2008-2017, Tony Hauber'). No manage.py anywhere -- a reusable pluggable Django app (ships only tests/settings.py for its own suite), not a standalone deployable application. schedule/urls.py exposes three plain JsonResponse endpoints used internally by a JS calendar widget (/api/occurrences, /api/move_or_resize/, /api/select_create/) -- no docstrings, no Swagger/OpenAPI/DRF, docs/views.txt does not document them; does not count as Rule B evidence. No postgres/psycopg evidence -- tests/settings.py uses sqlite3 in-memory; DB-agnostic pluggable app. Expected admission result: REJECTED on Rule A datastore (not recorded), Rule B (no published API docs), and Rule D (structural mismatch to the Calendly exemplar, recorded honestly above rather than the gate's mere non-empty check).
