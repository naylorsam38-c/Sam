'use strict';

const $ = (sel) => document.querySelector(sel);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// --- Login ------------------------------------------------------------

async function showApp() {
  $('#login').hidden = true;
  $('#app').hidden = false;
  await loadTasks();
}

$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const err = $('#login-error');
  err.hidden = true;
  try {
    await api('/api/login', { method: 'POST', body: { password: $('#password').value } });
    $('#password').value = '';
    await showApp();
  } catch (ex) {
    err.textContent = ex.message;
    err.hidden = false;
  }
});

$('#logout').addEventListener('click', async () => {
  await api('/api/logout', { method: 'POST' }).catch(() => {});
  location.reload();
});

// --- Tabs -------------------------------------------------------------

for (const tab of document.querySelectorAll('.tab')) {
  tab.addEventListener('click', () => {
    for (const t of document.querySelectorAll('.tab')) t.classList.toggle('active', t === tab);
    for (const p of document.querySelectorAll('.panel')) {
      p.classList.toggle('active', p.id === `panel-${tab.dataset.tab}`);
    }
  });
}

// --- Chat -------------------------------------------------------------

const history = [];

function addMessage(role, text, extraClass = '') {
  const el = document.createElement('div');
  el.className = `msg ${role} ${extraClass}`.trim();
  el.textContent = text;
  $('#messages').append(el);
  el.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return el;
}

$('#chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('#chat-input');
  const text = input.value.trim();
  if (!text) return;

  addMessage('user', text);
  history.push({ role: 'user', content: text });
  input.value = '';

  const send = $('#chat-send');
  send.disabled = true;
  const pending = addMessage('assistant', 'Thinking…', 'pending');

  try {
    const data = await api('/api/chat', { method: 'POST', body: { messages: history } });
    pending.remove();
    addMessage('assistant', data.reply);
    history.push({ role: 'assistant', content: data.reply });
  } catch (ex) {
    pending.remove();
    addMessage('assistant', ex.message, 'error');
    history.pop(); // drop the unanswered turn so the next call isn't malformed
  } finally {
    send.disabled = false;
  }
});

// --- Case: the complex-request lifecycle ------------------------------
// The screen shows the state, who owns it, and only the decisions that are
// Sam's to make. It never offers a control the state machine would refuse.

let current = null;

function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
}

// Phases and tasks arrive as objects carrying the reference that ties them to
// the approved goal. That reference is the point of PLN-004, so it is shown
// rather than buried in a JSON dump.
function list(items, ordered) {
  const n = el(ordered ? 'ol' : 'ul');
  for (const item of items || []) {
    const li = el('li');
    if (typeof item === 'string') {
      li.textContent = item;
    } else if (item && (item.name || item.title)) {
      li.append(el('span', 'item-name', item.name || item.title));
      const tail = item.done_when || item.outcome;
      if (tail) li.append(el('span', 'item-tail', ` — ${tail}`));
      if (item.owner) li.append(el('span', 'item-owner', item.owner));
      if (item.ref) li.append(el('span', 'item-ref', item.ref));
    } else {
      li.textContent = JSON.stringify(item);
    }
    n.append(li);
  }
  return n;
}

function block(title, node, className = '') {
  const wrap = el('div', `plan-block ${className}`.trim());
  wrap.append(el('h3', null, title), node);
  return wrap;
}

function fields(obj, keys) {
  const dl = el('dl', 'fields');
  for (const k of keys) {
    const v = obj?.[k];
    if (v === undefined || v === null || (Array.isArray(v) && !v.length)) continue;
    dl.append(el('dt', null, k.replace(/_/g, ' ')));
    const dd = el('dd');
    if (Array.isArray(v)) dd.append(list(v, false));
    else dd.textContent = typeof v === 'string' ? v : JSON.stringify(v);
    dl.append(dd);
  }
  return dl;
}

async function act(path, body) {
  const out = $('#case-output');
  out.classList.add('busy');
  try {
    const data = await api(path, { method: 'POST', body: body || {} });
    current = data.case;
    renderCase();
  } catch (ex) {
    const err = el('p', 'error', ex.message);
    out.prepend(err);
  } finally {
    out.classList.remove('busy');
  }
}

// Sam is offered exactly the decisions the current state permits — nothing
// else is a button, so the screen cannot ask for a transition that would be
// refused.
const DECISIONS = {
  goal_review: [
    { label: 'Approve the goal', primary: true, run: () => act(`/api/case/${current.id}/goal/approve`) },
    { label: 'Send it back', run: () => act(`/api/case/${current.id}/goal/reject`, { reason: 'returned by Sam' }) },
  ],
  goal_approved: [
    { label: 'Plan it', primary: true, run: () => act(`/api/case/${current.id}/plan`) },
  ],
  plan_review: [
    { label: 'Approve the plan', primary: true, run: () => act(`/api/case/${current.id}/plan/approve`) },
    { label: 'Send it back', run: () => act(`/api/case/${current.id}/plan/reject`, { reason: 'returned by Sam' }) },
  ],
};

function renderCase() {
  const out = $('#case-output');
  out.replaceChildren();
  if (!current) return;

  const head = el('div', 'case-head');
  head.append(el('span', 'state', current.state.replace(/_/g, ' ')));
  head.append(el('span', 'owner', `owner: ${current.owner}`));
  if (current.timeout_ms) head.append(el('span', 'timeout', `${current.timeout_ms / 1000}s timeout`));
  out.append(head);

  if (current.locked_goal) {
    const g = el('div', 'locked');
    g.append(el('strong', null, 'Locked goal'), el('p', null, current.locked_goal),
             el('code', null, current.locked_goal_id));
    out.append(g);
  }

  if (current.goal_package) {
    out.append(block(current.locked_goal ? 'Goal package (approved)' : 'Goal package — your decision',
      fields(current.goal_package, ['locked_goal_candidate', 'scope', 'exclusions', 'constraints',
        'assumptions', 'success_criteria', 'known_risks', 'unresolved_questions', 'confidence', 'evidence'])));
  }

  if (current.plan) {
    const p = el('div');
    p.append(fields(current.plan, ['phases', 'tasks', 'dependencies', 'owners', 'required_inputs',
      'evidence_requirements', 'decision_gates', 'risks', 'rollback', 'completion_criteria', 'final_verification']));
    out.append(block(current.plan_id ? 'Implementation plan (approved)' : 'Implementation plan — your decision', p));
  }

  const decisions = DECISIONS[current.state];
  if (decisions) {
    const row = el('div', 'decisions');
    for (const d of decisions) {
      const b = el('button', d.primary ? 'primary' : 'ghost', d.label);
      b.addEventListener('click', d.run);
      row.append(b);
    }
    out.append(row);
  }

  // The audit trail is the record of how the case moved, not a status message.
  const trail = el('ol', 'audit');
  for (const row of current.audit || []) {
    const li = el('li');
    li.append(el('span', 'ev', row.event));
    if (row.to) li.append(el('span', 'to', `→ ${row.to}`));
    if (row.requirement) li.append(el('span', 'req', row.requirement));
    if (row.reason) li.append(el('span', 'why', row.reason));
    trail.append(li);
  }
  out.append(block('Audit trail', trail, 'trail'));
}

$('#case-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const request = $('#case-input').value.trim();
  if (!request) return;

  const go = $('#case-go');
  go.disabled = true;
  go.textContent = 'Forming the goal…';
  $('#case-output').replaceChildren();

  try {
    const data = await api('/api/case', { method: 'POST', body: { request } });
    current = data.case;
    renderCase();
  } catch (ex) {
    $('#case-output').append(el('p', 'error', ex.message));
  } finally {
    go.disabled = false;
    go.textContent = 'Start';
  }
});

// --- Tasks ------------------------------------------------------------

function renderTasks(tasks) {
  const list = $('#task-list');
  list.replaceChildren();

  if (!tasks.length) {
    const empty = document.createElement('li');
    empty.className = 'empty';
    empty.textContent = 'No tasks yet.';
    empty.style.background = 'none';
    empty.style.border = 'none';
    list.append(empty);
    return;
  }

  for (const task of tasks) {
    const li = document.createElement('li');
    if (task.done) li.classList.add('done');

    const box = document.createElement('input');
    box.type = 'checkbox';
    box.checked = task.done;
    box.addEventListener('change', async () => {
      await api('/api/tasks', { method: 'PATCH', body: { id: task.id, done: box.checked } });
      await loadTasks();
    });

    const title = document.createElement('span');
    title.className = 'title';
    title.textContent = task.title;

    const del = document.createElement('button');
    del.className = 'del';
    del.type = 'button';
    del.textContent = '×';
    del.setAttribute('aria-label', `Delete ${task.title}`);
    del.addEventListener('click', async () => {
      await api('/api/tasks', { method: 'DELETE', body: { id: task.id } });
      await loadTasks();
    });

    li.append(box, title, del);
    list.append(li);
  }
}

async function loadTasks() {
  try {
    renderTasks((await api('/api/tasks')).tasks);
  } catch { /* not logged in yet */ }
}

$('#task-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('#task-input');
  const title = input.value.trim();
  if (!title) return;
  input.value = '';
  await api('/api/tasks', { method: 'POST', body: { title } });
  await loadTasks();
});

// --- Boot -------------------------------------------------------------

api('/api/me')
  .then((data) => { if (data.authed) showApp(); })
  .catch(() => {});
