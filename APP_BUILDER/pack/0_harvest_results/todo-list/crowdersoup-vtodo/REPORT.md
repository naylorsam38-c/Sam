# CrowderSoup/vTodo

category: Todo List (id 1, slug todo-list)
repository: CrowderSoup/vTodo
repository URL: https://github.com/CrowderSoup/vTodo
exact commit: 56745365951cda11f9958bc0e9e6c9941985ea78
licence: MIT
framework: django
datastore: postgresql

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 9 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 58
  event attach points: 0
  slot attach points: 43
  data attach points: 15
defined-but-unusable points measured (not counted): 63

## Extension system evidence
  (none mechanically found)
plugin-authoring documentation (mechanically found): no

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: no
  location: (none recorded)
third-party plugins: no

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 4.762173934797756
  contributors: 1.0986122886681096
  tagged_releases: 0.0
  test_suite_present: 1.0
  plugin_authoring_docs: 0.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 6.8608
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Todoist
features checked: 15  matched(code): 8  docs-only: 0  not found: 7
feature_match: 0.53

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 116,
  "contributors": 2,
  "tagged_releases": 0,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "extension": 1,
  "signal": 4,
  "signals": 4,
  "event": 5,
  "middleware": 3,
  "extend": 2,
  "contrib": 17,
  "django.dispatch": 2,
  "receiver": 2
}

## Admission result
**ADMITTED**

## Researcher notes
Real clone inspected directly (commit above). Django>=6.0, manage.py present -- a real deployable project, not a pluggable library. psycopg2-binary>=2.9 in pyproject.toml; config/settings.py reads DATABASE_URL via django-environ, defaulting to sqlite only when unset -- README documents PostgreSQL under Requirements and the Docker/production path is Postgres-driven. MIT LICENSE file present and verified verbatim. Very active: last commit 2026-09-18 (day before this run). No CONTRIBUTING.md / plugin-authoring docs found; no third-party dependents found via WebSearch.
