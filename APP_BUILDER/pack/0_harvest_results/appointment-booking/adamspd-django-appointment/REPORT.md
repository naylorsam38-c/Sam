# adamspd/django-appointment

category: Appointment Booking (id 25, slug appointment-booking)
repository: adamspd/django-appointment
repository URL: https://github.com/adamspd/django-appointment
exact commit: 55706a2bb8da75b1ee91226ac7bfaac529465eff
licence: Apache-2.0
framework: django
datastore: 

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 9 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 11
  event attach points: 0
  slot attach points: 0
  data attach points: 11
defined-but-unusable points measured (not counted): 153

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: docs/CUSTOM_TEMPLATES.md documents a real template-override mechanism, but not plugin authoring in the extension-point sense
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 4.5217885770490405
  contributors: 2.4849066497880004
  tagged_releases: 3.7612001156935624
  test_suite_present: 1.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 11.7679
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Calendly
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule A datastore: needs postgresql, source says (not recorded); Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 91,
  "contributors": 11,
  "tagged_releases": 42,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "signal": 2,
  "signals": 1,
  "event": 16,
  "middleware": 4,
  "extend": 5,
  "extending": 3,
  "contrib": 21,
  "django.dispatch": 1,
  "receiver": 2
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule A datastore: needs postgresql, source says (not recorded)
  - Rule B: source publishes no REST API documentation

## Researcher notes
Real clone inspected (commit above). Apache-2.0 LICENSE verified verbatim. manage.py present -- a real deployable demo project. No djangorestframework dependency anywhere -- docs/views.md and docs/admin_views.md (published at django-appt-doc.adamspierredavid.com via mkdocs-material) document plain session-auth AJAX JsonResponse endpoints, not a REST API (no DRF, no OpenAPI schema, no versioning) -- does not count as Rule B API documentation. No postgres/psycopg evidence -- appointments/settings.py DATABASES defaults to sqlite3, .env.example has no DB_* vars, requirements.txt lists no postgres driver, docker-compose.yml has no postgres service. Expected admission result: REJECTED on Rule A datastore (not recorded) and Rule B (AJAX endpoint docs are not REST API documentation).
