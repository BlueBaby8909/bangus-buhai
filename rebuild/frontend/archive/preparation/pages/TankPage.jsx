import { DeviceBadge, ReadingMetrics, ReadingSummary, SampleEvaluation } from '../components/ReadingDisplay.jsx'
import { PageState } from '../components/PageState.jsx'
import { Icon } from '../components/Icon.jsx'
import { readingStatus, formatSampleTime } from '../presentation.js'
import deviceFront from '../assets/original/device-front.png'

export function TankPage({ tank, view, onReset }) {
  if (view.state !== 'ready') {
    return (
      <>
        <a className="back-link" href="#/tanks"><Icon name="back" /> All sample tanks</a>
        <PageState kind={view.state} onReset={onReset} />
      </>
    )
  }
  if (!tank) return <PageState kind="not-found" />
  const status = readingStatus(tank)

  return (
    <>
      <a className="back-link" href="#/tanks"><Icon name="back" /> All sample tanks</a>
      <div className="page-heading">
        <div>
          <p className="eyebrow">{tank.location.toUpperCase()} · SAMPLE TANK</p>
          <h1>{tank.name}</h1><p>{tank.description}. All readings below are fictional.</p>
        </div>
        <DeviceBadge device={tank.device} />
      </div>
      <section className="device-banner" aria-label="Sample monitoring device">
        <span className="device-art"><img src={deviceFront} alt="" /></span>
        <div><strong>Aquasense Pro</strong><p>Sample device · Temperature, pH, and turbidity</p></div>
        <DeviceBadge device={tank.device} />
      </section>
      <section className={`reading-notice tone-${status.tone}`} aria-label="Reading availability">
        <Icon name={status.tone === 'caution' ? 'warning' : 'info'} />
        <div><strong>{status.label}</strong><p>{status.explanation}</p></div>
      </section>
      <section className="readings-panel" aria-labelledby="readings-heading">
        <div className="section-heading">
          <div><h2 id="readings-heading">Water readings</h2><p>Temperature, turbidity, and pH at a glance.</p></div>
        </div>
        <ReadingSummary tank={tank} />
        <ReadingMetrics tank={tank} />
        <SampleEvaluation tank={tank} />
      </section>
      <div className="detail-grid">
        <section className="detail-panel" aria-labelledby="device-heading">
          <div className="panel-title"><Icon name="signal" /><h2 id="device-heading">Device details</h2></div>
          <dl>
            <div><dt>Sample device ID</dt><dd className="device-id">{tank.device.id}</dd></div>
            <div><dt>Connection</dt><dd><DeviceBadge device={tank.device} /></dd></div>
            <div><dt>Last sample reading</dt><dd>{formatSampleTime(tank.reading?.observedAt)}</dd></div>
            <div><dt>Source</dt><dd>Local sample fixtures · no live connection</dd></div>
          </dl>
        </section>
        <section className="detail-panel provenance-panel" aria-labelledby="provenance-heading">
          <div className="panel-title"><Icon name="ph" /><h2 id="provenance-heading">Understanding pH</h2></div>
          <p>Default pH is a placeholder. Estimated pH is an estimate. Neither is a physical pH measurement.</p>
          <p>These samples do not establish sensor accuracy, hatchery suitability, or validated forecast performance.</p>
          <span className="provenance-tag">DEFAULT / ESTIMATED · NOT MEASURED</span>
        </section>
      </div>
      <div className="scope-note">
        <Icon name="info" /><p>This is a reading-display preview. Authentication, live updates, history, manual input, relay commands, forecasts, and notifications are not connected.</p>
      </div>
    </>
  )
}
