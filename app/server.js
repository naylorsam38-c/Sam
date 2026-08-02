'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

// ---------------------------------------------------------------------------
// Config. Everything sensitive comes from the environment, never from source.
// ---------------------------------------------------------------------------

const HOST = process.env.HOST || '127.0.0.1';
const PORT = Number(process.env.PORT || 8787);

const API_KEY = process.env.ANTHROPIC_API_KEY || '';
// APP_PASSWORD_HASH is preferred: it keeps the plaintext password out of the
// environment and out of any launcher script. APP_PASSWORD still works.
const PASSWORD = process.env.APP_PASSWORD || '';
const PASSWORD_HASH = (process.env.APP_PASSWORD_HASH || '').trim().toLowerCase();
const SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex');

const MIN_PASSWORD_LENGTH = 8;
const LOGIN_MAX_FAILURES = Number(process.env.LOGIN_MAX_FAILURES || 8);
const LOGIN_LOCKOUT_MS = Number(process.env.LOGIN_LOCKOUT_MINUTES || 15) * 60 * 1000;

const MODEL_CHAT = process.env.MODEL_CHAT || 'claude-sonnet-5';
const MODEL_PLAN = process.env.MODEL_PLAN || 'claude-opus-5';

const MAX_TOKENS_CHAT = Number(process.env.MAX_TOKENS_CHAT || 1024);
const MAX_TOKENS_PLAN = Number(process.env.MAX_TOKENS_PLAN || 2048);
const DAILY_CALL_CAP = Number(process.env.DAILY_CALL_CAP || 200);

const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 days
const PUBLIC_DIR = path.join(__dirname, 'public');
const DATA_DIR = path.join(__dirname, 'data');
const TASKS_FILE = path.join(DATA_DIR, 'tasks.json');

// Overridable only so the app can be exercised end-to-end against a local
// stub during testing. Unset, it always talks to the real API.
const ANTHROPIC_URL = process.env.ANTHROPIC_BASE_URL
  ? `${process.env.ANTHROPIC_BASE_URL.replace(/\/$/, '')}/v1/messages`
  : 'https://api.anthropic.com/v1/messages';
const ANTHROPIC_VERSION = '2023-06-01';

// ---------------------------------------------------------------------------
// Session cookies. Signed with HMAC so they cannot be forged client-side.
// ---------------------------------------------------------------------------

function sign(value) {
  return crypto.createHmac('sha256', SECRET).update(value).digest('base64url');
}

function issueToken() {
  const payload = `${Date.now() + SESSION_TTL_MS}.${crypto.randomBytes(12).toString('base64url')}`;
  return `${payload}.${sign(payload)}`;
}

function verifyToken(token) {
  if (!token) return null;
  const idx = token.lastIndexOf('.');
  if (idx < 0) return null;
  const payload = token.slice(0, idx);
  const provided = Buffer.from(token.slice(idx + 1));
  const expected = Buffer.from(sign(payload));
  if (provided.length !== expected.length) return null;
  if (!crypto.timingSafeEqual(provided, expected)) return null;
  const expiry = Number(payload.split('.')[0]);
  if (!Number.isFinite(expiry) || Date.now() > expiry) return null;
  return payload;
}

function parseCookies(header) {
  const out = {};
  for (const part of (header || '').split(';')) {
    const eq = part.indexOf('=');
    if (eq < 0) continue;
    out[part.slice(0, eq).trim()] = decodeURIComponent(part.slice(eq + 1).trim());
  }
  return out;
}

function passwordConfigured() {
  return Boolean(PASSWORD_HASH || PASSWORD);
}

function passwordMatches(candidate) {
  const supplied = crypto.createHash('sha256').update(String(candidate)).digest();
  const expected = PASSWORD_HASH
    ? Buffer.from(PASSWORD_HASH, 'hex')
    : crypto.createHash('sha256').update(PASSWORD).digest();
  // A malformed hash would otherwise throw inside timingSafeEqual.
  if (expected.length !== supplied.length) return false;
  return crypto.timingSafeEqual(supplied, expected);
}

// --- Login throttling -------------------------------------------------------
// The password is the only barrier in front of the API key, so failed attempts
// are counted per client address and locked out once they pile up.

const loginFailures = new Map(); // address -> { count, firstAt }

function lockoutRemainingMs(address) {
  const entry = loginFailures.get(address);
  if (!entry) return 0;
  if (Date.now() - entry.firstAt > LOGIN_LOCKOUT_MS) {
    loginFailures.delete(address);
    return 0;
  }
  if (entry.count < LOGIN_MAX_FAILURES) return 0;
  return LOGIN_LOCKOUT_MS - (Date.now() - entry.firstAt);
}

function recordLoginFailure(address) {
  const entry = loginFailures.get(address);
  if (!entry || Date.now() - entry.firstAt > LOGIN_LOCKOUT_MS) {
    loginFailures.set(address, { count: 1, firstAt: Date.now() });
    return;
  }
  entry.count += 1;
}

// ---------------------------------------------------------------------------
// Spend guard. A per-session daily cap so a leaked URL cannot run up a bill.
// ---------------------------------------------------------------------------

const callCounts = new Map(); // session -> { day, count }

function underCallCap(session) {
  const day = new Date().toISOString().slice(0, 10);
  const entry = callCounts.get(session);
  if (!entry || entry.day !== day) {
    callCounts.set(session, { day, count: 1 });
    return true;
  }
  if (entry.count >= DAILY_CALL_CAP) return false;
  entry.count += 1;
  return true;
}

// ---------------------------------------------------------------------------
// Task storage. A flat JSON file — no database to stand up.
// ---------------------------------------------------------------------------

function readTasks() {
  try {
    return JSON.parse(fs.readFileSync(TASKS_FILE, 'utf8'));
  } catch {
    return [];
  }
}

function writeTasks(tasks) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(TASKS_FILE, JSON.stringify(tasks, null, 2));
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

// Everything the page needs is served from this origin, so the policy can be
// strict. frame-ancestors 'none' is what stops the app being framed and
// clickjacked into spending against the key.
const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'Content-Security-Policy': [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "form-action 'self'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
  ].join('; '),
};

function sendJson(res, status, body, headers = {}) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(payload),
    'Cache-Control': 'no-store',
    ...SECURITY_HEADERS,
    ...headers,
  });
  res.end(payload);
}

function readBody(req, limitBytes = 256 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > limitBytes) {
        reject(new Error('Request body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error('Body was not valid JSON'));
      }
    });
    req.on('error', reject);
  });
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function serveStatic(req, res, urlPath) {
  const rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
  const target = path.join(PUBLIC_DIR, rel);
  // Path traversal guard: the resolved file must stay inside PUBLIC_DIR.
  if (!target.startsWith(PUBLIC_DIR + path.sep) && target !== PUBLIC_DIR) {
    return sendJson(res, 403, { error: 'Forbidden' });
  }
  fs.readFile(target, (err, data) => {
    if (err) return sendJson(res, 404, { error: 'Not found' });
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(target)] || 'application/octet-stream',
      'Content-Length': data.length,
      ...SECURITY_HEADERS,
    });
    res.end(data);
  });
}

// ---------------------------------------------------------------------------
// Anthropic calls
// ---------------------------------------------------------------------------

async function callClaude({ model, system, messages, maxTokens }) {
  const response = await fetch(ANTHROPIC_URL, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': API_KEY,
      'anthropic-version': ANTHROPIC_VERSION,
    },
    body: JSON.stringify({ model, max_tokens: maxTokens, system, messages }),
  });

  const raw = await response.text();
  if (!response.ok) {
    let detail = raw.slice(0, 500);
    try {
      detail = JSON.parse(raw)?.error?.message || detail;
    } catch { /* keep the raw text */ }
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }

  const data = JSON.parse(raw);
  const text = (data.content || [])
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('\n')
    .trim();
  return { text, usage: data.usage || null };
}

const PLAN_SYSTEM = `You are a planning assistant. Given a goal, respond with ONLY a JSON object, no prose and no code fences, matching exactly:
{
  "overview": "two or three sentences framing the goal",
  "key_parts": ["the distinct pieces that must exist"],
  "build_order": ["ordered steps, each one concrete enough to start"],
  "risks": ["what realistically goes wrong, and the early warning sign"],
  "next_action": "the single smallest thing to do first"
}`;

function extractJson(text) {
  // Models occasionally wrap JSON in fences despite instructions.
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = fenced ? fenced[1] : text;
  const start = candidate.indexOf('{');
  const end = candidate.lastIndexOf('}');
  if (start < 0 || end <= start) return null;
  try {
    return JSON.parse(candidate.slice(start, end + 1));
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const route = url.pathname;
  const cookies = parseCookies(req.headers.cookie);
  const session = verifyToken(cookies.sam_session);

  try {
    // --- Public routes -----------------------------------------------------

    if (route === '/api/health') {
      return sendJson(res, 200, {
        ok: true,
        models: { chat: MODEL_CHAT, plan: MODEL_PLAN },
        key_present: Boolean(API_KEY),
        password_set: passwordConfigured(),
      });
    }

    if (route === '/api/login' && req.method === 'POST') {
      if (!passwordConfigured()) {
        return sendJson(res, 500, { error: 'APP_PASSWORD is not set on the server' });
      }
      const address = req.socket.remoteAddress || 'unknown';
      const waitMs = lockoutRemainingMs(address);
      if (waitMs > 0) {
        return sendJson(res, 429, {
          error: `Too many failed attempts. Try again in ${Math.ceil(waitMs / 60000)} minute(s).`,
        });
      }
      const body = await readBody(req);
      if (!body.password || !passwordMatches(body.password)) {
        recordLoginFailure(address);
        return sendJson(res, 401, { error: 'Wrong password' });
      }
      loginFailures.delete(address);
      const secure = process.env.COOKIE_SECURE === '1' ? '; Secure' : '';
      const cookie = `sam_session=${issueToken()}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${SESSION_TTL_MS / 1000}${secure}`;
      return sendJson(res, 200, { ok: true }, { 'Set-Cookie': cookie });
    }

    if (route === '/api/logout' && req.method === 'POST') {
      return sendJson(res, 200, { ok: true }, {
        'Set-Cookie': 'sam_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0',
      });
    }

    if (route === '/api/me') {
      return sendJson(res, 200, { authed: Boolean(session) });
    }

    // --- Everything below requires a valid session -------------------------
    // Checked before any Anthropic call, so an unauthenticated request can
    // never spend against the API key.

    if (route.startsWith('/api/')) {
      if (!session) return sendJson(res, 401, { error: 'Not authenticated' });

      // Defence in depth behind the cookie, not in place of it. SameSite=Lax
      // already withholds the cookie cross-site; this rejects anything that
      // slips through with a foreign Origin on a state-changing request.
      if (req.method !== 'GET' && req.headers.origin) {
        let originHost = null;
        try {
          originHost = new URL(req.headers.origin).host;
        } catch { /* unparseable Origin is treated as foreign */ }
        if (originHost !== req.headers.host) {
          return sendJson(res, 403, { error: 'Cross-origin request refused' });
        }
      }

      if (route === '/api/chat' && req.method === 'POST') {
        if (!API_KEY) return sendJson(res, 500, { error: 'ANTHROPIC_API_KEY is not set on the server' });
        if (!underCallCap(session)) {
          return sendJson(res, 429, { error: `Daily cap of ${DAILY_CALL_CAP} calls reached` });
        }
        const body = await readBody(req);
        const history = Array.isArray(body.messages) ? body.messages : [];
        const messages = history
          .filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
          .slice(-20)
          .map((m) => ({ role: m.role, content: m.content }));
        if (!messages.length) return sendJson(res, 400, { error: 'No message supplied' });

        const result = await callClaude({
          model: MODEL_CHAT,
          system: 'You are a concise, practical assistant. Answer directly.',
          messages,
          maxTokens: MAX_TOKENS_CHAT,
        });
        return sendJson(res, 200, { reply: result.text, model: MODEL_CHAT, usage: result.usage });
      }

      if (route === '/api/plan' && req.method === 'POST') {
        if (!API_KEY) return sendJson(res, 500, { error: 'ANTHROPIC_API_KEY is not set on the server' });
        if (!underCallCap(session)) {
          return sendJson(res, 429, { error: `Daily cap of ${DAILY_CALL_CAP} calls reached` });
        }
        const body = await readBody(req);
        const goal = typeof body.goal === 'string' ? body.goal.trim() : '';
        if (!goal) return sendJson(res, 400, { error: 'No goal supplied' });

        const result = await callClaude({
          model: MODEL_PLAN,
          system: PLAN_SYSTEM,
          messages: [{ role: 'user', content: `Goal: ${goal}` }],
          maxTokens: MAX_TOKENS_PLAN,
        });
        const plan = extractJson(result.text);
        return sendJson(res, 200, {
          goal,
          model: MODEL_PLAN,
          plan,
          raw: plan ? undefined : result.text,
        });
      }

      if (route === '/api/tasks') {
        if (req.method === 'GET') return sendJson(res, 200, { tasks: readTasks() });

        if (req.method === 'POST') {
          const body = await readBody(req);
          const title = typeof body.title === 'string' ? body.title.trim() : '';
          if (!title) return sendJson(res, 400, { error: 'Task needs a title' });
          const tasks = readTasks();
          const task = {
            id: crypto.randomUUID(),
            title: title.slice(0, 500),
            done: false,
            created: new Date().toISOString(),
          };
          tasks.unshift(task);
          writeTasks(tasks);
          return sendJson(res, 201, { task });
        }

        if (req.method === 'PATCH') {
          const body = await readBody(req);
          const tasks = readTasks();
          const task = tasks.find((t) => t.id === body.id);
          if (!task) return sendJson(res, 404, { error: 'No such task' });
          if (typeof body.done === 'boolean') task.done = body.done;
          if (typeof body.title === 'string' && body.title.trim()) task.title = body.title.trim().slice(0, 500);
          writeTasks(tasks);
          return sendJson(res, 200, { task });
        }

        if (req.method === 'DELETE') {
          const body = await readBody(req);
          const tasks = readTasks();
          const next = tasks.filter((t) => t.id !== body.id);
          if (next.length === tasks.length) return sendJson(res, 404, { error: 'No such task' });
          writeTasks(next);
          return sendJson(res, 200, { ok: true });
        }
      }

      return sendJson(res, 404, { error: 'No such endpoint' });
    }

    // --- Static files ------------------------------------------------------

    if (req.method !== 'GET') return sendJson(res, 405, { error: 'Method not allowed' });
    return serveStatic(req, res, route);
  } catch (err) {
    const status = err.status && err.status >= 400 && err.status < 600 ? err.status : 500;
    return sendJson(res, status, { error: err.message || 'Server error' });
  }
});

// The password guards the API key, so a weak one is refused outright rather
// than warned about. A hash is accepted without a length check, since the
// plaintext behind it is never seen here.
if (!PASSWORD_HASH && PASSWORD && PASSWORD.length < MIN_PASSWORD_LENGTH) {
  console.error(`APP_PASSWORD must be at least ${MIN_PASSWORD_LENGTH} characters. Refusing to start.`);
  process.exit(1);
}

server.listen(PORT, HOST, () => {
  console.log(`Sam standalone listening on http://${HOST}:${PORT}`);
  console.log(`  chat model   : ${MODEL_CHAT}`);
  console.log(`  plan model   : ${MODEL_PLAN}`);
  console.log(`  API key      : ${API_KEY ? 'present' : 'MISSING — set ANTHROPIC_API_KEY'}`);
  console.log(`  password     : ${PASSWORD_HASH ? 'set (hash)' : PASSWORD ? 'set' : 'MISSING — set APP_PASSWORD'}`);
  console.log(`  daily cap    : ${DAILY_CALL_CAP} calls per session`);
  console.log(`  login lockout: ${LOGIN_MAX_FAILURES} failures, ${LOGIN_LOCKOUT_MS / 60000} min`);
});
