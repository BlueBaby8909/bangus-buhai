import "./gauge.css";

const TONE_COLOR = {
  optimal: "var(--success)",
  warning: "var(--warning)",
  critical: "var(--danger)",
  unknown: "var(--paper-line)",
};

const TONE_LABEL = {
  optimal: "Optimal",
  warning: "Watch",
  critical: "Critical",
  unknown: "No data",
};

/**
 * A dial-style status ring, modeled on the analog depth/pressure gauges
 * used pond-side. Fill amount is illustrative of status severity, not a
 * literal percentage.
 */
export default function GaugeRing({ status = "unknown", size = 76 }) {
  const fillByStatus = { optimal: 0.92, warning: 0.55, critical: 0.22, unknown: 0.06 };
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const fill = fillByStatus[status] ?? fillByStatus.unknown;
  const dash = circumference * fill;
  const color = TONE_COLOR[status] || TONE_COLOR.unknown;

  return (
    <div className="gauge-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--paper-line)"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="gauge-ring__label">
        <span className="gauge-ring__tick mono" style={{ color }}>
          {TONE_LABEL[status] || TONE_LABEL.unknown}
        </span>
      </div>
    </div>
  );
}
