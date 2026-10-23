import { useEffect, useState, useRef } from "react";
import { request, hatcheryPath } from "./api";
import { Badge, ErrorBox, Modal } from "./components";
export default function RelayControl({ hatchery, device, reading }) {
  const [command, setCommand] = useState(null),
    [intent, setIntent] = useState(null),
    [busy, setBusy] = useState(false),
    [confirm, setConfirm] = useState(null),
    [error, setError] = useState(null);
  const submitting = useRef(false),
    generation = useRef(0);
  const base = hatcheryPath(hatchery, `/devices/${device.device_id}/commands`);
  useEffect(() => {
    const abort = new AbortController();
    const refresh = () => {
      if (submitting.current) return;
      const current = generation.current;
      request(base + "/latest", { passive: true, signal: abort.signal })
        .then((value) => {
          if (current === generation.current && !abort.signal.aborted)
            setCommand(value);
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e);
        });
    };
    refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, 2500);
    return () => {
      abort.abort();
      clearInterval(timer);
    };
  }, [base]);
  const ready =
    device.verified &&
    !device.archived_at &&
    device.configuration?.status === "confirmed" &&
    device.binding;
  const pending =
    command && ["queued", "published", "accepted"].includes(command.status);
  async function send(next) {
    if (busy) return;
    submitting.current = true;
    generation.current++;
    setBusy(true);
    setError(null);
    setIntent(next);
    setConfirm(null);
    try {
      setCommand(
        await request(base, { method: "POST", body: next.body, key: next.key }),
      );
      setIntent(null);
    } catch (e) {
      setError(e);
      if (e.status && e.status < 500) setIntent(null);
    } finally {
      generation.current++;
      submitting.current = false;
      setBusy(false);
    }
  }
  const result = command?.results
    ?.filter((r) => ["applied", "rejected", "failed"].includes(r.result))
    .at(-1);
  const output = reading?.telemetry?.relay?.on;
  const label =
    command?.status === "timed_out"
      ? "Timed out · outcome uncertain"
      : command?.status?.replaceAll("_", " ") ||
        "No command for this assignment";
  return (
    <section className="panel relay-panel">
      <div className="section-heading">
        <div>
          <h2>Relay control</h2>
          <p className="muted">Unloaded demonstration relay</p>
        </div>
        <Badge>{label}</Badge>
      </div>
      <dl className="relay-state">
        <div>
          <dt>Last telemetry GPIO</dt>
          <dd>
            <strong>
              {output === undefined ? "Unknown" : output ? "ON" : "OFF"}
            </strong>
          </dd>
        </div>
        <div>
          <dt>Reported mode</dt>
          <dd>{reading?.telemetry?.relay?.mode || "Not reported"}</dd>
        </div>
        {command && (
          <div>
            <dt>Latest request</dt>
            <dd>
              <strong>
                {command.command?.type === "relay.auto"
                  ? "AUTO"
                  : command.command?.desired_on
                    ? "Manual ON"
                    : "Manual OFF"}
              </strong>
            </dd>
          </div>
        )}
      </dl>
      <p className="muted">
        Reported output is not relay-contact feedback. Manual mode lasts until
        AUTO or reboot.
      </p>
      <div className="actions relay-actions">
        {[
          ["ON", { type: "relay.set", desired_on: true }],
          ["OFF", { type: "relay.set", desired_on: false }],
          ["AUTO", { type: "relay.auto" }],
        ].map(([label, body]) => (
          <button
            key={label}
            disabled={!ready || pending || busy || !!intent}
            onClick={() =>
              setConfirm({ label, body, key: crypto.randomUUID() })
            }
          >
            {label}
          </button>
        ))}
      </div>
      {!ready && (
        <p className="muted">
          A verified device and confirmed current assignment are required.
        </p>
      )}
      {result && (
        <p>
          Last command result: {result.result} ·{" "}
          {result.reason?.replaceAll("_", " ")}
          {result.result === "applied"
            ? ` · GPIO ${result.observed_on ? "ON" : "OFF"} confirmed for this command`
            : ""}
        </p>
      )}
      {command && (
        <details>
          <summary>Command evidence</summary>
          <p className="mono">{command.command_id}</p>
          <p>
            {command.attempts.length} dispatch attempt(s),{" "}
            {command.results.length} device result(s).
          </p>
          {command.timed_out_at && (
            <p>Timeout history retained, even if a later result resolves it.</p>
          )}
        </details>
      )}
      <ErrorBox error={error} />
      {intent && (
        <button disabled={busy} onClick={() => send(intent)}>
          Retry the same command
        </button>
      )}
      {confirm && (
        <Modal
          title={`Send ${confirm.label} command?`}
          onClose={() => setConfirm(null)}
        >
          <p>
            Send {confirm.label} to {device.display_name || device.device_id}?
            The device will check its assignment and safety before applying it.
          </p>
          <button className="primary" onClick={() => send(confirm)}>
            Send {confirm.label}
          </button>
        </Modal>
      )}
    </section>
  );
}
