import { useState, useEffect } from "react";
import { api } from "../api/client";
import { useNavigate } from "react-router-dom";

export default function EditTankModal({ tank, onClose, onSuccess }) {
  const navigate = useNavigate();
  const [name, setName] = useState(tank?.name || "");
  const [volumeMl, setVolumeMl] = useState(tank?.volume_ml || 10000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Tank name is required.");
      return;
    }
    if (volumeMl <= 0) {
      setError("Volume must be greater than 0.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.updateTank(tank.id, {
        name: name.trim(),
        volume_ml: parseFloat(volumeMl)
      });
      onSuccess();
    } catch (err) {
      setError(err.message || "Failed to update tank.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.deleteTank(tank.id);
      // After deleting, navigate back to the dashboard/tanks list
      navigate("/tanks", { replace: true });
    } catch (err) {
      setError(err.message || "Failed to delete tank.");
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white rounded-[24px] shadow-[0_8px_32px_rgba(15,23,42,0.1)] w-full max-w-md p-[24px] md:p-[32px] transform transition-all">
        <div className="flex justify-between items-center mb-[24px]">
          <h2 className="text-[20px] md:text-[24px] font-bold text-slate-900">Tank Settings</h2>
          <button onClick={onClose} disabled={loading} className="w-[32px] h-[32px] rounded-full bg-slate-50 flex items-center justify-center hover:bg-slate-100 transition-colors disabled:opacity-50">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M13 1L1 13M1 1L13 13" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-[16px] p-[12px] bg-red-50 text-red-600 rounded-[12px] text-[14px] font-medium border border-red-100">
            {error}
          </div>
        )}

        <form onSubmit={handleUpdate} className="flex flex-col gap-[20px]">
          <div className="flex flex-col gap-[8px]">
            <label className="text-[14px] font-bold text-slate-900">Tank Name</label>
            <input 
              type="text" 
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="px-[16px] py-[12px] rounded-[12px] bg-slate-50 border border-slate-200 focus:border-sky-500 focus:bg-white focus:outline-none transition-colors text-[15px] font-medium text-slate-900"
            />
          </div>

          <div className="flex flex-col gap-[8px]">
            <label className="text-[14px] font-bold text-slate-900">Volume (mL)</label>
            <input 
              type="number" 
              value={volumeMl}
              onChange={(e) => setVolumeMl(e.target.value)}
              min="1"
              className="px-[16px] py-[12px] rounded-[12px] bg-slate-50 border border-slate-200 focus:border-sky-500 focus:bg-white focus:outline-none transition-colors text-[15px] font-medium text-slate-900"
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="mt-[8px] w-full py-[14px] bg-slate-900 hover:bg-slate-800 text-white rounded-[16px] font-bold text-[15px] shadow-sm transition-colors disabled:opacity-70"
          >
            {loading ? "Saving..." : "Save Changes"}
          </button>
        </form>

        <div className="mt-[32px] pt-[24px] border-t border-slate-100">
          <div className="flex flex-col gap-[12px]">
            <div>
              <h3 className="font-bold text-slate-900 text-[15px]">Danger Zone</h3>
              <p className="text-slate-500 text-[13px] mt-[2px]">Deleting this tank will permanently remove all associated water logs and predictions.</p>
            </div>
            
            {showConfirmDelete ? (
              <div className="flex flex-col gap-[8px] bg-red-50 p-[12px] rounded-[16px] border border-red-100">
                <p className="font-bold text-red-600 text-[13px] text-center">Are you absolutely sure?</p>
                <div className="flex gap-[8px]">
                  <button 
                    onClick={() => setShowConfirmDelete(false)}
                    disabled={loading}
                    className="flex-1 py-[10px] bg-white text-slate-700 border border-slate-200 rounded-[12px] font-bold text-[13px] hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={handleDelete}
                    disabled={loading}
                    className="flex-1 py-[10px] bg-red-600 text-white rounded-[12px] font-bold text-[13px] shadow-[0_2px_8px_rgba(220,38,38,0.3)] hover:bg-red-700"
                  >
                    Yes, Delete
                  </button>
                </div>
              </div>
            ) : (
              <button 
                onClick={() => setShowConfirmDelete(true)}
                disabled={loading}
                className="w-full py-[12px] bg-white text-red-600 border border-red-100 rounded-[16px] font-bold text-[14px] hover:bg-red-50 transition-colors"
              >
                Delete Tank
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
