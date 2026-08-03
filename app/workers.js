'use strict';

// ---------------------------------------------------------------------------
// Forge and Mind — the declared isolated pair (HOF-001).
//
// Forge proposes materially distinct interpretations (GF-003). Mind attacks
// the strongest defect and designs nothing (GF-004). Neither decides anything:
// they produce candidate content, and lifecycle.js decides whether Hub accepts
// it. The model roster is fixed by document 02 and is not negotiable at
// runtime, so the model ids live here rather than in an environment variable
// a caller could quietly change.
// ---------------------------------------------------------------------------

const MODEL_FORGE = 'claude-sonnet-5';   // document 02
const MODEL_MIND = 'claude-sonnet-5';    // document 02

const JSON_ONLY = 'Respond with ONLY a JSON object. No prose, no code fences.';

const FORGE_GOAL_SYSTEM = `You are Forge. You propose the goal, never the implementation.

${JSON_ONLY} It must match exactly:
{
  "locked_goal_candidate": "one sentence stating what must be true when this is done",
  "scope": ["what is included"],
  "exclusions": ["what is deliberately not included"],
  "constraints": ["limits that apply"],
  "assumptions": ["what you are taking as true, and why"],
  "success_criteria": ["measurable, checkable statements"],
  "known_risks": ["what realistically goes wrong"],
  "unresolved_questions": ["what you cannot settle from the request alone"],
  "confidence": "high | medium | low",
  "evidence": ["the part of the request each claim rests on"]
}

Hard rules:
- Never state HOW the work will be done. That is planning, not goal formation.
- Never introduce a number, amount, date, name, address or reference that is
  not in the request. An invented detail fails the package outright.
- Where the request admits materially distinct readings, take the one you can
  most defend and put the others in unresolved_questions.
- If something cannot be settled from the request, it belongs in
  unresolved_questions, not in an assumption dressed up as fact.`;

const MIND_SYSTEM = `You are Mind. You attack what Forge proposes. You design nothing.

${JSON_ONLY} It must match exactly:
{
  "strongest_defect": "the single worst ambiguity, unsupported assumption, scope defect or success-criteria defect",
  "why_it_matters": "what goes wrong downstream if it stands",
  "specific_correction": "what would resolve it — a correction to state, not a design",
  "survives": true or false
}

Hard rules:
- Attack one defect, the strongest. A list of quibbles is not an attack.
- Never propose an implementation, an architecture or a sequence of steps.
- "survives": true only when you cannot find a material defect.
- Never introduce a number, amount, date, name or reference that is not in the
  request.`;

const FORGE_PLAN_SYSTEM = `You are Forge in planning. The Locked Goal is immutable and reference-only —
you may not restate, improve or reinterpret it.

${JSON_ONLY} It must match exactly:
{
  "phases": [{"name": "...", "ref": "<locked_goal_id or an exact success criterion>", "outcome": "..."}],
  "tasks": [{"name": "...", "ref": "<locked_goal_id or an exact success criterion>", "owner": "...", "done_when": "..."}],
  "dependencies": ["what must exist before what"],
  "owners": ["who owns each phase"],
  "required_inputs": ["what must be supplied before work starts"],
  "evidence_requirements": ["what proof each phase must produce"],
  "decision_gates": ["the points where a decision is required before continuing"],
  "risks": ["what goes wrong, and the early warning sign"],
  "rollback": "how to get back to a known good state",
  "completion_criteria": ["how it is known to be finished"],
  "final_verification": "the check that settles it"
}

Hard rules:
- One recommended plan. Not a menu, not alternatives, not "option A or B".
- EVERY phase and EVERY task must carry "ref" set to the locked_goal_id you
  are given, or to one of the approved success criteria copied exactly.
- Never introduce a number, amount, date, name or reference that is not in the
  request or the approved goal.`;

function extractJson(text) {
  const fenced = String(text).match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = fenced ? fenced[1] : String(text);
  const start = candidate.indexOf('{');
  const end = candidate.lastIndexOf('}');
  if (start < 0 || end <= start) return null;
  try { return JSON.parse(candidate.slice(start, end + 1)); } catch { return null; }
}

// One round of goal formation: Forge proposes, Mind attacks (GF-003, GF-004).
// `call` is injected so the pair can be exercised without a network.
async function goalRound({ call, request, priorDefect, maxTokens = 2048 }) {
  const forgePrompt = priorDefect
    ? `Request: ${request}\n\nYour previous package was attacked on this point:\n${priorDefect}\n\nProduce a corrected package.`
    : `Request: ${request}`;

  const forge = await call({ model: MODEL_FORGE, system: FORGE_GOAL_SYSTEM, maxTokens,
    messages: [{ role: 'user', content: forgePrompt }] });
  const pkg = extractJson(forge.text);
  if (!pkg) return { pkg: null, attack: null, raw: forge.text };

  const mind = await call({ model: MODEL_MIND, system: MIND_SYSTEM, maxTokens,
    messages: [{ role: 'user', content: `Request: ${request}\n\nForge proposes:\n${JSON.stringify(pkg, null, 2)}` }] });
  const attack = extractJson(mind.text);
  return { pkg, attack, raw: null };
}

async function planRound({ call, request, goalPackage, lockedGoal, lockedGoalId, priorDefect, maxTokens = 3072 }) {
  const context = [
    `Request: ${request}`,
    `locked_goal_id: ${lockedGoalId}`,
    `Locked Goal (immutable, reference only): ${lockedGoal}`,
    `Approved success criteria (copy exactly when used as a ref):`,
    ...(goalPackage.success_criteria || []).map((c) => `  - ${c}`),
    `Scope: ${JSON.stringify(goalPackage.scope)}`,
    `Exclusions: ${JSON.stringify(goalPackage.exclusions)}`,
    `Constraints: ${JSON.stringify(goalPackage.constraints)}`,
  ];
  if (priorDefect) context.push('', `Your previous plan was rejected on this point:`, priorDefect);

  const forge = await call({ model: MODEL_FORGE, system: FORGE_PLAN_SYSTEM, maxTokens,
    messages: [{ role: 'user', content: context.join('\n') }] });
  return { plan: extractJson(forge.text), raw: forge.text };
}

module.exports = { MODEL_FORGE, MODEL_MIND, goalRound, planRound, extractJson,
  FORGE_GOAL_SYSTEM, MIND_SYSTEM, FORGE_PLAN_SYSTEM };
