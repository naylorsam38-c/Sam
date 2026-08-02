'use strict';

// End-to-end tests for the server. Spawns a real instance plus a local stand-in
// for the Anthropic API, so the whole request path is exercised without a key.
//
//   node test.js
//
// Exits non-zero on the first failing expectation.

const http = require('node:http');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

const PORT = 8788;
const STUB_PORT = 9998;
const BASE = `http://127.0.0.1:${PORT}`;
const PASSWORD = 'correct-horse-battery';

let passed = 0;
const failures = [];

function check(name, condition, detail = '') {
  if (condition) {
    passed += 1;
    console.log(`  PASS  ${name}`);
  } else {
    failures.push(`${name}${detail ? ` — ${detail}` : ''}`);
    console.log(`  FAIL  ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

function group(title) {
  console.log(`\n${title}`);
}

// --- Anthropic stand-in -----------------------------------------------------

function startStub() {
  return new Promise((resolve) => {
    const stub = http.createServer((req, res) => {
      let body = '';
      req.on('data', (c) => (body += c));
      req.on('end', () => {
        const parsed = JSON.parse(body || '{}');
        const isPlan = /ONLY a JSON object/.test(parsed.system || '');
        const text = isPlan
          ? JSON.stringify({
              overview: 'Overview text.',
              key_parts: ['Part one', 'Part two'],
              build_order: ['Step one', 'Step two', 'Step three'],
              risks: ['A risk'],
              next_action: 'Do the first thing.',
            })
          : `Stub reply from ${parsed.model}.`;
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          content: [{ type: 'text', text }],
          model: parsed.model,
          usage: { input_tokens: 1, output_tokens: 1 },
        }));
      });
    });
    stub.listen(STUB_PORT, '127.0.0.1', () => resolve(stub));
  });
}

// --- Server under test ------------------------------------------------------

function startServer(env = {}) {
  return spawn(process.execPath, [path.join(__dirname, 'server.js')], {
    env: {
      ...process.env,
      HOST: '127.0.0.1',
      PORT: String(PORT),
      APP_PASSWORD: PASSWORD,
      ANTHROPIC_API_KEY: 'stub-key',
      ANTHROPIC_BASE_URL: `http://127.0.0.1:${STUB_PORT}`,
      SESSION_SECRET: 'fixed-secret-for-tests',
      ...env,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

async function waitForServer() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const res = await fetch(`${BASE}/api/health`);
      if (res.ok) return true;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error('server never came up');
}

let cookie = '';

async function call(pathname, { method = 'GET', body, headers = {}, auth = false } = {}) {
  const res = await fetch(BASE + pathname, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(auth && cookie ? { Cookie: cookie } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    redirect: 'manual',
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* not JSON */ }
  return { status: res.status, headers: res.headers, json, text };
}

// --- The run ----------------------------------------------------------------

(async () => {
  const stub = await startStub();
  const server = startServer();
  await waitForServer();

  group('Secrets are not in the source');
  {
    const sources = ['server.js', 'test.js', 'start.ps1', 'public/app.js', 'public/index.html'];
    const offenders = sources.filter((f) => {
      const full = path.join(__dirname, f);
      return fs.existsSync(full) && /sk-ant-[A-Za-z0-9]/.test(fs.readFileSync(full, 'utf8'));
    });
    check('no API key literal in any source file', offenders.length === 0, offenders.join(', '));
  }

  group('Unauthenticated requests cannot reach the model');
  {
    const chat = await call('/api/chat', { method: 'POST', body: { messages: [{ role: 'user', content: 'hi' }] } });
    check('POST /api/chat is 401', chat.status === 401, `got ${chat.status}`);

    const forged = await call('/api/chat', {
      method: 'POST',
      body: { messages: [{ role: 'user', content: 'hi' }] },
      headers: { Origin: 'https://airexploit.com' },
    });
    check('forged Origin is still 401', forged.status === 401, `got ${forged.status}`);

    const plan = await call('/api/plan', { method: 'POST', body: { goal: 'x' } });
    check('POST /api/plan is 401', plan.status === 401, `got ${plan.status}`);

    const tasks = await call('/api/tasks');
    check('GET /api/tasks is 401', tasks.status === 401, `got ${tasks.status}`);
  }

  group('Login');
  {
    const wrong = await call('/api/login', { method: 'POST', body: { password: 'nope' } });
    check('wrong password is 401', wrong.status === 401, `got ${wrong.status}`);

    // Exhaust the remaining attempts and confirm the lockout engages.
    let lockedAt = null;
    for (let i = 0; i < 12; i += 1) {
      const res = await call('/api/login', { method: 'POST', body: { password: `guess-${i}` } });
      if (res.status === 429) { lockedAt = i + 2; break; }
    }
    check('brute force is locked out', lockedAt !== null, 'never returned 429');
    check('lockout engages within 10 attempts', lockedAt !== null && lockedAt <= 10, `after ${lockedAt} attempts`);

    // A locked-out client cannot get in even with the right password.
    const duringLockout = await call('/api/login', { method: 'POST', body: { password: PASSWORD } });
    check('correct password refused while locked out', duringLockout.status === 429, `got ${duringLockout.status}`);
  }

  group('Login on a fresh instance, then the authenticated surface');
  {
    // Restart to clear the lockout, since it is keyed by client address.
    server.kill();
    await new Promise((r) => setTimeout(r, 300));
    const fresh = startServer();
    await waitForServer();

    const ok = await call('/api/login', { method: 'POST', body: { password: PASSWORD } });
    check('correct password is 200', ok.status === 200, `got ${ok.status}`);

    const setCookie = ok.headers.get('set-cookie') || '';
    cookie = setCookie.split(';')[0];
    check('cookie is HttpOnly', /HttpOnly/i.test(setCookie));
    check('cookie is SameSite=Lax', /SameSite=Lax/i.test(setCookie));
    check('cookie value is not the password', !setCookie.includes(PASSWORD));

    const chat = await call('/api/chat', {
      method: 'POST', auth: true,
      body: { messages: [{ role: 'user', content: 'hi' }] },
    });
    check('chat returns 200', chat.status === 200, `got ${chat.status}`);
    check('chat used claude-sonnet-5', chat.json?.model === 'claude-sonnet-5', chat.json?.model);
    check('chat reply is non-empty', Boolean(chat.json?.reply));

    const plan = await call('/api/plan', { method: 'POST', auth: true, body: { goal: 'a habit tracker' } });
    check('plan returns 200', plan.status === 200, `got ${plan.status}`);
    check('plan used claude-opus-5', plan.json?.model === 'claude-opus-5', plan.json?.model);
    for (const key of ['overview', 'key_parts', 'build_order', 'risks', 'next_action']) {
      check(`plan has ${key}`, Boolean(plan.json?.plan?.[key]));
    }

    const created = await call('/api/tasks', { method: 'POST', auth: true, body: { title: 'Test task' } });
    check('task created', created.status === 201, `got ${created.status}`);
    const id = created.json?.task?.id;

    const ticked = await call('/api/tasks', { method: 'PATCH', auth: true, body: { id, done: true } });
    check('task ticked', ticked.json?.task?.done === true);

    const listed = await call('/api/tasks', { auth: true });
    check('task persists in the list', listed.json?.tasks?.some((t) => t.id === id));

    const removed = await call('/api/tasks', { method: 'DELETE', auth: true, body: { id } });
    check('task deleted', removed.status === 200, `got ${removed.status}`);

    const afterDelete = await call('/api/tasks', { auth: true });
    check('deleted task is gone', !afterDelete.json?.tasks?.some((t) => t.id === id));

    group('Cross-origin writes are refused even with a valid session');
    const crossOrigin = await call('/api/tasks', {
      method: 'POST', auth: true,
      body: { title: 'injected' },
      headers: { Origin: 'https://evil.example' },
    });
    check('cross-origin POST is 403', crossOrigin.status === 403, `got ${crossOrigin.status}`);

    group('Response hardening');
    const page = await call('/');
    check('CSP set on the page', /frame-ancestors 'none'/.test(page.headers.get('content-security-policy') || ''));
    check('X-Frame-Options DENY', page.headers.get('x-frame-options') === 'DENY');
    check('nosniff set', page.headers.get('x-content-type-options') === 'nosniff');

    const traversal = await call('/%2e%2e%2fserver.js');
    check('path traversal does not serve source', traversal.status !== 200, `got ${traversal.status}`);

    const icon = await call('/apple-touch-icon.png');
    check('touch icon served as image/png', icon.headers.get('content-type') === 'image/png');

    const manifest = await call('/manifest.webmanifest');
    check('manifest is display: standalone', /"display":\s*"standalone"/.test(manifest.text));

    fresh.kill();
  }

  group('A weak password is refused at startup');
  {
    const weak = startServer({ APP_PASSWORD: 'short' });
    const code = await new Promise((resolve) => weak.on('exit', resolve));
    check('server exits rather than start with a weak password', code === 1, `exit code ${code}`);
  }

  group('Hashed password is accepted in place of plaintext');
  {
    const crypto = require('node:crypto');
    const hash = crypto.createHash('sha256').update(PASSWORD).digest('hex');
    const hashed = startServer({ APP_PASSWORD: '', APP_PASSWORD_HASH: hash });
    await waitForServer();
    const ok = await call('/api/login', { method: 'POST', body: { password: PASSWORD } });
    check('login works against APP_PASSWORD_HASH', ok.status === 200, `got ${ok.status}`);
    const bad = await call('/api/login', { method: 'POST', body: { password: 'wrong' } });
    check('wrong password still rejected', bad.status === 401, `got ${bad.status}`);
    hashed.kill();
  }

  stub.close();

  console.log(`\n${passed} passed, ${failures.length} failed`);
  if (failures.length) {
    console.log('\nFailures:');
    for (const f of failures) console.log(`  - ${f}`);
  }
  process.exit(failures.length ? 1 : 0);
})().catch((err) => {
  console.error('\nTest harness error:', err.message);
  process.exit(1);
});
