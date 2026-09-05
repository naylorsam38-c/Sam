/* demo_store.js — the generated app's routes, in the browser, for when there is
   no server (the HTML opened straight from disk). It follows the same declared
   rules the real parts enforce — legal transitions by role, approval gates,
   declared custom actions, form validation, report specs, transition and
   create effects — so what a button does standalone is what it does against
   the real app. It is a demonstration store, not the product: data lives in
   this browser only, and the page says so. */
(function () {
  'use strict';
  const M = window.MODEL;
  const KEY = 'ui-demo:' + M.family;
  let DB = null;

  function fresh() {
    const db = { tables: {}, audit: [], stages: [], approvals: [] };
    for (const d of Object.values(M.records)) db.tables[d.table] = [];
    return db;
  }
  function load() {
    if (DB) return DB;
    try { const raw = localStorage.getItem(KEY); DB = raw ? JSON.parse(raw) : fresh(); } catch (e) { DB = fresh(); }
    for (const d of Object.values(M.records)) if (!DB.tables[d.table]) DB.tables[d.table] = [];
    return DB;
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(DB)); } catch (e) { /* per-viewer convenience only */ } }
  const now = () => Date.now() / 1000;
  const iso = () => new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  const uuid = () => 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => { const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 3 | 8)).toString(16); });
  const slug = (n) => String(n).toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/^_+|_+$/g, '');
  const recByTable = (t) => Object.entries(M.records).find(([n, d]) => d.table === t);
  const wfFor = (rname) => (M.records[rname].workflow ? M.workflows[M.records[rname].workflow] : null);
  const R = (status, data) => ({ status, data });
  const audit = (table, row_id, action, before, after) => { DB.audit.push({ table, row_id, action, before, after, at: now() }); };
  const enterStage = (table, row_id, stage) => { DB.stages.push({ record_table: table, row_id, stage, entered_at: now() }); };

  function gateFor(wf, stage) { return (wf.approvals || []).find((g) => g.stage === stage) || null; }
  function decisionFor(table, row_id, stage) {
    const hits = DB.approvals.filter((a) => a.table === table && a.row_id === row_id && a.stage === stage);
    return hits.length ? hits[hits.length - 1] : null;
  }
  function checkMayLeave(wf, table, row) {
    const g = gateFor(wf, row.stage); if (!g) return null;
    const d = decisionFor(table, row.id, row.stage);
    if (!d) throw Object.assign(new Error(table + ' ' + row.id + ' is waiting in \'' + row.stage + '\' for ' + JSON.stringify(g.approvers) + ' to approve'), { code: 409, waiting: true });
    return d;
  }
  function fireEvent(rname, table, row, event) {
    const wf = wfFor(rname);
    const edge = wf.transitions.find((t) => t.mover === 'automatic' && t.from === row.stage && t.event === event);
    if (!edge) {
      if (!wf.transitions.some((t) => t.mover === 'automatic' && t.event === event)) throw Object.assign(new Error('no declared event ' + JSON.stringify(event)), { code: 400 });
      throw Object.assign(new Error('event ' + JSON.stringify(event) + ' does not leave stage \'' + row.stage + '\''), { code: 409 });
    }
    const from = row.stage; row.stage = edge.to;
    audit(table, row.id, 'transition', { stage: from, by: 'system', event }, { stage: edge.to, by: 'system' });
    enterStage(table, row.id, edge.to);
    return { from, to: edge.to };
  }
  function transitionEffects(rname, table, row, entered) {
    const wf = wfFor(rname); const done = [];
    for (const eff of (wf && wf.effects) || []) {
      if (eff.on_enter !== entered) continue;
      if (eff.op === 'apply_order_lines') {
        const lines = DB.tables[eff.line_table].filter((l) => l[eff.line_fk] === row.id);
        const out = [];
        for (const l of lines) {
          const p = DB.tables[eff.product_table].find((x) => x.id === l[eff.product_fk]);
          if (!p) { out.push({ product_id: null, quantity: l[eff.quantity_column], new_stock: null, reorder_needed: null, error: 'line has no Product' }); continue; }
          const q = parseInt(l[eff.quantity_column] || 0, 10);
          p.stock_on_hand = (parseInt(p.stock_on_hand || 0, 10)) + (eff.direction === 'receive' ? q : -q);
          out.push({ product_id: p.id, quantity: q, new_stock: p.stock_on_hand, reorder_needed: p.reorder_point != null && p.stock_on_hand <= p.reorder_point });
        }
        done.push({ op: 'apply_order_lines', direction: eff.direction, lines: out });
      }
    }
    return done;
  }
  function createEffects(rname, row) {
    const done = [];
    for (const eff of M.records[rname].on_create || []) {
      if (eff.op !== 'ledger_balance') continue;
      const targetId = row[eff.link_column]; if (!targetId) continue;
      const target = DB.tables[eff.table].find((x) => x.id === targetId);
      let total = null;
      if (eff.total.kind === 'lines') total = DB.tables[eff.total.line_table].filter((l) => l[eff.total.line_fk] === targetId).reduce((s, l) => s + (parseFloat(l[eff.total.quantity_column]) || 0) * (parseFloat(l[eff.total.amount_column]) || 0), 0);
      else total = target ? target[eff.total.column] : null;
      const applied = DB.tables[eff.payments_table].filter((p) => p[eff.link_column] === targetId).reduce((s, p) => s + (parseFloat(p[eff.amount_column]) || 0), 0);
      const settled = total != null && parseFloat(total) > 0 && applied >= parseFloat(total);
      const result = { op: 'ledger_balance', target: eff.table, target_id: targetId, total, applied, settled, moved: null };
      if (settled && target) {
        const tr = recByTable(eff.table);
        try { checkMayLeave(wfFor(tr[0]), eff.table, target); result.moved = fireEvent(tr[0], eff.table, target, eff.event); }
        catch (e) { result.moved = null; result.not_moved_because = e.message; }
      }
      done.push(result);
    }
    return done;
  }

  // -------------------------------------------------------------- reports (reporting_engine / stage_history / stock_ledger rules)
  function passes(row, f) {
    const v = row[f.field];
    switch (f.op) {
      case '=': return v == f.value; case '!=': return v != f.value;
      case '<': return v < f.value; case '>': return v > f.value; case '<=': return v <= f.value; case '>=': return v >= f.value;
      case 'in': return (f.value || []).includes(v); case 'not_in': return !(f.value || []).includes(v);
      case 'before_now': return v != null && String(v).slice(0, 10) < new Date().toISOString().slice(0, 10);
      case 'within_next_days': { if (v == null) return false; const d = String(v).slice(0, 10); const t = new Date().toISOString().slice(0, 10); const e = new Date(Date.now() + f.value * 86400000).toISOString().slice(0, 10); return d >= t && d <= e; }
      default: return true;
    }
  }
  function runReport(sp) {
    if (!sp.engine || sp.engine === 'reporting_engine') {
      let rows = DB.tables[sp.table] || [];
      for (const f of sp.filters || []) rows = rows.filter((r) => passes(r, f));
      const agg = (rs) => {
        if (sp.aggregation === 'count') return rs.length;
        const vals = rs.map((r) => parseFloat(r[sp.value_field])).filter((x) => !isNaN(x));
        if (sp.aggregation === 'sum') return vals.reduce((a, b) => a + b, 0);
        if (sp.aggregation === 'avg') return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
        if (sp.aggregation === 'min') return vals.length ? Math.min.apply(null, vals) : null;
        if (sp.aggregation === 'max') return vals.length ? Math.max.apply(null, vals) : null;
        return null;
      };
      if (!sp.group_by) return agg(rows);
      const out = {};
      for (const r of rows) { const k = r[sp.group_by] == null ? 'null' : String(r[sp.group_by]); (out[k] = out[k] || []).push(r); }
      for (const k of Object.keys(out)) out[k] = agg(out[k]);
      return out;
    }
    if (sp.engine === 'stage_history' && sp.kind === 'rate_over_last_days') {
      const since = now() - sp.days * 86400;
      const inWin = DB.stages.filter((s) => s.record_table === sp.table && s.entered_at >= since);
      const numer = new Set(inWin.filter((s) => s.stage === sp.numerator_stage).map((s) => s.row_id)).size;
      const denom = new Set(inWin.filter((s) => sp.denominator_stages.includes(s.stage)).map((s) => s.row_id)).size;
      const rate = denom ? numer / denom : null;
      return { rate, percentage: rate == null ? null : Math.round(rate * 1000) / 10, numerator: numer, denominator: denom, window_days: sp.days };
    }
    if (sp.engine === 'stage_history' && sp.kind === 'line_value_by_month') {
      const months = sp.months || 12; const out = {}; const d = new Date();
      const keys = []; let y = d.getUTCFullYear(), m = d.getUTCMonth() + 1;
      for (let i = 0; i < months; i++) { keys.push(y + '-' + String(m).padStart(2, '0')); m--; if (m === 0) { m = 12; y--; } }
      keys.reverse().forEach((k) => { out[k] = 0; });
      const latest = {};
      for (const s of DB.stages) if (s.record_table === sp.table && s.stage === sp.stage) latest[s.row_id] = Math.max(latest[s.row_id] || 0, s.entered_at);
      const since = now() - months * 31 * 86400;
      for (const [rowId, at] of Object.entries(latest)) {
        if (at < since) continue;
        const k = new Date(at * 1000).toISOString().slice(0, 7);
        const v = DB.tables[sp.line_table].filter((l) => l[sp.line_fk] === rowId).reduce((s, l) => s + (parseFloat(l[sp.quantity_column]) || 0) * (parseFloat(l[sp.price_column]) || 0), 0);
        out[k] = (out[k] || 0) + v;
      }
      return out;
    }
    if (sp.engine === 'stock_ledger' && sp.kind === 'count_at_or_below_reorder') {
      return DB.tables[sp.table].filter((p) => p[sp.reorder_column] != null && p[sp.stock_column] != null && parseFloat(p[sp.stock_column]) <= parseFloat(p[sp.reorder_column])).length;
    }
    throw new Error('no rule for report metric');
  }

  // -------------------------------------------------------------- the routes
  function call(method, path, body) {
    load(); body = body || {};
    try {
      const out = route(method, path, body); save(); return Promise.resolve(out);
    } catch (e) { return Promise.resolve(R(e.code || 500, { error: e.message, waiting_for_approval: !!e.waiting })); }
  }
  function route(method, path, body) {
    let m;
    if ((m = path.match(/^\/api\/reports\/([^/]+)$/)) && method === 'GET') {
      const rp = Object.values(M.reports).find((r) => r.slug === m[1]); if (!rp) return R(404, { error: 'no route' });
      const out = {}; for (const e of rp.specs) out[e.metric] = runReport(e.spec); return R(200, out);
    }
    if ((m = path.match(/^\/api\/forms\/([^/]+)$/)) && method === 'POST') {
      const fm = Object.values(M.forms).find((f) => f.slug === m[1]); if (!fm) return R(404, { error: 'no route' });
      const d = M.records[fm.record]; const row = { id: uuid(), created_at: iso(), updated_at: iso() };
      for (const f of d.fields) {
        if (!fm.fields.includes(f.slug)) { row[f.slug] = null; continue; }
        const v = body[f.slug];
        if (f.type === 'yes_no') { row[f.slug] = v ? 1 : 0; continue; }
        if (v == null || v === '') { if (f.required === 'yes') throw Object.assign(new Error(f.name + ' is required'), { code: 400 }); row[f.slug] = null; continue; }
        row[f.slug] = v;
      }
      for (const k of Object.keys(body)) if (!d.fields.some((f) => f.slug === k)) throw Object.assign(new Error('[' + k + '] is not a field of this record'), { code: 400 });
      if (d.has_stage) { row.stage = wfFor(fm.record).initial; }
      DB.tables[d.table].push(row); if (d.has_stage) enterStage(d.table, row.id, row.stage);
      return R(201, { id: row.id });
    }
    if ((m = path.match(/^\/api\/(moves|events|approvals|actions|history)\/([^/]+)\/([^/]+)(?:\/(.+))?$/))) {
      const [, kind, table, id, tail] = m; const hit = recByTable(table); if (!hit) return R(404, { error: 'no route' });
      const [rname, d] = hit; const row = DB.tables[table].find((x) => x.id === id);
      if (kind === 'history' && method === 'GET') return R(200, { audit: DB.audit.filter((a) => a.table === table && a.row_id === id).map((a) => ({ action: a.action, before: a.before, after: a.after, at: a.at })), stages: DB.stages.filter((s) => s.record_table === table && s.row_id === id).map((s) => ({ stage: s.stage, entered_at: s.entered_at })) });
      if (!row) return R(404, { error: 'no such row' });
      const wf = wfFor(rname);
      if (kind === 'moves' && method === 'POST') {
        if (!wf) return R(404, { error: 'no route' });
        checkMayLeave(wf, table, row);
        const t = wf.transitions.find((x) => x.mover === 'roles' && x.from === row.stage && x.to === body.to && (x.roles || []).includes(body.role));
        if (!t) return R(409, { error: 'no declared person-triggered transition from \'' + row.stage + '\' to \'' + body.to + '\' for role \'' + body.role + '\'' });
        const from = row.stage; row.stage = body.to; audit(table, id, 'transition', { stage: from, by: body.role }, { stage: body.to, by: body.role }); enterStage(table, id, body.to);
        return R(200, { from, to: body.to, effects: transitionEffects(rname, table, row, body.to) });
      }
      if (kind === 'events' && method === 'POST') { if (!wf) return R(404, { error: 'no route' }); checkMayLeave(wf, table, row); const mv = fireEvent(rname, table, row, body.event); return R(200, Object.assign(mv, { effects: transitionEffects(rname, table, row, mv.to) })); }
      if (kind === 'approvals' && method === 'GET') { if (!wf || !(wf.approvals || []).length) return R(404, { error: 'no route' }); const g = gateFor(wf, row.stage); const dec = g ? decisionFor(table, id, row.stage) : null; return R(200, { stage: row.stage, gate: g, decision: dec ? { decision: dec.decision, decided_by: dec.decided_by, reason: dec.reason } : null }); }
      if (kind === 'approvals' && method === 'POST') {
        if (!wf || !(wf.approvals || []).length) return R(404, { error: 'no route' });
        const g = gateFor(wf, row.stage); if (!g) return R(409, { error: '\'' + row.stage + '\' is not a gated stage; there is nothing to approve' });
        if (!(g.approvers || []).includes(body.by)) return R(403, { error: '\'' + body.by + '\' does not approve \'' + row.stage + '\'; declared: ' + JSON.stringify(g.approvers) });
        if (body.decision !== 'APPROVED' && body.decision !== 'DECLINED') return R(400, { error: 'decision must be APPROVED or DECLINED' });
        DB.approvals.push({ table, row_id: id, stage: row.stage, decision: body.decision, decided_by: body.by, reason: body.reason || null, at: now() });
        audit(table, id, 'approval:' + row.stage, null, { decision: body.decision, by: body.by, reason: body.reason || null });
        if (body.decision === 'DECLINED' && wf.on_reject && wf.on_reject.back_to) { row.stage = wf.on_reject.back_to; enterStage(table, id, row.stage); return R(200, { decision: 'DECLINED', stage: row.stage }); }
        return R(200, { decision: body.decision, stage: row.stage });
      }
      if (kind === 'actions' && method === 'POST') {
        const name = decodeURIComponent(tail || ''); const a = d.custom_actions.find((x) => x.name === name);
        if (!a) return R(404, { error: 'no declared action ' + JSON.stringify(name) });
        if (!(a.who || []).includes(body.role)) return R(403, { error: '\'' + body.role + '\' may not press \'' + name + '\'; declared: ' + JSON.stringify(a.who) });
        const ex = a.execution || {}; const inputs = body.inputs || {};
        if (ex.op === 'clone') {
          const copy = Object.assign({}, row, { id: uuid(), created_at: iso(), updated_at: iso() }, ex.overrides || {});
          if (ex.title_column && ex.title_suffix) copy[ex.title_column] = (copy[ex.title_column] || '') + ex.title_suffix;
          DB.tables[table].push(copy); if ((ex.overrides || {}).stage) enterStage(table, copy.id, ex.overrides.stage);
          audit(table, id, 'custom:' + name, {}, { cloned_to: copy.id }); return R(200, { action: name, by: body.role, cloned_to: copy.id });
        }
        if (ex.op === 'generate_document') {
          const title = (ex.title_columns || []).map((c) => row[c] || '').join(' ').trim() || id;
          const lines = (ex.body_columns || []).map((c) => c.replace(/_/g, ' ') + ': ' + (row[c] == null ? '' : row[c]));
          let total = 0;
          if (ex.line_table) { for (const l of DB.tables[ex.line_table].filter((x) => x[ex.line_fk] === id)) { lines.push((ex.line_columns || []).map((c) => l[c] == null ? '' : l[c]).join(' | ')); total += (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_amount) || 0); } lines.push('Total: ' + total.toFixed(2)); }
          const html = '<h1>' + title + '</h1>' + lines.map((l) => '<p>' + l + '</p>').join('');
          const stamp = iso(); if (ex.stamp_column) row[ex.stamp_column] = stamp;
          audit(table, id, 'custom:' + name, {}, { document: table + '-' + id + '.pdf', stamped: stamp });
          return R(200, { action: name, by: body.role, document_html: html, document_pdf: null, stamped: stamp, total, email: 'not dispatched: no outbound email part is on the shelf (demo mode: no PDF file either)' });
        }
        let changes = {};
        if (ex.op === 'set_fields') changes = Object.assign({}, ex.fields);
        else if (ex.op === 'clear_fields') { for (const f of ex.fields) changes[f] = null; }
        else if (ex.op === 'reset_to_stage') { changes[ex.stage_column] = ex.stage; for (const f of ex.clear || []) changes[f] = null; }
        else if (ex.op === 'set_fields_from_input') { const missing = ex.fields.filter((f) => inputs[f] == null || inputs[f] === ''); if (missing.length) return R(400, { error: '\'' + name + '\' needs a value for ' + JSON.stringify(missing) + ' and none was supplied' }); for (const f of ex.fields) changes[f] = inputs[f]; }
        else return R(400, { error: 'no rule for op ' + JSON.stringify(ex.op) });
        if (!Object.keys(changes).length) return R(400, { error: '\'' + name + '\' would change nothing' });
        const before = {}; for (const k of Object.keys(changes)) before[k] = row[k];
        Object.assign(row, changes); audit(table, id, 'custom:' + name, before, changes);
        return R(200, { action: name, by: body.role, before, after: changes });
      }
      return R(404, { error: 'no route' });
    }
    if ((m = path.match(/^\/api\/([^/]+)(?:\/([^/]+))?$/))) {
      const [, table, id] = m; const hit = recByTable(table); if (!hit) return R(404, { error: 'no route' });
      const [rname, d] = hit; const rows = DB.tables[table];
      if (method === 'GET' && !id) return R(200, rows.slice().sort((a, b) => (a.created_at < b.created_at ? 1 : -1)));
      if (method === 'GET') { const r = rows.find((x) => x.id === id); return r ? R(200, r) : R(404, { error: 'not found' }); }
      if (method === 'POST' && !id) {
        if (!d.access.create || !d.access.create.length) return R(404, { error: 'no route' });
        const row = { id: uuid(), created_at: iso(), updated_at: iso() };
        for (const f of d.fields) row[f.slug] = body[f.name] == null ? null : body[f.name];
        if (d.has_stage) row.stage = wfFor(rname).initial;
        rows.push(row); if (d.has_stage) enterStage(table, row.id, row.stage);
        return R(201, { id: row.id, effects: createEffects(rname, row) });
      }
      if (method === 'PUT' && id) {
        const r = rows.find((x) => x.id === id); if (!r) return R(404, { error: 'not found' });
        for (const f of d.fields) r[f.slug] = body[f.name] == null ? null : body[f.name];
        r.updated_at = iso(); return R(200, { id });
      }
      if (method === 'DELETE' && id) {
        if (!d.access.delete || d.access.delete === 'nobody' || !d.access.delete.length) return R(404, { error: 'no route' });
        const i = rows.findIndex((x) => x.id === id); if (i < 0) return R(404, { deleted: false });
        rows.splice(i, 1); return R(200, { deleted: true });
      }
    }
    return R(404, { error: 'no route' });
  }
  window.DemoStore = { call, reset() { DB = fresh(); save(); } };
})();
