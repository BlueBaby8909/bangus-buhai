// Local sample adapter for original UI compatibility. No fetch, WebSocket, or device commands.
// These shapes are provisional display fixtures, not an accepted backend API contract.
import { makeScreenTanks, makeScreenLog, makeScreenHistory, makeScreenForecast, screenAlertFixtures } from './originalFixtures.js'
let scenario = 'ready'
let tanks = makeScreenTanks()
let revision = 0
let nextTank = 5
let resetKey = 0
const listeners = new Set()
const notify = () => { revision += 1; listeners.forEach((listener) => listener()) }
export const subscribe = (listener) => { listeners.add(listener); return () => listeners.delete(listener) }
export const getRevision = () => revision
export const getScenario = () => scenario
export const getResetKey = () => resetKey
export function setScenario(value) { scenario = value; notify() }
export function resetSamples() { tanks = makeScreenTanks(); scenario = 'ready'; nextTank = 5; resetKey += 1; notify() }
function currentTanks() {
  if (scenario === 'empty') return []
  if (scenario === 'ready') return tanks
  const stateTanks = makeScreenTanks(scenario)
  return tanks.map((tank, index) => ({ ...tank, device: { ...tank.device, connection: stateTanks[index % stateTanks.length]?.device.connection || 'unknown' }, reading: stateTanks[index % stateTanks.length]?.reading || null }))
}
async function respond(read) {
  if (scenario === 'loading') return new Promise(() => {}) // Deliberately paused preview, no network request.
  if (scenario === 'error') throw new Error('Unable to load data. Please try again.')
  return structuredClone(read())
}
function findTank(id) {
  const tank = currentTanks().find((item) => String(item.id) === String(id))
  if (!tank) throw new Error('Tank not found.')
  return tank
}
export const api = {
  listTanks: () => respond(() => currentTanks()),
  listDevices: () => respond(() => currentTanks().map((tank) => ({ id: tank.device.id, tank_id: tank.id, name: 'Aquasense Pro', is_online: tank.device.connection === 'online', connection_state: tank.device.connection, sample_only: true }))),
  getTankSummary: (id) => respond(() => { const tank = findTank(id); return { tank, latest_water_log: makeScreenLog(tank) } }),
  getLatestPrediction: (id) => respond(() => makeScreenForecast(findTank(id))),
  getPredictionHistory: (id) => respond(() => [makeScreenForecast(findTank(id)), makeScreenForecast(findTank(id), 1)].filter(Boolean)),
  listWaterLogs: (id) => respond(() => makeScreenHistory(findTank(id))),
  getAllLogs: () => respond(() => currentTanks().flatMap(makeScreenHistory).sort((a, b) => Date.parse(b.recorded_at) - Date.parse(a.recorded_at)).slice(0, 100)),
  listAlerts: () => respond(() => screenAlertFixtures.filter((alert) => {
    const tank=currentTanks().find((item)=>item.id===alert.tank_id)
    if(!tank) return false
    if(alert.type==='AI Forecast') return makeScreenForecast(tank)!==null
    if(alert.category==='Connection') return tank.device.connection==='offline'
    return tank.reading?.freshness==='stale' && tank.device.connection==='online'
  })),
  createTank: (data) => respond(() => {
    const id = `sample-tank-${nextTank++}`
    const tank = { ...data, id, location: 'Unassigned', sample_only: true, device: { id: `SAMPLE-UNASSIGNED-${id}`, connection: 'unknown' }, reading: null }
    tanks = [...tanks, tank]; notify(); return tank
  }),
  updateTank: (id, data) => respond(() => {
    const tank = findTank(id)
    tanks = tanks.map((item) => item.id === id ? { ...item, ...data } : item)
    notify(); return { ...tank, ...data }
  }),
  deleteTank: (id) => respond(() => { tanks = tanks.filter((tank) => tank.id !== id); notify(); return { sample_only: true } }),
  sendCommand: () => respond(() => ({ sample_only: true, sent: false })),
  createWaterLog: () => Promise.reject(new Error('Manual entries require a connected backend.')),
}
