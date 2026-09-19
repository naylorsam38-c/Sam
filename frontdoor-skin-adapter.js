/* frontdoor-skin-adapter.js
   Put one <script src="frontdoor-skin-adapter.js"></script> at the end of a shelf app's page.
   It listens for the Front Door's skin message and dresses the page in it. It never touches the
   app's own code or data: it only adds (or removes) one <style> tag, one font link and a set of
   CSS variables on <html>. Remove the script and the app is exactly as it was.

   ═══════════════════════════════════════════════════════════════════════
   RULES — edit these. One comment per setting.
   ═══════════════════════════════════════════════════════════════════════ */
var FRONTDOOR_SKIN_RULES = {
  // Where the Front Door runs. Messages from anywhere else are ignored and logged with their origin,
  // so if the skin doesn't arrive, the browser console tells you the exact value to paste here.
  ALLOWED_ORIGINS: [],
  // Must match SKIN_MESSAGE_TYPE in the Front Door's RULES block.
  MESSAGE_TYPE: "frontdoor.skin",
  // Id of the style tag this adapter owns. Change only if the app already uses this id.
  STYLE_ID: "frontdoor-skin",
  // Largest stylesheet accepted, in characters. Anything bigger is refused, not trimmed.
  MAX_CSS_LENGTH: 20000,
  // Prefix for the CSS variables set on <html> (e.g. --fd-primary). Lets an app's own CSS use the colours later.
  VAR_PREFIX: "--fd-"
};
/* ═══════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";
  var R = FRONTDOOR_SKIN_RULES;
  var FONT_ID = R.STYLE_ID + "-font";
  var HEX = /^#[0-9a-fA-F]{6}$/;
  var set = [];                                   // variables this adapter set, so it can clear them

  function clear() {
    var s = document.getElementById(R.STYLE_ID); if (s) s.remove();
    var f = document.getElementById(FONT_ID); if (f) f.remove();
    set.forEach(function (n) { document.documentElement.style.removeProperty(n); });
    set = [];
  }

  function fail(why) { console.warn("Front Door skin adapter: " + why); }

  function apply(m) {
    // "original": no tokens — take everything off, the app shows its own look.
    if (m.tokens === null) { clear(); return; }
    if (!m.tokens || typeof m.tokens !== "object") return fail("message had no tokens — ignored.");
    if (m.css !== null && typeof m.css !== "string") return fail("css must be text or null — ignored.");
    if (m.css && m.css.length > R.MAX_CSS_LENGTH) return fail("css longer than MAX_CSS_LENGTH — refused.");
    if (m.css && /<\/?style|@import|url\s*\(/i.test(m.css)) return fail("css contained a tag, @import or url() — refused.");
    if (m.font_url && !/^https:\/\/fonts\.googleapis\.com\/css2\?/.test(m.font_url)) return fail("font_url is not a Google Fonts address — refused.");

    clear();
    // Variables: every token, so the app's own CSS can pick them up by name.
    Object.keys(m.tokens).forEach(function (k) {
      var v = m.tokens[k];
      if (typeof v !== "string" || /[;{}<>]/.test(v)) return;       // plain values only
      var n = R.VAR_PREFIX + k.replace(/_/g, "-");
      document.documentElement.style.setProperty(n, v); set.push(n);
    });
    if (m.font_url) {
      var l = document.createElement("link"); l.id = FONT_ID; l.rel = "stylesheet"; l.href = m.font_url;
      document.head.appendChild(l);
    }
    // The full stylesheet only arrives when the Front Door knows this app's markup family.
    if (m.css) {
      var s = document.createElement("style"); s.id = R.STYLE_ID; s.textContent = m.css;
      document.head.appendChild(s);                                  // last in <head>, so it wins ties
    }
    if (m.tokens.primary && !HEX.test(m.tokens.primary)) fail("primary is not a 6-digit hex; variables set as sent.");
  }

  window.addEventListener("message", function (e) {
    var m = e.data;
    if (!m || m.type !== R.MESSAGE_TYPE) return;                     // not ours
    if (R.ALLOWED_ORIGINS.indexOf(e.origin) === -1) {
      return fail("ignored a skin from " + e.origin + " — add it to ALLOWED_ORIGINS if that is your Front Door.");
    }
    apply(m);
  });
})();
