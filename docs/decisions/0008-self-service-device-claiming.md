# 0008: Self-service device claiming and retained registry history

Date: 2026-10-21. Status: accepted under the owner's explicit T11 implementation
request. Requirements: [PRD R09/R16/R17](../PRD.md). Owner selected backend-first
verification, self-service device adding and archive/history preservation.

## Decision

Operators claim devices into an active hatchery/tank using a private per-device
claim code plus proof of the device's unique pinned credential. A public BB-ID,
MAC address, BLE advertisement or telemetry field is not ownership proof.
Devices are prepared once before distribution using trusted inventory tooling;
operators do not need owner intervention for each claim. Preparation registers
only public certificate/key fingerprints and a claim-code hash, never private
device keys or operator passwords. Duplicate device keys are rejected.

Claims reserve a device for ten minutes. Backend-issued purpose-bound challenges
expire after two minutes and use single-use RSA-PSS/SHA-256 signatures. Ownership
is committed only after valid proof and a fresh check of operator/membership/tank
eligibility. Confirmation of persisted configuration is separate from ownership;
lost confirmation never releases a hatchery or makes its consumed label reusable.
See the [implemented protocol](../../rebuild/backend/features/registry/README.md)
for exact bytes, endpoint shapes, retry states and limits.

Keep one active binding per device and multiple devices per tank. Reassignment
closes the old binding and creates a new UUID with server time. Serialize
mutations per hatchery, require expected versions and preserve immutable event
attribution. Logical registry assignment and confirmed physical configuration
must be displayed as distinct states. Archive resources instead of deleting them;
explicitly unassign first. Restore does not recreate assignments. Ownership does
not reset through archival, Wi-Fi reset or an untrusted message.

T11 uses the existing stack and a registry feature package. Add migration
0003_t11; preserve 0001/0002 and all populated data. Existing device rows remain
unverified until explicit same-identity inventory attachment and key proof.
No startup migration, automatic seed/import, ownership transfer or broker
credential rotation is introduced. Registry audit records are append-only.

## Delivery and limits

The owner prioritizes minimal setup: reuse a compatible existing Espressif phone
helper for initial secure Wi-Fi provisioning, then provide web-dashboard claiming.
This is a proposed two-stage client experience, not a working single-app flow.
Actual phone binary/Security 2 interoperability must be checked before promising
Android/iPhone support. No custom native app is authorized by this decision.

T11 completes the backend and tests with simulated devices. The current firmware
still uses a configured fixture binding and lacks claim proof/runtime binding
storage/confirmation. A separate firmware onboarding slice must implement and
verify that contract before real T13 admission. The interface remains later
frontend work. T13 must address capture-window admission during configuration
transitions without rewriting old queued readings.

Production HTTPS/reachable device endpoints, broker qualification, credential
rotation/revocation, deployment and fleet qualification remain later gates.
Existing T07 gaps and deferred BOOT-button Wi-Fi switching remain unchanged.
The [T11 record](../status/tasks/T11.md) owns actual verification and Git state;
source, simulated device proof and local checks do not establish live onboarding.
