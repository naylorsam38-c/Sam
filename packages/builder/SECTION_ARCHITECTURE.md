# Canonical Complete-Section Architecture

This document is the governing architecture policy for the Capability
Catalogue. It supersedes the earlier framing of the catalogue as a
collection of independent engines. It does not itself register or build
anything — `SECTION_AUDIT.md` in this directory applies it to what
currently exists.

## 1. Canonical sections, not engines

The five original application templates (Accounting/Ledger,
Booking/Front Desk, CRM/Pipeline, ERP/Backbone, Project
Management/Teamwork) are reference structures for complete applications,
not a checklist of engines to rebuild per app.

A catalogue entry represents a **complete, reusable section** of an
application. A complete section includes, as one unit:

- frontend/UI
- backend/API
- data models
- database schema and migrations
- business logic
- validation
- state transitions
- permissions
- error handling
- notifications
- audit behaviour
- integrations
- required dependencies
- tests
- configuration points

A section must be usable in another application without rebuilding its
underlying functionality.

## 2. One canonical implementation per capability

Where the same capability is needed by multiple applications, there is
one canonical implementation. The Builder reuses it; it does not create
a second implementation of a capability that already has a catalogued
section. Standard examples: Login/Authentication, Payment, Document,
Scheduling — every application needing one of these uses the same
section.

## 3. Configuration, not reimplementation

Application-specific differences are handled by configuring the
canonical section and controlling its exposed surface (which buttons,
menu items, fields, actions, sections are visible; labels; config
values) — never by rewriting the section's underlying implementation.
The Payment section, for example, stays structurally identical across
apps; only the configured provider/method changes.

## 4. The five original templates

Their purpose is to define complete application structures and the
reusable sections within them. When the same section appears in more
than one template, it must resolve to one catalogue section, not be
recreated per template.

## 5. Builder responsibility

```
Select Template
      |
Select Required Complete Sections
      |
Reuse Canonical Implementations
      |
Apply Application Configuration
      |
Add / Remove Approved UI Surface Elements
      |
Connect Application-Specific Data
      |
Run Qualification Tests
```

The Builder must not write a new implementation of an existing catalogue
section during an application build.

## 6. Consistency rule

Same catalogue section => same implementation and behaviour, every time
it's used. An application may expose or hide functionality through
configuration, but must not silently receive a newly invented version of
an existing section.

## 7. Reverse-engineering requirement

Three additional complex reference applications are to be
reverse-engineered specifically to discover complete reusable sections
missing from the current five-template catalogue. The objective is
complete, reusable, testable application sections — not isolated
functions.

**Status: blocked.** No source, export, or documented behaviour for any
such reference application exists anywhere in this repository or this
session's environment as of this writing. Nothing will be fabricated
under this requirement. This step starts only once the three reference
applications are actually supplied (a repo to attach, or files to
upload).

## 8. Source and provenance

Where reference source is legally reusable, its licence is respected and
recorded. Where it isn't, the section is implemented independently from
the application's observable behaviour and documented requirements. The
catalogue records the resulting implementation and its provenance either
way.

## 9. Qualification

A section is not canonical merely because source exists for it. It must
be proven against a real implementation (per this project's existing
evidence discipline — real system, real data, `prove()`, captured
output) before Builder may select it. Unproven sections stay
unregistered.

## Core principle

Build the section once. Prove it once. Catalogue it once. Reuse it
everywhere. Application variation comes from selecting, configuring, and
controlling the exposed UI of sections — not from rebuilding
functionality the catalogue already has.
