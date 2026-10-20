# Task handoff template

Copy this structure into `docs/status/tasks/Txx.md` when starting a numbered task. Replace the bracketed instructions; do not count template text as evidence. Use relative Markdown links to real files. The roadmap owns scope, the status page owns task states, and the PRD owns requirements.

## Task and inputs

- Task ID and title: [roadmap entry]
- Updated: [date]
- State: [ready / in progress / waiting / done]
- Working mode: owner implements; AI plans/guides. [Record any explicit, scoped implementation assistance requested in this session.]
- PRD IDs: [relevant IDs and PRD link]
- Inputs: [exact design/task/source references and known limits]
- Baseline: [Git SHA plus existing uncommitted changes relevant to this work]

## Goal and finish conditions

[Link the roadmap scope. Record concrete checks/conditions for this task; keep new product requirements in the PRD, not here.]

## Work completed

[Separate plan/guidance given, owner-completed work, and explicitly delegated AI changes. Link actual source files. Suggested steps are not completed work. State important choices and their accepted/proposed status.]

## Verification

| Check | Command and working directory / method | Actual result | Evidence source and limits |
|---|---|---|---|
| [check] | [command for the owner, or observed method] | [pass / fail / not run] | [user-reported / AI-reviewed output / explicitly authorized AI-run; environment limits] |

## Remaining work and dependencies

[Exact remaining steps, failures, missing evidence or material decisions. Mark the task waiting only when the missing dependency actually prevents its next step. Preserve uncertainty without blocking unrelated tasks.]

## Git checkpoint

- Commit: [actual SHA/message, or explicitly no commit]
- Uncommitted files: [exact task-owned paths and separately identified unrelated changes]
- Push: [actual result if requested/performed, otherwise not performed]

## Resume here

[One exact next guided action for the owner, relevant file/function, command/run directory and expected result. Resume with a short plan recap; do not interpret this handoff as AI execution permission. If complete, name the next task from status. Verify current files before relying on old results.]

Before ending the work, update `docs/status/rebuild.md` and the root `CONTEXT.md` pointer. Stage-specific reports can point to this record; do not maintain conflicting copies of task progress. Stage/commit only task-owned changes when authorized; a Git commit or push must not be invented or bundled with unrelated work.
