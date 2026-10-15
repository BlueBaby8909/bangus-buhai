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

Open this repository as the tool's workspace. Start with:

> Read AGENTS.md and CONTEXT.md. Use the rebuild baseline stage. Reconcile the existing PRD with the rebuild direction, identify decisions still needed, and write a proposed baseline artifact. Do not change application code or silently revise requirements.

Tools that load AGENTS.md automatically get the shared entry instructions. CLAUDE.md points there too. CONTEXT.md is a routing convention, not a universally auto-loaded filename: explicitly direct other tools to read it. No MCP connection is needed to read local Markdown.

For a later session, name the stage and exact prior artifact/work ID. Ask the assistant to read changed source or requirements again when the evidence may have gone stale. Selective loading is an instruction, not guaranteed context isolation; start a fresh session when old context is confusing the task.

## Authority and promotion

Follow the [knowledge index](../README.md) for evidence and promotion rules. The PRD owns product requirements; source establishes actual implementation. Stage outputs are working artifacts, not additional specifications. Link accepted decisions, architecture/contracts, status, and runbooks from their canonical homes. Keep proposals visibly provisional.

Existing-code reference/status documents remain dated. When replacement design or implementation is accepted, give it a separately labeled document rather than overwriting the old assessment as if it described new code. The [rebuild decision](../decisions/0002-rebuild-direction.md) establishes the current direction and limits.

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
