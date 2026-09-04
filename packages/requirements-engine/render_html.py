#!/usr/bin/env python3
"""render_html.py — render question_graph_v3.json as a single self-contained HTML reference page."""
# ============================================================================
# RULES / CONFIG
# ============================================================================
IN_JSON = "question_graph_v3.json"   # graph to render
OUT_HTML = "interview_v3.html"       # output page
SHOW_DONE_RULES = True               # False hides the machine done-rules (cleaner read for a customer-facing print)
# ============================================================================
import json, html, os

here = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(here, IN_JSON), encoding="utf-8"))
parts = {p["code"]: p for p in G["parts"]}
esc = html.escape


def gate_text(gate):
    if not gate:
        return ""
    if "all" in gate:
        return " and ".join(gate_text(x) for x in gate["all"])
    if "any" in gate:
        return " or ".join(gate_text(x) for x in gate["any"])
    op = {"eq": "=", "includes": "includes", "includes_any": "includes any of", "min_items": "has at least",
          "scope_includes": "has scope", "any_item_matches": "any item matches", "any_instance_includes": "any instance includes",
          "list_nonempty": "list non-empty"}[gate["op"]]
    return f"{gate['q']} {op} {gate['value']}"


qs = G["questions"]
fixed = sum(1 for q in qs if not q["per"])
tpl = len(qs) - fixed

nav = "".join(f'<a href="#part-{p}">{esc(p)}<span>{esc(parts[p]["title"])}</span></a>' for p in G["part_order"])
nav += '<a href="#defaults">SYS<span>Locked defaults</span></a><a href="#derivations">DER<span>Derivations</span></a><a href="#deploy">DI<span>Deploy inputs</span></a>'

body = []
for code in G["part_order"]:
    p = parts[code]
    meta = []
    if p["gate"]:
        meta.append("asked only if " + gate_text(p["gate"]))
    if p["per"]:
        meta.append(f"repeats once per confirmed <b>{esc(p['per'])}</b>")
    body.append(f'<section class="part" id="part-{code}"><header><span class="code">{esc(code)}</span><h2>{esc(p["title"])}</h2>'
                + (f'<p class="meta">{"; ".join(meta)}</p>' if meta else "")
                + (f'<p class="intro">{esc(p["intro"])}</p>' if p["intro"] else "") + "</header>")
    for q in qs:
        if q["part"] != code:
            continue
        chips = []
        chips.append(f'<span class="chip t">{esc(q["type"])}</span>')
        if q["options"]:
            chips.append('<span class="chip o">' + " · ".join(esc(o) for o in q["options"]) + "</span>")
        if q["gate"]:
            chips.append(f'<span class="chip g">if {esc(gate_text(q["gate"]))}</span>')
        if q["per"] != p["per"]:
            chips.append(f'<span class="chip p">{esc(q["per"] or "asked once")}</span>')
        if q["creates"]:
            chips.append(f'<span class="chip c">creates {esc(q["creates"]["kind"])}</span>')
        if q["feeds"]:
            chips.append('<span class="chip f">→ recurring ops</span>')
        done = f'<details><summary>done when</summary><code>{esc(json.dumps(q["done"]))}</code><div class="fills">fills ' + ", ".join(f"<code>{esc(f)}</code>" for f in q["fills"]) + "</div></details>" if SHOW_DONE_RULES else ""
        why = f'<p class="why">{esc(q["notes"])}</p>' if q["notes"] else ""
        body.append(f'<article class="q" id="{q["id"]}"><div class="id">{esc(q["id"])}</div><div class="main"><p class="prompt">{esc(q["prompt"])}</p>'
                    f'<div class="chips">{"".join(chips)}</div>{why}{done}</div></article>')
    body.append("</section>")

body.append('<section class="part" id="defaults"><header><span class="code">SYS</span><h2>Locked defaults</h2><p class="intro">Never asked. Overridable only through Part D, one default at a time, scoped narrowly.</p></header><div class="tbl"><table><thead><tr><th>ID</th><th>Area</th><th>Behaviour</th></tr></thead><tbody>')
for d in G["system_defaults"]:
    body.append(f'<tr><td><code>{esc(d["id"])}</code></td><td>{esc(d["area"])}</td><td>{esc(d["behaviour"])}' + (f'<div class="why">{esc(d["why"])}</div>' if d.get("why") else "") + "</td></tr>")
body.append("</tbody></table></div></section>")

body.append('<section class="part" id="derivations"><header><span class="code">DER</span><h2>Derivations</h2><p class="intro">Computed from answers. Each passes the two-builder test or it would be a question instead.</p></header><div class="tbl"><table><thead><tr><th>ID</th><th>Produces</th><th>From</th><th>Rule</th></tr></thead><tbody>')
for d in G["derivations"]:
    body.append(f'<tr><td>{esc(d["id"])}</td><td>{", ".join("<code>"+esc(f)+"</code>" for f in d["outputs"])}</td><td>{esc(", ".join(d["inputs"]))}</td><td>{esc(d["rule"])}<div class="why">{esc(d["safe_because"])}</div></td></tr>')
body.append("</tbody></table></div></section>")

body.append('<section class="part" id="deploy"><header><span class="code">DI</span><h2>Deploy inputs</h2><p class="intro">Block 0. A form the operator fills, not part of the interview. Without these the app cannot send an email, take a payment, or be logged into.</p></header><div class="tbl"><table><thead><tr><th>ID</th><th>Needed</th><th>When</th></tr></thead><tbody>')
for d in G["deploy_inputs"]:
    body.append(f'<tr><td>{esc(d["id"])}</td><td>{esc(d["prompt"])}</td><td>{esc(gate_text(d["gate"]) or "always")}</td></tr>')
body.append("</tbody></table></div></section>")

page = f"""<title>Requirements Interview v3</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--paper:#F2F4F6;--card:#FFFFFF;--ink:#17202A;--ink2:#54616D;--line:#D7DDE2;--accent:#1F6F78;--accent-ink:#0E4A51;--code:#E7ECEF;--chip:#EDF1F3;--why:#5B4A1F;--whybg:#FBF5E4}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--paper:#0F1518;--card:#161D21;--ink:#E3E9EC;--ink2:#95A3AC;--line:#28333A;--accent:#5FB3BB;--accent-ink:#8FD2D8;--code:#1F2A30;--chip:#1E272C;--why:#E5D4A3;--whybg:#2A2415}}}}
:root[data-theme="dark"]{{--paper:#0F1518;--card:#161D21;--ink:#E3E9EC;--ink2:#95A3AC;--line:#28333A;--accent:#5FB3BB;--accent-ink:#8FD2D8;--code:#1F2A30;--chip:#1E272C;--why:#E5D4A3;--whybg:#2A2415}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.5}}
.wrap{{display:grid;grid-template-columns:220px minmax(0,1fr);gap:32px;max-width:1180px;margin:0 auto;padding:32px 24px}}
nav{{position:sticky;top:24px;align-self:start;display:flex;flex-direction:column;gap:2px;font-family:"IBM Plex Mono",monospace;font-size:12px}}
nav a{{color:var(--ink2);text-decoration:none;padding:5px 8px;border-left:2px solid var(--line);display:flex;gap:10px}}
nav a span{{font-family:"IBM Plex Sans",sans-serif;color:var(--ink)}}
nav a:hover,nav a:focus-visible{{border-color:var(--accent);outline:none;color:var(--accent)}}
h1{{font-family:Archivo,sans-serif;font-weight:700;font-size:34px;letter-spacing:-.01em;margin:0 0 6px;text-wrap:balance}}
.lede{{color:var(--ink2);max-width:66ch;margin:0 0 8px}}
.stats{{display:flex;flex-wrap:wrap;gap:8px 20px;font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink2);margin:14px 0 36px;font-variant-numeric:tabular-nums}}
.stats b{{color:var(--ink);font-weight:500}}
.part{{margin:0 0 44px}}
.part header{{display:grid;grid-template-columns:64px 1fr;gap:0 14px;align-items:baseline;border-bottom:2px solid var(--ink);padding-bottom:10px;margin-bottom:14px}}
.part .code{{font-family:"IBM Plex Mono",monospace;color:var(--accent);font-weight:500;font-size:14px}}
.part h2{{font-family:Archivo,sans-serif;font-size:22px;font-weight:700;margin:0;text-wrap:balance}}
.part .meta,.part .intro{{grid-column:2;margin:4px 0 0;color:var(--ink2);font-size:13.5px;max-width:70ch}}
.q{{display:grid;grid-template-columns:64px minmax(0,1fr);gap:0 14px;padding:12px 0;border-bottom:1px solid var(--line)}}
.q .id{{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--accent-ink);padding-top:2px}}
.prompt{{margin:0 0 6px;max-width:72ch;font-weight:500}}
.chips{{display:flex;flex-wrap:wrap;gap:6px}}
.chip{{font-family:"IBM Plex Mono",monospace;font-size:11.5px;padding:2px 8px;border-radius:3px;background:var(--chip);color:var(--ink2)}}
.chip.g{{color:var(--accent-ink)}} .chip.c,.chip.f{{color:var(--why);background:var(--whybg)}}
.why{{font-size:13px;color:var(--why);background:var(--whybg);padding:6px 10px;border-radius:3px;margin:8px 0 0;max-width:72ch}}
details{{margin-top:6px;font-size:12.5px}} summary{{cursor:pointer;color:var(--ink2);font-family:"IBM Plex Mono",monospace}}
code{{font-family:"IBM Plex Mono",monospace;font-size:12px;background:var(--code);padding:1px 5px;border-radius:3px;word-break:break-word}}
details code{{display:inline-block;margin-top:4px}} .fills{{margin-top:4px;color:var(--ink2)}}
.tbl{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13.5px}}
th{{text-align:left;font-family:"IBM Plex Mono",monospace;font-weight:500;font-size:11.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink2);padding:8px 10px;border-bottom:1px solid var(--line)}}
td{{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}} td .why{{margin-top:6px}}
@media (max-width:820px){{.wrap{{grid-template-columns:1fr}} nav{{position:static;flex-direction:row;flex-wrap:wrap}} nav a span{{display:none}} .q,.part header{{grid-template-columns:52px 1fr}}}}
@media (prefers-reduced-motion:no-preference){{html{{scroll-behavior:smooth}}}}
</style>
<div class="wrap"><nav>{nav}</nav><main>
<h1>Requirements Interview v3</h1>
<p class="lede">Every question a product owner is asked to get from an idea to a build spec with nothing left for a builder to guess. The model chooses the words; the done-rule decides when a question is answered.</p>
<div class="stats"><span><b>{len(qs)}</b> questions</span><span><b>{fixed}</b> fixed</span><span><b>{tpl}</b> per instance</span><span><b>{len(G["system_defaults"])}</b> locked defaults</span><span><b>{len(G["derivations"])}</b> derivations</span><span><b>{len(G["deploy_inputs"])}</b> deploy inputs</span><span><b>{len(G["spec_fields"])}</b> spec fields, one source each</span></div>
{"".join(body)}
</main></div>
"""
open(os.path.join(here, OUT_HTML), "w", encoding="utf-8").write(page)
print("wrote", OUT_HTML, len(page), "bytes")
