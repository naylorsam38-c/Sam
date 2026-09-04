# Section audit: the 22 catalogued parts against the section bar

`SECTION_ARCHITECTURE.md` defines a catalogue entry as a **complete
section**: UI + API + data model + schema/migrations + business logic +
validation + state transitions + permissions + error handling +
notifications + audit + integrations + dependencies + tests +
configuration points, as one reusable unit.

This audit checks the 22 parts currently on the shelf (`parts_shelf.json`)
against that bar, honestly. Per section 9 of the architecture policy,
"unproven sections remain unregistered" — that includes unproven as
*complete sections*, not just unproven as working code. Nothing below is
downgraded or removed from the shelf; the shelf's existing claims (real,
proven, working code) still stand. What changes is a separate, stricter
question: does this part already qualify as a canonical **section**, or
is it (real, proven) raw material that a section still needs to be built
around?

## Verified by reading the actual code (not assumed)

`packages/builder/builder.py` has no session/login/cookie/current-user
mechanism at all (`grep -i "session|login|auth_user|current_user|cookie"`
returns zero matches). Access grants (`access.get("view"/"create"/"edit"/
"delete")`) control whether a route/screen is *generated at build time*
per record — there is no per-request identity check, because there is no
concept of an authenticated request yet.

## Result: zero complete sections exist yet

Nothing currently on the shelf satisfies all fourteen dimensions as one
catalogued unit. Two parts come closest; the rest are real, proven
backend logic with no UI, schema, permissions, or notification/audit
surface of their own.

### Closest to section-shaped (partial)

| part_id | has | missing to become a canonical section |
|---|---|---|
| `crud_list_detail` | UI (list+detail), API, schema (per-record table), build-time access-grant gating, tests | migrations (schema is generated fresh per build, not versioned/altered), per-request permission enforcement (no authenticated identity exists to check against), notifications, audit (not auto-wired to `audit_trail`), a documented configuration-point contract |
| `oauth_connect` | UI (integration status), API (start/callback/status), schema (`connections` table), tests | migrations, notifications on connect/disconnect, audit, error-handling surface beyond the OAuth error redirect, documented configuration points |

### Real, proven, backend-only — ingredients, not sections

All twenty engines below are genuine, working, individually proven
(`PROOFS.md`) — that claim is unchanged. None has UI, its own schema/
migrations, a permissions layer, or notification/audit surface, so none
qualifies as a section on its own: `record_cloning`, `stage_history`,
`stage_conditional_requiredness`, `stock_ledger`, `ledger_balancing`,
`scheduled_jobs`, `document_generation`, `email_parsing`, `audit_trail`,
`scheduling_availability`, `search_fts`, `import_export`,
`file_conversion`, `bank_feed_ofx`, `calendar_ics`, `document_signing`,
`pdf_form_filling`, `workflow_executor`, `reporting_engine`,
`notification_delivery`.

Several of these are the right raw material for sections named directly
in the architecture policy's own examples:

- **Document section** (policy's own example) — `document_generation` +
  `email_parsing` + `document_signing` + `pdf_form_filling` are real
  logic for exactly this, but there is no UI, no unified schema, and no
  single assembled section yet.
- **Scheduling section** (policy's own example) — `scheduling_availability`
  + `scheduled_jobs` + `calendar_ics` are real logic; same gap.

### Named in the policy, does not exist at all

- **Login/Authentication section** — the policy's first standard
  example. Confirmed by direct code inspection: no session mechanism,
  no login screen, no password storage, no per-request identity. This
  is not a partial section; it is fully absent.
- **Payment section** — the policy's second standard example. Already
  established earlier in this project: Stripe is network-blocked in
  this sandbox and no real payment credential exists here. No payment
  section, canonical or otherwise, exists.

## What this means for the five templates right now

None of the five templates' `BOUND_SPEC.json` files change because of
this audit — their bindings point at real, proven parts, and that was
true before this policy and remains true. What this audit adds is the
next layer of truth on top: those bindings are to proven *capability
modules*, not yet to catalogued *sections* as this policy now defines
the word. Promoting a capability module (or a cluster of them, per the
Document/Scheduling examples) into a canonical section is new work —
building the missing UI, schema/migrations, permissions, notification
and audit wiring, and a documented configuration-point contract around
the proven logic — not a relabeling exercise.

## Open, blocked item

Section 7 of the architecture policy (reverse-engineering three
additional complex reference applications for missing sections) cannot
proceed: no such application's source or documented behaviour exists
anywhere in this session's environment. This is unchanged from the
earlier, separate finding that no "Hands" source exists here either. No
section will be fabricated to fill this gap. It starts the moment the
three reference applications are actually supplied.
