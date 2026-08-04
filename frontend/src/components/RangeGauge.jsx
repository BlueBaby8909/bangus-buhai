import "./gauge.css";

/**
 * A single reading plotted on a labeled dial strip, with the optimal band
 * shaded so a grower can see at a glance where a value sits.
 */
export default function RangeGauge({ label, value, unit, min, max, optimalFrom, optimalTo, tone }) {
  const clampPct = (v) => Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100));
  const bandLeft = clampPct(optimalFrom);
  const bandWidth = clampPct(optimalTo) - bandLeft;
  const markerLeft = clampPct(value);

  const toneColor =
    tone === "critical" ? "var(--danger)" : tone === "warning" ? "var(--warning)" : "var(--success)";

  return (
    <div className="range-gauge">
      <span className="range-gauge__label">{label}</span>
      <div className="range-gauge__track">
        <div
          className="range-gauge__band"
          style={{ left: `${bandLeft}%`, width: `${bandWidth}%`, background: "rgba(76,140,107,0.25)" }}
        />
        <div
          className="range-gauge__marker"
          style={{ left: `${markerLeft}%`, background: toneColor }}
        />
      </div>
      <span className="range-gauge__value mono">
        {value}
        {unit}
      </span>
    </div>
  );
}
