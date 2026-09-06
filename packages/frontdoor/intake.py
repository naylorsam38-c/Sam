#!/usr/bin/env python3
"""
intake.py — the answer-sheet -> a built, tested app. The plumbing behind the
front door, not the front door itself.

The one front door is Design 3 ("Show Me"): one open question, matched
against the real catalogue (matcher.py) to propose which templates fit, a
handful of genuinely open items for whatever the match can't resolve, a
provisional app built and shown in all three interfaces before anything is
locked, and an explicit lock step that records the interface choice. Run it
with `python serve.py`, or drive it in a real browser with
`prove_frontdoor.py`.

Of the 122 questions in the graph, every template already answers all but
17; this module fills all but a handful of those 17 itself (AUTO, below,
with the real reason recorded, never hidden) so a person only ever answers
what nothing else can resolve: which pieces, who uses it, how dense, the
mark, the name, what it must not do, and -- once they've seen it running --
which interface. It never guesses any of them.

Nothing here designs anything. It selects from templates that already exist
and combines them with the assembly engine's own `combine`, which refuses
rather than reconciling a clash silently.

Usage (direct, for scripts that already have a filled answer sheet -- the
front door itself is serve.py, not this):
  python intake.py answers.json -o out/ [--lock console|board|pocket]
"""

import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for p in ("requirements-engine", "assembly-engine", "builder", "interfaces"):
    sys.path.insert(0, os.path.join(ROOT, p))
sys.path.insert(0, HERE)
import graph_lib          # noqa: E402
import check_template     # noqa: E402
import assemble as ae     # noqa: E402
import builder as bl      # noqa: E402
import make_interfaces as mi  # noqa: E402
import catalogue as cat   # noqa: E402

GRAPH = os.path.join(ROOT, "requirements-engine", "question_graph_v3.json")
TEMPLATES = os.path.join(ROOT, "requirements-engine", "templates")

# ============================================================================
# RULES / CONFIG — edit these, not the logic below.
# ============================================================================
#: Two records that mean the same thing under different names. Applied only when
#: BOTH are present in the selected templates -- the assembly engine refuses an
#: unreconciled clash rather than merging two different records into one.
SAME_THING = {"Customer": "Contact", "Customer account": "Contact"}

#: What a "Who uses it?" answer means. Nothing here invents a role: it picks
#: from the roles the chosen templates already declare, and decides whether the
#: public form (which only the booking family has) is kept.
WHO_USES = {
    "just_me":    {"label": "Just me",
                   "means": "One person does everything. Every job in the app is yours.",
                   "collapse_roles": True,  "public": False},
    "small_team": {"label": "A few of us, doing different jobs",
                   "means": "The app's own roles are kept, so each person only sees and does their part.",
                   "collapse_roles": False, "public": False},
    "team_public": {"label": "My team, plus the public",
                    "means": "Your team's roles are kept, and outsiders get a public page with no account.",
                    "collapse_roles": False, "public": True},
}

#: The three interfaces, by the real generator's own ids.
LOOKS = {
    "console": {"label": "Console", "for": "Sitting at a desk with a lot of rows in front of you.",
                "shot": "console.png"},
    "board":   {"label": "Board", "for": "Seeing what is at which stage, and dragging work along.",
                "shot": "board.png"},
    "pocket":  {"label": "Pocket", "for": "On a phone, on your feet, big buttons.",
                "shot": "pocket.png"},
}

#: How dense a screen should be -- a real open item (F1: no default, ever),
#: never assumed.
DENSITY_OPTIONS = [
    {"value": "spacious", "label": "Roomy", "sub": "Fewer things, more space around them."},
    {"value": "balanced", "label": "Balanced", "sub": "The middle."},
    {"value": "dense", "label": "Packed", "sub": "As much as will fit."},
]
#: The person's mark, from the real logo generator's own catalogue, plus the
#: one explicit "decide later" choice -- itself an answer the person picks,
#: not a value filled in for them.
MARK_OPTIONS = [
    {"value": lid, "label": l["name"], "sub": l["description"], "colour": l["colour"]}
    for lid, l in sorted(bl.LOGOS.items())
] + [{"value": "design_for_me", "label": "Decide later", "sub": "Your app's name in plain type for now."}]

#: Answers the person is never asked for, and why each is safe to fill. Printed
#: to them at the end, so an unasked question is visible, not hidden.
AUTO = {
    "0.01": ("guided", "You decide the product; the plumbing is proposed and shown to you at the end."),
    "A.02": (None, "Taken from what you said the app should do."),
    "A.03": (None, "Taken from who you said uses it."),
    "A.04": (None, "Taken from what you said the app should do."),
    "A.12": ({"required": "no"}, "Nothing is being imported from an old system. Say so and this changes."),
    "A.13": ({"region": "Australia", "languages": ["English"]}, "Dates, money and times use Australian English."),
    "A.14": ([], "Nothing about this app works differently from the normal way."),
    "C.01": ("none", "No other app's look is being copied."),
    "C.02": (None, "Taken from the look you picked."),
    "C.07": ("confirmed", "The menu is the order the screens were built in."),
    "Z.01": ("confirmed", "What the app does on its own is listed in your summary."),
    "Z.02": ("confirmed", "Every button and where its result lands is listed in your summary."),
    "Z.03": ("confirmed", "Every screen and who can open it is listed in your summary."),
}
#: A question a single template leaves open, whose answer is already settled by
#: that template's own structure. Each entry says what the answer is derived
#: from and refuses if that derivation does not hold -- so this can never become
#: a place where an unanswered question is quietly given a made-up value.
def _charges_from_services(inst):
    """B.03 asks what you charge. The booking template already declares that
    charges are one-off (B.01) and that every Service carries its own Price
    (R.02:Service). So the plan list is not a guess: it is one charge per
    appointment, at whatever price is set on the Service being booked."""
    if inst["answers"].get("B.01") != ["one_off"]:
        raise IntakeRefused("B.03 can only be derived when charges are one-off; this app declares "
                            f"{inst['answers'].get('B.01')!r}, so what you charge is a real question.")
    fields = {f["name"] for f in inst["per_instance"].get("R.02:Service") or []}
    if "Price" not in fields:
        raise IntakeRefused("B.03 can only be derived when a Service carries its own Price; it does not.")
    return ([{"name": "Per appointment", "price": "the Price set on the Service being booked",
              "interval": "one_off", "included": "one appointment of that service", "limits": "none"}],
            "What you charge is one payment per appointment, at whatever price you set on each service "
            "inside the app. There are no subscriptions or plans.")


DERIVED_FROM_TEMPLATE = {"B.03": _charges_from_services}
TONE_FOR_LOOK = {"console": ["clear", "efficient", "calm"],
                 "board": ["visual", "open", "friendly"],
                 "pocket": ["quick", "simple", "direct"]}
# ============================================================================


class IntakeRefused(Exception):
    """The answers ask for something this system will not guess at."""


# ---------------------------------------------------------------- the questions
def _templates_for(cards):
    picked = [c for c in cat.CAPABILITIES if c["id"] in (cards or [])]
    if not picked:
        raise IntakeRefused("nothing was picked, so there is nothing to build. Pick at least one card.")
    return picked


def _boss_question(answers):
    """Two families that each had a person in charge cannot both be in charge of
    the merged app -- and the demoted one now needs authority answers it never
    needed alone. The assembly engine refuses this rather than guessing; this is
    the question that answers it. It is asked only when it is real."""
    try:
        picked = _templates_for(answers.get("cards"))
    except IntakeRefused:
        return None
    if answers.get("who") == "just_me":
        return None                      # one person: no authority to divide
    supers = []
    for cap in picked:
        t = json.load(open(os.path.join(TEMPLATES, cap["template"] + ".json"), encoding="utf-8"))
        if t.get("super_role") and t["super_role"] not in [s[0] for s in supers]:
            supers.append((t["super_role"], cap["name"]))
    if len(supers) < 2:
        return None
    return {"id": "boss", "kind": "tap_one", "ask": "Who is in charge?",
            "help": "The pieces you picked each came with someone in charge. In one app, one of them is.",
            "options": [{"value": r, "label": r, "sub": f"the person in charge of {where.lower()}"} for r, where in supers]}


# ---------------------------------------------------------------- answers -> instance
def _reconcile_for(picked):
    """Which record renames the union really needs: only where two chosen
    templates hold the same thing under different names."""
    names = {r for cap in picked for r in cap["records"]}
    return {old: new for old, new in SAME_THING.items() if old in names and new in names}


def _demote(inst, boss, demoted, filled):
    """A role that was in charge of its own family and is not in charge of the
    merged app. It now needs the authority answers every ordinary role has.
    Rather than invent them, this copies them from an ordinary role of that
    role's own template -- an answer that template's author already gave for a
    role in exactly this position. If there is no such role, it refuses."""
    src = None
    for key in list(inst["per_instance"]):
        if key.startswith("P.02:") and key.split(":", 1)[1] != demoted:
            src = key.split(":", 1)[1]
            break
    if src is None:
        raise IntakeRefused(
            f"{demoted!r} is no longer in charge, and there is no ordinary role to take its "
            f"authority answers from. This needs a real decision about what {demoted!r} may do.")
    inst["per_instance"][f"P.01:{demoted}"] = (
        f"Was in charge before the pieces were joined; now an ordinary role, with the same "
        f"authority as {src}.")
    for qid in ("P.02", "P.03", "P.04"):
        got = inst["per_instance"].get(f"{qid}:{src}")
        if got is not None:
            inst["per_instance"][f"{qid}:{demoted}"] = [boss] if qid == "P.04" else copy.deepcopy(got)
    filled.append((f"authority of {demoted}",
                   f"{demoted} was in charge of its own piece; you put {boss} in charge, so {demoted} "
                   f"now has the same authority as {src}, and {boss} assigns it."))


def build_instance(answers):
    """The eight answers -> a real, complete instance the chain will accept.
    Returns (instance, filled) where `filled` is every answer the person was
    never asked for, with the reason -- shown to them, never hidden."""
    cat.verify()
    picked = _templates_for(answers.get("cards"))
    # 'look' is deliberately not required here: Design 3's provisional build
    # renders all three interfaces before anything is locked, and no default
    # look is ever guessed. It becomes required at lock time instead (see
    # finalize_look() below).
    for required in ("who", "density", "mark", "name"):
        if not answers.get(required):
            raise IntakeRefused(f"{required!r} has no answer; the front door does not fill it in for you.")
    if answers.get("must_not") is None:
        raise IntakeRefused("'must_not' has no answer; say 'nothing' if there are no exclusions, "
                            "but it must be answered.")
    filled = []
    graph = graph_lib.load_graph(GRAPH)
    graph["_q"] = {q["id"]: q for q in graph["questions"]}

    paths = [os.path.join(TEMPLATES, c["template"] + ".json") for c in picked]
    if len(paths) == 1:
        inst = json.loads(open(paths[0], encoding="utf-8").read())
    else:
        reconcile = _reconcile_for(picked)
        boss = answers.get("boss")
        order = paths
        if boss:
            # the family whose person is in charge leads the union, because the
            # union takes its super role from the first instance
            lead = [p for p, c in zip(paths, picked)
                    if json.load(open(p, encoding="utf-8")).get("super_role") == boss]
            order = lead + [p for p in paths if p not in lead]
        inst = ae.combine(order, reconcile)
        for old, new in reconcile.items():
            filled.append((f"{old} and {new}", f"Both pieces you picked hold the same kind of person, "
                                               f"under different names. They are one record, called {new}."))
        supers = {json.load(open(p, encoding="utf-8")).get("super_role") for p in paths}
        supers.discard(None)
        if len(supers) > 1:
            if not boss:
                raise IntakeRefused("two of the pieces you picked each came with someone in charge; "
                                    "answer 'Who is in charge?' before this can be built.")
            for demoted in sorted(supers - {boss}):
                _demote(inst, boss, demoted, filled)
            inst["super_role"] = boss

    # ---- the person's own answers
    a = inst["answers"]
    a["A.01"] = answers["does"]
    a["A.05"] = answers["name"]
    a["C.03"] = answers["density"]
    a["C.04"] = ({"mode": "design_for_me"} if answers["mark"] == "design_for_me"
                 else {"mode": "premade", "logo_id": answers["mark"]})
    # Real tone if a look has already been chosen; an honestly-labelled
    # placeholder otherwise (C.02 is a free 3-word list, min_items:3 -- this
    # satisfies the graph without claiming a real aesthetic decision was
    # made). Real words are written at lock time by finalize_look().
    a["C.02"] = TONE_FOR_LOOK[answers["look"]] if answers.get("look") else ["not", "yet", "locked"]
    who = WHO_USES[answers["who"]]
    a["A.03"] = who["means"]
    a["A.02"] = f"Use it to {answers['does'].strip().rstrip('.').lower()}."
    a["A.04"] = "It is being used, and what it holds is what is really going on."
    for qid, (value, reason) in AUTO.items():
        if value is not None:
            a[qid] = copy.deepcopy(value)
        filled.append((qid, reason))
    # every question every chosen template still leaves open must now be answered
    for qid in list(inst["ask_customer"]):
        if qid in a or qid not in DERIVED_FROM_TEMPLATE:
            continue
        value, reason = DERIVED_FROM_TEMPLATE[qid](inst)
        a[qid] = value
        filled.append((qid, reason))
    still_open = [q for q in inst["ask_customer"] if q not in a]
    if still_open:
        raise IntakeRefused("these are still unanswered and the front door will not guess them: "
                            + ", ".join(still_open))
    inst["ask_customer"] = []

    if who["collapse_roles"]:
        filled.append(("the different kinds of user",
                       "You said one person does everything, so the roles stay as built but you hold "
                       "the one in charge, which can do all of them."))
    if not who["public"] and inst["inventory"]["forms"]:
        filled.append(("the public page",
                       "The booking piece comes with a page the public can use. You said your team only, "
                       "so it is built but only your people can reach it."))

    if inst["structure"].get("interface"):
        inst["structure"]["interface"]["chosen"] = answers.get("look")
    inst["template"] = "+".join(c["template"] for c in picked)
    inst["front_door"] = {"answers": answers, "filled_without_asking": filled, "must_not": answers.get("must_not"),
                          "note": "Built by packages/frontdoor/intake.py."}
    errors = check_template.check(graph, inst)
    if errors:
        raise IntakeRefused("the answers do not make a buildable app:\n  - " + "\n  - ".join(errors))
    return inst, filled


# ---------------------------------------------------------------- build it
def run(answers, out_dir, port=8900):
    inst, filled = build_instance(answers)
    graph = graph_lib.load_graph(GRAPH)
    graph["_q"] = {q["id"]: q for q in graph["questions"]}
    os.makedirs(out_dir, exist_ok=True)
    spec = ae.assemble(graph, inst, spec_id="SPEC-FRONTDOOR", title=answers["name"])
    json.dump(inst, open(os.path.join(out_dir, "INSTANCE.json"), "w", encoding="utf-8"), indent=1, default=str)
    json.dump(spec, open(os.path.join(out_dir, "SPEC.json"), "w", encoding="utf-8"), indent=1, default=str)
    open(os.path.join(out_dir, "SPEC.md"), "w", encoding="utf-8").write(ae.render_markdown(spec))
    app_dir = os.path.join(out_dir, "app")
    result = bl.build(spec, app_dir, port=port)
    model = mi.model_from_spec(spec)
    static = os.path.join(app_dir, "static")
    # the accent comes from the first piece they picked, so a combined app still
    # has one colour rather than an invented one
    accent_family = _templates_for(answers["cards"])[0]["template"]
    chosen = spec["build_model"]["interface"]["chosen"]
    for design in mi.DESIGNS:
        html = mi.page(model, design, accent_family)
        open(os.path.join(static, f"ui-{design}.html"), "w", encoding="utf-8").write(html)
    # '/' serves the picked design directly once one is chosen -- landing on
    # a second picker there would undo the answer just given. Before a
    # choice exists (Design 3's provisional build, shown via /ui-*.html in
    # an iframe, never via '/'), '/' falls back to the three-way chooser
    # rather than guessing a design.
    open(os.path.join(static, "index.html"), "w", encoding="utf-8").write(
        mi.page(model, chosen, accent_family) if chosen else mi.chooser(model, accent_family))
    json.dump(model, open(os.path.join(out_dir, "MODEL.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(out_dir, "YOUR_APP.md"), "w", encoding="utf-8").write(summary(answers, spec, filled))
    return spec, app_dir, result, filled


def finalize_look(out_dir, look):
    """The person has seen the three real interfaces (run() built all of
    them) and confirmed which one is right. Writes that choice through the
    same real path as everything else -- reassembles from the instance
    build_instance() already produced, rather than hand-patching JSON files
    -- so SPEC.json, C.02, and the page actually served all agree. Refuses
    a look that isn't one of the three real ones; never defaults."""
    if look not in ("console", "board", "pocket"):
        raise IntakeRefused(f"{look!r} is not one of the three real interfaces (console, board, pocket)")
    inst_path = os.path.join(out_dir, "INSTANCE.json")
    if not os.path.exists(inst_path):
        raise IntakeRefused(f"no provisional build at {out_dir} -- run() must build one before it can be locked")
    prior = json.load(open(inst_path, encoding="utf-8"))
    answers = dict(prior["front_door"]["answers"], look=look)
    inst, filled = build_instance(answers)
    graph = graph_lib.load_graph(GRAPH)
    graph["_q"] = {q["id"]: q for q in graph["questions"]}
    spec = ae.assemble(graph, inst, spec_id="SPEC-FRONTDOOR", title=answers["name"])
    json.dump(inst, open(inst_path, "w", encoding="utf-8"), indent=1, default=str)
    json.dump(spec, open(os.path.join(out_dir, "SPEC.json"), "w", encoding="utf-8"), indent=1, default=str)
    open(os.path.join(out_dir, "SPEC.md"), "w", encoding="utf-8").write(ae.render_markdown(spec))
    model = mi.model_from_spec(spec)
    accent_family = _templates_for(answers["cards"])[0]["template"]
    static = os.path.join(out_dir, "app", "static")
    open(os.path.join(static, "index.html"), "w", encoding="utf-8").write(mi.page(model, look, accent_family))
    json.dump(model, open(os.path.join(out_dir, "MODEL.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(out_dir, "YOUR_APP.md"), "w", encoding="utf-8").write(summary(answers, spec, filled))
    return spec


def summary(answers, spec, filled):
    """The person's own page: what they asked for, what they got, what it will do
    on its own, and -- the part that must never be left out -- what was not built."""
    bm = spec["build_model"]
    L = [f"# {spec['title']}", "",
         f"> {answers['does'].strip()}", "",
         "This is what was built from your eight answers, in plain English.", "",
         "## What is in it", ""]
    for name, rec in bm["records"].items():
        wf = bl._workflow_for(spec, name)
        line = f"- **{name}** — {(rec.get('lifecycle') or {}).get('has') == 'yes' and 'moves through ' or ''}"
        if wf:
            stages = bl._stage_names(wf)
            line = f"- **{name}** — moves through {' → '.join(stages)}"
        else:
            line = f"- **{name}**"
        fields = ", ".join(list(rec["fields"])[:6])
        L.append(f"{line}. Holds: {fields}.")
    L += ["", "## Who can do what", ""]
    for role, r in bm["roles"].items():
        if r.get("is_admin"):
            L.append(f"- **{role}** — in charge; can do everything.")
        else:
            verbs = sorted({p["action"] for p in r["permitted"]})
            L.append(f"- **{role}** — can {', '.join(verbs) or 'view what they are given'}.")
    if bm.get("reports"):
        L += ["", "## What it will tell you", ""]
        for name, rep in bm["reports"].items():
            L.append(f"- **{name}** — {rep.get('data_source') or ''}")
    if bm.get("recurring_ops"):
        L += ["", "## What it does on its own, with nobody clicking", ""]
        for op in bm["recurring_ops"]:
            L.append(f"- {op.get('what') or op.get('id')}")
    L += ["", "## Three ways to look at it", "",
          "The same app, three interfaces — open any of them:", "",
          "- `app/static/ui-console.html` — sidebar and tables, for a desk",
          "- `app/static/ui-board.html` — a column per stage, for seeing the flow",
          "- `app/static/ui-pocket.html` — built for a phone",
          "",
          (f"You picked **{LOOKS[answers['look']]['label']}**. The other two are there anyway."
           if answers.get("look") else
           "**Not locked yet** — try all three, then say which one is right."), ""]
    L += ["## What you were not asked, and what was assumed", "",
          "Every one of these can be changed — they were filled in so you did not have to answer them.", ""]
    for what, why in filled:
        L.append(f"- **{what}** — {why}")
    L += ["", "## What this does NOT do", "",
          "Said plainly, so it is not a surprise later.", ""]
    must_not = (answers.get("must_not") or "").strip()
    if must_not and must_not.lower() != "nothing":
        L.append(f"- **What you said to exclude:** {must_not}")
    for g in cat.NOT_ON_THE_SHELF:
        L.append(f"- **{g['plain']}** {g['why']} {('_' + g['instead'] + '_') if g['instead'] else ''}")
    L += ["", "## Is it actually working?", "",
          "Every button in all three interfaces is pressed in a real browser and the result is checked "
          "against the app's own data — not against what the screen claims. Run it yourself:", "",
          "```bash", "cd app && python3 app.py        # then open http://127.0.0.1:8900/", "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- examples + cli
EXAMPLES = {
    "connecting-people": {
        "does": "Something for connecting people — I want to keep everyone's details, see who is at "
                "what stage of joining, and log every time we talk to them.",
        "cards": ["people"], "who": "small_team", "look": "board", "density": "balanced",
        "mark": "orbit", "name": "Connector", "must_not": "nothing",
    },
    "clinic": {
        "does": "Take bookings for my clinic and invoice people afterwards.",
        "cards": ["bookings", "money"], "who": "team_public", "look": "pocket", "density": "spacious",
        "mark": "wave", "name": "Front Room", "boss": "Owner", "must_not": "nothing",
    },
}


def main(argv=None):
    """The one front door is the matcher-driven flow serve.py/web/ runs
    (`python serve.py`) or the Chromium-driven prove_frontdoor.py. This CLI
    is for driving run()/finalize_look() directly against a filled answer
    sheet (a dict shaped like build_instance() expects), e.g. for a script
    that already knows every answer -- it does not ask anything itself."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answers", help="a filled answer sheet (JSON)")
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "build"))
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--lock", help="also call finalize_look() with this look (console/board/pocket)")
    args = ap.parse_args(argv)

    answers = json.load(open(args.answers, encoding="utf-8"))
    try:
        spec, app_dir, result, filled = run(answers, args.out, args.port)
        if args.lock:
            spec = finalize_look(args.out, args.lock)
    except (IntakeRefused, ae.Refused, bl.BuildRefused) as e:
        print("REFUSED —", e, file=sys.stderr)
        return 2
    print(f"{answers['name']}: {len(result['records_built'])} records, {result['screens_built']} screens, "
          f"3 interfaces -> {app_dir}")
    print(f"  filled in without asking: {len(filled)}   ·   summary: {args.out}/YOUR_APP.md   ·   "
          f"look: {spec['build_model']['interface'].get('chosen') or 'not locked'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
