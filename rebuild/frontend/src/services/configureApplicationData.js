import { configureDataSource } from './dataSource.js'
import { createBackendClient } from './backendClient.js'

export async function configureApplicationData() {
  // Vite removes the fixture import from production builds.
  if (import.meta.env.DEV && import.meta.env.VITE_ENABLE_SAMPLES === 'true') {
    const samples = await import('../data/sampleClient.js')
    configureDataSource({ mode: 'sample', provider: samples.api, preview: samples })
    return
  }
  const routes = JSON.parse(import.meta.env.VITE_API_ROUTES || '{}')
  configureDataSource({ mode: 'backend', provider: createBackendClient({ baseUrl: import.meta.env.VITE_API_BASE_URL, routes }) })
}
