# Bangus Buhai workspace

Task router for humans and AI tools. Start with [AGENTS.md](AGENTS.md); product requirements live only in [the PRD](docs/PRD.md).

## Active direction

**T01-T06 are complete within their recorded limits.** The [T06 record](docs/status/tasks/T06.md) owns the final eight-test PASS, owner normal build/flash and LCD/relay operation confirmation. Turbidity calibration is deferred at owner request; pH remains a default internally. Physical manual/stale-fault transitions, queue scheduling and connected-equipment operation are not verified. Next proposed task is T07: secure/recoverable connectivity, beginning with a plan and broker/provisioning context. No T07 implementation, device/cloud commands or Git mutation is authorized automatically. Source/notes remain uncommitted; preserve prototype, data, local configuration and unrelated work. The T04 baseline was deleted at owner request; historical results remain in its task record. [Rebuild status](docs/status/rebuild.md) owns task states. Follow [owner-led development](docs/decisions/0004-owner-led-development.md).

## Parallel frontend collaboration

2026-10-21 publication: frontend implementation committed as `9d49b57` and successfully pushed to `origin/kyle` at the owner's request. The [frontend handoff](docs/status/tasks/frontend-T16-T18-preparation.md#github-publication--2026-10-21) records the result; backend integration and production acceptance remain unfinished.

2026-10-21 implementation: owner authorized frontend consolidation and integration/deployment preparation while a teammate builds the backend. Active screens now use standard source folders; production excludes fixtures. Shared components, manual entry UI, guarded HTTP requests, retries and release configuration checks are implemented. Backend/auth/live integration and browser/deployment acceptance remain unfinished. See the [current frontend handoff](docs/status/tasks/frontend-T16-T18-preparation.md#component-consolidation-and-backenddeployment-preparation--2026-10-21). No backend/firmware/Git publication changes.

2026-10-21: read-only source review at `c5e2486` confirmed sample mode and identified Dashboard availability/connectivity/provenance and tank-detail request-lifecycle issues. Findings and the next guided step are in the [frontend handoff](docs/status/tasks/frontend-T16-T18-preparation.md#read-only-review--2026-10-21); no application edits or runtime checks were performed.

2026-10-20: frontend collaboration now restores the original Dashboard/Tanks/Alerts/Data navigation and feature screens in `rebuild/frontend/`, with approved original UI libraries and labelled sample history/forecast/export/tank-dialog/relay-preview flows. Latest preparation adds a replaceable data-provider boundary and integration guide. Product wording now uses neutral headings/actions; the offline indicator and pH provenance remain, with developer scenario controls hidden on normal routes. Live integration remains pending. The [separate frontend handoff](docs/status/tasks/frontend-T16-T18-preparation.md) owns checks, limitations and the next integration step. T16–T18 remain incomplete. Firmware T07 remains the active session below; its handoff/status is preserved.

## Where to go

Current session: [T07](docs/status/tasks/T07.md). Delegated BLE/trial-save/USB batch built/flashed by owner; service PROV_C68C60 advertises Security 2 and bb> prompt appears, with 63% app space free. Sensors currently disconnected by owner. Next owner reopens setup if needed and performs first phone provisioning, then reboot/persistence and failure checks. Actual phone authentication/IP trial/rollback remain unverified; MQTT and other checks pending. No AI flash, cloud changes or Git mutations.

| Task | Read next | Scope |
|---|---|---|
| Open this workspace in Obsidian or another AI tool | [Workspace guide](docs/operations/ai-workspace.md) | Setup and usage |
| Understand product goals | [PRD](docs/PRD.md) | Product vision, relevant requirement IDs, acceptance criteria |
| Start or resume the rebuild | [Rebuild router](workflows/rebuild/CONTEXT.md) | Pick the relevant stage and explicit work ID |
| Continue a numbered task in a new chat | [Rebuild status](docs/status/rebuild.md), [session guide](docs/operations/ai-workspace.md#one-task-per-chat) | Current task, exact handoff, actual tests and Git state |
| Review the replacement design | [Architecture proposal](docs/research/rebuild-architecture.md), [contract proposal](docs/research/device-and-api-contracts.md) | Proposed firmware/backend/UI boundaries and interfaces |
| Understand the existing implementation | [Architecture](docs/reference/architecture.md), [assessment](docs/status/implementation.md) | Relevant subsystem only; dated baseline evidence |
| Find unresolved assumptions | [Open questions](docs/research/open-questions.md) | Relevant question IDs |
| Find planned milestones | [Roadmap](docs/roadmap.md) | Proposed rebuild order |
| Run the existing prototype | [Development guide](docs/operations/development.md) | Current application only; startup has side effects |
| Browse supporting knowledge | [Knowledge index](docs/README.md) | Decisions, notes, research, experiments, history |

## Session handoff

When work progresses, keep the active-direction paragraph above short and point to the current task record/status. Do not copy their findings here. Use the evidence, handoff, and authority rules in the [workspace guide](docs/operations/ai-workspace.md).




