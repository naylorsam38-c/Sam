# THE PROCESS — harvest to build

One app has been through this end to end: **event ticketing, app one on the
shelf**, harvested from Indico (CERN), MIT licensed, at commit
`eb90264caec7d1210959c453d1f93ad88a98e6ce`.

Everything in this pack was run for real. Nothing here is generated,
simulated, or filled in from memory.

---

## The sequence

### Step 1 — Send the harvest
`1_harvest/HARVEST_COMMAND_EVENT_TICKETING.md`

Goes out to a fresh session. It says: find a permissively-licensed Flask app
that really does this job, reject the ones that fail admission and log why,
clone the accepted repo, install it, start it, hit it, and prove it runs with
real terminal output.

Admission rules: `rules/GOD_MODE_RULE_HARVEST_ADMISSION.md`.

**What came back for event ticketing:** a running Indico instance on
PostgreSQL 16 and Redis 7, a real event, priced ticket tiers, a completed
registration, and a real PDF ticket with a scannable QR code. See
`evidence/HARVEST_EVIDENCE_README.txt`.

### Step 2 — Record it from real code
`1_harvest/FORM_TEMPLATE_GODMODE_v2.json` → `forms/<slug>.form.json`

The form is filled by opening real files in the clone. Every capability gets a
route, a method, a data shape, an error contract, and a **provenance block**:
source file, source symbol, source line range. Anything not findable in the
code is named in `unresolved`. A named blank is correct; a guess is a defect.

**Result:** `forms/event-ticketing.form.json` — ten capabilities, each with an
exact address into the pinned commit.

### Step 3 — Admission happens at fetch, not after
There is no separate gate script. `check_form_godmode.py` is deleted.

Refusal lives inside `1_harvest/harvest_parts.py` and fires **before anything
is fetched**. A source that fails the Harvest Admission Rule is refused with
its reasons named, nothing is downloaded, and nothing reaches the shelf:

```
REFUSED: <slug> -- fails god mode's Harvest Admission Rule
```

Refusal is all-or-nothing. Settings live in the `ADMISSION` block of
`harvest_parts.py`; `ENFORCE_ADMISSION` turns the lot off.

This is stricter than the old gate, which complained about a part that had
already landed. Fail-tested against four real rejected sources: an AGPL
licence, a Java source, a MySQL datastore, and a source with no datastore
recorded.

The rule itself is `rules/GOD_MODE_RULE_HARVEST_ADMISSION.md`.

### Step 4 — Number it
```
python3 assign_numbers.py
```
`2_numbering/assign_numbers.py` — governed by `rules/GOD_MODE_RULE_NUMBERING.md`.

Allocates the app its sequential number, resolves every capability against the
global registry, and mints a number only when that capability has never been
seen. Writes the app tree: app, screens, controls, every leaf a numbered
reference, down to the individual button (Rule N4).

**Result for event ticketing:** seven screens, ten controls, every control
bound to a capability, nothing unbound. See `trees/event-ticketing.tree.txt`.

Ten capabilities newly minted, none reused — expected, it was the first app
through, so the registry started empty. The second app will reuse `log in`,
`log out`, `register account` and anything else it shares.

### Step 5 — Copy the code onto the shelf  ← THIS STEP WAS MISSING
```
python3 harvest_parts.py forms/event-ticketing.form.json
```
`1_harvest/harvest_parts.py`

Up to this point the numbers were correct addresses pointing at an empty
shelf. The harvest command brings back where the code lives. Nothing went and
fetched it. That is why assembly had nothing to assemble.

For every capability this script fetches the named file **at the pinned
commit**, cuts the named line range, verifies the named symbol is actually in
what it cut, and writes it to `shelf/<slug>/<CAP-id>/` with `PROVENANCE.json`
and `LICENCE.txt` beside it.

**Result:** ten of ten on the shelf, zero failures, every symbol verified.

Proven to fail on purpose:

| Fault injected | What it did |
|---|---|
| Line range moved to the wrong part of the file | `SYMBOL MISSING` — named the symbol and the address that had drifted |
| Source file that does not exist at that commit | `UNREACHABLE` — reported the 404 and the full URL tried |
| `harvest_source.commit` left empty | `REFUSED` — will not harvest off a moving branch |

### Step 5b — Write the records assembly reads
```
python3 shelf_records.py forms/event-ticketing.form.json
```
`1_harvest/shelf_records.py`

Step 5 puts the code on the shelf. `build.py` does not read that layout — it
reads three record files and an alias map:

```
shelf/capabilities/<CAP-id>.json                  the §3.6 record
shelf/implementations/<CAP-id>/<IMPL-id>.json     the §3.7 record
shelf/implementations/<CAP-id>/<IMPL-id>/         the payload directory
shelf/aliases.json                                "name@version" -> CAP/IMPL
```

This writes them. Every value is read off the filled form or the harvest
source block — nothing invented, and nothing taken from any previously
generated library. The implementation record carries the **real upstream
commit**, which is what makes a harvested part traceable and tells it apart
from a generated one.

**Result:** ten of ten records written.

Proven against `build.py` itself — its own loaders and validators imported and
run over the written files:

```
PASS CAP-0001 ... PASS CAP-0010
10 pass, 0 fail  (checked with build.py's own readers and validators)
```

And its own alias resolver, run live:

```
log in@1.0.0           -> CAP-0002/IMPL-01  commit=eb90264caec7
book slot@1.0.0        -> CAP-0007/IMPL-01  commit=eb90264caec7
generate report@1.0.0  -> CAP-0010/IMPL-01  commit=eb90264caec7
take payment@1.0.0     -> NOT ON SHELF
```

Payment correctly absent — nothing was faked to make the list look full.

That test caught a real defect on the first run. The script was writing
`aliases.json` as a flat name-to-id map; `read_shelf_aliases()` parses a list
under the key `aliases`, so build.py read it as empty and every alias missed.
Fixed and retested — that is the difference between running it and reading it.

Proven to fail on purpose:

| Fault injected | What it did |
|---|---|
| `harvest_source.commit` emptied | `REFUSED` — will not record a part with no pinned commit |
| `app_slug` emptied | `REFUSED` |
| Capability with no harvested code on the shelf | `PROBLEM` — named the capability and the path it looked in, wrote the other nine |
| The field `CATEGORY_SOURCE` points at left blank | `REFUSED` — named the setting and the blank field |

### Step 6 — Assemble and prove
```
python3 build.py
```
`3_assembly/build.py`

Reads a choice, assembles the app from parts on the shelf, then proves the app
works in a real browser. Prints one word.

---

## Why step 5 was missing

Rule N5 says *references, never copies* — no capability is ever copied into an
app, because a number is an address and apps reuse the library in place.

The harvest command was written to obey that, so its BRING BACK list asks for
addresses and proof-of-running, and never once asks for the code. Read it: ten
items, not one of them is "the code."

The gap is that N5 forbids copying **into an app** and assumes the library
already exists. Nothing in the rules said how code gets onto the shelf in the
first place. Step 5 is that, and it does not violate N5 — it writes to the
shelf itself, never into an app folder.

**Fold step 5 into the harvest command** so every future app does it in one
pass instead of needing a second run.

---

## Open — these are decisions, not work

### 1. The payload module — the one thing still in the way
The records are done and proven. The **payload** is not.

`build.py` copies a payload module into the app and the host runs it. The host
expects that module to be:

```
ROUTE  = '<path>'          plain string literal, read by AST, never imported
METHOD = '<GET|POST>'      plain string literal
DATA_FILE_NAME = '<file>'  if it stores anything
def handle(request): ...   returns (status, dict)
all storage through _shared from modules/CAP-0000/shared_lib.py
```

The harvested Indico code is not that shape. `RHLogin` is an Indico `RH`
subclass bound to Indico's own base class, its session machinery, its WTForms
and its SQLAlchemy models against PostgreSQL. No mechanical rule turns one
into the other — the storage layer, the session layer and the request layer
are all different.

Proven live. The record declares its entrypoint and the host reads nothing:

```
declared entrypoint: CAP-0002/route.py
ROUTE, METHOD read from it: (None, None)
form says the real route is: /login/  POST
```

Three ways out, and it is a decision, not a script:

- **A. Adapt each harvested part** into the host module contract by hand.
  Honest, slow, and it is real work per capability.
- **B. Change the host** to run the harvested framework as it stands.
  One piece of work instead of seventy, but the host stops being neutral.
- **C. Harvest only from repos whose parts already fit the host contract.**
  Cheapest to build, hardest to source — most real apps will not fit.

This is the fork the whole shelf sits behind.

### 2. Three settings in `build.py` are blank
```
BROKEN  missing setting  LAYER3_MODEL
```
That is the entire output of running it. Its own config block says empty means
refuse — no unnamed third-party dependency. Blank:

- `LAYER3_ENDPOINT`
- `LAYER3_MODEL`
- `LAYER3_CREDENTIAL`

Nothing assembles until these are named.

### 4. Six capabilities were never bound
The catalogue lists these for event ticketing and the harvest could not resolve
them in Indico, so they are correctly absent rather than faked: take payment,
issue refund, apply discount code, send push notification, split payout,
manage inventory.

Indico ships `PaymentPluginMixin` with no concrete subclass in core — there is
no real payment part to point at. That is why payment is unbound, and it is
also why an API key alone will not bind it.

### 5. Keys and parts are separate gaps
A key is a credential for an outside service. A part is code on the shelf.
`send email notification` needs the part on the shelf **and** a key before it
sends anything. Having one does not supply the other.

### 6. The host serves the shelf
`4_host/host.py` builds the source application's own stack, then serves only
the routes belonging to capabilities on the shelf. Everything else the source
ships is refused at dispatch. The shelf decides what the app is.

Proven over a real socket: ten capabilities answered, 1120 routes refused,
zero failures. Every response a shelf capability serves carries an
`X-Shelf-Capability` header naming the number that served it, so a handler
answering "no such record" is distinguishable from the host refusing a route.

Run it:

    INDICO_CONFIG=<real config> python3 4_host/host.py --check   # list, do not serve
    INDICO_CONFIG=<real config> python3 4_host/host.py           # serve
    INDICO_CONFIG=<real config> python3 4_host/host_test.py      # prove over a socket

Full figures in `evidence/LIVE_RUN_EVIDENCE.md`.

### 7. The harvest takes whole modules
The harvester no longer cuts line ranges out of a source file. It fetches the
whole module the symbol lives in; the recorded line range stays on the
provenance as the symbol's address but no longer limits what is fetched.

Cut fragments did not run. An AST check on the old shelf found zero imports on
every part, 28 unresolved names on one, and one part that would not parse at
all. The same check on whole modules: all ten parse, imports present,
**zero unresolved names**.

Settings: `HARVEST_WHOLE_MODULE`, `WHOLE_MODULE_MAX_LINES` in
`1_harvest/harvest_parts.py`.
