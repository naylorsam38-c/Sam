# angstromctf/djangoctf

category: challenge platform
repository: angstromctf/djangoctf
repository URL: https://github.com/angstromctf/djangoctf
exact commit: 7c6188791053b7da7b5bbbfec2fd57c004b8e5ac
licence: GPL-3.0
framework: django
datastore: 

## Attach points
hook/signal keyword-sweep hits: 7 distinct terms (discovery signal only, not proof -- see keyword_hits below)
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
  contributors: 2.6
  tagged_releases: 2
  test_suite_present: 0
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 4.6
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 13,
  "tagged_releases": 2,
  "test_suite_present_heuristic": false
}

## Keyword signal sweep (discovery only, never proof)
{
  "signal": 1,
  "signals": 1,
  "event": 1,
  "middleware": 1,
  "contrib": 5,
  "django.dispatch": 1,
  "receiver": 1
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule C licence: GPL-3.0 is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0)
  - Rule B: source publishes no REST API documentation
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected. LICENSE.txt is the verbatim GNU GPLv3 text -- copyleft, not on the permissive list. Last commit 2018-03-17 -- abandoned. Expected admission result: REJECTED on Rule C (GPL-3.0 is copyleft) and activity grounds.
