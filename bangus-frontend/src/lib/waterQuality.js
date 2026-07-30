// Mirrors backend/services/water_quality.py — display-only. The backend is the
// source of truth for the computed `status`/`warnings` on each log.

export const THRESHOLDS = {
  temperature: { min: 15, max: 40, optimalFrom: 26, optimalTo: 32, unit: "\u00b0C" },
  pH: { min: 4, max: 11, optimalFrom: 7.5, optimalTo: 8.5, unit: "" },
  turbidity: { min: 0, max: 200, optimalFrom: 0, optimalTo: 50, unit: " NTU" },
};

export function toneForMetric(metric, value) {
  const t = THRESHOLDS[metric];
  if (metric === "temperature") {
    return value < t.optimalFrom || value > t.optimalTo ? "warning" : "optimal";
  }
  if (metric === "pH") {
    if (value < 6.5 || value > 9.0) return "critical";
    if (value < t.optimalFrom || value > t.optimalTo) return "warning";
    return "optimal";
  }
  if (metric === "turbidity") {
    if (value > 100) return "critical";
    if (value > t.optimalTo) return "warning";
    return "optimal";
  }
  return "optimal";
}
