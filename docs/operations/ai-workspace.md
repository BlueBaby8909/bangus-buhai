# Obsidian and AI workspace

Configured: 2026-10-16. This is a lightweight project adaptation of [Interpretable Context Methodology](https://arxiv.org/html/2603.16021v2), using [stage contracts and canonical-source conventions](https://github.com/RinDig/Interpretable-Context-Methodology/blob/main/_core/CONVENTIONS.md). It is not a memory service or an enforcement system.

## Open in Obsidian

1. Open Obsidian's vault switcher and choose **Open folder as vault**.
2. Select `C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai` (the repository, not its parent or only `docs`).
3. Open [CONTEXT.md](../../CONTEXT.md) using the file explorer or Quick Switcher (`Ctrl+O`). Bookmark it if useful.
4. Follow its links to requirements, knowledge, or the current stage. Edit these existing files in place rather than importing copies.

Obsidian's [vault instructions](https://help.obsidian.md/vault) describe opening an existing folder. Obsidian will create its own local `.obsidian/` settings when the vault is opened; the repository ignores that directory. This setup has not launched or configured the desktop application.

No community plugins are required. Continue using normal Markdown links. If dependencies clutter navigation/search, add `frontend/node_modules`, `backend/venv`, `firmware/build`, and `firmware/managed_components` to the vault's excluded files; do not delete those folders as a navigation fix. Editor settings do not restrict what an AI tool may read.

## Use from an AI tool

Open this repository as the tool's workspace. For normal work, use the starting prompt in [One task per chat](#one-task-per-chat), which reads current status and selects the next numbered task. Request baseline reconciliation explicitly only when requirements/scope need review; do not restart the baseline interview at every new session.

Tools that load AGENTS.md automatically get the shared entry instructions. CLAUDE.md points there too. CONTEXT.md is a routing convention, not a universally auto-loaded filename: explicitly direct other tools to read it. No MCP connection is needed to read local Markdown.

For a later session, name the stage and exact prior artifact/work ID. Ask the assistant to read changed source or requirements again when the evidence may have gone stale. Selective loading is an instruction, not guaranteed context isolation; start a fresh session when old context is confusing the task.

## Authority and promotion

Follow the [knowledge index](../README.md) for evidence and promotion rules. The PRD owns product requirements; source establishes actual implementation. Stage outputs are working artifacts, not additional specifications. Link accepted decisions, architecture/contracts, status, and runbooks from their canonical homes. Keep proposals visibly provisional.

Existing-code reference/status documents remain dated. When replacement design or implementation is accepted, give it a separately labeled document rather than overwriting the old assessment as if it described new code. The [rebuild decision](../decisions/0002-rebuild-direction.md) establishes the current direction and limits.

## One task per chat

The owner implements the project themselves and moves between conversations for each task. Under [decision 0004](../decisions/0004-owner-led-development.md), the AI starts with a simple plan and acts as a guide. Read-only inspection supports planning/review; implementation edits and execution require an explicit, scoped request. The [roadmap](../roadmap.md#task-list) gives tasks stable IDs; [status](../status/rebuild.md) identifies the current task. Its record under `docs/status/tasks/Txx.md` is the cross-chat handoff, not an instruction to execute automatically.

Open the same repository workspace in the new chat. Because the repository is inside the outer BangusBuhai folder, specify the actual repository directory when needed. Use this starting prompt:

> Work in C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai. Read AGENTS.md, CONTEXT.md, docs/status/rebuild.md and the current task record. Start with a simple plan explaining the goal, scope, steps and how we will check the result. I will implement the task myself. Guide me one step at a time and review my work. Read-only inspection is fine. Do not edit implementation files, run setup/build/test commands, or stage/commit/push unless I explicitly ask. Keep our progress notes current and save the exact next guided step for the following session.

To choose a task, name its ID, such as T01. Start by explaining its goal, why it matters, scope/exclusions, small steps and finish checks. The owner then edits/runs the steps; the AI explains/reviews, using small examples when helpful. A task request, "continue", or agreement with a plan is not permission for AI implementation. An explicit request such as "edit this function for me" authorizes only that action. The owner opens their own next session; do not create a session or send instructions to another one unless explicitly asked.

Before leaving a working chat, record guidance given, work actually completed by the owner or explicitly delegated to the AI, reviewed files/results, remaining issues and the next guided step. Label user-reported results versus output the AI actually inspected or checks it was explicitly asked to run. Mark done only when finish conditions have evidence; otherwise leave in progress/waiting with a concrete reason. Keep status/CONTEXT current under the agreed documentation maintenance. Implementation Git actions need an explicit request; record the actual SHA or pending paths without implying a push/backup happened.

For numbered tasks, build/verify sections can live together in the single task record. Stage-specific output files are used when an additional deliverable is useful and should link to the task record for progress rather than duplicate it. Prior baseline/design outputs remain dated context. A new chat must inspect current files/tests, not treat old handoff text as fresh verification. Files remain available in the same local workspace; switching machines requires a saved/transferred repository including the relevant changes.

## Output and handoff convention

- Choose a unique work ID such as `2026-10-16-rebuild-baseline`. Use the suffix specified by each stage contract.
- Give every artifact: work ID, date, state (`proposed`, `accepted`, `in-progress`, `blocked`, or `complete`), relevant PRD IDs, input links, reviewed Git revision plus local-change scope, evidence/limitations, and next action.
- Use Markdown links to exact existing inputs. Keep evidence labels from the knowledge index. A Git SHA alone is insufficient when the working tree contains uncommitted changes.
- A successor stage reads the specified artifact, not the latest filename. For build slices, link the accepted baseline/design even if they have different work IDs.
- Keep useful text outputs under Git; do not add secrets, raw database exports, binaries, or repeated tool dumps. Output folders begin with only `.gitkeep`.
- At handoff, update the active-status paragraph in root CONTEXT.md with a short state and exact artifact link. Promote durable conclusions to canonical docs and retain output provenance without copying requirements.
- Respect the owner's actual authorization. Ask only for material missing decisions/permissions; do not turn every stage boundary into an unnecessary confirmation. A setup request does not authorize a rebuild implementation.

## Optional tools

Graphify can later supply generated code-navigation evidence. It is not required, and no Graphify package, index, or skill is installed by this setup. Generated graphs must be refreshed and checked against source. The unrelated `icm.exe` memory application is not part of this methodology.
