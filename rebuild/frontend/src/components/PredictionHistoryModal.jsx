import { RequestError } from "./RequestState.jsx";
import { phProvenanceLabel, formatTimestamp } from "../presentation.js";
import ModalFrame from './ModalFrame.jsx';
import { useState, useEffect } from "react";
import { api } from "../api/client";

export default function PredictionHistoryModal({ tankId, onClose }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [revision,setRevision] = useState(0);
  const retry = () => {setLoading(true);setError(null);setRevision(value=>value+1)};

  useEffect(() => {
    let mounted = true;
    async function fetchHistory() {
      try {
        const data = await api.getPredictionHistory(tankId);
        if (mounted) {
          // Sort newest first
          const sorted = data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          setPredictions(sorted);
          setError(null);
        }
      } catch (error) {
        if (mounted) setError(error.message || "Failed to fetch prediction history.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchHistory();
    return () => { mounted = false; };
  }, [tankId,revision]);

  return (
    <ModalFrame onClose={onClose} label="Forecast history">
      <div className="bg-white rounded-[24px] shadow-[0_8px_32px_rgba(15,23,42,0.1)] w-full max-w-2xl h-[80vh] flex flex-col transform transition-all">
        <div className="flex justify-between items-center p-[24px] border-b border-slate-100">
          <div>
            <h2 className="text-[20px] font-bold text-slate-900">Forecast History</h2>
            <p className="text-slate-500 text-[14px]">Estimated pH is not physically measured.</p>
          </div>
          <button aria-label="Close dialog" onClick={onClose} className="w-[32px] h-[32px] rounded-full bg-slate-50 flex items-center justify-center hover:bg-slate-100 transition-colors">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M13 1L1 13M1 1L13 13" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-[24px]">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div role="status" aria-label="Loading data" className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-500 font-medium">
              <RequestError message={error} onRetry={retry} />
            </div>
          ) : predictions.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-500 font-medium">
              No historical predictions found.
            </div>
          ) : (
            <div className="flex flex-col gap-[16px]">
              {predictions.map(pred => (
                <div key={pred.id} className="border border-slate-100 rounded-[16px] p-[16px] hover:border-slate-200 hover:shadow-sm transition-all">
                  <p className="text-xs text-amber-800 mb-3">{phProvenanceLabel(pred.ph_provenance)}</p>
                  <div className="flex justify-between items-center mb-[12px]">
                    <div className="flex items-center gap-[8px]">
                      <div className="bg-sky-500 w-[8px] h-[8px] rounded-full"></div>
                      <span className="font-bold text-slate-900 text-[14px]">Forecast Generated</span>
                    </div>
                    <span className="text-[12px] font-medium text-slate-500">
                      {formatTimestamp(pred.created_at)}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-[8px]">
                    {[1, 2, 3, 4].map(hr => (
                      <div key={hr} className="bg-slate-50 rounded-[12px] p-[12px] flex flex-col items-center">
                        <span className="text-[11px] font-bold text-slate-400 uppercase mb-[4px]">+{hr} Hr</span>
                        <div className="flex flex-col gap-[2px] w-full">
                          <div className="flex justify-between items-center">
                            <span className="text-[11px] text-slate-500">Temp</span>
                            <span className="text-[12px] font-bold text-slate-900">{pred[`temperature_${hr}h`]?.toFixed(1)}°</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-[11px] text-slate-500">pH</span>
                            <span className="text-[12px] font-bold text-slate-900">{pred[`pH_${hr}h`]?.toFixed(1)}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-[11px] text-slate-500">Turb</span>
                            <span className="text-[12px] font-bold text-slate-900">{pred[`turbidity_${hr}h`]?.toFixed(0)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </ModalFrame>
  );
}
