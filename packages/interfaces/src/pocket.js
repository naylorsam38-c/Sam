/* pocket.js — Design 3 "Pocket": mobile-first. Bottom tab bar, card lists with big
   tap targets, full-screen detail pages with a back button, a floating "New"
   button, an action sheet for moves/actions, stat tiles on Home. */
window.DESIGN = (function () {
  'use strict';
  const P = window.PARTS; const h = h_; function h_(s) { return P.h(s); }
  const ICONS = { home: '⌂', rec: '▤', rep: '◔', form: '✎', more: '⋯' };
  function tabbar(v) {
    const cur = v.S.view;
    const tabs = [{ act: 'home', label: 'Home', icon: ICONS.home, on: cur.kind === 'home', extra: '' }]
      .concat(v.visibleRecords.slice(0, 3).map((r) => ({ act: 'nav', label: P.plural(r), icon: ICONS.rec, on: ['list', 'detail', 'new'].includes(cur.kind) && (cur.record === r || cur.parent === r), extra: 'data-kind="list" data-record="' + h(r) + '"' })))
      .concat([{ act: 'nav', label: 'More', icon: ICONS.more, on: cur.kind === 'more', extra: 'data-kind="more"' }]);
    return '<nav class="tabbar">' + tabs.map((t) => '<a href="#" class="tb' + (t.on ? ' on' : '') + '" data-act="' + t.act + '" ' + t.extra + '><span class="ic">' + t.icon + '</span><span>' + h(t.label) + '</span></a>').join('') + '</nav>';
  }
  function topbar(v, title, back, right) {
    return '<header class="topbar">' + (back ? '<button class="back" data-act="' + back.act + '" ' + (back.attrs || '') + ' aria-label="Back">‹</button>' : '<span class="spacer"></span>') + '<h1>' + h(title) + '</h1>' + (right || '<span class="spacer"></span>') + '</header>';
  }
  function home(v) {
    const stats = v.visibleRecords.map((r) => '<a href="#" class="stat" data-act="nav" data-kind="list" data-record="' + h(r) + '"><b>' + v.rowsOf(r).length + '</b><span>' + h(P.plural(r)) + '</span></a>').join('');
    const reps = v.reports.map((name) => { const rv = v.reportView(name); return '<section class="sheet-card"><h3>' + h(name) + '</h3>' + (rv.data ? P.reportBody(v, name) : '<p class="muted small">' + h(rv.rp.question) + '</p><button class="btn small" data-act="runReport" data-report="' + h(name) + '">Run</button>') + '</section>'; }).join('');
    return topbar(v, v.M.app_name, null, '<span class="who">' + h(v.role) + '</span>') + '<div class="body"><section class="rolebox">' + P.roleSelect(v) + '</section><div class="stats">' + stats + '</div>' + reps + '</div>';
  }
  function more(v) {
    return topbar(v, 'More') + '<div class="body"><ul class="menu">' +
      v.visibleRecords.map((r) => '<li><a href="#" data-act="nav" data-kind="list" data-record="' + h(r) + '"><span class="ic">' + ICONS.rec + '</span>' + h(P.plural(r)) + '<span class="n">' + v.rowsOf(r).length + '</span></a></li>').join('') +
      v.reports.map((r) => '<li><a href="#" data-act="nav" data-kind="report" data-report="' + h(r) + '"><span class="ic">' + ICONS.rep + '</span>' + h(r) + '</a></li>').join('') +
      v.forms.map((f) => '<li><a href="#" data-act="nav" data-kind="form" data-form="' + h(f) + '"><span class="ic">' + ICONS.form + '</span>' + h(f) + '</a></li>').join('') +
      '</ul><section class="rolebox">' + P.roleSelect(v) + '</section></div>';
  }
  function list(v, record) {
    const rows = v.rowsOf(record); const d = v.rec(record);
    const cards = rows.map((r) => '<a href="#" class="rowcard" data-act="open" data-record="' + h(record) + '" data-id="' + h(r.id) + '"><div class="rc-main"><b>' + h(v.titleOf(record, r)) + '</b><span class="muted small">' + h(P.cardText(v, record, r)) + '</span></div>' + (d.has_stage ? P.stagePill(v, record, r.stage) : '') + '<span class="chev">›</span></a>').join('');
    return topbar(v, P.plural(record), { act: 'home' }) + '<div class="body">' + (cards || '<div class="empty">No ' + h(P.plural(record).toLowerCase()) + ' yet.</div>') + '</div>' +
      (v.canCreate(record) ? '<button class="fab" data-act="newRow" data-record="' + h(record) + '" aria-label="New ' + h(record) + '">+</button>' : '');
  }
  function detail(v) {
    const d = v.S.detail;
    return topbar(v, v.titleOf(d.record, d.row), { act: 'back' }, d.row.stage ? P.stagePill(v, d.record, d.row.stage) : '<span class="spacer"></span>') + '<div class="body detail">' + P.detailBody(v) + '</div>';
  }
  function newPage(v, record) {
    return topbar(v, 'New ' + record, { act: 'nav', attrs: 'data-kind="list" data-record="' + h(record) + '"' }) + '<div class="body">' + P.newForm(v, record) + '</div>';
  }
  function render(v) {
    const cur = v.S.view; let page = '';
    if (cur.kind === 'home') page = home(v);
    else if (cur.kind === 'more') page = more(v);
    else if (cur.kind === 'list') page = list(v, cur.record);
    else if (cur.kind === 'detail' || (cur.kind === 'new' && cur.parent)) page = detail(v);
    else if (cur.kind === 'new') page = newPage(v, cur.record);
    else if (cur.kind === 'report') page = topbar(v, cur.report, { act: 'nav', attrs: 'data-kind="more"' }) + '<div class="body"><section class="sheet-card">' + P.reportBody(v, cur.report) + '</section></div>';
    else if (cur.kind === 'form') page = topbar(v, cur.form, { act: 'nav', attrs: 'data-kind="more"' }) + '<div class="body"><section class="sheet-card">' + P.publicForm(v, cur.form) + '</section></div>';
    return '<div class="phone">' + P.modeBanner(v) + '<div class="screen">' + page + P.notice(v) + '</div>' + tabbar(v) + '</div>' + P.docModal(v);
  }
  return { render };
})();
