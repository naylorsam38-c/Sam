#!/usr/bin/env python3
"""apply_skin.py -- drives a real, running build of Super Productivity
(https://github.com/johannesjo/super-productivity) through its own real
Settings UI to apply a colour computed by our skin engine, and reports what
actually changed. This is the one shelf app in library.json that has moved
from "colours only" to a real, measured integration -- see ../../SKINS.md
and README.md in this directory for how it was measured and what did NOT
work (a naive direct CSS-variable override, kept here as a documented
negative result, not hidden).

Prerequisite: a real build of Super Productivity served somewhere reachable
by Playwright. This script does not build or clone it -- see README.md.

    python3 apply_skin.py <base_url> <hex_color> [tag_name]

Exits 0 and prints a JSON report on success; exits 1 on any mismatch.
"""
import json
import sys

from playwright.sync_api import sync_playwright

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def apply_skin(base_url: str, hex_color: str, tag_name: str = "Front Door Skin",
                headless: bool = True, screenshot_dir: str | None = None) -> dict:
    """Creates a real tag named `tag_name` in a running Super Productivity
    instance at `base_url`, sets its colour to `hex_color` through the app's
    own real native colour input (InputColorPickerComponent), saves, and
    switches into that tag's context -- exactly what a person clicking
    through Settings would do. Returns what was actually observed."""
    report: dict = {"base_url": base_url, "hex_color": hex_color, "errors": []}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM, headless=headless)
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.on("pageerror", lambda e: report["errors"].append(str(e)))
        pg.goto(base_url, timeout=30000)
        pg.wait_for_timeout(1500)

        # First run only: onboarding picker. Subsequent runs (persisted
        # localStorage) land straight in the main view.
        picker = pg.get_by_text("Simple Todo List")
        if picker.count():
            picker.click()
            pg.wait_for_timeout(1200)

        pg.evaluate("""() => {
            const tagsNav = Array.from(document.querySelectorAll('nav-item')).find(e => e.textContent.includes('Tags'));
            const wrap = tagsNav.parentElement;
            const btns = Array.from(wrap.querySelectorAll('.additional-btns button'));
            btns[1].click();
        }""")
        pg.wait_for_timeout(500)
        pg.fill('input[name="title"]', tag_name)

        pg.evaluate("""(hex) => {
            const inp = document.querySelector('.native-color-input');
            inp.value = hex;
            inp.dispatchEvent(new Event('change', { bubbles: true }));
        }""", hex_color)
        pg.wait_for_timeout(200)
        report["swatch_after_dialog"] = pg.evaluate(
            "() => getComputedStyle(document.querySelector('.color-trigger')).backgroundColor"
        )
        if screenshot_dir:
            pg.screenshot(path=f"{screenshot_dir}/dialog.png")

        pg.get_by_text("Save", exact=True).click()
        pg.wait_for_timeout(800)
        pg.get_by_text(tag_name, exact=True).click()
        pg.wait_for_timeout(1200)
        if screenshot_dir:
            pg.screenshot(path=f"{screenshot_dir}/reskinned.png")

        report["brand"] = pg.evaluate(
            "() => getComputedStyle(document.body).getPropertyValue('--brand').trim()"
        )
        report["palette_primary_500"] = pg.evaluate(
            "() => getComputedStyle(document.body).getPropertyValue('--palette-primary-500').trim()"
        )
        b.close()
    return report


if __name__ == "__main__":
    url, hex_color = sys.argv[1], sys.argv[2]
    tag = sys.argv[3] if len(sys.argv) > 3 else "Front Door Skin"
    result = apply_skin(url, hex_color, tag, headless=True)
    print(json.dumps(result, indent=2))
    ok = (not result["errors"]) and result["palette_primary_500"].lower() != ""
    sys.exit(0 if ok else 1)
