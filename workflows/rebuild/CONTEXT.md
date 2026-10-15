# Rebuild workflow

This is a lightweight adaptation of Interpretable Context Methodology: stage-specific instructions and Markdown handoffs. Follow [workspace conventions](../../docs/operations/ai-workspace.md) and existing authorization; folder numbering does not authorize application changes.

## Stage routing

| Stage | Contract | Completion evidence |
|---|---|---|
| 01 Baseline | [Inputs, process, outputs](01-baseline/CONTEXT.md) | PRD reconciliation proposal, open questions, explicit requirement decisions |
| 02 Design | [Inputs, process, outputs](02-design/CONTEXT.md) | Architecture, shared contracts, retain/replace/retire inventory, verification plan |
| 03 Build | [Inputs, process, outputs](03-build/CONTEXT.md) | An authorized, bounded implementation slice with meaningful checks |
| 04 Verify | [Inputs, process, outputs](04-verify/CONTEXT.md) | Evidence against acceptance criteria, limits, and next action |

## Choosing a stage

Start at 01 while the rebuild baseline is unresolved. For later slices, reuse accepted baseline/design references and enter at the relevant stage. Revisit earlier stages when requirements or interfaces change; do not create a full new document set for a trivial correction.

Read the selected contract and its scoped inputs, rather than every output. Resolve material requirement/design conflicts before dependent implementation. Continue within work the owner has authorized; record pending decisions when that authority is missing.

## Handoffs

Use one work ID, such as `2026-10-16-rebuild-baseline`, across the stage output folders. Each contract names its output suffix. Successor stages read the exact same work ID, never whichever file happens to be newest. Slice outputs must identify accepted baseline/design artifacts when these use different work IDs.

Output folders start empty. No baseline, design, implementation, or verification result is implied by a stage existing. Update the root [workspace status](../../CONTEXT.md) with the active artifact after substantive work.
