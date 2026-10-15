# 0003: First production-software release boundary

Date: 2026-10-16. Status: accepted scope, based on explicit owner answers in this conversation. Requirements are maintained in [PRD section 1](../PRD.md#first-production-software-release).

## Evidence and rationale

The owner wants to rebuild a working prototype because it is not production ready. When asked about hardware for the first production release, the owner selected: "Keep the current prototype hardware; focus on production software first." For users and deployment scope, the owner selected: "A small group of real operators at one farm."

These choices bound the first release without changing the end-product direction. Production software needs defined acceptance evidence; the term does not certify hardware, domain effectiveness, or forecasting accuracy.

The owner subsequently confirmed "hatchery/larvae" as the first deployment's growth stage on 2026-10-16. This settles the first-release audience/domain choice; environmental conditions and biological thresholds still require evidence under Q02.

The owner does not know the tank/operator counts or internet reliability and reiterated that the software should be production ready. Do not require farm estimates before proceeding with software planning. Use the PRD's engineering qualification approach, leaving site-specific suitability unverified until actual deployment details are available.

## Consequences

- The first-release scope is now explicit in the PRD; downstream design must reference it instead of inventing a separate specification.
- Keep the owner-confirmed unloaded-relay context from [decision 0001](0001-project-baseline.md). Real actuation and physical pH hardware are later milestones. Software must still handle provenance, failures, and truthful displayed state.
- One-farm operation still needs accounts, permissions, ownership enforcement, and protection against unauthorized access. Do not treat real operators as an unauthenticated demonstration audience.
- Existing choices are baseline constraints/evidence, not proof that every old module, artifact, interface, or exact dependency version should be reused.
- No replacement architecture, hosting provider, biological policy, ML validation result, code deletion, hardware flash, or data migration is selected by this decision.

## Remaining release decisions

Operating conditions for the selected hatchery/larvae stage, practical load/connectivity needs, hosting/operations responsibility, timing/model provenance and acceptance, capacity semantics, and hardware/calibration evidence remain unresolved. Record decisions against the existing [open questions](../research/open-questions.md) and PRD IDs rather than silently choosing answers.
