/* runtime.js — shared by every generated interface.
   MODEL (injected) describes the family exactly as its SPEC.json build_model does:
   records, fields, access, workflows, approvals, custom actions, forms, reports, roles.
   Every control on the page carries data-act="<verb>"; one dispatcher below performs
   it against the real generated routes (or the in-browser demo store when there is
   no server) and re-renders. Nothing here invents a capability the spec does not
   declare: a button appears only when the current role really may press it. */
(function () {
  'use strict';
  const M = window.MODEL;
  const $ = (sel, root) => (root || document).querySelector(sel);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ------------------------------------------------------------------ transport
  const Api = {
    mode: 'server',          // 'server' | 'demo'
    reason: '',
    async call(method, path, body) {
      if (this.mode === 'demo') return window.DemoStore.call(method, path, body);
      let res;
      try {
        res = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: body == null ? undefined : JSON.stringify(body) });
      } catch (e) {
        this.mode = 'demo'; this.reason = 'no server reachable';
        return window.DemoStore.call(method, path, body);
      }
      let data = null;
      try { data = await res.json(); } catch (e) { data = null; }
      return { status: res.status, data };
    },
  };
  if (location.protocol === 'file:') { Api.mode = 'demo'; Api.reason = 'opened as a file'; }

  // ------------------------------------------------------------------ model helpers
  const slug = (name) => String(name).toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/^_+|_+$/g, '');
  const rec = (name) => M.records[name];
  const wfOf = (name) => (rec(name).workflow ? M.workflows[rec(name).workflow] : null);
  const isAdmin = (role) => !!M.role_admin[role];
  const may = (list, role) => isAdmin(role) || (Array.isArray(list) && list.includes(role));
  const canView = (r, role) => may(rec(r).access.view, role);
  const canCreate = (r, role) => may(rec(r).access.create, role);
  const canEdit = (r, role) => may(rec(r).access.edit, role);
  const canDelete = (r, role) => may(rec(r).access.delete, role);
  const titleOf = (r, row, depth) => {
    const fname = rec(r).title_field;
    const f = rec(r).fields.find((x) => x.name === fname);
    const v = row && f ? row[f.slug] : null;
    if (v == null || v === '') return row ? row.id.slice(0, 8) : '';
    // a title that is a link (accounting's Invoice is titled by its Contact) shows
    // the linked record's own title, never its id -- found in a screenshot
    if (f.type === 'link' && f.target_record && (depth || 0) < 2) {
      const hit = (S.rows[rec(f.target_record).table] || []).find((x) => x.id === v);
      // two orders for one supplier must still tell apart: the short id rides along
      if (hit) return titleOf(f.target_record, hit, (depth || 0) + 1) + ((depth || 0) === 0 ? ' · ' + row.id.slice(0, 8) : '');
    }
    return String(v);
  };
  // person-moved edges the current role may take from the row's stage: exactly workflow_executor's rule
  const movesFor = (r, row, role) => {
    const wf = wfOf(r); if (!wf || !row) return [];
    return wf.transitions.filter((t) => t.mover === 'roles' && t.from === row.stage && (t.roles || []).includes(role));
  };
  const gateFor = (r, row) => { const wf = wfOf(r); if (!wf || !row) return null; return (wf.approvals || []).find((g) => g.stage === row.stage) || null; };
  const actionsFor = (r, role) => rec(r).custom_actions.filter((a) => (a.who || []).includes(role));
  const childrenOf = (r) => Object.entries(M.records).filter(([n, d]) => d.fields.some((f) => f.type === 'link' && f.target_record === r)).map(([n]) => n);

  // ------------------------------------------------------------------ state
  const S = {
    role: M.super_role || M.roles[0],
    view: { kind: 'home' },
    rows: {},          // table -> rows
    detail: null,      // {record, row, history, approval}
    report: null,      // {name, data}
    notice: null,      // {kind: 'ok'|'err'|'info', text}
    busy: false,
    inputsFor: null,   // pending custom action needing inputs {record,id,action}
    docShown: null,    // document html from generate_document
  };
  const D = window.DESIGN;

  async function loadAll() {
    for (const [name, d] of Object.entries(M.records)) {
      if (!canView(name, S.role)) { S.rows[d.table] = []; continue; }
      const r = await Api.call('GET', '/api/' + d.table);
      S.rows[d.table] = r.status === 200 && Array.isArray(r.data) ? r.data : [];
    }
  }
  async function openDetail(record, id) {
    const d = rec(record);
    const r = await Api.call('GET', '/api/' + d.table + '/' + id);
    if (r.status !== 200) { notice('err', 'Could not open ' + record); return; }
    const h = await Api.call('GET', '/api/history/' + d.table + '/' + id);
    let approval = null;
    if (wfOf(record) && (wfOf(record).approvals || []).length) {
      const a = await Api.call('GET', '/api/approvals/' + d.table + '/' + id);
      approval = a.status === 200 ? a.data : null;
    }
    S.detail = { record, row: r.data, history: h.status === 200 ? h.data : { audit: [], stages: [] }, approval };
    S.view = { kind: 'detail', record, id };
  }
  function notice(kind, text) { S.notice = { kind, text }; }

  // ------------------------------------------------------------------ actions (one per data-act verb)
  const Act = {
    async role(p) { S.role = p.role; S.view = { kind: 'home' }; S.detail = null; await loadAll(); },
    async nav(p) { S.view = { kind: p.kind, record: p.record, report: p.report, form: p.form }; S.detail = null; S.report = null; if (p.kind === 'report') await Act.runReport({ report: p.report }); },
    async home() { S.view = { kind: 'home' }; S.detail = null; },
    async open(p) { await openDetail(p.record, p.id); },
    async back(p) { S.view = { kind: 'list', record: S.detail ? S.detail.record : p.record }; S.detail = null; },
    async newRow(p) { S.view = { kind: 'new', record: p.record, parent: p.parent || null, parentId: p.parentId || null }; },
    async create(p, form) {
      const d = rec(p.record); const body = {};
      for (const f of d.fields) body[f.name] = valueFrom(form, f);
      const r = await Api.call('POST', '/api/' + d.table, body);
      if (r.status !== 201) return notice('err', (r.data && r.data.error) || 'Create failed');
      notice('ok', p.record + ' created' + effectsText(r.data.effects));
      await loadAll();
      if (p.parent) { await openDetail(p.parent, p.parentId); } else { await openDetail(p.record, r.data.id); }
    },
    async save(p, form) {
      const d = rec(p.record); const body = {};
      for (const f of d.fields) body[f.name] = valueFrom(form, f);
      const r = await Api.call('PUT', '/api/' + d.table + '/' + p.id, body);
      if (r.status !== 200) return notice('err', (r.data && r.data.error) || 'Save failed');
      notice('ok', 'Saved'); await loadAll(); await openDetail(p.record, p.id);
    },
    async remove(p) {
      const d = rec(p.record);
      const r = await Api.call('DELETE', '/api/' + d.table + '/' + p.id);
      if (r.status !== 200) return notice('err', (r.data && r.data.error) || 'Delete failed');
      notice('ok', p.record + ' deleted'); await loadAll();
      if (S.detail && S.detail.record === p.record && S.detail.row.id === p.id) { S.view = { kind: 'list', record: p.record }; S.detail = null; }
      else if (S.detail) await openDetail(S.detail.record, S.detail.row.id);
    },
    async move(p) {
      const d = rec(p.record);
      const r = await Api.call('POST', '/api/moves/' + d.table + '/' + p.id, { to: p.to, role: S.role });
      if (r.status !== 200) return notice('err', (r.data && r.data.error) || 'Move refused');
      notice('ok', 'Moved to ' + p.to + effectsText(r.data.effects));
      await loadAll(); if (S.view.kind === 'detail') await openDetail(p.record, p.id);
    },
    async approve(p, form) {
      const d = rec(p.record);
      const reason = form ? (form.querySelector('[name=reason]') || {}).value : '';
      const r = await Api.call('POST', '/api/approvals/' + d.table + '/' + p.id, { decision: p.decision, by: S.role, reason: reason || null });
      if (r.status !== 200) return notice('err', (r.data && r.data.error) || 'Decision refused');
      notice('ok', p.decision === 'APPROVED' ? 'Approved' : 'Declined — sent back to ' + r.data.stage);
      await loadAll(); await openDetail(p.record, p.id);
    },
    async action(p, form) {
      const d = rec(p.record); const a = d.custom_actions.find((x) => x.name === p.action);
      const ex = a.execution || {};
      let inputs = null;
      if (ex.op === 'set_fields_from_input') {
        if (!form) { S.inputsFor = { record: p.record, id: p.id, action: p.action, fields: ex.fields }; return; }
        inputs = {}; for (const f of ex.fields) inputs[f] = (form.querySelector('[name="' + f + '"]') || {}).value;
      }
      const r = await Api.call('POST', '/api/actions/' + d.table + '/' + p.id + '/' + encodeURIComponent(p.action), { role: S.role, inputs: inputs || {} });
      S.inputsFor = null;
      if (r.status !== 200) return notice('err', (r.data && r.data.error) || p.action + ' refused');
      if (r.data.cloned_to) notice('ok', p.action + ': copy created');
      else if (r.data.document_html) { notice('ok', p.action + ': document generated; ' + r.data.email); S.docShown = { html: r.data.document_html, pdf: r.data.document_pdf }; }
      else notice('ok', p.action + ' done');
      await loadAll(); await openDetail(p.record, p.id);
    },
    async cancelInputs() { S.inputsFor = null; },
    async closeDoc() { S.docShown = null; },
    async submitForm(p, form) {
      const fm = M.forms[p.form]; const d = rec(fm.record); const body = {};
      for (const sl of fm.fields) { const f = d.fields.find((x) => x.slug === sl); if (f) body[sl] = valueFrom(form, f); }
      const r = await Api.call('POST', '/api/forms/' + fm.slug, body);
      if (r.status !== 201) return notice('err', (r.data && r.data.error) || 'Submission refused');
      notice('ok', p.form + ' submitted (' + r.data.id.slice(0, 8) + ')'); await loadAll();
      form.reset();
    },
    async runReport(p) {
      const rp = M.reports[p.report];
      const r = await Api.call('GET', '/api/reports/' + rp.slug);
      S.report = { name: p.report, data: r.status === 200 ? r.data : null, error: r.status === 200 ? null : ((r.data && r.data.error) || 'report failed') };
      S.view = { kind: 'report', report: p.report };
    },
    async dismiss() { S.notice = null; },
    async resetDemo() { if (Api.mode === 'demo') { window.DemoStore.reset(); await loadAll(); S.view = { kind: 'home' }; S.detail = null; notice('info', 'Demo data cleared'); } },
  };
  function effectsText(effects) {
    if (!effects || !effects.length) return '';
    return ' · ' + effects.map((e) => {
      if (e.op === 'apply_order_lines') return (e.lines || []).map((l) => 'stock ' + (e.direction === 'ship' ? '−' : '+') + l.quantity + ' → ' + l.new_stock + (l.reorder_needed ? ' (reorder)' : '')).join(', ') || 'no lines';
      if (e.op === 'ledger_balance') return 'applied ' + e.applied + ' of ' + e.total + (e.settled ? (e.moved ? ' → ' + e.moved.to : ' (settled)') : '');
      return e.op;
    }).join('; ');
  }
  function valueFrom(form, f) {
    const el = form.querySelector('[name="' + f.slug + '"]');
    if (!el) return null;
    if (f.type === 'yes_no') return el.checked ? 1 : 0;
    const v = el.value;
    if (v === '') return null;
    if (f.type === 'whole_number') return parseInt(v, 10);
    if (f.type === 'decimal_number' || f.type === 'money') return parseFloat(v);
    return v;
  }

  // ------------------------------------------------------------------ field controls (shared by every design)
  function linkOptions(f, current) {
    const t = rec(f.target_record); const rows = S.rows[t.table] || [];
    return '<option value="">—</option>' + rows.map((r) => '<option value="' + esc(r.id) + '"' + (r.id === current ? ' selected' : '') + '>' + esc(titleOf(f.target_record, r)) + '</option>').join('');
  }
  function control(f, value) {
    const name = 'name="' + f.slug + '"' + (f.required === 'yes' ? ' required' : '');
    const v = value == null ? '' : value;
    switch (f.type) {
      case 'long_text': return '<textarea ' + name + ' rows="3">' + esc(v) + '</textarea>';
      case 'whole_number': return '<input type="number" step="1" ' + name + ' value="' + esc(v) + '">';
      case 'decimal_number': return '<input type="number" step="0.01" ' + name + ' value="' + esc(v) + '">';
      case 'money': return '<input type="number" step="0.01" ' + name + ' value="' + esc(v) + '">';
      case 'date': return '<input type="date" ' + name + ' value="' + esc(v) + '">';
      case 'date_time': return '<input type="datetime-local" ' + name + ' value="' + esc(v) + '">';
      case 'yes_no': return '<input type="checkbox" ' + name + (v ? ' checked' : '') + '>';
      case 'one_choice': return '<select ' + name + '><option value="">—</option>' + (f.options || []).map((o) => '<option' + (o === v ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select>';
      case 'multi_choice': return '<select multiple ' + name + '>' + (f.options || []).map((o) => '<option' + (String(v).split(',').includes(o) ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select>';
      case 'email': return '<input type="email" ' + name + ' value="' + esc(v) + '">';
      case 'phone': return '<input type="tel" ' + name + ' value="' + esc(v) + '">';
      case 'url': return '<input type="url" ' + name + ' value="' + esc(v) + '">';
      case 'link': return '<select ' + name + '>' + linkOptions(f, v) + '</select>';
      default: return '<input type="text" ' + name + ' value="' + esc(v) + '">';
    }
  }
  function display(f, row) {
    const v = row[f.slug];
    if (v == null || v === '') return '';
    if (f.type === 'link') { const t = rec(f.target_record); const hit = (S.rows[t.table] || []).find((r) => r.id === v); return hit ? titleOf(f.target_record, hit) : String(v).slice(0, 8); }
    if (f.type === 'yes_no') return v ? 'yes' : 'no';
    if (f.type === 'money') return Number(v).toFixed(2);
    return String(v);
  }
  function fieldRows(record, row, opts) {
    const d = rec(record); opts = opts || {};
    return d.fields.filter((f) => !(opts.lockedParent && f.type === 'link' && f.target_record === opts.lockedParent)).map((f) =>
      '<label class="fld"><span class="fld-l">' + esc(f.name) + (f.required === 'yes' ? ' <b>*</b>' : '') + '</span>' + control(f, row ? row[f.slug] : (opts.defaults || {})[f.slug]) + '</label>').join('') +
      (opts.lockedParent ? d.fields.filter((f) => f.type === 'link' && f.target_record === opts.lockedParent).map((f) => '<input type="hidden" name="' + f.slug + '" value="' + esc(opts.parentId) + '">').join('') : '');
  }

  // ------------------------------------------------------------------ view model handed to the design
  function vm() {
    const role = S.role;
    const visibleRecords = Object.keys(M.records).filter((r) => canView(r, role));
    const reports = Object.keys(M.reports);
    const forms = Object.keys(M.forms);
    const out = { M, S, role, esc, slug, rec, wfOf, titleOf, display, control, fieldRows, movesFor, gateFor, actionsFor, childrenOf,
      canCreate: (r) => canCreate(r, role), canEdit: (r) => canEdit(r, role), canDelete: (r) => canDelete(r, role),
      visibleRecords, reports, forms, mode: Api.mode, modeReason: Api.reason,
      rowsOf: (r) => S.rows[rec(r).table] || [],
      stagesOf: (r) => (wfOf(r) ? wfOf(r).stages : []),
      isTerminal: (r, st) => (wfOf(r) ? (wfOf(r).terminal || []).includes(st) : false),
      approvalState: (r, row) => {
        const g = gateFor(r, row); if (!g) return null;
        const dec = S.detail && S.detail.row.id === row.id ? S.detail.approval && S.detail.approval.decision : null;
        return { gate: g, decision: dec, mayDecide: (g.approvers || []).includes(role) };
      },
      childRows: (parent, id) => childrenOf(parent).map((c) => {
        const link = rec(c).fields.find((f) => f.type === 'link' && f.target_record === parent);
        return { record: c, link, rows: (S.rows[rec(c).table] || []).filter((x) => x[link.slug] === id) };
      }),
      reportView: (name) => {
        const rp = M.reports[name]; const data = S.report && S.report.name === name ? S.report.data : null;
        return { rp, data, error: S.report && S.report.name === name ? S.report.error : null };
      },
    };
    return out;
  }

  // ------------------------------------------------------------------ render + dispatch
  function render() {
    const root = $('#app');
    root.innerHTML = D.render(vm());
    const focus = root.querySelector('[autofocus]'); if (focus) focus.focus();
  }
  document.addEventListener('click', async (ev) => {
    const el = ev.target.closest('[data-act]'); if (!el) return;
    // an overlay closes only when the scrim itself is clicked, never when a click
    // inside its modal bubbles up to it (found in Board: stopPropagation on the
    // modal had silenced every button inside it instead)
    if (el.classList.contains('overlay') && ev.target !== el) return;
    if (el.tagName === 'SELECT' || el.tagName === 'INPUT' || el.tagName === 'FORM') return; // change/submit handle these
    if (el.tagName === 'BUTTON' && el.type === 'submit' && el.closest('form')) return; // handled on submit
    ev.preventDefault();
    if (el.dataset.confirm && !window.confirm(el.dataset.confirm)) return;
    await run(el.dataset, el.closest('form'));
  });
  document.addEventListener('submit', async (ev) => {
    const form = ev.target; const act = form.dataset.act; if (!act) return;
    ev.preventDefault();
    if (!form.reportValidity()) return;
    await run(form.dataset, form);
  });
  document.addEventListener('change', async (ev) => {
    const el = ev.target; if (el.dataset && el.dataset.act === 'role') { await run({ act: 'role', role: el.value }); }
  });
  async function run(p, form) {
    if (S.busy) return; S.busy = true;
    try { S.notice = null; await Act[p.act](p, form); } catch (e) { notice('err', String(e && e.message || e)); console.error(e); }
    S.busy = false; render();
  }
  window.UI = { state: S, api: Api, render, run, vm };
  (async () => { await loadAll(); render(); })();
})();
