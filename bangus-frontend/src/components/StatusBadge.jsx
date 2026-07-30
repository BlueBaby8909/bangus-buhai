const TONE = {
  optimal: { bg: "rgba(76,140,107,0.14)", fg: "var(--success)", label: "Optimal" },
  warning: { bg: "rgba(201,154,59,0.16)", fg: "var(--warning)", label: "Watch" },
  critical: { bg: "rgba(178,58,46,0.14)", fg: "var(--danger)", label: "Critical" },
  unknown: { bg: "rgba(22,48,44,0.06)", fg: "var(--ink-soft)", label: "No data" },
};

export default function StatusBadge({ status = "unknown" }) {
  const tone = TONE[status] || TONE.unknown;
  return (
    <span
      className="status-badge"
      style={{ background: tone.bg, color: tone.fg }}
    >
      <span className="status-badge__dot" style={{ background: tone.fg }} />
      {tone.label}
    </span>
  );
}
