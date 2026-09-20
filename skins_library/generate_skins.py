#!/usr/bin/env python3
"""generate_skins.py -- Phase 1 (GENERATE) of the skin generation command.

Reads the real category list and the real existing skin straight off the
working tree (OUTPUT_LIBRARY/<category>/{app.json,skin.json,modules/**}) --
nothing here hardcodes a category name or a color; every category and
every existing style rule is discovered from disk, and the run fails
loudly (never guesses) if an app's CSS doesn't match a known, already-
inspected family.

Writes, per category, SKINS_PER_CATEGORY new skin definitions into
SKIN_LIBRARY_PATH -- a location entirely separate from OUTPUT_LIBRARY.
Nothing here modifies OUTPUT_LIBRARY, NEW_APPS_FROM_LIBRARY, skin-001, or
any app/builder file. Run this before adapt_and_verify.py.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_tokens as dt
import render_css

# ==============================================================================
# RULES BLOCK -- change these, not the logic below
# ==============================================================================

SKINS_PER_CATEGORY = 4
# How many distinct looks to produce for each category. Must equal
# len(design_tokens.THEME_ORDER) -- add/remove a theme there to change this,
# not this number in isolation.

SKIN_LIBRARY_PATH = "skins_library"
# Where generated skins live, relative to the repo root. A separate library
# from the apps -- OUTPUT_LIBRARY and NEW_APPS_FROM_LIBRARY are never
# written to by this script.

SOURCE_DESIGN_SYSTEM = "shadcn/ui"
# The design system used as a REFERENCE ONLY (see design_tokens.py's
# docstring for exactly which tokens were read from it). Not installed as
# a dependency anywhere; changing this value alone does nothing -- it
# documents design_tokens.py's own sourcing, it does not re-derive it.

ADAPT_TO_SYSTEM = True
# Whether this run also writes each skin's "choice fragment" -- the
# {skin_id, skin_version, branding, arrangement} shape the existing
# choice.json -> build.py -> skin.json pipeline already understands with
# zero code changes. Leave true; adapt_and_verify.py depends on it.

FAIL_ON_UNADAPTED = True
# If true, a category whose app CSS doesn't match a known family (see
# render_css.py's FAMILY_RENDERERS) is reported as FAILED and no skin
# files are written for it, rather than emitting a skin that would render
# wrong or not at all.

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_LIBRARY = REPO_ROOT / "OUTPUT_LIBRARY"
LIBRARY_DIR = REPO_ROOT / SKIN_LIBRARY_PATH

# The one existing skin ID/version already on disk for every app today --
# read here only to make sure new IDs never collide with it, never to
# copy or modify it (Phase 1's own standing rule: add alongside).
EXISTING_SKIN_ID = "skin-001"

# ==============================================================================
# END OF RULES BLOCK
# ==============================================================================

# Known style-block fingerprints -> family name, established by actually
# hashing every one of the 43 apps' inline CSS (see the exploration this
# script's own history was built from). A hash that doesn't appear here is
# an app this generator has never inspected -- FAIL_ON_UNADAPTED governs
# what happens to it below; it is never guessed into an existing family.
KNOWN_STYLE_FAMILIES = {
    "8c2e648ace": "shared_card",
    "80c2bb04c5": "todomvc",
}


def style_block_hash(host_app_py: Path) -> str:
    src = host_app_py.read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", src, re.S)
    block = m.group(1) if m else ""
    return hashlib.sha1(block.encode("utf-8")).hexdigest()[:10]


def find_host_app_py(app_dir: Path) -> Path:
    for cap_dir in sorted((app_dir / "modules").iterdir()):
        candidate = cap_dir / "app.py"
        if candidate.is_file() and "INDEX_HTML" in candidate.read_text(encoding="utf-8"):
            return candidate
    raise FileNotFoundError(f"no host app.py (containing INDEX_HTML) found under {app_dir}/modules")


def discover_categories():
    """Returns a dict: slug -> {branding, arrangement, family, host_app_py,
    start, port}. Raises nothing; unrecognized-family apps are included
    with family=None so the caller can report + skip them per
    FAIL_ON_UNADAPTED, rather than this function silently dropping them."""
    categories = {}
    for app_dir in sorted(OUTPUT_LIBRARY.iterdir()):
        if not app_dir.is_dir():
            continue
        slug = app_dir.name
        app_json = json.loads((app_dir / "app.json").read_text(encoding="utf-8"))
        skin_json = json.loads((app_dir / "skin.json").read_text(encoding="utf-8"))
        if skin_json.get("skin_id") != EXISTING_SKIN_ID:
            raise RuntimeError(
                f"{slug}: expected the existing default {EXISTING_SKIN_ID!r} on disk, "
                f"found {skin_json.get('skin_id')!r} -- stopping rather than assuming "
                f"what the current skin means here."
            )
        host = find_host_app_py(app_dir)
        h = style_block_hash(host)
        categories[slug] = {
            "branding": skin_json["branding"],
            "arrangement": skin_json["arrangement"],
            "family": KNOWN_STYLE_FAMILIES.get(h),
            "style_hash": h,
            "host_app_py": str(host.relative_to(app_dir)),
            "start": app_json["start"],
            "port": app_json["port"],
        }
    return categories


def generate():
    assert SKINS_PER_CATEGORY == len(dt.THEME_ORDER), (
        f"SKINS_PER_CATEGORY ({SKINS_PER_CATEGORY}) must equal "
        f"len(design_tokens.THEME_ORDER) ({len(dt.THEME_ORDER)})"
    )
    categories = discover_categories()
    LIBRARY_DIR.mkdir(exist_ok=True)

    results = {}
    for slug, info in sorted(categories.items()):
        if info["family"] is None:
            results[slug] = {
                "status": "FAILED",
                "reason": f"style block hash {info['style_hash']} does not match any known "
                          f"family in render_css.KNOWN_STYLE_FAMILIES -- never guessed",
            }
            continue

        cat_dir = LIBRARY_DIR / slug
        cat_dir.mkdir(exist_ok=True)
        hue = dt.category_hue(slug)
        skins_written = []

        for i, theme in enumerate(dt.THEME_ORDER):
            skin_id = f"skin-{i + 2:03d}"  # skin-001 is the existing default; new ones start at 002
            skin_version = "1.0.0"
            tokens = dt.build_tokens(theme, hue)
            css_text = render_css.render(info["family"], tokens)

            definition = {
                "skin_id": skin_id,
                "skin_version": skin_version,
                "category": slug,
                "theme": theme,
                "label": tokens["label"],
                "source_design_system_reference": SOURCE_DESIGN_SYSTEM,
                "css_family": info["family"],
                "design_tokens": tokens,
                "css_file": f"{skin_id}.css",
            }
            (cat_dir / f"{skin_id}.json").write_text(json.dumps(definition, indent=2), encoding="utf-8")
            (cat_dir / f"{skin_id}.css").write_text(css_text + "\n", encoding="utf-8")

            if ADAPT_TO_SYSTEM:
                # The ONLY shape the existing choice.json -> build.py ->
                # skin.json pipeline understands today (see
                # STAGE_CROSS_REFERENCE.md's stage 6 / build.py's
                # stage1_assemble): skin_id, skin_version, branding
                # {name, color}, arrangement. branding.color here is this
                # skin's primary accent -- the one dimension the existing
                # generator already bakes verbatim into a built app's CSS.
                # arrangement is copied unchanged: this command reskins,
                # it does not redesign layout.
                choice_fragment = {
                    "skin_id": skin_id,
                    "skin_version": skin_version,
                    "branding": {"name": info["branding"]["name"], "color": tokens["primary"]},
                    "arrangement": info["arrangement"],
                }
                (cat_dir / f"{skin_id}.choice_fragment.json").write_text(
                    json.dumps(choice_fragment, indent=2), encoding="utf-8"
                )

            skins_written.append(skin_id)

        results[slug] = {"status": "GENERATED", "skins": skins_written, "family": info["family"]}

    (LIBRARY_DIR / "_index.json").write_text(json.dumps({
        "skins_per_category": SKINS_PER_CATEGORY,
        "source_design_system": SOURCE_DESIGN_SYSTEM,
        "existing_skin_id": EXISTING_SKIN_ID,
        "categories": {slug: {**categories[slug], **{"result": results[slug]}} for slug in categories},
    }, indent=2), encoding="utf-8")

    return results


def main():
    results = generate()
    n_ok = sum(1 for r in results.values() if r["status"] == "GENERATED")
    n_fail = len(results) - n_ok
    for slug, r in sorted(results.items()):
        if r["status"] == "GENERATED":
            print(f"GENERATED  {slug:32s} {', '.join(r['skins'])}  ({r['family']})")
        else:
            print(f"FAILED     {slug:32s} {r['reason']}")
    print(f"\n{n_ok}/{len(results)} categories generated, {n_fail} failed")
    return 0 if (n_fail == 0 or not FAIL_ON_UNADAPTED) else 1


if __name__ == "__main__":
    raise SystemExit(main())
