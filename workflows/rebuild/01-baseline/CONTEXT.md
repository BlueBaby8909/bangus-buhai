# 01 Baseline

Reconcile rebuild intent with existing requirements before selecting the replacement design. Apply [workspace conventions](../../../docs/operations/ai-workspace.md).

## Inputs

| Source | Section/scope | Why |
|---|---|---|
| [PRD](../../../docs/PRD.md) | Vision, requirements, completion rules | Authoritative starting point |
| [Rebuild decision](../../../docs/decisions/0002-rebuild-direction.md) | Full file | Owner-confirmed direction and limits |
| [Open questions](../../../docs/research/open-questions.md) | Relevant question IDs | Preserve unresolved assumptions |
| [Existing assessment](../../../docs/status/implementation.md) | Relevant findings only | Distinguish current code from target |
| Owner's current request | Explicit scope and core changes | Avoid inventing replacement requirements |

## Process

1. Identify which existing PRD IDs remain applicable and which need an explicit proposed revision. No silence counts as acceptance of a change.
2. Separate owner-confirmed constraints, dated source evidence, proposals, and unverified assumptions.
3. Record material open questions and the smallest useful next decisions. Do independent analysis while answers are pending.
4. Preserve the PRD until a requirement change is authorized. Record accepted changes there and their rationale in a decision, linking rather than duplicating requirement text.

## Outputs

Write `output/<work-id>-baseline.md` with requirement-ID dispositions, evidence, pending decisions, and the next action. Include the common metadata from the workspace guide. Mark it proposed or blocked on named decisions until reconciled; do not imply implementation has begun.
