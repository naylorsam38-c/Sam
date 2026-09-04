# Builder — component 3 of the chain

Consumes the Assembly Engine's `SPEC.json` (`build_model`) and emits a real,
runnable, dependency-free application. Builds what the spec says — it does
not reinterpret it or invent requirements: every generation rule is small,
explicit, and named after the numbered id it serves, and anything the spec
contains that has no rule refuses (`BuildRefused`, exit 2) rather than being
skipped or guessed at.

## Generation rules (the whole ruleset — nothing implicit)

| Spec construct | Rule | Real dependencies added |
|---|---|---|
| A record with a real view/create/edit/delete grant | `crud_routes()` + `render_crud_handler()` — one sqlite table (`build_schema()`), `/api/<record>s` routes | none (stdlib `sqlite3`) |
| An integration whose provider resolves to `OAUTH_PROVIDERS` | `oauth_routes()` + `render_oauth_handler()` — start/callback/status routes | none (stdlib `urllib.request`) |
| Screen kind `list`, `detail`, `integration_status` | one real HTML file each, vanilla JS, `fetch()` against the real generated routes | none |
| Screen kind `report`, `form`, or anything else | **refused** — no rule yet; see "What this does not do" |

Output is a single directory: `app.py` (stdlib `http.server` +
`ThreadingHTTPServer`), `schema.sql`, `static/*.html`, `run.sh`. No new
dependency beyond Python's standard library — the same constraint Command
Desk's own approved spec already states for itself.

## The OAuth provider registry is a phone book, not a guess

`OAUTH_PROVIDERS` holds real, publicly documented endpoints (`authorize_url`,
`token_url`) for named providers — currently just `google`
(`accounts.google.com` / `oauth2.googleapis.com`). `PROVIDER_ALIASES` maps
real product names to the provider whose infrastructure they actually use
(`gmail` → `google` — a fact, not an invention). An integration whose
provider cannot be resolved this way is refused, never guessed at with a
made-up endpoint.

## Tested against real running servers, not mocks

`tests/test_builder.py` builds real apps and starts them for real:

- **Records/CRUD**, from pm-teamwork's real records and access grants (via
  the Assembly Engine's own `derive()`/`build_model()`): create, list, read,
  update, delete, both real HTML pages, a real 404 — all against a live
  `sqlite3`-backed server on a real port.
- **OAuth**, from Command Desk's own already-approved spec
  (`packages/specgate/examples/good.spec.yaml`, `status: approved`) — the
  provider, env var names, and behaviour are copied from that real document,
  not invented for this Builder. Two of these tests make a **real outbound
  request** to Google's real, live OAuth endpoints (skipped, not faked, if
  that is unreachable): the `/start` route's 302 is followed to a real
  `accounts.google.com` response, and the `/callback` route sends a bogus
  code to Google's real token endpoint and gets a real 401 back, which the
  generated app turns into a real 502 without crashing.

That is also the honest edge of what this Builder (or any automation) can
prove without a human: completing OAuth requires a live person consenting on
Google's own screen. No test here pretends to clear that bar — it stops at
the last step automation can honestly perform and says so.

Building this test suite found and fixed three real bugs: an f-string bug
that evaluated `{f!r}` in a Python list comprehension at code-generation
time instead of leaving it as literal text in the generated code (a
`NameError` in every generated CRUD create/update handler); the `status`
route being double-handled by both its dedicated handler and the generic
per-route dispatch loop (a `KeyError` building `app.py` for any spec with an
integration); and `Gmail` not resolving to the `google` provider because
the resolver only matched literal provider names, not real product aliases.

## What this does not do

- **`report` and `form` screens have no rendering rule yet.** Refused, not
  silently skipped — `test_builder_refuses_on_a_screen_kind_it_has_no_rule_for`
  proves it. Real scope, not fabricated: none of the real specs this Builder
  has actually built need one yet.
- **Only one OAuth provider is registered.** Adding another means adding its
  real, published endpoints to `OAUTH_PROVIDERS` — never inventing one.
- **No authentication/session layer for the record/CRUD path yet** — the
  generated routes are open. Real future work, not attempted here because no
  real spec built so far has needed it (pm-teamwork's real access grants are
  used to decide *which* routes exist, not to gate them per request yet).
