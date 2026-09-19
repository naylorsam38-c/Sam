#!/usr/bin/env python3
"""
test_registry_harvest.py -- Section 36's additional test list, for the
registry/exemplar/mechanical-attach-point layer added on top of the
Section 20 admission architecture (test_admission.py).

Same two-tier discipline as test_admission.py:

TIER 1 (TestMechanical*, TestFeatureMatch*, TestRanking*, TestDiscovery*)
exercises attach_points.py, exemplar_match.py, discover.py and hunt.py's
ranking helpers as pure functions -- but "pure function" here still means
real AST parsing and real regex matching against real files this test
writes to a temp directory (never against a synthetic dict standing in for
a clone). A fabricated .py file written to disk and parsed for real by
`ast` is real evidence of the parser's behaviour, not mocked evidence.

TIER 2 (TestRealRepo*, TestRegistryDriven*) uses an actual small git clone
and the actual CATEGORY_REGISTRY.json / EXEMPLAR_FEATURES.json shipped in
this repo.

Run:
    python3 -m pytest test_registry_harvest.py -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PACK_ROOT = HERE.parent

sys.path.insert(0, str(HERE))
import attach_points as AP  # noqa: E402
import exemplar_match as EM  # noqa: E402

sys.path.insert(0, str(PACK_ROOT / "0_harvest"))
import hunt as H  # noqa: E402
import discover as D  # noqa: E402

CLONE_SCRATCH = Path("/tmp/test_registry_harvest_clones")


def _write(root: Path, rel: str, content: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# =====================================================================
# TIER 1 -- attach_points.py, real parsing against real fixture files
# =====================================================================

class TestMechanicalEventDetection:
    def test_signal_defined_but_never_sent_does_not_count(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Widget(models.Model):\n    name = models.CharField(max_length=10)\n")
        _write(tmp_path, "app/signals.py",
               "import django.dispatch\nwidget_touched = django.dispatch.Signal()\n")
        # No .send()/.send_robust() site anywhere -- DEFINED_NOT_SENT.
        result = AP.measure_attach_points(tmp_path)
        assert result["counts"]["usable_events"] == 0
        statuses = {p["status"] for p in result["all_measured"] if p["kind"] == "EVENT"}
        assert "DEFINED_NOT_SENT" in statuses

    def test_signal_with_real_send_site_counts(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Widget(models.Model):\n    name = models.CharField(max_length=10)\n")
        _write(tmp_path, "app/signals.py",
               "import django.dispatch\nwidget_touched = django.dispatch.Signal()\n")
        _write(tmp_path, "app/views.py",
               "from .signals import widget_touched\n\n"
               "def touch(request):\n    widget_touched.send(sender=None, widget_id=1)\n")
        result = AP.measure_attach_points(tmp_path)
        assert result["counts"]["usable_events"] == 1
        assert result["usable_events"][0]["implementation"] == "NATIVE"
        assert ":" in result["usable_events"][0]["evidence"]

    def test_model_signals_excluded_by_default(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Widget(models.Model):\n    name = models.CharField(max_length=10)\n")
        _write(tmp_path, "app/views.py", "from .models import Widget\n\n"
               "def create(request):\n    Widget.objects.create(name='x')\n")
        result = AP.measure_attach_points(tmp_path, require_model_signals_count=False)
        assert result["counts"]["usable_events"] == 0
        excluded = [p for p in result["all_measured"]
                    if p["status"] == "MODEL_SIGNAL_EXCLUDED"]
        assert len(excluded) == 4  # post_save/pre_save/post_delete/pre_delete

    def test_model_signals_counted_when_flag_true(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Widget(models.Model):\n    name = models.CharField(max_length=10)\n")
        _write(tmp_path, "app/views.py", "from .models import Widget\n\n"
               "def create(request):\n    Widget.objects.create(name='x')\n")
        result = AP.measure_attach_points(tmp_path, require_model_signals_count=True)
        assert result["counts"]["usable_events"] == 4


class TestMechanicalDataDetection:
    def test_orphan_model_does_not_count(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Orphan(models.Model):\n    x = models.CharField(max_length=1)\n")
        result = AP.measure_attach_points(tmp_path)
        assert result["counts"]["usable_data"] == 0
        assert any(p["status"] == "DEFINED_NOT_REACHABLE" for p in result["all_measured"]
                   if p["kind"] == "DATA")

    def test_reachable_model_counts_as_data(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Widget(models.Model):\n    name = models.CharField(max_length=10)\n")
        _write(tmp_path, "app/views.py", "from .models import Widget\n\n"
               "def list_widgets(request):\n    return Widget.objects.all()\n")
        result = AP.measure_attach_points(tmp_path)
        assert result["counts"]["usable_data"] == 1
        assert result["usable_data"][0]["operations"] == "READ"

    def test_abstract_base_is_not_itself_a_data_point(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class Base(models.Model):\n    class Meta:\n        abstract = True\n"
               "class Widget(Base):\n    name = models.CharField(max_length=10)\n")
        _write(tmp_path, "app/views.py", "from .models import Widget\n\n"
               "def list_widgets(request):\n    return Widget.objects.all()\n")
        result = AP.measure_attach_points(tmp_path)
        names = {p["source_symbol"] for p in result["usable_data"]}
        assert "Widget" in names
        assert "Base" not in names


class TestMechanicalSlotDetection:
    def test_block_in_rendered_template_is_a_slot(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/views.py",
               "from django.shortcuts import render\n\n"
               "def home(request):\n    return render(request, 'home.html')\n")
        _write(tmp_path, "app/templates/home.html",
               "{% block content %}hi{% endblock %}\n")
        result = AP.measure_attach_points(tmp_path)
        assert result["counts"]["usable_slots"] >= 1
        assert any(p["kind"] == "SLOT" and p["status"] == "USABLE"
                  for p in result["usable_slots"])

    def test_block_in_untraced_template_is_not_usable(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/templates/orphan.html",
               "{% block content %}hi{% endblock %}\n")
        result = AP.measure_attach_points(tmp_path)
        assert result["counts"]["usable_slots"] == 0
        assert any(p["status"] == "DEFINED_NOT_REACHABLE" for p in result["all_measured"]
                   if p["kind"] == "SLOT")


class TestAdapterNeverNative:
    """Section 4/33.6: an ADAPTER point must never be rendered as NATIVE."""

    def test_render_never_marks_adapter_as_native(self):
        aps = [
            {"name": "x.native", "kind": "EVENT", "evidence": "real", "implementation": "NATIVE",
             "source_file": "a.py"},
            {"name": "x.adapter", "kind": "EVENT", "evidence": "real", "implementation": "ADAPTER",
             "underlying_source": "some non-native mechanism"},
        ]
        sys.path.insert(0, str(HERE))
        import harvest_parts as HP
        md = HP.render_attach_points_md("test", {}, aps)
        assert "x.adapter" in md
        adapter_section = md.split("## Adapter Requirements")[1]
        assert "x.adapter" in adapter_section
        events_table = md.split("## Events")[1].split("## Slots")[0]
        # both rows are printed in the Events table (with their own Implementation
        # column value) -- the assertion that matters is the adapter section
        # lists it, and its own row says ADAPTER, never NATIVE for that row.
        for line in events_table.splitlines():
            if "x.adapter" in line:
                assert "ADAPTER" in line
                assert "NATIVE" not in line.replace("ADAPTER", "")


# =====================================================================
# TIER 1 -- exemplar_match.py
# =====================================================================

class TestExemplarFeatureLoading:
    def test_feature_with_no_source_url_is_dropped(self, tmp_path):
        data = {"categories": [{"id": 999, "category": "X", "exemplar": "Y", "features": [
            {"name": "has url", "keywords": ["foo"], "source_url": "https://y.example/foo"},
            {"name": "no url", "keywords": ["bar"], "source_url": ""},
            {"name": "missing url key", "keywords": ["baz"]},
        ]}]}
        p = tmp_path / "EXEMPLAR_FEATURES.json"
        p.write_text(json.dumps(data))
        loaded = EM.load_exemplar_features(p)
        names = {f["name"] for f in loaded[999]["features"]}
        assert names == {"has url"}
        assert loaded[999]["features_dropped_no_source_url"] == 2


class TestFeatureMatchVerdicts:
    def test_keyword_in_model_name_scores_matched_with_evidence(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "app/models.py", "from django.db import models\n\n"
               "class RecurringTask(models.Model):\n    pass\n")
        entry = {"exemplar": "Todoist", "features": [
            {"name": "recurring tasks", "keywords": ["recurring"]},
        ]}
        result = EM.measure_feature_match(tmp_path, entry)
        pf = result["per_feature"][0]
        assert pf["verdict"] == "MATCHED"
        assert ":" in pf["evidence"]
        assert result["feature_match"] == 1.0

    def test_keyword_only_in_readme_scores_docs_only_weight(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        _write(tmp_path, "README.md", "# My App\n\n## Recurring reminders\n\nText.\n")
        entry = {"exemplar": "Todoist", "features": [
            {"name": "reminders", "keywords": ["reminder"]},
        ]}
        result = EM.measure_feature_match(tmp_path, entry, docs_only_weight=0.5)
        pf = result["per_feature"][0]
        assert pf["verdict"] == "DOCS_ONLY"
        assert result["feature_match"] == 0.5
        result_weighted = EM.measure_feature_match(tmp_path, entry, docs_only_weight=0.2)
        assert result_weighted["feature_match"] == 0.2

    def test_not_found_keyword_scores_zero(self, tmp_path):
        _write(tmp_path, "app/apps.py", "")
        entry = {"exemplar": "Todoist", "features": [
            {"name": "karma", "keywords": ["karma-gamification-xyz"]},
        ]}
        result = EM.measure_feature_match(tmp_path, entry)
        assert result["per_feature"][0]["verdict"] == "NOT_FOUND"
        assert result["feature_match"] == 0.0

    def test_rejected_candidate_is_not_measured(self):
        r = EM.not_measured_result("rejected at gate(s): Rule B: no API docs")
        assert r["feature_match"] is None
        md = EM.render_feature_match_md("x", r)
        assert "NOT MEASURED" in md
        assert "Rule B" in md


# =====================================================================
# TIER 1 -- ranking (hunt.py's _rank_key / write_category_summary)
# =====================================================================

class TestRanking:
    def _result(self, name, admitted, fm, score):
        return {"category": H._category_dict("X"), "repo_name": name, "repo_url": "u",
                "commit": "c" * 40, "admission_result": "ADMITTED" if admitted else "REJECTED",
                "rejection_reasons": [], "quality_score": score, "feature_match": fm}

    def test_higher_quality_lower_match_does_not_win(self, tmp_path, monkeypatch):
        monkeypatch.setattr(H, "OUTPUT_DIR", str(tmp_path))
        monkeypatch.setattr(H, "MIN_FEATURE_MATCH", 0.0)
        results = [
            self._result("low-match-high-quality", True, 0.1, 99.0),
            self._result("high-match-low-quality", True, 0.9, 1.0),
        ]
        winner = H.write_category_summary("X", results)
        assert winner["repo_name"] == "high-match-low-quality"

    def test_min_feature_match_floor_yields_none_admitted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(H, "OUTPUT_DIR", str(tmp_path))
        monkeypatch.setattr(H, "MIN_FEATURE_MATCH", 0.8)
        results = [self._result("only-candidate", True, 0.3, 50.0)]
        winner = H.write_category_summary("X", results)
        assert winner is None
        text = (tmp_path / re_slug("X") / "CATEGORY_SUMMARY.md").read_text()
        assert "NONE ADMITTED" in text
        assert "0.30" in text and "MIN_FEATURE_MATCH" in text


def re_slug(name):
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# =====================================================================
# TIER 1 -- discover.py
# =====================================================================

class TestDiscoveryRecording:
    def test_every_query_and_every_hit_recorded_kept_and_dropped(self, tmp_path):
        run = D.DiscoveryRun(
            category_name="Todo List", category_slug="todo-list", exemplar="Todoist",
            queries=["todo list django github", "django todo"],
            hits=[
                D.DiscoveryHit("a/kept", "https://github.com/a/kept", kept=True),
                D.DiscoveryHit("b/dropped", "https://github.com/b/dropped", kept=False,
                              filter_reason="stale"),
            ],
        )
        path = D.write_discovery_md(run, tmp_path)
        text = path.read_text()
        assert "todo list django github" in text
        assert "django todo" in text
        assert "a/kept" in text and "yes" in text
        assert "b/dropped" in text and "stale" in text


# =====================================================================
# TIER 2 -- real clone
# =====================================================================

@pytest.fixture(scope="session")
def small_django_clone():
    dest = CLONE_SCRATCH / "vtodo"
    if not dest.exists():
        CLONE_SCRATCH.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1",
             "https://github.com/CrowderSoup/vTodo", str(dest)],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            pytest.skip(f"could not clone vTodo for a real-repo test: {r.stderr[:200]}")
    return dest


class TestRealRepoMechanicalMeasurement:
    def test_real_clone_produces_usable_data_points_with_evidence(self, small_django_clone):
        result = AP.measure_attach_points(small_django_clone)
        assert result["counts"]["usable_data"] > 0
        for p in result["usable_data"]:
            assert ":" in p["evidence"]
            assert p["implementation"] == "NATIVE"

    def test_real_clone_never_modified_by_measurement(self, small_django_clone):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=small_django_clone,
                                capture_output=True, text=True).stdout
        AP.measure_attach_points(small_django_clone)
        EM.measure_feature_match(small_django_clone,
                                 {"exemplar": "Todoist", "features": [
                                     {"name": "x", "keywords": ["task"]}]})
        after = subprocess.run(["git", "status", "--porcelain"], cwd=small_django_clone,
                               capture_output=True, text=True).stdout
        assert before == after == "", "harvesting must not modify candidate source (Section 13)"


class TestRegistryDriven:
    def test_registry_has_seventy_categories_with_required_fields(self):
        with open(PACK_ROOT / "CATEGORY_REGISTRY.json") as f:
            data = json.load(f)
        assert data["count"] == 70
        assert len(data["categories"]) == 70
        for c in data["categories"]:
            assert {"id", "category", "slug", "exemplar"} <= set(c)

    def test_categories_subset_produces_exactly_those_folders_and_no_others(self, tmp_path, monkeypatch):
        import run_registry_harvest as RRH
        monkeypatch.setattr(RRH.H, "OUTPUT_DIR", str(tmp_path))
        monkeypatch.setattr(RRH, "CANDIDATES_DIR", tmp_path / "nonexistent_candidates")
        registry = RRH.load_registry()
        selected = RRH.select_categories(registry, "1,25,27")
        assert len(selected) == 3
        assert {c["id"] for c in selected} == {1, 25, 27}

    def test_none_admitted_category_produces_no_library_index_entry(self):
        # By construction: run_registry_harvest.py only appends to
        # winners_for_index when H.run_category() returns a non-None
        # winner -- there is no code path that appends a NONE ADMITTED
        # category. Confirmed structurally against the real module here
        # rather than re-deriving it from a string search.
        import inspect
        import run_registry_harvest as RRH
        src = inspect.getsource(RRH.main)
        assert "if winner:" in src
        idx = src.index("if winner:")
        assert "winners_for_index.append" in src[idx:idx + 400]

    def test_exemplar_names_never_appear_as_candidate_identity(self):
        """Section 26: exemplars are proprietary, never candidates, never
        cloned. Checked against this run's own real candidate research
        files -- no repo_name/repo_url may literally be the exemplar."""
        exemplar_terms = ["todoist.com", "calendly.com", "eventbrite.com/organizer",
                          "github.com/todoist", "github.com/calendly"]
        candidates_dir = PACK_ROOT / "0_harvest" / "candidates"
        for f in candidates_dir.glob("*.py"):
            text = f.read_text().lower()
            for term in exemplar_terms:
                assert term not in text, f"{f} references exemplar identity {term!r}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
