# HARVEST PROCESS v2 — god mode aligned, Flask only

Supersedes `PROCESS.md`. `PROCESS.md` describes the v1 form and is kept only for
reference. Anything it says that contradicts this document is wrong.

Governing spec: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Form: `FORM_TEMPLATE_GODMODE_v2.json`
Admission: enforced inside `harvest_parts.py` at fetch time
Catalog: `catalog.json` (v1.2.0, 70 app types, 81 capabilities, non-button class defined)

---

## The pipeline

One app type at a time. Seven steps. No step may be skipped and no step may be
filled from memory.

### 1. Take the category name

From `catalog.json`. The name is the only input you need. A row with an empty
capability list is not blocked — the name alone drives everything below.

### 2. Name the best app in the market for that category

The real commercial product, by brand name. The one people actually use.
Dating → Tinder. Video conferencing → Zoom. Invoicing → Xero.

Record it in `exemplar.brand_name`, with `evidence_urls`.

### 3. Read its structure and capabilities off that product

What it does, screen by screen, capability by capability. Each one goes in
`exemplar.capability_targets` with what it does and the URL that proves it.

This is the only step where a marketing page or public docs are an acceptable
source, because this step is describing a product, not a contract. Nothing from
this step is ever copied into a capability contract.

### 4. Find the closest open-source equivalent

Same structure, same capability set, as near as it gets. It does not have to be
a clone; it has to be the same shape.

### 5. Apply the admission rules

A candidate repo is admitted only if all four hold:

| Rule | Why |
|---|---|
| Permissive licence — MIT, Apache-2.0, BSD, ISC, MPL-2.0 | code can be taken |
| **Built on Flask** | the host is Flask; routes and handlers lift straight across |
| **Publishes REST API docs** | the contract is written down, not guessed from source |
| Structural match to the step-2 exemplar | otherwise it is a different product |

Any one of these missing → reject the repo and go back to step 4. Do not adapt a
FastAPI, Django or Node app. Do not harvest from a repo with no API docs.

Confirm the branch with `git ls-remote` before recording it.
`raw.githubusercontent.com` returns HTTP 200 for a branch that does not exist and
silently serves the default branch, so a URL check proves nothing.

Record repo, licence, branch, commit, clone path, framework, API docs URL, and a
sentence on how it matches, in `harvest_source`.

### 6. Fill the form from the real code

Open the clone. For each capability:

- read the route and the method out of the real handler
- read the input and output fields out of the real code
- read the error codes out of the real error paths
- record `provenance`: file, symbol, line range

Every capability contract field comes from a file you opened. If you cannot
determine something, leave it blank and name it in `unresolved`. A named blank is
correct. **A guess is a defect.**

God mode constraints that bite here:

- method is **GET or POST only**. A harvested PUT/DELETE/PATCH silently 404s.
- `data_filename` is the raw name. Namespacing to `<slug>__<file>` happens at
  generation, not on the form.
- `data_access` must be declared or `validate_v2_contract` raises `Broken`.
- `shared_lib_calls` may only name the CAP-0000 public API. A raw path read is a
  bypass and fails the gate.
- auth capabilities must be renamed to exactly `Register`, `Login` or
  `Bootstrap Admin`, or slot proving cannot acquire a session.
- `cap_id` must sit inside the app's own 100-block.
- the journey capability must be plain, unauthenticated, text, not an upload,
  and not a non-button capability.
- control labels come out of the code. A promo string off a marketing page — the
  Xero pilot recorded `Get 90% off for 6 months` — is rejected by the gate.

### 7. Run the gate

```
# no gate script -- admission fires inside harvest_parts.py before anything is fetched
```

Exit 0 or the form is not finished. The gate runs the rules god mode enforces at
build time, so a form that passes here is a form `build.py` can generate from.

---

## Non-button capabilities

`catalog.json` defines a second capability class. Fifteen capabilities across
four kinds cannot be driven by one button firing one POST:

- **live connection** — join call, receive message, show unread count, show typing indicator, show presence, share screen
- **streaming media** — mix media streams, stream video
- **device hardware** — capture photo, scan barcode, show map, play audio, play video
- **background worker** — run background sync, read sensor stream

They are harvested from real code like anything else and they are all
Flask-compatible. Two rules apply:

1. the slot needs a real `trigger_type` — `button` is rejected
2. none of them may be the journey target (god mode section 7)

Four capabilities are listed under `needs_decision` in the catalog — track
location, sync offline changes, transcribe speech, synthesise speech. They behave
one way in some products and the other way in others. Decide each, then move it.

---

## Current state

- 70 app types in the catalog, 0 harvested
- both v1 pilot forms were filled from marketing pages, not code, and both fail
  the v2 gate on their real defects
- the gate's **pass path is unproven**, because no form has ever been filled from
  real code. It will be proven by the first real harvest, not before, and not by
  a made-up form
