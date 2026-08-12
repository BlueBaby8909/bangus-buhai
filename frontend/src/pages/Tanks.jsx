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
    <div className="bg-white flex flex-col min-h-screen">
      <AppHeader title="Hatchery Monitor" />
      <div 
        className="flex-1 w-full pb-[32px] pt-[16px] px-[16px] flex flex-col gap-[20px]"
        style={{ backgroundImage: "linear-gradient(140.75deg, rgb(248, 249, 250) 8.48%, rgb(243, 244, 245) 91.51%)" }}
      >
        <div className="bg-[#f3f4f5] rounded-[32px] shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.1)] flex flex-col overflow-hidden">
          <div className="h-[177px] relative w-full">
            <div className="absolute left-[32px] top-[20px] w-[160px] flex flex-col">
              <div className="bg-[#003fb1] rounded-[8px] w-[40px] h-[40px] flex items-center justify-center mb-[12px]">
                <img src={arrowBlue} alt="Manage" className="w-[20px] h-[17px] brightness-0 invert" />
              </div>
              <h2 className="font-bold text-[#101828] text-[24px] leading-[30px] tracking-[-0.6px]">
                Tank<br/>Management
              </h2>
              <p className="text-[#6a7282] text-[11px] leading-[16.5px] mt-[4px]">
                Select a tank to manage devices and view readings.
              </p>
            </div>
            <div className="absolute right-[-10px] top-[8px] w-[180px] h-[160px] drop-shadow-[0px_20px_12px_rgba(0,0,0,0.15)]">
              <img src={imgImageAquasensePro} alt="Aquasense Pro" className="w-full h-full object-contain" />
            </div>
          </div>
          <div className="bg-[#003fb1] px-[32px] py-[16px] flex justify-between items-center rounded-b-[32px]">
            <div className="flex items-center gap-[8px]">
              <div className="bg-[#00d492] w-[8px] h-[8px] rounded-full"></div>
              <div className="flex flex-col">
                <span className="font-semibold text-white text-[13px] leading-[16px]">Aquasense Pro</span>
                <span className="font-semibold text-[rgba(255,255,255,0.7)] text-[13px] leading-[16px]">Online · Monitoring</span>
              </div>
            </div>
            <button className="bg-white rounded-full px-[20px] py-[8px] flex items-center gap-[8px]">
              <span className="font-bold text-[#003fb1] text-[13px] leading-[19px]">Manage Unit</span>
              <img src={arrowBlue} alt="Manage" className="w-[12px] h-[12px]" />
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-[12px]">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-[#101828] text-[20px] leading-[28px]">Your Tanks</h3>
            <div className="flex items-center gap-[12px]">
              <div className="flex items-center gap-[4px]">
                <div className="bg-[#00bc7d] w-[10px] h-[10px] rounded-full"></div>
                <span className="font-medium text-[#566068] text-[12px]">Active</span>
              </div>
              <div className="flex items-center gap-[4px]">
                <div className="bg-[#fe9a00] w-[10px] h-[10px] rounded-full"></div>
                <span className="font-medium text-[#566068] text-[12px]">Standby</span>
              </div>
              <div className="flex items-center gap-[4px]">
                <div className="bg-[#ec003f] w-[10px] h-[10px] rounded-full"></div>
                <span className="font-medium text-[#566068] text-[12px]">Alert</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-[12px]">
            {displayTanks.map((tank) => {
              const statusInfo = getStatusInfo(tank._mockStatus);
              const isOnline = tank._mockStatus !== "Offline";

              return (
                <Link 
                  key={tank.id} 
                  to={`/tanks/${tank.id}`}
                  className={`bg-white border-[1.2px] ${statusInfo.border} rounded-[16px] shadow-[0px_2px_8px_0px_rgba(0,0,0,0.06)] h-[108px] p-[16px] flex items-center gap-[16px] overflow-hidden relative block`}
                >
                  {statusInfo.text === "Alert" && (
                    <div className="absolute top-0 left-0 right-0 h-[4px] bg-[#ec003f]"></div>
                  )}
                  <div className={`bg-[#f3f4f5] border-[1.2px] border-[#e5e7eb] rounded-[12px] w-[64px] h-[64px] flex items-center justify-center shrink-0 ${!isOnline ? "opacity-50" : ""}`}>
                    <img src={imgImage} alt="Tank" className="w-[61px] h-[61px] object-contain" />
                  </div>
                  <div className="flex flex-col flex-1">
                    <h4 className="font-semibold text-[#101828] text-[16px] leading-[22px]">{tank.name}</h4>
                    <p className="font-normal text-[#99a1af] text-[14px] leading-[20px]">{tank.growth_stage}</p>
                    <div className="flex items-center gap-[6px] mt-[6px]">
                      <div className={`w-[8px] h-[8px] rounded-full ${statusInfo.dot}`}></div>
                      <span className={`font-medium text-[13px] leading-[19px]`} style={{ color: statusInfo.color }}>
                        {statusInfo.text}
                      </span>
                      <span className="text-[#d1d5dc] text-[16px] leading-[24px]">·</span>
                      <span className="font-normal text-[#99a1af] text-[13px] leading-[19px]">
                        {tank._mockDevice}
                      </span>
                    </div>
                  </div>
                  <img src={arrowGray} alt="Go" className="w-[7px] h-[12px]" />
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
