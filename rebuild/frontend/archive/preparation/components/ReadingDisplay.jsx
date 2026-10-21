import { metricDefinitions, isUsableMetric, readingStatus, formatSampleTime } from '../presentation.js'
import { Icon } from './Icon.jsx'
import temperatureIcon from '../assets/original/temperature.svg'
import phIcon from '../assets/original/ph.svg'
import turbidityIcon from '../assets/original/turbidity.svg'

const metricIcons = { temperature: temperatureIcon, ph: phIcon, turbidity: turbidityIcon }

export function StatusBadge({ label, tone = 'neutral' }) {
  return (
    <span className={`status-badge tone-${tone}`}>
      <span className="status-dot" />{label}
    </span>
  )
}

export function DeviceBadge({ device }) {
  const states = {
    online: ['Device online', 'good'],
    offline: ['Device offline', 'neutral'],
    unknown: ['Device status unknown', 'neutral'],
  }
  const [label, tone] = states[device.connection] || states.unknown
  return <StatusBadge label={label} tone={tone} />
}

export function MetricDisplay({ definition, metric, historical, compact = false }) {
  const usable = isUsableMetric(metric)
  const invalid = metric && metric.state !== 'missing' && !usable
  let provenance = 'Sample sensor value'
  if (definition.key === 'ph') {
    const labels = {
      default: 'Default pH · not measured',
      estimated: 'Estimated pH · not measured',
    }
    provenance = labels[metric?.provenance] || 'pH provenance unavailable'
  }
  const availability = !usable
    ? (invalid ? 'Invalid reading · value withheld' : 'No reading available')
    : (historical ? 'Last known · not current' : 'Sample value')

  return (
    <div className={`metric metric-${definition.key} ${compact ? 'metric-compact' : ''}`}>
      <div className="metric-label"><span className="metric-icon"><img src={metricIcons[definition.key]} alt="" /></span><span>{definition.label}</span></div>
      <p className={`metric-value ${!usable ? 'unavailable' : ''}`}>
        {usable ? metric.value.toFixed(definition.precision) : '—'} <span>{definition.unit}</span>
      </p>
      <p className={`metric-provenance ${definition.key === 'ph' ? 'ph-provenance' : ''}`}>{provenance}</p>
      <p className={`metric-state ${invalid ? 'text-caution' : ''}`}>{availability}</p>
    </div>
  )
}

export function ReadingMetrics({ tank, compact = false }) {
  const historical = tank.device.connection === 'offline' || tank.reading?.freshness === 'stale'
  // Match the original detail layout: pH and temperature, then a wide turbidity card.
  const definitions = compact ? metricDefinitions : [metricDefinitions[2], metricDefinitions[0], metricDefinitions[1]]
  return (
    <div className={`metrics ${compact ? 'metrics-compact' : ''}`}>
      {definitions.map((definition) => (
        <MetricDisplay key={definition.key} definition={definition}
          metric={tank.reading?.metrics[definition.key]} historical={historical} compact={compact} />
      ))}
    </div>
  )
}

export function ReadingSummary({ tank }) {
  return (
    <div className="reading-summary">
      <StatusBadge {...readingStatus(tank)} />
      <span>
        <Icon name="clock" />
        {tank.reading
          ? <time dateTime={tank.reading.observedAt}>{formatSampleTime(tank.reading.observedAt)}</time>
          : 'No reading time available'}
      </span>
    </div>
  )
}

export function SampleEvaluation({ tank }) {
  // Withhold the supplied quality label when it cannot describe current, complete data.
  // This is display availability, not a water-quality evaluation or thresholds policy.
  const currentAndComplete = tank.reading && tank.device.connection === 'online'
    && tank.reading.freshness === 'fresh'
    && metricDefinitions.every(({ key }) => isUsableMetric(tank.reading.metrics[key]))
  const evaluation = currentAndComplete ? tank.reading.evaluation : null
  return (
    <div className="evaluation">
      <strong>Sample quality evaluation</strong>
      {evaluation ? (
        <>
          <StatusBadge {...evaluation} />
          <p>{evaluation.explanation} This label is sample data, not a frontend calculation or a safety assessment.</p>
        </>
      ) : <p>Unavailable for this sample. Current water quality is unknown.</p>}
    </div>
  )
}
