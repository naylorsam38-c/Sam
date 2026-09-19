#!/usr/bin/env python3
"""
candidates/appointment-booking.py -- registry category id 25, "Appointment
Booking", exemplar Calendly. Real, hand-verified evidence.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hunt as H
import discover as D

CandidateSpec = H.CandidateSpec

QUERIES = D.queries_for("Appointment Booking", "Calendly")

HITS = [
    D.DiscoveryHit("adamspd/django-appointment", "https://github.com/adamspd/django-appointment", kept=True),
    D.DiscoveryHit("aaronGeb/health_booking_system", "https://github.com/aaronGeb/health_booking_system", kept=True),
    D.DiscoveryHit("llazzaro/django-scheduler", "https://github.com/llazzaro/django-scheduler", kept=True),
    D.DiscoveryHit("waleed-haider38/clinic_booking_system",
                  "https://github.com/waleed-haider38/clinic_booking_system", kept=False,
                  filter_reason="no LICENSE file in repo (all-rights-reserved by default)"),
    D.DiscoveryHit("Amirmhdp/doctor-appointment-system",
                  "https://github.com/Amirmhdp/doctor-appointment-system", kept=False,
                  filter_reason="no LICENSE file in repo (all-rights-reserved by default)"),
    D.DiscoveryHit("shiningflash/django-reservation-system",
                  "https://github.com/shiningflash/django-reservation-system", kept=False,
                  filter_reason="general reservation system, not scheduling-page specific; "
                                 "not independently re-verified this pass, kept out to bound scope"),
    D.DiscoveryHit("akash1997/django-calendly", "https://github.com/akash1997/django-calendly", kept=False,
                  filter_reason="GPLv3 licence -- not on the permissive allowlist"),
    D.DiscoveryHit("fsinfuhh/Bitpoll", "https://github.com/fsinfuhh/Bitpoll", kept=False,
                  filter_reason="Doodle-style date polling, not Calendly-style booking; GPLv3 licence"),
]

CANDIDATES = [
    CandidateSpec(
        repo_name="adamspd/django-appointment",
        repo_url="https://github.com/adamspd/django-appointment",
        branch="master",
        commit="55706a2bb8da75b1ee91226ac7bfaac529465eff",
        licence="Apache-2.0",
        framework="django",
        datastore="",
        api_docs_url="",
        structural_match=(
            "django-appointment is a strong structural match to Calendly -- "
            "Service/StaffMember/AppointmentRequest/Appointment/WorkingHours/"
            "DayOff/PaymentInfo models implement staff-specific availability "
            "windows, slot generation, booking-request-to-confirmed-"
            "appointment flow, and payment tracking, Calendly's core "
            "booking-page mechanic."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        plugin_authoring_docs_location="docs/CUSTOM_TEMPLATES.md documents a real template-"
                                       "override mechanism, but not plugin authoring in the "
                                       "extension-point sense",
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected (commit above). Apache-2.0 LICENSE "
            "verified verbatim. manage.py present -- a real deployable demo "
            "project. No djangorestframework dependency anywhere -- "
            "docs/views.md and docs/admin_views.md (published at "
            "django-appt-doc.adamspierredavid.com via mkdocs-material) "
            "document plain session-auth AJAX JsonResponse endpoints, not a "
            "REST API (no DRF, no OpenAPI schema, no versioning) -- does "
            "not count as Rule B API documentation. No postgres/psycopg "
            "evidence -- appointments/settings.py DATABASES defaults to "
            "sqlite3, .env.example has no DB_* vars, requirements.txt lists "
            "no postgres driver, docker-compose.yml has no postgres "
            "service. Expected admission result: REJECTED on Rule A "
            "datastore (not recorded) and Rule B (AJAX endpoint docs are "
            "not REST API documentation)."
        ),
    ),
    CandidateSpec(
        repo_name="aaronGeb/health_booking_system",
        repo_url="https://github.com/aaronGeb/health_booking_system",
        branch="main",
        commit="be523259842a952df328bc3217cbb99acc9d1e24",
        licence="MIT",
        framework="django",
        datastore="postgresql",
        api_docs_url="",
        structural_match=(
            "README and ER diagram describe a Zocdoc/Calendly-style doctor-"
            "booking system (patients/doctors/appointments/medical records, "
            "role-based access), but the actual code does not implement "
            "that yet -- only doctors/models.py (83 lines) has real model "
            "content; appointments/models.py, medical_records/models.py and "
            "patients/models.py are each 3-line stubs, zero views or URL "
            "routes exist beyond Django admin. An early-stage skeleton, not "
            "a working booking app."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected (commit above). MIT LICENSE verified "
            "verbatim. Django>=5.2.6, manage.py present. Genuine postgres: "
            "settings.py lines 96-105 set ENGINE django.db.backends."
            "postgresql (env-driven), docker-compose.yml runs a real "
            "postgres:16 service, psycopg2-binary>=2.9.10 in pyproject."
            "toml -- this is the one candidate in this category that "
            "genuinely clears Rule A. djangorestframework>=3.16.1 is listed "
            "as a dependency but is completely unused -- root urls.py only "
            "wires admin/, none of the five apps has a urls.py, every "
            "views.py is untouched boilerplate. Expected admission result: "
            "REJECTED on Rule B (no published API docs -- DRF dependency "
            "present but unused) and, independently, on Rule G (mechanical "
            "attach-point measurement is expected to find effectively no "
            "reachable models given the empty views/urls, since Section "
            "33.3's reachability rule requires a model be referenced "
            "outside its own file)."
        ),
    ),
    CandidateSpec(
        repo_name="llazzaro/django-scheduler",
        repo_url="https://github.com/llazzaro/django-scheduler",
        branch="master",
        commit="ab3618013b3de2f194e3d2898653bcf88d6ec163",
        licence="BSD-3-Clause",
        framework="django",
        datastore="",
        api_docs_url="",
        structural_match=(
            "django-scheduler is a general-purpose recurring-events "
            "calendar engine (Calendar->Event->Occurrence with iCal-style "
            "Rule recurrence, plus iCal/RSS export) matching Google "
            "Calendar's event/recurrence model, not Calendly's booking-page "
            "product -- no client-facing booking-request workflow, no "
            "staff/service/availability concept, no payment integration. A "
            "poor structural match for this category's exemplar "
            "specifically."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected (commit above). BSD-3-Clause LICENSE.txt "
            "verified verbatim ('Copyright (c) 2008-2017, Tony Hauber'). No "
            "manage.py anywhere -- a reusable pluggable Django app (ships "
            "only tests/settings.py for its own suite), not a standalone "
            "deployable application. schedule/urls.py exposes three plain "
            "JsonResponse endpoints used internally by a JS calendar widget "
            "(/api/occurrences, /api/move_or_resize/, /api/select_create/) "
            "-- no docstrings, no Swagger/OpenAPI/DRF, docs/views.txt does "
            "not document them; does not count as Rule B evidence. No "
            "postgres/psycopg evidence -- tests/settings.py uses sqlite3 "
            "in-memory; DB-agnostic pluggable app. Expected admission "
            "result: REJECTED on Rule A datastore (not recorded), Rule B "
            "(no published API docs), and Rule D (structural mismatch to "
            "the Calendly exemplar, recorded honestly above rather than "
            "the gate's mere non-empty check)."
        ),
    ),
]

if __name__ == "__main__":
    out_dir = Path(H.HERE, H.OUTPUT_DIR, "appointment-booking")
    D.write_discovery_md(D.DiscoveryRun("Appointment Booking", "appointment-booking", "Calendly",
                                        QUERIES, HITS), out_dir)
    winner, results = H.run_category(
        {"id": 25, "category": "Appointment Booking", "slug": "appointment-booking",
         "exemplar": "Calendly"}, CANDIDATES)
    print("\nWINNER:", winner["repo_name"] if winner else "NONE ADMITTED")
