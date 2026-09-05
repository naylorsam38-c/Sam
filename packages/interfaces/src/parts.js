/* parts.js — render fragments the three designs compose differently.
   Everything actionable carries data-act; nothing is shown that the current
   role may not really do (the same rules the generated routes enforce). */
window.PARTS = (function () {
  'use strict';
  const h = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtTime = (t) => { try { return new Date(t * 1000).toLocaleString(); } catch (e) { return String(t); } };
  // the label a person reads ("Activities", "Invoice lines"); table names keep the Builder's own rule
  const plural = (name) => /[^aeiou]y$/i.test(name) ? name.slice(0, -1) + 'ies' : /(s|x|z|ch|sh)$/i.test(name) ? name + 'es' : name + 's';

  function notice(v) {
    const n = v.S.notice; if (!n) return '';
    return '<div class="notice notice-' + n.kind + '" role="status"><span>' + h(n.text) + '</span><button class="lnk" data-act="dismiss" aria-label="Dismiss">×</button></div>';
  }
  function modeBanner(v) {
    if (v.mode !== 'demo') return '';
    return '<div class="demo-banner">Demo mode — ' + h(v.modeReason) + '. Data lives only in this browser. <button class="lnk" data-act="resetDemo">Clear demo data</button></div>';
  }
  function roleSelect(v) {
    return '<label class="role"><span>Acting as</span><select data-act="role" aria-label="Role">' + v.M.roles.map((r) => '<option' + (r === v.role ? ' selected' : '') + '>' + h(r) + '</option>').join('') + '</select></label>';
  }
  function stagePill(v, record, stage) {
    const idx = v.stagesOf(record).indexOf(stage);
    return '<span class="stage s' + (idx < 0 ? 0 : idx) + (v.isTerminal(record, stage) ? ' terminal' : '') + '">' + h(stage) + '</span>';
  }

  // ---- list cells / cards
  function cells(v, record, row) {
    return v.rec(record).fields.map((f) => '<td>' + h(v.display(f, row)) + '</td>').join('') + (v.rec(record).has_stage ? '<td>' + stagePill(v, record, row.stage) + '</td>' : '');
  }
  function headers(v, record) {
    return v.rec(record).fields.map((f) => '<th>' + h(f.name) + '</th>').join('') + (v.rec(record).has_stage ? '<th>Stage</th>' : '');
  }
  function cardSummary(v, record, row, n) {
    const fs = v.rec(record).fields.filter((f) => f.name !== v.rec(record).title_field).slice(0, n || 3);
    return fs.map((f) => { const d = v.display(f, row); return d ? '<span class="kv"><i>' + h(f.name) + '</i> ' + h(d) + '</span>' : ''; }).join('');
  }

  // ---- forms
  function newForm(v, record, opts) {
    opts = opts || {};
    const attrs = 'data-act="create" data-record="' + h(record) + '"' + (opts.parent ? ' data-parent="' + h(opts.parent) + '" data-parent-id="' + h(opts.parentId) + '"' : '');
    return '<form class="frm" ' + attrs + '><div class="fields">' + v.fieldRows(record, null, { lockedParent: opts.parent, parentId: opts.parentId }) + '</div>' +
      '<div class="frm-actions"><button type="submit" class="btn primary" data-act="create">Create ' + h(record) + '</button>' +
      (opts.cancel ? '<button type="button" class="btn" data-act="' + opts.cancel.act + '" ' + (opts.cancel.attrs || '') + '>Cancel</button>' : '') + '</div></form>';
  }
  function editForm(v, record, row) {
    return '<form class="frm" data-act="save" data-record="' + h(record) + '" data-id="' + h(row.id) + '"><div class="fields">' + v.fieldRows(record, row) + '</div>' +
      '<div class="frm-actions"><button type="submit" class="btn primary" data-act="save">Save</button></div></form>';
  }
  function readOnly(v, record, row) {
    return '<dl class="ro">' + v.rec(record).fields.map((f) => '<div><dt>' + h(f.name) + '</dt><dd>' + (h(v.display(f, row)) || '<span class="muted">—</span>') + '</dd></div>').join('') + '</dl>';
  }
  function publicForm(v, name) {
    const fm = v.M.forms[name]; const d = v.rec(fm.record);
    const fields = fm.fields.map((sl) => d.fields.find((f) => f.slug === sl)).filter(Boolean);
    return '<form class="frm public" data-act="submitForm" data-form="' + h(name) + '"><div class="fields">' +
      fields.map((f) => '<label class="fld"><span class="fld-l">' + h(f.name) + (f.required === 'yes' ? ' <b>*</b>' : '') + '</span>' + v.control(f, null) + '</label>').join('') +
      '</div><div class="frm-actions"><button type="submit" class="btn primary" data-act="submitForm">Submit</button></div></form>';
  }

  // ---- lifecycle + actions for one row
  function lifecycle(v, record, row) {
    if (!v.rec(record).has_stage) return '';
    const stages = v.stagesOf(record); const cur = stages.indexOf(row.stage);
    const rail = '<ol class="rail">' + stages.map((s, i) => '<li class="' + (i < cur ? 'past' : i === cur ? 'now' : '') + (v.isTerminal(record, s) ? ' terminal' : '') + '">' + h(s) + '</li>').join('') + '</ol>';
    const moves = v.movesFor(record, row, v.role);
    const ap = v.approvalState(record, row);
    let gate = '';
    if (ap) {
      const who = (ap.gate.approvers || []).join(', ');
      if (ap.decision && ap.decision.decision === 'APPROVED') gate = '<p class="gate ok">Approved by ' + h(ap.decision.decided_by) + (ap.decision.reason ? ' — ' + h(ap.decision.reason) : '') + '. It may move on.</p>';
      else gate = '<p class="gate wait">Waiting in <b>' + h(row.stage) + '</b> for <b>' + h(who) + '</b> to approve.</p>';
      if (ap.mayDecide && !(ap.decision && ap.decision.decision === 'APPROVED')) {
        gate += '<form class="decide" data-act="approve" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-decision="APPROVED">' +
          '<input name="reason" placeholder="Reason (optional)">' +
          '<button type="submit" class="btn primary" data-act="approve" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-decision="APPROVED">Approve</button>' +
          '<button type="button" class="btn danger" data-act="approve" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-decision="DECLINED">Decline</button></form>';
      }
    }
    const btns = moves.length ? '<div class="moves">' + moves.map((t) => '<button class="btn move" data-act="move" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-to="' + h(t.to) + '">→ ' + h(t.to) + '</button>').join('') + '</div>' :
      (v.rec(record).has_stage ? '<p class="muted small">' + (v.isTerminal(record, row.stage) ? 'Finished stage.' : 'No move you can make from here as ' + h(v.role) + '.') + '</p>' : '');
    return '<section class="life"><h3>Lifecycle</h3>' + rail + gate + btns + '</section>';
  }
  function customActions(v, record, row) {
    const acts = v.actionsFor(record, v.role); if (!acts.length) return '';
    const pend = v.S.inputsFor;
    return '<section class="acts"><h3>Actions</h3>' + acts.map((a) => {
      const ex = a.execution || {};
      let html = '<div class="act"><button class="btn" data-act="action" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-action="' + h(a.name) + '">' + h(a.name) + '</button><span class="muted small">' + h(a.effect) + '</span></div>';
      if (pend && pend.record === record && pend.id === row.id && pend.action === a.name) {
        html += '<form class="inputs" data-act="action" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-action="' + h(a.name) + '">' +
          ex.fields.map((f) => '<label class="fld"><span class="fld-l">' + h(f.replace(/_/g, ' ')) + '</span><input name="' + h(f) + '" required autofocus></label>').join('') +
          '<button type="submit" class="btn primary" data-act="action">Confirm ' + h(a.name) + '</button><button type="button" class="btn" data-act="cancelInputs">Cancel</button></form>';
      }
      return html;
    }).join('') + '</section>';
  }
  function related(v, record, row) {
    const kids = v.childRows(record, row.id); if (!kids.length) return '';
    return kids.map((k) => {
      const canAdd = v.canCreate(k.record);
      const adding = v.S.view.kind === 'new' && v.S.view.record === k.record && v.S.view.parentId === row.id;
      return '<section class="related"><h3>' + h(plural(k.record)) + ' <span class="count">' + k.rows.length + '</span></h3>' +
        (k.rows.length ? '<ul class="mini">' + k.rows.map((r) => '<li><a href="#" data-act="open" data-record="' + h(k.record) + '" data-id="' + h(r.id) + '">' + h(v.titleOf(k.record, r)) + '</a> <span class="muted small">' + h(cardText(v, k.record, r)) + '</span>' +
          (v.canDelete(k.record) ? ' <button class="lnk danger" data-act="remove" data-record="' + h(k.record) + '" data-id="' + h(r.id) + '" data-confirm="Delete this ' + h(k.record) + '?">delete</button>' : '') + '</li>').join('') + '</ul>' : '<p class="muted small">None yet.</p>') +
        (canAdd ? (adding ? newForm(v, k.record, { parent: record, parentId: row.id, cancel: { act: 'open', attrs: 'data-record="' + h(record) + '" data-id="' + h(row.id) + '"' } }) :
          '<button class="btn small" data-act="newRow" data-record="' + h(k.record) + '" data-parent="' + h(record) + '" data-parent-id="' + h(row.id) + '">+ Add ' + h(k.record) + '</button>') : '') + '</section>';
    }).join('');
  }
  function cardText(v, record, row) {
    return v.rec(record).fields.filter((f) => f.name !== v.rec(record).title_field && !(f.type === 'link')).slice(0, 2).map((f) => v.display(f, row)).filter(Boolean).join(' · ');
  }
  function trail(v) {
    const d = v.S.detail; if (!d) return '';
    const items = (d.history.audit || []).map((a) => ({ at: a.at, text: a.action.startsWith('transition') ? 'Moved ' + h((a.before || {}).stage) + ' → ' + h((a.after || {}).stage) + ' by ' + h((a.after || {}).by || 'system') :
      a.action.startsWith('approval:') ? h((a.after || {}).decision) + ' by ' + h((a.after || {}).by) + ((a.after || {}).reason ? ' — ' + h(a.after.reason) : '') :
      a.action.startsWith('custom:') ? h(a.action.slice(7)) + (a.after && a.after.cloned_to ? ' → copy ' + h(String(a.after.cloned_to).slice(0, 8)) : a.after && a.after.document ? ' → ' + h(a.after.document) : a.after ? ' ' + h(JSON.stringify(a.after)) : '') : h(a.action) }));
    if (!items.length) return '<section class="trail"><h3>Activity</h3><p class="muted small">Nothing yet.</p></section>';
    return '<section class="trail"><h3>Activity</h3><ul>' + items.map((i) => '<li><time>' + h(fmtTime(i.at)) + '</time> ' + i.text + '</li>').join('') + '</ul></section>';
  }
  function docModal(v) {
    const d = v.S.docShown; if (!d) return '';
    return '<div class="overlay" data-act="closeDoc"><div class="modal doc"><div class="modal-h"><b>Generated document</b>' + (d.pdf ? ' <a class="btn small" href="' + h(d.pdf) + '" target="_blank" rel="noopener">Open PDF</a>' : '') + '<button class="lnk" data-act="closeDoc" aria-label="Close">×</button></div><div class="doc-body">' + d.html + '</div></div></div>';
  }
  function reportBody(v, name) {
    const rv = v.reportView(name); const rp = rv.rp;
    let body = '';
    if (rv.error) body = '<p class="notice notice-err">' + h(rv.error) + '</p>';
    else if (!rv.data) body = '<p class="muted">Loading…</p>';
    else body = rp.metrics.map((m) => '<div class="metric"><h4>' + h(m) + '</h4>' + metricView(rv.data[m]) + '</div>').join('');
    return '<div class="report"><p class="question">' + h(rp.question) + '</p>' + body + '<button class="btn small" data-act="runReport" data-report="' + h(name) + '">Refresh</button></div>';
  }
  function metricView(val) {
    if (val == null) return '<p class="muted">No data yet.</p>';
    if (typeof val === 'number') return '<p class="big">' + h(Number.isInteger(val) ? val : val.toFixed(2)) + '</p>';
    if (typeof val === 'object' && 'percentage' in val) return '<p class="big">' + (val.percentage == null ? '—' : h(Number(val.percentage).toFixed(1)) + '%') + '</p><p class="muted small">' + h(val.numerator) + ' of ' + h(val.denominator) + ' in the last ' + h(val.window_days) + ' days</p>';
    if (typeof val === 'object') {
      const entries = Object.entries(val); if (!entries.length) return '<p class="muted">Nothing to count yet.</p>';
      const max = Math.max.apply(null, entries.map(([, x]) => Number(x) || 0)) || 1;
      return '<ul class="bars">' + entries.map(([k, x]) => '<li><span class="bar-l">' + h(k) + '</span><span class="bar"><i style="width:' + Math.round((Number(x) || 0) / max * 100) + '%"></i></span><span class="bar-v">' + h(Number.isInteger(Number(x)) ? x : Number(x).toFixed(2)) + '</span></li>').join('') + '</ul>';
    }
    return '<p>' + h(JSON.stringify(val)) + '</p>';
  }
  function detailBody(v) {
    const d = v.S.detail; if (!d) return '';
    const canEdit = v.canEdit(d.record);
    return (canEdit ? editForm(v, d.record, d.row) : readOnly(v, d.record, d.row)) + lifecycle(v, d.record, d.row) + customActions(v, d.record, d.row) + related(v, d.record, d.row) + trail(v) +
      (v.canDelete(d.record) ? '<p class="danger-zone"><button class="btn danger" data-act="remove" data-record="' + h(d.record) + '" data-id="' + h(d.row.id) + '" data-confirm="Delete this ' + h(d.record) + '?">Delete ' + h(d.record) + '</button></p>' : '');
  }
  return { h, plural, notice, modeBanner, roleSelect, stagePill, cells, headers, cardSummary, cardText, newForm, editForm, readOnly, publicForm, lifecycle, customActions, related, trail, docModal, reportBody, metricView, detailBody };
})();
