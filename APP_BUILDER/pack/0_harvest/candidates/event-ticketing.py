#!/usr/bin/env python3
"""
candidates/event-ticketing.py -- registry category id 27, "Event
Ticketing", exemplar Eventbrite (secondary Ticketmaster). Real,
hand-verified evidence. Includes the two candidates already inspected in
the pre-registry pilot (iyanuashiri/meethub, fossasia/eventyay) re-recorded
here against the canonical category id, plus newly discovered pretix/pretix
and SalahEddine-Ghannouch/GetTicket_Events_Django. Not re-cloning eventyay
in this pass -- its prior REPORT.md/evidence at
0_harvest_results/event-ticketing/fossasia-eventyay/ (pre-registry pilot,
different output path than this run) already stands on real evidence; its
licence conflict is stated in researcher_notes below rather than re-derived.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hunt as H
import discover as D

CandidateSpec = H.CandidateSpec

QUERIES = D.queries_for("Event Ticketing", "Eventbrite", "Ticketmaster")

HITS = [
    D.DiscoveryHit("iyanuashiri/meethub", "https://github.com/iyanuashiri/meethub", kept=True),
    D.DiscoveryHit("SalahEddine-Ghannouch/GetTicket_Events_Django",
                  "https://github.com/SalahEddine-Ghannouch/GetTicket_Events_Django", kept=True),
    D.DiscoveryHit("pretix/pretix", "https://github.com/pretix/pretix", kept=False,
                  filter_reason="AGPL-3.0 with additional terms -- confirmed by reading LICENSE "
                                 "directly; not on the permissive allowlist"),
    D.DiscoveryHit("fossasia/eventyay", "https://github.com/fossasia/eventyay", kept=True),
    D.DiscoveryHit("kerry407/ticket-system", "https://github.com/kerry407/ticket-system", kept=False,
                  filter_reason="no LICENSE file (all-rights-reserved by default); last commit "
                                 "2023-10-26, ~3 years stale"),
    D.DiscoveryHit("dkerobean/Django-Event-Booking-And-Ticketing-System",
                  "https://github.com/dkerobean/Django-Event-Booking-And-Ticketing-System", kept=False,
                  filter_reason="no LICENSE file; last commit 2023-03-06, ~3.5 years stale"),
    D.DiscoveryHit("sajib1066/django-event-management",
                  "https://github.com/sajib1066/django-event-management", kept=False,
                  filter_reason="no LICENSE file; last commit 2024-01-28, ~2.5 years stale"),
    D.DiscoveryHit("sonamkshenoy/Events-Hosting", "https://github.com/sonamkshenoy/Events-Hosting",
                  kept=False, filter_reason="no LICENSE file; last commit 2020-01-21, ~6.5 years stale"),
]

CANDIDATES = [
    CandidateSpec(
        repo_name="iyanuashiri/meethub",
        repo_url="https://github.com/iyanuashiri/meethub",
        branch="master",
        commit="500925d0962f67a32fa739b477416079af382dd7",
        licence="MIT",
        framework="django",
        datastore="postgresql",
        api_docs_url="",
        structural_match=(
            "meethub is explicitly modeled on Meetup.com (RSVP-based Event/"
            "Category/Account with an attendees M2M and comments), not "
            "Eventbrite -- there is no Ticket model, no price/quantity "
            "field, and no payment flow anywhere in the codebase. As an "
            "event-ticketing exemplar match it is weak: free RSVP "
            "attendance, not paid ticket sales."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected (commit above, re-verified this pass -- "
            "identical SHA to the pre-registry pilot's finding, repo "
            "unchanged). MIT LICENSE verified verbatim. Django, manage.py "
            "present. Genuine postgres: config/settings.py lines 92-101 set "
            "ENGINE django.db.backends.postgresql (env-driven) as the "
            "production branch, psycopg2-binary>=2.9.10 present. "
            "djangorestframework>=3.16.0 and a real serializers.py exist, "
            "but config/urls.py's only API route is commented out "
            "(# path('api/v1/', include('apiv1.urls'))) and the referenced "
            "apiv1 module does not exist in the repo at all -- DRF is an "
            "unused/dead dependency in practice. Expected admission "
            "result: REJECTED on Rule B (no published, live API docs) and "
            "Rule D (structural mismatch -- RSVP/Meetup domain, not "
            "ticketed events)."
        ),
    ),
    CandidateSpec(
        repo_name="SalahEddine-Ghannouch/GetTicket_Events_Django",
        repo_url="https://github.com/SalahEddine-Ghannouch/GetTicket_Events_Django",
        branch="main",
        commit="30ff0da00881f6db1882fa599ca46ee29db447e4",
        licence="MIT",
        framework="django",
        datastore="",
        api_docs_url="",
        structural_match=(
            "A genuine Eventbrite-style match -- events/models.py has a "
            "real Ticket model with price (DecimalField) and nbr_ticket "
            "(quantity), tied to Event/EventCategory with admin/organizer/"
            "customer role separation and an online-purchase flow "
            "described in the README, closer to Eventbrite's ticketed-"
            "event model than meethub's free-RSVP model."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected (commit above). MIT LICENSE verified "
            "verbatim. Django==5.2.16, manage.py present at gestion_even/. "
            "No djangorestframework anywhere -- fully server-rendered, no "
            "API surface at all. Datastore mismatch: requirements.txt "
            "lists djongo/pymongo/bson (suggesting intended MongoDB use) "
            "but the actual settings.py DATABASES block is hardcoded to "
            "django.db.backends.sqlite3, with a db.sqlite3 file committed "
            "-- the Mongo dependencies are dead/unused and there is no "
            "Postgres evidence at all. Expected admission result: REJECTED "
            "on Rule A datastore (sqlite3 in actual use, no postgres path) "
            "and Rule B (no API at all)."
        ),
    ),
    CandidateSpec(
        repo_name="fossasia/eventyay",
        repo_url="https://github.com/fossasia/eventyay",
        branch="main",
        commit="786bd095c63b8cf2bbacfdc05f39d132816035f6",
        licence="UNRESOLVED -- see researcher_notes",
        framework="django",
        datastore="postgresql",
        api_docs_url="",
        structural_match=(
            "Full event management, ticketing, checkins, talks/schedules, "
            "badges -- a strong structural match to Eventbrite, actively "
            "maintained by FOSSASIA."
        ),
        attach_points=[],
        plugin_authoring_docs_present=True,
        plugin_authoring_docs_location="doc/ (inherited from pretix's docs.pretix.eu references "
                                       "still present in-tree)",
        third_party_plugins_present=None,
        researcher_notes=(
            "Re-recorded from the pre-registry pilot's own real, first-hand "
            "clone inspection (not re-cloned this pass -- see this file's "
            "module docstring). LICENCE PROVENANCE CONFLICT, surfaced not "
            "guessed: the repo's top-level LICENSE file declares Apache-2.0, "
            "but its own NOTICE file states substantial portions are "
            "derived from Pretix (AGPL-3.0-only) with no independent "
            "relicensing consent recorded anywhere. Licence recorded as "
            "UNRESOLVED so the mechanical Rule C gate reflects that same "
            "unresolved state honestly rather than trusting the self-"
            "declared Apache-2.0 string. Expected admission result: "
            "REJECTED on Rule C, for the reason recorded, not a plain "
            "copyleft rejection."
        ),
    ),
]

if __name__ == "__main__":
    out_dir = Path(H.HERE, H.OUTPUT_DIR, "event-ticketing")
    D.write_discovery_md(D.DiscoveryRun("Event Ticketing", "event-ticketing",
                                        "Eventbrite / Ticketmaster", QUERIES, HITS), out_dir)
    winner, results = H.run_category(
        {"id": 27, "category": "Event Ticketing", "slug": "event-ticketing",
         "exemplar": "Eventbrite", "secondary_exemplar": "Ticketmaster"}, CANDIDATES)
    print("\nWINNER:", winner["repo_name"] if winner else "NONE ADMITTED")
