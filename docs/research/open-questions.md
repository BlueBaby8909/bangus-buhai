# Open questions and unverified claims

Recorded: 2026-10-15. These are unresolved inputs to the [PRD](../PRD.md), not accepted requirements or implementation facts. No external scientific, vendor, training-repository, or cloud-account research was performed for this source/documentation migration.

## Q01 Time and forecast contract

PRD R06/R11 preserve intended telemetry and forecast behavior. Source has a short telemetry loop; the previous ML spec prescribed 48 observations at 15-minute intervals; metadata says horizon 12. Establish the actual training timestep, capture clock, missing/duplicate handling, aggregation/resampling, origin/target timestamps, and model output interpretation. Decide whether retraining is needed using training evidence. Do not infer hourly outputs from field names or count alone.

## Q02 Domain policy

Partially resolved, owner-confirmed 2026-10-16: the first deployment targets hatchery/larvae; see [PRD scope](../PRD.md#first-production-software-release) and [decision 0003](../decisions/0003-first-production-software-release.md). Earlier grow-out descriptions do not define this release.

Still unresolved: environmental conditions (including water/salinity conditions and hatchery practices) and scientifically appropriate policy for that setting. Validate the PRD's retained limits against suitable aquaculture sources before accepting them for larvae. No biological thresholds were validated by this scope clarification. Claims of reduced mortality, safe stocking density, and biological suitability are not demonstrated by source code.

## Q03 Model provenance

Obtain the training dataset/notebook, artifact version mapping, feature/scaler provenance, evaluation splits, and training-time dependencies. The previous training prescription was Adam, MSE, batch size 32, early-stopping patience 10; it is retained here as an unverified legacy prescription, not asserted as the actual training recipe. The earlier document named `github.com/apaolol/bangus-ml` as an external training repository; its existence/content/alignment were not checked. Recorded artifact metrics and versions are self-reported metadata. Calibrate or explicitly characterize the confidence indicator. A multi-output model was previously preferred, but selection/retraining feasibility remains unverified.

## Q04 Connected relay equipment

Owner-confirmed: no connected load; the relay is for visual demonstration. Before production control, confirm actuator type, electrical ratings/wiring, thresholds, control direction, manual/automatic ownership, and failure recovery. The legacy string `heater` conflicts with activation at high temperature. Do not connect equipment based only on code labels or historical thresholds.

## Q05 Production security and hosting

Partially resolved, owner-confirmed 2026-10-16: the first release serves real operators at one hatchery, and the [PRD](../PRD.md#first-production-software-release) requires accounts, permissions, and ownership enforcement for that release. Historical disagreement about prototype authentication does not waive that release requirement.

Still unresolved: confirm HiveMQ plan support and configuration for per-device mTLS and topic permissions. Broker account capabilities cannot be inferred from a successful username/password connection.

Choose the backend/static frontend hosting, TLS termination, pooling, backups, monitoring, deployment gates, and secret management. The former claims about Mbed TLS 4.x/PSA Crypto and Picolibc compatibility are not verified by this audit; confirm the actual selected framework/toolchain before relying on them. MAC-derived PoP is an existing prototype mechanism, not proof of a secure production ownership flow.

## Q06 Hardware and build evidence

The documented board/target, GPIO defaults, LCD address, 8 MB configuration, and local IDF lock do not prove actual wiring, electrical voltage limits, flash size, sensor calibration, or clean-build compatibility. Preserve current configuration and known binaries until verified. Validate the turbidity 2.28 voltage multiplier with calibration records. Check BLE provisioning, disconnect/reconnect behavior, watchdogs, stale readings, and future OTA/rollback on hardware. No hardware behavior was verified during migration.

## Q07 Capacity and data semantics

The tank capacity code multiplies volume in mL by 600; its comment describes a reciprocal relationship. Define the quantity, units, formula, and validation source before correcting it or exposing it as a biological recommendation. Define device/tank reassignment, deletion behavior, SQLite constraint enforcement, schema migration, and manual versus device measurement provenance. No live database schema/data audit was performed.
