#!/usr/bin/env python3
"""
build_templates.py — five reverse-engineered app templates, expressed as pre-filled
answers to question_graph_v3.json. The interview is NOT changed; a template is just
a saved set of answers plus a list of what must still be asked of the customer.

Source apps studied for the generalised shape (no branding is copied):
  project management -> Asana      CRM -> Pipedrive      booking -> Acuity Scheduling
  ERP core           -> Odoo       accounting -> Xero

Emits:  templates/<name>.json  (one per template)  and  CONFIG_MAP.md
Run:    python build_templates.py
Check:  python check_template.py templates/<name>.json
"""

# ============================================================================
# RULES / CONFIG — edit these, not the logic below.
# ============================================================================
GRAPH = "question_graph_v3.json"   # graph the templates are validated against. Point elsewhere to target another version.
OUT_DIR = "templates"              # where template JSONs land. Change to relocate output.
CONFIG_MAP = "CONFIG_MAP.md"       # generated interview-answer -> template-feature map.
USER_REF = {"type": "other", "custom_rule": "reference to a user account (pick-a-person field)"}
#   The interview's closed field-type list has no "person/user" type, so every assignee/owner field uses
#   type 'other' with this rule. If a 'user' type is ever added to the graph, change this one line.
ASK_ALWAYS = ["0.01", "A.01", "A.02", "A.03", "A.04", "A.05", "A.12", "A.13", "A.14",
              "C.01", "C.02", "C.03", "C.04", "C.07", "Z.01", "Z.02", "Z.03"]
#   Questions every template leaves to the customer: identity, brand, imports, deviations, read-backs.
#   Remove one only if a template can truthfully pre-answer it for every customer.
# ============================================================================

import json, os
from collections import OrderedDict

here = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- helpers
def f(name, type, required="no", unique="no", **kw):
    d = {"name": name, "type": type, "required": required, "unique": unique}
    d.update(kw)
    return d


def user_ref(name, required="no"):
    d = f(name, USER_REF["type"], required)
    d["custom_rule"] = USER_REF["custom_rule"]
    return d


def scoped(*pairs):
    out = []
    for p in pairs:
        role, scope = p[0], p[1]
        e = {"role": role, "scope": scope}
        if scope == "linked":
            e["via"] = p[2]
        out.append(e)
    return out


def std_auth(modes, default_role=None, inviters=None, invite_role=None):
    """Standard SaaS auth block shared by all templates (Asana/Pipedrive/Acuity/Odoo/Xero all converge here)."""
    a = {
        "AU.01": modes,
        "AU.02": [f("Full name", "short_text", "yes"), f("Email address", "email", "yes", "yes")],
        "AU.03": "yes",
        "AU.04": ["password", "google"],
        "AU.07": {"scope": "nobody", "method": "n/a"},
        "AU.08": {"attempts": 5, "duration": "15 minutes"},
        "AU.09": "yes",
        "AU.10": "30 days",
        "AU.11": {"allowed": "yes", "by": ["super"], "auto_triggers": []},
        "AU.12": {"allowed": "yes", "by": "both", "data": "anonymised"},
        "AU.13": ["super"],
        "AU.14": {"required": "yes", "status": "need_drafting"},
    }
    if "public" in modes:
        a["AU.05"] = default_role
    if "invited" in modes:
        a["AU.06"] = {"inviters": inviters, "default_role": invite_role}
    return a


def workflow(trigger, stages, initial, terminal, transitions, approvals=None, on_reject=None,
             cancel=None, on_complete="Nothing further; it stays visible in its finished stage.",
             readonly_from="never", timeouts=None):
    w = {
        "FL.01": trigger,
        "FL.02": {"stages": stages, "initial": initial, "terminal": terminal},
        "FL.03": transitions,
        "FL.04": [],
        "FL.05": approvals or [],
        "FL.07": cancel or {"allowed": "no"},
        "FL.08": on_complete,
        "FL.09": readonly_from,
        "FL.10": timeouts or [],
        "FL.11": [],
    }
    if approvals:
        w["FL.06"] = on_reject
    return w


def t_move(frm, to, roles=None, event=None):
    if event:
        return {"from": frm, "to": to, "mover": "automatic", "event": event}
    return {"from": frm, "to": to, "mover": "roles", "roles": roles}


def notification(trigger, recipients, channels, intent, opt_out="yes"):
    return {"N.01": trigger, "N.02": recipients, "N.03": channels, "N.04": intent, "N.05": opt_out}


def report(question, viewers, form, metrics, filters, default_range, export_by, definitions=None):
    r = {
        "RP.01": question, "RP.02": viewers, "RP.03": form, "RP.04": metrics,
        "RP.06": {"filters": filters, "default_range": default_range},
        "RP.07": {"allowed": "yes", "by": export_by},
        "RP.08": {"enabled": "no"},
    }
    if definitions:
        r["_metric_definitions"] = definitions   # keyed by metric name; emitted as RP.05:<report>:<metric>
    return r


def record(purpose, fields, title, human_id, view, create, edit, delete, relations,
           on_delete=None, archivable="yes", retention="forever", lifecycle=None,
           ownership=None, custom_actions=None):
    r = {
        "R.01": purpose, "R.02": fields, "R.03": title,
        "R.04": human_id or {"needed": "no"},
        "R.05": view, "R.06": create, "R.07": edit, "R.08": delete,
        "R.10": {"has": "yes", "stages": lifecycle} if lifecycle else {"has": "no"},
        "R.11": relations, "R.13": archivable, "R.14": retention,
        "R.15": custom_actions or [],
    }
    if relations:
        r["R.12"] = on_delete or "block"
    if ownership:
        r["R.09"] = ownership
    return r


def rel(target, cardinality="one_to_many", required="yes"):
    return {"target": target, "cardinality": cardinality, "required": required}


OWN_CREATOR = {"basis": "creator"}


def own_field(field):
    return {"basis": "field", "field": field}


TEMPLATES = []


def template(name, source_app, category, modules, roles, super_role, records, workflows,
             notifications, reports, forms, file_types, answers, per_instance, features,
             ask_customer_extra=None, integrations=None):
    ask = list(ASK_ALWAYS) + (ask_customer_extra or [])
    TEMPLATES.append(OrderedDict(
        template=name, source_app=source_app, category=category, modules=modules,
        inventory=OrderedDict(records=list(records), roles=list(roles), forms=list(forms),
                              notifications=list(notifications), reports=list(reports),
                              workflows=list(workflows), file_types=list(file_types),
                              integrations=list(integrations or []), screens=[]),
        super_role=super_role, answers=answers, per_instance=per_instance,
        ask_customer=ask, features=features))


# ============================================================================
# TEMPLATE 1 — PROJECT MANAGEMENT (modelled on Asana)
# ============================================================================
pm_roles = ["Admin", "Member", "Guest"]
pm_records = {
    "Project": record(
        "A container of related work with an owner and a set of tasks.",
        [f("Name", "short_text", "yes"), f("Description", "long_text"), user_ref("Owner", "yes"),
         f("Due date", "date"), f("Colour", "one_choice", options=["grey", "blue", "green", "red", "purple", "orange"])],
        "Name", None,
        scoped(("Member", "all"), ("Guest", "linked", "Projects the guest was invited to")),
        ["Member"], scoped(("Member", "all")), scoped(("Member", "own"), ("Admin", "all")),
        [], archivable="yes", ownership=own_field("Owner")),
    "Task": record(
        "A single unit of work inside a project, assigned to one person.",
        [f("Title", "short_text", "yes"), f("Description", "long_text"), user_ref("Assignee"),
         f("Due date", "date"), f("Priority", "one_choice", options=["low", "medium", "high"]),
         f("Project", "link", "yes", target_record="Project")],
        "Title", None,
        scoped(("Member", "all"), ("Guest", "linked", "tasks in projects the guest was invited to")),
        ["Member"], scoped(("Member", "all")), scoped(("Member", "own"), ("Admin", "all")),
        [rel("Project")], on_delete="delete_too", lifecycle=["To do", "In progress", "Done"],
        ownership=OWN_CREATOR,
        custom_actions=[{"name": "Duplicate", "who": ["Member"],
                         "effect": "creates a copy of the task in stage 'To do' with '(copy)' appended to the title",
                         "result_location": "the same project's task list"}]),
    "Comment": record(
        "A message left on a task by a person.",
        [f("Body", "long_text", "yes"), f("Task", "link", "yes", target_record="Task")],
        "Body", None,
        scoped(("Member", "all"), ("Guest", "linked", "comments on tasks the guest can see")),
        ["Member", "Guest"], scoped(("Member", "own")), scoped(("Member", "own"), ("Admin", "all")),
        [rel("Task")], on_delete="delete_too", archivable="no", ownership=OWN_CREATOR),
}
pm_workflows = {
    "Task lifecycle": workflow(
        {"kind": "person", "who": ["Member"], "action": "creating a task (starts in 'To do')"},
        ["To do", "In progress", "Done"], "To do", ["Done"],
        [t_move("To do", "In progress", ["Member"]), t_move("In progress", "Done", ["Member"]),
         t_move("Done", "In progress", ["Member"]), t_move("In progress", "To do", ["Member"])]),
}
pm_notifications = {
    "Task assigned": notification({"kind": "event", "event": "a task's Assignee field is set or changed"},
                                  [{"kind": "field", "record": "Task", "field": "Assignee"}],
                                  ["email", "in_app"], "You've been given this task — open it and see what's needed."),
    "Task due reminder": notification({"kind": "relative_to_date", "record": "Task", "date_field": "Due date", "offset": "-24 hours"},
                                      [{"kind": "field", "record": "Task", "field": "Assignee"}],
                                      ["email", "in_app"], "This task is due tomorrow — finish it or move the date."),
    "New comment": notification({"kind": "event", "event": "a comment is created on a task"},
                                [{"kind": "field", "record": "Task", "field": "Assignee"}, {"kind": "owner"}],
                                ["in_app"], "Someone said something on your task — read and reply if needed."),
}
pm_reports = {
    "Open tasks by person": report("Who is carrying how much open work right now?", ["Member"],
                                   {"delivery": "screen", "shape": "both"},
                                   ["count of Tasks not in stage Done, grouped by Assignee"],
                                   ["Project", "Assignee", "Priority"], "all time", ["Member"]),
    "Overdue tasks": report("What has slipped past its due date and needs chasing?", ["Member"],
                            {"delivery": "screen", "shape": "table"},
                            ["count of overdue Tasks"],
                            ["Project", "Assignee"], "all time", ["Member"],
                            definitions={"count of overdue Tasks":
                                         "a Task counts as overdue when Due date is before today AND its stage is not Done, as at the moment the report is viewed"}),
}
template(
    "pm-teamwork", "Asana", "project management",
    ["tasking", "collaboration", "files"],
    pm_roles, "Admin", pm_records, pm_workflows, pm_notifications, pm_reports,
    forms=[], file_types=["Attachment"],
    answers=dict(
        {"A.06": ["web"], "A.07": "yes", "A.08": "single", "A.09": "no", "A.10": [],
         "A.11": "no", "A.16": "Admin", "P.00": "no",
         "C.05": {"mode": "simplified"},
         "C.06": {"Admin": "Projects list", "Member": "My tasks", "Guest": "Projects list"}},
        **std_auth(["invited"], inviters=["Admin", "Member"], invite_role="Member")),
    per_instance=dict(
        {f"{k}:{n}": v for n, rec in pm_records.items() for k, v in rec.items()},
        **{f"{k}:{n}": v for n, w in pm_workflows.items() for k, v in w.items()},
        **{f"{k}:{n}": v for n, x in pm_notifications.items() for k, v in x.items()},
        **{f"{k}:{n}": v for n, x in pm_reports.items() for k, v in x.items() if k != "_metric_definitions"},
        **{"RP.05:Overdue tasks:count of overdue Tasks": pm_reports["Overdue tasks"]["_metric_definitions"]["count of overdue Tasks"]},
        **{"P.01:Member": "A person on the team who plans and does the work.",
           "P.02:Member": "no", "P.04:Member": ["Admin"],
           "P.01:Guest": "An outside collaborator invited into specific projects only.",
           "P.02:Guest": "no", "P.04:Guest": ["Admin", "Member"],
           "FI.01:Attachment": {"purpose": "a file added to a task for context", "parent": "Task"},
           "FI.02:Attachment": "many",
           "FI.03:Attachment": {"uploaders": ["Member"], "viewers": ["Member", "Guest"]},
           "FI.04:Attachment": "document", "FI.05:Attachment": 50,
           "FI.06:Attachment": "keep_history", "FI.07:Attachment": "yes"}),
    features=[
        {"feature": "Guest access", "controlled_by": "A.15 roles list", "rule": "remove role 'Guest' -> every Guest grant and the invite path for guests disappears"},
        {"feature": "Attachments", "controlled_by": "A.15 file_types list", "rule": "remove 'Attachment' -> files module drops out entirely"},
        {"feature": "Priorities", "controlled_by": "R.02:Task", "rule": "delete the Priority field -> filter and report grouping on it drop out"},
        {"feature": "Task duplication", "controlled_by": "R.15:Task", "rule": "delete the Duplicate action"},
        {"feature": "Due-date reminders", "controlled_by": "A.15 notifications list", "rule": "remove 'Task due reminder'"},
    ])

# ============================================================================
# TEMPLATE 2 — CRM (modelled on Pipedrive)
# ============================================================================
crm_roles = ["Admin", "Sales manager", "Sales rep"]
crm_records = {
    "Organisation": record(
        "A company the business sells to.",
        [f("Name", "short_text", "yes", "yes"), f("Website", "url"), f("Phone", "phone"), f("Notes", "long_text")],
        "Name", None,
        scoped(("Sales rep", "all"), ("Sales manager", "all")), ["Sales rep", "Sales manager"],
        scoped(("Sales rep", "all"), ("Sales manager", "all")), scoped(("Sales manager", "all")),
        []),
    "Contact": record(
        "A person at an organisation the business talks to.",
        [f("Full name", "short_text", "yes"), f("Email", "email", "no", "yes"), f("Phone", "phone"),
         f("Organisation", "link", "no", target_record="Organisation")],
        "Full name", None,
        scoped(("Sales rep", "all"), ("Sales manager", "all")), ["Sales rep", "Sales manager"],
        scoped(("Sales rep", "all"), ("Sales manager", "all")), scoped(("Sales manager", "all")),
        [rel("Organisation", required="no")], on_delete="keep_unlinked"),
    "Deal": record(
        "A potential sale being worked through the pipeline.",
        [f("Title", "short_text", "yes"), f("Value", "money", "yes"), user_ref("Owner", "yes"),
         f("Contact", "link", "yes", target_record="Contact"),
         f("Organisation", "link", "no", target_record="Organisation"),
         f("Expected close date", "date"),
         f("Lost reason", "one_choice", options=["price", "timing", "competitor", "no response", "other"])],
        "Title", None,
        scoped(("Sales rep", "own"), ("Sales manager", "all")), ["Sales rep", "Sales manager"],
        scoped(("Sales rep", "own"), ("Sales manager", "all")), scoped(("Sales manager", "all")),
        [rel("Contact"), rel("Organisation", required="no")], on_delete="block",
        lifecycle=["Lead in", "Contacted", "Proposal sent", "Negotiation", "Won", "Lost"],
        ownership=own_field("Owner"),
        custom_actions=[{"name": "Reassign", "who": ["Sales manager"],
                         "effect": "changes the deal's Owner to another person",
                         "result_location": "the deal page; the new owner's pipeline view"}]),
    "Activity": record(
        "A scheduled call, meeting or to-do attached to a deal.",
        [f("Subject", "short_text", "yes"),
         f("Type", "one_choice", "yes", options=["call", "meeting", "email", "task"]),
         f("Due", "date_time", "yes"), f("Done", "yes_no"), user_ref("Owner", "yes"),
         f("Deal", "link", "yes", target_record="Deal")],
        "Subject", None,
        scoped(("Sales rep", "own"), ("Sales manager", "all")), ["Sales rep", "Sales manager"],
        scoped(("Sales rep", "own"), ("Sales manager", "all")), scoped(("Sales rep", "own"), ("Sales manager", "all")),
        [rel("Deal")], on_delete="delete_too", archivable="no", ownership=own_field("Owner")),
}
crm_workflows = {
    "Deal pipeline": workflow(
        {"kind": "person", "who": ["Sales rep", "Sales manager"], "action": "creating a deal (starts in 'Lead in')"},
        ["Lead in", "Contacted", "Proposal sent", "Negotiation", "Won", "Lost"], "Lead in", ["Won", "Lost"],
        [t_move("Lead in", "Contacted", ["Sales rep", "Sales manager"]),
         t_move("Contacted", "Proposal sent", ["Sales rep", "Sales manager"]),
         t_move("Proposal sent", "Negotiation", ["Sales rep", "Sales manager"]),
         t_move("Negotiation", "Won", ["Sales rep", "Sales manager"]),
         t_move("Lead in", "Lost", ["Sales rep", "Sales manager"]),
         t_move("Contacted", "Lost", ["Sales rep", "Sales manager"]),
         t_move("Proposal sent", "Lost", ["Sales rep", "Sales manager"]),
         t_move("Negotiation", "Lost", ["Sales rep", "Sales manager"])],
        readonly_from="Won",
        on_complete="Won: the deal locks and counts toward revenue reporting. Lost: Lost reason becomes required."),
}
crm_notifications = {
    "Activity due": notification({"kind": "relative_to_date", "record": "Activity", "date_field": "Due", "offset": "-1 hour"},
                                 [{"kind": "field", "record": "Activity", "field": "Owner"}],
                                 ["email", "push", "in_app"], "This call/meeting/to-do is coming up — be ready or move it."),
    "Deal won": notification({"kind": "event", "event": "a deal moves to stage Won"},
                             [{"kind": "roles", "roles": ["Sales manager"]}],
                             ["in_app"], "A deal just closed — see who won it and its value."),
}
crm_reports = {
    "Pipeline by stage": report("How much potential value sits in each stage of the pipeline?",
                                ["Sales rep", "Sales manager"], {"delivery": "screen", "shape": "both"},
                                ["sum of open Deal Value grouped by stage", "count of Deals grouped by stage"],
                                ["Owner", "Expected close date"], "all open deals", ["Sales manager"]),
    "Win rate": report("Of the deals we finish, what share do we win?",
                       ["Sales manager"], {"delivery": "screen", "shape": "both"},
                       ["win rate"], ["Owner"], "last 90 days", ["Sales manager"],
                       definitions={"win rate":
                                    "deals that entered Won divided by deals that entered Won or Lost, in the selected period, attributed to the date the deal reached that stage; expressed as a percentage"}),
}
template(
    "crm-pipeline", "Pipedrive", "CRM",
    ["people_directory", "pipeline", "activities"],
    crm_roles, "Admin", crm_records, crm_workflows, crm_notifications, crm_reports,
    forms=[], file_types=[],
    answers=dict(
        {"A.06": ["web"], "A.07": "yes", "A.08": "single", "A.09": "no", "A.10": [],
         "A.11": "no", "A.16": "Admin", "P.00": "no",
         "C.05": {"mode": "simplified"},
         "C.06": {"Admin": "Pipeline board", "Sales manager": "Pipeline board", "Sales rep": "My pipeline"}},
        **std_auth(["invited"], inviters=["Admin", "Sales manager"], invite_role="Sales rep")),
    per_instance=dict(
        {f"{k}:{n}": v for n, rec in crm_records.items() for k, v in rec.items()},
        **{f"{k}:{n}": v for n, w in crm_workflows.items() for k, v in w.items()},
        **{f"{k}:{n}": v for n, x in crm_notifications.items() for k, v in x.items()},
        **{f"{k}:{n}": v for n, x in crm_reports.items() for k, v in x.items() if k != "_metric_definitions"},
        **{"RP.05:Win rate:win rate": crm_reports["Win rate"]["_metric_definitions"]["win rate"]},
        **{"P.01:Sales manager": "Runs the sales team; sees and edits every deal.",
           "P.02:Sales manager": "no", "P.04:Sales manager": ["Admin"],
           "P.01:Sales rep": "Works their own deals and activities.",
           "P.02:Sales rep": "no", "P.04:Sales rep": ["Admin", "Sales manager"]}),
    features=[
        {"feature": "Rep visibility (own vs all deals)", "controlled_by": "R.05:Deal", "rule": "change 'Sales rep: own' to 'all' for a transparent-pipeline shop"},
        {"feature": "Organisations layer", "controlled_by": "A.15 records list", "rule": "remove 'Organisation' -> contacts stand alone; Deal loses its Organisation link"},
        {"feature": "Lost reasons", "controlled_by": "R.02:Deal", "rule": "edit the Lost reason option list"},
        {"feature": "Pipeline stages", "controlled_by": "FL.02:Deal pipeline", "rule": "rename/add stages; FL.03 transitions must be restated for any new stage"},
        {"feature": "Win-rate reporting", "controlled_by": "A.15 reports list", "rule": "remove 'Win rate'"},
    ])

# ============================================================================
# TEMPLATE 3 — BOOKING (modelled on Acuity Scheduling)
# ============================================================================
bk_roles = ["Owner", "Staff"]
bk_records = {
    "Service": record(
        "Something customers can book: a name, a length and a price.",
        [f("Name", "short_text", "yes"), f("Description", "long_text"),
         f("Duration minutes", "whole_number", "yes"), f("Price", "money", "yes"),
         f("Deposit required", "yes_no", "yes"), f("Deposit amount", "money")],
        "Name", None,
        scoped(("Staff", "all"), ("public", "public")), ["Owner"], scoped(("Owner", "all")), scoped(("Owner", "all")),
        []),
    "Customer": record(
        "A person who books appointments; created from the public booking form.",
        [f("Full name", "short_text", "yes"), f("Email", "email", "yes", "yes"), f("Phone", "phone", "yes"),
         f("Notes", "long_text")],
        "Full name", None,
        scoped(("Staff", "all")), ["Staff", "public"], scoped(("Staff", "all")), scoped(("Owner", "all")),
        []),
    "Appointment": record(
        "A booked time slot for one customer, one service and one staff member.",
        [f("Service", "link", "yes", target_record="Service"),
         f("Customer", "link", "yes", target_record="Customer"),
         user_ref("Staff member", "yes"), f("Start", "date_time", "yes"),
         f("Notes", "long_text"), f("Deposit paid", "yes_no")],
        "Start", {"needed": "yes", "format": "APT-#### (sequential)"},
        scoped(("Staff", "all")), ["Staff", "public"],
        scoped(("Staff", "all")), scoped(("Owner", "all")),
        [rel("Service"), rel("Customer")], on_delete="block",
        lifecycle=["Booked", "Confirmed", "Completed", "Cancelled", "No-show"]),
}
bk_workflows = {
    "Appointment lifecycle": workflow(
        {"kind": "event", "event": "an appointment is created (public form or by staff); starts in 'Booked'"},
        ["Booked", "Confirmed", "Completed", "Cancelled", "No-show"], "Booked",
        ["Completed", "Cancelled", "No-show"],
        [t_move("Booked", "Confirmed", event="the deposit payment succeeds, or a staff member confirms manually"),
         t_move("Confirmed", "Completed", ["Staff"]),
         t_move("Confirmed", "No-show", ["Staff"]),
         t_move("Booked", "Cancelled", ["Staff"]),
         t_move("Confirmed", "Cancelled", ["Staff"])],
        cancel={"allowed": "yes", "by": ["Staff"], "from_stages": ["Booked", "Confirmed"]},
        readonly_from="Completed",
        on_complete="Completed/No-show appointments lock and feed the reports.",
        timeouts=[{"stage": "Booked", "duration": "24 hours",
                   "then": "if the deposit is unpaid, the appointment moves to Cancelled and the slot is released"}]),
}
bk_notifications = {
    "Booking confirmation": notification({"kind": "event", "event": "an appointment reaches stage Confirmed"},
                                         [{"kind": "field", "record": "Appointment", "field": "Customer"}],
                                         ["email", "sms"], "Your booking is locked in — here's the time, the service and how to change it.",
                                         opt_out="no"),
    "Appointment reminder": notification({"kind": "relative_to_date", "record": "Appointment", "date_field": "Start", "offset": "-24 hours"},
                                         [{"kind": "field", "record": "Appointment", "field": "Customer"}],
                                         ["email", "sms"], "Your appointment is tomorrow — reply or use the link to reschedule."),
    "Cancellation notice": notification({"kind": "event", "event": "an appointment moves to Cancelled"},
                                        [{"kind": "field", "record": "Appointment", "field": "Customer"},
                                         {"kind": "field", "record": "Appointment", "field": "Staff member"}],
                                        ["email"], "This booking was cancelled — rebook if it wasn't you.", opt_out="no"),
}
bk_reports = {
    "Upcoming appointments": report("What's booked for the coming days, per staff member?",
                                    ["Staff"], {"delivery": "screen", "shape": "table"},
                                    ["count of Appointments in stage Booked or Confirmed"],
                                    ["Staff member", "Service"], "next 7 days", ["Staff"]),
    "No-show rate": report("How often do customers fail to turn up?",
                           ["Owner"], {"delivery": "screen", "shape": "both"},
                           ["no-show rate"], ["Staff member", "Service"], "last 30 days", ["Owner"],
                           definitions={"no-show rate":
                                        "appointments that ended No-show divided by appointments that ended Completed or No-show, in the selected period, by the appointment's Start date; expressed as a percentage"}),
}
bk_forms = {
    "Public booking form": {
        "F.01": {"purpose": "lets a customer pick a service, a time and a staff member and book it without an account",
                 "fillers": ["public"]},
        "F.02": {"target": "Appointment", "extra_fields": []},
        "F.03": [{"field": "Deposit payment step", "shown_when": "the chosen Service has Deposit required = yes"}],
        "F.04": "no",
        "F.05": "stay_with_message",
    }
}
template(
    "booking-frontdesk", "Acuity Scheduling", "booking",
    ["catalog_services", "scheduling", "people_directory", "deposits"],
    bk_roles, "Owner", bk_records, bk_workflows, bk_notifications, bk_reports,
    forms=list(bk_forms), file_types=[],
    answers=dict(
        {"A.06": ["web"], "A.07": "yes", "A.08": "single", "A.09": "yes",
         "A.10": ["public booking page", "public booking form"],
         "A.11": "no", "A.16": "Owner", "P.00": "no",
         "C.05": {"mode": "different",
                  "what": "the public booking flow is mobile-first: one step per screen (service -> time -> details -> pay)"},
         "C.06": {"Owner": "Calendar", "Staff": "Calendar"},
         "B.01": ["one_off"], "B.02": "person", "B.04": "AUD",
         "B.07": "card_only",
         "B.08": {"grace_days": 0, "after_repeated": "cancel"},
         "B.11": {"allowed": "yes", "by": ["Owner"]}},
        **std_auth(["invited"], inviters=["Owner"], invite_role="Staff")),
    per_instance=dict(
        {f"{k}:{n}": v for n, rec in bk_records.items() for k, v in rec.items()},
        **{f"{k}:{n}": v for n, w in bk_workflows.items() for k, v in w.items()},
        **{f"{k}:{n}": v for n, x in bk_notifications.items() for k, v in x.items()},
        **{f"{k}:{n}": v for n, x in bk_reports.items() for k, v in x.items() if k != "_metric_definitions"},
        **{f"{k}:{n}": v for n, x in bk_forms.items() for k, v in x.items()},
        **{"RP.05:No-show rate:no-show rate": bk_reports["No-show rate"]["_metric_definitions"]["no-show rate"]},
        **{"P.01:Staff": "A person who delivers services and manages their own calendar.",
           "P.02:Staff": "no", "P.03:Staff": "no", "P.04:Staff": ["Owner"]}),
    ask_customer_extra=["B.03"],   # services/prices are the customer's plan list equivalent; B.03 asks what one-off charges exist
    features=[
        {"feature": "Deposits", "controlled_by": "R.02:Service (Deposit required)", "rule": "set every Service's Deposit required = no -> A.09 flips to no, Part B drops, Booked auto-confirms"},
        {"feature": "SMS reminders", "controlled_by": "N.03 answers", "rule": "remove 'sms' from the channels -> DI.07 (SMS credentials) no longer needed"},
        {"feature": "Customer accounts", "controlled_by": "AU.01", "rule": "add 'public' self-registration and a 'Customer' role to let customers log in and see their own bookings (R.05:Appointment gains Customer: own)"},
        {"feature": "Auto-cancel unpaid bookings", "controlled_by": "FL.10:Appointment lifecycle", "rule": "change or delete the 24-hour Booked timeout"},
        {"feature": "No-show tracking", "controlled_by": "FL.02 stages", "rule": "remove the No-show stage and its report"},
    ])

# ============================================================================
# TEMPLATE 4 — ERP CORE (modelled on Odoo: sales, purchasing, inventory)
# ============================================================================
erp_roles = ["Admin", "Operations", "Sales", "Purchasing", "Warehouse"]
ERP_ALL = ["Operations", "Sales", "Purchasing", "Warehouse"]
erp_records = {
    "Product": record(
        "An item the business buys, stocks and sells.",
        [f("Name", "short_text", "yes"), f("SKU", "short_text", "yes", "yes"),
         f("Sale price", "money", "yes"), f("Cost", "money", "yes"),
         f("Stock on hand", "whole_number", "yes"), f("Reorder point", "whole_number")],
        "Name", None,
        scoped(*[(r, "all") for r in ERP_ALL]), ["Operations"], scoped(("Operations", "all")),
        scoped(("Operations", "all")), []),
    "Supplier": record(
        "A company the business buys from.",
        [f("Name", "short_text", "yes", "yes"), f("Email", "email"), f("Phone", "phone"),
         f("Payment terms", "one_choice", options=["prepaid", "net 7", "net 30", "net 60"])],
        "Name", None,
        scoped(("Operations", "all"), ("Purchasing", "all"), ("Warehouse", "all")),
        ["Purchasing", "Operations"], scoped(("Purchasing", "all"), ("Operations", "all")),
        scoped(("Operations", "all")), []),
    "Customer account": record(
        "A company or person the business sells to.",
        [f("Name", "short_text", "yes"), f("Email", "email"), f("Phone", "phone"),
         f("Delivery address", "long_text", "yes")],
        "Name", None,
        scoped(("Operations", "all"), ("Sales", "all"), ("Warehouse", "all")),
        ["Sales", "Operations"], scoped(("Sales", "all"), ("Operations", "all")),
        scoped(("Operations", "all")), []),
    "Purchase order": record(
        "An order placed with a supplier to buy stock.",
        [f("Supplier", "link", "yes", target_record="Supplier"), f("Order date", "date", "yes"),
         f("Expected date", "date"), f("Notes", "long_text")],
        "Supplier", {"needed": "yes", "format": "PO-#### (sequential)"},
        scoped(("Operations", "all"), ("Purchasing", "all"), ("Warehouse", "all")),
        ["Purchasing"], scoped(("Purchasing", "all"), ("Operations", "all")),
        scoped(("Operations", "all")),
        [rel("Supplier")], on_delete="block",
        lifecycle=["Draft", "Confirmed", "Received", "Closed", "Cancelled"]),
    "Purchase order line": record(
        "One product and quantity on a purchase order.",
        [f("Purchase order", "link", "yes", target_record="Purchase order"),
         f("Product", "link", "yes", target_record="Product"),
         f("Quantity", "whole_number", "yes"), f("Unit cost", "money", "yes")],
        "Product", None,
        scoped(("Operations", "all"), ("Purchasing", "all"), ("Warehouse", "all")),
        ["Purchasing"], scoped(("Purchasing", "all")), scoped(("Purchasing", "all")),
        [rel("Purchase order"), rel("Product")], on_delete="delete_too", archivable="no"),
    "Sales order": record(
        "An order from a customer to be picked, shipped and invoiced.",
        [f("Customer account", "link", "yes", target_record="Customer account"),
         f("Order date", "date", "yes"), f("Notes", "long_text")],
        "Customer account", {"needed": "yes", "format": "SO-#### (sequential)"},
        scoped(("Operations", "all"), ("Sales", "all"), ("Warehouse", "all")),
        ["Sales"], scoped(("Sales", "all"), ("Operations", "all")), scoped(("Operations", "all")),
        [rel("Customer account")], on_delete="block",
        lifecycle=["Draft", "Confirmed", "Shipped", "Closed", "Cancelled"]),
    "Sales order line": record(
        "One product and quantity on a sales order.",
        [f("Sales order", "link", "yes", target_record="Sales order"),
         f("Product", "link", "yes", target_record="Product"),
         f("Quantity", "whole_number", "yes"), f("Unit price", "money", "yes")],
        "Product", None,
        scoped(("Operations", "all"), ("Sales", "all"), ("Warehouse", "all")),
        ["Sales"], scoped(("Sales", "all")), scoped(("Sales", "all")),
        [rel("Sales order"), rel("Product")], on_delete="delete_too", archivable="no"),
    "Stock adjustment": record(
        "A manual correction to a product's stock level, with a reason.",
        [f("Product", "link", "yes", target_record="Product"),
         f("Change", "whole_number", "yes"),
         f("Reason", "one_choice", "yes", options=["stocktake", "damage", "loss", "correction"]),
         f("Notes", "long_text")],
        "Product", None,
        scoped(("Operations", "all"), ("Warehouse", "all")), ["Warehouse", "Operations"],
        scoped(("Operations", "all")), scoped(("Operations", "all")),
        [rel("Product")], on_delete="block", archivable="no"),
}
erp_workflows = {
    "Purchase order lifecycle": workflow(
        {"kind": "person", "who": ["Purchasing"], "action": "creating a purchase order (starts in Draft)"},
        ["Draft", "Confirmed", "Received", "Closed", "Cancelled"], "Draft", ["Closed", "Cancelled"],
        [t_move("Draft", "Confirmed", ["Purchasing"]),
         t_move("Confirmed", "Received", ["Warehouse"]),
         t_move("Received", "Closed", ["Operations"])],
        approvals=[{"stage": "Draft", "approvers": ["Operations"]}],
        on_reject={"back_to": "Draft", "resubmit": "yes"},
        cancel={"allowed": "yes", "by": ["Operations", "Purchasing"], "from_stages": ["Draft", "Confirmed"]},
        readonly_from="Received",
        on_complete="On Received, each line's Quantity is added to its Product's Stock on hand."),
    "Sales order lifecycle": workflow(
        {"kind": "person", "who": ["Sales"], "action": "creating a sales order (starts in Draft)"},
        ["Draft", "Confirmed", "Shipped", "Closed", "Cancelled"], "Draft", ["Closed", "Cancelled"],
        [t_move("Draft", "Confirmed", ["Sales"]),
         t_move("Confirmed", "Shipped", ["Warehouse"]),
         t_move("Shipped", "Closed", ["Operations"])],
        cancel={"allowed": "yes", "by": ["Operations", "Sales"], "from_stages": ["Draft", "Confirmed"]},
        readonly_from="Shipped",
        on_complete="On Shipped, each line's Quantity is subtracted from its Product's Stock on hand."),
}
erp_notifications = {
    "Low stock alert": notification({"kind": "event", "event": "a Product's Stock on hand falls to or below its Reorder point"},
                                    [{"kind": "roles", "roles": ["Purchasing", "Operations"]}],
                                    ["email", "in_app"], "This product is running out — raise a purchase order."),
    "Order shipped": notification({"kind": "event", "event": "a sales order moves to Shipped"},
                                  [{"kind": "roles", "roles": ["Sales"]}],
                                  ["in_app"], "The customer's order has left — tell them if they ask."),
}
erp_reports = {
    "Stock on hand": report("What do we hold right now, and what is at or below its reorder point?",
                            ERP_ALL, {"delivery": "screen", "shape": "table"},
                            ["sum of Product Stock on hand", "count of Products at or below Reorder point"],
                            ["Product"], "as at now", ["Operations"]),
    "Sales by month": report("What did we sell, month by month?",
                             ["Operations", "Sales"], {"delivery": "both", "shape": "both"},
                             ["sales value"], ["Product", "Customer account"], "last 12 months", ["Operations"],
                             definitions={"sales value":
                                          "sum of (Quantity x Unit price) over Sales order lines whose Sales order reached Shipped in the month, attributed to the date it reached Shipped"}),
    "Open orders": report("What is confirmed but not yet fulfilled, on both sides?",
                          ERP_ALL, {"delivery": "screen", "shape": "table"},
                          ["count of Sales orders in Confirmed", "count of Purchase orders in Confirmed"],
                          ["Supplier", "Customer account"], "as at now", ["Operations"]),
}
template(
    "erp-backbone", "Odoo (sales + purchasing + inventory core)", "ERP",
    ["catalog_products", "people_directory", "ordering", "inventory"],
    erp_roles, "Admin", erp_records, erp_workflows, erp_notifications, erp_reports,
    forms=[], file_types=[],
    answers=dict(
        {"A.06": ["web"], "A.07": "yes", "A.08": "single", "A.09": "no", "A.10": [],
         "A.11": "no", "A.16": "Admin", "P.00": "yes",
         "C.05": {"mode": "simplified"},
         "C.06": {"Admin": "Stock on hand", "Operations": "Stock on hand", "Sales": "Sales orders",
                  "Purchasing": "Purchase orders", "Warehouse": "Open orders"}},
        **std_auth(["admin_created"])),
    per_instance=dict(
        {f"{k}:{n}": v for n, rec in erp_records.items() for k, v in rec.items()},
        **{f"{k}:{n}": v for n, w in erp_workflows.items() for k, v in w.items()},
        **{f"{k}:{n}": v for n, x in erp_notifications.items() for k, v in x.items()},
        **{f"{k}:{n}": v for n, x in erp_reports.items() for k, v in x.items() if k != "_metric_definitions"},
        **{"RP.05:Sales by month:sales value": erp_reports["Sales by month"]["_metric_definitions"]["sales value"]},
        **{f"P.01:{r}": d for r, d in {
            "Operations": "Oversees the whole flow; approves purchases and closes orders.",
            "Sales": "Takes customer orders and manages customer accounts.",
            "Purchasing": "Buys stock and manages suppliers.",
            "Warehouse": "Receives, ships and corrects stock."}.items()},
        **{f"P.02:{r}": "no" for r in ERP_ALL},
        **{f"P.04:{r}": ["Admin"] for r in ERP_ALL}),
    features=[
        {"feature": "Purchasing side", "controlled_by": "A.15 records list", "rule": "remove Purchase order, Purchase order line, Supplier and the PO workflow -> sales-only inventory app"},
        {"feature": "PO approval", "controlled_by": "FL.05:Purchase order lifecycle", "rule": "empty the approvals list -> Draft->Confirmed needs no sign-off"},
        {"feature": "Reorder alerts", "controlled_by": "R.02:Product + A.15 notifications", "rule": "remove Reorder point field and the Low stock alert together"},
        {"feature": "Role split", "controlled_by": "A.15 roles + P.00", "rule": "small shops merge Sales/Purchasing/Warehouse into Operations; P.00 = yes lets one person hold several"},
        {"feature": "Stock corrections audit", "controlled_by": "R.08:Stock adjustment", "rule": "delete rights stay 'Operations only' to keep the adjustment trail honest — widen deliberately or not at all"},
    ])

# ============================================================================
# TEMPLATE 5 — ACCOUNTING (modelled on Xero: invoicing core)
# ============================================================================
ac_roles = ["Admin", "Accountant", "Advisor"]
ac_records = {
    "Contact": record(
        "A customer or supplier the business invoices or is billed by.",
        [f("Name", "short_text", "yes"), f("Email", "email"), f("Phone", "phone"),
         f("Type", "one_choice", "yes", options=["customer", "supplier", "both"]),
         f("Payment terms days", "whole_number")],
        "Name", None,
        scoped(("Accountant", "all"), ("Advisor", "all")), ["Accountant"],
        scoped(("Accountant", "all")), scoped(("Accountant", "all")), []),
    "Invoice": record(
        "Money owed TO the business by a customer.",
        [f("Contact", "link", "yes", target_record="Contact"), f("Issue date", "date", "yes"),
         f("Due date", "date", "yes"), f("Reference", "short_text"), f("Notes", "long_text")],
        "Contact", {"needed": "yes", "format": "INV-#### (sequential, never reused)"},
        scoped(("Accountant", "all"), ("Advisor", "all")), ["Accountant"],
        scoped(("Accountant", "all")), "nobody",
        [rel("Contact")], on_delete="block",
        lifecycle=["Draft", "Awaiting approval", "Awaiting payment", "Paid", "Voided"],
        custom_actions=[{"name": "Send", "who": ["Accountant"],
                         "effect": "emails the invoice document to the Contact and stamps the sent time",
                         "result_location": "the invoice page's activity trail"}]),
    "Invoice line": record(
        "One charged item on an invoice.",
        [f("Invoice", "link", "yes", target_record="Invoice"), f("Description", "short_text", "yes"),
         f("Quantity", "decimal_number", "yes"), f("Unit amount", "money", "yes")],
        "Description", None,
        scoped(("Accountant", "all"), ("Advisor", "all")), ["Accountant"],
        scoped(("Accountant", "all")), scoped(("Accountant", "all")),
        [rel("Invoice")], on_delete="delete_too", archivable="no"),
    "Bill": record(
        "Money owed BY the business to a supplier.",
        [f("Contact", "link", "yes", target_record="Contact"), f("Issue date", "date", "yes"),
         f("Due date", "date", "yes"), f("Amount", "money", "yes"), f("Reference", "short_text")],
        "Contact", {"needed": "yes", "format": "BILL-#### (sequential)"},
        scoped(("Accountant", "all"), ("Advisor", "all")), ["Accountant"],
        scoped(("Accountant", "all")), "nobody",
        [rel("Contact")], on_delete="block",
        lifecycle=["Draft", "Awaiting payment", "Paid", "Voided"]),
    "Payment": record(
        "A received or made payment applied against an invoice or bill.",
        [f("Invoice", "link", "no", target_record="Invoice"), f("Bill", "link", "no", target_record="Bill"),
         f("Amount", "money", "yes"), f("Date", "date", "yes"),
         f("Method", "one_choice", "yes", options=["bank transfer", "card", "cash", "other"])],
        "Amount", None,
        scoped(("Accountant", "all"), ("Advisor", "all")), ["Accountant"],
        scoped(("Accountant", "all")), "nobody",
        [rel("Invoice", required="no"), rel("Bill", required="no")], on_delete="block", archivable="no"),
}
ac_workflows = {
    "Invoice lifecycle": workflow(
        {"kind": "person", "who": ["Accountant"], "action": "creating an invoice (starts in Draft)"},
        ["Draft", "Awaiting approval", "Awaiting payment", "Paid", "Voided"], "Draft", ["Paid", "Voided"],
        [t_move("Draft", "Awaiting approval", ["Accountant"]),
         t_move("Awaiting approval", "Awaiting payment", ["Admin"]),
         t_move("Awaiting payment", "Paid", event="Payments applied to the invoice reach its total"),
         t_move("Awaiting payment", "Voided", ["Admin"]),
         t_move("Draft", "Voided", ["Accountant"])],
        approvals=[{"stage": "Awaiting approval", "approvers": ["Admin"]}],
        on_reject={"back_to": "Draft", "resubmit": "yes"},
        readonly_from="Awaiting payment",
        on_complete="Paid invoices lock permanently and feed Profit & loss; Voided invoices keep their number and show struck through."),
    "Bill lifecycle": workflow(
        {"kind": "person", "who": ["Accountant"], "action": "creating a bill (starts in Draft)"},
        ["Draft", "Awaiting payment", "Paid", "Voided"], "Draft", ["Paid", "Voided"],
        [t_move("Draft", "Awaiting payment", ["Accountant"]),
         t_move("Awaiting payment", "Paid", event="Payments applied to the bill reach its total"),
         t_move("Awaiting payment", "Voided", ["Admin"]),
         t_move("Draft", "Voided", ["Accountant"])],
        readonly_from="Awaiting payment",
        on_complete="Paid bills lock and feed Profit & loss as expenses."),
}
ac_notifications = {
    "Invoice sent": notification({"kind": "event", "event": "the Send action runs on an invoice"},
                                 [{"kind": "custom", "who": "the invoice's Contact, at their email address"}],
                                 ["email"], "Here is your invoice: what it's for, the total, the due date and how to pay.",
                                 opt_out="no"),
    "Payment reminder": notification({"kind": "relative_to_date", "record": "Invoice", "date_field": "Due date", "offset": "+3 days"},
                                     [{"kind": "custom", "who": "the invoice's Contact — only while the invoice is in Awaiting payment"}],
                                     ["email"], "This invoice is past due — pay it or tell us why not.", opt_out="no"),
    "Payment received": notification({"kind": "event", "event": "an invoice moves to Paid"},
                                     [{"kind": "roles", "roles": ["Accountant"]}],
                                     ["in_app"], "An invoice just got paid in full."),
}
ac_reports = {
    "Profit and loss": report("What did the business earn and spend in the period?",
                              ["Admin", "Accountant", "Advisor"], {"delivery": "both", "shape": "both"},
                              ["revenue", "expenses", "net profit"],
                              ["Contact"], "this financial year to date", ["Accountant"],
                              definitions={
                                  "revenue": "sum of (Quantity x Unit amount) over Invoice lines whose Invoice is in Awaiting payment or Paid (never Draft or Voided), attributed to the Invoice's Issue date — accrual basis, GST-exclusive",
                                  "expenses": "sum of Bill Amount for Bills in Awaiting payment or Paid, attributed to the Bill's Issue date — accrual basis",
                                  "net profit": "revenue minus expenses, exactly as those two are defined above"}),
    "Aged receivables": report("Who owes us money, and how overdue is it?",
                               ["Admin", "Accountant", "Advisor"], {"delivery": "both", "shape": "table"},
                               ["overdue invoice totals bucketed by age"],
                               ["Contact"], "as at today", ["Accountant"],
                               definitions={"overdue invoice totals bucketed by age":
                                            "for each Invoice in Awaiting payment: its total minus applied Payments, bucketed by days past Due date as at today (current, 1-30, 31-60, 61-90, 90+)"}),
}
template(
    "accounting-ledger", "Xero (invoicing core)", "accounting",
    ["people_directory", "invoicing", "payments"],
    ac_roles, "Admin", ac_records, ac_workflows, ac_notifications, ac_reports,
    forms=[], file_types=[],
    answers=dict(
        {"A.06": ["web"], "A.07": "yes", "A.08": "single", "A.09": "no", "A.10": [],
         "A.11": "no", "A.16": "Admin", "P.00": "no",
         "C.05": {"mode": "simplified"},
         "C.06": {"Admin": "Profit and loss", "Accountant": "Invoices list", "Advisor": "Profit and loss"}},
        **std_auth(["invited"], inviters=["Admin"], invite_role="Accountant")),
    per_instance=dict(
        {f"{k}:{n}": v for n, rec in ac_records.items() for k, v in rec.items()},
        **{f"{k}:{n}": v for n, w in ac_workflows.items() for k, v in w.items()},
        **{f"{k}:{n}": v for n, x in ac_notifications.items() for k, v in x.items()},
        **{f"{k}:{n}": v for n, x in ac_reports.items() for k, v in x.items() if k != "_metric_definitions"},
        **{f"RP.05:Profit and loss:{m}": d for m, d in ac_reports["Profit and loss"]["_metric_definitions"].items()},
        **{"RP.05:Aged receivables:overdue invoice totals bucketed by age":
           ac_reports["Aged receivables"]["_metric_definitions"]["overdue invoice totals bucketed by age"]},
        **{"P.01:Accountant": "Does the books: raises invoices, records bills and payments.",
           "P.02:Accountant": "no", "P.04:Accountant": ["Admin"],
           "P.01:Advisor": "An external accountant/bookkeeper with read-only access to everything financial.",
           "P.02:Advisor": "no", "P.04:Advisor": ["Admin"]}),
    features=[
        {"feature": "Invoice approval step", "controlled_by": "FL.05:Invoice lifecycle", "rule": "empty the approvals list -> Draft goes straight to Awaiting payment (sole traders)"},
        {"feature": "Bills side", "controlled_by": "A.15 records list", "rule": "remove Bill and its lifecycle -> invoicing-only app; P&L expenses metric drops"},
        {"feature": "Overdue chasing", "controlled_by": "N.01:Payment reminder", "rule": "change the +3 days offset, or remove the notification to stop chasing"},
        {"feature": "Accrual vs cash reporting", "controlled_by": "RP.05:Profit and loss:revenue", "rule": "rewrite the definition to 'Payments received in the period' for cash basis — one answer, not a rebuild"},
        {"feature": "Advisor access", "controlled_by": "A.15 roles list", "rule": "remove Advisor -> external-accountant access disappears"},
    ])

# ============================================================================
# EMIT
# ============================================================================
if __name__ == "__main__":
    import graph_lib
    import lock_structure

    outdir = os.path.join(here, OUT_DIR)
    os.makedirs(outdir, exist_ok=True)
    graph = graph_lib.load_graph(os.path.join(here, GRAPH))
    for t in TEMPLATES:
        # strip authoring-only keys
        t["per_instance"] = {k: v for k, v in t["per_instance"].items() if not k.startswith("_")}
        path = os.path.join(outdir, t["template"] + ".json")
        # a prior locked structure (if this template is already tracked) is the
        # one thing this rewrite must not disturb -- lock_structure.py reuses
        # every id whose natural key still matches, so carrying it forward here
        # keeps regeneration byte-reproducible instead of wiping the freeze.
        prior_structure = None
        if os.path.exists(path):
            prior_structure = json.load(open(path, encoding="utf-8")).get("structure")
        if prior_structure is not None:
            t["structure"] = prior_structure
        json.dump(t, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        lock_structure.lock_one(graph, path)   # freezes/refreshes "structure" -- reused, never a second numbering pass
        print("wrote", path, f"({len(t['per_instance'])} per-instance answers)")

    L = ["# Config map — interview answers -> template features\n",
         "A template is a saved answer set for `question_graph_v3.json`. The builder assembles modules and applies these answers; "
         "the customer changes a feature by changing the named interview answer, never by redesigning. "
         "Removing an item from the A.15 inventory removes every per-instance answer keyed to it (the checker proves nothing is left dangling).\n"]
    for t in TEMPLATES:
        L.append(f"\n## {t['template']} — {t['category']} (modelled on {t['source_app']})\n")
        L.append(f"Modules: {', '.join(t['modules'])}. Roles: {', '.join(t['inventory']['roles'])} (super: {t['super_role']}). "
                 f"Records: {', '.join(t['inventory']['records'])}. "
                 f"Still asked of every customer: {len(t['ask_customer'])} questions (identity, brand, imports, deviations, read-backs"
                 + (", plus " + ", ".join(q for q in t['ask_customer'] if q not in ASK_ALWAYS) if [q for q in t['ask_customer'] if q not in ASK_ALWAYS] else "") + ").\n")
        L.append("| Feature | Controlled by | Rule |\n|---|---|---|")
        for ft in t["features"]:
            L.append(f"| {ft['feature']} | `{ft['controlled_by']}` | {ft['rule']} |")
        L.append("")
    L.append("\n## Combining templates\n")
    L.append("Modules are the unit of combination, and 'combine' means: union the inventories, union the per-instance answers, "
             "re-run the checker. Shared record names (Contact, Customer account) must be reconciled to ONE record before the union — "
             "the checker fails on a record answered twice. Worked combinations that need no reconciliation beyond that: "
             "booking + accounting (Acuity's Customer becomes Xero's Contact with Type=customer); "
             "CRM + accounting (Pipedrive's Organisation becomes the Contact, Deals in Won feed invoice creation via an R.15 action); "
             "ERP + accounting (Sales order Closed triggers invoice creation — add one FL.11/notification or R.15 action, nothing structural).\n")
    open(os.path.join(here, CONFIG_MAP), "w", encoding="utf-8").write("\n".join(L))
    print("wrote", CONFIG_MAP)
