# pdogg/ctfmanager

category: challenge platform
repository: pdogg/ctfmanager
repository URL: https://github.com/pdogg/ctfmanager
exact commit: d8f0ac7d7e12d7973b7eb39cd30a0bc81e4cb770
licence: BSD-3-Clause
framework: django
datastore: mysql

## Attach points
hook/signal keyword-sweep hits: 3 distinct terms (discovery signal only, not proof -- see keyword_hits below)
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
  contributors: 0.8
  tagged_releases: 0
  test_suite_present: 0
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 0.8
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 4,
  "tagged_releases": 0,
  "test_suite_present_heuristic": false
}

## Keyword signal sweep (discovery only, never proof)
{
  "middleware": 1,
  "extend": 1,
  "contrib": 6
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says mysql
  - Rule B: source publishes no REST API documentation
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected. LICENSE file text is a verbatim 3-clause BSD licence (verified word-for-word against the standard text) -- permissive, and it IS on the allowed list, but settings.py declares 'django.db.backends.mysql', not PostgreSQL, and the settings.py comment scaffolding ('# Django settings for ctfmanager project.') is generic django-admin startproject boilerplate left unedited -- this project was never brought past an initial scaffold toward production. Last commit 2014-05-12 -- abandoned 12 years. Expected admission result: REJECTED on Rule A datastore (mysql, not postgresql) and activity/quality grounds; this is the one candidate in this pilot that genuinely clears Rule C on licence alone.
