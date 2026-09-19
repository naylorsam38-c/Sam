# iyanuashiri/meethub

category: Event Ticketing (id 27, slug event-ticketing)
repository: iyanuashiri/meethub
repository URL: https://github.com/iyanuashiri/meethub
exact commit: 500925d0962f67a32fa739b477416079af382dd7
licence: MIT
framework: django
datastore: postgresql

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 9 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 28
  event attach points: 0
  slot attach points: 23
  data attach points: 5
defined-but-unusable points measured (not counted): 26

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 0.0
  contributors: 2.302585092994046
  tagged_releases: 0.0
  test_suite_present: 1.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 3.3026
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Eventbrite / Ticketmaster
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 0,
  "contributors": 9,
  "tagged_releases": 0,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "plugin": 15,
  "extension": 2,
  "event": 50,
  "event listener": 2,
  "middleware": 1,
  "extend": 4,
  "addon": 4,
  "contrib": 33,
  "plugins/": 4
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule B: source publishes no REST API documentation

## Researcher notes
Real clone inspected (commit above, re-verified this pass -- identical SHA to the pre-registry pilot's finding, repo unchanged). MIT LICENSE verified verbatim. Django, manage.py present. Genuine postgres: config/settings.py lines 92-101 set ENGINE django.db.backends.postgresql (env-driven) as the production branch, psycopg2-binary>=2.9.10 present. djangorestframework>=3.16.0 and a real serializers.py exist, but config/urls.py's only API route is commented out (# path('api/v1/', include('apiv1.urls'))) and the referenced apiv1 module does not exist in the repo at all -- DRF is an unused/dead dependency in practice. Expected admission result: REJECTED on Rule B (no published, live API docs) and Rule D (structural mismatch -- RSVP/Meetup domain, not ticketed events).
