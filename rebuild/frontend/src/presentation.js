export const metricDefinitions = [
  { key: 'temperature', label: 'Temperature', unit: '°C', precision: 1 },
  { key: 'turbidity', label: 'Turbidity', unit: 'NTU', precision: 0 },
  { key: 'ph', label: 'pH', unit: 'pH', precision: 1 },
]

export function formatTimestamp(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Time unavailable'
  return `${new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Manila', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(new Date(value))} PHT`
}

export const formatSampleTime = formatTimestamp

export function connectionLabel(device) {
  const state = device?.connection_state ?? device?.connection
  if (state === 'unknown' || !device) return 'Device status unknown'
  if (state === 'online') return 'Connected'
  if (state === 'offline') return 'Disconnected'
  if (device.is_online === true) return 'Connected'
  if (device.is_online === false) return 'Disconnected'
  return 'Device status unknown'
}

export function availableMetricCount(log) {
  return ['temperature', 'pH', 'turbidity'].filter(key => Number.isFinite(log?.[key])).length
}

export function alertTone(type) {
  if (type === 'Critical') return 'bg-red-50 text-red-700'
  if (type === 'Warning') return 'bg-amber-50 text-amber-800'
  return 'bg-sky-50 text-sky-800'
}

export function phProvenanceLabel(provenance) {
  if (provenance === 'manual') return 'Manually entered pH'
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
  if (tank.device?.connection === 'offline') return { label: 'Last known readings', tone: 'neutral', explanation: 'The device is offline. These historical values do not describe current conditions.' }
  if (tank.device?.connection !== 'online') return { label: 'Reading status unknown', tone: 'neutral' }
  if (tank.reading.freshness === 'stale') return { label: 'Stale readings', tone: 'caution', explanation: 'The sample device is online, but these readings are marked stale. Current conditions are unknown.' }
  if (metricDefinitions.some(({ key }) => !isUsableMetric(tank.reading.metrics[key]))) return { label: 'Incomplete readings', tone: 'caution', explanation: 'Some sample readings are missing or invalid. No overall water-quality evaluation is available.' }
  if (tank.reading.freshness !== 'fresh') return { label: 'Reading freshness unknown', tone: 'neutral' }
  return { label: 'Fresh readings', tone: 'good' }
}
