import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import imgImageAquasensePro from "../assets/Tanks/Device (Angled).png"; 
import arrowBlue from "../assets/Tanks/Arrow(Blue).svg";
import arrowGray from "../assets/Tanks/Arrow(Gray).svg";
import imgImage from "../assets/Tanks/Device (Front).png";

export default function Tanks() {
  const getStatusInfo = (fallbackStatus) => {
    if (fallbackStatus === "Active") return { color: "#009966", text: "Active", dot: "bg-[#00bc7d]", border: "border-[#e5e7eb]", bg: "bg-white" };
    if (fallbackStatus === "Standby") return { color: "#e17100", text: "Standby", dot: "bg-[#fe9a00]", border: "border-[rgba(254,230,133,0.6)]", bg: "bg-white" };
    if (fallbackStatus === "Alert") return { color: "#ec003f", text: "Alert", dot: "bg-[#ec003f]", border: "border-[#fecaca]", bg: "bg-white" };
    return { color: "#99a1af", text: "Offline", dot: "bg-[#99a1af]", border: "border-[#e5e7eb]", bg: "bg-white" };
  };

  const displayTanks = [
    { id: 1, name: "Tank A1", growth_stage: "Grow-out", _mockStatus: "Active", _mockDevice: "Aquasense Pro" },
    { id: 2, name: "Nursery B", growth_stage: "Nursery", _mockStatus: "Standby", _mockDevice: "Aquasense Pro #2" },
    { id: 3, name: "Tank C3", growth_stage: "Grow-out", _mockStatus: "Alert", _mockDevice: "Aquasense Pro #3" },
    { id: 4, name: "Reserve Unit X", growth_stage: "Empty", _mockStatus: "Offline", _mockDevice: "No Device" }
  ];

  return (
    <div className="bg-[#f4f6f8] flex flex-col min-h-screen">
      <AppHeader 
        title="Hatchery Monitor" 
        leftNode={
          <div className="bg-white rounded-full p-[8px] shadow-sm border border-gray-100">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#5c666e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        } 
      />
      <div className="flex-1 w-full pb-[32px] pt-[16px] px-[16px] flex flex-col gap-[24px]">
        <div className="bg-white rounded-[32px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] flex flex-col overflow-hidden relative">
          <div className="absolute top-0 right-0 w-full h-[180px] opacity-[0.03] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-[#003fb1] via-transparent to-transparent pointer-events-none"></div>
          <div className="h-[180px] relative w-full p-[24px] z-10">
            <div className="absolute left-[24px] top-[24px] w-[180px] flex flex-col">
              <div className="bg-blue-50 rounded-[12px] w-[44px] h-[44px] flex items-center justify-center mb-[16px] shadow-sm">
                <img src={arrowBlue} alt="Manage" className="w-[20px] h-[17px] brightness-0 invert filter hue-rotate-180" style={{ filter: 'brightness(0) saturate(100%) invert(20%) sepia(91%) saturate(2311%) hue-rotate(209deg) brightness(97%) contrast(106%)' }} />
              </div>
              <h2 className="font-bold text-[#101828] text-[26px] leading-[30px] tracking-[-0.6px]">
                Tank<br/>Management
              </h2>
            </div>
            <div className="absolute right-[-20px] top-[10px] w-[200px] h-[170px] drop-shadow-xl">
              <img src={imgImageAquasensePro} alt="Aquasense Pro" className="w-full h-full object-contain" />
            </div>
          </div>
          <div className="bg-gradient-to-r from-[#003fb1] to-[#0055ff] px-[24px] py-[20px] flex justify-between items-center z-10">
            <div className="flex items-center gap-[12px]">
              <div className="bg-[#00d492] w-[10px] h-[10px] rounded-full shadow-[0_0_8px_rgba(0,212,146,0.8)]"></div>
              <div className="flex flex-col">
                <span className="font-bold text-white text-[14px] leading-[18px]">Aquasense Pro</span>
                <span className="font-medium text-[rgba(255,255,255,0.8)] text-[12px] leading-[16px]">Online · Monitoring</span>
              </div>
            </div>
            <button className="bg-white rounded-full px-[16px] py-[8px] flex items-center gap-[6px] shadow-sm">
              <span className="font-bold text-[#003fb1] text-[13px]">Manage</span>
              <img src={arrowBlue} alt="Manage" className="w-[12px] h-[12px]" />
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-[16px]">
          <div className="flex justify-between items-center px-[4px]">
            <h3 className="font-bold text-[#101828] text-[20px] leading-[28px]">Your Tanks</h3>
            <div className="flex items-center gap-[12px]">
              <div className="flex items-center gap-[6px]">
                <div className="bg-[#00bc7d] w-[8px] h-[8px] rounded-full"></div>
                <span className="font-semibold text-[#6b7280] text-[12px]">Active</span>
              </div>
              <div className="flex items-center gap-[6px]">
                <div className="bg-[#fe9a00] w-[8px] h-[8px] rounded-full"></div>
                <span className="font-semibold text-[#6b7280] text-[12px]">Standby</span>
              </div>
              <div className="flex items-center gap-[6px]">
                <div className="bg-[#ec003f] w-[8px] h-[8px] rounded-full"></div>
                <span className="font-semibold text-[#6b7280] text-[12px]">Alert</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-[16px]">
            {displayTanks.map((tank) => {
              const statusInfo = getStatusInfo(tank._mockStatus);
              const isOnline = tank._mockStatus !== "Offline";

              return (
                <Link 
                  key={tank.id} 
                  to={`/tanks/${tank.id}`}
                  className={`bg-white rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] h-[116px] p-[20px] flex items-center gap-[16px] overflow-hidden relative block group transition-all duration-300 hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)]`}
                >
                  {statusInfo.text === "Alert" && (
                    <div className="absolute top-0 left-0 bottom-0 w-[6px] bg-[#ec003f]"></div>
                  )}
                  <div className={`bg-gray-50 border-[1px] border-gray-100 rounded-[16px] w-[72px] h-[72px] flex items-center justify-center shrink-0 shadow-inner ${!isOnline ? "opacity-50" : ""}`}>
                    <img src={imgImage} alt="Tank" className="w-[64px] h-[64px] object-contain" />
                  </div>
                  <div className="flex flex-col flex-1">
                    <h4 className="font-bold text-[#101828] text-[18px] leading-[22px]">{tank.name}</h4>
                    <p className="font-medium text-[#6b7280] text-[14px] leading-[20px] mt-[2px]">{tank.growth_stage}</p>
                    <div className="flex items-center gap-[6px] mt-[6px]">
                      <div className={`w-[8px] h-[8px] rounded-full ${statusInfo.dot}`}></div>
                      <span className={`font-bold text-[13px] leading-[19px]`} style={{ color: statusInfo.color }}>
                        {statusInfo.text}
                      </span>
                      <span className="text-[#d1d5dc] text-[16px] leading-[24px]">·</span>
                      <span className="font-medium text-[#6b7280] text-[13px] leading-[19px]">
                        {tank._mockDevice}
                      </span>
                    </div>
                  </div>
                  <div className="w-[32px] h-[32px] rounded-full bg-gray-50 flex items-center justify-center group-hover:bg-gray-100 transition-colors">
                    <img src={arrowGray} alt="Go" className="w-[6px] h-[10px]" />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
