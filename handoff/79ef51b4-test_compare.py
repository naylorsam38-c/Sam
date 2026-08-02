"""
Tests for the deterministic half of the brain. NO MODEL, NO DATABASE.

Run: python -m oversight.test_compare

These pass or fail the same way every time, forever. That is the point of
keeping the verdict out of the model — the part that decides whether your
customer got the right invoice is testable, and here it is, tested.
"""

from .compare import compare, VAGUE
from .grounding import ground
from .angel import should_raise


def _check(name, got, want):
    status = "PASS" if got == want else "FAIL"
    print(f"[{status}] {name}" + ("" if got == want else f"\n        got {got!r} want {want!r}"))
    return got == want


def run():
    ok = []

    # --- the one that matters: wrong amount gets caught ---
    r = compare(
        {"action": "send invoice", "recipient": "Acme Corp", "amount": "250", "reference": "March invoice"},
        {"action": "send invoice", "recipient": "Acme Corp", "amount": "2500", "reference": "March invoice"},
    )
    ok.append(_check("wrong amount -> mismatch", r["status"], "mismatch"))
    ok.append(_check("wrong amount names the field", r["mismatches"][0]["field"], "amount"))

    # --- clean run stays quiet ---
    r = compare(
        {"action": "send invoice", "recipient": "Acme Corp", "amount": "250", "reference": None},
        {"action": "send invoice", "recipient": "Acme Corp", "amount": "250", "reference": None},
    )
    ok.append(_check("clean run -> checked", r["status"], "checked"))
    ok.append(_check("clean run raises nothing", should_raise(r), False))

    # --- money formatting must not create fake mismatches ---
    r = compare({"amount": "$250.00"}, {"amount": "250"})
    ok.append(_check("$250.00 == 250", r["status"], "checked"))

    r = compare({"recipient": " Acme Corp "}, {"recipient": "acme corp"})
    ok.append(_check("whitespace/case ignored", r["status"], "checked"))

    # --- tonight's real failure: "send something" ---
    r = compare({"action": None, "recipient": None, "amount": None, "reference": None},
                {"action": "send invoice", "recipient": "Acme Corp"})
    ok.append(_check("vague intent -> intent_too_vague", r["status"], VAGUE))
    ok.append(_check("vague intent DOES raise", should_raise(r), True))

    # --- intent claimed something nothing could confirm ---
    r = compare({"amount": "250"}, {})
    ok.append(_check("nothing to check against -> unverified", r["status"], "unverified"))
    ok.append(_check("unverified DOES raise", should_raise(r), True))
    ok.append(_check("unverified is not a mismatch", r["mismatches"], []))

    # --- partial: one field confirmed, one not. Not a pass, not a fail. ---
    r = compare({"recipient": "Acme Corp", "amount": "250"}, {"recipient": "Acme Corp"})
    ok.append(_check("partial -> checked on what was seen", r["status"], "checked"))
    ok.append(_check("partial records the gap", r["unverifiable"][0]["field"], "amount"))

    # --- missing intent entirely ---
    ok.append(_check("no_intent_recorded raises", should_raise({"status": "no_intent_recorded"}), True))

    # --- grounding: the real hallucinations from the 2026-07-28 test run ---
    f = ground({"reference": "March invoice", "recipient": "Acme Corp"},
               "chase up Acme about that invoice")
    ok.append(_check("invented 'March' caught", [x["field"] for x in f], ["reference"]))

    f = ground({"amount": "250", "reference": "March invoice"},
               "email the invoice to Acme and also schedule a call for next week")
    ok.append(_check("invented amount caught", f[0]["field"], "amount"))

    f = ground({"recipient": "Acme Corp", "amount": "400", "reference": "April invoice"},
               "Please send the April invoice to Acme Corp for $400.")
    ok.append(_check("genuine intent not accused", f, []))

    f = ground({"recipient": "Acme Corp"}, "chase up Acme")
    ok.append(_check("Acme -> Acme Corp allowed", f, []))

    f = ground({"amount": "400.00"}, "send them $400")
    ok.append(_check("400.00 == 400 allowed", f, []))

    f = ground({"recipient": "Ghost Ltd", "amount": "9999"}, "")
    ok.append(_check("no request text = no accusation", f, []))

    # --- grounding retune: hard tokens strict, describing words lenient ---
    # An invented weekday is as serious as an invented figure.
    f = ground({"reference": "Thursday call"}, "schedule a call for next week")
    ok.append(_check("invented 'Thursday' caught", f[0]["invented"], ["thursday"]))

    # A describing word the user didn't say is NOT a fabrication. Flagging
    # it was tested and rejected as noise — a queue that cries about
    # adjectives stops being read.
    f = ground({"reference": "the outstanding invoice"}, "chase up that invoice")
    ok.append(_check("'outstanding' is not an accusation", f, []))

    # The domain noun is legitimate grounding evidence.
    f = ground({"reference": "unpaid quote"}, "follow up on the quote")
    ok.append(_check("'quote' traces back, allowed", f, []))

    # Month still caught even when the rest of the phrase traces fine.
    f = ground({"reference": "June invoice"}, "send the invoice to Acme")
    ok.append(_check("invented month still caught", f[0]["invented"], ["june"]))

    # Real dates pass untouched.
    f = ground({"reference": "June invoice"}, "send the June invoice to Acme")
    ok.append(_check("real month not accused", f, []))

    print(f"\n{sum(ok)}/{len(ok)} passed")
    return all(ok)


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
