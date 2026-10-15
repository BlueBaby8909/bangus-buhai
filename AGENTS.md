# Project orientation

- Read [docs/PRD.md](docs/PRD.md) for product requirements and scope. It is the single authoritative product specification.
- Read [CONTEXT.md](CONTEXT.md) for task routing and the active rebuild workflow. Follow its selected stage contract; do not assume every stage is authorized by a request to inspect or plan.
- Read [docs/README.md](docs/README.md) for the documentation structure and evidence rules.
- Use [docs/status/implementation.md](docs/status/implementation.md) for the dated existing-code assessment and [docs/roadmap.md](docs/roadmap.md) for rebuild milestones. Existing code and architecture are reference material, not an approved replacement design.
- Requirements describe the target; source code establishes implemented behavior. Record disagreements explicitly instead of silently changing either.
- Confirm hardware context before hardware-facing changes. The owner confirmed ESP-IDF firmware and an unloaded demonstration relay on 2026-10-15; electrical wiring and calibration still need verification.
- Preserve local environment files, databases, model artifacts, certificates, and unrelated work. Do not run seeding/simulator scripts or flash hardware as part of a read-only audit.
- For each authorized code change, identify the relevant PRD requirement, add meaningful verification, and update affected evidence/status documents.
- Keep notes and experiments non-authoritative until their conclusions are reviewed and promoted through the PRD/decision process.
