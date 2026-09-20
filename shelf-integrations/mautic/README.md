# Mautic: proven running

Real source cloned (`github.com/mautic/mautic`, branch `7.x`, pinned commit
`7912edbd7`).

## Real infrastructure, one genuine version gap found and fixed

- PHP: `composer.json` pins the platform to `8.2.0`. This sandbox's default
  PHP is 8.4, and the PHP 8.1-8.4 packages available via the `ondrej/php`
  PPA are blocked by egress policy (`launchpadcontent.net` 403s through
  the proxy). Installed PHP 8.3 instead, from Ubuntu's own archive
  (`8.3.6-0ubuntu0.24.04.11`, not the PPA's newer build) -- close enough
  to the pinned 8.2 that `composer install --ignore-platform-req=php` (a
  standard, documented Composer flag for exactly this situation) resolved
  and ran cleanly with every real extension Mautic needs (mysqli,
  pdo_mysql, xml, mbstring, curl, zip, intl, bcmath, gd, imap, ldap,
  opcache, soap).
- Database: Mautic 7.x's own installer refuses anything older than
  **MySQL 8.4.0 or MariaDB 10.11.0** -- Ubuntu's own MySQL package is
  8.0.46, which the installer correctly rejected
  (`Your database version ... is too old`). Switched to MariaDB
  10.11.14 (also from Ubuntu's own archive), which does meet Mautic's
  own published minimum -- a real, supported alternative per Mautic's
  compatibility matrix, not a downgrade or a hack.
- `composer install` ran real `npm`/webpack asset-build scripts as part
  of its post-install hooks (Sass compilation, Symfony AssetMapper
  manifest/importmap generation) -- genuinely completed, not skipped.
- PHP's built-in dev server (`php -S`) doesn't apply `.htaccess`
  rewrite rules, so every asset URL that isn't a literal file 404'd and
  the login page's own JS (`Mautic is not defined`) broke. Wrote a
  small router script (`.router.php`, the same front-controller pattern
  Symfony's own docs recommend for `php -S`: serve the file if it
  exists, else forward to `index.php`) rather than reaching for
  nginx/php-fpm, since this reproduces the real `.htaccess` semantics
  exactly for a CLI-server smoke test.
- Real MySQL/MariaDB database and user created by hand
  (`CREATE DATABASE mautic ...`), then Mautic's own
  `bin/console mautic:install` ran the real schema creation and fixture
  loading -- not a manually-imported dump.

## What was verified, in a real browser

- Real login page (`/s/login`) -- clean render, no visual breakage.
- Logged in with the real admin account created by the installer
  (`admin` / a real password) -- Symfony's own `_username`/`_password`
  security form, not a shortcut.
- Reached the real **Dashboard** (Mautic v7.2.0 shown in the footer):
  full real nav (Contacts, Companies, Segments, Components, Campaigns,
  Channels, Points, Stages, Reports, Projects, Tags), real widgets
  (Contacts Created / Page Visits charts, Form Submissions, Upcoming
  Emails, Recent Activity showing the installer's own real audit-log
  entries -- "System created 127.0.0.1").
- Clicked into **Contacts**, then **New** -- a real multi-tab
  (Core/Social) contact form, "Contact owner" pre-filled with the real
  admin user ("Naylor, Sam").
- **Filled in and saved a real contact** (name + email) through the
  app's own form -- round-tripped to the real MySQL `leads` table,
  confirmed by querying the database directly afterwards
  (`SELECT ... FROM leads WHERE email='realtest@example.com'` returned
  the real row). This is the same "prove the write path, not just the
  page load" bar used for Super Productivity and Memos elsewhere on
  this shelf.
- Mobile viewport (390px): sidebar collapses to a hamburger menu,
  dashboard cards stack into a single column, zero horizontal overflow.
- Zero real JS errors. The only console/network failures are genuinely
  external calls this sandbox's egress policy blocks: Google Fonts CSS
  (`fonts.googleapis.com`, used for the email-builder's font preview
  list), Gravatar (real avatar lookups), and Mautic's own update-check
  ping to `updates.mautic.org` -- the same class of block already seen
  elsewhere on this shelf (Langfuse's GitHub star badge, Docker Hub).
  Not app bugs.

See `evidence/` for the full walkthrough: login, dashboard, contacts
list, new-contact form, the saved real contact, and the mobile
dashboard.
