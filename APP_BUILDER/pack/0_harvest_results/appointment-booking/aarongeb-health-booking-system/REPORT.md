# aaronGeb/health_booking_system

category: Appointment Booking (id 25, slug appointment-booking)
repository: aaronGeb/health_booking_system
repository URL: https://github.com/aaronGeb/health_booking_system
exact commit: be523259842a952df328bc3217cbb99acc9d1e24
licence: MIT
framework: django
datastore: postgresql

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 2 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 1
  event attach points: 0
  slot attach points: 0
  data attach points: 1
defined-but-unusable points measured (not counted): 6

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 0.0
  contributors: 1.0986122886681096
  tagged_releases: 0.0
  test_suite_present: 0.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 1.0986
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Calendly
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 2,
  "tagged_releases": 0,
  "test_suite_present_heuristic": false
}

## Keyword signal sweep (discovery only, never proof)
{
  "middleware": 1,
  "contrib": 11
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule B: source publishes no REST API documentation

## Researcher notes
Real clone inspected (commit above). MIT LICENSE verified verbatim. Django>=5.2.6, manage.py present. Genuine postgres: settings.py lines 96-105 set ENGINE django.db.backends.postgresql (env-driven), docker-compose.yml runs a real postgres:16 service, psycopg2-binary>=2.9.10 in pyproject.toml -- this is the one candidate in this category that genuinely clears Rule A. djangorestframework>=3.16.1 is listed as a dependency but is completely unused -- root urls.py only wires admin/, none of the five apps has a urls.py, every views.py is untouched boilerplate. Expected admission result: REJECTED on Rule B (no published API docs -- DRF dependency present but unused) and, independently, on Rule G (mechanical attach-point measurement is expected to find effectively no reachable models given the empty views/urls, since Section 33.3's reachability rule requires a model be referenced outside its own file).
