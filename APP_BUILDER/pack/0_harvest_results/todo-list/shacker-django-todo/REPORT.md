# shacker/django-todo

category: Todo List (id 1, slug todo-list)
repository: shacker/django-todo
repository URL: https://github.com/shacker/django-todo
exact commit: 95e3a022d239ebaa8771376c838a4d36590ab9b1
licence: BSD-3-Clause
framework: django
datastore: 

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 7 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 27
  event attach points: 0
  slot attach points: 23
  data attach points: 4
defined-but-unusable points measured (not counted): 16

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 3.295836866004329
  contributors: 3.1354942159291497
  tagged_releases: 1.791759469228055
  test_suite_present: 1.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 9.2231
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Todoist
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule A datastore: needs postgresql, source says (not recorded); Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 26,
  "contributors": 22,
  "tagged_releases": 5,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "extension": 3,
  "event": 5,
  "middleware": 1,
  "entry point": 1,
  "entry points": 1,
  "extend": 2,
  "contrib": 25
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule B: source publishes no REST API documentation

## Researcher notes
Real clone inspected (commit above). BSD-3-Clause LICENSE verified verbatim ('Copyright (c) 2010, Scot Hacker, Birdhouse Arts and individual contributors'). No manage.py anywhere -- this is a reusable/pluggable Django app meant to be installed into a host project (mkdocs.yml is a bare 2-line stub, no real docs/ directory), not a standalone deployable application. No djangorestframework dependency anywhere; the one non-admin urlconf entry (ticket/add/ for external ticket filing) is a plain view, not documented API. No postgres/psycopg evidence anywhere -- test_settings.py uses sqlite3; as a pluggable app it is DB-agnostic and does not itself declare Postgres. Expected admission result: REJECTED on Rule A datastore (not recorded) and Rule B (no published API docs).
