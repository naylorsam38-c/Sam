#!/usr/bin/env python3
"""Install Phase C — Background tasks (spec section 21).

Exercises the real, running control API + worker (and, for the cloud
steps, whatever GPU_PROVIDER is configured — pass --allow-cloud-cost to
confirm you understand that a real provider will incur real cost).

Usage:
    python3 scripts/install/phase_c_tasks.py \
        --url http://localhost:8000 --username sam --password ... \
        [--local-model llama3.2:latest] [--allow-cloud-cost]

Every step reports a genuine pass/fail/skip against the live system —
nothing here is simulated (spec operational rule #10).
"""

from __future__ import annotations

import argparse
import sys
import time

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
    parser.add_argument("--local-model", default=None, help="name of an installed local model to use")
    parser.add_argument("--allow-cloud-cost", action="store_true",
                        help="confirm it's OK to start the configured GPU provider (real cost if not 'mock')")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    client = httpx.Client(base_url=args.url, timeout=30.0)

    step("Authenticate")
    resp = client.post("/api/auth/login", json={"username": args.username, "password": args.password})
    if resp.status_code != 200:
        _report("fail", f"login failed: {resp.status_code} {resp.text}")
        print_summary()
        return 1
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    _report("pass", "authenticated")

    step("1-2. Task queue + worker availability")
    health = client.get("/health/worker").json()
    if health["healthy"]:
        _report("pass", f"worker healthy: {health['detail']}")
    else:
        _report("fail", f"no healthy worker: {health['detail']} — start one with 'make worker-dev'")

    step("3-4. Submit and complete a local task")
    local_model = args.local_model
    if local_model is None:
        models = client.get("/api/models/local").json()
        available = [m for m in models if m["status"] == "available"]
        if not available:
            _report("skip", "no local models available — run /api/models/refresh after installing an Ollama model")
        else:
            local_model = available[0]["id"]

    if local_model:
        model_row = next((m for m in client.get("/api/models/local").json() if m["id"] == local_model), None)
        model_id = model_row["id"] if model_row else local_model
        task = client.post("/api/tasks", json={
            "type": "chat", "model_id": model_id,
            "input": {"messages": [{"role": "user", "content": "Say OK if you can hear me."}]},
        }).json()
        task_id = task["id"]
        final = _wait_for_terminal(client, task_id, args.timeout)
        if final["status"] == "COMPLETED":
            _report("pass", f"local task completed: {final['result']}")
        else:
            _report("fail", f"local task ended in {final['status']}: {final.get('error')}")

    step("5-8. Cloud task: GPU auto-start, inference, result persistence")
    if not args.allow_cloud_cost:
        _report("skip", "pass --allow-cloud-cost to run this against the configured GPU_PROVIDER "
                        "(will incur real cost unless GPU_PROVIDER=mock)")
    else:
        cloud_models = [m for m in client.get("/api/models/cloud").json()]
        if not cloud_models:
            _report("skip", "no cloud models registered yet — refresh the registry once the GPU has been "
                            "started at least once, or seed one manually for a mock-provider dry run")
        else:
            cloud_task = client.post("/api/tasks", json={
                "type": "chat", "model_id": cloud_models[0]["id"],
                "input": {"messages": [{"role": "user", "content": "Say OK if you can hear me from the cloud."}]},
            }).json()
            final = _wait_for_terminal(client, cloud_task["id"], args.timeout)
            if final["status"] == "COMPLETED":
                _report("pass", f"cloud task completed (GPU auto-start + inference verified): {final['result']}")
            else:
                _report("fail", f"cloud task ended in {final['status']}: {final.get('error')}")

    step("9-10. GPU idle detection + auto-shutdown")
    _report("skip", "these are time-based (GPU_IDLE_TIMEOUT_MINUTES) — verified by "
                    "apps/control/tests/test_gpu_monitor.py rather than a real-time wait here")

    step("11. Notification generated")
    notifications = client.get("/api/notifications").json()
    if notifications:
        _report("pass", f"{len(notifications)} notification(s) present")
    else:
        _report("fail", "no notifications found after running tasks")

    return print_summary()


def _wait_for_terminal(client: httpx.Client, task_id: str, timeout: float) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = client.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return task
        time.sleep(1.0)
    return {"status": "TIMEOUT", "error": f"did not finish within {timeout}s"}


def print_summary() -> int:
    print(f"\n---------------------------------------------\n"
          f"Results: {RESULTS['pass']} passed, {RESULTS['fail']} failed, {RESULTS['skip']} skipped\n"
          f"---------------------------------------------")
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
