# pyconsk/django-konfera

category: event ticketing
repository: pyconsk/django-konfera
repository URL: https://github.com/pyconsk/django-konfera
exact commit: 1072778e109d67bbc49fe3b06fa8ab29d6131eea
licence: MIT
framework: django
datastore: 

## Attach points
hook/signal keyword-sweep hits: 5 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 0
  event attach points: 0
  slot attach points: 0
  data attach points: 0

## Documentation and ecosystem
plugin-authoring documentation: NOT RESEARCHED
  location: (none recorded)
third-party plugins: NOT RESEARCHED

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 0.0
  contributors: 5
  tagged_releases: 1
  test_suite_present: 3
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 9.0
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 32,
  "tagged_releases": 1,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "extension": 1,
  "event": 48,
  "middleware": 2,
  "extend": 1,
  "contrib": 14
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule B: source publishes no REST API documentation
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected. MIT LICENSE file present and verified. Last commit 2017-03-21 -- abandoned for 9 years at the time of this pilot. Django 1.10 (long EOL). No psycopg2 or postgres backend evidence found in either requirements file. Expected admission result: REJECTED on Rule A datastore (not recorded/not postgresql) and on activity/quality grounds.
