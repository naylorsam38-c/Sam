"""The agent's own policy classifier — an independent copy of
workstation_core.policy_engine, loading the same config/policies.yaml file
but with its own code path (see that module's SECURITY NOTE and
docs/SECURITY.md). This is what actually decides whether an operation runs;
whatever the control plane decided is not trusted.

RESTRICTED (as a classify() result, whether from explicit config or from
failing the allowed_paths/allowed_commands check) always means "refuse,
no approval token can override this." APPROVAL means "only run if the
request carries a non-empty approval_token" (proof the control plane's own
human-approval step happened — see agent/main.py). TRUSTED means "run
regardless of approval_token."
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

PolicyLevel = Literal["RESTRICTED", "APPROVAL", "TRUSTED"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]

_VALID_LEVELS = {"RESTRICTED", "APPROVAL", "TRUSTED"}
_VALID_RISKS = {"LOW", "MEDIUM", "HIGH"}


class PolicyRule:
    def __init__(self, raw: dict[str, Any]):
        self.operation: str = raw["operation"]
        level = raw.get("level", "APPROVAL")
        risk = raw.get("risk", "MEDIUM")
        self.level: PolicyLevel = level if level in _VALID_LEVELS else "APPROVAL"
        self.risk: RiskLevel = risk if risk in _VALID_RISKS else "MEDIUM"
        self.allowed_paths: list[str] = raw.get("allowed_paths", [])
        self.allowed_commands: list[str] = raw.get("allowed_commands", [])


class PolicyEngine:
    def __init__(self, rules: list[PolicyRule]):
        self._rules = {r.operation: r for r in rules}

    @classmethod
    def load(cls, path: Path) -> "PolicyEngine":
        if not path.exists():
            return cls([])
        data = yaml.safe_load(path.read_text()) or {}
        return cls([PolicyRule(r) for r in data.get("operations", [])])

    def rule_for(self, operation: str) -> PolicyRule | None:
        return self._rules.get(operation)

    def classify(self, operation: str, parameters: dict[str, Any]) -> tuple[PolicyLevel, RiskLevel, str]:
        """Returns (level, risk, reason). reason is only meaningful when
        level == RESTRICTED, explaining why."""
        rule = self._rules.get(operation)
        if rule is None:
            return "RESTRICTED", "HIGH", f"operation '{operation}' is not defined in policies.yaml"

        if rule.allowed_commands:
            command = str(parameters.get("command", ""))
            binary = command.strip().split(" ")[0] if command.strip() else ""
            if binary not in rule.allowed_commands:
                return "RESTRICTED", "HIGH", f"command '{binary}' is not in allowed_commands for '{operation}'"

        if rule.allowed_paths:
            target = str(parameters.get("path") or parameters.get("working_directory") or "")
            if target and not any(is_within(target, allowed) for allowed in rule.allowed_paths):
                return "RESTRICTED", "HIGH", f"path '{target}' is outside allowed_paths for '{operation}'"

        return rule.level, rule.risk, "ok"


def is_within(target: str, allowed_root: str) -> bool:
    try:
        target_path = Path(target).expanduser().resolve()
        allowed_path = Path(allowed_root).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    return target_path == allowed_path or allowed_path in target_path.parents
