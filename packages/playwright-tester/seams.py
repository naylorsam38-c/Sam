#!/usr/bin/env python3
"""
seams.py — seam journeys: the tester drives the joins BETWEEN shelf parts, in
a real browser, against the real running app, and issues the qualification
receipts that move a part from TESTED to PRODUCT_QUALIFIED.

A journey is owned by the parts it exercises (declared per journey below,
mirrored on each part's `seam_journeys` field on the shelf) and follows one
user-facing path all the way through:

    UI action -> request -> response -> state change -> persistence (re-read)

Every journey ends in exactly one of three results, and only one of them is
ever good news:

    N/A      the spec declares nothing this journey drives — recorded, not a finding
    PASS     every user-facing step happened in the browser and the persisted
             state was read back — this is the only result that can qualify a part
    BLOCKED  the assembled app gives the browser no way to perform or observe a
             step (a control that does not exist, a field no screen renders).
             The API half is still driven and recorded as evidence, but the
             journey does not qualify anything. A BLOCKED journey is a finding
             about the product, and it is printed, never hidden.
    FAIL     a step was performed and the product did the wrong thing

Why this file exists: Command Desk 42f7cf6ce72f63fa passed Tester and threw on
the first real click, because the parts were proven one at a time and nothing
drove the join. Also because a part frozen after one app's qualification is
still dropped into a different page in the next app; the journeys ship with
the part so every assembled app re-runs them at its own seams.

Usage:
  python seams.py SPEC.json --base-url http://127.0.0.1:8788 -o out/
  python seams.py SPEC.json --base-url ... -o out/ --no-receipts     (drive, report, qualify nothing)
"""

# ============================================================================
# RULES / CONFIG — edit here, not in the logic below.
# ============================================================================

#: Which journeys exist and which shelf parts each one exercises. A part is
#: eligible for a qualification receipt only through journeys that list it
#: here; a part with no journey can never become PRODUCT_QUALIFIED, which is
#: deliberate — "no journey" must never read as "nothing wrong".
JOURNEYS = {
    "form_submit_lands_in_list_and_detail":  ["form_render_submit", "crud_list_detail"],
    "report_screen_reflects_written_rows":   ["reporting_engine"],
    "api_key_screen_connects_never_echoes":  ["api_key_connect"],
    "oauth_connect_click_reaches_provider":  ["oauth_connect"],
    "person_move_is_visible_on_the_screen":  ["workflow_executor"],
    "gated_system_move_is_visible_on_the_screen": ["system_triggered_transition", "stage_approval_gate"],
    "custom_action_is_pressable_and_visible": ["custom_action_execution"],
    # the five parts the families' own declared effects run on -- each proven
    # by pressing the declared control on the generated screen and reading the
    # persisted result back on a screen
    "stock_moves_on_the_screen_when_an_order_enters_its_stage": ["stock_ledger"],
    "payment_settles_its_target_on_the_screen": ["ledger_balancing"],
    "clone_appears_in_the_list_screen": ["record_cloning"],
    "sent_document_is_stamped_on_the_screen": ["document_generation"],
    "rate_report_reflects_the_moves_made_on_the_screen": ["stage_history"],
}

#: Write qualification receipts (via shelf.py) for every part that has at
#: least one PASS and no FAIL across the run. False = drive and report only.
WRITE_RECEIPTS = True

#: A part gets a receipt only if NONE of its journeys FAILED. A BLOCKED
#: journey does not veto (it is a product gap, not a part defect) but does
#: not count towards the PASS the receipt needs either.
FAIL_VETOES_RECEIPT = True

#: How long the browser waits for the app to render a state before the step
#: is declared FAIL. Raise on a slow machine; lower and a healthy app on a
#: busy box will be reported broken.
STEP_TIMEOUT_MS = 8000

#: The one text every seam writes so it can be found again on the next
#: screen. Unique per run so an earlier run's rows can never satisfy a check.
NONCE_PREFIX = "seam-"

# ============================================================================
# LOGIC
# ============================================================================

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "builder")))
sys.path.insert(0, HERE)
import shelf as shelf_lib                       # noqa: E402
from builder import _screen_filename, slug, table_name, _workflow_for  # noqa: E402  the Builder's own naming and workflow lookup, not a second copy
from live_test import _launch                   # noqa: E402  the same pinned-Chromium launch
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402


def _nonce():
    return NONCE_PREFIX + hex(int(time.time() * 1000))[2:]


def _url(base, screen):
    return f"{base}/static/{_screen_filename(screen['id'])}"


async def _goto(page, url):
    """A previous journey may have left the browser mid-flight to a third-party
    host this sandbox's egress denies (the OAuth redirect). Settle on a blank
    page first so that interrupted navigation cannot abort this one."""
    try:
        await page.goto("about:blank")
    except PlaywrightError:
        pass
    return await page.goto(url, wait_until="networkidle")


def _api(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


class Journey:
    """One run of one journey. Collects steps and ends in exactly one result."""

    def __init__(self, name, subject):
        self.name, self.subject = name, subject
        self.parts = JOURNEYS[name]
        self.steps = []
        self.result = None
        self.reason = None
        self.failed_part = None
        self.notes = []  # findings about the product that did not decide the result

    def step(self, channel, action, observed):
        self.steps.append({"channel": channel, "action": action, "observed": observed})

    def blocked(self, reason):
        self.result, self.reason = "BLOCKED", reason
        return self

    def not_applicable(self, reason):
        """The spec declares nothing this journey drives. Not a finding about
        the product — recorded so the absence is visible, never as a defect."""
        self.result, self.reason = "N/A", reason
        return self

    def failed(self, reason, part=None):
        """`part` names which of this journey's parts the failing step belongs
        to. Only that part carries the FAIL; the journey's other parts were not
        reached and are recorded as such — never as PASS, never as FAIL."""
        self.result, self.reason = "FAIL", reason
        self.failed_part = part if part in self.parts else self.parts[0]
        return self

    def passed(self):
        self.result = "PASS"
        return self

    def to_dict(self):
        return {"journey": self.name, "subject": self.subject, "parts": self.parts,
                "result": self.result, "reason": self.reason, "failed_part": self.failed_part, "notes": self.notes,
                "browser_verified": self.result == "PASS" and all(s["channel"] == "browser" for s in self.steps
                                                                   if s.get("user_facing", True)),
                "steps": self.steps}


# ----------------------------------------------------------------- helpers
def _fields_of(bm, record):
    return bm["records"][record]["fields"]


def _record_of_table(bm, table):
    for record in bm["records"]:
        if table_name(record) == table:
            return record
    return None


def _value_for(ftype, nonce):
    return {
        "short_text": nonce, "long_text": nonce, "other": nonce,
        "email": f"{nonce}@example.test", "phone": "0400000000", "url": f"https://example.test/{nonce}",
        "whole_number": 1, "decimal_number": 1.5, "money": 1.25,
        "date": "2026-09-05", "date_time": "2026-09-05T10:00", "yes_no": 1,
    }.get(ftype, nonce)


async def _fill_form(page, fields, nonce, tmpdir):
    """Fills every rendered control by its own declared type. Returns the
    slug of the text field that carries the nonce, or a BLOCKED reason."""
    carrier = None
    for f in fields:
        key = slug(f["name"])
        ftype = f["type"]
        ctl = page.locator(f"#{key}")
        if await ctl.count() == 0:
            return None, f"the form renders no control for field '{f['name']}'"
        if ftype in ("short_text", "long_text", "other", "email", "phone", "url"):
            await ctl.fill(str(_value_for(ftype, nonce)))
            if carrier is None and ftype in ("short_text", "long_text", "other"):
                carrier = key
        elif ftype in ("whole_number", "decimal_number", "money"):
            await ctl.fill(str(_value_for(ftype, nonce)))
        elif ftype in ("date", "date_time"):
            await ctl.fill(_value_for(ftype, nonce))
        elif ftype == "yes_no":
            await ctl.check()
        elif ftype in ("one_choice", "multi_choice"):
            if await ctl.locator("option").count() == 0:
                return None, f"'{f['name']}' offers no options to choose"
            await ctl.select_option(index=0)
        elif ftype == "link":
            try:
                await page.wait_for_function(
                    f"document.querySelectorAll('#{key} option').length > 0", timeout=STEP_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                if f.get("required") == "yes":
                    return None, ("NEEDS_ROW", f["target_record"], f["name"])
                continue  # optional link with nothing to pick: legitimately left blank
            await ctl.select_option(index=0)
        elif ftype == "file":
            path = os.path.join(tmpdir, f"{nonce}.txt")
            open(path, "w").write(nonce)
            await ctl.set_input_files(path)
        else:
            return None, f"no fill rule for field type '{ftype}'"
    if carrier is None:
        return None, "the form has no text field to carry a value the next screen can be checked for"
    return carrier, None


# ---------------------------------------------------------------- journeys
async def form_submit_lands_in_list_and_detail(page, bm, base, tmpdir):
    out = []
    forms = [s for s in bm["screens_inventory"] if s["kind"] == "form"]
    for scr in forms:
        j = Journey("form_submit_lands_in_list_and_detail", scr["id"])
        record = scr.get("record")
        lst = next((s for s in bm["screens_inventory"] if s["kind"] == "list" and s.get("record") == record), None)
        det = next((s for s in bm["screens_inventory"] if s["kind"] == "detail" and s.get("record") == record), None)
        if not lst or not det:
            out.append(j.blocked(f"{record!r} has no list/detail screen to land on"))
            continue
        fields = [_fields_of(bm, record)[n] for n in bm["forms"][scr["form"]] if n in _fields_of(bm, record)]
        nonce = _nonce()
        await _goto(page, _url(base, scr))
        j.step("browser", f"open form {scr['id']}", await page.title())
        carrier, why = await _fill_form(page, fields, nonce, tmpdir)
        seeded = set()
        while isinstance(why, tuple) and why[0] == "NEEDS_ROW" and why[1] not in seeded:
            # a required link with nothing to pick. Recorded as a finding (on a
            # fresh install this form cannot be completed from the screen), then
            # one target row is written over the API so the rest of the seam can
            # still be driven and its own defects found.
            target, fname = why[1], why[2]
            seeded.add(target)
            status, seed = _create_row(bm, base, target, nonce + "-seed")
            j.step("api", f"seed one {target!r} so required link {fname!r} has something to pick", status)
            j.steps[-1]["user_facing"] = False
            j.notes.append(f"FRESH_INSTALL_GAP: required field {fname!r} links to {target!r}; with no {target} rows "
                           f"yet, this form cannot be completed from the screen")
            if status not in (200, 201):
                why = f"could not seed a {target!r} row for required link {fname!r}: {status} {seed}"
                break
            await _goto(page, _url(base, scr))
            carrier, why = await _fill_form(page, fields, nonce, tmpdir)
        if isinstance(why, tuple):
            why = f"required field {why[2]!r} links to {why[1]!r} which has no rows and could not be seeded"
        if why:
            out.append(j.blocked(why))
            continue
        j.step("browser", "fill every declared control", f"{len(fields)} controls, carrier={carrier}={nonce}")
        await page.click("button[type=submit]")
        try:
            await page.wait_for_function(
                "document.getElementById('result').textContent.startsWith('saved ')", timeout=STEP_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            msg = await page.locator("#result").inner_text()
            out.append(j.failed(f"submit did not report saved; the page says {msg!r}", part="form_render_submit"))
            continue
        result_text = await page.locator("#result").inner_text()
        new_id = result_text.split("saved ", 1)[1].strip()
        j.step("browser", "click Save", result_text)

        await _goto(page, _url(base, lst))
        try:
            await page.wait_for_selector("#rows:not([hidden])", timeout=STEP_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            out.append(j.failed(f"list screen {lst['id']} never showed its rows: {await page.locator('#state').inner_text()!r}", part="crud_list_detail"))
            continue
        cells = await page.locator(f"#rows td:text-is('{nonce}')").count()
        j.step("browser", f"open list {lst['id']}", f"{cells} cell(s) carry {nonce}")
        if cells < 1:
            out.append(j.failed("the saved row is not on the list screen", part="crud_list_detail"))
            continue

        await _goto(page, _url(base, det) + f"?id={new_id}")
        try:
            await page.wait_for_selector("#fields:not([hidden])", timeout=STEP_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            out.append(j.failed(f"detail screen {det['id']} never rendered: {await page.locator('#state').inner_text()!r}", part="crud_list_detail"))
            continue
        shown = await page.locator(f"[data-field='{carrier}']").inner_text()
        j.step("browser", f"open detail {det['id']}?id={new_id}", f"{carrier}={shown!r}")
        if shown != nonce:
            out.append(j.failed(f"detail shows {shown!r} for {carrier}, expected {nonce!r}", part="crud_list_detail"))
            continue
        out.append(j.passed())
    if not forms:
        out.append(Journey("form_submit_lands_in_list_and_detail", "-").not_applicable("the spec declares no form screen"))
    return out


async def _read_report_table(page):
    await page.wait_for_function("document.querySelectorAll('#numbers tr').length > 0", timeout=STEP_TIMEOUT_MS)
    rows = await page.locator("#numbers tr").all()
    table = {}
    for r in rows:
        tds = await r.locator("td").all_inner_texts()
        table[tds[0]] = json.loads(tds[1])
    return table


async def report_screen_reflects_written_rows(page, bm, base, tmpdir):
    out = []
    screens = [s for s in bm["screens_inventory"] if s["kind"] == "report"]
    for scr in screens:
        j = Journey("report_screen_reflects_written_rows", scr["id"])
        report = bm["reports"][scr["report"]]
        await _goto(page, _url(base, scr))
        try:
            before = await _read_report_table(page)
        except PlaywrightTimeoutError:
            out.append(j.failed("the report screen rendered no numbers"))
            continue
        j.step("browser", f"open report {scr['id']}", {k: v for k, v in before.items()})

        # pick one metric this journey can move by writing one row
        chosen = None
        block = None
        for m in report["spec"]:
            sp = m["spec"]
            if sp.get("engine") not in (None, "reporting_engine"):
                # a metric run by another part (stage_history rates, stock_ledger
                # counts) cannot be moved by writing one row; it is that part's
                # journey to prove, not this one's
                block = f"metric {m['metric']!r} is computed by the {sp['engine']} part, not by writing one row"
                continue
            record = _record_of_table(bm, sp["table"])
            if not record:
                block = f"metric {m['metric']!r} reads table {sp['table']!r}, which is no declared record"
                continue
            filters = sp.get("filters") or []
            wf = _workflow_for({"build_model": bm}, record)
            bad = [f for f in filters if f["field"] == "stage" and wf and f["value"] != (wf.get("initial") or wf["stages"][0]["name"])]
            if bad:
                block = (f"metric {m['metric']!r} counts rows at stage {bad[0]['value']!r}; a new row starts at "
                         f"{(wf.get('initial') or wf['stages'][0]['name'])!r} and no screen offers a control to move it")
                continue
            chosen = (m, record)
            break
        if not chosen:
            out.append(j.blocked(block or "no metric can be moved by writing one row"))
            continue
        m, record = chosen
        sp = m["spec"]
        nonce = _nonce()
        body = {}
        for name, f in _fields_of(bm, record).items():
            if f.get("required") == "yes" or slug(name) in (sp.get("group_by"), sp.get("value_field")):
                body[name] = _value_for(f["type"], nonce)
        if sp.get("group_by"):
            gname = next((n for n in _fields_of(bm, record) if slug(n) == sp["group_by"]), None)
            if gname:
                body[gname] = nonce
        for flt in sp.get("filters") or []:
            fname = next((n for n in _fields_of(bm, record) if slug(n) == flt["field"]), None)
            if not fname:
                continue
            if flt["op"] in ("=",):
                body[fname] = flt["value"]
            elif flt["op"] == "in" and flt.get("value"):
                body[fname] = flt["value"][0]
            elif flt["op"] == "within_next_days":
                body[fname] = time.strftime("%Y-%m-%dT10:00", time.gmtime(time.time() + 86400))
            elif flt["op"] == "before_now":
                body[fname] = "2000-01-01"
            # "!=" / "not_in": a new row's own value already differs; leave it
        status, created = _api(base, "POST", f"/api/{sp['table']}", body)
        j.step("api", f"POST /api/{sp['table']} (no screen creates this record)", {"status": status, "body": body},)
        j.steps[-1]["user_facing"] = False
        if status not in (200, 201):
            out.append(j.failed(f"could not write the row the metric reads: {status} {created}"))
            continue

        await page.reload(wait_until="networkidle")
        after = await _read_report_table(page)
        j.step("browser", "reload the report screen", after.get(m["metric"]))
        val = after.get(m["metric"])
        expected = _value_for(next(f["type"] for n, f in _fields_of(bm, record).items() if slug(n) == sp.get("value_field")), nonce) \
            if sp["aggregation"] == "sum" else 1
        if isinstance(val, dict) and sp.get("group_by") == "stage":
            wf_ = _workflow_for({"build_model": bm}, record)
            got = val.get(wf_.get("initial") or wf_["stages"][0]["name"]) if wf_ else None
            expected = float(got) if got is not None else None   # the group exists and counts this row (at least)
            expected = expected if got is not None and float(got) >= 1 else None
        else:
            got = val.get(nonce) if isinstance(val, dict) else val
        if got is None or expected is None or abs(float(got) - float(expected)) > 1e-9:
            out.append(j.failed(f"metric {m['metric']!r} shows {got!r} for the written row, expected {expected!r}"))
            continue
        out.append(j.passed())
    if not screens:
        out.append(Journey("report_screen_reflects_written_rows", "-").not_applicable("the spec declares no report screen"))
    return out


async def api_key_screen_connects_never_echoes(page, bm, base, tmpdir):
    out = []
    screens = [s for s in bm["screens_inventory"] if s["kind"] == "integration_status"
               and bm["integrations"].get(s.get("integration"), {}).get("auth") == "api_key"]
    for scr in screens:
        j = Journey("api_key_screen_connects_never_echoes", scr["id"])
        nonce = _nonce() + "-secret"
        await _goto(page, _url(base, scr))
        if await page.locator("#key").count() == 0:
            out.append(j.blocked("the screen renders no key field"))
            continue
        await page.fill("#key", nonce)
        await page.click("button[type=submit]")
        try:
            await page.wait_for_function("document.getElementById('state').textContent.trim() !== ''",
                                         timeout=STEP_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            out.append(j.failed("Save key produced no state text"))
            continue
        state = await page.locator("#state").inner_text()
        j.step("browser", f"paste a key on {scr['id']} and press Save key", state)
        if state.strip() != "connected":
            out.append(j.failed(f"state is {state!r}, expected 'connected'"))
            continue
        status, conns = _api(base, "GET", "/api/connections/status")
        provider = scr["integration"]
        conn = (conns or {}).get(provider)
        j.step("api", "GET /api/connections/status (read-back)", conn)
        j.steps[-1]["user_facing"] = False
        if not conn or conn.get("state") != "connected":
            out.append(j.failed(f"status route does not show {provider!r} connected: {conns}"))
            continue
        if nonce in json.dumps(conns):
            out.append(j.failed("the pasted key is echoed back by the status route"))
            continue
        await page.reload(wait_until="networkidle")
        html = await page.content()
        j.step("browser", "reload the screen", "key present in page" if nonce in html else "key not in page")
        if nonce in html:
            out.append(j.failed("the pasted key appears in the reloaded page"))
            continue
        out.append(j.passed())
    if not screens:
        out.append(Journey("api_key_screen_connects_never_echoes", "-").not_applicable("no pasted-key integration in this spec"))
    return out


async def oauth_connect_click_reaches_provider(page, bm, base, tmpdir):
    out = []
    screens = [s for s in bm["screens_inventory"] if s["kind"] == "integration_status"
               and bm["integrations"].get(s.get("integration"), {}).get("auth") == "oauth"]
    for scr in screens:
        j = Journey("oauth_connect_click_reaches_provider", scr["id"])
        # one tab per screen: the click sends the browser off to the provider,
        # and that trip must not be able to interrupt the next screen's load
        page = await page.context.new_page()
        await _goto(page, _url(base, scr))
        btn = page.get_by_role("button", name=re.compile("connect", re.I))
        try:
            await btn.wait_for(state="visible", timeout=STEP_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            tiles = await page.locator("#tiles").inner_text() if await page.locator("#tiles").count() else ""
            out.append(j.blocked(f"no Connect button is rendered (tiles: {tiles!r})"))
            continue
        try:
            async with page.expect_response(
                lambda r: r.request.url.rstrip("/").endswith("/start"), timeout=STEP_TIMEOUT_MS
            ) as resp_info:
                await btn.click()
            resp = await resp_info.value
        except PlaywrightTimeoutError:
            out.append(j.failed("clicking Connect produced no response from the start route"))
            continue
        # let the browser finish (or fail) its trip to the provider before the
        # next journey navigates; this sandbox may deny that egress, which is
        # not a product defect and is not what this journey asserts
        try:
            await page.wait_for_load_state("load", timeout=STEP_TIMEOUT_MS)
        except (PlaywrightTimeoutError, PlaywrightError):
            pass
        location = resp.headers.get("location", "")
        body = ""
        if resp.status != 302:
            try:
                body = (await resp.text())[:200]
            except Exception:
                pass
        j.step("browser", f"click Connect on {scr['id']}", f"{resp.status} -> Location: {location!r} {body}")
        if resp.status == 500 and "not configured" in body:
            out.append(j.blocked(f"the start route has no OAuth client id in this environment: {body}"))
            continue
        if resp.status != 302:
            out.append(j.failed(f"the start route answered {resp.status}, not a 302 to the provider: {body}"))
            continue
        if not location.startswith("https://accounts.google.com/"):
            out.append(j.failed(f"the redirect does not reach the real provider: {location!r}"))
            continue
        out.append(j.passed())
    for extra in page.context.pages[1:]:
        try:
            await extra.close()
        except PlaywrightError:
            pass
    if not screens:
        out.append(Journey("oauth_connect_click_reaches_provider", "-").not_applicable("no OAuth integration in this spec"))
    return out


def _create_row(bm, base, record, nonce):
    body = {n: _value_for(f["type"], nonce) for n, f in _fields_of(bm, record).items()
            if f.get("required") == "yes" or f["type"] in ("short_text", "other")}
    return _api(base, "POST", f"/api/{table_name(record)}", body)


async def _stage_visible(page, bm, base, record, row_id, expected_stage):
    """Opens the record's detail screen and looks for the stage. Returns
    (visible: bool, detail_screen_id or None, reason)."""
    det = next((s for s in bm["screens_inventory"] if s["kind"] == "detail" and s.get("record") == record), None)
    if not det:
        return False, None, f"{record!r} has no detail screen"
    await _goto(page, _url(base, det) + f"?id={row_id}")
    try:
        await page.wait_for_selector("#fields:not([hidden])", timeout=STEP_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return False, det["id"], "the detail screen never rendered"
    if await page.locator("[data-field='stage']").count() == 0:
        return False, det["id"], f"detail screen {det['id']} renders no 'stage' — the move happened but no screen shows it"
    shown = await page.locator("[data-field='stage']").inner_text()
    return shown == expected_stage, det["id"], f"stage shown as {shown!r}"


async def person_move_is_visible_on_the_screen(page, bm, base, tmpdir):
    out = []
    moves = [a for a in bm["actions_inventory"] if a["kind"] == "transition" and a.get("mover") != "automatic"]
    seen = set()
    for act in moves:
        wf = bm["workflows"].get(act["workflow"])
        # the record this workflow belongs to: by its declared stages, as the Builder resolves it
        record = next((r for r in bm["records"] if _workflow_for({"build_model": bm}, r) is wf), None)
        if record is None:
            continue
        if not wf or record in seen or act["from"] != (wf.get("initial") or wf["stages"][0]["name"]):
            continue
        seen.add(record)
        j = Journey("person_move_is_visible_on_the_screen", act["id"])
        nonce = _nonce()
        status, row = _create_row(bm, base, record, nonce)
        j.step("api", f"POST /api/{table_name(record)}", status)
        j.steps[-1]["user_facing"] = False
        if status not in (200, 201):
            out.append(j.failed(f"could not create a {record}: {status} {row}"))
            continue
        # the user-facing step: a person presses the move. Does any screen offer it?
        det = next((s for s in bm["screens_inventory"] if s["kind"] == "detail" and s.get("record") == record), None)
        if det:
            await _goto(page, _url(base, det) + f"?id={row['id']}")
            control = await page.get_by_role("button", name=re.compile(re.escape(act["to"]), re.I)).count()
            j.step("browser", f"look for a control on {det['id']} that moves to {act['to']!r}", f"{control} control(s)")
        role = (act.get("roles") or ["?"])[0]
        gate = next((g for g in (wf.get("approvals") or []) if g.get("stage") == act["from"]), None)
        if gate:
            approver = (gate.get("approvers") or ["?"])[0]
            st_, dec = _api(base, "POST", f"/api/approvals/{table_name(record)}/{row['id']}", {"decision": "APPROVED", "by": approver})
            j.step("api", f"the gate at {act['from']!r}: {approver} approves first", {"status": st_, "body": dec})
            j.steps[-1]["user_facing"] = False
        if det and control:
            # the user-facing step, really performed: press the control, wait for the screen's own result text
            if gate:
                await page.reload(wait_until="networkidle")
            btn = page.get_by_role("button", name=re.compile(re.escape(act["to"]), re.I)).first
            await btn.click()
            try:
                await page.wait_for_function("document.getElementById('state') && !document.getElementById('state').hidden && document.getElementById('state').textContent.trim() !== ''", timeout=STEP_TIMEOUT_MS)
                state_text = (await page.locator("#state").inner_text()).strip()
            except PlaywrightTimeoutError:
                state_text = ""
            j.step("browser", f"press the control on {det['id']} that moves to {act['to']!r}", state_text)
            status, moved = (200, {"pressed": True}) if state_text == "Done." else (409, {"error": state_text or "no result text"})
        else:
            status, moved = _api(base, "POST", f"/api/moves/{table_name(record)}/{row['id']}", {"to": act["to"], "role": role})
            j.step("api", f"POST /api/moves/{table_name(record)}/{row['id']} to={act['to']!r} role={role!r}", {"status": status, "body": moved})
        if status != 200:
            out.append(j.failed(f"the declared person-moved edge was refused: {status} {moved}"))
            continue
        visible, det_id, why = await _stage_visible(page, bm, base, record, row["id"], act["to"])
        j.step("browser", f"open detail {det_id}", why)
        if not det or control == 0:
            out.append(j.blocked(f"no screen offers the person a control for {act['id']} ({act['from']!r} -> {act['to']!r}); "
                                 f"the move works over the API but a user cannot press it. Also: {why}"))
        elif not visible:
            out.append(j.blocked(why))
        else:
            out.append(j.passed())
    if not out:
        out.append(Journey("person_move_is_visible_on_the_screen", "-").not_applicable("no person-moved edge leaves an initial stage"))
    return out


async def gated_system_move_is_visible_on_the_screen(page, bm, base, tmpdir):
    out = []
    for wf_name, wf in bm["workflows"].items():
        record = next((r for r in bm["records"] if _workflow_for({"build_model": bm}, r) is wf), None)
        if record is None:
            continue
        initial = wf.get("initial") or wf["stages"][0]["name"]
        chain = []  # automatic edges with events, followed from the initial stage
        stage = initial
        for _ in range(len(wf.get("transitions", []))):
            nxt = next((t for t in wf.get("transitions", []) if t["from"] == stage and t.get("mover") == "automatic" and t.get("event")), None)
            if not nxt:
                break
            chain.append(nxt)
            stage = nxt["to"]
        if not chain:
            continue
        j = Journey("gated_system_move_is_visible_on_the_screen", chain[0]["id"])
        nonce = _nonce()
        status, row = _create_row(bm, base, record, nonce)
        j.step("api", f"POST /api/{table_name(record)}", status)
        j.steps[-1]["user_facing"] = False
        if status not in (200, 201):
            out.append(j.failed(f"could not create a {record}: {status} {row}"))
            continue
        gated_stages = {a["stage"] for a in wf.get("approvals", [])}
        approver_for = {a["stage"]: (a.get("approvers") or ["?"])[0] for a in wf.get("approvals", [])}
        gate_exercised = False
        ok = True
        for t in chain:
            status, moved = _api(base, "POST", f"/api/events/{table_name(record)}/{row['id']}", {"event": t["event"]})
            j.step("api", f"system event {t['event']!r} ({t['from']!r} -> {t['to']!r})", {"status": status, "body": moved})
            j.steps[-1]["user_facing"] = False
            if status == 409 and (moved or {}).get("waiting_for_approval") and t["from"] in gated_stages:
                gate_exercised = True
                by = approver_for[t["from"]]
                # the user-facing step: the declared approver presses Approve on the
                # record's own detail screen. No control there = BLOCKED, as everywhere.
                det = next((s_ for s_ in bm["screens_inventory"] if s_["kind"] == "detail" and s_.get("record") == record), None)
                pressed = False
                if det:
                    await _goto(page, _url(base, det) + f"?id={row['id']}")
                    btn = page.get_by_role("button", name=re.compile(r"^Approve", re.I))
                    if await btn.count():
                        await btn.first.click()
                        try:
                            await page.wait_for_function("document.getElementById('state') && !document.getElementById('state').hidden && document.getElementById('state').textContent.trim() !== ''", timeout=STEP_TIMEOUT_MS)
                            pressed = (await page.locator("#state").inner_text()).strip() == "Done."
                        except PlaywrightTimeoutError:
                            pressed = False
                        j.step("browser", f"declared approver {by!r} presses Approve on {det['id']} at gated stage {t['from']!r}", "Done." if pressed else "no result")
                if not pressed:
                    out.append(j.blocked(f"no screen offers the approver {by!r} a control at gated stage {t['from']!r}; the gate works over the API but a person cannot decide it"))
                    ok = False
                    break
                status, moved = _api(base, "POST", f"/api/events/{table_name(record)}/{row['id']}", {"event": t["event"]})
                j.step("api", f"system event {t['event']!r} again", {"status": status, "body": moved})
                j.steps[-1]["user_facing"] = False
            if status != 200 or (moved or {}).get("to") != t["to"]:
                blame = "stage_approval_gate" if (moved or {}).get("waiting_for_approval") else "system_triggered_transition"
                out.append(j.failed(f"declared automatic edge {t['id']} did not fire: {status} {moved}", part=blame))
                ok = False
                break
        if not ok:
            continue
        visible, det_id, why = await _stage_visible(page, bm, base, record, row["id"], chain[-1]["to"])
        j.step("browser", f"open detail {det_id}", why)
        if not gate_exercised and gated_stages:
            why += f"; the declared approval gate at {sorted(gated_stages)} was never reached by this chain"
        if visible and gated_stages and not gate_exercised:
            out.append(j.blocked(why))
        elif visible:
            out.append(j.passed())
        else:
            out.append(j.blocked(why))
    if not out:
        out.append(Journey("gated_system_move_is_visible_on_the_screen", "-").not_applicable("no workflow has an automatic edge with an event leaving its initial stage"))
    return out


async def custom_action_is_pressable_and_visible(page, bm, base, tmpdir):
    out = []
    customs = [a for a in bm["actions_inventory"] if a["kind"] == "custom" and (a.get("detail") or {}).get("execution")]
    for act in customs:
        record = act["record"]
        name = act["detail"]["name"]
        j = Journey("custom_action_is_pressable_and_visible", act["id"])
        nonce = _nonce()
        status, row = _create_row(bm, base, record, nonce)
        j.step("api", f"POST /api/{table_name(record)}", status)
        j.steps[-1]["user_facing"] = False
        if status not in (200, 201):
            out.append(j.failed(f"could not create a {record}: {status} {row}"))
            continue
        det = next((s for s in bm["screens_inventory"] if s["kind"] == "detail" and s.get("record") == record), None)
        control = 0
        if det:
            await _goto(page, _url(base, det) + f"?id={row['id']}")
            control = await page.get_by_role("button", name=re.compile(re.escape(name), re.I)).count()
            j.step("browser", f"look for a {name!r} control on {det['id']}", f"{control} control(s)")
        role = (act.get("roles") or ["?"])[0]
        ex = act["detail"].get("execution") or {}
        # an action that takes its values from the press (set_fields_from_input) is
        # pressed with a value, as a person would supply one
        inputs = {f: nonce for f in (ex.get("fields") or [])} if ex.get("op") == "set_fields_from_input" else {}
        if det and control:
            # press it for real; an action that asks for a value gets one through the screen's own prompt
            page.once("dialog", lambda d: __import__("asyncio").ensure_future(d.accept(nonce)))
            await page.get_by_role("button", name=re.compile(re.escape(name), re.I)).first.click()
            try:
                await page.wait_for_function("document.getElementById('state') && !document.getElementById('state').hidden && document.getElementById('state').textContent.trim() !== ''", timeout=STEP_TIMEOUT_MS)
                state_text = (await page.locator("#state").inner_text()).strip()
            except PlaywrightTimeoutError:
                state_text = ""
            j.step("browser", f"press {name!r} on {det['id']}", state_text)
            status, result = (200, {"pressed": True}) if state_text == "Done." else (400, {"error": state_text or "no result text"})
        else:
            status, result = _api(base, "POST", f"/api/actions/{table_name(record)}/{row['id']}/{urllib.parse.quote(name)}", {"role": role, "inputs": inputs})
            j.step("api", f"POST /api/actions/{table_name(record)}/{row['id']}/{name} role={role!r}", {"status": status, "body": result})
        if status != 200:
            out.append(j.failed(f"the declared custom action was refused: {status} {result}"))
            continue
        if not det or control == 0:
            out.append(j.blocked(f"no screen offers a {name!r} control for {act['id']}; the action works over the API "
                                 f"but a user cannot press it"))
            continue
        # persistence, read back: the press is in the row's own trail
        st_, hist = _api(base, "GET", f"/api/history/{table_name(record)}/{row['id']}")
        j.step("api", f"GET /api/history/{table_name(record)}/{row['id']}", {"status": st_, "entries": len((hist or {}).get("audit", []))})
        j.steps[-1]["user_facing"] = False
        if st_ != 200 or not any(e.get("action") == f"custom:{name}" for e in (hist or {}).get("audit", [])):
            out.append(j.failed(f"the press did not persist: no 'custom:{name}' entry in the row's trail", part="custom_action_execution"))
            continue
        out.append(j.passed())
    if not customs:
        out.append(Journey("custom_action_is_pressable_and_visible", "-").not_applicable("no custom action with a declared execution"))
    return out


# ---------------------------------------------------------------- shared press helpers
async def _press_on_detail(page, bm, base, record, row_id, pattern):
    """Opens the record's detail screen and presses the first button whose
    accessible name matches `pattern`. Returns (pressed: bool, detail_id, text)."""
    det = next((s_ for s_ in bm["screens_inventory"] if s_["kind"] == "detail" and s_.get("record") == record), None)
    if not det:
        return False, None, f"{record!r} has no detail screen"
    await _goto(page, _url(base, det) + f"?id={row_id}")
    btn = page.get_by_role("button", name=re.compile(pattern, re.I))
    if await btn.count() == 0:
        return False, det["id"], f"no control matching /{pattern}/ on {det['id']}"
    await btn.first.click()
    try:
        await page.wait_for_function("document.getElementById('state') && !document.getElementById('state').hidden && document.getElementById('state').textContent.trim() !== ''", timeout=STEP_TIMEOUT_MS)
        text = (await page.locator("#state").inner_text()).strip()
    except PlaywrightTimeoutError:
        text = ""
    return text == "Done.", det["id"], text or "no result text"


async def _walk_to_on_screen(page, j, bm, base, record, row_id, target_stage):
    """Presses the declared person-moved controls on the record's detail screen
    (and Approve at a gate) until the row is in target_stage. Every press is a
    browser step. Returns True on arrival, or records the block/failure."""
    wf = _workflow_for({"build_model": bm}, record)
    for _ in range(10):
        st, row = _api(base, "GET", f"/api/{table_name(record)}/{row_id}")
        if row.get("stage") == target_stage:
            return True
        gate = next((g for g in (wf.get("approvals") or []) if g.get("stage") == row.get("stage")), None)
        if gate:
            st2, dec = _api(base, "GET", f"/api/approvals/{table_name(record)}/{row_id}")
            if not ((dec or {}).get("decision") or {}).get("decision") == "APPROVED":
                ok, det_id, text = await _press_on_detail(page, bm, base, record, row_id, r"^Approve")
                j.step("browser", f"press Approve on {det_id} at gated stage {row.get('stage')!r}", text)
                if not ok:
                    out = j.blocked(f"no Approve control at gated stage {row.get('stage')!r}: {text}")
                    return False
        # shortest declared path, one press
        from collections import deque
        q = deque([(row.get("stage"), [])]); seen = {row.get("stage")}; path = None
        while q:
            st_, pth = q.popleft()
            if st_ == target_stage:
                path = pth; break
            for t in wf["transitions"]:
                if t.get("mover") == "roles" and t["from"] == st_ and t["to"] not in seen:
                    seen.add(t["to"]); q.append((t["to"], pth + [t]))
        if not path:
            j.failed(f"no declared person-moved path from {row.get('stage')!r} to {target_stage!r}")
            return False
        t = path[0]
        ok, det_id, text = await _press_on_detail(page, bm, base, record, row_id, r"^Move to " + re.escape(t["to"]))
        j.step("browser", f"press 'Move to {t['to']}' on {det_id}", text)
        if not ok:
            j.blocked(f"could not press the move to {t['to']!r}: {text}")
            return False
    j.failed(f"never reached {target_stage!r}")
    return False


async def _field_on_detail(page, bm, base, record, row_id, field_slug):
    det = next((s_ for s_ in bm["screens_inventory"] if s_["kind"] == "detail" and s_.get("record") == record), None)
    if not det:
        return None, None
    await _goto(page, _url(base, det) + f"?id={row_id}")
    try:
        await page.wait_for_selector("#fields:not([hidden])", timeout=STEP_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return None, det["id"]
    loc = page.locator(f"[data-field='{field_slug}']")
    if await loc.count() == 0:
        return None, det["id"]
    return (await loc.inner_text()).strip(), det["id"]


def _record_with_field_type(bm, record, ftype):
    return next((n for n, f in _fields_of(bm, record).items() if f["type"] == ftype), None)


async def stock_moves_on_the_screen_when_an_order_enters_its_stage(page, bm, base, tmpdir):
    out = []
    for wf_name, wf in bm["workflows"].items():
        record = next((r for r in bm["records"] if _workflow_for({"build_model": bm}, r) is wf), None)
        for eff in wf.get("effects") or []:
            if eff.get("op") != "apply_order_lines" or record is None:
                continue
            j = Journey("stock_moves_on_the_screen_when_an_order_enters_its_stage", f"{wf_name}:{eff['on_enter']}")
            nonce = _nonce()
            product_rec = _record_of_table(bm, eff["product_table"]); line_rec = _record_of_table(bm, eff["line_table"])
            # rows written over the API (no generated screen creates a record); the press and the read-back are on screens
            pf = _fields_of(bm, product_rec)
            pbody = {n: _value_for(f["type"], nonce) for n, f in pf.items() if f.get("required") == "yes" or f["type"] in ("short_text",)}
            stock_name = next(n for n in pf if slug(n) == "stock_on_hand"); reorder_name = next((n for n in pf if slug(n) == "reorder_point"), None)
            pbody[stock_name] = 10
            if reorder_name: pbody[reorder_name] = 2
            st, product = _api(base, "POST", f"/api/{eff['product_table']}", pbody)
            j.step("api", f"POST /api/{eff['product_table']} stock 10", st); j.steps[-1]["user_facing"] = False
            st, order = _create_row(bm, base, record, nonce)
            j.step("api", f"POST /api/{table_name(record)}", st); j.steps[-1]["user_facing"] = False
            lf = _fields_of(bm, line_rec)
            lbody = {n: _value_for(f["type"], nonce) for n, f in lf.items() if f.get("required") == "yes"}
            lbody[next(n for n in lf if slug(n) == eff["line_fk"])] = order["id"]
            lbody[next(n for n in lf if slug(n) == eff["product_fk"])] = product["id"]
            lbody[next(n for n in lf if slug(n) == eff["quantity_column"])] = 4
            st, line = _api(base, "POST", f"/api/{eff['line_table']}", lbody)
            j.step("api", f"POST /api/{eff['line_table']} qty 4", st); j.steps[-1]["user_facing"] = False
            if st not in (200, 201):
                out.append(j.failed(f"could not write the order line: {st} {line}")); continue
            if not await _walk_to_on_screen(page, j, bm, base, record, order["id"], eff["on_enter"]):
                out.append(j); continue
            expected = 10 + (4 if eff["direction"] == "receive" else -4)
            shown, det_id = await _field_on_detail(page, bm, base, product_rec, product["id"], "stock_on_hand")
            j.step("browser", f"open the product's detail {det_id} and read Stock on hand", shown)
            if shown is None:
                out.append(j.blocked(f"no screen shows the product's stock on hand")); continue
            if str(shown) != str(expected):
                out.append(j.failed(f"stock shown as {shown!r} after the order entered {eff['on_enter']!r}; expected {expected}", part="stock_ledger")); continue
            out.append(j.passed())
    if not out:
        out.append(Journey("stock_moves_on_the_screen_when_an_order_enters_its_stage", "-").not_applicable("no workflow declares a stock effect"))
    return out


async def payment_settles_its_target_on_the_screen(page, bm, base, tmpdir):
    out = []
    for record, rd in bm["records"].items():
        for eff in rd.get("on_create") or []:
            if eff.get("op") != "ledger_balance":
                continue
            target_rec = _record_of_table(bm, eff["table"]); wf = _workflow_for({"build_model": bm}, target_rec)
            edge = next((t for t in wf["transitions"] if t.get("mover") == "automatic" and t.get("event") == eff["event"]), None)
            j = Journey("payment_settles_its_target_on_the_screen", f"{record}->{target_rec}")
            if not edge:
                out.append(j.failed(f"no automatic edge for {eff['event']!r}")); continue
            nonce = _nonce()
            st, target = _create_row(bm, base, target_rec, nonce)
            j.step("api", f"POST /api/{eff['table']}", st); j.steps[-1]["user_facing"] = False
            total = None
            tf = _fields_of(bm, target_rec)
            if eff["total"]["kind"] == "lines":
                line_rec = _record_of_table(bm, eff["total"]["line_table"]); lf = _fields_of(bm, line_rec)
                lbody = {n: _value_for(f["type"], nonce) for n, f in lf.items() if f.get("required") == "yes"}
                lbody[next(n for n in lf if slug(n) == eff["total"]["line_fk"])] = target["id"]
                lbody[next(n for n in lf if slug(n) == eff["total"]["quantity_column"])] = 2
                lbody[next(n for n in lf if slug(n) == eff["total"]["amount_column"])] = 50
                st, line = _api(base, "POST", f"/api/{eff['total']['line_table']}", lbody)
                j.step("api", f"POST /api/{eff['total']['line_table']} 2 x 50", st); j.steps[-1]["user_facing"] = False
                total = 100
            else:
                st, row = _api(base, "GET", f"/api/{eff['table']}/{target['id']}")
                total = row.get(eff["total"]["column"])
            if not await _walk_to_on_screen(page, j, bm, base, target_rec, target["id"], edge["from"]):
                out.append(j); continue
            pf = _fields_of(bm, record)
            pbody = {n: _value_for(f["type"], nonce) for n, f in pf.items() if f.get("required") == "yes"}
            pbody[next(n for n in pf if slug(n) == eff["link_column"])] = target["id"]
            pbody[next(n for n in pf if slug(n) == eff["amount_column"])] = total
            st, pay = _api(base, "POST", f"/api/{table_name(record)}", pbody)
            j.step("api", f"POST /api/{table_name(record)} for the full {total} (no screen creates a payment)", {"status": st, "effects": (pay or {}).get("effects")})
            j.steps[-1]["user_facing"] = False
            visible, det_id, why = await _stage_visible(page, bm, base, target_rec, target["id"], edge["to"])
            j.step("browser", f"open {det_id}", why)
            if not visible:
                out.append(j.failed(f"after the settling payment the screen shows: {why}; expected {edge['to']!r}", part="ledger_balancing")); continue
            out.append(j.passed())
    if not out:
        out.append(Journey("payment_settles_its_target_on_the_screen", "-").not_applicable("no record declares a ledger_balance create effect"))
    return out


async def clone_appears_in_the_list_screen(page, bm, base, tmpdir):
    out = []
    for act in bm["actions_inventory"]:
        d = act.get("detail") or {}
        if act["kind"] != "custom" or (d.get("execution") or {}).get("op") != "clone":
            continue
        record = act["record"]; ex = d["execution"]
        j = Journey("clone_appears_in_the_list_screen", act["id"])
        nonce = _nonce()
        st, row = _create_row(bm, base, record, nonce)
        j.step("api", f"POST /api/{table_name(record)}", st); j.steps[-1]["user_facing"] = False
        ok, det_id, text = await _press_on_detail(page, bm, base, record, row["id"], r"^" + re.escape(d["name"]))
        j.step("browser", f"press {d['name']!r} on {det_id}", text)
        if not ok:
            out.append(j.blocked(f"could not press {d['name']!r}: {text}")); continue
        lst = next((s_ for s_ in bm["screens_inventory"] if s_["kind"] == "list" and s_.get("record") == record), None)
        if not lst:
            out.append(j.blocked(f"{record!r} has no list screen to show the copy")); continue
        await _goto(page, _url(base, lst))
        try:
            await page.wait_for_selector("#rows:not([hidden])", timeout=STEP_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            out.append(j.failed("the list screen never rendered", part="record_cloning")); continue
        body = await page.locator("#rows").inner_text()
        expected = nonce + (ex.get("title_suffix") or "")
        j.step("browser", f"open list {lst['id']} and look for {expected!r}", expected in body)
        if expected not in body:
            out.append(j.failed(f"the copy {expected!r} is not in the list", part="record_cloning")); continue
        out.append(j.passed())
    if not out:
        out.append(Journey("clone_appears_in_the_list_screen", "-").not_applicable("no custom action clones a record"))
    return out


async def sent_document_is_stamped_on_the_screen(page, bm, base, tmpdir):
    out = []
    for act in bm["actions_inventory"]:
        d = act.get("detail") or {}
        if act["kind"] != "custom" or (d.get("execution") or {}).get("op") != "generate_document":
            continue
        record = act["record"]; ex = d["execution"]
        j = Journey("sent_document_is_stamped_on_the_screen", act["id"])
        nonce = _nonce()
        st, row = _create_row(bm, base, record, nonce)
        j.step("api", f"POST /api/{table_name(record)}", st); j.steps[-1]["user_facing"] = False
        ok, det_id, text = await _press_on_detail(page, bm, base, record, row["id"], r"^" + re.escape(d["name"]))
        j.step("browser", f"press {d['name']!r} on {det_id}", text)
        if not ok:
            out.append(j.blocked(f"could not press {d['name']!r}: {text}")); continue
        shown, det_id = await _field_on_detail(page, bm, base, record, row["id"], ex.get("stamp_column", ""))
        j.step("browser", f"re-open {det_id} and read {ex.get('stamp_column')!r}", shown)
        if not shown:
            out.append(j.failed(f"{ex.get('stamp_column')!r} is empty on the screen after {d['name']!r}", part="document_generation")); continue
        st, pdf = _api(base, "GET", f"/api/history/{table_name(record)}/{row['id']}")
        doc = next((e.get("after", {}).get("document") for e in (pdf or {}).get("audit", []) if e.get("action") == f"custom:{d['name']}"), None)
        j.step("api", "the trail names the generated document", doc); j.steps[-1]["user_facing"] = False
        if not doc:
            out.append(j.failed("no generated document recorded in the trail", part="document_generation")); continue
        out.append(j.passed())
    if not out:
        out.append(Journey("sent_document_is_stamped_on_the_screen", "-").not_applicable("no custom action generates a document"))
    return out


async def rate_report_reflects_the_moves_made_on_the_screen(page, bm, base, tmpdir):
    out = []
    for scr in [s_ for s_ in bm["screens_inventory"] if s_["kind"] == "report"]:
        report = bm["reports"][scr["report"]]
        for m in report.get("spec") or []:
            sp = m["spec"]
            if sp.get("engine") != "stage_history" or sp.get("kind") != "rate_over_last_days":
                continue
            j = Journey("rate_report_reflects_the_moves_made_on_the_screen", f"{scr['id']}:{m['metric']}")
            record = _record_of_table(bm, sp["table"])
            nonce = _nonce()
            st, row = _create_row(bm, base, record, nonce)
            j.step("api", f"POST /api/{sp['table']}", st); j.steps[-1]["user_facing"] = False
            if not await _walk_to_on_screen(page, j, bm, base, record, row["id"], sp["numerator_stage"]):
                out.append(j); continue
            await _goto(page, _url(base, scr))
            try:
                table = await _read_report_table(page)
            except PlaywrightTimeoutError:
                out.append(j.failed("the report screen rendered no numbers", part="stage_history")); continue
            val = table.get(m["metric"]) or {}
            j.step("browser", f"open report {scr['id']} and read {m['metric']!r}", val)
            if not isinstance(val, dict) or not val.get("numerator"):
                out.append(j.failed(f"the row moved to {sp['numerator_stage']!r} on the screen but the rate counts {val!r}", part="stage_history")); continue
            out.append(j.passed())
    if not out:
        out.append(Journey("rate_report_reflects_the_moves_made_on_the_screen", "-").not_applicable("no report metric is a stage-history rate"))
    return out


RUNNERS = {
    "form_submit_lands_in_list_and_detail": form_submit_lands_in_list_and_detail,
    "report_screen_reflects_written_rows": report_screen_reflects_written_rows,
    "api_key_screen_connects_never_echoes": api_key_screen_connects_never_echoes,
    "oauth_connect_click_reaches_provider": oauth_connect_click_reaches_provider,
    "person_move_is_visible_on_the_screen": person_move_is_visible_on_the_screen,
    "gated_system_move_is_visible_on_the_screen": gated_system_move_is_visible_on_the_screen,
    "custom_action_is_pressable_and_visible": custom_action_is_pressable_and_visible,
    "stock_moves_on_the_screen_when_an_order_enters_its_stage": stock_moves_on_the_screen_when_an_order_enters_its_stage,
    "payment_settles_its_target_on_the_screen": payment_settles_its_target_on_the_screen,
    "clone_appears_in_the_list_screen": clone_appears_in_the_list_screen,
    "sent_document_is_stamped_on_the_screen": sent_document_is_stamped_on_the_screen,
    "rate_report_reflects_the_moves_made_on_the_screen": rate_report_reflects_the_moves_made_on_the_screen,
}
assert set(RUNNERS) == set(JOURNEYS), "every journey in JOURNEYS needs a runner and vice versa"


# ------------------------------------------------------------------- runner
def parts_in_manifest(app_dir):
    """The parts this app was actually built from, per its own manifest.
    Journeys run only for those; a part the app does not use cannot be
    qualified by driving this app."""
    path = os.path.join(app_dir, "MANIFEST.json") if app_dir else None
    if not path or not os.path.exists(path):
        return None
    return {p["part_id"]: p for p in json.load(open(path))["parts"]}


async def run(spec, base_url, out_dir, app_dir=None, write_receipts=WRITE_RECEIPTS):
    bm = spec["build_model"]
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    manifest = parts_in_manifest(app_dir)
    journeys = []
    with tempfile.TemporaryDirectory() as tmpdir:
        async with async_playwright() as pw:
            browser = await _launch(pw)
            for name, runner in RUNNERS.items():
                if manifest is not None and not any(p in manifest for p in JOURNEYS[name]):
                    continue  # the app does not use these parts; nothing to drive
                # a fresh page per journey: one journey's leftover navigation can
                # never poison the next (the qualifier's own third defect, 9 Aug)
                ctx = await browser.new_context()
                page_errors = []
                ctx.on("page", lambda p: p.on("pageerror", lambda e: page_errors.append(str(e))))
                page = await ctx.new_page()
                before = 0
                results = await runner(page, bm, base_url, tmpdir)
                await ctx.close()
                for j in results:
                    d = j.to_dict()
                    d["page_errors"] = page_errors[before:]
                    if d["page_errors"] and d["result"] == "PASS":
                        d["result"], d["reason"] = "FAIL", f"uncaught page error(s): {d['page_errors']}"
                        d["browser_verified"] = False
                    journeys.append(d)
            await browser.close()

    # per-part verdict
    parts = {}
    for d in journeys:
        for pid in d["parts"]:
            v = parts.setdefault(pid, {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "N/A": 0, "NOT_REACHED": 0, "browser_verified_passes": 0})
            if d["result"] == "FAIL" and d.get("failed_part") not in (None, pid):
                v["NOT_REACHED"] += 1  # the journey failed in another part's step before reaching this one
                continue
            v[d["result"]] += 1
            if d["result"] == "PASS" and d["browser_verified"]:
                v["browser_verified_passes"] += 1

    receipts = []
    refused = []
    if write_receipts:
        shelf = shelf_lib.load_shelf()
        by_id = {p["part_id"]: p for p in shelf["parts"]}
        for pid, v in parts.items():
            if v["browser_verified_passes"] == 0 or (FAIL_VETOES_RECEIPT and v["FAIL"] > 0):
                continue
            part = by_id.get(pid)
            if part is None:
                refused.append({"part_id": pid, "reason": "not on the shelf"})
                continue
            revision = shelf_lib.source_revision(part)
            if manifest is not None and manifest.get(pid, {}).get("revision") not in (None, revision):
                refused.append({"part_id": pid, "reason": f"the app vendors revision {manifest[pid]['revision']} but the shelf is at {revision} — drove stale bytes"})
                continue
            try:
                r = shelf_lib.record_qualification(
                    pid, revision, [d for d in journeys if pid in d["parts"]], base_url)
                receipts.append({"part_id": pid, "version": r["version"], "revision": r["revision"]})
            except shelf_lib.ShelfError as exc:
                refused.append({"part_id": pid, "reason": str(exc)})

    report = {"base_url": base_url, "journeys": journeys, "parts": parts,
              "receipts_written": receipts, "receipts_refused": refused}
    json.dump(report, open(os.path.join(out_dir, "report_seams.json"), "w"), indent=1)
    return report


def summarise(report):
    lines = []
    for d in report["journeys"]:
        lines.append(f"{d['result']:7} {d['journey']} [{d['subject']}]" + (f" — {d['reason']}" if d["reason"] else ""))
        for note in d.get("notes", []):
            lines.append(f"        note: {note}")
    lines.append("---")
    for pid, v in sorted(report["parts"].items()):
        lines.append(f"{pid:32} PASS {v['PASS']}  FAIL {v['FAIL']}  BLOCKED {v['BLOCKED']}  NOT_REACHED {v['NOT_REACHED']}")
    lines.append("---")
    lines.append("receipts written: " + (", ".join(f"{r['part_id']}@{r['version']}={r['revision']}" for r in report["receipts_written"]) or "none"))
    for r in report["receipts_refused"]:
        lines.append(f"receipt refused: {r['part_id']} — {r['reason']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--app-dir", help="the built app (its MANIFEST.json limits journeys to the parts it uses)")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--no-receipts", action="store_true")
    args = ap.parse_args(argv)
    spec = json.load(open(args.spec, encoding="utf-8"))
    report = asyncio.run(run(spec, args.base_url, args.out, args.app_dir, write_receipts=not args.no_receipts))
    print(summarise(report))
    failed = [d for d in report["journeys"] if d["result"] == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
