# Documentation audit and migration, 2026-10-15

This dated record explains what was kept, corrected, retired, or left uncertain. It is historical evidence, not another specification. Product authority is [PRD](../PRD.md); current source assessment is [implementation](../status/implementation.md).

## Method and limits

Reviewed the four project READMEs, all eight Markdown planning documents, planning configuration, and the inventory/role of six OpenSpec skill files and six matching workflow files. Compared claims with source entry points, every backend route/model/service, frontend routes/data paths, firmware task/provisioning/telemetry/sensor/relay implementations, manifests, partition/default configuration, and model metadata. Examined recent local Git history. Non-OpenSpec skills in the outer workspace are reusable tooling and remain untouched; they were not audited as product documentation.

Baseline is `785e08b` plus the local cleanup and documentation changes already present before migration. Source review does not prove runtime correctness. No build, hardware flash, sensor calibration, model evaluation, cloud-account inspection, remote fetch, live database audit, or mutating test was performed for this migration. Earlier session startup/broker observations are historical observations, not new acceptance results.

## Document dispositions

Retired paths below are provenance labels, not live links. No stale originals are duplicated in the active knowledge tree. Git retains committed history; current accepted scope changes are preserved in the PRD and decision record.

| Original file | Accurate or useful content | Outdated, conflicting, or redundant content | Disposition / destination |
|---|---|---|---|
| `README.md` | FastAPI/SQLModel, tank/log concepts, startup entry point, quality evaluation | Root incorrectly titled backend; feeding scope and user endpoints no longer exist; insufficient system orientation | Rewritten project entry point; commands link to [operations](../operations/development.md) and scope to PRD |
| `backend/README.md` | Backend startup, tank/log CRUD, SQLite/settings, computed quality | User/feeding routes and ownership fields removed; change-history claims describe superseded code; lacks device/prediction/WebSocket surface | Rewritten module entry point; [architecture](../reference/architecture.md), [status](../status/implementation.md) |
| `frontend/README.md` | React/Vite, development/build scripts, API URL setting | Deleted Users page/components/styles/helper; obsolete feeding/manual forms; old palette; dashboard described as tank grid | Rewritten module entry point with actual route map; [architecture](../reference/architecture.md) |
| `firmware/README.md` | BLE provisioning, default name/PoP derivation, NVS | "securely" overstates validation; erase-flash is broader than credential reset; hardware/app compatibility unverified | Rewritten firmware entry point; [operations](../operations/development.md), [questions](../research/open-questions.md) |
| `openspec/.../proposal.md` | Three-parameter monitoring, early-warning vision, prototype/production distinction | Blanket assertion all layers are functional; duplicates requirements; workflow-specific capability scaffolding | Vision in PRD; rationale in [decision 0001](../decisions/0001-project-baseline.md); original retired |
| `openspec/.../design.md` | Broad architecture, explicit estimated pH, accepted active ESP-IDF/HiveMQ/demo choices, discussion of forecast alternatives | "Production-grade", all-questions-resolved, old Keras migration, aiomqtt-only backend, pure vanilla CSS, claimed completed research, guarantee that all requirements were phase-tagged | [Architecture](../reference/architecture.md), [decision](../decisions/0001-project-baseline.md), questions; original retired |
| `openspec/.../tasks.md` | Review categories across firmware/backend/frontend/ML/infra/security | All 72 unchecked items are review prompts, not verified defects; some request already-present functionality | Replaced by evidence-based status and dependency-ordered [roadmap](../roadmap.md); no unchecked item promoted to a completed result |
| `openspec/.../specs/prd/product-requirements/spec.md` | Product vision, hardware scope, device/data/UI/ML targets, production/security/reliability requirements | Mixes targets with completed behavior; BLE/SoftAP contradiction; scope boundaries ambiguous; telemetry timing differs from code; hatchery/grow-out context unresolved | Consolidated into PRD R01-R22; ambiguities retained as Q01-Q07 |
| `openspec/.../specs/prd/relay-control/spec.md` | Active-low relay, state reporting, command flow, hysteresis, stale OFF, configurable thresholds | Demonstration vs real equipment not separated clearly; Kconfig threshold configurability absent; `heater` label conflicts with high-temperature activation | PRD R14-R15, S08, Q04; original retired |
| `openspec/.../specs/prd/ml-forecasting/spec.md` | Three outputs, sequence/scaler, persistence/endpoints, provenance/confidence, artifact expectations | "Only one forecast" misses current recursive outputs; hourly semantics unproven; training recipe/data interval unverified; requested response timestamps/flag absent | PRD R06/R11-R13; Q01/Q03 retains original prescriptions and verification needs |
| `openspec/.../specs/prd/cloud-security/spec.md` | Managed broker selection, production ownership/auth/TLS/deployment/backup/OTA/validation goals | Goals treated as implementation; cloud/mTLS capability and framework crypto claims unverified; lifecycle scope ambiguous | PRD R16-R21, Q05/Q06; original retired |
| `openspec/.../specs/prd/gap-analysis/spec.md` | Layer-by-layer review method and roadmap intent | A specification for doing an audit, not a completed report; several of its 19 "known gaps" are stale or unverified | Replaced by this audit, implementation assessment, and roadmap; original retired |

Here `openspec/.../` abbreviates the former `openspec/changes/define-prd-and-gap-analysis/` directory.

## Reconciliation of the 19 old gap claims

| Old item(s) | Finding after source review |
|---|---|
| 1: single 3-hour forecast | Current code returns four recursive outputs, but genuine hour horizons are unverified; S07/Q01 |
| 2, 6, 9, 10, 11, 17: auth, durable alerts, CI, containers, automated tests, OTA | Still absent/incomplete in inspected source; S05/S09. Manual test utilities and OTA partitions exist, which do not complete these features. |
| 3, 4, 5: relay UI, prediction UI, charts missing | Incorrect: present, with integration/interpretation defects; S06-S08 |
| 7: SQLite unsuitable | SQLite is the current prototype backend; PostgreSQL is a retained production target. No workload benchmark establishes a universal suitability claim. |
| 8: auto-registration production concern | Mechanism exists; production ownership/claiming absent. Do not treat a payload tank ID as authorization; S04/S09. |
| 12: deprecated `datetime.utcnow` | Reviewed current model/ingestion timestamps use timezone-aware calls; the blanket migration claim is stale. Time semantics still need work. |
| 13: missing broker ACLs | Cloud account configuration cannot be verified from this repository; Q05 |
| 14, 15: missing relay telemetry/command topic | Incorrect: both exist in firmware/backend; state ownership and command transport have defects; S03/S08 |
| 16: SoftAP wording vs BLE | BLE is used in source; wording corrected in replacement docs |
| 18: Keras inference | Incorrect: PyTorch is already used; S07 |
| 19: framework migration | Managed components/new I2C/ADC/OneWire interfaces exist; local lock records IDF 6.0.2. Do not promise compatibility without a clean build; Q06. |

## Retained planning coverage

Old task groups 1 (requirements/domain) map to PRD/Q01-Q07; 2 (firmware) to S01-S03/S08 and roadmap 0-2; 3 (backend) to S04-S05/S09 and roadmap 2-4; 4 (frontend) to S06 and roadmap 6; 5 (ML) to S07/Q01/Q03 and roadmap 5; 6-7 (infrastructure/security) to S09/Q05 and roadmap 3/7; 8 (report assembly) to this audit and the roadmap. This preserves the useful review coverage without copying stale checkboxes.

Former design decisions D1 (five-spec layout) and D2 (workflow/audit method) are superseded by the portable documentation index. D3 (multi-output preference) remains a candidate in Q03; D4 (estimated pH), D5 (prototype/production separation), and D8 (active stack/demo scope) are retained in PRD/decision 0001. D6 (IDF migration) becomes version/build evidence in Q06; D7 (PyTorch migration) is recorded as already reflected in source. Old risks R1/R6 map to model provenance/timing, R2/R3 to production auth/database work, R4 to audit limits, and R5 to build compatibility. None is copied as a verified incident.

## Retired setup and preserved boundaries

After replacement documents and links were checked, `openspec/` was removed, including its two configuration YAML files, along with these project-local instructions:

- `.agent/skills/openspec-apply-change/SKILL.md`
- `.agent/skills/openspec-archive-change/SKILL.md`
- `.agent/skills/openspec-explore/SKILL.md`
- `.agent/skills/openspec-propose/SKILL.md`
- `.agent/skills/openspec-sync-specs/SKILL.md`
- `.agent/skills/openspec-update-change/SKILL.md`
- `.agent/workflows/opsx-apply.md`, `opsx-archive.md`, `opsx-explore.md`, `opsx-propose.md`, `opsx-sync.md`, `opsx-update.md`

The `.agent` tree contained only those OpenSpec items at audit time and was removed after its contents were verified. The outer workspace's `.agents/skills` is unrelated and preserved. The owner explicitly requested keeping the globally installed OpenSpec CLI available for other projects; it remains installed. Project documentation no longer depends on it.

This migration does not change application code, package manifests, runtime settings, certificates, data, or model artifacts. Earlier requested cleanup deletions and unrelated editor settings are preserved as existing work. Verification compares retained non-document tracked-file hashes and checks internal links, retired paths, requirement references, and whitespace. Passing these checks certifies the migration boundaries, not application behavior.

Migration checks: 17 Markdown documents; 183 local links/anchors validated; 22 unique PRD requirement IDs; 111 retained non-Markdown tracked files unchanged from the pre-migration fingerprint. No application test or build was needed for these documentation-only edits, and none was claimed.
