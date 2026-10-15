# 0001: Product authority and active prototype baseline

Date: 2026-10-15. Status: accepted by the owner's instructions in this conversation. This records rationale; the [PRD](../PRD.md) remains the only product specification.

## Decisions and provenance

| Decision | Evidence and rationale | Consequence |
|---|---|---|
| Keep ESP-IDF as active firmware | Owner explicitly confirmed it is running on the prototype. Source contains ESP-IDF task/components. | Do not maintain the removed Arduino alternative as an active implementation. |
| Use HiveMQ Cloud | Selected setup in the conversation; backend startup earlier in the session reported a cloud TLS connection. Cloud permissions/capabilities were not audited. | Retired self-hosted broker files do not return as a documentation dependency. Preserve production authentication/authorization requirements; verify service-plan support separately. |
| Treat relay as an unloaded demonstration | Owner explicitly confirmed nothing is connected to its load side. | Preserve truthful ON/OFF behavior and state handling; do not assume the existing `heater` label specifies connected equipment. Production actuation remains a separate requirement. |
| Keep estimated pH explicit | Firmware provides a default source; physical pH is a future product requirement. | Preserve provenance through data and display; do not call default pH a measurement. |
| Retain PyTorch inference and three-parameter scope | Current imports/model class/artifacts use PyTorch; the inherited requirements limit current prediction to temperature/pH/turbidity. | Migration from Keras is no longer an outstanding task. Four-horizon validity remains unproven. |
| Replace workflow-specific planning with portable Markdown | Owner requested removal of the entire OpenSpec setup after a careful migration. | Use one PRD, linked reference/status/decisions, and clearly non-authoritative research/notes/experiments/history. AI-specific entry files only point to shared documentation. |

## Alternatives and unresolved choices

The older design preferred a single multi-output model over independent or recursive models, but did not provide a verified retraining implementation. Current source uses recursion; neither approach is accepted as proof of correct time horizons. That choice remains Q01/Q03.

Do not carry over the old five-spec layout, framework migration promises, "production-grade" label, assertion that every requirement was phase-tagged, or statement that all questions were resolved. These were superseded structure or unsupported claims. The retained requirements and unresolved prescriptions are mapped in the [audit](../history/2026-10-15-documentation-audit.md).

## Historical context

Local history records integration/PyTorch changes on August 11, forecast changes on August 12, frontend and firmware changes on August 13, and Arduino/Paho changes on August 14, 2026. This is local Git history; remotes were not fetched. Arduino and self-hosted broker files were subsequently removed at the owner's request. The uncommitted Arduino sketch was checksum-verified in an archive outside the repository before deletion. This record does not require a local backup to exist on another machine.

Later decisions should link relevant PRD IDs, state evidence and alternatives, and explain supersession. A decision that changes product scope must update the PRD in the same change.
