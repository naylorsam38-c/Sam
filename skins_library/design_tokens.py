#!/usr/bin/env python3
"""design_tokens.py -- four real, distinct design systems, each built by
reading shadcn/ui's actual token architecture (background/foreground/
primary/primary-foreground/muted/border/radius, a 4px spacing base, a
type scale, and interactive states) and rebuilding it as plain CSS custom
properties -- no shadcn/ui dependency is installed anywhere; nothing here
imports or ships their code. Each theme parameterizes one thing per
category: an accent hue (0-359), so every one of the 43 canonical app
types gets its own accent within each of the 4 looks, while the four
looks themselves stay structurally distinct from one another (radius,
background, typography, shadow language, and state behaviour all differ).

This file has no import-time side effects and touches no app or builder
file -- it only computes token dictionaries consumed by render_css.py.
"""
import colorsys
from typing import Dict


# ==============================================================================
# RULES BLOCK -- change these, not the logic below
# ==============================================================================

# The four base looks every category is rendered in. Order is fixed: skin
# IDs are assigned in this order (skin-002 = THEMES[0], etc.), continuing
# the existing "skin-001" numbering already on disk -- skin-001 is never
# reassigned or touched. Add a fifth entry here (and bump SKINS_PER_CATEGORY
# in generate_skins.py to match) to add a fifth look to every category;
# removing an entry drops that look everywhere.
THEME_ORDER = ["minimal_neutral", "bold_contrast", "warm_editorial", "soft_rounded"]

# ==============================================================================
# END OF RULES BLOCK
# ==============================================================================


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """h in [0,360), s and l in [0,1]. Standard HSL->RGB->hex, no guessing."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def hex_to_rgb(hexcolor: str):
    hexcolor = hexcolor.lstrip("#")
    return tuple(int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(hexcolor: str) -> float:
    """WCAG relative luminance, used to pick a readable foreground for a
    given accent instead of guessing black-or-white."""
    def chan(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = hex_to_rgb(hexcolor)
    rl, gl, bl = chan(r), chan(g), chan(b)
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl


def readable_foreground(bg_hex: str, dark="#161616", light="#ffffff") -> str:
    return dark if relative_luminance(bg_hex) > 0.42 else light


def category_hue(slug: str) -> float:
    """Deterministic hue per category (0-359), derived from the category's
    own slug -- so re-running generation reproduces byte-identical colors,
    and no two runs of this function ever silently drift or need a stored
    random seed. Not cryptographic; just a stable, even spread."""
    h = 0
    for ch in slug:
        h = (h * 131 + ord(ch)) % 360
    return float(h)


def _mix_hue(h1: float, h2: float, weight_h2: float) -> float:
    """Circular hue mix (shortest arc), used to pull a theme's accent
    toward a characteristic hue family (e.g. warm terracotta) without
    fully discarding the category's own identity."""
    diff = ((h2 - h1 + 540) % 360) - 180
    return (h1 + diff * weight_h2) % 360


def _shade(hexcolor: str, delta: float) -> str:
    """Lighten (delta>0) or darken (delta<0) a hex color by delta in
    [-1,1] of lightness, preserving hue/saturation -- used for real
    hover/active states instead of a flat opacity hack."""
    r, g, b = (c / 255.0 for c in hex_to_rgb(hexcolor))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l + delta))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(round(r2 * 255), round(g2 * 255), round(b2 * 255))


def build_tokens(theme: str, hue: float) -> Dict:
    """Returns one theme's full token set for a given category accent hue.
    Every field is consumed by render_css.py -- add a field here and a
    matching CSS rule there, never invent a field render_css.py ignores."""
    if theme == "minimal_neutral":
        # shadcn/ui "New York" light style: near-white surfaces, a border
        # rather than a shadow to separate cards, a restrained, desaturated
        # primary, 0.5rem radius, system sans stack, 4px spacing base.
        primary = hsl_to_hex(hue, 0.35, 0.32)
        return {
            "theme": theme,
            "label": "Minimal Neutral",
            "background": "#ffffff",
            "surface": "#ffffff",
            "foreground": "#171a1f",
            "muted": "#f4f5f6",
            "muted_foreground": "#6b7280",
            "border": "#e2e5e9",
            "primary": primary,
            "primary_hover": _shade(primary, -0.08),
            "primary_foreground": readable_foreground(primary),
            "danger": "#af2f2f",
            "secondary_button": "#e9eaec",
            "secondary_button_foreground": "#171a1f",
            "radius": "8px",
            "radius_sm": "6px",
            "radius_pill": "8px",
            "font_heading": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
            "font_body": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
            "heading_weight": "600",
            "body_max_width": "700px",
            "card_padding": "24px",
            "card_gap": "16px",
            "row_gap": "8px",
            "shadow_card": "0 1px 2px rgba(16,24,40,.06)",
            "shadow_focus_ring": f"0 0 0 3px {primary}33",
            "input_border": "1px solid #d5d8dc",
            "input_padding": "9px 12px",
            "button_padding": "9px 16px",
            "button_font_weight": "500",
        }

    if theme == "bold_contrast":
        # shadcn/ui dark style: near-black background, a vivid saturated
        # accent that has to carry all the contrast itself, sharper 0.25rem
        # radius, heavier headings, a colored glow shadow instead of a
        # neutral one.
        primary = hsl_to_hex(hue, 0.82, 0.58)
        bg = "#0a0a0c"
        surface = "#151517"
        return {
            "theme": theme,
            "label": "Bold Contrast",
            "background": bg,
            "surface": surface,
            "foreground": "#f5f5f6",
            "muted": "#1f1f22",
            "muted_foreground": "#9a9aa2",
            "border": "#2a2a2f",
            "primary": primary,
            "primary_hover": _shade(primary, 0.08),
            "primary_foreground": readable_foreground(primary),
            "danger": "#ff5c5c",
            "secondary_button": "#26262b",
            "secondary_button_foreground": "#f5f5f6",
            "radius": "4px",
            "radius_sm": "3px",
            "radius_pill": "4px",
            "font_heading": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
            "font_body": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
            "heading_weight": "700",
            "body_max_width": "700px",
            "card_padding": "20px",
            "card_gap": "14px",
            "row_gap": "8px",
            "shadow_card": f"0 4px 18px {primary}26",
            "shadow_focus_ring": f"0 0 0 3px {primary}55",
            "input_border": "1px solid #35353b",
            "input_padding": "9px 12px",
            "button_padding": "9px 16px",
            "button_font_weight": "600",
        }

    if theme == "warm_editorial":
        # A warm, content-forward look: creamy paper background, serif
        # display headings over a sans body (a real typographic hierarchy,
        # not just a color swap), a larger 0.75rem radius, generous
        # spacing, and the accent pulled toward terracotta regardless of
        # the category's own hue, so the family reads as one warm palette.
        warm_hue = _mix_hue(hue, 20.0, 0.6)
        primary = hsl_to_hex(warm_hue, 0.55, 0.42)
        return {
            "theme": theme,
            "label": "Warm Editorial",
            "background": "#faf6ef",
            "surface": "#ffffff",
            "foreground": "#2a211a",
            "muted": "#f1eadc",
            "muted_foreground": "#7a6a58",
            "border": "#e6dcc9",
            "primary": primary,
            "primary_hover": _shade(primary, -0.08),
            "primary_foreground": readable_foreground(primary),
            "danger": "#a4402c",
            "secondary_button": "#efe6d6",
            "secondary_button_foreground": "#2a211a",
            "radius": "12px",
            "radius_sm": "8px",
            "radius_pill": "12px",
            "font_heading": "Georgia, 'Times New Roman', 'Iowan Old Style', serif",
            "font_body": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
            "heading_weight": "700",
            "body_max_width": "720px",
            "card_padding": "32px",
            "card_gap": "20px",
            "row_gap": "10px",
            "shadow_card": "0 10px 28px rgba(120,86,40,.10)",
            "shadow_focus_ring": f"0 0 0 3px {primary}2e",
            "input_border": "1px solid #ddcfb4",
            "input_padding": "10px 14px",
            "button_padding": "10px 18px",
            "button_font_weight": "600",
        }

    if theme == "soft_rounded":
        # A pastel, consumer-friendly look: a background lightly tinted
        # with the category's own hue, pill-shaped buttons (radius so
        # large it always reads as a pill regardless of button height),
        # airy spacing, diffuse soft shadows.
        primary = hsl_to_hex(hue, 0.60, 0.60)
        bg = hsl_to_hex(hue, 0.45, 0.965)
        return {
            "theme": theme,
            "label": "Soft Rounded",
            "background": bg,
            "surface": "#ffffff",
            "foreground": hsl_to_hex(hue, 0.30, 0.20),
            "muted": hsl_to_hex(hue, 0.35, 0.93),
            "muted_foreground": hsl_to_hex(hue, 0.15, 0.42),
            "border": hsl_to_hex(hue, 0.35, 0.88),
            "primary": primary,
            "primary_hover": _shade(primary, -0.08),
            "primary_foreground": readable_foreground(primary),
            "danger": "#d1477a",
            "secondary_button": hsl_to_hex(hue, 0.30, 0.90),
            "secondary_button_foreground": hsl_to_hex(hue, 0.30, 0.20),
            "radius": "20px",
            "radius_sm": "14px",
            "radius_pill": "999px",
            "font_heading": "'Segoe UI Rounded', Nunito, -apple-system, BlinkMacSystemFont, sans-serif",
            "font_body": "'Segoe UI Rounded', Nunito, -apple-system, BlinkMacSystemFont, sans-serif",
            "heading_weight": "700",
            "body_max_width": "720px",
            "card_padding": "28px",
            "card_gap": "18px",
            "row_gap": "12px",
            "shadow_card": "0 10px 30px rgba(30,20,50,.07)",
            "shadow_focus_ring": f"0 0 0 4px {primary}33",
            "input_border": f"1px solid {hsl_to_hex(hue, 0.35, 0.82)}",
            "input_padding": "10px 16px",
            "button_padding": "10px 20px",
            "button_font_weight": "700",
        }

    raise ValueError(f"unknown theme {theme!r} -- add it to THEME_ORDER and build_tokens(), never guess its tokens")
