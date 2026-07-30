import { useState } from "react";

export default function WaterLogForm({ onSubmit, submitting, error }) {
  const [form, setForm] = useState({ temperature: "", pH: "", turbidity: "", notes: "" });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      temperature: Number(form.temperature),
      pH: Number(form.pH),
      turbidity: Number(form.turbidity),
      notes: form.notes || null,
    });
  };

  return (
    <form className="form" onSubmit={handleSubmit}>
      {error && <div className="form-error">{error}</div>}

      <div className="form-grid">
        <div className="form-row">
          <label htmlFor="temperature">Temperature (&deg;C)</label>
          <input
            id="temperature"
            type="number"
            step="any"
            required
            value={form.temperature}
            onChange={update("temperature")}
          />
        </div>
        <div className="form-row">
          <label htmlFor="pH">pH</label>
          <input
            id="pH"
            type="number"
            step="any"
            required
            value={form.pH}
            onChange={update("pH")}
          />
        </div>
      </div>

      <div className="form-row">
        <label htmlFor="turbidity">Turbidity (NTU)</label>
        <input
          id="turbidity"
          type="number"
          step="any"
          min="0"
          required
          value={form.turbidity}
          onChange={update("turbidity")}
        />
      </div>

      <div className="form-row">
        <label htmlFor="notes">Notes (optional)</label>
        <textarea
          id="notes"
          rows={2}
          placeholder="e.g. after rain, water looked cloudy"
          value={form.notes}
          onChange={update("notes")}
        />
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Logging..." : "Log reading"}
        </button>
      </div>
    </form>
  );
}
