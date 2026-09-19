# SalahEddine-Ghannouch/GetTicket_Events_Django

category: Event Ticketing (id 27, slug event-ticketing)
repository: SalahEddine-Ghannouch/GetTicket_Events_Django
repository URL: https://github.com/SalahEddine-Ghannouch/GetTicket_Events_Django
exact commit: 30ff0da00881f6db1882fa599ca46ee29db447e4
licence: MIT
framework: django
datastore: 

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 13 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 148
  event attach points: 0
  slot attach points: 136
  data attach points: 12
defined-but-unusable points measured (not counted): 48

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 2.3978952727983707
  contributors: 1.3862943611198906
  tagged_releases: 0.0
  test_suite_present: 0.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 3.7842
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Eventbrite / Ticketmaster
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule A datastore: needs postgresql, source says (not recorded); Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 10,
  "contributors": 3,
  "tagged_releases": 0,
  "test_suite_present_heuristic": false
}

## Keyword signal sweep (discovery only, never proof)
{
  "plugin": 8,
  "extension": 2,
  "signal": 1,
  "signals": 1,
  "event": 53,
  "event listener": 1,
  "middleware": 1,
  "extend": 2,
  "addon": 2,
  "contrib": 18,
  "plugins/": 2,
  "django.dispatch": 1,
  "receiver": 1
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule B: source publishes no REST API documentation

## Researcher notes
Real clone inspected (commit above). MIT LICENSE verified verbatim. Django==5.2.16, manage.py present at gestion_even/. No djangorestframework anywhere -- fully server-rendered, no API surface at all. Datastore mismatch: requirements.txt lists djongo/pymongo/bson (suggesting intended MongoDB use) but the actual settings.py DATABASES block is hardcoded to django.db.backends.sqlite3, with a db.sqlite3 file committed -- the Mongo dependencies are dead/unused and there is no Postgres evidence at all. Expected admission result: REJECTED on Rule A datastore (sqlite3 in actual use, no postgres path) and Rule B (no API at all).
