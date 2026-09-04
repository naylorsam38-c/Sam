#!/usr/bin/env python3
"""
build_graph.py — Requirements Engine question graph v3 (single source of truth)

Emits:
  question_graph_v3.json   machine-readable graph (questions, gates, done-rules, derivations, defaults, deploy inputs)
  INTERVIEW_v3.md          human-readable numbered interview generated FROM the graph (cannot drift)

Run:  python build_graph.py            (writes both files next to this script)
"""

# ============================================================================
# RULES / CONFIG — edit these, not the logic below.
# ============================================================================
OUT_JSON = "question_graph_v3.json"      # where the graph is written. Change to relocate the JSON output.
OUT_MD = "INTERVIEW_v3.md"               # where the readable interview is written. Change to relocate the doc.
GRAPH_VERSION = "3.0"                    # bump when the question set changes; the validator prints it.
PART_ORDER = ["0", "A", "C", "AU", "P", "R", "F", "FI", "FL", "FLX", "RP", "N", "B", "T", "D", "Z"]
#   The order parts are asked in. Reordering changes the interview order only; gates still reference IDs, so
#   a part that depends on another must stay after it (the validator refuses a gate that points forward).
AMBIGUOUS_METRIC_TERMS = ["active", "completed", "engaged", "churn", "churned", "converted", "conversion",
                          "retained", "retention", "revenue", "growth", "at risk", "overdue", "on time",
                          "utilisation", "utilization", "average", "rate"]
#   A report metric containing any of these words forces RP.05 (definition). Add a word → more definitions asked;
#   remove one → that word derives silently (risk: two builders count it differently).
SUPER_ROLE_TOKEN = "super"               # token the engine uses for the always-allowed role named in A.16.
PUBLIC_ROLE_TOKEN = "public"             # token for "not logged in" in any role choice.
WIDGET_VOCAB = {
    # visual answer widgets. The QUESTION, gate and done-rule never change - only how the answer is captured.
    "icon_multi":          "tap device/channel/category icons; each shows a small rendered sample",
    "icon_pick":           "tap one icon from a small set",
    "style_board":         "board of labelled app-style screenshots; tap to like or avoid (credit the shown apps on the tile)",
    "chip_select":         "tap word chips from a curated vocabulary; free-type to add",
    "visual_abc":          "2-4 rendered mockups of the same thing; tap the one you mean",
    "brand_kit":           "logo upload + colour picker with a live header preview",
    "screen_picker":       "tap a screen thumbnail per role",
    "screen_map":          "map of all screens; tap a lock to make one public/private",
    "drag_order":          "drag items to reorder a live preview (menu, columns)",
    "card_board":          "editable cards per inventory list; tap to remove, type to add",
    "form_builder":        "live form preview that rebuilds as fields are added/typed/reordered; conditional fields toggle live",
    "tap_on_preview":      "answer by tapping the element on a rendered mockup (title field, lock stage, button placement)",
    "access_matrix":       "roles x verbs grid with per-cell scope; renders a see-it-as-that-role sample underneath",
    "pipeline_editor":     "stages as draggable pills; draw arrows for moves; badges for approval/timeout; tap an arrow to set who moves it",
    "link_diagram":        "record cards on a canvas; drag a line between two to declare the relationship",
    "login_preview":       "live sign-in screen; toggling a method adds/removes its button",
    "message_preview":     "rendered sample message per channel (email/SMS bubble/push banner); edit intent under it",
    "report_mockup":       "rendered report with toggleable filter chips and a date-range control",
    "pricing_builder":     "plan cards edited in place on a live pricing-page preview",
    "wireframe_walkthrough": "clickable wireframe of every screen; every numbered button present; tap through and confirm",
}
WIDGETS = {
    # question id -> widget. Remove a line -> that question falls back to plain text/choice input.
    "A.06": "icon_multi", "A.10": "screen_map", "A.15": "card_board",
    "C.01": "style_board", "C.02": "chip_select", "C.03": "visual_abc", "C.04": "brand_kit",
    "C.05": "visual_abc", "C.06": "screen_picker", "C.07": "drag_order",
    "AU.01": "icon_multi", "AU.02": "form_builder", "AU.04": "login_preview",
    "R.02": "form_builder", "R.03": "tap_on_preview", "R.05": "access_matrix", "R.06": "access_matrix",
    "R.07": "access_matrix", "R.08": "access_matrix", "R.10": "pipeline_editor", "R.11": "link_diagram",
    "R.15": "tap_on_preview",
    "F.02": "form_builder", "F.03": "form_builder", "F.05": "visual_abc",
    "FI.04": "icon_pick",
    "FL.02": "pipeline_editor", "FL.03": "pipeline_editor", "FL.05": "pipeline_editor",
    "FL.06": "pipeline_editor", "FL.07": "pipeline_editor", "FL.09": "tap_on_preview", "FL.10": "pipeline_editor",
    "N.03": "icon_multi", "N.04": "message_preview",
    "RP.03": "visual_abc", "RP.06": "report_mockup",
    "B.03": "pricing_builder",
    "Z.02": "wireframe_walkthrough", "Z.03": "wireframe_walkthrough",
}
# ============================================================================

import json, os, sys
from collections import OrderedDict

QUESTIONS = []
PARTS = OrderedDict()
DEFAULTS = []
DERIVATIONS = []
DEPLOY_INPUTS = []
SPEC_FIELDS = []          # master list; every entry must have exactly one source (validator enforces)


def part(code, title, per=None, gate=None, intro=""):
    PARTS[code] = {"code": code, "title": title, "per": per, "gate": gate, "intro": intro}


def spec(*names):
    for n in names:
        if n not in SPEC_FIELDS:
            SPEC_FIELDS.append(n)
    return list(names)


_PART_DEFAULT = "__part__"


def Q(id, prompt, type, fills=(), gate=None, options=None, per=_PART_DEFAULT, done=None, notes=None, feeds=None,
      required=True, creates=None):
    code = id.split(".")[0]
    assert code in PARTS, f"part {code} not declared before {id}"
    if type == "yesno" and options is None:
        options = ["yes", "no"]
    if done is None:
        done = {
            "text": {"rule": "non_empty"},
            "yesno": {"rule": "one_of", "options": ["yes", "no"]},
            "choice": {"rule": "one_of"},
            "multi": {"rule": "subset_min1"},
            "list": {"rule": "min_items", "n": 1},
            "number": {"rule": "number"},
            "duration": {"rule": "duration_or_never"},
            "roles": {"rule": "roles_min1"},
            "roles_scoped": {"rule": "roles_scoped_min1"},
            "structured": {"rule": "structured"},
            "confirm": {"rule": "confirmed"},
        }[type]
    if type in ("choice", "multi") and done.get("rule") in ("one_of", "subset_min1") and "options" not in done:
        assert options, f"{id}: choice/multi needs options"
        done = dict(done, options=[o.split(" — ")[0] for o in options])
    q = OrderedDict(id=id, part=code, prompt=prompt, type=type, options=options, gate=gate,
                    per=PARTS[code]["per"] if per == _PART_DEFAULT else per, fills=spec(*fills), done=done,
                    feeds=feeds or [], notes=notes, required=required, creates=creates)
    QUESTIONS.append(q)
    return id


def default(id, area, behaviour, fields=(), why=None):
    DEFAULTS.append(OrderedDict(id=id, area=area, behaviour=behaviour, fields=spec(*fields), why=why))


def derive(id, produces, inputs, rule, safe_because):
    DERIVATIONS.append(OrderedDict(id=id, outputs=spec(*produces), inputs=inputs, rule=rule, safe_because=safe_because))


def deploy(id, prompt, fields, gate=None):
    DEPLOY_INPUTS.append(OrderedDict(id=id, prompt=prompt, fields=spec(*fields), gate=gate))


def g(q, op="eq", value=None):
    return {"q": q, "op": op, "value": value}


def g_all(*gs):
    return {"all": list(gs)}


def g_any(*gs):
    return {"any": list(gs)}


# ----------------------------------------------------------------------------
# PART 0 — Setup (asked once, before anything)
# ----------------------------------------------------------------------------
part("0", "Setup", intro="Asked once. Changes how much the interviewer asks, never what gets built or verified.")
Q("0.01", "How involved do you want to be? Full (you decide everything), guided (you decide the product things, "
          "I'll propose the rest and you confirm), or hands-off (you answer the essentials, I'll fill the rest "
          "with standard behaviour and show you the list at the end).",
  "choice", ["engine.involvement"], options=["full", "guided", "hands-off"],
  notes="Sets how many derived/defaulted values are read back for confirmation. Never changes the spec's content.")

# ----------------------------------------------------------------------------
# PART A — The idea
# ----------------------------------------------------------------------------
part("A", "The idea", intro="Conversational. The interviewer may ask these in any words; the script decides when each field is filled.")
Q("A.01", "What are you trying to build? Describe it like you're explaining it to a friend.", "text",
  ["product.description"], done={"rule": "non_empty_and_extracts", "must_extract": ["records"]},
  notes="Done only when at least one record noun can be extracted. Feeds the A.15 inventory proposal.")
Q("A.02", "What should people be able to accomplish with it?", "text", ["product.goals"])
Q("A.03", "Who is it for?", "text", ["product.audience"])
Q("A.04", "How will you know it's working — what does success look like to you?", "text", ["product.success_definition"])
Q("A.05", "What is the app called?", "text", ["product.name"],
  notes="Dropped in the handoff's final pass. It appears on every screen and email; two builders would invent two names.")
Q("A.06", "Where will people use it — in a web browser, as a phone app (iOS/Android), both, or as a desktop program?",
  "multi", ["client.platforms"], options=["web", "ios", "android", "desktop"],
  notes="Never asked in the handoff. The single biggest divergence between two builders.")
Q("A.07", "Do people need to log in / have accounts?", "yesno", ["auth.required"])
Q("A.08", "Is this for one organisation/user base, or for many separate organisations that must never see each other's data?",
  "choice", ["tenancy.mode"], options=["single", "multiple"])
Q("A.09", "Does this involve charging people money?", "yesno", ["billing.required"])
Q("A.10", "Which parts, if any, can be seen without logging in? (e.g. a public landing page, a public booking form, nothing)",
  "list", ["client.public_surfaces"], gate=g("A.07", "eq", "yes"), done={"rule": "min_items", "n": 0},
  notes="'Nothing' is a valid answer and must be recorded explicitly.")
Q("A.11", "Do other systems need to push data into, or pull data out of, your app automatically (an API, webhooks)?",
  "yesno", ["integration.public_api_required"], creates={"kind": "integration", "name": "Public API", "when": "yes"})
Q("A.12", "Is there existing data that has to be brought in before launch (a spreadsheet, an old system)? If so, what and where from?",
  "structured", ["data.import_required", "data.import_sources"],
  done={"rule": "structured", "keys": ["required"], "if": {"required": "yes", "then_keys": ["sources"]}})
Q("A.13", "What country are most of your users in, and do you need more than one language?",
  "structured", ["locale.primary_region", "locale.languages"],
  done={"rule": "structured", "keys": ["region", "languages"]},
  notes="Drives date/number/currency display format and default timezone. Never asked in the handoff.")
Q("A.14", "Is there anything you want to work differently from how a typical app of this kind normally works?",
  "list", ["deviation.flags"], done={"rule": "min_items", "n": 0}, creates={"kind": "deviation", "each": True})
Q("A.15", "Here's what I understood you'll need — screens, records, roles, forms, notifications, file types, reports, "
          "workflows, external systems. Did I miss anything, or get anything wrong? (confirm each list)",
  "confirm", ["inventory.screens", "inventory.records", "inventory.roles", "inventory.forms", "inventory.notifications",
              "inventory.file_types", "inventory.reports", "inventory.workflows", "inventory.integrations"],
  done={"rule": "confirmed_lists", "lists": ["screens", "records", "roles", "forms", "notifications", "file_types",
                                            "reports", "workflows", "integrations"]},
  notes="Engine proposes from A.01–A.04; owner corrects. Each confirmed item instantiates its part. Empty lists are allowed but must be confirmed empty.")
Q("A.16", "Is there one role that can always do everything, no matter what? If so, which one?",
  "choice", ["roles.super_role"], gate=g("A.07", "eq", "yes"), options=["<a confirmed role>", "none"],
  done={"rule": "role_or_none"},
  notes="That role is skipped in every per-record/per-workflow authority question and granted everything. Removes dozens of repeat answers.")

# ----------------------------------------------------------------------------
# PART C — Client (the interface itself)
# ----------------------------------------------------------------------------
part("C", "Client — look, feel and navigation")
Q("C.01", "Are there other apps, brands or products whose look and feel you want this to resemble — or specifically avoid?",
  "text", ["visual.references"], done={"rule": "non_empty_or_none"})
Q("C.02", "In three words, how should this feel to use? (e.g. playful, fast, minimal / serious, trustworthy, dense)",
  "list", ["visual.tone"], done={"rule": "min_items", "n": 3})
Q("C.03", "How much should be visible at once — spacious and simple, balanced, or dense and information-rich?",
  "choice", ["visual.density"], options=["spacious", "balanced", "dense"])
Q("C.04", "Is there a primary colour, logo or existing brand material to build from, or should that be designed for you?",
  "structured", ["visual.brand_assets"], done={"rule": "structured", "keys": ["mode"], "one_of": {"mode": ["provided", "design_for_me"]}})
Q("C.05", "On phones, should it be a simplified version of the big-screen layout, or does anything need to work completely differently on mobile?",
  "structured", ["client.mobile_behaviour"], gate=g("A.06", "includes_any", ["web", "desktop"]),
  done={"rule": "structured", "keys": ["mode"], "one_of": {"mode": ["simplified", "different"]}, "if": {"mode": "different", "then_keys": ["what"]}},
  notes="Only asked if there is a big-screen platform to simplify from.")
Q("C.06", "After logging in, which screen does each role land on first?", "structured", ["client.landing_screen_per_role"],
  gate=g("A.07", "eq", "yes"), done={"rule": "map_complete", "keys_from": "inventory.roles", "values_from": "inventory.screens"},
  notes="Handoff classed 'what happens after login' as a system default. It is product-specific: dashboard vs list vs record. Two builders diverge.")
Q("C.07", "Here is the main menu I'd build from your screens, in this order: [derived]. Reorder, rename or hide anything?",
  "confirm", ["client.navigation"], done={"rule": "confirmed"})

# ----------------------------------------------------------------------------
# PART AU — Auth
# ----------------------------------------------------------------------------
part("AU", "Auth", gate=g("A.07", "eq", "yes"))
Q("AU.01", "How do people get an account — sign up themselves publicly, get invited by someone, or get created by an admin? (any that apply)",
  "multi", ["auth.registration_modes"], options=["public", "invited", "admin_created"])
Q("AU.02", "What information do you need from someone when they register? (each item: what it is, and is it required)",
  "structured", ["auth.registration_fields"], done={"rule": "fields_list", "min": 1, "type_options": "FIELD_TYPES"})
Q("AU.03", "Must they verify their email address before they can use the app?", "yesno", ["auth.email_verification"])
Q("AU.04", "Which login methods? (any that apply)", "multi", ["auth.methods"],
  options=["password", "google", "microsoft", "apple", "magic_link"])
Q("AU.05", "When someone signs up by themselves, which role do they get?", "choice", ["auth.default_role"],
  gate=g("AU.01", "includes", "public"), options=["<a confirmed role>"], done={"rule": "role"},
  notes="Never asked in the handoff. Without it one builder makes new signups Members, another makes them Admins.")
Q("AU.06", "Who can invite people, and which role does an invited person get by default?", "structured", ["auth.invite_authority", "auth.invite_default_role"],
  gate=g("AU.01", "includes", "invited"), done={"rule": "structured", "keys": ["inviters", "default_role"], "roles_keys": ["inviters", "default_role"]})
Q("AU.07", "Is two-factor authentication required — for nobody, admins only, or everyone? And by which method — authenticator app, SMS code, or either?",
  "structured", ["auth.mfa_scope", "auth.mfa_method"],
  done={"rule": "structured", "keys": ["scope", "method"], "one_of": {"scope": ["nobody", "admins", "everyone"], "method": ["app", "sms", "either", "n/a"]},
        "if": {"scope": "nobody", "then_value": {"method": "n/a"}}},
  notes="Handoff's classification said MFA method stays a closed question; the final interview lost it.")
Q("AU.08", "After how many failed login attempts should an account be temporarily locked, and for how long? ('never lock' is a valid answer)",
  "structured", ["auth.lockout_attempts", "auth.lockout_duration"],
  done={"rule": "structured", "keys": ["attempts", "duration"], "or_value": "never"})
Q("AU.09", "Can one person be logged in on more than one device at the same time?", "yesno", ["auth.multi_device"])
Q("AU.10", "How long can someone stay signed in before being asked to sign in again?", "duration", ["auth.session_length"])
Q("AU.11", "Can accounts be suspended? If so, who can do it, and does anything trigger it automatically (e.g. unpaid bill)?",
  "structured", ["auth.suspension_allowed", "auth.suspension_by", "auth.suspension_auto_triggers"],
  done={"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by", "auto_triggers"]}, "roles_keys": ["by"]})
Q("AU.12", "Can accounts be deleted? By whom — the person themselves, an admin, or both? And what happens to their data: kept, anonymised, or fully erased?",
  "structured", ["auth.deletion_allowed", "auth.deletion_by", "auth.deletion_data_policy"],
  done={"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by", "data"]},
        "one_of": {"by": ["self", "admin", "both"], "data": ["kept", "anonymised", "erased"]}})
Q("AU.13", "Who, if anyone, may reset someone else's password on their behalf?", "roles", ["auth.reset_others_by"],
  done={"rule": "roles_or_nobody"})
Q("AU.14", "Must people accept terms of service / a privacy policy when they sign up? Do those documents exist already?",
  "structured", ["legal.terms_required", "legal.terms_status"],
  done={"rule": "structured", "keys": ["required"], "if": {"required": "yes", "then_keys": ["status"]}, "one_of": {"status": ["have_them", "need_drafting"]}})

# ----------------------------------------------------------------------------
# PART P — Permissions (roles)
# ----------------------------------------------------------------------------
part("P", "Permissions — roles", per="role", gate=g("A.07", "eq", "yes"),
     intro="Once per confirmed role, except the super role from A.16. Authority over specific things is asked where it is exercised (Records, Flow, Billing).")
Q("P.00", "Can one person hold more than one role at the same time?", "yesno", ["roles.multi_role_per_person"], per=None,
  notes="Asked once, not per role. Decides single-select vs multi-select role assignment — a visible difference.")
Q("P.01", "In one sentence, who is a '${role}' — what kind of person holds this role?", "text", ["role.{r}.description"],
  notes="Context only. Never a build-spec source by itself.")
Q("P.02", "Can a '${role}' see other people's private information anywhere in the app (personal settings, contact details, private notes)?",
  "yesno", ["role.{r}.sees_private_data"])
Q("P.03", "Can a '${role}' see or change billing and payment details?", "yesno", ["role.{r}.billing_access"], gate=g("A.09", "eq", "yes"))
Q("P.04", "Who can give someone the '${role}' role, or take it away?", "roles", ["role.{r}.assignable_by"])

# ----------------------------------------------------------------------------
# PART R — Records
# ----------------------------------------------------------------------------
part("R", "Records", per="record")
Q("R.01", "What does a '${record}' represent, in one sentence?", "text", ["record.{r}.purpose"])
Q("R.02", "What information does a '${record}' store? For each item: what kind is it, is it required, must it be unique, "
          "and (for a list choice) what are the options / (for a link) which record does it link to?",
  "structured", ["record.{r}.fields"],
  done={"rule": "fields_list", "min": 1, "type_options": "FIELD_TYPES",
        "per_field_required_keys": ["name", "type", "required", "unique"],
        "per_field_conditional": {"one_choice": ["options"], "multi_choice": ["options"], "link": ["target_record"], "other": ["custom_rule"]}},
  notes="Handoff never asked for choice options, uniqueness, or the link target. Each one makes two builders diverge.")
Q("R.03", "Which of those fields is the '${record}'s name — the thing shown in lists, links and messages?", "choice", ["record.{r}.title_field"],
  options=["<a field from R.02>"], done={"rule": "field_of", "from": "R.02"})
Q("R.04", "Does a '${record}' need a human-readable number or code (like INV-0001)? If so, what format?",
  "structured", ["record.{r}.human_id"], done={"rule": "structured", "keys": ["needed"], "if": {"needed": "yes", "then_keys": ["format"]}})
Q("R.05", "Who can VIEW a '${record}'? For each role: all of them, only their own, only ones linked to something they belong to (say what), or public (no login)?",
  "roles_scoped", ["record.{r}.access.view"],
  done={"rule": "roles_scoped_min1", "scopes": ["all", "own", "linked", "public"], "if_scope": {"linked": ["via"]}},
  notes="The handoff's audit resolved the Manager example with a 'their team' scope, then the interview only offered all/own. 'linked' restores it and must name the relation.")
Q("R.06", "Who can CREATE a '${record}'?", "roles", ["record.{r}.access.create"])
Q("R.07", "Who can EDIT a '${record}'? For each role: any, only their own, or only linked ones?", "roles_scoped", ["record.{r}.access.edit"],
  done={"rule": "roles_scoped_min1", "scopes": ["all", "own", "linked"], "if_scope": {"linked": ["via"]}})
Q("R.08", "Who can DELETE a '${record}'? For each role: any, only their own, or only linked ones? ('nobody' is valid)", "roles_scoped", ["record.{r}.access.delete"],
  done={"rule": "roles_scoped_min1", "scopes": ["all", "own", "linked"], "if_scope": {"linked": ["via"]}, "or_value": "nobody"})
Q("R.09", "What makes a '${record}' someone's OWN — the person who created it, or the person named in a particular field (which one)?",
  "structured", ["record.{r}.ownership_rule"], gate=g_any(g("R.05", "scope_includes", "own"), g("R.07", "scope_includes", "own"), g("R.08", "scope_includes", "own")),
  done={"rule": "structured", "keys": ["basis"], "one_of": {"basis": ["creator", "field"]}, "if": {"basis": "field", "then_keys": ["field"]}},
  notes="Never asked in the handoff. created_by vs assigned_to is the classic two-builder split.")
Q("R.10", "Does a '${record}' move through stages over its life (e.g. Draft → Active → Archived)? If so, name them in order.",
  "structured", ["record.{r}.has_lifecycle"], done={"rule": "structured", "keys": ["has"], "if": {"has": "yes", "then_keys": ["stages"]}},
  creates={"kind": "workflow", "name": "${record} lifecycle", "when": "yes"})
Q("R.11", "Is a '${record}' connected to any other record? For each: which record, is it one-to-many or many-to-many, and must the link always exist?",
  "structured", ["record.{r}.relations"], done={"rule": "relations_list", "min": 0, "keys": ["target", "cardinality", "required"],
                                                 "one_of": {"cardinality": ["one_to_many", "many_to_many"]}})
Q("R.12", "When a '${record}' is deleted, what happens to the things connected to it — deleted too, kept but unlinked, or deletion blocked until they're dealt with?",
  "choice", ["record.{r}.on_delete"], gate=g("R.11", "min_items", 1), options=["delete_too", "keep_unlinked", "block"])
Q("R.13", "Should old or inactive '${record}'s be archivable (hidden but kept) rather than deleted?", "yesno", ["record.{r}.archivable"])
Q("R.14", "How long should '${record}' data be kept before it is permanently removed — forever, or a set time after it's archived/closed?",
  "duration", ["record.{r}.retention"], done={"rule": "duration_or_forever"},
  feeds=["OPS"])
Q("R.15", "Besides create/edit/delete and moving through stages, are there any other buttons people need on a '${record}' "
          "(e.g. duplicate, send, print, mark as paid)? For each: who can press it, what it does, and where the result shows up.",
  "structured", ["record.{r}.custom_actions"], done={"rule": "actions_list", "min": 0, "keys": ["name", "who", "effect", "result_location"], "roles_keys": ["who"]},
  notes="This is where every non-CRUD button gets its number. Handoff derived all actions from CRUD + transitions, so 'Duplicate' could never exist.")

# ----------------------------------------------------------------------------
# PART F — Forms
# ----------------------------------------------------------------------------
part("F", "Forms", per="form")
Q("F.01", "What is the '${form}' for, and who fills it out?", "structured", ["form.{f}.purpose", "form.{f}.fillers"],
  done={"rule": "structured", "keys": ["purpose", "fillers"], "roles_keys": ["fillers"]})
Q("F.02", "Which record does it create or edit? And does it collect anything that is NOT stored on that record? (list those extra items with their kind)",
  "structured", ["form.{f}.target_record", "form.{f}.extra_fields"],
  done={"rule": "structured", "keys": ["target"], "optional_keys": ["extra_fields"], "fields_list_key": "extra_fields"})
Q("F.03", "Does any field only appear depending on another answer? (which field, depends on which answer)", "structured", ["form.{f}.conditional_fields"],
  done={"rule": "conditional_list", "min": 0, "keys": ["field", "shown_when"]},
  notes="Handoff classified this as 'asked only if the owner indicates' but had no prompt that could surface it.")
Q("F.04", "Can someone save it as a draft and finish later?", "yesno", ["form.{f}.draft_save"])
Q("F.05", "Right after a successful submit, where should they end up?", "choice", ["form.{f}.on_success"],
  options=["open_the_record", "back_to_list", "stay_with_message", "another_screen"],
  done={"rule": "one_of", "if_value": {"another_screen": ["screen"]}})

# ----------------------------------------------------------------------------
# PART FI — Files
# ----------------------------------------------------------------------------
part("FI", "Files", per="file_type")
Q("FI.01", "What is a '${file_type}' used for, and which record is it attached to?", "structured", ["file.{ft}.purpose", "file.{ft}.parent_record"],
  done={"rule": "structured", "keys": ["purpose", "parent"]})
Q("FI.02", "One per record, or many?", "choice", ["file.{ft}.cardinality"], options=["one", "many"])
Q("FI.03", "Who can upload it, and who can view/download it? ('public' allowed for viewing)", "structured", ["file.{ft}.uploaders", "file.{ft}.viewers"],
  done={"rule": "structured", "keys": ["uploaders", "viewers"], "roles_keys": ["uploaders", "viewers"]})
Q("FI.04", "What kind of file — image, document, spreadsheet, video/audio, or something else (say which formats)?", "choice", ["file.{ft}.category"],
  options=["image", "document", "spreadsheet", "media", "other"], done={"rule": "one_of", "if_value": {"other": ["formats"]}})
Q("FI.05", "Roughly how large might these get? (e.g. 10 MB, 500 MB)", "number", ["file.{ft}.max_size_mb"])
Q("FI.06", "If someone uploads a new version, keep the old one (history) or replace it?", "choice", ["file.{ft}.versioning"], options=["keep_history", "replace"])
Q("FI.07", "When the record it belongs to is deleted, delete the file too?", "yesno", ["file.{ft}.cascade_delete"])

# ----------------------------------------------------------------------------
# PART FL — Flow (workflows, lifecycles, external systems, automatic work)
# ----------------------------------------------------------------------------
part("FL", "Flow — processes and external systems", per="workflow",
     intro="Once per confirmed workflow, including every record lifecycle from R.10. Integrations are Flow instances (FL.X questions).")
Q("FL.01", "What starts '${workflow}' — a person doing something (who, doing what), something happening automatically (what), or a schedule (when)?",
  "structured", ["workflow.{w}.trigger"],
  done={"rule": "structured", "keys": ["kind"], "one_of": {"kind": ["person", "event", "schedule"]},
        "if_any": {"person": ["who", "action"], "event": ["event"], "schedule": ["schedule"]}, "roles_keys": ["who"]}, feeds=["OPS"])
Q("FL.02", "What are its stages, in order? Which is the starting stage, and which stage(s) mean it's finished?", "structured", ["workflow.{w}.stages"],
  done={"rule": "stages", "min": 2, "keys": ["stages", "initial", "terminal"]})
Q("FL.03", "For each move from one stage to the next: is it done by a person (which roles) or does it happen automatically when something happens (what)?",
  "structured", ["workflow.{w}.transitions"],
  done={"rule": "per_transition", "keys": ["from", "to", "mover"], "mover_one_of": ["roles", "automatic"], "if_mover": {"roles": ["roles"], "automatic": ["event"]}},
  notes="Handoff only allowed a person as mover. 'Order becomes Paid when payment arrives' had no home.")
Q("FL.04", "Must anything be true before a move is allowed (e.g. can't ship without an address)? For each move: the condition, or none.",
  "structured", ["workflow.{w}.preconditions"], done={"rule": "per_transition_optional", "keys": ["from", "to", "condition"]})
Q("FL.05", "Does any stage need someone's approval before it can move on? Which stage, and which roles approve?", "structured", ["workflow.{w}.approvals"],
  done={"rule": "approvals_list", "min": 0, "keys": ["stage", "approvers"], "roles_keys": ["approvers"]})
Q("FL.06", "If an approver says no, which stage does it go back to, and can it be resubmitted?", "structured", ["workflow.{w}.on_reject"],
  gate=g("FL.05", "min_items", 1), done={"rule": "structured", "keys": ["back_to", "resubmit"]},
  notes="Handoff locked 'standard advance/revert' as a default. Back to previous vs back to start vs terminal Rejected are three different products.")
Q("FL.07", "Can it be cancelled? By whom, and from which stages?", "structured", ["workflow.{w}.cancel"],
  done={"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by", "from_stages"]}, "roles_keys": ["by"]})
Q("FL.08", "Once it reaches a finished stage, what should happen? (e.g. nothing, lock it, send something, create something)", "text", ["workflow.{w}.on_complete"])
Q("FL.09", "From which stage onward, if any, should the record become read-only?", "choice", ["workflow.{w}.readonly_from"],
  options=["<a stage>", "never"], done={"rule": "stage_or_never", "from": "FL.02"})
Q("FL.10", "Does any stage have a time limit? Which stage, how long, and what happens when it runs out?", "structured", ["workflow.{w}.timeouts"],
  done={"rule": "timeouts_list", "min": 0, "keys": ["stage", "duration", "then"]}, feeds=["OPS"])
Q("FL.11", "Should anyone be told when it moves stage? Which moves, who, and by which channel?", "structured", ["workflow.{w}.stage_notifications"],
  done={"rule": "notify_list", "min": 0, "keys": ["transition", "recipients", "channels"]},
  creates={"kind": "notification", "each": True},
  notes="Owners never list 'tell the assignee on stage change' as a notification in A.15. Asked here so it exists.")

part("FLX", "Flow — external systems", per="integration", intro="Once per confirmed external system (incl. 'Public API' if A.11 = yes).")
Q("FLX.01", "Why do you need '${integration}' — what is it for?", "text", ["integration.{i}.purpose"])
Q("FLX.02", "What does your app send to it, and what does it get back?", "structured", ["integration.{i}.sends", "integration.{i}.receives"],
  done={"rule": "structured", "keys": ["sends", "receives"]})
Q("FLX.03", "When does that exchange happen — when something happens in your app (what), on a schedule (when), or when someone presses a button (who)?",
  "structured", ["integration.{i}.timing"], done={"rule": "structured", "keys": ["kind"], "one_of": {"kind": ["event", "schedule", "manual"]},
                                                  "if_any": {"event": ["event"], "schedule": ["schedule"], "manual": ["who"]}}, feeds=["OPS"])
Q("FLX.04", "Is it one connection for the whole organisation, or does each person connect their own account?", "choice", ["integration.{i}.connection_scope"],
  options=["organisation", "per_user"])
Q("FLX.05", "If '${integration}' is unavailable, what should the person see — a blocking message, nothing (it quietly retries later), or the app carries on without it?",
  "choice", ["integration.{i}.on_unavailable"], options=["block_with_message", "queue_silently", "continue_without"])

# ----------------------------------------------------------------------------
# PART N — Notify
# ----------------------------------------------------------------------------
part("N", "Notify", per="notification", intro="Once per confirmed notification, including those created by FL.11 and RP.08 (those arrive pre-filled and only ask what is still empty).")
Q("N.01", "What sends '${notification}' — something happening (what), a time relative to a date on a record (which date, how long before/after), or a fixed schedule?",
  "structured", ["notification.{n}.trigger"],
  done={"rule": "structured", "keys": ["kind"], "one_of": {"kind": ["event", "relative_to_date", "schedule"]},
        "if_any": {"event": ["event"], "relative_to_date": ["record", "date_field", "offset"], "schedule": ["schedule"]}}, feeds=["OPS"])
Q("N.02", "Who receives it — roles, the record's owner, a person named in a field on the record (which), or someone else?",
  "structured", ["notification.{n}.recipients"], done={"rule": "recipients", "min": 1, "kinds": ["roles", "owner", "field", "custom"]})
Q("N.03", "Which channels — email, SMS, push, in-app? (any)", "multi", ["notification.{n}.channels"], options=["email", "sms", "push", "in_app"])
Q("N.04", "What should the recipient understand or do after reading it? (exact wording is drafted at build time and sent to you to approve)",
  "text", ["notification.{n}.intent"])
Q("N.05", "Can the recipient switch this one off?", "yesno", ["notification.{n}.opt_out"])

# ----------------------------------------------------------------------------
# PART RP — Reports
# ----------------------------------------------------------------------------
part("RP", "Reports", per="report")
Q("RP.01", "What question does '${report}' answer for the person reading it?", "text", ["report.{rp}.question"])
Q("RP.02", "Who can view it?", "roles", ["report.{rp}.viewers"])
Q("RP.03", "Is it a live screen in the app, a downloadable document, or both? And shown as a table, a chart, or both?",
  "structured", ["report.{rp}.form"], done={"rule": "structured", "keys": ["delivery", "shape"],
                                            "one_of": {"delivery": ["screen", "document", "both"], "shape": ["table", "chart", "both"]}})
Q("RP.04", "What numbers/metrics does it show? (list them)", "list", ["report.{rp}.metrics"])
Q("RP.05", "For '${metric}': exactly how is it calculated — when does something count, and as at which date?", "text", ["report.{rp}.metric.{m}.definition"],
  per="ambiguous_metric", gate=g("RP.04", "any_item_matches", "AMBIGUOUS_METRIC_TERMS"),
  notes="Fires once per metric whose name contains a flagged term. Unanswered = build blocked, never defaulted.")
Q("RP.06", "What should it be filterable or grouped by, and what date range should it show by default?", "structured", ["report.{rp}.filters", "report.{rp}.default_range"],
  done={"rule": "structured", "keys": ["filters", "default_range"]})
Q("RP.07", "Can it be exported? By whom?", "structured", ["report.{rp}.export"],
  done={"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by"]}, "roles_keys": ["by"]})
Q("RP.08", "Should it be sent to anyone automatically on a schedule? Who, how often?", "structured", ["report.{rp}.scheduled_delivery"],
  done={"rule": "structured", "keys": ["enabled"], "if": {"enabled": "yes", "then_keys": ["recipients", "schedule"]}},
  creates={"kind": "notification", "name": "${report} scheduled delivery", "when": "yes"}, feeds=["OPS"])

# ----------------------------------------------------------------------------
# PART B — Billing
# ----------------------------------------------------------------------------
part("B", "Billing", gate=g("A.09", "eq", "yes"))
Q("B.01", "What are you charging for — subscriptions, one-off purchases, usage, or a mix?", "multi", ["billing.model"],
  options=["subscription", "one_off", "usage"])
Q("B.02", "Who pays — each person, or a whole organisation at once?", "choice", ["billing.charged_party"], options=["person", "organisation"])
Q("B.03", "List your plans. For each: name, price, how often it's billed, what's included, and any limits. Is there a free plan?",
  "structured", ["billing.plans"], done={"rule": "plans_list", "min": 1, "keys": ["name", "price", "interval", "included", "limits"]})
Q("B.04", "What currency do you bill in?", "text", ["billing.currency"], done={"rule": "iso_currency"})
Q("B.05", "Is there a free trial? How long, and is a card required to start it?", "structured", ["billing.trial"],
  gate=g("B.01", "includes", "subscription"),
  done={"rule": "structured", "keys": ["enabled"], "if": {"enabled": "yes", "then_keys": ["days", "card_required"]}},
  notes="Never asked in the handoff.", feeds=["OPS"])
Q("B.06", "What unit is counted for usage billing, and when is it charged?", "structured", ["billing.usage_unit", "billing.usage_charge_timing"],
  gate=g("B.01", "includes", "usage"), done={"rule": "structured", "keys": ["unit", "timing"]})
Q("B.07", "Card only, or can customers also pay by invoice / bank transfer?", "choice", ["billing.payment_methods"], options=["card_only", "card_and_invoice"],
  notes="Locked as 'card via gateway' in the handoff. Pay-by-invoice changes the product (manual reconciliation, dunning), so it is asked.")
Q("B.08", "If a payment fails: keep access for how many days before restricting? And after repeated failure — suspend, downgrade to free, or cancel?",
  "structured", ["billing.on_failure"], done={"rule": "structured", "keys": ["grace_days", "after_repeated"],
                                              "one_of": {"after_repeated": ["suspend", "downgrade", "cancel"]}}, feeds=["OPS"])
Q("B.09", "Can customers change plan themselves? Does an upgrade take effect immediately or at the next cycle? A downgrade?",
  "structured", ["billing.plan_change"], done={"rule": "structured", "keys": ["self_serve", "upgrade_timing", "downgrade_timing"],
                                               "one_of": {"upgrade_timing": ["immediate", "next_cycle"], "downgrade_timing": ["immediate", "next_cycle"]}},
  gate=g("B.01", "includes", "subscription"))
Q("B.10", "Can customers cancel themselves? Do they keep access until the end of the paid period, or lose it immediately?",
  "structured", ["billing.cancellation"], done={"rule": "structured", "keys": ["self_serve", "access_after"], "one_of": {"access_after": ["period_end", "immediate"]}},
  gate=g("B.01", "includes", "subscription"))
Q("B.11", "Are refunds allowed? Who exactly may issue one?", "structured", ["billing.refunds"],
  done={"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by"]}, "roles_keys": ["by"]})

# ----------------------------------------------------------------------------
# PART T — Organisations (tenants)
# ----------------------------------------------------------------------------
part("T", "Organisations (tenants)", gate=g("A.08", "eq", "multiple"))
Q("T.01", "Can one person belong to more than one organisation?", "yesno", ["tenancy.multi_membership"])
Q("T.02", "How does a new organisation come to exist — someone signs up and creates it, or you (the operator) create it?",
  "multi", ["tenancy.creation"], options=["self_signup", "operator_created"])
Q("T.03", "Inside an organisation, which role manages its members and settings?", "choice", ["tenancy.org_admin_role"],
  options=["<a confirmed role>"], done={"rule": "role"},
  notes="Never asked in the handoff. Without it, no builder knows who invites people into an org.")
Q("T.04", "Are the roles the same in every organisation, or can each organisation define its own?", "choice", ["tenancy.roles_scope"],
  options=["same_everywhere", "per_organisation"])
Q("T.05", "Is there an operator role (you) that can see across all organisations? Which role?", "choice", ["tenancy.operator_role"],
  options=["<a confirmed role>", "none"], done={"rule": "role_or_none"})
Q("T.06", "By default, is everything about an organisation — records, files, reports, billing, workflows — completely separate from the others? If not, what is shared and how?",
  "structured", ["tenancy.isolation"], done={"rule": "structured", "keys": ["complete"], "if": {"complete": "no", "then_keys": ["shared"]}})
Q("T.07", "Can organisations set their own branding (logo, colours)?", "yesno", ["tenancy.branding"])
Q("T.08", "Can an organisation be suspended or deleted? By whom, and what happens to its members and data?", "structured", ["tenancy.suspend_delete"],
  done={"rule": "structured", "keys": ["suspend_allowed", "delete_allowed"], "if_any_yes": ["by", "members", "data"], "roles_keys": ["by"]})

# ----------------------------------------------------------------------------
# PART D — Deviations
# ----------------------------------------------------------------------------
part("D", "Deviations", per="deviation", gate=g("A.14", "min_items", 1))
Q("D.01", "You said '${deviation}' should work differently from the standard. Which standard behaviour is it replacing, exactly what should happen instead, "
          "and which screens/records does it apply to? Everything you don't mention keeps the standard behaviour.",
  "structured", ["deviation.{d}.default_overridden", "deviation.{d}.behaviour", "deviation.{d}.scope"],
  done={"rule": "structured", "keys": ["default_id", "behaviour", "scope"], "default_id_in": "DEFAULTS"})

# ----------------------------------------------------------------------------
# PART Z — Read-back (script-generated, owner confirms)
# ----------------------------------------------------------------------------
part("Z", "Read-back", intro="Generated by the script from earlier answers. The owner confirms or corrects; nothing new is asked.")
Q("Z.01", "Here is everything the app will do on its own, with nobody clicking: [derived list of scheduled jobs — retention purges, "
          "stage time-outs, date-relative reminders, scheduled reports, subscription renewals, trial expiries, integration syncs]. Correct?",
  "confirm", ["ops.recurring_operations"], done={"rule": "confirmed"},
  notes="This is the recurring-ops namespace. Each item gets its own OPS-nnn id.")
Q("Z.02", "Here is every numbered button/action in the app and where its result lands: [derived]. Correct?", "confirm", ["actions.inventory"])
Q("Z.03", "Here is every screen, who can open it, and what it shows: [derived]. Correct?", "confirm", ["screens.inventory"])

# ============================================================================
# FIELD TYPES (closed list used by R.02, AU.02, F.02)
# ============================================================================
FIELD_TYPES = ["short_text", "long_text", "whole_number", "decimal_number", "money", "date", "date_time", "yes_no",
               "one_choice", "multi_choice", "email", "phone", "url", "file", "link", "other"]

# ============================================================================
# SYSTEM DEFAULTS — never asked; each overridable only through Part D
# ============================================================================
inherited = [
    ("sys_credential_storage", "security", "Secrets in an environment vault, never in code or the database."),
    ("sys_encryption_rest", "security", "AES-256 at rest for database and file storage."),
    ("sys_encryption_transit", "security", "TLS everywhere; HttpOnly/Secure/SameSite cookies."),
    ("sys_database_identifiers", "records", "UUIDv4 primary keys on every table.", ["record.*.id_strategy"]),
    ("sys_audit_fields", "records", "created_at/updated_at/created_by/updated_by on every table.", ["record.*.audit_fields"]),
    ("sys_request_timeout", "client", "15 s request timeout → transaction aborted, HTTP 504."),
    ("sys_retry_policy", "flow", "Failed external calls retry 3× with exponential backoff + jitter.", ["integration.*.retry_policy"]),
    ("sys_idempotency_webhook", "billing", "Payment webhooks signature-verified and processed exactly once.", ["billing.webhook_handling"]),
    ("sys_duplicate_click", "client", "Submit buttons disable on click."),
    ("sys_error_handling", "client", "RFC 7807 error bodies; stack traces masked in production."),
    ("sys_logging", "client", "Structured JSON audit log of every mutation and failed authorisation."),
    ("sys_file_storage", "files", "Private object storage for uploads.", ["file.*.storage_backend"]),
    ("sys_file_security_scanning", "files", "Async malware scan before a file is marked active.", ["file.*.malware_scanning"]),
    ("sys_file_upload_fail", "files", "Failed upload/scan → file marked broken, transaction rolled back, 400."),
    ("sys_client_isolation", "tenancy", "Row-level security enforces organisation isolation in the database.", ["tenancy.isolation_mechanism"]),
    ("sys_backup_recovery", "ops", "Nightly encrypted backups, 30-day retention."),
    ("sys_session_security_protections", "auth", "Signed session tokens; CSRF-safe cookie rules."),
    ("sys_notification_audit", "notify", "Every notification logged with channel, recipient, status, retries."),
    ("sys_notification_retry", "notify", "3 delivery retries then dead-letter.", ["notification.*.retry_policy"]),
    ("sys_report_storage", "reports", "Generated documents stored transiently behind 1-hour signed URLs."),
    ("sys_report_timeout", "reports", "Report generation times out at 60 s."),
    ("sys_api_convention", "technical", "One fixed REST convention for every endpoint, verb and envelope.", ["api.*"]),
    ("sys_screen_interaction_pattern", "client", "Standard loading / empty / error / success / back / leave-and-return behaviour on every screen.",
     ["screen.*.interaction_states"]),
    ("sys_field_type_defaults", "records", "Each field type carries one standard validation rule and error message.", ["record.*.field.*.validation"]),
    ("sys_report_caching", "reports", "Reports regenerate on demand, cached 5 min.", ["report.*.cache_policy"]),
    ("sys_tax_calculation", "billing", "Tax computed by the payment gateway from the billing address.", ["billing.tax_calculation"]),
    ("sys_notification_copywriting", "notify", "Message wording drafted at build time and approved by the owner before launch; never shipped unseen.",
     ["notification.*.copy_final"]),
    ("sys_file_type_inference", "files", "Allowed formats come from a fixed allow-list per file category.", ["file.*.allowed_mimes"]),
    ("sys_qa_pass_conditions", "qa", "Every node's pass/fail check is generated from that node's own answers.", ["qa.pass_condition.*"]),
]
for row in inherited:
    default(row[0], row[1], row[2], row[3] if len(row) > 3 else ())

added = [
    ("sys_account_identity", "auth", "The email address is the account identity; changing it requires re-verification.", ["auth.identity_field"],
     "Handoff never stated what identifies an account."),
    ("sys_password_reset", "auth", "Self-service reset by emailed link, valid 1 hour.", ["auth.self_reset_flow"], None),
    ("sys_mfa_recovery", "auth", "One-time recovery codes issued at MFA enrolment.", ["auth.mfa_recovery"],
     "Classification kept this as a question; owners cannot meaningfully choose otherwise."),
    ("sys_profile_self_edit", "auth", "Every user can edit their own name, email, password and notification preferences.", ["auth.profile_self_service"], None),
    ("sys_suspended_experience", "auth", "A suspended user sees a fixed 'account suspended — contact <support contact>' screen and nothing else.",
     ["auth.suspended_screen"], None),
    ("sys_first_admin", "auth", "The first super-role account is seeded from the deploy inputs, not created through the app.", ["auth.bootstrap_admin"],
     "A complete working app needs a first login; nothing in the handoff created one."),
    ("sys_theme", "client", "Light theme only; WCAG 2.1 AA contrast and keyboard access.", ["visual.theme", "visual.accessibility"], None),
    ("sys_locale_formatting", "client", "Dates, numbers and currency display in the format of A.13's region; stored in UTC; shown in the viewer's timezone.",
     ["locale.formatting", "locale.timezone_handling"], None),
    ("sys_concurrent_edit", "records", "Last save wins; a user saving over a newer version is warned and shown the newer version.", ["record.*.concurrency"], None),
    ("sys_list_behaviour", "records", "Every record list is searchable and filterable on its visible fields, sorted newest first, exportable by anyone who can view it.",
     ["record.*.list_behaviour", "record.*.exportable"], None),
    ("sys_form_failure", "forms", "A failed submit shows inline errors and keeps what was typed; forms are single-page; public forms get spam protection.",
     ["form.*.on_failure", "form.*.layout", "form.*.spam_protection"], None),
    ("sys_inapp_inbox", "notify", "If any notification uses in-app, the app has one notification inbox with read/unread state.", ["notify.inbox"], None),
    ("sys_image_handling", "files", "Images get thumbnails; downloads are served by signed URL.", ["file.*.image_handling"], None),
    ("sys_limit_reached", "billing", "Hitting a plan limit shows an upgrade prompt, then blocks the action.", ["billing.on_limit_reached"], None),
    ("sys_billing_details", "billing", "Card, billing address and tax IDs are collected by the gateway's hosted form; invoices/receipts are the gateway's.",
     ["billing.details_collection", "billing.invoices"], None),
    ("sys_proration", "billing", "Mid-cycle plan changes are prorated by the gateway.", ["billing.proration_rule"], None),
    ("sys_org_switcher", "tenancy", "A person in several organisations switches with a standard switcher; each organisation has its own timezone setting defaulting to A.13.",
     ["tenancy.switcher", "tenancy.org_settings"], None),
    ("sys_invite_expiry", "auth", "Invitations expire after 7 days and can be re-sent.", ["auth.invite_expiry"], None),
]
for id, area, beh, fields, why in added:
    default(id, area, beh, fields, why)

# ============================================================================
# DERIVATIONS — computed, never asked; each must pass the two-builder test
# ============================================================================
derive("D01", ["record.*.field.*.storage_type"], ["R.02"], "Fixed 1:1 map from field type to column type.", "Exhaustive, unique per type.")
derive("D02", ["form.*.fields"], ["F.02", "R.02"], "Form fields = target record's fields + extra fields.", "Restatement of answers.")
derive("D03", ["screen.*.contents", "screen.*.access", "role.*.visible_screens"], ["A.15", "R.05", "R.06", "R.07", "R.08", "FL.03", "FL.05"],
       "A screen shows its record/form fields; a role sees a screen if it can view/act on anything on it.", "Mechanical union of explicit grants.")
derive("D04", ["role.*.permitted_actions", "role.*.forbidden_actions", "role.*.is_admin"], ["R.05", "R.06", "R.07", "R.08", "R.15", "FL.03", "FL.05", "FL.07", "AU.11", "AU.12", "AU.13", "P.04", "B.11"],
       "Permitted = every explicit grant; forbidden = everything else (default deny); admin = any user-management grant.", "Enumeration, no judgement.")
derive("D05", ["notification.*.timing"], ["N.01"], "Immediate on event; offset for relative_to_date; cron for schedule.", "Read from the owner's own trigger.")
derive("D06", ["file.*.retention"], ["R.14", "FI.01"], "File inherits its parent record's retention.", "Direct inheritance.")
derive("D07", ["report.*.data_source", "report.*.metric.*.derived_definition"], ["RP.04", "RP.05", "R.02"],
       "Unflagged metric = count/sum of the named field; flagged metric = RP.05 text.", "Flagged terms never derive.")
derive("D08", ["workflow.*.transition_graph"], ["FL.02", "FL.03"], "Edges exactly as listed in FL.03; nothing added.", "Never invents a transition.")
derive("D09", ["tenancy.role_visibility"], ["T.05", "T.06"], "Operator role sees all orgs; everyone else sees their memberships.", "Restatement.")
derive("D10", ["billing.plan_linkage"], ["B.03"], "Each subscription event links to one plan by name.", "Restatement.")
derive("D11", ["ops.recurring_operations.items"], ["R.14", "FL.01", "FL.10", "FLX.03", "N.01", "RP.08", "B.05", "B.08"],
       "Every duration/schedule answer becomes one OPS-nnn job; confirmed in Z.01.", "Mechanical collection; owner confirms the list.")
derive("D12", ["actions.inventory.items"], ["R.06", "R.07", "R.08", "R.15", "FL.03", "FL.07", "FL.05", "F.01"],
       "One numbered action per create/edit/delete grant, custom action, transition, cancel, approve, and form submit.", "Enumeration; owner confirms in Z.02.")
derive("D13", ["screens.inventory.items", "client.navigation.derived"], ["A.15", "C.06", "D03"], "One list + one detail screen per record, one per form/report, plus landing per role.",
       "Enumeration; owner confirms in Z.03 / C.07.")
derive("D14", ["record.*.field.*.storage_type_for_options"], ["R.02"], "Choice options become an enum with the exact listed values.", "Restatement.")
derive("D15", ["qa.generated_tests"], ["*"], "For every numbered action and transition: perform it as each role, assert the declared outcome and location.",
       "Definitionally downstream of answers; no LLM in the pass/fail path.")

# ============================================================================
# DEPLOY INPUTS — block-0 values a working app needs; collected on a form, not in the interview
# ============================================================================
deploy("DI.01", "Web address (domain) the app will live at", ["deploy.domain"])
deploy("DI.02", "Sender name and email address for outgoing email", ["deploy.email_sender"])
deploy("DI.03", "Support contact shown to users (email or URL)", ["deploy.support_contact"])
deploy("DI.04", "Email address of the first super-role account", ["deploy.first_admin_email"], gate=g("A.07", "eq", "yes"))
deploy("DI.05", "Hosting region / data residency (e.g. Australia)", ["deploy.region"])
deploy("DI.06", "Payment gateway account credentials", ["deploy.gateway_credentials"], gate=g("A.09", "eq", "yes"))
deploy("DI.07", "SMS provider credentials and sender ID", ["deploy.sms_credentials"], gate=g("N.03", "any_instance_includes", "sms"))
deploy("DI.08", "OAuth client credentials for each social login chosen", ["deploy.oauth_credentials"], gate=g("AU.04", "includes_any", ["google", "microsoft", "apple"]))
deploy("DI.09", "Credentials / API keys for each external system", ["deploy.integration_credentials"], gate=g("A.15", "list_nonempty", "integrations"))
deploy("DI.10", "App-store developer accounts", ["deploy.app_store_accounts"], gate=g("A.06", "includes_any", ["ios", "android"]))
deploy("DI.11", "Terms of service and privacy policy documents (or a request to draft them)", ["deploy.legal_documents"], gate=g("AU.14", "eq", "yes"))


# ============================================================================
# EMIT
# ============================================================================
def build():
    for q in QUESTIONS:
        q["widget"] = WIDGETS.get(q["id"])
    unknown = [k for k in WIDGETS if k not in {q["id"] for q in QUESTIONS}]
    badv = [k for k, v in WIDGETS.items() if v not in WIDGET_VOCAB]
    assert not unknown, f"WIDGETS names unknown questions: {unknown}"
    assert not badv, f"WIDGETS uses undeclared widgets: {badv}"
    graph = OrderedDict(
        version=GRAPH_VERSION,
        part_order=PART_ORDER,
        config=dict(ambiguous_metric_terms=AMBIGUOUS_METRIC_TERMS, super_role_token=SUPER_ROLE_TOKEN,
                    public_role_token=PUBLIC_ROLE_TOKEN, field_types=FIELD_TYPES,
                    widget_vocab=WIDGET_VOCAB),
        parts=list(PARTS.values()),
        questions=QUESTIONS,
        system_defaults=DEFAULTS,
        derivations=DERIVATIONS,
        deploy_inputs=DEPLOY_INPUTS,
        spec_fields=SPEC_FIELDS,
    )
    return graph


def gate_text(gate):
    if not gate:
        return ""
    if "all" in gate:
        return " and ".join(gate_text(x) for x in gate["all"])
    if "any" in gate:
        return " or ".join(gate_text(x) for x in gate["any"])
    op = {"eq": "=", "includes": "includes", "includes_any": "includes any of", "min_items": "has at least",
          "scope_includes": "has scope", "any_item_matches": "any item matches", "any_instance_includes": "any instance includes",
          "list_nonempty": "list non-empty"}[gate["op"]]
    v = gate["value"]
    return f"{gate['q']} {op} {v}"


def to_md(graph):
    L = []
    L.append(f"# Requirements Interview v{graph['version']}\n")
    L.append("Generated from `question_graph_v3.json` by `build_graph.py`. Do not edit by hand — edit the graph and rebuild.\n")
    L.append("Every question has an ID, an answer type, a gate (when it is asked), a done-rule (what counts as answered — the script decides, not the model), "
             "and the spec fields it fills. Per-instance parts repeat once per confirmed item from A.15. The super role from A.16 is skipped in every authority question.\n")
    total_fixed = sum(1 for q in graph["questions"] if not q["per"])
    total_tpl = sum(1 for q in graph["questions"] if q["per"])
    L.append(f"**{total_fixed} fixed questions, {total_tpl} per-instance template questions, {len(graph['system_defaults'])} locked defaults, "
             f"{len(graph['derivations'])} derivations, {len(graph['deploy_inputs'])} deploy inputs, {len(graph['spec_fields'])} spec fields each with exactly one source.**\n")
    parts = {p["code"]: p for p in graph["parts"]}
    for code in graph["part_order"]:
        p = parts[code]
        L.append(f"\n## Part {code} — {p['title']}\n")
        meta = []
        if p["gate"]:
            meta.append(f"asked only if {gate_text(p['gate'])}")
        if p["per"]:
            meta.append(f"repeats once per confirmed **{p['per']}**")
        if meta:
            L.append("*(" + "; ".join(meta) + ")*\n")
        if p["intro"]:
            L.append(p["intro"] + "\n")
        for q in graph["questions"]:
            if q["part"] != code:
                continue
            L.append(f"**{q['id']}** — {q['prompt']}  ")
            bits = [f"type: `{q['type']}`"]
            if q["options"]:
                bits.append("options: " + ", ".join(f"`{o}`" for o in q["options"]))
            if q["gate"]:
                bits.append(f"asked if: {gate_text(q['gate'])}")
            if q["per"] != p["per"]:
                bits.append(f"per: {q['per'] or 'asked once'}")
            if q.get("widget"):
                bits.append(f"visual: `{q['widget']}`")
            bits.append(f"done when: `{json.dumps(q['done'])}`")
            bits.append("fills: " + ", ".join(f"`{f}`" for f in q["fills"]))
            if q["creates"]:
                bits.append(f"creates: `{json.dumps(q['creates'])}`")
            if q["feeds"]:
                bits.append("feeds: " + ", ".join(q["feeds"]))
            L.append("<br>" + " · ".join(bits))
            if q["notes"]:
                L.append(f"<br>*Why: {q['notes']}*")
            L.append("")
    L.append("\n## Field types (closed list for R.02 / AU.02 / F.02)\n")
    L.append(", ".join(f"`{t}`" for t in graph["config"]["field_types"]) + "\n")
    L.append("`one_choice`/`multi_choice` require the options; `link` requires the target record; `other` requires the exact rule. "
             "`whole_number` and `decimal_number` are separate because 'Number' alone makes two builders diverge on decimals.\n")
    L.append("\n## Locked system defaults (never asked; override only via Part D)\n")
    L.append("| ID | Area | Behaviour | Spec fields |\n|---|---|---|---|")
    for d in graph["system_defaults"]:
        L.append(f"| `{d['id']}` | {d['area']} | {d['behaviour']} | {', '.join('`'+f+'`' for f in d['fields']) or '—'} |")
    L.append("\n## Derivations (computed; two-builder safe)\n")
    L.append("| ID | Produces | From | Rule | Safe because |\n|---|---|---|---|---|")
    for d in graph["derivations"]:
        L.append(f"| {d['id']} | {', '.join('`'+f+'`' for f in d['outputs'])} | {', '.join(d['inputs'])} | {d['rule']} | {d['safe_because']} |")
    L.append("\n## Deploy inputs (block 0 — a form, not the interview)\n")
    L.append("| ID | Needed | When |\n|---|---|---|")
    for d in graph["deploy_inputs"]:
        L.append(f"| {d['id']} | {d['prompt']} | {gate_text(d['gate']) or 'always'} |")
    L.append("\n## Ambiguous metric terms (force RP.05)\n")
    L.append(", ".join(graph["config"]["ambiguous_metric_terms"]) + "\n")
    return "\n".join(L)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    graph = build()
    with open(os.path.join(here, OUT_JSON), "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    with open(os.path.join(here, OUT_MD), "w", encoding="utf-8") as f:
        f.write(to_md(graph))
    print(f"wrote {OUT_JSON} ({len(QUESTIONS)} questions, {len(SPEC_FIELDS)} spec fields) and {OUT_MD}")
