# 0006: Hatchery ownership and database foundation

Date: 2026-10-21. Status: accepted for T09 under the owner's explicit request to
implement the reviewed plan. PRD: R07, R09, R16-R18. This accepts the database
slice, not the entire provisional backend/transport architecture.

T10 update (2026-10-21): [decision 0007](0007-operator-authentication.md) replaces
the original three-role vocabulary with one operator role and records the
provider/session choice. Ownership, bindings and immutable event rules remain.
The account-status descriptions below are historical T09 boundaries.

## Owner decisions

The owner selected hatchery ownership with individual account roles and several
devices per tank. Each tank/device belongs exclusively to one hatchery; the
individual operator is a member, not a competing resource owner. A device has
at most one active tank binding. Resources cannot be claimed/reassigned by
self-reported message fields. Record this interpretation in PRD R16.

The owner requested minimal setup. Use the existing Docker Desktop installation
with a dedicated PostgreSQL 18 container, local port/volume and separate rebuild
development/test databases. Production hosting remains T24. Preserve the
prototype and existing data; no automatic importer, dual write or reset.

## Database decisions

- SQLModel/SQLAlchemy, Alembic and Psycopg 3 extend the existing Python/FastAPI
  backend. Run reviewed, frozen migrations explicitly, never startup `create_all`.
- UUID binding history fixes device/tank/hatchery attribution. Only closing an
  open binding is permitted; identity/start changes, reopening and binding
  deletion are rejected. Composite foreign keys enforce matching ownership.
  Resource IDs/owners and external device IDs cannot be rewritten; names remain editable.
  Closed historical interval overlap and authenticated reassignment workflows
  remain T11 decisions; capture-window admission is T13, not guessed here.
- A single append-only event registry gives telemetry and command results the
  shared `(device, boot_id, seq)` uniqueness domain accepted in decision 0005.
  Preserve validated payload/provenance and nullable capture time independently
  of receipt time. Semantic identical retries are duplicates; changed content or
  kind conflicts. Raw JSON whitespace/key order is not identity.
- The transaction-scoped persistence helper is not an authenticated ingestion
  interface. T13 must verify broker/registry/binding/capture eligibility before
  invoking it and must commit before any application ACK. No fixture binding is
  automatically enrolled. T10/T11 supply authentication and protected management.
- Test only newly generated schemas in the dedicated rebuild test DB. Migration
  downgrade/failure exercises cannot target existing application schemas.

## Evidence and consequences

The [T09 record](../status/tasks/T09.md) owns verification and remaining limits.
Hatchery tenancy establishes ownership integrity without adding multi-site UI or
rollout scope. Accounts remain internal identities until T10 chooses integration.
Referenced history is retained; protected archive/deletion behavior belongs to
later API work. SQL relationship checks alone do not authorize callers or provide
row-level security.

Docker Desktop failed locally during startup. AI verified the foundation using a
new native PostgreSQL 18.6 cluster exclusively in ignored rebuild verification
storage, with fresh credentials/loopback port. This is database behavior evidence,
not a passing Docker setup, production deployment or hosted CI result. No existing
Docker configuration/data was repaired, deleted or reset.

Final checkpoint (2026-10-21): after the owner supplied working Docker engine
output, the supported Compose setup, initial/repeated migration and all 22 tests
passed on Docker PostgreSQL 18.6. T09 is complete within its recorded scope;
production deployment and hosted CI remain separate evidence limits. The initial
Docker failure and native run above are historical context.
