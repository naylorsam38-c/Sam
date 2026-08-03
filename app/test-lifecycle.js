'use strict';

// Unit tests for the lifecycle engine. No server, no network, no clock — time
// is injected, so the timeout rules are tested rather than waited for.
//
//   node test-lifecycle.js

const L = require('./lifecycle');

let passed = 0;
const failures = [];

function check(name, condition, detail = '') {
  if (condition) { passed += 1; console.log(`  PASS  ${name}`); }
  else { failures.push(`${name}${detail ? ` — ${detail}` : ''}`); console.log(`  FAIL  ${name}${detail ? ` — ${detail}` : ''}`); }
}
function group(t) { console.log(`\n${t}`); }
function threw(fn) {
  try { fn(); return null; } catch (e) { return e; }
}

const GOOD_GOAL = {
  locked_goal_candidate: 'A habit tracker exists that records habits',
  scope: ['Recording habits'],
  exclusions: ['Reminders'],
  constraints: ['One machine'],
  assumptions: ['Sam is the only user'],
  success_criteria: ['A habit can be recorded and read back'],
  known_risks: ['Scope grows'],
  unresolved_questions: ['Whether history is kept'],
  confidence: 'medium',
  evidence: ['The request asks for a habit tracker'],
};

function approvedCase(request = 'a habit tracker') {
  const c = L.newCase(request);
  L.submitGoalPackage(c, GOOD_GOAL);
  L.approveGoal(c);
  return c;
}

function goodPlan(c) {
  const ref = c.locked_goal_id;
  return {
    phases: [{ name: 'Build', ref, outcome: 'A working thing' }],
    tasks: [{ name: 'Write it', ref, owner: 'builder', done_when: 'it runs' }],
    dependencies: ['none'], owners: ['builder'], required_inputs: ['the goal'],
    evidence_requirements: ['a run log'], decision_gates: ['Sam approves'],
    risks: ['scope creep'], rollback: 'revert', completion_criteria: ['tasks done'],
    final_verification: 'the suite passes',
  };
}

function executingCase() {
  const c = approvedCase();
  L.beginPlanning(c);
  L.submitPlan(c, goodPlan(c));
  L.approvePlan(c);
  return c;
}

function goodHandoff(c) {
  return {
    handoff_id: 'h1', locked_goal_id: c.locked_goal_id, plan_id: c.plan_id,
    originating_worker: 'builder', intended_recipient: 'tester',
    completed_responsibilities: ['built it'], work_product: 'the thing',
    evidence: ['a run log'], requirement_coverage: ['all covered'],
    unresolved_items: ['none'], risks: ['none'], confidence: 'medium',
    requested_next_action: 'verify it',
  };
}

// ---------------------------------------------------------------------------

group('The state machine cannot be stepped around');
{
  const c = L.newCase('a habit tracker');
  const e = threw(() => L.transition(c, 'executing', 'skip ahead'));
  check('an unlisted transition is refused', Boolean(e), 'it was allowed');
  check('the refusal names the rule', e?.requirement === 'WF-EXIT', e?.requirement);
  check('the case did not move', c.state === 'goal_forming', c.state);
  check('the refusal is written to the audit log',
    c.audit.some((r) => r.event === 'transition_refused'));
  check('INV-013 — the state carries exactly one owner', typeof c.owner === 'string' && c.owner.length > 0);
}

group('GF-007 — Hub rejects invented detail rather than trusting the pair');
{
  const c = L.newCase('a habit tracker');
  const invented = { ...GOOD_GOAL, constraints: ['Must ship by 2026-09-01 for £4,500'] };
  const problems = L.validateGoalPackage(c, invented);
  check('a date absent from the request is caught', problems.some((p) => p.requirement === 'GF-007'));
  const detail = problems.find((p) => p.requirement === 'GF-007').detail;
  check('the invented date is named', detail.includes('2026-09-01'), detail);
  check('the invented amount is named', detail.includes('4500'), detail);
  check('a grounded package passes', L.validateGoalPackage(L.newCase('a habit tracker'), GOOD_GOAL).length === 0);
}

group('GF-002 — a goal package may not carry implementation instructions');
{
  const c = L.newCase('a habit tracker');
  const p = L.validateGoalPackage(c, { ...GOOD_GOAL, implementation_instructions: ['use sqlite'] });
  check('implementation detail in a goal package is caught', p.some((x) => x.requirement === 'GF-002'));
}

group('GF-006 — the package must be complete');
{
  const c = L.newCase('a habit tracker');
  const p = L.validateGoalPackage(c, { ...GOOD_GOAL, success_criteria: [] });
  check('an empty required field is caught', p.some((x) => x.requirement === 'GF-006'));
  check('the missing field is named', p.find((x) => x.requirement === 'GF-006').detail.includes('success_criteria'));
}

group('GF-005 — the pair stops at the round limit instead of looping forever');
{
  const c = L.newCase('a habit tracker');
  let last;
  for (let i = 0; i < L.GOAL_ROUND_LIMIT; i++) last = L.submitGoalPackage(c, { ...GOOD_GOAL, evidence: [] });
  check('the round limit ends goal formation', last.atRoundLimit === true);
  check('an unvalidated package still goes to Sam, not to planning', c.state === 'goal_review', c.state);
  check('the defect is not silently dropped', last.problems.length > 0);
}

group('GF-008 / INV-015 — the Locked Goal is set once and never again');
{
  const c = approvedCase();
  check('approval locks the goal', c.locked_goal === GOOD_GOAL.locked_goal_candidate);
  check('a goal id is issued', /^goal_[0-9a-f]{16}$/.test(c.locked_goal_id), c.locked_goal_id);
  check('the goal package is frozen', Object.isFrozen(c.goal_package));
  const e = threw(() => L.approveGoal(c));
  check('a second approval is refused', Boolean(e));
}

group('PLN-001 — planning cannot begin before the goal is approved');
{
  const c = L.newCase('a habit tracker');
  L.submitGoalPackage(c, GOOD_GOAL);
  const e = threw(() => L.beginPlanning(c));
  check('planning from goal_review is refused', e?.requirement === 'PLN-001', e?.requirement);
}

group('PLN-002 / PLN-004 — one plan, every element tied to the approved goal');
{
  const c = approvedCase(); L.beginPlanning(c);
  const menu = { ...goodPlan(c), options: [{ a: 1 }, { b: 2 }] };
  check('a menu of options is refused', L.validatePlan(c, menu).some((p) => p.requirement === 'PLN-002'));

  const unref = goodPlan(c);
  unref.tasks = [{ name: 'Write it', owner: 'builder', done_when: 'it runs' }];
  const p = L.validatePlan(c, unref);
  check('a task with no reference is refused', p.some((x) => x.requirement === 'PLN-004'));

  const byCriterion = goodPlan(c);
  byCriterion.tasks = [{ name: 'Write it', ref: GOOD_GOAL.success_criteria[0], owner: 'builder', done_when: 'ok' }];
  check('a reference to an approved success criterion is accepted',
    !L.validatePlan(c, byCriterion).some((x) => x.requirement === 'PLN-004'));
}

group('PLN-005 — planning may not alter the Locked Goal');
{
  const c = approvedCase(); L.beginPlanning(c);
  const out = L.submitPlan(c, { ...goodPlan(c), locked_goal: 'something else entirely' });
  check('the alteration is caught', out.problems.some((p) => p.requirement === 'PLN-005'));
  check('work stops and goal formation reopens', out.goalReopened === true && c.state === 'goal_forming', c.state);
  check('the Locked Goal is cleared, not quietly kept', c.locked_goal === null);
  check('the reopening is on the record', c.audit.some((r) => r.event === 'goal_reopened'));
}

group('PLN-006 — execution opens only after Sam approves the plan');
{
  const c = approvedCase(); L.beginPlanning(c);
  L.submitPlan(c, goodPlan(c));
  check('a validated plan waits in plan_review', c.state === 'plan_review', c.state);
  L.approvePlan(c);
  check('approval opens execution', c.state === 'executing', c.state);
  check('the plan is frozen', Object.isFrozen(c.plan));
  check('a plan id is issued', /^plan_[0-9a-f]{16}$/.test(c.plan_id), c.plan_id);
}

group('HOF-002 / HOF-009 — Hub validates before the receiver is asked');
{
  const c = executingCase();
  const r = L.openHandoff(c, { ...goodHandoff(c), evidence: [] });
  check('a package with no evidence is refused', r.problems.some((p) => p.requirement === 'HOF-009'));
  check('it never reaches the receiver', c.state !== 'handoff_awaiting_acceptance', c.state);
  check('ownership stays with the originating worker', c.owner === 'builder', c.owner);
}

group('INV-012 — a package from another goal is escalated, not returned');
{
  const c = executingCase();
  const r = L.openHandoff(c, { ...goodHandoff(c), locked_goal_id: 'goal_deadbeefdeadbeef' });
  check('the mismatch is caught', r.problems.some((p) => p.requirement === 'INV-012'));
  check('HOF-010 — it escalates rather than returns', c.state === 'handoff_escalated', c.state);
  check('ownership returns to Hub', c.owner === 'hub', c.owner);
}

group('HOF-004 / HOF-006 — acceptance is what completes a handoff');
{
  const c = executingCase();
  L.openHandoff(c, goodHandoff(c));
  check('a valid package reaches the receiver', c.state === 'handoff_awaiting_acceptance', c.state);
  check('the receiver owns it while deciding', c.owner === 'receiving_worker', c.owner);
  const out = L.receiveHandoff(c, { accepted: true });
  check('acceptance transfers ownership', out.outcome === 'ACCEPTED' && c.owner === 'tester', c.owner);
  check('INV-014 — both events are on the record',
    c.audit.some((r) => r.event === 'handoff_validated_by_hub') && c.audit.some((r) => r.event === 'handoff_accepted'));
}

group('HOF-004 — the receiver may not reinterpret the Locked Goal');
{
  const c = executingCase();
  L.openHandoff(c, goodHandoff(c));
  L.receiveHandoff(c, { accepted: true, goal_dispute: 'I think the goal is wrong' });
  check('the dispute is refused and logged', c.audit.some((r) => r.event === 'goal_dispute_refused'));
}

group('HOF-012 — a worker cannot set the outcome itself');
{
  const c = executingCase();
  L.openHandoff(c, goodHandoff(c));
  L.receiveHandoff(c, { state: 'ACCEPTED', insufficiency: 'the evidence does not cover the second criterion' });
  check('the claimed state is ignored and logged',
    c.audit.some((r) => r.event === 'worker_state_claim_ignored' && r.claimed === 'ACCEPTED'));
  check('Hub decided the outcome instead', c.state === 'handoff_returned', c.state);
}

group('HOF-014 — a refusal naming nothing specific is returned to the receiver');
{
  const c = executingCase();
  L.openHandoff(c, goodHandoff(c));
  const out = L.receiveHandoff(c, { accepted: false, insufficiency: '   ' });
  check('the vague refusal is not acted on', out.outcome === 'REFUSAL_UNSPECIFIC');
  check('ownership does not transfer', c.state === 'handoff_awaiting_acceptance', c.state);
  check('it is classified Category B against the receiver',
    c.audit.some((r) => r.event === 'refusal_returned_to_receiver' && r.category === 'B'));
}

group('HOF-013 — Hub maps the refusal by rule');
{
  const correctable = executingCase();
  L.openHandoff(correctable, goodHandoff(correctable));
  const a = L.receiveHandoff(correctable, { accepted: false, insufficiency: 'the run log is missing' });
  check('a correctable defect returns', a.outcome === 'RETURNED' && correctable.state === 'handoff_returned');

  const beyond = executingCase();
  L.openHandoff(beyond, goodHandoff(beyond));
  const b = L.receiveHandoff(beyond, { accepted: false, insufficiency: 'this needs a new scope', changes_goal_or_plan: true });
  check('a defect that would change the goal escalates', b.outcome === 'ESCALATED' && beyond.state === 'handoff_escalated');

  const perm = executingCase();
  L.openHandoff(perm, goodHandoff(perm));
  const d = L.receiveHandoff(perm, { accepted: false, insufficiency: 'sending this needs authorisation', requires_permission: true });
  check('a defect needing a permission escalates', d.outcome === 'ESCALATED', perm.state);
}

group('The fix loop runs twice, then escalates');
{
  const c = executingCase();
  const thin = { ...goodHandoff(c), evidence: [] };
  L.openHandoff(c, thin);
  check('first failure returns', c.state === 'handoff_returned' && c.fix_attempts === 1, `${c.state}/${c.fix_attempts}`);
  L.resubmitHandoff(c, thin);
  check('second failure returns', c.state === 'handoff_returned' && c.fix_attempts === 2, `${c.state}/${c.fix_attempts}`);
  L.resubmitHandoff(c, thin);
  check('the third attempt escalates instead of returning', c.state === 'handoff_escalated', c.state);
  check('the limit is named in the record',
    c.audit.some((r) => r.event === 'transition' && /fix loop limit/.test(r.reason || '')));
  check('the attempt counter never exceeded the limit', c.fix_attempts === L.FIX_LOOP_LIMIT, String(c.fix_attempts));
}

group('HOF-011 — a timeout escalates, and is never retried or accepted');
{
  const c = executingCase();
  const t0 = c.enteredAt;
  L.openHandoff(c, goodHandoff(c), { now: t0 });
  check('the state carries a timeout', L.STATES[c.state].timeoutMs === 30000, String(L.STATES[c.state].timeoutMs));
  check('nothing happens before the deadline', L.sweepTimeout(c, { now: t0 + 29999 }) === false);
  check('the deadline fires', L.sweepTimeout(c, { now: t0 + 30000 }) === true);
  check('it resolves to escalated', c.state === 'handoff_escalated', c.state);
  check('ownership returns to Hub', c.owner === 'hub', c.owner);
  const row = c.audit.find((r) => r.event === 'timeout');
  check('the timeout is the logged reason', /timeout/.test(row?.reason || ''), row?.reason);
  check('it names HOF-011', row?.requirement === 'HOF-011');
  check('it was not retried', row?.retried === false);
  check('it did not resolve to accepted', !c.audit.some((r) => r.event === 'handoff_accepted'));
}

group('Every state in the table has its specified timeout');
{
  const expected = {
    handoff_validating: 30000, handoff_awaiting_acceptance: 30000,
    handoff_returned: 120000, goal_forming: null, goal_review: null,
    goal_approved: null, plan_forming: null, plan_review: null,
    plan_approved: null, handoff_escalated: null,
  };
  for (const [state, ms] of Object.entries(expected)) {
    check(`${state} timeout is ${ms === null ? 'none' : ms / 1000 + 's'}`, L.STATES[state].timeoutMs === ms, String(L.STATES[state]?.timeoutMs));
  }
  for (const [state, def] of Object.entries(expected)) {
    void def;
    check(`${state} lists its permitted exits`, Array.isArray(L.STATES[state].exits));
  }
}

console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) { console.log('\nFailures:'); for (const f of failures) console.log(`  - ${f}`); }
process.exit(failures.length ? 1 : 0);
