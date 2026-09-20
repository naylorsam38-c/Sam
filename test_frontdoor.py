# test_frontdoor.py -- real Chromium (Playwright), real HTTP servers, real ground truth.
#
# Section A/B: skins-engine.js (the JS port of skins_library/design_tokens.py +
#   render_css.py) reproduces the real Python engine byte-for-byte, across the
#   43 actually-measured categories and the full 360-hue x 4-look input range.
# Section C: withEdits/lookFields -- Front-Door-specific logic with no Python
#   original, verified against its own explicit spec (this file's assertions).
# Section D: checkEdit/normalizeChanges gates.
# Section E: the real ask -> resolve -> preview -> keep/undo flow in
#   front-door.html, against the real 8-app shelf catalog in library.json,
#   three viewports.
# Section F: frontdoor-skin-adapter.js's postMessage contract, proven against
#   genuinely cross-origin pages (a second HTTP server on a different port),
#   both measured families plus an unmeasured one.
import functools, http.server, json, os, sys, threading, time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
SKINS = os.path.join(ROOT, "skins_library")
PARENT_PORT = 8766
CHILD_PORT = 8767
URL = f"http://localhost:{PARENT_PORT}/front-door.html"
URL_LIB = f"http://localhost:{PARENT_PORT}/_test_with_library.html"
CHILD_ORIGIN = f"http://localhost:{CHILD_PORT}"
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

sys.path.insert(0, SKINS)
import design_tokens as dt, render_css as rc

res = []
def check(name, ok, detail=""):
    res.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else " -- " + str(detail)[:300]))

def serve(directory, port):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

def rgb(hexcolor):
    hexcolor = hexcolor.lstrip("#")
    return "rgb(%d, %d, %d)" % tuple(int(hexcolor[i:i+2], 16) for i in (0, 2, 4))

def seed_front_door(pg, ask_text, category_id):
    """Seed localStorage as if resolve() had already matched `ask_text` to the
    library app whose slug is `category_id`, so tests can jump straight past
    the ask screen (mirrors real resolve() output exactly)."""
    lib = json.load(open(os.path.join(ROOT, "library.json")))
    app = next(a for a in lib["apps"] if a["slug"] == category_id)
    inst = {"category_id": category_id, "label": app["name"], "capabilities": [ask_text], "app": app,
            "skin": {"look": "original", "accent": "#1D1D1B", "background": "#FFFFFF", "surface": "#F5F5F4",
                     "text": "#1D1D1B", "font": "", "radius": 12},
            "log": [], "created": "2026-09-20T00:00:00Z"}
    pg.evaluate("i => localStorage.setItem('fd.instance', JSON.stringify(i))", inst)

def seed_lib_harness(pg, category_id):
    inst = {"category_id": category_id,
            "skin": {"look": "original", "accent": "#1D1D1B", "background": "#FFFFFF", "surface": "#F5F5F4",
                     "text": "#1D1D1B", "font": "", "radius": 12},
            "log": []}
    pg.evaluate("i => localStorage.setItem('fd.instance', JSON.stringify(i))", inst)


httpd1 = serve(ROOT, PARENT_PORT)
httpd2 = serve(os.path.join(ROOT, "adapter-fixture"), CHILD_PORT)
time.sleep(0.2)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROMIUM)

    # ── A. Engine parity: the JS port against the real 43 measured categories ──
    pg = b.new_page(); pg.goto(URL); pg.wait_for_timeout(200)
    idx = json.load(open(f"{SKINS}/_index.json"))["categories"]
    rows = []
    for slug, info in idx.items():
        for i, th in enumerate(dt.THEME_ORDER):
            sid = f"skin-00{i+2}"
            rows.append({"slug": slug, "family": info["family"], "theme": th, "sid": sid,
                         "css": open(f"{SKINS}/{slug}/{sid}.css").read(),
                         "tokens": json.load(open(f"{SKINS}/{slug}/{sid}.json"))["design_tokens"]})
    out = pg.evaluate("""rows => rows.map(r => {
        const t = Skins.build(r.theme, Skins.hue(r.slug));
        delete t._hue;
        return { css: Skins.render(r.family, t) + "\\n", tokens: t };
    })""", rows)
    css_bad = [r["sid"] + " " + r["slug"] for r, o in zip(rows, out) if o["css"] != r["css"]]
    tok_bad = [r["sid"] + " " + r["slug"] for r, o in zip(rows, out) if o["tokens"] != r["tokens"]]
    check(f"all {len(rows)} real skin CSS files reproduced byte-for-byte by skins-engine.js", len(rows) == 172 and not css_bad, css_bad[:5])
    check(f"all {len(rows)} real skin token sets reproduced exactly by skins-engine.js", not tok_bad, tok_bad[:5])
    check("both markup families covered (shared_card, todomvc)", {r["family"] for r in rows} == {"shared_card", "todomvc"})

    # ── B. Full input range: all 360 hues x 4 looks, against the real Python ──
    alljs = pg.evaluate("""() => { const o = []; for (let h = 0; h < 360; h++) for (const th of Skins.THEME_ORDER) { const t = Skins.build(th, h); delete t._hue; o.push(t); } return o; }""")
    allpy = [dt.build_tokens(th, float(h)) for h in range(360) for th in dt.THEME_ORDER]
    diff = [i for i, (a, c) in enumerate(zip(alljs, allpy)) if a != c]
    check("all 360 hues x 4 looks = 1440 token sets identical to design_tokens.py", len(alljs) == 1440 and not diff, [(i // 4, dt.THEME_ORDER[i % 4]) for i in diff[:5]])
    rnd = pg.evaluate("() => [0.5, 1.5, 2.5, 3.5, 2.4999, 2.5001].map(x => Skins.pyRound(x))")
    check("Skins.pyRound matches Python's round() on halves (banker's rounding)", rnd == [round(x) for x in [0.5, 1.5, 2.5, 3.5, 2.4999, 2.5001]], rnd)

    # ── C. withEdits / lookFields: Front-Door-specific edit-layering logic ──
    ident = pg.evaluate("""() => { const bad = []; for (let h = 0; h < 360; h += 37) for (const th of Skins.THEME_ORDER) {
        const t = Skins.build(th, h), skin = { ...SKIN_DEFAULT, ...Skins.lookFields(th, h) };
        const edited = Skins.withEdits(t, skin); delete edited._hue; const tc = {...t}; delete tc._hue;
        if (JSON.stringify(edited) !== JSON.stringify(tc)) bad.push(th + " " + h); } return bad; }""")
    check("picking a look with zero further edits reproduces its own build() tokens exactly", not ident, ident[:5])
    edit = pg.evaluate("""() => { const h = Skins.hue("ab-testing-experimentation"), t = Skins.build("bold_contrast", h);
        return Skins.withEdits(t, { ...SKIN_DEFAULT, ...Skins.lookFields("bold_contrast", h), accent: "#1F3A5F", radius: 8 }); }""")
    check("accent edit recolours primary, hover, focus ring and glow together",
          edit["primary"] == "#1f3a5f" and "#1f3a5f" in edit["shadow_focus_ring"] and "#1f3a5f" in edit["shadow_card"] and edit["primary_hover"] != "#1f3a5f", edit)
    check("radius edit keeps the look's own small-to-large ratio", edit["radius"] == "8px" and edit["radius_sm"] == "6px", edit)
    check("readable foreground text on the new accent", edit["primary_foreground"] == "#ffffff", edit["primary_foreground"])
    pill = pg.evaluate("""() => { const h = Skins.hue("productivity"); return Skins.withEdits(Skins.build("soft_rounded", h), { ...SKIN_DEFAULT, ...Skins.lookFields("soft_rounded", h), radius: 6 }).radius_pill; }""")
    check("pill buttons stay pills (999px) when corners change on soft_rounded", pill == "999px", pill)

    # ── D. Gates ──
    g = pg.evaluate("""() => ({
        badLook: checkEdit({changes:[{key:"look",value:"neon",say:"x"}]}).length > 0,
        goodLook: checkEdit({changes:[{key:"look",value:"warm_editorial",say:"x"}]}).length === 0,
        lookFont: checkEdit({changes:[{key:"font",value:"",say:"x"}]}).length === 0,
        badFont: checkEdit({changes:[{key:"font",value:"Comic Sans MS",say:"x"}]}).length > 0,
        badAccent: checkEdit({changes:[{key:"accent",value:"not-a-color",say:"x"}]}).length > 0,
        noFamily: (() => { try { Skins.render("bootstrap", Skins.build("minimal_neutral", 1)); return false; } catch (e) { return true; } })(),
        noTheme: (() => { try { Skins.build("neon", 1); return false; } catch (e) { return true; } })(),
        libSize: Object.keys(LIBRARY).length,
        libAllColorsOnly: Object.values(LIBRARY).every(v => v.family === "")
    })""")
    for k in ["badLook", "badFont", "badAccent", "noFamily", "noTheme"]: check("gate refuses: " + k, g[k])
    for k in ["goodLook", "lookFont"]: check("gate accepts: " + k, g[k])
    check("shelf library has all 19 real catalog apps", g["libSize"] == 19, g["libSize"])
    check("every shelf app is honestly colours-only (no markup was measured)", g["libAllColorsOnly"])
    nc = pg.evaluate("() => normalizeChanges([{key:'accent',value:'#1F3A5F',say:'x'}])")
    check("colour change while on 'original' adds a visible look-switch step first", nc[0]["key"] == "look" and nc[0]["value"] == "minimal_neutral" and bool(nc[0]["say"]))
    resolved = pg.evaluate("""() => { const lib = window.__lib || null; return true; }""")
    pg.close()

    # ── E. The real ask -> resolve -> preview -> keep/undo flow, 3 viewports ──
    for label, vp, scheme in [("desktop", {"width": 1280, "height": 800}, "light"), ("mobile", {"width": 390, "height": 844}, "light"), ("mobile-dark", {"width": 390, "height": 844}, "dark")]:
        pg = b.new_page(viewport=vp, color_scheme=scheme); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(200)

        # Ask flow, unseeded: a real free-text ask must resolve to the real Flagsmith entry.
        pg.fill("#ask-input", "I need a feature flag tool for gradual rollouts")
        pg.click("#ask-form button")
        pg.wait_for_timeout(200)
        check(f"{label}: a real ask resolves to the matching real shelf app", pg.evaluate("inst.app.slug") == "ab-testing-experimentation", pg.evaluate("inst.app.name"))
        pg.evaluate("localStorage.clear()")

        # An ask matching nothing on the shelf must say so, not guess.
        pg.reload(); pg.wait_for_timeout(200)
        pg.fill("#ask-input", "xyzzy plugh quux")
        pg.click("#ask-form button")
        pg.wait_for_timeout(150)
        check(f"{label}: an ask matching nothing says so instead of guessing", not pg.locator("#ask-empty").is_hidden())
        pg.evaluate("localStorage.clear()")

        seed_front_door(pg, "I need a feature flag tool", "ab-testing-experimentation")
        pg.reload(); pg.wait_for_timeout(600)
        slot = lambda: pg.frame_locator("#slot")
        def btn_bg(): return slot().locator("button").first.evaluate("e => getComputedStyle(e).backgroundColor")
        def body_bg(): return slot().locator("body").evaluate("e => getComputedStyle(e).backgroundColor")
        def slot_css(): return slot().locator("#skin").evaluate("e => e.textContent")

        check(f"{label}: saved instance opens straight into the app screen", pg.evaluate("document.body.dataset.state") == "app")
        check(f"{label}: the real app's own name/screenshot/repo are shown", pg.locator("#app-name").inner_text() == "Flagsmith" and "ab-testing-experimentation" in pg.locator("#app-shot").get_attribute("src") and "github.com/Flagsmith" in pg.locator("#app-repo").get_attribute("href"))
        check(f"{label}: unmeasured app is labelled colours-only, not silently faked as fully skinned", "hasn't been measured" in pg.locator("#app-family-note").inner_text())
        check(f"{label}: original look = the demo's own plain monochrome button", btn_bg() == rgb("#1D1D1B"), btn_bg())

        pg.click("#fab"); pg.wait_for_timeout(200)
        tiles = pg.locator(".look")
        check(f"{label}: five looks offered, original marked pressed", tiles.count() == 5 and pg.locator('.look[data-look="original"]').get_attribute("aria-pressed") == "true")
        check(f"{label}: looks row scrolls sideways, page doesn't", pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))

        exp = pg.evaluate("() => { const t = Skins.build('bold_contrast', Skins.hue('ab-testing-experimentation')); delete t._hue; return t; }")
        exp_css = pg.evaluate("() => { const t = Skins.build('bold_contrast', Skins.hue('ab-testing-experimentation')); return Skins.render('shared_card', t); }")
        pg.click('.look[data-look="bold_contrast"]'); pg.wait_for_timeout(300)
        check(f"{label}: tapping a look previews it live", btn_bg() == rgb(exp["primary"]) and body_bg() == rgb(exp["background"]), (btn_bg(), body_bg()))
        check(f"{label}: preview uses the exact byte-verified skin CSS", slot_css().strip() == exp_css.strip())
        check(f"{label}: preview asks before keeping", pg.locator("#ecol .choices").last.is_visible() and "Keep it" in pg.locator("#ecol").inner_text())
        pg.locator("#ecol .choices").last.get_by_text("Not that").click(); pg.wait_for_timeout(300)
        check(f"{label}: 'Not that' puts it back, nothing logged", btn_bg() == rgb("#1D1D1B") and pg.evaluate("inst.log.length") == 0)

        warm = pg.evaluate("() => { const t = Skins.build('warm_editorial', Skins.hue('ab-testing-experimentation')); delete t._hue; return t; }")
        pg.click('.look[data-look="warm_editorial"]'); pg.wait_for_timeout(200)
        pg.locator("#ecol .choices").last.get_by_text("Keep it").click(); pg.wait_for_timeout(300)
        saved = pg.evaluate("JSON.parse(localStorage.getItem('fd.instance'))")
        check(f"{label}: kept look is saved and logged", saved["skin"]["look"] == "warm_editorial" and len(saved["log"]) == 1)
        check(f"{label}: warm look applied (serif headings, warm accent)", btn_bg() == rgb(warm["primary"]) and "Georgia" in slot().locator("h1").evaluate("e => getComputedStyle(e).fontFamily"))
        check(f"{label}: tile now marked pressed", pg.locator('.look[data-look="warm_editorial"]').get_attribute("aria-pressed") == "true")
        pg.click('.look[data-look="warm_editorial"]'); pg.wait_for_timeout(150)
        check(f"{label}: re-picking the same look says so, changes nothing", "That's the look it has now." in pg.locator("#ecol").inner_text() and pg.evaluate("inst.log.length") == 1)

        pg.fill("#say-input", "make it navy"); pg.click("#say-form button"); pg.wait_for_timeout(300)
        pg.locator("#ecol .choices").last.get_by_text("Apply").click(); pg.wait_for_timeout(300)
        check(f"{label}: a free-text colour edit lands on top of the kept look", btn_bg() == rgb("#1F3A5F") and "Georgia" in slot().locator("h1").evaluate("e => getComputedStyle(e).fontFamily"))
        pg.reload(); pg.wait_for_timeout(600)
        check(f"{label}: survives reload", btn_bg() == rgb("#1F3A5F") and pg.evaluate("inst.skin.look") == "warm_editorial")

        pg.click("#fab"); pg.wait_for_timeout(150)
        pg.locator("#log .link").first.click(); pg.wait_for_timeout(300)
        check(f"{label}: undo the colour edit -> back to plain warm", btn_bg() == rgb(warm["primary"]))
        pg.locator("#log .link").first.click(); pg.wait_for_timeout(300)
        check(f"{label}: undo the look -> back to original", btn_bg() == rgb("#1D1D1B") and pg.evaluate("inst.skin.look") == "original")

        pg.click('.look[data-look="soft_rounded"]'); pg.wait_for_timeout(200)
        pg.click("#close"); pg.wait_for_timeout(200)
        check(f"{label}: closing mid-preview puts it back", btn_bg() == rgb("#1D1D1B") and pg.evaluate("inst.skin.look") == "original")
        for look in ["minimal_neutral", "bold_contrast", "soft_rounded"]:
            pg.click("#fab"); pg.wait_for_timeout(100); pg.click(f'.look[data-look="{look}"]'); pg.wait_for_timeout(250)
            pg.locator("#ecol .choices").last.get_by_text("Keep it").click(); pg.wait_for_timeout(250)
            pg.click("#close"); pg.wait_for_timeout(150)
        check(f"{label}: no JS errors across the whole flow", not errs, errs)
        pg.close()

    # ── F. Adapter: real cross-origin postMessage, both measured families + one unmeasured ──
    pg = b.new_page(viewport={"width": 1280, "height": 800}); errs = []; warns = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: warns.append(m.text) if "skin adapter" in m.text else None)
    pg.goto(URL_LIB); pg.wait_for_timeout(200)
    seed_lib_harness(pg, "shared-demo")
    pg.reload(); pg.wait_for_timeout(1000)
    app = pg.frame_locator("#app iframe")
    has_style = lambda: app.locator("#frontdoor-skin").count() > 0
    check("adapter: app loads in its own genuinely cross-origin frame, own look on 'original'",
          not has_style() and app.locator("#b").evaluate("e => getComputedStyle(e).backgroundColor") == rgb("#1D1D1B"))
    pg.click("#fab"); pg.click('.look[data-look="bold_contrast"]'); pg.wait_for_timeout(500)
    exp_css = pg.evaluate("() => { const t = Skins.build('bold_contrast', Skins.hue('shared-demo')); return Skins.render('shared_card', t); }")
    exp = pg.evaluate("() => { const t = Skins.build('bold_contrast', Skins.hue('shared-demo')); delete t._hue; return t; }")
    check("adapter: preview reaches the app across a real different origin", has_style() and app.locator("#frontdoor-skin").evaluate("e => e.textContent").strip() == exp_css.strip())
    check("adapter: app's own button wears the skin", app.locator("#b").evaluate("e => getComputedStyle(e).backgroundColor") == rgb(exp["primary"]))
    check("adapter: colours exposed as --fd-* variables", app.locator("html").evaluate("e => e.style.getPropertyValue('--fd-primary')") == exp["primary"])
    pg.locator("#ecol .choices").last.get_by_text("Not that").click(); pg.wait_for_timeout(400)
    check("adapter: 'Not that' strips the skin off again", not has_style() and app.locator("html").evaluate("e => e.style.getPropertyValue('--fd-primary')") == "")
    app.locator("body").evaluate("() => window.postMessage({type:'frontdoor.skin', tokens:{primary:'#ff0000'}, css:'button{background:#ff0000}'}, '*')")
    pg.wait_for_timeout(300)
    check(f"adapter: refuses a skin from any other origin, and says which", not has_style() and any(f"localhost:{CHILD_PORT}" in w for w in warns), warns)
    check("adapter: no JS errors", not errs, errs)
    pg.close()

    # todomvc family, cross-origin
    pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL_LIB); pg.wait_for_timeout(200)
    seed_lib_harness(pg, "todomvc-demo")
    pg.reload(); pg.wait_for_timeout(1000)
    app = pg.frame_locator("#app iframe")
    pg.click("#fab"); pg.click('.look[data-look="minimal_neutral"]'); pg.wait_for_timeout(500)
    exp2 = pg.evaluate("() => { const t = Skins.build('minimal_neutral', Skins.hue('todomvc-demo')); delete t._hue; return t; }")
    check("adapter: todomvc family also gets a real cross-origin stylesheet",
          app.locator("#frontdoor-skin").count() == 1 and app.locator(".toggle").evaluate("e => getComputedStyle(e).accentColor") == rgb(exp2["primary"]))
    check("adapter: no JS errors (todomvc)", not errs, errs)
    pg.close()

    # A shelf app whose markup nobody has measured: colours only, no CSS guessed at it
    pg = b.new_page()
    pg.goto(URL_LIB); pg.wait_for_timeout(200)
    seed_lib_harness(pg, "unmeasured-demo")
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click("#fab"); pg.click('.look[data-look="minimal_neutral"]'); pg.wait_for_timeout(500)
    app = pg.frame_locator("#app iframe")
    check("adapter: unmeasured shelf app gets variables but no guessed stylesheet",
          app.locator("#frontdoor-skin").count() == 0 and app.locator("html").evaluate("e => e.style.getPropertyValue('--fd-primary')") != "")
    pg.close()

    b.close()

httpd1.shutdown(); httpd2.shutdown()
print(f"\n{sum(res)}/{len(res)} passed")
if sum(res) != len(res):
    sys.exit(1)
