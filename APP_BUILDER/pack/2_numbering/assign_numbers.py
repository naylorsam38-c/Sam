#!/usr/bin/env python3
"""
assign_numbers.py -- allocate APP and CAP numbers to returned harvest forms.

Governed by GOD_MODE_RULE_NUMBERING.md.

  N1  apps numbered sequentially by category, in harvest order
  N2  capabilities numbered ONCE, globally, in a shared registry
  N3  variants are separate capabilities; no per-app duplicates
  N4  an app is a tree of references, down to the button
  N5  references, never copies
  N6  CAP-0000 reserved for the shared library

Drop filled harvest forms into FORMS_DIR and run this. An app gets its sequential
number. Each capability resolves to a number that already exists in the registry,
or mints a new one only if the capability has never been seen before.

Seventy apps through this yields ONE 'log in' number, referenced seventy times.
"""

# =====================================================================
# RULES / CONFIG  -- edit these, nothing below this block
# =====================================================================

FORMS_DIR = "forms"
# Where the filled harvest forms live. Every *.form.json in here is considered.

REGISTRY_PATH = "number_registry.json"
# THE source of truth: which app numbers and which capability numbers exist.
# Delete this and every number is handed out again from scratch.

TREE_DIR = "trees"
# Where the app tree files are written -- one <app>.tree.json per app, plus a
# human-readable <app>.tree.txt. This is the N4 tree: app, screens, controls,
# every leaf a numbered reference.

FIRST_APP = 1
# First app number. App one is whatever category is harvested first.

FIRST_CAP = 1
# First capability number. CAP-0001 onward. CAP-0000 is reserved (N6).

RESERVED_CAP_IDS = ["CAP-0000"]
# Never allocated. CAP-0000 is the Shared Library Contract, section 3.

IDENTITY_VARIANTS = [
    "standard individual",
    "role-based privileged",
    "two-sided peer",
    "guest/anonymous",
    "service/system",
]
# The five identity types from god mode section 6. A capability listed in
# VARIANT_CAPABILITIES gets one number PER variant and no more -- five logins
# across the whole library, never one per app. Add a variant here and you widen
# that set for every variant-carrying capability.

VARIANT_CAPABILITIES = [
    "log in",
    "log out",
    "register account",
]
# Capabilities whose behaviour genuinely differs by identity type. These are
# numbered as "<name> [<variant>]". Everything NOT in this list gets exactly one
# number for the whole library. Adding a capability here multiplies it by the
# number of IDENTITY_VARIANTS -- do not add anything that does not truly differ.

DEFAULT_VARIANT = "standard individual"
# Which variant an app gets when its form does not name one.

SKIP_BLANK_FORMS = True
# True: a form with no app_slug or no capabilities is skipped silently.
# False: a blank form is an error and stops the run.

WRITE_TREES = True
# True: write the tree files to TREE_DIR. False: number the forms only.

DRY_RUN = False
# True: print what would be allocated and write nothing at all.

# =====================================================================
# LOGIC
# =====================================================================

import json
import os
import sys
import glob


def load_registry(path):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {"apps": {}, "capabilities": {}}


def app_id(n):
    return "APP-%03d" % n


def cap_id(n):
    return "CAP-%04d" % n


def next_app_number(reg):
    used = {int(v["number"]) for v in reg["apps"].values()}
    n = FIRST_APP
    while n in used:
        n += 1
    return n


def next_cap_number(reg):
    used = {int(v) for v in reg["capabilities"].values()}
    n = FIRST_CAP
    while n in used or cap_id(n) in RESERVED_CAP_IDS:
        n += 1
    return n


def registry_key(cap_name, variant):
    """N2/N3: one key per genuinely distinct capability."""
    name = cap_name.strip().lower()
    if name in [v.lower() for v in VARIANT_CAPABILITIES]:
        return "%s [%s]" % (name, variant)
    return name


def resolve_cap(reg, cap_name, variant, minted):
    key = registry_key(cap_name, variant)
    if key in reg["capabilities"]:
        return cap_id(reg["capabilities"][key]), False
    n = next_cap_number(reg)
    reg["capabilities"][key] = n
    minted.append((key, cap_id(n)))
    return cap_id(n), True


def build_tree(form, app_num, resolved):
    """N4: app -> screens -> controls, every leaf a numbered reference."""
    by_name = {c["cap_name"].strip().lower(): c["cap_id"]
               for c in form.get("capabilities", []) if c.get("cap_name")}
    tree = {
        "app_id": app_id(app_num),
        "app_slug": form.get("app_slug", ""),
        "category": form.get("app_type", ""),
        "screens": [],
        "unbound_controls": [],
    }
    for scr in form.get("screens") or []:
        node = {"screen": scr.get("screen_name", ""), "controls": []}
        for slot in scr.get("slots") or []:
            cname = str(slot.get("cap_name", "")).strip().lower()
            cid = by_name.get(cname, "")
            leaf = {
                "control": slot.get("control_name", ""),
                "trigger_type": slot.get("trigger_type", ""),
                "cap_ref": cid,
                "cap_name": slot.get("cap_name", ""),
            }
            node["controls"].append(leaf)
            if not cid:
                tree["unbound_controls"].append(
                    "%s / %s" % (node["screen"], leaf["control"]))
        tree["screens"].append(node)
    tree["referenced_caps"] = sorted(set(
        c["cap_id"] for c in form.get("capabilities", []) if c.get("cap_id")))
    return tree


def render_tree(tree):
    out = ["%s  %s  (%s)" % (tree["app_id"], tree["category"] or tree["app_slug"],
                             tree["app_slug"])]
    if not tree["screens"]:
        out.append("  (no screens recorded in the form)")
    for s in tree["screens"]:
        out.append("  screen: %s" % (s["screen"] or "(unnamed)"))
        for c in s["controls"]:
            ref = c["cap_ref"] or "UNBOUND"
            out.append("    %-8s %-28s -> %s  %s"
                       % (c["trigger_type"] or "?",
                          '"%s"' % c["control"] if c["control"] else "(unnamed)",
                          ref, c["cap_name"]))
    if tree["unbound_controls"]:
        out.append("  UNBOUND CONTROLS: %d" % len(tree["unbound_controls"]))
    return "\n".join(out)


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    forms_dir = os.path.join(base, FORMS_DIR)
    reg_path = os.path.join(base, REGISTRY_PATH)
    tree_dir = os.path.join(base, TREE_DIR)
    reg = load_registry(reg_path)

    minted = []
    done = []

    for path in sorted(glob.glob(os.path.join(forms_dir, "*.form.json"))):
        with open(path) as fh:
            form = json.load(fh)

        slug = str(form.get("app_slug", "")).strip()
        caps = form.get("capabilities") or []

        if not slug or not caps:
            if SKIP_BLANK_FORMS:
                continue
            print("ERROR: %s is not filled" % os.path.basename(path))
            return 1

        # N1: sequential app number, allocated once, never reused
        if slug in reg["apps"]:
            app_num = int(reg["apps"][slug]["number"])
        else:
            app_num = next_app_number(reg)
            reg["apps"][slug] = {"number": app_num,
                                 "category": form.get("app_type", "")}
        form["app_id"] = app_id(app_num)

        variant = str(form.get("identity_variant", "")).strip() or DEFAULT_VARIANT
        if variant not in IDENTITY_VARIANTS:
            print("ERROR: %s names identity_variant %r, which is not one of the "
                  "five in IDENTITY_VARIANTS" % (slug, variant))
            return 1

        # N2/N3: resolve every capability against the shared registry
        reused = 0
        new = 0
        for c in caps:
            name = str(c.get("cap_name", "")).strip()
            if not name:
                print("ERROR: %s has a capability with no cap_name" % slug)
                return 1
            cid, is_new = resolve_cap(reg, name, variant, minted)
            c["cap_id"] = cid
            if is_new:
                new += 1
            else:
                reused += 1

        # journey pointer follows its capability by name
        jname = str(form.get("journey_cap_name", "")).strip().lower()
        if jname:
            for c in caps:
                if str(c.get("cap_name", "")).strip().lower() == jname:
                    form["journey_cap_id"] = c["cap_id"]
                    break

        tree = build_tree(form, app_num, caps)

        if not DRY_RUN:
            with open(path, "w") as fh:
                json.dump(form, fh, indent=2)
                fh.write("\n")
            if WRITE_TREES:
                os.makedirs(tree_dir, exist_ok=True)
                with open(os.path.join(tree_dir, "%s.tree.json" % slug), "w") as fh:
                    json.dump(tree, fh, indent=2)
                    fh.write("\n")
                with open(os.path.join(tree_dir, "%s.tree.txt" % slug), "w") as fh:
                    fh.write(render_tree(tree) + "\n")

        done.append((app_id(app_num), slug, len(caps), new, reused,
                     len(tree["unbound_controls"])))

    if not DRY_RUN:
        with open(reg_path, "w") as fh:
            json.dump(reg, fh, indent=2)
            fh.write("\n")

    if not done:
        print("no filled forms found in %s/" % FORMS_DIR)
        return 0

    print("%s%d app(s)" % ("DRY RUN -- nothing written -- " if DRY_RUN else "",
                           len(done)))
    print("  %-8s %-24s %5s %5s %6s %8s"
          % ("app", "category", "caps", "new", "reused", "unbound"))
    for aid, slug, total, new, reused, unbound in done:
        print("  %-8s %-24s %5d %5d %6d %8d"
              % (aid, slug, total, new, reused, unbound))
    print("\nregistry: %d apps, %d capabilities"
          % (len(reg["apps"]), len(reg["capabilities"])))
    if minted:
        print("newly minted this run: %d" % len(minted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
