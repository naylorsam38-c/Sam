#!/usr/bin/env python3
"""
catalogue.py — what this system can really build, in plain English.

Two lists, and the whole front door rests on them:

  CAPABILITIES  every kind of thing the shelf can really build, named the way a
                person would say it. Each one names the real template pieces it
                comes from, and this file REFUSES TO LOAD if any of those pieces
                is not actually in the templates -- so the catalogue can never
                drift into promising something the builder cannot make.

  NOT_ON_THE_SHELF  the things people ask for that this system cannot build,
                each with what to say instead. Not a disclaimer at the bottom of
                a page: the front door reads this list out loud, early, whenever
                someone asks for one of them.

Why it exists: the person describing their app does not know what is buildable,
and the model helping them must not guess. The model may only ever offer a card
from CAPABILITIES. Anything else it must name as not available and redirect,
using the words in NOT_ON_THE_SHELF. That is the same rule the rest of this
chain runs on (refuse, never guess) applied to the conversation itself.

Usage:
  python catalogue.py                 # print the catalogue, proving every piece is real
  python catalogue.py --json          # CAPABILITIES.json for the intake page
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, "..", "requirements-engine", "templates")


class CatalogueError(Exception):
    """A card names something the templates do not declare."""


# ============================================================================
# THE CATALOGUE — edit here. Every `records`/`workflows`/`reports`/`forms`/
# `notifications` entry is checked against the real template on load.
# ============================================================================
CAPABILITIES = [
    {
        "id": "work",
        "template": "pm-teamwork",
        "name": "Work and tasks",
        "one_line": "Jobs to do, who is doing them, and whether they are done.",
        "you_get": [
            "Projects, and tasks inside them",
            "Each task assigned to a person, with a due date and a priority",
            "Tasks move To do → In progress → Done",
            "Comments on a task",
            "A nudge the day before something is due",
            "Who is carrying how much open work, and what has slipped",
        ],
        "sounds_like": ["to-do", "task", "project", "assign", "deadline", "team work", "kanban", "backlog"],
        "records": ["Project", "Task", "Comment"],
        "workflows": ["Task lifecycle"],
        "reports": ["Open tasks by person", "Overdue tasks"],
        "notifications": ["Task assigned", "Task due reminder", "New comment"],
        "forms": [],
    },
    {
        "id": "people",
        "template": "crm-pipeline",
        "name": "People and how they progress",
        "one_line": "A directory of people and companies, each moving through stages.",
        "you_get": [
            "Companies, and the people at them",
            "Something you track for each one, moving through stages you choose",
            "Calls, meetings and to-dos logged against them",
            "Who owns each one, and the ability to hand it to someone else",
            "How many are at each stage, and what share you finish successfully",
        ],
        "sounds_like": ["contact", "directory", "member", "lead", "deal", "pipeline", "crm",
                        "connecting people", "network", "applicant", "candidate", "client list"],
        "records": ["Organisation", "Contact", "Deal", "Activity"],
        "workflows": ["Deal pipeline"],
        "reports": ["Pipeline by stage", "Win rate"],
        "notifications": ["Activity due", "Deal won"],
        "forms": [],
    },
    {
        "id": "bookings",
        "template": "booking-frontdesk",
        "name": "Appointments and bookings",
        "one_line": "What you offer, who booked it, and when.",
        "you_get": [
            "The services you offer, with how long they take and what they cost",
            "Your customers",
            "Appointments: Booked → Confirmed → Completed, or Cancelled, or No-show",
            "A public page where someone books without making an account",
            "A reminder before the appointment",
            "What is coming up, and how often people do not turn up",
        ],
        "sounds_like": ["booking", "appointment", "calendar", "schedule", "slot", "session",
                        "reservation", "class", "consultation"],
        "records": ["Service", "Customer", "Appointment"],
        "workflows": ["Appointment lifecycle"],
        "reports": ["Upcoming appointments", "No-show rate"],
        "notifications": ["Booking confirmation", "Appointment reminder", "Cancellation notice"],
        "forms": ["Public booking form"],
    },
    {
        "id": "stock",
        "template": "erp-backbone",
        "name": "Stock and orders",
        "one_line": "What you hold, what you are buying, what you are selling.",
        "you_get": [
            "Products, each with how many you hold and when to reorder",
            "Suppliers you buy from and accounts you sell to",
            "Purchase orders that add stock when they arrive",
            "Sales orders that take stock away when they ship",
            "A sign-off step before an order is confirmed",
            "An alert when a product runs low",
            "What you hold now, what you sold month by month, what is still open",
        ],
        "sounds_like": ["stock", "inventory", "warehouse", "product", "supplier", "purchase order",
                        "sales order", "shipping", "reorder", "erp"],
        "records": ["Product", "Supplier", "Customer account", "Purchase order",
                    "Purchase order line", "Sales order", "Sales order line", "Stock adjustment"],
        "workflows": ["Purchase order lifecycle", "Sales order lifecycle"],
        "reports": ["Stock on hand", "Sales by month", "Open orders"],
        "notifications": ["Low stock alert", "Order shipped"],
        "forms": [],
    },
    {
        "id": "money",
        "template": "accounting-ledger",
        "name": "Invoices and payments",
        "one_line": "What you are owed, what you owe, and what has been settled.",
        "you_get": [
            "Contacts you invoice or are billed by",
            "Invoices with lines, going Draft → sign-off → Awaiting payment → Paid",
            "Bills you owe",
            "Payments that settle an invoice on their own once they add up to the total",
            "An invoice document you can produce and keep a record of",
            "A reminder when an invoice goes past its due date",
        ],
        "sounds_like": ["invoice", "billing", "payment", "accounts", "owed", "receipt",
                        "bookkeeping", "ledger", "quote"],
        "records": ["Contact", "Invoice", "Invoice line", "Bill", "Payment"],
        "workflows": ["Invoice lifecycle", "Bill lifecycle"],
        "reports": [],
        "notifications": ["Invoice sent", "Payment reminder", "Payment received"],
        "forms": [],
    },
]

#: Comes with every app, no matter what they pick. Worth saying out loud,
#: because people assume these have to be asked for.
ALWAYS_INCLUDED = [
    "Different kinds of user, each only able to see and do what their job allows",
    "A record of everything that happened: who moved what, who approved what, who pressed what",
    "Every list, and a page per item where you can change it",
    "Three interfaces to choose from, all working on the same app",
]

# ============================================================================
# WHAT THIS SYSTEM CANNOT BUILD — say it, do not bury it.
# `instead` is what the front door offers in its place. Empty means there is no
# substitute and the honest answer is "not this system".
# ============================================================================
NOT_ON_THE_SHELF = [
    {
        "id": "card_payments",
        "they_say": ["take payments", "stripe", "credit card", "checkout", "pay online", "deposit"],
        "plain": "Taking card payments.",
        "why": "Charging a real card needs a live payment provider, which is not part of this system.",
        "instead": "You can record that a payment was made, and an invoice settles itself once "
                   "the payments recorded against it reach the total. Someone still takes the money elsewhere.",
    },
    {
        "id": "sending_email",
        "they_say": ["send email", "email them", "mail out", "newsletter", "sms", "text them"],
        "plain": "Actually sending the email or text.",
        "why": "Nothing in this system is connected to a mail or SMS provider.",
        "instead": "The app produces the document (an invoice, say) and records that it was produced "
                   "and when. Sending it is a step a person still does.",
    },
    {
        "id": "logins",
        "they_say": ["log in", "login", "sign up", "password", "account", "authentication", "sso"],
        "plain": "People signing in with their own username and password.",
        "why": "The app knows the different kinds of user and enforces what each may do, but there is "
               "no sign-in screen yet — the app is told who is acting.",
        "instead": "Everything about roles and permissions is real and enforced. Put the app somewhere "
                   "only your people can reach until sign-in exists.",
    },
    {
        "id": "messaging",
        "they_say": ["chat", "message each other", "dm", "inbox", "messaging", "talk to each other"],
        "plain": "People messaging each other inside the app.",
        "why": "There is no messaging engine on the shelf.",
        "instead": "People can leave comments on a specific item, and everyone who can see that item "
                   "sees the comments. That covers 'discuss this job' but not 'chat with Sarah'.",
    },
    {
        "id": "matching",
        "they_say": ["match", "matching", "recommend", "suggest people", "algorithm", "ai picks", "swipe"],
        "plain": "The app deciding who or what to match together.",
        "why": "There is no matching or recommendation engine on the shelf.",
        "instead": "You can hold everyone's details, filter and group them, and move each person "
                   "through stages by hand. A person does the matching; the app records it.",
    },
    {
        "id": "video",
        "they_say": ["video", "call", "zoom", "meet", "webcam", "live stream"],
        "plain": "Video or voice calls.",
        "why": "Not on the shelf, and not something this system builds.",
        "instead": "You can book a time and hold the details of the meeting. The call happens "
                   "in whatever you already use.",
    },
    {
        "id": "maps",
        "they_say": ["map", "location", "gps", "nearby", "directions", "geolocation"],
        "plain": "Maps, distance or 'people near me'.",
        "why": "There is no mapping or location engine on the shelf.",
        "instead": "You can hold an address as text and filter on it. No map, no distance.",
    },
    {
        "id": "app_store",
        "they_say": ["app store", "ios", "android", "download the app", "native app", "play store"],
        "plain": "An app people install from the App Store or Play Store.",
        "why": "What gets built is a web app, opened in a browser.",
        "instead": "One of the three looks is built for phones — it fills the screen, has big buttons "
                   "and a bottom tab bar. People open it in their phone browser and can pin it to their home screen.",
    },
    {
        "id": "going_live",
        "they_say": ["go live", "domain", "hosting", "publish", "deploy", "url", "website address"],
        "plain": "Putting it on the internet at your own web address.",
        "why": "The system builds and proves the app; it does not host it or buy you a domain.",
        "instead": "You get the whole app and instructions to run it. Putting it somewhere permanent "
                   "is a separate job for you or a developer.",
    },
]


# ============================================================================
# PROOF — every card is checked against the real templates on load.
# ============================================================================
def _template(name):
    path = os.path.join(TEMPLATES, name + ".json")
    if not os.path.isfile(path):
        raise CatalogueError(f"card names template {name!r}, which does not exist")
    return json.load(open(path, encoding="utf-8"))


def verify(capabilities=None):
    """Every piece every card promises must really be declared by its template.
    Returns the checked catalogue; raises rather than returning a card that
    promises something the builder could not make."""
    problems = []
    for cap in (capabilities or CAPABILITIES):
        t = _template(cap["template"])
        inv = t["inventory"]
        for kind in ("records", "workflows", "reports", "notifications", "forms"):
            for item in cap.get(kind) or []:
                if item not in inv[kind]:
                    problems.append(f"{cap['id']}: {kind[:-1]} {item!r} is not in {cap['template']}'s inventory")
        # a card must not quietly leave out a record its template declares: the
        # person picking it gets the whole template, so the card must say so
        missing = [r for r in inv["records"] if r not in (cap.get("records") or [])]
        if missing:
            problems.append(f"{cap['id']}: {cap['template']} also declares record(s) {missing} that the card never mentions")
    if problems:
        raise CatalogueError("the catalogue promises what the templates do not declare:\n  - " + "\n  - ".join(problems))
    return capabilities or CAPABILITIES


def match(words):
    """Which cards a person's own words point at, and which unavailable things
    they asked for. Plain substring matching on the card's own `sounds_like`:
    a hint for the person and for the model, never a decision. The person
    always confirms, and the model may only ever offer what comes back here."""
    low = " " + (words or "").lower() + " "
    hits = [c for c in CAPABILITIES if any(s in low for s in c["sounds_like"])]
    gaps = [g for g in NOT_ON_THE_SHELF if any(s in low for s in g["they_say"])]
    return hits, gaps


def as_json():
    verify()
    return {
        "capabilities": [{k: v for k, v in c.items()} for c in CAPABILITIES],
        "always_included": ALWAYS_INCLUDED,
        "not_on_the_shelf": NOT_ON_THE_SHELF,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        verify()
    except CatalogueError as e:
        print("REFUSED —", e, file=sys.stderr)
        return 2
    if "--json" in argv:
        out = os.path.join(HERE, "CAPABILITIES.json")
        json.dump(as_json(), open(out, "w", encoding="utf-8"), indent=1)
        print("wrote", out)
        return 0
    print("WHAT THIS SYSTEM CAN BUILD — every piece below proven present in a real template\n")
    for c in CAPABILITIES:
        print(f"  {c['name']}  ({c['template']})")
        print(f"    {c['one_line']}")
        for line in c["you_get"]:
            print(f"      · {line}")
        print()
    print("COMES WITH EVERY APP")
    for line in ALWAYS_INCLUDED:
        print(f"      · {line}")
    print("\nWHAT IT CANNOT BUILD — said out loud, with what is offered instead\n")
    for g in NOT_ON_THE_SHELF:
        print(f"  {g['plain']}")
        print(f"    why:     {g['why']}")
        print(f"    instead: {g['instead'] or '— nothing; this is not the system for it'}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
