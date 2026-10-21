import { readdir, readFile } from 'node:fs/promises'
import assert from 'node:assert/strict'

const assets = new URL('../dist/assets/', import.meta.url)
const files = (await readdir(assets)).filter(name => name.endsWith('.js'))
assert.ok(files.length, 'Build the frontend before checking its output.')
for (const name of files) {
  const source = await readFile(new URL(name, assets), 'utf8')
  for (const marker of ['SAMPLE-DEVICE-01', 'Nursery 01', 'Unvalidated illustration', 'Display states', 'Reset workspace']) {
    assert.ok(!source.includes(marker), `Development fixture or controls leaked into ${name}: ${marker}`)
  }
}
const styles = (await readdir(assets)).filter(name => name.endsWith('.css'))
const css = (await Promise.all(styles.map(name => readFile(new URL(name, assets), 'utf8')))).join('\n')
for (const marker of ['.bg-sky-600', '.font-bold', 'grid-cols-2', '240px']) {
  assert.ok(css.includes(marker), `Required design utilities are missing from the build: ${marker}`)
}
console.log(`PASS: ${files.length} production JavaScript files contain no fixture/control markers.`)
