# Real-device setup (T13A)

The normal firmware now uses backend-issued assignments. Sensing/LCD/demo relay
remain local. Unclaimed/unassigned/archived/pending configurations pause new
telemetry capture, not the replay of existing queue entries. A saved confirmed
assignment remains usable for offline capture after restart. Old events never
acquire a new binding or capture time.

## Local setup already prepared

Current checkpoint (2026-10-22): T13A A/B/C passed, including actual custody release
followed by a normal ACK. Owner restored normal firmware with the diagnostic option
OFF; saved revision 1 confirmed=1 and queue-to-zero observed. Do not rerun claiming
or the diagnostic exercise for ordinary operation. Commands below are setup/test
reference; see the T13A handoff for dated evidence and currently running services.
The owner approved MQTT password mode on Starter; see the [MQTT cutover guide](../../../backend/mqtt/README.md#t13a-starter-password-mode-cutover).
Keep the existing setup key and saved NVS/queue intact. Lab MQTT credentials are
private build inputs outside Git, separate from Wi-Fi and operator credentials.
The older A/B commands below are reference, not instructions to repeat completed work.

For the coordinated C cutover, build from rebuild/firmware in the IDF shell:

```powershell
idf.py -DBB_MQTT_AUTH_MODE=password build
```

Only after the broker's separate credentials/roles are configured, exit any monitor
and run `idf.py -p COM11 app-flash monitor`. Do not erase flash or change the
partition table. Expected connection log: `MQTT connected to HiveMQ using device login`.
Retained configuration should still restore at revision 1, confirmed=1. The AI
will then qualify the broker and start the single guarded ingestion worker.
Actual stored/duplicate/custody queue removal still needs owner monitor evidence.

### Final C custody exercise (explicit lab build only)

Normal delivery and queue-to-zero have passed on hardware. Current real queue
no longer contains rejected fixture events. To verify actual custody removal:

```powershell
idf.py -DBB_MQTT_AUTH_MODE=password -DBB_T13A_CUSTODY_EXERCISE=ON build
idf.py -p COM11 app-flash monitor
```

The exercise is OFF by default. The opted-in image attempts one diagnostic per
boot only after confirmed assignment, response subscriptions and an empty queue.
It creates a fresh reading with an unknown binding (explicitly logged DIAGNOSTIC,
never normal tank history), then captures a normal follow-up with the saved binding.
Original queued events and NVS configuration are unchanged. Expect a durable
quarantine receipt to remove the diagnostic, then an ordinary application ACK for
the follow-up. No queue erasure or artificial backend history insertion.

After the owner supplies evidence, restore normal firmware:

```powershell
idf.py -DBB_MQTT_AUTH_MODE=password -DBB_T13A_CUSTODY_EXERCISE=OFF build
idf.py -p COM11 app-flash monitor
```

Do not leave the diagnostic image as the normal firmware: ON repeats the explicit
exercise after another boot. Broker subscriptions/settings/partitions stay unchanged.

- Existing XIAO ESP32-S3, COM11, 8 MiB, IDF 6.0.2, unloaded relay and wiring unchanged.
- Device: BB-14C19FC68C60, existing RSA 2048 certificate/key retained.
- Private directory: `C:\Users\Kent Christian\BangusBuhai-Secrets\t13a`.
- Device HTTPS URL currently `https://172.20.10.3:8443`; verify the PC still has
  this Wi-Fi address before the normal firmware test. It is compiled from the
  private device_setup_material.h; only the public CA is embedded alongside it.
- Local server certificate expires after seven days, its CA after thirty.
  New material requires an explicit new directory; generation refuses overwrite.
  This local address/certificate is not production configuration.
- The private claim JSON and dedicated backend MQTT certificate/key are there.
  Upload only mqtt-backend-cert.pem to HiveMQ. Never upload a private key.

## Checkpoint A: firmware regression app

In an ESP-IDF terminal:

```powershell
cd 'C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\firmware\tests'
idf.py -p COM11 app-flash monitor
```

Use **app-flash**, which writes only the application at 0x10000. Do not use the
test project's full flash command or erase flash. Its table is not the normal
firmware table. The test image header now correctly declares 8 MiB; signing
tests use a 12 KiB main stack. Expect **26 Tests 0 Failures 0 Ignored**, OK.
NVS is simulated by wrappers; tests never erase real credentials/config/queue.
Send the summary and any failed case, panic or stack message. The test app has
no normal network/sensing loop. Restore normal firmware for checkpoint B.

## Checkpoint B: claiming and restart

Before normal app flashing, check the selected LAN address, local listener
reachability and any client isolation/firewall limitation. The software preflight
validated real local TLS and route isolation; ESP32-to-PC reachability needs
device evidence. Do not silently switch to HTTP or disable verification.

From rebuild, separate terminals run the normal API and device listener:

```powershell
.\backend\run.cmd
.\backend\.venv\Scripts\python.exe -m backend.features.registry.lab serve --host 172.20.10.3
```

Restore normal firmware from rebuild/firmware:

```powershell
idf.py -p COM11 app-flash monitor
```

In another rebuild terminal start the claim with a hidden password prompt:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.features.registry.live claim --hatchery deeee68d-a62b-4fdf-9174-c038133efe70 --tank 05e3e04b-96dd-4c93-b9a1-8c5ec907f207
```

The trusted prepare command already created only the named T13A test resources
for the owner's supplied Supabase UID. It registered public inventory and wrote
the private claim file; it did not create ownership or an initial binding.
Claiming uses the authenticated operator API, CSRF and existing membership.
The helper logs out immediately after starting the claim and never prints codes.

Device polls every 30 seconds. Look for `Configuration saved and confirmed`.
Power-cycle without flashing; then look for `Saved configuration restored` with
confirmed=1. No repeated QR/claim is needed. On lost responses a new signed sync
retrieves the server state. On a changed configuration, persist/read back before
confirming; a failure leaves capture paused and existing queue content intact.

## Checkpoint C: HiveMQ and real delivery

Configure only the rebuild topic prefix. Give the **new backend certificate**
read telemetry/command-results and write acks/quarantine-receipts. Devices may
publish their own telemetry/status (command results remain future firmware),
subscribe to their own acks/quarantine-receipts, and publish neither response.
Authorize certificate identity rather than an arbitrary MQTT client-ID string.
Keep the existing retained status/LWT behavior; do not change plans/subscriptions.
Record actual role configuration, positive delivery and denied response/foreign
topic permissions separately from the disposable Mosquitto tests. Do not revive
the old T07 outage/revocation checklist.

The MQTT worker stays disabled until checkpoint B and the new broker-role gate
have evidence. Then record both qualification flags and use backend.mqtt on the
isolated development database. Never use the ESP32 key for the backend.

Verify real telemetry creates one event/history row before stored ACK removal;
pause the worker and restart it to exercise retained delivery. To test lost ACK,
run `.\backend\.venv\Scripts\python.exe -m backend.mqtt.verify_live` instead of the normal worker.
It withholds exactly the first stored ACK after commit; the retry must receive duplicate.
The normal qualification gates still apply, and only one worker may run.
Old fixture-binding readings should enter quarantine and receive custody receipts;
subsequent correctly bound readings must reach normal tank history. If no such
pending event exists, report that condition and use an isolated simulator for
the negative candidate instead of inventing or relabelling a real sensor event.
Actual device quarantine-receipt evidence remains required before T13A closure.

## Storage, transport and safety

Configuration is one versioned, CRC-protected bb_setup/active blob in the existing
NVS partition. Save closes/reopens and reads back; no automatic erasure. A failed
or ambiguous save disables new captures until recovery verifies a coherent record.
Lower revisions, same-version digest changes and hatchery changes are rejected.
Setup uses a dedicated low-priority task with five-second HTTP timeouts, a 4 KiB
response bound, disabled redirects and 30..300-second retry delay/Retry-After.
No HTTPS work or signing runs in the MQTT callback or sensing task.

QuarantineReceipt uses schema_version/device_id/boot_id/seq/event_kind=telemetry,
quarantine_id/reason/payload_sha256. Hash the exact MQTT bytes, not canonicalized
JSON. Only an exact current queue-head match can release its slot. Receipt
delivery is QoS 1, non-retained. Lost delivery/manifest commit recovers by retry;
the backend deduplicates custody records. Quarantined content stays outside tank
history and is inspectable through backend.mqtt.inspect. Capacity/error cases
still retain device responsibility; the original newest-16 overflow policy stays.

T07 skipped checks, BOOT switching, T14 commands, T18 screens and production
deployment/OTA/credential lifecycle are not implemented by this slice.
