# APP-029: gaseous-server -- INSTALL_FAILED to SCREEN-VERIFIED

Real source cloned (`github.com/gaseous-project/gaseous-server`, pinned
commit `c21363f`). A .NET 10 solution: a ROM/title library manager with a
built-in browser emulator (via EmulatorJS), backed by MariaDB.

## The automated pipeline's finding was stale

The recorded reason was "no Dockerfile or compose file - no documented way
to run it". That's not accurate for this repo: it has a real
`build/Dockerfile` and `docker-compose-build.yml` at its root. It doesn't
matter for this verification either way, though -- this session's own
container cannot pull Docker images at all (confirmed against both Docker
Hub and ghcr.io, both failing identically with 403 Forbidden at the CDN
blob-download stage, the same constraint already documented for other apps
on this shelf). Verified natively instead, following this repo's own
Dockerfile as the reference for what native build/runtime setup is needed.

## Real build chain

- **.NET SDK 10.0.112** installed via Ubuntu's own apt archive
  (`dotnet-sdk-10.0`), matching the Dockerfile's own
  `mcr.microsoft.com/dotnet/sdk:10.0` base image exactly.
- **ffmpeg** via apt (a documented hard requirement).
- **Native MariaDB** (already running on this shelf from earlier work); a
  dedicated `gaseous`/`gaseous` database and user were created, matching
  the compose file's own `MARIADB_USER`/`MARIADB_PASSWORD` values.
- `dotnet restore`/`build` needed an explicit `-r linux-x64` (the project
  declares `<RuntimeIdentifiers>win-x64;linux-x64</RuntimeIdentifiers>`,
  plural, with no default single RID -- without `-r linux-x64` the
  FrameworkReference resolution behaves differently and several ASP.NET
  Core types don't resolve at all).

One real build bug found and fixed (in `gaseous-server/Program.cs`, not
committed here since `source/` is gitignored project-wide -- reproduce by
applying this same change): even with `-r linux-x64` specified, this
apt-packaged SDK's FrameworkReference resolution does not expose
`Microsoft.AspNetCore.Server.IIS`'s reference assembly for compilation,
even though the assembly is physically present in the installed
`Microsoft.AspNetCore.App.Ref` pack on disk
(`/usr/lib/dotnet/packs/Microsoft.AspNetCore.App.Ref/10.0.12/ref/net10.0/Microsoft.AspNetCore.Server.IIS.dll`).
Neither adding an explicit `using Microsoft.AspNetCore.Server.IIS;` nor a
manual `<Reference HintPath="...">` in the `.csproj` fixed it -- the SDK's
own duplicate-reference deduplication appears to silently drop it either
way. Since this app is only ever hosted via Kestrel on Linux (IIS hosting
is Windows-only, and the equivalent Kestrel option
`KestrelServerOptions.Limits.MaxRequestBodySize` is configured immediately
below it in the same file), the four-line
`builder.Services.Configure<IISServerOptions>(...)` block was removed
rather than continuing to fight SDK-packaging-specific reference
resolution for an option with zero effect on this build.

Startup: `dbhost=127.0.0.1 dbuser=gaseous dbpass=gaseous dotnet run
--project gaseous-server/gaseous-server.csproj -c Release -r linux-x64
--no-self-contained`. Real first-run log output: repeated
`Platform Map Id N does not exist` / `Importing <platform> from predefined
data` lines are the app's own real first-boot seeding of its platform
catalog, not errors, despite the `CRIT` log level -- this is the app's own
check-then-import control flow via exceptions, confirmed by the app then
reaching `Startup initialization complete.` and serving real traffic
immediately after.

One optional feature explicitly not exercised, and disclosed rather than
silently skipped: EmulatorJS (the in-browser "Play" feature) is pulled in
as a real git submodule, which clones fine from GitHub, but its actual
emulator core binaries are downloaded separately by
`build/scripts/get-ejs-git.sh` from `cdn.emulatorjs.org`, which this
sandbox's egress policy blocks (confirmed: 403). Core library management,
account creation, and settings are unaffected by this.

## What was verified, in a real browser

- Real landing page ("Gaseous", Get Started / GitHub / Discord).
- Real **administrator account creation** form with live client-side email/
  password validation; created a real account. Found and disclosed a real
  app bug here: the page throws `registerAccount is not defined` right
  after a successful account creation (a genuinely broken/missing JS
  function reference in the app's own code) -- cosmetic in that it didn't
  block the actual signup (the account really was created and the flow
  continued), but a real defect worth reporting upstream.
- Real **first-run setup wizard**: picked "Local Only" for signatures and
  "None" for metadata (no IGDB key available), stepping through with the
  wizard's own real Next/Finish buttons (which are correctly disabled
  until a selection is made -- confirmed by first hitting that disabled
  state, then fixing the interaction to actually check the radio inputs).
- Real **library dashboard**, correctly showing the honest empty state.
- Real **Settings modal** with working tab navigation across ten real
  tabs; the General tab shows a live `Database Size: 5.11 MiB` figure read
  from the real MariaDB database, and the Users tab lists the exact real
  admin account created earlier (round-tripped through the real database --
  the same "prove the write path" bar used for Krayin/Mautic/Ghost
  elsewhere on this shelf).
- Two harmless, disclosed console errors throughout, both from the ASP.NET
  Core dev HTTPS certificate being self-signed (service worker
  registration refuses an untrusted cert even with the browser's
  ignore-HTTPS-errors flag set for normal navigation) -- cosmetic, doesn't
  affect any exercised functionality.

See `evidence/` for the full walkthrough: landing page, account creation
form (filled) and its result, both wizard steps, the library dashboard,
the Settings modal, and the Users tab showing the real created account.
