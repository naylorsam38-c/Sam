Indico event-ticketing harvest — evidence bundle
=================================================

Repo:      https://github.com/indico/indico
Commit:    eb90264caec7d1210959c453d1f93ad88a98e6ce (master)
Licence:   MIT
Framework: Flask

Contents
--------
screenshots/   Every screenshot captured while installing, running, and
               driving the real Indico instance (chronological by filename
               timestamp — see the numbered/step_ prefixes).
ticket.pdf     The real PDF ticket Indico generated after registering as
               the VIP tier (EUR 150.00) for event #1, downloaded straight
               from /event/1/registrations/1/ticket.pdf on the running
               instance.

Key screenshots
----------------
01_bootstrap.png                 unauthenticated homepage
02_login.png                     login form
03_authenticated_home.png        logged-in homepage (admin session)
04_admin_panel.png               admin settings panel
step_event_created.png           real event created (PyDayCon 2026)
step_form_created.png            registration form created
step_ticket_tier_prices_open.png "Ticket Tier" field w/ priced options
                                  (Standard EUR 50 / VIP EUR 150)
step_tickets_saved.png           e-ticket module enabled
step_registration_final.png      completed registration + invoice
ticket_rendered.png              the generated ticket, rasterized from
                                  ticket.pdf (QR code + attendee details)

Everything here was captured against a real, locally running instance of
Indico (PostgreSQL 16 + Redis 7 backing it) — no mocks, no synthetic data.
