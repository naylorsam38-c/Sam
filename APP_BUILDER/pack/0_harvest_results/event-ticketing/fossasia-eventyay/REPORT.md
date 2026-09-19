# fossasia/eventyay

category: event ticketing
repository: fossasia/eventyay
repository URL: https://github.com/fossasia/eventyay
exact commit: 786bd095c63b8cf2bbacfdc05f39d132816035f6
licence: UNRESOLVED -- see researcher_notes
framework: django
datastore: postgresql

## Attach points
hook/signal keyword-sweep hits: 26 distinct terms (discovery signal only, not proof -- see keyword_hits below)
usable, evidenced attach-point count: 1
  event attach points: 0
  slot attach points: 1
  data attach points: 0

## Documentation and ecosystem
plugin-authoring documentation: yes
  location: doc/ (inherited from pretix's docs.pretix.eu references still present in-tree)
third-party plugins: NOT RESEARCHED

## Quality score components (see quality_score() for the weighting)
  commits_last_6_months: 5
  contributors: 5
  tagged_releases: 0
  test_suite_present: 3
  plugin_authoring_docs: 4
  issue_closure_ratio: 0
  third_party_plugins: 0
  TOTAL: 17.0
  NOTE: issue_closure_ratio is always 0 here -- no real data source was available to this script (GitHub-wide search was out of scope for the session that wrote it); this is a stated gap, not a silent zero.

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
LICENCE PROVENANCE CONFLICT -- surfaced, not guessed either way. The repository's own top-level LICENSE file declares Apache License 2.0. But NOTICE (read in full) states under 'UPSTREAM ATTRIBUTIONS': 'Portions of Eventyay are derived from Pretix code ... Copyright (c) Raphael Michel and contributors ... Latest incorporated upstream snapshot: April 12, 2021', plus equivalent statements for Pretalx and Venueless. Pretix is itself AGPL-3.0-only (confirmed via web search and consistent with public knowledge of the project). 885 literal occurrences of the string 'pretix' remain in app/eventyay/**/*.py, including the plugin entry-point group name 'pretix.plugin' itself, config keys, and a direct reference to docs.pretix.eu for API auth docs (app/eventyay/config/settings.py:1568). No statement anywhere in NOTICE, README.rst, CLA.md or git log messages claims explicit relicensing permission from Raphael Michel/pretix, pretalx, or venueless for the AGPL-derived portions. Relicensing AGPL-3.0 code as Apache-2.0 without the original copyright holders' consent is not something a downstream project can do unilaterally -- this is a real, evidenced gap in the repository's own licensing claim, not a suspicion. Per the standing instruction to never guess when something is genuinely unknown, this pilot does NOT assert eventyay is validly Apache-2.0, and does NOT assert it is actually AGPL -- it records the licence field as UNRESOLVED so the mechanical gate (Rule C, which only string-matches a declared licence) reflects the same unresolved state honestly, rather than passing on a self-declared string that the repository's own NOTICE file gives a specific, concrete reason to doubt. Expected admission result: REJECTED on Rule C, for a reason distinct from every other rejection in this pilot -- not 'copyleft', but 'licence claim contradicted by the project's own stated provenance and not independently resolvable without a legal opinion this pilot cannot supply.'
