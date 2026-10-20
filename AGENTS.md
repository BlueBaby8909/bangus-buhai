# Project orientation

## Owner-led work: guide by default

- The owner implements the project themselves. Begin each session with a plain-language plan: goal, why it matters, scope, what is outside scope, steps and finish checks. Then guide one step at a time and review the owner's work/results.
- Read-only inspection is allowed for context and review. Do not edit application code, tests, build/deployment configuration, create implementation scaffolding, install dependencies, run build/test/application commands, change hardware/cloud state, or stage/commit/push implementation work unless the owner explicitly requests that action and scope.
- "Start T01", "continue", "help me", or agreement with a plan means planning/guidance, not permission to implement. A session's task description or finish conditions do not override this rule. Explicit requests such as "edit this function for me" authorize only the requested implementation assistance.
- Explain concepts and provide steps/check commands for the owner to run. Use small examples when helpful; do not deliver or apply the entire implementation by default. Label user-reported results separately from checks actually observed/run by the AI.
- Continue the agreed second-brain documentation maintenance: record confirmed decisions, user progress, evidence/limits and the next guided step. Documentation maintenance never authorizes application changes or silent product-scope changes.
- The owner starts their own sessions. Do not create, resume or message another session unless explicitly asked. Record this preference in [decision 0004](docs/decisions/0004-owner-led-development.md).

## Project references

- Read [docs/PRD.md](docs/PRD.md) for product requirements and scope. It is the single authoritative product specification.
- Read [CONTEXT.md](CONTEXT.md) for task routing and the active rebuild workflow. Follow its selected stage contract; do not assume every stage is authorized by a request to inspect or plan.
- Read [docs/README.md](docs/README.md) for the documentation structure and evidence rules.
- Use [docs/status/implementation.md](docs/status/implementation.md) for the dated existing-code assessment and [docs/roadmap.md](docs/roadmap.md) for rebuild milestones. Existing code and architecture are reference material, not an approved replacement design.
- Requirements describe the target; source code establishes implemented behavior. Record disagreements explicitly instead of silently changing either.
- Confirm hardware context before hardware-facing changes. The owner confirmed ESP-IDF firmware and an unloaded demonstration relay on 2026-10-15; electrical wiring and calibration still need verification.
- Preserve local environment files, databases, model artifacts, certificates, and unrelated work. Do not run seeding/simulator scripts or flash hardware as part of a read-only audit.
- For each authorized code change, identify the relevant PRD requirement, add meaningful verification, and update affected evidence/status documents.
- Keep notes and experiments non-authoritative until their conclusions are reviewed and promoted through the PRD/decision process.

## Working across chats

- Before a numbered rebuild task, read [rebuild status](docs/status/rebuild.md), its task record, and the task's scope/finish conditions in [the roadmap](docs/roadmap.md). Inspect the actual Git tree; do not rely on the previous chat's memory or a stale status claim.
- Plan and guide the requested task only. A task may span chats; do not mark it done just because a chat ends or advance to the next task without the owner's request. Implementation still requires the explicit permission described above.
- After meaningful checkpoints and before ending task work, update the task record with the plan/guidance given, work actually completed by the owner or explicitly delegated to the AI, changed files, decisions, test commands/results and who observed them, remaining work, exact next guided step and commit/uncommitted state. Update rebuild status and the root CONTEXT pointer too.
- Use [the handoff template](docs/templates/task-handoff.md). Keep task state in one record; stage outputs should link to it. Update canonical product/reference documents when the work warrants it.
- Preserve unrelated edits. Commit only task-owned changes when authorized and record the actual commit; do not assume a push is authorized or invent a checkpoint. Explicitly record pending files when no commit is made.
