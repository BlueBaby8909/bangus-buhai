// Frontend provider interface only. This does not define backend URLs or response schemas.
export const dataMethods = Object.freeze([
  'listTanks', 'listDevices', 'getTankSummary', 'getLatestPrediction',
  'getPredictionHistory', 'listWaterLogs', 'getAllLogs', 'listAlerts',
  'createTank', 'updateTank', 'deleteTank', 'sendCommand',
])

export class DataClientError extends Error {
  constructor(message, { status, code = 'request_failed', cause } = {}) {
    super(message, { cause })
    this.name = 'DataClientError'
    this.status = status
    this.code = code
  }
}

export function createDataClient(provider) {
  const missing = dataMethods.filter((method) => typeof provider?.[method] !== 'function')
  if (missing.length) throw new TypeError(`Data provider is missing methods: ${missing.join(', ')}`)
  return Object.freeze(Object.fromEntries(dataMethods.map((method) => [method, async (...args) => {
    try {
      return await provider[method](...args)
    } catch (error) {
      if (error instanceof DataClientError) throw error
      throw new DataClientError(error?.message || 'Unable to complete this request.', {
        status: error?.status, code: error?.code || 'request_failed', cause: error,
      })
    }
  }])))
}
