#!/usr/bin/env python3
"""
candidates/todo-list.py -- registry category id 1, "Todo List", exemplar
Todoist. Real, hand-verified evidence: WebSearch discovery (query log
below, run for real during this session) followed by direct clone-and-read
verification of API docs, licence, and structural fit for every candidate
kept. Nothing here is invented.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hunt as H
import discover as D

CandidateSpec = H.CandidateSpec

QUERIES = D.queries_for("Todo List", "Todoist")

HITS = [
    D.DiscoveryHit("CrowderSoup/vTodo", "https://github.com/CrowderSoup/vTodo", kept=True),
    D.DiscoveryHit("shacker/django-todo", "https://github.com/shacker/django-todo", kept=True),
    D.DiscoveryHit("rtzll/django-todolist", "https://github.com/rtzll/django-todolist", kept=False,
                  filter_reason="sqlite3 hardcoded, no Postgres wiring found"),
    D.DiscoveryHit("Nneji123/django_todo_list", "https://github.com/Nneji123/django_todo_list", kept=False,
                  filter_reason="last commit 2023-04-07, ~3.5 years stale"),
    D.DiscoveryHit("NAHIAN-19/Todo-List-Django", "https://github.com/NAHIAN-19/Todo-List-Django", kept=False,
                  filter_reason="last commit 2025-01-01, ~20 months stale; licence wording ambiguous"),
    D.DiscoveryHit("bradtraversy/django-todolist", "https://github.com/bradtraversy/django-todolist", kept=False,
                  filter_reason="no LICENSE file (all-rights-reserved by default); last commit 2020-10-01"),
]

CANDIDATES = [
    CandidateSpec(
        repo_name="CrowderSoup/vTodo",
        repo_url="https://github.com/CrowderSoup/vTodo",
        branch="main",
        commit="56745365951cda11f9958bc0e9e6c9941985ea78",
        licence="MIT",
        framework="django",
        datastore="postgresql",
        api_docs_url="/api/docs/ (in-app Swagger UI via drf-spectacular; also /api/schema/ "
                     "and /api/redoc/ -- config/urls.py lines 31-33 wire SpectacularAPIView, "
                     "SpectacularSwaggerView, SpectacularRedocView; settings.py registers "
                     "drf_spectacular and sets DEFAULT_SCHEMA_CLASS)",
        structural_match=(
            "vTodo implements a genuine Trello-style kanban board -- "
            "apps/boards/models.py has Board->Column->Task with per-column "
            "filter_config (status/tag/due-date filters) and drag-and-drop "
            "ordering, plus Teams for shared boards, matching Todoist's board "
            "view and shared-project model, though without Todoist's karma/"
            "gamification or natural-language quick-add."
        ),
        attach_points=[],  # mechanically measured by attach_points.py at run time
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected directly (commit above). Django>=6.0, "
            "manage.py present -- a real deployable project, not a "
            "pluggable library. psycopg2-binary>=2.9 in pyproject.toml; "
            "config/settings.py reads DATABASE_URL via django-environ, "
            "defaulting to sqlite only when unset -- README documents "
            "PostgreSQL under Requirements and the Docker/production path "
            "is Postgres-driven. MIT LICENSE file present and verified "
            "verbatim. Very active: last commit 2026-09-18 (day before this "
            "run). No CONTRIBUTING.md / plugin-authoring docs found; no "
            "third-party dependents found via WebSearch."
        ),
    ),
    CandidateSpec(
        repo_name="shacker/django-todo",
        repo_url="https://github.com/shacker/django-todo",
        branch="main",
        commit="95e3a022d239ebaa8771376c838a4d36590ab9b1",
        licence="BSD-3-Clause",
        framework="django",
        datastore="",
        api_docs_url="",
        structural_match=(
            "django-todo is a group/ticket-oriented task tracker "
            "(TaskList<->Task tied to Django auth Groups, CSV import, "
            "mail-tracking merge) closer to a lightweight helpdesk ticketing "
            "tool than to Todoist's personal-first task manager -- no "
            "kanban board, no personal due-date reminders, explicitly "
            "multi-user/multi-group rather than individual-first."
        ),
        attach_points=[],
        plugin_authoring_docs_present=False,
        third_party_plugins_present=False,
        researcher_notes=(
            "Real clone inspected (commit above). BSD-3-Clause LICENSE "
            "verified verbatim ('Copyright (c) 2010, Scot Hacker, Birdhouse "
            "Arts and individual contributors'). No manage.py anywhere -- "
            "this is a reusable/pluggable Django app meant to be installed "
            "into a host project (mkdocs.yml is a bare 2-line stub, no real "
            "docs/ directory), not a standalone deployable application. No "
            "djangorestframework dependency anywhere; the one non-admin "
            "urlconf entry (ticket/add/ for external ticket filing) is a "
            "plain view, not documented API. No postgres/psycopg evidence "
            "anywhere -- test_settings.py uses sqlite3; as a pluggable app "
            "it is DB-agnostic and does not itself declare Postgres. "
            "Expected admission result: REJECTED on Rule A datastore (not "
            "recorded) and Rule B (no published API docs)."
        ),
    ),
]

if __name__ == "__main__":
    out_dir = Path(H.HERE, H.OUTPUT_DIR, "todo-list")
    D.write_discovery_md(D.DiscoveryRun("Todo List", "todo-list", "Todoist", QUERIES, HITS), out_dir)
    winner, results = H.run_category(
        {"id": 1, "category": "Todo List", "slug": "todo-list", "exemplar": "Todoist"}, CANDIDATES)
    print("\nWINNER:", winner["repo_name"] if winner else "NONE ADMITTED")
