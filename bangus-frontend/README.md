# Bangus Buhai — Frontend

React + Vite frontend for the Bangus Buhai pond/tank monitoring app. Pairs
with the `backend/` FastAPI service (see the backend repo's README).

## Setup

```bash
npm install
cp .env.example .env   # edit VITE_API_URL if your backend isn't on localhost:8000
npm run dev
```

Runs at `http://localhost:5173` by default. Make sure the backend's
`CORS_ORIGINS` includes that origin (it does by default — see
`backend/config.py`).

```bash
npm run build     # production build -> dist/
npm run preview   # serve the production build locally
```

## Structure

```
src/
  api/client.js        fetch wrapper for every backend endpoint
  lib/waterQuality.js   client-side mirror of backend water-quality thresholds (display only)
  components/           GaugeRing, RangeGauge, StatusBadge, Sidebar, Modal, forms, TankCard
  pages/                Dashboard, TankDetail, Users
  styles/               tokens.css (design system), global.css, components.css
```

## Pages

- **Dashboard (`/`)** — grid of tanks with a live status gauge per card, and a
  form to add a new tank.
- **Tank detail (`/tanks/:id`)** — latest reading plotted on range gauges
  (temperature / pH / turbidity, with the optimal band shaded), latest
  feeding, and tabbed history for water logs and feedings. Lets you log new
  readings/feedings or delete the tank.
- **Growers (`/users`)** — list/add/remove users who tanks can be assigned to.

## Design notes

Palette and type are themed around a brackish milkfish pond rather than a
generic dashboard look — deep teal sidebar, sage-paper background, clay/mud
accent, moss-green/mud-gold/rust status colors. All numeric readouts use a
monospace face to read like a logbook. The gauge-ring/range-gauge motif on
cards and the tank-detail page is the app's one recurring signature element,
modeled on the analog dial gauges used pond-side.

Design tokens live in `src/styles/tokens.css` if you want to retheme.
