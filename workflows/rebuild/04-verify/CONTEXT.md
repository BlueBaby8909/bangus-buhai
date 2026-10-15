# 04 Verify

Assess a specific implementation slice against its acceptance criteria. Apply [workspace conventions](../../../docs/operations/ai-workspace.md).

## Inputs

| Source | Section/scope | Why |
|---|---|---|
| Build stage output | Explicit `../03-build/output/<work-id>-build.md` | Actual changes and checks |
| Design stage output | Exact reference supplied by build | Intended interfaces and verification criteria |
| [PRD](../../../docs/PRD.md) | Relevant requirement IDs | Product acceptance criteria |
| Current diff, tests, fixtures, logs | Changed slice and relevant integrations | Independently assess evidence |

## Process

1. Map each acceptance condition to evidence or a named missing check. Inspect actual changes rather than treating a prior summary as proof.
2. Run appropriate authorized checks in an isolated environment. Avoid redundant reruns when existing evidence still applies.
3. Distinguish source review, build/test, runtime, hardware, and model-evaluation evidence. Record unavailable equipment or environments explicitly.
4. Record pass, fail, or unverified per condition. Return defects to the relevant stage; preserve incomplete status until required work is complete.
5. Promote reviewed findings into the appropriate status/reference/runbook and link the output. Keep existing-code assessments dated and separate from replacement status.

## Outputs

Write `output/<work-id>-verification.md` with common metadata, criterion-to-evidence mapping, actual results, limitations, and next action. Identify the reviewed revision and local-change scope. Set complete only when all applicable acceptance criteria have evidence; never present a source-only review as working hardware.
