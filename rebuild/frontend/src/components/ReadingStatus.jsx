import { readingStatus, formatSampleTime } from '../presentation.js'

// Normal readings need no explanatory panel. Exceptions stay visible as concise text.
export default function ReadingStatus({ tank }) {
  const status = readingStatus(tank)
  if (status.label === 'Fresh readings') return null
  return (
    <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
      <span className={status.tone==='caution'?'font-semibold text-amber-800':'font-semibold'}>{status.label}</span>
      {tank.reading && <time dateTime={tank.reading.observedAt}>Last reading: {formatSampleTime(tank.reading.observedAt)}</time>}
    </div>
  )
}
