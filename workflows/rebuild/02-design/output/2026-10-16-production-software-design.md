# Production-software design and readiness plan

- Work ID: `2026-10-16-production-software`
- Date: 2026-10-16
- State: proposed, partial design; no replacement architecture or implementation accepted yet
- PRD IDs: R01-R22, with first-release boundary from PRD section 1
- Reviewed revision: `785e08b41a53f837a84d6c86ac2490a772d0329b` plus uncommitted cleanup/documentation/workspace changes. This is planning based on the dated source assessment, not a new runtime audit.
- Inputs: [baseline artifact](../../01-baseline/output/2026-10-16-production-software-baseline.md), [PRD](../../../../docs/PRD.md), [release decision](../../../../docs/decisions/0003-first-production-software-release.md), [existing assessment](../../../../docs/status/implementation.md), [existing architecture](../../../../docs/reference/architecture.md), [open questions](../../../../docs/research/open-questions.md).

## Planning boundary

Unknown farm counts and internet reliability do not prevent designing or qualifying the software. Use the PRD's [qualification approach](../../../../docs/PRD.md#first-production-software-release). Do not invent a farm size, uptime commitment, acceptable forecast error, or field validation result. This plan maps existing requirements to candidate boundaries and evidence; it does not create a competing product specification.

The baseline remains incomplete for domain/model-specific claims. Independent architecture and test planning can proceed. No application implementation, dependency installation, migration, hardware actuation, or replacement-directory creation is performed here.

## Proposed responsibility boundaries

| Boundary | Responsibility | Design questions to settle |
|---|---|---|
| Device/firmware | Readings, validity/provenance, measurement time, local state and buffering | Versioned payload, clock/sequence rules, replay behavior, fail-safe state ownership |
| MQTT ingestion | Authenticate source, validate schema, persist trustworthy events | Topic permissions, identity binding, duplicate/out-of-order policy, recovery |
| Core API and persistence | Accounts, tank/device ownership, history, configuration, commands | Schema/migrations, authorization on every access path, consistent pagination/order |
| Forecast and quality services | Shared quality policy, time-aware inference and evidence | Verified policy source, input eligibility, validated horizon/metrics, explicit unavailable states |
| Operator UI and live updates | Authorized tank views, truthful state, provenance and actionable alerts | Reconnect/resync behavior; stale/missing/default data; command acceptance versus observed state |
| Operations | Configuration, deployment, health/metrics, backup, recovery and update procedures | Environment isolation, secrets, reproducible artifacts, rollback/restore evidence |

These are conceptual responsibilities, not a decision to build separate microservices. The existing stack is reference evidence; the PRD's selected technologies remain requirements unless explicitly revised. Concrete replacement layout and module contracts are the next design deliverable.

## Proposed readiness evidence

| Area | PRD references | Evidence to prepare and eventually demonstrate |
|---|---|---|
| Identity and access | R16-R17 | Login/session lifecycle, role enforcement, owner scoping, denied cross-owner access including live channels and commands |
| Device trust and transport | R04-R05, R17 | Invalid-source rejection, broker permission checks, encrypted and authenticated ingestion/command paths; no secrets in source/logs |
| Reliable data | R03, R06-R09 | Versioned valid/invalid payload fixtures, timestamps, duplicates/replay, missing/stale/default provenance, persistence constraints and ordered history |
| Device and command behavior | R01-R05, R14, R19 | Restart/outage/recovery scenarios; truthful unloaded-relay state; clear acceptance/observed-state semantics; build versus hardware results distinguished |
| Operator workflows | R08-R10, R14, R20 | Account-to-tank access, fresh/stale/offline displays, reconnect, alert lifecycle, history/manual entry/export and responsive/accessibility verification |
| Forecast eligibility and quality | R06, R11-R13 | Reproducible training/artifact mapping, chronological inputs, actual target times and evaluation; explicit insufficient/unvalidated states |
| Deployment and observation | R17-R19, R21 | Reproducible builds/configuration, isolated environment, useful health/metrics/logging, automated checks and deployment rollback |
| Durable operations | R18-R21 | Migration, backup/restore, restart/outage and notification failure exercises with recorded results and limitations |
| Supported capacity | R18, R21 | Declared hardware/software environment, synthetic device count/event rate, concurrent UI sessions, duration and data volume; measured latency, errors, resource use and recovery |

No row is marked passed. Before execution, assign measurable pass/fail conditions and the environment for each check. Engineering benchmark values will be labeled test conditions, not owner-confirmed farm requirements. A release can claim only demonstrated capabilities within documented limits; site rollout needs its own suitability check.

## Preliminary reuse assessment

Based on the dated assessment, not final module approval:

| Existing material | Candidate disposition | Required evidence |
|---|---|---|
| [Firmware components](../../../../firmware/components/) | Evaluate reusable drivers and provisioning helpers | Clean build, calibration/wiring evidence, lifecycle/state review and fault checks |
| [Backend](../../../../backend/) | Reuse domain knowledge; reassess API, data, ingestion and state boundaries | Known authorization, ingestion, ordering and command-path gaps from the assessment must not be copied unreviewed |
| [Frontend](../../../../frontend/) | Evaluate presentation assets and user-flow ideas | Correct ownership/device identifiers, unified policy/provenance, stale/offline behavior and UI checks |
| [ML code/artifacts](../../../../backend/ml/) | Preserve as evidence; no production approval | Provenance, compatible preprocessing, timestep/horizon evidence and meaningful evaluation |
| Local data/configuration/certificates | Preserve; plan transition separately | Inventory without exposing secrets; reviewed migration and recovery strategy before data changes |

No existing file is approved for deletion or production reuse by this table.

## Proposed delivery order

1. Draft the replacement architecture and shared identity/data/telemetry contracts, plus a qualification plan. Resolve known state/provenance boundaries before selecting implementation modules.
2. Propose the first bounded implementation slice: authenticated access to an owned tank and validated reading history, using isolated fixtures initially. This is a proposal, not authorization or a new feature requirement.
3. Extend to authenticated MQTT ingestion, live views and outage/recovery behavior, then remaining operator workflows and demonstrations under the accepted design.
4. Qualify forecast behavior after its independent domain/model evidence is available. Prepare infrastructure, observability, migration and recovery alongside implementation; verify release readiness against all applicable PRD criteria.

Hosting, exact module layout, shared contract documents, final reuse inventory, implementation location, capacity profile and numerical acceptance targets remain pending. Continue design work without requesting speculative farm numbers; raise product decisions only when a concrete tradeoff requires them.
