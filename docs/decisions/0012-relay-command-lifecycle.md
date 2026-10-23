# 0012: Relay command lifecycle

Accepted 2026-10-22 by owner approval of the T14 implementation plan (R14/R17).

- Commit authorized intent with actor, UUID idempotency key and confirmed binding
  before HTTP 202. Conflicting content/target conflicts; one unresolved command/device.
- Retain relay.set ON/OFF; add relay.auto without a Boolean target (explicit null
  accepted as absent). Commands expire in 60 seconds; retries retain ID every 5 seconds.
- Recheck active actor/membership, resources and assignment before publication through
  the existing singleton worker/separate restricted identity. PUBACK is separate evidence.
- Distinguish queued, published, accepted, applied, rejected, failed and timed_out.
  Timeout means unknown; late valid results resolve it while preserving timeout history.
  Reordering cannot regress terminal state; conflicting results quarantine. Results
  never enter reading history. ACK follows successful transaction commit.
- Relay task remains sole GPIO writer, with per-request completion and execution-time
  binding, wall/monotonic expiry and temperature checks. Retain T06 manual/AUTO and
  stale-OFF policy. Expiry limits delivery, not manual-mode duration. GPIO evidence
  does not certify relay contacts or connected equipment.
- Eight CRC/readback ledger entries reserve accepted/terminal results before admission
  in bb_cmd within the existing telemetry partition. Preserve newest-16 readings and
  old format; share boot/sequence allocation. Retry immutable results until application
  ACK. Full/unhealthy storage refuses actuation. Reuse only final/ACKed/expired entries.
- Duplicates resend evidence without reapplication. Reboot fails pending commands;
  interrupted_by_restart admits uncertainty after a crash around actuation/storage.

Use isolated schemas/disposable TLS brokers and separate firmware/owner hardware
checks. Actual HiveMQ permission and unloaded ON/OFF/AUTO/restart/fault evidence is
required. See [T14](../status/tasks/T14.md). T13A remains complete in its original
scope; earlier command denial becomes historical after T14 permission changes.
T07 declined checks/BOOT deferral remain; browser controls stay T18.


T14 closure (2026-10-22): owner explicitly ended the task after the real command
cycle/physical ON/OFF/AUTO observation. Remaining physical reboot/temperature-fault
checks were declined and remain untested. Scoped completion does not waive product
requirements or establish full hardware/failure qualification. Do not resume those
checks automatically; T07/BOOT limits remain unchanged.
