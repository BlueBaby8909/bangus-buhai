// Provisional display-only fixtures for the copied prototype screens, not API contracts.
import { getSampleView, sampleReferenceTime, sampleTanks } from './sampleData.js'

export function makeScreenTanks(scenario = 'ready') {
  return getSampleView(scenario).tanks.map((tank) => ({
    ...tank, volume_ml: 10000, growth_stage: 'larvae', sample_only: true,
  }))
}

export function makeScreenLog(tank, offset = 0) {
  if (!tank.reading) return null
  const metricValue = (key) => {
    const metric = tank.reading.metrics[key]
    return metric?.state === 'valid' && typeof metric.value === 'number' && Number.isFinite(metric.value)
      ? metric.value : null
  }
  return {
    id: `sample-log-${tank.id}-${offset}`, tank_id: tank.id, device_id: tank.device.id,
    recorded_at: new Date(Date.parse(tank.reading.observedAt) - offset * 300000).toISOString(),
    temperature: metricValue('temperature') === null ? null : Number((metricValue('temperature') + (offset ? Math.sin(offset / 5) * .3 : 0)).toFixed(1)),
    pH: metricValue('ph'), turbidity: metricValue('turbidity'),
    ph_provenance: tank.reading.metrics.ph?.provenance || 'unknown',
    freshness: tank.reading.freshness, connection: tank.device.connection,
    relay_on: false, sample_only: true,
    quality_status: tank.device.connection === 'online' && tank.reading.freshness === 'fresh'
      ? tank.reading.evaluation?.label || 'Unavailable' : 'Unavailable',
  }
}

export function makeScreenHistory(tank) {
  return tank.reading ? Array.from({ length: 48 }, (_, index) => makeScreenLog(tank, index)) : []
}

export function makeScreenForecast(tank, hoursAgo = 0) {
  const log = makeScreenLog(tank)
  if (!log || tank.device.connection !== 'online' || log.freshness !== 'fresh'
    || [log.temperature, log.pH, log.turbidity].some((value) => !Number.isFinite(value))) return null
  const origin = new Date(Date.parse(log.recorded_at) - hoursAgo * 3600000).toISOString()
  const result = {
    id: `sample-forecast-${tank.id}-${hoursAgo}`, tank_id: tank.id,
    created_at: origin, predicted_from: origin, ph_provenance: 'estimated',
    sample_only: true, quality_label: 'Unavailable', confidence_label: 'Unvalidated illustration',
  }
  for (const hour of [1, 2, 3, 4]) {
    result[`temperature_${hour}h`] = Number((log.temperature + hour * .2).toFixed(1))
    result[`pH_${hour}h`] = Number((log.pH - hour * .02).toFixed(2))
    result[`turbidity_${hour}h`] = Number((log.turbidity + hour).toFixed(1))
    result[`target_${hour}h`] = new Date(Date.parse(origin) + hour * 3600000).toISOString()
  }
  return result
}

export const screenAlertFixtures = [
  { id: 'sample-offline', tank_id: 'nursery-03', type: 'Critical', category: 'Connection', title: 'Device offline', message: 'The device is offline. Readings show its last reported values.', color: 'bg-red-50 text-red-700', titleColor: 'text-red-600', dotColor: 'bg-red-500' },
  { id: 'sample-stale', tank_id: 'nursery-02', type: 'Warning', category: 'Reading freshness', title: 'Readings are out of date', message: 'No recent readings have been received. Check the device connection.', color: 'bg-amber-50 text-amber-800', titleColor: 'text-amber-600', dotColor: 'bg-amber-500' },
  { id: 'sample-forecast', tank_id: 'nursery-01', type: 'AI Forecast', category: 'Forecast', title: 'Forecast available', message: 'View the four-hour temperature, pH and turbidity outlook.', color: 'bg-sky-50 text-sky-800', titleColor: 'text-sky-600', dotColor: 'bg-sky-500' },
].map((alert) => ({ ...alert, tank: sampleTanks.find((tank) => tank.id === alert.tank_id).name, time: '20 Oct 2026, 09:30 SGT', recorded_at: sampleReferenceTime, sample_only: true }))
