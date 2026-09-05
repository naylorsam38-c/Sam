# Command Desk — compiled from the interview answers

What this is: Sam's own Interview v3 answers
(`COMMAND_DESK_INTERVIEW_ANSWERS.md`) run through this repository's real
pipeline — the 122-question graph, the template checker, the Assembly
Engine's structure lock, and the parts-shelf binder. Every number below is
output from a run, not an estimate.

Reproduce it:

```bash
cd packages/requirements-engine
python build_command_desk.py                       # answers -> templates/command-desk.json
python check_template.py templates/command-desk.json
python lock_structure.py templates/command-desk.json
python bind_and_assemble.py                        # binds every numbered item to a real shelf part
```

## 1. The answer set

```
command-desk            250 answers  PASS
```

250 answers, all keyed to real question ids, all closed answers legal, every
role/record/field/stage resolving, and full coverage — every question the
graph fires for this app is either answered or explicitly open. The checker's
own self-test catches six deliberate breaks, and four deliberate breaks
introduced into *this* template (a title field that does not exist, an
illegal option, a deleted answer, an unknown role) were each caught by name.

Command Desk is now the **sixth template** — the agent-app one. That was
Sam's own fix number 5: build it, then lock it so the next agent-shaped
build starts from a proven structure.

## 2. The numbered structure, locked

```
7 records · 23 screens · 33 actions · 4 notifications · 2 reports
6 workflows · 19 recurring ops · 56 generated QA cases
```

Screens: 7 list, 7 detail, 4 integration-status, 3 form, 2 report.
Actions: 7 create, 7 edit, 7 delete, 6 stage transitions, 3 custom
(Pause, Retry, Open source document), 3 form submits.
Every id is prefixed `command-desk/` and is frozen: re-running the lock, or
reordering the inventory, never renumbers an id that already exists.

## 3. What has a real part behind it

```
99/99 PASS, 0 FAIL — CLEAN
```

Every numbered item — 23 screens, 47 actions, 4 notifications, 2 reports, 19
recurring ops — binds to a real, proven part. The seven generic Builder parts
(`workflow_executor`, `system_triggered_transition`, `custom_action_execution`,
`form_render_submit`, `reporting_engine`, `notification_delivery`,
`stage_approval_gate`) cover the plumbing; the Document lifecycle binds to the
Hands parts; CRUD and OAuth bind to the Builder's own long-standing rules.

## 4. It is built, and proven running

```
$ pytest tests/test_command_desk_app_live.py -q
12 passed
```

The answers assemble into a deployable spec, the Builder generates the real
app, and the tests drive that app as a real server process over real HTTP —
records created, the Job lifecycle moving on its own declared events, the
approval gate refusing to let a job leave `running` unattended, a decline
sending it to `failed`, Pause and Retry really running, both reports returning
real numbers from real rows, a pasted API key stored and never echoed, and the
generated form filled in by real Chromium with the row landing in the database.

The generated app runs the shelf's own engine files, copied byte-for-byte —
a test asserts that byte-identity, so the app cannot drift from the parts that
were proven.

**Three real defects the live run caught**, none of which reading the code
would have found: the generated schema died on `near "when": syntax error`
(Command Desk has fields called *When* and *On*, both SQL keywords — every
generated identifier is now quoted); the generated form wrote rows with no
`created_at`, violating the schema's own NOT NULL; and a link field rendered
as an empty required `<select>` that nothing could ever fill — it now loads
the target record's real rows from the running app.

## 5. What was proposed rather than asked

0.01 is **guided**: Sam decides the product things, plumbing is proposed for
him to confirm. The 28 questions that blocked assembly were plumbing, so they
are filled in as proposals, all in one editable block in
`packages/requirements-engine/build_command_desk.py` and listed in plain
English in `PROPOSED_ANSWERS.md`.

## 6. What this does not do

It does not deploy. `/home/ubuntu/commanddesk-unified` is unreachable from a
Claude session — the cloud container has no SSH egress and the laptop grants
terminals in click-only mode, so no keystroke can reach a shell. Deployment is
Dispatch's. The screen half is still governed by the Nova Frontend Master
Specification, which is not in this repository; the built app carries the
starter library's mark because Sam's orb artwork is not here either.
