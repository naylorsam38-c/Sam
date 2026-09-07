"""Control-plane policy classifier, used to pre-classify a requested laptop
action's risk level so an Approval record can be created before the local
agent is ever contacted (spec section 17).

SECURITY NOTE: this is deliberately NOT imported by local-agent. The agent
carries its own independent copy of this logic (local-agent/src/agent/policy)
so that a compromised or buggy control plane cannot bypass the laptop-side
enforcement boundary (spec: "the agent must enforce policy locally even if
the cloud service requests otherwise"). Keep the two in sync when editing
config/policies.yaml semantics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from workstation_core.enums import PolicyLevel, RiskLevel

DEFAULT_LEVEL = PolicyLevel.APPROVAL
DEFAULT_RISK = RiskLevel.MEDIUM


class PolicyRule:
    def __init__(self, raw: dict[str, Any]):
        self.operation: str = raw["operation"]
        self.level: PolicyLevel = PolicyLevel(raw.get("level", DEFAULT_LEVEL.value))
        self.risk: RiskLevel = RiskLevel(raw.get("risk", DEFAULT_RISK.value))
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
        rules = [PolicyRule(r) for r in data.get("operations", [])]
        return cls(rules)

    def classify(self, operation: str, parameters: dict[str, Any]) -> tuple[PolicyLevel, RiskLevel]:
        rule = self._rules.get(operation)
        if rule is None:
            # Unknown operation: fail closed to the strictest posture.
            return PolicyLevel.RESTRICTED, RiskLevel.HIGH

        level = rule.level
        risk = rule.risk

        if rule.allowed_commands:
            command = str(parameters.get("command", ""))
            binary = command.strip().split(" ")[0] if command.strip() else ""
            if binary not in rule.allowed_commands:
                return PolicyLevel.RESTRICTED, RiskLevel.HIGH

        if rule.allowed_paths:
            target = str(parameters.get("path") or parameters.get("working_directory") or "")
            if target and not any(_is_within(target, allowed) for allowed in rule.allowed_paths):
                return PolicyLevel.RESTRICTED, RiskLevel.HIGH

        return level, risk


def _is_within(target: str, allowed_root: str) -> bool:
    try:
        target_path = Path(target).expanduser().resolve()
        allowed_path = Path(allowed_root).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    return target_path == allowed_path or allowed_path in target_path.parents
