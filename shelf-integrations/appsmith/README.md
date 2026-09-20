# Appsmith: genuinely blocked

Real source cloned (`github.com/appsmithorg/appsmith`, commit `983129b`).
Not a duplicate of anything already on the shelf.

## Why this is a hard blocker, not a workaround target

Appsmith's backend (`app/server`, Spring Boot/WebFlux) persists its entire
config store -- apps, pages, datasources, users, workspaces -- through
Spring Data's **reactive MongoDB repositories**. This isn't a connection
string that could point somewhere else instead:

```
appsmith-server/src/main/java/com/appsmith/server/repositories/BaseRepository.java
appsmith-server/src/main/java/com/appsmith/server/repositories/BaseRepositoryImpl.java   (ReactiveMongoRepository)
appsmith-server/src/main/java/com/appsmith/server/configurations/MongoConfig.java
appsmith-server/src/main/java/com/appsmith/server/configurations/mongo/SoftDeleteMongoRepositoryFactory.java
appsmith-server/src/main/java/com/appsmith/server/configurations/mongo/SoftDeleteMongoRepositoryFactoryBean.java
appsmith-server/src/main/java/com/appsmith/server/configurations/mongo/SoftDeleteMongoQueryLookupStrategy.java
```

23 references across 7 files to `ReactiveMongoRepository`/`@Document`, plus
a custom soft-delete repository factory built specifically against Mongo's
query-derivation machinery. `application-ce.properties` wires
`spring.data.mongodb.*` directly (`appsmith.db.url` falls back to
`APPSMITH_MONGODB_URI`). There is no Postgres/MySQL fallback anywhere in
the CE codebase -- unlike DocuSeal, which genuinely could run on Postgres
once its SQLite-only schema bug was worked around.

## MongoDB is unreachable here, checked three ways

- `apt-cache policy mongodb mongodb-org` -- no candidate for either
  package; Ubuntu's own archive doesn't carry MongoDB (Mongo's own
  licensing keeps it out of Debian/Ubuntu main).
- `repo.mongodb.org` (the official apt repo add-on) -- connection returns
  `000`, unreachable through this sandbox's egress proxy.
- `fastdl.mongodb.org` (generic binary tarball, no package manager
  involved at all) -- explicitly `connect_rejected` by the egress proxy's
  organization policy, the same class of block seen on Docker Hub.

No apt package, no official repo, no generic download -- every path to a
real MongoDB instance is closed in this sandbox. Java 25 (required by
`app/server/pom.xml`) and Maven are both actually available here
(`openjdk-25-jdk` candidate `25.0.4+7-1~24.04`, Maven 3.9.11), so the
backend's own toolchain isn't the blocker; the datastore is.

## What was and wasn't tried

Not attempted: standing up a fake/mock Mongo-wire-protocol shim
(`python3-mongomock` etc.) in front of the real reactive-repository layer.
That would mean fabricating a fake datastore behind a real app just to
claim "it boots" -- the same category of shortcut ruled out for
Flagsmith's private dependency. Appsmith is marked blocked instead of
faked.

## Status

`"real_integration": {"status": "blocked", "reason": "Core config store is Spring Data reactive MongoDB (ReactiveMongoRepository/@Document across 7 files, custom soft-delete repository factory); no Postgres/MySQL fallback in CE. MongoDB itself is unreachable in this sandbox: no apt package, repo.mongodb.org unreachable, fastdl.mongodb.org tarball blocked by egress policy."}`
