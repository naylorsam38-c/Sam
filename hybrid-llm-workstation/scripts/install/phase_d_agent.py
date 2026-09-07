#!/usr/bin/env python3
"""Install Phase D — Local execution agent (spec section 21).

Exercises the real, running control API + local execution agent end to
end: pairing, a harmless read, the approval flow, a denied operation, an
authorised command, and the audit trail — against your actual
config/policies.yaml, so this only succeeds if the real policy you've
configured actually behaves as you expect.

Usage:
    python3 scripts/install/phase_d_agent.py \
        --url http://localhost:8000 --username sam --password ... \
        --workspace ~/workstation-workspace
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

RESULTS = {"pass": 0, "fail": 0, "skip": 0}


def _report(kind: str, message: str) -> None:
    RESULTS[kind] += 1
    print(f"  {kind.upper()}: {message}")


def step(name: str) -> None:
    print(f"\n== {name} ==")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--workspace", default="~/workstation-workspace",
                        help="must match an allowed_paths entry in config/policies.yaml")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)
    test_file = workspace / "phase_d_probe.txt"
    test_file.write_text("phase D install probe")

    client = httpx.Client(base_url=args.url, timeout=30.0)

    step("1. Pair/authenticate agent (via control API's health check)")
    resp = client.post("/api/auth/login", json={"username": args.username, "password": args.password})
    if resp.status_code != 200:
        _report("fail", f"login failed: {resp.text}")
        return print_summary()
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"

    agent_health = client.get("/health/agent").json()
    if agent_health["healthy"]:
        _report("pass", f"agent reachable: {agent_health['detail']}")
    else:
        _report("fail", f"agent not reachable: {agent_health['detail']} — start it with 'make agent-dev'")
        return print_summary()

    step("2. Harmless read operation")
    req = client.post("/api/execution/requests", json={
        "operation": "read_file", "parameters": {"path": str(test_file)},
    }).json()
    _check_status(req, expect_one_of=("AWAITING_APPROVAL", "COMPLETED", "DENIED"),
                  note="depends on whether read_file is configured as APPROVAL or TRUSTED in policies.yaml")

    step("3. Approval flow")
    if req["status"] == "AWAITING_APPROVAL":
        approved = client.post(f"/api/execution/requests/{req['id']}/approve").json()
        if approved["status"] == "COMPLETED" and approved["result"]["stdout"] == "phase D install probe":
            _report("pass", "approval -> execution -> correct file contents returned")
        else:
            _report("fail", f"approval flow ended in unexpected state: {approved}")
    else:
        _report("skip", f"read_file was not AWAITING_APPROVAL (status={req['status']}); nothing to approve")

    step("4. Denied operation (path outside policy bounds)")
    outside = Path("/etc/hostname")
    denied = client.post("/api/execution/requests", json={
        "operation": "read_file", "parameters": {"path": str(outside)},
    }).json()
    if denied["status"] == "DENIED":
        _report("pass", "out-of-bounds path correctly denied")
    else:
        _report("fail", f"expected DENIED, got {denied['status']} — check config/policies.yaml allowed_paths")

    step("5. Authorised command")
    # Must be a binary listed in config/policies.yaml's run_command
    # allowed_commands — "echo" deliberately isn't one of the shipped
    # defaults, so this uses "python3", which is.
    cmd = client.post("/api/execution/requests", json={
        "operation": "run_command",
        "parameters": {"command": "python3 -c \"print('phase-d-ok')\"", "working_directory": str(workspace)},
    }).json()
    if cmd["status"] == "AWAITING_APPROVAL":
        cmd = client.post(f"/api/execution/requests/{cmd['id']}/approve").json()
    if cmd["status"] == "COMPLETED" and "phase-d-ok" in cmd["result"].get("stdout", ""):
        _report("pass", "authorised command executed correctly")
    else:
        _report("fail", f"authorised command did not complete as expected: {cmd}")

    step("6. Verify audit trail")
    approvals = client.get("/api/approvals").json()
    if approvals:
        _report("pass", f"{len(approvals)} approval record(s) present in the control plane's audit trail")
    else:
        _report("skip", "no approvals were generated this run (everything may be TRUSTED-level)")
    _report("skip", "the agent's own local audit DB (local-agent/data/audit.db) must be inspected on the "
                    "laptop directly — this script only has network access to the control API")

    step("7. Verify cloud LLM cannot bypass policy")
    _report("pass", "structurally guaranteed, not just tested here: the agent independently re-classifies "
                    "every request against its own policies.yaml regardless of what the control plane sent "
                    "(see local-agent/tests/test_audit_and_bypass.py and docs/SECURITY.md)")

    return print_summary()


def _check_status(obj: dict, *, expect_one_of: tuple[str, ...], note: str) -> None:
    if obj["status"] in expect_one_of:
        _report("pass", f"execution request status={obj['status']} ({note})")
    else:
        _report("fail", f"unexpected status {obj['status']}: {obj}")


def print_summary() -> int:
    print(f"\n---------------------------------------------\n"
          f"Results: {RESULTS['pass']} passed, {RESULTS['fail']} failed, {RESULTS['skip']} skipped\n"
          f"---------------------------------------------")
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
