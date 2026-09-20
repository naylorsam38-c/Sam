# OneDev: genuinely blocked

Real source cloned (`github.com/theonedev/onedev`, commit `aef745b5f`).
Not a duplicate of anything already on the shelf.

## Why this is a hard blocker, not a workaround target

OneDev is a multi-module Maven project. Its root `pom.xml` declares:

```xml
<parent>
  <groupId>io.onedev</groupId>
  <artifactId>parent</artifactId>
  <version>1.4.0</version>
</parent>
```

That parent POM -- required before Maven can even resolve the module
graph, let alone compile anything -- is published **only** on OneDev's own
self-hosted Maven repository, `code.onedev.io` (the same instance the
project dogfoods as its own OneDev-hosted git/CI server; see the repo's
own `readme.md`: "We develop OneDev at code.onedev.io for sake of
dogfooding"). Checked three ways, matching this shelf's standard for
declaring something genuinely unreachable rather than assumed:

- `https://code.onedev.io/onedev/~maven/io/onedev/parent/1.4.0/parent-1.4.0.pom`
  -- blocked by this sandbox's own egress policy (`CONNECT tunnel failed,
  response 403` at the proxy level, confirmed via `curl -v` showing the
  403 coming from the local proxy, not the remote host).
- `https://repo.maven.apache.org/maven2/io/onedev/parent/1.4.0/...` (Maven
  Central) -- genuinely does **not** have it: a real `404 NoSuchKey` from
  Maven Central's own S3-backed storage, not a block.
- The project's only other real distribution channel, the `1dev/server`
  Docker image referenced in its own `docker-compose.library.yml` recipe,
  is unreachable for the same reason every other Docker Hub pull has been
  on this shelf (Flagsmith, DocuSeal, etc. all needed native
  installs instead).

A third possibility -- official prebuilt binaries on GitHub Releases --
was checked directly against GitHub's own servers (not this sandbox's
GitHub-API gateway, which is scoped to attached repos): release-asset
URLs under `github.com/theonedev/onedev/releases/download/v16.6.4/...`
resolve to **real** GitHub responses (confirmed via `Server: github.com`
in the headers, genuinely different from this sandbox's own proxy
refusals), but every filename tried came back a real 404. The project's
own `readme.md` never links a GitHub release binary anywhere -- every
"try it" / "get started" link points at `code.onedev.io` or
`docs.onedev.io`, consistent with a project whose only real distribution
channels are the ones already confirmed blocked.

## What was and wasn't tried

Not attempted: fabricating a local copy of `io.onedev:parent:1.4.0` to
drop into `~/.m2/repository` so Maven would resolve it locally. That POM
defines real shared plugin/dependency version management for the whole
project; inventing its contents would mean guessing at real build
configuration this shelf has no way to verify, the same category of
shortcut ruled out for Flagsmith's private dependency and Appsmith's
MongoDB requirement. OneDev is marked blocked instead of faked.

## Status

`"real_integration": {"status": "blocked", "reason": "Root pom.xml's parent (io.onedev:parent:1.4.0) is published only on the project's own private Maven repo (code.onedev.io), which is unreachable in this sandbox; Maven Central genuinely lacks it (real 404, not a block). The project's other distribution channel, the 1dev/server Docker image, is unreachable for the same reason as every other Docker Hub pull on this shelf. No GitHub release binaries exist as a fallback."}`
