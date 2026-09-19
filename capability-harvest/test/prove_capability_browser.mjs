// prove_capability_browser.mjs — real browser proof for CAP-0001 (export data).
//
// No mocks, no canned responses. Drives the REAL running composed app
// (started by build.py) with a real Chromium browser via Playwright:
//   1. Navigates to /register and fills in the real form
//   2. Navigates to /expenses and adds a real expense through the real form
//   3. Navigates to /settings and clicks the real "Download CSV" link
//   4. Captures the real download and asserts the real expense is in it
//
// Run (after `python3 build.py start`), with the pre-installed global
// Playwright on NODE_PATH:
//   NODE_PATH=/opt/node22/lib/node_modules node test/prove_capability_browser.mjs

// The pre-installed global Playwright has no local package.json for Node's
// ESM resolver to find via bare specifier + NODE_PATH, so it's imported by
// its absolute path instead (see README for why this is the pre-installed
// browser environment's Playwright, not one installed into this project).
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

const manifest = JSON.parse(readFileSync(path.join(PROJECT_ROOT, 'output', 'build_manifest.json'), 'utf8'));
if (!manifest.verification.verified) {
  throw new Error('ABORT: build manifest says the composed app was not verified -- refusing to test it');
}
const baseUrl = `http://${manifest.host}:${manifest.port}`;
const stamp = Date.now();
const username = `harvest-browser-${stamp}`;
const email = `harvest-browser-${stamp}@example.test`;
const password = 'CorrectHorseBattery9!';
const expenseDescription = 'Capability-harvest browser proof expense';

const evidence = { cap_id: 'CAP-0001', base_url: baseUrl, steps: [] };

function record(step, extra) {
  evidence.steps.push({ step, ...extra });
  console.log(`  [${step}]`, extra);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage();

  // 1. Register through the real form
  await page.goto(`${baseUrl}/register`);
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.fill('input[name="confirm_password"]', password);
  await page.click('button[type="submit"], input[type="submit"]');
  await page.waitForLoadState('networkidle');
  record('register', { url: page.url() });
  if (!/dashboard|\/$/.test(page.url())) {
    throw new Error(`registration did not land on the dashboard, landed on ${page.url()}`);
  }

  // 2. Add a real expense through the real form on /expenses -- the form
  // lives in a modal that is hidden until the real "+ Add Expense" button
  // is clicked, same as a real user would have to do.
  await page.goto(`${baseUrl}/expenses`);
  await page.click('button:has-text("+ Add Expense")');
  const modal = page.locator('#addExpenseModal');
  await modal.locator('input[name="description"]').fill(expenseDescription);
  await modal.locator('input[name="category"]').fill('HarvestBrowserProof');
  await modal.locator('input[name="amount"]').fill('17.50');
  await modal.locator('button[type="submit"]').click();
  await page.waitForLoadState('networkidle');
  record('add_expense', { url: page.url() });
  const expensesPageText = await page.content();
  if (!expensesPageText.includes(expenseDescription)) {
    throw new Error('added expense did not appear on the expenses page');
  }

  // 3. Go to settings and click the real "Download CSV" link
  await page.goto(`${baseUrl}/settings`);
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('text=Download CSV'),
  ]);
  const savedPath = path.join(PROJECT_ROOT, 'output', 'browser_export_download.csv');
  await download.saveAs(savedPath);
  record('download_export', { suggested_filename: download.suggestedFilename(), saved_to: savedPath });

  // 4. Verify the REAL downloaded file contains the REAL expense
  const csvText = readFileSync(savedPath, 'utf8');
  if (!csvText.includes(expenseDescription)) {
    throw new Error(`downloaded CSV did not contain the expense we added. CSV was:\n${csvText}`);
  }

  evidence.downloaded_csv_text = csvText;
  evidence.expense_found_in_download = true;
  evidence.verified_at = new Date().toISOString();
  evidence.result = 'PASS';

  const evidenceDir = path.join(PROJECT_ROOT, 'shelf', manifest.verification.app_slug, 'CAP-0001', 'evidence');
  mkdirSync(evidenceDir, { recursive: true });
  const outPath = path.join(evidenceDir, 'TEST_EVIDENCE_BROWSER.json');
  writeFileSync(outPath, JSON.stringify(evidence, null, 2) + '\n');
  console.log(`\nPASS -- wrote ${outPath}`);
  console.log('Downloaded CSV:\n' + csvText);
} finally {
  await browser.close();
}
