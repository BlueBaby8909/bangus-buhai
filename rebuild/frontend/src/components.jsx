import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { message } from "./api";
import { display, metric, metricNames, timestamp } from "./readings";
import temperatureIcon from "./prototype-assets/DashBoard/Temp(Orange).svg";
import phIcon from "./prototype-assets/DashBoard/Ph(Blue).svg";
import detailPhIcon from "./prototype-assets/DeviceDetail/Ph(LightBlue).svg";
import detailTempIcon from "./prototype-assets/DeviceDetail/Temp(Blue).svg";
import turbidityIcon from "./prototype-assets/DashBoard/Turb(Gray).svg";
const metricIcons = {
  temperature: temperatureIcon,
  ph: phIcon,
  turbidity: turbidityIcon,
};
export function ErrorBox({ error }) {
  return error ? (
    <p className="notice error" role="alert">
      {typeof error === "string" ? error : message(error)}
    </p>
  ) : null;
}
export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
export function Badge({ children }) {
  return <span className="badge">{children}</span>;
}
export function Future({ title, children }) {
  return (
    <section className="future">
      <div>
        <h3>{title}</h3>
        <p>{children}</p>
      </div>
      <Badge>Not available yet</Badge>
    </section>
  );
}
export function Modal({ title, children, onClose }) {
  const ref = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      previous?.focus();
    };
  }, []);
  return createPortal(
    <dialog
      className="feature-dialog"
      ref={ref}
      onKeyDown={(e) => {
        if (e.key !== "Tab") return;
        const nodes = [
          ...e.currentTarget.querySelectorAll(
            "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
          ),
        ];
        const first = nodes[0],
          last = nodes.at(-1),
          active = document.activeElement;
        if (
          e.shiftKey &&
          (active === first || !e.currentTarget.contains(active))
        ) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first?.focus();
        }
      }}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-label={title}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <div className="dialog-body">{children}</div>
    </dialog>,
    document.body,
  );
}
export function ActionForm({
  onSubmit,
  children,
  label = "Save changes",
  initialError = "",
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(initialError);
  return (
    <form
      className="action-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (busy) return;
        setBusy(true);
        setError("");
        const values = Object.fromEntries(new FormData(e.currentTarget));
        try {
          await onSubmit(values);
        } catch (failure) {
          setError(failure);
        } finally {
          setBusy(false);
        }
      }}
    >
      {children}
      <ErrorBox error={error} />
      <button className="primary" disabled={busy}>
        {busy ? "Saving…" : label}
      </button>
    </form>
  );
}
export function Field({ label, name, type = "text", value, ...props }) {
  return (
    <label>
      {label}
      <input name={name} type={type} defaultValue={value} {...props} />
    </label>
  );
}
export function MetricStrip({ reading, serverOffset = 0, tiles = false }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className={tiles ? "metrics metric-tiles" : "metrics"}>
      {(tiles
        ? ["ph", "temperature", "turbidity"]
        : Object.keys(metricNames)
      ).map((key) => {
        const [label, unit] = metricNames[key];
        const m = metric(reading, key, now + serverOffset);
        return (
          <section className={"metric metric-" + key} key={key}>
            {tiles && (
              <img
                className="metric-icon"
                src={
                  tiles && key === "ph"
                    ? detailPhIcon
                    : tiles && key === "temperature"
                      ? detailTempIcon
                      : metricIcons[key]
                }
                alt=""
              />
            )}
            <span>{label}</span>
            <strong>
              {display(m.value)} <small>{unit}</small>
            </strong>
            <p>{m.label}</p>
            <small>{m.source}</small>
          </section>
        );
      })}
      <p className="metric-time">
        Measured: {timestamp(reading?.measured_at)}
        <br />
        Received:{" "}
        {reading?.received_at
          ? timestamp(reading.received_at)
          : "No delivery yet"}
      </p>
    </div>
  );
}
