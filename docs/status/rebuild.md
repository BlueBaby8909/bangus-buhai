# Rebuild status

Updated: 2026-10-21 (frontend integration preparation; firmware handoff preserved). This page owns task states and the next task. Scope and finish conditions live in the [roadmap](../roadmap.md#task-list); product requirements live in the [PRD](../PRD.md). This is distinct from the [existing-code assessment](implementation.md).

## Current handoff

- Frontend publication (2026-10-21): owner-requested commit `9d49b57` successfully pushed to `origin/kyle`. See [publication evidence](tasks/frontend-T16-T18-preparation.md#github-publication--2026-10-21). This does not change T16-T18 acceptance or the firmware T07 handoff.

- Frontend implementation preparation (2026-10-21): owner-authorized component/source consolidation preserves original design/assets, adds manual entry UI and guarded backend transport, excludes fixtures from production, and adds release/deployment preparation. Lint, 23 regression/rendering checks and build/distribution checks pass; unconfigured release is blocked. Browser localhost access timed out; backend/auth/live/deployed acceptance remains unverified. [Current frontend handoff](tasks/frontend-T16-T18-preparation.md#component-consolidation-and-backenddeployment-preparation--2026-10-21) owns details. T16-T18 remain incomplete; firmware T07 unchanged.

- Frontend source review (2026-10-21): reviewed clean HEAD `c5e2486`; sample integration limits confirmed. Dashboard availability/connectivity/provenance and TankDetail request-lifecycle findings are recorded in the [frontend handoff](tasks/frontend-T16-T18-preparation.md#read-only-review--2026-10-21). No application changes or runtime checks; T16–T18 states and firmware T07 handoff unchanged.

- Parallel frontend preparation (2026-10-20): original Dashboard/Tanks/Alerts/Data navigation and feature screens restored in `rebuild/frontend/` under the expanded request and library approval, with labelled sample forecast/history/chart/export/dialog/relay-preview flows. Latest preparation separates the sample provider behind a configurable facade and uses neutral product wording, an offline indicator and pH provenance; developer controls are hidden on normal routes. Live integration remains pending reviewed contracts. Lint/build, seven sample/provider regression tests and bounded browser checks passed. [Separate frontend handoff](tasks/frontend-T16-T18-preparation.md) owns evidence, limits, uncommitted files and the next integration step. T16–T18 remain incomplete; T07 remains the firmware collaborator's active task below.

- Active T07 guidance (2026-10-18): owner reports starting HiveMQ Starter trial and accepted the revised owner-led plan. Next inspect separate cluster Overview/Access Management, expiry/payment status and certificate controls. EMQX/Mosquitto no longer targeted; no automatic resource deletion. Owner implements/configures/runs commands; AI guides/reviews/maintains notes only. All firmware implementation and runtime checks pending. See [T07](tasks/T07.md).

- Latest completed task: **T06 - relay ownership and LCD integration**. Final eight tests passed; owner normal build/flash and LCD/relay operation confirmed. Calibration and controlled physical fault/manual-transition checks remain explicit limits. Next is **T07 planning**, in a new owner-started session. No T07 implementation, cloud changes or commands are authorized by this handoff. See [T06](tasks/T06.md).

- Completed task: **T03 - automate useful build and contract checks**. The owner implemented the runner/workflow and published source as `9b93ff6569f63b0a9e4abc7a70b1800851a36e0c` on `t03-checks`. Local success/failure source/output and successful public [CI run 38882404960](https://github.com/BlueBaby8909/bangus-buhai/actions/runs/38882404960) are reviewed. Detailed remote logs required sign-in and were not inspected; backend smoke remains limited to app import/health-function response. AI completed the final README usage update under explicit delegation and reviewed its diff/paths. The [T03 handoff](tasks/T03.md) records completion, limits and Git state: source/workflow published, final README/progress notes unstaged/uncommitted, no merge. Follow the [owner-led workflow decision](../decisions/0004-owner-led-development.md).
- Latest completed task: **T04 - verify the firmware starting point**. The owner reversed the skip and explicitly delegated the isolated prototype copy/build to AI. It passed with exit 0 using IDF 6.0.2-dirty, Python 3.13.3, CMake 4.0.3, Ninja 1.12.1 and GCC 15.2.0. The app is 1,319,168 bytes with 253,696 bytes (16%) free in each configured OTA slot. All 783 original inputs and 783 copied inputs were hash-identical at that checkpoint. The [T04 record](tasks/T04.md) records the exact recipe, log, ignored-default findings, SDK limits and preservation evidence. No feature edits, package installation, flash/monitor, hardware operation or Git mutation occurred. Notes remain unstaged/uncommitted. On 2026-10-17 the owner explicitly requested deletion of the untracked local baseline specimen; AI removed it without archiving. Raw T04 build/hash artifacts are no longer available, while the historical task record remains.
- Latest completed task: **T05 - make firmware readings trustworthy**, complete for the documented software scope. Owner-run normal sensor acquisition and the repaired regression app were reviewed: `test_snapshot_lifecycle:PASS`, `1 Tests 0 Failures 0 Ignored`. The [T05 record](tasks/T05.md) owns evidence, changes and limits. NTU calibration, physical fault exercises, UTC/wire integration and production configuration remain unverified/deferred. T06 was subsequently completed within documented unloaded-demo limits; see its task record.
- Completed tasks: **T01 and T02**. Their required rebuild source is now included in the published T03 source commit. The [T02 record](tasks/T02.md), [package guide](../../rebuild/contracts/README.md) and [accepted subset decision](../decisions/0005-device-contracts-v1.md) cover offline contracts only. T02's detailed local evidence remains 40 tests, 97 fixture cases and five schemas; T03 adds reviewed local automation output and independently observed hosted CI success. Firmware/browser consumers and live integration remain unverified. Supporting progress/research documents remain uncommitted.
- Latest source commit checked: `9b93ff6569f63b0a9e4abc7a70b1800851a36e0c` on `t03-checks`, matching `origin/t03-checks` and the successful CI run. Earlier baseline: `a8cb6260d545d9bcef487a008a8aaa304d1d5b0f` (approved cleanup), following `8ec0183` (second-brain setup).
- Working state at handoff: architecture/contract proposals and subsequent documentation changes are uncommitted. Separate pre-existing edits remain in `backend/mock_device.py` and `firmware/main/Kconfig.projbuild`; `.vscode/` and `docs/notes/Untitled.base` are also outside this roadmap change. Run `git status` again before work; this paragraph is a dated record, not a promise of a clean checkout.
- Limits: replacement design remains proposed; actual hardware/wiring/calibration, domain thresholds, model evidence and broker plan are not verified. These constrain affected tasks rather than blocking every independent foundation task.

## Task states

States: `ready` = next bounded task can be requested; `planned` = not started; `in progress` = work remains; `waiting` = a named dependency is missing; `done` = scope and required checks have evidence. Record waiting reasons and partial work in the task record. The end of a chat does not change a task to done.

| Task | State | Evidence / handoff |
|---|---|---|
| T01 | done | [Task record](tasks/T01.md); workspace, setup guide and bounded verification complete |
| T02 | done | [Task record](tasks/T02.md); offline schemas/validation/examples complete, 40 tests and 97 fixture cases pass |
| T03 | done | [Task record](tasks/T03.md); source/workflow published, local success/failure and hosted CI success reviewed, usage documentation complete locally |
| T04 | done | [Task record](tasks/T04.md); delegated isolated build passed, exit 0, partition fit and input preservation verified; config/hardware limits recorded |
| T05 | done | [Task record](tasks/T05.md); normal acquisition plus on-device simulated-input lifecycle PASS; calibration/integration/configuration limits explicit |
| T06 | done | [Task record](tasks/T06.md); final eight tests pass; normal build/flash and owner LCD/relay operation confirmed; unloaded demo only, physical fault/manual tests and calibration remain explicit limits |
| T07 | in progress | [Task record](tasks/T07.md); owner build/flash and BLE Security 2 advertising/USB prompt confirmed (63% app space free). Sensors intentionally disconnected. Next first phone provisioning/reboot; actual IP trials/rollback/recovery and remaining MQTT/security checks pending |
| T08 | planned | No implementation evidence yet |
| T09 | planned | Ownership interpretation must be settled before schema decisions |
| T10 | planned | No implementation evidence yet |
| T11 | planned | No implementation evidence yet |
| T12 | planned | No implementation evidence yet |
| T13 | planned | No implementation evidence yet |
| T14 | planned | No implementation evidence yet |
| T15 | planned | No implementation evidence yet |
| T16 | planned | Shared frontend layout/navigation prepared only; authentication/access integration unfinished. [Frontend preparation](tasks/frontend-T16-T18-preparation.md) |
| T17 | in progress | Preparatory sample tank displays and data states checked; backend/server policy/live/auth dependencies remain unfinished. This is not full T17 completion. [Frontend preparation](tasks/frontend-T16-T18-preparation.md) |
| T18 | in progress | Original history/chart/export and local relay/tank-dialog previews restored with sample data; manual input, permissions, real commands and integration unfinished. [Frontend preparation](tasks/frontend-T16-T18-preparation.md) |
| T19 | planned | Domain research can begin independently; policy not yet validated |
| T20 | planned | No implementation evidence yet |
| T21 | planned | Model evidence gathering can begin independently |
| T22 | planned | No implementation evidence yet |
| T23 | planned | No implementation evidence yet |
| T24 | planned | Prepare deployment/monitoring alongside relevant slices |
| T25 | planned | Hardware/partition context and authorized device checks required |
| T26 | planned | No implementation evidence yet |
| T27 | planned | No qualification evidence yet |
| T28 | planned | No release acceptance claimed |

At a task boundary, update this table and the current handoff to the next unfinished task. Keep details and actual test/commit evidence in that task's record. A suggested order may change when evidence warrants it; record dependency changes in the roadmap rather than inventing completed work.



Current work: T07 BLE/USB batch build/startup confirmed; first owner phone provisioning and reboot check next. See [T07](tasks/T07.md). T06 remains complete within recorded limits, calibration deferred. No further implementation authorized automatically; no cloud changes or flash performed by AI.
