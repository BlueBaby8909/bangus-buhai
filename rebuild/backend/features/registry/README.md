# Registry and device setup v1

T11 supplies the backend APIs and simulated-device verification. The current
ESP32 implementation is now in T13A; real hardware verification is pending. The static frontend does not implement this flow yet.
Requirements: R09/R16/R17. See [T11 evidence](../../../../docs/status/tasks/T11.md)
and [decision 0008](../../../../docs/decisions/0008-self-service-device-claiming.md).

## Prepare a device once

Run from `rebuild` using a public certificate and a new private output path:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.features.registry.owner --device-id BB-001122334455 --certificate 'C:\private\device-cert.pem' --output 'C:\private\device-claim.json'
```

Replace the example identity/paths with your own. This is an explicit development/
application database write, not a test command. Do not run it to manufacture sample
records in the normal database. T11 itself prepared no real device or claim code.

The certificate must be a single public PEM certificate, valid now, non-CA, with
clientAuth usage, exactly matching CN and a 2048/3072/4096-bit RSA public key.
Preparation pins that public certificate, its SHA-256 DER fingerprint and the
SHA-256 SubjectPublicKeyInfo fingerprint. Duplicate IDs, certificates or shared
device keys are rejected. This is trusted inventory approval, not an arbitrary
self-signed certificate enrollment endpoint or a broker registration command.

The tool creates a random 32-byte claim code, stores only its SHA-256 hash and
writes `{schema_version: 1, device_id, claim_code}` as private QR-payload JSON.
It does not render a QR image; a later interface can render the payload locally.
Keep it outside the checkout, private and backed up. No code/private key is
printed or logged. The output must not exist; existing files are never replaced.
An operation failure removes only the new file it created. Preserve the payload
with deployment records; losing it is not a reason to reset the database.

For an existing T09/T10 device, explicitly add `--existing-device LOCAL-DEVICE-UUID`.
The public ID must match that exact row. Its hatchery/history stay unchanged;
no claim code is issued and the exported claim_code is null. Verification remains
pending until that device proves its pinned key. Existing identities cannot be
implicitly adopted or moved to a different hatchery.

No device key is read/generated, no firmware is built/flashed, and no broker
configuration changes. Credential rotation/revocation and lost-label operational
recovery require a separately reviewed procedure; preparation never silently
replaces registered credentials or resets ownership.

## Operator API

Base: `/api/v1/hatcheries/{hatchery_id}`. All routes require an active T10 operator
session and current membership. Mutations require an allowed Origin and the
session's X-CSRF-Token. All API responses use no-store. Hatchery access denial is
403; foreign/unknown resources inside an accessible hatchery return 404.

| Path | Method / body |
|---|---|
| `/tanks` | GET list; POST `{name}` |
| `/tanks/{tank_id}` | GET detail; PATCH `{name, expected_version}` |
| `/tanks/{tank_id}/archive`, `/restore` | POST `{expected_version}` |
| `/devices` | GET list |
| `/devices/{device_id}` | GET detail; PATCH `{display_name, expected_version}`; display_name may be null |
| `/devices/{device_id}/archive`, `/restore` | POST `{expected_version}` |
| `/devices/{device_id}/assignment` | POST `{tank_id, expected_version}`; tank_id null explicitly unassigns |
| `/devices/{device_id}/bindings` | GET retained history |
| `/device-claims` | POST `{device_id, tank_id, claim_code}` |
| `/device-claims/{claim_id}` | GET state |
| `/device-claims/{claim_id}/cancel` | POST with no body, only while pending_proof |

Devices use canonical BB- plus twelve uppercase hex characters; tank/claim IDs
are UUIDs. Bodies reject unknown fields. Names are trimmed, nonempty, at most 200
characters; display names may be cleared with null. Duplicate tank labels remain
allowed; UUIDs establish identity. List responses are `{items, next_cursor}`.
`limit` defaults to 50 and is bounded 1..200; `cursor` is an opaque keyset cursor
ordered by creation time/UUID (start time/UUID for bindings). Resource lists hide
archived rows unless `include_archived=true`; detail/history retain access.

Versions begin at 1. Stale mutations return 409; refetch the resource before
retrying. Reassigning to the same tank or unassigning an already unbound device
is a no-op when the expected version matches. Repeating an already satisfied
archive/restore is similarly a no-op. Archival requires no active bindings,
preserves ownership/history and does not revoke broker credentials. Restoration
does not restore an old assignment. Unverified legacy devices may be explicitly
unassigned for retirement but cannot receive a new assignment until verified.

Claim reservations last ten minutes. A matching retry by the original operator
for the same hatchery/tank/device returns the same pending reservation. Other
pending claimants receive 409. Wrong/consumed codes return generic claim_unavailable.
Expired/cancelled reservations create no ownership; expiry is materialized on
inspection or the next valid claim start. Audit records retain these transitions.

## Device protocol: separate authentication

Machine endpoints are `/api/device/v1/challenges` and `/api/device/v1/proofs`.
They do not use operator cookies, Supabase tokens, browser Origin or CSRF tokens.
HTTPS is required; only explicit loopback development mode permits HTTP. They
share the lazy backend engine/lifecycle; missing deployment configuration fails
closed. Ordinary device proof processing does not contact Supabase.

POST challenges:

```json
{"device_id":"BB-001122334455","purpose":"sync"}
```

For `confirm`, also supply `configuration_revision` and `configuration_digest`
matching the current desired document. Omit those fields for sync. The response
contains `challenge_id`, `payload`, `signing_input` and algorithm RSA-PSS-SHA256.
Challenges expire at the two-minute boundary, using server time.

The payload contains challenge_id, device_id, purpose, a random nonce, expires_at,
claim_id (nullable), configuration_revision (nullable) and configuration_digest
(nullable). The exact signed bytes are:

```text
ASCII("BB-SETUP-V1\n") + canonical_json(payload)
```

Canonical JSON uses lexically sorted keys, separators `,` and `:`, ASCII escaping
and no whitespace, as implemented in security.py. `signing_input` is the unpadded
base64url encoding of those exact bytes. The future firmware must authenticate
the backend's HTTPS connection, validate the domain/device/purpose and sign the
decoded bytes, without translating timestamps, dropping nulls or reformatting.
Use RSA-PSS, SHA-256, MGF1-SHA-256 and a 32-byte salt. Post an unpadded base64url
signature with the challenge_id:

```json
{"challenge_id":"SERVER-ISSUED-UUID","signature":"BASE64URL-SIGNATURE"}
```

The backend verifies against its pinned public certificate, not a certificate or
hatchery supplied in this request. A successful proof consumes the challenge
atomically; replay returns 409. Invalid/expired proof returns 401. Request a new
challenge if a response is lost; do not replay an old proof.

Sync proof with no ownership or associated pending claim returns `unclaimed`
and no configuration. A challenge issued before a later claim cannot prove that
later claim. A valid pending claim rechecks active identity/membership and tank
eligibility, then creates ownership/binding, consumes the label code and returns
`awaiting_confirmation`. Cancellation/expiry cannot undo established ownership.
Subsequent valid sync proofs retrieve the same desired configuration after lost
responses or restart. Explicitly attached legacy identities are verified by sync.

The configuration response contains `document`, `digest`, confirmed_revision,
confirmed_at and status pending/confirmed. Document fields are schema_version=1,
device_id, hatchery_id, nullable tank_id/binding_id, archived and revision.
Digest is lowercase SHA-256 of canonical_json(document). Assignment/archive/
restore changes advance its revision; display-name edits do not. Initial
confirmed_revision is 0. Future firmware must persist the document atomically,
then request/sign a confirm challenge for its revision/digest. Old revisions
return 409; confirmation advances only the current configuration and completes
any awaiting-confirmation claim. A confirmation assertion is simulated in T11;
it is not evidence of actual NVS persistence yet.

Registry binding timestamps are logical server-side assignment times. Device
application/acknowledgement is recorded separately. T13 must define admission
for buffered old-binding events during configuration transitions; never rewrite
their original binding, identity, capture time or payload to fit a new tank.

T13 now retains each confirmed document/digest/credential fingerprint in immutable
device_configuration_receipts inside the same proof transaction. This changes no
HTTP/signing bytes or firmware obligations. Migration backfills only supported
currently confirmed documents; older missing confirmations are not reconstructed.
The [ingestion guide](../../mqtt/README.md) defines active/closed capture windows,
commit-before-ACK and quarantine. Live ESP32 NVS/binding proof remains unverified.

## Bounds, audit and checks

JSON mutation requests are bounded to 16 KiB (login retains 8 KiB). Shared durable
throttling permits ten claim starts per operator/IP per fixed minute, and ten
setup requests (challenge plus proof combined) per device/IP per minute. Separate
key namespaces preserve login limits; addresses are keyed hashes and forwarded
addresses remain untrusted. Retry-After is 1..60 seconds. Production proxy trust,
fleet capacity and retention/cleanup scheduling remain deployment work.

The audit table is append-only at the database boundary and contains only action,
actor, resource references, safe details and server timestamps. No passwords,
claim codes, signatures or private keys enter the audit. Use 409 for lifecycle/
version conflicts, 422 for invalid typed requests, 429 for throttling and 503 for
temporary infrastructure failures. Certificate/key/ownership fields are never
editable through resource HTTP bodies.

From `rebuild`:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -t . -v
.\check.cmd
```

Tests use generated in-memory device keys, mocked Supabase and only random
t11_test schemas in bangus_buhai_rebuild_test. No real device is prepared or
claimed. Hosted CI and real firmware/client onboarding require separate evidence.

## T13A real-device follow-up

See the [device guide](../../../firmware/components/device_setup/README.md) and
[T13A handoff](../../../../docs/status/tasks/T13A.md). The opt-in lab HTTPS
listener exposes only the existing device routes at port 8443. Normal API/health
remain on 8001. Trusted `backend.features.registry.live prepare` creates only
explicit named development test resources; `live claim` prompts for credentials,
starts a normal protected operator claim and logs out without printing secrets.
No passwords/device private keys enter inventory. Hardware and actual HiveMQ
qualification are separate from the T11 simulated proofs.
