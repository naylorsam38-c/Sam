"""Unit tests for the control-plane policy classifier
(workstation_core.policy_engine — the agent's own independent copy is
tested separately in local-agent/tests)."""

from pathlib import Path

import yaml

from workstation_core.policy_engine import PolicyEngine


def _engine(tmp_path: Path, operations: list[dict]) -> PolicyEngine:
    path = tmp_path / "policies.yaml"
    path.write_text(yaml.safe_dump({"operations": operations}))
    return PolicyEngine.load(path)


def test_unknown_operation_fails_closed_to_restricted_high(tmp_path):
    engine = _engine(tmp_path, [])
    level, risk = engine.classify("delete_everything", {})
    assert level.value == "RESTRICTED"
    assert risk.value == "HIGH"


def test_configured_level_and_risk_are_honoured_within_bounds(tmp_path):
    engine = _engine(tmp_path, [
        {"operation": "read_file", "level": "APPROVAL", "risk": "LOW", "allowed_paths": [str(tmp_path)]},
    ])
    level, risk = engine.classify("read_file", {"path": str(tmp_path / "f.txt")})
    assert level.value == "APPROVAL"
    assert risk.value == "LOW"


def test_path_outside_allowed_paths_forces_restricted_regardless_of_configured_level(tmp_path):
    engine = _engine(tmp_path, [
        {"operation": "read_file", "level": "TRUSTED", "risk": "LOW", "allowed_paths": [str(tmp_path / "ws")]},
    ])
    level, risk = engine.classify("read_file", {"path": "/etc/passwd"})
    assert level.value == "RESTRICTED"
    assert risk.value == "HIGH"


def test_command_outside_allowlist_forces_restricted(tmp_path):
    engine = _engine(tmp_path, [
        {"operation": "run_command", "level": "APPROVAL", "risk": "MEDIUM",
         "allowed_paths": [str(tmp_path)], "allowed_commands": ["git", "npm"]},
    ])
    level, _risk = engine.classify("run_command", {"command": "rm -rf /", "working_directory": str(tmp_path)})
    assert level.value == "RESTRICTED"


def test_command_within_allowlist_and_path_passes(tmp_path):
    engine = _engine(tmp_path, [
        {"operation": "run_command", "level": "APPROVAL", "risk": "MEDIUM",
         "allowed_paths": [str(tmp_path)], "allowed_commands": ["git", "npm"]},
    ])
    level, _risk = engine.classify("run_command", {"command": "git status", "working_directory": str(tmp_path)})
    assert level.value == "APPROVAL"


def test_missing_policies_file_yields_empty_engine_that_still_fails_closed(tmp_path):
    engine = PolicyEngine.load(tmp_path / "does-not-exist.yaml")
    level, risk = engine.classify("read_file", {"path": "/anything"})
    assert level.value == "RESTRICTED"
    assert risk.value == "HIGH"


def test_symlink_or_traversal_path_resolves_before_the_bounds_check(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    engine = _engine(tmp_path, [
        {"operation": "read_file", "level": "APPROVAL", "risk": "LOW", "allowed_paths": [str(workspace)]},
    ])
    traversal_path = str(workspace / ".." / "outside" / "secret.txt")
    level, _risk = engine.classify("read_file", {"path": traversal_path})
    assert level.value == "RESTRICTED"
