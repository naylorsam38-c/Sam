/* console.js — Design 1 "Console": left sidebar, data tables, right slide-over detail. */
window.DESIGN = (function () {
  'use strict';
  const P = window.PARTS; const h = P.h;
  function sidebar(v) {
    const cur = v.S.view;
    const item = (act, label, extra, on) => '<a href="#" class="nav' + (on ? ' on' : '') + '" data-act="' + act + '" ' + extra + '>' + label + '</a>';
    return '<aside class="side"><div class="brand"><span class="mark"></span><b>' + h(v.M.app_name) + '</b><small>' + h(v.M.family) + '</small></div>' +
      '<nav>' + item('home', 'Overview', '', cur.kind === 'home') +
      '<div class="grp">Records</div>' + v.visibleRecords.map((r) => item('nav', h(P.plural(r)) + ' <span class="n">' + v.rowsOf(r).length + '</span>', 'data-kind="list" data-record="' + h(r) + '"', (cur.kind === 'list' || cur.kind === 'detail' || cur.kind === 'new') && cur.record === r)).join('') +
      (v.reports.length ? '<div class="grp">Reports</div>' + v.reports.map((r) => item('nav', h(r), 'data-kind="report" data-report="' + h(r) + '"', cur.kind === 'report' && cur.report === r)).join('') : '') +
      (v.forms.length ? '<div class="grp">Forms</div>' + v.forms.map((f) => item('nav', h(f), 'data-kind="form" data-form="' + h(f) + '"', cur.kind === 'form' && cur.form === f)).join('') : '') +
      '</nav><div class="side-foot">' + P.roleSelect(v) + '</div></aside>';
  }
  function home(v) {
    const cards = v.visibleRecords.map((r) => '<a href="#" class="tile" data-act="nav" data-kind="list" data-record="' + h(r) + '"><b>' + v.rowsOf(r).length + '</b><span>' + h(P.plural(r)) + '</span></a>').join('');
    const stages = v.visibleRecords.filter((r) => v.rec(r).has_stage).map((r) => {
      const counts = {}; v.rowsOf(r).forEach((x) => { counts[x.stage] = (counts[x.stage] || 0) + 1; });
      return '<div class="panel"><h3>' + h(r) + ' by stage</h3><div class="stagebar">' + v.stagesOf(r).map((s) => '<span>' + P.stagePill(v, r, s) + ' <b>' + (counts[s] || 0) + '</b></span>').join('') + '</div></div>';
    }).join('');
    const landing = v.M.landing_per_role[v.role];
    return '<header class="top"><h1>Overview</h1><span class="muted">' + h(v.role) + (landing ? ' · lands on ' + h(landing) : '') + '</span></header><div class="tiles">' + cards + '</div>' + stages +
      (v.reports.length ? '<div class="panel"><h3>Reports</h3><div class="links">' + v.reports.map((r) => '<a href="#" class="btn" data-act="nav" data-kind="report" data-report="' + h(r) + '">' + h(r) + '</a>').join('') + '</div></div>' : '');
  }
  function list(v, record) {
    const rows = v.rowsOf(record); const d = v.rec(record);
    return '<header class="top"><h1>' + h(P.plural(record)) + '</h1>' + (v.canCreate(record) ? '<button class="btn primary" data-act="newRow" data-record="' + h(record) + '">New ' + h(record) + '</button>' : '<span class="muted small">' + h(v.role) + ' cannot create</span>') + '</header>' +
      (rows.length ? '<div class="tbl-wrap"><table class="tbl"><thead><tr>' + P.headers(v, record) + '<th></th></tr></thead><tbody>' +
        rows.map((r) => '<tr data-act="open" data-record="' + h(record) + '" data-id="' + h(r.id) + '" class="row">' + P.cells(v, record, r) + '<td class="r"><button class="lnk" data-act="open" data-record="' + h(record) + '" data-id="' + h(r.id) + '">Open</button></td></tr>').join('') + '</tbody></table></div>'
        : '<div class="empty"><p>No ' + h(P.plural(record).toLowerCase()) + ' yet.</p>' + (v.canCreate(record) ? '<button class="btn primary" data-act="newRow" data-record="' + h(record) + '">Create the first ' + h(record) + '</button>' : '') + '</div>') +
      (d.has_stage ? '<p class="muted small">Stages: ' + v.stagesOf(record).map((s) => P.stagePill(v, record, s)).join(' ') + '</p>' : '');
  }
  function newPage(v, record) {
    return '<header class="top"><h1>New ' + h(record) + '</h1><button class="btn" data-act="nav" data-kind="list" data-record="' + h(record) + '">Cancel</button></header><div class="panel">' + P.newForm(v, record) + '</div>';
  }
  function slideover(v) {
    const d = v.S.detail; if (!d) return '';
    return '<div class="scrim" data-act="back"></div><section class="drawer" aria-label="' + h(d.record) + ' detail"><div class="drawer-h"><div><small>' + h(d.record) + '</small><h2>' + h(v.titleOf(d.record, d.row)) + '</h2></div>' + (d.row.stage ? P.stagePill(v, d.record, d.row.stage) : '') + '<button class="lnk big" data-act="back" aria-label="Close">×</button></div><div class="drawer-b">' + P.detailBody(v) + '</div></section>';
  }
  function report(v, name) { return '<header class="top"><h1>' + h(name) + '</h1></header><div class="panel">' + P.reportBody(v, name) + '</div>'; }
  function form(v, name) { const fm = v.M.forms[name]; return '<header class="top"><h1>' + h(name) + '</h1><span class="muted small">creates a ' + h(fm.record) + '</span></header><div class="panel narrow">' + P.publicForm(v, name) + '</div>'; }
  function render(v) {
    const cur = v.S.view; let main = '';
    if (cur.kind === 'home') main = home(v);
    else if (cur.kind === 'list' || cur.kind === 'detail' || (cur.kind === 'new' && cur.parent)) main = list(v, cur.record === undefined ? v.S.detail.record : (cur.kind === 'new' ? cur.parent : cur.record));
    else if (cur.kind === 'new') main = newPage(v, cur.record);
    else if (cur.kind === 'report') main = report(v, cur.report);
    else if (cur.kind === 'form') main = form(v, cur.form);
    return P.modeBanner(v) + '<div class="shell">' + sidebar(v) + '<main class="main">' + P.notice(v) + main + '</main></div>' + slideover(v) + P.docModal(v);
  }
  return { render };
})();
