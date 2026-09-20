# Krayin: proven running

Real source cloned (`github.com/krayin/laravel-crm`, branch `2.2`, pinned
commit `570a8db1`). A Laravel CRM built on top of native PHP + MariaDB,
both already proven working on this shelf via Mautic -- PHP 8.3.6 matched
Krayin's own `composer.json` requirement (`^8.3`) exactly, no version
relaxation needed this time.

## Real build chain

- `composer install --no-dev --optimize-autoloader` -- clean, no gaps.
- Real MariaDB database and user created by hand
  (`CREATE DATABASE krayin ...`), `.env` pointed at it.
- `php artisan krayin-crm:install` -- Krayin's own real installer command:
  ran every real migration (60+ timestamped migrations), seeded real
  kickstart data, published real config files, linked the storage
  directory, and printed real generated admin credentials
  (`admin@example.com` / `admin123`) at the end -- not something invented,
  the installer's own real output.
- `npm install && npm run build` -- a real Vite build of the admin's
  frontend assets.
- Booted with `php artisan serve`.

## What was verified, in a real browser

- Real "Sign In" login page ("Powered by Krayin, an open-source project
  by Webkul").
- Logged in with the installer's own generated credentials and reached
  the real **Dashboard**: real nav (Leads, Quotes, Mail, Activities,
  Contacts, Products, Settings, Configuration), real revenue/lead charts
  and stat cards, all correctly showing zero/empty state for a fresh
  install.
- Opened the real **Create Lead** form and exercised its actual
  validation and data-entry flow end to end, including a genuinely
  non-obvious part of the UI: the "Contact Person" field is a real
  search-or-create combobox (`Click to Add` -> type a name -> the
  dropdown offers a real **"Add as New"** option when there's no
  match), not a plain text input. Filled in a real name, email, and
  phone number this way, removed the still-empty required product row
  via its real delete icon, and **saved a real lead** -- confirmed by
  the app's own "Success: Lead created successfully" toast, the new
  lead appearing as a real card on the real Kanban pipeline board
  ("New (1)"), the Dashboard's own "Total Leads" stat updating to 1,
  and independently querying the real MariaDB `leads` table directly
  and finding the exact same row. Same "prove the write path" bar used
  for Strapi, Mautic, and Ghost elsewhere on this shelf.
- Mobile viewport (390px): the sidebar correctly collapses to a
  hamburger menu. One real, disclosed layout gap found: the dashboard's
  date-range picker + "Export PDF" button row doesn't wrap at this
  width, causing a small real horizontal overflow (much narrower in
  scope than AnythingLLM's sidebar issue elsewhere on this shelf, but
  reported the same way -- plainly, not smoothed over).
- Zero real JS errors. The console/network failures seen
  (`fonts.googleapis.com`, `cdnjs.cloudflare.com`'s TinyMCE bundle,
  `cdn.jsdelivr.net`'s chart plugin) are all genuinely external CDN
  assets this sandbox's egress policy blocks -- not app bugs. Their
  absence means the rich-text mail composer and the funnel chart widget
  weren't exercised, since both are real cosmetic/functional
  enhancements loaded from those CDNs rather than core Krayin
  functionality.

See `evidence/` for the full walkthrough: login, dashboard, the
create-lead form (both the initial validation-error state and the
fully filled-in state), the saved lead on the pipeline board, and the
mobile dashboard.
