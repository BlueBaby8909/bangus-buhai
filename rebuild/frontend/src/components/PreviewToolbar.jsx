import { scenarios } from '../data/sampleData.js'

export function PreviewToolbar({ scenario, onChange, onReset }) {
  return (
    <div className="preview-toolbar">
      <span className="preview-mode">Sample data</span>
      <details className="preview-options">
        <summary>Preview options</summary>
        <div className="preview-options-panel">
          <label htmlFor="preview-scenario">Data state</label>
          <select id="preview-scenario" value={scenario} onChange={(event)=>onChange(event.target.value)}>
            {scenarios.map((item)=><option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <button type="button" onClick={onReset}>Reset samples</button>
        </div>
      </details>
      <span role="status" className="sr-only">{scenarios.find((item)=>item.value===scenario)?.label}</span>
    </div>
  )
}
