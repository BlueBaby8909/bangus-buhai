import { createDataClient, dataMethods } from './createDataClient.js'

let source

// Configure once before mounting React. Backend adapters must map reviewed payloads
// into the current screen model; sample data is never an error fallback.
export function configureDataSource({ mode, provider, preview }) {
  if (!['sample', 'backend'].includes(mode)) throw new TypeError('Data mode must be sample or backend.')
  const client = createDataClient(provider)
  source = Object.freeze({ mode, client, preview: mode === 'sample' ? preview : undefined })
}

function currentSource() {
  if (!source) throw new Error('Configure the frontend data source before mounting the app.')
  return source
}

export const api = Object.freeze(Object.fromEntries(dataMethods.map((method) => [method,
  (...args) => currentSource().client[method](...args),
])))
export const getDataMode = () => currentSource().mode
export const subscribe = (listener) => currentSource().preview?.subscribe(listener) || (() => {})
export const getRevision = () => currentSource().preview?.getRevision() ?? 0
export const getResetKey = () => currentSource().preview?.getResetKey() ?? 0
export const getScenario = () => currentSource().preview?.getScenario() ?? 'backend'
export const setScenario = (value) => currentSource().preview?.setScenario(value)
export const resetSamples = () => currentSource().preview?.resetSamples()
