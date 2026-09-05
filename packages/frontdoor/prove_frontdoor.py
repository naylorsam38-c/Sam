#!/usr/bin/env python3
"""
prove_frontdoor.py — the front door, driven by a real browser, end to end.

Three jobs in one run:

  1. SHOTS   Real screenshots of the three looks, taken from real running apps
             with real rows in them, for the "which of these looks right?"
             question. The person is choosing from photographs of the thing
             they will get, not from drawings of it.

  2. DRIVE   A person who has never seen this answers the eight questions in a
             real browser -- types their words, taps the cards, taps a look --
             presses Build it, and gets an app.

  3. VERIFY  That app is then opened and used: a row is created through its own
             interface and read back from its own data. If the front door hands
             someone an app whose buttons do not work, this fails.

Usage:  python prove_frontdoor.py            (writes evidence/FRONTDOOR.md)
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SHOTS = os.path.join(HERE, "web", "shots")
EVID = os.path.join(HERE, "evidence")
IFACE = os.path.join(ROOT, "interfaces")
sys.path.insert(0, IFACE)

#: which family's real app each look is photographed from, and what to seed so
#: the picture shows a working app rather than an empty one
SHOT_SOURCE = {
    "console": ("erp-backbone", 8951, (1280, 780)),
    "board":   ("crm-pipeline", 8952, (1280, 780)),
    "pocket":  ("booking-frontdesk", 8953, (390, 780)),
}
SEED = {
    "erp-backbone": [("products", {"Name": "Blue widget", "SKU": "BW-1", "Sale price": 24.5, "Cost": 11, "Stock on hand": 42, "Reorder point": 10}),
                     ("products", {"Name": "Red widget", "SKU": "RW-2", "Sale price": 31, "Cost": 14, "Stock on hand": 6, "Reorder point": 10}),
                     ("products", {"Name": "Steel bracket", "SKU": "SB-9", "Sale price": 8.75, "Cost": 3.2, "Stock on hand": 260, "Reorder point": 50}),
                     ("suppliers", {"Name": "Northwind Supply", "Email": "hello@northwind.test", "Phone": "+61 400 111 222"}),
                     ("customer_accounts", {"Name": "Harbour Trading", "Email": "ap@harbour.test"})],
    "crm-pipeline": [("organisations", {"Name": "Harbour Trading", "Website": "https://harbour.test"}),
                     ("contacts", {"Full name": "Dana Ellis", "Email": "dana@harbour.test"}),
                     ("deals", {"Title": "Annual supply", "Value": 24000, "Owner": "ann"}),
                     ("deals", {"Title": "Pilot rollout", "Value": 6500, "Owner": "ben"}),
                     ("deals", {"Title": "Renewal — Northwind", "Value": 11200, "Owner": "ann"})],
    "booking-frontdesk": [("services", {"Name": "Consultation", "Duration minutes": 30, "Price": 90}),
                          ("services", {"Name": "Follow-up", "Duration minutes": 20, "Price": 60}),
                          ("customers", {"Full name": "Jo Bright", "Email": "jo@example.test", "Phone": "+61 400 333 444"}),
                          ("customers", {"Full name": "Sam Reilly", "Email": "sam@example.test"})],
}
#: deals are moved along so the Board picture shows a real spread across columns
MOVES = {"crm-pipeline": [(1, "Contacted", "Sales rep"), (2, "Contacted", "Sales rep"), (2, "Proposal sent", "Sales rep")]}


def api(port, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def start(cwd, port, script="app.py", extra=()):
    proc = subprocess.Popen(["python3", script, *extra], cwd=cwd, env=dict(os.environ, PORT=str(port)),
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            return proc
        except Exception:
            time.sleep(0.15)
    proc.terminate()
    raise RuntimeError(f"{script} on {port} did not start")


async def take_shots(pw, log):
    os.makedirs(SHOTS, exist_ok=True)
    for design, (family, port, vp) in SHOT_SOURCE.items():
        app = os.path.join(IFACE, "build", family, "app")
        db = os.path.join(app, "app.db")
        if os.path.exists(db):
            os.remove(db)
        proc = start(app, port)
        try:
            ids = []
            for table, body in SEED.get(family, []):
                st, r = api(port, "POST", "/api/" + table, body)
                ids.append((table, (r or {}).get("id")))
            for idx, to, role in MOVES.get(family, []):
                table, rid = [x for x in ids if x[0] == "deals"][idx] if family == "crm-pipeline" else (None, None)
                if rid:
                    api(port, "POST", f"/api/moves/{table}/{rid}", {"to": to, "role": role})
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={"width": vp[0], "height": vp[1]},
                                          device_scale_factor=2)
            await page.goto(f"http://127.0.0.1:{port}/ui-{design}.html")
            await page.wait_for_timeout(500)
            # land on a page that shows the design at its most characteristic
            target = {"console": "Products", "board": "Deals", "pocket": "Services"}[design]
            link = page.locator(f'[data-act="nav"][data-kind="list"][data-record="{target[:-1] if target.endswith("s") else target}"]')
            if await link.count():
                await link.first.click()
                await page.wait_for_timeout(400)
            out = os.path.join(SHOTS, f"{design}.png")
            await page.screenshot(path=out)
            await browser.close()
            log.append((True, f"{design} picture taken from the real {family} app ({len(SEED.get(family, []))} rows seeded)"))
        finally:
            proc.terminate()


async def drive_front_door(pw, log):
    proc = start(HERE, 8700, "serve.py", extra=("--port", "8700", "--apps-from", "8961"))
    result = {}
    try:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 900, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await page.goto("http://127.0.0.1:8700/")
        await page.wait_for_selector("#stage h1")
        os.makedirs(EVID, exist_ok=True)

        # 1 — their own words, including something this system cannot do
        words = ("Something for connecting people — keep everyone's details, see who is at what stage "
                 "of joining, and log every time we talk to them. I'd also like them to chat to each other.")
        await page.fill("#w", words)
        await page.screenshot(path=os.path.join(EVID, "01-what-do-you-want.png"))
        await page.click("#next")
        await page.wait_for_timeout(300)

        # 2 — the cards. The impossible ask must be named here, before they choose.
        body = await page.locator("#stage").inner_text()
        log.append((("chat" in body.lower() and "not something this can build" in body.lower()),
                    "the chat request is named as impossible on the card screen, with what is offered instead"))
        ticked = await page.locator(".opt.on b").all_inner_texts()
        log.append((any("People" in t for t in ticked),
                    f"their words pre-ticked the right card: {ticked}"))
        await page.screenshot(path=os.path.join(EVID, "02-which-does-it-need.png"))
        await page.click("#next"); await page.wait_for_timeout(250)

        # 3 — who uses it
        await page.click('[data-v="small_team"]'); await page.screenshot(path=os.path.join(EVID, "03-who-uses-it.png"))
        await page.click("#next"); await page.wait_for_timeout(250)

        # 4 — the look, from real photographs
        shots = await page.locator(".shot img").count()
        log.append((shots == 3, f"three real screenshots offered for the look ({shots} found)"))
        await page.click('[data-v="board"]'); await page.screenshot(path=os.path.join(EVID, "04-which-look.png"))
        await page.click("#next"); await page.wait_for_timeout(250)

        # 5, 6, 7
        await page.click('[data-v="balanced"]'); await page.click("#next"); await page.wait_for_timeout(200)
        await page.click('[data-v="orbit"]'); await page.screenshot(path=os.path.join(EVID, "05-your-mark.png"))
        await page.click("#next"); await page.wait_for_timeout(200)
        await page.fill("#w", "Connector"); await page.click("#next"); await page.wait_for_timeout(300)

        # review, then build
        review = await page.locator("#stage").inner_text()
        log.append(("Here is what you will get" in review, "a plain-English review before anything is built"))
        log.append(("chat" in review.lower() or "messaging" in review.lower(),
                    "the review repeats what will NOT be in the app"))
        await page.screenshot(path=os.path.join(EVID, "06-here-is-what-you-get.png"), full_page=True)
        await page.click("#next")
        await page.wait_for_selector(".built .big, .err", timeout=180000)
        if await page.locator(".err").count():
            log.append((False, "the build refused: " + await page.locator(".err").inner_text()))
            await browser.close()
            return result
        headline = await page.locator(".built .big").inner_text()
        stats = await page.locator(".built .help").inner_text()
        log.append((True, f"built from eight answers — {headline.strip()} · {stats.strip()}"))
        await page.screenshot(path=os.path.join(EVID, "07-built.png"))
        result["app_url"] = await page.locator('a.card[target="_blank"]').first.get_attribute("href")
        summary_href = await page.locator("a.card").nth(1).get_attribute("href")
        # the summary is a page of plain English, not JSON -- fetched as text
        with urllib.request.urlopen("http://127.0.0.1:8700" + summary_href, timeout=10) as r:
            result["summary_text"] = r.read().decode()
        log.append(("What this does NOT do" in result["summary_text"],
                    "the plain-English summary is there, and it states what the app does NOT do"))
        log.append((not errors, "no browser errors in the front door" + (": " + "; ".join(errors[:2]) if errors else "")))
        await browser.close()
    finally:
        pass  # the front door keeps the built app alive; both are stopped by the caller
    result["front_door_proc"] = proc
    return result


async def verify_built_app(pw, url, log):
    """The person opens what they were handed and uses it. A row is created
    through the interface and read back from the app's own data."""
    port = int(url.rstrip("/").rsplit(":", 1)[1])
    browser = await pw.chromium.launch()
    page = await browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.goto(url)
    log.append((await page.locator("a.c").count() == 3, "the app opens on a chooser offering all three looks"))
    await page.goto(url + "ui-board.html")
    await page.wait_for_timeout(600)
    st, before = api(port, "GET", "/api/organisations")
    await page.click('[data-act="nav"][data-kind="list"][data-record="Organisation"]')
    await page.wait_for_timeout(250)
    await page.click('[data-act="newRow"][data-record="Organisation"]')
    await page.wait_for_timeout(250)
    await page.fill('form[data-act="create"] [name="name"]', "Proof Co")
    await page.click('form[data-act="create"] button[type=submit]')
    await page.wait_for_timeout(500)
    st, after = api(port, "GET", "/api/organisations")
    made = [r for r in after if r["id"] not in {x["id"] for x in before}]
    log.append((len(made) == 1 and made[0]["name"] == "Proof Co",
                "a row created through the handed-over app's own button is really in its data"))
    await page.screenshot(path=os.path.join(EVID, "08-the-app-they-got.png"))
    log.append((not errors, "no browser errors in the built app" + (": " + errors[0] if errors else "")))
    await browser.close()


async def main():
    log = []
    async with async_playwright() as pw:
        await take_shots(pw, log)
        res = await drive_front_door(pw, log)
        try:
            if res.get("app_url"):
                await verify_built_app(pw, res["app_url"], log)
        finally:
            if res.get("front_door_proc"):
                res["front_door_proc"].terminate()
    os.makedirs(EVID, exist_ok=True)
    passed = sum(1 for ok, _ in log if ok)
    lines = ["# The front door, driven end to end", "",
             f"Run {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}. **{passed}/{len(log)} checks passed.**", "",
             "Someone who has never seen this system answered eight questions in a real browser and was "
             "handed a working app. Every line below was produced by doing it, not by describing it.", ""]
    for ok, text in log:
        lines.append(f"- {'PASS' if ok else 'FAIL'} {text}")
    if res.get("summary_text"):
        lines += ["", "## The summary they were handed", "", "```", res["summary_text"][:4000], "```"]
    lines += ["", "## Pictures", ""] + [f"- `evidence/{f}`" for f in sorted(os.listdir(EVID)) if f.endswith(".png")]
    open(os.path.join(EVID, "FRONTDOOR.md"), "w", encoding="utf-8").write("\n".join(lines))
    for ok, text in log:
        print(("PASS " if ok else "FAIL ") + text)
    print(f"\n{passed}/{len(log)} -> evidence/FRONTDOOR.md")
    return 0 if passed == len(log) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
