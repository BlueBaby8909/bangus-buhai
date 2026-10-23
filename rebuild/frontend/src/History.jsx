import { useEffect, useState, useRef } from "react";
import { request, query, hatcheryPath } from "./api";
import { ActionForm, Field, Modal, ErrorBox, Empty, Badge } from "./components";
import { timestamp, display } from "./readings";
function MeasurementForm({ row, action, onSave }) {
  const requestId = useRef(null);
  const [initialTime] = useState(() =>
    localDate(row?.measured_at || new Date()),
  );
  return (
    <ActionForm
      label={
        action === "create"
          ? "Add measurement"
          : action === "correct"
            ? "Save correction"
            : action === "void"
              ? "Void entry"
              : "Restore entry"
      }
      onSubmit={async (values) => {
        let body = {};
        if (["create", "correct"].includes(action)) {
          body = {
            measured_at: new Date(values.measured).toISOString(),
            temperature_c:
              values.temperature === "" ? null : Number(values.temperature),
            ph: values.ph === "" ? null : Number(values.ph),
            turbidity_ntu:
              values.turbidity === "" ? null : Number(values.turbidity),
            notes: values.notes || null,
            instrument: values.instrument || null,
          };
          if (
            [body.temperature_c, body.ph, body.turbidity_ntu].every(
              (v) => v === null,
            )
          )
            throw new Error("measurement_required");
        }
        if (action === "create") {
          requestId.current ||= crypto.randomUUID();
          body.request_id = requestId.current;
        } else
          Object.assign(body, {
            expected_version: row.version,
            reason: values.reason,
          });
        await onSave(body);
      }}
    >
      {["create", "correct"].includes(action) && (
        <>
          <label>
            Measured at (your local time)
            <input
              name="measured"
              type="datetime-local"
              required
              defaultValue={initialTime}
            />
          </label>
          <div className="form-grid">
            <Field
              label="Temperature (°C)"
              name="temperature"
              type="number"
              step="any"
              value={row?.temperature_c ?? ""}
            />
            <Field
              label="pH"
              name="ph"
              type="number"
              step="any"
              value={row?.ph ?? ""}
            />
            <Field
              label="Turbidity (NTU)"
              name="turbidity"
              type="number"
              step="any"
              value={row?.turbidity_ntu ?? ""}
            />
          </div>
          <p className="muted">
            Enter at least one measured value. Leave unmeasured values blank.
          </p>
          <Field
            label="Instrument"
            name="instrument"
            maxLength={200}
            value={row?.instrument || ""}
          />
          <label>
            Notes
            <textarea
              name="notes"
              maxLength={2000}
              defaultValue={row?.notes || ""}
            />
          </label>
        </>
      )}
      {action !== "create" && (
        <Field
          label="Reason for this change"
          name="reason"
          maxLength={500}
          required
        />
      )}
    </ActionForm>
  );
}
function localDate(value) {
  const d = new Date(value);
  return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
export default function History({
  hatchery,
  tank,
  archived,
  revision = 0,
  readOnly = false,
  title = "Reading history",
}) {
  const [rows, setRows] = useState([]),
    [cursor, setCursor] = useState(null),
    [filters, changeFilters] = useState({
      origin: "all",
      time_basis: "received",
      include_voided: false,
      since: "",
      until: "",
    }),
    [error, setError] = useState(null),
    [busy, setBusy] = useState(true),
    [edit, setEdit] = useState(null),
    [audit, setAudit] = useState(null),
    [reload, setReload] = useState(0);
  const setFilters = (value) => {
    setRows([]);
    setCursor(null);
    setBusy(true);
    setError(null);
    changeFilters(value);
  };
  const base = hatcheryPath(hatchery, `/tanks/${tank}`);
  const filterQuery = {
    ...filters,
    since: filters.since ? new Date(filters.since).toISOString() : "",
    until: filters.until ? new Date(filters.until).toISOString() : "",
  };
  const signature = JSON.stringify(filterQuery);
  useEffect(() => {
    const abort = new AbortController();
    request(
      base + "/readings?" + query({ ...JSON.parse(signature), limit: 50 }),
      { signal: abort.signal, passive: true },
    )
      .then((page) => {
        setRows(page.items);
        setCursor(page.next_cursor);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e);
      })
      .finally(() => {
        if (!abort.signal.aborted) setBusy(false);
      });
    return () => abort.abort();
  }, [base, signature, reload, revision]);
  async function more() {
    setBusy(true);
    try {
      const page = await request(
        base + "/readings?" + query({ ...filterQuery, cursor, limit: 50 }),
        { passive: true },
      );
      setRows((r) => [...r, ...page.items]);
      setCursor(page.next_cursor);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  async function exportCsv() {
    setBusy(true);
    setError(null);
    try {
      const blob = await request(
        hatcheryPath(
          hatchery,
          "/readings/export?" + query({ ...filterQuery, tank_id: tank }),
        ),
        { download: true },
      );
      const url = URL.createObjectURL(blob),
        link = document.createElement("a");
      link.href = url;
      link.download = "bangus-readings.csv";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel history-panel">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
        </div>
        <div className="actions">
          <button onClick={() => setReload((n) => n + 1)}>Refresh</button>
          {!readOnly && (
            <button
              className="primary"
              disabled={archived}
              onClick={() => setEdit({ action: "create" })}
            >
              Add measurement
            </button>
          )}

          <button disabled={busy} onClick={exportCsv}>
            Export CSV
          </button>
        </div>
      </div>
      <div className="filters history-filters">
        <label>
          Source
          <select
            value={filters.origin}
            onChange={(e) => setFilters({ ...filters, origin: e.target.value })}
          >
            <option value="all">All sources</option>
            <option value="device">Devices</option>
            <option value="manual">Manual entries</option>
          </select>
        </label>
        <label>
          Time basis
          <select
            value={filters.time_basis}
            onChange={(e) =>
              setFilters({ ...filters, time_basis: e.target.value })
            }
          >
            <option value="received">Received time</option>
            <option value="measured">Measured time</option>
          </select>
        </label>
        <label>
          From
          <input
            type="datetime-local"
            value={filters.since}
            onChange={(e) => setFilters({ ...filters, since: e.target.value })}
          />
        </label>
        <label>
          Until
          <input
            type="datetime-local"
            value={filters.until}
            onChange={(e) => setFilters({ ...filters, until: e.target.value })}
          />
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.include_voided}
            onChange={(e) =>
              setFilters({ ...filters, include_voided: e.target.checked })
            }
          />
          Include voided
        </label>
      </div>
      <p className="muted">
        Received-time history includes unknown capture times. CSV exports all
        matching snapshot rows, not just this page.
      </p>
      <ErrorBox error={error} />
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Source / measured</th>
              <th>Temperature</th>
              <th>pH</th>
              <th>Turbidity</th>
              <th>Revision / actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.origin + r.id} className={r.voided ? "voided" : ""}>
                <td>
                  <strong>
                    {r.origin === "manual" ? "Manual entry" : r.device_id}
                  </strong>
                  <br />
                  {timestamp(r.measured_at)}
                  <small>Received {timestamp(r.received_at)}</small>
                </td>
                <td>
                  {display(
                    r.origin === "manual"
                      ? r.temperature_c
                      : r.telemetry.readings.temperature.value,
                  )}{" "}
                  °C
                </td>
                <td>
                  {display(
                    r.origin === "manual"
                      ? r.ph
                      : r.telemetry.readings.ph.value,
                  )}
                  <small>
                    {r.origin === "manual"
                      ? "Operator measured"
                      : r.telemetry.readings.ph.source +
                        " · " +
                        r.telemetry.readings.ph.validity}
                  </small>
                </td>
                <td>
                  {display(
                    r.origin === "manual"
                      ? r.turbidity_ntu
                      : r.telemetry.readings.turbidity.value,
                  )}{" "}
                  NTU
                </td>
                <td>
                  {r.origin === "manual" ? (
                    <>
                      <Badge>
                        v{r.version}
                        {r.voided ? " · voided" : ""}
                      </Badge>
                      <div className="actions">
                        {!readOnly && (
                          <>
                            <button
                              disabled={archived || r.voided}
                              onClick={() =>
                                setEdit({ action: "correct", row: r })
                              }
                            >
                              Correct
                            </button>
                            <button
                              disabled={archived}
                              onClick={() =>
                                setEdit({
                                  action: r.voided ? "restore" : "void",
                                  row: r,
                                })
                              }
                            >
                              {r.voided ? "Restore" : "Void"}
                            </button>
                          </>
                        )}
                        <button
                          onClick={async () => {
                            try {
                              setAudit(
                                await request(
                                  base + `/manual-readings/${r.id}/revisions`,
                                  { passive: true },
                                ),
                              );
                            } catch (e) {
                              setError(e);
                            }
                          }}
                        >
                          Revisions
                        </button>
                      </div>
                    </>
                  ) : (
                    <Badge>Immutable capture</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && !busy && (
        <Empty>
          No matching readings. Adjust the filters or add a manual measurement.
        </Empty>
      )}
      {busy && <p role="status">Loading readings…</p>}
      {cursor && (
        <button disabled={busy} onClick={more}>
          Load older readings
        </button>
      )}
      {edit && (
        <Modal
          title={
            edit.action === "create"
              ? "Add manual measurement"
              : edit.action + " manual entry"
          }
          onClose={() => setEdit(null)}
        >
          <MeasurementForm
            {...edit}
            onSave={async (body) => {
              const url =
                base +
                "/manual-readings" +
                (edit.row
                  ? "/" +
                    edit.row.id +
                    (["void", "restore"].includes(edit.action)
                      ? "/" + edit.action
                      : "")
                  : "");
              await request(url, {
                method: edit.action === "correct" ? "PATCH" : "POST",
                body,
              });
              setEdit(null);
              setReload((n) => n + 1);
            }}
          />
        </Modal>
      )}
      {audit && (
        <Modal title="Revision history" onClose={() => setAudit(null)}>
          {audit.items.map((r) => (
            <article className="audit" key={r.revision_id}>
              <Badge>
                Version {r.version}
                {r.voided ? " · voided" : ""}
              </Badge>
              <p>{timestamp(r.changed_at)}</p>
              <p>{r.reason || "Original measurement"}</p>
              <p className="mono">Actor {r.actor_id}</p>
              <p>
                {display(r.temperature_c)} °C · {display(r.ph)} pH ·{" "}
                {display(r.turbidity_ntu)} NTU
              </p>
            </article>
          ))}
          {audit.next_before_version && (
            <button
              onClick={async () => {
                try {
                  const next = await request(
                    base +
                      `/manual-readings/${audit.items[0].id}/revisions?before_version=${audit.next_before_version}`,
                    { passive: true },
                  );
                  setAudit({
                    items: [...audit.items, ...next.items],
                    next_before_version: next.next_before_version,
                  });
                } catch (e) {
                  setError(e);
                }
              }}
            >
              Older revisions
            </button>
          )}
        </Modal>
      )}
    </section>
  );
}
