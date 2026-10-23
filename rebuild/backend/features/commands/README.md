# T14 unloaded-relay commands

Protected endpoints share the existing session, membership, origin and CSRF boundary:

- `POST /api/v1/hatcheries/{hatchery_id}/devices/{device_id}/commands` with a UUID
  `Idempotency-Key`. Body: `{"type":"relay.set","desired_on":true}` (or false),
  or `{"type":"relay.auto"}`. AUTO has no Boolean target.
- `GET .../commands/{command_id}` returns immutable intent, actor/binding, status,
  dispatch attempts/PUBACK evidence, device receipts and retained timeout evidence.

HTTP 202 means committed intent. Device GPIO results do not verify relay contacts
or attached equipment. States are queued, published, accepted, applied, rejected,
failed and timed_out. PUBACK is recorded separately even if a device result wins
the race. Late valid results can resolve timed_out; accepted cannot regress a final
result. Conflicting terminal evidence stays in quarantine. No command results enter
water-reading history. Identical event retries receive duplicate ACK after commit.

Commands expire after 60 seconds. The singleton worker retries unchanged IDs every
five seconds. One unresolved command per device; idempotency is actor/operation
scoped and conflicting content or target returns 409. Current verified assignment,
resource state and active operator access are rechecked before dispatch. Commands
HTTP writes have the existing durable ten-per-minute actor/device throttle.
Expiry limits delivery, not manual-mode duration. Manual ON/OFF remains until
AUTO or reboot; temperature faults cancel remembered ON and force local OFF.

Apply migration 0006_t14 explicitly; no startup migrations or seeds. Dispatch runs
only in test mode or with process setting `BB_MQTT_COMMANDS_QUALIFIED=true`. Leave
the private MQTT .env unchanged; set this flag only for the qualified worker process.
The existing worker owns publication and the database singleton lease. Do not run
a second dispatcher. Command dispatch uses short database deadlines on the network
owner, holds registry locks through publication, and commits attempt intent first.
Device-result persistence remains on the separate processing thread.

## Broker checkpoint (owner dashboard)

Keep existing permissions and credentials. Add only:

| Role | Operation | Topic |
|---|---|---|
| `t13a-backend` | Publish | `bangusbuhai-rebuild/devices/+/cmd` |
| `t07-device` | Subscribe | `bangusbuhai-rebuild/devices/BB-14C19FC68C60/cmd` |

If the device subscription already exists, retain it rather than adding a duplicate.
Do not grant device command publication, foreign-device subscriptions, wildcard
device write access or backend telemetry publication. No credential/authentication
cutover is needed. Before flashing the new normal firmware, run from rebuild:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.mqtt.qualify --commands
```

It uses invalid, non-retained wire markers; it cannot actuate the relay. No database
events are seeded. Successful login alone is insufficient. Requalify a permission
change; do not use old T13A denial-of-backend-command evidence as T14 qualification.

## Owner hardware checkpoints

1. App-only flash/run the firmware regression build: 34 cases expected. NVS and
   GPIO are mocked there; the test binary does not operate real storage or relay.
2. Restore the normal image using `idf.py -DBB_MQTT_AUTH_MODE=password
   -DBB_T13A_CUSTODY_EXERCISE=OFF -p COM11 app-flash monitor`. Never erase NVS or
   change the partition table. Verify saved assignment, three successful MQTT
   subscriptions, ordinary readings/application ACKs and no T13A diagnostic.
3. With qualified dispatch enabled, run each live helper action separately below;
   supply the operator email/password locally. Observe actual unloaded relay and
   LCD mode; keep logs and command IDs. Repeat with the same idempotency key to
   verify no new intent; wire duplicate behavior is also covered by software tests.
4. Power-cycle: startup follows the existing OFF/AUTO policy, and old commands do
   not reapply. Confirm queued result delivery and normal ingestion recover.
5. Power down before changing the temperature-probe connection. With the probe
   unavailable, verify local OFF and rejected manual ON. Reconnect safely and
   verify that manual ON needs a new request. Threshold/calibration claims remain
   outside this unloaded-demo check. Finish in normal firmware, preferably AUTO.

From rebuild, use the retained T13A hatchery:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.features.commands.live on --hatchery deeee68d-a62b-4fdf-9174-c038133efe70
# Repeat with off, then auto; each invocation logs in and logs out.
```

Use `--idempotency-key UUID` to repeat the identical API request, or `status
--command UUID` to query later. A timeout means outcome unknown. Current observed
telemetry is historical evidence, not continuous confirmation of an old command.

## Device storage and replay

The MQTT owner keeps eight command ledger entries in namespace bb_cmd in the
existing telemetry partition. Each reserves accepted and terminal result space
(768 bytes each), retains semantic command digest and expiry, and checks CRC and
readback. It does not alter the telemetry namespace/format/newest-16 retention.
Command results share telemetry's boot/sequence allocator. Only application ACKs
release pending results; PUBACK cannot. Results survive reboot unchanged.

Full/unhealthy storage refuses new actuation. Entries are reusable only after
terminal completion, both results acknowledged, and expiry passed with a usable
clock. Duplicate commands resend their original evidence without queueing relay
work again. Interrupted commands yield failed/interrupted_by_restart, which is
uncertainty about past actuation, not evidence that it never occurred.

### Single-login quick cycle

After normal restoration and dispatcher qualification, replace the three separate
live helper invocations with one:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.features.commands.live exercise --hatchery deeee68d-a62b-4fdf-9174-c038133efe70
```

Watch the unloaded relay/LCD while it runs ON, OFF and AUTO, including automatic
same-key API retries. It logs in/out once and stops on uncertain/failed results.
Physical reboot/fault checks remain separate hardware evidence.
# T18 browser recovery

`GET /api/v1/hatcheries/{hatchery_id}/devices/{device_id}/commands/latest` returns
the latest intent/result view for the device's **current binding**,or null when
unassigned/no command exists. Existing operator authorization applies; another
binding's command never becomes the current control state. Poll with
`X-BB-Passive: 1` to avoid extending inactivity. Device telemetry GPIO is separate
from the last command's observed_on; neither establishes contact feedback.
No new command is created by this lookup. T18 browser tests use simulated results;
they do not reopen declined T14 hardware checks.

