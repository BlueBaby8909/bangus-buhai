# Production-software rebuild baseline

- Work ID: `2026-10-16-production-software`
- Date: 2026-10-16
- State: in-progress; first-release direction accepted, remaining baseline decisions pending
- PRD IDs: R01-R22
- Reviewed revision: `785e08b41a53f837a84d6c86ac2490a772d0329b` plus uncommitted cleanup, documentation migration, and rebuild-workspace changes. This artifact reviews documentation/owner scope, not a fresh code/runtime/hardware audit.
- Inputs: [PRD](../../../../docs/PRD.md), [rebuild direction](../../../../docs/decisions/0002-rebuild-direction.md), [release decision](../../../../docs/decisions/0003-first-production-software-release.md), [existing source assessment](../../../../docs/status/implementation.md), [open questions](../../../../docs/research/open-questions.md), and the owner's explicit answers in this conversation.

## Accepted direction

The PRD's [first-release scope](../../../../docs/PRD.md#first-production-software-release) is authoritative. This output records dispositions and pending work; it does not copy or replace the requirements. The restart targets production software, with current prototype hardware, for real operators at one hatchery/larvae operation. The owner confirmed that growth stage on 2026-10-16; biological limits remain unverified.

## Requirement dispositions

All requirement IDs are retained. The first-release boundary is clarified in PRD section 1; no new requirement IDs or unapproved technology choices are introduced.

| ID | Disposition for baseline/design | Evidence or unresolved input |
|---|---|---|
| R01 | Retain existing hardware baseline | Electrical/wiring/calibration evidence remains Q06. |
| R02 | Retain firmware reliability behavior | Compatibility and failure checks remain unverified. |
| R03 | Retain validity, stale-data, and provenance behavior | Physical pH is outside the first hardware scope; defaults remain explicit. |
| R04 | Retain provisioning/recovery behavior | Production provisioning decisions must also satisfy R17. |
| R05 | Retain selected broker and transport behavior | Verify cloud permissions/certificate capabilities in Q05. |
| R06 | Retain intended telemetry behavior; reconcile time contract | Q01 must settle model-compatible intervals and timestamps. |
| R07 | Retain persistence/provenance requirements | Q07 must settle schema lifecycle/data semantics. |
| R08 | Retain consistent quality reporting | Hatchery/larvae stage selected; Q02 must still validate environmental conditions and numerical policy. |
| R09 | Retain required API capabilities | Replacement API/data contracts belong to design; existing endpoints are not proof of correct behavior. |
| R10 | Retain required operator interface behavior | Do not carry forward inconsistent existing UI assumptions. |
| R11 | Retain actual forecast horizons and input requirements | Q01/Q03 timing, missing data, and validation evidence pending. |
| R12 | Retain persistence, target times, and confidence/provenance | Confidence interpretation and forecast evidence pending. |
| R13 | Retain model-family/provenance requirements | No existing artifact is accepted as production-valid without Q03 evidence. |
| R14 | Retain unloaded demonstration scope in first release | Owner-confirmed hardware decision; verify truthful state and safe failure handling. |
| R15 | Retain end-product requirement; defer connected equipment | Revisit Q04 before a future hardware milestone. |
| R16 | Retain accounts and ownership for real operators | One-farm release does not remove user access boundaries. |
| R17 | Retain security and authorization requirements | Q05 vendor capability, identity/provisioning, and hosting choices pending. |
| R18 | Retain production-software infrastructure requirements | Hosting and practical operating targets still need decisions. |
| R19 | Retain software recovery/update requirements | Q06 hardware/build/rollback evidence remains necessary for corresponding claims. |
| R20 | Retain alerting and recovery requirements | Channels, retention, backup/restore and operational targets need concrete acceptance evidence. |
| R21 | Retain release verification requirements | Isolated test environment and acceptance thresholds need design. |
| R22 | Retain future-expansion boundary | Physical pH and multi-site rollout are outside the first release; no dissolved-oxygen/ammonia expansion selected. |

## Pending decisions and limits

1. Q02: husbandry stage is settled for the first release (hatchery/larvae); establish environmental conditions and evidence-backed biological policy. Retained constants are not validated for larvae by this decision.
2. Q05: tank/operator counts and internet reliability are unknown to the owner; these do not block software design. Establish an explicit engineering test profile and measured limits rather than inventing farm facts. Hosting, operations responsibility, and service/recovery targets remain choices for qualification/deployment. Existing production requirements remain in force.
3. Q01/Q03: obtain training/provenance evidence, settle timing and actual forecast acceptance metrics. Default pH cannot establish physical pH forecast accuracy.
4. Q06/Q07: establish hardware/calibration/build evidence and intended data/capacity semantics. No field safety or stocking recommendation is validated here.
5. Replacement architecture, implementation location, reuse inventory, transition/migration strategy, and first implementation slice are not yet accepted.

## Next action

Proceed with the [proposed software readiness/design plan](../../02-design/output/2026-10-16-production-software-design.md), without further farm-count estimates. Keep domain/model-specific acceptance questions open while developing independent software foundations. Resolve material dependencies before implementing the affected feature, rather than blocking every design task on all unknowns. No application, runtime, database, model, or hardware changes were performed for this artifact.
