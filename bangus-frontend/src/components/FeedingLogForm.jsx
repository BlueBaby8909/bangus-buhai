import { useState } from "react";

const FEED_TYPES = ["pellet", "natural", "supplement"];

export default function FeedingLogForm({ onSubmit, submitting, error }) {
  const [form, setForm] = useState({ feed_type: "pellet", amount_grams: "", notes: "" });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      feed_type: form.feed_type,
      amount_grams: Number(form.amount_grams),
      notes: form.notes || null,
    });
  };

  return (
    <form className="form" onSubmit={handleSubmit}>
      {error && <div className="form-error">{error}</div>}

      <div className="form-row">
        <label>Feed type</label>
        <div className="pill-select">
          {FEED_TYPES.map((type) => (
            <button
              type="button"
              key={type}
              className={`pill-option ${form.feed_type === type ? "selected" : ""}`}
              onClick={() => setForm({ ...form, feed_type: type })}
            >
              {type[0].toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="form-row">
        <label htmlFor="amount">Amount (grams)</label>
        <input
          id="amount"
          type="number"
          min="0"
          step="any"
          required
          value={form.amount_grams}
          onChange={update("amount_grams")}
        />
      </div>

      <div className="form-row">
        <label htmlFor="fnotes">Notes (optional)</label>
        <textarea
          id="fnotes"
          rows={2}
          placeholder="e.g. split into two feedings"
          value={form.notes}
          onChange={update("notes")}
        />
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Logging..." : "Log feeding"}
        </button>
      </div>
    </form>
  );
}
