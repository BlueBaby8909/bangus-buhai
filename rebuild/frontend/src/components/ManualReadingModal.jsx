import { useState } from 'react'
import ModalFrame from './ModalFrame.jsx'
import { api } from '../api/client.js'
import { manualReadingPayload } from '../services/manualReading.js'

export default function ManualReadingModal({ tankId, onClose, onSuccess }) {
  const [values, setValues] = useState({ temperature: '', pH: '', turbidity: '', recorded_at: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const fields = [
    { key: 'temperature', label: 'Temperature (°C)' },
    { key: 'pH', label: 'pH', min: 0, max: 14 },
    { key: 'turbidity', label: 'Turbidity (NTU)', min: 0 },
  ]
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await api.createWaterLog(tankId, manualReadingPayload(values))
      onSuccess()
    } catch (error) { setError(error.message || 'The reading could not be saved.') }
    finally { setBusy(false) }
  }
  return <ModalFrame label="Add manual reading" onClose={onClose} busy={busy}>
    <div className="bg-white rounded-[24px] p-6 md:p-8">
      <div className="flex items-center justify-between gap-4 mb-4">
        <h2 className="text-xl font-bold text-slate-900">Add Reading</h2>
        <button type="button" disabled={busy} aria-label="Close dialog" onClick={onClose} className="rounded-full bg-slate-50 px-3">×</button>
      </div>
      <p className="text-sm text-slate-500 mb-5">Enter observations taken independently of the device. Blank parameters remain unavailable. pH is recorded as manually entered.</p>
      {error && <p role="alert" className="text-red-700 mb-4">{error}</p>}
      <form onSubmit={submit} aria-busy={busy}>
        <fieldset disabled={busy} className="flex flex-col gap-4">
          {fields.map(({ key, label, min, max }) => <div key={key}>
            <label htmlFor={`manual-${key}`} className="block text-sm font-bold text-slate-900 mb-2">{label}</label>
            <input id={`manual-${key}`} type="number" step="any" min={min} max={max} value={values[key]}
              onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3" />
          </div>)}
          <div>
            <label htmlFor="manual-time" className="block text-sm font-bold text-slate-900 mb-2">Observation time (your local time)</label>
            <input id="manual-time" type="datetime-local" required value={values.recorded_at}
              onChange={event => setValues(current => ({ ...current, recorded_at: event.target.value }))}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3" />
          </div>
          <button type="submit" className="rounded-2xl bg-sky-600 text-white px-5 py-3 font-bold">{busy ? 'Saving…' : 'Save Reading'}</button>
        </fieldset>
      </form>
    </div>
  </ModalFrame>
}
