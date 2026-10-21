import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { build } from 'vite'
import react from '@vitejs/plugin-react'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

// Render the actual production-transformed components, without a browser/backend.
const require = createRequire(import.meta.url)
async function component(name) {
  const bundle = await build({ configFile: false, logLevel: 'silent', plugins: [react()], build: {
    write: false, lib: { entry: `src/components/${name}.jsx`, formats: ['es'] },
    rolldownOptions: { external: ['react', 'react/jsx-runtime'] },
  } })
  const output = (Array.isArray(bundle) ? bundle[0] : bundle).output
  let code = output.find(item => item.type === 'chunk' && item.isEntry).code
  for (const specifier of ['react/jsx-runtime', 'react']) code = code.replaceAll(`"${specifier}"`, JSON.stringify(pathToFileURL(require.resolve(specifier)).href))
  return import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)
}
const { default: MetricCard } = await component('MetricCard')
const { default: ForecastCard } = await component('ForecastCard')
const { RequestError } = await component('RequestState')

test('metric card retains valid zero and withholds missing/non-finite values', () => {
  const zero = renderToStaticMarkup(createElement(MetricCard, { label: 'Temp', value: 0, unit: '°C', description: 'Temperature', icon: '/temperature.svg' }))
  assert.ok(zero.includes('0.0°C'))
  for (const value of [null, undefined, NaN, Infinity, '28']) {
    const markup = renderToStaticMarkup(createElement(MetricCard, { label: 'Temp', value, icon: '/temperature.svg' }))
    assert.ok(markup.includes('—'))
    assert.ok(!markup.includes('NaN'))
  }
})

test('forecast card uses supplied target and provenance rather than inventing either', () => {
  const markup = renderToStaticMarkup(createElement(ForecastCard, { hour: 1, prediction: {
    temperature_1h: 0, pH_1h: null, turbidity_1h: 12, ph_provenance: 'unknown', target_1h: '2026-10-21T10:00:00Z',
  } }))
  assert.ok(markup.includes('pH source unavailable'))
  assert.ok(markup.includes('2026-10-21T10:00:00Z'))
  assert.ok(markup.includes('0.0'))
  assert.ok(!markup.includes('Estimated pH'))
})

test('request errors escape supplied text and expose a retry button', () => {
  const markup = renderToStaticMarkup(createElement(RequestError, { message: '<script>bad</script>', onRetry() {} }))
  assert.ok(markup.includes('role="alert"'))
  assert.ok(markup.includes('&lt;script&gt;'))
  assert.ok(markup.includes('Try again'))
})
