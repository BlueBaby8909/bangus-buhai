import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import TankCard from "../components/TankCard";
import TankForm from "../components/TankForm";
import Modal from "../components/Modal";
import WaveDivider from "../components/WaveDivider";

export default function Dashboard() {
  const [tanks, setTanks] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const loadTanks = () => {
    setLoading(true);
    api
      .listTanks({ limit: 100 })
      .then(setTanks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTanks();
    api.listDevices().then(setDevices).catch(() => {});
  }, []);

  const handleCreate = async (data) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.createTank(data);
      setShowForm(false);
      loadTanks();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add tank.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-header__eyebrow">Grow-out tanks</div>
          <h1>Your ponds, at a glance</h1>
          <p>Track water quality and ML predictions across every tank.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          + Add tank
        </button>
      </div>
      <WaveDivider />

      {loading && <div className="loading-strip">Loading tanks...</div>}

      {!loading && tanks.length === 0 && (
        <div className="empty-state">
          <h3>No tanks yet</h3>
          <p>Add your first tank to start logging water readings.</p>
        </div>
      )}

      <div className="tank-grid">
        {tanks.map((tank) => (
          <TankCard 
            key={tank.id} 
            tank={tank} 
            device={devices.find(d => d.tank_id === tank.id)} 
          />
        ))}
      </div>

      {showForm && (
        <Modal title="Add a tank" onClose={() => setShowForm(false)}>
          <TankForm onSubmit={handleCreate} submitting={submitting} error={error} />
        </Modal>
      )}
    </>
  );
}
