# paxalia/paxalia-dashboard

category: analytics and BI
repository: paxalia/paxalia-dashboard
repository URL: https://github.com/paxalia/paxalia-dashboard
exact commit: f5a280342b7a5aeaa85487d39172f7debea6ab4e
licence: Apache-2.0
framework: django
datastore: 

## Attach points
hook/signal keyword-sweep hits: 14 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 0
  event attach points: 0
  slot attach points: 0
  data attach points: 0

## Documentation and ecosystem
plugin-authoring documentation: NOT RESEARCHED
  location: (none recorded)
third-party plugins: NOT RESEARCHED

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 5
  contributors: 0.2
  tagged_releases: 5
  test_suite_present: 0
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 10.2
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 67,
  "contributors": 1,
  "tagged_releases": 5,
  "test_suite_present_heuristic": false
}

## Keyword signal sweep (discovery only, never proof)
{
  "plugin": 3,
  "extension": 10,
  "hook": 5,
  "webhook": 5,
  "signal": 6,
  "signals": 5,
  "event": 35,
  "middleware": 16,
  "entry point": 2,
  "extend": 5,
  "add-on": 1,
  "contrib": 40,
  "signals.py": 4,
  "events.py": 3
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule B: source publishes no REST API documentation
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected. Genuinely Apache-2.0 licensed with no provenance red flags (unlike eventyay). But: exactly 1 commit in its entire history, created days before this pilot ran -- no track record, no real users, no evidence this is anything beyond a freshly-scaffolded package. Expected admission result: REJECTED as not a whole candidate application, and independently on quality/maturity grounds.
