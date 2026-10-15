# Bangus Buhai frontend

React 19 + Vite 8 single-page application with React Router, Recharts, and Tailwind CSS. Dependency ranges are declared in [package.json](package.json), with installed versions resolved through the lockfile.

- [Product requirements](../docs/PRD.md)
- [Run/build/configuration instructions](../docs/operations/development.md#frontend)
- [Architecture](../docs/reference/architecture.md)
- [Current integration limitations](../docs/status/implementation.md#s06-browser-interface)

## Current pages

| Path | Source | Existing responsibility |
|---|---|---|
| `/` | [Dashboard](src/pages/Dashboard.jsx) | First-tank overview and per-tank socket updates |
| `/tanks` | [Tanks](src/pages/Tanks.jsx) | Tank list and creation modal |
| `/tanks/:id` | [TankDetail](src/pages/TankDetail.jsx) | Readings, charts, forecasts/history, relay toggle, editing/deletion |
| `/alerts` | [Alerts](src/pages/Alerts.jsx) | On-load alert summaries from devices/readings/forecasts |
| `/data` | [DataExport](src/pages/DataExport.jsx) | Loaded water-log table and bounded CSV export |

[App.jsx](src/App.jsx) defines routing. [api/client.js](src/api/client.js) wraps REST calls and constructs socket URLs. [global.css](src/styles/global.css) imports Tailwind and defines the current theme. Components use local React state; the source has no central state store.

The old Users/feeding UI, old gauge/sidebar components, token/component stylesheets, and unused `lib/waterQuality.js` are not part of the current source. Manual water-log entry and estimated-pH presentation remain product gaps. Some device matching and thresholds are incorrect; charts/relay/forecast UI existing does not prove their integrations are correct. See the status assessment rather than treating this route map as feature acceptance.
