# super1337/Super1337-CTF

category: challenge platform
repository: super1337/Super1337-CTF
repository URL: https://github.com/super1337/Super1337-CTF
exact commit: 3af085d310a8303ef3aff376ba930649586d5993
licence: MIT
framework: django
datastore: postgresql

## Attach points
hook/signal keyword-sweep hits: 6 distinct terms (discovery signal only, not proof -- see keyword_hits below)
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
  contributors: 1.6
  tagged_releases: 0
  test_suite_present: 0
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 1.6
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 8,
  "tagged_releases": 0,
  "test_suite_present_heuristic": false
}

## Keyword signal sweep (discovery only, never proof)
{
  "signal": 1,
  "signals": 1,
  "middleware": 1,
  "contrib": 17,
  "django.dispatch": 1,
  "receiver": 1
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule B: source publishes no REST API documentation
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected. MIT LICENSE file present and verified. settings.py defaults to sqlite3 for local dev but requirements.txt pins psycopg2==2.7.3.1 and dj-database-url==0.4.2, and settings.py calls DATABASES['default'].update(db_from_env) -- genuine, evidenced production PostgreSQL capability via DATABASE_URL (Heroku-style deploy), recorded as postgresql on that real basis rather than the sqlite default alone. Django requirement is Django>=1.11.18 (EOL for years). Last commit 2019-01-23 -- abandoned 7+ years. No signals.py, no plugin documentation, no published API docs found. Expected admission result: REJECTED on Rule G (no usable attach points recorded) and Rule B (no published API docs); this is the closest any candidate in this category came to clearing Rules A and C together, and it still fails outright on activity/extensibility evidence.
