# Frontend backend handoff

Updated 2026-10-21. The owner reports that a teammate is building the backend on another branch. This checkout's `rebuild/backend/main.py` provides only `/health`. The following is the **current frontend screen model and an integration proposal**, not an accepted backend specification. Review it against the teammate's OpenAPI and authentication design before enabling release configuration. No teammate branch was changed or messaged.

## Connection and transport

`src/main.jsx` awaits `configureApplicationData()` before mounting. Normal and production execution selects `createBackendClient`; only explicit development mode can import fixtures. `dataSource.js` remains the stable screen facade. If backend payloads differ, map them at the service boundary rather than changing screen layouts or adding biological thresholds.

Public Vite build variables:

| Variable | Meaning |
|---|---|
| `VITE_API_BASE_URL` | Same-origin API base path, ending in `/`. No production default is invented. |
| `VITE_API_ROUTES` | JSON object mapping operation names below to relative URL templates. Scoped operations use `{id}`. No leading slash, origin, query, fragment or traversal. |
| `VITE_ENABLE_SAMPLES` | Development-only opt-in. Ignored for production builds. |

Route entries are supplied from the reviewed backend contract. The client encodes IDs, appends query arguments using URLSearchParams and rejects cross-origin/base-path escapes. Do not put tokens, passwords or secrets in VITE variables: they are public bundle contents.

The selected transport proposal uses **same-origin cookie sessions** behind an HTTPS reverse proxy, no browser token storage, no automatic redirects, no response caching and a 15-second request timeout. Network/timeout failures, 401/403/404/409/429/server errors and incompatible payloads remain explicit. There are no automatic retries of mutations and no fixture fallback. Missing operation configuration is an error, not an empty successful result.

Writes require an `X-CSRF-Token` obtained from `meta[name="csrf-token"]`; the authenticated deployment/bootstrap must supply it. The current static HTML intentionally has no fake token. Server authorization, ownership checks, session establishment/refresh/logout, cookie attributes and CSRF verification still need the backend team's review and implementation. If the teammate chooses a different auth/CSRF mechanism, revise the client together with that reviewed contract. Current 401 handling reports expiry; a complete login flow is not implemented by this transport.

## Operations

| Operation | HTTP method | Arguments / screen expectation |
|---|---|---|
| listTanks | GET | Optional query; returns tank array |
| listDevices | GET | Returns device array |
| getTankSummary | GET | tank ID; returns `{tank, latest_water_log}` |
| getLatestPrediction | GET | tank ID; returns forecast or explicit `null` |
| getPredictionHistory | GET | tank ID; returns forecast array |
| listWaterLogs | GET | tank ID and query (currently limit 48); returns log array |
| getAllLogs | GET | Query (currently limit 100); returns recent log array |
| listAlerts | GET | Returns server-owned alert array |
| createTank | POST | `{name, volume_ml, growth_stage}`; returns saved tank identity |
| updateTank | PUT | tank ID, `{name, volume_ml}`; returns saved tank identity |
| deleteTank | DELETE | tank ID; supports 204 response |
| createWaterLog | POST | tank ID, manual payload below; returns saved log with matching tank ID/time |
| sendCommand | Disabled | No live command writes until acknowledgement, timeout and reported-state semantics are accepted |

Paths are intentionally absent until the teammate supplies them. JSON response arrays are currently unwrapped; pagination envelopes need mapping in the service adapter. Empty arrays/null must mean real empty/unavailable data; API errors must remain non-success responses.

## Screen model

All records have stable string/number IDs. Identity types must be consistent; summary/history/forecast data must belong to the requested tank. Missing relationships are explicit rather than substituted from another resource.

- Tank: `id`, `name`, `volume_ml`, `growth_stage`, `device: {id, connection}`, and nullable `reading`.
- Reading: `observedAt` (ISO timestamp), server-owned `freshness` (`fresh`, `stale`, or unknown), and `metrics.temperature`, `metrics.ph`, `metrics.turbidity`. Each metric has `{state, value, provenance}`. Only `state: valid` and finite numeric values are usable. The frontend does not invent staleness intervals or water quality policy.
- Device: `id`, `tank_id`, `name`, `connection_state` (`online`, `offline`, `unknown`), `is_online`. Unknown must remain unknown even if a legacy boolean is false. No assignment uses another tank's device identity.
- Latest log: nullable; otherwise `id`, `tank_id`, `device_id`, `recorded_at`, nullable numeric `temperature`, `pH`, `turbidity`, `ph_provenance`, `freshness`, `connection`, nullable boolean `relay_on`. Summary values must match valid snapshot metrics, and pH provenance must agree. Invalid/missing metrics are null, not zero. Unknown relay state is null, not OFF.
- History/export log: same log fields, ordered by observation time in the service. Detail also sorts chronologically. Export currently contains up to the 100 loaded rows and advertises that scope; full-history/paginated export remains a backend/UI integration requirement.
- Forecast: `id`, `tank_id`, `created_at`, `predicted_from`, `ph_provenance`; nullable numeric `temperature_1h` through `temperature_4h`, `pH_1h` through `pH_4h`, `turbidity_1h` through `turbidity_4h`; explicit `target_1h` through `target_4h`. The UI uses supplied target times and provenance, not inferred horizons or hardcoded confidence. Only publish qualified forecasts under the accepted model contract.
- Alert: `id`, `tank_id`, `tank` (display name), `type` (`Critical`, `Warning`, `AI Forecast`), `category`, `title`, `message`, `recorded_at`. Colors are selected by the frontend from type, not passed as server CSS. No browser threshold calculations or simulated notification status.

Backend records marked `sample_only: true`, invalid numeric fields and malformed timestamps are rejected. Guards are defensive, not a substitute for full backend schema validation or access control.

Manual entries submit nullable numeric `temperature`, `pH`, `turbidity`, UTC `recorded_at`, `source: manual` and `ph_provenance: manual` (or `unknown` when pH is blank). At least one reading is required. The local datetime input is converted to UTC; timestamps cannot be in the future. pH 0-14 and nonnegative turbidity are input sanity checks, not biological thresholds. The backend must validate and authorize these fields, preserve attribution and publish committed updates. Acknowledged writes reload details instead of claiming persistence from local state.

## Integration acceptance still required

1. Compare these screen models and methods with the teammate's actual API; add explicit payload/pagination mapping as needed.
2. Complete login/logout/session expiry and role/ownership controls with allowed/denied tests. Client-side UI is not authorization.
3. Configure authenticated reads/writes and CSRF, then verify persistence/reload, malformed responses, partial errors, stale/offline/invalid/default/manual pH and cross-tank isolation.
4. Add the approved live-update protocol and reconnect/resume behavior. There is currently no live subscription, polling or automatic reconnect.
5. Connect approved relay results/state semantics; keep the switch disabled until then. Connect real alerts/acknowledgement and qualified forecasts. Full-history paging/filter/export requirements remain unfinished. Review create-operation idempotency and uncertain outcomes after network loss before enabling production writes; the client does not automatically retry mutations.
6. Run browser/keyboard/responsive checks against real data, then the release/deployment rehearsals. Build success or route configuration is not production acceptance.
