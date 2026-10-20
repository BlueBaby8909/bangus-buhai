import { useState, useEffect } from "react";
import AppHeader from "../components/AppHeader";
import { api } from "../api/client";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [counts, setCounts] = useState({ critical: 0, warning: 0, forecast: 0 });

  useEffect(() => {
    let mounted = true;
    api.listAlerts().then((items) => {
      if (!mounted) return;
      setAlerts(items);
      setCounts({ critical: items.filter((item) => item.type === 'Critical').length,
        warning: items.filter((item) => item.type === 'Warning').length,
        forecast: items.filter((item) => item.type === 'AI Forecast').length });
    }).catch((err) => { if (mounted) setError(err.message); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);
  return (
    <div className="bg-slate-50 flex flex-col min-h-screen">
      <AppHeader 
        title="Alerts" 
        leftNode={
          <div className="w-[40px] h-[40px] bg-white rounded-full flex items-center justify-center shadow-sm border border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#64748b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        }
      />
      
      <div className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] md:px-[40px] md:py-[40px] flex flex-col gap-[24px] md:gap-[32px]">
        <div className="grid grid-cols-3 gap-[12px] md:gap-[24px]">
          <div className="bg-white rounded-[20px] md:rounded-[24px] p-[16px] md:p-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col gap-[6px] md:gap-[12px] items-center text-center">
            <div className="flex items-center gap-[6px]">
              <div className="bg-red-500 w-[8px] h-[8px] md:w-[10px] md:h-[10px] rounded-full"></div>
              <span className="font-bold text-slate-500 text-[10px] md:text-[12px] tracking-[0.5px] uppercase">Critical</span>
            </div>
            <p className="font-bold text-red-500 text-[28px] md:text-[40px] leading-[32px] md:leading-[48px]">
              {loading ? "-" : counts.critical}
            </p>
          </div>
          
          <div className="bg-white rounded-[20px] md:rounded-[24px] p-[16px] md:p-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col gap-[6px] md:gap-[12px] items-center text-center">
            <div className="flex items-center gap-[6px]">
              <div className="bg-amber-500 w-[8px] h-[8px] md:w-[10px] md:h-[10px] rounded-full"></div>
              <span className="font-bold text-slate-500 text-[10px] md:text-[12px] tracking-[0.5px] uppercase">Warning</span>
            </div>
            <p className="font-bold text-amber-500 text-[28px] md:text-[40px] leading-[32px] md:leading-[48px]">
              {loading ? "-" : counts.warning}
            </p>
          </div>
          
          <div className="bg-white rounded-[20px] md:rounded-[24px] p-[16px] md:p-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col gap-[6px] md:gap-[12px] items-center text-center">
            <div className="flex items-center gap-[6px]">
              <div className="bg-sky-500 w-[8px] h-[8px] md:w-[10px] md:h-[10px] rounded-full"></div>
              <span className="font-bold text-slate-500 text-[10px] md:text-[12px] tracking-[0.5px] uppercase">Forecast</span>
            </div>
            <p className="font-bold text-sky-600 text-[28px] md:text-[40px] leading-[32px] md:leading-[48px]">
              {loading ? "-" : counts.forecast}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-[16px] md:gap-[24px]">
          <h3 className="font-bold text-slate-900 text-[18px] md:text-[24px]">Sample Alerts</h3>
          
          <div className="flex flex-col md:grid md:grid-cols-2 lg:grid-cols-3 gap-[16px] md:gap-[24px]">
            {loading ? (
              <div className="col-span-full py-10 flex justify-center">
                <div role="status" aria-label="Loading sample data" className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : error ? (
              <p role="alert" className="col-span-full text-red-700">{error}</p>
            ) : alerts.length === 0 ? (
              <div className="col-span-full py-10 text-center text-slate-500">No sample alerts are available. This does not establish real system status.</div>
            ) : (
              alerts.map(alert => (
                <div key={alert.id} className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col p-[20px] md:p-[24px]">
                  <div className="flex items-start justify-between">
                    <div className="sample-alert-meta flex items-center gap-[12px]">
                      <div className={`px-[10px] py-[4px] rounded-[6px] ${alert.color}`}>
                        <span className="font-bold text-[11px] md:text-[12px] tracking-wide uppercase">{alert.type}</span>
                      </div>
                      <span className="font-medium text-slate-500 text-[13px] md:text-[14px]">{alert.tank}</span>
                      <span className="text-slate-300 text-[14px]">·</span>
                      <span className="font-medium text-slate-400 text-[13px] md:text-[14px]">{alert.category}</span>
                    </div>
                    <span className="font-medium text-slate-400 text-[11px] md:text-[12px] pt-[4px]">{alert.time}</span>
                  </div>
                  <p className="font-bold text-slate-900 text-[16px] md:text-[18px] mt-[16px] md:mt-[20px]">{alert.title}</p>
                  <p className="text-slate-500 text-[14px] md:text-[15px] leading-[22px] md:leading-[24px] mt-[4px]">{alert.message}</p>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
