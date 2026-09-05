/* board.js — Design 2 "Board": top tabs, kanban columns for records with a lifecycle,
   card grids for the rest, a centred modal for detail, reports as tiles on Overview. */
window.DESIGN = (function () {
  'use strict';
  const P = window.PARTS; const h = P.h;
  function header(v) {
    const cur = v.S.view;
    const tab = (act, label, extra, on) => '<a href="#" class="tab' + (on ? ' on' : '') + '" data-act="' + act + '" ' + extra + '>' + label + '</a>';
    return '<header class="hdr"><div class="brand"><span class="dot"></span><b>' + h(v.M.app_name) + '</b></div><nav class="tabs">' +
      tab('home', 'Overview', '', cur.kind === 'home') +
      v.visibleRecords.map((r) => tab('nav', h(P.plural(r)), 'data-kind="list" data-record="' + h(r) + '"', ['list', 'detail', 'new'].includes(cur.kind) && (cur.record === r || cur.parent === r))).join('') +
      v.forms.map((f) => tab('nav', h(f), 'data-kind="form" data-form="' + h(f) + '"', cur.kind === 'form' && cur.form === f)).join('') +
      '</nav><div class="hdr-r">' + P.roleSelect(v) + '</div></header>';
  }
  function card(v, record, row) {
    const moves = v.movesFor(record, row, v.role);
    return '<article class="card" data-act="open" data-record="' + h(record) + '" data-id="' + h(row.id) + '"><h4>' + h(v.titleOf(record, row)) + '</h4><div class="kvs">' + P.cardSummary(v, record, row, 3) + '</div>' +
      (moves.length ? '<div class="card-moves">' + moves.map((t) => '<button class="chip" data-act="move" data-record="' + h(record) + '" data-id="' + h(row.id) + '" data-to="' + h(t.to) + '">' + h(t.to) + ' →</button>').join('') + '</div>' : '') + '</article>';
  }
  function kanban(v, record) {
    const rows = v.rowsOf(record);
    return '<div class="kanban">' + v.stagesOf(record).map((s, i) => {
      const inStage = rows.filter((r) => r.stage === s);
      return '<section class="col c' + i + (v.isTerminal(record, s) ? ' terminal' : '') + '"><h3>' + h(s) + ' <span class="n">' + inStage.length + '</span></h3><div class="col-b">' + (inStage.map((r) => card(v, record, r)).join('') || '<p class="muted small">Empty</p>') + '</div></section>';
    }).join('') + '</div>';
  }
  function grid(v, record) {
    const rows = v.rowsOf(record);
    return rows.length ? '<div class="grid">' + rows.map((r) => card(v, record, r)).join('') + '</div>' : '<div class="empty">No ' + h(P.plural(record).toLowerCase()) + ' yet.</div>';
  }
  function list(v, record) {
    return '<div class="page-h"><h1>' + h(P.plural(record)) + '</h1><span class="muted">' + v.rowsOf(record).length + '</span>' + (v.canCreate(record) ? '<button class="btn primary" data-act="newRow" data-record="' + h(record) + '">+ New ' + h(record) + '</button>' : '') + '</div>' +
      (v.rec(record).has_stage ? kanban(v, record) : grid(v, record));
  }
  function home(v) {
    const counts = v.visibleRecords.map((r) => '<a href="#" class="stat" data-act="nav" data-kind="list" data-record="' + h(r) + '"><b>' + v.rowsOf(r).length + '</b><span>' + h(P.plural(r)) + '</span></a>').join('');
    const reps = v.reports.map((name) => {
      const rv = v.reportView(name);
      return '<section class="rtile"><h3>' + h(name) + '</h3>' + (rv.data ? P.reportBody(v, name) : '<p class="muted small">' + h(rv.rp.question) + '</p><button class="btn small" data-act="runReport" data-report="' + h(name) + '">Run report</button>') + '</section>';
    }).join('');
    return '<div class="page-h"><h1>Overview</h1><span class="muted">acting as ' + h(v.role) + '</span></div><div class="stats">' + counts + '</div>' + (reps ? '<div class="rtiles">' + reps + '</div>' : '');
  }
  function modal(v, inner, title, sub, closeAct, closeAttrs) {
    return '<div class="overlay" data-act="' + closeAct + '" ' + (closeAttrs || '') + '><div class="modal"><div class="modal-h"><div><small>' + h(sub) + '</small><h2>' + h(title) + '</h2></div><button class="lnk big" data-act="' + closeAct + '" ' + (closeAttrs || '') + ' aria-label="Close">×</button></div><div class="modal-b">' + inner + '</div></div></div>';
  }
  function render(v) {
    const cur = v.S.view; let page = ''; let over = '';
    if (cur.kind === 'home') page = home(v);
    else if (cur.kind === 'list') page = list(v, cur.record);
    else if (cur.kind === 'detail' || (cur.kind === 'new' && cur.parent)) { const d = v.S.detail; page = list(v, d.record); over = modal(v, P.detailBody(v), v.titleOf(d.record, d.row), d.record + (d.row.stage ? ' · ' + d.row.stage : ''), 'back'); }
    else if (cur.kind === 'new') { page = list(v, cur.record); over = modal(v, P.newForm(v, cur.record), 'New ' + cur.record, cur.record, 'nav', 'data-kind="list" data-record="' + h(cur.record) + '"'); }
    else if (cur.kind === 'report') page = '<div class="page-h"><h1>' + h(cur.report) + '</h1></div><section class="rtile wide">' + P.reportBody(v, cur.report) + '</section>';
    else if (cur.kind === 'form') page = '<div class="page-h"><h1>' + h(cur.form) + '</h1></div><section class="rtile wide">' + P.publicForm(v, cur.form) + '</section>';
    return P.modeBanner(v) + header(v) + '<main class="wrap">' + P.notice(v) + page + '</main>' + over + P.docModal(v);
  }
  return { render };
})();
