import { useEffect, useState, lazy, Suspense } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useParams,
  Navigate,
} from "react-router-dom";
import { AuthProvider } from "./auth";
import { useAuth } from "./auth-context";
import { request, query, hatcheryPath } from "./api";
import {
  ActionForm,
  Field,
  ErrorBox,
  Empty,
  Badge,
  Future,
  MetricStrip,
  Modal,
} from "./components";
import { TankEditor, DeviceEditor, ClaimDevice } from "./management";
import RelayControl from "./RelayControl";
import History from "./History";
import { useTankStream } from "./useTankStream";
import { chartRows } from "./readings";
import deviceArt from "./prototype-assets/Tanks/Device (Angled).png";
import frontArt from "./prototype-assets/Tanks/Device (Front).png";
import AlertsPage from "./prototype/Alerts";
import AppHeader from "./AppHeader";
import PrototypeNav from "./prototype/BottomNav";
import Dashboard from "./prototype/Dashboard";
import PrototypeTanks from "./prototype/Tanks";
const TrendChart = lazy(() => import("./TrendChart"));

function Login() {
  const { login, notice } = useAuth();
  return (
    <main className="login">
      <section className="login-brand">
        <Link className="wordmark" to="/">
          Bangus <strong>BuhAI</strong>
          <span className="brand-dot" />
        </Link>
        <p className="eyebrow">Milkfish hatchery monitoring</p>
        <h1>
          Your hatchery,
          <br />
          in view.
        </h1>
        <p>View your tanks, follow readings and manage your devices.</p>
        <img src={deviceArt} alt="Bangus BuhAI monitoring device" />
      </section>
      <section className="login-form">
        <div>
          <h2>Welcome back</h2>
          <p className="muted">Sign in to your hatchery workspace.</p>
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          <ActionForm
            label="Sign in"
            onSubmit={(v) => login(v.email, v.password)}
          >
            <Field
              label="Email"
              name="email"
              type="email"
              autoComplete="username"
              required
              autoFocus
            />
            <Field
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </ActionForm>
          <p className="muted">
            Need an account or password reset? Contact the hatchery owner.
          </p>
        </div>
      </section>
    </main>
  );
}
function useOverview(hatchery) {
  const [data, setData] = useState({ items: [], next_cursor: null }),
    [error, setError] = useState(null),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0),
    [archived, setArchived] = useState(false);
  const base = hatcheryPath(hatchery, "/tank-summaries");
  useEffect(() => {
    const abort = new AbortController();
    request(base + "?" + query({ include_archived: archived }), {
      signal: abort.signal,
    })
      .then((page) =>
        setData({
          ...page,
          serverOffset: Date.parse(page.server_time) - Date.now(),
        }),
      )
      .catch((e) => {
        if (e.name !== "AbortError") setError(e);
      })
      .finally(() => {
        if (!abort.signal.aborted) setLoading(false);
      });
    return () => abort.abort();
  }, [base, revision, archived]);
  async function more() {
    setLoading(true);
    try {
      const page = await request(
        base +
          "?" +
          query({ cursor: data.next_cursor, include_archived: archived }),
      );
      setData((d) => ({ ...d, ...page, items: [...d.items, ...page.items] }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }
  return {
    data,
    error,
    loading,
    refresh: () => {
      setLoading(true);
      setError(null);
      setRevision((n) => n + 1);
    },
    archived,
    setArchived: (value) => {
      setData({ items: [], next_cursor: null });
      setLoading(true);
      setArchived(value);
    },
    more,
  };
}
function Tanks({ overview, onEdit, onClaim, onDevice }) {
  return (
    <PrototypeTanks
      overview={overview}
      onEdit={onEdit}
      onClaim={onClaim}
      recovery={
        <details className="device-recovery">
          <summary>Unassigned and archived devices</summary>
          <DeviceRecovery overview={overview} onDevice={onDevice} />
        </details>
      }
    />
  );
}
function TankDetail({ overview, onEdit, onDevice }) {
  const { id } = useParams(),
    { hatchery } = useAuth();
  const [metadata, setMetadata] = useState(null),
    [error, setError] = useState(null),
    [deviceId, setDeviceId] = useState(""),
    [metric, setMetric] = useState("temperature"),
    [directDevices, setDirectDevices] = useState([]);
  const base = hatcheryPath(hatchery, `/tanks/${id}`),
    stream = useTankStream(hatchery, id);
  useEffect(() => {
    const abort = new AbortController();
    request(base, { signal: abort.signal, passive: true })
      .then(setMetadata)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e);
      });
    return () => abort.abort();
  }, [base, overview.data]);
  const item = overview.data.items.find((i) => i.tank.id === id);
  useEffect(() => {
    if (item) return;
    const abort = new AbortController();
    let stopped = false;
    async function load() {
      let cursor = null,
        devices = [];
      do {
        const page = await request(
          hatcheryPath(
            hatchery,
            "/tank-summaries?" +
              query({ cursor, limit: 100, include_archived: true }),
          ),
          { signal: abort.signal, passive: true },
        );
        const found = page.items.find((i) => i.tank.id === id);
        if (found) {
          devices = found.devices;
          break;
        }
        cursor = page.next_cursor;
      } while (cursor && !stopped);
      if (!stopped) setDirectDevices(devices);
    }
    load().catch((e) => {
      if (e.name !== "AbortError") setError(e);
    });
    return () => {
      stopped = true;
      abort.abort();
    };
  }, [hatchery, id, item]);
  const devices = item?.devices || directDevices,
    device = devices.find((d) => d.device_id === deviceId) || devices[0];
  const reading =
    stream.rows.find(
      (r) =>
        r.origin === "device" &&
        r.device_id === device?.device_id &&
        r.binding_id === device?.binding?.id,
    ) || device?.latest;
  const chart = chartRows(stream.rows, device?.device_id, metric);
  if (error) return <ErrorBox error={error} />;
  if (!metadata) return <p role="status">Loading tank…</p>;
  return (
    <>
      <div className="page-title">
        <div>
          <h1>{metadata.name}</h1>
          <p>Readings and controls for this tank.</p>
        </div>
        <button onClick={() => onEdit(metadata)}>Edit tank</button>
      </div>
      <div className="tank-status-bar">
        <Badge>{stream.status}</Badge>
        <Badge>{metadata.archived_at ? "Archived" : "Active tank"}</Badge>
        <button onClick={overview.refresh}>Refresh device details</button>
      </div>
      {devices.length ? (
        <>
          <label className="device-picker">
            Viewing device
            <select
              value={device?.device_id || ""}
              onChange={(e) => setDeviceId(e.target.value)}
            >
              {devices.map((d) => (
                <option key={d.id} value={d.device_id}>
                  {d.display_name || d.device_id}
                </option>
              ))}
            </select>
          </label>
          <section className="tank-device-bar">
            <div className="device-summary">
              <img src={frontArt} alt="Monitoring device" />
              <div className="device-identity">
                <h2>{device.display_name || device.device_id}</h2>
                <p className="mono">{device.device_id}</p>
                <p className="muted">Device connectivity unknown</p>
              </div>
              <Badge>
                Assignment {device.configuration?.status || "unknown"}
              </Badge>
              <button onClick={() => onDevice(device)}>Manage device</button>
            </div>
          </section>
          <div className="tank-live-grid">
            <section className="detail-readings" aria-label="Current readings">
              <h2>Current readings</h2>
              <MetricStrip
                reading={reading}
                serverOffset={overview.data.serverOffset || 0}
                tiles
              />
            </section>
            <div className="tank-control-column">
              <RelayControl
                key={device.device_id + device.binding?.id}
                hatchery={hatchery}
                device={device}
                reading={reading}
              />
              <div className="forecast-placeholder">
                <Future title="Tank forecast">
                  Forecasts are not available yet.
                </Future>
              </div>
            </div>
          </div>
        </>
      ) : (
        <Empty>
          No device assigned. Open Tanks to add a device or assign an existing
          one. Retained history remains available below.
        </Empty>
      )}
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Recent received observations · up to 500</p>
            <h2>Measurement trends</h2>
          </div>
          <div className="metric-switch" role="group" aria-label="Chart metric">
            {[
              ["temperature", "Temperature"],
              ["ph", "pH"],
              ["turbidity", "Turbidity"],
            ].map(([value, label]) => (
              <button
                key={value}
                aria-pressed={metric === value}
                onClick={() => setMetric(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <p className="muted">
          Selected device only; manual entries are separate points. Unknown
          capture times are excluded. Open history for older observations.
        </p>
        {chart.length ? (
          <div
            className="chart"
            role="img"
            aria-label={`${metric} history for selected device, with separate manual measurements`}
          >
            <Suspense fallback={<p role="status">Loading chart…</p>}>
              <TrendChart chart={chart} />
            </Suspense>
          </div>
        ) : (
          <Empty>No timestamped observations to chart.</Empty>
        )}
      </section>
      <History
        hatchery={hatchery}
        tank={id}
        archived={!!metadata.archived_at}
      />
      <details className="tank-information">
        <summary>Tank information</summary>
        <p className="mono">{metadata.id}</p>
      </details>
    </>
  );
}
function TankRoute(props) {
  const { id } = useParams();
  return (
    <div className="feature-page">
      <TankDetail key={id} {...props} />
    </div>
  );
}
function DeviceRecovery({ overview, onDevice }) {
  const { hatchery } = useAuth(),
    [data, setData] = useState({ items: [], next_cursor: null }),
    [error, setError] = useState(null),
    [archived, setArchived] = useState(false);
  const signature = JSON.stringify(overview.data);
  useEffect(() => {
    const abort = new AbortController();
    request(
      hatcheryPath(
        hatchery,
        "/devices?" + query({ include_archived: archived }),
      ),
      { signal: abort.signal },
    )
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e);
      });
    return () => abort.abort();
  }, [hatchery, signature, archived]);
  return (
    <>
      <p className="muted">
        Assign an available device to a tank, or restore an archived device.
      </p>
      <label className="check">
        <input
          type="checkbox"
          checked={archived}
          onChange={(e) => setArchived(e.target.checked)}
        />
        Include archived devices
      </label>
      <ErrorBox error={error} />
      <div className="tank-grid">
        {data.items
          .filter((d) => !d.binding || d.archived_at)
          .map((d) => (
            <article className="panel" key={d.id}>
              <img className="small-device" src={frontArt} alt="" />
              <h2>{d.display_name || d.device_id}</h2>
              <p className="mono">{d.device_id}</p>
              <Badge>
                {d.archived_at
                  ? "Archived"
                  : d.binding
                    ? "Assigned"
                    : "Unassigned"}
              </Badge>
              <p>
                Configuration: {d.configuration?.status || "No configuration"}
              </p>
              <p className="muted">Connectivity unknown</p>
              <button onClick={() => onDevice(d)}>Manage device</button>
            </article>
          ))}
      </div>
      {!data.items.some((d) => !d.binding || d.archived_at) && (
        <Empty>No unassigned or archived devices on this page.</Empty>
      )}
      {data.next_cursor && (
        <button
          onClick={async () => {
            try {
              const page = await request(
                hatcheryPath(
                  hatchery,
                  "/devices?" +
                    query({
                      include_archived: archived,
                      cursor: data.next_cursor,
                    }),
                ),
              );
              setData({ ...page, items: [...data.items, ...page.items] });
            } catch (e) {
              setError(e);
            }
          }}
        >
          Load more devices
        </button>
      )}
    </>
  );
}
function ExportPage({ tanks, loading }) {
  const { hatchery } = useAuth();
  const [tankId, setTankId] = useState(""),
    [exporting, setExporting] = useState(false);
  const tank = tanks.find((t) => t.id === tankId) || tanks[0];
  return (
    <>
      <div className="page-title">
        <div>
          <h2 className="text-[20px] md:text-[24px] font-bold text-slate-900">
            Recent telemetry
          </h2>
          <p>Browse reading records or download a CSV file.</p>
        </div>
        <button className="primary pill" onClick={() => setExporting(true)}>
          Download CSV
        </button>
      </div>
      <div className="history-tank-picker">
        <label htmlFor="history-tank">History tank</label>
        <select
          id="history-tank"
          value={tank?.id || ""}
          disabled={!tanks.length}
          onChange={(e) => setTankId(e.target.value)}
        >
          {!tanks.length && (
            <option value="">
              {loading ? "Loading tanks…" : "No tanks available"}
            </option>
          )}
          {tanks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
              {t.archived_at ? " (archived)" : ""}
            </option>
          ))}
        </select>
      </div>
      {tank ? (
        <History
          key={tank.id}
          hatchery={hatchery}
          tank={tank.id}
          archived={!!tank.archived_at}
          readOnly
          title="Recent readings"
        />
      ) : (
        <Empty>
          {loading
            ? "Loading tank records…"
            : "No tank records yet. Create a tank to begin collecting readings."}
        </Empty>
      )}
      {tank && (
        <p className="muted">
          Viewing {tank.name}. <Link to={"/tanks/" + tank.id}>Open tank</Link>{" "}
          to manage devices or add a manual measurement.
        </p>
      )}
      {exporting && (
        <Modal title="Export readings" onClose={() => setExporting(false)}>
          <p className="muted">
            Choose the tank, source and dates to include in your CSV file.
          </p>
          <ActionForm
            label="Download CSV"
            onSubmit={async (v) => {
              const blob = await request(
                hatcheryPath(
                  hatchery,
                  "/readings/export?" +
                    query({
                      ...v,
                      since: v.since ? new Date(v.since).toISOString() : "",
                      until: v.until ? new Date(v.until).toISOString() : "",
                    }),
                ),
                { download: true },
              );
              const url = URL.createObjectURL(blob),
                link = document.createElement("a");
              link.href = url;
              link.download = "bangus-readings.csv";
              link.click();
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }}
          >
            <label>
              Tank
              <select name="tank_id">
                <option value="">All tanks in this hatchery</option>
                {tanks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Source
              <select name="origin">
                <option value="all">All sources</option>
                <option value="device">Devices</option>
                <option value="manual">Manual entries</option>
              </select>
            </label>
            <label>
              Time basis
              <select name="time_basis">
                <option value="received">
                  Received time (includes unknown capture times)
                </option>
                <option value="measured">Measured time</option>
              </select>
            </label>
            <Field
              name="since"
              label="From (local time)"
              type="datetime-local"
            />
            <Field
              name="until"
              label="Until (local time)"
              type="datetime-local"
            />
            <label>
              Voided entries
              <select name="include_voided">
                <option value="false">Exclude</option>
                <option value="true">Include</option>
              </select>
            </label>
            <p className="muted">
              Each export uses one committed snapshot and the latest manual
              revision at that point. Times in the file include their UTC
              offset. A failed download must be retried.
            </p>
          </ActionForm>
        </Modal>
      )}
    </>
  );
}
function Shell() {
  const auth = useAuth(),
    overview = useOverview(auth.hatchery);
  const [tankEditor, setTankEditor] = useState(undefined),
    [deviceEditor, setDeviceEditor] = useState(null),
    [claim, setClaim] = useState(false),
    [logoutError, setLogoutError] = useState(null);
  const [tanks, setTanks] = useState([]),
    [tanksLoading, setTanksLoading] = useState(true);
  useEffect(() => {
    const abort = new AbortController();
    async function choices() {
      let cursor = null,
        items = [];
      do {
        const page = await request(
          hatcheryPath(
            auth.hatchery,
            "/tanks?" + query({ cursor, limit: 200, include_archived: true }),
          ),
          { passive: true, signal: abort.signal },
        );
        items.push(...page.items);
        cursor = page.next_cursor;
      } while (cursor);
      if (!abort.signal.aborted) setTanks(items);
    }
    choices()
      .catch((e) => {
        if (e.name !== "AbortError") setLogoutError(e);
      })
      .finally(() => {
        if (!abort.signal.aborted) setTanksLoading(false);
      });
    return () => abort.abort();
  }, [auth.hatchery, overview.data]);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <PrototypeNav />
      <div className="workspace">
        <AppHeader onError={setLogoutError} />
        <main id="main" className="page" key={auth.hatchery}>
          <ErrorBox error={logoutError} />
          <Routes>
            <Route path="/" element={<Dashboard overview={overview} />} />
            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route
              path="/tanks"
              element={
                <Tanks
                  overview={overview}
                  onEdit={setTankEditor}
                  onClaim={() => setClaim(true)}
                  onDevice={setDeviceEditor}
                />
              }
            />
            <Route
              path="/tanks/:id"
              element={
                <TankRoute
                  overview={overview}
                  onEdit={setTankEditor}
                  onDevice={setDeviceEditor}
                />
              }
            />
            <Route path="/devices" element={<Navigate to="/tanks" replace />} />
            <Route
              path="/data"
              element={
                <div className="feature-page data-page">
                  <ExportPage tanks={tanks} loading={tanksLoading} />
                </div>
              }
            />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route
              path="*"
              element={
                <Empty>
                  Page not found. <Link to="/">Return to dashboard</Link>.
                </Empty>
              }
            />
          </Routes>
        </main>
      </div>
      {tankEditor !== undefined && (
        <TankEditor
          hatchery={auth.hatchery}
          tank={tankEditor}
          onClose={() => setTankEditor(undefined)}
          onSaved={overview.refresh}
        />
      )}
      {deviceEditor && (
        <DeviceEditor
          hatchery={auth.hatchery}
          device={deviceEditor}
          tanks={tanks}
          onClose={() => setDeviceEditor(null)}
          onSaved={overview.refresh}
        />
      )}
      {claim && (
        <ClaimDevice
          hatchery={auth.hatchery}
          tanks={tanks}
          onClose={() => setClaim(false)}
          onSaved={overview.refresh}
        />
      )}
    </div>
  );
}
function SessionBoundary() {
  const { loading, operator, hatchery } = useAuth();
  return loading ? (
    <main className="session-loading" role="status">
      Opening your workspace…
    </main>
  ) : operator ? (
    <Shell key={operator.id + ":" + hatchery} />
  ) : (
    <Login />
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SessionBoundary />
      </AuthProvider>
    </BrowserRouter>
  );
}
