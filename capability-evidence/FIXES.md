# `looksLikeImplementation` — defect fixes and evidence

Job 2 from `HANDOFF_capabilities_and_fixes.md`. Standalone module, **not wired
into any pipeline.** Run the tests with `npm test` (or
`node test/run-tests.js`) from this directory — no dependencies, no
network access needed to run them (the real-repo lines were already
harvested into `test/real-lines.js`).

## Gap check, before touching anything

The handoff asked us to find `containsCapabilityToken` in the repo and
establish what `patterns` looks like in practice, before fixing anything.
We searched the whole `naylorsam38-c/Sam` repository: at the time this job
started it contained nothing but a one-line README. `looksLikeImplementation`
had never been wired into anything, `containsCapabilityToken` does not exist
anywhere, and there was no other call site to observe. So instead of
guessing, we designed the contract explicitly and wrote it down in the
module's own header comment (`looksLikeImplementation.js`) for Sam to confirm
or override — it is a decision, not a discovered fact:

- `patterns` is an array of `RegExp`, one per significant word of the
  capability's name, in name order (`patternsForCapabilityName("PDF Export")`
  → `[/pdf/i, /export/i]`).
- `containsCapabilityToken` ORs them — a cheap "does this line mention the
  capability at all" pre-filter.
- `buildCapabilityIdentifierPattern` joins them, in order, into one
  compound-identifier pattern, and is only ever tested against a name this
  module captured from a real declaration.

## The four defects, each proven on real code

Every fixture below is a verbatim line transcribed from a real, public
GitHub repository (repo, path, and blob sha recorded in
`test/real-lines.js` — found via GitHub's own code search, on 2026-09-19).
No line was invented. `npm test` runs all of them against both the
original pasted code (`original_pasted_version.js`, kept only for this
comparison) and the fixed module, and asserts the verdicts below.

| # | Defect | Real line | Repo | old | new |
|---|--------|-----------|------|-----|-----|
| 1 | Token anywhere on the line, not in the declared name | `function export_code(pdf) {` | pelinquin/ConnectedGraph `cg.js` | **true** (bug) | false |
| 2 | `/i` flag lets capitalised prose match keyword regexes | `// Class is exported (eslint flag)` (isolated regex test) | CodingTrain/Flappy-Bird-Clone `bird.js` | **true** (bug) | false |
| 3 | Generic `\b[A-Za-z_][\w]*\s*=\s*` fallback also matches `==` | `if(config.format == "pdf") {` (+2 corroborating repos) | magicbookproject/magicbook `src/plugins/pdf.js` | **true** (bug) | false |
| 4 | `buildCapabilityIdentifierPattern` ORs tokens instead of joining them in order | `async function export_nominees() {` (+1 corroborating repo, +1 direct unit test) | mainy1995/MemeHub-Bot `mha.js` | **true** (bug) | false |

Fix, per defect:

1. Every construct now **captures the declared name** via a regex group,
   and the capability pattern is tested against that captured name only —
   never against the whole line. This was the root cause: the original
   code's first nine checks returned `true` on a construct match
   regardless of what the captured name (if any) actually was.
2. The `i` flag is off every keyword-literal regex (`function`, `class`,
   `def`, `async`, `func`, `type ... struct`, `fn`, `struct`, `impl`).
   Case-insensitivity is still applied, but only when comparing a
   *captured identifier* against the capability's tokens — `pdfExport`,
   `PdfExportService` and `pdf_export` must all still match.
3. The generic `=` fallback is gone. Each language that needs an
   assignment-style construct (Python, Go, Rust, PHP) gets its own
   anchored extractor that requires the match to start the (trimmed)
   line and excludes `==`, `!=`, `<=`, `>=`, `=>` by construction, and
   excludes `if`/`elif`/`while`/`for`/`return`/`assert` lines.
4. `buildCapabilityIdentifierPattern` now joins the tokens **in order**,
   separated by an optional `_`/`-` (camelCase needs no separator), instead
   of OR-ing them. `pdfExport` matches; `export` alone, `exportPdf` (wrong
   order), and `pdfImport` do not.

### True positives (must still match after the fix)

12 real declarations across 7 languages/styles all still return `true`:
JS `class`, JS arrow-const, JS bare `function`, TS-style `export const`
arrow, JS dotted-chain property assignment (`util.pdfExport = function
...`), Python `def`, Go `func`, Rust `fn`, and Java `public void ...` — the
Java case (`youseries/ureport` `ExportManagerImpl.java`) is old=false /
new=true: Java wasn't supported at all before this fix (one of the
"missing languages" the handoff asked for), so that's the language
addition working, not a defect fix.

### True-negative control

A capability word inside a doc comment only
(`HashDefineElectronics/KiCad_BOM_Wizard` `Lib/pdfExport.js`,
`@file pdfExport.js`) — both old and new correctly say `false`.

### Multi-line declarations

`scanSource(source, patterns)` strips comments/strings across the whole
file first (so multi-line block comments and triple-quoted strings are
handled correctly, not just per-line) and joins paren-unbalanced physical
lines into one logical line before matching — proven against a real
wrapped signature (`darshanmarathe/dm-react-components`
`PdfExport.jsx`). Honesty note: we looked for a real case where the join
is the *only* reason a match succeeds (i.e. the capability-bearing name
itself split across lines) and didn't find one — capability names are
conventionally never split mid-identifier, only parameter lists wrap. So
this fixture proves the joiner reconstructs and matches correctly, not
that joining was strictly necessary for a real true positive we found.

### Adversarial pass (not one of the four original defects — new code we
wrote ourselves, so we broke it on purpose before shipping it)

Adding object/map property support (`pdfExport: () => {}`) for handler
registries initially also matched plain config flags:

- `pdf: true,` → wrongly `true`
- `pdf: null,` → wrongly `true`
- `pdf: { enabled: true },` → wrongly `true`

Fixed by requiring the property's value to itself be a function or arrow
function (`pdf: () => registerPdfHandler()` still correctly matches; the
three above now correctly return `false`). All four are permanent
regression fixtures in `test/real-lines.js` (`adversarial`).

## Smaller items from the handoff, addressed

- **Comment/string stripping**: hand-rolled character scanner (not regex —
  regex can't correctly track nested quote/comment state), handles `//`,
  `/* */`, `#`, Ruby `=begin`/`=end`, `'...'`/`"..."`/`` `...` `` with
  escapes, and Python triple-quoted strings.
- **Multi-line declarations**: see `scanSource` above.
- **Added languages**: Java, C#, Kotlin (`fun`), PHP, Ruby (`def name`
  without parens). `SUPPORTED_LANGUAGES` and `UNSUPPORTED_LANGUAGES` are
  both exported explicitly — `c`, `cpp`, `swift`, `scala`, `objective-c`,
  `shell`, `sql`, `perl` are listed as not covered rather than silently
  mismatched. A `false` verdict on an unsupported language is a coverage
  gap, not evidence of absence — documented in the module header.
- **Java/C# method detection requires a visibility modifier**
  (`public`/`private`/`protected`/`internal`) to bound the regex's
  false-positive rate; package-private methods without one are a
  documented gap, not silently claimed as covered.

## What this is not

This does not decide whether a capability is "implemented" — it is one
signal (declaration-name evidence) for whatever pipeline eventually uses
it. It is not wired into anything, per the handoff's instruction, and
`containsCapabilityToken`'s contract above is a design decision flagged
for Sam, not a discovered fact.
