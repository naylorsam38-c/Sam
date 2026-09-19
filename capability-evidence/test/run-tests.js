'use strict';

/*
 * Standalone test runner for the looksLikeImplementation fix.
 * Run with: node capability-evidence/test/run-tests.js
 *
 * Every fixture in real-lines.js is a verbatim transcription of a real,
 * public GitHub file (repo/path/sha recorded). Nothing here is mocked or
 * synthesised — see the "no mocks" standing rule in the handoff.
 *
 * Exit code is 0 only if every assertion below passed.
 */

const assert = require('assert');
const path = require('path');

const oldImpl = require(path.join(__dirname, '..', 'original_pasted_version.js'));
const newImpl = require(path.join(__dirname, '..', 'looksLikeImplementation.js'));
const fixtures = require(path.join(__dirname, 'real-lines.js'));

let passed = 0;
let failed = 0;
const rows = [];

function record(section, description, provenance, oldVerdict, newVerdict, expectedOld, expectedNew) {
    const oldOk = expectedOld === undefined || oldVerdict === expectedOld;
    const newOk = expectedNew === undefined || newVerdict === expectedNew;
    const ok = oldOk && newOk;
    if (ok) passed += 1; else failed += 1;
    rows.push({
        section,
        description,
        provenance: provenance ? `${provenance.repo} :: ${provenance.path} (${provenance.sha.slice(0, 12)})` : '',
        old: oldVerdict,
        new: newVerdict,
        changed: oldVerdict !== newVerdict,
        ok,
    });
    assert.strictEqual(oldOk, true, `[${section}] unexpected OLD verdict for: ${description}`);
    assert.strictEqual(newOk, true, `[${section}] unexpected NEW verdict for: ${description}`);
}

console.log('=== DEFECT 1: token-anywhere-on-line vs token-in-declared-name ===');
for (const c of fixtures.defect1) {
    const patterns = newImpl.patternsForCapabilityName(c.capability);
    const oldV = oldImpl.looksLikeImplementation(c.line, patterns);
    const newV = newImpl.looksLikeImplementation(c.line, patterns);
    record('defect1', c.line, c.provenance, oldV, newV, c.expectOld, c.expectNew);
    console.log(`  "${c.line}"  old=${oldV} new=${newV}  (${c.provenance.repo})`);
    console.log(`    ${c.note}`);
}

console.log('\n=== DEFECT 2: /i flag on keyword regexes (isolated at the regex level) ===');
for (const c of fixtures.defect2) {
    const oldClassRe = /\bclass\s+[A-Za-z_$][\w$]*/i;
    const newClassRe = /\bclass\s+[A-Za-z_$][\w$]*/; // same source as CONSTRUCTS' class-declaration regex, no i
    const oldV = oldClassRe.test(c.rawFragment);
    const newV = newClassRe.test(c.rawFragment);
    record('defect2', c.rawFragment, c.provenance, oldV, newV, true, false);
    console.log(`  "${c.rawFragment}"  old(/i)=${oldV} new(no /i)=${newV}  (${c.provenance.repo})`);
    console.log(`    ${c.note}`);
}
// Corroborating end-to-end check: the same comment line, run through the
// full matcher, for the "export data" capability (#13 in Sam's 81 names).
// Comment-stripping alone already removes it; the /i removal is defense in
// depth for the case a comment style slips past the stripper.
{
    const line = fixtures.defect2[0].rawFragment;
    const patterns = newImpl.patternsForCapabilityName(fixtures.CAPABILITY_EXPORT_DATA);
    const oldV = oldImpl.looksLikeImplementation(line, patterns);
    const newV = newImpl.looksLikeImplementation(line, patterns);
    record('defect2-e2e', line, fixtures.defect2[0].provenance, oldV, newV, undefined, false);
    console.log(`  end-to-end (capability "${fixtures.CAPABILITY_EXPORT_DATA}"): old=${oldV} new=${newV}`);
}

console.log('\n=== DEFECT 3: generic `=` fallback also matches `==` ===');
for (const c of fixtures.defect3) {
    const patterns = newImpl.patternsForCapabilityName(c.capability);
    const oldV = oldImpl.looksLikeImplementation(c.line, patterns);
    const newV = newImpl.looksLikeImplementation(c.line, patterns);
    record('defect3', c.line, c.provenance, oldV, newV, c.expectOld, c.expectNew);
    console.log(`  "${c.line}"  old=${oldV} new=${newV}  (${c.provenance.repo})`);
    console.log(`    ${c.note}`);
}

console.log('\n=== DEFECT 4: OR-joined tokens vs AND-joined (ordered) identifier pattern ===');
for (const c of fixtures.defect4) {
    if (c.capturedName) {
        const patterns = newImpl.patternsForCapabilityName(fixtures.CAPABILITY_PDF_EXPORT);
        const oldPattern = oldImpl.buildCapabilityIdentifierPattern(patterns);
        const newPattern = newImpl.buildCapabilityIdentifierPattern(patterns);
        const oldV = oldPattern.test(c.capturedName);
        const newV = newPattern.test(c.capturedName);
        record('defect4-unit', `buildCapabilityIdentifierPattern vs "${c.capturedName}"`, null, oldV, newV, true, false);
        console.log(`  captured name "${c.capturedName}"  old(OR)=${oldV} new(AND,ordered)=${newV}`);
        console.log(`    ${c.note}`);
        continue;
    }
    const patterns = newImpl.patternsForCapabilityName(c.capability);
    const oldV = oldImpl.looksLikeImplementation(c.line, patterns);
    const newV = newImpl.looksLikeImplementation(c.line, patterns);
    record('defect4', c.line, c.provenance, oldV, newV, c.expectOld, c.expectNew);
    console.log(`  "${c.line}"  old=${oldV} new=${newV}  (${c.provenance.repo})`);
    console.log(`    ${c.note}`);
}

console.log('\n=== TRUE POSITIVES: real declarations that genuinely carry the capability ===');
for (const c of fixtures.truePositives) {
    const patterns = newImpl.patternsForCapabilityName(c.capability);
    const oldV = oldImpl.looksLikeImplementation(c.line, patterns);
    const newV = newImpl.looksLikeImplementation(c.line, patterns);
    record('true-positive', c.line, c.provenance, oldV, newV, undefined, true);
    console.log(`  "${c.line}"  old=${oldV} new=${newV}  (${c.provenance.repo})`);
}

console.log('\n=== TRUE NEGATIVE CONTROL: capability word inside a doc comment only ===');
for (const c of fixtures.trueNegatives) {
    const patterns = newImpl.patternsForCapabilityName(c.capability);
    const oldV = oldImpl.looksLikeImplementation(c.line, patterns);
    const newV = newImpl.looksLikeImplementation(c.line, patterns);
    record('true-negative', c.line, c.provenance, oldV, newV, false, false);
    console.log(`  "${c.line}"  old=${oldV} new=${newV}  (${c.provenance.repo})`);
}

console.log('\n=== ADVERSARIAL: config flags must not count as implementation ===');
for (const c of fixtures.adversarial) {
    const patterns = newImpl.patternsForCapabilityName(c.capability);
    const newV = newImpl.looksLikeImplementation(c.line, patterns);
    record('adversarial', c.line, null, 'n/a', newV, undefined, c.expect);
    console.log(`  "${c.line}"  new=${newV} (expected ${c.expect})  — ${c.note}`);
}

console.log('\n=== MULTI-LINE DECLARATION: real wrapped signature, scanSource() joins it ===');
{
    // Real wrapped parameter list, verbatim from darshanmarathe/dm-react-components
    // src/stories/PdfExport/PdfExport.jsx (sha 4bffdba927adbb98d30cb5ebd0d30b0f2a01bbcc).
    const source = [
        'export default function PdfExport({',
        '  element,',
        '  filename,',
        '}) {',
    ].join('\n');
    const patterns = newImpl.patternsForCapabilityName(fixtures.CAPABILITY_PDF_EXPORT);
    const results = newImpl.scanSource(source, patterns);
    const anyMatch = results.some((r) => r.matched);
    const ok = anyMatch === true;
    if (ok) passed += 1; else failed += 1;
    rows.push({
        section: 'multiline',
        description: 'wrapped PdfExport({ element, filename, }) signature',
        provenance: 'darshanmarathe/dm-react-components :: src/stories/PdfExport/PdfExport.jsx (4bffdba927ad)',
        old: 'n/a',
        new: anyMatch,
        changed: 'n/a',
        ok,
    });
    console.log(`  joined logical line matched=${anyMatch} (expected true)`);
    assert.strictEqual(anyMatch, true, 'scanSource should reconstruct and match the wrapped PdfExport signature');
    // Honesty note: this fixture proves the joiner works correctly on a
    // real wrapped signature. We looked for a real repo case where joining
    // is the ONLY reason a real true-positive is found (i.e. line 1 alone
    // would not match) and did not find one in the searches run for this
    // job — the capability-bearing name is conventionally never itself
    // split across lines, only the parameter list is. Reporting that
    // honestly rather than constructing one.
}

console.log('\n--- SUMMARY TABLE ---');
console.log(rows.map((r) => `[${r.ok ? 'PASS' : 'FAIL'}] ${r.section.padEnd(14)} old=${String(r.old).padEnd(5)} new=${String(r.new).padEnd(5)} changed=${String(r.changed).padEnd(5)} ${r.description}`).join('\n'));

const beforeAfter = {};
for (const r of rows) {
    beforeAfter[r.section] = beforeAfter[r.section] || { total: 0, changed: 0 };
    beforeAfter[r.section].total += 1;
    if (r.changed === true) beforeAfter[r.section].changed += 1;
}
console.log('\n--- BEFORE/AFTER COUNTS PER SECTION ---');
for (const [section, counts] of Object.entries(beforeAfter)) {
    console.log(`  ${section}: ${counts.total} cases, ${counts.changed} changed verdict old->new`);
}

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
    process.exitCode = 1;
}
