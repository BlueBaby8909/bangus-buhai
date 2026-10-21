# Frontend deployment preparation

The output is a static Vite application using hash routing. This repository has not been deployed by this change. Authentication, real APIs/live updates and release acceptance remain blocked on backend integration; see [INTEGRATION.md](INTEGRATION.md).

## Build and serve

1. Use the committed package lock (`npm ci`). This change added no dependencies. Checks were run with Node 24.19.0, npm 11.17.0 and the existing Vite 8.3.4 installation; a fresh install was not repeated.
2. Configure public `VITE_API_BASE_URL` and `VITE_API_ROUTES` from the reviewed backend contract at build time. Vite values are embedded, not dynamically supplied by the static host. Never include credentials. Changing the API configuration requires rebuilding.
3. Run `npm run lint`, `npm test`, then `npm run build:release`. Missing route configuration must stop the release build. Ordinary `npm run build` remains available for structural/UI verification without pretending the backend is connected.
4. Publish the contents of `dist/` to a static host at the origin root. Keep application files and `/api/` on the same public HTTPS origin. Configure the reviewed backend upstream and session/CSRF bootstrap at the hosting boundary.
5. Serve HTML with revalidation/no-cache to avoid stale chunk references. Serve unknown API routes as non-success errors, never the app's HTML. Retain previous versioned assets during rollout so already-open tabs can finish loading their chunks. Keep a previous build for rollback.
6. Open dashboard and each hash route directly, reload them, exercise backend success/401/403/unavailable states and verify caching/security headers from the deployed endpoint before release.

`deployment/nginx.conf` is an optional conservative static-serving configuration on port 8080. It sends CSP, MIME, referrer and permissions headers; caches are revalidated. `/api/` intentionally returns 503 until the backend upstream and authentication are configured. It is not a working backend proxy or a complete production deployment. Put it behind the chosen TLS terminator; do not expose port 8080 as an authenticated public production origin. Nginx syntax/runtime were not tested here because Nginx is not installed in this workspace.

The CSP allows same-origin connections/scripts/assets and the Google Fonts domains used by the root frontend. Inline styles remain allowed because the existing React/Recharts design uses them. Review this policy when changing fonts, charts, auth redirects or the approved streaming protocol. Do not weaken the policy just to hide an integration error. Inter has system-font fallbacks; an environment that blocks external fonts needs a licensed self-hosted font asset for exact typography.

## Checks and boundaries

- `npm run check:dist`: checks production JS for known fixture/control markers and CSS for representative original-design utilities. Even `VITE_ENABLE_SAMPLES=true` cannot select fixtures in a production build.
- `npm run build:release`: route configuration gate plus build/distribution checks. It does not test API reachability, session/permission behavior or backend compatibility.
- Browser/responsive/a11y tests, real backend integration, login, live recovery, complete history export, relay command semantics and deployment rehearsal remain release work. This frontend is hardened for integration, not certified production-ready.

No cloud resources, DNS, certificates, backend/firmware, credentials, prototype files or Git publication were changed.
