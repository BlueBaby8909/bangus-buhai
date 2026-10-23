# Bangus Buhai workspace

Feature styling follow-up (2026-10-23): claiming, manual readings, history/CSV and
relay controls now follow the original prototype's dialog/form/table styling.
Fixed production CSS layer ordering.14 frontend tests and isolated production
browser checks at360/768/1440 PASS. Owner runs setup/services; none started or
restarted. See [T18](docs/status/tasks/T18.md). Owner visual review pending.

Original frontend baseline restored (2026-10-22), explicitly requested by owner.
Rebuild now reuses the prototype's actual navigation/header/dashboard/Tanks/Alerts
markup and original Tailwind4.3.3 tooling, with completed T16–T18 APIs/features
adapted into that baseline. Earlier visual redesigns are superseded. Keep this
baseline; future work should adapt features,not redesign it. Devices stays inside
Tanks. See T17's baseline-restoration checkpoint. Owner visual review pending;
hardware/Wi-Fi checkpoint and declined tests/BOOT deferral unchanged.

Task router for humans and AI tools. Start with [AGENTS.md](AGENTS.md); product requirements live only in [the PRD](docs/PRD.md).

## Active direction

Runtime refresh (2026-10-22): after owner reported changes not visible, verified
source edits exist but no frontend/API listeners were running. Started only the
missing rebuild Vite5174 (session14326) and API8001 (PID40608/session6040). Frontend,
API health and served prototype/Dashboard.jsx all HTTP200. Older PID/service
notes below are historical; inspect actual processes before starting others.


**Temporary five-second telemetry trial installed (2026-10-22).** Owner requested
faster live readings. Normal app build/app-only COM11 flash PASS; serial capture
cadence5.010seconds observed,diagnostics OFF. Website delivery remains unverified:
device Wi-Fi reports BACKOFF with saved credentials. Owner must make its saved
Wi-Fi/hotspot available; it retries automatically (up to five minutes). No reflash,
new worker,credential replacement or relay actuation needed. See the trial checkpoint
in [T18](docs/status/tasks/T18.md). Normal product target remains300seconds.

**T16–T18 DONE within approved frontend/local scope (2026-10-22).** Rebuilt operator
interface reuses prototype layouts/artwork and adds login, tank/device views,
claiming, manual/history/CSV and honest ON/OFF/AUTO results. All248 backend tests,
13 frontend tests, six integrated browser scenarios and rebuild runner PASS.
See [T16](docs/status/tasks/T16.md), [T17](docs/status/tasks/T17.md),
[T18](docs/status/tasks/T18.md). Device connectivity stays explicitly unknown;
quality/alerts/forecasts remain unavailable as approved. No owner action pending.
Next:T19 policy validation when requested. T07/T14 declines/BOOT deferral stand.

**T15 DONE within approved backend/local scope (2026-10-22).** Protected tank
streams,history cursors,replay and passive access checks implemented. All240 backend
tests and rebuild runner PASS. One API restart/health/transport check PASS; no
migration,firmware,broker or new worker. See [T15](docs/status/tasks/T15.md).
Its frontend consumers are now implemented in T16–T18 above.

**T14 DONE within owner-approved scope (2026-10-22).** Real ON/OFF/AUTO and
API duplicates passed; owner confirmed physical relay ON/OFF and LCD AUTO.
Software/build/broker checks and owner34/34 regression PASS. Normal firmware
restored,diagnostics OFF; qualified singleton retained. Remaining physical
reboot/fault checks are owner-declined and untested. See [T14](docs/status/tasks/T14.md).
T07 declined/untested and BOOT deferral stand. T15 completion is recorded above.

## Where to go

Deferred at owner request: [T07 standalone Wi-Fi switching](docs/status/tasks/T07.md). Proposed XIAO ESP32S3 BOOT/GPIO0 five-second hold, LCD feedback and existing secure BLE/recoverable replacement remain unimplemented; deliberate setup reopening currently requires USB. Do not block backend development or resume this feature automatically. T08/T09 stay complete within their recorded limits.

Current checkpoint: [T18 completion handoff](docs/status/tasks/T18.md).
Frontend http://127.0.0.1:5174/ (PID36628/session91128).
API8001 (PID16808/session31926), ingestion/commands (session22251, qualified/enabled) and
existing device-only HTTPS172.20.10.3:8443 retained. Check current processes before
starting anything else. One diagnostic remains in quarantine. Local processes
stop with the PC/processes; no production deployment or hosted CI claim.

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

Owner subsequently delegated secure-connection implementation and ran its build/flash/device check successfully. Reviewed output confirms positive time/TLS/MQTT login. Status/LWT and retry implementation remain the next batch; negative security cases still pending. See T07.

Current MQTT checkpoint: owner refetch/reconfigure passed; package checksum and expiry/TLS settings verified. Delegated SNTP foundation implemented and syntax-checked; certificate-authenticated connection is next. No full build/flash yet for the new source. See T07.

External Wi-Fi architecture critique reviewed in T07: maintenance concerns valid, but proposed backup-at-CRED_RECV and permanent BLE-memory release do not preserve current requirements. Targeted cleanup recommended; no refactor authorized or implemented.

When work progresses, keep the active-direction paragraph above short and point to the current task record/status. Do not copy their findings here. Use the evidence, handoff, and authority rules in the [workspace guide](docs/operations/ai-workspace.md).




