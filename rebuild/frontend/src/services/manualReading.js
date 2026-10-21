export function manualReadingPayload(values, now = Date.now()) {
  const metrics = Object.fromEntries(['temperature', 'pH', 'turbidity'].map(key => [key, values[key] === '' ? null : Number(values[key])]))
  const observed = new Date(values.recorded_at)
  if (Object.values(metrics).every(value => value === null) || Object.values(metrics).some(value => value !== null && !Number.isFinite(value))
    || !Number.isFinite(observed.getTime()) || observed.getTime() > now
    || (metrics.pH !== null && (metrics.pH < 0 || metrics.pH > 14)) || (metrics.turbidity !== null && metrics.turbidity < 0)) {
    throw new Error('Enter at least one valid reading and an observation time that is not in the future.')
  }
  return { ...metrics, recorded_at: observed.toISOString(), source: 'manual', ph_provenance: metrics.pH === null ? 'unknown' : 'manual' }
}
