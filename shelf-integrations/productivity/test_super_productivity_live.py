# test_super_productivity_live.py -- proves the skin engine drives a real,
# separately-built copy of Super Productivity through its own real UI.
#
# Unlike test_frontdoor.py, this test needs a real Super Productivity build
# already running (npm install + ng build, ~90s-3min, plus a ~100MB clone)
# -- too heavy to run on every commit, so it SKIPS (not fails) when
# SP_BASE_URL isn't set or isn't reachable, rather than being wired into the
# main test_frontdoor.py suite. See README.md for how to stand one up.
#
#   git clone --depth 1 https://github.com/johannesjo/super-productivity
#   cd super-productivity && npm install && node tools/load-env.js --ensure
#   npx ng build sp2 --configuration=productionWeb
#   python3 -m http.server 8899 --directory dist/browser &
#   SP_BASE_URL=http://localhost:8899/index.html python3 test_super_productivity_live.py
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "skins_library"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_tokens as dt
from apply_skin import apply_skin

BASE_URL = os.environ.get("SP_BASE_URL", "http://localhost:8899/index.html")

res = []
def check(name, ok, detail=""):
    res.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else " -- " + str(detail)[:300]))


def hex_to_rgb_css(h):
    h = h.lstrip("#")
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


try:
    urllib.request.urlopen(BASE_URL, timeout=3)
except Exception as e:
    print(f"SKIPPED: no live Super Productivity build reachable at {BASE_URL} ({e}). "
          f"This is expected unless you followed README.md to stand one up. Not a failure.")
    sys.exit(0)

# The real colour our engine computes for this exact shelf app (library.json's
# own "productivity" slug) -- not an arbitrary test colour.
tokens = dt.build_tokens("bold_contrast", dt.category_hue("productivity"))
primary = tokens["primary"]

report = apply_skin(BASE_URL, primary, tag_name="Front Door Skin Test")
check("no JS errors while driving the real app", not report["errors"], report["errors"])
check("real colour swatch in the real dialog reflects our engine's colour",
      report["swatch_after_dialog"] == hex_to_rgb_css(primary), report["swatch_after_dialog"])
check("the real app's own --palette-primary-500 was recomputed to our colour",
      report["palette_primary_500"].lower() == hex_to_rgb_css(primary).lower(), report["palette_primary_500"])
check("the real app's own --brand reflects our colour (not left at default)",
      report["brand"] not in ("", "rgb(3, 169, 244)"), report["brand"])

print(f"\n{sum(res)}/{len(res)} passed")
if sum(res) != len(res):
    sys.exit(1)
