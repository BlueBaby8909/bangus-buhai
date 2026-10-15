# Foundation-first repair roadmap (superseded)

Superseded: 2026-10-16 by the owner's [rebuild direction](../decisions/0002-rebuild-direction.md). Retained as dated dependency/risk analysis, not the active work plan.

Proposed: 2026-10-15. This is a work sequence supporting the [PRD](../PRD.md), not evidence that repairs have been implemented or authorization to implement them in this documentation task. Current findings are in [status](../status/implementation.md). Each future change needs requirement IDs, a focused diff, verification, and an updated status record.

| Order | Work package | PRD references | Exit evidence |
|---|---|---|---|
| 0 | Resolve hardware/control scope and timing contracts; capture reproducible environment/model provenance. Preserve current data/configuration. | R01-R07, R11-R15 | Q01/Q03/Q04/Q06/Q07 decisions recorded; clean baseline/build strategy documented; no guessed calibration or forecast horizon. |
| 1 | Establish reliable local sensor and relay state ownership, validity/staleness propagation, and independent operation during network failure. | R01-R04, R14 | Appropriate host/unit checks and ESP-IDF build; documented hardware tests for failure/stale/manual command sequences and reconnect outages. |
| 2 | Define and enforce telemetry/command contracts, measurement time, sequence/duplicate policy, queue behavior, and authenticated TLS transport. | R05-R07, R14 | Valid/invalid/buffered/duplicate fixtures pass contract checks; capture time survives buffering; TLS command and status paths demonstrated in an isolated setup. |
| 3 | Repair persistence, constraints, associations, capacity semantics, migrations, and stable ordered history. Establish future ownership schema before production access features. | R07, R09, R16 | Isolated database tests for reassignment/deletion/invalid input/history; reviewed migration and recovery path without resetting existing data. |
| 4 | Repair MQTT lifecycle, device-status routing, quality policy consistency, and command/result reporting. | R04-R10, R14 | Reconnect/failure tests, correct tank broadcasts, no silent malformed-data acceptance, backend policy fixtures, explicit command acceptance versus physical execution semantics. |
| 5 | Reconcile model training/inference timing, valid sequences, artifacts, target timestamps, confidence, and actual four-horizon evaluation. | R06, R11-R13 | Reproducible preprocessing and evaluation with training-compatible data/artifacts; time-aware acceptance evidence. Field names alone do not pass. |
| 6 | Repair browser device IDs, status/threshold use, provenance, manual entry, history ordering, socket recovery, and bounded export messaging. | R08-R10, R12, R14 | End-to-end fixtures for real/missing/estimated/offline states; responsive/accessibility checks; no optimistic UI claim of confirmed actuation. |
| 7 | Deliver production ownership/authentication, device claiming/certificates, real control hardware, deployment, recovery, notifications, and OTA. | R15-R21 | Ownership isolation and broker permissions tests; authenticated encrypted connections; calibrated equipment verification; deployment/restore/rollback exercises. |
| Later | Evaluate explicitly deferred expansions through a PRD revision. | R22 | Reviewed requirements and feasibility evidence before implementation. |

Production security, backup, and identity constraints inform stages 0-4 even though their complete delivery is stage 7. New faults may change dependency order; record that decision rather than working around an unresolved foundation. No old checklist item is marked complete merely because source exists.
