/* skins-engine.js
   A byte-exact JS port of skins_library/design_tokens.py + skins_library/render_css.py,
   plus Front-Door-specific logic (withEdits, lookFields, checkEdit, normalizeChanges,
   resolveAsk) that has no Python source to port from -- it implements the behaviour
   described in SKINS.md and is verified by test_frontdoor.py's own assertions, not by
   byte-diffing against a prior implementation.

   Everything under "PORTED FROM PYTHON" must stay line-for-line equivalent to the .py
   files in skins_library/. If you change the math there, change it here too, then rerun
   test_frontdoor.py's engine-parity section (compares this file's output against the
   real design_tokens.py/render_css.py for all 172 measured skins and all 1440 hue x
   theme combinations).
*/
(function (root) {
  "use strict";

  // ============================================================================
  // PORTED FROM PYTHON: colorsys (only the two functions design_tokens.py calls)
  // ============================================================================
  var ONE_THIRD = 1.0 / 3.0, TWO_THIRD = 2.0 / 3.0, ONE_SIXTH = 1.0 / 6.0;

  function _v(m1, m2, hue) {
    hue = pymod(hue, 1.0);
    if (hue < ONE_SIXTH) return m1 + (m2 - m1) * hue * 6.0;
    if (hue < 0.5) return m2;
    if (hue < TWO_THIRD) return m1 + (m2 - m1) * (TWO_THIRD - hue) * 6.0;
    return m1;
  }

  function hlsToRgb(h, l, s) {
    if (s === 0.0) return [l, l, l];
    var m2 = l <= 0.5 ? l * (1.0 + s) : l + s - l * s;
    var m1 = 2.0 * l - m2;
    return [_v(m1, m2, h + ONE_THIRD), _v(m1, m2, h), _v(m1, m2, h - ONE_THIRD)];
  }

  function rgbToHls(r, g, b) {
    var maxc = Math.max(r, g, b), minc = Math.min(r, g, b);
    var sumc = maxc + minc, rangec = maxc - minc, l = sumc / 2.0;
    if (minc === maxc) return [0.0, l, 0.0];
    var s = l <= 0.5 ? rangec / sumc : rangec / (2.0 - sumc);
    var rc = (maxc - r) / rangec, gc = (maxc - g) / rangec, bc = (maxc - b) / rangec;
    var h;
    if (r === maxc) h = bc - gc;
    else if (g === maxc) h = 2.0 + rc - bc;
    else h = 4.0 + gc - rc;
    h = pymod(h / 6.0, 1.0);
    return [h, l, s];
  }

  // ============================================================================
  // PORTED FROM PYTHON: design_tokens.py helpers
  // ============================================================================

  // Python's a % b always has the sign of b; JS's % has the sign of a. Only
  // correct the sign when JS's result actually disagrees -- unconditionally
  // doing ((a % b) + b) % b (a double mod) silently loses a bit of float
  // precision even when a is already correctly signed, which showed up as a
  // real, hard-to-spot bug: hue 210 in Soft Rounded came out #dee5ed instead
  // of Python's #dee6ed (one LSB off in the green channel) because the extra
  // +b/%b round trip perturbed a value that should have rounded to exactly
  // x.5 at the pyRound() step. Verified against Python's % for the full
  // 0-359 hue range in test_frontdoor.py's Section A/B.
  function pymod(a, b) {
    var r = a % b;
    return r < 0 ? r + b : r;
  }

  // Python 3's round(): round-half-to-even ("banker's rounding"), not
  // round-half-up. Exposed as Skins.pyRound and unit-tested against Python's
  // own round() on exact halves.
  function pyRound(x) {
    var f = Math.floor(x);
    var diff = x - f;
    if (diff < 0.5) return f;
    if (diff > 0.5) return f + 1;
    return (pymod(f, 2) === 0) ? f : f + 1;
  }

  function hslToHex(h, s, l) {
    var rgb = hlsToRgb(pymod(h, 360) / 360.0, l, s);
    var r = pyRound(rgb[0] * 255), g = pyRound(rgb[1] * 255), b = pyRound(rgb[2] * 255);
    return "#" + toHex2(r) + toHex2(g) + toHex2(b);
  }

  function toHex2(n) {
    n = Math.max(0, Math.min(255, n));
    var s = n.toString(16);
    return s.length < 2 ? "0" + s : s;
  }

  function hexToRgb(hexcolor) {
    hexcolor = hexcolor.replace(/^#/, "");
    return [
      parseInt(hexcolor.substr(0, 2), 16),
      parseInt(hexcolor.substr(2, 2), 16),
      parseInt(hexcolor.substr(4, 2), 16)
    ];
  }

  function relativeLuminance(hexcolor) {
    function chan(c) {
      c = c / 255.0;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    }
    var rgb = hexToRgb(hexcolor);
    var rl = chan(rgb[0]), gl = chan(rgb[1]), bl = chan(rgb[2]);
    return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl;
  }

  function readableForeground(bgHex, dark, light) {
    dark = dark || "#161616"; light = light || "#ffffff";
    return relativeLuminance(bgHex) > 0.42 ? dark : light;
  }

  function categoryHue(slug) {
    var h = 0;
    for (var i = 0; i < slug.length; i++) {
      h = pymod(h * 131 + slug.charCodeAt(i), 360);
    }
    return h;
  }

  function mixHue(h1, h2, weightH2) {
    var diff = pymod(h2 - h1 + 540, 360) - 180;
    return pymod(h1 + diff * weightH2, 360);
  }

  function shade(hexcolor, delta) {
    var rgb = hexToRgb(hexcolor).map(function (c) { return c / 255.0; });
    var hls = rgbToHls(rgb[0], rgb[1], rgb[2]);
    var h = hls[0], l = hls[1], s = hls[2];
    l = Math.max(0.0, Math.min(1.0, l + delta));
    var rgb2 = hlsToRgb(h, l, s);
    return "#" + toHex2(pyRound(rgb2[0] * 255)) + toHex2(pyRound(rgb2[1] * 255)) + toHex2(pyRound(rgb2[2] * 255));
  }

  var THEME_ORDER = ["minimal_neutral", "bold_contrast", "warm_editorial", "soft_rounded"];

  function buildTokens(theme, hue) {
    if (theme === "minimal_neutral") {
      var primary = hslToHex(hue, 0.35, 0.32);
      return {
        theme: theme, label: "Minimal Neutral",
        background: "#ffffff", surface: "#ffffff", foreground: "#171a1f",
        muted: "#f4f5f6", muted_foreground: "#6b7280", border: "#e2e5e9",
        primary: primary, primary_hover: shade(primary, -0.08), primary_foreground: readableForeground(primary),
        danger: "#af2f2f", secondary_button: "#e9eaec", secondary_button_foreground: "#171a1f",
        radius: "8px", radius_sm: "6px", radius_pill: "8px",
        font_heading: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
        font_body: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
        heading_weight: "600", body_max_width: "700px", card_padding: "24px", card_gap: "16px", row_gap: "8px",
        shadow_card: "0 1px 2px rgba(16,24,40,.06)", shadow_focus_ring: "0 0 0 3px " + primary + "33",
        input_border: "1px solid #d5d8dc", input_padding: "9px 12px", button_padding: "9px 16px", button_font_weight: "500"
      };
    }
    if (theme === "bold_contrast") {
      var primary = hslToHex(hue, 0.82, 0.58);
      var bg = "#0a0a0c", surface = "#151517";
      return {
        theme: theme, label: "Bold Contrast",
        background: bg, surface: surface, foreground: "#f5f5f6",
        muted: "#1f1f22", muted_foreground: "#9a9aa2", border: "#2a2a2f",
        primary: primary, primary_hover: shade(primary, 0.08), primary_foreground: readableForeground(primary),
        danger: "#ff5c5c", secondary_button: "#26262b", secondary_button_foreground: "#f5f5f6",
        radius: "4px", radius_sm: "3px", radius_pill: "4px",
        font_heading: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
        font_body: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif",
        heading_weight: "700", body_max_width: "700px", card_padding: "20px", card_gap: "14px", row_gap: "8px",
        shadow_card: "0 4px 18px " + primary + "26", shadow_focus_ring: "0 0 0 3px " + primary + "55",
        input_border: "1px solid #35353b", input_padding: "9px 12px", button_padding: "9px 16px", button_font_weight: "600"
      };
    }
    if (theme === "warm_editorial") {
      var warmHue = mixHue(hue, 20.0, 0.6);
      var primary = hslToHex(warmHue, 0.55, 0.42);
      return {
        theme: theme, label: "Warm Editorial",
        background: "#faf6ef", surface: "#ffffff", foreground: "#2a211a",
        muted: "#f1eadc", muted_foreground: "#7a6a58", border: "#e6dcc9",
        primary: primary, primary_hover: shade(primary, -0.08), primary_foreground: readableForeground(primary),
        danger: "#a4402c", secondary_button: "#efe6d6", secondary_button_foreground: "#2a211a",
        radius: "12px", radius_sm: "8px", radius_pill: "12px",
        font_heading: "Georgia, 'Times New Roman', 'Iowan Old Style', serif",
        font_body: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
        heading_weight: "700", body_max_width: "720px", card_padding: "32px", card_gap: "20px", row_gap: "10px",
        shadow_card: "0 10px 28px rgba(120,86,40,.10)", shadow_focus_ring: "0 0 0 3px " + primary + "2e",
        input_border: "1px solid #ddcfb4", input_padding: "10px 14px", button_padding: "10px 18px", button_font_weight: "600"
      };
    }
    if (theme === "soft_rounded") {
      var primary = hslToHex(hue, 0.60, 0.60);
      var bg = hslToHex(hue, 0.45, 0.965);
      return {
        theme: theme, label: "Soft Rounded",
        background: bg, surface: "#ffffff", foreground: hslToHex(hue, 0.30, 0.20),
        muted: hslToHex(hue, 0.35, 0.93), muted_foreground: hslToHex(hue, 0.15, 0.42), border: hslToHex(hue, 0.35, 0.88),
        primary: primary, primary_hover: shade(primary, -0.08), primary_foreground: readableForeground(primary),
        danger: "#d1477a", secondary_button: hslToHex(hue, 0.30, 0.90), secondary_button_foreground: hslToHex(hue, 0.30, 0.20),
        radius: "20px", radius_sm: "14px", radius_pill: "999px",
        font_heading: "'Segoe UI Rounded', Nunito, -apple-system, BlinkMacSystemFont, sans-serif",
        font_body: "'Segoe UI Rounded', Nunito, -apple-system, BlinkMacSystemFont, sans-serif",
        heading_weight: "700", body_max_width: "720px", card_padding: "28px", card_gap: "18px", row_gap: "12px",
        shadow_card: "0 10px 30px rgba(30,20,50,.07)", shadow_focus_ring: "0 0 0 4px " + primary + "33",
        input_border: "1px solid " + hslToHex(hue, 0.35, 0.82), input_padding: "10px 16px", button_padding: "10px 20px", button_font_weight: "700"
      };
    }
    throw new Error("unknown theme " + JSON.stringify(theme) + " -- add it to THEME_ORDER and buildTokens(), never guess its tokens");
  }

  // ============================================================================
  // PORTED FROM PYTHON: render_css.py (two families measured across 43 real apps)
  // ============================================================================

  function renderSharedCard(t) {
    return [
      "body { font-family: " + t.font_body + "; max-width: " + t.body_max_width + "; margin: 40px auto;",
      "  color: " + t.foreground + "; background: " + t.background + "; }",
      ".card { background: " + t.surface + "; box-shadow: " + t.shadow_card + "; border: 1px solid " + t.border + ";",
      "  border-radius: " + t.radius + "; padding: " + t.card_padding + "; margin-bottom: " + t.card_gap + "; }",
      "h1 { font-family: " + t.font_heading + "; font-weight: " + t.heading_weight + "; font-size: 22px;",
      "  color: " + t.foreground + "; }",
      "input, select, textarea { font-family: " + t.font_body + "; font-size: 15px; padding: " + t.input_padding + ";",
      "  border: " + t.input_border + "; border-radius: " + t.radius_sm + "; box-sizing: border-box;",
      "  background: " + t.surface + "; color: " + t.foreground + "; }",
      "input:focus, select:focus, textarea:focus { outline: none; border-color: " + t.primary + ";",
      "  box-shadow: " + t.shadow_focus_ring + "; }",
      "button { font-family: " + t.font_body + "; font-size: 14px; font-weight: " + t.button_font_weight + ";",
      "  padding: " + t.button_padding + "; border: none; border-radius: " + t.radius_pill + ";",
      "  background: " + t.primary + "; color: " + t.primary_foreground + "; cursor: pointer;",
      "  transition: background-color .12s ease; }",
      "button:hover { background: " + t.primary_hover + "; }",
      "button:focus-visible { outline: none; box-shadow: " + t.shadow_focus_ring + "; }",
      "button.danger { background: " + t.danger + "; color: #ffffff; }",
      "button.secondary { background: " + t.secondary_button + "; color: " + t.secondary_button_foreground + "; }",
      "ul { list-style: none; margin: 0; padding: 0; }",
      "li { border-bottom: 1px solid " + t.border + "; padding: 10px 4px; color: " + t.foreground + "; }",
      ".row { display: flex; gap: " + t.row_gap + "; align-items: center; flex-wrap: wrap; }"
    ].join("\n");
  }

  function renderTodomvc(t) {
    return [
      "body { font-family: " + t.font_body + "; max-width: 550px; margin: 40px auto;",
      "  color: " + t.foreground + "; background: " + t.background + "; }",
      ".todoapp { background: " + t.surface + "; box-shadow: " + t.shadow_card + "; border: 1px solid " + t.border + ";",
      "  border-radius: " + t.radius + "; }",
      ".header input#new-todo { width: 100%; box-sizing: border-box; font-family: " + t.font_body + ";",
      "  font-size: 20px; padding: 12px; border: none; border-bottom: 1px solid " + t.border + ";",
      "  background: " + t.surface + "; color: " + t.foreground + "; }",
      ".header input#new-todo:focus { outline: none; box-shadow: inset " + t.shadow_focus_ring + "; }",
      "ul#todo-list { list-style: none; margin: 0; padding: 0; }",
      "ul#todo-list li { position: relative; border-bottom: 1px solid " + t.border + ";",
      "  padding: 12px 12px 12px 40px; color: " + t.foreground + "; }",
      "ul#todo-list li .toggle { position: absolute; left: 10px; top: 14px; accent-color: " + t.primary + "; }",
      "ul#todo-list li label { margin-left: 6px; }",
      "ul#todo-list li.completed label { text-decoration: line-through; color: " + t.muted_foreground + "; }",
      "ul#todo-list li .destroy { display: none; float: right; cursor: pointer; border: none; background: none;",
      "  color: " + t.danger + "; }",
      "ul#todo-list li:hover .destroy { display: inline; }",
      "ul#todo-list li .edit { display: none; width: 90%; font-size: 16px; }",
      "ul#todo-list li.editing .edit { display: inline; }",
      "ul#todo-list li.editing .view { display: none; }",
      ".footer { padding: 10px 15px; display: flex; justify-content: space-between; align-items: center;",
      "  color: " + t.muted_foreground + "; }",
      ".footer .filters { list-style: none; display: inline-flex; gap: 8px; margin: 0; padding: 0; }",
      ".footer .filters a { text-decoration: none; color: " + t.muted_foreground + "; padding: 2px 6px;",
      "  border: 1px solid transparent; border-radius: " + t.radius_sm + "; }",
      ".footer .filters a.selected { border-color: " + t.primary + "55; }",
      "#clear-completed { border: none; background: none; cursor: pointer; color: " + t.muted_foreground + "; }"
    ].join("\n");
  }

  var FAMILY_RENDERERS = { shared_card: renderSharedCard, todomvc: renderTodomvc };

  function render(family, tok) {
    var fn = FAMILY_RENDERERS[family];
    if (!fn) throw new Error("no CSS renderer registered for family " + JSON.stringify(family) + " -- known families: " + Object.keys(FAMILY_RENDERERS).sort().join(", ") + ". Never guess; add one.");
    return fn(tok);
  }

  // ============================================================================
  // FRONT-DOOR LOGIC (no Python source -- new for this app, spec'd by SKINS.md
  // and pinned down by test_frontdoor.py's explicit assertions)
  // ============================================================================

  var ALLOWED_FONTS = [
    "", "Instrument Sans", "Inter", "Georgia", "Nunito", "Segoe UI Rounded",
    "Roboto", "Merriweather", "Playfair Display", "Source Sans Pro"
  ];

  var KNOWN_COLOR_NAMES = {
    navy: "#1F3A5F", red: "#B42318", green: "#2F7D4F", blue: "#2563EB",
    purple: "#6D28D9", orange: "#C2410C", pink: "#DB2777", teal: "#0F766E",
    black: "#161616", charcoal: "#1D1D1B"
  };

  // A "skin" record's editable fields, derived from one look at one hue --
  // designed so that choosing a look with zero further edits reproduces the
  // look's own build_tokens() output exactly once passed through withEdits.
  function lookFields(theme, hue) {
    var t = buildTokens(theme, hue);
    return {
      look: theme,
      accent: t.primary,
      background: t.background,
      surface: t.surface,
      text: t.foreground,
      font: "",              // "" = use the look's own font, never overridden
      radius: parseInt(t.radius, 10)
    };
  }

  var HEX_RE = /^#[0-9a-fA-F]{6}$/;

  // Layers a skin's edits (accent/background/surface/text/font/radius) on top
  // of that look's pure computed tokens. A field left at its look-default value
  // (as produced by lookFields) never marks the result as edited.
  function withEdits(tokens, skin) {
    var base = lookFields(tokens.theme, categoryHueOfTokens(tokens));
    var out = {};
    for (var k in tokens) out[k] = tokens[k];

    if (skin.accent && HEX_RE.test(skin.accent) && skin.accent.toLowerCase() !== base.accent.toLowerCase()) {
      var primary = skin.accent.toLowerCase();
      out.primary = primary;
      out.primary_hover = shade(primary, tokens.theme === "bold_contrast" ? 0.08 : -0.08);
      out.primary_foreground = readableForeground(primary);
      out.shadow_focus_ring = out.shadow_focus_ring.replace(/#[0-9a-fA-F]{6}/, primary);
      out.shadow_card = out.shadow_card.replace(/#[0-9a-fA-F]{6}/, primary);
    }
    if (skin.background && HEX_RE.test(skin.background) && skin.background.toLowerCase() !== base.background.toLowerCase()) {
      out.background = skin.background.toLowerCase();
    }
    if (skin.surface && HEX_RE.test(skin.surface) && skin.surface.toLowerCase() !== base.surface.toLowerCase()) {
      out.surface = skin.surface.toLowerCase();
    }
    if (skin.text && HEX_RE.test(skin.text) && skin.text.toLowerCase() !== base.text.toLowerCase()) {
      out.foreground = skin.text.toLowerCase();
    }
    if (skin.font && skin.font !== base.font) {
      out.font_heading = skin.font + ", " + tokens.font_heading;
      out.font_body = skin.font + ", " + tokens.font_body;
    }
    if (typeof skin.radius === "number" && skin.radius !== base.radius) {
      var baseRadius = parseFloat(tokens.radius);
      var baseSm = parseFloat(tokens.radius_sm);
      var ratio = baseRadius === 0 ? 1 : baseSm / baseRadius;
      out.radius = skin.radius + "px";
      out.radius_sm = Math.round(skin.radius * ratio) + "px";
      // A look whose pill radius already equals its own radius scales with it;
      // a look whose pill radius is the fixed "999px" (soft_rounded) always stays a pill.
      out.radius_pill = (tokens.radius_pill === "999px") ? "999px" : (skin.radius + "px");
    }
    return out;
  }

  // build_tokens()'s output carries no hue field, so withEdits needs the hue
  // it was built from to compute the look's own defaults for comparison. We
  // recover it losslessly: every theme's `primary` (or, for soft_rounded, also
  // `background`) is a pure function of hue, so we invert hslToHex numerically
  // is unnecessary -- callers that build tokens always know their own hue, so
  // withEdits takes it from the caller-tagged `_hue` field build() attaches.
  function categoryHueOfTokens(tokens) {
    if (typeof tokens._hue === "number") return tokens._hue;
    throw new Error("withEdits requires tokens produced by Skins.build(), which tags _hue");
  }

  function build(theme, hue) {
    var t = buildTokens(theme, hue);
    t._hue = hue;
    return t;
  }

  var KNOWN_THEMES = THEME_ORDER.slice();

  // Validates a proposed list of {key, value, say} changes. Returns an array
  // of problem strings; empty means every change is acceptable as-is.
  function checkEdit(proposal) {
    var problems = [];
    (proposal.changes || []).forEach(function (c) {
      if (c.key === "look") {
        if (KNOWN_THEMES.indexOf(c.value) === -1 && c.value !== "original") {
          problems.push("unknown look " + JSON.stringify(c.value));
        }
      } else if (c.key === "font") {
        if (ALLOWED_FONTS.indexOf(c.value) === -1) {
          problems.push("font " + JSON.stringify(c.value) + " is not in the allowed list");
        }
      } else if (c.key === "accent" || c.key === "background" || c.key === "surface" || c.key === "text") {
        if (!HEX_RE.test(c.value)) problems.push(c.key + " must be a 6-digit hex color");
      } else if (c.key === "radius") {
        if (typeof c.value !== "number" || c.value < 0 || c.value > 40) problems.push("radius out of range");
      } else {
        problems.push("unknown change key " + JSON.stringify(c.key));
      }
    });
    return problems;
  }

  // If any non-"look" change is requested while the current look is "original",
  // insert a visible step that switches to Minimal Neutral first -- colour/font/
  // radius edits are never applied silently on top of the app's own untouched look.
  function normalizeChanges(changes, currentLook) {
    currentLook = currentLook || "original";
    var hasLookChange = changes.some(function (c) { return c.key === "look"; });
    var hasOtherChange = changes.some(function (c) { return c.key !== "look"; });
    if (currentLook === "original" && hasOtherChange && !hasLookChange) {
      return [{ key: "look", value: "minimal_neutral", say: "Switches to Minimal Neutral so there's a look to edit." }].concat(changes);
    }
    return changes;
  }

  // Free-text -> {look, accent, radius, font} guess, used by the "or just say
  // it" affordance ("make it dark", "more classic"). Deliberately a small,
  // deterministic, fully-tested keyword table -- not a call to an external
  // model -- so behaviour is reproducible offline and in CI. Documented as
  // such in SKINS.md; swap this function for a real model call if/when one
  // is wired up, without changing anything else that depends on it.
  var LOOK_KEYWORDS = [
    [/dark|night|moody|black/i, "bold_contrast"],
    [/classic|serif|editorial|warm|vintage|paper/i, "warm_editorial"],
    [/round|soft|friendly|pastel|pill|playful/i, "soft_rounded"],
    [/minimal|clean|plain|neutral|simple|default/i, "minimal_neutral"],
    [/original|reset|untouched|as.is/i, "original"]
  ];

  function parseAsk(text) {
    var changes = [];
    for (var i = 0; i < LOOK_KEYWORDS.length; i++) {
      if (LOOK_KEYWORDS[i][0].test(text)) { changes.push({ key: "look", value: LOOK_KEYWORDS[i][1], say: "Switches the look to match “" + text + "”." }); break; }
    }
    var hexMatch = text.match(/#[0-9a-fA-F]{6}/);
    if (hexMatch) {
      changes.push({ key: "accent", value: hexMatch[0].toLowerCase(), say: "Sets the accent colour to " + hexMatch[0] + "." });
    } else {
      for (var name in KNOWN_COLOR_NAMES) {
        if (new RegExp("\\b" + name + "\\b", "i").test(text)) {
          changes.push({ key: "accent", value: KNOWN_COLOR_NAMES[name], say: "Sets the accent colour to " + name + "." });
          break;
        }
      }
    }
    return changes;
  }

  // ---- Shelf resolution: free text -> best-matching real app in the library ----
  var STOPWORDS = { i: 1, want: 1, need: 1, to: 1, a: 1, an: 1, the: 1, for: 1, my: 1, me: 1, some: 1, with: 1, of: 1, and: 1 };

  function tokenize(text) {
    return (text.toLowerCase().match(/[a-z0-9]+/g) || []).filter(function (w) { return !STOPWORDS[w]; });
  }

  function scoreApp(app, askWords, askText) {
    var score = 0;
    var haystacks = [app.name, app.category].concat(app.keywords || []);
    haystacks.forEach(function (h) {
      if (askText.indexOf(h.toLowerCase()) !== -1) score += 5;
    });
    askWords.forEach(function (w) {
      haystacks.forEach(function (h) {
        if (h.toLowerCase().split(/[^a-z0-9]+/).indexOf(w) !== -1) score += 2;
      });
    });
    return score;
  }

  // Returns the best-matching app object from `library` (an array, as in
  // library.json's `apps`), or null if nothing scores above zero -- resolveAsk
  // never guesses a match when the request doesn't actually name anything in
  // the catalog.
  function resolveAsk(text, library) {
    var askText = text.toLowerCase();
    var askWords = tokenize(text);
    var best = null, bestScore = 0;
    library.forEach(function (app) {
      var s = scoreApp(app, askWords, askText);
      if (s > bestScore) { bestScore = s; best = app; }
    });
    return best;
  }

  var Skins = {
    THEME_ORDER: THEME_ORDER,
    ALLOWED_FONTS: ALLOWED_FONTS,
    pyRound: pyRound,
    hue: categoryHue,
    hslToHex: hslToHex,
    build: build,
    render: render,
    lookFields: lookFields,
    withEdits: withEdits,
    checkEdit: checkEdit,
    normalizeChanges: normalizeChanges,
    parseAsk: parseAsk,
    resolveAsk: resolveAsk,
    _internal: { hexToRgb: hexToRgb, relativeLuminance: relativeLuminance, readableForeground: readableForeground, shade: shade, mixHue: mixHue }
  };

  if (typeof module !== "undefined" && module.exports) module.exports = Skins;
  else root.Skins = Skins;
})(typeof window !== "undefined" ? window : this);
