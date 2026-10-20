import { formatSampleTime } from '../presentation.js'
import { Icon } from './Icon.jsx'

export function PreviewControls({ scenario, onChange, scenarios, referenceTime }) {
  return (
    <section className="preview-panel" aria-label="Sample data preview">
      <div className="sample-notice">
        <Icon name="info" />
        <div><strong>Sample data only</strong><p>Fictional readings. No devices or backend connected.</p></div>
        <span className="sample-tag">DEMO</span>
      </div>
      <details className="preview-controls">
        <summary>Preview scenarios</summary>
        <div className="preview-fields">
          <div>
            <label htmlFor="scenario">Sample scenario</label>
            <select id="scenario" value={scenario} onChange={(event) => onChange(event.target.value)} aria-describedby="scenario-description">
              {scenarios.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </div>
          <p id="scenario-description">{scenarios.find((item) => item.value === scenario)?.description}</p>
        </div>
        <p className="preview-clock">Fixed sample clock: {formatSampleTime(referenceTime)}. Freshness and quality labels are supplied examples; this UI does not evaluate water quality.</p>
      </details>
    </section>
  )
}
