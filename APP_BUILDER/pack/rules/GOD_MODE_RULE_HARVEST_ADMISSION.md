# God Mode — Harvest Admission Rule

**Status:** active. Governs every capability that enters the shelf.

**Supersedes:** the earlier proposed version of this file, which admitted repos
by framework alone and left the payload question open. Both are settled here.

**Scope.** Applies to every capability that enters the shelf, whether harvested
from an external codebase or written directly against the stack below.

It does **not** grandfather the capabilities previously produced by
`verification/gen_common.py`. Those were machine-generated, their
implementation records carry `"commit": "gen_common.py"` rather than a real
upstream commit, and they are not a parts source. They fail Rule A on
provenance and are out of scope as stock, not exempt from it.

---

## Rule A — One stack, library-wide

Every part on the shelf runs the **same stack: Flask and PostgreSQL.**

A capability may be harvested only from a codebase already built on that stack.

**Reason.** This is the rule the whole library rests on. Parts are only
interchangeable if they speak the same language underneath. Two parts harvested
from different stacks cannot coexist in one app — one wants an ORM session the
other has never heard of, one wants async the other is sync. Fixing that at
assembly time is a rewrite, and a rewrite is where invented code enters the
library.

Pick the stack once, and every part ever harvested fits every other part.

No exceptions for "close enough". Reject the repo.

## Rule B — Published API documentation

The source app must publish REST API documentation.

**Reason.** The capability contract is routes, methods, input fields, output
fields and error codes. If the app documents its API, that contract is already
written down and can be recorded rather than inferred. If it does not, every
contract axis is a reading of source under time pressure, which is where
defects come from.

## Rule C — Licence

Permissive only: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0.

## Rule D — Structural match

The repo must match the commercial exemplar it was chosen against, in structure
and capability set. Recorded in one sentence on the form.

## Rule E — One source per app

All capabilities in a single app come from a single source repo.

**Reason.** Rule A makes parts compatible at the stack level. Rule E keeps them
compatible at the application level — one source means one set of models, one
session model, one set of conventions. Mixing two Flask apps in one build is
still mixing two designs.

Cross-app reuse of a part is governed separately, by the shelf, not by this
rule.

## Rule F — Where no exemplar exists, build the part

If no repo on the stack provides a capability, the capability is **written
directly against the stack** — Flask, PostgreSQL, and the Shared Library
(`CAP-0000`).

A part written this way is a first-class shelf part. It carries the same
records, the same contract and the same approval as a harvested one. What it
does not carry is an upstream commit, so its implementation record names this
system as its origin and says so plainly.

**Reason.** Without this rule the shelf has holes it can never fill, and the
only ways to fill them are to bend Rule A or to fake a part. This rule is what
makes Rule A affordable: the stack stays uniform *because* there is a legitimate
way to fill a gap without leaving it.

Rule F is a fallback, not a shortcut. If a qualifying repo exists, harvest it.

---

## The payload question — settled

A harvested part **runs as its source wrote it.** The host does not require
foreign code to be rewritten into a neutral module shape before it will run.

This is the direct consequence of Rule A. Once every part on the shelf is Flask
on PostgreSQL, the host can run Flask parts natively, because there is no second
framework for it to stay neutral between. The cost of a non-neutral host — that
each app inherits its source's stack — is not a cost here, because the stack is
the same one every time by rule.

What matters is that the capability does what it says it does. The framework
underneath it is an implementation detail, and it is the same detail everywhere.

**Route reading — settled.** `build.py`'s `_extract_route_meta` now reads how
real Flask code declares a route, not only the `ROUTE`/`METHOD` constants a
generated part writes. It understands the decorator form, the `add_url_rule`
call form, and blueprint `url_prefix`, including a rule that opts out of its
prefix. The `ROUTE`/`METHOD` path still works first, so generated parts read
unchanged. It is still static, via the AST — no part is ever imported to find
out where it routes.

The reader was fixed rather than requiring each part to declare its route by
hand, because two sources of truth on the same fact drift: the day the
declaration and the decorator disagree, the app routes somewhere the code does
not. One finite change instead of a duplicated line on every part forever.

Where one handler binds to several real paths — which happens in real source,
e.g. Indico's login binds both `/login/` and `/login/<provider>/` — the reader
returns nothing rather than guessing. The form already records which path the
capability is, so this is a check, not a gap: the declared route is verified to
exist in the source at the pinned commit.

---

## Enforcement

Enforced by `harvest_parts.py`, **at the point code is fetched**. A source that
fails any rule is refused before a single byte is written, so nothing
downstream has to inspect it afterwards. Nothing that reaches the shelf ever
failed a rule.

| Rule | What is refused | Setting |
|---|---|---|
| A framework | not Flask | `REQUIRED_FRAMEWORK` |
| A datastore | not PostgreSQL | `REQUIRED_DATASTORE`, `DATASTORE_ALIASES` |
| B | no published REST API documentation | `REQUIRE_API_DOCS` |
| C | licence not permissive | `ALLOWED_LICENCES` |
| D | no structural match to the exemplar recorded | `REQUIRE_STRUCTURAL_MATCH` |
| E | capabilities naming more than one repo | `ONE_SOURCE_PER_APP` |

All switchable in that script's config block. `ENFORCE_ADMISSION = False`
turns the lot off, which is a decision to admit code the host cannot run.

Refusal is all-or-nothing: one failed rule refuses the whole source. A
partially admitted source is a shelf with a part on it that no rule allowed.

Rule F needs no check. A part written against the stack is written to the
stack by definition; what it needs is an origin naming this system rather than
an upstream commit, recorded on its implementation record.

The former `check_form_godmode.py` is deleted. It inspected a filled form
after the fact; refusal now happens where the code is fetched, which is the
only place it can stop a bad part actually landing.

## Known god mode gaps this rule interacts with

Recorded, not fixed:

- `dispatch()` handles GET and POST only. A harvested REST verb 404s silently.
- `_RAW_PATH_BYPASS_RE` covers one bypass shape, so a novel raw-path read in
  harvested code can slip the static scan.
- No login rate limiting exists anywhere, so a harvested auth capability
  inherits none — including one harvested from a source that had its own.
- `_master_key()` is one local key: no rotation, no per-tenant separation, no
  external KMS.
- A multipart upload cannot be the Playwright journey target.
