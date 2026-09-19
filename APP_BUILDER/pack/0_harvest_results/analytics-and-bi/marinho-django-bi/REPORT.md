# marinho/django-bi

category: analytics and BI
repository: marinho/django-bi
repository URL: https://github.com/marinho/django-bi
exact commit: 29f9de5622e0fd9e9a6608daafd30a4f2f8593a0
licence: LGPL
framework: django
datastore: 

## Attach points
hook/signal keyword-sweep hits: 2 distinct terms (discovery signal only, not proof -- see keyword_hits below)
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
  contributors: 0.2
  tagged_releases: 0
  test_suite_present: 3
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 3.2
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 1,
  "tagged_releases": 0,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "signal": 1,
  "contrib": 2
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule C licence: LGPL is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0)
  - Rule B: source publishes no REST API documentation
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected. setup.py declares licence = 'GNU Lesser General Public License (LGPL)' verbatim -- not on the permissive list regardless of the whole-application question. 7 total commits, last release April 2019, 6 GitHub stars. Expected admission result: REJECTED on Rule C (LGPL is copyleft, not permissive) and, independently, on not being a whole candidate application.
