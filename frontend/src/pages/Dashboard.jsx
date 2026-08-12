import { Link } from "react-router-dom";
import AppHeader from "../components/AppHeader";
import powerButtonIcon from "../assets/DashBoard/PowerButton.svg";
import imgImageAquasenseProDevice from "../assets/DashBoard/Device (Front).png";
import imgIcon2 from "../assets/DashBoard/Star.svg";
import imgIcon4 from "../assets/DashBoard/Temp(Orange).svg";
import imgIcon5 from "../assets/DashBoard/Ph(Blue).svg";
import imgIcon6 from "../assets/DashBoard/Turb(Gray).svg";

export default function Dashboard() {
  const firstTank = { id: 1, name: "Tank A1" };
  const firstDevice = { name: "Aquasense Pro", is_online: true };
  const latestLog = { temp: 28.5, ph: 7.2, turbidity: 5 };

  return (
    <div className="bg-white flex flex-col min-h-screen">
      <AppHeader 
        title="Hatchery Monitor" 
        leftNode={
          <div className="bg-[#f3f4f6] rounded-full p-[8px]">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 12H21M3 6H21M3 18H21" stroke="#5c666e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        } 
      />
      <div 
        className="flex-1 w-full pb-[32px] pt-[24px] px-[16px] flex flex-col gap-[24px]"
        style={{ backgroundImage: "linear-gradient(139.52deg, rgb(235, 245, 255) 8.48%, rgb(240, 246, 255) 91.51%)" }}
      >
        <div className="flex flex-col">
          <h2 className="font-bold text-[#101828] text-[24px] leading-[30px]">Hello, Manager</h2>
          <p className="text-[#99a1af] text-[14px] leading-[20px] mt-1">Bangus Buhai water quality at a glance.</p>
        </div>

        <div className="bg-[#003fb1] rounded-[16px] p-[16px] flex items-center gap-[16px] drop-shadow-[0px_4px_8px_rgba(0,63,177,0.2)]">
          <div className="bg-[rgba(255,255,255,0.15)] rounded-[12px] w-[40px] h-[40px] flex items-center justify-center shrink-0">
            <img src={imgIcon2} alt="AI" className="w-[20px] h-[20px]" />
          </div>
          <div className="flex flex-col flex-1">
            <h3 className="font-semibold text-white text-[14px] leading-[19px]">AI Forecasting Active</h3>
            <p className="text-[rgba(255,255,255,0.7)] text-[12px] leading-[18px] mt-[2px]">Predicting Temp · pH · Turbidity</p>
          </div>
          <div className="bg-white rounded-full px-[10px] py-[4px]">
            <span className="font-bold text-[#003fb1] text-[11px]">LSTM</span>
          </div>
        </div>

        <div className="flex flex-col gap-[12px]">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-[#101828] text-[18px] leading-[28px]">{firstTank.name}</h3>
            <Link to="/tanks" className="bg-[#00bc7d] rounded-full px-[16px] py-[6px] text-white text-[13px] font-medium leading-[13px]">
              See All
            </Link>
          </div>

          <Link to={`/tanks/${firstTank.id}`} className="bg-white rounded-[16px] border-[1.2px] border-[#f3f4f6] overflow-hidden shadow-[0px_4px_16px_0px_rgba(0,0,0,0.07)] flex flex-col h-[262px] block">
            <div className="p-[16px] flex-1 flex flex-col">
              <div className="flex justify-between items-start">
                <div className="flex flex-col">
                  <h4 className="font-bold text-[#101828] text-[18px]">{firstTank.name}</h4>
                  <p className="font-medium text-[#99a1af] text-[13px] mt-[2px]">{firstDevice.name}</p>
                  <p className={`font-medium text-[14px] mt-[2px] ${firstDevice.is_online ? "text-[#009966]" : "text-[#99a1af]"}`}>
                    {firstDevice.is_online ? "Connected" : "Disconnected"}
                  </p>
                </div>
                <div className="bg-[#00bcff] rounded-full w-[48px] h-[48px] flex items-center justify-center drop-shadow-[0px_8px_8px_rgba(14,165,233,0.3)]">
                  <img src={powerButtonIcon} alt="Power" className="w-[23px] h-[23px]" />
                </div>
              </div>

              <div className="mt-auto flex justify-between items-end">
                <div className="flex flex-col mb-4">
                  <p className="font-medium text-[#99a1af] text-[13px] tracking-[0.65px] uppercase">Sensors Active</p>
                  <p className="font-bold text-[#00bc7d] text-[48px] leading-[48px] tracking-[-1.2px] mt-1">3 / 3</p>
                </div>
                <img src={imgImageAquasenseProDevice} alt="Device" className="w-[128px] h-[112px] object-contain drop-shadow-[0px_8px_24px_rgba(0,0,0,0.12)]" />
              </div>
            </div>
            <div className="px-[16px] pb-[16px] pt-[12px]">
              <div className="bg-[#f3f4f6] h-[6px] rounded-full w-full overflow-hidden">
                <div className="bg-[#00bc7d] h-full w-full rounded-full"></div>
              </div>
            </div>
          </Link>
        </div>

        <div className="flex flex-col gap-[8px]">
          <h3 className="font-bold text-[#101828] text-[18px] leading-[28px]">Live Readings</h3>
          <div className="grid grid-cols-2 grid-rows-2 gap-[12px]">
            {/* Temperature Card */}
            <div className="bg-[rgba(255,255,255,0.95)] border-[1.2px] border-[rgba(243,244,246,0.5)] rounded-[12px] p-[16px] shadow-[0px_4px_15px_0px_rgba(26,86,219,0.04)] flex flex-col justify-between overflow-hidden relative min-h-[128px]">
              <div className="flex justify-between items-start z-10">
                <img src={imgIcon4} alt="Temp" className="w-[18px] h-[18px]" />
                <span className="bg-[#e5e7eb] text-[#6a7282] text-[10px] font-semibold px-[8px] py-[2px] rounded-[4px]">Avg</span>
              </div>
              <div className="flex flex-col z-10 mt-auto">
                <div className="flex items-end gap-[2px]">
                  <span className="font-bold text-[#101828] text-[36px] leading-[36px] tracking-[-0.9px]">{latestLog.temp}</span>
                  <span className="font-semibold text-[#101828] text-[18px] leading-[28px] pb-[2px]">°C</span>
                </div>
                <span className="font-medium text-[#99a1af] text-[12px] mt-1">Temperature</span>
              </div>
              <div className="absolute w-[64px] h-[64px] bg-[rgba(254,154,0,0.05)] rounded-full blur-[24px] right-[-10px] bottom-[-10px]"></div>
            </div>

            {/* pH Card */}
            <div className="bg-[rgba(255,255,255,0.95)] border-[1.2px] border-[rgba(243,244,246,0.5)] rounded-[12px] p-[16px] shadow-[0px_4px_15px_0px_rgba(26,86,219,0.04)] flex flex-col justify-between overflow-hidden relative min-h-[128px]">
              <div className="flex justify-between items-start z-10">
                <img src={imgIcon5} alt="pH" className="w-[16px] h-[20px]" />
                <span className="bg-[#d0fae5] text-[#009966] text-[10px] font-semibold px-[8px] py-[2px] rounded-[4px]">Optimal</span>
              </div>
              <div className="flex flex-col z-10 mt-auto">
                <span className="font-bold text-[#101828] text-[36px] leading-[36px] tracking-[-0.9px]">{latestLog.ph}</span>
                <span className="font-medium text-[#99a1af] text-[12px] mt-1">pH Level</span>
              </div>
              <div className="absolute w-[64px] h-[64px] bg-[rgba(43,127,255,0.05)] rounded-full blur-[24px] right-[-10px] bottom-[-10px]"></div>
            </div>

            {/* Turbidity Card */}
            <div className="col-span-2 bg-[rgba(255,255,255,0.95)] border-[1.2px] border-[rgba(243,244,246,0.5)] rounded-[12px] p-[16px] shadow-[0px_4px_15px_0px_rgba(26,86,219,0.04)] flex justify-between items-end min-h-[123px]">
              <div className="flex flex-col justify-between h-full">
                <img src={imgIcon6} alt="Turbidity" className="w-[20px] h-[17px] mb-[12px]" />
                <div className="flex flex-col mt-auto">
                  <div className="flex items-end gap-[4px]">
                    <span className="font-bold text-[#101828] text-[36px] leading-[36px] tracking-[-0.9px]">{latestLog.turbidity}</span>
                    <span className="font-semibold text-[#99a1af] text-[18px] leading-[28px] pb-[2px]">NTU</span>
                  </div>
                  <span className="font-medium text-[#99a1af] text-[12px] mt-1">Turbidity</span>
                </div>
              </div>
              <div className="flex items-end gap-[4px] h-[32px] opacity-50 pb-[2px]">
                <div className="w-[12px] h-[10px] bg-[#e5e7eb] rounded-t-[4px]"></div>
                <div className="w-[12px] h-[16px] bg-[#e5e7eb] rounded-t-[4px]"></div>
                <div className="w-[12px] h-[21px] bg-[#e5e7eb] rounded-t-[4px]"></div>
                <div className="w-[12px] h-[32px] bg-[#566068] rounded-t-[4px]"></div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
