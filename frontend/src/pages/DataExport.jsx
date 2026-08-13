import { useState, useEffect } from "react";
import AppHeader from "../components/AppHeader";
import { api } from "../api/client";

export default function DataExport() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function fetchLogs() {
      try {
        // Fetch the latest 100 logs globally
        const data = await api.getAllLogs({ limit: 100 });
        if (mounted) {
          setLogs(data);
          setError(null);
        }
      } catch (err) {
        if (mounted) setError("Failed to fetch global logs.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchLogs();
    return () => { mounted = false; };
  }, []);

  const handleExportCSV = () => {
    if (!logs.length) return;
    
    // Create CSV content
    const headers = ["ID", "Tank ID", "Recorded At", "Temp (°C)", "pH", "Turbidity (NTU)", "Relay On"];
    const rows = logs.map(log => [
      log.id,
      log.tank_id,
      new Date(log.recorded_at).toLocaleString(),
      log.temperature?.toFixed(2) || "",
      log.pH?.toFixed(2) || "",
      log.turbidity?.toFixed(2) || "",
      log.relay_on ? "Yes" : "No"
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
      
    // Download
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `bangus_logs_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-slate-50 flex flex-col min-h-screen pb-[100px] md:pb-[40px]">
      <AppHeader title="Global Data Export" />
      
      <div className="px-[16px] md:px-[40px] py-[24px] md:py-[32px] flex-1 flex flex-col max-w-5xl mx-auto w-full">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-[24px] gap-[16px]">
          <div>
            <h2 className="font-bold text-slate-900 text-[20px] md:text-[24px]">Recent Telemetry</h2>
            <p className="text-slate-500 text-[14px] mt-[4px]">Showing the 100 most recent water logs across all tanks.</p>
          </div>
          
          <button 
            onClick={handleExportCSV}
            disabled={loading || logs.length === 0}
            className="w-full md:w-auto bg-sky-500 hover:bg-sky-600 text-white px-[20px] py-[12px] rounded-[16px] font-bold text-[14px] flex items-center justify-center gap-[8px] transition-colors shadow-[0_4px_12px_rgba(14,165,233,0.3)] disabled:opacity-50 disabled:hover:bg-sky-500"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Export to CSV
          </button>
        </div>

        <div className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] overflow-hidden border border-slate-100 flex-1 flex flex-col">
          {loading ? (
            <div className="flex-1 flex items-center justify-center min-h-[300px]">
              <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center min-h-[300px] text-red-500 font-medium">
              {error}
            </div>
          ) : logs.length === 0 ? (
            <div className="flex-1 flex items-center justify-center min-h-[300px] text-slate-500 font-medium">
              No data available.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-[12px] uppercase tracking-[1px] font-bold">
                    <th className="py-[16px] px-[24px]">Time</th>
                    <th className="py-[16px] px-[24px]">Tank ID</th>
                    <th className="py-[16px] px-[24px]">Temp</th>
                    <th className="py-[16px] px-[24px]">pH</th>
                    <th className="py-[16px] px-[24px]">Turbidity</th>
                    <th className="py-[16px] px-[24px]">Relay</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                      <td className="py-[16px] px-[24px] text-[14px] text-slate-600 font-medium whitespace-nowrap">
                        {new Date(log.recorded_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
                      </td>
                      <td className="py-[16px] px-[24px] text-[14px] text-slate-900 font-bold">
                        Tank {log.tank_id}
                      </td>
                      <td className="py-[16px] px-[24px] text-[14px] text-slate-900 font-semibold">
                        {log.temperature?.toFixed(1) || "--"}°C
                      </td>
                      <td className="py-[16px] px-[24px] text-[14px] text-slate-900 font-semibold">
                        {log.pH?.toFixed(1) || "--"}
                      </td>
                      <td className="py-[16px] px-[24px] text-[14px] text-slate-900 font-semibold">
                        {log.turbidity?.toFixed(1) || "--"}
                      </td>
                      <td className="py-[16px] px-[24px]">
                        <div className={`inline-flex items-center px-[8px] py-[4px] rounded-[6px] text-[12px] font-bold ${log.relay_on ? 'bg-sky-50 text-sky-600' : 'bg-slate-100 text-slate-500'}`}>
                          {log.relay_on ? 'ON' : 'OFF'}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
