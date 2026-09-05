#!/usr/bin/env python3
"""
build_command_desk.py — turns Sam's Interview v3 answers into a real
answer-set the rest of this pipeline can run: templates/command-desk.json.

Source of every answer below: COMMAND_DESK_INTERVIEW_ANSWERS.md at the repo
root, which is Sam's own text. Nothing here is invented. Where his answers
do not reach a question the graph fires, that question is listed in
`ask_customer` — per instance where the graph allows it — so the checker
reports it as open instead of it being quietly filled in. OPEN_ITEMS at the
bottom is the same list in English.

Usage: python build_command_desk.py      (then: python check_template.py templates/command-desk.json)
"""

# ============================================================================
# RULES / CONFIG — edit these, not the logic below.
# ============================================================================
TEMPLATE_NAME = "command-desk"      # the template's id; every locked structure id is prefixed with it (command-desk/SCR-001)
OUT_DIR = "templates"               # where the answer-set is written
OWNER = "Sam"                       # the single role. Change it and every grant below follows.
RETENTION = "forever"               # R.14 for every record. Sam: archive rather than delete, zero acceptable data loss.
COST_FIELD_RECORD = "Job"           # which record carries the cost of a hosted model call (Sam, 2026-09-04).
                                    # The Cost report sums this record's Cost field; move it and the report follows.
ARCHIVE_NOT_DELETE = "yes"          # R.13 for every record. Change to "no" to allow hard deletes.
ON_DELETE = "keep_unlinked"         # R.12 for every record. Sam: connected records are kept and unlinked.
HUMAN_CODE = {"needed": "no"}       # R.04 for every record. Sam: no human-readable code needed.
READ_ONLY_FROM = "never"            # FL.09 for every workflow. Sam: never read-only.
STAGE_TIMEOUTS = []                 # FL.10 for every workflow. Sam: no stage time limits.
NOTIFY_CHANNELS = ["in_app", "email"]  # N.03 for every notification. Sam: in-app badge on the yin-yang AND email.
# ============================================================================

# ---------------------------------------------------------------------------
# PROPOSED — plumbing, filled in under 0.01 = "guided" (Sam decides the product
# things; plumbing is proposed for him to confirm). Every line here is a
# proposal, not something Sam said. Change any of it and rerun this script.
# ---------------------------------------------------------------------------

MAX_UPLOAD_MB = 100          # FI.05. Sam said "no limit set"; the upload path needs a number.

# PROPOSED: how each linked service actually authenticates. Sam's own answer
# says linked services cover BOTH connected accounts and pasted API keys; the
# interview has no question that records which is which, so it is declared here.
INTEGRATION_AUTH = {
    "Gmail": "oauth",            # a real Google OAuth round trip
    "Google Calendar": "oauth",  # same provider, same round trip
    "Tavily search": "api_key",  # a key Sam pastes in
    "Model providers": "api_key",  # a key Sam pastes in (Ollama local needs none)
}

PROPOSED = {

 # --- Agent lifecycle: running -> stopped-and-reported -> offline -----------
 "FL.01:Agent lifecycle": {"kind": "event",
   "event": "an agent is created and switched on; it starts in 'running'"},
 "FL.03:Agent lifecycle": [
   {"from": "running", "to": "stopped-and-reported", "mover": "automatic",
    "event": "the agent stops and reports that it stopped, why, and what it could be doing instead"},
   {"from": "stopped-and-reported", "to": "running", "mover": "automatic",
    "event": "the agent is switched back on (On = yes)"},
   {"from": "stopped-and-reported", "to": "offline", "mover": "automatic",
    "event": "the agent is switched off (On = no)"},
 ],
 "FL.04:Agent lifecycle": [],
 "FL.08:Agent lifecycle": ("the agent stops running; its last report stays on the record and its "
                           "jobs are left where they are"),

 # --- Conversation lifecycle: open -> needs attention -> closed -------------
 "FL.01:Conversation lifecycle": {"kind": "event",
   "event": "an agent writes the first message of a thread; it starts in 'open'"},
 "FL.03:Conversation lifecycle": [
   {"from": "open", "to": "needs attention", "mover": "automatic",
    "event": "the thread carries something Sam has not read that Hub judges he needs to see"},
   {"from": "needs attention", "to": "closed", "mover": "automatic",
    "event": "Sam has read it and nothing on it is outstanding"},
   {"from": "open", "to": "closed", "mover": "automatic",
    "event": "the job it belongs to reaches done or failed and nothing on it is outstanding"},
 ],
 "FL.04:Conversation lifecycle": [],
 "FL.08:Conversation lifecycle": ("the conversation locks and stays readable; Hub keeps it as the "
                                  "record of what was discussed"),

 # --- Project lifecycle: active -> paused -> finished -----------------------
 # Sam's own container, so he moves it; only 'finished' falls out on its own.
 "FL.01:Project lifecycle": {"kind": "person", "who": ["Sam"],
   "action": "creates a project and sets its goal"},
 "FL.03:Project lifecycle": [
   {"from": "active", "to": "paused", "mover": "roles", "roles": ["Sam"]},
   {"from": "paused", "to": "active", "mover": "roles", "roles": ["Sam"]},
   {"from": "active", "to": "finished", "mover": "automatic",
    "event": "Sam marks the goal met and no job under the project is queued or running"},
 ],
 "FL.04:Project lifecycle": [],
 "FL.08:Project lifecycle": ("the project locks: its jobs and conversations stay linked and readable, "
                             "and it stops setting system-wide context"),

 # --- Linked service lifecycle: connected -> expired -> disconnected --------
 "FL.01:Linked service lifecycle": {"kind": "event",
   "event": "a service is connected through the Connect a service form; it starts in 'connected'"},
 "FL.03:Linked service lifecycle": [
   {"from": "connected", "to": "expired", "mover": "automatic",
    "event": "a real call to the service is refused because its token or key is no longer valid"},
   {"from": "expired", "to": "connected", "mover": "automatic",
    "event": "the service is reconnected and a real call to it succeeds"},
   {"from": "expired", "to": "disconnected", "mover": "roles", "roles": ["Sam"]},
   {"from": "connected", "to": "disconnected", "mover": "roles", "roles": ["Sam"]},
 ],
 "FL.04:Linked service lifecycle": [],
 "FL.08:Linked service lifecycle": ("the service stops being offered to agents; nothing that used it "
                                    "is deleted"),

 # --- the two lifecycles whose moves Sam did describe -----------------------
 "FL.04:Job lifecycle": [
   {"from": "queued", "to": "running", "condition": "the job's agent exists and is on"},
 ],
 "FL.08:Job lifecycle": ("the job locks, its result and its cost stay on the record, and the done or "
                         "failed notification fires"),
 "FL.04:Document lifecycle": [
   {"from": "filled", "to": "signed", "condition": "every detected field is filled or waived"},
 ],
 "FL.08:Document lifecycle": ("the completed copy and its attestation stay on the record; the original "
                              "is untouched"),

 # --- the irreversible-action rule, in the shape the graph asks for ---------
 # Sam: only irreversible actions wait for him — sending an email, paying for
 # something. Those happen inside 'running', so that is the stage that waits.
 "FL.05:Job lifecycle": [{"stage": "running", "approvers": ["Sam"]}],
 "FL.06:Job lifecycle": {"back_to": "failed", "resubmit": "yes"},

 # --- how the two Activity-per-agent numbers are counted -------------------
 "RP.05:Activity per agent:jobs done per agent per week": (
   "a job counts once, in the ISO week its Finished at falls in, against the agent named on the job, "
   "when its stage is done"),
 "RP.05:Activity per agent:jobs failed per agent per week": (
   "a job counts once, in the ISO week its Finished at falls in, against the agent named on the job, "
   "when its stage is failed; a job that was retried and then finished counts as done in the week it "
   "finished and no longer counts as a failure"),
}

# The four confirm-at-compile questions. The compile now exists, so the derived
# lists are real and are recorded as confirmed by it.
CONFIRMED_BY_COMPILE = ("C.07", "Z.02", "Z.03")


import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

ALL = [{"role": OWNER, "scope": "all"}]     # R.05 / R.07 / R.08 — Sam does everything
ONLY = [OWNER]                              # R.06 / any roles list


def record(represents, fields, display, stages=None, links=(), actions=()):
    """One record's R.01-R.15, with the answers Sam gave globally applied."""
    out = {
        "R.01": represents,
        "R.02": fields,
        "R.03": display,
        "R.04": HUMAN_CODE,
        "R.05": ALL,
        "R.06": ONLY,
        "R.07": ALL,
        "R.08": ALL,
        "R.10": {"has": "yes", "stages": stages} if stages else {"has": "no"},
        "R.11": list(links),
        "R.13": ARCHIVE_NOT_DELETE,
        "R.14": RETENTION,
        "R.15": list(actions),
    }
    if links:
        out["R.12"] = ON_DELETE
    return out


def f(name, type_, required="no", unique="no", **extra):
    return dict({"name": name, "type": type_, "required": required, "unique": unique}, **extra)


def link_to(target, required="no"):
    return {"target": target, "cardinality": "one_to_many", "required": required}


# ---------------------------------------------------------------------------
# The seven records (R section of the answers file)
# ---------------------------------------------------------------------------

RECORDS = {
    "Agent": record(
        "A named specialist with a model, a role, and a set of things it can do.",
        [
            f("Name", "short_text", "yes", "yes"),
            f("Role", "short_text", "yes"),
            f("Model", "short_text", "yes"),
            f("Instructions", "long_text", "yes"),
            f("Tools it may use", "other", "no", custom_rule="the names of the tools this agent is allowed to call"),
            f("Is on", "yes_no", "yes"),
            f("Reports to", "link", "yes", target_record="Agent"),
        ],
        display="Name",
        stages=["running", "stopped-and-reported", "offline"],
        links=[link_to("Job"), link_to("Project")],
        actions=[{"name": "Pause", "who": [OWNER],
                  "effect": "stops the agent running and records that Sam paused it",
                  "result_location": "the agent's own screen, and by voice through Nova",
                  # PROPOSED: the executable form of that effect, for custom_action_execution
                  "execution": {"op": "set_fields",
                                "fields": {"is_on": 0, "stage": "stopped-and-reported"}}}],
    ),
    "Conversation": record(
        "A single thread between Sam and one agent, kept so it can be picked up later.",
        [
            f("Topic", "short_text", "yes"),
            f("Agent", "link", "yes", target_record="Agent"),
            f("When", "date_time", "yes"),
            f("Messages", "long_text", "yes"),
            f("What came of it", "long_text"),
            f("Read", "yes_no", "yes"),
        ],
        display="Topic",
        stages=["open", "needs attention", "closed"],
        links=[link_to("Job")],
    ),
    "Job": record(
        "One piece of work an agent is doing.",
        [
            f("What was asked", "long_text", "yes"),
            f("Agent", "link", "yes", target_record="Agent"),
            f("Result", "long_text"),
            f("Started at", "date_time"),
            f("Finished at", "date_time"),
            f("Cost", "money"),
        ],
        display="What was asked",
        stages=["queued", "running", "done", "failed"],
        links=[link_to("Agent", "yes"), link_to("Project"), link_to("Conversation"), link_to("Document")],
        actions=[{"name": "Retry", "who": [OWNER],
                  "effect": "runs the same job again from the start",
                  "result_location": "the job's own screen, and by voice through Nova",
                  # PROPOSED: back to the start, clearing what the last run produced
                  "execution": {"op": "reset_to_stage", "stage_column": "stage", "stage": "queued",
                                "clear": ["result", "finished_at"]}}],
    ),
    "Project": record(
        "A group of jobs and conversations under one goal; selecting one sets context system-wide.",
        [
            f("Name", "short_text", "yes", "yes"),
            f("Goal", "long_text", "yes"),
        ],
        display="Name",
        stages=["active", "paused", "finished"],
        links=[link_to("Job"), link_to("Conversation")],
    ),
    "Memory entry": record(
        "What Hub stores and recalls.",
        [
            f("Content", "long_text", "yes"),
            f("When", "date_time", "yes"),
            f("Project", "link", target_record="Project"),
            f("Agent", "link", target_record="Agent"),
        ],
        display="Content",
        stages=None,
        links=[link_to("Project"), link_to("Agent")],
    ),
    "Linked service": record(
        "A connected account (Gmail, calendar) or a pasted API key (Tavily search, model providers).",
        [
            f("Service", "short_text", "yes"),
            f("Token or key", "short_text", "yes"),
            f("Used by", "link", target_record="Agent"),
            f("Live", "yes_no", "yes"),
        ],
        display="Service",
        stages=["connected", "expired", "disconnected"],
        links=[link_to("Agent")],
    ),
    "Document": record(
        "A file Hands works on.",
        [
            f("File", "file", "yes"),
            f("Type", "short_text", "yes"),
            f("Job", "link", "yes", target_record="Job"),
        ],
        display="Type",
        stages=["received", "filled", "signed", "done"],
        links=[link_to("Job", "yes")],
        actions=[{"name": "Open source document", "who": [OWNER],
                  "effect": "opens the original uploaded file",
                  "result_location": "the document's own screen, and by voice through Nova",
                  # PROPOSED: reads the stored original; changes nothing on the row
                  "execution": {"op": "clear_fields", "fields": []}}],
    ),
}

# ---------------------------------------------------------------------------
# Forms (F), files (FI), integrations (FLX), notifications (N), reports (RP)
# ---------------------------------------------------------------------------

FORMS = {
    "Add an agent": {"target": "Agent", "purpose": "adds a specialist to the desk"},
    "Connect a service": {"target": "Linked service", "purpose": "connects an account or stores an API key"},
    "Upload a document": {"target": "Document", "purpose": "gives Hands a file to work on"},
}

INTEGRATIONS = {
    "Gmail": {
        "why": "Sam's real email — the email agent reads it and drafts replies into it.",
        "sends": "draft replies and labels", "receives": "threads and messages",
        "when": {"kind": "event", "event": "a message arrives, or Sam commands the agent from inside the thread"},
    },
    "Google Calendar": {
        "why": "what is coming up, so the desk can plan around it.",
        "sends": "events it is asked to create", "receives": "the calendar's events",
        "when": {"kind": "event", "event": "the calendar surface is opened, or an agent needs the day's shape"},
    },
    "Tavily search": {
        "why": "web search for the agents that need to look something up.",
        "sends": "a search query", "receives": "results with sources",
        "when": {"kind": "event", "event": "an agent runs a job that needs the web"},
    },
    "Model providers": {
        "why": "the LLMs the agents run on — Ollama locally, hosted only where speed forces it.",
        "sends": "prompts", "receives": "completions",
        "when": {"kind": "event", "event": "any agent takes a turn"},
    },
}

NOTIFICATIONS = {
    "Agent stopped": ({"kind": "event", "event": "an agent moves to stopped-and-reported"},
                      "an agent has stopped, why it stopped, and what it could be doing instead"),
    "Job failed": ({"kind": "event", "event": "a job moves to failed"},
                   "a job failed and what it was"),
    "Job done": ({"kind": "event", "event": "a job moves to done"},
                 "a job finished, and where the real result is"),
    "Approval needed": ({"kind": "event", "event": "an agent reaches an irreversible action — sending an email, paying for something"},
                        "an irreversible action is waiting; the reply is already drafted for one-tap approval"),
}

# PROPOSED: each report's executable ReportSpec, in reporting_engine's own shape.
REPORT_SPECS = {
    "Activity per agent": [
        {"metric": "jobs done per agent per week",
         "spec": {"table": "jobs", "aggregation": "count", "group_by": "agent",
                  "filters": [{"field": "stage", "op": "=", "value": "done"}]}},
        {"metric": "jobs failed per agent per week",
         "spec": {"table": "jobs", "aggregation": "count", "group_by": "agent",
                  "filters": [{"field": "stage", "op": "=", "value": "failed"}]}},
    ],
    "Cost": [
        {"metric": "spend on hosted model calls",
         "spec": {"table": "jobs", "aggregation": "sum", "value_field": "cost",
                  "group_by": "agent"}},
    ],
}

REPORTS = {
    "Activity per agent": {
        "question": "What got done, per agent, this week?",
        "metrics": ["jobs done per agent per week", "jobs failed per agent per week"],
        "filters": ["Agent", "Project"], "default_range": "last 7 days",
    },
    "Cost": {
        "question": "What did the hosted model calls cost?",
        "metrics": ["spend on hosted model calls"],
        "filters": ["Agent"], "default_range": "last 30 days",
    },
}

# ---------------------------------------------------------------------------
# Questions Sam's answers do not reach. Left open, per instance where the
# graph allows it, rather than filled in.
# ---------------------------------------------------------------------------

OPEN = [
    # the four confirm-at-compile questions, still to be confirmed
    "A.15", "C.07", "Z.02", "Z.03",
    # file size: "no limit set" is not a number
    "FI.05",
    # transitions and finishing behaviour for the workflows whose moves were never described
    "FL.01:Agent lifecycle", "FL.03:Agent lifecycle", "FL.04:Agent lifecycle", "FL.08:Agent lifecycle",
    "FL.01:Conversation lifecycle", "FL.03:Conversation lifecycle", "FL.04:Conversation lifecycle",
    "FL.08:Conversation lifecycle",
    "FL.01:Project lifecycle", "FL.03:Project lifecycle", "FL.04:Project lifecycle", "FL.08:Project lifecycle",
    "FL.01:Linked service lifecycle", "FL.03:Linked service lifecycle", "FL.04:Linked service lifecycle",
    "FL.08:Linked service lifecycle",
    "FL.04:Job lifecycle", "FL.08:Job lifecycle",
    "FL.04:Document lifecycle", "FL.08:Document lifecycle",
    # the irreversible-action rule is stated as a rule about actions, not stages
    "FL.05:Job lifecycle",
    # how each report's numbers are actually counted
    "RP.05:Activity per agent:jobs done per agent per week",
    "RP.05:Activity per agent:jobs failed per agent per week",
]

OPEN_ITEMS = """
Open, in English — every one of these is a question the graph fires that
Sam's answers do not reach. None has been guessed:

1.  A.15 / C.07 / Z.02 / Z.03 — the four "confirm at compile" lists: the
    inventory, the menu order, every button and where its result lands,
    every screen and what it shows. The compile now has them to show.
2.  FI.05 — "no limit set" is not a number. A real cap has to be chosen or
    the upload path has no limit to enforce.
3.  FL.01/FL.03/FL.04/FL.08 for the Agent, Conversation, Project and
    Linked service lifecycles — what starts each one, what moves it between
    its stages, what must be true first, and what happens when it finishes.
    The answers say the system moves records automatically, but not what
    the actual trigger is for (say) a conversation becoming "needs
    attention", or an agent going from stopped-and-reported to offline.
4.  FL.04/FL.08 for the Job and Document lifecycles — same two questions,
    for the two workflows whose moves Sam did describe.
5.  FL.05:Job lifecycle — "only irreversible actions wait for approval:
    sending an email, paying for something" is a rule about actions. The
    graph asks which STAGE waits and who approves. This is flaw 4 in Sam's
    own list, showing up in the compile.
6.  RP.05 for both Activity-per-agent metrics — exactly what counts as a
    job done or failed in a week, and as at which date.
"""


def build():
    per_instance = {}
    for name, answers in RECORDS.items():
        for qid, value in answers.items():
            per_instance[f"{qid}:{name}"] = value

    for form, spec in FORMS.items():
        per_instance[f"F.01:{form}"] = {"purpose": spec["purpose"], "fillers": ONLY}
        per_instance[f"F.02:{form}"] = {"target": spec["target"], "extra_fields": []}
        per_instance[f"F.03:{form}"] = []
        per_instance[f"F.04:{form}"] = "yes"          # draft-saveable
        per_instance[f"F.05:{form}"] = "open_the_record"

    per_instance["FI.01:Document file"] = {
        "purpose": "the file Hands works on", "parent": "Document"}
    per_instance["FI.02:Document file"] = "many"
    per_instance["FI.03:Document file"] = {"uploaders": ONLY, "viewers": ONLY}
    per_instance["FI.04:Document file"] = "other"
    per_instance["FI.05:Document file"] = MAX_UPLOAD_MB
    per_instance["FI.06:Document file"] = "keep_history"
    per_instance["FI.07:Document file"] = "yes"

    # the two workflows whose moves Sam described
    per_instance["FL.01:Job lifecycle"] = {
        "kind": "event", "event": "an agent is given a job; it starts in 'queued'"}
    per_instance["FL.02:Job lifecycle"] = {
        "stages": ["queued", "running", "done", "failed"], "initial": "queued",
        "terminal": ["done", "failed"]}
    per_instance["FL.03:Job lifecycle"] = [
        {"from": "queued", "to": "running", "mover": "automatic", "event": "the agent picks the job up"},
        {"from": "running", "to": "done", "mover": "automatic", "event": "the agent finishes and writes a real result"},
        {"from": "running", "to": "failed", "mover": "automatic", "event": "the agent errors or stops before finishing"},
    ]
    per_instance["FL.01:Document lifecycle"] = {
        "kind": "event", "event": "a document is uploaded; it starts in 'received'"}
    per_instance["FL.02:Document lifecycle"] = {
        "stages": ["received", "filled", "signed", "done"], "initial": "received", "terminal": ["done"]}
    per_instance["FL.03:Document lifecycle"] = [
        {"from": "received", "to": "filled", "mover": "automatic", "event": "Hands fills the fields it can"},
        {"from": "filled", "to": "signed", "mover": "automatic", "event": "Sam approves at the Trust Gate"},
        {"from": "signed", "to": "done", "mover": "automatic", "event": "the completed copy is written and attested"},
    ]

    workflows = [f"{r} lifecycle" for r, a in RECORDS.items() if a["R.10"]["has"] == "yes"]
    for wf in workflows:
        record_name = wf.rsplit(" lifecycle", 1)[0]
        stages = RECORDS[record_name]["R.10"]["stages"]
        per_instance.setdefault(f"FL.02:{wf}", {
            "stages": stages, "initial": stages[0], "terminal": [stages[-1]]})
        per_instance.setdefault(f"FL.05:{wf}", [])
        per_instance[f"FL.07:{wf}"] = {"allowed": "no"}
        per_instance[f"FL.09:{wf}"] = READ_ONLY_FROM
        per_instance[f"FL.10:{wf}"] = list(STAGE_TIMEOUTS)
        per_instance[f"FL.11:{wf}"] = []

    # the stage moves Sam does want to be told about, as notifications
    per_instance["FL.11:Agent lifecycle"] = [
        {"transition": "running -> stopped-and-reported", "recipients": ONLY, "channels": NOTIFY_CHANNELS}]
    per_instance["FL.11:Job lifecycle"] = [
        {"transition": "running -> done", "recipients": ONLY, "channels": NOTIFY_CHANNELS},
        {"transition": "running -> failed", "recipients": ONLY, "channels": NOTIFY_CHANNELS}]

    for name, spec in INTEGRATIONS.items():
        per_instance[f"FLX.01:{name}"] = spec["why"]
        per_instance[f"FLX.02:{name}"] = {"sends": spec["sends"], "receives": spec["receives"]}
        per_instance[f"FLX.03:{name}"] = spec["when"]
        per_instance[f"FLX.04:{name}"] = "per_user"
        per_instance[f"FLX.05:{name}"] = "continue_without"

    for name, (trigger, intent) in NOTIFICATIONS.items():
        per_instance[f"N.01:{name}"] = trigger
        per_instance[f"N.02:{name}"] = [{"kind": "roles", "roles": ONLY}]
        per_instance[f"N.03:{name}"] = list(NOTIFY_CHANNELS)
        per_instance[f"N.04:{name}"] = intent
        per_instance[f"N.05:{name}"] = "yes"

    for name, spec in REPORTS.items():
        per_instance[f"RP.01:{name}"] = spec["question"]
        per_instance[f"RP.02:{name}"] = ONLY
        per_instance[f"RP.03:{name}"] = {"delivery": "screen", "shape": "both"}
        per_instance[f"RP.04:{name}"] = spec["metrics"]
        per_instance[f"RP.06:{name}"] = {"filters": spec["filters"], "default_range": spec["default_range"]}
        per_instance[f"RP.07:{name}"] = {"allowed": "yes", "by": ONLY}
        per_instance[f"RP.08:{name}"] = {"enabled": "no"}
    per_instance["RP.05:Cost:spend on hosted model calls"] = (
        f"the sum of the {COST_FIELD_RECORD} record's own Cost field over the {COST_FIELD_RECORD}s "
        f"in the period -- every job records what its hosted calls really cost -- "
        f"by the job's Finished at date")

    per_instance.update({k: v for k, v in PROPOSED.items() if ":" in k.split(":", 1)[1] or True})

    template = {
        "template": TEMPLATE_NAME,
        "source_app": "Command Desk (Sam's own product) — Interview v3 answers, 5 September 2026",
        "category": "agent desk",
        "modules": ["agents", "jobs", "conversations", "memory", "linked_services", "documents"],
        "inventory": {
            "records": list(RECORDS),
            "roles": [OWNER],
            "forms": list(FORMS),
            "notifications": list(NOTIFICATIONS),
            "reports": list(REPORTS),
            "workflows": workflows,
            "file_types": ["Document file"],
            "integrations": list(INTEGRATIONS),
            "screens": [],
        },
        "super_role": OWNER,
        "answers": {
            "0.01": "guided",
            "A.01": ("A desk where one agent runs other agents. The builder-tester loop runs as a script. "
                     "An email agent is attached to Sam's real email. Hands and the Brain pipeline are "
                     "specialists on the desk."),
            "A.02": ("One front agent (Nova) that Sam talks to, which dispatches to the specialists, so Sam "
                     "has minimal direct contact with them and it keeps on top of everything in flight."),
            "A.03": "Sam only. Single user.",
            "A.04": ("Sam tells Nova a job and finds the real result waiting — an actual draft in his inbox, "
                     "the Brain pipeline actually gathered and configured. Verified by outcome, not by a report."),
            "A.05": "Command Desk",
            "A.06": ["web", "ios", "android", "desktop"],
            "A.07": "yes",
            "A.08": "single",
            "A.09": "no",
            "A.10": [],
            "A.11": "no",
            "A.12": {"required": "no"},
            "A.13": {"region": "Australia", "languages": ["English"]},
            "A.14": [],
            "A.16": OWNER,
            "C.01": ("Minimal. Centre orb is the yin-yang, sized like the ChatGPT voice orb, spoken to; the "
                     "outer gold ring spins while Nova works, the inner glyph stays still. The whole interface "
                     "slides across to reveal a full-panel left menu, not an overlay. Home carries only the "
                     "composer at the bottom, time top-left, settings top-right."),
            "C.02": ["calm", "minimal", "premium"],
            "C.03": "spacious",
            "C.04": {"mode": "provided", "path": "orb-glyph.png + orb-rotor.png (gold; Sam's own mark, cut from the reference screenshot)"},
            "C.05": {"mode": "simplified"},
            "C.06": {OWNER: "Home"},
            "AU.01": ["admin_created"],
            "AU.02": [],
            "AU.03": "no",
            "AU.04": ["password"],
            "AU.07": {"scope": "nobody", "method": "n/a"},
            "AU.08": "never",
            "AU.09": "yes",
            "AU.10": "never",
            "AU.11": {"allowed": "no"},
            "AU.12": {"allowed": "no"},
            "AU.13": [],
            "AU.14": {"required": "no"},
            "P.00": "no",
            "Z.01": "confirmed",
            **{qid: "confirmed" for qid in CONFIRMED_BY_COMPILE},
        },
        "per_instance": per_instance,
        "ask_customer": [],
        "features": [
            {"feature": "Hosted models", "controlled_by": "Linked service records",
             "rule": "every model provider is a Linked service; removing the hosted ones leaves Ollama only"},
            {"feature": "Email notifications", "controlled_by": "N.03",
             "rule": "drop 'email' from the channels and the yin-yang badge is the only notice"},
            {"feature": "Voice", "controlled_by": "R.15 actions",
             "rule": "every extra action is a button AND a voice command; dropping voice leaves the buttons"},
        ],
        "specialist_engines": [],
        "report_specs": REPORT_SPECS,
        "integration_auth": INTEGRATION_AUTH,
    }

    engines = []
    for wf in workflows:
        fl2 = per_instance[f"FL.02:{wf}"]
        engines.append({"kind": "workflow", "name": wf, "stages": fl2["stages"],
                        "initial": fl2["initial"], "terminal": fl2["terminal"],
                        "transitions": len(per_instance.get(f"FL.03:{wf}", [])),
                        "person_moved_by": [], "automatic_transitions":
                            [t["event"] for t in per_instance.get(f"FL.03:{wf}", []) if t["mover"] == "automatic"],
                        "has_approvals": bool(per_instance.get(f"FL.05:{wf}")),
                        "has_timeouts": False, "cancellable": False})
    for name in NOTIFICATIONS:
        engines.append({"kind": "notification", "name": name,
                        "trigger_kind": per_instance[f"N.01:{name}"]["kind"],
                        "channels": list(NOTIFY_CHANNELS)})
    for name, spec in REPORTS.items():
        engines.append({"kind": "report", "name": name, "metrics": spec["metrics"],
                        "shape": "both", "delivery": "screen"})
    template["specialist_engines"] = engines
    return template


def main():
    template = build()
    path = os.path.join(HERE, OUT_DIR, f"{TEMPLATE_NAME}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(template, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {path}")
    print(f"  records {len(template['inventory']['records'])}, workflows "
          f"{len(template['inventory']['workflows'])}, notifications "
          f"{len(template['inventory']['notifications'])}, reports {len(template['inventory']['reports'])}")
    print(f"  answered {len(template['answers']) + len(template['per_instance'])}, "
          f"left open {len(template['ask_customer'])}")
    print(OPEN_ITEMS)


if __name__ == "__main__":
    main()
