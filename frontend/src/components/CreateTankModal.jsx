import { useState } from "react";
import { api } from "../api/client";

export default function CreateTankModal({ onClose, onSuccess }) {
  const [name, setName] = useState("");
  const [volumeMl, setVolumeMl] = useState(10000);
  const [growthStage, setGrowthStage] = useState("grow-out");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
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
      // growth_stage in backend enum is 'fry', 'fingerling', 'juvenile', 'adult'
      // If we use 'grow-out', we need to ensure it matches backend or backend might reject it.
      // Let's stick to the backend enums: fry, fingerling, juvenile, adult
      await api.createTank({
        name: name.trim(),
        volume_ml: parseFloat(volumeMl),
        growth_stage: growthStage
      });
      onSuccess();
    } catch (err) {
      setError(err.message || "Failed to create tank.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <div className="bg-white rounded-[24px] shadow-[0_8px_32px_rgba(15,23,42,0.1)] w-full max-w-md p-[24px] md:p-[32px] transform transition-all">
        <div className="flex justify-between items-center mb-[24px]">
          <h2 className="text-[20px] md:text-[24px] font-bold text-slate-900">Add New Tank</h2>
          <button onClick={onClose} className="w-[32px] h-[32px] rounded-full bg-slate-50 flex items-center justify-center hover:bg-slate-100 transition-colors">
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

        <form onSubmit={handleSubmit} className="flex flex-col gap-[20px]">
          <div className="flex flex-col gap-[8px]">
            <label className="text-[14px] font-bold text-slate-900">Tank Name</label>
            <input 
              type="text" 
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Tank 01"
              className="px-[16px] py-[12px] rounded-[12px] bg-slate-50 border border-slate-200 focus:border-sky-500 focus:bg-white focus:outline-none transition-colors text-[15px] font-medium text-slate-900 placeholder:text-slate-400"
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

          <div className="flex flex-col gap-[8px]">
            <label className="text-[14px] font-bold text-slate-900">Growth Stage</label>
            <div className="relative">
              <select 
                value={growthStage}
                onChange={(e) => setGrowthStage(e.target.value)}
                className="w-full px-[16px] py-[12px] rounded-[12px] bg-slate-50 border border-slate-200 focus:border-sky-500 focus:bg-white focus:outline-none transition-colors text-[15px] font-medium text-slate-900 appearance-none"
              >
                <option value="fry">Fry</option>
                <option value="fingerling">Fingerling</option>
                <option value="juvenile">Juvenile</option>
                <option value="adult">Adult (Grow-out)</option>
              </select>
              <div className="absolute right-[16px] top-1/2 -translate-y-1/2 pointer-events-none">
                <svg width="12" height="8" viewBox="0 0 12 8" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M1 1.5L6 6.5L11 1.5" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="mt-[8px] w-full py-[14px] bg-sky-500 hover:bg-sky-600 text-white rounded-[16px] font-bold text-[15px] shadow-[0_4px_12px_rgba(14,165,233,0.3)] transition-all disabled:opacity-70 disabled:hover:bg-sky-500"
          >
            {loading ? "Creating..." : "Create Tank"}
          </button>
        </form>
      </div>
    </div>
  );
}
