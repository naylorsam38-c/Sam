/* Test fixture copy of ../frontdoor-skin-adapter.js, differing ONLY in
   ALLOWED_ORIGINS -- filled in exactly as SKINS.md instructs a real
   integrator to do, pointed at the test harness's own origin
   (http://localhost:8766, see test_frontdoor.py). The shipped adapter at
   the repo root is never modified; this file exists purely so the adapter
   proof can run against a genuinely different origin (this fixture serves
   from :8767) instead of faking it. Keep this in sync with the real
   adapter's logic -- only the RULES block below should ever differ. */
var FRONTDOOR_SKIN_RULES = {
  ALLOWED_ORIGINS: ["http://localhost:8766"],
  MESSAGE_TYPE: "frontdoor.skin",
  STYLE_ID: "frontdoor-skin",
  MAX_CSS_LENGTH: 20000,
  VAR_PREFIX: "--fd-"
};

(function () {
  "use strict";
  var R = FRONTDOOR_SKIN_RULES;
  var FONT_ID = R.STYLE_ID + "-font";
  var HEX = /^#[0-9a-fA-F]{6}$/;
  var set = [];

  function clear() {
    var s = document.getElementById(R.STYLE_ID); if (s) s.remove();
    var f = document.getElementById(FONT_ID); if (f) f.remove();
    set.forEach(function (n) { document.documentElement.style.removeProperty(n); });
    set = [];
  }

  function fail(why) { console.warn("Front Door skin adapter: " + why); }

  function apply(m) {
    if (m.tokens === null) { clear(); return; }
    if (!m.tokens || typeof m.tokens !== "object") return fail("message had no tokens — ignored.");
    if (m.css !== null && typeof m.css !== "string") return fail("css must be text or null — ignored.");
    if (m.css && m.css.length > R.MAX_CSS_LENGTH) return fail("css longer than MAX_CSS_LENGTH — refused.");
    if (m.css && /<\/?style|@import|url\s*\(/i.test(m.css)) return fail("css contained a tag, @import or url() — refused.");
    if (m.font_url && !/^https:\/\/fonts\.googleapis\.com\/css2\?/.test(m.font_url)) return fail("font_url is not a Google Fonts address — refused.");

    clear();
    Object.keys(m.tokens).forEach(function (k) {
      var v = m.tokens[k];
      if (typeof v !== "string" || /[;{}<>]/.test(v)) return;
      var n = R.VAR_PREFIX + k.replace(/_/g, "-");
      document.documentElement.style.setProperty(n, v); set.push(n);
    });
    if (m.font_url) {
      var l = document.createElement("link"); l.id = FONT_ID; l.rel = "stylesheet"; l.href = m.font_url;
      document.head.appendChild(l);
    }
    if (m.css) {
      var s = document.createElement("style"); s.id = R.STYLE_ID; s.textContent = m.css;
      document.head.appendChild(s);
    }
    if (m.tokens.primary && !HEX.test(m.tokens.primary)) fail("primary is not a 6-digit hex; variables set as sent.");
  }

  window.addEventListener("message", function (e) {
    var m = e.data;
    if (!m || m.type !== R.MESSAGE_TYPE) return;
    if (R.ALLOWED_ORIGINS.indexOf(e.origin) === -1) {
      return fail("ignored a skin from " + e.origin + " — add it to ALLOWED_ORIGINS if that is your Front Door.");
    }
    apply(m);
  });
})();
