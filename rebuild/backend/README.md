# Rebuild backend

T16–T18 add optional passive browser authentication (`X-BB-Passive: 1`),
protected [tank summaries/CSV](features/readings/README.md) and latest-current-
binding [command lookup](features/commands/README.md). The
[operator interface](../frontend/README.md) runs on loopback5174 using the existing
cookie APIs. No migration,MQTT,broker or firmware change; database head0006_t14.

T15 adds protected [per-tank reading streams](features/live/README.md), using the
existing T12 journal and snapshot-bound history cursors. `run.cmd` selects pinned
wsproto transport; no database, firmware, broker or worker changes are needed.
Current database head remains `0006_t14`; application startup never migrates/seeds.

FastAPI with SQLModel/SQLAlchemy, Alembic, Psycopg 3 and PostgreSQL. T10 adds
Supabase email/password authentication behind our own browser-session APIs.
The static frontend is not connected to these APIs yet (T16). T11 adds protected
tank/device management and secure self-service claiming; see the
[registry API/protocol guide](features/registry/README.md). These backend APIs
are verified with simulated devices; real ESP32 onboarding remains a follow-up.

T12 adds protected tank reading history, partial manual measurements and retained
correction/void/restoration revisions. See the [readings API guide](features/readings/README.md)
for request examples, provenance and stable snapshot pagination. Device payloads
remain immutable. The latest explicit database revision is 0005_t13; startup does
not migrate or seed. Run all backend regressions from rebuild with
`backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -t . -v`.
Actual local/hosted verification and preserved boundaries are in
[T12](../../docs/status/tasks/T12.md).

T13 adds a separate [MQTT ingestion process](mqtt/README.md), retained configuration
confirmations and bounded uncertain-event quarantine. It defaults to disabled;
API startup/health never start MQTT. Automated tests use generated credentials,
a pinned disposable loopback broker and isolated PostgreSQL schemas. Real firmware
onboarding and HiveMQ backend-role qualification remain pending before live use.
No new browser endpoint or wire schema is introduced. See the
[T13 handoff](../../docs/status/tasks/T13.md) for evidence and limits.

## Organization

```text
backend/
  main.py                       small app entry point and unchanged /health
  core/
    application.py              app composition, lifecycle and request guards
    config.py                   private authentication settings
    security.py                 session hashes and CSRF tokens
  database/
    models.py                   persisted tables, separate from HTTP schemas
    config.py                   pooled engines and per-operation sessions
    events.py                   validated immutable event persistence
    migrate.py                  explicit migration command
    local.py                    isolated Docker setup command
    migrations/
      env.py
      versions/
        0001_t09.py              original database foundation, unchanged
        0002_t10.py              identities, operator memberships and sessions
        0003_t11.py              registry lifecycle, inventory, claims and proof
  features/
    accounts/
      router.py                 login, me, logout and access dependencies
      schemas.py                HTTP request/response models
      service.py                admission, transactions and session lifecycle
      repository.py             account/session/throttling queries
      provider.py               bounded Supabase REST/JWKS adapter
      errors.py                 safe authentication errors
      owner.py                  trusted local provisioning command
      smoke.py                  explicit live-provider verification helper
    registry/
      router.py                 protected management and device setup routes
      schemas.py                typed HTTP interfaces
      service.py                registry/claim/configuration transactions
      repository.py             scoped queries and keyset pagination
      security.py               public certificate and signature verification
      owner.py                  one-time trusted public-credential preparation
      errors.py
      README.md                 exact API/setup/signing contract
  tests/
    auth_support.py             generated signing keys and mock provider
    test_database.py            existing PostgreSQL foundation regressions
    test_database_config.py     isolated setup/configuration tests
    unit/test_auth.py           offline settings, JWT and failure checks
    integration/test_accounts.py
  .env.example                  secret-free authentication example
  requirements.lock.txt
  run.cmd
```

Feature folders grow only when working code needs them. Accounts and registry
now have working code; T12 readings, T13 MQTT and later workers are not speculative
empty packages. The current database head is 0003_t11; run migrations explicitly.

## Local setup

Run commands from `rebuild`, not `backend`. Use the existing isolated `.venv`:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
.\backend\.venv\Scripts\python.exe -m backend.database.local up
.\backend\.venv\Scripts\python.exe -m backend.database.migrate
.\backend\.venv\Scripts\python.exe -m backend.features.accounts.owner init-config
```

The database guide is [here](../database/README.md). `init-config` only creates
an absent `backend/.env`, generates a private Fernet key and never overwrites an
existing file. Fill the project URL and publishable key locally. Keep the
encryption key stable and private; changing it makes existing encrypted sessions
unreadable. Database settings remain separately in `rebuild/database/.env`.
Environment variables override the respective anchored rebuild files; no
prototype configuration is loaded. Neither private file belongs in Git.

In the dedicated Supabase project, disable public signup and anonymous sign-in,
keep email/password enabled, use an active ES256 signing key and configure access
tokens for 900 seconds. For authentication-only usage the Supabase Data API may
stay disabled. Save project credentials privately. The backend requires the
project URL and publishable key, never a Supabase secret/service-role key.

Start the API using `backend\run.cmd`; it remains on `127.0.0.1:8001`. The
development origins in `.env.example` cover `127.0.0.1:5174` and `:8001` exactly.
Use matching hostnames; localhost is a different origin. Explicit development
mode allows loopback HTTP only. Production mode requires HTTPS and a deployment
encryption key shared by all API replicas. Configure production reverse-proxy
trust and HTTPS termination explicitly in T24. The local launcher ignores proxy
headers so clients cannot choose their own throttling address.

`/health` stays database-free liveness. Application startup/import never creates,
migrates or seeds database tables. Missing/invalid auth configuration leaves
protected endpoints unavailable with 503 while health still works.

## Provision accounts explicitly

Create a provider email/password user in Supabase Authentication > Users. For a
dedicated test user, console auto-confirm avoids needing email delivery during
the smoke check. Actual invitations, activation and recovery email must be
configured and verified before operator rollout.

Run the following trusted commands locally, replacing UUID arguments with the
IDs printed by your own previous commands or the Supabase console:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.features.accounts.owner create-hatchery --name "My hatchery"
.\backend\.venv\Scripts\python.exe -m backend.features.accounts.owner link --subject PROVIDER-USER-UUID --hatchery HATCHERY-UUID
.\backend\.venv\Scripts\python.exe -m backend.features.accounts.owner revoke --user LOCAL-USER-UUID --hatchery HATCHERY-UUID
.\backend\.venv\Scripts\python.exe -m backend.features.accounts.owner disable --user LOCAL-USER-UUID
```

`link --identity LOCAL-USER-UUID` explicitly maps an existing unmapped T09 identity
without changing its ID. A mapped principal cannot be reassigned. Linking grants
or reactivates operator membership and explicitly enables the identity; it may
therefore re-enable a disabled account. Revoke removes that hatchery's access.
Disable deactivates the identity and revokes all its application sessions. There
is no role flag or public provisioning endpoint. Console account creation alone
never grants application membership. These commands change the configured
development/application database; do not use them merely to run the smoke test.

## Browser session API

| Endpoint | Request | Response |
|---|---|---|
| POST `/api/v1/auth/login` | JSON email/password and an allowed Origin | Operator context and CSRF token; protected opaque session cookie |
| GET `/api/v1/me` | Session cookie | Identity, role `operator`, permitted hatcheries and CSRF token |
| POST `/api/v1/auth/logout` | Cookie, allowed Origin and X-CSRF-Token | 204, immediate local revocation and cleared cookie |

All authentication responses use `Cache-Control: no-store`. Browsers must send
credentials and use the returned CSRF token on mutations. Do not put passwords
in command arguments, logs or chat. Provider tokens remain encrypted server-side;
only the session-token hash is persisted. Cookie attributes are HttpOnly,
SameSite=Lax, Path=/ and Secure in production, with no Domain attribute.

Sessions expire at eight hours or 30 minutes since the last authenticated
application request. Provider refresh alone does not count as activity. Session
row locks serialize concurrent refresh across backend processes. Active local
identity/membership is checked each time; local logout/disable survives restart
and provider outages. Supabase logout alone is not our local disable operation;
use the owner command for immediate local access revocation. Expired/revoked
sessions cannot regain access; automatic historical session-row retention cleanup
is not implemented in this slice.

`current_operator` and `hatchery_operator` in accounts/router.py are reusable
FastAPI dependencies for T11. Always check hatchery membership before a resource
query; database foreign keys alone do not authorize API access. Never determine
ownership from email, a client-provided role or Supabase's database-role claim.

Safe errors use 401 for invalid authentication, 403 for denied access/origin/CSRF,
429 for shared login throttling, and 503 for unavailable configuration/provider/
database. Throttling allows ten attempts per actual client IP per fixed minute;
Retry-After is bounded to 1..60 seconds. PostgreSQL shares counts across API
processes and stores keyed address hashes, not plaintext client IPs. Request
validation never reflects submitted secrets. Later logging/deployment settings
must preserve this behavior.

## Verification

```powershell
# Offline auth checks; no cloud keys needed
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests/unit -v
# PostgreSQL tests use only fresh schemas in bangus_buhai_rebuild_test
.\backend\.venv\Scripts\python.exe -m unittest backend.tests.test_database_config backend.tests.test_database backend.tests.integration.test_accounts -v
# Existing complete offline/backend/frontend runner
.\check.cmd
```

The PostgreSQL CI job uses generated signing keys, mocked HTTP responses and a
disposable PostgreSQL service. Local pass, actual hosted CI and live-provider
results are recorded separately in [T10](../../docs/status/tasks/T10.md).
Starlette currently emits a TestClient/httpx deprecation warning; the pinned
combination passes checks, and no test failures are suppressed.

After configuring the real project and creating its dedicated test account:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.features.accounts.smoke
```

Enter the email and password at the local prompts; password entry is hidden.
The helper contacts real Supabase Auth, creates and migrates only a random
`t10_live_...` schema in the dedicated local test database, links a temporary
identity/membership there, and checks login, /me, logout and rejection of the old
cookie through in-process HTTP requests. It removes its own temporary schema and
attempts session cleanup on failure. It does not seed the normal application
database or create provider accounts. This is live-provider API evidence, not
a browser/frontend or hosted deployment test. The owner-run live smoke passed
on 2026-10-21; see the T10 record for the reviewed evidence and completion limits.
T07 gaps/deferred BOOT work remain unchanged.

## T14 relay commands

The protected command API and owner exercise are documented in
[commands](features/commands/README.md). Dispatch uses the existing MQTT singleton;
API startup still does not connect to the broker. Migration 0006_t14 is additive.
Hardware acceptance and actual broker qualification are separate checkpoints.
