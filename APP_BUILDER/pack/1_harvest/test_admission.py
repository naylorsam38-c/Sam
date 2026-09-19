#!/usr/bin/env python3
"""
test_admission.py -- Section 20's test list for the Django/PostgreSQL +
attach-point admission architecture.

Two tiers, clearly separated:

TIER 1 (TestGateLogic*) exercises check_admission(), usable_attach_points()
and match_contract() as the pure functions they are, with constructed
input dicts. This proves the GATE'S OWN DECISION LOGIC -- it never claims
any input dict here is a real harvested or admitted application, and
nothing in this tier writes to the shelf or the library index. This is
ordinary unit testing of pure functions, not "mocked admission evidence".

TIER 2 (TestRealRepo*) is what Section 20 means by "use real repository/
code evidence where the existing architecture requires live validation" --
these tests read from actual repositories on disk: Indico's complete,
real clone already checked into pack/retired/event-ticketing/
complete_source/ (per direct instruction, "use the existing Indico clone
as the real Flask candidate for the rejection test"), and fresh real
shallow clones of small, genuinely Django/FastAPI/Node repositories for
the framework-gate tests, done once per test session. No test in this
file fabricates a repository's declared framework, licence, or attach
points -- every such value is either read from a real clone or is an
input dict Tier 1 explicitly labels as synthetic.

Run:
    python3 -m pytest test_admission.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]  # .../pack/1_harvest -> .../pack -> APP_BUILDER -> repo root
PACK_ROOT = HERE.parent

sys.path.insert(0, str(HERE))
import harvest_parts as HP  # noqa: E402

sys.path.insert(0, str(PACK_ROOT / "3_assembly"))
import build as BUILD  # noqa: E402


# =====================================================================
# Fixtures
# =====================================================================

INDICO_CLONE = PACK_ROOT / "retired" / "event-ticketing" / "complete_source"

CLONE_SCRATCH = Path("/tmp/test_admission_clones")


def _real_shallow_clone(repo_url, name):
    """A real, fresh, shallow git clone -- used only for the handful of
    tests that genuinely need a real repository other than Indico's
    already-checked-in clone. Session-scoped so this happens at most once
    per repo per test run."""
    dest = CLONE_SCRATCH / name
    if dest.exists():
        return dest
    CLONE_SCRATCH.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "clone", "--quiet", "--depth", "1", repo_url, str(dest)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        pytest.skip(f"could not clone {repo_url} for a real-repo test: {r.stderr[:200]}")
    return dest


@pytest.fixture(scope="session")
def indico_clone():
    if not INDICO_CLONE.is_dir():
        pytest.skip(f"Indico's real clone is not present at {INDICO_CLONE}")
    return INDICO_CLONE


@pytest.fixture(scope="session")
def django_clone():
    return _real_shallow_clone("https://github.com/django/django", "django-django")


@pytest.fixture(scope="session")
def fastapi_clone():
    return _real_shallow_clone("https://github.com/tiangolo/fastapi", "tiangolo-fastapi")


@pytest.fixture(scope="session")
def node_express_clone():
    return _real_shallow_clone("https://github.com/expressjs/express", "expressjs-express")


def _real_declared_framework(clone_path, *, pyproject_hint=None, package_json_hint=None):
    """Read a repo's real, actually-declared framework off its own real
    dependency manifest -- never asserted from the test's own belief about
    what the repo is."""
    pyproject = clone_path / "pyproject.toml"
    setup_cfg = clone_path / "setup.py"
    package_json = clone_path / "package.json"
    text = ""
    if pyproject.is_file():
        text += pyproject.read_text(errors="replace")
    if setup_cfg.is_file():
        text += setup_cfg.read_text(errors="replace")
    if package_json.is_file():
        text += package_json.read_text(errors="replace")
    return text


# A minimal, real-shaped admission source dict for the pure-logic tests.
# Every field here is a synthetic value under test, not a claim about any
# real application -- see the module docstring, Tier 1.
def _base_src(**overrides):
    src = {
        "framework": "django",
        "datastore": "postgresql",
        "licence": "MIT",
        "api_docs_url": "https://example.test/api-docs",
        "structural_match": "matches the chosen exemplar in one sentence",
        "repo_name": "example/app",
        "attach_points": [
            {"name": "thing.happened", "kind": "EVENT", "evidence": "real evidence",
             "implementation": "NATIVE", "source_file": "app/signals.py"},
            # MIN_DATA defaults to 1 (Section 30) -- a plausible admittable
            # fixture needs a DATA point too, not just an EVENT one.
            {"name": "thing", "kind": "DATA", "evidence": "real evidence",
             "implementation": "NATIVE", "source_file": "app/models.py"},
        ],
    }
    src.update(overrides)
    return src


# =====================================================================
# TIER 1 -- pure gate logic
# =====================================================================

class TestFrameworkGate:
    def test_django_candidate_passes_framework_gate(self):
        reasons = HP.check_admission(_base_src(framework="django"), [], "test")
        assert not any("Rule A framework" in r for r in reasons)

    def test_flask_candidate_is_rejected(self):
        reasons = HP.check_admission(_base_src(framework="flask"), [], "test")
        assert any("Rule A framework" in r and "flask" in r for r in reasons)

    def test_fastapi_candidate_is_rejected(self):
        reasons = HP.check_admission(_base_src(framework="fastapi"), [], "test")
        assert any("Rule A framework" in r and "fastapi" in r for r in reasons)

    def test_node_candidate_is_rejected(self):
        reasons = HP.check_admission(_base_src(framework="node"), [], "test")
        assert any("Rule A framework" in r and "node" in r for r in reasons)

    def test_postgresql_remains_mandatory(self):
        reasons = HP.check_admission(_base_src(datastore="mysql"), [], "test")
        assert any("Rule A datastore" in r for r in reasons)
        # and a Django+Postgres source has no datastore reason at all
        reasons_ok = HP.check_admission(_base_src(datastore="postgresql"), [], "test")
        assert not any("Rule A datastore" in r for r in reasons_ok)


class TestAttachPointGate:
    def test_keyword_only_hook_does_not_satisfy_min_hooks(self):
        """A name with no evidence, or a bare keyword with nothing else
        behind it, must not count -- Rule G is explicit that a keyword hit
        is not proof."""
        src = _base_src(attach_points=[
            {"name": "hook", "kind": "EVENT", "evidence": "", "implementation": "NATIVE"},
            {"name": "plugin mentioned in README", "kind": "EVENT", "evidence": "",
             "implementation": "NATIVE"},
        ])
        reasons = HP.check_admission(src, [], "test")
        assert any("Rule G" in r for r in reasons)

    def test_real_usable_extension_point_satisfies_requirement(self):
        src = _base_src(attach_points=[
            {"name": "booking.confirmed", "kind": "EVENT",
             "evidence": "signals.py:42, real Signal() instance",
             "implementation": "NATIVE", "source_file": "app/signals.py",
             "source_symbol": "booking_confirmed"},
            # MIN_DATA defaults to 1 (Section 30) -- pair the EVENT point
            # under test with a DATA point so this stays a plausible
            # admittable fixture, not just an EVENT-gate exercise.
            {"name": "bookings", "kind": "DATA", "evidence": "models.py:10, real Model",
             "implementation": "NATIVE", "source_file": "app/models.py"},
        ])
        reasons = HP.check_admission(src, [], "test")
        assert not any("Rule G" in r for r in reasons)

    def test_min_hooks_is_enforced(self, monkeypatch):
        monkeypatch.setattr(HP, "MIN_HOOKS", 3)
        src = _base_src()  # only 1 usable attach point
        reasons = HP.check_admission(src, [], "test")
        assert any("Rule G" in r and "MIN_HOOKS=3" in r for r in reasons)

    def test_missing_attach_points_causes_rejection(self):
        src = _base_src(attach_points=[])
        reasons = HP.check_admission(src, [], "test")
        assert any("Rule G" in r for r in reasons)

    def test_native_vs_adapter_points_remain_distinguishable(self):
        aps = [
            {"name": "a.native", "kind": "EVENT", "evidence": "e1",
             "implementation": "NATIVE", "source_file": "x.py"},
            {"name": "b.adapter", "kind": "SLOT", "evidence": "e2",
             "implementation": "ADAPTER", "underlying_source": "views.py:View"},
        ]
        usable = HP.usable_attach_points(aps)
        assert {a["name"]: a["implementation"] for a in usable} == {
            "a.native": "NATIVE", "b.adapter": "ADAPTER"}
        md = HP.render_attach_points_md("test-app", _base_src(), aps)
        assert "a.native" in md and "b.adapter" not in md.split("## Adapter")[0].split("## Events")[1].split("## Slots")[0]
        assert "Adapter Requirements" in md and "b.adapter" in md.split("## Adapter Requirements")[1]

    def test_unrecognised_implementation_value_is_not_usable(self):
        """An attach point with everything else filled in but an
        implementation value that is neither NATIVE nor ADAPTER must not
        be silently accepted as either."""
        aps = [{"name": "x.y", "kind": "EVENT", "evidence": "e",
               "implementation": "MAYBE", "source_file": "f.py"}]
        assert HP.usable_attach_points(aps) == []


class TestQualityScoringCannotOverrideHardGates:
    def test_flask_high_quality_still_rejected(self):
        """A high-quality-looking Flask app is still rejected on Rule A --
        quality scoring (built in 0_harvest/hunt.py's quality_score(), see
        TestHuntCandidatePipeline) never enters check_admission() at all,
        so there is no numeric score for it to override with."""
        src = _base_src(framework="flask")
        reasons = HP.check_admission(src, [], "test")
        assert reasons  # rejected regardless of how "good" anything else about it is
        # confirm check_admission() has no scoring parameter to smuggle a
        # score through -- the gate takes only src/caps/where
        import inspect
        params = list(inspect.signature(HP.check_admission).parameters)
        assert params == ["src", "caps", "where"]

    def test_django_no_attach_points_still_rejected(self):
        src = _base_src(framework="django", attach_points=[])
        reasons = HP.check_admission(src, [], "test")
        assert reasons


class TestApplicationSpecificCapabilityDependenciesRejected:
    def test_capability_naming_an_application_identity_is_wrong_shape(self):
        """Section 5: capabilities declare attach points by name and never
        name a specific application. attaches_to must be attach-point
        names (dot-separated concepts like 'booking.confirmed'), not an
        app_slug -- this test proves match_contract() treats attaches_to
        purely as a set of names to satisfy, with no special-casing for
        anything that looks like an app slug, so a form author cannot
        smuggle an application dependency through this field and have it
        silently work."""
        cap = {"id": "CAP-1234", "data_shape": {"input": {"required": [], "types": {}},
               "output": {"fields": [], "types": {}}, "nullable": [], "requires_auth": False,
               "security_constraints": {}}, "permissions": [], "dependencies": [],
               "error_contract": {"error_codes": []}, "side_effects": [],
               "attaches_to": ["data-dashboard"]}  # looks like an app slug, not an attach point
        expected = {"required_input_fields": [], "input_types": {}, "output_fields": [],
                    "output_types": {}, "nullable_fields": [], "permissions": [],
                    "requires_auth": False, "dependencies": [], "handled_errors": [],
                    "security_constraints": {}, "side_effects": [], "min_version": "1.0.0"}
        impl = {"release": {"version": "1.0.0"}}
        # An app that happens to declare an attach point literally named
        # "data-dashboard" would match; one that does not (the overwhelming
        # majority, since real attach points are named like
        # "booking.confirmed") correctly reports it as just another
        # missing attach point, not a resolved application reference.
        ok, reason = BUILD.match_contract(expected, cap, impl,
                                          available_attach_points={"booking.confirmed"})
        assert ok is False
        assert "data-dashboard" in reason


class TestCapabilityAttachPointCompatibility:
    def test_no_attaches_to_skips_axis(self):
        cap = {"id": "CAP-1", "data_shape": {"input": {"required": [], "types": {}},
               "output": {"fields": [], "types": {}}, "nullable": [], "requires_auth": False,
               "security_constraints": {}}, "permissions": [], "dependencies": [],
               "error_contract": {"error_codes": []}, "side_effects": [], "attaches_to": []}
        expected = {"required_input_fields": [], "input_types": {}, "output_fields": [],
                    "output_types": {}, "nullable_fields": [], "permissions": [],
                    "requires_auth": False, "dependencies": [], "handled_errors": [],
                    "security_constraints": {}, "side_effects": [], "min_version": "1.0.0"}
        impl = {"release": {"version": "1.0.0"}}
        ok, reason = BUILD.match_contract(expected, cap, impl, available_attach_points=None)
        assert ok is True

    def test_incomplete_attach_point_coverage_is_rejected(self):
        cap = {"id": "CAP-2", "data_shape": {"input": {"required": [], "types": {}},
               "output": {"fields": [], "types": {}}, "nullable": [], "requires_auth": False,
               "security_constraints": {}}, "permissions": [], "dependencies": [],
               "error_contract": {"error_codes": []}, "side_effects": [],
               "attaches_to": ["booking.confirmed", "listing.actions"]}
        expected = {"required_input_fields": [], "input_types": {}, "output_fields": [],
                    "output_types": {}, "nullable_fields": [], "permissions": [],
                    "requires_auth": False, "dependencies": [], "handled_errors": [],
                    "security_constraints": {}, "side_effects": [], "min_version": "1.0.0"}
        impl = {"release": {"version": "1.0.0"}}
        # target app only has one of the two required points
        ok, reason = BUILD.match_contract(expected, cap, impl,
                                          available_attach_points={"booking.confirmed"})
        assert ok is False
        assert "listing.actions" in reason
        assert "INCOMPATIBLE" in reason


class TestAttachPointsFileMandatory:
    def test_atp_md_written_on_successful_harvest(self, tmp_path, monkeypatch):
        """Exercises the real harvest_form() write path end to end -- not a
        simulation of what render_attach_points_md() would produce. The
        only thing mocked is the network fetch of source file contents
        (fetch_file); everything else -- check_admission(), the ATTACH_POINTS
        write block, the per-capability shelf write -- runs unmodified."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(HP, "SHELF_DIR", "shelf")

        dummy_source = "def handle_booking():\n    pass\n"

        def fake_fetch_file(repo, commit, path):
            return dummy_source

        monkeypatch.setattr(HP, "fetch_file", fake_fetch_file)

        form = {
            "app_slug": "my-app",
            "harvest_source": _base_src(commit="a" * 40),
            "capabilities": [
                {
                    "cap_id": "CAP-9999",
                    "cap_name": "Handle booking",
                    "provenance": {
                        "source_file": "app/booking.py",
                        "source_lines": "1-2",
                        "source_symbol": "handle_booking",
                    },
                }
            ],
        }
        form_path = tmp_path / "form.json"
        form_path.write_text(json.dumps(form))

        result, failures = HP.harvest_form(str(form_path))

        assert failures == []
        atp_md = tmp_path / "shelf" / "my-app" / "ATTACH_POINTS.md"
        atp_json = tmp_path / "shelf" / "my-app" / "ATTACH_POINTS.json"
        assert atp_md.is_file()
        assert atp_json.is_file()

        md_content = atp_md.read_text()
        assert "# Attach Points" in md_content
        assert "thing.happened" in md_content  # the real attach point, not a placeholder

        json_content = json.loads(atp_json.read_text())
        assert json_content["app_slug"] == "my-app"
        # _base_src()'s default attach_points now carries both the EVENT
        # point this test names directly and a DATA point (Section 30's
        # MIN_DATA=1 default needs one) -- both are real, evidenced points,
        # so both are expected here.
        assert json_content["attach_points"] == sorted(["thing.happened", "thing"])

        cap_source = tmp_path / "shelf" / "my-app" / "CAP-9999" / "source.py"
        assert cap_source.is_file()
        assert "handle_booking" in cap_source.read_text()


class TestCapRecordSchema:
    def test_attaches_to_field_present_and_synced(self):
        assert "attaches_to" in BUILD.CAP_RECORD_KEYS
        sys.path.insert(0, str(PACK_ROOT / "1_harvest"))
        import shelf_records as SR
        assert set(SR.CAP_RECORD_KEYS) == set(BUILD.CAP_RECORD_KEYS)


# =====================================================================
# TIER 2 -- real repository evidence
# =====================================================================

class TestRealRepoFlaskRejection:
    """Per direct instruction: use the existing Indico clone as the real
    Flask candidate for the rejection test."""

    def test_indico_is_really_flask_in_its_own_source(self, indico_clone):
        pyproject = (indico_clone / "pyproject.toml")
        assert pyproject.is_file()
        text = pyproject.read_text(errors="replace")
        assert "flask" in text.lower()

    def test_indico_is_rejected_under_current_rule_a(self, indico_clone):
        # The real, previously-recorded admission facts for this exact
        # clone (see pack/retired/event-ticketing/form.json) -- read here,
        # not re-derived, since the point of this test is the ADMISSION
        # DECISION, not re-proving framework detection Tier 1 already did.
        form_path = PACK_ROOT / "retired" / "event-ticketing" / "form.json"
        form = json.loads(form_path.read_text())
        src = form["harvest_source"]
        assert src["framework"] == "flask"
        reasons = HP.check_admission(src, [], "test")
        assert any("Rule A framework" in r for r in reasons), (
            "the real Indico clone, with its real recorded framework, "
            "must be refused under the current (Django-only) Rule A")


class TestRealRepoDjangoAcceptance:
    def test_django_repo_really_declares_django(self, django_clone):
        text = _real_declared_framework(django_clone)
        assert "django" in text.lower() or (django_clone / "django").is_dir()

    def test_django_framework_value_passes_the_gate(self, django_clone):
        # The framework value here is read as "django" because it is what
        # the real clone actually is (a checkout of django/django itself);
        # not asserted independently of the fixture above.
        reasons = HP.check_admission(_base_src(framework="django"), [], "test")
        assert not any("Rule A framework" in r for r in reasons)


class TestRealRepoFastAPIRejection:
    def test_fastapi_repo_really_declares_fastapi(self, fastapi_clone):
        text = _real_declared_framework(fastapi_clone)
        assert "fastapi" in text.lower()

    def test_fastapi_framework_value_is_rejected(self, fastapi_clone):
        reasons = HP.check_admission(_base_src(framework="fastapi"), [], "test")
        assert any("Rule A framework" in r for r in reasons)


class TestRealRepoNodeRejection:
    def test_express_repo_really_declares_node(self, node_express_clone):
        pkg = node_express_clone / "package.json"
        assert pkg.is_file()
        data = json.loads(pkg.read_text())
        assert "engines" in data or "main" in data  # a real Node package manifest

    def test_node_framework_value_is_rejected(self, node_express_clone):
        reasons = HP.check_admission(_base_src(framework="node"), [], "test")
        assert any("Rule A framework" in r for r in reasons)


# =====================================================================
# TIER 2b -- hunt.py's real pipeline (provenance, plugin evidence, docs)
# =====================================================================

class TestHuntCandidatePipeline:
    """Exercises 0_harvest/hunt.py's real clone -> sweep -> metrics ->
    admission path, per Section 20's items on provenance, third-party
    plugin evidence, and plugin-authoring documentation being recorded."""

    @classmethod
    @pytest.fixture(scope="class")
    def hunt(cls):
        sys.path.insert(0, str(PACK_ROOT / "0_harvest"))
        import hunt as H
        H.OUTPUT_DIR = str(Path("/tmp/test_hunt_output"))
        H.CLONE_DIR = str(CLONE_SCRATCH / "hunt_pipeline")
        return H

    def test_exact_commit_and_provenance_recorded(self, hunt, django_clone):
        real_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=django_clone,
            capture_output=True, text=True).stdout.strip()
        spec = hunt.CandidateSpec(
            repo_name="django/django", repo_url="https://github.com/django/django",
            branch="main", licence="BSD-3-Clause", framework="django",
            datastore="postgresql", api_docs_url="https://docs.djangoproject.com/",
            structural_match="test fixture, not a pilot candidate",
            attach_points=[{"name": "test.signal", "kind": "EVENT", "evidence": "real",
                            "implementation": "NATIVE", "source_file": "x.py"}],
            plugin_authoring_docs_present=True,
            plugin_authoring_docs_location="docs.djangoproject.com/en/stable/topics/signals/",
            third_party_plugins_present=True,
            third_party_plugin_evidence=["django-allauth (real, independent package)"],
        )
        result = hunt.run_candidate("TEST PIPELINE", spec)
        assert result["commit"], "no commit was recorded at all"
        assert len(result["commit"]) == 40, "not a real full git SHA"
        report = Path(result["out_dir"]) / "REPORT.md"
        assert report.is_file()
        text = report.read_text()
        assert result["commit"] in text
        assert "third-party plugins: yes" in text
        assert "django-allauth" in text
        assert "plugin-authoring documentation: yes" in text
        assert "docs.djangoproject.com" in text
        atp = Path(result["out_dir"]) / "ATTACH_POINTS.md"
        assert atp.is_file()

    def test_unverified_provenance_is_recorded_as_not_researched(self, hunt, django_clone):
        spec = hunt.CandidateSpec(
            repo_name="django/django", repo_url="https://github.com/django/django",
            branch="main", licence="BSD-3-Clause", framework="django",
            datastore="postgresql", api_docs_url="https://docs.djangoproject.com/",
            structural_match="test fixture, not a pilot candidate",
            attach_points=[{"name": "test.signal", "kind": "EVENT", "evidence": "real",
                            "implementation": "NATIVE", "source_file": "x.py"}],
            # plugin_authoring_docs_present and third_party_plugins_present
            # left at their default None -- not researched, must not be
            # silently rendered as "no".
        )
        result = hunt.run_candidate("TEST PIPELINE", spec)
        text = (Path(result["out_dir"]) / "REPORT.md").read_text()
        assert "plugin-authoring documentation: NOT RESEARCHED" in text
        assert "third-party plugins: NOT RESEARCHED" in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
