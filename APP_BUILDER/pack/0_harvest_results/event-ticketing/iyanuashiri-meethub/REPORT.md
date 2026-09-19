# iyanuashiri/meethub

category: event ticketing
repository: iyanuashiri/meethub
repository URL: https://github.com/iyanuashiri/meethub
exact commit: 500925d0962f67a32fa739b477416079af382dd7
licence: MIT
framework: django
datastore: postgresql

## Attach points
hook/signal keyword-sweep hits: 9 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 0
  event attach points: 0
  slot attach points: 0
  data attach points: 0

## Documentation and ecosystem
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 0.0
  contributors: 1.8
  tagged_releases: 0
  test_suite_present: 3
  plugin_authoring_docs: 0
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 4.8
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

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
  - Rule G: no usable, evidenced attach points recorded in harvest_source.attach_points

## Researcher notes
Real clone inspected directly. Django 5.2.4, psycopg2-binary, django.db.backends.postgresql confirmed in config/settings.py. MIT LICENSE file present and verbatim-checked. 173 commits, active 2018-2025 (most recent commit within this pilot's research window), contributors are effectively one person under three git identities plus a few small PRs and dependabot. No signals.py anywhere in the tree; grep for django.dispatch returns zero hits. A DRF serializer exists (meethub/accounts/serializers.py) but its api/v1 urlconf line in config/urls.py is commented out -- the only candidate externally-consumable DATA attach point is not actually wired into a live URL, so it is not usable, evidenced attach-point material under Rule G. The 18 files using Django's {% block %} template tag are ordinary internal template inheritance for the app's own pages, not a documented theme/plugin slot system for third parties -- no README or docs claim otherwise. Expected admission result: REJECTED on Rule G (no usable, evidenced attach points) and Rule B (no published API docs).
