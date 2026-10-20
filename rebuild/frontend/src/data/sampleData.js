// Display-only fixtures. Provisional structures, not an accepted backend API contract.
// Evaluation and freshness are supplied examples, never calculated from thresholds here.
export const sampleReferenceTime = '2026-10-20T01:30:00Z'

const metrics = (temperature, turbidity, ph, provenance = 'default') => ({
  temperature: { value: temperature, state: 'valid', provenance: 'sample' },
  turbidity: { value: turbidity, state: 'valid', provenance: 'sample' },
  ph: { value: ph, state: 'valid', provenance },
})

export const sampleTanks = [
  {
    id: 'nursery-01', name: 'Nursery 01', location: 'North wing', description: 'Sample larvae tank',
    device: { id: 'SAMPLE-DEVICE-01', connection: 'online' },
    reading: {
      observedAt: '2026-10-20T01:29:40Z', freshness: 'fresh',
      metrics: metrics(28.4, 24, 8),
      evaluation: { label: 'Optimal', tone: 'good', explanation: 'Illustrative upstream quality label. pH is a default value.' },
    },
  },
  {
    id: 'nursery-02', name: 'Nursery 02', location: 'North wing', description: 'Sample larvae tank',
    device: { id: 'SAMPLE-DEVICE-02', connection: 'online' },
    reading: {
      observedAt: '2026-10-20T01:15:00Z', freshness: 'stale',
      metrics: metrics(29.1, 38, 7.9, 'estimated'), evaluation: null,
    },
  },
  {
    id: 'nursery-03', name: 'Nursery 03', location: 'South wing', description: 'Sample larvae tank',
    device: { id: 'SAMPLE-DEVICE-03', connection: 'offline' },
    reading: {
      observedAt: '2026-10-20T00:40:00Z', freshness: 'stale',
      metrics: metrics(28.7, 31, 8), evaluation: null,
    },
  },
  {
    id: 'nursery-04', name: 'Nursery 04', location: 'South wing', description: 'Sample larvae tank',
    device: { id: 'SAMPLE-DEVICE-04', connection: 'unknown' }, reading: null,
  },
]

export const scenarios = [
  { value: 'ready', label: 'Mixed sample data', description: 'Four fictional tanks with fresh, stale, offline, and missing readings.' },
  { value: 'loading', label: 'Loading', description: 'Loading preview is paused. Choose another scenario to continue.' },
  { value: 'empty', label: 'Empty', description: 'No sample tanks or readings are available in this scenario.' },
  { value: 'error', label: 'Error', description: 'A simulated load failure. Retry restores sample data only.' },
  { value: 'offline', label: 'Device offline', description: 'Devices are offline. Values are last-known samples, not live readings.' },
  { value: 'stale', label: 'Stale readings', description: 'Devices are online but the supplied readings are explicitly marked stale.' },
  { value: 'invalid', label: 'Invalid readings', description: 'Invalid values are withheld; a valid zero is still displayed as zero.' },
  { value: 'missing', label: 'Missing readings', description: 'Devices are online, but no readings have been received in this sample.' },
]

export function getSampleView(scenario) {
  if (['loading', 'empty', 'error'].includes(scenario)) return { state: scenario, tanks: [] }
  const tanks = sampleTanks.map((tank) => {
    if (scenario === 'ready') return tank
    const reading = structuredClone(sampleTanks[0].reading)
    const device = { ...tank.device, connection: 'online' }
    if (scenario === 'missing') return { ...tank, device, reading: null }
    if (scenario === 'offline' || scenario === 'stale') {
      reading.freshness = 'stale'
      reading.observedAt = '2026-10-20T00:40:00Z'
      reading.evaluation = null
      if (scenario === 'offline') device.connection = 'offline'
    }
    if (scenario === 'invalid') {
      reading.metrics.temperature = { value: 'sensor-fault', state: 'invalid', provenance: 'sample' }
      reading.metrics.turbidity = { value: 0, state: 'valid', provenance: 'sample' }
      reading.metrics.ph = { value: null, state: 'invalid', provenance: 'default' }
      reading.evaluation = null
    }
    return { ...tank, device, reading }
  })
  return { state: 'ready', tanks }
}
