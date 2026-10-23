# 0007: Owner-provisioned operators and managed authentication

Date: 2026-10-21. Status: accepted by the owner's explicit T10 implementation
request. Requirements: [PRD R16-R17](../PRD.md). Evidence belongs to the
[T10 record](../status/tasks/T10.md); accepted design is not a completion claim.

## Decision

Use a dedicated Supabase Auth project for email/password authentication. Keep
the application database in the existing rebuild PostgreSQL instance. Disable
public signup and anonymous sign-in. Create provider users through the trusted
Supabase console; a local owner command explicitly links their issuer/subject
UUIDs to application identities and hatchery memberships. Valid provider
credentials alone never create application access. No public provisioning route
or Supabase service-role key is needed by the backend.

There is one application role: **operator**. Operators have equal access within
their active hatchery memberships. Owner provisioning is an operational action,
not an application admin role. This explicitly replaces the former
admin/operator/viewer requirement and supersedes only that role vocabulary in
decision 0006; hatchery ownership and binding/history rules remain unchanged.
Migration `0002_t10` converts all existing membership labels to operator while
preserving user/hatchery associations. Existing unmapped identities remain
inactive until explicitly linked. Downgrade restores the old allowed vocabulary
but cannot infer historical role labels that were deliberately converted.

The backend verifies issuer, audience, subject, expiry, provider session UUID and
the configured asymmetric signing algorithm through public JWKS. The selected
project uses ES256 and 900-second provider access tokens. Email and Supabase's
database-role claim never determine application permissions.

Browser sessions use random opaque cookies, with only their hashes stored in
PostgreSQL. Provider access/refresh tokens are encrypted server-side using a
private deployment key. Sessions last at most eight hours and expire after
30 minutes without an authenticated application request. Refresh is serialized
per session using a database row lock and cannot independently extend deadlines.
Local logout/disable persists before best-effort provider sign-out, so provider
outages cannot restore local access. Active membership is checked on every
authenticated operation, including after restart.

Use explicit allowed origins, credential-aware CORS, Origin and CSRF checks for
browser mutations, no-store authentication responses, shared PostgreSQL login
throttling and bounded provider requests. Production cookies require HTTPS,
HttpOnly, SameSite=Lax and the __Host- prefix. Explicit development mode permits
only loopback HTTP. Forwarded client addresses are untrusted in the supplied
launcher; production proxy trust requires explicit T24 configuration.

## Consequences and boundaries

- Login, current-user and logout APIs plus reusable operator/hatchery
  dependencies arrive in T10. T11 supplies actual protected management routes.
- The browser does not call Supabase directly or receive provider tokens.
  Frontend login/activation/recovery screens remain T16. Provider email delivery
  must be configured and verified before operator rollout.
- Startup does not migrate, seed accounts or create hatcheries. The owner tool
  can explicitly create the initial hatchery. Provisioning commands accept no
  role selection; a link command can explicitly reactivate an account.
- Preserve `0001_t09`, data and private configuration. Add versioned migration
  `0002_t10`; do not import prototype credentials or database contents.
- Ordinary tests use generated signing keys, mocked provider responses and
  disposable PostgreSQL schemas. A separate live-provider login/me/logout/cookie
  replay check is required for T10 completion; hosted CI evidence stays separate.
- Production deployment, device enrollment, MQTT admission and a full account
  recovery rollout are later tasks. T07 gaps and deferred BOOT-button Wi-Fi work
  remain unchanged. No Git publication or production deployment is authorized.
