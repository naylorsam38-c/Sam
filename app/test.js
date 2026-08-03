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
        const system = parsed.system || '';
        const user = (parsed.messages || []).map((m) => m.content).join('\n');
        let text;
        if (/You are Forge in planning/.test(system)) {
          // Every phase and task must reference the Locked Goal it was given.
          const ref = (user.match(/locked_goal_id: (\S+)/) || [])[1] || 'unknown';
          text = JSON.stringify({
            phases: [{ name: 'Build', ref, outcome: 'A working thing' }],
            tasks: [{ name: 'Write it', ref, owner: 'builder', done_when: 'it runs' }],
            dependencies: ['Nothing before the first phase'],
            owners: ['builder owns Build'],
            required_inputs: ['The approved goal'],
            evidence_requirements: ['A run log'],
            decision_gates: ['Sam approves before release'],
            risks: ['Scope creep, seen as tasks with no ref'],
            rollback: 'Revert to the previous state',
            completion_criteria: ['Every task done'],
            final_verification: 'The suite passes',
          });
        } else if (/You are Forge\./.test(system)) {
          // Deliberately free of digits, names and dates: anything not in the
          // request would be refused by Hub as invented scope.
          text = JSON.stringify({
            locked_goal_candidate: 'A habit tracker exists that records habits',
            scope: ['Recording habits'],
            exclusions: ['Reminders'],
            constraints: ['Runs on one machine'],
            assumptions: ['Sam is the only user, stated in the request'],
            success_criteria: ['A habit can be recorded and read back'],
            known_risks: ['Scope grows beyond recording'],
            unresolved_questions: ['Whether history must be kept'],
            confidence: 'medium',
            evidence: ['The request asks for a habit tracker'],
          });
        } else if (/You are Mind/.test(system)) {
          text = JSON.stringify({
            strongest_defect: 'none found',
            why_it_matters: 'nothing downstream is affected',
            specific_correction: 'none required',
            survives: true,
          });
        } else {
          text = `Stub reply from ${parsed.model}.`;
        }
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
    const kase = await call('/api/case', { method: 'POST', body: { request: 'x' } });
    check('POST /api/case is 401', kase.status === 401, `got ${kase.status}`);

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

    group('INV-011 — a complex request cannot skip the lifecycle');
    const bypass = await call('/api/plan', { method: 'POST', auth: true, body: { goal: 'a habit tracker' } });
    check('planning straight off a request is refused', bypass.status === 409, `got ${bypass.status}`);
    check('the refusal names INV-011', bypass.json?.requirement === 'INV-011', bypass.json?.requirement);

    group('Goal Formation through to execution');
    const opened = await call('/api/case', { method: 'POST', auth: true, body: { request: 'a habit tracker' } });
    check('case opens', opened.status === 201, `got ${opened.status}`);
    const cid = opened.json?.case?.id;
    check('GF-001 — entry reason is recorded', opened.json?.case?.audit?.some((r) => r.requirement === 'GF-001'));
    check('case reaches goal_review', opened.json?.case?.state === 'goal_review', opened.json?.case?.state);
    for (const key of ['locked_goal_candidate', 'scope', 'exclusions', 'constraints', 'assumptions',
                       'success_criteria', 'known_risks', 'unresolved_questions', 'confidence', 'evidence']) {
      check(`GF-006 — goal package has ${key}`, Boolean(opened.json?.case?.goal_package?.[key]));
    }
    check('no Locked Goal before approval', opened.json?.case?.locked_goal === null);

    const early = await call(`/api/case/${cid}/plan`, { method: 'POST', auth: true, body: {} });
    check('PLN-001 — planning before approval is refused', early.status === 409, `got ${early.status}`);
    check('the refusal names PLN-001', early.json?.requirement === 'PLN-001', early.json?.requirement);

    const approved = await call(`/api/case/${cid}/goal/approve`, { method: 'POST', auth: true, body: {} });
    check('GF-008 — Sam approval locks the goal', approved.json?.case?.state === 'goal_approved', approved.json?.case?.state);
    check('a locked_goal_id is issued', Boolean(approved.json?.case?.locked_goal_id));

    const planned = await call(`/api/case/${cid}/plan`, { method: 'POST', auth: true, body: {} });
    check('plan reaches plan_review', planned.json?.case?.state === 'plan_review', planned.json?.case?.state);
    for (const key of ['phases', 'tasks', 'dependencies', 'owners', 'required_inputs', 'evidence_requirements',
                       'decision_gates', 'risks', 'rollback', 'completion_criteria', 'final_verification']) {
      check(`PLN-003 — plan has ${key}`, Boolean(planned.json?.case?.plan?.[key]));
    }
    check('PLN-004 — every task references the Locked Goal',
      (planned.json?.case?.plan?.tasks || []).every((t) => t.ref === planned.json.case.locked_goal_id));

    const planApproved = await call(`/api/case/${cid}/plan/approve`, { method: 'POST', auth: true, body: {} });
    check('PLN-006 — approval opens execution', planApproved.json?.case?.state === 'executing', planApproved.json?.case?.state);
    check('a plan_id is issued', Boolean(planApproved.json?.case?.plan_id));

    group('HOF — a handoff is validated before anyone accepts it');
    const gid = planApproved.json.case.locked_goal_id;
    const pid = planApproved.json.case.plan_id;

    // A package that names no goal cannot be corrected without changing the
    // approved goal, so HOF-010 requires escalation rather than a return.
    const orphan = await call(`/api/case/${cid}/handoff`, { method: 'POST', auth: true, body: { package: { work_product: 'a thing' } } });
    check('HOF-002 — an incomplete package does not reach the receiver',
      orphan.json?.case?.state !== 'handoff_awaiting_acceptance', orphan.json?.case?.state);
    check('the defect names HOF-002', (orphan.json?.result?.problems || []).some((p) => p.requirement === 'HOF-002'));
    check('HOF-010 — a package from no goal escalates', orphan.json?.case?.state === 'handoff_escalated', orphan.json?.case?.state);
    check('ownership returns to Hub', orphan.json?.case?.owner === 'hub', orphan.json?.case?.owner);

    // Back to executing, then a correctable defect: the right goal and plan,
    // but no evidence. That one returns to the worker who raised it.
    await call(`/api/case/${cid}/handoff`, { method: 'POST', auth: true, body: {} }).catch(() => {});
    const resumed = await call(`/api/case/${cid}/handoff/resubmit`, { method: 'POST', auth: true, body: {} });
    check('a resubmit from escalated is refused', resumed.status === 409, `got ${resumed.status}`);

    const c2 = await call('/api/case', { method: 'POST', auth: true, body: { request: 'a habit tracker' } });
    const cid2 = c2.json.case.id;
    await call(`/api/case/${cid2}/goal/approve`, { method: 'POST', auth: true, body: {} });
    await call(`/api/case/${cid2}/plan`, { method: 'POST', auth: true, body: {} });
    const ready = await call(`/api/case/${cid2}/plan/approve`, { method: 'POST', auth: true, body: {} });
    const pkg = {
      handoff_id: 'h1', locked_goal_id: ready.json.case.locked_goal_id, plan_id: ready.json.case.plan_id,
      originating_worker: 'builder', intended_recipient: 'tester',
      completed_responsibilities: ['built it'], work_product: 'the thing',
      evidence: [], requirement_coverage: ['covered'], unresolved_items: ['none'],
      risks: ['none'], confidence: 'medium', requested_next_action: 'verify it',
    };
    const returned = await call(`/api/case/${cid2}/handoff`, { method: 'POST', auth: true, body: { package: pkg } });
    check('HOF-009 — a package with no evidence is refused',
      (returned.json?.result?.problems || []).some((p) => p.requirement === 'HOF-009'));
    check('a correctable defect returns', returned.json?.case?.state === 'handoff_returned', returned.json?.case?.state);
    check('ownership stays with the originating worker', returned.json?.case?.owner === 'builder', returned.json?.case?.owner);
    check('the fix loop counter moved', returned.json?.case?.fix_attempts === 1, String(returned.json?.case?.fix_attempts));

    const accepted = await call(`/api/case/${cid2}/handoff/resubmit`, { method: 'POST', auth: true, body: { package: { ...pkg, evidence: ['a run log'] } } });
    check('a corrected package reaches the receiver', accepted.json?.case?.state === 'handoff_awaiting_acceptance', accepted.json?.case?.state);
    const vague = await call(`/api/case/${cid2}/handoff/receive`, { method: 'POST', auth: true, body: { accepted: false, insufficiency: '  ' } });
    check('HOF-014 — a refusal naming nothing is not acted on', vague.json?.result?.outcome === 'REFUSAL_UNSPECIFIC', vague.json?.result?.outcome);
    const done = await call(`/api/case/${cid2}/handoff/receive`, { method: 'POST', auth: true, body: { accepted: true } });
    check('HOF-006 — acceptance transfers ownership', done.json?.result?.outcome === 'ACCEPTED' && done.json?.case?.owner === 'tester', done.json?.case?.owner);
    gid; pid;

    const audit = await call(`/api/case/${cid}/audit`, { auth: true });
    check('the audit log is readable', Array.isArray(audit.json?.audit) && audit.json.audit.length > 0);
    check('INV-012 — audit rows carry the goal they descend from',
      audit.json.audit.filter((r) => r.event === 'transition').every((r) => 'locked_goal_id' in r));

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
