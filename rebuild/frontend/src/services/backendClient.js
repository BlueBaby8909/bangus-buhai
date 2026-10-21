import { DataClientError, dataMethods } from './createDataClient.js'

const writes = { createTank: 'POST', updateTank: 'PUT', deleteTank: 'DELETE', createWaterLog: 'POST', sendCommand: 'POST' }
const scoped = new Set(['getTankSummary', 'getLatestPrediction', 'getPredictionHistory', 'listWaterLogs', 'updateTank', 'deleteTank', 'createWaterLog', 'sendCommand'])

// Endpoint paths are supplied after the backend contract is reviewed.
export function createBackendClient({ baseUrl, routes = {}, fetchImpl = globalThis.fetch, origin = globalThis.location?.origin,
  timeoutMs = 15000, getCsrfToken = () => globalThis.document?.querySelector('meta[name="csrf-token"]')?.content } = {}) {
  let base
  if (baseUrl) {
    base = new URL(baseUrl, origin)
    if (base.origin !== origin || !['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) {
      throw new TypeError('The API must use a same-origin HTTP(S) base URL without credentials, query, or fragment.')
    }
    if (!base.pathname.endsWith('/')) base.pathname += '/'
  }
  if (!routes || typeof routes !== 'object' || Array.isArray(routes)) throw new TypeError('API routes must be an object.')
  for (const [method, path] of Object.entries(routes)) {
    if (!dataMethods.includes(method) || typeof path !== 'string' || !path || path.startsWith('/') || path.includes('..') || /[?#:\\]/.test(path)
      || (scoped.has(method) && !path.includes('{id}')) || /\{(?!id\})/.test(path)) {
      throw new TypeError(`Invalid API route configuration: ${method}`)
    }
  }
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new TypeError('Request timeout must be positive.')
  return Object.fromEntries(dataMethods.map((operation) => [operation, async (...args) => {
    if (!base || !routes[operation]) throw new DataClientError('This service is currently unavailable.', { code: 'not_configured' })
    if (operation === 'sendCommand') throw new DataClientError('Relay control is unavailable.', { code: 'not_supported' })
    const method = writes[operation] || 'GET'
    const id = scoped.has(operation) ? args[0] : undefined
    if (scoped.has(operation) && (id == null || String(id).trim() === '' || ['.', '..'].includes(String(id)))) {
      throw new DataClientError('A resource identity is required.', { code: 'invalid_identity' })
    }
    const url = new URL(routes[operation].replaceAll('{id}', encodeURIComponent(String(id))), base)
    if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) throw new TypeError('API route escapes its base URL.')
    const query = method === 'GET' ? (scoped.has(operation) ? args[1] : args[0]) : undefined
    for (const [key, value] of Object.entries(query || {})) if (value != null) url.searchParams.set(key, String(value))
    const headers = { Accept: 'application/json' }
    let body
    if (method !== 'GET') {
      const csrf = getCsrfToken()
      if (!csrf) throw new DataClientError('Your session must be refreshed before making changes.', { code: 'csrf_required' })
      headers['X-CSRF-Token'] = csrf
      if (method !== 'DELETE') {
        headers['Content-Type'] = 'application/json'
        body = JSON.stringify(scoped.has(operation) ? args[1] : args[0])
      }
    }
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const response = await fetchImpl(url, { method, headers, body, credentials: 'same-origin', signal: controller.signal,
        cache: 'no-store', redirect: 'error' })
      if (!response.ok) {
        const message = response.status === 401 ? 'Your session has expired. Sign in again.'
          : response.status === 403 ? 'You do not have permission to perform this action.'
          : response.status === 404 ? 'The requested resource was not found.'
          : response.status === 409 ? 'This record has changed. Refresh and try again.'
          : response.status === 429 ? 'Too many requests. Please try again shortly.' : 'The service could not complete this request.'
        throw new DataClientError(message, { status: response.status, code: `http_${response.status}` })
      }
      if (response.status === 204 && operation === 'deleteTank') return null
      if (!(response.headers.get('content-type') || '').includes('application/json')) throw new DataClientError('The service returned an unexpected response.', { code: 'invalid_response' })
      let payload
      try { payload = await response.json() } catch (cause) {
        if (controller.signal.aborted) throw cause
        throw new DataClientError('The service returned invalid JSON.', { code: 'invalid_response', cause })
      }
      const result = validateResponse(operation, payload)
      if (operation === 'getTankSummary' && String(result.tank.id) !== String(id)) {
        throw new DataClientError('The service returned a different tank.', { code: 'invalid_response' })
      }
      if (['getLatestPrediction', 'getPredictionHistory', 'listWaterLogs', 'createWaterLog'].includes(operation)) {
        const items = Array.isArray(result) ? result : result ? [result] : []
        if (items.some(item => String(item.tank_id) !== String(id))) throw new DataClientError('The service returned data for a different tank.', { code: 'invalid_response' })
      }
      return result
    } catch (error) {
      if (error instanceof DataClientError) throw error
      throw new DataClientError(controller.signal.aborted ? 'The request timed out. Please try again.' : 'Unable to reach the service. Please try again.',
        { code: controller.signal.aborted ? 'timeout' : 'network_error', cause: error })
    } finally { clearTimeout(timer) }
  }]))
}

function validateResponse(operation, value) {
  const fail = () => { throw new DataClientError('The service returned incompatible data.', { code: 'invalid_response' }) }
  const identity = (item) => item && typeof item === 'object' && ['string', 'number'].includes(typeof item.id)
  const validLog = item => identity(item) && ['string', 'number'].includes(typeof item.tank_id)
    && Number.isFinite(Date.parse(item.recorded_at)) && ['temperature', 'pH', 'turbidity'].every(key => item[key] === null || Number.isFinite(item[key]))
  const lists = ['listTanks', 'listDevices', 'getPredictionHistory', 'listWaterLogs', 'getAllLogs', 'listAlerts']
  if (lists.includes(operation) && (!Array.isArray(value) || !value.every(identity))) fail()
  if (operation === 'getTankSummary' && (!identity(value?.tank) || !Object.hasOwn(value, 'latest_water_log'))) fail()
  if (['createTank', 'updateTank'].includes(operation) && !identity(value)) fail()
  if (operation === 'createWaterLog' && (!identity(value) || !Number.isFinite(Date.parse(value.recorded_at)))) fail()
  if (operation === 'getLatestPrediction' && value !== null && !identity(value)) fail()
  if (['listWaterLogs', 'getAllLogs'].includes(operation) && !value.every(validLog)) fail()
  if (operation === 'createWaterLog' && !validLog(value)) fail()
  if (operation === 'getTankSummary' && value.latest_water_log !== null && (!validLog(value.latest_water_log) || String(value.latest_water_log.tank_id) !== String(value.tank.id))) fail()
  const forecasts = operation === 'getPredictionHistory' ? value : operation === 'getLatestPrediction' && value ? [value] : []
  for (const forecast of forecasts) {
    if (!Number.isFinite(Date.parse(forecast.predicted_from))) fail()
    for (const hour of [1, 2, 3, 4]) {
      if (!Number.isFinite(Date.parse(forecast[`target_${hour}h`]))) fail()
      for (const metric of ['temperature', 'pH', 'turbidity']) if (forecast[`${metric}_${hour}h`] !== null && !Number.isFinite(forecast[`${metric}_${hour}h`])) fail()
    }
  }
  function inspect(item) {
    if (!item || typeof item !== 'object') return
    if (item.sample_only === true) fail()
    for (const [key, child] of Object.entries(item)) {
      if (/^(temperature|pH|turbidity)(_[1-4]h)?$/.test(key) && child !== null && typeof child !== 'object' && !Number.isFinite(child)) fail()
      if (key === 'value' && child !== null && typeof child === 'number' && !Number.isFinite(child)) fail()
      if ((key === 'recorded_at' || key === 'created_at' || key === 'predicted_from' || /^target_[1-4]h$/.test(key)) && child != null && !Number.isFinite(Date.parse(child))) fail()
      inspect(child)
    }
  }
  inspect(value)
  const tanks = operation === 'listTanks' ? value : operation === 'getTankSummary' ? [value.tank] : []
  for (const tank of tanks) {
    if (typeof tank.name !== 'string' || !tank.device || typeof tank.device.connection !== 'string') fail()
    if (tank.reading && (!tank.reading.metrics || !['temperature', 'ph', 'turbidity'].every((key) => tank.reading.metrics[key]))) fail()
  }
  if (operation === 'getTankSummary' && value.latest_water_log) {
    const reading = value.tank.reading
    if (!reading || !Number.isFinite(Date.parse(reading.observedAt)) || !Number.isFinite(Date.parse(value.latest_water_log.recorded_at))) fail()
    for (const [metricKey, logKey] of [['temperature', 'temperature'], ['ph', 'pH'], ['turbidity', 'turbidity']]) {
      const metric = reading.metrics[metricKey]
      const expected = metric.state === 'valid' && Number.isFinite(metric.value) ? metric.value : null
      if (value.latest_water_log[logKey] !== expected) fail()
    }
    if (value.latest_water_log.ph_provenance !== reading.metrics.ph.provenance) fail()
  }
  return value
}
