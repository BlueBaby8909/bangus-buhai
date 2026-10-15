# 02 Design

Design the replacement around accepted requirements and explicit interfaces. Apply [workspace conventions](../../../docs/operations/ai-workspace.md).

## Inputs

| Source | Section/scope | Why |
|---|---|---|
| Baseline stage output | Explicit `../01-baseline/output/<baseline-work-id>-baseline.md` | Accepted scope and unresolved constraints |
| [PRD](../../../docs/PRD.md) | Relevant requirement IDs | Define acceptance conditions |
| [Existing architecture](../../../docs/reference/architecture.md) | Relevant components | Reuse evidence, not a mandatory design |
| [Existing assessment](../../../docs/status/implementation.md) | Relevant findings | Avoid inheriting known faults |
| [Decisions](../../../docs/decisions/) | Applicable accepted decisions | Explain constraints and tradeoffs |

## Process

1. Describe proposed boundaries, data ownership, interfaces, lifecycle/failure behavior, and observability. Identify assumptions requiring hardware or domain evidence.
2. Define shared telemetry/API/data contracts and a verification strategy before dependent components are built.
3. Assess retain, replace, or retire candidates with source evidence. Preserve existing data, secrets, model artifacts, and code until their disposition is authorized.
4. Propose the implementation location, coexistence/data-migration strategy, and smallest end-to-end slice. Do not choose a new stack solely because it already exists or is fashionable.
5. Record accepted replacement design separately from the dated existing architecture; keep proposed design clearly provisional. Resolve material design decisions before dependent implementation.

## Outputs

Write `output/<work-id>-design.md` with design/contract references, reuse inventory, tradeoffs, slice boundaries, and verification criteria. Include common metadata and exact baseline reference. Product requirements remain in the PRD; accepted rationale belongs in decisions. No application changes in this stage.
