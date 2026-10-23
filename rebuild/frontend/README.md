# Bangus BuhAI operator interface (T16–T18)

Uses the original prototype as the visual baseline inside rebuild. Actual copied
navigation/header/dashboard/Tanks/Alerts markup lives in `src/prototype/`, adapted
to the protected backend and all T16–T18 features. Exact Tailwind4.3.3 and its Vite
plugin match the original tooling. Feature styles use a single component layer;
prototype utilities take priority. Original `frontend/` remains untouched; its22
artwork/icon assets are unchanged. The prior accumulated redesign is superseded.
Keep this baseline when adding features. Devices is managed inside Tanks.

## Run locally

From `rebuild/frontend`, use `npm ci` for a fresh install, then `npm run dev`.
Check existing listeners first. Vite binds only `127.0.0.1:5174` with strict port
selection and proxies `/api` and WebSockets to the existing API on8001. Use
<http://127.0.0.1:5174/> and the existing owner-provisioned operator account.
No frontend secret/configuration file is needed. Do not start another MQTT worker.
`BB_API_PROXY_TARGET` exists for isolated test routing; normal default remains8001.

The API's existing allowed Origin must include the frontend origin. The current
local configuration already permits5174 and was preserved. Production hosting,
HTTPS/WSS/reverse-proxy setup remains T24. `npm run preview` is not the configured
authenticated local workflow; use the dev command above.

## Implemented flows

- Cookie login/logout and restoration, protected screens, hatchery selection,
  access-loss handling, and in-memory auth/CSRF. No provider/password storage.
- Dashboard/tanks, explicit device selection, latest delivered readings, server
  clock alignment, provenance, missing/default/invalid/stale/unknown time states.
- One live stream for the selected overview or tank detail, stable cursor replay, deduplication, reconnect
  and resync. Recent chart window holds at most500 received observations; unknown
  capture times are not plotted. Manual points remain separate from devices.
- Device claims and actual proof/confirmation stages, cancellation/expiry, naming,
  versioned tank/device archival/restoration and assignments. Claim codes clear
  after submission; the browser never performs the device's signing proof.
- Snapshot history filters/pagination, measured partial manual entries, audited
  correction/void/restore/revision inspection and CSV export. History is stable
  until refreshed; CSV creates its own fresh snapshot of the selected filters.
- Explicit ON/OFF/AUTO controls, same-key uncertain retries, pending status recovered
  after reload, and distinct applied/rejected/failed/uncertain results. Telemetry
  GPIO and command-specific confirmation remain separate; no contact readback.

Readings are not quality classifications. Forecast/alert/quality sections say
unavailable until T19–T23. Device broker connectivity is explicitly unknown;
last telemetry and assignment confirmation are evidence, not online/offline proof.
Do not infer a healthy device from a working browser WebSocket.

Background status/session requests use `X-BB-Passive: 1`; automatic traffic does
not extend the30-minute inactivity deadline. Hatchery/access changes unmount
private state and sockets. Header details and read APIs are documented in the
[readings guide](../backend/features/readings/README.md).

## Verification

- `npm run lint`: Oxlint, clean on the implemented source.
- `npm test`:14 Vitest/React Testing Library tests.
- `npm run build`: production bundle; chart module loads separately.
- `npm run test:styles`: builds and reviews the production UI at360/768/1440
  using Edge with every HTTP/WebSocket response intercepted. No API, database,
  Vite server, provider login or hardware is used. Covers feature dialogs,
  history/revisions, claim progress, relay confirmation, CSS cascade, viewport
  bounds and Escape/focus return. Screenshots go to ignored `.verification`.
- `npm run test:e2e`: six Playwright scenarios using the dedicated test database,
  disposable PostgreSQL schema, generated auth keys, simulated device proofs and
  results. No real MQTT/device is involved. Tests use separate loopback8019/5189.
  They refuse existing test servers and shut down/clean the schema afterwards.
  Windows uses the already installed Edge browser.
  The current config/launcher is verified on Windows, not hosted CI.

The browser suite covers login/access/logout/reload, hatchery switching, live
reconnect replay, manual lifecycle/CSV, command results, device claim confirmation,
keyboard focus/Escape, expiry, and screenshots at360/768/1440. Screenshots/traces
and logs live in ignored `rebuild/.verification/`. Full rebuild checks include
frontend unit/component tests; browser tests stay an explicit isolated command.

[T16](../../docs/status/tasks/T16.md), [T17](../../docs/status/tasks/T17.md) and
[T18](../../docs/status/tasks/T18.md) record actual evidence and limits.
