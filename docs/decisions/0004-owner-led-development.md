# 0004: Owner-led implementation and planning-first sessions

Date: 2026-10-16. Status: accepted workflow preference, explicitly stated by the owner. This changes how work is performed, not the product requirements in the [PRD](../PRD.md).

## Owner's direction

The owner wants to implement the project themselves. Every new session should begin with a plan explaining the task's goal and scope. The AI should act as a guide and touch implementation only when explicitly asked. The owner deleted the automatically created T01 session; do not recreate it without a new request.

## Working agreement

The AI reads relevant project context, explains a plain-language plan, guides the owner step by step, and reviews their code/results. Read-only inspection supports that role. Task requests, continuation requests and plan agreement do not by themselves authorize implementation or command execution.

Explicit, scoped requests are needed for AI implementation edits, scaffolding, dependency installation, build/test/application execution, hardware/cloud changes and implementation Git operations. Guidance may include suggested commands or small examples for the owner; it must not silently become an end-to-end implementation service.

The previously agreed second-brain maintenance continues. Record decisions and actual progress, separating suggested steps, user-completed work, user-reported evidence and AI-observed verification. A documentation update is not permission to change the application or product scope.

## Consequences

- Shared entry rules are in [AGENTS.md](../../AGENTS.md); the [session guide](../operations/ai-workspace.md#one-task-per-chat) supplies the corrected starting prompt.
- The roadmap and finish conditions stay useful; their verbs describe the work to be done, primarily by the owner, not automatic AI permission.
- [T01](../status/tasks/T01.md) remains ready for a planning/guidance session. A roadmap or plan is not completed implementation evidence.
- The owner creates the next conversation themselves. No replacement session is created by this correction.
