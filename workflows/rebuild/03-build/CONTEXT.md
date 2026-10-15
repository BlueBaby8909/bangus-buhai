# 03 Build

Implement only an authorized slice against accepted requirements and design. Apply [workspace conventions](../../../docs/operations/ai-workspace.md).

## Inputs

| Source | Section/scope | Why |
|---|---|---|
| Design stage output | Explicit `../02-design/output/<design-work-id>-design.md` | Accepted design and slice boundary |
| [PRD](../../../docs/PRD.md) | Relevant requirement IDs | Expected behavior |
| Accepted contracts and decisions | Exact references named by design | Shared interfaces and constraints |
| Relevant source and build configuration | Selected slice only | Implement and verify actual behavior |
| Owner's authorization | Current or earlier applicable instruction | Establish permitted changes |

## Process

1. Confirm the slice is authorized and its material dependencies resolved. A workspace-setup or planning request does not authorize feature implementation.
2. Inspect the working tree and preserve unrelated changes, local configuration, data, and artifacts.
3. Implement the bounded slice; use meaningful tests appropriate to its behavior. Record actual commands and results, including failures.
4. Update affected interfaces and evidence. If requirements or accepted design must change, reconcile them before continuing dependent work.
5. Avoid claiming hardware, deployment, or model accuracy from source/build results alone. Do not flash hardware or migrate live data without applicable authorization.

## Outputs

Write `output/<work-id>-build.md` with common metadata, exact design reference, changed-file references, checks/results, unresolved issues, and handoff to verification. Application changes are outputs only when separately authorized; never mark a slice verified merely because code was written.
