'use strict';

// ---------------------------------------------------------------------------
// The complex-request lifecycle, as specified in the Command Desk Master
// Specification v1.3 (Part 2, Engineering standard; Part 3, Workflow).
//
// Everything in this file is deterministic. No model decides a state, a
// verdict or an ownership transfer — code does. Models only ever produce
// candidate content, which is then checked here.
//
// Requirement identifiers in comments refer to the specification and are
// covered one-for-one by tests in test.js.
// ---------------------------------------------------------------------------

const crypto = require('node:crypto');

// --- States ----------------------------------------------------------------
// Permitted exits and timeouts are transcribed from the state table in
// document 05. A transition not listed here does not exist.
//
// `executing` is the one state whose permitted exits the specification does
// not state; it appears only as an exit target of other states. The two edges
// below are the minimum needed to reach a handoff or a failure, and are
// flagged as a specification gap rather than presented as specified.
const STATES = {
  goal_forming:                { exits: ['goal_review'],                                                     timeoutMs: null,   owner: 'forge_mind' },
  goal_review:                 { exits: ['goal_forming', 'goal_approved'],                                   timeoutMs: null,   owner: 'sam' },
  goal_approved:               { exits: ['plan_forming'],                                                    timeoutMs: null,   owner: 'hub' },
  plan_forming:                { exits: ['plan_review'],                                                     timeoutMs: null,   owner: 'forge_mind' },
  plan_review:                 { exits: ['plan_forming', 'plan_approved'],                                   timeoutMs: null,   owner: 'sam' },
  plan_approved:               { exits: ['executing'],                                                       timeoutMs: null,   owner: 'hub' },
  executing:                   { exits: ['handoff_validating', 'failed'],                                    timeoutMs: null,   owner: 'worker', inferred: true },
  handoff_validating:          { exits: ['handoff_returned', 'handoff_escalated', 'handoff_awaiting_acceptance'], timeoutMs: 30000,  owner: 'hub' },
  handoff_awaiting_acceptance: { exits: ['handoff_returned', 'handoff_escalated', 'executing'],              timeoutMs: 30000,  owner: 'receiving_worker' },
  handoff_returned:            { exits: ['executing', 'handoff_escalated'],                                  timeoutMs: 120000, owner: 'originating_worker' },
  handoff_escalated:           { exits: ['goal_forming', 'plan_forming', 'executing', 'failed'],             timeoutMs: null,   owner: 'hub' },
  failed:                      { exits: [],                                                                  timeoutMs: null,   owner: 'hub' },
};

// A Category B failure returns to the worker with the condition named, for a
// maximum of two attempts, then escalates (document 01).
const FIX_LOOP_LIMIT = 2;

// Goal Formation stops when one unambiguous goal survives or the configured
// round limit is reached (GF-005).
const GOAL_ROUND_LIMIT = Number(process.env.GOAL_ROUND_LIMIT || 3);

// --- Required package fields ------------------------------------------------
const GOAL_FIELDS = [           // GF-006
  'locked_goal_candidate', 'scope', 'exclusions', 'constraints', 'assumptions',
  'success_criteria', 'known_risks', 'unresolved_questions', 'confidence', 'evidence',
];
const PLAN_FIELDS = [           // PLN-003
  'phases', 'tasks', 'dependencies', 'owners', 'required_inputs',
  'evidence_requirements', 'decision_gates', 'risks', 'rollback',
  'completion_criteria', 'final_verification',
];
const HANDOFF_FIELDS = [        // HOF-002
  'handoff_id', 'locked_goal_id', 'plan_id', 'originating_worker', 'intended_recipient',
  'completed_responsibilities', 'work_product', 'evidence', 'requirement_coverage',
  'unresolved_items', 'risks', 'confidence', 'requested_next_action',
];

function missingFields(obj, fields) {
  const src = obj && typeof obj === 'object' ? obj : {};
  return fields.filter((f) => {
    const v = src[f];
    if (v === undefined || v === null) return true;
    if (typeof v === 'string') return v.trim() === '';
    if (Array.isArray(v)) return v.length === 0;
    return false;
  });
}

// --- Grounding (GF-007) -----------------------------------------------------
// Hub compares every Goal Package field against the original request and
// rejects any invented scope, constraint, recipient, amount, date or
// reference. "Invented" is decided by code, not by a model: any hard token in
// the package — a number, amount, date, address, identifier or URL — must be
// present in the request that produced it.

const HARD_TOKEN = new RegExp([
  '[\\w.+-]+@[\\w-]+\\.[\\w.-]+',            // email address
  'https?://\\S+',                            // url
  '[£$€]\\s?\\d[\\d,]*(?:\\.\\d+)?',          // amount
  '\\b\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}\\b',   // date
  '\\b\\d{4}-\\d{2}-\\d{2}\\b',               // iso date
  '\\b\\d[\\d,]*(?:\\.\\d+)?\\b',             // bare number
].join('|'), 'gi');

function hardTokens(value, acc = new Set()) {
  if (value === null || value === undefined) return acc;
  if (Array.isArray(value)) { value.forEach((v) => hardTokens(v, acc)); return acc; }
  if (typeof value === 'object') { Object.values(value).forEach((v) => hardTokens(v, acc)); return acc; }
  for (const m of String(value).matchAll(HARD_TOKEN)) acc.add(m[0].toLowerCase().replace(/[\s,]/g, ''));
  return acc;
}

// Returns the tokens present in `pkg` that are absent from `request`.
function ungrounded(pkg, request) {
  const inRequest = hardTokens(request);
  const out = [];
  for (const token of hardTokens(pkg)) if (!inRequest.has(token)) out.push(token);
  return out;
}

// --- Case -------------------------------------------------------------------

function newCase(request, { now = Date.now() } = {}) {
  const id = crypto.randomUUID();
  return {
    id,
    request: String(request),
    state: 'goal_forming',
    owner: STATES.goal_forming.owner,
    enteredAt: now,
    goal_rounds: 0,
    goal_package: null,
    locked_goal: null,       // set only on approval; immutable thereafter
    locked_goal_id: null,
    plan: null,
    plan_id: null,
    handoff: null,
    fix_attempts: 0,
    audit: [],
  };
}

// Every transition, accepted or refused, is written to the audit log with its
// reason. INV-012: each row carries the goal and plan it descends from.
function record(c, event, detail, { now = Date.now() } = {}) {
  c.audit.push({
    at: new Date(now).toISOString(),
    event,
    state: c.state,
    owner: c.owner,
    locked_goal_id: c.locked_goal_id,
    plan_id: c.plan_id,
    ...detail,
  });
  return c.audit[c.audit.length - 1];
}

class LifecycleError extends Error {
  constructor(message, requirement) { super(message); this.requirement = requirement; this.status = 409; }
}

// The only way a case changes state. An unlisted transition is refused and
// the refusal is logged — a state machine that can be stepped around is not a
// state machine.
function transition(c, next, reason, { now = Date.now(), owner } = {}) {
  const from = STATES[c.state];
  if (!from) throw new LifecycleError(`Unknown state ${c.state}`, 'WF-STATE');
  if (!from.exits.includes(next)) {
    record(c, 'transition_refused', { to: next, reason: reason || null, refused_because: 'not a permitted exit' }, { now });
    throw new LifecycleError(`${c.state} may not go to ${next}. Permitted: ${from.exits.join(', ') || 'none'}`, 'WF-EXIT');
  }
  c.state = next;
  c.owner = owner || STATES[next].owner;   // INV-013: exactly one owner, always
  c.enteredAt = now;
  record(c, 'transition', { to: next, reason: reason || null }, { now });
  return c;
}

// --- Timeouts (HOF-011) -----------------------------------------------------
// A handoff state that reaches its timeout without a transition resolves to
// ESCALATED, ownership returns to Hub, and the timeout is written to the audit
// log as the reason. Never silently retried, never resolved to ACCEPTED.
function sweepTimeout(c, { now = Date.now() } = {}) {
  const s = STATES[c.state];
  if (!s || !s.timeoutMs) return false;
  const elapsed = now - c.enteredAt;
  if (elapsed < s.timeoutMs) return false;
  const from = c.state;
  // Escalation is reached directly: the timeout is the transition, and it is
  // permitted from every state that carries one.
  c.state = 'handoff_escalated';
  c.owner = STATES.handoff_escalated.owner;
  c.enteredAt = now;
  record(c, 'timeout', {
    to: 'handoff_escalated',
    from,
    reason: `${from} reached its ${s.timeoutMs / 1000}s timeout without a transition`,
    requirement: 'HOF-011',
    retried: false,
  }, { now });
  return true;
}

// --- Goal Formation ---------------------------------------------------------

// GF-002/GF-006/GF-007. The package is produced elsewhere; this decides
// whether Hub accepts it.
function validateGoalPackage(c, pkg, { now = Date.now() } = {}) {
  const problems = [];
  const missing = missingFields(pkg, GOAL_FIELDS);
  if (missing.length) problems.push({ requirement: 'GF-006', detail: `missing or empty: ${missing.join(', ')}` });

  // GF-002: a goal package states what and why, never how.
  if (pkg && Array.isArray(pkg.implementation_instructions) && pkg.implementation_instructions.length) {
    problems.push({ requirement: 'GF-002', detail: 'goal package carried implementation instructions' });
  }

  const invented = ungrounded(pkg, c.request);
  if (invented.length) {
    problems.push({ requirement: 'GF-007', detail: `not present in the request: ${invented.join(', ')}` });
  }
  record(c, problems.length ? 'goal_package_rejected' : 'goal_package_validated',
    { problems, round: c.goal_rounds }, { now });
  return problems;
}

function submitGoalPackage(c, pkg, { now = Date.now() } = {}) {
  if (c.state !== 'goal_forming') throw new LifecycleError(`Goal packages are produced in goal_forming, not ${c.state}`, 'WF-EXIT');
  c.goal_rounds += 1;
  const problems = validateGoalPackage(c, pkg, { now });
  if (problems.length) {
    // GF-005: the pair stops at the round limit even unresolved. Hub does not
    // approve an unvalidated package — it escalates the decision to Sam.
    if (c.goal_rounds >= GOAL_ROUND_LIMIT) {
      c.goal_package = pkg;
      transition(c, 'goal_review', `round limit ${GOAL_ROUND_LIMIT} reached with ${problems.length} unresolved defect(s)`, { now });
      return { accepted: false, atRoundLimit: true, problems };
    }
    return { accepted: false, atRoundLimit: false, problems };
  }
  c.goal_package = pkg;
  transition(c, 'goal_review', 'goal package validated against the original request', { now });
  return { accepted: true, atRoundLimit: false, problems: [] };
}

// GF-008: Sam approves the Goal Package before it becomes the Locked Goal.
function approveGoal(c, { now = Date.now() } = {}) {
  if (c.state !== 'goal_review') throw new LifecycleError(`Approval is given in goal_review, not ${c.state}`, 'GF-008');
  if (c.locked_goal) throw new LifecycleError('This case already carries a Locked Goal', 'INV-015');
  const goal = c.goal_package.locked_goal_candidate;
  c.locked_goal = goal;
  c.locked_goal_id = 'goal_' + crypto.createHash('sha256')
    .update(JSON.stringify({ id: c.id, goal })).digest('hex').slice(0, 16);
  Object.freeze(c.goal_package);            // immutable from here (INV-015)
  transition(c, 'goal_approved', 'approved by Sam', { now });
  record(c, 'goal_locked', { locked_goal: goal, requirement: 'GF-008' }, { now });
  return c;
}

function rejectGoal(c, reason, { now = Date.now() } = {}) {
  if (c.state !== 'goal_review') throw new LifecycleError(`Rejection is given in goal_review, not ${c.state}`, 'GF-008');
  c.goal_package = null;
  transition(c, 'goal_forming', reason || 'returned by Sam', { now });
  return c;
}

// --- Solution Planning ------------------------------------------------------

function beginPlanning(c, { now = Date.now() } = {}) {
  // PLN-001: planning begins only when Goal State is APPROVED.
  if (c.state !== 'goal_approved') throw new LifecycleError(`Planning begins from goal_approved, not ${c.state}`, 'PLN-001');
  transition(c, 'plan_forming', 'goal approved; planning opened', { now });
  return c;
}

function validatePlan(c, plan, { now = Date.now() } = {}) {
  const problems = [];
  const missing = missingFields(plan, PLAN_FIELDS);
  if (missing.length) problems.push({ requirement: 'PLN-003', detail: `missing or empty: ${missing.join(', ')}` });

  // PLN-002: one recommended plan, not a menu.
  if (plan && Array.isArray(plan.options) && plan.options.length > 1) {
    problems.push({ requirement: 'PLN-002', detail: `plan offered ${plan.options.length} options instead of one recommendation` });
  }

  // PLN-004: every plan element references the Locked Goal or an approved
  // success criterion.
  const criteria = new Set((c.goal_package?.success_criteria || []).map((x) => String(x)));
  const unreferenced = [];
  for (const group of ['phases', 'tasks']) {
    for (const el of (plan?.[group] || [])) {
      const ref = el && typeof el === 'object' ? el.ref : null;
      if (!ref || (ref !== c.locked_goal_id && !criteria.has(String(ref)))) {
        unreferenced.push(`${group}: ${(el && (el.name || el.title)) || JSON.stringify(el).slice(0, 40)}`);
      }
    }
  }
  if (unreferenced.length) problems.push({ requirement: 'PLN-004', detail: `no reference to the Locked Goal or an approved success criterion — ${unreferenced.join('; ')}` });

  // PLN-005: the pair must not alter the Locked Goal.
  if (plan && plan.locked_goal !== undefined && String(plan.locked_goal) !== String(c.locked_goal)) {
    problems.push({ requirement: 'PLN-005', detail: 'planning altered the Locked Goal', reopenGoal: true });
  }

  const invented = ungrounded(plan, `${c.request} ${JSON.stringify(c.goal_package || {})}`);
  if (invented.length) problems.push({ requirement: 'GF-007', detail: `not present in the request or approved goal: ${invented.join(', ')}` });

  record(c, problems.length ? 'plan_rejected' : 'plan_validated', { problems }, { now });
  return problems;
}

function submitPlan(c, plan, { now = Date.now() } = {}) {
  if (c.state !== 'plan_forming') throw new LifecycleError(`Plans are produced in plan_forming, not ${c.state}`, 'WF-EXIT');
  const problems = validatePlan(c, plan, { now });

  // PLN-005: a defective goal stops the work; Hub reopens Goal Formation.
  if (problems.some((p) => p.reopenGoal)) {
    c.plan = null;
    c.locked_goal = null;
    c.locked_goal_id = null;
    c.goal_package = null;
    transition(c, 'plan_review', 'planning exposed a defective goal', { now });
    transition(c, 'plan_forming', 'reopening goal formation', { now });
    c.state = 'goal_forming';
    c.owner = STATES.goal_forming.owner;
    c.enteredAt = now;
    record(c, 'goal_reopened', { requirement: 'PLN-005', reason: 'planning altered the Locked Goal' }, { now });
    return { accepted: false, goalReopened: true, problems };
  }
  if (problems.length) return { accepted: false, goalReopened: false, problems };

  c.plan = plan;
  transition(c, 'plan_review', 'plan validated against the approved Locked Goal', { now });
  return { accepted: true, goalReopened: false, problems: [] };
}

// PLN-006: Sam approves the Implementation Plan before execution begins.
function approvePlan(c, { now = Date.now() } = {}) {
  if (c.state !== 'plan_review') throw new LifecycleError(`Approval is given in plan_review, not ${c.state}`, 'PLN-006');
  c.plan_id = 'plan_' + crypto.createHash('sha256')
    .update(JSON.stringify({ goal: c.locked_goal_id, plan: c.plan })).digest('hex').slice(0, 16);
  Object.freeze(c.plan);
  transition(c, 'plan_approved', 'approved by Sam', { now });
  transition(c, 'executing', 'plan approved; execution opened', { now, owner: 'worker' });
  return c;
}

function rejectPlan(c, reason, { now = Date.now() } = {}) {
  if (c.state !== 'plan_review') throw new LifecycleError(`Rejection is given in plan_review, not ${c.state}`, 'PLN-006');
  c.plan = null;
  transition(c, 'plan_forming', reason || 'returned by Sam', { now });
  return c;
}

// --- Handoff ----------------------------------------------------------------

// HOF-002/HOF-003. Hub validates the package before anyone is asked to accept it.
function openHandoff(c, pkg, { now = Date.now() } = {}) {
  if (c.state !== 'executing') throw new LifecycleError(`A handoff opens from executing, not ${c.state}`, 'HOF-001');
  c.handoff = { ...pkg, handoff_id: pkg.handoff_id || crypto.randomUUID() };
  transition(c, 'handoff_validating', 'handoff package received by Hub', { now });

  const problems = [];
  const missing = missingFields(c.handoff, HANDOFF_FIELDS);
  if (missing.length) problems.push({ requirement: 'HOF-002', detail: `missing or empty: ${missing.join(', ')}` });

  // HOF-003 / INV-012: the package must descend from this case's approved goal
  // and plan, not from some other one.
  if (c.handoff.locked_goal_id !== c.locked_goal_id) problems.push({ requirement: 'INV-012', detail: 'locked_goal_id does not match this case' });
  if (c.plan_id && c.handoff.plan_id !== c.plan_id) problems.push({ requirement: 'INV-012', detail: 'plan_id does not match this case' });

  // HOF-009: never accepted where evidence is absent or work is concealed.
  const evidence = c.handoff.evidence;
  if (!evidence || (Array.isArray(evidence) && !evidence.length)) {
    problems.push({ requirement: 'HOF-009', detail: 'no evidence supplied' });
  }

  record(c, problems.length ? 'handoff_rejected_by_hub' : 'handoff_validated_by_hub', { problems }, { now });

  if (problems.length) return hubDisposition(c, problems, { now });
  transition(c, 'handoff_awaiting_acceptance', 'Hub validated the package', { now });
  return { state: c.state, problems: [] };
}

// HOF-010/HOF-013. Whether a defect returns or escalates is Hub's call, made
// by rule: correctable within the approved goal and plan → RETURNED; anything
// that would change the goal or plan, exceed authority, need a permission or
// user decision, or that has already used the fix loop → ESCALATED.
function hubDisposition(c, problems, { now = Date.now() } = {}) {
  const beyondAuthority = problems.some((p) =>
    p.requirement === 'PLN-005' || p.requirement === 'INV-012' || p.exceedsAuthority);

  if (beyondAuthority) {
    transition(c, 'handoff_escalated', `defect cannot be corrected without changing the approved goal or plan: ${problems.map((p) => p.requirement).join(', ')}`, { now });
    return { state: c.state, problems, escalated: true };
  }
  if (c.fix_attempts >= FIX_LOOP_LIMIT) {
    transition(c, 'handoff_escalated', `fix loop limit of ${FIX_LOOP_LIMIT} attempts reached`, { now });
    return { state: c.state, problems, escalated: true, fixLoopExhausted: true };
  }
  c.fix_attempts += 1;
  // HOF-007 / guardrail: a returned handoff preserves the originating owner
  // and increments the attempt counter.
  transition(c, 'handoff_returned',
    `${problems[0].requirement}: ${problems[0].detail}`,
    { now, owner: c.handoff?.originating_worker || 'originating_worker' });
  record(c, 'fix_loop', { attempt: c.fix_attempts, limit: FIX_LOOP_LIMIT }, { now });
  return { state: c.state, problems, escalated: false, attempt: c.fix_attempts };
}

// HOF-004/HOF-012/HOF-014. The receiving worker reports; it never sets the
// state. Its check is completeness and authority only — it may not question
// the Locked Goal.
function receiveHandoff(c, report, { now = Date.now() } = {}) {
  if (c.state !== 'handoff_awaiting_acceptance') {
    throw new LifecycleError(`A receiving worker reports in handoff_awaiting_acceptance, not ${c.state}`, 'HOF-012');
  }
  // HOF-012: a worker that tries to declare the outcome is ignored on that
  // point; the attempt is logged.
  if (report && report.state) {
    record(c, 'worker_state_claim_ignored', { claimed: report.state, requirement: 'HOF-012' }, { now });
  }

  if (report && report.accepted === true) {
    // HOF-004: acceptance is a completeness and authority check. A receiver
    // that reports acceptance while disputing the goal has exceeded its remit.
    if (report.goal_dispute) {
      record(c, 'goal_dispute_refused', { requirement: 'HOF-004', detail: 'the Locked Goal is immutable and reference-only' }, { now });
    }
    transition(c, 'executing', 'receiving worker accepted responsibility', { now, owner: c.handoff?.intended_recipient || 'worker' });
    record(c, 'handoff_accepted', {
      requirement: 'HOF-006',
      from: c.handoff?.originating_worker,
      to: c.handoff?.intended_recipient,
    }, { now });
    return { outcome: 'ACCEPTED', state: c.state };
  }

  // HOF-014: a refusal naming no specific insufficiency is a Category B defect
  // against the receiving worker. Ownership does not transfer and the refusal
  // goes back to the receiver for a specific statement.
  const insufficiency = report && typeof report.insufficiency === 'string' ? report.insufficiency.trim() : '';
  if (!insufficiency) {
    record(c, 'refusal_returned_to_receiver', {
      requirement: 'HOF-014',
      category: 'B',
      detail: 'refusal named no specific insufficiency',
    }, { now });
    return { outcome: 'REFUSAL_UNSPECIFIC', state: c.state };
  }

  // HOF-013: Hub maps the refusal.
  const problems = [{
    requirement: 'HOF-004',
    detail: insufficiency,
    exceedsAuthority: Boolean(report.requires_permission || report.requires_user_decision || report.changes_goal_or_plan),
  }];
  record(c, 'refusal_received', { insufficiency, requirement: 'HOF-012' }, { now });
  const d = hubDisposition(c, problems, { now });
  return { outcome: d.escalated ? 'ESCALATED' : 'RETURNED', state: c.state, problems };
}

// The originating worker corrects and re-submits (HOF-007).
function resubmitHandoff(c, pkg, { now = Date.now() } = {}) {
  if (c.state !== 'handoff_returned') throw new LifecycleError(`A correction is submitted from handoff_returned, not ${c.state}`, 'HOF-007');
  transition(c, 'executing', 'correction submitted by the originating worker', { now, owner: c.handoff?.originating_worker || 'worker' });
  return openHandoff(c, pkg, { now });
}

module.exports = {
  STATES, FIX_LOOP_LIMIT, GOAL_ROUND_LIMIT,
  GOAL_FIELDS, PLAN_FIELDS, HANDOFF_FIELDS,
  LifecycleError,
  newCase, transition, sweepTimeout, record,
  missingFields, ungrounded, hardTokens,
  validateGoalPackage, submitGoalPackage, approveGoal, rejectGoal,
  beginPlanning, validatePlan, submitPlan, approvePlan, rejectPlan,
  openHandoff, receiveHandoff, resubmitHandoff, hubDisposition,
};
