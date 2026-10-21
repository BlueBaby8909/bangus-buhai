import { useRef, useState } from 'react'
import { DeviceBadge, ReadingMetrics, ReadingSummary } from '../components/ReadingDisplay.jsx'
import { PageState } from '../components/PageState.jsx'
import { Icon } from '../components/Icon.jsx'
import { readingStatus } from '../presentation.js'
import deviceAngled from '../assets/original/device-angled.png'
import deviceFront from '../assets/original/device-front.png'

function TankCard({ tank }) {
  const status = readingStatus(tank)
  return (
    <article className="tank-card">
      <div className="tank-card-header">
        <div className="tank-title">
          <span className="tank-symbol"><img src={deviceFront} alt="" /></span>
          <div>
            <h3><a href={`#/tanks/${tank.id}`}>{tank.name}</a></h3>
            <p>{tank.location} · Sample tank</p>
          </div>
        </div>
        <DeviceBadge device={tank.device} />
      </div>
      <ReadingSummary tank={tank} />
      <ReadingMetrics tank={tank} compact />
      <div className="tank-card-footer">
        <span>{status.label === 'Fresh sample' ? 'Sample values · pH provenance shown' : status.explanation}</span>
        <a className="tank-open" href={`#/tanks/${tank.id}`} aria-label={`View ${tank.name}`}>
          View tank <Icon name="arrow" />
        </a>
      </div>
    </article>
  )
}

export function OverviewPage({ view, onReset }) {
  const [search, setSearch] = useState('')
  const [connection, setConnection] = useState('all')
  const searchRef = useRef(null)
  if (view.state !== 'ready') return <PageState kind={view.state} onReset={onReset} />

  const filtered = view.tanks.filter((tank) => (
    `${tank.name} ${tank.location} ${tank.device.id}`.toLowerCase().includes(search.trim().toLowerCase())
    && (connection === 'all' || tank.device.connection === connection)
  ))
  const counts = [
    { label: 'Sample tanks', value: view.tanks.length, icon: 'tank', detail: 'Fictional workspace' },
    { label: 'Devices online', value: view.tanks.filter((tank) => tank.device.connection === 'online').length, icon: 'signal', detail: 'Connectivity only' },
    { label: 'Stale readings', value: view.tanks.filter((tank) => tank.reading?.freshness === 'stale').length, icon: 'clock', detail: 'May overlap offline devices' },
    { label: 'Without readings', value: view.tanks.filter((tank) => !tank.reading).length, icon: 'info', detail: 'No conditions available' },
  ]

  return (
    <>
      <section className="tank-hero" aria-labelledby="overview-heading">
        <div className="hero-content">
          <div className="hero-copy">
            <span className="hero-icon"><Icon name="tank" /></span>
            <p className="eyebrow">YOUR SAMPLE WORKSPACE</p>
            <h1 id="overview-heading">Tank<br />Management</h1>
            <p>A clear view of your sample tanks.</p>
          </div>
          <img className="hero-device" src={deviceAngled} alt="Aquasense Pro device illustration from the original interface" />
        </div>
        <div className="hero-strip">
          <div><span className="hero-status-dot" /><div><strong>Aquasense Pro · Sample preview</strong><p>Fictional readings · no live connection</p></div></div>
          <button className="button hero-action" onClick={() => searchRef.current?.focus()}>Browse tanks <Icon name="arrow" /></button>
        </div>
      </section>
      <section className="summary-grid" aria-label="Sample workspace summary">
        {counts.map((count) => (
          <div className="summary-card" key={count.label}>
            <div><span>{count.label}</span><Icon name={count.icon} /></div>
            <strong>{count.value}</strong><small>{count.detail}</small>
          </div>
        ))}
      </section>
      <section aria-labelledby="tank-list-heading">
        <div className="section-heading">
          <div><h2 id="tank-list-heading">Your sample tanks</h2><p>Open a tank to inspect readings and data quality.</p></div>
          <span className="result-count" role="status">{filtered.length} of {view.tanks.length} tanks</span>
        </div>
        <div className="filters">
          <div className="search-field">
            <label htmlFor="tank-search">Find a sample tank</label>
            <input ref={searchRef} id="tank-search" type="search" placeholder="Search tank, wing, or device…"
              value={search} onChange={(event) => setSearch(event.target.value)} />
          </div>
          <div>
            <label htmlFor="connection-filter">Device connection</label>
            <select id="connection-filter" value={connection} onChange={(event) => setConnection(event.target.value)}>
              <option value="all">All connections</option><option value="online">Online</option>
              <option value="offline">Offline</option><option value="unknown">Unknown</option>
            </select>
          </div>
        </div>
        {filtered.length ? (
          <div className="tank-grid">{filtered.map((tank) => <TankCard key={tank.id} tank={tank} />)}</div>
        ) : (
          <div className="filter-empty">
            <Icon name="tank" /><h3>No matching sample tanks</h3><p>Try another name or connection filter.</p>
            <button className="button" onClick={() => {
              searchRef.current?.focus()
              setSearch('')
              setConnection('all')
            }}>Clear filters</button>
          </div>
        )}
      </section>
      <div className="scope-note">
        <Icon name="info" /><p>Connection status does not describe water quality. Default and estimated pH are always labelled. History, controls, and forecasts are pending later integration.</p>
      </div>
    </>
  )
}
