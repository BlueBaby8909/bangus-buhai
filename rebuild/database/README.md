# Rebuild PostgreSQL foundation

T09 supplies ownership, assignment history and event-identity storage. T10 adds
operator identity mapping, membership status, browser sessions and login buckets;
see the [backend authentication guide](../backend/README.md). Device enrollment,
MQTT admission and ACK publication remain later tasks. The unchanged backend
`/health` remains database-free liveness only.

## Local setup (Windows CMD)

Start Docker Desktop first. From this checkout's `rebuild` directory:

```cmd
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
backend\.venv\Scripts\python.exe -m backend.database.local up
backend\.venv\Scripts\python.exe -m backend.database.migrate
backend\.venv\Scripts\python.exe -m unittest backend.tests.test_database_config backend.tests.test_database -v
```

The `up` command generates a private random password in `rebuild/database/.env`
only if that file does not already exist, then runs the anchored Compose project
`bangusbuhai-t09`. No activation, manual SQL installation or cloud account is
needed. Configuration is never printed. Existing local configuration is retained.
The example `.env.example` is documentation, not a working credential file.

The dedicated PostgreSQL 18 server binds only `127.0.0.1:55432`. The named Compose
volume persists data at `/var/lib/postgresql` (the PostgreSQL 18 image layout).
First initialization creates `bangus_buhai_rebuild` and
`bangus_buhai_rebuild_test`. Init SQL runs only on a new volume: it never resets
an existing database. A port conflict is an error; leave unrelated services alone.
If an existing volume lacks the test database, create that database explicitly
after checking its identity; never delete the volume to repeat initialization.

```cmd
backend\.venv\Scripts\python.exe -m backend.database.local status
backend\.venv\Scripts\python.exe -m backend.database.local stop
```

`stop` retains the volume. There is deliberately no reset or volume-deletion
command. Do not run Compose `down -v` on databases containing useful data.
Preserve the private `.env` with its matching data volume; changing its password
does not change credentials already initialized in PostgreSQL.

## Connection and migration interfaces

`BB_DATABASE_URL` and `BB_TEST_DATABASE_URL` use `postgresql+psycopg://` URLs.
Process environment values take precedence over the one anchored rebuild `.env`.
No prototype `.env`, SQLite file or default database is read. URL-encode special
characters when configuring custom credentials. Inject deployed secrets through
the environment; do not commit them.

Run `python -m backend.database.migrate` explicitly from `rebuild` to upgrade to
head. The same migrations work with a compatible deployed PostgreSQL host; T24
selects and configures production hosting, TLS, least-privilege database accounts
and monitoring. The Compose account is a local development bootstrap identity.
T26 owns full backup/restore and application rollback rehearsals.

`backend.database.config.make_engine()` creates a lazy pooled engine (five pooled
connections, five overflow, ten-second pool timeout, five-second connect timeout,
pre-ping and hidden SQL parameters). `transaction(engine)` yields one SQLModel
session and commits or rolls back its operation. Create/dispose engines at each
future process lifecycle boundary; never share a Session across concurrent tasks.
Importing the app or database package does not connect, create tables or migrate.

The original `0001_t09` and `0002_t10` are unchanged; current head is `0003_t11`. Future changes add revisions using Alembic,
review generated SQL and verify upgrade against metadata. To generate a revision
programmatically, use `backend.database.migrate.configuration()` with
`alembic.command.revision(..., autogenerate=True)` and the configured rebuild URL.
Never replace existing revisions or use startup `create_all` to upgrade a DB.

## Schema and persistence rules

T11 extends the schema to **14 application tables**, plus Alembic's revision
ledger. Tanks/devices add archival timestamps and resource versions; devices add
an optional display name. Five tables add device_inventory (trusted public
credentials and hashed claim codes), device_claims (operator reservations and
ownership progress), device_challenges (expiring single-use proof requests),
device_configurations (desired revisions/digests and separate confirmation) and
registry_audit (append-only safe actor/action history). No startup seed/import.
The [registry guide](../backend/features/registry/README.md) documents preparation,
legacy verification, API behavior and the future firmware boundary.

- Hatcheries own tanks and devices. Memberships now have one allowed role,
  `operator`, plus an active flag. Migration 0002_t10 converts former admin/viewer
  labels to operator without changing user/hatchery associations. Identities
  retain their internal UUIDs and add a unique nullable Supabase issuer/subject
  mapping, display email and active status. Existing unmapped identities are
  inactive until explicitly provisioned. API access requires active identity
  and membership; foreign keys do not provide API authorization or row security.
- `auth_sessions` stores a session-token hash, local user/provider-session IDs,
  encrypted provider tokens, creation/activity/absolute-expiry/revocation times.
  It stores no password or plaintext browser token. `auth_login_buckets` stores
  keyed client-address hashes, minute windows and bounded attempt counts shared
  across backend processes. Encryption settings live separately in backend/.env.
- Canonical external `BB-` plus twelve uppercase hex device IDs are unique and
  distinct from internal UUIDs. Triggers prevent rewriting resource identity,
  hatchery ownership or external device ID; tank names remain editable. Ownership
  transfer is not implemented in this slice. MAC-derived IDs are not proof of possession.
- Bindings have UUIDs, device/tank/hatchery identity and UTC start/end timestamps.
  Composite foreign keys prevent cross-hatchery associations. A partial unique
  index permits only one open binding per device; multiple devices can share a
  tank. Close the old binding and insert a new one in a transaction. A trigger
  permits closing a binding once, forbids changing its identity/start or reopening
  it, and retains binding history. T11 defines protected enrollment/reassignment
  operations; this foundation does not implement ownership transfers or enforce
  non-overlap between already closed historical intervals.
- Device events have a unique `(internal device UUID, boot UUID, sequence)`
  across telemetry and command results, with uint32 sequence bounds. Their binding
  fixes original tank/hatchery attribution. Payload JSONB preserves validated
  values, provenance, ages, diagnostics and original timestamp text; it does not
  preserve JSON whitespace/key ordering. Indexed capture time is nullable and
  separate from timezone-aware receipt time. A trigger rejects event updates and
  deletes. Referenced resources use restrictive foreign keys, never cascades.
- `persist_event(session, validated_event)` returns `stored` or `duplicate`, or
  raises `ContractError('event_conflict')` for changed content/kind under the same
  identity. It revalidates T02 models and resolves the supplied binding against the
  registered device; it never creates/claims/reassigns a resource. PostgreSQL
  conflict handling makes competing inserts safe under READ COMMITTED isolation.
  Caller owns the transaction: a returned `stored` is not a commit or ACK.
  T13 must first authenticate the publisher and enforce capture-window admission,
  including late/unsynchronized events for closed bindings. This low-level helper
  intentionally permits comparing historical retries after reassignment.

Do not seed the firmware fixture binding or accept its test identity as enrollment.
T12 adds query/manual-entry/correction behavior; no speculative forecasts, commands,
alerts or outbox/jobs tables are introduced in T09.

## Verification boundaries

Database tests require the exact database name `bangus_buhai_rebuild_test` and
PostgreSQL 18+. Each test creates a random `t09_test_...` schema with its own
migrations, sets its connection search path there, and drops only that generated
schema. No existing schema, dev database or data is reset. Missing configuration
or an unreachable server fails the suite; these cases are never skipped as PASS.
Downgrade and injected migration-failure tests run only inside those disposable
schemas. Normal migration commands only upgrade.

`rebuild/check.cmd` retains its original checks and adds offline database-config
tests. Real database checks run separately in the commands above and in
`.github/workflows/rebuild-database.yml` using a disposable PostgreSQL service.
Hosted CI success must be observed after publication; adding the workflow alone
is not a passing CI result. See the [T09 record](../../docs/status/tasks/T09.md)
for actual local evidence and current limitations.

## T12 history extension

T12 migration **0004_t12** retains 0001–0003 unchanged.
T12 adds manual_readings, manual_reading_revisions, reading_history_state and
reading_changes, bringing the application schema to 18 tables. Existing telemetry
is indexed by reference; payloads, timestamps and ownership stay unchanged.
Triggers index new telemetry and manual revisions atomically, excluding command
results and identical event retries. Manual history is append-only. There is no
startup migration or seeding. See the
[readings API/storage guide](../backend/features/readings/README.md).

Run the full PostgreSQL/account/registry/readings regressions from rebuild:

```powershell
backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -t . -v
```

Each suite owns disposable schemas in bangus_buhai_rebuild_test; T12 uses
t12_test_ prefixes. Never reset the development database to run migration tests.
The explicit development upgrade, unchanged prior rows/private settings and local
106-test pass are recorded in [T12](../../docs/status/tasks/T12.md); hosted CI is
separate and remains unobserved without publication.

## Current T13 ingestion extension

The current explicit head is **0005_t13**, with **20 application tables**.
It adds device_configuration_receipts (retained proved documents/digests/public
credential fingerprints) and ingestion_quarantine (deduplicated immutable uncertain
event candidates). Supported currently confirmed configurations are backfilled;
earlier missing proof is never inferred. Existing tables, records, identities,
bindings, payloads and timestamps are preserved; no accounts or samples seed.

Registry confirmation records evidence transactionally. The separate ingestion
worker defaults disabled and never runs from API startup. Accepted telemetry uses
the existing event/history transaction; only successful commits can produce
application ACKs. See the [MQTT worker guide](../backend/mqtt/README.md) and
[T13 evidence](../../docs/status/tasks/T13.md). Live ESP32/HiveMQ remains a separate
gate despite the local 158-test and isolated mTLS broker pass.

The same complete backend command above now requires Docker for a pinned,
generated-certificate, loopback test broker. T13 owns only random t13_test schemas
in the dedicated test database and bb-t13-test containers. These fixtures do not
replace HiveMQ or touch the persistent PostgreSQL service/volume. Missing Docker
fails the broker checks; it is not a silently skipped pass.
