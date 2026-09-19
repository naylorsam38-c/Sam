/* shelf-ui.js -- the fab/sheet/look-picker/undo-log mechanics, shared between
   front-door.html (applies skins to a same-origin #slot via direct DOM) and
   _test_with_library.html (applies skins to a cross-origin iframe via
   frontdoor-skin-adapter.js's postMessage contract). Written once so the two
   never drift apart on what "preview / keep / not that / undo" actually does.

   config = {
     els: {fab, sheet, looks, sayForm, sayInput, ecol, log, close},
     getInstance: () => inst,               // current {app, skin, log}
     onChange: (inst) => {...},             // called after every commit/undo; persist + re-render host UI
     applySkin: (inst, skin) => {...},      // push `skin` live to wherever the app actually lives
   }
*/
(function (root) {
  "use strict";

  function attachShelfUI(config) {
    var els = config.els;
    var pending = null;

    function clone(o) { return JSON.parse(JSON.stringify(o)); }

    function swatchColors(inst, look) {
      if (look === "original") return { bg: root.SKIN_DEFAULT.background, primary: root.SKIN_DEFAULT.accent, label: "Original" };
      var t = Skins.build(look, config.getHue(inst));
      return { bg: t.background, primary: t.primary, label: t.label };
    }

    function renderLooks() {
      var inst = config.getInstance();
      var wrap = els.looks;
      wrap.innerHTML = "";
      ["original"].concat(Skins.THEME_ORDER).forEach(function (look) {
        var c = swatchColors(inst, look);
        var el = document.createElement("div");
        el.className = "look";
        el.dataset.look = look;
        el.setAttribute("role", "button");
        el.setAttribute("aria-pressed", String(inst.skin.look === look));
        var sw = document.createElement("div");
        sw.className = "swatch";
        sw.style.background = c.bg;
        sw.style.border = "2px solid " + c.primary;
        el.appendChild(sw);
        var label = document.createElement("div");
        label.textContent = c.label;
        el.appendChild(label);
        el.addEventListener("click", function () { pickLook(look); });
        wrap.appendChild(el);
      });
    }

    function pickLook(look) {
      var inst = config.getInstance();
      if (look === inst.skin.look) {
        els.ecol.innerHTML = "<p class=\"say\">That's the look it has now.</p>";
        return;
      }
      showProposal([{ key: "look", value: look, say: "Switches the look to " + swatchColors(inst, look).label + "." }], true);
    }

    function skinWithChanges(inst, changes) {
      var next = clone(inst.skin);
      changes.forEach(function (c) {
        if (c.key === "look") {
          if (c.value === "original") { next = clone(root.SKIN_DEFAULT); return; }
          var fields = Skins.lookFields(c.value, config.getHue(inst));
          next.accent = fields.accent; next.background = fields.background; next.surface = fields.surface;
          next.text = fields.text; next.font = fields.font; next.radius = fields.radius; next.look = c.value;
        } else {
          next[c.key] = c.value;
        }
      });
      return next;
    }

    function showProposal(changes, isLookPick) {
      var inst = config.getInstance();
      var next = skinWithChanges(inst, changes);
      pending = { skin: next, changes: changes };
      config.applySkin(inst, next);
      showChoices(changes, isLookPick ? "Keep it" : "Apply", isLookPick ? "Not that" : "Cancel");
    }

    function showChoices(changes, yes, no) {
      els.ecol.innerHTML = "";
      changes.forEach(function (c) {
        var p = document.createElement("p"); p.className = "say"; p.textContent = c.say; els.ecol.appendChild(p);
      });
      var box = document.createElement("div"); box.className = "choices";
      var yesBtn = document.createElement("button"); yesBtn.textContent = yes;
      yesBtn.addEventListener("click", commitPending);
      var noBtn = document.createElement("button"); noBtn.textContent = no;
      noBtn.addEventListener("click", cancelPending);
      box.appendChild(yesBtn); box.appendChild(noBtn);
      els.ecol.appendChild(box);
    }

    function commitPending() {
      if (!pending) return;
      var inst = config.getInstance();
      var before = clone(inst.skin);
      inst.skin = pending.skin;
      inst.log.unshift({ before: before, after: clone(inst.skin), say: pending.changes.map(function (c) { return c.say; }).join(" "), ts: Date.now() });
      pending = null;
      els.ecol.innerHTML = "";
      config.onChange(inst);
      renderLooks();
      renderLog();
    }

    function cancelPending() {
      var inst = config.getInstance();
      pending = null;
      els.ecol.innerHTML = "";
      config.applySkin(inst, inst.skin);
    }

    function renderLog() {
      var inst = config.getInstance();
      els.log.innerHTML = "";
      inst.log.forEach(function (entry, i) {
        var li = document.createElement("li");
        li.className = "link";
        li.textContent = "Undo: " + entry.say;
        li.addEventListener("click", function () { undo(i); });
        els.log.appendChild(li);
      });
    }

    function undo(i) {
      var inst = config.getInstance();
      var entry = inst.log[i];
      inst.skin = clone(entry.before);
      inst.log.splice(i, 1);
      els.ecol.innerHTML = "";
      config.onChange(inst);
      renderLooks();
      renderLog();
    }

    els.fab.addEventListener("click", function () {
      els.sheet.hidden = false;
      els.ecol.innerHTML = "";
      renderLooks();
      renderLog();
    });

    els.close.addEventListener("click", function () {
      var inst = config.getInstance();
      pending = null;
      config.applySkin(inst, inst.skin);
      els.ecol.innerHTML = "";
      els.sheet.hidden = true;
    });

    els.sayForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = els.sayInput.value.trim();
      els.sayInput.value = "";
      if (!text) return;
      var inst = config.getInstance();
      var changes = Skins.parseAsk(text);
      changes = Skins.normalizeChanges(changes, inst.skin.look);
      if (!changes.length) {
        els.ecol.innerHTML = "<p class=\"say\">Didn't catch a look, colour or font in that -- try 'make it dark' or a #hex colour.</p>";
        return;
      }
      var problems = Skins.checkEdit({ changes: changes });
      if (problems.length) {
        els.ecol.innerHTML = "<p class=\"say\">" + problems.join("; ") + "</p>";
        return;
      }
      showProposal(changes, false);
    });

    return { renderLooks: renderLooks, renderLog: renderLog, showProposal: showProposal };
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { attachShelfUI: attachShelfUI };
  else root.attachShelfUI = attachShelfUI;
})(typeof window !== "undefined" ? window : this);
