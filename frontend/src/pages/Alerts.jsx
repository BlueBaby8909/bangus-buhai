import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { api } from "../api/client";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState({ critical: 0, warning: 0, forecast: 0 });

  useEffect(() => {
    let mounted = true;
    async function loadAlerts() {
      try {
        const [tanks, devices] = await Promise.all([
          api.listTanks(),
          api.listDevices()
        ]);
        
        const newAlerts = [];
        let crit = 0, warn = 0, fore = 0;

        for (const tank of tanks) {
          const device = devices.find(d => d.id === tank.device_id);
          if (!device || !device.is_online) {
            crit++;
            newAlerts.push({
              id: `crit-${tank.id}`,
              type: "Critical",
              color: "bg-red-50 text-red-600",
              titleColor: "text-red-500",
              dotColor: "bg-red-500",
              tank: tank.name,
              category: "Connection",
              time: "Just now",
              title: "Sensor offline",
              message: "Device lost connection. Unable to receive telemetry or send commands."
            });
          }
          
          try {
            const summary = await api.getTankSummary(tank.id);
            if (summary?.latest_water_log) {
               const temp = summary.latest_water_log.temperature;
               const ph = summary.latest_water_log.pH;
               const turb = summary.latest_water_log.turbidity;
               if (temp < 25 || temp > 30) {
                 warn++;
                 newAlerts.push({
                   id: `warn-temp-${tank.id}`,
                   type: "Warning",
                   color: "bg-amber-50 text-amber-600",
                   titleColor: "text-amber-500",
                   dotColor: "bg-amber-500",
                   tank: tank.name,
                   category: "Temperature",
                   time: "Just now",
                   title: `${temp.toFixed(1)} °C — Out of range`,
                   message: `Exceeds optimal 25–30 °C threshold. Monitor heater relay.`
                 });
               }
               if (ph < 6.5 || ph > 7.5) {
                 warn++;
                 newAlerts.push({
                   id: `warn-ph-${tank.id}`,
                   type: "Warning",
                   color: "bg-amber-50 text-amber-600",
                   titleColor: "text-amber-500",
                   dotColor: "bg-amber-500",
                   tank: tank.name,
                   category: "pH",
                   time: "Just now",
                   title: `${ph.toFixed(1)} — Out of range`,
                   message: `Outside optimal 6.5-7.5 threshold.`
                 });
               }
               if (turb > 20) {
                 warn++;
                 newAlerts.push({
                   id: `warn-turb-${tank.id}`,
                   type: "Warning",
                   color: "bg-amber-50 text-amber-600",
                   titleColor: "text-amber-500",
                   dotColor: "bg-amber-500",
                   tank: tank.name,
                   category: "Turbidity",
                   time: "Just now",
                   title: `${turb.toFixed(1)} NTU — Elevated`,
                   message: `Exceeds 20 NTU threshold. Consider partial water change.`
                 });
               }
            }
            
            // Forecast Mock
            const pred = await api.getLatestPrediction(tank.id).catch(() => null);
            if (pred) {
               // Checking +1h forecast
               if (pred.temperature_1h > 30) {
                 fore++;
                 newAlerts.push({
                   id: `fore-${tank.id}`,
                   type: "AI Forecast",
                   color: "bg-sky-50 text-sky-700",
                   titleColor: "text-sky-600",
                   dotColor: "bg-sky-500",
                   tank: tank.name,
                   category: "Temp Forecast",
                   time: "ML",
                   title: `Rise to ${pred.temperature_1h.toFixed(1)} °C in ~1 h`,
                   message: `LSTM model predicts temperature may exceed the upper threshold soon.`
                 });
               }
            }
          } catch(e) {}
        }
        
        if (mounted) {
          setAlerts(newAlerts);
          setCounts({ critical: crit, warning: warn, forecast: fore });
        }
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadAlerts();
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
          <h3 className="font-bold text-slate-900 text-[18px] md:text-[24px]">Active Alerts</h3>
          
          <div className="flex flex-col md:grid md:grid-cols-2 lg:grid-cols-3 gap-[16px] md:gap-[24px]">
            {loading ? (
              <div className="col-span-full py-10 flex justify-center">
                <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : alerts.length === 0 ? (
              <div className="col-span-full py-10 text-center text-slate-500">No active alerts. All systems operational.</div>
            ) : (
              alerts.map(alert => (
                <div key={alert.id} className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition-shadow flex flex-col p-[20px] md:p-[24px]">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-[12px]">
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
