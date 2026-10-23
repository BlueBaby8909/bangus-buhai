# 0011: Real-device onboarding and quarantine custody

Date: 2026-10-21. Status: accepted by the owner's explicit T13A implementation request.
Requirements: PRD R04-R07/R09/R16-R19/R21. T13A precedes T14.

Implementation evidence updated 2026-10-22: T13A A/B/C and normal-image restoration
PASS on the real ESP32/HiveMQ/local PostgreSQL setup. Ordinary ingestion running,
test worker stopped. See the task handoff for owner logs, local test results and
the deliberate retained diagnostic quarantine candidate. Hosted CI is unobserved;
this does not establish production deployment or later credential lifecycle work.

## Decision

### MQTT authentication adjustment approved 2026-10-21

After viewing the actual single certificate-entry/role UI and discussing the
tradeoff, the owner explicitly requested separate device/backend username/password
authentication over verified TLS on Starter. This supersedes certificate-only
MQTT in T13/T13A, not the HTTPS signed proof protocol. R17 is updated accordingly.
No plan upgrade. HiveMQ documents per-credential roles and one active method:
[official access management](https://docs.hivemq.com/hivemq-cloud/authn-authz.html).
The support chatbot's conflicting multi-certificate instructions are not evidence.

Generate independent 256-bit random passwords outside Git. Scope each device to
its own canonical topics; backend receives only ingestion and ACK/custody publish
permissions. Never use Supabase/operator credentials for MQTT or grant Allow All.
Keep server trust, hostname/date checks, ownership/binding admission, event identity
and commit-before-ACK/custody unchanged. Retain the device key/certificate for
setup proofs and certificate-mode rollback.

Prepare/build/test before switching broker authentication, then owner app-flashes
without erasing NVS/queued readings. Switching may interrupt current clients.
Qualify actual cloud roles and delivery after switching; local tests cannot satisfy
that gate. Passwords are embedded in the local lab firmware, with no new flash/NVS
encryption. Physical secret extraction and deployment credential provisioning/
rotation remain later production work, not solved by this change. Lab preparation
does not establish fleet onboarding or production credential lifecycle readiness.

Implement the ESP32 side of the existing T11 challenge protocol: authenticated
HTTPS, exact BB-SETUP-V1 input, RSA-PSS/SHA-256 with a 32-byte salt, durable
versioned runtime configuration, readback and explicit server confirmation.
New captures use a confirmed runtime binding; fixture binding is no longer used
by the normal firmware. Existing queued events remain immutable.

Use a separate opt-in device-only HTTPS listener on port 8443 for same-Wi-Fi
development. Keep the normal loopback API on 8001. Private local CA/server
material stays outside Git. This is a lab endpoint, not production hosting.
Keep the existing per-device key and prepare a distinct backend MQTT identity.

The owner chose automatic queue progress after durable quarantine custody.
Extend T13's earlier no-application-response quarantine rule with a separate
QuarantineReceipt on /quarantine-receipts. This is not a stored/duplicate ACK
and does not insert the reading into tank history. It identifies the exact
payload bytes, event identity and retained quarantine UUID. Only verified owned
device telemetry with committed quarantine content receives one. No receipt
is sent for invalid/unverified input, failed commit or capacity failure.
Device queue removal must match its pending head and remain power-loss safe.

Broker permissions authenticate both normal ACKs and quarantine receipts: only
the dedicated backend can publish them; devices receive only their own topics.
Receipts do not carry an additional application signature. They share the
existing qualified mTLS broker trust boundary. This requires new-topic broker
qualification, not a claim based on self-reported client IDs.

All prior migrations, payload attribution and history semantics remain intact.
No quarantine release/deletion API or automatic relabelling is introduced.
Later owner-reviewed recovery may inspect quarantined content; this task only
transfers delivery custody and prevents a head from blocking newer readings.

## Owner boundaries and evidence

The owner explicitly declines the remaining T07 checks. Leave them untested and
do not rerun or label them passed. BOOT-button switching stays deferred. New
T13A backend identity/receipt permissions are still required for its live test.

The owner flashes and supplies monitor/power-cycle evidence. AI implements,
builds, runs isolated software tests and maintains the handoff. T13A is not
complete until real claiming/restart and ESP32/HiveMQ delivery pass. Hosted CI
and deployment are separate evidence. Add device screens belong to T18;
credential lifecycle, hosting and release qualification retain later scope.

See [T13A handoff](../status/tasks/T13A.md) and
[setup guide](../../rebuild/firmware/components/device_setup/README.md).
