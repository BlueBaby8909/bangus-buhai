import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import Modal from "../components/Modal";
import UserForm from "../components/UserForm";
import WaveDivider from "../components/WaveDivider";

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    api
      .listUsers({ limit: 100 })
      .then(setUsers)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCreate = async (data) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.createUser(data);
      setShowForm(false);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add grower.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Remove this grower?")) return;
    await api.deleteUser(id);
    load();
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-header__eyebrow">Growers</div>
          <h1>Who's tending the ponds</h1>
          <p>Assign tanks to a grower so everyone knows who's responsible for what.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Add grower
        </button>
      </div>
      <WaveDivider />

      {loading && <div className="loading-strip">Loading growers...</div>}

      {!loading && users.length === 0 && (
        <div className="empty-state">
          <h3>No growers yet</h3>
          <p>Add a grower to start assigning tanks to them.</p>
        </div>
      )}

      {!loading && users.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Joined</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td className="row-actions">
                  <button className="btn-danger" style={{ border: "none", background: "none", cursor: "pointer" }} onClick={() => handleDelete(u.id)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showForm && (
        <Modal title="Add a grower" onClose={() => setShowForm(false)}>
          <UserForm onSubmit={handleCreate} submitting={submitting} error={error} />
        </Modal>
      )}
    </>
  );
}
