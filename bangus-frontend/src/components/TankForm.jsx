import { useState } from "react";

const GROWTH_STAGES = ["fry", "fingerling", "juvenile", "adult"];

export default function TankForm({ onSubmit, submitting, error, users = [] }) {
  const [form, setForm] = useState({
    name: "",
    volume_ml: "",
    growth_stage: "fingerling",
    owner_id: "",
  });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      name: form.name,
      volume_ml: Number(form.volume_ml),
      growth_stage: form.growth_stage,
      owner_id: form.owner_id ? Number(form.owner_id) : null,
    });
  };

  return (
    <form className="form" onSubmit={handleSubmit}>
      {error && <div className="form-error">{error}</div>}

      <div className="form-row">
        <label htmlFor="name">Tank name</label>
        <input
          id="name"
          required
          placeholder="e.g. Pond A"
          value={form.name}
          onChange={update("name")}
        />
      </div>

      <div className="form-row">
        <label htmlFor="volume">Volume (mL)</label>
        <input
          id="volume"
          type="number"
          min="0"
          step="any"
          required
          placeholder="e.g. 5000"
          value={form.volume_ml}
          onChange={update("volume_ml")}
        />
      </div>

      <div className="form-row">
        <label htmlFor="stage">Growth stage</label>
        <select id="stage" value={form.growth_stage} onChange={update("growth_stage")}>
          {GROWTH_STAGES.map((stage) => (
            <option key={stage} value={stage}>
              {stage[0].toUpperCase() + stage.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {users.length > 0 && (
        <div className="form-row">
          <label htmlFor="owner">Grower (optional)</label>
          <select id="owner" value={form.owner_id} onChange={update("owner_id")}>
            <option value="">Unassigned</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Adding tank..." : "Add tank"}
        </button>
      </div>
    </form>
  );
}
