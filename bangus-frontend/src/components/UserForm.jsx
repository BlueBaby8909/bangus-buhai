import { useState } from "react";

export default function UserForm({ onSubmit, submitting, error }) {
  const [form, setForm] = useState({ name: "", email: "" });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <form className="form" onSubmit={handleSubmit}>
      {error && <div className="form-error">{error}</div>}

      <div className="form-row">
        <label htmlFor="uname">Name</label>
        <input id="uname" required value={form.name} onChange={update("name")} />
      </div>

      <div className="form-row">
        <label htmlFor="uemail">Email</label>
        <input
          id="uemail"
          type="email"
          required
          value={form.email}
          onChange={update("email")}
        />
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Adding..." : "Add grower"}
        </button>
      </div>
    </form>
  );
}
