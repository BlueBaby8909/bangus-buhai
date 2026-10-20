# Frontend integration handoff

The frontend currently runs in **sample mode**. The rebuild backend currently exposes only `/health`; tank, identity, telemetry, forecast and alert contracts are not implemented. This preparation does not complete T16–T18.

## Connection point

`src/main.jsx` calls `configureApplicationData()` before rendering React. Change `src/services/configureApplicationData.js` when a reviewed backend adapter exists:

```js
configureDataSource({ mode: 'backend', provider: backendAdapter })
```

The adapter must implement the operations in `src/services/createDataClient.js`. Those names describe existing frontend calls, **not HTTP routes or accepted backend contracts**. Map reviewed backend responses to the screen model there. Keep sample imports in sample configuration; never return samples after a backend request fails. Backend mode hides the Offline workspace indicator and developer state toolbar, and disables the local relay control. The developer toolbar is available only with `?tools=1` inside the hash route.

| Frontend operations | Purpose |
| --- | --- |
| listTanks, listDevices, getTankSummary | Tank list, device identity/connectivity and latest readings |
| listWaterLogs, getAllLogs | Tank history and recent export rows |
| getLatestPrediction, getPredictionHistory | Forecast and historical forecast displays |
| listAlerts | Server supplied alert records |
| createTank, updateTank, deleteTank | Tank management, subject to reviewed authorization |
| sendCommand | Local preview compatibility only; live relay controls remain disabled |

All methods are asynchronous. Errors retain `message`, `status` and `code` through `DataClientError`. For unavailable operations, reject explicitly; do not fabricate successful responses. Configure the source once before mount; runtime switching and live subscriptions are not implemented.

## Before enabling backend mode

1. Agree on authentication, authorization, tank/device identities, pagination and error semantics with the backend collaborator. No token storage or transport policy is established here.
2. Review the actual response schemas. Existing `tank.reading`, `latest_water_log`, metric validity, freshness, timestamps, connection and pH provenance fields are provisional screen models. Convert non-finite/invalid values to unavailable values while preserving valid zero. Missing device identity must remain unknown.
3. Obtain freshness, evaluation and alert policy from accepted backend/product contracts. Do not add frontend biological thresholds. Preserve default/estimated pH labels; only explicit measured provenance may say measured.
4. Product wording is already neutral. Review the Offline workspace indicator, disconnected relay copy, forecast provenance and actual feature availability alongside each integration. The current sample UI does not establish live forecasting, relay acknowledgement or notification behavior. Review partial request failures in detail/history and forecast views; these currently use unavailable states.
5. Add transport cancellation, bounded timeouts, authentication/error recovery and request lifecycle checks with the real adapter. No polling, MQTT, reconnect policy or backend URL has been guessed here.
6. Verify against the real service: empty/loading/error, stale/offline/invalid readings, identity changes, permissions, CRUD persistence, history/export and provenance. Validate CSV source labels (`sample_only` must be explicit for fixtures). Run lint, sample/provider regression checks and build, plus browser/keyboard/responsive checks.

Sample fixtures and local mutations live in `src/data/sampleClient.js` and `src/data/originalFixtures.js`. Display components access the stable `api` facade via `src/original/api/client.js`; they no longer own the sample provider.
