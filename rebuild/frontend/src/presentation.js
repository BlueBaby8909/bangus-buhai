export const metricDefinitions = [
  { key: 'temperature', label: 'Temperature', unit: '°C', precision: 1 },
  { key: 'turbidity', label: 'Turbidity', unit: 'NTU', precision: 0 },
  { key: 'ph', label: 'pH', unit: 'pH', precision: 1 },
]

export function formatSampleTime(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Time unavailable'
  return `${new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Singapore', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(new Date(value))} SGT`
}

export function phProvenanceLabel(provenance) {
  if (provenance === 'estimated') return 'Estimated pH · not measured'
  if (provenance === 'default') return 'Default pH · not measured'
  if (provenance === 'measured') return 'Measured pH'
  return 'pH source unavailable'
}

export function isUsableMetric(metric) {
  return metric?.state === 'valid' && typeof metric.value === 'number' && Number.isFinite(metric.value)
}

export function readingStatus(tank) {
  if (!tank.reading) return { label: 'No readings', tone: 'neutral', explanation: 'No sample readings are available for this tank.' }
  if (tank.device.connection === 'offline') return { label: 'Last known readings', tone: 'neutral', explanation: 'The sample device is offline. These historical values do not describe current conditions.' }
  if (tank.reading.freshness === 'stale') return { label: 'Stale readings', tone: 'caution', explanation: 'The sample device is online, but these readings are marked stale. Current conditions are unknown.' }
  if (metricDefinitions.some(({ key }) => !isUsableMetric(tank.reading.metrics[key]))) return { label: 'Incomplete readings', tone: 'caution', explanation: 'Some sample readings are missing or invalid. No overall water-quality evaluation is available.' }
  return { label: 'Fresh sample', tone: 'good', explanation: 'These readings are marked fresh relative to the fixed sample clock, not the current time.' }
}
