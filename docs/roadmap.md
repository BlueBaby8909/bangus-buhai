# Rebuild roadmap

Updated: 2026-10-22. Product scope comes from the [PRD](PRD.md) and [first-release decision](decisions/0003-first-production-software-release.md). This is the proposed delivery order, not a claim that the replacement design or code is complete.

## Current position

T16–T18 are **complete within owner-approved frontend/local scope** (2026-10-22).
Prototype design/assets reused; working accounts,tank/device views,claiming,
history/manual/CSV and relay interface verified.248 backend tests,13 frontend
tests,six real browser scenarios and runner PASS. Device connectivity is explicitly
unknown; quality/alerts/forecasts remain unavailable under the owner's chosen scope.
See [T16](status/tasks/T16.md),[T17](status/tasks/T17.md),[T18](status/tasks/T18.md).
No owner action pending. Next:T19 policy validation on request; declined hardware
checks and BOOT deferral remain. No production-deployment/capacity claim.

T15 is **complete within approved backend/local scope** (2026-10-22). Protected
streams/history cursors,committed replay and passive authorization verified;
240 backend tests/full runner PASS. One API restart/health/transport check PASS;
data/configuration/migrations preserved. See [T15](status/tasks/T15.md).
Its frontend consumers are complete above. No firmware,broker,migration,new worker
or UI change; T07/T14 declines and BOOT deferral stand.

T14 is **complete within owner-approved scope** (2026-10-22). Real ON/OFF/AUTO,
API duplicates,committed results and physical relay/LCD observation passed.
Software/build/broker checks and owner34/34 regression passed; normal firmware
restored. Owner explicitly ended the task and declined remaining physical reboot/
fault checks: these remain untested. See [T14](status/tasks/T14.md).
T07 deferrals stand. T15 completion is recorded above.

T13A is complete within the approved local/hardware scope (2026-10-22).
Real claiming/save/confirmation/restart, restricted MQTT logins over verified TLS,
commit/ACK/retry and quarantine custody followed by normal delivery passed. Normal
firmware restored with diagnostic exercise OFF. Hosted CI remains unobserved;
production deployment and credential lifecycle remain later tasks. See
[T13A](status/tasks/T13A.md) and decision 0011. Next is T14 planning on request.
T07 remaining checks stay owner-declined/untested; BOOT switching stays deferred.
The earlier T13 completion below remains a historical backend-only checkpoint.

Current T13 checkpoint (2026-10-21): owner explicitly delegated backend-first
ingestion and quarantine. **158 backend tests** and the full rebuild runner PASS,
including real local mTLS/ACL broker integration. Explicit/repeated development
migration 0005_t13: 20 application tables, zero drift/seeds/test schemas or broker
fixtures. Earlier rows/migrations/private settings and firmware preserved.
See [T13](status/tasks/T13.md) and [decision 0010](decisions/0010-mqtt-ingestion-and-quarantine.md).
The backend slice is complete; live ESP32/HiveMQ acceptance remains pending
firmware proof/runtime binding/confirmation and dedicated broker-role qualification.
Next T14 planning at owner request; no inherited firmware/cloud authorization.
Hosted CI remains unobserved. UI/export and quality/forecast tasks stay separate.
T07 gaps and deferred BOOT work remain; older chronology below is historical.

Second-brain setup and the approved cleanup are committed (`8ec0183`, `a8cb626`). T01's isolated workspace, T02's offline contracts and T03's basic check automation are complete within their recorded limits. T03 source/workflow is published as `9b93ff6` on `t03-checks` with successful hosted CI status; its final README usage update and progress notes remain unstaged/uncommitted. The [T03 handoff](status/tasks/T03.md) holds evidence and limits. T04's isolated prototype build passed under explicit AI copy/build delegation; its [task record](status/tasks/T04.md) holds tool/component versions, partition fit, preserved-input hashes and configuration/hardware limits. T05 is complete within the [recorded software limits](status/tasks/T05.md): normal acquisition and the owner-run composite lifecycle test passed (1 test, 0 failures). Physical calibration, fault exercises, wire integration and the flash/OTA configuration mismatch remain explicit later work. T06 now includes relay ownership and LCD integration: after owner confirmation of 3.3 V signals, the explicitly delegated source was simplified to three components with real GPIO/I2C drivers. T06 is complete within its unloaded-demo limits: final eight tests passed, normal build/flash succeeded, and the owner confirmed LCD and relay operation. Calibration and controlled physical fault/manual-transition checks remain explicit limits. T07 planning is next; see [T06](status/tasks/T06.md). No further implementation/build/hardware work or merge is authorized automatically. Documentation and unrelated work remain uncommitted. The owner explicitly requested removal of the untracked T04 baseline specimen on 2026-10-17; its raw artifacts were deleted without archiving, while the T04 task record retains historical results. [Rebuild status](status/rebuild.md) owns task states and the exact next action. [Decision 0005](decisions/0005-device-contracts-v1.md) accepts only the implemented local message subset; the broader [architecture](research/rebuild-architecture.md), API, transport and persistence proposals remain pending scoped review.

We can start independent foundations without knowing farm size. Resolve the choices needed by a task before its dependent code; unresolved biology/model/hardware questions do not block unrelated software work. Under [decision 0004](decisions/0004-owner-led-development.md), the owner implements and the AI plans/guides. Task requests and plan agreement do not authorize AI implementation; that requires an explicit, scoped request.

## Task list

2026-10-21 transition: owner delegated T08 durable newest-16 retention and local ACK tests after T07 implementation/partial verification. T08 is complete within recorded scope: normal build/storage/publication/retry/reboot recovery, 18 Unity cases and three actual C payload contract checks passed; normal firmware restored. Live backend ACKs remain T13 and physical qualification limits remain explicit. T07 acceptance gaps remain documented, with no dependency-completion claim or waived finish criteria. Next is T09 planning when requested, without inherited implementation authorization. See the task records for evidence.

Aim for one numbered task per chat. Begin each session by explaining the goal, scope, steps and finish checks, then guide the owner one step at a time. A task can take more than one chat; finish its scope and checks rather than marking it done because the conversation ended. Split a task further if inspection shows it is too large, recording the change before implementation. Table verbs describe the owner's intended work, not instructions for the AI to implement automatically.

| ID | Task | Start after / condition | Finished when | PRD |
|---|---|---|---|---|
| T01 | Set up the separate rebuild workspace | Owner requests T01; settle only the layout/environment choices it needs | Replacement folders, isolated configuration and reproducible start/build/check commands work; the current prototype is preserved. | R18, R21 |
| T02 | Define and test the shared device messages | T01; resolve the remaining fields/limits in the contract proposal | Executable schemas and shared examples accept valid readings/commands/results and reject malformed, mismatched or conflicting data. | R03, R05-R07, R14, R17 |
| T03 | Automate basic build and test checks | T01-T02 | A fresh checkout can run the documented checks; CI runs useful contract/build checks and records failures. | R18, R21 |
| T04 | Verify the firmware starting point | T01; actual board/wiring/electrical context must be confirmed for hardware work | Toolchain/component versions and build baseline are recorded; hardware checks are distinguished from source/build checks. Unknowns have explicit limits. | R01-R02, R19, R21 |
| T05 | Make firmware readings trustworthy | T02, T04 | Sensor snapshots preserve sample time, validity, age and pH source; failure/stale cases pass appropriate tests. | R01-R03, R06-R07 |
| T06 | Give the relay one state owner and integrate the LCD | T04-T05; settle manual/automatic precedence; confirm relay/LCD wiring and electrical context before hardware-facing changes | Commands and local rules use one control path; startup/stale OFF and truthful unloaded-demo state are verified. LCD displays sensor-service readings and relay demo state, distinguishes missing/invalid/stale and default/unverified values, and reports display failure without stopping sensing. | R01-R03, R14 |
| T07 | Make device connections secure and recoverable | T02, T04; verify broker capability needed for R17 | Provisioning, credentials/TLS, bounded reconnect and disconnected local operation have evidence; cloud settings are not assumed. | R04-R05, R17 |
| T08 | Preserve readings through connection loss | T05, T07; decide/test finite buffer loss and persistence behavior | Capture IDs/times survive retries; queue overflow, acknowledgement loss and reboot behavior are explicit and tested. | R05-R07, R19 |
| T09 | Build the production database foundation | T01-T02; settle ownership and assignment rules | Versioned PostgreSQL migrations enforce identity, relationships and event uniqueness in an isolated database. | R07, R09, R16, R18 |
| T10 | Add operator accounts and authentication | T09; dedicated Supabase Auth configuration | Owner-provisioned operator login/session handling, hatchery access, expiry/revocation and migration/regression checks pass; a separate live-provider login/me/logout/replay smoke test passes and the handoff is updated. | R16-R17 |
| T11 | Add protected tank/device management | T09-T10; define verified enrollment and binding lifecycle | Protected tank/device lifecycle, private-code/device-proof claiming and configuration-confirmation APIs pass simulated-device tests; ownership/history remain enforced. Real firmware/client onboarding is tracked separately. | R09, R16-R17 |
| T12 | Add reliable history and manual entries | T02, T09-T11 | Protected mixed history, measured partial manual entries, audited correction/void/restore and stable snapshot ordering pass tests. | R07, R09-R10 |
| T13 | Connect authenticated MQTT ingestion | T02, T07-T12; verified firmware claiming/runtime binding handoff and broker qualification before live admission | Backend admission, commit-before-ACK, deduplication, quarantine and outage/mTLS checks pass with simulated devices; separately qualify real ESP32/HiveMQ before live acceptance. | R05-R09, R16-R17 |
| T13A | Connect real ESP32 onboarding and unblock quarantined readings | T11-T13; existing board/wiring confirmed, local HTTPS and dedicated backend broker identity | Software/build checks plus owner-run claiming/restart and real HiveMQ delivery/ACK/quarantine receipt evidence pass. No T07 retests. | R04-R07, R09, R16-R19, R21 |
| T14 | Connect relay commands end to end | T06-T08, T10-T13; T13A before real-device acceptance | API acceptance, publication, device result and timeout remain distinct; duplicate/expired/unsafe commands are covered. | R14, R17 |
| T15 | Add reliable live updates | T10-T13 | Authorized browsers receive committed events and recover after disconnect/restart without exposing another owner's data. | R08-R10, R17 |
| T16 | Add the interface's login and access flow | T10-T11 | The user can sign in/out; route/API access follows permissions and session expiry. | R10, R16-R17 |
| T17 | Build tank views and reading displays | T12-T13, T15-T16 | Fresh, stale, missing, offline and default/estimated states are clear; server policy is used consistently. | R03, R08-R10 |
| T18 | Add device claiming, history, manual input, export and relay controls | T12, T14, T16-T17 | Operator Add device/claim status and other flows work with correct identities and honest export/command status; responsive/accessibility checks pass. | R09-R10, R14 |
| T19 | Validate and implement one water-quality policy | R08/Q02; research may start early; environmental assumptions must be explicit | Evidence supports the hatchery policy, the PRD is explicitly revised if needed, and shared policy tests pass. Unvalidated limits are not presented as proven. | R08, R10 |
| T20 | Add durable alerts and notifications | T10-T13, T17, T19; settle notification delivery/configuration | Alerts survive restarts, support acknowledgement and have visible notification retry/failure behavior. | R08, R20 |
| T21 | Verify the model and its timing | Q01/Q03; evidence gathering may start early | Training/artifact evidence and evaluation define the real input interval/horizons; missing evidence stays unresolved rather than being guessed. | R06, R11-R13 |
| T22 | Build and test the forecasting pipeline | T09, T12-T13, T21 | Eligible windows and target times are correct; evaluation meets documented criteria or the model remains unavailable/unqualified. | R11-R13 |
| T23 | Connect forecasts to the API and interface | T10, T15-T17, T22 | Stored forecasts, provenance, target times, confidence limitations and unavailable states display correctly. | R09-R13 |
| T24 | Prepare production deployment and monitoring | T03, T07, T10-T15; continue as features arrive | Isolated configuration, HTTPS/WSS, process roles, logs/metrics and readiness checks work in a reproducible deployment rehearsal. | R17-R18, R21 |
| T25 | Verify firmware updates and rollback | T04-T08; confirmed hardware/flash/partition/security context | Authorized update/self-test/rollback exercises provide device evidence; partitions alone do not count. | R19, R21 |
| T26 | Verify backups and database/app recovery | T09, T20, T24 | Backup restore, migration failure and application rollback are rehearsed without using or resetting live data. | R18-R21 |
| T27 | Test the complete software under failures and load | Applicable implementation tasks; define a measured test profile | Access, end-to-end, disconnect/recovery and load checks have recorded results, limits and resolved release-blocking failures. | R01-R14, R16-R21 |
| T28 | Prepare the release evidence and rollout plan | T19-T27 and all applicable release requirements | Requirement-to-evidence report, supported limits, runbooks and rollout/rollback steps are reviewed; actual site suitability remains explicit. | R01-R21, first-release boundary |

The task list is a proposed order, not a requirement to postpone all deployment, security or domain work until late. Security/data preservation apply throughout. T19/T21 research may run earlier; T24 deployment preparation can grow alongside each slice. Actual connected equipment (R15) and hardware expansions (R22) remain outside the first software release.

## Cross-chat working rule

[Rebuild status](status/rebuild.md) identifies the current task. Each started task has one record under `docs/status/tasks/Txx.md`, using the [handoff template](templates/task-handoff.md). Work, verification and remaining items stay in that record; stage-specific reports link to it instead of copying its state.

Before ending a working chat, update the task record, status and root [CONTEXT](../CONTEXT.md). Distinguish guidance given from owner-completed or explicitly delegated work; identify user-reported versus AI-observed results. State the exact next guided step, outstanding decisions and commit/uncommitted state. No task is done merely because source exists, a plan was explained or a session ended. Use [the session guide](operations/ai-workspace.md#one-task-per-chat) to start/resume work.

## Release limits

Production software needs evidence for applicable requirements, not just a passing build. Unverified hatchery thresholds, model horizons, hardware behavior and broker certificate capabilities remain explicit release questions in [open questions](research/open-questions.md). The numerical supported capacity is measured against a declared profile; unknown farm counts do not become invented facts.

The [existing assessment](status/implementation.md), [existing architecture](reference/architecture.md) and [superseded repair roadmap](history/2026-10-15-repair-roadmap.md) remain reference evidence. This roadmap does not delete the working prototype, alter the PRD or silently accept every design proposal.
