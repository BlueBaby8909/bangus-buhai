import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import { api } from "../api/client";
import imgImageAquasensePro from "../assets/Tanks/Device (Angled).png"; 
import arrowBlue from "../assets/Tanks/Arrow(Blue).svg";
import arrowGray from "../assets/Tanks/Arrow(Gray).svg";
import imgImage from "../assets/Tanks/Device (Front).png";

import CreateTankModal from "../components/CreateTankModal";

export default function Tanks() {
  const getStatusInfo = (fallbackStatus) => {
    if (fallbackStatus === "Active") return { color: "#0ea5e9", text: "Active", dot: "bg-sky-500", border: "border-sky-100", bg: "bg-white" };
    if (fallbackStatus === "Standby") return { color: "#f59e0b", text: "Standby", dot: "bg-amber-500", border: "border-amber-100", bg: "bg-white" };
    if (fallbackStatus === "Alert") return { color: "#ef4444", text: "Alert", dot: "bg-red-500", border: "border-red-100", bg: "bg-white" };
    return { color: "#64748b", text: "Offline", dot: "bg-slate-400", border: "border-slate-200", bg: "bg-white" };
  };

  const [displayTanks, setDisplayTanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const loadData = async () => {
    try {
      const [tanks, devices] = await Promise.all([
        api.listTanks(),
        api.listDevices()
      ]);
      
      const summaries = await Promise.all(tanks.map(t => api.getTankSummary(t.id).catch(()=>null)));

      const mergedTanks = tanks.map((tank, i) => {
        const device = devices.find(d => d.tank_id === tank.id);
        const summary = summaries[i];
        
        let actualStatus = "Active";
        if (!device || !device.is_online) {
          actualStatus = "Offline";
        } else if (summary?.latest_water_log) {
           const log = summary.latest_water_log;
           if (log.temperature < 25 || log.temperature > 30 || log.pH < 6.5 || log.pH > 7.5 || log.turbidity > 20) {
             actualStatus = "Alert";
           }
        }
        
        return {
          ...tank,
          _mockStatus: actualStatus,
          _mockDevice: device ? device.name : "No Device"
        };
      });
      setDisplayTanks(mergedTanks);
      setError(null);
    } catch (err) {
      setError("Failed to load tanks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="bg-slate-50 flex flex-col min-h-screen">
      {showCreateModal && (
        <CreateTankModal 
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            setLoading(true);
            loadData();
          }}
        />
      )}
      <AppHeader 
        title="Tanks" 
        leftNode={
          <div className="bg-white rounded-full p-[8px] md:p-[10px] shadow-sm border border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="md:w-[24px] md:h-[24px]">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#64748b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        } 
      />
      <div className="flex-1 w-full pb-[32px] pt-[16px] px-[16px] md:px-[40px] md:py-[32px] flex flex-col gap-[24px] md:gap-[32px]">
        
        {/* Header Hero */}
        <div className="bg-white rounded-[32px] shadow-[0_4px_24px_rgba(15,23,42,0.05)] flex flex-col overflow-hidden relative">
          <div className="h-[180px] md:h-[240px] relative w-full p-[24px] md:p-[40px] z-10 flex items-center">
            <div className="absolute left-[24px] md:left-[40px] w-[180px] md:w-[300px] flex flex-col">
              <div className="bg-sky-50 rounded-[12px] w-[44px] h-[44px] md:w-[56px] md:h-[56px] flex items-center justify-center mb-[16px] shadow-sm">
                <img src={arrowBlue} alt="Manage" className="w-[20px] h-[17px] md:w-[24px] md:h-[20px] brightness-0 invert filter hue-rotate-180" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
              </div>
              <h2 className="font-bold text-slate-900 text-[26px] md:text-[36px] leading-[30px] md:leading-[40px] tracking-[-0.6px]">
                Tank<br/>Management
              </h2>
            </div>
            <div className="absolute right-[-20px] md:right-[40px] top-[10px] md:top-[20px] w-[200px] md:w-[260px] h-[170px] md:h-[220px] drop-shadow-xl">
              <img src={imgImageAquasensePro} alt="Aquasense Pro" className="w-full h-full object-contain" />
            </div>
          </div>
          <div className="bg-sky-600 px-[24px] md:px-[40px] py-[20px] flex justify-between items-center z-10">
            <div className="flex items-center gap-[12px] md:gap-[16px]">
              <div className="bg-sky-300 w-[10px] h-[10px] rounded-full shadow-[0_0_8px_rgba(125,211,252,0.8)]"></div>
              <div className="flex flex-col">
                <span className="font-bold text-white text-[14px] md:text-[16px] leading-[18px] md:leading-[20px]">Aquasense Pro</span>
                <span className="font-medium text-sky-100 text-[12px] md:text-[14px] leading-[16px] md:leading-[18px]">Online · Monitoring</span>
              </div>
            </div>
            <button className="bg-white hover:bg-sky-50 transition-colors rounded-full px-[16px] py-[8px] md:px-[20px] md:py-[10px] flex items-center gap-[6px] shadow-sm">
              <span className="font-bold text-sky-700 text-[13px] md:text-[14px]">Manage</span>
              <img src={arrowBlue} alt="Manage" className="w-[12px] h-[12px] md:w-[14px] md:h-[14px]" style={{ filter: 'invert(45%) sepia(96%) saturate(2371%) hue-rotate(178deg) brightness(96%) contrast(97%)' }} />
            </button>
          </div>
        </div>

        {/* Tanks List */}
        <div className="flex flex-col gap-[16px] md:gap-[24px]">
          <div className="flex justify-between items-center px-[4px]">
            <h3 className="font-bold text-slate-900 text-[20px] md:text-[24px] leading-[28px]">Your Tanks</h3>
            <div className="flex items-center gap-[16px] md:gap-[24px]">
              <div className="hidden md:flex items-center gap-[12px] md:gap-[16px]">
                <div className="flex items-center gap-[6px]">
                  <div className="bg-sky-500 w-[8px] h-[8px] rounded-full"></div>
                  <span className="font-semibold text-slate-500 text-[12px] md:text-[13px]">Active</span>
                </div>
                <div className="flex items-center gap-[6px]">
                  <div className="bg-amber-500 w-[8px] h-[8px] rounded-full"></div>
                  <span className="font-semibold text-slate-500 text-[12px] md:text-[13px]">Standby</span>
                </div>
                <div className="flex items-center gap-[6px]">
                  <div className="bg-red-500 w-[8px] h-[8px] rounded-full"></div>
                  <span className="font-semibold text-slate-500 text-[12px] md:text-[13px]">Alert</span>
                </div>
              </div>
              <button 
                onClick={() => setShowCreateModal(true)}
                className="bg-slate-900 hover:bg-slate-800 text-white rounded-full px-[16px] py-[8px] font-bold text-[13px] md:text-[14px] flex items-center gap-[6px] shadow-sm transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M7 1V13M1 7H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                New Tank
              </button>
            </div>
          </div>

          <div className="flex flex-col md:grid md:grid-cols-2 lg:grid-cols-3 gap-[16px] md:gap-[24px]">
            {loading ? (
              <div className="col-span-full py-10 flex justify-center">
                <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : error ? (
              <div className="col-span-full py-10 text-center text-slate-500">{error}</div>
            ) : displayTanks.length === 0 ? (
              <div className="col-span-full py-10 text-center text-slate-500">No tanks found.</div>
            ) : (
              displayTanks.map((tank) => {
                const statusInfo = getStatusInfo(tank._mockStatus);
                const isOnline = tank._mockStatus !== "Offline";

                return (
                  <Link 
                    key={tank.id} 
                    to={`/tanks/${tank.id}`}
                    className={`bg-white rounded-[24px] shadow-[0_4px_20px_rgba(15,23,42,0.04)] hover:shadow-[0_8px_30px_rgba(15,23,42,0.08)] h-[116px] md:h-[132px] p-[20px] md:p-[24px] flex items-center gap-[16px] overflow-hidden relative block group transition-all duration-300`}
                  >
                    {statusInfo.text === "Alert" && (
                      <div className="absolute top-0 left-0 bottom-0 w-[6px] bg-red-500"></div>
                    )}
                    <div className={`bg-slate-50 border border-slate-100 rounded-[16px] w-[72px] h-[72px] md:w-[84px] md:h-[84px] flex items-center justify-center shrink-0 ${!isOnline ? "opacity-50" : ""}`}>
                      <img src={imgImage} alt="Tank" className="w-[64px] h-[64px] md:w-[72px] md:h-[72px] object-contain" />
                    </div>
                    <div className="flex flex-col flex-1">
                      <h4 className="font-bold text-slate-900 text-[18px] md:text-[20px] leading-[22px]">{tank.name}</h4>
                      <p className="font-medium text-slate-500 text-[14px] md:text-[15px] leading-[20px] mt-[2px]">{tank.growth_stage || "Grow-out"}</p>
                      <div className="flex items-center gap-[6px] mt-[6px] md:mt-[8px]">
                        <div className={`w-[8px] h-[8px] rounded-full ${statusInfo.dot}`}></div>
                        <span className={`font-bold text-[13px] md:text-[14px] leading-[19px]`} style={{ color: statusInfo.color }}>
                          {statusInfo.text}
                        </span>
                        <span className="text-slate-300 text-[16px] leading-[24px]">·</span>
                        <span className="font-medium text-slate-500 text-[13px] md:text-[14px] leading-[19px]">
                          {tank._mockDevice}
                        </span>
                      </div>
                    </div>
                    <div className="w-[32px] h-[32px] md:w-[40px] md:h-[40px] rounded-full bg-slate-50 flex items-center justify-center group-hover:bg-slate-100 transition-colors">
                      <img src={arrowGray} alt="Go" className="w-[6px] h-[10px] md:w-[8px] md:h-[12px]" />
                    </div>
                  </Link>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
