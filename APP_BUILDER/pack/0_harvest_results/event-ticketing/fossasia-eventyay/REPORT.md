# fossasia/eventyay

category: Event Ticketing (id 27, slug event-ticketing)
repository: fossasia/eventyay
repository URL: https://github.com/fossasia/eventyay
exact commit: 786bd095c63b8cf2bbacfdc05f39d132816035f6
licence: UNRESOLVED -- see researcher_notes
framework: django
datastore: postgresql

## Attach points (Section 33 -- mechanically measured from the real clone)
hook/signal keyword-sweep hits: 26 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 1329
  event attach points: 34
  slot attach points: 1151
  data attach points: 144
defined-but-unusable points measured (not counted): 691

## Extension system evidence
  - PLUGINS setting: app/eventyay/config/settings.py:428
plugin-authoring documentation (mechanically found): yes -- README.rst

## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)
plugin-authoring documentation: yes
  location: doc/ (inherited from pretix's docs.pretix.eu references still present in-tree)
third-party plugins: NOT RESEARCHED

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 7.403061091090091
  contributors: 6.07073772800249
  tagged_releases: 0.0
  test_suite_present: 1.0
  plugin_authoring_docs: 1.0
  issue_closure_ratio: 0.0
  third_party_plugins: 0.0
  TOTAL: 15.4738
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (no GitHub API access for repositories outside this session's own repo, see module docstring); this is a stated gap, not a silent zero.

## Exemplar feature match (Section 26.2)
exemplar: Eventbrite / Ticketmaster
features checked: 0  matched(code): 0  docs-only: 0  not found: 0
feature_match: NOT MEASURED (rejected at gate(s): Rule C licence: UNRESOLVED -- see researcher_notes is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0); Rule B: source publishes no REST API documentation)

## Git-derived metrics (real, from the clone's own history)
{
  "history_available_for_recency_check": true,
  "commits_last_6_months": 1640,
  "contributors": 432,
  "tagged_releases": 0,
  "test_suite_present_heuristic": true
}

## Keyword signal sweep (discovery only, never proof)
{
  "plugin": 326,
  "plugin system": 4,
  "plugin API": 2,
  "extension": 56,
  "hook": 72,
  "hooks": 45,
  "webhook": 63,
  "signal": 206,
  "signals": 193,
  "event": 1368,
  "subscriber": 1,
  "dispatcher": 6,
  "middleware": 45,
  "entry point": 15,
  "entry points": 5,
  "extend": 96,
  "extending": 3,
  "add-on": 43,
  "addon": 96,
  "contrib": 194,
  "signals.py": 1,
  "plugins/": 27,
  "extensions/": 1,
  "django.dispatch": 82,
  "receiver": 124,
  "Signal()": 15
}

## Admission result
**REJECTED**

Rejection reason(s):
  - Rule C licence: UNRESOLVED -- see researcher_notes is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0)
  - Rule B: source publishes no REST API documentation

## Researcher notes
Re-recorded from the pre-registry pilot's own real, first-hand clone inspection (not re-cloned this pass -- see this file's module docstring). LICENCE PROVENANCE CONFLICT, surfaced not guessed: the repo's top-level LICENSE file declares Apache-2.0, but its own NOTICE file states substantial portions are derived from Pretix (AGPL-3.0-only) with no independent relicensing consent recorded anywhere. Licence recorded as UNRESOLVED so the mechanical Rule C gate reflects that same unresolved state honestly rather than trusting the self-declared Apache-2.0 string. Expected admission result: REJECTED on Rule C, for the reason recorded, not a plain copyleft rejection.
