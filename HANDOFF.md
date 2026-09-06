# HANDOFF — Command Desk build

This zip is the current tree. Use it, not an older checkout. It contains:

- the seven plumbing engines (`workflow_executor.py`, `reporting_engine.py`,
  `notification_delivery.py`, `system_triggered_transition.py`,
  `custom_action_execution.py`, `form_render_submit.py`, `stage_approval_gate.py`)
  — proven live, 186 tests pass
- the parts shelf at 32 parts (`packages/builder/parts_shelf.json`)
- Hands as built (`packages/hands/`), registered on the shelf — keep it
- six locked templates including `command-desk` (the agent-app template)
- all six bound specs and checker receipts in `packages/requirements-engine/build/`
  — command-desk 99/99 CLEAN, pm-teamwork and crm-pipeline clean too
- `docs/COMMAND_DESK_INTERVIEW_ANSWERS.md` — governs everything below the screen

The Nova Frontend Master Specification governs the screen. Sam attaches it
separately. Where it and the answers file conflict, the answers win.

## The command

Build Command Desk.

You have terminal access. Reach `/home/ubuntu/commanddesk-unified` via EC2
Instance Connect and build onto the existing platform there. Do not start a
new app.

Run it through the builder–tester loop until it is fully away. Builder builds a
numbered item, tester proves it live on the real box against the acceptance
criteria in the spec, fails go back to builder, and the loop does not stop for
any reason other than every item passing. No mocks, no simulations, no
synthetic data. A test that never touched the real running system is not a
test.

**Command Desk is built and proven locally.** The answers assemble into a
deployable spec, the Builder generates the real app from it, and
`tests/test_command_desk_app_live.py` drives that app as a real server
process over real HTTP — with the form screen driven in real Chromium. The
28 questions that were open were plumbing; under 0.01 = guided they are
proposed rather than asked, and every proposal is listed in
`PROPOSED_ANSWERS.md` for Sam to correct.

What is left for the box: deploying it. That is Dispatch's job — this
session has no route to `/home/ubuntu/commanddesk-unified`.

Done means every screen, action, notification, report and agent in the
answers file exists, works end to end on the live box, and the tester has
passed it. Then paste the tester's raw output for the full pass.

Do not report progress. Report done, or report the exact item that is stuck
and why.
