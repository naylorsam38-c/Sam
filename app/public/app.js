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

// --- Plan -------------------------------------------------------------

function block(title, node, className = '') {
  const wrap = document.createElement('div');
  wrap.className = `plan-block ${className}`.trim();
  const h = document.createElement('h3');
  h.textContent = title;
  wrap.append(h, node);
  return wrap;
}

function list(items, ordered) {
  const el = document.createElement(ordered ? 'ol' : 'ul');
  for (const item of items) {
    const li = document.createElement('li');
    li.textContent = item;
    el.append(li);
  }
  return el;
}

function paragraph(text) {
  const p = document.createElement('p');
  p.style.margin = '0';
  p.textContent = text;
  return p;
}

function renderPlan(data) {
  const out = $('#plan-output');
  out.replaceChildren();

  if (!data.plan) {
    out.append(block('Plan', paragraph(data.raw || 'No plan returned.')));
    return;
  }

  const p = data.plan;
  if (p.overview) out.append(block('Overview', paragraph(p.overview)));
  if (p.key_parts?.length) out.append(block('Key parts', list(p.key_parts, false)));
  if (p.build_order?.length) out.append(block('Build order', list(p.build_order, true)));
  if (p.risks?.length) out.append(block('Risks', list(p.risks, false)));
  if (p.next_action) out.append(block('Next action', paragraph(p.next_action), 'next'));
}

$('#plan-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const goal = $('#plan-input').value.trim();
  if (!goal) return;

  const go = $('#plan-go');
  go.disabled = true;
  go.textContent = 'Planning…';
  $('#plan-output').replaceChildren();

  try {
    renderPlan(await api('/api/plan', { method: 'POST', body: { goal } }));
  } catch (ex) {
    const err = document.createElement('div');
    err.className = 'msg error';
    err.textContent = ex.message;
    $('#plan-output').append(err);
  } finally {
    go.disabled = false;
    go.textContent = 'Plan an idea';
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
