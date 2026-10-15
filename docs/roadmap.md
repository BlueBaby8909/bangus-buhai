# Rebuild roadmap

Updated: 2026-10-16. The owner chose a restart rather than a repair campaign; see [decision 0002](decisions/0002-rebuild-direction.md). This is a proposed sequence supporting the [PRD](PRD.md), not an approved replacement architecture or authorization to implement features.

## Current position

The Obsidian-ready Markdown workspace and shared AI routing are configured. [Baseline reconciliation](../workflows/rebuild/01-baseline/output/2026-10-16-production-software-baseline.md) is in progress: the first production-software release boundary is accepted in [PRD section 1](PRD.md#first-production-software-release), while remaining baseline decisions, replacement design, and reuse choices are pending. Continue with [stage 01](../workflows/rebuild/01-baseline/CONTEXT.md); no stage is complete simply because its folder exists.

Independent [software readiness/design planning](../workflows/rebuild/02-design/output/2026-10-16-production-software-design.md) has started. Unknown farm size/connectivity is not a blocker for software foundations: qualify against a declared test profile and preserve site assumptions as unknown. Domain/model claims still require their own evidence before acceptance.

| Order | Milestone | Exit evidence |
|---|---|---|
| 1 | Reconcile product baseline and core changes | Existing PRD IDs reviewed; proposed revisions separated from retained requirements; unresolved domain, hardware, timing/model, and security decisions identified; accepted changes recorded in the PRD with rationale. |
| 2 | Design replacement architecture and transition | Accepted component boundaries and shared contracts; data/state ownership and failure behavior; source-backed retain/replace/retire inventory; implementation location and coexistence/data-transition plan; meaningful verification criteria. |
| 3 | Build bounded end-to-end slices | Each authorized slice links accepted baseline/design and PRD IDs, preserves unrelated work/data, and includes appropriate verification. Choose concrete slice order after design, rather than inheriting the old repair list. |
| 4 | Verify slices and milestone readiness | Acceptance criteria mapped to evidence; hardware/model/runtime limits explicit; defects returned to the appropriate stage; reviewed status and runbooks updated. |

Repeat build/verify for each slice. Changes to requirements or interfaces return to baseline/design as needed. Production security, recovery, and data preservation constraints inform design from the beginning; their delivery milestones must be settled during baseline/design.

## Reference material

- [Existing implementation assessment](status/implementation.md): dated source findings, not replacement progress.
- [Existing architecture](reference/architecture.md): source map, not an adopted new design.
- [Open questions](research/open-questions.md): unresolved assumptions requiring evidence.
- [Superseded repair roadmap](history/2026-10-15-repair-roadmap.md): useful dependency/risk analysis; superseded work order.
- [Rebuild workflow](../workflows/rebuild/CONTEXT.md): stage contracts and handoff routing.

This documentation setup preserves requirements; it does not silently choose a replacement stack, discard the existing project, or certify a prototype or production release.
