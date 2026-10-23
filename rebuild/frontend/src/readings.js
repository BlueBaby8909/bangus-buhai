export const metricNames = {
  temperature: ["Temperature", "°C", "temperature_c"],
  ph: ["pH", "pH", "ph"],
  turbidity: ["Turbidity", "NTU", "turbidity_ntu"],
};
export function metric(reading, name, now = Date.now()) {
  if (!reading) return { value: null, label: "No reading", source: "—" };
  if (reading.origin === "manual") {
    const value = reading[metricNames[name][2]];
    return {
      value,
      source: "Manual measurement",
      label:
        value == null
          ? "Not reported"
          : reading.voided
            ? "Voided"
            : "Operator reported",
    };
  }
  const sample = reading.telemetry.readings[name];
  const captured = reading.measured_at && Date.parse(reading.measured_at);
  const elapsed = captured == null ? null : now - captured;
  let label = sample.validity;
  if (sample.source === "default") label = "Default · unverified";
  else if (
    !["missing", "invalid", "stale"].includes(sample.validity) &&
    (elapsed == null || elapsed < 0)
  )
    label = "Capture time uncertain";
  else if (
    name === "temperature" &&
    sample.sample_age_ms != null &&
    elapsed + sample.sample_age_ms >= 60000
  )
    label = "Stale";
  return {
    value: sample.value,
    source: sample.source === "sensor" ? "Sensor" : sample.source,
    label,
  };
}
export function display(value) {
  return value == null || !Number.isFinite(value)
    ? "—"
    : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
export function timestamp(value) {
  return value ? new Date(value).toLocaleString() : "Capture time unknown";
}
export function mergeReading(rows, reading) {
  const index = rows.findIndex(
    (r) => r.origin === reading.origin && r.id === reading.id,
  );
  if (index >= 0 && (rows[index].version || 0) >= (reading.version || 0))
    return rows;
  return [...rows.filter((_, i) => i !== index), reading].sort(
    (a, b) => Date.parse(b.received_at) - Date.parse(a.received_at),
  );
}
export function chartRows(rows, deviceId, name) {
  return rows
    .filter(
      (r) =>
        !r.voided &&
        r.measured_at &&
        (r.origin === "manual" || r.device_id === deviceId),
    )
    .sort((a, b) => Date.parse(a.measured_at) - Date.parse(b.measured_at))
    .map((r) => {
      const m = metric(r, name);
      return {
        id: r.id,
        time: Date.parse(r.measured_at),
        device: r.origin === "device" ? m.value : null,
        manual: r.origin === "manual" ? m.value : null,
        source:
          r.origin === "manual"
            ? "Operator reported"
            : r.telemetry.readings[name].source +
              " · " +
              r.telemetry.readings[name].validity,
      };
    });
}
