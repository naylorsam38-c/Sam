#!/usr/bin/env python3
"""
Driver for the three-category validation pilot: event ticketing, analytics
and BI, and challenge platform -- the three categories confirmed for
validation, kept here as a permanent, re-runnable audit record rather than
only in chat history.

Every CandidateSpec here reflects real, first-hand-verified evidence from an
actual git clone inspected during the pilot (license file contents,
settings.py DATABASES/requirements.txt framework+datastore declarations,
grep for real plugin/signal/API evidence, git log for activity). Nothing
here is invented or guessed -- where evidence was genuinely absent (no
attach points found, no published API docs, a licence claim contradicted by
the repo's own NOTICE file), that absence is recorded as such, not papered
over with an optimistic default.

Result of the pilot run recorded here: NONE of the twelve real candidates
inspected across the three categories were admitted. See
0_harvest_results/HARVEST_SUMMARY.md and each category's CATEGORY_SUMMARY.md
for the full, generated record -- this script reproduces exactly the input
that produced it.

Run (writes fresh output to ../0_harvest_results, re-cloning and
re-verifying every candidate's commit against the pinned SHAs below):
    cd APP_BUILDER/pack/0_harvest && python3 run_three_category_pilot.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hunt as H

CandidateSpec = H.CandidateSpec

# =====================================================================
# Category 1 -- Event ticketing
# =====================================================================

event_ticketing = [
    CandidateSpec(
        repo_name="iyanuashiri/meethub",
        repo_url="https://github.com/iyanuashiri/meethub",
        commit="500925d0962f67a32fa739b477416079af382dd7",
        licence="MIT",
        framework="django",
        datastore="postgresql",
        structural_match=(
            "Event creation, discovery and RSVP/attendance for meetups and "
            "conferences -- matches the event-ticketing exemplar's core "
            "domain, though its own DRF API urlconf line is commented out "
            "in config/urls.py, so nothing is actually published."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected directly. Django 5.2.4, psycopg2-binary, "
            "django.db.backends.postgresql confirmed in config/settings.py. "
            "MIT LICENSE file present and verbatim-checked. 173 commits, "
            "active 2018-2025 (most recent commit within this pilot's "
            "research window), contributors are effectively one person "
            "under three git identities plus a few small PRs and dependabot. "
            "No signals.py anywhere in the tree; grep for django.dispatch "
            "returns zero hits. A DRF serializer exists "
            "(meethub/accounts/serializers.py) but its api/v1 urlconf line "
            "in config/urls.py is commented out -- the only candidate "
            "externally-consumable DATA attach point is not actually wired "
            "into a live URL, so it is not usable, evidenced attach-point "
            "material under Rule G. The 18 files using Django's {% block %} "
            "template tag are ordinary internal template inheritance for "
            "the app's own pages, not a documented theme/plugin slot system "
            "for third parties -- no README or docs claim otherwise. "
            "Expected admission result: REJECTED on Rule G (no usable, "
            "evidenced attach points) and Rule B (no published API docs)."
        ),
    ),
    CandidateSpec(
        repo_name="fossasia/eventyay",
        repo_url="https://github.com/fossasia/eventyay",
        commit="786bd095c63b8cf2bbacfdc05f39d132816035f6",
        licence="UNRESOLVED -- see researcher_notes",
        framework="django",
        datastore="postgresql",
        structural_match=(
            "Full event management, ticketing, checkins, talks/schedules, "
            "badges -- a strong structural match to the event-ticketing "
            "exemplar, actively maintained by FOSSASIA, last commit the day "
            "before this pilot ran."
        ),
        attach_points=[
            {
                "name": "pretix.plugin entry points",
                "kind": "SLOT",
                "evidence": (
                    "app/eventyay/config/settings.py line 384: "
                    "'ticket_plugins = [ep.module for ep in "
                    "eps.select(group=\\'pretix.plugin\\') if ep.module not "
                    "in EVENTYAY_PLUGINS_EXCLUDE]' -- a real, live "
                    "setuptools entry-point group that third-party Python "
                    "packages register plugins into; this is the exact "
                    "mechanism pretix (the AGPL project eventyay forked "
                    "from) uses for its own third-party plugin ecosystem, "
                    "still active verbatim in eventyay's own settings.py."
                ),
                "implementation": "NATIVE",
                "source_file": "app/eventyay/config/settings.py",
            }
        ],
        plugin_authoring_docs_present=True,
        plugin_authoring_docs_location="doc/ (inherited from pretix's docs.pretix.eu references still present in-tree)",
        third_party_plugins_present=None,
        third_party_plugin_evidence=[],
        researcher_notes=(
            "LICENCE PROVENANCE CONFLICT -- surfaced, not guessed either way. "
            "The repository's own top-level LICENSE file declares Apache "
            "License 2.0. But NOTICE (read in full) states under "
            "'UPSTREAM ATTRIBUTIONS': 'Portions of Eventyay are derived "
            "from Pretix code ... Copyright (c) Raphael Michel and "
            "contributors ... Latest incorporated upstream snapshot: April "
            "12, 2021', plus equivalent statements for Pretalx and "
            "Venueless. Pretix is itself AGPL-3.0-only (confirmed via "
            "web search and consistent with public knowledge of the "
            "project). 885 literal occurrences of the string 'pretix' "
            "remain in app/eventyay/**/*.py, including the plugin "
            "entry-point group name 'pretix.plugin' itself, config keys, "
            "and a direct reference to docs.pretix.eu for API auth docs "
            "(app/eventyay/config/settings.py:1568). No statement anywhere "
            "in NOTICE, README.rst, CLA.md or git log messages claims "
            "explicit relicensing permission from Raphael Michel/pretix, "
            "pretalx, or venueless for the AGPL-derived portions. "
            "Relicensing AGPL-3.0 code as Apache-2.0 without the original "
            "copyright holders' consent is not something a downstream "
            "project can do unilaterally -- this is a real, evidenced gap "
            "in the repository's own licensing claim, not a suspicion. "
            "Per the standing instruction to never guess when something is "
            "genuinely unknown, this pilot does NOT assert eventyay is "
            "validly Apache-2.0, and does NOT assert it is actually AGPL -- "
            "it records the licence field as UNRESOLVED so the mechanical "
            "gate (Rule C, which only string-matches a declared licence) "
            "reflects the same unresolved state honestly, rather than "
            "passing on a self-declared string that the repository's own "
            "NOTICE file gives a specific, concrete reason to doubt. "
            "Expected admission result: REJECTED on Rule C, for a reason "
            "distinct from every other rejection in this pilot -- not "
            "'copyleft', but 'licence claim contradicted by the project's "
            "own stated provenance and not independently resolvable "
            "without a legal opinion this pilot cannot supply.'"
        ),
    ),
    CandidateSpec(
        repo_name="pyconsk/django-konfera",
        repo_url="https://github.com/pyconsk/django-konfera",
        commit="1072778e109d67bbc49fe3b06fa8ab29d6131eea",
        licence="MIT",
        framework="django",
        datastore="",
        structural_match=(
            "Conference organisation (speakers, talks, sponsors, venues) "
            "-- adjacent to event ticketing but no evidence of ticket "
            "sales/payment in requirements.txt; PostgreSQL is not declared "
            "anywhere in requirements.txt or requirements-test.txt (only "
            "django==1.10.4, django-wkhtmltopdf, django-sitetree)."
        ),
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. MIT LICENSE file present and verified. "
            "Last commit 2017-03-21 -- abandoned for 9 years at the time "
            "of this pilot. Django 1.10 (long EOL). No psycopg2 or "
            "postgres backend evidence found in either requirements file. "
            "Expected admission result: REJECTED on Rule A datastore (not "
            "recorded/not postgresql) and on activity/quality grounds."
        ),
    ),
    CandidateSpec(
        repo_name="suenkler/django-tickets",
        repo_url="https://github.com/suenkler/django-tickets",
        commit="6394e234e5909dd8c0f5f6e4cdd8827e0c25c06a",
        licence="MIT",
        framework="django",
        datastore="",
        structural_match=(
            "This is a generic IT/support helpdesk ticket tracker (create "
            "ticket via web or email, followups, assignment, file "
            "attachments) -- a completely different domain from event "
            "ticket sales. Its own README describes it as 'a simple "
            "ticketing application' in the help-desk sense, not event "
            "admission. Rule D structural match fails on domain grounds "
            "alone, independent of any other rule."
        ),
        attach_points=[],
        researcher_notes=(
            "Real clone inspected; README read in full. Last commit "
            "2017-01-29 -- abandoned. Included in this pilot's record for "
            "completeness of the real search performed, not because it was "
            "ever a plausible admit."
        ),
    ),
    CandidateSpec(
        repo_name="DefinitelyNotAnAssassin/TicketManagementSystem",
        repo_url="https://github.com/DefinitelyNotAnAssassin/TicketManagementSystem",
        commit="c5c8a742aa7bd4acff6bb0702414405efd51b91a",
        licence="",
        framework="django",
        datastore="",
        structural_match=(
            "A small student-style ticket system (module named "
            "'StudentTicket', db.sqlite3 committed to the repo) -- not "
            "event ticket sales."
        ),
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. README claims 'This project is licensed "
            "under the MIT License. See the LICENSE file for details' but "
            "no LICENSE file actually exists in the repository -- a claim "
            "the repo's own contents do not back up, so licence is "
            "recorded here as unverifiable rather than trusting the README "
            "text at face value. Expected admission result: REJECTED on "
            "Rule C (no verifiable licence) and Rule D (structural "
            "mismatch)."
        ),
    ),
]

# =====================================================================
# Category 2 -- Analytics / BI (Redash-equivalent)
# =====================================================================

analytics_bi = [
    CandidateSpec(
        repo_name="marinho/django-bi",
        repo_url="https://github.com/marinho/django-bi",
        commit="29f9de5622e0fd9e9a6608daafd30a4f2f8593a0",
        licence="LGPL",
        framework="django",
        datastore="",
        structural_match=(
            "A small Django app meant to be added to INSTALLED_APPS in "
            "someone else's project ('add \"bi\" to your INSTALLED_APPS') "
            "-- not a whole, standalone BI application in the sense the "
            "Redash/Metabase/Superset exemplar is. Section 9 requires "
            "evaluating whole candidate applications; this is a library."
        ),
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. setup.py declares licence = 'GNU Lesser "
            "General Public License (LGPL)' verbatim -- not on the "
            "permissive list regardless of the whole-application question. "
            "7 total commits, last release April 2019, 6 GitHub stars. "
            "Expected admission result: REJECTED on Rule C (LGPL is "
            "copyleft, not permissive) and, independently, on not being a "
            "whole candidate application."
        ),
    ),
    CandidateSpec(
        repo_name="paxalia/paxalia-dashboard",
        repo_url="https://github.com/paxalia/paxalia-dashboard",
        commit="f5a280342b7a5aeaa85487d39172f7debea6ab4e",
        licence="Apache-2.0",
        framework="django",
        datastore="",
        structural_match=(
            "Explicitly a drop-in package for other Django projects "
            "('Drop it into any Django project and get a beautiful, "
            "full-featured analytics dashboard') -- a library/addon, not a "
            "standalone whole application. Fails the Section 9 'whole "
            "candidate application' requirement on its own terms, "
            "independent of any other rule."
        ),
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. Genuinely Apache-2.0 licensed with no "
            "provenance red flags (unlike eventyay). But: exactly 1 commit "
            "in its entire history, created days before this pilot ran -- "
            "no track record, no real users, no evidence this is anything "
            "beyond a freshly-scaffolded package. Expected admission "
            "result: REJECTED as not a whole candidate application, and "
            "independently on quality/maturity grounds."
        ),
    ),
    CandidateSpec(
        repo_name="ManjunathGouda7/Django_PBI",
        repo_url="https://github.com/ManjunathGouda7/Django_PBI",
        commit="029e82f884ce117668c70ce930904fa8d9507756",
        licence="",
        framework="django",
        datastore="",
        structural_match=(
            "README describes an 'enterprise-grade telemetry analytics & "
            "interactive dashboard platform' -- structurally the closest "
            "fit to the BI/analytics exemplar of anything found in this "
            "category, but no LICENSE file exists in the repository at "
            "all."
        ),
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. No LICENSE file present anywhere in the "
            "tree. Exactly 1 commit in its entire history, created within "
            "days of this pilot running -- no independent evidence of "
            "production use, third-party adoption, or a real maintenance "
            "history behind the unusually polished README. Expected "
            "admission result: REJECTED on Rule C (no licence recorded at "
            "all) and on quality/maturity grounds."
        ),
    ),
]

# =====================================================================
# Category 3 -- Challenge platform (CTFd-equivalent)
# =====================================================================

challenge_platform = [
    CandidateSpec(
        repo_name="SniperOJ/Jeopardy-Platform",
        repo_url="https://github.com/SniperOJ/Jeopardy-Platform",
        commit="bfcfee060dd405258a605d9dfb0da523a39e7857",
        licence="",
        framework="django",
        datastore="",
        structural_match="Jeopardy-style CTF challenge/scoring platform -- correct domain.",
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. No LICENSE file in the repository and "
            "no licence statement in README.md. Last commit 2018-06-15 -- "
            "abandoned. Expected admission result: REJECTED on Rule C (no "
            "licence recorded) and activity/quality grounds."
        ),
    ),
    CandidateSpec(
        repo_name="pdogg/ctfmanager",
        repo_url="https://github.com/pdogg/ctfmanager",
        commit="d8f0ac7d7e12d7973b7eb39cd30a0bc81e4cb770",
        licence="BSD-3-Clause",
        framework="django",
        datastore="mysql",
        structural_match="Jeopardy-style CTF management/scoreboard -- correct domain.",
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. LICENSE file text is a verbatim 3-clause "
            "BSD licence (verified word-for-word against the standard "
            "text) -- permissive, and it IS on the allowed list, but "
            "settings.py declares 'django.db.backends.mysql', not "
            "PostgreSQL, and the settings.py comment scaffolding "
            "('# Django settings for ctfmanager project.') is generic "
            "django-admin startproject boilerplate left unedited -- this "
            "project was never brought past an initial scaffold toward "
            "production. Last commit 2014-05-12 -- abandoned 12 years. "
            "Expected admission result: REJECTED on Rule A datastore "
            "(mysql, not postgresql) and activity/quality grounds; this is "
            "the one candidate in this pilot that genuinely clears Rule C "
            "on licence alone."
        ),
    ),
    CandidateSpec(
        repo_name="super1337/Super1337-CTF",
        repo_url="https://github.com/super1337/Super1337-CTF",
        commit="3af085d310a8303ef3aff376ba930649586d5993",
        licence="MIT",
        framework="django",
        datastore="postgresql",
        structural_match="Jeopardy-style CTF site (app name 'jeopardyctf') -- correct domain.",
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. MIT LICENSE file present and verified. "
            "settings.py defaults to sqlite3 for local dev but requirements.txt "
            "pins psycopg2==2.7.3.1 and dj-database-url==0.4.2, and "
            "settings.py calls DATABASES['default'].update(db_from_env) -- "
            "genuine, evidenced production PostgreSQL capability via "
            "DATABASE_URL (Heroku-style deploy), recorded as postgresql on "
            "that real basis rather than the sqlite default alone. Django "
            "requirement is Django>=1.11.18 (EOL for years). Last commit "
            "2019-01-23 -- abandoned 7+ years. No signals.py, no plugin "
            "documentation, no published API docs found. Expected "
            "admission result: REJECTED on Rule G (no usable attach "
            "points recorded) and Rule B (no published API docs); this is "
            "the closest any candidate in this category came to clearing "
            "Rules A and C together, and it still fails outright on "
            "activity/extensibility evidence."
        ),
    ),
    CandidateSpec(
        repo_name="angstromctf/djangoctf",
        repo_url="https://github.com/angstromctf/djangoctf",
        commit="7c6188791053b7da7b5bbbfec2fd57c004b8e5ac",
        licence="GPL-3.0",
        framework="django",
        datastore="",
        structural_match="Jeopardy-style CTF competition platform -- correct domain.",
        attach_points=[],
        researcher_notes=(
            "Real clone inspected. LICENSE.txt is the verbatim GNU GPLv3 "
            "text -- copyleft, not on the permissive list. Last commit "
            "2018-03-17 -- abandoned. Expected admission result: REJECTED "
            "on Rule C (GPL-3.0 is copyleft) and activity grounds."
        ),
    ),
]

if __name__ == "__main__":
    results = {}
    for category, specs in [
        ("event ticketing", event_ticketing),
        ("analytics and BI", analytics_bi),
        ("challenge platform", challenge_platform),
    ]:
        winner, all_results = H.run_category(category, specs)
        results[category] = (winner, all_results)

    H.write_harvest_summary(results)
    print("\n\n=== PILOT COMPLETE ===")
    for category, (winner, all_results) in results.items():
        print(f"{category}: {'ADMITTED ' + winner['repo_name'] if winner else 'NONE ADMITTED'} "
              f"({len(all_results)} candidates inspected)")
