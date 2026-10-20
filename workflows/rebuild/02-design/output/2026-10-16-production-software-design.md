# Production-software design and readiness plan

- Work ID: `2026-10-16-production-software`
- Date: 2026-10-16
- State: proposed design for review; architecture and contract drafts exist, no replacement implementation or design acceptance claimed
- PRD IDs: R01-R22, with first-release boundary from PRD section 1
- Reviewed revision: `8ec01836b84c235d999b04f9bf4c8724bde1444f` plus earlier uncommitted cleanup and this documentation proposal. Includes targeted source inspection, not a runtime/build/hardware audit.
- Inputs: [baseline artifact](../../01-baseline/output/2026-10-16-production-software-baseline.md), [PRD](../../../../docs/PRD.md), [release decision](../../../../docs/decisions/0003-first-production-software-release.md), [existing assessment](../../../../docs/status/implementation.md), [existing architecture](../../../../docs/reference/architecture.md), [open questions](../../../../docs/research/open-questions.md).

## Planning boundary

Unknown farm counts and internet reliability do not prevent designing or qualifying the software. Use the PRD's [qualification approach](../../../../docs/PRD.md#first-production-software-release). Do not invent a farm size, uptime commitment, acceptable forecast error, or field validation result. This plan maps existing requirements to candidate boundaries and evidence; it does not create a competing product specification.

The baseline remains incomplete for domain/model-specific claims. Independent architecture and test planning can proceed. No application implementation, dependency installation, migration, hardware actuation, or replacement-directory creation is performed here.

## Proposed responsibility boundaries

The [replacement architecture proposal](../../../../docs/research/rebuild-architecture.md) now owns the proposed component/task boundaries, process roles, transaction behavior, reuse/transition strategy and diagram. The [shared contract proposal](../../../../docs/research/device-and-api-contracts.md) owns proposed identity, reading/command/acknowledgement semantics and HTTP/live API conventions. Both remain provisional supporting research, not accepted requirements or implemented interfaces.

Firmware is included in production-software scope while the physical prototype hardware remains unchanged. Authentication integration, R16 group-ownership interpretation, executable schema details, queue persistence/loss budget, control arbitration and qualification budgets remain open before their dependent implementation slices. These are engineer-owned design tasks; do not request speculative farm counts to proceed.

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

Architecture, shared contract documents, proposed isolated implementation location and a source-backed candidate reuse inventory are drafted in the linked proposals. They remain unaccepted; executable schemas, concrete module layout/authentication integration, final reuse checks, capacity profile and numerical acceptance targets need further design/qualification. Continue design work without requesting speculative farm numbers; raise product decisions only when a concrete tradeoff requires them. No code, dependencies, hardware, broker/account settings or existing data were changed.
