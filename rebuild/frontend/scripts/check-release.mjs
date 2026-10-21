import { loadEnv } from 'vite'
import { createBackendClient } from '../src/services/backendClient.js'

const env = { ...loadEnv('production', process.cwd(), 'VITE_'), ...process.env }
const required = ['listTanks', 'listDevices', 'getTankSummary', 'listWaterLogs', 'getAllLogs', 'getLatestPrediction', 'getPredictionHistory', 'listAlerts', 'createTank', 'updateTank', 'deleteTank', 'createWaterLog']
const routes = JSON.parse(env.VITE_API_ROUTES || '{}')
if (!env.VITE_API_BASE_URL || required.some(operation => !routes[operation])) {
  throw new Error('Release blocked: configure the API base and all reviewed screen operation routes. See INTEGRATION.md.')
}
if (!env.VITE_API_BASE_URL.startsWith('/') || env.VITE_API_BASE_URL.startsWith('//')) throw new Error('Release API base must be a same-origin absolute path.')
createBackendClient({ baseUrl: env.VITE_API_BASE_URL, routes, origin: 'https://deployment.invalid' })
console.log('API route configuration is structurally valid. This does not verify backend availability, authentication, or release acceptance.')
