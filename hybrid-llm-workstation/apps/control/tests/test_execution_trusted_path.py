"""Regression test for the TRUSTED policy level, which auto-executes
without waiting for approval (submit_request awaits execute_now internally
for this level — a plain, un-awaited call here previously returned a
coroutine object instead of the ExecutionRequest, i.e. silently "succeeded"
while never actually running anything)."""

import yaml

from control.deps import get_settings_dep
from tests.support.fake_agent import fake_agent_server


def test_trusted_operation_executes_immediately_without_approval(client, auth_headers, tmp_path):
    policies_path = tmp_path / "policies.yaml"
    policies_path.write_text(yaml.safe_dump({
        "operations": [
            {"operation": "list_directory", "level": "TRUSTED", "risk": "LOW", "allowed_paths": ["~/workstation-workspace"]},
        ]
    }))

    with fake_agent_server() as (agent_url, received):
        overridden = client.app.state.settings.model_copy(update={
            "execution_agent_url": agent_url,
            "config_dir": tmp_path,
        })
        client.app.dependency_overrides[get_settings_dep] = lambda: overridden

        resp = client.post(
            "/api/execution/requests",
            json={"operation": "list_directory", "parameters": {"path": "~/workstation-workspace"}},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()

        # This is the crux of the regression: it must actually be COMPLETED
        # (agent contacted), not silently PENDING with nothing run.
        assert body["status"] == "COMPLETED", body
        assert len(received) == 1
        assert received[0]["operation"] == "list_directory"

        client.app.dependency_overrides.pop(get_settings_dep, None)
