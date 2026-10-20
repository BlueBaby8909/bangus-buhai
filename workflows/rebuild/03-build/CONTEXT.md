# 03 Build

Guide the owner through a bounded slice against accepted requirements/design. The owner implements by default; AI implementation requires an explicit request under [decision 0004](../../../docs/decisions/0004-owner-led-development.md). Apply [workspace conventions](../../../docs/operations/ai-workspace.md).

## Inputs

| Source | Section/scope | Why |
|---|---|---|
| Design stage output | Explicit `../02-design/output/<design-work-id>-design.md` | Accepted design and slice boundary |
| [PRD](../../../docs/PRD.md) | Relevant requirement IDs | Expected behavior |
| Accepted contracts and decisions | Exact references named by design | Shared interfaces and constraints |
| Relevant source and build configuration | Selected slice only | Implement and verify actual behavior |
| Owner's authorization | Current or earlier applicable instruction | Establish permitted changes |

## Process

1. Begin with a plain-language plan: goal, scope/exclusions, steps and finish checks. Resolve material slice dependencies. Task requests and plan agreement do not authorize AI implementation.
2. Inspect the working tree and preserve unrelated changes, local configuration, data, and artifacts.
3. Guide the owner one step at a time as they implement and run meaningful checks. Review their code/output and record actual results, including failures. AI edits/executes only the action explicitly requested; label who performed and observed checks.
4. Update affected interfaces and evidence. If requirements or accepted design must change, reconcile them before continuing dependent work.
5. Avoid claiming hardware, deployment, or model accuracy from source/build results alone. Do not flash hardware or migrate live data without applicable authorization.

## Outputs

For numbered tasks, write build evidence in the single `docs/status/tasks/Txx.md` record using the [session guide](../../../docs/operations/ai-workspace.md#one-task-per-chat). Include exact design reference, changed files, checks/results, unresolved issues and the next step. For a separate stage deliverable, use `output/<work-id>-build.md` and link to the task record for progress. Application changes require applicable authorization; code written alone does not establish verification.
