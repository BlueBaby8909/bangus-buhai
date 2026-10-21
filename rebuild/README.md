# Rebuild workspace

T01 provides a separate FastAPI backend, React/Vite frontend and firmware starting-point area. The backend in this checkout currently serves only a health response. The frontend now preserves the original React screens with a backend adapter and production fixture exclusion; see [frontend setup](frontend/README.md), [integration handoff](frontend/INTEGRATION.md) and [deployment preparation](frontend/DEPLOYMENT.md). Live application integration remains unfinished.

The existing prototype remains in the repository's top-level `backend/`, `frontend/` and `firmware/` directories. All commands below target `rebuild/`. T02 adds the [offline shared device contracts](contracts/README.md), independently of the application shells.

## Prerequisites and tested versions

Verified on Windows on 2026-10-16:

| Tool | Tested version |
|---|---|
| Python | 3.14.6 |
| Node.js | v24.13.1 |
| npm | 11.8.0 |

Use CMD in the VS Code terminal. Python's `py` launcher, Node and npm must be available. Check their versions with:

```cmd
py -3.14 --version
node --version
npm --version
```

These are the tested versions, not a guarantee about other versions. The frontend lockfile resolves Vite 8.3.4 and declares Node `^20.19.0 || >=22.12.0`.

Commands assume this checkout is at `C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai`. If you move it, replace that prefix while retaining the `rebuild` directory in each path.

## First-time setup

Create the backend environment when `rebuild/backend/.venv` does not already exist:

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\backend"
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.venv\Scripts\python.exe -m pip check
```

The commands use the environment's interpreter directly, so activation is unnecessary. Preserve an existing environment; routine startup does not require recreating or reinstalling it.

Install the frontend from its lockfile:

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\frontend"
npm ci
```

`npm ci` recreates this frontend's dependencies from `package-lock.json`. Stop its running development server with Ctrl+C first so Windows can release native dependency files. Package installation requires access to a package registry or a suitable local cache; offline installation has not been verified.

## Normal startup

In one CMD terminal:

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\backend"
run.cmd
```

In a second CMD terminal:

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild\frontend"
npm run dev
```

Open the [backend health endpoint](http://127.0.0.1:8001/health) and [frontend](http://127.0.0.1:5174/). Expected backend response:

```json
{"status":"ok","service":"bangus-buhai-rebuild"}
```

The frontend renders Dashboard/Tanks/Alerts/Data navigation. Without reviewed API configuration, data pages report service unavailability rather than showing fictional records. See [frontend setup](frontend/README.md) for the explicit development-only sample mode. Stop a server with Ctrl+C in its terminal. No dependency installation or clean-install check is needed for normal daily startup.

## Automated checks

After completing first-time setup, run in CMD:

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild"
check.cmd
```

This runs Python dependency checks, contract tests, fixture/schema checks,
a backend import/health-function check, frontend lint and frontend build.

Exit code 0 means all checks passed. Exit code 1 means a check failed;
the script names the failed step and stops.

The backend smoke check does not test HTTP requests or live integrations.

The [GitHub workflow](../.github/workflows/rebuild-checks.yml) installs
the recorded dependencies and runs the same script automatically.

## Checks and frontend build

From `rebuild/backend/`, check dependency consistency:

```cmd
.venv\Scripts\python.exe -m pip check
```

From `rebuild/frontend/`, run:

```cmd
npm run lint
npm run build
```

Both should exit successfully. The build writes ignored output to `rebuild/frontend/dist/`. For an optional local preview of that output, run `npm run preview` and open [port 4174](http://127.0.0.1:4174/). Preview settings were source-reviewed; the preview server was not exercised during T01.

The health response checks that the minimal app starts; it does not certify database, MQTT, model or hardware readiness. There is no backend API or device integration suite in this scaffold. T02's offline contract checks run from `rebuild/`:

```cmd
backend\.venv\Scripts\python.exe -m unittest discover -s contracts\tests -v
backend\.venv\Scripts\python.exe -m contracts check
```

These checks do not start the app or contact a broker/database. See [contract usage and limits](contracts/README.md). T03 now automates these checks through `check.cmd` and GitHub Actions. Deployment and live integration remain unverified.

## Optional clean-install checkpoint

Use this when checking dependency reproducibility, rather than for every development session. The successful T01 check used a separate environment at `rebuild/.venv`, preserving `rebuild/backend/.venv`.

The following recipe assumes `rebuild/.venv` does not exist and the normal backend environment has already been prepared:

```cmd
cd /d "C:\Users\Kent Christian\Documents\BangusBuhai\bangus-buhai\rebuild"
backend\.venv\Scripts\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8002
```

Check [the temporary backend health endpoint](http://127.0.0.1:8002/health), then stop that server with Ctrl+C. Port 8002 lets the normal backend on 8001 remain running. The verification environment is ignored by Git and was retained after T01. Reusing it later checks consistency but is no longer a fresh-environment recreation.

For the frontend, stop its development server, run `npm ci`, then lint/build and restart with the commands above. Verify the page in a browser.

## Configuration and preservation

| Area | Configuration source | T01 setting |
|---|---|---|
| Backend | [backend/run.cmd](backend/run.cmd) | Own working directory and `.venv`; bind `127.0.0.1:8001` |
| Frontend development | [frontend/vite.config.js](frontend/vite.config.js), `server` | Bind `127.0.0.1:5174`; `strictPort: true` |
| Frontend preview | [frontend/vite.config.js](frontend/vite.config.js), `preview` | Bind `127.0.0.1:4174`; `strictPort: true` |
| Backend packages | [backend/requirements.lock.txt](backend/requirements.lock.txt) | Install the recorded exact versions |
| Frontend packages | [frontend/package-lock.json](frontend/package-lock.json) | Install with `npm ci` |

These files are the supported configuration examples for this shell. The backend does not load `.env` files. Vite supports frontend `.env` files; current public build variables and their limits are documented in [the frontend integration handoff](frontend/INTEGRATION.md). No `.env` file, database URL or broker credentials are required for T01.

The frontend fails if its configured port is occupied instead of silently moving to another port. The backend also reports a bind failure on an occupied port. Stop the relevant rebuild server before restarting; leave prototype processes alone. The temporary backend check uses an explicit alternate port.

No current rebuild code connects to a database or MQTT broker, loads model artifacts, reads prototype credentials, migrates data or flashes a device. Keep the prototype's environments, database, certificates, model artifacts and local firmware configuration preserved. Git ignores the Python environments and generated frontend dependencies/build output; keep both dependency lockfiles with the rebuild source.

## Firmware and verification limits

Read [firmware/README.md](firmware/README.md) for the ESP-IDF starting point. ESP32-S3 and ESP-IDF 6.0.2 are recorded source baselines, not a verified toolchain/device result. T01 supplies the firmware area and boundary notes only. T04 owns firmware build compatibility and the necessary hardware-context verification; no build, flash, calibration or device behavior is claimed here.

The [T01 record](../docs/status/tasks/T01.md) owns dated evidence. AI-run locked dependency installs, `pip check`, frontend lint/build, a backend health request in the separate environment on port 8002, and browser rendering on port 5174 passed on the versions above. The normal backend launcher was source-reviewed. Existing wheel/npm caches were reused on this machine; a fresh checkout on another machine, an empty-cache install, frontend/backend data integration and production deployment have not been verified.
