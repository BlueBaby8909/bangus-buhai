# 04 Verify

Guide verification of a specific implementation slice against its acceptance criteria. Apply [workspace conventions](../../../docs/operations/ai-workspace.md) and the [owner-led workflow](../../../docs/decisions/0004-owner-led-development.md); read-only review does not authorize running application checks or changing implementation.

## Inputs

| Source | Section/scope | Why |
|---|---|---|
| Build stage output | Explicit `../03-build/output/<work-id>-build.md` | Actual changes and checks |
| Design stage output | Exact reference supplied by build | Intended interfaces and verification criteria |
| [PRD](../../../docs/PRD.md) | Relevant requirement IDs | Product acceptance criteria |
| Current diff, tests, fixtures, logs | Changed slice and relevant integrations | Independently assess evidence |

## Process

1. Map each acceptance condition to evidence or a named missing check. Inspect actual changes rather than treating a prior summary as proof.
2. Explain appropriate isolated checks for the owner to run, then review their results. Execute checks on their behalf only when explicitly asked. Distinguish user-reported, AI-reviewed and AI-run evidence; avoid redundant reruns when existing evidence still applies.
3. Distinguish source review, build/test, runtime, hardware, and model-evaluation evidence. Record unavailable equipment or environments explicitly.
4. Record pass, fail, or unverified per condition. Return defects to the relevant stage; preserve incomplete status until required work is complete.
5. Promote reviewed findings into the appropriate status/reference/runbook and link the output. Keep existing-code assessments dated and separate from replacement status.

## Outputs

For numbered tasks, write criterion-to-evidence results, limits and next action in the single `docs/status/tasks/Txx.md` record using the [session guide](../../../docs/operations/ai-workspace.md#one-task-per-chat). For an additional stage deliverable, use `output/<work-id>-verification.md` and link to the task record for progress. Identify reviewed revision/local changes. Mark complete only when applicable acceptance criteria have evidence; source review does not establish working hardware.
