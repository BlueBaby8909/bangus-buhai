import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createBackendClient } from '../src/services/backendClient.js'
import { createRequestGate } from '../src/services/requestGate.js'
import { availableMetricCount, connectionLabel } from '../src/presentation.js'
import { logsCsv } from '../src/api/exportCsv.js'
import { manualReadingPayload } from '../src/services/manualReading.js'

const origin = 'https://hatchery.example'
const settings = { origin, baseUrl: '/api/', routes: { listDevices: 'devices', getTankSummary: 'tanks/{id}/summary', createTank: 'tanks', deleteTank: 'tanks/{id}' } }
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })

test('unconfigured operations never perform requests or fabricate success', async () => {
  let called = false
  const client = createBackendClient({ origin, fetchImpl: () => { called = true } })
  await assert.rejects(client.listTanks(), { code: 'not_configured' })
  assert.equal(called, false)
})

test('reject cross-origin configuration, route escapes and missing identity placeholders', () => {
  assert.throws(() => createBackendClient({ ...settings, baseUrl: 'https://other.example' }))
  for (const route of ['/devices', '../devices', 'https://other.example/devices', 'devices?token=secret']) {
    assert.throws(() => createBackendClient({ ...settings, routes: { listDevices: route } }))
  }
  assert.throws(() => createBackendClient({ ...settings, routes: { getTankSummary: 'summary' } }))
})

test('requests use same-origin cookies, no cache, no redirects and encoded resource identity', async () => {
  let requested
  const client = createBackendClient({ ...settings, fetchImpl: async (url, options) => {
    requested = { url, options }
    return json({ tank: { id: 'tank/a', name: 'Nursery', device: { connection: 'unknown' }, reading: null }, latest_water_log: null })
  } })
  await client.getTankSummary('tank/a', { limit: 48 })
  assert.equal(requested.url.pathname, '/api/tanks/tank%2Fa/summary')
  assert.equal(requested.url.searchParams.get('limit'), '48')
  assert.equal(requested.options.credentials, 'same-origin')
  assert.equal(requested.options.cache, 'no-store')
  assert.equal(requested.options.redirect, 'error')
})

test('HTTP authentication, permission, rate and server failures stay explicit', async () => {
  for (const status of [401, 403, 404, 409, 429, 500]) {
    const client = createBackendClient({ ...settings, fetchImpl: async () => json({ detail: 'private server error' }, status) })
    await assert.rejects(client.listDevices(), error => error.status === status && !error.message.includes('private'))
  }
})

test('HTML responses, wrong collection types, nonnumeric metrics and backend fixtures are rejected', async () => {
  const cases = [new Response('<html>login</html>', { headers: { 'Content-Type': 'text/html' } }), json({ items: [] }),
    json([{ id: 'a', sample_only: true }]), json([{ id: 'a', temperature: '28' }])]
  for (const response of cases) {
    const client = createBackendClient({ ...settings, fetchImpl: async () => response })
    await assert.rejects(client.listDevices(), { code: 'invalid_response' })
  }
})

test('bounded timeout aborts stalled transport', async () => {
  const client = createBackendClient({ ...settings, timeoutMs: 10, fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true })
  }) })
  await assert.rejects(client.listDevices(), { code: 'timeout' })
})

test('network errors cannot become empty successful collections', async () => {
  const client = createBackendClient({ ...settings, fetchImpl: async () => { throw new Error('offline') } })
  await assert.rejects(client.listDevices(), { code: 'network_error' })
})

test('summary identities and invalid metric representations cannot reach the screen', async () => {
  const summary = { tank: { id: 'tank-1', name: 'Nursery', device: { connection: 'online' }, reading: {
    observedAt: '2026-10-21T10:00:00Z', metrics: {
      temperature: { state: 'invalid', value: 28 }, ph: { state: 'valid', value: 8, provenance: 'default' }, turbidity: { state: 'valid', value: 0 },
    },
  } }, latest_water_log: { id: 'log-1', tank_id: 'tank-1', recorded_at: '2026-10-21T10:00:00Z', temperature: 28, pH: 8, turbidity: 0, ph_provenance: 'default' } }
  const client = createBackendClient({ ...settings, fetchImpl: async () => json(summary) })
  await assert.rejects(client.getTankSummary('tank-1'), { code: 'invalid_response' })
  summary.latest_water_log.temperature = null
  await assert.rejects(client.getTankSummary('different-tank'), { code: 'invalid_response' })
  assert.equal((await client.getTankSummary('tank-1')).latest_water_log.turbidity, 0)
})

test('writes require CSRF token; delete accepts 204 without parsing JSON', async () => {
  let called = false
  const client = createBackendClient({ ...settings, getCsrfToken: () => null, fetchImpl: async () => { called = true } })
  await assert.rejects(client.createTank({ name: 'Nursery' }), { code: 'csrf_required' })
  assert.equal(called, false)
  const authorized = createBackendClient({ ...settings, getCsrfToken: () => 'csrf-token', fetchImpl: async (_url, options) => {
    assert.equal(options.method, 'DELETE')
    assert.equal(options.headers['X-CSRF-Token'], 'csrf-token')
    return new Response(null, { status: 204 })
  } })
  assert.equal(await authorized.deleteTank('tank-1'), null)
})

test('request gate discards delayed responses after newer load or unmount', () => {
  const gate = createRequestGate()
  const old = gate.begin()
  const current = gate.begin()
  assert.equal(old(), false)
  assert.equal(current(), true)
  gate.cancel()
  assert.equal(current(), false)
})

test('availability preserves zero and unknown connection stays unknown', () => {
  assert.equal(availableMetricCount({ temperature: 0, pH: null, turbidity: NaN }), 1)
  assert.equal(availableMetricCount(null), 0)
  assert.equal(connectionLabel({ is_online: false, connection_state: 'unknown' }), 'Device status unknown')
})

test('CSV neutralizes spreadsheet formulas while preserving numeric negatives and unknown relay', () => {
  const csv = logsCsv([{ id: '\t=HYPERLINK("bad")', tank_id: '@formula', temperature: -2, relay_on: null }])
  assert.ok(csv.includes("'\t=HYPERLINK"))
  assert.ok(csv.includes("'@formula"))
  assert.ok(csv.includes('"-2"'))
  assert.ok(csv.includes('"Unknown"'))
})

test('manual readings preserve missing versus zero and manual pH provenance', () => {
  const values = { temperature: '', pH: '8', turbidity: '0', recorded_at: '2026-10-21T10:00:00Z' }
  const now = Date.parse('2026-10-21T11:00:00Z')
  const payload = manualReadingPayload(values, now)
  assert.equal(payload.temperature, null)
  assert.equal(payload.turbidity, 0)
  assert.equal(payload.ph_provenance, 'manual')
  assert.equal(manualReadingPayload({ ...values, pH: '' }, now).ph_provenance, 'unknown')
  for (const invalid of [{ ...values, pH: '15' }, { ...values, turbidity: '-1' }, { ...values, recorded_at: 'invalid' },
    { ...values, recorded_at: '2026-10-22T10:00:00Z' }, { ...values, pH: '', turbidity: '' }]) assert.throws(() => manualReadingPayload(invalid, now))
})
