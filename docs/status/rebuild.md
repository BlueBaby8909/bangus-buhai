# Rebuild status

2026-10-23 feature styling follow-up: matched claiming, manual readings,
history/CSV and relay controls to the original prototype. Production CSS import
ordering fixed;14 frontend tests,lint/build and isolated production-browser
checks at360/768/1440 PASS. No services started/restarted; owner handles setup.
See [T18 follow-up](tasks/T18.md). Visual acceptance remains with the owner.

Original frontend baseline restored (2026-10-22), explicitly requested by owner.
Rebuild now reuses the prototype's actual navigation/header/dashboard/Tanks/Alerts
markup and original Tailwind4.3.3 tooling, with completed T16–T18 APIs/features
adapted into that baseline. Earlier visual redesigns are superseded. Keep this
baseline; future work should adapt features,not redesign it. Devices stays inside
Tanks. See T17's baseline-restoration checkpoint. Owner visual review pending;
hardware/Wi-Fi checkpoint and declined tests/BOOT deferral unchanged.

Updated: 2026-10-22. This page owns task states and the next task. Scope and finish conditions live in the [roadmap](../roadmap.md#task-list); product requirements live in the [PRD](../PRD.md). This is distinct from the [existing-code assessment](implementation.md).

## Current handoff

- **Owner-requested five-second live trial** (2026-10-22): interval source300→5seconds,
  normal build and app-only COM11 flash PASS; serial captures5.010seconds apart.
  Diagnostics OFF;9/9 preservation hashes match. Real web delivery blocked by device
  Wi-Fi BACKOFF,saved=yes; current finite queue full/oldest-event eviction observed.
  Backend worker41316 and verified broker TLS remain healthy. No broker/service/
  credential/partition change or new relay actuation. Next: owner makes the existing
  saved Wi-Fi/hotspot available; automatic retry can take up to five minutes.
  No reflash needed. Temporary5second firmware remains installed; normal product
  target300seconds unchanged. See [T18 trial checkpoint](tasks/T18.md).

- **T16–T18 DONE within approved frontend/local scope** (2026-10-22), under explicit
  combined implementation delegation. Prototype layout/artwork reused and polished;
  protected session/hatchery flow,tank/device displays/management,claims,live replay,
  manual revisions,CSV and explicit ON/OFF/AUTO command/result states implemented.
  **248 backend tests,13 frontend tests,six integrated browser scenarios and full
  rebuild runner PASS**;360/768/1440 screenshots/keyboard/no-overflow checks PASS.
  Unknown device connectivity and quiet unavailable quality/alert/forecast sections
  are explicit owner-approved scope choices. One API restart:16808/session31926;
  frontend36628/session91128 on5174. Existing MQTT/HTTPS/database retained.9/9
  preservation hashes,22/22 reused assets,zero leftover schemas,0006_t14/23 tables
  unchanged. No migration,firmware,broker,real actuation/claim,publication/deployment.
  T07/T14 declines and BOOT deferral unchanged. See [T16](tasks/T16.md),
  [T17](tasks/T17.md),[T18](tasks/T18.md). No pending owner action;next T19 on request.

- **T15 DONE within approved backend/local scope** (2026-10-22), under explicit
  implementation delegation. Protected tank streams,snapshot cursors,committed
  ordered replay,passive revocation/expiry and bounded connections/sends implemented.
  **240 backend tests PASS**,including25 T15 cases/real TCP; full rebuild runner PASS.
  API restarted once:PID26000/session70360,health200/protected HTTP401/WS403.
  Existing MQTT41316,HTTPS38672,PostgreSQL41608 retained; zero leftover test schemas,
  unchanged0006_t14/23 tables and9/9 preserved hashes. No migration/firmware/broker/
  new worker,owner hardware/provider login,Git publication or deployment. Production
  capacity/TLS rollout remain later tasks. T07/T14 declines/BOOT deferral unchanged.
  See [T15](tasks/T15.md). Next:T16 when requested; no pending owner action.
  Older handoffs below are historical.

- **T14 DONE within owner-approved scope** (2026-10-22), at explicit owner closure.
  Real protected ON/OFF/AUTO,committed results and API duplicates PASS; physical
  relay ON/OFF/LCD AUTO owner-confirmed.213 backend tests,44 contract tests/99 fixtures,
  runner,both builds,owner34/34 and five C payload checks PASS. Actual HiveMQ ACL and
  normal restoration PASS. Local0006_t14:23 tables/zero drift,data/config/hashes
  preserved. Qualified singleton/API8001/HTTPS8443 retained; diagnostics OFF.
  Remaining physical reboot/fault/unsafe-ON **owner-declined,UNTESTED**; no full
  hardware/failure qualification claim. T07 declined/BOOT deferred unchanged.
  No Git publication/deployment; hosted CI unobserved. See [T14](tasks/T14.md).
  Next:T15 planning only on request; do not reopen declined checks automatically.

- **T13A complete** (2026-10-22): approved real-device claiming, persistent binding,
  confirmation/restart, authenticated MQTT ingestion and quarantine custody verified.
  Owner restored normal firmware (exercise OFF), assignment retained and queue zero.
  Actual HiveMQ permission probes/DB checks PASS; 187 full backend tests plus one
  targeted probe test, full runner/builds and owner 26/26 firmware tests PASS.
  Ordinary ingestion running; lost-ACK test worker stopped. Local snapshot 22 accepted
  readings/history entries and one retained diagnostic quarantine candidate; migrations,
  original auth/database settings and partitions preserved. Hosted CI unobserved;
  no production deployment/Git publication. See [T13A](tasks/T13A.md).
  Next: T14 planning at owner request. T07 declined/untested, BOOT deferred.

- T13 **backend slice complete; live acceptance pending** (2026-10-21), under
  explicit owner delegation: separate verified MQTT worker, commit-before-ACK,
  retained confirmation evidence, binding-window admission and bounded quarantine.
  **158 backend tests/full rebuild runner PASS**, including nine real local
  generated-certificate broker checks. Local 0005_t13: 20 application tables,
  zero drift/seeds or leftover test schemas/containers. Prior rows/migrations/
  settings/firmware preserved. Live mode stays disabled pending real ESP32 proof/
  runtime binding/confirmation and actual HiveMQ backend/device role qualification.
  Next T14 planning at owner request. No cloud/firmware/Git/deployment action;
  hosted CI unobserved. T07 gaps/BOOT deferral unchanged. See [T13](tasks/T13.md).
  Older handoffs below are chronology.

- T12 complete within its approved backend scope (2026-10-21), under explicit
  owner implementation delegation: protected combined reading history, partial
  measured manual entries, audited correction/void/restore and signed snapshot
  pagination. All **106 backend tests** and the full rebuild runner PASS. Explicit/
  repeated local migration 0004_t12: 18 application tables, zero drift/seeds or
  leftover test schemas; prior rows, migrations and private settings preserved.
  Next T13 planning at owner request; real firmware proof/runtime binding and
  confirmation remain a prerequisite before live admission. No Git publication,
  deployment, cloud or firmware action. Hosted CI unobserved; T07 gaps/deferred
  BOOT work unchanged. See [T12](tasks/T12.md). Older entries below are chronology.

- T11 complete within backend-first scope (2026-10-21), under explicit owner
  implementation delegation: protected registry, trusted device preparation,
  operator claiming/device proof, desired/confirmed configuration, archival and
  retained binding history implemented. All 76 backend tests and full rebuild
  runner PASS. Local revision 0003_t11, 14 application tables, zero drift/seeds
  or leftover test schemas; existing counts/old migrations/private configs preserved.
  Real ESP32/phone onboarding remains a separate follow-up before live T13.
  Next T12 planning at owner request; no inherited implementation authorization.
  No Git publication, firmware/cloud changes or real device prepared. Hosted CI
  unobserved; T07 gaps/deferred BOOT work unchanged. See [T11](tasks/T11.md).

- T10 complete within operator-authentication scope (2026-10-21), under explicit owner implementation delegation:
  Supabase/operator accounts, migration 0002_t10, persistent revocable sessions,
  local provisioning and request protection implemented. All 48 backend checks
  PASS; full rebuild runner PASS. Development metadata has zero drift and zero
  seeded account/domain rows; no test schemas remain. Real Auth/JWKS and saved
  signup/anonymous/email settings verified. Owner-run live smoke now PASS:
  real Supabase login/protected cookie, /me, logout/reused-cookie rejection and
  temporary-schema cleanup; AI reviewed the supplied terminal output. Next T11
  planning when requested; no inherited T11 implementation authorization.
  Hosted CI unobserved, no Git publication/deployment. See [T10](tasks/T10.md).
  T09 completion, T07 gaps and deferred BOOT work remain unchanged; older entries
  below are chronology, not the active task.

- T09 complete within database-foundation scope (2026-10-21): owner supplies
  successful Docker info; AI runs supported Compose setup, explicit/repeated
  migration and all 22 tests successfully. PostgreSQL 18.6 container healthy on
  loopback 55432, revision 0001_t09, zero metadata drift/development event rows/
  remaining test schemas. Docker volume/private configuration retained; no old
  database reset or firmware/Git change. Hosted CI remains unobserved. Next T10
  planning only when requested; see [T09](tasks/T09.md). Earlier pending-Docker
  entries below are historical and superseded by this checkpoint.

- T09 implemented under explicit owner delegation (2026-10-21): hatchery ownership,
  several devices per tank/one open binding per device, immutable history, pooled
  SQLModel access and frozen Alembic migration, shared event identity/conflict
  persistence, dedicated Compose setup and PostgreSQL CI job. Seventeen real DB
  tests and five offline setup/config tests PASS on isolated native PostgreSQL
  18.6; full rebuild checks/fresh locked install PASS. Docker Desktop exits at a
  runtime socket error, so Compose startup remains the T09 finish checkpoint.
  No prototype/data/firmware/Git mutation. T07 gaps/deferred BOOT work unchanged;
  do not advance to T10 automatically. See [T09](tasks/T09.md).

- Standalone Wi-Fi switching deferred by owner (2026-10-21): keep proposed XIAO ESP32S3 BOOT/GPIO0 five-second hold, LCD feedback and secure phone BLE replacement as a later firmware follow-up. No implementation or hardware changes; current deliberate reopening remains USB-only. Do not block backend development or restart this follow-up automatically. Next T09 planning when requested; T08 complete within limits. See [T07](tasks/T07.md).

- Standalone Wi-Fi follow-up (2026-10-21): owner requests PC-free network switching. Current deliberate setup reopening is USB-only. Recommend five-second physical setup-button hold with LCD feedback and existing secure phone BLE/recoverable replacement; confirm exact board/button wiring first. Guidance only, no code/hardware change; T08 completion unchanged. See [T07](tasks/T07.md).

- T08 complete within recorded firmware/local-ACK scope (2026-10-21): normal firmware restored after 18/18 Unity and 3/3 actual C contract checks. Latest owner log restores eight real pending readings, adds new-boot capture (nine pending), republishes original event and receives telemetry PUBACK at 13.452 s; sensing and secure connectivity continue. Physical wear/cut-during-write and T13 backend integration remain limits; T07 gaps unchanged. Next T09 planning only when requested. No further build/flash or implementation needed for T08; no Git mutation. See [T08](tasks/T08.md).

- T08 regression/contract PASS (2026-10-21): owner test build/app-only flash succeeds after nvs_flash dependency correction; all 18 cases PASS, zero failures/ignored, ELF ef47d7233. AI validates three actual C-emitted payloads using accepted wire contracts: 3/3 PASS. Red storage-error logs are expected fake-NVS injections, not real partition faults. Next cd .. and app-flash monitor to restore normal firmware, review telemetry PUBACK. Prior real storage/reboot checks stand; restoration pending. See [T08](tasks/T08.md).

- T08 test build correction (2026-10-21): owner compilation stopped before flash/assertions because test main could not include nvs.h. AI adds direct PRIV_REQUIRES nvs_flash in tests/main/CMakeLists.txt; header/dependency/diff reviewed, owner rebuild pending. Repeat build app-flash monitor from tests, send 18 results and emitted payloads. Board still runs normal firmware. Prior runtime/recovery evidence stands. See [T08](tasks/T08.md).

- T08 power-cycle checkpoint reviewed (2026-10-21): restored four readings, new boot capture raises pending to five, original boot/seq replay receives PUBACK and repeats after 30 seconds. Saved network/mTLS and sensing continue. Observed reboot restoration, not cut-at-write-boundary qualification or payload-byte comparison. Next owner combined build app-flash monitor from tests: 18 assertions plus emitted payloads, then normal restoration. AI review/notes only. See [T08](tasks/T08.md).

- T08 full flash/runtime PASS (2026-10-21): new 256 KiB telemetry partition active, initial event captured before network, ACK subscription/secure telemetry PUBACK and same-event 30-second retry confirmed. One pending event correctly retained without backend ACK; sensing continues. Next power-cycle current app and reopen monitor without flash, then combined 18 tests/normal restoration. Persistence/test results pending. AI review/notes only. See [T08](tasks/T08.md).

- T08 first owner build/app-only flash reviewed (2026-10-21): build/hash PASS, image 1,403,616 bytes with 55% app slot free. Old device table still lacks telemetry because owner used app-flash; storage pauses with ESP_ERR_NOT_FOUND. Certificate MQTT/ACK subscription/online PUBACK and continued sensing confirmed. Next normal firmware idf.py -p COM11 flash monitor installs the new table; no erase-flash. Storage/replay, 18 tests and power-cycle remain pending. AI review/notes only. See [T08](tasks/T08.md).

- T08 delegated implementation (2026-10-21): owner selects durable/newest-16/local-ACK tests and explicitly requests implementation. Queue/storage/serialization/MQTT ACK/replay and ten new Unity cases implemented. Syntax/static/partition checks, 40 contract tests and 97 fixtures PASS; owner full normal/test builds, 18-case run and actual power-cycle remain pending. Next normal build flash monitor includes new partition table; no erase. No AI full build/flash/cloud/Git actions. See [T08](tasks/T08.md).

- T08 planning begins at owner request (2026-10-21): preserve 16 readings through outages; first settle power-loss persistence/overflow and contract metadata, then guide coding after plan response. No implementation authorized. T07 code finished with partial verification; gaps remain, two tests explicitly skipped. See [T08](tasks/T08.md) and [T07](tasks/T07.md). No AI implementation/device/cloud/Git actions.

- T07 certificate test skipped (2026-10-21): owner explicitly skips certificate removal/recovery due to testing burden. Mark untested; no broker change or further execution. Existing confirmed results stand; T07 remains in progress with verification gaps. Do not resume skipped test automatically or interpret as all remaining tests completed. Notes only, no AI implementation/device/cloud/Git actions. See [T07](tasks/T07.md).

- T07 scan fix runtime PASS (2026-10-21): owner build/flash/scan found three APs without timing warning; candidate commit and certificate MQTT/online PUBACK recovered. Next owner certificate removal/restoration on separate Starter with fresh-session rejection and cache-aware automatic recovery checks. No AI cloud/device/implementation/Git actions. See [T07](tasks/T07.md).

- T07 delegated scan timing fix (2026-10-21): owner explicitly requested code edit; AI switched active dwell to installed SDK defaults 0/120 ms, passive path unchanged. Diff/SDK-definition checks PASS. Owner build/flash and phone scan validation next; no AI build/device/cloud/Git action. See [T07](tasks/T07.md).

- T07 forget/reprovision PASS (2026-10-21): owner log confirms Wi-Fi-only record removal, Security 2 setup, candidate IP/commit, BLE close and same-identity certificate MQTT/online PUBACK at 68.257 s; sensing continues. Known scan dwell warning persists. Next owner uses SDK default active scan min/max, rebuilds/app-flashes and checks phone scan; guidance only. No new AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- T07 normal firmware restored (2026-10-21): owner app-only flash/hash and 56% free-slot check PASS; saved Wi-Fi, time/TLS/certificate MQTT and online PUBACK at 13.728 s confirmed. Eight regressions already PASS. Next owner Wi-Fi forget/reprovision check in one pass; no certificate change. AI review/notes only; no implementation/device/cloud/Git mutation. See [T07](tasks/T07.md).

- T07 eight regressions PASS (2026-10-21): owner runtime shows all eight named tests PASS, 8 Tests 0 Failures 0 Ignored, OK; normal 8 MB/3 MiB factory layout retained. Board last runs test app; next owner restores normal firmware with app-flash monitor from rebuild/firmware on COM11. Networking/physical output not covered by this suite. No AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- T07 regression build PASS (2026-10-21): owner output confirms test build/image fit after networking exclusion. Next owner app-flash monitor on COM11 from tests; generated app-only arguments preserve current bootloader/table/NVS. Eight assertion results pending; restore normal firmware app after review. No AI build/test/flash or further implementation. See [T07](tasks/T07.md).

- T07 delegated test-build correction (2026-10-21): owner explicitly requested implementation; AI added one-line wifi_manager/mqtt_manager exclusions to test CMake. Diff/whitespace check PASS; owner build and test execution pending. No AI build/flash, dependency/configuration changes beyond that exclusion, or cloud/Git mutation. See [T07](tasks/T07.md).

- T07 regression build (2026-10-21): owner build fails resolving espressif__mqtt from unused networking component. Next owner excludes wifi_manager/mqtt_manager in test project and rebuilds; no test execution/flash yet. Installed SDK EXCLUDE_COMPONENTS behavior reviewed. AI guidance/notes only; no configuration edit or build. See [T07](tasks/T07.md).

- T07 test deferral (2026-10-21): owner skips internet-only outage due to unavailable router access; untested. Next owner builds existing eight-case regression app, then review before device execution because test flash/partition settings predate normal firmware layout. No AI build/test/flash, implementation or cloud/Git changes. See [T07](tasks/T07.md).

- T07 retained restart cycle (2026-10-21): owner supplied restored-power online JSON with fresh boot_id 8ae134a5-8a60-4b53-953e-527bc85931e9 and connection_id 1dfe34f7-a4f9-4746-a29d-92002dbcbf61. Complete retained online/offline Will/restored online cycle PASS from owner broker observations. Next internet-only outage with Wi-Fi left on and monitor evidence through automatic MQTT recovery. Notes only; no AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- T07 offline Will (2026-10-21): owner supplied retained offline JSON after guided abrupt power loss; boot_id and connection_id match preceding online state. Retained offline Will check PASS from owner broker observation; exact latency unmeasured. Next restore power and confirm retained online with fresh boot/connection IDs. No AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- T07 retained online (2026-10-21): owner Control Center observation/pasted JSON matches recovered connection 61b02c51-cb3b-4868-a0ca-e418ae8175ab, state online. Next abrupt device power loss, wait 60 seconds and refresh retained status for offline Will with matching identities before restoring power. No broker permission changes or independent observer enrollment performed. See [T07](tasks/T07.md).

- T07 outage recovery (2026-10-21): owner log confirms automatic Wi-Fi/MQTT reconnection without reboot, fresh connection ID and online PUBACK about 4.9 s after restored IP; sensing continues. Increasing Wi-Fi retry delays observed; five-minute cap and MQTT-only backoff not exercised. Next inspect Starter Control Center for authorized retained/Will observation. No new AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- T07 normal status check (2026-10-20): latest owner boot log confirms online enqueue/PUBACK at 28.088 s with sensing continuing. No outage or second connection shown; next AP outage/restoration with new ID/PUBACK. Retained/Will needs separate broker observation. No new AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- T07 delegated status/LWT/recovery (2026-10-20): implemented in existing MQTT component with one notification-driven lifecycle owner, per-attempt identity, retained QoS 1 status/Will and capped jittered retries. Syntax/format-contract checks PASS; owner full build/radio/backoff/Will evidence pending. Host C execution checks unavailable, not PASS. Next owner build/flash and online/outage/reconnect logs. No AI cloud/device/Git changes. See [T07](tasks/T07.md).

- Owner secure-MQTT positive check (2026-10-20): combined build/flash PASS, UTC synchronized, broker certificate validated, MQTT device-certificate login at 27.217 s, acquisition continues; 56% app partition free. Next status/LWT and bounded reconnect guidance; remaining negative/security/local/regression checks open. No new AI implementation/device/cloud/Git changes. See [T07](tasks/T07.md).

- Delegated MQTT connection (2026-10-20): certificate embedding, MAC client ID, verified HiveMQ mTLS and start after SNTP/live IP implemented; Clang syntax PASS. Owner combined build/flash/log review next. No actual ESP32 MQTT result yet; status/LWT/bounded retries and other checks pending. No AI full build/device/cloud/Git mutation. See [T07](tasks/T07.md).

- Secure MQTT connection guidance (2026-10-20): owner to add external PEM embedding, verified mTLS client configuration and first connect after SNTP event/live IP; no new AI implementation authorized/performed. Source review then combined owner build next. See [T07](tasks/T07.md).

- T07 delegated time foundation (2026-10-20): mqtt_manager SNTP/startup implemented at explicit owner request; Clang syntax PASS for component/main. Full owner build/runtime deferred until certificate connection batch. Next mTLS connection guidance, then status/LWT/recovery. Source/docs uncommitted; no AI full build/flash/cloud/Git mutation. See [T07](tasks/T07.md).

- MQTT preparation (2026-10-20): owner refetch/reconfigure succeeded; MQTT 1.1.0, zero package checksum mismatches and certificate expiry checks confirmed. Next owner mqtt_manager time-readiness coding, then mTLS connection. No AI implementation/setup/build commands. See [T07](tasks/T07.md).

- T07 architecture critique reviewed (2026-10-20): targeted cleanup recommended; suggested 120-line manager replacement does not preserve RAM-only trials/BLE reopening as written. No redesign accepted or implementation performed. Evidence in [T07](tasks/T07.md).

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
| T07 | remaining checks owner-declined; untested | [Task record](tasks/T07.md); implementation finished, partly verified: provisioning/recovery/mTLS/retained status-Will/eight regressions/scan fix evidenced. Required security/local checks remain unverified; owner moves to T08 planning, no acceptance completion claim |
| T08 | complete within recorded limits | [Task record](tasks/T08.md); normal storage/publication/retry/reboot recovery, all 18 Unity cases and 3 actual C payload/contract comparisons PASS; normal firmware restored, real queue intact. Live backend ACKs remain T13; physical qualification limits explicit |
| T09 | done | [Task record](tasks/T09.md); supported Docker setup, initial/repeated migration, 22 tests and metadata/cleanup checks PASS; later API/deployment and hosted CI limits explicit |
| T10 | done | [Task record](tasks/T10.md); 48 backend checks/full runner and real Supabase login/me/logout/replay/temporary-schema cleanup PASS; hosted CI/deployment limits explicit |
| T11 | done within backend scope | [Task record](tasks/T11.md); 76 backend checks/full runner, local 0003_t11 migration and preservation/cleanup PASS; real firmware/interface onboarding remains explicit follow-up |
| T12 | done within backend scope | [Task record](tasks/T12.md); 106 backend checks/full runner, local 0004_t12 migration, history/revisions/concurrency/pagination/preservation PASS; frontend/MQTT/hosted CI remain separate |
| T13 | backend complete; live pending | [Task record](tasks/T13.md); 158 backend/full runner PASS, real isolated mTLS broker integration and 0005_t13 preservation verified; real ESP32/HiveMQ qualification still required |
| T13A | in progress | [Task record](tasks/T13A.md); software implementation/build checks, owner hardware checkpoints next |
| T14 | planned | No implementation evidence yet |
| T15 | planned | No implementation evidence yet |
| T16 | planned | No implementation evidence yet |
| T17 | planned | No implementation evidence yet |
| T18 | planned | No implementation evidence yet |
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



Current position (2026-10-21): T13 backend slice complete, live acceptance pending. 158 backend tests/full runner PASS, including isolated generated-cert broker checks. Local 0005_t13 has 20 tables, zero drift/seeds/test schemas or broker containers; old rows/migrations/settings and firmware preserved. Live mode disabled pending real ESP32 proof/runtime binding/confirmation and actual HiveMQ role qualification. Next T14 planning at owner request; hosted CI/deployment unobserved. T07 gaps/BOOT deferral and unrelated work preserved. HEAD 0bf5fcd; no stage/commit/push. See [T13](tasks/T13.md).
