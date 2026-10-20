# Bangus BuhAI rebuild frontend

The active UI now reuses all original frontend screens and the original Dashboard / Tanks / Alerts / Data sidebar and mobile bottom navigation. The root `frontend/` is preserved unchanged. Backend-dependent features still use local sample data while integration remains unfinished. Product screens use neutral wording with an Offline workspace indicator; CSV source metadata still identifies fixtures. This is not completion of T16–T18.

## Run and check

From `rebuild/frontend/`:

```sh
npm ci
npm run dev
npm run lint
npm run check:samples
npm run build
```

Dev: `http://127.0.0.1:5174/#/`. Production preview: `npm run preview` on port 4174. Existing server/preview hosts and ports are unchanged. Node v24.15.0 and npm 11.12.1 were used for the recorded checks.

## Restored screens and flows

| Route | Original features retained | Current data/action behavior |
|---|---|---|
| `#/` | Dashboard, primary tank/device, parameter cards, forecast summary, tank links | Fictional readings, explicit pH provenance and sample availability |
| `#/tanks` | Device hero, tank list/status, New Tank dialog | Create a sample tank in memory |
| `#/tanks/:id` | Tank/device readings, settings, edit/delete, relay switch, four forecast horizons, prediction history dialog, historical chart and parameter controls | Local sample edits/deletion and relay-state preview; fictional forecast/history values; no backend requests or relay commands |
| `#/alerts` | Critical / Warning / Forecast counts and alert cards | Supplied fictional alerts; no frontend numerical quality evaluation or notifications |
| `#/data` | Recent telemetry table and CSV export | Up to 100 fictional logs; downloadable CSV labelled SAMPLE ONLY, with pH provenance and exact UTC times |

The bell opens Alerts; the menu opens navigation. Dialogs support labels, focus cycling, Escape, and return focus to the trigger. Sample relay preview is unavailable for offline/stale/missing temperature. Default/estimated pH is not presented as measured pH. Missing/invalid values do not become valid zeros. Empty chart parameters show an explanatory state.

## Source map and design basis

- [src/App.jsx](src/App.jsx) mounts the original routes with lazy page loading and the preview controls; [src/main.jsx](src/main.jsx) uses HashRouter so existing `#/tanks/nursery-01` links remain valid.
- [src/original/](src/original/) contains copies of the root frontend's pages, components, assets, and styles, adapted for the sample boundary and minor accessibility/data-display improvements. The original four-destination navigation and feature layouts are retained directly.
- [src/data/originalFixtures.js](src/data/originalFixtures.js) owns additional fictional history, forecast, and alert data, based on [sampleData.js](src/data/sampleData.js).
- [src/services/configureApplicationData.js](src/services/configureApplicationData.js) configures the provider before React mounts. [dataSource.js](src/services/dataSource.js) exposes a stable facade; the compatibility client re-exports it. Samples live in [src/data/sampleClient.js](src/data/sampleClient.js). See [INTEGRATION.md](INTEGRATION.md) for the connection point, current interface and remaining integration requirements; no backend routes or accepted contracts are invented.
- [CSV formatting](src/original/api/exportCsv.js) preserves zero, quotes fields, and includes provenance/source metadata. [Regression checks](scripts/sample-adapter.test.mjs) cover invalid/zero handling, forecast eligibility/times, reversible sample mutations/identity, and CSV quoting.
- Earlier preparation components/pages/styles under `src/components/`, `src/pages/`, `src/App.css`, `src/index.css`, and selected assets remain preserved; the active screens/styles are in `src/original/`. The active compact controls use `PreviewToolbar`; earlier preparation files are retained.

React/JavaScript/Vite remain in use. The owner approved the original UI libraries: React Router DOM 7.18.4 (patched from the original 7.18.1), Recharts 3.10.1, Tailwind CSS and its Vite plugin 4.3.3. The library install reports zero audit vulnerabilities. The Inter font stack uses system fallbacks and makes no external font requests.

## Sample controls and limits

Developer scenario controls are hidden on normal routes. Open `http://127.0.0.1:5174/#/tanks/nursery-01?tools=1` and expand **Display states** for mixed, loading, empty, error, offline, stale, invalid, or missing data. Loading is deliberately paused. **Reset workspace** resets local tank changes and the scenario; reload also resets changes. No database/device data is changed. Scenario changes remount the original screens to demonstrate their loading/empty/error states. A fixed 20 October 2026, 09:30 SGT sample clock makes state review reproducible.

Forecasts and history are fictional illustrations, not model output, calibration, physical pH measurement, or validated forecast evidence. No numerical biological limits or water-quality evaluation algorithm were copied from the prototype. Alert examples and display-availability checks do not establish a production policy. Real authentication, authorization, APIs/MQTT, relay commands, inference, durable alerting/notifications, and full integration remain unfinished. Manual water-log entry is still required by the PRD and absent from the original UI.

Progress, verification evidence, uncommitted files, and the next integration step are recorded in the [frontend handoff](../../docs/status/tasks/frontend-T16-T18-preparation.md). T07 remains the firmware collaborator's active task; T16–T18 remain incomplete.

## Integration preparation (2026-10-20)

Verbose fresh-sample/clock explanation panels are removed. A compact sample badge and collapsed preview controls remain; exceptional reading states use short text. Default/estimated pH labels remain beside values. The provider boundary validates required operations and normalizes errors without silently substituting fixtures. Backend mode hides sample controls and disables relay commands. Seven regression checks cover the sample adapter and provider boundary. This is preparation only: real authentication, transport, accepted payload mapping and full T16–T18 integration remain unfinished.

## Product wording (2026-10-20)

At the collaborator’s request, active screen titles, buttons, dialogs, alerts and accessible labels no longer repeat sample/demo/preview explanations. The small Offline workspace indicator remains while the sample provider is selected, alongside default/estimated pH labels and disconnected relay wording. The export filename is bangus_logs.csv; its source column still identifies SAMPLE ONLY records. Internal fixture names/metadata and developer documentation remain explicit. Commercial wording does not establish validated forecasting, real controls, persistent CRUD or production readiness. No dependency or backend changes.
