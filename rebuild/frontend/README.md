# Bangus BuhAI frontend

The rebuild preserves the root frontend's Dashboard, Tanks, tank details, Alerts, Data, assets, sidebar and mobile navigation. Active code now uses one conventional source tree. Backend mode is the default; production bundles exclude fictional fixtures and developer controls.

This is frontend integration preparation, **not a production release certification**. The backend in this checkout implements only `/health`; the owner reports that a teammate is implementing application APIs on another branch. No existing prototype API is selected automatically. Read [INTEGRATION.md](INTEGRATION.md) before configuring routes and [DEPLOYMENT.md](DEPLOYMENT.md) before publishing.

## Source map

- `src/App.jsx`, `src/main.jsx`: hash routing, lazy pages, navigation focus, error boundaries and application configuration.
- `src/pages/`: Dashboard, Tanks, TankDetail, Alerts and DataExport.
- `src/components/`: navigation, shared metric/forecast/status/error components, tank/settings/history dialogs and manual reading entry.
- `src/styles/global.css`, `src/assets/`: original Tailwind design and identical original image/icon copies, plus accessibility/responsive rules. Inter is loaded using the root frontend's Google Fonts approach, with system fallbacks.
- `src/services/`: configured data facade, bounded same-origin HTTP client, request lifecycle gate and manual entry validation.
- `src/api/`: screen compatibility import and CSV serialization.
- `src/data/`, `src/development/`: opt-in development fixtures and scenario controls. Never selected by a production build.
- `archive/preparation/`: preserved earlier unused UI implementation and starter assets. Historical reference only; not mounted, linted or imported into the app.
- `scripts/`: regression, component rendering, configuration and distribution checks.

## Development and verification

From `rebuild/frontend`:

```sh
npm ci
npm run dev
npm run lint
npm test
npm run build
npm run check:dist
```

Development binds to `127.0.0.1:5174`; production preview uses `4174`. Hash routing retains links such as `/#/tanks/nursery-01` and needs no server-side route fallback. Do not open `index.html` directly: Vite builds the React/Tailwind assets.

With no reviewed backend configuration, pages show a service-unavailable state and retry controls. They do not fabricate tanks, readings, alerts, forecasts, account names or successful writes. Missing device/relay state stays unknown. Manual readings are available from tank details; saving requires a configured authenticated service. Live relay commands stay disabled pending an accepted acknowledgement/observed-state contract.

For isolated development UI inspection, set `VITE_ENABLE_SAMPLES=true` in the shell **before** starting Vite (PowerShell: `$env:VITE_ENABLE_SAMPLES = 'true'`). The header explicitly identifies development samples; append `?tools=1` inside the hash route to expose state controls. This switch has no effect on production builds. Fixtures do not implement successful manual entry saves. They are not model, biological, hardware or integration evidence.

## Checks and limits

`npm test` checks transport errors/timeouts, request races, identity and data guards, manual reading payloads, CSV safety, fixtures/provider behavior and server rendering of actual production-transformed components. `check:dist` rejects known fixture/control markers and missing representative Tailwind design utilities. These are bounded checks, not browser, accessibility, authentication or end-to-end acceptance.

`npm run build:release` requires all configured screen operation routes before building. It validates configuration structure only; it cannot certify a backend that has not been integrated. See the [frontend task record](../../docs/status/tasks/frontend-T16-T18-preparation.md) for actual results and outstanding release requirements. T16-T18 remain incomplete.
