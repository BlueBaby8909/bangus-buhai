# Project knowledge index

Updated: 2026-10-16 (rebuild workspace). The source audit remains dated 2026-10-15. This is a plain Markdown second brain: it requires no particular editor, AI product, plugin, or documentation CLI. Start at the [workspace router](../CONTEXT.md) or [Obsidian/AI guide](operations/ai-workspace.md).

## Authority and reading order

1. [PRD](PRD.md): the only normative source for product scope, requirements, and acceptance criteria.
2. [Architecture](reference/architecture.md): descriptive source map and existing data flow.
3. [Implementation assessment](status/implementation.md): dated observations, limitations, and source evidence.
4. [Open questions](research/open-questions.md): unresolved product, hardware, and model assumptions.
5. [Rebuild roadmap](roadmap.md): proposed milestones; replacement design and reuse decisions remain pending.
6. [Development guide](operations/development.md): run/configuration instructions and operational limits.
7. [Decision record](decisions/0001-project-baseline.md): accepted choices and their provenance.
8. [Documentation audit](history/2026-10-15-documentation-audit.md): migration dispositions and rejected historical claims.
9. [Rebuild decision](decisions/0002-rebuild-direction.md): owner-confirmed restart direction and limits.
10. [First-release decision](decisions/0003-first-production-software-release.md): owner-confirmed production-software boundary; requirements remain in the PRD.

The architecture and implementation assessment describe the existing code, not an accepted replacement design. The [rebuild workflow](../workflows/rebuild/CONTEXT.md) selects scoped inputs and produces provisional stage outputs; those outputs do not override this authority order.

## Structure and boundaries

```text
docs/
  PRD.md                 product requirements; edit here to change scope
  reference/             verified descriptions of source and interfaces
  status/                dated implementation and verification evidence
  operations/            reproducible run and maintenance procedures
  decisions/             accepted decisions, rationale, consequences
  roadmap.md             prioritized work linked to requirement IDs
  research/              questions, external research, candidate conclusions
  notes/                 dated observations, meetings, working notes
  experiments/           reproducible hypotheses, methods, results
  history/               superseded context and migration records
```

The structure is the proposed cross-tool working convention adopted for this migration. Notes, research, experiments, history, and decisions cannot override the PRD. Architecture and status describe implementation; they do not introduce new requirements. Link to requirement IDs instead of copying requirement text. Module READMEs are entry points, not parallel specifications.

## Maintenance rules

- Label claims **source-verified**, **owner-confirmed**, **runtime-verified**, **proposed**, or **unverified**. State date, source/revision, and verification limits. Source presence does not prove working hardware or model accuracy.
- For changes to product behavior: update the PRD, record the rationale in a decision, then adjust roadmap/status references. Decisions explain a requirement but do not supersede it independently.
- For implementation-only changes: update source evidence, status, and applicable runbooks. Keep historical audit snapshots dated; do not rewrite them as current truth.
- Name future decisions `NNNN-short-title.md`; name observations and experiments `YYYY-MM-DD-short-title.md`.
- A useful note has a date, context, evidence, confidence, related PRD IDs, and follow-up. An experiment also has a hypothesis, reproducible method, results, and limitations. Research distinguishes citations from conclusions.
- Promote validated findings by updating the authoritative destination and linking the originating note. Never promote a historical claim simply because it appeared in an older document.
- Do not copy credentials, local environment contents, device secrets, or database exports into this knowledge base.

New AI tools should start with the repository [AGENTS.md](../AGENTS.md). [CLAUDE.md](../CLAUDE.md) is a pointer to the same material. Neither contains a separate specification.
